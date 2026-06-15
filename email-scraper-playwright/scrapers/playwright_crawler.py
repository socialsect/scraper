"""Parallel email extraction using Playwright browser contexts."""

import asyncio
import os
import random
from urllib.parse import urljoin, urlparse, urlunparse

from config import (
    CRAWL_PAGE_DELAY,
    MAX_CRAWL_DEPTH,
    MAX_PAGES_TO_CRAWL,
    TARGET_EMAIL_COUNT,
)
from engine.playwright_pool import PlaywrightPool, dismiss_consent
from utils.csv_output import (
    append_email_row,
    count_data_rows,
    ensure_csv_header,
    load_existing_emails,
    write_query_marker,
)
from utils.email_regex import extract_emails_from_html

DOMAIN_BLOCKLIST = [
    "gov.uk",
    "nhs.net",
    "nhs.scot",
    "ac.uk",
    "gov.scot",
    "microsoft.com",
    "nasa.gov",
    "facebook.com",
    "linkedin.com",
    "google.com",
    "visa.com",
    "amazon.com",
    "wikipedia.org",
    "sentry.io",
    "wixpress.com",
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "apps.trac.jobs",
    "trac.jobs",
]

BLOCKED_URLS = (
    "https://apps.trac.jobs/about",
    "apps.trac.jobs/about",
)

BLOCKED_TLDS = (".gov", ".in", ".pk", ".cn", ".za", ".ng", ".tn")

LINK_KEYWORDS = ("contact", "about", "info", "team", "staff")


def normalize_url(url: str) -> str:
    parsed = urlparse(url.lower().strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def should_crawl(url: str) -> bool:
    url_lower = url.lower().strip()

    if any(blocked in url_lower for blocked in BLOCKED_URLS):
        return False

    if any(blocked in url_lower for blocked in DOMAIN_BLOCKLIST):
        return False

    if "@" in url_lower:
        return True

    try:
        host = urlparse(url_lower).netloc
    except ValueError:
        return True

    if host:
        return not any(blocked in host for blocked in DOMAIN_BLOCKLIST)

    return True


def is_valid_email(email: str) -> bool:
    from utils.email_regex import is_valid_email as regex_valid

    email = email.lower().strip()
    if not regex_valid(email):
        return False
    try:
        domain = email.split("@", 1)[1]
    except IndexError:
        return False
    if domain.endswith(BLOCKED_TLDS):
        return False
    return should_crawl(email)


class PlaywrightEmailCrawler:
    def __init__(
        self,
        pool: PlaywrightPool,
        output_file: str,
        query_label: str = "default queries",
    ):
        self.pool = pool
        self.output_file = output_file
        self.query_label = query_label
        self.saved_emails: set[str] = set()
        self.found_emails: set[str] = set()
        self.visited: set[str] = set()
        self.pages_crawled = 0
        self._session_saved = 0
        self._csv_total_at_start = 0
        self._queue: asyncio.Queue[tuple[str, int] | None] = asyncio.Queue()
        self._stop = asyncio.Event()
        self._inflight = 0
        self._inflight_lock = asyncio.Lock()

    async def setup_output(self) -> None:
        ensure_csv_header(self.output_file)
        self.saved_emails = load_existing_emails(self.output_file)
        self._csv_total_at_start = count_data_rows(self.output_file)
        write_query_marker(self.output_file, self.query_label)

        print(f"Output CSV: {os.path.abspath(self.output_file)}")
        print(f"Emails already in CSV: {self._csv_total_at_start}")
        print("Press Ctrl+C once to stop gracefully.\n")

    def request_stop(self) -> None:
        self._stop.set()

    async def append_email(self, email: str, source: str) -> None:
        email = email.lower().strip()
        if not is_valid_email(email):
            return
        if append_email_row(self.output_file, email, source, self.saved_emails):
            self._session_saved += 1
            total = self._csv_total_at_start + self._session_saved
            print(
                f"[{self._session_saved} new | {total} total in CSV] "
                f"Saved: {email} (from {source[:80]})"
            )

    async def fetch_page(self, page, url: str) -> str | None:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await dismiss_consent(page)
            return await page.content()
        except Exception as e:
            print(f"  Failed {url[:60]}: {e}")
            return None

    async def _enqueue(self, url: str, depth: int) -> None:
        if self._stop.is_set():
            return
        key = normalize_url(url)
        if key in self.visited:
            return
        if not should_crawl(url):
            return
        await self._queue.put((url, depth))

    async def process_url(self, url: str, depth: int) -> None:
        if self._stop.is_set():
            return

        key = normalize_url(url)
        if key in self.visited:
            return
        if not should_crawl(url):
            return

        self.visited.add(key)
        self.pages_crawled += 1

        if self.pages_crawled % 10 == 0:
            total = self._csv_total_at_start + self._session_saved
            print(
                f"Progress: {self.pages_crawled} pages | "
                f"{self._session_saved} new this run | {total} total in CSV | "
                f"queue ~{self._queue.qsize()}"
            )

        async with self.pool.acquire_page() as page:
            html = await self.fetch_page(page, url)
            if not html:
                return

            emails = extract_emails_from_html(html)

            mailto_links = await page.eval_on_selector_all(
                'a[href^="mailto:"]',
                "els => els.map(e => e.getAttribute('href') || '')",
            )
            for link in mailto_links:
                email = link.replace("mailto:", "").split("?")[0].strip().lower()
                if "@" in email:
                    emails.add(email)

            for email in emails:
                if email not in self.found_emails:
                    self.found_emails.add(email)
                    await self.append_email(email, url)

            if (
                not self._stop.is_set()
                and depth < MAX_CRAWL_DEPTH
                and len(self.found_emails) < TARGET_EMAIL_COUNT
                and self.pages_crawled < MAX_PAGES_TO_CRAWL
            ):
                for keyword in LINK_KEYWORDS:
                    links = await page.eval_on_selector_all(
                        f'a[href*="{keyword}"]',
                        "els => els.map(e => e.href).filter(h => h && h.startsWith('http'))",
                    )
                    for link in links[:3]:
                        await self._enqueue(link, depth + 1)

            await asyncio.sleep(random.uniform(*CRAWL_PAGE_DELAY))

    async def worker(self, worker_id: int) -> None:
        while True:
            if self._stop.is_set() and self._queue.empty():
                return

            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            if item is None:
                self._queue.task_done()
                return

            url, depth = item
            async with self._inflight_lock:
                self._inflight += 1
            try:
                await self.process_url(url, depth)
            except Exception as e:
                print(f"Worker {worker_id} error on {url[:50]}: {e}")
            finally:
                async with self._inflight_lock:
                    self._inflight -= 1
                self._queue.task_done()

    async def crawl(self, start_urls: list[str]) -> None:
        await self.setup_output()

        filtered = [u for u in start_urls if should_crawl(u)]
        print(f"Crawling {len(filtered)} URLs (filtered from {len(start_urls)})")

        for url in filtered:
            await self._enqueue(url, 0)

        num_workers = self.pool.max_workers
        workers = [asyncio.create_task(self.worker(i)) for i in range(num_workers)]

        while not self._stop.is_set():
            await asyncio.sleep(0.5)
            async with self._inflight_lock:
                busy = self._inflight
            if self._queue.empty() and busy == 0:
                break

        self._stop.set()
        await asyncio.gather(*workers, return_exceptions=True)

        total = self._csv_total_at_start + self._session_saved
        print(
            f"Crawl finished: {self.pages_crawled} pages | "
            f"{self._session_saved} new this run | {total} total in CSV"
        )
