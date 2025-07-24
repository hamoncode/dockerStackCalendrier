#!/usr/bin/env bash
set -euo pipefail

# — CONFIG: set these to your values
ICS_URL="https://nextcloud.example.com/remote.php/dav/calendars/user/calendar.ics"
DEST="/var/www/static-calendar/calendar.ics"

# work in a safe temp dir
TMP="$(mktemp --tmpdir sync.XXXXXX.ics)"

# try to fetch only if newer
curl -fsS --time-cond "$DEST" -o "$TMP" "$ICS_URL" \
  || { echo "❌ curl failed"; rm -f "$TMP"; exit 1; }

# if curl saw “Not Modified” it will write an empty file of size zero
if [[ ! -s "$TMP" ]]; then
  echo "ℹ️  No updates, leaving existing calendar."
  rm -f "$TMP"
  exit 0
fi

# atomically replace
mv "$TMP" "$DEST"
echo " Calendar updated at $(date --iso-8601=seconds)"

