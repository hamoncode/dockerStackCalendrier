#!/usr/bin/env python3
import os, json, requests, argparse
from pathlib import Path
from icalendar import Calendar
from datetime import datetime
from dateutil.tz import tzutc

def normalize(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip().strip('"').strip("'")
    if url.startswith("webcal://"):
        # requests can't handle webcal; inside compose, Nextcloud is plain http
        url = "http://" + url[len("webcal://"):]
    return url

def parse_feed_file(path: str) -> dict[str, str]:
    feeds = {}
    p = Path(path)
    if not p.exists():
        return feeds
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        feeds[k.strip()] = v.strip()
    return feeds

def feeds_from_env() -> dict[str, str]:
    """
    Any ENV like REI_ICS, TONIK_ICS, AGE_ICS becomes {"REI": "...", "TONIK": "...", ...}
    """
    feeds = {}
    for k, v in os.environ.items():
        if k.endswith("_ICS"):
            slug = k[:-4]  # drop suffix
            feeds[slug] = v
    return feeds

def iso(dt):
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tzutc())
        return dt.isoformat()
    else:
        return dt.strftime("%Y-%m-%d")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.environ.get("FEEDS_FILE", "/config/feeds.txt"),
                    help="Optional feeds file with lines like SLUG=URL")
    ap.add_argument("--output", default=os.environ.get("OUTPUT", "calendar-app/public/events.json"))
    args = ap.parse_args()

    # load feeds: env first, file can override
    feeds = feeds_from_env()
    feeds.update(parse_feed_file(args.config))

    if not feeds:
        print("!! No feeds configured (env *_ICS or /config/feeds.txt). Nothing to do.")
        return 0

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    events = []
    counter = 1

    for assoc, raw_url in feeds.items():
        url = normalize(raw_url)
        print(f"Fetching {assoc} → {url}")
        if not url:
            print(f"!! {assoc}: empty URL, skipping")
            continue

        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            cal = Calendar.from_ical(resp.content)
        except Exception as e:
            print(f"!! {assoc}: fetch/parse failed: {e}")
            continue

        for vevent in cal.walk("VEVENT"):
            dtstart = vevent.get("dtstart").dt
            dtend   = vevent.get("dtend").dt if vevent.get("dtend") else None

            e = {
                "id":     str(counter),
                "title":  str(vevent.get("summary")),
                "start":  iso(dtstart),
                **({"end": iso(dtend)} if dtend else {}),
                "allDay": not isinstance(dtstart, datetime),
                "extendedProps": {
                    "association": assoc,
                    "description": str(vevent.get("description", "")),
                    "location":    str(vevent.get("location", "")),
                    "image":       f"images/{assoc.lower()}.jpg",  # ensure this exists under calendar-app/public/images/
                }
            }
            if vevent.get("url"):
                e["extendedProps"]["registrationLink"] = str(vevent["url"])

            events.append(e)
            counter += 1

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(events)} events to {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

