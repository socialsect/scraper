import urllib.parse

from scrapling.fetchers import FetcherSession


def build_ddg_url(query: str) -> str:
    return f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"


def get_result_urls_ddg(query: str, pages: int = 5) -> list[str]:
    urls: list[str] = []

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