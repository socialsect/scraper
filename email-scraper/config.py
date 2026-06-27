import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

KEYWORD_VARIANTS = ["email", "info", "about", "support", "contact"]
TARGET_EMAIL_COUNT = 50000
MAX_PAGES_TO_CRAWL = 500
MAX_CRAWL_DEPTH = 2
PAGES_TO_SCRAPE = 20
CONCURRENT_REQUESTS = 32
OUTPUT_FILE = os.path.join(BASE_DIR, "output", "emails.csv")
GMAPS_OUTPUT_FILE = os.path.join(BASE_DIR, "output", "businesses.csv")
GMAPS_EMAILS_OUTPUT_FILE = os.path.join(BASE_DIR, "output", "gmaps_emails.csv")
CRAWL_DIR = os.path.join(BASE_DIR, "crawl_data")
GMAPS_MAX_SCROLLS = 15
GMAPS_SCROLL_DELAY = 2.0
GMAPS_DETAIL_DELAY = 1.5
USE_STEALTH = True
MIN_URLS_BEFORE_CRAWL = 50

# Playwright backend settings
PLAYWRIGHT_SEARCH_WORKERS = 6
PLAYWRIGHT_CRAWL_WORKERS = 8
PLAYWRIGHT_HEADLESS = True
SEARCH_PAGE_DELAY = (1.0, 2.0)
CRAWL_PAGE_DELAY = (0.3, 0.8)

# Location expansion — generic, not UK-specific
# Override via --locations flag or set your own list here
LOCATION_EXPAND_LIST: list[str] = []

# Default queries — generic starting points, override with positional arg
DEFAULT_QUERIES = [
    'contact email',
    'business email contact',
    'company info email',
]

# Proxy support
# Set via --proxy http://user:pass@host:port or --proxy-file proxies.txt
PROXY = None  # Current proxy
PROXY_LIST: list[str] = []  # List for rotation

# VPN / IP Rotation Configuration
VPN_ENABLED = False                    # Set True to enable auto VPN rotation
VPN_ROTATE_AFTER = 3                   # Rotate after N successful requests
VPN_PREFERRED_COUNTRIES = ["US", "GB", "DE", "NL"]  # ISO country codes
