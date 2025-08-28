#!/usr/bin/env bash
set -euo pipefail
WATCH_DIR="${WATCH_DIR:-/mnt/images}"

echo "👀 Watching: $WATCH_DIR"
inotifywait -m -r -e close_write -e moved_to -e create --format '%e|%w%f' "$WATCH_DIR" \
| while IFS='|' read -r ev path; do
  case "$path" in
    *.jpg|*.jpeg|*.JPG|*.JPEG|*.png|*.PNG|*.gif|*.GIF|*.webp|*.WEBP)
      bash /usr/local/bin/optimize-one.sh "$path" || echo "⚠️ failed: $path"
      ;;
    *) : ;;
  esac
done

