#!/usr/bin/env python3
import os, json
import requests
from icalendar import Calendar
from datetime import datetime
from dateutil.tz import tzutc

# 1) configure your feeds → map a “slug” to its ICS URL
FEEDS = {
    "Tonik": os.environ.get("TONIK_ICS"),
    "AGE":   os.environ.get("AGE_ICS"),
    "REI":   os.environ.get("REI_ICS"),
    "REMMA": os.environ.get("REMMA_ICS"),
}

OUTPUT = "calendar-app/public/events.json"

events = []
counter = 1

for assoc, url in FEEDS.items():
    print(f"Fetching {assoc} → {url}")
    resp = requests.get(url)
    resp.raise_for_status()

    cal = Calendar.from_ical(resp.content)
    for vevent in cal.walk("VEVENT"):
        dtstart = vevent.get("dtstart").dt
        dtend   = vevent.get("dtend"  ).dt if vevent.get("dtend") else None

        # normalize to ISO format
        def iso(dt):
            if isinstance(dt, datetime):
                # ensure timezone-aware → UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tzutc())
                return dt.isoformat()
            else:
                return dt.strftime("%Y-%m-%d")

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
                # you can add logic here to pick an image per assoc
                "image":       f"images/{assoc.lower()}.jpg",
            }
        }

        # if you have a URL in the event:
        if vevent.get("url"):
            e["extendedProps"]["registrationLink"] = str(vevent["url"])

        events.append(e)
        counter += 1

# 3) write the JSON out
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(events, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(events)} events to {OUTPUT}")

