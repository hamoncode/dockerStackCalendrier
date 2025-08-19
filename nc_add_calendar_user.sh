#!/usr/bin/env bash
set -euo pipefail

# ====== CONFIG ======
NC_CONTAINER="${NC_CONTAINER:-dockerstackcalendrier-nextcloud-1}"
CAL_GROUP="calendar-only"
TEMP_PASS="${TEMP_PASS:-Welcome1}"
# Use a small quota to block Files; we'll temporarily lift it for first login tasks
SETUP_QUOTA="${SETUP_QUOTA:-10 MB}"
LOCKED_QUOTA="${LOCKED_QUOTA:-1 B}"

# Your external Nextcloud base URL (MUST be in Nextcloud trusted domains)
NC_BASE_URL="${NC_BASE_URL:-https://cloud.reiuqode.com}"

# If using a self-signed cert, set CURL_INSECURE=1 in env when running the script
CURL_FLAGS=()
[[ "${CURL_INSECURE:-0}" == "1" ]] && CURL_FLAGS+=(-k)

# ====== Helpers ======
occ () {
  docker exec -u www-data -w /var/www/html "$NC_CONTAINER" php occ "$@"
}

rename_personal_calendar () {
  local user="$1"
  local pass="$2"
  local newname="$3"

  # CalDAV URL for the default calendar (slug is 'personal' regardless of UI language)
  local url="${NC_BASE_URL%/}/remote.php/dav/calendars/${user}/personal/"

  # Send PROPPATCH to set DAV:displayname = username
  # Expected status is 207 (Multi-Status) when successful.
  local body status
  body="$(curl -sS -u "${user}:${pass}" -X PROPPATCH -H 'Content-Type: application/xml; charset=utf-8' \
    --data-binary @- "${CURL_FLAGS[@]}" "$url" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<d:propertyupdate xmlns:d="DAV:">
  <d:set>
    <d:prop>
      <d:displayname>${newname}</d:displayname>
    </d:prop>
  </d:set>
</d:propertyupdate>
EOF
)"
  # Rough success check: look for HTTP/1.1 200 OK inside multistatus or no obvious error
  if echo "$body" | grep -qE 'HTTP/1\.1 2.. OK|<d:status>HTTP/1\.1 2..'; then
    echo "   ✓ Renamed default calendar to '${newname}'"
    return 0
  fi

  # If rename failed (e.g., calendar not created yet), just report it.
  echo "   ! Could not rename 'personal' calendar (maybe it doesn't exist yet)."
  echo "     Response:"
  echo "$body" | sed 's/^/       /'
  return 1
}

# ====== Pre-flight ======
if ! docker ps --format '{{.Names}}' | grep -q "^${NC_CONTAINER}\$"; then
  echo "ERROR: Container '${NC_CONTAINER}' not found or not running." >&2
  exit 1
fi

# ====== Ask for input ======
read -rp "Enter new username: " USER
read -rp "Enter email for $USER: " EMAIL
if [[ -z "$USER" ]]; then
  echo "Username cannot be empty." >&2
  exit 1
fi

# ====== Ensure group & apps ======
occ group:add "$CAL_GROUP" || true
occ app:install calendar || true
occ app:enable calendar
occ app:install apporder || true
occ app:enable apporder

# Disable skeleton contents (prevents quota-related 500s on first login)
occ config:system:set skeletondirectory --value=""

# Make Calendar the default app (optional; comment out if not desired)
occ config:system:set defaultapp --value="calendar"

# ====== Create user ======
echo "Creating user '$USER' with temporary password '${TEMP_PASS}'..."
docker exec -e OC_PASS="${TEMP_PASS}" -u www-data -w /var/www/html \
  "$NC_CONTAINER" php occ user:add --password-from-env \
  --group "$CAL_GROUP" --display-name "$USER" "$USER"

# Set email (optional)
if [[ -n "$EMAIL" ]]; then
  occ user:setting "$USER" settings email "$EMAIL"
fi

# Give a small temporary quota so the account can initialize cleanly
occ user:setting "$USER" files quota "$SETUP_QUOTA"

# ====== Rename the default calendar 'personal' to the username ======
rename_personal_calendar "$USER" "$TEMP_PASS" "$USER" || true

# Lock files usage down after initialization
occ user:setting "$USER" files quota "$LOCKED_QUOTA"

echo "✅ User '$USER' ready."
echo "   Email: ${EMAIL:-<none>}"
echo "   Temp password: ${TEMP_PASS}"
echo "   Group: $CAL_GROUP"
echo "   Quota now: $LOCKED_QUOTA (was $SETUP_QUOTA for setup)"
echo "   Calendar renamed to: $USER (if default existed)"
echo "⚠️ Ask the user to log in and change their password immediately."
