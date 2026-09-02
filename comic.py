from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request
import re
import random
import datetime

# Add/remove comics here. "slug" is the part of the URL after gocomics.com/
# "start"/"end" is the range of years that comic actually ran (so we don't
# pick a date it never published on). Update "end" occasionally for comics
# still running.
COMICS = [
    {"name": "Calvin and Hobbes", "slug": "calvinandhobbes", "start": 1985, "end": 1995},
    {"name": "Garfield", "slug": "garfield", "start": 1978, "end": 2025},
    {"name": "Peanuts", "slug": "peanuts", "start": 1950, "end": 2000},
    {"name": "The Far Side", "slug": "farside", "start": 1980, "end": 1994},
    {"name": "FoxTrot", "slug": "foxtrot", "start": 1988, "end": 2006},
    {"name": "Pearls Before Swine", "slug": "pearlsbeforeswine", "start": 2002, "end": 2025},
    {"name": "Get Fuzzy", "slug": "getfuzzy", "start": 1999, "end": 2019},
    {"name": "Non Sequitur", "slug": "nonsequitur", "start": 1992, "end": 2025},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

OG_IMAGE_RE = re.compile(r'<meta property="og:image" content="([^"]+)"')


def fetch_og_image(url: str):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=8) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    match = OG_IMAGE_RE.search(html)
    return match.group(1) if match else None


def pick_strip(date_str: str, attempt: int = 0):
    """Deterministic-per-day pick, but nudge the seed on retry so a dead
    link doesn't just fail silently."""
    rnd = random.Random(f"{date_str}-{attempt}")
    comic = rnd.choice(COMICS)
    month, day = date_str[5:7], date_str[8:10]
    year = rnd.randint(comic["start"], comic["end"])
    page_url = f"https://www.gocomics.com/{comic['slug']}/{year}/{month}/{day}"
    return comic, page_url


def get_comic_image(date_str: str):
    last_page_url = None
    for attempt in range(5):
        comic, page_url = pick_strip(date_str, attempt)
        last_page_url = page_url
        try:
            img_url = fetch_og_image(page_url)
        except Exception:
            img_url = None
        if img_url:
            return comic, page_url, img_url
    return None, last_page_url, None


PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  html, body {{
    margin: 0;
    padding: 0;
    height: 100%;
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  a {{ text-decoration: none; }}
  img {{
    max-width: 100%;
    max-height: 100vh;
    object-fit: contain;
    display: block;
  }}
  .caption {{
    position: fixed;
    bottom: 4px;
    right: 8px;
    font: 11px sans-serif;
    color: #999;
  }}
</style>
</head>
<body>
  <a href="{page_url}" target="_blank" rel="noopener">
    <img src="{img_url}" alt="{alt}" />
  </a>
  <div class="caption">{caption}</div>
</body>
</html>
"""

FALLBACK_TEMPLATE = """<!DOCTYPE html>
<html><body style="font-family:sans-serif;display:flex;align-items:center;
justify-content:center;height:100vh;margin:0;color:#666;">
Couldn't load a comic today. <a href="{page_url}">Try the source page</a>.
</body></html>
"""


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        date_str = qs.get("date", [datetime.date.today().isoformat()])[0]

        comic, page_url, img_url = get_comic_image(date_str)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()

        if img_url:
            body = PAGE_TEMPLATE.format(
                page_url=page_url,
                img_url=img_url,
                alt=comic["name"],
                caption=f"{comic['name']} — via GoComics",
            )
        else:
            body = FALLBACK_TEMPLATE.format(page_url=page_url or "https://www.gocomics.com")

        self.wfile.write(body.encode("utf-8"))
