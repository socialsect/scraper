# ⚡ Quick Start Guide

**Project:** Email Scraper v0.2.0  
**Status:** ✅ Production Ready

---

## 🚀 5-Minute Setup

### Step 1: Install Dependencies
```bash
cd email-scraper
pip install -r requirements.txt
```

### Step 2: Start Backend (Terminal 1)
```bash
python server.py
```
✅ Backend running: http://localhost:8000

### Step 3: Start Frontend (Terminal 2)
```bash
python app.py
```
✅ Frontend running: http://localhost:5000

### Step 4: Open Browser
```
http://localhost:5000
```

**Done!** Start scraping from the web UI.

---

## 🎯 CLI Quick Commands

### Basic Scrape
```bash
python main.py "dental clinics london"
```

### With VPN Rotation (Recommended)
```bash
python main.py "dental clinics london" --vpn
```

### Use DuckDuckGo (Less Blocking)
```bash
python main.py "clinics" --engine ddg
```

### Multiple Locations
```bash
python main.py "clinics" --vpn --expand-locations --locations london paris berlin
```

### Skip MX Validation (Faster)
```bash
python main.py "clinics" --vpn --no-mx
```

### Playwright Backend (JS Sites)
```bash
python main.py "clinics" --vpn --backend playwright
```

### Google Maps
```bash
python main.py --gmaps-emails "dental clinics london" --vpn
```

### Domain-Targeted (No Search)
```bash
# Create domains.txt with one domain per line
echo "example.com" > domains.txt
python main.py --domains domains.txt --vpn
```

---

## 📊 Output Files

### Emails CSV
```
output/emails.csv
```

**Columns:**
- email
- source (URL)
- phone
- linkedin, twitter, instagram, facebook, youtube
- mx_valid (yes/no)
- confidence (1=low, 2=medium, 3=high)

### Database
```
scraped_data.db
```

**Query jobs:**
```bash
sqlite3 scraped_data.db "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 5;"
```

---

## 🔧 Configuration

### Edit config.py

**VPN Settings:**
```python
VPN_ENABLED = False
VPN_ROTATE_AFTER = 3
VPN_PREFERRED_COUNTRIES = ["US", "GB", "DE", "NL"]
```

**Performance:**
```python
PAGES_TO_SCRAPE = 30
CONCURRENT_REQUESTS = 5
PLAYWRIGHT_CRAWL_WORKERS = 2
```

---

## 🌐 API Usage

### Start Server
```bash
python server.py
```

### Create Job
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "query": "dental clinics london",
    "engine": "google",
    "backend": "scrapling",
    "check_mx": true
  }'
```

**Response:**
```json
{
  "id": "abc12345",
  "status": "pending",
  "query": "dental clinics london",
  ...
}
```

### Stream Stats (Real-time)
```bash
curl -N http://localhost:8000/jobs/abc12345/stream
```

**Output:**
```
data: {"status":"running","pages_crawled":10,"new_emails":5}
data: {"status":"running","pages_crawled":20,"new_emails":12}
data: ping
data: {"_done":true}
```

### Poll Status (Fallback)
```bash
curl http://localhost:8000/jobs/abc12345/status
```

### Download Results
```bash
curl http://localhost:8000/jobs/abc12345/download -o results.csv
```

### Stop Job
```bash
curl -X DELETE http://localhost:8000/jobs/abc12345
```

### List All Jobs
```bash
curl http://localhost:8000/jobs
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: aiosqlite"
```bash
pip install aiosqlite
```

### "VPN initialization failed"
```bash
# Install OpenVPN
sudo apt install openvpn  # Ubuntu/Debian
brew install openvpn      # macOS

# Run with sudo
sudo python main.py "query" --vpn
```

### "No URLs found"
```bash
# Switch to DuckDuckGo
python main.py "query" --engine ddg --vpn
```

### "Connection refused" (Web UI)
```bash
# Start backend first
python server.py  # Terminal 1
python app.py     # Terminal 2
```

### Google Rate Limiting
```bash
# Enable VPN rotation
python main.py "query" --vpn

# Or use DuckDuckGo
python main.py "query" --engine ddg
```

---

## 📚 Documentation

| File | Purpose |
|------|---------|
| **README.md** | Main documentation |
| **PROJECT_STATUS.md** | Complete project overview |
| **TECHNICAL_BRIEFING.md** | Full technical details (15,000 words) |
| **VPN_INTEGRATION_COMPLETE.md** | VPN setup and usage |
| **SERVER_FIXES.md** | Backend implementation details |
| **USAGE_GUIDE.md** | CLI reference guide |
| **QUICK_START.md** | This file |

---

## ✨ Features

✅ Multiple search engines (Google, DuckDuckGo, Google Maps)  
✅ Two crawl backends (Scrapling fast, Playwright for JS sites)  
✅ VPN rotation (automatic IP switching)  
✅ Email confidence scoring (1-3 quality rating)  
✅ MX validation (filter dead domains)  
✅ Social media extraction (LinkedIn, Twitter, etc.)  
✅ Phone number extraction  
✅ Database persistence (jobs survive restarts)  
✅ Real-time SSE streaming  
✅ Web UI + CLI + API  
✅ Comprehensive documentation  

---

## 🎯 Common Workflows

### 1. Quick Test
```bash
python main.py "test query" --pages 1
```

### 2. Production Scrape
```bash
python main.py "dental clinics london" \
    --vpn \
    --engine google \
    --backend scrapling \
    --expand-locations \
    --locations london manchester birmingham \
    --fresh \
    --output london_dental.csv
```

### 3. Large Scale (Web UI)
1. Start servers: `python server.py` + `python app.py`
2. Open: http://localhost:5000
3. New Job → Fill form → Start
4. Dashboard → Watch progress
5. History → Download CSV

### 4. Domain List Import
```bash
# Prepare domains.txt
cat << EOF > domains.txt
example.com
another-site.org
test-domain.net
EOF

# Scrape
python main.py --domains domains.txt --vpn --backend playwright
```

---

## 📦 Installation from Scratch

### Clone/Download Project
```bash
cd /your/project/folder
```

### Create Virtual Environment (Optional)
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Install VPN (Optional)
```bash
# Ubuntu/Debian
sudo apt install openvpn

# macOS
brew install openvpn

# Windows
# Download from: https://openvpn.net/community-downloads/
```

### Install Playwright (Optional)
```bash
pip install playwright
playwright install chromium
```

### Test Installation
```bash
python main.py "test" --pages 1
```

---

## 🚦 Status Indicators

### CLI Output
- `[✓]` — Success
- `[↻]` — VPN rotating
- `[!]` — Warning/rate limit
- `[✗]` — Error

### Web UI
- **Green** — Running/Success
- **Yellow** — Pending/Warning
- **Red** — Failed/Error
- **Blue** — Info

### API Response
- `"status": "pending"` — Job queued
- `"status": "running"` — Actively scraping
- `"status": "completed"` — Finished successfully
- `"status": "failed"` — Error occurred
- `"status": "stopped"` — User cancelled

---

## 💡 Pro Tips

1. **Use VPN for jobs > 100 URLs** to avoid IP bans
2. **Start with `--pages 1`** to test queries
3. **Skip MX validation** (`--no-mx`) for 2x speed boost
4. **Use DDG engine** for more reliable results
5. **Filter by confidence >= 2** after scraping for quality
6. **Enable `--fresh`** to clear cached progress
7. **Use Playwright backend** only for JS-heavy sites
8. **Check API docs** at http://localhost:8000/docs

---

## 🔐 Security Notes

- VPN requires **sudo** privileges on Linux/macOS
- OpenVPN configs stored in **temp directory** (cleaned on exit)
- Database file `scraped_data.db` contains job history
- CSV files may contain **personal data** (GDPR compliance)
- No authentication by default (add for production)

---

## 📊 Performance Expectations

### Speed
- **100-500 emails/minute** (with MX validation)
- **500-1000 emails/minute** (without MX validation)
- **~15 seconds** per VPN rotation

### Resource Usage
- **CPU:** 10-30% (2-5 workers)
- **RAM:** 200-500 MB
- **Disk:** Minimal (CSV + SQLite database)
- **Network:** 1-10 Mbps

---

## 🎓 Learning Resources

### Understand the Code
1. Read `main.py` — Entry point and CLI logic
2. Read `scrapers/google_scraper.py` — Search implementation
3. Read `spiders/email_spider.py` — Crawl and extraction
4. Read `server.py` — API backend
5. Read `TECHNICAL_BRIEFING.md` — Complete architecture

### Modify & Extend
- Add new extractors → `utils/` directory
- Change search logic → `scrapers/` directory
- Modify UI → `templates/index.html`
- Add API endpoints → `server.py`
- Configure settings → `config.py`

---

## 📞 Support

### Need Help?
1. Check **PROJECT_STATUS.md** for overview
2. Read **TECHNICAL_BRIEFING.md** for details
3. Review **USAGE_GUIDE.md** for CLI reference
4. Check **SERVER_FIXES.md** for backend info
5. Review source code (well-commented)

### Common Questions

**Q: How do I stop a running job?**  
A: Press Ctrl+C in CLI, or use "Stop" button in Web UI, or `DELETE /jobs/{id}` in API

**Q: Can I run multiple jobs simultaneously?**  
A: Yes, via API or Web UI. CLI is single-job only.

**Q: How do I export to Excel?**  
A: Use CSV export, then open in Excel or convert with `pandas`

**Q: Can I schedule jobs?**  
A: Not built-in. Use cron (Linux) or Task Scheduler (Windows)

**Q: How do I increase speed?**  
A: Use `--no-mx`, increase `CONCURRENT_REQUESTS` in config.py, use faster backend (scrapling)

---

## ✅ Verification Checklist

Before starting production scraping:

- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Backend starts without errors (`python server.py`)
- [ ] Frontend connects to backend (`python app.py`)
- [ ] Test query works (`python main.py "test" --pages 1`)
- [ ] VPN connects if needed (`python main.py "test" --vpn --pages 1`)
- [ ] Output directory exists and writable (`output/`)
- [ ] Database created (`scraped_data.db`)
- [ ] Confidence scores appear in CSV
- [ ] Documentation reviewed

---

## 🎉 You're Ready!

Choose your interface:

### Web UI (Easiest)
```bash
python server.py  # Terminal 1
python app.py     # Terminal 2
# Open: http://localhost:5000
```

### CLI (Most Control)
```bash
python main.py "your query" --vpn
```

### API (Most Flexible)
```bash
python server.py
# Then use curl/Postman/code to interact
```

---

**Happy Scraping! 🚀**

For detailed documentation, see **PROJECT_STATUS.md** or **TECHNICAL_BRIEFING.md**.
