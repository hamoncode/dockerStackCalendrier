#!/usr/bin/env bash
set -euo pipefail

# --- CONFIG (override via environment if needed) ---
NEXTCLOUD_CONTAINER="${NEXTCLOUD_CONTAINER:-dockerstackcalendrier-nextcloud-1}"
DB_CONTAINER="${DB_CONTAINER:-dockerstackcalendrier-db-1}"
FEEDS_FILE="${FEEDS_FILE:-./icsToJson/feeds.txt}"
FEED_HOST="${FEED_HOST:-nextcloud}"             # we rewrite hostname to this
TEMP_PASS="${TEMP_PASS:-Welcome1}"
CAL_URI_DEFAULT="personal"                       # internal URI, not the display name

# Load DB creds from .env if present (expects MARIADB_* vars)
if [[ -f .env ]]; then
  # shellcheck disable=SC2046
  export $(grep -E '^(MARIADB_ROOT_PASSWORD|MARIADB_DATABASE)=' .env | xargs -d '\n' -I{} echo {})
fi

: "${MARIADB_ROOT_PASSWORD:?Set MARIADB_ROOT_PASSWORD in environment or .env}"
: "${MARIADB_DATABASE:?Set MARIADB_DATABASE in environment or .env}"

# --- Helpers ---
occ() {
  docker exec -i -u www-data "$NEXTCLOUD_CONTAINER" php occ "$@"
}

dbq() {
  local sql=$1
  docker exec -i "$DB_CONTAINER" mariadb -N -u root "-p${MARIADB_ROOT_PASSWORD}" "$MARIADB_DATABASE" -e "$sql"
}

urlencode() {
  # minimal urlencode for username in URL path
  python3 - <<'PY'
import sys, urllib.parse
print(urllib.parse.quote(sys.argv[1], safe=''))
PY
}

ensure_dir() {
  mkdir -p "$(dirname "$FEEDS_FILE")"
  touch "$FEEDS_FILE"
}

upsert_feed_line() {
  local user="$1" url="$2"
  ensure_dir
  # delete existing line for user, then append
  grep -v -E "^${user}=" "$FEEDS_FILE" > "${FEEDS_FILE}.tmp" || true
  echo "${user}=${url}" >> "${FEEDS_FILE}.tmp"
  mv "${FEEDS_FILE}.tmp" "$FEEDS_FILE"
  echo "Wrote feed: ${user}=${url}  ->  $FEEDS_FILE"
}

# --- Prompt ---
read -rp "Enter new username: " USERNAME
read -rp "Enter email for ${USERNAME}: " EMAIL

# --- Ensure group & apps ---
occ group:add "calendar-only" 2>/dev/null || echo "Group \"calendar-only\" already exists."
for app in calendar apporder; do
  occ app:install "$app" 2>/dev/null || echo "$app already installed"
  occ app:enable "$app" 2>/dev/null || true
done

# --- Create user if missing ---
if ! occ user:list --output=json | grep -q "\"${USERNAME}\""; then
  echo "Creating user '${USERNAME}' with temporary password '${TEMP_PASS}'..."
  docker exec -i "$NEXTCLOUD_CONTAINER" bash -lc "OC_PASS='${TEMP_PASS}' php occ user:add --password-from-env --group='calendar-only' --display-name='${USERNAME}' --email='${EMAIL}' '${USERNAME}'"
else
  echo "User '${USERNAME}' already exists; skipping creation."
fi

# --- Rename default calendar (display name only) ---
# We cannot rename the internal URI with occ; we set the DAV displayname instead.
# This keeps the path /calendars/<user>/personal stable.
# Using CalDAV PROPPATCH requires valid auth. We can use the admin or the created user.
ENC_USER=$(urlencode "$USERNAME")
NC_BASE="http://${FEED_HOST}" # host is irrelevant for PROPPATCH, but we keep consistent

cat > /tmp/prop.xml <<EOF
<?xml version="1.0" encoding="utf-8" ?>
<d:propertyupdate xmlns:d="DAV:">
  <d:set>
    <d:prop>
      <d:displayname>${USERNAME}</d:displayname>
    </d:prop>
  </d:set>
</d:propertyupdate>
EOF

# Try with the new user's temp password; ignore failure if credentials changed
curl -sS -X PROPPATCH \
  -u "${USERNAME}:${TEMP_PASS}" \
  -H "Content-Type: application/xml; charset=utf-8" \
  --data-binary @/tmp/prop.xml \
  "${NC_BASE}/remote.php/dav/calendars/${ENC_USER}/${CAL_URI_DEFAULT}/" >/dev/null || true
rm -f /tmp/prop.xml

# --- Find a public calendar token (if the calendar was published already) ---
# 1) Find calendar id for user's 'personal' calendar
CAL_ID="$(dbq "SELECT id FROM oc_calendars WHERE principaluri='principals/users/${USERNAME}' AND uri='${CAL_URI_DEFAULT}' LIMIT 1;")" || true
TOKEN=""
if [[ -n "${CAL_ID}" ]]; then
  # 2) Look up public token for that calendar in oc_dav_shares
  TOKEN="$(dbq "SELECT publicuri FROM oc_dav_shares WHERE type='calendar' AND resourceid=${CAL_ID} AND access=4 LIMIT 1;")" || true
fi

# --- Build feed URL (rewrite host to 'nextcloud') and write to feeds.txt ---
if [[ -n "${TOKEN}" ]]; then
  FEED_URL="http://${FEED_HOST}/remote.php/dav/public-calendars/${TOKEN}?export"
  echo "Found existing public calendar token for '${USERNAME}'."
else


  # Fall back to authenticated export (works everywhere, requires creds for consumers)
  FEED_URL="http://${FEED_HOST}/remote.php/dav/calendars/${USERNAME}/${CAL_URI_DEFAULT}?export"
  echo "No public link found for '${USERNAME}'. Using private export URL (auth required)."
fi

upsert_feed_line "${USERNAME}" "${FEED_URL}"
