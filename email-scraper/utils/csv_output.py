"""Thread-safe / multi-process CSV output with query session markers."""

from __future__ import annotations

import csv
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime

QUERY_MARKER_PREFIX = "#QUERY"

# All columns written to the emails CSV.
# New columns are appended after email/source so old CSVs stay readable.
CSV_COLUMNS = [
    "email",
    "source",
    "phone",
    "linkedin",
    "twitter",
    "instagram",
    "facebook",
    "youtube",
    "mx_valid",
    "confidence",
]

# Columns used for deduplication / existence checks
_IDENTITY_COL = "email"


@contextmanager
def _file_lock(path: str):
    """Exclusive lock on a sidecar lock file (works across processes on Windows + Unix)."""
    lock_path = f"{path}.lock"
    os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)

    if sys.platform == "win32":
        import msvcrt

        lock_file = open(lock_path, "a+b")
        try:
            lock_file.seek(0)
            lock_file.write(b"\0")
            lock_file.flush()
            lock_file.seek(0)
            while True:
                try:
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
            yield
        finally:
            try:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            lock_file.close()
    else:
        import fcntl

        lock_file = open(lock_path, "w")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()


def is_query_marker_row(row: dict | list | tuple) -> bool:
    if isinstance(row, dict):
        first = (row.get("email") or "").strip()
    else:
        first = (row[0] if row else "").strip()
    return first.upper().startswith(QUERY_MARKER_PREFIX)


def count_data_rows(path: str) -> int:
    if not os.path.exists(path):
        return 0
    count = 0
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            if row[0].strip().lower() == "email":
                continue
            if is_query_marker_row(row):
                continue
            if row[0].strip():
                count += 1
    return count


def load_existing_emails(path: str) -> set[str]:
    emails: set[str] = set()
    if not os.path.exists(path):
        return emails
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 1:
                continue
            email = row[0].strip().lower()
            if not email or email == "email" or is_query_marker_row(row):
                continue
            emails.add(email)
    return emails


def ensure_csv_header(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    with _file_lock(path):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CSV_COLUMNS)


def write_query_marker(path: str, query_label: str) -> None:
    """Append a session marker so you can see which search produced the rows below."""
    ensure_csv_header(path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    marker = [QUERY_MARKER_PREFIX, query_label.strip(), timestamp]
    with _file_lock(path):
        with open(path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(marker)


def append_email_row(
    path: str,
    email: str,
    source: str,
    known_emails: set[str],
    *,
    phone: str = "",
    linkedin: str = "",
    twitter: str = "",
    instagram: str = "",
    facebook: str = "",
    youtube: str = "",
    mx_valid: str = "",
    confidence: str = "",
) -> bool:
    """
    Append one email row under a file lock.
    Returns True if a new row was written.

    Extra enrichment fields (phone, socials, mx_valid, confidence) are optional —
    pass empty string to leave the column blank.
    """
    email = email.lower().strip()
    if not email or email in known_emails:
        return False

    ensure_csv_header(path)
    with _file_lock(path):
        # Re-check against file in case another process wrote it first.
        on_disk = load_existing_emails(path)
        if email in on_disk:
            known_emails.add(email)
            return False
        with open(path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                email, source,
                phone, linkedin, twitter, instagram, facebook, youtube,
                mx_valid, confidence,
            ])

    known_emails.add(email)
    return True
