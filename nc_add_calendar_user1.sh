#!/usr/bin/env bash
set -euo pipefail

# ====== CONFIG ======
NC_CONTAINER="${NC_CONTAINER:-dockerstackcalendrier-nextcloud-1}"
CAL_GROUP="calendar-only"
<<<<<<< Updated upstream
TEMP_PASS="${TEMP_PASS:-TEMP_PASS1}"
=======
TEMP_PASS="${TEMP_PASS:-Welcome1!}"
>>>>>>> Stashed changes

# Quotas — give enough space for attachments
SETUP_QUOTA="${SETUP_QUOTA:-50 MB}"         # for first login/init
ATTACHMENT_QUOTA="${ATTACHMENT_QUOTA:-250 MB}"  # final quota for ongoing use (attachments)

# Your external Nextcloud URL (must be in trusted domains)
NC_BASE_URL="${NC_BASE_URL:-https://cloud.reiuqode.com}"

# If using a self-signed cert to reach NC_BASE_URL, run with CURL_INSECURE=1
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
  local url="${NC_BASE_URL%/}/remote.php/dav/calendars/${user}/personal/"

  local body
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
  if echo "$body" | grep -qE 'HTTP/1\.1 2..'; then
    echo "   ✓ Renamed default calendar to '${newname}'"
  else
    echo "   ! Could not rename 'personal' calendar (maybe not created yet)."
    echo "     Response:"
    echo "$body" | sed 's/^/       /'
  fi
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

# Avoid skeleton copy (saves space / prevents 500s on tiny quotas)
occ config:system:set skeletondirectory --value=""

# Make Calendar the default app (keep users focused)
occ config:system:set defaultapp --value="calendar"

# ====== Create user (pass OC_PASS into the container) ======
echo "Creating user '$USER' with temporary password '${TEMP_PASS}'..."
docker exec -e OC_PASS="${TEMP_PASS}" -u www-data -w /var/www/html \
  "$NC_CONTAINER" php occ user:add --password-from-env \
  --group "$CAL_GROUP" --display-name "$USER" "$USER"

# Email
if [[ -n "$EMAIL" ]]; then
  occ user:setting "$USER" settings email "$EMAIL"
fi

# Let the account initialize, then assign final quota for attachments
occ user:setting "$USER" files quota "$SETUP_QUOTA"

# Rename default calendar "personal" → "<username>"
rename_personal_calendar "$USER" "$TEMP_PASS" "$USER" || true

# Final quota suitable for attachments
occ user:setting "$USER" files quota "$ATTACHMENT_QUOTA"

echo "✅ User '$USER' ready."
echo "   Email: ${EMAIL:-<none>}"
echo "   Temp password: ${TEMP_PASS}"
echo "   Group: $CAL_GROUP"
echo "   Quota now: $ATTACHMENT_QUOTA (was $SETUP_QUOTA for setup)"
echo "   Calendar renamed to: $USER (if default existed)"
echo "⚠️ Ask the user to change their password at first login."
