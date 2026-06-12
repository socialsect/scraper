from utils.email_regex import is_valid_email


def deduplicate_items(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []

    for item in items:
        email = (item.get("email") or "").lower().strip()
        if not email or not is_valid_email(email) or email in seen:
            continue
        seen.add(email)
        result.append({"email": email, "source": item.get("source", "")})

    return result
