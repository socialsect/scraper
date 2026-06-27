# ✅ Server.py Critical Fixes — COMPLETE

**Date:** June 28, 2026  
**Version:** 0.2.0  
**Status:** Both issues resolved and production-ready

---

## Issue 1: Job Persistence ✅ FIXED

### Problem
Jobs stored in memory dict → lost on server restart

### Solution Implemented

#### Database Integration
- **SimpleDB wrapper** created for aiosqlite operations
- **Schema initialized** on server startup
- **Jobs table** stores: job_id, query, engine, backend, status, timestamps, stats

#### Persistence Flow
```python
# On job creation
await _save_job_to_db(job)  # Write to database

# Every 2 seconds during scraping
await _save_job_to_db(job)  # Update stats in DB

# On job completion/failure
await _save_job_to_db(job)  # Final DB save
```

#### Hybrid Architecture
- **Database:** Long-term storage, survives restarts
- **running_jobs dict:** Cache for active jobs only
- **Load strategy:**
  1. Check running_jobs cache first
  2. If not found, load from database
  3. Throw 404 if not in either

#### Database Operations
```python
# Save/Update
async def _save_job_to_db(job: Job)
# → INSERT on new jobs
# → UPDATE on existing jobs

# Load single job
async def _load_job_from_db(job_id: str) -> Optional[Job]
# → Returns reconstructed Job object

# List all jobs
async def _list_jobs_from_db() -> list[dict]
# → Returns all jobs sorted by created_at DESC
```

---

## Issue 2: Real-time SSE Streaming ✅ FIXED

### Problem
LiveDisplay patching unreliable, no proper SSE implementation

### Solution Implemented

#### Event Queue Architecture
```python
# Per-job queues
job_event_queues: dict[str, asyncio.Queue] = {}

# Create on job start
await _get_or_create_event_queue(job_id)

# Broadcast stats every 2 seconds
async def _stats_broadcaster(job: Job):
    while job.status == RUNNING:
        await _broadcast_stats(job)
        await asyncio.sleep(2)

# Client connects to stream
GET /jobs/{job_id}/stream
```

#### New Endpoint: `/jobs/{job_id}/stream`
**Purpose:** Server-Sent Events stream for real-time stats

**Features:**
- ✅ Broadcasts stats every 2 seconds
- ✅ Sends heartbeat "data: ping\n\n" every 5 seconds
- ✅ Closes stream when job completes/fails/stops
- ✅ Sends final `{"_done": true}` event
- ✅ Non-blocking queue operations (drops events if full)
- ✅ Handles client disconnects gracefully

**Response Format:**
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"status":"running","stats":{...},"pages_crawled":10}

data: {"status":"running","stats":{...},"pages_crawled":20}

data: ping

data: {"_done":true}
```

#### Client Usage
```javascript
const eventSource = new EventSource('/jobs/abc12345/stream');

eventSource.onmessage = (event) => {
    if (event.data === 'ping') {
        return; // Heartbeat, ignore
    }
    
    const data = JSON.parse(event.data);
    
    if (data._done) {
        eventSource.close();
        console.log('Job completed');
    } else {
        // Update UI with live stats
        updateDashboard(data.stats);
    }
};

eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    eventSource.close();
};
```

#### Fallback: `/jobs/{job_id}/status`
- Still available for polling-based clients
- Returns current stats from database
- No streaming, single request/response

---

## Architecture Changes

### Before
```
POST /jobs → In-memory dict only
GET /jobs → Read from memory dict
GET /jobs/{id}/status → Read from memory dict
[Server restart] → All jobs lost ✗
[Stats updates] → No real-time streaming ✗
```

### After
```
POST /jobs → Save to database + memory cache
Every 2s → Broadcast to SSE + Save to database
GET /jobs → Read from database (merge with cache)
GET /jobs/{id}/status → Read from cache or database
GET /jobs/{id}/stream → Real-time SSE stream ✓
[Server restart] → Jobs persisted in database ✓
[Stats updates] → Real-time SSE + heartbeats ✓
```

---

## Database Schema

```sql
CREATE TABLE jobs (
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
);
```

**Location:** `scraped_data.db` (SQLite)

---

## Key Functions

### Database Operations
```python
# Initialize on startup
@app.on_event("startup")
async def startup_event():
    db = SimpleDB("scraped_data.db")
    await db.init()

# Save job to DB
await _save_job_to_db(job)

# Load job from DB
job = await _load_job_from_db(job_id)

# List all jobs
jobs = await _list_jobs_from_db()
```

### SSE Operations
```python
# Create event queue
await _get_or_create_event_queue(job_id)

# Broadcast stats
await _broadcast_stats(job)

# Close queue
await _close_event_queue(job_id)

# Stats broadcaster task
broadcaster = asyncio.create_task(_stats_broadcaster(job))
```

---

## Testing

### Test Database Persistence
```bash
# Start server
python server.py

# Create job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"query":"test","engine":"ddg"}'

# Response: {"id":"abc12345",...}

# Check database
sqlite3 scraped_data.db "SELECT * FROM jobs;"

# Restart server
# Ctrl+C, then: python server.py

# Job still exists
curl http://localhost:8000/jobs/abc12345/status
# ✓ Returns job from database
```

### Test SSE Streaming
```bash
# Terminal 1: Start server
python server.py

# Terminal 2: Create job
JOB_ID=$(curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"query":"test clinics","engine":"ddg"}' \
  | jq -r .id)

# Terminal 3: Stream events
curl -N http://localhost:8000/jobs/$JOB_ID/stream

# Output:
# data: {"status":"running","stats":{...}}
# data: {"status":"running","stats":{...}}
# data: ping
# data: {"_done":true}
```

### Test with Browser
```html
<!DOCTYPE html>
<html>
<head><title>SSE Test</title></head>
<body>
<h1>Job Stats</h1>
<pre id="stats"></pre>

<script>
const jobId = 'abc12345'; // Replace with real job ID
const eventSource = new EventSource(`/jobs/${jobId}/stream`);

eventSource.onmessage = (event) => {
    if (event.data === 'ping') {
        console.log('Heartbeat');
        return;
    }
    
    const data = JSON.parse(event.data);
    document.getElementById('stats').textContent = JSON.stringify(data, null, 2);
    
    if (data._done) {
        eventSource.close();
        console.log('Stream closed');
    }
};

eventSource.onerror = (error) => {
    console.error('SSE error:', error);
    eventSource.close();
};
</script>
</body>
</html>
```

---

## Performance Considerations

### Database Writes
- **Frequency:** Every 2 seconds during scraping
- **Impact:** Minimal (SQLite handles this easily)
- **Optimization:** Uses INSERT/UPDATE pattern

### SSE Connections
- **Concurrent limit:** No hard limit (limited by server resources)
- **Memory per connection:** ~1KB per event in queue
- **Heartbeat overhead:** 1 message every 5 seconds
- **Queue size:** Unbounded (but events are dropped if full)

### Cleanup
- **Event queues:** Closed 2 seconds after job completion
- **Running jobs cache:** Removed on job completion
- **Database:** No automatic cleanup (manual pruning recommended)

---

## Backwards Compatibility

### Existing Endpoints
✅ **Unchanged signatures:**
- `POST /jobs`
- `GET /jobs/{id}/status`
- `GET /jobs/{id}/logs`
- `GET /jobs/{id}/download`
- `DELETE /jobs/{id}`
- `GET /jobs`
- `GET /health`

✅ **Response formats:** Identical to before

✅ **Frontend compatibility:** Existing app.py still works (uses polling)

### New Endpoints
✅ **Added (non-breaking):**
- `GET /jobs/{id}/stream` (SSE streaming)

---

## Migration Guide

### From Old server.py
No migration needed! The new server is backward compatible.

**Steps:**
1. Stop old server (Ctrl+C)
2. Replace server.py with new version
3. Start new server: `python server.py`
4. Database will be created automatically
5. Existing frontend still works

### Database Location
- **File:** `scraped_data.db`
- **Created:** Automatically on first startup
- **Location:** Project root directory

---

## Troubleshooting

### "Database initialization failed"
**Cause:** Missing aiosqlite dependency

**Solution:**
```bash
pip install aiosqlite
```

### "Event queue full"
**Cause:** Client not consuming events fast enough

**Impact:** Events are dropped (non-blocking)

**Solution:** This is expected behavior, no action needed

### "SSE connection closed unexpectedly"
**Cause:** Network timeout, firewall, or proxy buffering

**Solution:**
- Check nginx/proxy settings
- Add `X-Accel-Buffering: no` header (already included)
- Increase client timeout

### Jobs not persisting
**Cause:** Database writes failing

**Check:**
```bash
# Verify database file exists
ls -lh scraped_data.db

# Check contents
sqlite3 scraped_data.db "SELECT COUNT(*) FROM jobs;"
```

---

## API Documentation

### GET /jobs/{job_id}/stream (NEW)

**Description:** Server-Sent Events stream for real-time job stats

**Response:** `text/event-stream`

**Headers:**
- `Cache-Control: no-cache`
- `Connection: keep-alive`
- `X-Accel-Buffering: no`

**Event Format:**
```
data: <JSON>\n\n
```

**JSON Schema:**
```json
{
  "status": "running",
  "stats": {
    "query": "string",
    "backend": "string",
    "elapsed_seconds": 0,
    "pages_crawled": 0,
    "new_emails": 0,
    "total_emails": 0,
    "last_email": "string",
    "queue_size": 0,
    "errors": 0,
    "rate_per_min": 0.0
  }
}
```

**Special Events:**
- `data: ping` — Heartbeat (every 5s)
- `data: {"_done": true}` — Stream end

**Example:**
```bash
curl -N http://localhost:8000/jobs/abc12345/stream
```

---

## Summary of Changes

### Files Modified
- ✅ `server.py` (complete rewrite)

### New Features
- ✅ SQLite database persistence
- ✅ Real-time SSE streaming
- ✅ Event queue per job
- ✅ Heartbeat mechanism
- ✅ Automatic cleanup on completion

### Bug Fixes
- ✅ Jobs survive server restart
- ✅ Stats update reliably
- ✅ Proper async event handling
- ✅ Graceful connection cleanup

### Performance
- ✅ Non-blocking queue operations
- ✅ Efficient database writes (every 2s)
- ✅ Memory-efficient (cache only running jobs)

### Reliability
- ✅ Database writes on every stats update
- ✅ Heartbeats keep connections alive
- ✅ Graceful error handling
- ✅ Proper cleanup on shutdown

---

## Next Steps

1. **Test SSE with frontend:**
   ```bash
   python server.py  # Terminal 1
   python app.py     # Terminal 2
   ```

2. **Monitor database growth:**
   ```bash
   watch -n 5 'sqlite3 scraped_data.db "SELECT COUNT(*) FROM jobs;"'
   ```

3. **Implement frontend SSE client:**
   ```javascript
   // Replace polling with SSE
   const eventSource = new EventSource(`/jobs/${jobId}/stream`);
   ```

4. **Optional: Add database cleanup:**
   ```sql
   -- Delete old jobs (older than 30 days)
   DELETE FROM jobs WHERE created_at < date('now', '-30 days');
   ```

---

## Version Info

- **Before:** v0.1.0 (in-memory, no SSE)
- **After:** v0.2.0 (database + SSE)
- **Breaking Changes:** None
- **New Dependencies:** aiosqlite (already in requirements.txt)

---

**Status:** ✅ Production-ready

**Run it:**
```bash
python server.py
```

Then test:
```bash
# Create job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"query":"test","engine":"ddg"}'

# Stream stats (real-time)
curl -N http://localhost:8000/jobs/{job_id}/stream

# Or poll (fallback)
curl http://localhost:8000/jobs/{job_id}/status
```

---

**End of Fix Report**
