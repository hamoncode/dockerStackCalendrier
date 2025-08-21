#!/usr/bin/env python3
import os, sys, hashlib, time, base64
from urllib.parse import urljoin, urlparse
import requests
import xml.etree.ElementTree as ET
from pathlib import Path

OUT_DIR = Path(os.environ.get("IMAGE_OUT_DIR", "/out/images"))
FEEDS_FILE = os.environ.get("IMAGE_FEEDS_FILE", "/config/image_feeds.txt")
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
TIMEOUT = 20

NS_DAV = {"d": "DAV:"}

def _is_image(path: str) -> bool:
    return Path(path).suffix.lower() in ALLOWED_EXT

def _hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]

def _safe_name(href: str) -> str:
    # make a stable filename based on the path and name
    p = Path(urlparse(href).path)
    stem = p.stem[:80] or "file"
    ext = p.suffix.lower() or ".bin"
    return f"{stem}{ext}"

def _list_children(session: requests.Session, root_url: str, depth: int = 1):
    # PROPFIND to list directory contents
    headers = {"Depth": str(depth), "Content-Type": "text/xml"}
    body = """<?xml version="1.0"?>
<d:propfind xmlns:d="DAV:">
  <d:prop>
    <d:resourcetype/>
    <d:getcontentlength/>
    <d:getlastmodified/>
  </d:prop>
</d:propfind>"""
    r = session.request("PROPFIND", root_url, data=body, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text

def _parse_multistatus(xml_text: str, base_url: str):
    root = ET.fromstring(xml_text)
    entries = []
    for resp in root.findall("d:response", NS_DAV):
        href = resp.findtext("d:href", namespaces=NS_DAV)
        if not href: 
            continue
        # Normalize joins for consistent URL usage
        full_url = urljoin(base_url, href)
        prop = resp.find("d:propstat/d:prop", NS_DAV)
        if prop is None:
            continue
        is_dir = prop.find("d:resourcetype/d:collection", NS_DAV) is not None
        entries.append((full_url, is_dir))
    return entries

def _walk(session: requests.Session, folder_url: str):
    # Depth: 1 to get this folder; then recurse on subfolders
    xml = _list_children(session, folder_url, depth=1)
    entries = _parse_multistatus(xml, folder_url)
    for url, is_dir in entries:
        # Skip the folder itself (WebDAV returns the parent as first entry)
        if url.rstrip("/") == folder_url.rstrip("/"):
            continue
        if is_dir:
            # Recurse
            yield from _walk(session, url)
        else:
            yield url

def _download_if_needed(session: requests.Session, file_url: str, out_dir: Path):
    # Only download if it looks like an image (by extension)
    if not _is_image(file_url):
        return False, None

    r = session.get(file_url, timeout=TIMEOUT, stream=True)
    if r.status_code == 404:
        return False, None
    r.raise_for_status()
    data = r.content
    h = _hash_bytes(data)

    name = _safe_name(file_url)
    target = out_dir / f"{h}_{name}"
    if target.exists() and target.stat().st_size == len(data):
        # Already have it
        return False, target

    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "wb") as f:
        f.write(data)
    return True, target

def import_images_once():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(FEEDS_FILE):
        print(f"[image] feeds file not found: {FEEDS_FILE}", file=sys.stderr)
        return

    with open(FEEDS_FILE) as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]

    total_new = 0
    for ln in lines:
        parts = ln.split()
        if len(parts) < 3:
            print(f"[image] skip malformed line (need URL USER PASS): {ln}", file=sys.stderr)
            continue
        root_url, user, pwd = parts[0], parts[1], parts[2]

        sess = requests.Session()
        sess.auth = (user, pwd) if user != "-" else None

        try:
            for file_url in _walk(sess, root_url):
                new, path = _download_if_needed(sess, file_url, OUT_DIR)
                if new:
                    total_new += 1
                    print(f"[image] downloaded: {path}")
        except requests.HTTPError as e:
            print(f"[image] HTTP error on {root_url}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"[image] error on {root_url}: {e}", file=sys.stderr)

    print(f"[image] done; new files: {total_new}")

if __name__ == "__main__":
    # Optional one-shot mode for startup
    if "--once" in sys.argv:
        import_images_once()
    else:
        interval = int(os.environ.get("IMAGE_INTERVAL", "300"))
        # Run forever
        while True:
            import_images_once()
            time.sleep(interval)

