FROM alpine:3.18

# 1. Install cron, curl, python + ICS library
RUN apk add --no-cache dcron curl python3 py3-pip \
 && pip3 install --no-cache-dir ics

# 2. Copy your sync script
COPY calendar_sync.sh /usr/local/bin/calendar_sync.sh
RUN chmod +x /usr/local/bin/calendar_sync.sh

# 3. Add a crontab
#    This installs a root crontab that runs the sync every minute.
COPY crontab /etc/crontabs/root

# 4. Expose/use a volume for the calendar files
VOLUME ["/data"]

# 5. Start cron in foreground with logs to stdout
CMD ["crond", "-f", "-L", "/dev/stdout"]

