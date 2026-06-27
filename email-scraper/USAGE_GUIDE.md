# Quick Usage Guide — VPN Rotation & Confidence Scoring

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install VPN rotation dependencies
pip install curl_cffi stem

# Install OpenVPN (Ubuntu/Debian)
sudo apt install openvpn

# Install OpenVPN (macOS)
brew install openvpn
```

---

## Basic Commands

### Simple scrape (no VPN)
```bash
python main.py "orthopaedic clinics london"
```

### With VPN rotation (recommended for large jobs)
```bash
python main.py "orthopaedic clinics london" --vpn
```

### Skip MX validation (faster)
```bash
python main.py "orthopaedic clinics london" --vpn --no-mx
```

### Use DuckDuckGo (less blocking)
```bash
python main.py "orthopaedic clinics london" --vpn --engine ddg
```

### Playwright backend (JS-heavy sites)
```bash
python main.py "orthopaedic clinics london" --vpn --backend playwright
```

---

## Advanced Usage

### Location expansion
```bash
python main.py "dental clinics" --vpn \
    --expand-locations \
    --locations london manchester birmingham paris
```

### Google Maps scraping
```bash
# Get businesses (name, phone, website)
python main.py --gmaps "dental clinics london" --scrolls 20

# Get businesses + crawl for emails
python main.py --gmaps-emails "dental clinics london" --vpn
```

### Domain-targeted (skip search)
```bash
# Create domains.txt with one domain per line
echo "example.com" > domains.txt
echo "another-site.org" >> domains.txt

python main.py --domains domains.txt --vpn
```

### Custom output file
```bash
python main.py "query" --vpn --output custom_results.csv
```

### Fresh start (clear cache)
```bash
python main.py "query" --vpn --fresh
```

---

## VPN Configuration

### Edit config.py
```python
VPN_ENABLED = True                     # Enable by default
VPN_ROTATE_AFTER = 5                   # Rotate after 5 requests
VPN_PREFERRED_COUNTRIES = ["US", "CA"] # North America only
```

### Edit vpn_rotator.py
```python
MIN_DELAY = 1.0  # Faster requests
MAX_DELAY = 3.0
ROTATE_AFTER = 5  # More requests per IP
```

---

## Output

### CSV Schema
```csv
email,source,phone,linkedin,twitter,instagram,facebook,youtube,mx_valid,confidence
info@clinic.com,https://example.com/contact,+44-20-7946-0958,https://linkedin.com/company/clinic,,,,,yes,3
```

### Filter by Confidence
```python
import csv

# Read CSV
with open('output/emails.csv') as f:
    reader = csv.DictReader(f)
    
    # Filter high-confidence only
    high_conf = [row for row in reader if row.get('confidence') == '3']
    
    # Save filtered
    with open('high_confidence.csv', 'w', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(high_conf)
```

---

## Monitoring

### Watch VPN rotations
```bash
python main.py "query" --vpn 2>&1 | grep "Rotating VPN"
```

### Check current IP
```python
from vpn_rotator import SmartScraper
s = SmartScraper()
print(f"Current IP: {s.vpn.get_current_ip()}")
s.close()
```

### Count results
```bash
# Total emails
wc -l output/emails.csv

# High confidence only
grep ",3$" output/emails.csv | wc -l
```

---

## Troubleshooting

### VPN won't connect
```bash
# Check OpenVPN
which openvpn
sudo openvpn --version

# Run with verbose output
sudo python main.py "query" --vpn
```

### Too many rotations
Increase threshold:
```python
# In vpn_rotator.py
ROTATE_AFTER = 10  # Instead of 3
```

### Google blocking
Switch to DuckDuckGo:
```bash
python main.py "query" --vpn --engine ddg
```

---

## Complete Example

```bash
# Full-featured scrape with all options
python main.py "orthopaedic clinics london" \
    --vpn \
    --engine google \
    --backend scrapling \
    --expand-locations \
    --locations london manchester birmingham \
    --pages 30 \
    --output ortho_london.csv \
    --fresh

# Expected output:
# [✓] VPN connected: 185.xxx.xxx.xxx
# Running 18 search queries (engine: google, backend: scrapling, MX: on, VPN: on)...
# Total unique URLs: 340
# [bold]Search complete[/bold] — [green]340[/green] URLs to crawl
# Progress: 50 pages | 120 new emails | 1,120 total
# [↻] Rotating VPN... (rate limit detected)
# [✓] New IP: 149.xxx.xxx.xxx
# Progress: 100 pages | 245 new emails | 1,245 total
# [bold green]Done.[/bold green] 245 new emails — /path/to/ortho_london.csv
```

---

## Performance Tips

1. **Use VPN for jobs > 100 URLs** (prevents IP bans)
2. **Skip MX validation** for speed (`--no-mx`)
3. **Use DDG for reliability** (`--engine ddg`)
4. **Increase workers** (edit `CONCURRENT_REQUESTS` in config.py)
5. **Filter by confidence** after scraping (confidence >= 2)

---

## Quick Reference

| Flag | Purpose |
|------|---------|
| `--vpn` | Enable VPN rotation |
| `--engine ddg` | Use DuckDuckGo |
| `--backend playwright` | Use browser automation |
| `--no-mx` | Skip email validation |
| `--fresh` | Clear cache |
| `--expand-locations` | Multi-city search |
| `--locations X Y Z` | Specify cities |
| `--output FILE` | Custom output file |
| `--pages N` | Pages per query |
| `--gmaps` | Google Maps mode |
| `--domains FILE` | Skip search, use domains |

---

**That's it!** Start with:
```bash
python main.py "orthopaedic clinics london" --vpn
```
