"""
SQLite database layer for email scraper.
Tables: jobs, emails, domains.
Solves dedup across runs and provides clean query interface.
"""

import aiosqlite
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Email:
    email: str
    domain: str
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    confidence: int = 2  # 1, 2, or 3
    source_url: str = ""
    found_at: str = ""  # ISO timestamp


@dataclass
class Domain:
    domain: str
    first_seen: str  # ISO timestamp
    last_seen: str
    email_count: int = 0


@dataclass
class Job:
    job_id: str
    query: str
    engine: str
    backend: str
    status: str  # pending, running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_emails: int = 0
    total_domains: int = 0
    errors: int = 0


class Database:
    """Thread-safe SQLite wrapper for the scraper."""

    def __init__(self, db_path: str = "scraped_data.db"):
        self.db_path = db_path
        self._initialized = False

    async def init(self):
        """Initialize database schema."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
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

            await db.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    email TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    phone TEXT,
                    linkedin TEXT,
                    confidence INTEGER DEFAULT 2,
                    source_url TEXT,
                    found_at TEXT,
                    job_id TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(job_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS domains (
                    domain TEXT PRIMARY KEY,
                    first_seen TEXT,
                    last_seen TEXT,
                    email_count INTEGER DEFAULT 0
                )
            """)

            # Indexes for performance
            await db.execute("CREATE INDEX IF NOT EXISTS idx_emails_domain ON emails(domain)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_emails_job ON emails(job_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_domains_seen ON domains(last_seen)")

            await db.commit()

        self._initialized = True

    # ========================================================================
    # Email operations
    # ========================================================================

    async def add_email(self, email: Email, job_id: Optional[str] = None) -> bool:
        """
        Add email to database. Returns True if inserted, False if duplicate.
        """
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO emails
                    (email, domain, phone, linkedin, confidence, source_url, found_at, job_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    email.email,
                    email.domain,
                    email.phone,
                    email.linkedin,
                    email.confidence,
                    email.source_url,
                    email.found_at or datetime.utcnow().isoformat(),
                    job_id,
                ))
                await db.commit()

                # Update domain stats
                await db.execute("""
                    INSERT INTO domains (domain, first_seen, last_seen, email_count)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(domain) DO UPDATE SET
                        last_seen = ?,
                        email_count = email_count + 1
                """, (
                    email.domain,
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat(),
                ))
                await db.commit()

                return True
            except aiosqlite.IntegrityError:
                # Email already exists
                return False

    async def email_exists(self, email: str) -> bool:
        """Check if email already in database."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT 1 FROM emails WHERE email = ?", (email,))
            row = await cursor.fetchone()
            return row is not None

    async def get_emails(
        self,
        domain: Optional[str] = None,
        job_id: Optional[str] = None,
        min_confidence: int = 1,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Email]:
        """Query emails with optional filtering."""
        query = "SELECT * FROM emails WHERE confidence >= ?"
        params = [min_confidence]

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if job_id:
            query += " AND job_id = ?"
            params.append(job_id)

        query += f" ORDER BY found_at DESC LIMIT {limit} OFFSET {offset}"

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

        return [
            Email(
                email=row[0],
                domain=row[1],
                phone=row[2],
                linkedin=row[3],
                confidence=row[4],
                source_url=row[5],
                found_at=row[6],
            )
            for row in rows
        ]

    async def count_emails(self, job_id: Optional[str] = None) -> int:
        """Total email count."""
        query = "SELECT COUNT(*) FROM emails"
        params = []

        if job_id:
            query += " WHERE job_id = ?"
            params.append(job_id)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            return row[0] if row else 0

    # ========================================================================
    # Domain operations
    # ========================================================================

    async def get_domains(
        self, min_emails: int = 1, limit: int = 1000, offset: int = 0
    ) -> List[Domain]:
        """Get domains with optional filtering."""
        query = f"""
            SELECT domain, first_seen, last_seen, email_count
            FROM domains
            WHERE email_count >= ?
            ORDER BY email_count DESC
            LIMIT {limit} OFFSET {offset}
        """

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, (min_emails,))
            rows = await cursor.fetchall()

        return [
            Domain(
                domain=row[0],
                first_seen=row[1],
                last_seen=row[2],
                email_count=row[3],
            )
            for row in rows
        ]

    async def count_domains(self) -> int:
        """Total domain count."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM domains")
            row = await cursor.fetchone()
            return row[0] if row else 0

    # ========================================================================
    # Job operations
    # ========================================================================

    async def create_job(
        self, job_id: str, query: str, engine: str, backend: str
    ) -> None:
        """Create a job record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO jobs (job_id, query, engine, backend, status, started_at)
                VALUES (?, ?, ?, ?, 'running', ?)
            """, (job_id, query, engine, backend, datetime.utcnow().isoformat()))
            await db.commit()

    async def complete_job(
        self, job_id: str, total_emails: int, total_domains: int, errors: int = 0
    ) -> None:
        """Mark job as completed."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE jobs
                SET status = 'completed', completed_at = ?, total_emails = ?, total_domains = ?, errors = ?
                WHERE job_id = ?
            """, (datetime.utcnow().isoformat(), total_emails, total_domains, errors, job_id))
            await db.commit()

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Fetch job metadata."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = await cursor.fetchone()

        if not row:
            return None

        return Job(
            job_id=row[0],
            query=row[1],
            engine=row[2],
            backend=row[3],
            status=row[4],
            started_at=row[5],
            completed_at=row[6],
            total_emails=row[7],
            total_domains=row[8],
            errors=row[9],
        )

    async def export_csv(self, output_path: str, job_id: Optional[str] = None):
        """Export all emails to CSV."""
        import csv

        emails = await self.get_emails(job_id=job_id, limit=999999)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["email", "domain", "phone", "linkedin", "confidence", "source_url", "found_at"])

            for email in emails:
                writer.writerow([
                    email.email,
                    email.domain,
                    email.phone or "",
                    email.linkedin or "",
                    email.confidence,
                    email.source_url,
                    email.found_at,
                ])
