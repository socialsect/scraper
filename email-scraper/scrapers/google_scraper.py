import urllib.parse

from scrapling.fetchers import StealthySession

# Global VPN scraper instance (set by main.py when --vpn flag is used)
_vpn_scraper = None

def set_vpn_scraper(scraper):
    """Set global VPN scraper instance for rotation on rate limits."""
    global _vpn_scraper
    _vpn_scraper = scraper


def build_google_url(query: str, page: int) -> str:
    encoded = urllib.parse.quote_plus(query)
    start = page * 10
    return f"https://www.google.com/search?q={encoded}&start={start}"


def _extract_result_urls(page_obj) -> list[str]:
    urls: list[str] = []

    for selector in (
        'a[jsname]::attr(href)',
        'div.g a::attr(href)',
        'a[href^="http"]::attr(href)',
    ):
        links = page_obj.css(selector).getall()
        for link in links:
            if link.startswith('http') and 'google.com' not in link:
                urls.append(link)

    return urls


def get_result_urls_google(query: str, pages: int = 10) -> list[str]:
    urls: list[str] = []

    # If VPN scraper is available, use it for rotation on rate limits
    if _vpn_scraper:
        for page in range(pages):
            url = build_google_url(query, page)
            html = _vpn_scraper.get(url)
            if html:
                # Parse HTML manually since we're using VPN scraper
                from scrapling import Adaptor
                page_obj = Adaptor(html, url)
                urls.extend(_extract_result_urls(page_obj))
            else:
                print(f"[!] Failed to fetch page {page+1} for query: {query}")
    else:
        # Original logic without VPN
        with StealthySession(headless=True, solve_cloudflare=True) as session:
            for page in range(pages):
                url = build_google_url(query, page)
                page_obj = session.fetch(url, google_search=True)
                urls.extend(_extract_result_urls(page_obj))

    return list(set(urls))
