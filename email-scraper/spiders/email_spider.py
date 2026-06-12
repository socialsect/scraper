import csv
import os
from urllib.parse import urlparse, urlunparse

from scrapling.fetchers import AsyncStealthySession, FetcherSession
from scrapling.spiders import Request, Response, Spider

from config import CONCURRENT_REQUESTS, MAX_CRAWL_DEPTH, MAX_PAGES_TO_CRAWL, TARGET_EMAIL_COUNT
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
    ):
        self._start_urls = start_urls
        self.output_file = output_file
        self.found_emails: set[str] = set()
        self.concurrent_requests = concurrent_requests
        self.saved_emails: set[str] = set()
        self._visited_pages: set[str] = set()
        self._pages_crawled = 0

        super().__init__(crawldir=crawldir)

    async def on_start(self, resuming: bool = False):
        os.makedirs(os.path.dirname(self.output_file) or ".", exist_ok=True)
        if not os.path.exists(self.output_file):
            with open(self.output_file, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["email", "source"])
            print(f"Created output file: {os.path.abspath(self.output_file)}")

    def append_email(self, email: str, source: str):
        email = email.lower().strip()

        if not is_valid_email(email):
            return

        if email in self.saved_emails:
            return

        os.makedirs(os.path.dirname(self.output_file) or ".", exist_ok=True)

        file_exists = os.path.exists(self.output_file)

        with open(self.output_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if not file_exists:
                writer.writerow(["email", "source"])

            writer.writerow([email, source])

        self.saved_emails.add(email)
        print(f"Saved: {email} (from {source})")

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
        page_key = normalize_crawl_url(response.url)
        if page_key in self._visited_pages:
            return
        self._visited_pages.add(page_key)
        self._pages_crawled += 1

        if self._pages_crawled % 25 == 0:
            print(
                f"Progress: {self._pages_crawled} pages crawled, "
                f"{len(self.saved_emails)} emails saved"
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