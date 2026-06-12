from scrapling.fetchers import DynamicSession, FetcherSession

from utils.email_regex import extract_emails_from_html


def extract_emails_from_url(url: str, use_dynamic: bool = False) -> tuple[list[str], list[str]]:
    try:
        if use_dynamic:
            with DynamicSession(headless=True, network_idle=True) as session:
                page = session.fetch(url)
        else:
            with FetcherSession(impersonate='chrome', stealthy_headers=True) as session:
                page = session.get(url, timeout=15)

        emails: set[str] = set()

        emails.update(extract_emails_from_html(page.html_content))

        for mailto in page.css('a[href^="mailto:"]::attr(href)').getall():
            email = mailto.replace('mailto:', '').split('?')[0].strip()
            if '@' in email:
                emails.add(email.lower())

        contact_links = page.css('a[href*="contact"]::attr(href)').getall()
        return list(emails), contact_links[:2]

    except Exception as e:
        print(f"Failed {url}: {e}")
        return [], []
