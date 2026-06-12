import argparse
import asyncio
import os
import shutil

from config import (
    CRAWL_DIR,
    DEFAULT_QUERIES,
    KEYWORD_VARIANTS,
    OUTPUT_FILE,
    PAGES_TO_SCRAPE,
    PLAYWRIGHT_CRAWL_WORKERS,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_SEARCH_WORKERS,
    UK_LOCATIONS,
)
from engine.playwright_pool import PlaywrightPool
from scrapers.ddg_scraper import get_result_urls_ddg
from scrapers.google_scraper_playwright import get_result_urls_google_parallel
from scrapers.playwright_crawler import PlaywrightEmailCrawler


async def search_ddg_parallel(queries: list[str], pages: int) -> list[str]:
    """Run DDG searches with staggered starts to avoid 202 rate limits."""
    sem = asyncio.Semaphore(2)

    async def one_query(query: str, delay: float) -> list[str]:
        await asyncio.sleep(delay)
        async with sem:
            return await asyncio.to_thread(get_result_urls_ddg, query, pages, 1.5)

    tasks = [one_query(q, i * 2.0) for i, q in enumerate(queries)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_urls: list[str] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"DDG query failed: {queries[i]} - {result}")
        else:
            all_urls.extend(result)
    return list(set(all_urls))


def build_queries(base_query: str, expand_locations: bool, no_variants: bool) -> list[str]:
    """Build search queries. Always includes plain query + optional keyword variants."""
    base_query = " ".join(base_query.split())  # collapse double spaces

    if expand_locations and "uk" in base_query.lower():
        queries = []
        for location in UK_LOCATIONS:
            location_query = base_query.lower().replace("uk", location)
            queries.append(location_query)
            if not no_variants:
                for variant in KEYWORD_VARIANTS:
                    queries.append(f'{location_query} "{variant}"')
        return queries

    queries = [base_query]
    if not no_variants:
        queries.extend(f'{base_query} "{variant}"' for variant in KEYWORD_VARIANTS)
    return queries


async def run(
    base_query: str | None,
    engine: str = "both",
    expand_locations: bool = False,
    fresh: bool = False,
    no_variants: bool = False,
    search_workers: int = PLAYWRIGHT_SEARCH_WORKERS,
    crawl_workers: int = PLAYWRIGHT_CRAWL_WORKERS,
    pages: int = PAGES_TO_SCRAPE,
):
    if fresh:
        if os.path.isdir(CRAWL_DIR):
            shutil.rmtree(CRAWL_DIR)
            print(f"Cleared crawl checkpoint: {CRAWL_DIR}")
        if os.path.exists(OUTPUT_FILE):
            os.remove(OUTPUT_FILE)
            print(f"Cleared output: {OUTPUT_FILE}")

    if base_query:
        queries = build_queries(base_query, expand_locations, no_variants)
    else:
        queries = DEFAULT_QUERIES

    print(f"Search queries ({len(queries)}): {queries[:3]}{'...' if len(queries) > 3 else ''}")

    all_urls: list[str] = []

    if engine in ("google", "both"):
        print(f"Phase 1a: Google (Playwright) — {len(queries)} queries, {search_workers} browsers")
        print(f"Pages per query: {pages}")
        async with PlaywrightPool(max_workers=search_workers, headless=PLAYWRIGHT_HEADLESS) as search_pool:
            google_urls = await get_result_urls_google_parallel(queries, search_pool, pages)
        all_urls.extend(google_urls)
        print(f"Google URLs: {len(google_urls)}")

    if engine in ("ddg", "both") or len(all_urls) < 20:
        print(f"\nPhase 1b: DuckDuckGo — {len(queries)} queries in parallel")
        ddg_urls = await search_ddg_parallel(queries, pages)
        all_urls.extend(ddg_urls)
        print(f"DDG URLs: {len(ddg_urls)}")

    all_urls = list(set(all_urls))
    print(f"\nTotal unique URLs found: {len(all_urls)}")

    if not all_urls:
        print("No URLs found. Try --engine ddg or run with --headed to debug Google.")
        return

    print(f"\nPhase 2: Email crawl — {crawl_workers} parallel browsers on {len(all_urls)} URLs")

    async with PlaywrightPool(max_workers=crawl_workers, headless=PLAYWRIGHT_HEADLESS) as crawl_pool:
        crawler = PlaywrightEmailCrawler(crawl_pool, OUTPUT_FILE)
        try:
            await crawler.crawl(all_urls)
        except KeyboardInterrupt:
            print(f"\nStopped. Emails saved so far: {len(crawler.saved_emails)}")
            return

    print(f"\nDone. {len(crawler.saved_emails)} unique emails saved to:")
    print(os.path.abspath(OUTPUT_FILE))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Email scraper with Playwright — parallel browser windows for Google + crawl"
    )
    parser.add_argument("query", nargs="?", default=None, help='e.g. "therapy in us"')
    parser.add_argument("--engine", default="both", choices=["google", "ddg", "both"],
                        help="Search engine(s) to use (default: both)")
    parser.add_argument("--output", default=None, help="Output CSV file (default: output/emails.csv)")
    parser.add_argument("--expand-locations", action="store_true", help="Expand UK queries to 15 major cities")
    parser.add_argument("--no-variants", action="store_true",
                        help="Search plain query only (no quoted email/contact filters)")
    parser.add_argument("--fresh", action="store_true", help="Clear output and start over")
    parser.add_argument("--search-workers", type=int, default=PLAYWRIGHT_SEARCH_WORKERS,
                        help=f"Parallel browsers for Google search (default: {PLAYWRIGHT_SEARCH_WORKERS})")
    parser.add_argument("--crawl-workers", type=int, default=PLAYWRIGHT_CRAWL_WORKERS,
                        help=f"Parallel browsers for page crawl (default: {PLAYWRIGHT_CRAWL_WORKERS})")
    parser.add_argument("--pages", type=int, default=PAGES_TO_SCRAPE,
                        help=f"Search result pages per query (default: {PAGES_TO_SCRAPE})")
    parser.add_argument("--headed", action="store_true", help="Show browser windows (not headless)")
    args = parser.parse_args()

    if args.output:
        import config
        config.OUTPUT_FILE = args.output

    if args.headed:
        import config
        config.PLAYWRIGHT_HEADLESS = False

    asyncio.run(
        run(
            args.query,
            args.engine,
            args.expand_locations,
            args.fresh,
            args.no_variants,
            args.search_workers,
            args.crawl_workers,
            args.pages,
        )
    )
