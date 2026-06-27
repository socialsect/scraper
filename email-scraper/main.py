import argparse
import asyncio
import os
import shutil
import signal
from typing import Callable, Optional

from config import (
    CONCURRENT_REQUESTS,
    CRAWL_DIR,
    DEFAULT_QUERIES,
    GMAPS_EMAILS_OUTPUT_FILE,
    GMAPS_MAX_SCROLLS,
    GMAPS_OUTPUT_FILE,
    KEYWORD_VARIANTS,
    LOCATION_EXPAND_LIST,
    MIN_URLS_BEFORE_CRAWL,
    OUTPUT_FILE,
    PAGES_TO_SCRAPE,
    PLAYWRIGHT_CRAWL_WORKERS,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_SEARCH_WORKERS,
)
from utils.mx_check import mx_cache_stats
from scrapers.ddg_scraper import get_result_urls_ddg
from scrapers.gmaps_scraper import scrape_gmaps_businesses
from scrapers.google_scraper import get_result_urls_google
from spiders.email_spider import EmailSpider
from utils.business_csv import (
    append_business_row,
    count_data_rows as count_business_rows,
    load_existing_keys,
    load_websites,
    write_query_marker as write_business_query_marker,
)
from utils.csv_output import count_data_rows
from utils.display import LiveDisplay, console


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_queries(
    base_query: str,
    expand_locations: bool,
    locations: list[str],
    no_variants: bool,
) -> list[str]:
    if expand_locations and locations:
        queries: list[str] = []
        for location in locations:
            location_query = f"{base_query} {location}"
            queries.append(location_query)
            if not no_variants:
                for variant in KEYWORD_VARIANTS:
                    queries.append(f'{location_query} "{variant}"')
        return queries

    queries = [base_query]
    if not no_variants:
        queries.extend(f'{base_query} "{variant}"' for variant in KEYWORD_VARIANTS)
    return queries


async def get_urls_for_query_async(query: str, engine: str, sem: asyncio.Semaphore) -> list[str]:
    async with sem:
        try:
            if engine == "google":
                return await asyncio.to_thread(get_result_urls_google, query, PAGES_TO_SCRAPE)
            else:
                return await asyncio.to_thread(get_result_urls_ddg, query, PAGES_TO_SCRAPE)
        except Exception as e:
            console.print(f"[red]Error scraping '{query}': {e}[/red]")
            return []


# ---------------------------------------------------------------------------
# Google Maps modes
# ---------------------------------------------------------------------------

async def run_gmaps(
    base_query: str | None,
    scrolls: int = GMAPS_MAX_SCROLLS,
    output_file: str = GMAPS_OUTPUT_FILE,
):
    if not base_query:
        console.print("[red]--gmaps requires a search query, e.g. python main.py --gmaps \"dental clinics london\"[/red]")
        return

    existing = count_business_rows(output_file)
    known_keys = load_existing_keys(output_file)
    console.print(f"\nOutput file: [cyan]{os.path.abspath(output_file)}[/cyan]")
    console.print(f"Businesses already in CSV: [bold]{existing}[/bold]")
    console.print(f"Searching Google Maps: [yellow]{base_query}[/yellow]\n")

    write_business_query_marker(output_file, base_query)
    businesses = await asyncio.to_thread(scrape_gmaps_businesses, base_query, scrolls)

    saved = 0
    for biz in businesses:
        if append_business_row(output_file, biz["number"], biz["business_name"], known_keys, biz.get("website", "")):
            saved += 1
            total = existing + saved
            console.print(f"[[bold green]{saved} new[/bold green] | {total} total] {biz['business_name']}")

    console.print(f"\n[bold green]Done.[/bold green] {saved} new businesses ({existing + saved} total):")
    console.print(os.path.abspath(output_file))


async def run_gmaps_emails(
    base_query: str | None,
    scrolls: int = GMAPS_MAX_SCROLLS,
    businesses_file: str = GMAPS_OUTPUT_FILE,
    emails_file: str = GMAPS_EMAILS_OUTPUT_FILE,
    fresh: bool = False,
    from_existing: bool = False,
    backend: str = "scrapling",
    check_mx: bool = True,
):
    if not from_existing:
        if not base_query:
            console.print("[red]--gmaps-emails requires a search query[/red]")
            return

        existing = count_business_rows(businesses_file)
        known_keys = load_existing_keys(businesses_file)
        console.print(f"\n[bold cyan][Phase 1][/bold cyan] Scraping Google Maps: [yellow]{base_query}[/yellow]")

        write_business_query_marker(businesses_file, base_query)
        businesses = await asyncio.to_thread(scrape_gmaps_businesses, base_query, scrolls)

        saved = 0
        for biz in businesses:
            if append_business_row(businesses_file, biz["number"], biz["business_name"], known_keys, biz.get("website", "")):
                saved += 1
                total = existing + saved
                website_note = f" | {biz['website']}" if biz.get("website") else ""
                console.print(f"[[bold]{saved} new[/bold] | {total} total] {biz['business_name']}{website_note}")

        console.print(f"\n[bold green]Phase 1 done.[/bold green] {saved} new businesses saved.")
    else:
        console.print(f"\n[dim][Phase 1 skipped] Loading from: {os.path.abspath(businesses_file)}[/dim]")

    websites = load_websites(businesses_file)
    if not websites:
        console.print("[yellow]No website URLs found in businesses CSV. Nothing to crawl.[/yellow]")
        return

    websites = list(set(websites))
    console.print(f"\n[bold cyan][Phase 2][/bold cyan] Crawling [bold]{len(websites)}[/bold] website(s) for emails...")

    crawl_dir = os.path.join(os.path.dirname(emails_file), "crawl_data_gmaps")
    if fresh and os.path.isdir(crawl_dir):
        shutil.rmtree(crawl_dir)

    query_label = base_query or f"websites from {os.path.basename(businesses_file)}"

    display = LiveDisplay(
        query=query_label,
        total_urls=len(websites),
        backend=backend,
    )

    with display:
        await _crawl_urls(
            urls=websites,
            output_file=emails_file,
            crawl_dir=crawl_dir,
            query_label=query_label,
            backend=backend,
            display=display,
            check_mx=check_mx,
        )


# ---------------------------------------------------------------------------
# Domain-targeted mode
# ---------------------------------------------------------------------------

async def run_domains(
    domains_file: str,
    output_file: str = OUTPUT_FILE,
    backend: str = "scrapling",
    fresh: bool = False,
    check_mx: bool = True,
):
    """
    Skip search entirely — read a list of domains/URLs from a file and crawl them directly.
    File format: one domain or URL per line. Lines starting with # are ignored.
    """
    if not os.path.exists(domains_file):
        console.print(f"[red]Domains file not found: {domains_file}[/red]")
        return

    with open(domains_file, "r", encoding="utf-8") as f:
        raw_lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # Normalise: ensure each entry is a full URL
    urls: list[str] = []
    for line in raw_lines:
        if line.startswith("http://") or line.startswith("https://"):
            urls.append(line)
        else:
            urls.append(f"https://{line}")

    urls = list(dict.fromkeys(urls))  # deduplicate, preserve order

    if not urls:
        console.print("[yellow]No valid domains found in file.[/yellow]")
        return

    console.print(
        f"[bold cyan]Domain mode[/bold cyan] — {len(urls)} domains from [cyan]{domains_file}[/cyan]"
        + (f" | backend: [magenta]{backend}[/magenta]")
        + (f" | MX validation: {'on' if check_mx else '[yellow]off[/yellow]'}")
    )

    crawl_dir = CRAWL_DIR
    if fresh and os.path.isdir(crawl_dir):
        shutil.rmtree(crawl_dir)
        console.print(f"[dim]Cleared crawl checkpoint: {crawl_dir}[/dim]")

    query_label = f"domains:{os.path.basename(domains_file)}"

    display = LiveDisplay(query=query_label, total_urls=len(urls), backend=backend)
    with display:
        display.log(f"[bold]Domain crawl[/bold] — {len(urls)} targets loaded")
        await _crawl_urls(
            urls=urls,
            output_file=output_file,
            crawl_dir=crawl_dir,
            query_label=query_label,
            backend=backend,
            display=display,
            check_mx=check_mx,
        )

    stats = mx_cache_stats()
    if stats["cached_domains"]:
        console.print(
            f"\nMX cache: {stats['cached_domains']} domains checked — "
            f"[green]{stats['with_mx']} valid[/green], [red]{stats['without_mx']} no MX[/red]"
        )

async def run(
    base_query: str | None,
    engine: str = "google",
    expand_locations: bool = False,
    locations: list[str] | None = None,
    fresh: bool = False,
    no_variants: bool = False,
    backend: str = "scrapling",
    output_file: str = OUTPUT_FILE,
    check_mx: bool = True,
    use_vpn: bool = False,
    on_update: Optional[Callable] = None,
    on_log: Optional[Callable] = None,
):
    # Initialize VPN scraper if requested
    vpn_scraper = None
    if use_vpn:
        try:
            from vpn_rotator import SmartScraper
            console.print("[cyan]Initializing VPN rotation...[/cyan]")
            vpn_scraper = SmartScraper(auto_vpn=True)
            console.print(f"[green]✓ VPN connected: {vpn_scraper.vpn.get_current_ip()}[/green]")
            
            # Set VPN scraper in search modules
            from scrapers import google_scraper, ddg_scraper
            google_scraper.set_vpn_scraper(vpn_scraper)
            ddg_scraper.set_vpn_scraper(vpn_scraper)
        except Exception as e:
            console.print(f"[red]VPN initialization failed: {e}[/red]")
            console.print("[yellow]Continuing without VPN...[/yellow]")
            use_vpn = False

    try:
        if fresh and os.path.isdir(CRAWL_DIR):
            shutil.rmtree(CRAWL_DIR)
            console.print(f"[dim]Cleared crawl checkpoint: {CRAWL_DIR}[/dim]")

        loc_list = locations or LOCATION_EXPAND_LIST

        if base_query:
            queries = build_queries(base_query, expand_locations, loc_list, no_variants)
        else:
            queries = DEFAULT_QUERIES

        vpn_status = "on" if use_vpn else "off"
        console.print(f"Running [bold]{len(queries)}[/bold] search queries (engine: [cyan]{engine}[/cyan], backend: [magenta]{backend}[/magenta], MX: {'on' if check_mx else '[yellow]off[/yellow]'}, VPN: [cyan]{vpn_status}[/cyan])...")

        sem = asyncio.Semaphore(2)

        async def task_with_jitter(query: str, delay: float) -> list[str]:
            await asyncio.sleep(delay)
            return await get_urls_for_query_async(query, engine, sem)

        tasks = [task_with_jitter(q, i * 6.0) for i, q in enumerate(queries)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_urls: list[str] = []
        failed_queries = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                console.print(f"[red]Query failed: {queries[i]} — {result}[/red]")
                failed_queries += 1
            else:
                all_urls.extend(result)

        all_urls = list(set(all_urls))
        console.print(f"Total unique URLs: [bold green]{len(all_urls)}[/bold green] (failed queries: {failed_queries})")

        # Auto-fallback to DDG if Google failed badly
        if len(all_urls) < 10 and engine == "google" and failed_queries > 0:
            console.print("[yellow]Google failed significantly, falling back to DDG...[/yellow]")
            engine = "ddg"
            tasks = [task_with_jitter(q, i * 3.0) for i, q in enumerate(queries)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if not isinstance(result, Exception):
                    all_urls.extend(result)
            all_urls = list(set(all_urls))
            console.print(f"After DDG fallback: [bold]{len(all_urls)}[/bold] unique URLs")

        if not all_urls:
            console.print("[red]No URLs found. Try --engine ddg if Google is blocking requests.[/red]")
            return

        query_label = base_query or ", ".join(DEFAULT_QUERIES[:2]) + ", ..."

        display = LiveDisplay(
            query=query_label,
            total_urls=len(all_urls),
            backend=backend,
            on_update=on_update,
            on_log=on_log,
        )

        with display:
            display.log(f"[bold]Search complete[/bold] — [green]{len(all_urls)}[/green] URLs to crawl")
            await _crawl_urls(
                urls=all_urls,
                output_file=output_file,
                crawl_dir=CRAWL_DIR,
                query_label=query_label,
                backend=backend,
                display=display,
                check_mx=check_mx,
            )

        stats = mx_cache_stats()
        if stats["cached_domains"] and check_mx:
            console.print(
                f"\nMX cache: {stats['cached_domains']} domains — "
                f"[green]{stats['with_mx']} valid[/green], [red]{stats['without_mx']} no MX[/red]"
            )
    finally:
        # Clean up VPN connection
        if vpn_scraper:
            console.print("[cyan]Disconnecting VPN...[/cyan]")
            vpn_scraper.close()
            console.print("[green]✓ VPN disconnected[/green]")


# ---------------------------------------------------------------------------
# Unified crawl dispatcher — scrapling or playwright
# ---------------------------------------------------------------------------

async def _crawl_urls(
    urls: list[str],
    output_file: str,
    crawl_dir: str,
    query_label: str,
    backend: str,
    display: LiveDisplay,
    check_mx: bool = True,
):
    if backend == "playwright":
        await _crawl_playwright(urls, output_file, query_label, display, check_mx=check_mx)
    else:
        await _crawl_scrapling(urls, output_file, crawl_dir, query_label, display, check_mx=check_mx)


async def _crawl_scrapling(
    urls: list[str],
    output_file: str,
    crawl_dir: str,
    query_label: str,
    display: LiveDisplay,
    check_mx: bool = True,
):
    spider = EmailSpider(
        start_urls=urls,
        output_file=output_file,
        crawldir=crawl_dir,
        concurrent_requests=CONCURRENT_REQUESTS,
        query_label=query_label,
        live_display=display,
        check_mx=check_mx,
    )

    _sigint_count = 0
    _original_sigint = signal.getsignal(signal.SIGINT)

    def _handle_sigint(signum, frame):
        nonlocal _sigint_count
        _sigint_count += 1
        if _sigint_count == 1:
            display.log("[yellow]Ctrl+C — stopping gracefully...[/yellow]")
            spider.request_stop()
        else:
            raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        result = await asyncio.to_thread(spider.start)
        total = spider._csv_total_at_start + spider._session_saved
        display.log(
            f"[bold green]Done.[/bold green] {spider._session_saved} new emails "
            f"({total} total) — {os.path.abspath(output_file)}"
        )
    except KeyboardInterrupt:
        total = spider._csv_total_at_start + spider._session_saved
        display.log(f"[yellow]Stopped.[/yellow] {spider._session_saved} new emails ({total} total).")
    finally:
        signal.signal(signal.SIGINT, _original_sigint)


async def _crawl_playwright(
    urls: list[str],
    output_file: str,
    query_label: str,
    display: LiveDisplay,
    check_mx: bool = True,
):
    try:
        from engine.playwright_pool import PlaywrightPool
        from scrapers.playwright_crawler import PlaywrightEmailCrawler
    except ImportError:
        console.print("[red]Playwright backend requires: pip install playwright && playwright install chromium[/red]")
        return

    display.log(f"[magenta]Playwright backend[/magenta] — {PLAYWRIGHT_CRAWL_WORKERS} parallel browser contexts")

    _original_sigint = signal.getsignal(signal.SIGINT)
    crawler_ref: PlaywrightEmailCrawler | None = None
    _sigint_count = 0

    def _handle_sigint(signum, frame):
        nonlocal _sigint_count
        _sigint_count += 1
        if _sigint_count == 1:
            display.log("[yellow]Ctrl+C — stopping gracefully...[/yellow]")
            if crawler_ref:
                crawler_ref.request_stop()
        else:
            raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        async with PlaywrightPool(max_workers=PLAYWRIGHT_CRAWL_WORKERS, headless=PLAYWRIGHT_HEADLESS) as pool:
            crawler = PlaywrightEmailCrawler(
                pool, output_file, query_label=query_label,
                live_display=display, check_mx=check_mx,
            )
            crawler_ref = crawler
            await crawler.crawl(urls)

        total = crawler._csv_total_at_start + crawler._session_saved
        display.log(
            f"[bold green]Done.[/bold green] {crawler._session_saved} new emails "
            f"({total} total) — {os.path.abspath(output_file)}"
        )
    except KeyboardInterrupt:
        total = crawler._csv_total_at_start + crawler._session_saved
        display.log(f"[yellow]Stopped.[/yellow] {crawler._session_saved} new emails ({total} total).")
    finally:
        signal.signal(signal.SIGINT, _original_sigint)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Email scraper — search Google/DDG, crawl results, extract emails.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "dental clinics london"
  python main.py "therapy clinics" --engine ddg
  python main.py "clinics" --expand-locations --locations london manchester birmingham
  python main.py "law firms new york" --backend playwright
  python main.py --gmaps "dental clinics london"
  python main.py --gmaps-emails "dental clinics london"
  python main.py --gmaps-emails "dental clinics london" --from-existing
        """,
    )

    parser.add_argument("query", nargs="?", default=None, help="Search query")

    # Domain-targeted mode
    parser.add_argument("--domains", default=None, metavar="FILE", help="Path to a .txt file of domains/URLs to crawl directly (skips search phase)")

    # Search options
    parser.add_argument("--engine", default="google", choices=["google", "ddg"], help="Search engine (default: google)")
    parser.add_argument("--pages", type=int, default=PAGES_TO_SCRAPE, help=f"Search result pages per query (default: {PAGES_TO_SCRAPE})")
    parser.add_argument("--no-variants", action="store_true", help="Search plain query only, no keyword variants")
    parser.add_argument("--expand-locations", action="store_true", help="Expand query across locations (use with --locations)")
    parser.add_argument("--locations", nargs="+", default=None, metavar="LOCATION", help="Locations to expand query across, e.g. --locations london manchester paris")

    # Crawl backend
    parser.add_argument("--backend", default="scrapling", choices=["scrapling", "playwright"], help="Crawl backend (default: scrapling). Use playwright for JS-heavy sites.")

    # Output
    parser.add_argument("--output", default=None, help="Output CSV file (default: output/emails.csv)")
    parser.add_argument("--fresh", action="store_true", help="Clear saved crawl checkpoint and start over")
    parser.add_argument("--no-mx", action="store_true", help="Skip MX record validation (faster but includes dead domains)")
    parser.add_argument("--vpn", action="store_true", help="Enable automatic VPN rotation on rate limits (requires OpenVPN)")

    # Google Maps modes
    parser.add_argument("--gmaps", action="store_true", help="Scrape Google Maps for business name, phone, website")
    parser.add_argument("--gmaps-emails", action="store_true", help="Scrape Google Maps then crawl websites for emails")
    parser.add_argument("--from-existing", action="store_true", help="Skip Maps scraping, use existing businesses CSV (with --gmaps-emails)")
    parser.add_argument("--businesses", default=None, help="Businesses CSV path for --gmaps-emails (default: output/businesses.csv)")
    parser.add_argument("--scrolls", type=int, default=GMAPS_MAX_SCROLLS, help=f"Maps feed scroll count (default: {GMAPS_MAX_SCROLLS})")

    # Playwright tuning
    parser.add_argument("--search-workers", type=int, default=PLAYWRIGHT_SEARCH_WORKERS, help=f"Playwright search workers (default: {PLAYWRIGHT_SEARCH_WORKERS})")
    parser.add_argument("--crawl-workers", type=int, default=PLAYWRIGHT_CRAWL_WORKERS, help=f"Playwright crawl workers (default: {PLAYWRIGHT_CRAWL_WORKERS})")
    parser.add_argument("--headed", action="store_true", help="Show browser windows (disables headless)")

    args = parser.parse_args()

    output_file = args.output or OUTPUT_FILE
    check_mx = not args.no_mx

    if args.headed:
        import config as _cfg
        _cfg.PLAYWRIGHT_HEADLESS = False

    if args.domains:
        asyncio.run(run_domains(
            domains_file=args.domains,
            output_file=output_file,
            backend=args.backend,
            fresh=args.fresh,
            check_mx=check_mx,
        ))

    elif args.gmaps_emails:
        businesses_file = args.businesses or GMAPS_OUTPUT_FILE
        emails_file = output_file if args.output else GMAPS_EMAILS_OUTPUT_FILE
        asyncio.run(run_gmaps_emails(
            args.query,
            args.scrolls,
            businesses_file,
            emails_file,
            args.fresh,
            args.from_existing,
            args.backend,
            check_mx,
        ))

    elif args.gmaps:
        asyncio.run(run_gmaps(args.query, args.scrolls, output_file if args.output else GMAPS_OUTPUT_FILE))

    else:
        asyncio.run(run(
            base_query=args.query,
            engine=args.engine,
            expand_locations=args.expand_locations,
            locations=args.locations,
            fresh=args.fresh,
            no_variants=args.no_variants,
            backend=args.backend,
            output_file=output_file,
            check_mx=check_mx,
            use_vpn=args.vpn,
        ))
