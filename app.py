# app.py (updated scraping to match the /srch structure you showed)
"""
Flask Backend for Torrent Management
-------------------------------------
Now using 1377x.to /srch structure for search and detail magnet extraction.
"""

import time
import sys
import logging
import configparser
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from qbittorrent import Client

# -------- CONFIGURATION SETUP -------- #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("config.ini")

try:
    qb_host = config.get("qbit", "host")
    qb_user = config.get("qbit", "user")
    qb_pass = config.get("qbit", "pass")
    if not qb_host or qb_host.lower() == "http://host_ip:port":
        raise ValueError("Invalid 'host' in 'config.ini'.")
    if not qb_user:
        raise ValueError("Invalid 'user' in 'config.ini'.")
    if not qb_pass:
        raise ValueError("Invalid 'pass' in 'config.ini'.")
    logger.info("Configuration loaded successfully.")
except Exception as e:
    logger.error("Configuration error: %s", e)
    sys.exit(1)

# Initialize qBittorrent client
try:
    logger.info("Connecting to qBittorrent host: %s", qb_host)
    qb = Client(qb_host)
except Exception as e:
    logger.error("Failed to init qBittorrent client: %s", e)
    sys.exit(1)

# Initialize Flask
app = Flask(__name__)

# -------- SCRAPER (1377x.to /srch) -------- #

MIRROR_BASE = "https://www.1377x.to"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": MIRROR_BASE,
    "Connection": "keep-alive",
}

def _abs(href: str) -> str:
    return href if href.startswith("http") else f"{MIRROR_BASE}{href}"

def scrape_1377x_detail(detail_url: str) -> str | None:
    """Extract a magnet link from a 1377x detail page (generic selector)."""
    try:
        r = requests.get(detail_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Detail fetch failed: %s", e)
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    # be resilient: any anchor starting with magnet:?
    magnet_tag = soup.select_one("a[href^='magnet:?']")
    if magnet_tag:
        return magnet_tag.get("href")
    logger.warning("No magnet link found on detail page: %s", detail_url)
    return None

def scrape_1377x(query: str, limit: int = 5) -> list[dict]:
    """Scrape the /srch results you provided, then fetch magnet from each detail page."""
    url = f"{MIRROR_BASE}/srch?search={requests.utils.quote(query)}"
    logger.info("Scraping search: %s", url)

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.error("Search fetch failed: %s", e)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select("tbody tr")
    logger.info("Found %d rows", len(rows))
    results = []

    for row in rows:
        try:
            title_tag = row.select_one("td.coll-1.name a[href^='/torrent/']")
            if not title_tag:
                # skip rows that don't have a torrent link (e.g., only /sub/ icon)
                continue

            title = title_tag.get_text(strip=True)
            link = _abs(title_tag["href"])
            seeds = (row.select_one("td.coll-2.seeds") or {}).get_text(strip=True) if row.select_one("td.coll-2.seeds") else ""
            leeches = (row.select_one("td.coll-3.leeches") or {}).get_text(strip=True) if row.select_one("td.coll-3.leeches") else ""
            date = (row.select_one("td.coll-date") or {}).get_text(strip=True) if row.select_one("td.coll-date") else ""
            size = (row.select_one("td.coll-4.size") or {}).get_text(strip=True) if row.select_one("td.coll-4.size") else ""
            uploader_tag = row.select_one("td.coll-5.uploader a")
            uploader = uploader_tag.get_text(strip=True) if uploader_tag else ""

            magnet = scrape_1377x_detail(link)

            results.append({
                "title": title,
                "link": link,
                "category": "Movies",        # default/fallback
                "seeders": seeds,
                "leechers": leeches,
                "date": date,
                "size": size,
                "uploader": uploader,
                "magnet_link": magnet or ""
            })

            if len(results) >= limit:
                break
        except Exception as e:
            logger.exception("Error parsing row: %s", e)
            continue

    logger.info("Returning %d results", len(results))
    return results

# -------- ROUTES -------- #

@app.route("/torrents", methods=["GET"])
def torrents():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "Missing query"}), 400
    data = scrape_1377x(q, limit=10)
    return jsonify(data), 200

@app.route("/infoglobal", methods=["GET"])
def get_filtered_torrents():
    if not qb:
        return jsonify({"error": "qBittorrent unavailable"}), 503
    try:
        qb.login(qb_user, qb_pass)
        torrent_list = qb.torrents(filter="downloading", sort="time_active", limit=10, offset=0)
        return jsonify(torrent_list), 200
    except Exception as e:
        logger.error("Error fetching qBittorrent info: %s", e)
        return jsonify({"error": str(e)}), 500

# -------- MAIN -------- #

if __name__ == "__main__":
    logger.info("Starting Flask backend (dev mode)...")
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    logger.info("Backend running under Gunicorn")
