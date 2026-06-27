# Quick Start Guide

## Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn

## Setup

### 1. Backend (FastAPI Server)

```bash
# Install Python dependencies
pip install -r requirements.txt

# Start the API server
python server.py
```

Server will be available at: `http://localhost:8000`

API documentation: `http://localhost:8000/docs` (Swagger UI)

### 2. Frontend (React)

In a new terminal:

```bash
cd frontend

# Install Node dependencies
npm install

# Start dev server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

Automatically proxies API calls to `http://localhost:8000`

---

## Basic Usage

### Via Frontend

1. Open `http://localhost:5173`
2. Fill in the job form:
   - **Search Query**: e.g. `"dental clinics london"`
   - **Engine**: Google or DuckDuckGo
   - **Backend**: Scrapling (fast) or Playwright (JS-heavy sites)
   - **Expand Locations**: Optional, comma-separated
   - **MX Check**: Validate email domains
3. Click **Start Job**
4. Watch live stats stream in real-time
5. Download CSV when done

### Via Command Line (Original CLI)

```bash
# Basic search
python main.py "dental clinics london"

# With DuckDuckGo
python main.py "clinics" --engine ddg

# Expand across locations
python main.py "clinics" --expand-locations --locations london manchester paris

# Use Playwright backend
python main.py "clinics" --backend playwright

# Skip MX validation (faster)
python main.py "clinics" --no-mx

# Domain-targeted (skip search)
python main.py --domains domains.txt

# Google Maps scraping
python main.py --gmaps "dental clinics london"
python main.py --gmaps-emails "dental clinics london"
```

### Via API (curl)

```bash
# Start a job
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "query": "dental clinics london",
    "engine": "google",
    "backend": "scrapling",
    "check_mx": true
  }'

# Response:
# {
#   "id": "abc12345",
#   "status": "pending",
#   ...
# }

# Get status
curl http://localhost:8000/jobs/abc12345/status

# Download results
curl http://localhost:8000/jobs/abc12345/download -o emails.csv

# Stop job
curl -X DELETE http://localhost:8000/jobs/abc12345
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│           Frontend (React + Vite)               │
│  - Job form submission                          │
│  - Live SSE stats stream                        │
│  - Results table                                │
│  - CSV download                                 │
└────────────────────┬────────────────────────────┘
                     │ HTTP + SSE
┌────────────────────▼────────────────────────────┐
│         Backend (FastAPI)                       │
│  - Job management (create, status, stream)      │
│  - SSE broadcaster                              │
│  - CSV export                                   │
└────────────────────┬────────────────────────────┘
                     │ asyncio
┌────────────────────▼────────────────────────────┐
│      Scraper (main.py)                          │
│  - Search (Google/DDG)                          │
│  - Crawl (Scrapling/Playwright)                 │
│  - Extract emails                               │
│  - MX validation                                │
└────────────────────┬────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────┐
│    SQLite Database                              │
│  - jobs table                                   │
│  - emails table                                 │
│  - domains table                                │
└─────────────────────────────────────────────────┘
```

---

## Database

SQLite database file: `scraped_data.db`

Query emails:
```bash
sqlite3 scraped_data.db "SELECT * FROM emails LIMIT 10;"
```

Query domains:
```bash
sqlite3 scraped_data.db "SELECT domain, email_count FROM domains ORDER BY email_count DESC LIMIT 20;"
```

---

## Troubleshooting

### "Connection refused" error
- Ensure backend server is running: `python server.py`
- Check if port 8000 is in use: `lsof -i :8000` (macOS/Linux)

### Frontend can't reach API
- Verify CORS is enabled in `server.py`
- Check browser console for specific errors
- Ensure both frontend and backend are running

### "Playwright not installed"
```bash
pip install playwright
playwright install chromium
```

### Slow scraping with Google
- Try `--engine ddg` to switch to DuckDuckGo
- Add `--proxy http://...` to rotate IPs
- Use `--no-mx` to skip email validation (faster)

---

## Next Steps

1. **Try different queries** — Customize for your use case
2. **Combine backends** — Use Scrapling for speed, Playwright for JS
3. **Enable proxy rotation** — Handle rate limiting
4. **Database queries** — Analyze results across jobs
5. **Integrate with your app** — Use the REST API

---

## Support

- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173
- **Roadmap**: See `ROADMAP.md`
- **API Spec**: See `API_SPEC.md`

---

## Current Status

✅ Phase 1 (FastAPI + SSE) — Complete
✅ Phase 2 (React Frontend) — Complete  
✅ Phase 3 (SQLite Database) — Ready to integrate
⏳ Phase 4 (Proxy Support) — Pending
⏳ Phase 5 (Confidence Scoring) — Pending

See `ROADMAP.md` for integration checklist.
