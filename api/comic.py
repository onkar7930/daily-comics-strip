from flask import Flask, request, Response
import urllib.request
import urllib.error
import re
import random
import datetime
import xml.etree.ElementTree as ET

app = Flask(__name__)

# Sourced from comicsrss.com (https://www.comicsrss.com/), which publishes
# pre-generated static RSS feeds — no live scraping against the original
# publishers happens here, which sidesteps both GoComics' bot protection
# and (more importantly) their stated objection to RSS mirroring of their
# content. These are all Comics Kingdom / Arcamax / dilbert.com sourced,
# none from GoComics.
#
# Add more by checking https://www.comicsrss.com/ for a "Copy RSS URL"
# link — the slug is the part before ".rss".
COMICS = [
    {"name": "Dilbert", "slug": "dilbert"},
    {"name": "Beetle Bailey", "slug": "beetle-bailey-1"},
    {"name": "Beetle Bailey (Arcamax)", "slug": "beetlebailey"},
    {"name": "Blondie", "slug": "blondie"},
    {"name": "Hagar the Horrible", "slug": "hagarthehorrible"},
    {"name": "Hi and Lois", "slug": "hiandlois"},
    {"name": "Dennis the Menace", "slug": "dennisthemenace"},
    {"name": "Family Circus", "slug": "familycircus"},
    {"name": "Mallard Fillmore", "slug": "mallardfillmore"},
    {"name": "Judge Parker", "slug": "judge-parker"},
    {"name": "Flash Gordon", "slug": "flash-gordon"},
    {"name": "Barney Google and Snuffy Smith", "slug": "barney-google-and-snuffy-smith"},
    {"name": "Barney Google and Snuffy Smith (Arcamax)", "slug": "barneygoogle"},
    {"name": "Kevin and Kell", "slug": "kevin-and-kell"},
    {"name": "Crock", "slug": "crock"},
    {"name": "Archie", "slug": "archie"},
    {"name": "Arctic Circle", "slug": "arcticcircle"},
    {"name": "Candorville", "slug": "candorville"},
    {"name": "The Dinette Set", "slug": "thedinetteset"},
    {"name": "Dustin", "slug": "dustin"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

BASE_URL = "https://www.comicsrss.com/rss"
IMG_SRC_RE = re.compile(r'<img[^>]+src="([^"]+)"')


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def extract_image_from_item(item_el):
    enclosure = item_el.find("enclosure")
    if enclosure is not None and enclosure.get("url"):
        return enclosure.get("url")
    for child in item_el:
        if child.tag.endswith("content") and child.get("url"):
            return child.get("url")
    description = item_el.find("description")
    if description is not None and description.text:
        match = IMG_SRC_RE.search(description.text)
        if match:
            return match.group(1)
    return None


def pick_strip(date_str: str, attempt: int = 0):
    rnd = random.Random(f"{date_str}-{attempt}")
    return rnd.choice(COMICS)


def get_comic_image(date_str: str):
    tried = []
    for attempt in range(len(COMICS)):
        strip = pick_strip(date_str, attempt)
        if strip["name"] in tried:
            continue
        tried.append(strip["name"])
        feed_url = f"{BASE_URL}/{strip['slug']}.rss"
        try:
            xml_text = fetch(feed_url)
            root = ET.fromstring(xml_text)
            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else []
            if not items:
                continue
            latest = items[0]
            title = latest.findtext("title", default="")
            if "no longer updated" in title.lower() or "no more comics" in title.lower():
                continue
            img_url = extract_image_from_item(latest)
            if img_url:
                source_link = latest.findtext("link", default=feed_url)
                return strip, source_link, img_url
        except Exception:
            continue
    return None, None, None


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
Couldn't load a comic today. <a href="https://www.comicsrss.com">Browse comicsrss.com</a>.
</body></html>
"""


@app.route("/api/comic")
@app.route("/")
def comic():
    date_str = request.args.get("date", datetime.date.today().isoformat())
    strip, page_url, img_url = get_comic_image(date_str)

    if img_url:
        body = PAGE_TEMPLATE.format(
            page_url=page_url,
            img_url=img_url,
            alt=strip["name"],
            caption=f"{strip['name']} — via comicsrss.com",
        )
    else:
        body = FALLBACK_TEMPLATE

    return Response(body, mimetype="text/html", headers={"Cache-Control": "public, max-age=3600"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)