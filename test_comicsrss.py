"""
Batch-checks a curated list of comicsrss.com feeds and reports which ones
are actually alive (have a real image in the latest item) vs dead
(no items, or a "no longer updated" notice like the GoComics ones now show).

Deliberately excludes GoComics-sourced strips (Calvin and Hobbes, Garfield,
etc.) since comicsrss.com's own notice confirms those were shut down after
a copyright complaint from GoComics. Includes Comics Kingdom and Arcamax
strips (unaffected by that notice) plus Dilbert (sourced from dilbert.com
directly, not GoComics).

Run directly:

    python3 check_available_comics.py

Add/remove slugs in CANDIDATES below to test others — check
https://www.comicsrss.com/ for the exact slug (shown in each entry's
"Copy RSS URL" link).
"""

import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

IMG_SRC_RE = re.compile(r'<img[^>]+src="([^"]+)"')
BASE_URL = "https://www.comicsrss.com/rss"

# name -> slug. Sourced from Comics Kingdom / Arcamax (not GoComics), plus
# Dilbert (its own site). Feel free to add more from comicsrss.com's list.
CANDIDATES = {
    "Dilbert": "dilbert",
    "Beetle Bailey (Comics Kingdom)": "beetle-bailey-1",
    "Beetle Bailey (Arcamax)": "beetlebailey",
    "Blondie": "blondie",
    "Hagar the Horrible": "hagarthehorrible",
    "Hi and Lois": "hiandlois",
    "Dennis the Menace": "dennisthemenace",
    "Family Circus": "familycircus",
    "Mallard Fillmore": "mallardfillmore",
    "Judge Parker": "judge-parker",
    "Flash Gordon": "flash-gordon",
    "Barney Google and Snuffy Smith (Comics Kingdom)": "barney-google-and-snuffy-smith",
    "Barney Google and Snuffy Smith (Arcamax)": "barneygoogle",
    "Kevin and Kell": "kevin-and-kell",
    "Crock": "crock",
    "Archie": "archie",
    "Arctic Circle": "arcticcircle",
    "Candorville": "candorville",
    "The Dinette Set": "thedinetteset",
    "Dustin": "dustin",
    # Included on purpose as a known-dead control, to show what "dead" looks like:
    "Calvin and Hobbes (GoComics — expected dead)": "calvinandhobbes",
    "Garfield (GoComics — expected dead)": "garfield",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"__FETCH_ERROR__:{e}"


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


def check(slug: str):
    xml_text = fetch(f"{BASE_URL}/{slug}.rss")
    if xml_text.startswith("__FETCH_ERROR__"):
        return "ERROR", xml_text.split(":", 1)[1]

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return "DEAD", "not valid XML"

    channel = root.find("channel")
    if channel is None:
        return "DEAD", "no <channel>"

    items = channel.findall("item")
    if not items:
        return "DEAD", "no items"

    latest = items[0]
    title = latest.findtext("title", default="")
    if "no longer updated" in title.lower() or "no more comics" in title.lower():
        return "DEAD", title

    img_url = extract_image_from_item(latest)
    if img_url:
        return "ALIVE", img_url
    return "DEAD", f"no image in latest item ({title})"


def main():
    print(f"Checking {len(CANDIDATES)} feeds...\n")
    alive = []
    dead = []
    for name, slug in CANDIDATES.items():
        status, detail = check(slug)
        if status == "ALIVE":
            print(f"✅ ALIVE   {name} ({slug})")
            alive.append((name, slug))
        else:
            print(f"❌ {status:6} {name} ({slug}) — {detail[:80]}")
            dead.append((name, slug))
        time.sleep(0.5)  # be polite, don't hammer the site

    print(f"\n{len(alive)} alive, {len(dead)} dead/errored.")
    if alive:
        print("\nAlive slugs (copy into COMICS in comic.py):")
        for name, slug in alive:
            print(f'  "{slug}",  # {name}')


if __name__ == "__main__":
    main()