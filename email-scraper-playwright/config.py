import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

KEYWORD_VARIANTS = ["email", "info", "about", "support", "contact"]
TARGET_EMAIL_COUNT = 50000
MAX_PAGES_TO_CRAWL = 500
MAX_CRAWL_DEPTH = 2
PAGES_TO_SCRAPE = 30
OUTPUT_FILE = os.path.join(BASE_DIR, "output", "emails.csv")
CRAWL_DIR = os.path.join(BASE_DIR, "crawl_data")

# Playwright concurrency
PLAYWRIGHT_SEARCH_WORKERS = 6   # one browser context per search query variant
PLAYWRIGHT_CRAWL_WORKERS = 8    # parallel tabs/contexts for page crawling
PLAYWRIGHT_HEADLESS = True
SEARCH_PAGE_DELAY = (1.0, 2.0)  # random delay range between Google result pages
CRAWL_PAGE_DELAY = (0.3, 0.8)   # random delay between crawl requests

UK_LOCATIONS = [
    "london", "manchester", "birmingham", "leeds", "glasgow",
    "edinburgh", "bristol", "liverpool", "sheffield", "newcastle",
    "nottingham", "leicester", "brighton", "cardiff", "belfast",
]

DEFAULT_QUERIES = [
    'private clinics in uk "email"',
    'dental practice uk "contact"',
    'physiotherapy clinic london "info"',
    'GP surgery private uk "email"',
    'aesthetic clinic uk "contact"',
]
