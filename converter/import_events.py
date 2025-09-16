#!/usr/bin/env python3
import os, json, requests, argparse, base64, mimetypes, hashlib, shutil, re
from pathlib import Path
from icalendar import Calendar, Event
from datetime import datetime
from dateutil.tz import tzutc
from urllib.parse import urlparse
from urllib.parse import quote
from typing import Optional

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

FILS_ICALENDAR = Path("/config/feeds.txt")
SORTIE_ÉVÉNEMENTS = Path("calendar-app/public/events.json")
SORTIE_IMAGES = Path("calendar-app/public/images/")
RACINE_NEXTCLOUD = Path("/ncdata")

def normalize_root_url(p: Optional[str]) -> Optional[str]:
    """Return a root-relative, percent-encoded URL like /images/foo%20bar.png."""
    if not p:
        return None
    p = p.strip()
    if p.startswith("http://") or p.startswith("https://"):
        return p
    parts = p.lstrip("./").lstrip("/").split("/")
    return "/" + "/".join(quote(seg) for seg in parts if seg)

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

def iso(dt):
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tzutc())
        return dt.isoformat()
    else:
        return dt.strftime("%Y-%m-%d")

def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def save_event_attachments(vevent: Event, assoc: str, utilisateur: str) -> Path:
    attributs: list[tuple[str,object]] = vevent.property_items()
    for clé, attribut in attributs:
        if not clé == "ATTACH":
            continue
        
        nom_fichier = attribut.params.get("FILENAME")[1:] # Le nom est toujours écrit en débutant avec "/", ce qui mélange la combinaison de répertoires.
        if not nom_fichier:
            break
        
        répertoire_source = RACINE_NEXTCLOUD / "data" / utilisateur / "files/Calendar" / nom_fichier
        répertoire_sortie = SORTIE_IMAGES / assoc / nom_fichier
        répertoire_sortie.parent.mkdir(parents=True, exist_ok=True)
        
        try :
            if répertoire_sortie.exists():
                    if répertoire_source.stat().st_size != répertoire_sortie.stat().st_size or hash_file(répertoire_source) != hash_file(répertoire_sortie) :
                        shutil.copy2(répertoire_source, répertoire_sortie)
            else :
                shutil.copy2(répertoire_source, répertoire_sortie)
        except Exception:
            pass

        return répertoire_sortie
    pass

def main():

    # load feeds: env first, file can override
    feeds = parse_feed_file(FILS_ICALENDAR)

    if not feeds:
        print("!! No feeds configured (env *_ICS or /config/feeds.txt). Nothing to do.")
        return 0

    SORTIE_ÉVÉNEMENTS.parent.mkdir(parents=True, exist_ok=True)

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
        
        # Il se pourrait que le nom d'utilisateur Nextcloud soit différent du nom du calendrier. 
        # Nextcloud fournit le nom d'utilisateur dans le nom du calendrier, sous le format suivant : 
        # NOM_CAL (NOM_UTILISATEUR)
        utilisateur = cal.calendar_name.split(" ")[1].replace("(","").replace(")","")
        
        for vevent in cal.walk("VEVENT"):
            dtstart = vevent.get("dtstart").dt
            dtend   = vevent.get("dtend").dt if vevent.get("dtend") else None

            desc = str(vevent.get("description", ""))

            saved_img = save_event_attachments(vevent, assoc, utilisateur)

            img_rel = None
            if saved_img:
                try:
                    rel = saved_img.relative_to(Path("calendar-app/public"))
                    img_rel = "/"+str(rel).replace("\\", "/")
                except ValueError:
                    img_rel = f"images/{saved_img.name}"
            else:
                # TODO use category directive instead of a global default
                img_rel = None
             
            try:
                img_rel = normalize_root_url(img_rel)
            except Exception as e:
                print(f"[WARN] normalize_root_url failed for {img_rel!r}: {e}")
                img_rel = None

            lien_inscription = None
            mots = re.split("[ \n\t\(\)\{\}\[\]]",desc)
            for m in mots:
                if m.startswith("http://") or m.startswith("https://"):
                    lien_inscription = m

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
                    "image": img_rel,
                    "registrationLink": lien_inscription
                }
            }

            events.append(e)
            counter += 1

    with SORTIE_ÉVÉNEMENTS.open("w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(events)} events to {SORTIE_ÉVÉNEMENTS}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

