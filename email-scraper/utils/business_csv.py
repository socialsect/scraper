"""Thread-safe CSV output for Google Maps business listings."""

from __future__ import annotations

import csv
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime

QUERY_MARKER_PREFIX = "#QUERY"
BUSINESS_CSV_COLUMNS = ["number", "business_name", "website"]


@contextmanager
def _file_lock(path: str):
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
        first = (row.get("number") or row.get("business_name") or "").strip()
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
            if row[0].strip().lower() == "number":
                continue
            if is_query_marker_row(row):
                continue
            if any(cell.strip() for cell in row):
                count += 1
    return count


def load_existing_keys(path: str) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    if not os.path.exists(path):
        return keys
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            number = (row.get("number") or "").strip()
            name = (row.get("business_name") or "").strip()
            if not name or is_query_marker_row({"number": number, "business_name": name}):
                continue
            keys.add((name.lower(), number))
    return keys


def ensure_csv_header(path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return
    with _file_lock(path):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(BUSINESS_CSV_COLUMNS)


def write_query_marker(path: str, query_label: str) -> None:
    ensure_csv_header(path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    marker = [QUERY_MARKER_PREFIX, query_label.strip(), timestamp]
    with _file_lock(path):
        with open(path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(marker)
    print(f"\n--- CSV session: {query_label} ({timestamp}) ---")


def append_business_row(
    path: str,
    number: str,
    business_name: str,
    known_keys: set[tuple[str, str]],
    website: str = "",
) -> bool:
    business_name = business_name.strip()
    number = number.strip()
    website = website.strip()
    if not business_name:
        return False

    key = (business_name.lower(), number)
    if key in known_keys:
        return False

    ensure_csv_header(path)
    with _file_lock(path):
        on_disk = load_existing_keys(path)
        if key in on_disk:
            known_keys.add(key)
            return False
        with open(path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([number, business_name, website])

    known_keys.add(key)
    return True


def load_websites(path: str) -> list[str]:
    """Return all non-empty website URLs from a businesses CSV."""
    websites: list[str] = []
    if not os.path.exists(path):
        return websites
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue
            website = (row.get("website") or "").strip()
            if website and website.startswith("http") and not is_query_marker_row(row):
                websites.append(website)
    return websites
