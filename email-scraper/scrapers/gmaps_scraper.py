"""Scrape business name and phone number from Google Maps search results."""

from __future__ import annotations

import time
import urllib.parse

from scrapling.fetchers import StealthySession

from config import GMAPS_DETAIL_DELAY, GMAPS_MAX_SCROLLS, GMAPS_SCROLL_DELAY


def build_maps_url(query: str) -> str:
    return f"https://www.google.com/maps/search/{urllib.parse.quote(query)}/"


def _dismiss_consent(page) -> None:
    for label in ("Accept all", "Reject all", "Accept"):
        try:
            page.locator(f'button:has-text("{label}")').click(timeout=2000)
            return
        except Exception:
            continue


def _scroll_results_feed(page, max_scrolls: int) -> None:
    last_height = 0
    for _ in range(max_scrolls):
        page.evaluate(
            """() => {
            const feed = document.querySelector('div[role="feed"]');
            if (feed) feed.scrollTop = feed.scrollHeight;
        }"""
        )
        time.sleep(GMAPS_SCROLL_DELAY)
        height = page.evaluate(
            """() => {
            const feed = document.querySelector('div[role="feed"]');
            return feed ? feed.scrollHeight : 0;
        }"""
        )
        if height == last_height:
            break
        last_height = height


def _extract_name(article) -> str:
    for sel in (".qBF1Pd", ".fontHeadlineSmall", "a.hfpxzc"):
        loc = article.locator(sel).first
        if loc.count():
            name = (loc.inner_text() or loc.get_attribute("aria-label") or "").strip()
            if name:
                return name
    aria = article.get_attribute("aria-label") or ""
    return aria.strip()


def _extract_phone_from_detail(page) -> str:
    for sel in (
        'button[data-item-id^="phone:tel:"]',
        'button[data-item-id*="phone"]',
        'a[href^="tel:"]',
    ):
        loc = page.locator(sel).first
        if not loc.count():
            continue
        data_id = loc.get_attribute("data-item-id") or ""
        if data_id.startswith("phone:tel:"):
            return urllib.parse.unquote(data_id.removeprefix("phone:tel:")).strip()
        href = loc.get_attribute("href") or ""
        if href.startswith("tel:"):
            return urllib.parse.unquote(href.removeprefix("tel:")).strip()
        aria = loc.get_attribute("aria-label") or ""
        if "Phone:" in aria:
            return aria.split("Phone:", 1)[-1].strip()
    return ""


def _extract_website_from_detail(page) -> str:
    """Extract the business website URL from the Maps detail panel."""
    # Google Maps renders website as a link with data-item-id="authority"
    for sel in (
        'a[data-item-id="authority"]',
        'a[href*="//"][aria-label*="website" i]',
        'a[href*="//"][aria-label*="Website" i]',
    ):
        loc = page.locator(sel).first
        if not loc.count():
            continue
        href = loc.get_attribute("href") or ""
        if href and href.startswith("http"):
            # Strip Google's redirect wrapper if present
            if "google.com/url" in href or "google.com/maps/place" in href:
                # Try to parse the actual URL from the `url` query param
                parsed = urllib.parse.urlparse(href)
                params = urllib.parse.parse_qs(parsed.query)
                actual = params.get("q") or params.get("url")
                if actual:
                    return actual[0].strip()
            return href.strip()
    return ""


def _extract_businesses_from_page(page, max_scrolls: int) -> list[dict[str, str]]:
    page.wait_for_selector('div[role="feed"]', timeout=30000)
    _scroll_results_feed(page, max_scrolls)

    articles = page.locator('div[role="feed"] div[role="article"]')
    count = articles.count()
    businesses: list[dict[str, str]] = []
    seen_names: set[str] = set()

    for i in range(count):
        article = articles.nth(i)
        name = _extract_name(article)
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())

        phone = ""
        website = ""
        try:
            article.click(timeout=10000)
            time.sleep(GMAPS_DETAIL_DELAY)
            phone = _extract_phone_from_detail(page)
            website = _extract_website_from_detail(page)
        except Exception:
            pass

        businesses.append({"business_name": name, "number": phone, "website": website})
        extra = " | ".join(filter(None, [phone, website]))
        print(f"  [{len(businesses)}] {name}" + (f" - {extra}" if extra else ""))

    return businesses


def scrape_gmaps_businesses(query: str, max_scrolls: int = GMAPS_MAX_SCROLLS) -> list[dict[str, str]]:
    """Return list of {business_name, number} dicts for a Maps search query."""
    url = build_maps_url(query)
    results: list[dict[str, str]] = []

    def page_action(page):
        _dismiss_consent(page)
        extracted = _extract_businesses_from_page(page, max_scrolls)
        results.extend(extracted)

    with StealthySession(headless=True, solve_cloudflare=True) as session:
        session.fetch(url, network_idle=True, timeout=120000, page_action=page_action)

    return results
