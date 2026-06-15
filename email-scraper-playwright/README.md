# email-scraper-playwright

Email scraper that uses **real Playwright browsers** for Google search and page crawling. Slower and heavier than `email-scraper/`, but better when Google blocks plain HTTP requests.

**Default output:** `output/emails.csv`

---

## Setup

```bash
cd email-scraper-playwright
pip install -r requirements.txt
playwright install chromium
```

---

## Main scraper

```bash
# Default queries (built-in list in config.py)
python main.py

# Custom search query
python main.py "vascular surgery in us"

# Plain query only (no "email", "contact", etc. variants)
python main.py "therapy chicago" --no-variants

# Google only
python main.py "dental uk" --engine google

# DuckDuckGo only
python main.py "dental uk" --engine ddg

# Both Google + DDG (default)
python main.py "clinics london" --engine both

# Expand UK query across 15 cities
python main.py "private clinics in uk" --expand-locations

# Custom output file
python main.py "physio uk" --output output/my_run.csv

# Wipe checkpoint + output and start over
python main.py "clinics uk" --fresh

# Show browser windows (debug captcha / blocks)
python main.py "clinics uk" --headed

# Tune parallelism
python main.py "clinics uk" --search-workers 4 --crawl-workers 6

# More Google result pages per query
python main.py "clinics uk" --pages 40
```

### Flags

| Flag | Description |
|------|-------------|
| `query` | Optional search phrase. If omitted, uses `DEFAULT_QUERIES` from `config.py`. |
| `--engine` | `google`, `ddg`, or `both` (default: `both`) |
| `--output` | CSV path (default: `output/emails.csv`) |
| `--expand-locations` | Replace `uk` with 15 UK cities (+ variants unless `--no-variants`) |
| `--no-variants` | Search only the plain query (no quoted keyword suffixes) |
| `--fresh` | Delete `crawl_data/` and remove existing output CSV |
| `--search-workers` | Parallel browsers for Google (default: 6) |
| `--crawl-workers` | Parallel browsers for page crawl (default: 8) |
| `--pages` | Search result pages per query (default: 30) |
| `--headed` | Visible browser windows instead of headless |

### While it runs

**Phase 1** — search (Google and/or DDG) collects URLs.  
**Phase 2** — browsers crawl those URLs and follow contact/about links.

- Terminal shows **`[N new \| M total in CSV]`** on every saved email.
- Progress every 10 pages: pages crawled, queue size, totals.
- Each run adds a **`#QUERY`** marker row in the CSV before new emails.
- **Ctrl+C once** — graceful stop.
- **Ctrl+C twice** — force quit.

Unlike the Scrapling-based scraper, this version **finishes when the crawl queue is empty** (all seed URLs and discovered links processed). Run another query or increase `--pages` for more results.

### Two terminals, same CSV

Same as `email-scraper`: use the same `--output` in two terminals; both append with file locking.

---

## Utility scripts

```bash
# Clean invalid/blocked/duplicate rows (creates .bak backup)
python clean_csv.py

# Merge all CSVs in output/ into output/batch1.csv
python combine_csvs.py
```

---

## Output format

Same as `email-scraper`:

```csv
email,source
#QUERY,vascular surgery in us,2026-06-13 14:30:00
info@example.com,https://example.com/contact
```

---

## email-scraper vs email-scraper-playwright

| | **email-scraper** | **email-scraper-playwright** |
|--|-------------------|------------------------------|
| Speed | Faster | Slower (real browsers) |
| Google | Scrapling stealth fetch | Playwright (harder to block) |
| Typical yield | Higher | Lower per run (finishes when queue drains) |
| RAM / CPU | Lower | Higher |
| Best for | Long runs, max emails | Google captcha issues, JS-heavy sites |

If Playwright finds few URLs, try `--engine ddg`, `--pages 50`, or drop `--no-variants`. For maximum emails, prefer `email-scraper/` for long sessions.

---

## Folders

| Path | Purpose |
|------|---------|
| `output/` | CSV results |
| `crawl_data/` | Optional checkpoint dir (cleared with `--fresh`) |
| `engine/` | Playwright browser pool |
| `scrapers/` | Google, DDG, page crawler |
| `utils/` | Email regex, dedup, CSV helpers |

---

## Tips

- First run: `playwright install chromium`
- Google blocked? Use `--headed` to see captcha, or `--engine ddg`
- `--no-variants` returns broader results but often fewer emails per page
- Run `clean_csv.py` after merging runs from multiple terminals
