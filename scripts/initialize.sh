#!/bin/sh
echo "!! === INITIALIZE.SH DEBUT === !!"
set -eu

# wait for DB
until php -r 'exit((int)!@fsockopen(getenv("MYSQL_HOST")?: "db", 3306));'; do sleep 1; done

# trust docker DNS hostnames to avoid 400s internally (safe to repeat)
php /var/www/html/occ config:system:set trusted_domains 1 --value=localhost       || true
php /var/www/html/occ config:system:set trusted_domains 2 --value=nextcloud       || true
php /var/www/html/occ config:system:set trusted_domains 3 --value=127.0.0.1       || true

# if Calendar already enabled, exit quickly
if su -s /bin/sh -c "php /var/www/html/occ app:list | grep -q '^  - calendar:'" www-data; then
  exit 0
fi

# ensure custom_apps exists
mkdir -p /var/www/html/custom_apps
chown -R www-data:www-data /var/www/html/custom_apps

# 1) prefer vendored tarball
if [ -f /vendor/calendar-v5.5.1.tar.gz ]; then
  echo "Installing Calendar from vendor/calendar-v5.5.1.tar.gz"
  tar -xzf /vendor/calendar-v5.5.1.tar.gz -C /var/www/html/custom_apps
  chown -R www-data:www-data /var/www/html/custom_apps/calendar
  su -s /bin/sh -c "php /var/www/html/occ app:enable calendar" www-data || true
fi

# 2) if still not enabled, try latest compatible from GitHub (best-effort)
if ! su -s /bin/sh -c "php /var/www/html/occ app:list | grep -q '^  - calendar:'" www-data; then
  echo "Trying to fetch Calendar releases from GitHub…"
  for TAG in $(curl -fsSL https://api.github.com/repos/nextcloud-releases/calendar/releases?per_page=15 \
               | sed -n 's/.*"tag_name": "\(v[0-9.]\+\)".*/\1/p'); do
    echo "  -> $TAG"
    URL="https://github.com/nextcloud-releases/calendar/releases/download/$TAG/calendar-$TAG.tar.gz"
    if curl -fsSL "$URL" -o /tmp/calendar.tgz; then
      tar -xzf /tmp/calendar.tgz -C /var/www/html/custom_apps && rm -f /tmp/calendar.tgz
      chown -R www-data:www-data /var/www/html/custom_apps/calendar
      if su -s /bin/sh -c "php /var/www/html/occ app:enable calendar" www-data; then
        echo "Calendar $TAG enabled."
        break
      else
        rm -rf /var/www/html/custom_apps/calendar
      fi
    fi
  done
fi

# don’t fail the container if app install can’t happen
exit 0

