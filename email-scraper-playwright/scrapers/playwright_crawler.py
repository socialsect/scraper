"""Parallel email extraction using Playwright browser contexts."""

import asyncio
import csv
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
from utils.email_regex import extract_emails_from_html

DOMAIN_BLOCKLIST = [
    "gov.uk", "nhs.net", "nhs.scot", "ac.uk", "gov.scot",
    "microsoft.com", "nasa.gov", "facebook.com", "linkedin.com",
    "google.com", "visa.com", "amazon.com", "wikipedia.org",
    "sentry.io", "wixpress.com", "youtube.com", "youtu.be",
    "twitter.com", "x.com", "instagram.com", "pinterest.com",
    "cnn.com", "nytimes.com", "theguardian.com", "reddit.com",
    "mayoclinic.org", "webmd.com", "healthline.com", "nih.gov",
    "cdc.gov", "who.int", "nature.com", "springernature.com",
]

BLOCKED_TLDS = (".gov", ".in", ".pk", ".cn", ".za", ".ng", ".tn")


def normalize_url(url: str) -> str:
    parsed = urlparse(url.lower().strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def should_crawl(url: str) -> bool:
    url_lower = url.lower()
    if any(blocked in url_lower for blocked in DOMAIN_BLOCKLIST):
        return False
    try:
        host = urlparse(url_lower).netloc
    except ValueError:
        return False
    return not any(blocked in host for blocked in DOMAIN_BLOCKLIST)


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
    ):
        self.pool = pool
        self.output_file = output_file
        self.saved_emails: set[str] = set()
        self.found_emails: set[str] = set()
        self.visited: set[str] = set()
        self.pages_crawled = 0
        self._write_lock = asyncio.Lock()
        self._queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()
        self._done = asyncio.Event()

    async def setup_output(self) -> None:
        os.makedirs(os.path.dirname(self.output_file) or ".", exist_ok=True)
        if not os.path.exists(self.output_file):
            with open(self.output_file, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["email", "source"])

    async def append_email(self, email: str, source: str) -> None:
        email = email.lower().strip()
        if not is_valid_email(email):
            return
        async with self._write_lock:
            if email in self.saved_emails:
                return
            with open(self.output_file, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([email, source])
            self.saved_emails.add(email)
            print(f"Saved: {email} (from {source})")

    async def fetch_page(self, page, url: str) -> str | None:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await dismiss_consent(page)
            return await page.content()
        except Exception as e:
            print(f"  Failed {url[:60]}: {e}")
            return None

    async def process_url(self, url: str, depth: int) -> None:
        key = normalize_url(url)
        if key in self.visited:
            return
        if not should_crawl(url):
            return
        if self.pages_crawled >= MAX_PAGES_TO_CRAWL:
            return
        if len(self.found_emails) >= TARGET_EMAIL_COUNT:
            return

        self.visited.add(key)
        self.pages_crawled += 1

        if self.pages_crawled % 25 == 0:
            print(
                f"Progress: {self.pages_crawled} pages, "
                f"{len(self.saved_emails)} emails saved"
            )

        async with self.pool.acquire_page() as page:
            html = await self.fetch_page(page, url)
            if not html:
                return

            emails = extract_emails_from_html(html)
            for email in emails:
                if email not in self.found_emails:
                    self.found_emails.add(email)
                    await self.append_email(email, url)

            if depth < MAX_CRAWL_DEPTH and self.pages_crawled < MAX_PAGES_TO_CRAWL:
                contact_links = await page.eval_on_selector_all(
                    'a[href*="contact"], a[href*="about"], a[href*="info"], '
                    'a[href*="team"], a[href^="mailto:"]',
                    """els => els.map(e => e.href).filter(h => h && h.startsWith('http'))""",
                )
                for link in contact_links[:5]:
                    if normalize_url(link) not in self.visited and should_crawl(link):
                        await self._queue.put((link, depth + 1))

            await asyncio.sleep(random.uniform(*CRAWL_PAGE_DELAY))

    async def worker(self, worker_id: int) -> None:
        while True:
            url, depth = await self._queue.get()
            if url is None:
                self._queue.task_done()
                break
            try:
                await self.process_url(url, depth)
            except Exception as e:
                print(f"Worker {worker_id} error on {url[:50]}: {e}")
            finally:
                self._queue.task_done()

    async def crawl(self, start_urls: list[str]) -> None:
        await self.setup_output()

        filtered = [u for u in start_urls if should_crawl(u)]
        print(f"Crawling {len(filtered)} URLs (filtered from {len(start_urls)})")

        for url in filtered:
            await self._queue.put((url, 0))

        num_workers = self.pool.max_workers
        workers = [asyncio.create_task(self.worker(i)) for i in range(num_workers)]
        await self._queue.join()

        for _ in workers:
            await self._queue.put((None, 0))
        await self._queue.join()
        await asyncio.gather(*workers, return_exceptions=True)

        print(
            f"Crawl done: {self.pages_crawled} pages, "
            f"{len(self.saved_emails)} unique emails"
        )
