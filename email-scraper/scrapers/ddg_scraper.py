import urllib.parse

from scrapling.fetchers import FetcherSession

# Global VPN scraper instance (set by main.py when --vpn flag is used)
_vpn_scraper = None

def set_vpn_scraper(scraper):
    """Set global VPN scraper instance for rotation on rate limits."""
    global _vpn_scraper
    _vpn_scraper = scraper


def build_ddg_url(query: str) -> str:
    return f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"


def get_result_urls_ddg(query: str, pages: int = 5) -> list[str]:
    urls: list[str] = []

    # If VPN scraper is available, use it for rotation on rate limits
    if _vpn_scraper:
        first_url = build_ddg_url(query)
        html = _vpn_scraper.get(first_url)
        if not html:
            print(f"[!] Failed to fetch DDG page 1 for query: {query}")
            return []
        
        from scrapling import Adaptor
        page = Adaptor(html, first_url)

        for page_num in range(pages):
            links = page.css('.result__a::attr(href)').getall()
            print(f"DDG Page {page_num + 1}: Found {len(links)} links")

            urls.extend(
                link for link in links
                if link and link.startswith("http") and 'duckduckgo' not in link
            )

            next_form = page.css('form[action="/html/"]')
            if not next_form:
                print("No next page form found")
                break

            inputs = {
                inp.css("::attr(name)").get(): inp.css("::attr(value)").get()
                for inp in next_form.css("input")
            }
            inputs = {k: v for k, v in inputs.items() if k}

            if not inputs.get("s"):
                print("No pagination token found")
                break

            # POST with VPN scraper (note: this may not work perfectly, DDG is tricky)
            # For now, fall back to non-VPN for pagination
            print("[!] DDG pagination with VPN not fully supported, stopping at page 1")
            break
    else:
        # Original logic without VPN
        with FetcherSession(
            impersonate="chrome",
            stealthy_headers=True
        ) as session:

            page = session.get(build_ddg_url(query))

            for page_num in range(pages):
                links = page.css('.result__a::attr(href)').getall()

                print(f"DDG Page {page_num + 1}: Found {len(links)} links")

                urls.extend(
                    link for link in links
                    if link and link.startswith("http") and 'duckduckgo' not in link
                )

                next_form = page.css('form[action="/html/"]')

                if not next_form:
                    print("No next page form found")
                    break

                inputs = {
                    inp.css("::attr(name)").get(): inp.css("::attr(value)").get()
                    for inp in next_form.css("input")
                }

                inputs = {k: v for k, v in inputs.items() if k}

                if not inputs.get("s"):
                    print("No pagination token found")
                    break

                page = session.post(
                    "https://html.duckduckgo.com/html/",
                    data=inputs
                )

    unique_urls = list(set(urls))
    print(f"DDG Total unique URLs: {len(unique_urls)}")
    return unique_urls