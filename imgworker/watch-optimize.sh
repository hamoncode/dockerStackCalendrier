#!/usr/bin/env bash
set -euo pipefail
WATCH_DIR="${WATCH_DIR:-/mnt/images}"

echo "👀 Watching: $WATCH_DIR"
inotifywait -m -r -e close_write -e moved_to -e create -e delete --format '%e|%w%f' "$WATCH_DIR" \
| while IFS='|' read -r ev path; do
  case "$ev" in
    *DELETE*)
      bn="$(basename "$path")"; base="${bn%.*}"
      odir="$(dirname "$path")/_optimized"
      for f in "$odir/${base}-400.webp" "$odir/${base}-800.webp" "$odir/${base}-1200.webp" "$odir/${base}-tiny.b64"; do
        [[ -f "$f" ]] && { echo "🗑️  removing $f"; rm -f "$f"; }
      done
      ;;
    *CLOSE_WRITE*|*MOVED_TO*|*CREATE*)
      if [[ "$path" =~ \.(jpg|jpeg|png|gif)$ ]]; then
        bash /usr/local/bin/optimize-one.sh "$path" || echo "⚠️ failed: $path"
      fi
      ;;
    *) ;;
  esac
done

