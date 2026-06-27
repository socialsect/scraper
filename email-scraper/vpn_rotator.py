"""
vpn_rotator.py
──────────────
Auto-rotating VPN scraper using VPN Gate free servers + OpenVPN.
Detects 429/302 → fetches fresh VPN configs → rotates IP → retries.

Requirements:
    pip install requests curl_cffi stem
    sudo apt install openvpn curl

Usage:
    from vpn_rotator import SmartScraper
    scraper = SmartScraper()
    html = scraper.get("https://www.google.com/search?q=orthopaedic+clinic+miami")
"""

import os
import csv
import time
import random
import subprocess
import tempfile
import io
import logging
from typing import Optional

# Try curl_cffi first (mimics real browser TLS), fallback to requests
try:
    from curl_cffi import requests as cffi_requests
    USE_CURL_CFFI = True
    print("[✓] Using curl_cffi (browser TLS fingerprinting)")
except ImportError:
    import requests as std_requests
    USE_CURL_CFFI = False
    print("[!] curl_cffi not found, using requests. Run: pip install curl_cffi")

import requests  # always needed for fetching VPN Gate configs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

VPNGATE_CSV_URL = "https://www.vpngate.net/api/iphone/"   # returns CSV of free VPN servers

MAX_RETRIES      = 5        # retries per request before giving up
ROTATE_AFTER     = 3        # rotate VPN after this many successful requests (keeps IP fresh)
CONNECT_TIMEOUT  = 15       # seconds to wait for VPN connection
REQUEST_TIMEOUT  = 20       # seconds for each HTTP request
MIN_DELAY        = 2.0      # min seconds between requests
MAX_DELAY        = 5.0      # max seconds between requests

# Countries to prefer (ISO codes). Leave empty [] for any.
PREFERRED_COUNTRIES = ["US", "GB", "DE", "NL", "JP"]

# Browser profiles to rotate through
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]


# ─────────────────────────────────────────────
# VPN GATE — fetch + parse free server list
# ─────────────────────────────────────────────

def fetch_vpngate_servers(preferred_countries: list[str] = None) -> list[dict]:
    """
    Download VPN Gate server list and return as list of dicts.
    Each dict has: hostname, ip, score, ping, speed, country, ovpn_config_base64
    """
    log.info("Fetching VPN Gate server list...")
    try:
        resp = requests.get(VPNGATE_CSV_URL, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        log.error(f"Failed to fetch VPN Gate list: {e}")
        return []

    # VPN Gate CSV has a junk first line and last line
    lines = resp.text.strip().splitlines()
    # Remove comment lines starting with *
    lines = [l for l in lines if not l.startswith("*")]

    reader = csv.DictReader(lines)
    servers = []
    for row in reader:
        try:
            servers.append({
                "hostname":    row.get("#HostName", row.get("HostName", "")),
                "ip":          row.get("IP", ""),
                "score":       int(row.get("Score", 0)),
                "ping":        int(row.get("Ping", 999)),
                "speed":       int(row.get("Speed", 0)),
                "country":     row.get("CountryShort", ""),
                "ovpn_base64": row.get("OpenVPN_ConfigData_Base64", ""),
            })
        except Exception:
            continue

    log.info(f"Got {len(servers)} VPN Gate servers")

    # Filter by preferred countries if specified
    if preferred_countries:
        filtered = [s for s in servers if s["country"] in preferred_countries]
        if filtered:
            log.info(f"Filtered to {len(filtered)} servers in {preferred_countries}")
            servers = filtered

    # Sort by score descending (higher = more reliable)
    servers.sort(key=lambda x: x["score"], reverse=True)

    # Return top 20 to avoid connecting to dead servers
    return servers[:20]


# ─────────────────────────────────────────────
# VPN CONNECTION MANAGER
# ─────────────────────────────────────────────

class VPNManager:
    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None
        self.current_config_path: Optional[str] = None
        self.servers: list[dict] = []
        self.server_index = 0
        self._tmpdir = tempfile.mkdtemp()

    def _check_openvpn(self):
        result = subprocess.run(["which", "openvpn"], capture_output=True)
        if result.returncode != 0:
            raise EnvironmentError(
                "OpenVPN not found. Install with: sudo apt install openvpn"
            )

    def load_servers(self):
        self.servers = fetch_vpngate_servers(PREFERRED_COUNTRIES)
        if not self.servers:
            raise RuntimeError("No VPN Gate servers available. Check your internet connection.")
        self.server_index = 0

    def _get_next_server(self) -> Optional[dict]:
        if not self.servers:
            self.load_servers()
        if self.server_index >= len(self.servers):
            log.info("Exhausted server list, refreshing from VPN Gate...")
            self.load_servers()
        server = self.servers[self.server_index]
        self.server_index += 1
        return server

    def disconnect(self):
        if self.current_process:
            log.info("Disconnecting current VPN...")
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.current_process.kill()
            self.current_process = None

        # Also kill any lingering openvpn processes
        subprocess.run(["sudo", "pkill", "-f", "openvpn"], capture_output=True)
        time.sleep(1)

    def connect(self) -> bool:
        """Connect to next available server. Returns True on success."""
        self._check_openvpn()
        self.disconnect()

        for attempt in range(5):
            server = self._get_next_server()
            if not server or not server["ovpn_base64"]:
                continue

            log.info(f"Connecting to {server['country']} | {server['ip']} | ping:{server['ping']}ms")

            # Decode base64 config
            import base64
            try:
                config_data = base64.b64decode(server["ovpn_base64"]).decode("utf-8", errors="ignore")
            except Exception:
                continue

            # Write config to temp file
            config_path = os.path.join(self._tmpdir, f"vpn_{attempt}.ovpn")
            with open(config_path, "w") as f:
                f.write(config_data)

            # Connect
            try:
                self.current_process = subprocess.Popen(
                    ["sudo", "openvpn", "--config", config_path,
                     "--daemon", "--log", "/tmp/openvpn.log"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                # Wait for connection
                if self._wait_for_connection(timeout=CONNECT_TIMEOUT):
                    log.info(f"[✓] Connected! New IP via {server['country']}")
                    self.current_config_path = config_path
                    return True
                else:
                    log.warning(f"Connection timed out for {server['ip']}, trying next...")
                    self.disconnect()
            except Exception as e:
                log.warning(f"OpenVPN error: {e}")
                self.disconnect()

        log.error("Failed to connect to any VPN server after 5 attempts")
        return False

    def _wait_for_connection(self, timeout=15) -> bool:
        """Poll until OpenVPN log shows 'Initialization Sequence Completed'"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with open("/tmp/openvpn.log", "r") as f:
                    content = f.read()
                if "Initialization Sequence Completed" in content:
                    return True
                if "AUTH_FAILED" in content or "TLS handshake failed" in content:
                    return False
            except FileNotFoundError:
                pass
            time.sleep(1)
        return False

    def get_current_ip(self) -> str:
        """Check current public IP for verification."""
        try:
            resp = requests.get("https://api.ipify.org", timeout=5)
            return resp.text.strip()
        except Exception:
            return "unknown"

    def __del__(self):
        self.disconnect()


# ─────────────────────────────────────────────
# SMART SCRAPER
# ─────────────────────────────────────────────

class SmartScraper:
    """
    Drop-in scraper with automatic VPN rotation on 429/302.

    Usage:
        scraper = SmartScraper()
        html = scraper.get("https://example.com")
    """

    def __init__(self, auto_vpn=True):
        self.vpn = VPNManager() if auto_vpn else None
        self.request_count = 0
        self.auto_vpn = auto_vpn
        self._connect_initial_vpn()

    def _connect_initial_vpn(self):
        if self.auto_vpn:
            log.info("Establishing initial VPN connection...")
            success = self.vpn.connect()
            if success:
                ip = self.vpn.get_current_ip()
                log.info(f"[✓] Starting IP: {ip}")
            else:
                log.warning("[!] Could not connect VPN, proceeding without it")

    def _rotate(self):
        log.info("[↻] Rotating VPN...")
        success = self.vpn.connect()
        if success:
            ip = self.vpn.get_current_ip()
            log.info(f"[✓] New IP: {ip}")
        self.request_count = 0

    def _build_headers(self) -> dict:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def get(self, url: str, **kwargs) -> Optional[str]:
        """
        Fetch a URL. Returns HTML string or None on failure.
        Auto-rotates VPN on 429/302.
        """
        # Rotate proactively after N requests
        if self.auto_vpn and self.request_count >= ROTATE_AFTER:
            log.info(f"[↻] Proactive rotation after {ROTATE_AFTER} requests")
            self._rotate()

        for attempt in range(MAX_RETRIES):
            # Random delay to mimic human behavior
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            log.info(f"Waiting {delay:.1f}s before request...")
            time.sleep(delay)

            try:
                headers = self._build_headers()

                if USE_CURL_CFFI:
                    # Mimics real Chrome TLS fingerprint — much harder to detect
                    resp = cffi_requests.get(
                        url,
                        headers=headers,
                        impersonate="chrome124",
                        timeout=REQUEST_TIMEOUT,
                        **kwargs
                    )
                else:
                    resp = requests.get(
                        url,
                        headers=headers,
                        timeout=REQUEST_TIMEOUT,
                        **kwargs
                    )

                self.request_count += 1

                if resp.status_code == 200:
                    log.info(f"[✓] {url[:60]} → 200 OK")
                    return resp.text

                elif resp.status_code in (429, 302, 403):
                    log.warning(f"[!] {resp.status_code} on attempt {attempt+1}/{MAX_RETRIES}")
                    if self.auto_vpn:
                        self._rotate()
                    else:
                        # Exponential backoff if no VPN
                        backoff = (2 ** attempt) + random.uniform(0, 1)
                        log.info(f"Backing off {backoff:.1f}s...")
                        time.sleep(backoff)

                else:
                    log.warning(f"[!] Unexpected status {resp.status_code}")

            except Exception as e:
                log.error(f"Request error (attempt {attempt+1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(3)

        log.error(f"[✗] Failed to fetch {url} after {MAX_RETRIES} attempts")
        return None

    def get_many(self, urls: list[str]) -> dict[str, Optional[str]]:
        """Scrape multiple URLs. Returns {url: html} dict."""
        results = {}
        for i, url in enumerate(urls):
            log.info(f"[{i+1}/{len(urls)}] {url}")
            results[url] = self.get(url)
        return results

    def close(self):
        if self.vpn:
            self.vpn.disconnect()


# ─────────────────────────────────────────────
# EXAMPLE USAGE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Example: scrape Google search results
    scraper = SmartScraper(auto_vpn=True)

    urls = [
        "https://www.google.com/search?q=orthopaedic+clinic+miami",
        "https://www.google.com/search?q=med+spa+new+york",
        "https://www.google.com/search?q=vascular+surgeon+los+angeles",
    ]

    try:
        results = scraper.get_many(urls)
        for url, html in results.items():
            if html:
                print(f"\n[✓] {url[:50]} → {len(html)} chars")
            else:
                print(f"\n[✗] {url[:50]} → Failed")
    finally:
        scraper.close()