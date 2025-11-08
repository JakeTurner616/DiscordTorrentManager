# tests/bitsearch_service_test.py
#!/usr/bin/env python3
import unittest
import requests
from bs4 import BeautifulSoup
import time
import random

# --- Authorized Mirror ---
MIRROR_BASE = "https://www.1377x.to"

# --- Offline HTML Fixtures (matching your provided structure) ---
SAMPLE_SEARCH_HTML = """<tbody>
<tr>
<td class="coll-1 name"><a href="/sub/movies/HD/1/" class="icon">
        <i class="flaticon-hd"></i></a><a href="/torrent/3994201/Spider-Man-Far-from-Home-2019-WEBRip-1080p-YTS-YIFY/">Spider-Man: Far from Home (2019) [WEBRip] [1080p] [YTS] [YIFY]</a></td>
<td class="coll-2 seeds">24989</td>
<td class="coll-3 leeches">9792</td>
<td class="coll-date">May. 11th  '20</td>
<td class="coll-4 size mob-uploader">2 GB</td>
<td class="coll-5 uploader"><a href="/user/YTSAGx/">YTSAGx</a>
</td>
</tr>
</tbody>"""

SAMPLE_DETAIL_HTML = """<ul class="l9007bbd0b313f4aa20553ab76822d4971c77b323 ldcb0d226eccf9ef57b49d77ef2a5c194f84fb666">
  <li>
    <a class="torrentdown1" href="magnet:?xt=urn:btih:37E77490BC4F285DBFA837514715A20BD405A502&amp;dn=Spider-Man%3A+Far+from+Home+%282019%29+%5BWEBRip%5D+%5B1080p%5D+%5BYTS%5D+%5BYIFY%5D">
      Magnet Download
    </a>
  </li>
</ul>"""

class Test1377xMirror(unittest.TestCase):
    """🔍 Validate scraping and parsing for the 1377x.to mirror (srch endpoint)."""

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

    # --- Live connectivity ---

    def test_search_page_status(self):
        """✅ Ensure 1377x /srch returns HTML with rows."""
        url = f"{MIRROR_BASE}/srch?search=spider+man"
        print(f"\nTesting {url} ...")
        time.sleep(random.uniform(1, 2))
        try:
            r = requests.get(url, timeout=10, headers=self.HEADERS)
            self.assertEqual(r.status_code, 200, f"{url} -> {r.status_code}")
            soup = BeautifulSoup(r.text, "html.parser")
            rows = soup.select("tbody tr")
            self.assertGreater(len(rows), 0, "No results parsed from live /srch page")
        except requests.RequestException as e:
            self.skipTest(f"⚠️ Skipped live test: {e}")

    def test_detail_page_has_magnet(self):
        """✅ Ensure magnet exists on a live detail page."""
        url = f"{MIRROR_BASE}/torrent/3994201/Spider-Man-Far-from-Home-2019-WEBRip-1080p-YTS-YIFY/"
        print(f"\nTesting {url} for magnet link ...")
        time.sleep(random.uniform(1, 2))
        try:
            r = requests.get(url, timeout=10, headers=self.HEADERS)
            self.assertEqual(r.status_code, 200)
            soup = BeautifulSoup(r.text, "html.parser")
            # generic + resilient: any <a> starting with magnet:? on the page
            magnet = soup.select_one("a[href^='magnet:?']")
            self.assertIsNotNone(magnet, "Magnet not found")
            self.assertTrue(magnet["href"].startswith("magnet:?xt=urn:btih:"))
        except requests.RequestException as e:
            self.skipTest(f"⚠️ Skipped magnet test: {e}")

    # --- Offline parsing (structure you provided) ---

    def test_offline_parse_search_row(self):
        """🧩 Offline: Verify search row parsing (srch structure)."""
        soup = BeautifulSoup(SAMPLE_SEARCH_HTML, "html.parser")
        row = soup.select_one("tbody tr")
        self.assertIsNotNone(row)

        # pick the actual torrent link (not the /sub/ icon link)
        title_tag = row.select_one("td.coll-1.name a[href^='/torrent/']")
        seeds_tag = row.select_one("td.coll-2.seeds")
        leech_tag = row.select_one("td.coll-3.leeches")
        size_tag = row.select_one("td.coll-4.size")
        date_tag = row.select_one("td.coll-date")
        uploader_tag = row.select_one("td.coll-5.uploader a")

        title = title_tag.get_text(strip=True)
        link = f"{MIRROR_BASE}{title_tag['href']}"
        seeds = seeds_tag.get_text(strip=True)
        leeches = leech_tag.get_text(strip=True)
        size = size_tag.get_text(strip=True)
        date = date_tag.get_text(strip=True)
        uploader = uploader_tag.get_text(strip=True) if uploader_tag else ""

        self.assertIn("Spider-Man", title)
        self.assertTrue(link.startswith(MIRROR_BASE))
        self.assertTrue(seeds.isdigit())
        self.assertTrue(leeches.isdigit())
        self.assertTrue(len(size) > 0)
        self.assertIn(".", date)  # e.g., May.
        self.assertTrue(len(uploader) > 0)

    def test_offline_parse_detail_magnet(self):
        """🧩 Offline: Extract magnet link correctly (srch structure)."""
        soup = BeautifulSoup(SAMPLE_DETAIL_HTML, "html.parser")
        magnet = soup.select_one("a[href^='magnet:?']")
        self.assertIsNotNone(magnet)
        href = magnet["href"]
        self.assertTrue(href.startswith("magnet:?xt=urn:btih:37E77490"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
