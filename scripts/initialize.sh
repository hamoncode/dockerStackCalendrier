#!/usr/bin/env bash
# /docker-entrypoint.d runs this once on container start
set -e

# Only run if Nextcloud is already installed
if [ ! -f /var/www/html/config/config.php ]; then
  exit 0
fi

OC="occ"   # inside container, Nextcloud’s CLI

# Enable only Calendar app
$OC app:enable calendar
# Disable common extras
for app in files photos contacts deck; do
  $OC app:disable $app || true
done

# Create group + users
$OC group:add calendar-creators
for u in ${CALENDAR_CREATORS_USERS//,/ }; do
  if ! $OC user:exists $u; then
    echo -e "$u\n$DEFAULT_USER_PASSWORD\n$DEFAULT_USER_PASSWORD" | $OC user:add --group calendar-creators --display-name="$u"
  fi
  $OC group:adduser calendar-creators "$u"
done

# Share the “Calendar” with group (owner: admin)
CAL_ID=$($OC calendar:list --output=json | jq -r '.[0].id')
$OC calendar:share "$CAL_ID" group:calendar-creators edit
# Also create a public, read-only share for “everyone”
$OC calendar:share "$CAL_ID" public

