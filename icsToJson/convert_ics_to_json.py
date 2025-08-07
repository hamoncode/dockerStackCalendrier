#!/usr/bin/env python3
import os, json, requests, argparse, base64, mimetypes, hashlib
from pathlib import Path
from icalendar import Calendar
from datetime import datetime
from dateutil.tz import tzutc
from urllib.parse import urlparse

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

def _safe_ext_from_fmt(fmt: str | None) -> str:
    if not fmt:
        return ".bin"
    # common fast paths
    if fmt.lower() in ("image/jpeg", "image/jpg"):
        return ".jpg"
    if fmt.lower() == "image/png":
        return ".png"
    if fmt.lower() == "image/webp":
        return ".webp"
    guess = mimetypes.guess_extension(fmt, strict=False)
    return guess or ".bin"

def _filename_for_attach(assoc: str, idx: int, ext: str) -> str:
    return f"{assoc.lower()}_attach_{idx}{ext}"

def _ext_from_url(u: str) -> str:
    path = urlparse(u).path
    ext = Path(path).suffix
    return ext if ext else ".bin"

def save_event_attachments(vevent, images_dir: Path, assoc: str) -> list[Path]:
    """
    Extract ATTACH properties from a VEVENT.
    - URL attachments are downloaded.
    - Base64/binary attachments are decoded.
    Files are saved to images_dir and returned as a list of Paths.
    """
    images_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []
    attach_idx = 1

    # icalendar stores properties in uppercase keys
    for key, prop in vevent.property_items():
        if key != "ATTACH":
            continue

        # MIME type if present
        fmt = None
        try:
            fmt = prop.params.get("FMTTYPE")
        except Exception:
            pass

        # Value may be bytes (already unfolded). Convert to str for URL check.
        raw = prop.to_ical()
        if isinstance(raw, bytes):
            text_val = raw.decode("utf-8", "ignore")
        else:
            text_val = str(raw)

        if text_val.startswith("http://") or text_val.startswith("https://"):
            # URL attachment
            try:
                r = requests.get(text_val, timeout=20)
                r.raise_for_status()
                ext = _ext_from_url(text_val)
                # prefer FMTTYPE if extension is generic
                if ext == ".bin" and fmt:
                    ext = _safe_ext_from_fmt(fmt)
                fname = _filename_for_attach(assoc, attach_idx, ext)
                out = images_dir / fname
                out.write_bytes(r.content)
                saved_paths.append(out)
                attach_idx += 1
            except Exception:
                continue
        else:
            # Inline/base64 attachment
            try:
                # Some producers set ENCODING=BASE64 or VALUE=BINARY
                # prop.to_ical() returns the base64 text for binary; decode safely.
                b = base64.b64decode(text_val, validate=False)
                # Decide extension
                ext = _safe_ext_from_fmt(fmt)
                # Content-based fallback: simple magic sniff for JPEG/PNG/WEBP
                if ext == ".bin" and len(b) >= 12:
                    if b[:3] == b"\xff\xd8\xff":
                        ext = ".jpg"
                    elif b[:8] == b"\x89PNG\r\n\x1a\n":
                        ext = ".png"
                    elif b[:4] == b"RIFF" and b[8:12] == b"WEBP":
                        ext = ".webp"
                fname = _filename_for_attach(assoc, attach_idx, ext)
                out = images_dir / fname
                out.write_bytes(b)
                saved_paths.append(out)
                attach_idx += 1
            except Exception:
                continue

    return saved_paths

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.environ.get("FEEDS_FILE", "/config/feeds.txt"),
                    help="Optional feeds file with lines like SLUG=URL")
    ap.add_argument("--output", default=os.environ.get("OUTPUT", "calendar-app/public/events.json"))
    ap.add_argument("--images-dir", default=os.environ.get("IMAGES_DIR", "calendar-app/public/images"),
                    help="Directory where extracted ATTACH images will be saved")
    args = ap.parse_args()

    # load feeds: env first, file can override
    feeds = feeds_from_env()
    feeds.update(parse_feed_file(args.config))

    if not feeds:
        print("!! No feeds configured (env *_ICS or /config/feeds.txt). Nothing to do.")
        return 0

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    images_dir = Path(args.images_dir)

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

            # Try to extract images from ATTACH and use the first one if any
            saved_imgs = save_event_attachments(vevent, images_dir, assoc)
            img_rel = None
            if saved_imgs:
                # make path relative to public/ root (same as current hardcoded convention)
                # assumes images_dir is under calendar-app/public/
                # fall back to basename if not under public
                try:
                    # produce a relative like "images/foo.jpg"
                    rel = saved_imgs[0].relative_to(Path("calendar-app/public"))
                    img_rel = str(rel).replace("\\", "/")
                except ValueError:
                    img_rel = f"images/{saved_imgs[0].name}"

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
                    "image":       img_rel or f"images/{assoc.lower()}.jpg",
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

