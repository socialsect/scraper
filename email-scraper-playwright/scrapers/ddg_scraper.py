import time
import urllib.parse

from scrapling.fetchers import FetcherSession


def build_ddg_url(query: str) -> str:
    return f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"


def unwrap_ddg_url(link: str) -> str | None:
    """Extract the real destination URL from DDG redirect links."""
    if not link:
        return None

    link = link.strip()
    if link.startswith("//"):
        link = "https:" + link
    if link.startswith("/l/"):
        link = "https://duckduckgo.com" + link

    if "duckduckgo.com/l/" in link or "/l/?" in link:
        parsed = urllib.parse.urlparse(link)
        params = urllib.parse.parse_qs(parsed.query)
        uddg = params.get("uddg", [None])[0]
        if uddg:
            return urllib.parse.unquote(uddg)
        return None

    if link.startswith("http") and "duckduckgo" not in link:
        return link

    return None


def _extract_links(page) -> list[str]:
    urls: list[str] = []
    for href in page.css(".result__a::attr(href)").getall():
        real = unwrap_ddg_url(href)
        if real and real.startswith("http"):
            urls.append(real)
    return urls


def get_result_urls_ddg(query: str, pages: int = 5, delay: float = 1.5) -> list[str]:
    urls: list[str] = []

    with FetcherSession(
        impersonate="chrome",
        stealthy_headers=True,
    ) as session:
        page = session.get(build_ddg_url(query))
        status = getattr(page, "status", 200)

        if status == 202:
            print(f"DDG rate-limited (202) for: {query[:50]}")
            time.sleep(3)
            page = session.get(build_ddg_url(query))

        for page_num in range(pages):
            links = _extract_links(page)
            print(f"DDG [{query[:40]}] page {page_num + 1}: {len(links)} links")

            urls.extend(links)

            next_form = page.css('form[action="/html/"]')
            if not next_form:
                break

            inputs = {
                inp.css("::attr(name)").get(): inp.css("::attr(value)").get()
                for inp in next_form.css("input")
            }
            inputs = {k: v for k, v in inputs.items() if k}

            if not inputs.get("s"):
                break

            time.sleep(delay)
            page = session.post("https://html.duckduckgo.com/html/", data=inputs)

    unique_urls = list(set(urls))
    print(f"DDG [{query[:40]}] total: {len(unique_urls)} unique URLs")
    return unique_urls
