from __future__ import annotations

import asyncio
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
from utils.mx_check import validate_email_mx
from utils.phone_regex import extract_phones_from_html, extract_phone_from_tel_links
from utils.social_links import extract_social_links

DOMAIN_BLOCKLIST = [
    'gov.uk', 'nhs.net', 'nhs.scot', 'ac.uk', 'gov.scot',
    'microsoft.com', 'nasa.gov', 'facebook.com', 'linkedin.com',
    'google.com', 'visa.com', 'amazon.com', 'wikipedia.org',
    'sentry.io', 'wixpress.com', 'youtube.com', 'www.youtube.com',
    'youtu.be', 'apps.trac.jobs', 'trac.jobs',
]

BLOCKED_URLS = (
    'https://apps.trac.jobs/about',
    'apps.trac.jobs/about',
)

BLOCKED_TLDS = ('.gov', '.in', '.pk', '.cn', '.za', '.ng', '.tn')


def normalize_crawl_url(url: str) -> str:
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
    return should_crawl(email)


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
        live_display=None,
        check_mx: bool = True,
    ):
        self._start_urls = start_urls
        self.output_file = output_file
        self.query_label = query_label
        self.live_display = live_display
        self.check_mx = check_mx
        self.found_emails: set[str] = set()
        self.concurrent_requests = concurrent_requests
        self.saved_emails: set[str] = set()
        self._session_saved = 0
        self._csv_total_at_start = 0
        self._visited_pages: set[str] = set()
        self._pages_crawled = 0
        self._stop_requested = False

        # Per-domain enrichment cache: domain -> {phone, socials}
        # So we don't lose enrichment data found on page A when saving from page B
        self._domain_data: dict[str, dict] = {}

        super().__init__(crawldir=crawldir)

    async def on_start(self, resuming: bool = False):
        ensure_csv_header(self.output_file)
        self.saved_emails = load_existing_emails(self.output_file)
        self._csv_total_at_start = count_data_rows(self.output_file)
        write_query_marker(self.output_file, self.query_label)

        if self.live_display:
            self.live_display.log(
                f"[cyan]Spider started[/cyan] — {len(self._start_urls)} URLs, "
                f"{self._csv_total_at_start} emails already in CSV"
                + (" [MX validation on]" if self.check_mx else "")
            )
        else:
            print(f"Output CSV: {os.path.abspath(self.output_file)}")
            print(f"Emails already in CSV: {self._csv_total_at_start}")
            print(f"URLs to crawl: {len(self._start_urls)}")
            print(f"MX validation: {'on' if self.check_mx else 'off'}")
            print("Press Ctrl+C once to stop gracefully (twice to force quit).\n")

    def request_stop(self) -> None:
        self._stop_requested = True
        try:
            self.pause()
        except RuntimeError:
            pass

    def _get_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""

    async def save_email(
        self,
        email: str,
        source: str,
        enrichment: dict,
    ) -> None:
        """Async save — runs MX check if enabled, calculates confidence score, then writes CSV row."""
        email = email.lower().strip()
        if not is_valid_email(email):
            return

        mx_valid = ""
        if self.check_mx:
            ok = await validate_email_mx(email)
            mx_valid = "yes" if ok else "no"
            if not ok:
                if self.live_display:
                    self.live_display.log(f"[dim]MX fail: {email}[/dim]")
                return  # drop emails whose domain has no MX record

        # Calculate confidence score
        from utils.confidence import score_from_source
        # Extract visible text (simplified - in production would parse HTML more carefully)
        visible_text = email  # Basic fallback
        confidence = score_from_source(
            email=email,
            html="",  # Would need full HTML for better scoring
            url=source,
            visible_text=visible_text
        )

        written = append_email_row(
            self.output_file,
            email,
            source,
            self.saved_emails,
            phone=enrichment.get("phone", ""),
            linkedin=enrichment.get("linkedin", ""),
            twitter=enrichment.get("twitter", ""),
            instagram=enrichment.get("instagram", ""),
            facebook=enrichment.get("facebook", ""),
            youtube=enrichment.get("youtube", ""),
            mx_valid=mx_valid,
            confidence=str(confidence),
        )

        if not written:
            return

        self._session_saved += 1
        total = self._csv_total_at_start + self._session_saved

        if self.live_display:
            self.live_display.update_stats(
                pages=self._pages_crawled,
                new_emails=self._session_saved,
                total_emails=total,
                last_email=email,
            )
        else:
            extras = " | ".join(filter(None, [
                enrichment.get("phone", ""),
                enrichment.get("linkedin", ""),
            ]))
            print(
                f"[{self._session_saved} new | {total} total] "
                f"{email}"
                + (f"  ({extras})" if extras else "")
                + f"  — {source[:60]}"
            )

    def configure_sessions(self, manager):
        manager.add(
            "fast",
            FetcherSession(impersonate="chrome", stealthy_headers=True),
            default=True,
        )
        manager.add(
            "stealth",
            AsyncStealthySession(headless=True, solve_cloudflare=True, network_idle=True),
            lazy=True,
        )

    async def start_requests(self):
        for url in self._start_urls:
            if should_crawl(url):
                yield Request(url, callback=self.parse, sid="fast", meta={"depth": 0})

    async def parse(self, response: Response):
        if self._stop_requested:
            return

        page_key = normalize_crawl_url(response.url)
        if page_key in self._visited_pages:
            return
        self._visited_pages.add(page_key)
        self._pages_crawled += 1

        if self.live_display:
            if self._pages_crawled % 5 == 0:
                self.live_display.update_stats(
                    pages=self._pages_crawled,
                    new_emails=self._session_saved,
                    total_emails=self._csv_total_at_start + self._session_saved,
                )
        elif self._pages_crawled % 10 == 0:
            total = self._csv_total_at_start + self._session_saved
            print(
                f"Progress: {self._pages_crawled} pages | "
                f"{self._session_saved} new emails | {total} total in CSV"
            )

        html_content = response.html_content
        domain = self._get_domain(response.url)

        # --- Phone extraction ---
        tel_hrefs = [
            a.replace("mailto:", "")  # won't match but harmless
            for a in response.css('a[href^="tel:"]::attr(href)').getall()
        ]
        phones_from_links = extract_phone_from_tel_links(tel_hrefs)
        phones_from_body = extract_phones_from_html(html_content)
        all_phones = phones_from_links or phones_from_body  # prefer tel: links
        primary_phone = all_phones[0] if all_phones else ""

        # --- Social link extraction ---
        all_hrefs = response.css("a::attr(href)").getall()
        socials = extract_social_links(all_hrefs)

        # Accumulate enrichment per domain — later pages on same site fill gaps
        if domain not in self._domain_data:
            self._domain_data[domain] = {}
        existing = self._domain_data[domain]
        if primary_phone and not existing.get("phone"):
            existing["phone"] = primary_phone
        for key in ("linkedin", "twitter", "instagram", "facebook", "youtube"):
            if socials.get(key) and not existing.get(key):
                existing[key] = socials[key]

        enrichment = self._domain_data[domain]

        # --- Email extraction ---
        emails = extract_emails_from_html(html_content)
        for link in response.css('a[href^="mailto:"]::attr(href)').getall():
            email = link.replace("mailto:", "").split("?")[0].strip().lower()
            if "@" in email:
                emails.add(email)

        # Save new emails — run MX checks concurrently across all found addresses
        new_emails = [e.lower().strip() for e in emails if e.lower().strip() not in self.found_emails]
        for e in new_emails:
            self.found_emails.add(e)

        await asyncio.gather(*[self.save_email(e, response.url, enrichment) for e in new_emails])

        # --- Follow contact/about/team links ---
        depth = response.meta.get("depth", 0)
        if (
            len(self.found_emails) < TARGET_EMAIL_COUNT
            and self._pages_crawled < MAX_PAGES_TO_CRAWL
            and depth < MAX_CRAWL_DEPTH
        ):
            for keyword in ("contact", "about", "info", "team", "staff"):
                for link in response.css(f'a[href*="{keyword}"]::attr(href)').getall()[:3]:
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
