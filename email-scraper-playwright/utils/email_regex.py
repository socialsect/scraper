import html
import re

EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9][a-zA-Z0-9._%+\-]*[a-zA-Z0-9]@[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)+',
    re.IGNORECASE,
)

BLACKLIST_PATTERNS = [
    r'@sentry',
    r'@.*\.(png|jpe?g|gif|webp|svg|ico|bmp|tiff?|woff2?|ttf|eot|css|js|map|pdf|zip)$',
    r'\.(png|jpe?g|gif|webp|svg|ico|woff2?|ttf|css|js)$',
    r'@2x\.',
    r'@.*\d+x\d+',
    r'logo@',
    r'-logo@',
    r'^u003e',
    r'^%20',
    r'^t[a-z]+@',
    r'example\.com$',
    r'sample\.com$',
    r'email\.com$',
    r'address\.com$',
    r'domain\.com$',
    r'yoursite\.com$',
    r'company\.com$',
    r'placeholder',
    r'noreply',
    r'no-reply',
    r'donotreply',
    r'do-not-reply',
    r'mailer-daemon',
    r'postmaster@',
    r'test@test',
    r'name@',
    r'user@',
    r'your@',
    r'you@',
    r'@webform\.',
    r'@error-tracking\.',
    r'@.*\.boxly\.ai$',
    r'@.*\.reddit\.com$',
    r'@wixpress\.com$',
    r'@sentry\.io$',
    r'@newsletters?\.',
    r'@.*hash',
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}@',
    r'^[0-9a-f]{16,}@',
]

BLOCKED_DOMAIN_PARTS = (
    'sentry',
    'wixpress',
    'error-tracking',
    'webform',
    'boxly.ai',
    'placeholder',
    'example',
    'sample',
)

def _normalize_email(email: str) -> str:
    email = html.unescape(email or '').strip().lower()
    email = email.strip('.,;:!?()[]{}"\'<>')
    return email


def _split_email(email: str) -> tuple[str, str] | None:
    if email.count('@') != 1:
        return None
    local, domain = email.split('@', 1)
    if not local or not domain:
        return None
    return local, domain


def is_valid_email(email: str) -> bool:
    email = _normalize_email(email)

    if any(re.search(p, email) for p in BLACKLIST_PATTERNS):
        return False

    parts = _split_email(email)
    if not parts:
        return False

    local, domain = parts

    if len(local) < 2 or len(local) > 64:
        return False

    if len(domain) < 4 or len(domain) > 255:
        return False

    if local.startswith('.') or local.endswith('.') or '..' in local:
        return False

    if domain.startswith('.') or domain.endswith('.') or '..' in domain:
        return False

    if not re.match(r'^[a-z0-9][a-z0-9._%+\-]*[a-z0-9]$', local) and not re.match(r'^[a-z0-9]$', local):
        return False

    if not re.match(
        r'^[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?)+$',
        domain,
    ):
        return False

    if any(part in BLOCKED_DOMAIN_PARTS for part in domain.split('.')):
        return False

    tld = domain.rsplit('.', 1)[-1]
    if len(tld) < 2 or len(tld) > 24:
        return False

    if not tld.isalpha():
        return False

    if re.fullmatch(r'[0-9a-f]{16,}', local):
        return False

    if re.fullmatch(r'[0-9]{6,}', local):
        return False

    return True


def extract_emails_from_html(html_content: str) -> set[str]:
    raw_html = html.unescape(html_content or '')
    found = set(EMAIL_PATTERN.findall(raw_html))

    for match in re.finditer(
        r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})',
        raw_html,
        re.IGNORECASE,
    ):
        found.add(match.group(1))

    return {
        _normalize_email(e)
        for e in found
        if is_valid_email(_normalize_email(e))
    }
