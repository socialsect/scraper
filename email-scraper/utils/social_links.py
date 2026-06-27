"""Extract social media profile links from a page's anchor tags."""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Each entry: (key, pattern_that_must_match_the_href)
# We intentionally skip personal profile paths and only keep company/brand pages.
_SOCIAL_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "linkedin",
        re.compile(
            r"linkedin\.com/(company|school|organization|showcase)/[^\"'\s/>?#]+",
            re.IGNORECASE,
        ),
    ),
    (
        "twitter",
        re.compile(
            # twitter.com/handle  OR  x.com/handle — skip /home /search /intent etc.
            r"(?:twitter\.com|x\.com)/(?!home|search|intent|share|hashtag|explore|settings|i/)([A-Za-z0-9_]{1,50})(?:[/?#]|$)",
            re.IGNORECASE,
        ),
    ),
    (
        "instagram",
        re.compile(
            r"instagram\.com/(?!p/|reel/|stories/|explore/)([A-Za-z0-9_.]{1,30})(?:[/?#]|$)",
            re.IGNORECASE,
        ),
    ),
    (
        "facebook",
        re.compile(
            r"facebook\.com/(?!sharer|share|login|dialog|permalink|photo|video|events|groups|watch|marketplace|pages/create)([A-Za-z0-9.\-]{3,})(?:[/?#]|$)",
            re.IGNORECASE,
        ),
    ),
    (
        "youtube",
        re.compile(
            r"youtube\.com/(?:c/|channel/|@)([A-Za-z0-9_\-]{1,100})(?:[/?#]|$)",
            re.IGNORECASE,
        ),
    ),
]

# Domains that should never be returned as a social link
_BLOCKLIST = {
    "google.com", "googletagmanager.com", "googleapis.com",
    "goo.gl", "bit.ly", "t.co", "ow.ly",
}


def _is_blocked(url: str) -> bool:
    try:
        host = urlparse(url.lower()).netloc.lstrip("www.")
        return host in _BLOCKLIST
    except Exception:
        return False


def extract_social_links(hrefs: list[str]) -> dict[str, str]:
    """
    Given a list of href strings from a page, return a dict of
    {platform: first_matching_url} for each detected social network.

    Only the first match per platform is kept (the most prominent link).
    """
    found: dict[str, str] = {}

    for href in hrefs:
        if not href or not href.startswith("http"):
            continue
        if _is_blocked(href):
            continue

        for key, pattern in _SOCIAL_PATTERNS:
            if key in found:
                continue
            if pattern.search(href):
                # Normalise: strip query params and fragments
                try:
                    p = urlparse(href)
                    clean = f"{p.scheme}://{p.netloc}{p.path}".rstrip("/")
                    found[key] = clean
                except Exception:
                    found[key] = href

    return found
