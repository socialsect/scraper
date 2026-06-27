"""Phone number extraction from HTML content and tel: links."""

from __future__ import annotations

import html
import re

# Matches common international and local formats:
#   +1 (800) 555-0100   |   +44 20 7946 0958   |   (800) 555-0100
#   800-555-0100        |   0800 555 0100       |   +353 1 234 5678
_PHONE_PATTERN = re.compile(
    r"""
    (?<![0-9@\w])           # not preceded by digit/email char
    (
        (?:\+\d{1,3}[\s\-.]?)?          # optional country code  +1 / +44
        (?:\(?\d{2,4}\)?[\s\-.]?)       # area code  (800) / 800
        \d{3,4}[\s\-.]?\d{3,4}          # main number  555-0100
        (?:[\s\-.]?\d{1,5})?            # optional extension
    )
    (?![0-9])               # not followed by digit
    """,
    re.VERBOSE,
)

# Minimum digits a match must contain to count as a phone number
_MIN_DIGITS = 7
# Maximum digits — avoids matching long ID numbers
_MAX_DIGITS = 15


def _digit_count(s: str) -> int:
    return sum(c.isdigit() for c in s)


def _looks_like_version(s: str) -> bool:
    """Filter out version strings like 1.0.0 or 12.3.4."""
    return bool(re.fullmatch(r"\d+\.\d+(?:\.\d+)*", s.strip()))


def extract_phones_from_html(html_content: str) -> list[str]:
    """
    Return a deduplicated list of phone number strings found in HTML.
    Extracts from tel: links first (highest confidence), then regex fallback.
    """
    raw = html.unescape(html_content or "")
    seen: set[str] = set()
    results: list[str] = []

    # tel: href links — most reliable source
    # Capture everything between tel: and the closing quote (number can contain spaces)
    for match in re.finditer(r'''href=["']tel:\s*([^"']+)["']''', raw, re.IGNORECASE):
        phone = _clean(match.group(1))
        if phone and phone not in seen:
            seen.add(phone)
            results.append(phone)

    # Regex scan over visible text portions (strip tags first for cleaner matches)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)

    for match in _PHONE_PATTERN.finditer(text):
        candidate = match.group(1).strip()
        if _looks_like_version(candidate):
            continue
        dc = _digit_count(candidate)
        if dc < _MIN_DIGITS or dc > _MAX_DIGITS:
            continue
        phone = _clean(candidate)
        if phone and phone not in seen:
            seen.add(phone)
            results.append(phone)

    return results


def _clean(phone: str) -> str:
    """Normalise whitespace/punctuation but preserve leading +."""
    phone = phone.strip().strip(".,;:")
    # Collapse internal whitespace
    phone = re.sub(r"\s+", " ", phone)
    return phone if _digit_count(phone) >= _MIN_DIGITS else ""


def extract_phone_from_tel_links(tel_hrefs: list[str]) -> list[str]:
    """Given a list of raw tel: href values, return cleaned phone strings."""
    results: list[str] = []
    seen: set[str] = set()
    for raw in tel_hrefs:
        phone = _clean(raw.replace("tel:", "").strip())
        if phone and phone not in seen:
            seen.add(phone)
            results.append(phone)
    return results
