import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

KEYWORD_VARIANTS = ["email", "info", "about", "support", "contact"]
TARGET_EMAIL_COUNT = 50000     # Increased from 100 to 50k
MAX_PAGES_TO_CRAWL = 500       # Stop after this many pages (prevents infinite loops)
MAX_CRAWL_DEPTH = 2            # Max link-hops from each search result
PAGES_TO_SCRAPE = 20          # Reduced from 50 to avoid rate limiting
CONCURRENT_REQUESTS = 32        # Increased from 16 to 32
OUTPUT_FILE = os.path.join(BASE_DIR, "output", "emails.csv")
CRAWL_DIR = os.path.join(BASE_DIR, "crawl_data")    # for pause/resume
USE_STEALTH = True            # toggle StealthyFetcher vs Fetcher
MIN_URLS_BEFORE_CRAWL = 50

# Location-based expansion for UK queries
UK_LOCATIONS = [
    "london", "manchester", "birmingham", "leeds", "glasgow",
    "edinburgh", "bristol", "liverpool", "sheffield", "newcastle",
    "nottingham", "leicester", "brighton", "cardiff", "belfast"
]

DEFAULT_QUERIES = [
    'private clinics in uk "email"',
    'dental practice uk "contact"',
    'physiotherapy clinic london "info"',
    'GP surgery private uk "email"',
    'aesthetic clinic uk "contact"',
]
