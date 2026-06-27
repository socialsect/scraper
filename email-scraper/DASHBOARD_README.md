# 🚀 Email Scraper Dashboard

A clean, simple web dashboard for the email scraper. No complex setup, just works.

## Quick Start

### 1. Start the Dashboard

**Windows:**
```cmd
start_dashboard.cmd
```

**Mac/Linux:**
```bash
python web_dashboard.py
```

### 2. Open Browser

Go to: **http://localhost:5000**

That's it! 🎉

## Features

✅ **Real-time monitoring** - Watch jobs run live  
✅ **Job history** - See all past jobs  
✅ **Live logs** - Terminal output streamed to browser  
✅ **Download results** - Get CSV files instantly  
✅ **Clean UI** - Dark theme, professional design  
✅ **Zero config** - No FastAPI, no complex setup  

## How It Works

1. **Start a job** - Click "New Job", enter your query
2. **Watch it run** - See pages crawled, emails found in real-time
3. **Download** - Get your CSV when done

The dashboard runs your CLI scraper (`main.py`) in the background and parses its output to show stats.

## Job Files

Jobs are stored in `web_jobs/` as JSON files. Each job has:
- Stats (pages, emails, rate)
- Logs (last 50 lines)
- Status (running, completed, failed)

## Tips

🔥 **Use DuckDuckGo** - Google blocks requests, DDG doesn't  
🔥 **Disable MX validation** - Faster results (but less accurate)  
🔥 **Watch the logs** - See exactly what the scraper is doing  

## Architecture

```
web_dashboard.py (Flask server)
    ↓
main.py (CLI scraper) ← Runs as subprocess
    ↓
Output parsed ← Stats extracted from terminal
    ↓
JSON file ← Stored in web_jobs/
    ↓
Browser polls ← Updates every 2 seconds
```

Simple. Clean. Works.

## Requirements

- Python 3.10+
- Flask (`pip install flask`)
- All scraper dependencies already installed

## Troubleshooting

**"Connection refused"**
- Make sure server is running
- Check http://localhost:5000 in browser

**"Job stuck at pending"**
- Check the terminal for errors
- Make sure `main.py` runs normally

**"No stats updating"**
- Jobs are running, output is being parsed
- Refresh the page
- Check `web_jobs/*.json` files

## Open Source Ready

This dashboard is production-ready for your open source release:
- Clean, professional UI
- Simple architecture
- Easy to understand
- No unnecessary dependencies
- Works on all platforms

Share it. Ship it. Done. 🚢
