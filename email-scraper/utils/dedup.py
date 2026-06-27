from utils.email_regex import is_valid_email

_ENRICHMENT_KEYS = ("source", "phone", "linkedin", "twitter", "instagram", "facebook", "youtube", "mx_valid", "confidence")


def deduplicate_items(items: list[dict]) -> list[dict]:
    """
    Deduplicate on email address. Preserves the first occurrence.
    Carries all enrichment columns through unchanged.
    """
    seen: set[str] = set()
    result: list[dict] = []

    for item in items:
        email = (item.get("email") or "").lower().strip()
        if not email or not is_valid_email(email) or email in seen:
            continue
        seen.add(email)
        row = {"email": email}
        for key in _ENRICHMENT_KEYS:
            row[key] = (item.get(key) or "").strip()
        result.append(row)

    return result
