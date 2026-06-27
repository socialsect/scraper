"""
Confidence scoring for extracted emails.

Scoring:
  3 — mailto: link on a contact page (explicit)
  2 — regex match in visible text (high confidence)
  1 — match in script/obfuscated content (low confidence)
"""

import re
from typing import Optional


def score_from_source(
    email: str,
    html: str,
    url: str = "",
    visible_text: str = "",
) -> int:
    """
    Score email based on where it was found.
    
    Returns confidence: 1 (low), 2 (medium), 3 (high)
    """
    
    # mailto: link (highest confidence)
    if _found_in_mailto(email, html):
        return 3
    
    # In visible text on contact/about page (high confidence)
    if _is_contact_page(url) and _found_in_visible_text(email, visible_text):
        return 3
    
    # In visible text anywhere (medium confidence)
    if _found_in_visible_text(email, visible_text):
        return 2
    
    # In HTML but not visible (low confidence)
    if email.lower() in html.lower():
        return 1
    
    # Default (shouldn't reach here)
    return 2


def _found_in_mailto(email: str, html: str) -> bool:
    """Check if email is in a mailto: link."""
    pattern = rf'href\s*=\s*["\']?mailto:([^"\'\s>]+)'
    matches = re.findall(pattern, html, re.IGNORECASE)
    
    email_lower = email.lower()
    for match in matches:
        if email_lower == match.lower():
            return True
    
    return False


def _is_contact_page(url: str) -> bool:
    """Check if URL looks like a contact page."""
    contact_keywords = ['contact', 'about', 'team', 'support', 'help']
    url_lower = url.lower()
    
    for keyword in contact_keywords:
        if keyword in url_lower:
            return True
    
    return False


def _found_in_visible_text(email: str, visible_text: str) -> bool:
    """Check if email appears in visible text."""
    return email.lower() in visible_text.lower()


def describe_confidence(score: int) -> str:
    """Human-readable confidence description."""
    descriptions = {
        1: "Low (obfuscated content)",
        2: "Medium (visible text)",
        3: "High (mailto link or contact page)",
    }
    return descriptions.get(score, "Unknown")
