import argparse
import asyncio
import os
import shutil
import signal

from config import (
    CONCURRENT_REQUESTS,
    CRAWL_DIR,
    DEFAULT_QUERIES,
    KEYWORD_VARIANTS,
    MIN_URLS_BEFORE_CRAWL,
    OUTPUT_FILE,
    PAGES_TO_SCRAPE,
    UK_LOCATIONS,
)
from scrapers.ddg_scraper import get_result_urls_ddg
from scrapers.google_scraper import get_result_urls_google
from spiders.email_spider import EmailSpider
from utils.csv_output import count_data_rows


async def get_urls_for_query_async(query: str, engine: str, sem: asyncio.Semaphore) -> list[str]:
    async with sem:
        print(f"Searching: {query}")
        try:
            if engine == "google":
                return await asyncio.to_thread(get_result_urls_google, query, PAGES_TO_SCRAPE)
            else:
                return await asyncio.to_thread(get_result_urls_ddg, query, PAGES_TO_SCRAPE)
        except Exception as e:
            print(f"Error scraping search engine for query '{query}': {e}")
            return []


async def run(base_query: str | None, engine: str = "google", expand_locations: bool = False, fresh: bool = False):
    if fresh and os.path.isdir(CRAWL_DIR):
        shutil.rmtree(CRAWL_DIR)
        print(f"Cleared crawl checkpoint: {CRAWL_DIR}")

    if base_query:
        # Generate location-based queries for UK if enabled
        if expand_locations and "uk" in base_query.lower():
            queries = []
            for location in UK_LOCATIONS:
                for variant in KEYWORD_VARIANTS:
                    # Replace "uk" with specific location
                    location_query = base_query.lower().replace("uk", location)
                    queries.append(f'{location_query} "{variant}"')
        else:
            queries = [f'{base_query} "{variant}"' for variant in KEYWORD_VARIANTS]
    else:
        queries = DEFAULT_QUERIES

    print(f"Running search queries concurrently ({len(queries)} total)...")
    
    # Semaphore of 2 allows 2 concurrent search engine queries
    sem = asyncio.Semaphore(2)
    
    # Stagger request starts with larger delay to be stealthier
    async def task_with_jitter(query: str, delay: float) -> list[str]:
        await asyncio.sleep(delay)
        return await get_urls_for_query_async(query, engine, sem)

    tasks = [task_with_jitter(q, index * 6.0) for index, q in enumerate(queries)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_urls: list[str] = []
    failed_queries = 0
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Query failed: {queries[i]} - {result}")
            failed_queries += 1
        else:
            all_urls.extend(result)
    
    all_urls = list(set(all_urls))
    print(f"Total unique URLs found: {len(all_urls)} (failed queries: {failed_queries})")

    # Auto-fallback to DDG if Google failed significantly
    if len(all_urls) < 10 and engine == "google" and failed_queries > 0:
        print("Google failed significantly, trying DDG as fallback...")
        engine = "ddg"
        tasks = [task_with_jitter(q, index * 3.0) for index, q in enumerate(queries)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                all_urls.extend(result)
        
        all_urls = list(set(all_urls))
        print(f"After DDG fallback: {len(all_urls)} unique URLs")

    if not all_urls:
        print("No URLs found. Try --engine ddg if Google blocked the request.")
        return

    query_label = base_query or ", ".join(DEFAULT_QUERIES[:2]) + ", ..."
    existing = count_data_rows(OUTPUT_FILE)
    print(f"\nOutput file: {os.path.abspath(OUTPUT_FILE)}")
    print(f"Emails already in CSV: {existing}")
    print(f"Starting email spider on {len(all_urls)} URLs...")
    print("Tip: you can run a second terminal with the same --output; both append safely.\n")

    spider = EmailSpider(
        start_urls=all_urls,
        output_file=OUTPUT_FILE,
        crawldir=CRAWL_DIR,
        concurrent_requests=CONCURRENT_REQUESTS,
        query_label=query_label,
    )

    _sigint_count = 0
    _original_sigint = signal.getsignal(signal.SIGINT)

    def _handle_sigint(signum, frame):
        nonlocal _sigint_count
        _sigint_count += 1
        if _sigint_count == 1:
            print("\nCtrl+C — stopping gracefully (finishing active requests)...")
            print("Press Ctrl+C again to force quit.")
            spider.request_stop()
        else:
            print("\nForce quit.")
            if _original_sigint not in (signal.SIG_DFL, signal.SIG_IGN):
                signal.signal(signal.SIGINT, _original_sigint)
            raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        result = await asyncio.to_thread(spider.start)
    except KeyboardInterrupt:
        total = spider._csv_total_at_start + spider._session_saved
        print(f"\nStopped. {spider._session_saved} new emails this run ({total} total in CSV).")
        return
    finally:
        signal.signal(signal.SIGINT, _original_sigint)

    total = spider._csv_total_at_start + spider._session_saved
    print(f"\nDone. {spider._session_saved} new emails this run ({total} total in CSV):")
    print(os.path.abspath(OUTPUT_FILE))
    print(f"Requests: {result.stats.requests_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Email scraper powered by Scrapling")
    parser.add_argument("query", nargs="?", default=None, help='e.g. "clinics in uk"')
    parser.add_argument("--engine", default="google", choices=["google", "ddg"])
    parser.add_argument("--output", default=None, help='Output CSV file (default: output/emails.csv)')
    parser.add_argument("--expand-locations", action="store_true", help='Expand UK queries to 15 major cities')
    parser.add_argument("--fresh", action="store_true", help='Clear saved crawl checkpoint and start over')
    args = parser.parse_args()
    
    if args.output:
        global OUTPUT_FILE
        OUTPUT_FILE = args.output
    
    asyncio.run(run(args.query, args.engine, args.expand_locations, args.fresh))
