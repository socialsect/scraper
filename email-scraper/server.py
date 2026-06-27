"""
FastAPI server for email scraper with database persistence and real-time SSE streaming.
"""

import asyncio
import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import aiosqlite
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config import OUTPUT_FILE


# ============================================================================
# Data Models
# ============================================================================

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class JobStats:
    """Live stats from the scraper — mirrors LiveDisplay state."""
    query: str
    backend: str
    elapsed_seconds: int = 0
    pages_crawled: int = 0
    new_emails: int = 0
    total_emails: int = 0
    last_email: str = ""
    queue_size: int = 0
    errors: int = 0
    rate_per_min: float = 0.0


@dataclass
class Job:
    """Job state container."""
    id: str
    status: JobStatus
    query: str
    engine: str = "google"
    backend: str = "scrapling"
    expand_locations: bool = False
    locations: list[str] = field(default_factory=list)
    check_mx: bool = True
    output_file: str = OUTPUT_FILE
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    stats: JobStats = field(default_factory=lambda: JobStats(query="", backend=""))
    task: Optional[asyncio.Task] = field(default=None, init=False)
    logs: list[str] = field(default_factory=list, init=False)


class JobRequest(BaseModel):
    query: str
    engine: str = "google"
    backend: str = "scrapling"
    expand_locations: bool = False
    locations: list[str] = []
    check_mx: bool = True
    output_file: Optional[str] = None


class JobResponse(BaseModel):
    id: str
    status: str
    query: str
    engine: str
    backend: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    stats: dict


# ============================================================================
# Server state
# ============================================================================

app = FastAPI(title="Email Scraper API", version="0.2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database instance (initialized on startup)
db = None

# In-memory cache for RUNNING jobs only
running_jobs: dict[str, Job] = {}
job_lock = asyncio.Lock()

# SSE event queues: job_id -> asyncio.Queue
job_event_queues: dict[str, asyncio.Queue] = {}
queue_lock = asyncio.Lock()


# ============================================================================
# Database helpers
# ============================================================================

async def _save_job_to_db(job: Job):
    """Save or update job in database."""
    try:
        # Check if job exists
        async with db._get_connection() as conn:
            cursor = await conn.execute(
                "SELECT job_id FROM jobs WHERE job_id = ?",
                (job.id,)
            )
            exists = await cursor.fetchone()
            
            if exists:
                # Update existing job
                await conn.execute("""
                    UPDATE jobs SET
                        status = ?,
                        started_at = ?,
                        completed_at = ?,
                        total_emails = ?,
                        errors = ?
                    WHERE job_id = ?
                """, (
                    job.status.value,
                    job.started_at,
                    job.completed_at,
                    job.stats.total_emails,
                    job.stats.errors,
                    job.id,
                ))
            else:
                # Insert new job
                await conn.execute("""
                    INSERT INTO jobs (
                        job_id, query, engine, backend, status,
                        started_at, completed_at, total_emails, errors, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.id,
                    job.query,
                    job.engine,
                    job.backend,
                    job.status.value,
                    job.started_at,
                    job.completed_at,
                    job.stats.total_emails,
                    job.stats.errors,
                    job.created_at,
                ))
            await conn.commit()
    except Exception as e:
        print(f"[DB] Error saving job {job.id}: {e}")


async def _load_job_from_db(job_id: str) -> Optional[Job]:
    """Load job from database."""
    try:
        async with db._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT job_id, query, engine, backend, status,
                       started_at, completed_at, total_emails, errors, created_at
                FROM jobs WHERE job_id = ?
            """, (job_id,))
            row = await cursor.fetchone()
            
            if not row:
                return None
            
            # Reconstruct Job object
            job = Job(
                id=row[0],
                status=JobStatus(row[4]),
                query=row[1],
                engine=row[2],
                backend=row[3],
                started_at=row[5],
                completed_at=row[6],
                created_at=row[9],
                stats=JobStats(
                    query=row[1],
                    backend=row[3],
                    total_emails=row[7] or 0,
                    errors=row[8] or 0,
                ),
            )
            return job
    except Exception as e:
        print(f"[DB] Error loading job {job_id}: {e}")
        return None


async def _list_jobs_from_db() -> list[dict]:
    """List all jobs from database."""
    try:
        async with db._get_connection() as conn:
            cursor = await conn.execute("""
                SELECT job_id, query, engine, backend, status,
                       started_at, completed_at, total_emails, errors, created_at
                FROM jobs ORDER BY created_at DESC
            """)
            rows = await cursor.fetchall()
            
            jobs = []
            for row in rows:
                jobs.append({
                    "id": row[0],
                    "query": row[1],
                    "engine": row[2],
                    "backend": row[3],
                    "status": row[4],
                    "started_at": row[5],
                    "completed_at": row[6],
                    "created_at": row[9],
                    "stats": {
                        "query": row[1],
                        "backend": row[3],
                        "total_emails": row[7] or 0,
                        "errors": row[8] or 0,
                        "elapsed_seconds": 0,
                        "pages_crawled": 0,
                        "new_emails": 0,
                        "last_email": "",
                        "queue_size": 0,
                        "rate_per_min": 0.0,
                    }
                })
            return jobs
    except Exception as e:
        print(f"[DB] Error listing jobs: {e}")
        return []


# ============================================================================
# Event queue helpers
# ============================================================================

async def _get_or_create_event_queue(job_id: str) -> asyncio.Queue:
    """Get or create SSE event queue for a job."""
    async with queue_lock:
        if job_id not in job_event_queues:
            job_event_queues[job_id] = asyncio.Queue()
        return job_event_queues[job_id]


async def _broadcast_stats(job: Job):
    """Broadcast job stats to SSE listeners."""
    queue = await _get_or_create_event_queue(job.id)
    
    event_data = {
        "status": job.status.value,
        "stats": asdict(job.stats),
        "elapsed_seconds": job.stats.elapsed_seconds,
        "pages_crawled": job.stats.pages_crawled,
        "new_emails": job.stats.new_emails,
        "total_emails": job.stats.total_emails,
        "last_email": job.stats.last_email,
        "queue_size": job.stats.queue_size,
        "errors": job.stats.errors,
        "rate_per_min": job.stats.rate_per_min,
    }
    
    # Non-blocking put (don't wait if queue is full)
    try:
        queue.put_nowait(event_data)
    except asyncio.QueueFull:
        pass  # Drop event if queue is full


async def _close_event_queue(job_id: str):
    """Close and cleanup event queue for a job."""
    async with queue_lock:
        if job_id in job_event_queues:
            # Send final event
            queue = job_event_queues[job_id]
            try:
                queue.put_nowait({"_done": True})
            except:
                pass
            # Remove from dict after a delay to allow final event delivery
            await asyncio.sleep(2)
            if job_id in job_event_queues:
                del job_event_queues[job_id]


# ============================================================================
# Job Management
# ============================================================================

async def _get_job(job_id: str) -> Job:
    """Get job from cache or database."""
    # Check running jobs cache first
    async with job_lock:
        if job_id in running_jobs:
            return running_jobs[job_id]
    
    # Load from database
    job = await _load_job_from_db(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job


async def _stats_broadcaster(job: Job):
    """Background task that broadcasts stats every 2 seconds."""
    try:
        while job.status == JobStatus.RUNNING:
            await _broadcast_stats(job)
            await _save_job_to_db(job)  # Persist stats to DB
            await asyncio.sleep(2)
        
        # Final broadcast when job completes
        await _broadcast_stats(job)
        await _save_job_to_db(job)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[BROADCAST] Error for job {job.id}: {e}")


async def _run_scraper_job(job: Job):
    """Execute a scraper job using main.py's run() function."""
    broadcaster_task = None
    
    try:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow().isoformat()
        await _save_job_to_db(job)
        print(f"[JOB] Starting job {job.id}: {job.query}")

        # Start stats broadcaster
        broadcaster_task = asyncio.create_task(_stats_broadcaster(job))

        # Patch LiveDisplay to update job stats
        from utils import display as display_module
        original_display_class = display_module.LiveDisplay
        
        update_counter = [0]
        
        class InterceptedDisplay(original_display_class):
            """LiveDisplay that updates job stats."""
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._job = job
                print(f"[JOB] ✓ InterceptedDisplay created for job {job.id}")
                
            def update_stats(self, **kwargs):
                super().update_stats(**kwargs)
                update_counter[0] += 1
                
                # Update job stats
                stats = {
                    "elapsed_seconds": int((datetime.now() - self._start_time).total_seconds()),
                    "pages_crawled": self._pages,
                    "new_emails": self._new_emails,
                    "total_emails": self._total_emails,
                    "queue_size": self._queue_size,
                    "errors": self._errors,
                    "last_email": self._last_email,
                    "rate_per_min": self._parse_rate(),
                }
                
                if update_counter[0] % 5 == 1:
                    print(f"[JOB] Update #{update_counter[0]} for {self._job.id}: "
                          f"pages={stats['pages_crawled']}, emails={stats['new_emails']}")
                
                self._job.stats = JobStats(
                    query=self._job.query,
                    backend=self._job.backend,
                    **stats
                )
                
            def _parse_rate(self):
                rate_str = self._rate()
                if rate_str == "—":
                    return 0.0
                try:
                    return float(rate_str.replace("/min", "").strip())
                except:
                    return 0.0
                    
            def log(self, message: str):
                super().log(message)
                timestamp = datetime.now().strftime("%H:%M:%S")
                self._job.logs.append(f"{timestamp} | {message}")
                if len(self._job.logs) > 50:
                    self._job.logs = self._job.logs[-50:]
                
            def log_error(self, message: str):
                super().log_error(message)
                timestamp = datetime.now().strftime("%H:%M:%S")
                self._job.logs.append(f"{timestamp} | ERROR: {message}")
                if len(self._job.logs) > 50:
                    self._job.logs = self._job.logs[-50:]
        
        display_module.LiveDisplay = InterceptedDisplay
        print(f"[JOB] ✓ Patched LiveDisplay class")

        import main as main_module
        main_module.LiveDisplay = InterceptedDisplay
        print(f"[JOB] ✓ Patched main.LiveDisplay reference")

        try:
            print(f"[JOB] → Calling main.run() for job {job.id}")
            await main_module.run(
                base_query=job.query,
                engine=job.engine,
                expand_locations=job.expand_locations,
                locations=job.locations if job.locations else None,
                fresh=False,
                no_variants=False,
                backend=job.backend,
                output_file=job.output_file,
                check_mx=job.check_mx,
            )

            print(f"[JOB] ✓ Scraper finished for job {job.id}")
            print(f"[JOB] → Final stats: pages={job.stats.pages_crawled}, emails={job.stats.new_emails}")
            
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow().isoformat()
            print(f"[JOB] ✓ Job {job.id} completed successfully")
            
        finally:
            display_module.LiveDisplay = original_display_class
            main_module.LiveDisplay = original_display_class
            print(f"[JOB] ✓ Restored original LiveDisplay class")

    except asyncio.CancelledError:
        print(f"[JOB] ✗ Job {job.id} was cancelled")
        job.status = JobStatus.STOPPED
        job.completed_at = datetime.utcnow().isoformat()
    except Exception as e:
        print(f"[JOB] ✗ Job {job.id} failed with error: {e}")
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.completed_at = datetime.utcnow().isoformat()
        import traceback
        traceback.print_exc()
    finally:
        # Stop broadcaster
        if broadcaster_task:
            broadcaster_task.cancel()
            try:
                await broadcaster_task
            except asyncio.CancelledError:
                pass
        
        # Final DB save
        await _save_job_to_db(job)
        
        # Remove from running jobs cache
        async with job_lock:
            if job.id in running_jobs:
                del running_jobs[job.id]
        
        # Close event queue
        await _close_event_queue(job.id)


# ============================================================================
# Startup/Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database on server startup."""
    global db
    try:
        # Import and initialize database
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        
        # Create a minimal database wrapper that works with aiosqlite
        class SimpleDB:
            def __init__(self, db_path):
                self.db_path = db_path
            
            async def _get_connection(self):
                return aiosqlite.connect(self.db_path)
            
            async def init(self):
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS jobs (
                            job_id TEXT PRIMARY KEY,
                            query TEXT NOT NULL,
                            engine TEXT,
                            backend TEXT,
                            status TEXT,
                            started_at TEXT,
                            completed_at TEXT,
                            total_emails INTEGER DEFAULT 0,
                            total_domains INTEGER DEFAULT 0,
                            errors INTEGER DEFAULT 0,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    await conn.commit()
        
        db = SimpleDB("scraped_data.db")
        await db.init()
        print("[DB] ✓ Database initialized")
    except Exception as e:
        print(f"[DB] ✗ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown."""
    # Cancel all running jobs
    async with job_lock:
        for job in running_jobs.values():
            if job.task:
                job.task.cancel()
    
    # Close all event queues
    async with queue_lock:
        for queue in job_event_queues.values():
            try:
                queue.put_nowait({"_done": True})
            except:
                pass
    
    print("[SERVER] ✓ Shutdown complete")


# ============================================================================
# Endpoints
# ============================================================================

@app.post("/jobs", response_model=JobResponse)
async def create_job(req: JobRequest) -> JobResponse:
    """Start a new scrape job."""
    job_id = str(uuid.uuid4())[:8]
    job = Job(
        id=job_id,
        status=JobStatus.PENDING,
        query=req.query,
        engine=req.engine,
        backend=req.backend,
        expand_locations=req.expand_locations,
        locations=req.locations,
        check_mx=req.check_mx,
        output_file=req.output_file or OUTPUT_FILE,
        stats=JobStats(query=req.query, backend=req.backend),
    )

    # Save to database
    await _save_job_to_db(job)

    # Add to running jobs cache
    async with job_lock:
        running_jobs[job_id] = job

    # Create event queue
    await _get_or_create_event_queue(job_id)

    # Start job in background
    job.task = asyncio.create_task(_run_scraper_job(job))

    return JobResponse(
        id=job.id,
        status=job.status.value,
        query=job.query,
        engine=job.engine,
        backend=job.backend,
        created_at=job.created_at,
        stats=asdict(job.stats),
    )


@app.get("/jobs/{job_id}/status", response_model=JobResponse)
async def get_job_status(job_id: str) -> JobResponse:
    """Get current job state and stats (fallback for non-SSE clients)."""
    job = await _get_job(job_id)

    return JobResponse(
        id=job.id,
        status=job.status.value,
        query=job.query,
        engine=job.engine,
        backend=job.backend,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
        stats=asdict(job.stats),
    )


@app.get("/jobs/{job_id}/stream")
async def stream_job_stats(job_id: str):
    """
    Server-Sent Events stream for real-time job stats.
    
    Usage:
        const eventSource = new EventSource('/jobs/{job_id}/stream');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data._done) {
                eventSource.close();
            } else {
                // Update UI with stats
            }
        };
    """
    # Verify job exists
    job = await _get_job(job_id)
    
    # Get event queue
    queue = await _get_or_create_event_queue(job_id)
    
    async def event_generator():
        """Generate SSE events."""
        try:
            last_heartbeat = datetime.now()
            
            while True:
                # Send heartbeat every 5 seconds to keep connection alive
                if (datetime.now() - last_heartbeat).total_seconds() > 5:
                    yield f"data: ping\n\n"
                    last_heartbeat = datetime.now()
                
                try:
                    # Wait for event with timeout
                    event_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    
                    # Check if stream should close
                    if event_data.get("_done"):
                        yield f"data: {json.dumps({'_done': True})}\n\n"
                        break
                    
                    # Send event
                    yield f"data: {json.dumps(event_data)}\n\n"
                    
                except asyncio.TimeoutError:
                    # No event, continue to next iteration (will send heartbeat if needed)
                    continue
                    
        except asyncio.CancelledError:
            print(f"[SSE] Client disconnected from job {job_id}")
        except Exception as e:
            print(f"[SSE] Error streaming job {job_id}: {e}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@app.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    """Get recent logs for a job."""
    job = await _get_job(job_id)
    return {"logs": job.logs}


@app.get("/jobs/{job_id}/download")
async def download_job_results(job_id: str):
    """Download CSV results for a job."""
    job = await _get_job(job_id)

    if not os.path.exists(job.output_file):
        raise HTTPException(status_code=404, detail=f"Results file not found at {job.output_file}")

    if os.path.getsize(job.output_file) == 0:
        raise HTTPException(status_code=404, detail="Results file is empty")

    return FileResponse(
        path=job.output_file,
        filename=f"emails_{job.id}.csv",
        media_type="text/csv",
    )


@app.delete("/jobs/{job_id}")
async def stop_job(job_id: str):
    """Stop a running job."""
    job = await _get_job(job_id)

    if job.status == JobStatus.RUNNING:
        async with job_lock:
            if job.id in running_jobs and running_jobs[job.id].task:
                running_jobs[job.id].task.cancel()
        
        job.status = JobStatus.STOPPED
        job.completed_at = datetime.utcnow().isoformat()
        await _save_job_to_db(job)

    return {"status": "stopped"}


@app.get("/jobs")
async def list_jobs():
    """List all jobs from database."""
    jobs_list = await _list_jobs_from_db()
    
    # Merge with running jobs cache for live stats
    async with job_lock:
        for job_dict in jobs_list:
            if job_dict["id"] in running_jobs:
                running_job = running_jobs[job_dict["id"]]
                job_dict["stats"] = asdict(running_job.stats)
                job_dict["status"] = running_job.status.value
    
    return {"jobs": jobs_list}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "database": "connected" if db else "not initialized"}


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
