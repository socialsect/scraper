# Email Scraper API Specification

## Overview

FastAPI server providing job-based email scraping with Server-Sent Events (SSE) live streaming and SQLite persistence.

## Base URL

```
http://localhost:8000
```

## Endpoints

### POST /jobs
**Start a new scrape job**

Request body:
```json
{
  "query": "dental clinics london",
  "engine": "google",
  "backend": "scrapling",
  "expand_locations": false,
  "locations": [],
  "check_mx": true,
  "output_file": null
}
```

Response:
```json
{
  "id": "abc12345",
  "status": "pending",
  "query": "dental clinics london",
  "engine": "google",
  "backend": "scrapling",
  "created_at": "2024-01-15T10:30:00.000000",
  "stats": {
    "query": "dental clinics london",
    "backend": "scrapling",
    "elapsed_seconds": 0,
    "pages_crawled": 0,
    "new_emails": 0,
    "total_emails": 0,
    "last_email": "",
    "queue_size": 0,
    "errors": 0,
    "rate_per_min": 0.0
  }
}
```

### GET /jobs/{id}/status
**Get current job state and stats**

Response: Same as POST /jobs response

### GET /jobs/{id}/stream
**Server-Sent Events stream of live stats**

Connect with EventSource to receive real-time updates as newline-delimited JSON:

```javascript
const eventSource = new EventSource('/jobs/abc12345/stream');
eventSource.addEventListener('message', (event) => {
  const stats = JSON.parse(event.data);
  console.log('Pages:', stats.pages_crawled);
  console.log('Emails:', stats.new_emails);
  console.log('Rate:', stats.rate_per_min, '/min');
  
  if (stats._done) {
    eventSource.close();
  }
});
```

Stats payload format:
```json
{
  "query": "dental clinics london",
  "backend": "scrapling",
  "elapsed_seconds": 45,
  "pages_crawled": 120,
  "new_emails": 320,
  "total_emails": 1250,
  "last_email": "info@example.com",
  "queue_size": 45,
  "errors": 2,
  "rate_per_min": 6.2
}
```

When job completes:
```json
{
  "_done": true
}
```

### GET /jobs/{id}/download
**Download CSV results**

Returns the CSV file for the job.

```bash
curl http://localhost:8000/jobs/abc12345/download -o emails.csv
```

### DELETE /jobs/{id}
**Stop a running job**

Response:
```json
{
  "status": "stopped"
}
```

### GET /jobs
**List all jobs**

Response:
```json
{
  "jobs": [
    {
      "id": "abc12345",
      "status": "running",
      "query": "dental clinics london",
      "created_at": "2024-01-15T10:30:00.000000",
      "started_at": "2024-01-15T10:30:05.000000",
      "completed_at": null
    }
  ]
}
```

### GET /health
**Health check**

Response:
```json
{
  "status": "ok"
}
```

## Job Status Values

- `pending` — Job created, not yet started
- `running` — Job actively scraping
- `completed` — Job finished successfully
- `failed` — Job encountered an error
- `stopped` — Job was manually stopped

## Query Parameters

### engine
- `google` — Use Google search (default)
- `ddg` — Use DuckDuckGo search

### backend
- `scrapling` — Fast, async backend (default)
- `playwright` — Full browser automation (JS-heavy sites)

### expand_locations
- `false` — Run query as-is
- `true` — Expand query across each location with keyword variants

### check_mx
- `true` — Validate MX records (slower, more accurate)
- `false` — Skip MX validation (faster)

## Error Responses

### 404 Job Not Found
```json
{
  "detail": "Job not found"
}
```

### 500 Server Error
```json
{
  "detail": "error message"
}
```

## CORS

The API accepts requests from all origins (`*`). Customize in `server.py` if needed.

## Database

SQLite database (`scraped_data.db`) stores:
- `jobs` — Job metadata and stats
- `emails` — Extracted emails with confidence scores
- `domains` — Domain aggregation and tracking

Query the database directly:
```bash
sqlite3 scraped_data.db "SELECT * FROM emails LIMIT 10;"
```

## Running the Server

```bash
python server.py
```

Server starts on `http://localhost:8000`

Docs available at: `http://localhost:8000/docs` (Swagger UI)

## Frontend

React/Vite frontend at `frontend/` folder.

Install and run:
```bash
cd frontend
npm install
npm run dev
```

Frontend connects to API at `http://localhost:8000`
