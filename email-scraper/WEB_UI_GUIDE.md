# Email Scraper Web UI - Quick Start Guide

## 🚀 Starting the Dashboard

### Option 1: Use the startup script (Recommended)
```cmd
start.cmd
```

This will automatically open two terminal windows:
- FastAPI backend (port 8000)
- Flask frontend (port 5000)

### Option 2: Manual start

**Terminal 1 - Backend:**
```cmd
python server.py
```

**Terminal 2 - Frontend:**
```cmd
python app.py
```

## 🌐 Access the Dashboard

Open your browser to:
```
http://localhost:5000
```

## ✅ Testing the Integration

To verify everything is working:

```cmd
python test_server.py
```

This will create a test job and show you if stats are updating in real-time.

## 📊 How It Works

1. **Frontend (Flask on :5000)** - The web UI you interact with
2. **Backend (FastAPI on :8000)** - The API that runs scraper jobs
3. **Live Updates** - The frontend polls the backend every second for stats

### Stats Flow:
```
Scraper → LiveDisplay → Intercepted → Job.stats → API → Frontend
```

The `server.py` monkey-patches `LiveDisplay` to capture all stat updates from the scraper and make them available via the API.

## 🎨 Features

- **Dark themed dashboard** with professional UI
- **Real-time stats** - pages crawled, emails found, rate/min
- **Job management** - create, monitor, stop jobs
- **History** - view all past jobs
- **Download results** - get CSV files
- **Health check** - verify backend is running

## 🐛 Troubleshooting

### Dashboard shows "Backend not reachable"
- Make sure `python server.py` is running
- Check http://localhost:8000/health in browser

### Stats not updating
- Check the terminal running `server.py` for errors
- Look for `[JOB]` log messages showing stat updates
- Run `python test_server.py` to diagnose

### Job shows "pending" forever
- Backend might have crashed
- Check the FastAPI terminal for Python errors
- Restart with `start.cmd`

## 📝 Example Usage

1. Open dashboard
2. Click "New Job"
3. Enter query: `dental clinics london`
4. Select engine: `DuckDuckGo` (less likely to block)
5. Enable MX validation
6. Click "Start Job"
7. Watch real-time stats update
8. Download CSV when complete

## 🔧 Configuration

Edit `config.py` to change:
- Number of pages to scrape
- Concurrent requests
- Output file paths
- MX validation settings
- And more...

## 💡 Tips

- Use `ddg` engine to avoid Google blocks
- Disable MX validation for faster results (but less accurate)
- Use `playwright` backend for JavaScript-heavy sites
- Start with small queries to test before scaling up

## 🚦 Status Indicators

- **🟢 Running** - Job is actively scraping
- **✅ Completed** - Job finished successfully
- **🔴 Failed** - Job encountered an error
- **⏸️ Stopped** - Job was manually stopped
- **⏳ Pending** - Job is queued

Enjoy your professional email scraper dashboard! 🎉
