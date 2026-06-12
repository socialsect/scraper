import urllib.parse

from scrapling.fetchers import StealthySession


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

    with StealthySession(headless=True, solve_cloudflare=True) as session:
        for page in range(pages):
            url = build_google_url(query, page)
            page_obj = session.fetch(url, google_search=True)
            urls.extend(_extract_result_urls(page_obj))

    return list(set(urls))
