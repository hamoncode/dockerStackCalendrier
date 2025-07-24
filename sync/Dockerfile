FROM alpine:3.18

# install bash + curl + python + the ics library
RUN apk add --no-cache bash curl python3 py3-pip \
 && pip3 install --no-cache-dir ics

COPY calendar_sync.sh /usr/local/bin/calendar_sync.sh
RUN chmod +x /usr/local/bin/calendar_sync.sh

# run the sync every 60s
CMD ["sh", "-c", "while true; do /usr/local/bin/calendar_sync.sh; sleep 60; done"]

