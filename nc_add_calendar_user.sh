#!/usr/bin/env bash
set -euo pipefail

# ====== CONFIG ======
NC_CONTAINER="${NC_CONTAINER:-dockerstackcalendrier-nextcloud-1}"
CAL_GROUP="calendar-only"
TEMP_PASS="${TEMP_PASS:-Welcome1}"
TINY_QUOTA="${TINY_QUOTA:-1 B}"   # safer than 0 B on some Nextcloud versions

# ====== Helpers ======
occ () {
  docker exec -u www-data -w /var/www/html "$NC_CONTAINER" php occ "$@"
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

# ====== Create user ======
export OC_PASS="$TEMP_PASS"
echo "Creating user '$USER' with temporary password '$TEMP_PASS'..."
occ user:add --password-from-env --group "$CAL_GROUP" --display-name "$USER" "$USER"

# Set email
if [[ -n "$EMAIL" ]]; then
  occ user:setting "$USER" settings email "$EMAIL"
fi

# Block Files with tiny quota
occ user:setting "$USER" files quota "$TINY_QUOTA"

# Make Calendar the default app (optional)
occ config:system:set defaultapp --value="calendar"

echo "✅ User '$USER' created."
echo "   Email: $EMAIL"
echo "   Temp password: $TEMP_PASS"
echo "   Group: $CAL_GROUP"
echo "   Quota: $TINY_QUOTA"
echo
echo "⚠️  Advise the user to log in and change their password immediately."
