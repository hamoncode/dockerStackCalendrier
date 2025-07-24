#!/usr/bin/env bash
set -euo pipefail

# — Path to your feeds file (one NAME=URL per line)
FEEDS_FILE="${FEEDS_FILE:-/data/calendar_feeds.env}"

# — Where to write the .ics files
DEST_DIR="${DEST_DIR:-/var/www/static-calendar}"

# load into an associative array
declare -A FEEDS
while IFS='=' read -r name url; do
  [[ -z "$name" || -z "$url" ]] && continue
  FEEDS[$name]="$url"
done < "$FEEDS_FILE"

# make sure dest exists
mkdir -p "$DEST_DIR"

# temporary work dir
TMPDIR=$(mktemp -d)

for assoc in "${!FEEDS[@]}"; do
  URL="${FEEDS[$assoc]}"
  DEST_FILE="$DEST_DIR/${assoc}.ics"
  TMP_FILE="$TMPDIR/${assoc}.ics"

  # fetch only if newer
  if ! curl -fsS --time-cond "$DEST_FILE" -o "$TMP_FILE" "$URL"; then
    echo "❌ [$assoc] fetch failed"
    continue
  fi

  # if non-empty, replace; else skip
  if [[ -s "$TMP_FILE" ]]; then
    mv "$TMP_FILE" "$DEST_FILE"
    echo " [$assoc] updated at $(date --iso-8601=seconds)"
  else
    echo "ℹ️  [$assoc] no change"
    rm -f "$TMP_FILE"
  fi
done

# clean up
rmdir "$TMPDIR"

