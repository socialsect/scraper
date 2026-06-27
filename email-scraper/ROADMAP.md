# Implementation Roadmap

## Phase 1: FastAPI Server + SSE Streaming ✅

- [x] FastAPI server with job management (`server.py`)
- [x] Job lifecycle: pending → running → completed/failed
- [x] SSE streaming endpoint for live stats
- [x] Job API endpoints: create, status, stream, download, stop
- [x] In-memory job storage (prototype)
- [x] Stats model matching `LiveDisplay` interface

**Status:** Core API implemented. Next: integrate with main.py scraper.

---

## Phase 2: Frontend (React + Vite + Tailwind) ✅

- [x] Project scaffold (package.json, vite.config, tsconfig)
- [x] TypeScript types for API contracts
- [x] API client with axios + EventSource
- [x] Job submission form (query, engine, backend, locations, MX toggle)
- [x] Live dashboard with SSE stats stream
- [x] Download CSV button
- [x] Job status display and error handling

**Status:** Frontend UI complete. Connects to API at localhost:8000.

---

## Phase 3: SQLite Output (`--output-format sqlite`)

- [x] Database layer (`utils/database.py`)
- [x] Schema: jobs, emails, domains tables
- [x] Dedup prevention (email PRIMARY KEY)
- [x] Bulk operations for performance
- [x] CSV export function

**Status:** Database module ready. Next: integrate into main.py crawlers.

---

## Phase 4: Proxy Support

- [x] Config additions for `PROXY` and `PROXY_LIST`
- [ ] Proxy parsing: `http://user:pass@host:port`
- [ ] Proxy file loader: `--proxy-file proxies.txt`
- [ ] Integration in Scrapling backend
- [ ] Integration in Playwright backend

**Next Steps:**
- Add `--proxy` and `--proxy-file` CLI args to main.py
- Modify `get_result_urls_google` and `get_result_urls_ddg` to use proxies
- Modify `EmailSpider` to rotate proxies
- Modify `PlaywrightEmailCrawler` to use proxies

---

## Phase 5: Confidence Scoring

- [x] Confidence module (`utils/confidence.py`)
- [x] Scoring rules (1=low, 2=medium, 3=high)
- [x] Email source detection (mailto, contact page, visible text)

**Status:** Module complete. Next: integrate into crawlers.

**Implementation:**
1. In `EmailSpider.save_email()`, call `score_from_source()`
2. In `PlaywrightEmailCrawler.extract_emails()`, score each email
3. Store confidence in database
4. Frontend sorts/filters by confidence

---

## Integration Checklist

### Server Integration
- [ ] Replace dummy job execution with actual `run()` call from main.py
- [ ] Pass `LiveDisplay` reference to server job
- [ ] Broadcast stats updates to SSE subscribers
- [ ] Handle job cancellation gracefully

### Database Integration
- [ ] Modify email extraction to call `db.add_email()` instead of CSV write
- [ ] Add dedup check before crawling URL
- [ ] Export CSV on download request
- [ ] Query analytics: top domains, confidence distribution

### Confidence Integration
- [ ] Pass HTML + visible text to confidence scorer
- [ ] Store score in database
- [ ] Filter frontend results by confidence threshold
- [ ] Show confidence badge in results table

### Proxy Integration
- [ ] Parse proxy CLI arguments
- [ ] Implement proxy rotation strategy
- [ ] Handle proxy failures + fallback
- [ ] Log proxy usage stats

---

## Quick Setup

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Start API server
python server.py
# Runs on http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
# Proxies API calls to http://localhost:8000
```

### Test Flow

1. Open http://localhost:5173
2. Fill job form (query, engine, backend, etc.)
3. Click "Start Job"
4. Watch live stats update in real-time (SSE)
5. Download CSV when done

---

## Known Limitations (Prototype)

- Job data stored in memory (lost on server restart)
- Single server instance (no clustering)
- No authentication/authorization
- No rate limiting
- Frontend assumes API at localhost:8000

**For Production:**
- Persist jobs to database
- Add user authentication (OAuth2 + JWT)
- Implement rate limiting (FastAPI middleware)
- Deploy frontend to CDN
- Use environment variables for API base URL
- Add request validation + error handling

---

## Next Priority

1. **Integrate server with main.py** — Wire up the dummy job execution
2. **Test full flow** — E2E job submission → SSE stats → CSV download
3. **Proxy support** — Add CLI args and rotate logic
4. **Database integration** — Replace CSV writes with DB inserts
5. **Confidence scoring** — Score emails as they're extracted
