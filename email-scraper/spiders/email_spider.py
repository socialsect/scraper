import os
from urllib.parse import urlparse, urlunparse

from scrapling.fetchers import AsyncStealthySession, FetcherSession
from scrapling.spiders import Request, Response, Spider

from config import CONCURRENT_REQUESTS, MAX_CRAWL_DEPTH, MAX_PAGES_TO_CRAWL, TARGET_EMAIL_COUNT
from utils.csv_output import (
    append_email_row,
    count_data_rows,
    ensure_csv_header,
    load_existing_emails,
    write_query_marker,
)
from utils.email_regex import extract_emails_from_html, is_valid_email as regex_is_valid_email

DOMAIN_BLOCKLIST = [
    'gov.uk',
    'nhs.net',
    'nhs.scot',
    'ac.uk',
    'gov.scot',
    'microsoft.com',
    'nasa.gov',
    'facebook.com',
    'linkedin.com',
    'google.com',
    'visa.com',
    'amazon.com',
    'wikipedia.org',
    'sentry.io',
    'wixpress.com',
    'youtube.com',
    'www.youtube.com',
    'youtu.be',
    'apps.trac.jobs',
    'trac.jobs',
]

BLOCKED_URLS = (
    'https://apps.trac.jobs/about',
    'apps.trac.jobs/about',
)

BLOCKED_TLDS = (
    '.gov',
    '.in',
    '.pk',
    '.cn',
    '.za',
    '.ng',
    '.tn',
)


def normalize_crawl_url(url: str) -> str:
    """Strip query/fragment so ?_ts=... variants count as the same page."""
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
    email = email.lower().strip()

    if not regex_is_valid_email(email):
        return False

    try:
        domain = email.split("@", 1)[1]
    except IndexError:
        return False

    if domain.endswith(BLOCKED_TLDS):
        return False

    if not should_crawl(email):
        return False

    return True


class EmailSpider(Spider):
    name = "email_hunter"
    concurrent_requests = CONCURRENT_REQUESTS

    def __init__(
        self,
        start_urls: list[str],
        output_file: str,
        crawldir: str | None = None,
        concurrent_requests: int = CONCURRENT_REQUESTS,
        query_label: str = "default queries",
    ):
        self._start_urls = start_urls
        self.output_file = output_file
        self.query_label = query_label
        self.found_emails: set[str] = set()
        self.concurrent_requests = concurrent_requests
        self.saved_emails: set[str] = set()
        self._session_saved = 0
        self._csv_total_at_start = 0
        self._visited_pages: set[str] = set()
        self._pages_crawled = 0
        self._stop_requested = False

        super().__init__(crawldir=crawldir)

    async def on_start(self, resuming: bool = False):
        ensure_csv_header(self.output_file)
        self.saved_emails = load_existing_emails(self.output_file)
        self._csv_total_at_start = count_data_rows(self.output_file)
        write_query_marker(self.output_file, self.query_label)

        print(f"Output CSV: {os.path.abspath(self.output_file)}")
        print(f"Emails already in CSV: {self._csv_total_at_start}")
        print(f"URLs to crawl: {len(self._start_urls)}")
        print("Press Ctrl+C once to stop gracefully (twice to force quit).\n")

    def request_stop(self) -> None:
        """Called from the main thread on Ctrl+C (signal handlers cannot run in worker threads)."""
        self._stop_requested = True
        try:
            self.pause()
        except RuntimeError:
            pass

    def append_email(self, email: str, source: str):
        email = email.lower().strip()

        if not is_valid_email(email):
            return

        if not append_email_row(self.output_file, email, source, self.saved_emails):
            return

        self._session_saved += 1
        total = self._csv_total_at_start + self._session_saved
        print(
            f"[{self._session_saved} new | {total} total in CSV] "
            f"Saved: {email} (from {source[:80]})"
        )

    def configure_sessions(self, manager):
        manager.add(
            "fast",
            FetcherSession(
                impersonate="chrome",
                stealthy_headers=True,
            ),
            default=True,
        )

        manager.add(
            "stealth",
            AsyncStealthySession(
                headless=True,
                solve_cloudflare=True,
                network_idle=True,
            ),
            lazy=True,
        )

    async def start_requests(self):
        for url in self._start_urls:
            if should_crawl(url):
                yield Request(
                    url,
                    callback=self.parse,
                    sid="fast",
                    meta={"depth": 0},
                )

    async def parse(self, response: Response):
        if self._stop_requested:
            return

        page_key = normalize_crawl_url(response.url)
        if page_key in self._visited_pages:
            return
        self._visited_pages.add(page_key)
        self._pages_crawled += 1

        if self._pages_crawled % 10 == 0:
            total = self._csv_total_at_start + self._session_saved
            print(
                f"Progress: {self._pages_crawled} pages crawled | "
                f"{self._session_saved} new emails this run | {total} total in CSV"
            )

        emails = extract_emails_from_html(response.html_content)

        for link in response.css('a[href^="mailto:"]::attr(href)').getall():
            email = (
                link.replace("mailto:", "")
                .split("?")[0]
                .strip()
                .lower()
            )

            if "@" in email:
                emails.add(email)

        for email in emails:
            email = email.lower().strip()

            if email in self.found_emails:
                continue

            self.found_emails.add(email)
            self.append_email(email, response.url)

        depth = response.meta.get("depth", 0)
        if (
            len(self.found_emails) < TARGET_EMAIL_COUNT
            and self._pages_crawled < MAX_PAGES_TO_CRAWL
            and depth < MAX_CRAWL_DEPTH
        ):
            for keyword in ("contact", "about", "info", "team", "staff"):
                for link in response.css(
                    f'a[href*="{keyword}"]::attr(href)'
                ).getall()[:3]:
                    absolute_url = response.urljoin(link)

                    if not should_crawl(absolute_url):
                        continue

                    if normalize_crawl_url(absolute_url) in self._visited_pages:
                        continue

                    yield response.follow(
                        link,
                        callback=self.parse,
                        sid="fast",
                        meta={"depth": depth + 1},
                    )