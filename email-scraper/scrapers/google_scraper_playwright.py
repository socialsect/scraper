"""Google search via Playwright — handles JS-heavy anti-bot pages."""

from __future__ import annotations

import asyncio
import random
import urllib.parse

from config import PAGES_TO_SCRAPE, SEARCH_PAGE_DELAY


def build_google_url(query: str, page: int) -> str:
    encoded = urllib.parse.quote_plus(query)
    start = page * 10
    return f"https://www.google.com/search?q={encoded}&start={start}"


def _extract_urls_from_html(html: str) -> list[str]:
    import re
    urls = []
    # Match href="https://..." that aren't google-internal
    for match in re.finditer(r'href="(https?://[^"]+)"', html):
        url = match.group(1)
        if "google.com" not in url and url.startswith("http"):
            urls.append(url)
    return urls


async def get_result_urls_google_parallel(
    queries: list[str],
    pool,
    pages: int = PAGES_TO_SCRAPE,
) -> list[str]:
    """Run all queries in parallel using the shared PlaywrightPool."""
    sem = asyncio.Semaphore(pool.max_workers)

    async def fetch_query(query: str) -> list[str]:
        urls: list[str] = []
        async with sem:
            for page_num in range(pages):
                url = build_google_url(query, page_num)
                try:
                    async with pool.acquire_page() as page:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        html = await page.content()
                        found = _extract_urls_from_html(html)
                        urls.extend(found)
                        print(f"  Google page {page_num + 1}/{pages} for '{query[:40]}': {len(found)} links")
                except Exception as e:
                    print(f"  Google failed page {page_num + 1} for '{query[:40]}': {e}")
                    break
                delay = random.uniform(*SEARCH_PAGE_DELAY)
                await asyncio.sleep(delay)
        return urls

    tasks = [fetch_query(q) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_urls: list[str] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Query failed: {queries[i]} - {result}")
        else:
            all_urls.extend(result)

    return list(set(all_urls))
