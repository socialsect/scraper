"""Async MX record validation with an in-process domain cache."""

from __future__ import annotations

import asyncio
from functools import lru_cache

# Cache: domain -> bool  (True = has MX records)
_mx_cache: dict[str, bool] = {}
_cache_lock = asyncio.Lock()


async def has_mx_record(domain: str) -> bool:
    """
    Return True if `domain` has at least one MX record.
    Results are cached so each domain is only queried once per process.
    Requires: pip install dnspython
    """
    domain = domain.lower().strip().rstrip(".")

    async with _cache_lock:
        if domain in _mx_cache:
            return _mx_cache[domain]

    result = await asyncio.to_thread(_check_mx_sync, domain)

    async with _cache_lock:
        _mx_cache[domain] = result

    return result


def _check_mx_sync(domain: str) -> bool:
    try:
        import dns.resolver  # type: ignore

        answers = dns.resolver.resolve(domain, "MX", lifetime=5.0)
        return len(answers) > 0
    except Exception:
        # NXDOMAIN, NoAnswer, Timeout, no dnspython installed — treat as invalid
        return False


async def validate_email_mx(email: str) -> bool:
    """Convenience wrapper — extract domain from email and check MX."""
    try:
        domain = email.split("@", 1)[1]
    except IndexError:
        return False
    return await has_mx_record(domain)


def mx_cache_stats() -> dict[str, int]:
    total = len(_mx_cache)
    valid = sum(1 for v in _mx_cache.values() if v)
    return {"cached_domains": total, "with_mx": valid, "without_mx": total - valid}
