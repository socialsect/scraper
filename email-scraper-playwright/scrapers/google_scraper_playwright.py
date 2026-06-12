"""Google search via Playwright — runs each query in its own browser context."""

import asyncio
import random
import urllib.parse

from config import PAGES_TO_SCRAPE, SEARCH_PAGE_DELAY
from engine.playwright_pool import PlaywrightPool, dismiss_consent


def build_google_url(query: str, page: int) -> str:
    encoded = urllib.parse.quote_plus(query)
    start = page * 10
    return f"https://www.google.com/search?q={encoded}&start={start}&hl=en&gl=us"


async def _extract_links(page) -> list[str]:
    """Extract organic result URLs from a Google SERP page."""
    try:
        await page.wait_for_selector("#search, div#rso, div.g", timeout=8000)
    except Exception:
        pass

    hrefs = await page.evaluate("""() => {
        const skip = ['google.com', 'google.co.', 'gstatic.com', 'youtube.com/redirect'];
        const out = new Set();
        // h3 is the standard organic result title wrapper
        for (const h3 of document.querySelectorAll('h3')) {
            const a = h3.closest('a') || h3.querySelector('a') || h3.parentElement?.querySelector('a');
            if (a && a.href && a.href.startsWith('http')) {
                if (!skip.some(s => a.href.includes(s))) out.add(a.href);
            }
        }
        // fallback selectors
        for (const sel of ['div.g a[href^="http"]', 'a[data-ved][href^="http"]', '#rso a[href^="http"]']) {
            for (const a of document.querySelectorAll(sel)) {
                if (!skip.some(s => a.href.includes(s))) out.add(a.href);
            }
        }
        return [...out];
    }""")
    return hrefs or []


async def search_google_query(
    pool: PlaywrightPool,
    query: str,
    pages: int = PAGES_TO_SCRAPE,
) -> list[str]:
    urls: list[str] = []

    async with pool.acquire_page() as page:
        for page_num in range(pages):
            url = build_google_url(query, page_num)
            try:
                await page.goto(url, wait_until="networkidle", timeout=45000)
                await dismiss_consent(page)
                await asyncio.sleep(random.uniform(1.0, 2.0))

                if "sorry" in page.url or "captcha" in (await page.content()).lower():
                    print(f"  [{query[:40]}] blocked/captcha on page {page_num + 1}, stopping")
                    break

                page_urls = await _extract_links(page)
                if not page_urls:
                    print(f"  [{query[:40]}] page {page_num + 1}: no results, stopping")
                    break

                urls.extend(page_urls)
                print(f"  [{query[:40]}] page {page_num + 1}: {len(page_urls)} links")

                delay = random.uniform(*SEARCH_PAGE_DELAY)
                await asyncio.sleep(delay)
            except Exception as e:
                print(f"  [{query[:40]}] page {page_num + 1} error: {e}")
                break

    unique = list(set(urls))
    print(f"  [{query[:40]}] total: {len(unique)} unique URLs")
    return unique


async def get_result_urls_google_parallel(
    queries: list[str],
    pool: PlaywrightPool,
    pages: int = PAGES_TO_SCRAPE,
) -> list[str]:
    """Run all search queries concurrently, each in its own browser context."""
    tasks = [search_google_query(pool, q, pages) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_urls: list[str] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Query failed: {queries[i]} - {result}")
        else:
            all_urls.extend(result)

    return list(set(all_urls))
