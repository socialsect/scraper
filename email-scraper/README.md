# email-scraper

Fast email scraper that searches Google or DuckDuckGo, crawls result pages, and appends emails to a CSV. Built on [Scrapling](https://github.com/D4Vinci/Scrapling).

**Default output:** `output/emails.csv`

---

## Setup

```bash
cd email-scraper
pip install -r requirements.txt
```

---

## Main scraper

```bash
# Default queries (built-in list in config.py)
python main.py

# Custom search query
python main.py "vascular surgery in us"

# Use DuckDuckGo instead of Google
python main.py "dental clinics uk" --engine ddg

# Expand one UK query into 15 cities × keyword variants (many searches)
python main.py "private clinics in uk" --expand-locations

# Custom output file
python main.py "therapy london" --output output/my_run.csv

# Clear crawl checkpoint and start URL discovery from scratch
python main.py "clinics uk" --fresh
```

### Flags

| Flag | Description |
|------|-------------|
| `query` | Optional search phrase. If omitted, uses `DEFAULT_QUERIES` from `config.py`. |
| `--engine` | `google` (default) or `ddg` |
| `--output` | CSV path (default: `output/emails.csv`) |
| `--expand-locations` | Replace `uk` in query with 15 UK cities and run all keyword variants |
| `--fresh` | Delete `crawl_data/` checkpoint before crawling |

### While it runs

- Terminal shows **`[N new \| M total in CSV]`** on every saved email.
- Progress line every 10 pages: pages crawled, new emails this run, total in CSV.
- Each run writes a **`#QUERY`** marker row in the CSV before new emails (so you can see which search produced which block).
- **Ctrl+C once** — graceful stop (finishes active requests, saves checkpoint).
- **Ctrl+C twice** — force quit.
- The scraper is meant to run until you stop it; it does not exit on its own when there is still work to do.

### Two terminals, same CSV

You can run two instances with the same `--output` path. Both append safely (file locking). Duplicates across terminals are skipped when possible; run `clean_csv.py` to dedupe.

---

## Utility scripts

```bash
# Remove invalid/blocked/duplicate rows from output/emails.csv (creates .bak backup)
python clean_csv.py

# Merge all CSVs in output/ into output/batch1.csv and delete the source files
python combine_csvs.py
```

---

## Output format

`output/emails.csv`:

```csv
email,source
#QUERY,vascular surgery in us,2026-06-13 14:30:00
info@example.com,https://example.com/contact
```

- **`email`** — extracted address  
- **`source`** — page URL where it was found  
- **`#QUERY` rows** — session markers (ignored by `clean_csv.py` and `combine_csvs.py`)

A sidecar `output/emails.csv.lock` may appear briefly during writes; leave it alone.

---

## Folders

| Path | Purpose |
|------|---------|
| `output/` | CSV results |
| `crawl_data/` | Crawl checkpoint (resume after Ctrl+C or crash) |
| `scrapers/` | Google / DDG URL collectors |
| `spiders/` | Page crawler and email extraction |
| `utils/` | Email regex, dedup, CSV helpers |

---

## Tips

- If Google returns few URLs, retry with `--engine ddg`.
- Use `--fresh` if a crawl feels stuck on old URLs.
- Run `clean_csv.py` after long sessions or multi-terminal runs.
- Use `combine_csvs.py` when you have several CSV files in `output/` to merge into one deduplicated `batch1.csv`.
