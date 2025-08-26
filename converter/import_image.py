#!/usr/bin/env python3
import os, sys, time, hashlib, shutil
from pathlib import Path

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

# Where Nextcloud's data volume is mounted inside the container
NC_DATA_ROOT = os.environ.get("NC_DATA_ROOT", "/ncdata")
# Template to find each association's Calendar folder (uses slug)
IMAGE_SRC_TEMPLATE = os.environ.get(
    "IMAGE_SRC_TEMPLATE",
    f"{NC_DATA_ROOT}/data/{{slug}}/files/Calendar"
)
# Optional per‑slug override: IMAGE_SRC_REI=/custom/path
PER_SLUG_PREFIX = "IMAGE_SRC_"

OUT_DIR = Path(os.environ.get("IMAGE_OUT_DIR", "/app/calendar-app/public/images"))
INTERVAL = int(os.environ.get("IMAGE_INTERVAL", "300"))

KEEP_ORIGINAL_NAMES = os.environ.get("KEEP_ORIGINAL_NAMES", "1").lower() in ("1","true","yes")
GROUP_BY_SLUG = os.environ.get("GROUP_BY_SLUG", "0").lower() in ("1","true","yes")
OVERWRITE = os.environ.get("IMAGE_OVERWRITE", "1").lower() in ("1","true","yes")

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
    feeds = {}
    for k, v in os.environ.items():
        if k.endswith("_ICS"):
            slug = k[:-4]
            feeds[slug] = v
    return feeds

def association_slugs(config_path: str) -> list[str]:
    slugs = set()
    slugs.update(feeds_from_env().keys())
    slugs.update(parse_feed_file(config_path).keys())
    return sorted(slugs)

def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def copy_image(src: Path, out_base: Path, subfolder: str | None):
    ext = src.suffix.lower()
    if ext not in ALLOWED_EXT:
        return False, None
    try:
        # Decide target directory and name
        target_dir = out_base / (subfolder or "")
        target_dir.mkdir(parents=True, exist_ok=True)

        if KEEP_ORIGINAL_NAMES:
            name = src.name
        else:
            digest = hash_file(src)
            name = f"{digest}_{src.name}"

        target = target_dir / name

        if target.exists():
            if not OVERWRITE:
                # keep existing; no change
                return False, target
            # Overwrite only if content differs
            try:
                if target.stat().st_size == src.stat().st_size and hash_file(target) == hash_file(src):
                    return False, target  # identical
            except Exception:
                pass  # if hashing fails, fall through to copy

        shutil.copy2(src, target)
        return True, target
    except Exception as e:
        print(f"[image] error copying {src}: {e}", file=sys.stderr)
        return False, None

def src_dir_for_slug(slug: str) -> Path:
    # Per‑slug override env: IMAGE_SRC_<SLUG>=/path/to/folder
    ov_key = f"{PER_SLUG_PREFIX}{slug}"
    if ov_key in os.environ:
        return Path(os.environ[ov_key])
    # Else use the template
    path = IMAGE_SRC_TEMPLATE.format(slug=slug)
    return Path(path)

def import_once(config_path: str):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    slugs = association_slugs(config_path)
    if not slugs:
        print("[image] No associations found from feeds; nothing to do.", file=sys.stderr)
        return
    total_new = 0
    for slug in slugs:
        root = src_dir_for_slug(slug)
        if not root.exists():
            print(f"[image] missing source for {slug}: {root}", file=sys.stderr)
            continue
        subfolder = slug if GROUP_BY_SLUG else None
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in ALLOWED_EXT:
                new, tgt = copy_image(p, OUT_DIR, subfolder)
                if new:
                    total_new += 1
                    print(f"[image] + {tgt}")
    print(f"[image] done; new files: {total_new}")

def main():
    config_path = os.environ.get("FEEDS_FILE", "/config/feeds.txt")
    if "--once" in sys.argv:
        import_once(config_path)
        return
    while True:
        import_once(config_path)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()

