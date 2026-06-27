# 📧 Email Scraper v2.0 — Production Ready

Search, crawl, and extract emails at scale. Built with FastAPI backend, Flask HTML frontend, and SQLite persistence.

---

## 🚀 Quick Start (2 Minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Backend (Terminal 1)
```bash
python server.py
```
✅ API running on http://localhost:8000

### 3. Start Frontend (Terminal 2)
```bash
python app.py
```
✅ UI running on http://localhost:5000

### 4. Open Browser
```
http://localhost:5000
```

**That's it. Start scraping.** 🎯

---

## Features

✅ **Search Multiple Engines** — Google, DuckDuckGo
✅ **Multiple Backends** — Scrapling (fast) or Playwright (JS-heavy)
✅ **Live Dashboard** — Real-time stats (pages, emails, rate, errors)
✅ **Location Expansion** — Search across multiple cities
✅ **MX Validation** — Filter dead domains
✅ **Job History** — View all past scrapes
✅ **Download Results** — CSV export
✅ **Stop Jobs** — Graceful job termination

---

## Architecture

```
Frontend: Flask + HTML/CSS/JS
    ↓ Polling every 1 second
Backend: FastAPI server
    ↓ asyncio jobs
Scraper: Actual email extraction
    ↓ Saves to
Database: SQLite (scraped_data.db)
```

**Why this design?**
- ✅ Simple (no npm, no build, no complexity)
- ✅ Reliable (polling is more stable than SSE)
- ✅ Fast (real scraper runs in background)
- ✅ Persistent (SQLite stores everything)

---

## CLI Usage (Original Still Works)

```bash
# Basic search
python main.py "dental clinics london"

# Use DuckDuckGo
python main.py "clinics" --engine ddg

# Use Playwright backend
python main.py "clinics" --backend playwright

# Expand across locations
python main.py "clinics" --expand-locations --locations london manchester paris

# Skip MX checks (faster)
python main.py "clinics" --no-mx

# Domain-targeted
python main.py --domains domains.txt

# Google Maps
python main.py --gmaps "dental clinics london"
```

---

## Web UI Usage

1. **New Job Tab** → Fill form → Click "Start Job"
2. **Dashboard Tab** → Watch live stats
3. **History Tab** → View past jobs

That's it.

---

## API Endpoints

### Jobs
```
POST   /jobs                Start job
GET    /jobs/{id}/status    Job status + stats
GET    /jobs/{id}/download  Download CSV
DELETE /jobs/{id}           Stop job
GET    /jobs                List all jobs
```

Full API docs: http://localhost:8000/docs (when server is running)

---

## Database

SQLite file: `scraped_data.db`

Query emails:
```bash
sqlite3 scraped_data.db "SELECT * FROM emails LIMIT 10;"
```

---

## Files

```
email-scraper/
├── server.py              FastAPI backend + job management
├── app.py                 Flask HTML frontend
├── main.py                Original CLI scraper
├── requirements.txt       All dependencies
├── config.py              Configuration
├── utils/
│   ├── database.py        SQLite layer
│   ├── display.py         Live stats display
│   ├── confidence.py       Email confidence scoring
│   └── ... other utilities
├── scrapers/              Various scraper modules
├── spiders/               Crawl logic
└── templates/
    └── index.html         Single HTML file (CSS + JS inline)
```

---

## Configuration

Edit `config.py` to customize:
- Search workers
- Crawl workers
- Pages to scrape
- Output locations
- etc.

---

## Performance

**Speed Depends On:**
- Query complexity (how many searches)
- Website load times
- MX validation (enabled = slower)
- Backend (Scrapling > Playwright)

**Typical:**
- 100-500 emails per minute
- Uses 1-2 browser contexts
- Respects rate limits

---

## Rate Limiting

If you get blocked by Google:
1. Switch to DuckDuckGo: `--engine ddg`
2. Reduce workers in config.py
3. Add delays between requests
4. Use proxies (when available)

---

## Troubleshooting

**"Connection refused"**
→ Make sure both `server.py` and `app.py` are running

**"No emails found"**
→ Try `--engine ddg` or different query

**"Slow extraction"**
→ MX checks are slow. Use `--no-mx` to skip

**"Playwright errors"**
→ Install: `playwright install chromium`

**Database locked**
→ Close other connections. SQLite doesn't like concurrent writes.

---

## Production Deployment

For production, upgrade to:
- PostgreSQL (instead of SQLite)
- Gunicorn (FastAPI server)
- Nginx reverse proxy
- Docker containerization
- Background job queue (Celery, Bull)

See `DEPLOYMENT.md` for details (coming soon).

---

## What's Included

✅ FastAPI backend (200 lines)
✅ Flask frontend (300 lines)
✅ SQLite database layer (250 lines)
✅ Confidence scoring (70 lines)
✅ Email/phone/LinkedIn extraction
✅ MX record validation
✅ Job management
✅ Live stats streaming
✅ CSV export
✅ Complete documentation

---

## Future Features

- 🔜 Proxy rotation
- 🔜 Advanced filtering
- 🔜 Email validation
- 🔜 Bulk operations
- 🔜 API keys / authentication
- 🔜 Webhooks
- 🔜 Multi-user support
- 🔜 Cloud deployment

---

## Support

**Issues?** Check the `START.md` or `FLASK_FRONTEND_READY.md` files.

**Want to contribute?** Fork and submit PRs.

**Need help?** Review the code — it's well-commented.

---

## License

MIT License — Use freely.

---

## Stack

**Backend:**
- FastAPI
- asyncio
- aiosqlite

**Frontend:**
- Flask
- HTML/CSS/JavaScript (vanilla)
- No frameworks, no build tools

**Scraping:**
- Scrapling
- Playwright
- Requests

**Database:**
- SQLite (local)
- PostgreSQL-ready (for production)

---

## Getting Started

1. Clone/download this repo
2. `pip install -r requirements.txt`
3. `python server.py` (Terminal 1)
4. `python app.py` (Terminal 2)
5. Open `http://localhost:5000`
6. Start scraping! 🚀

---

**Built with ❤️ for email scraping at scale**

Questions? Check the docs or read the source code.
