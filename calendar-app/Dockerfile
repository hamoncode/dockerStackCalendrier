# ─── Base: nginx + python ───────────────────────────────────────────────────
FROM nginx:stable-alpine

# 1) Install python3 & pip
RUN apk add --no-cache python3 py3-pip bash

# 2) Create working dir for your converter
WORKDIR /app

# 3) Copy in your converter script, requirements, (and optionally .env)
COPY requirements.txt convert_ics_to_json.py ./

# 4) Install Python deps
RUN pip3 install --no-cache-dir -r requirements.txt

# 5) Expose HTTP
EXPOSE 80

# 6) Default interval (in seconds) → 60 (every minute)
ENV INTERVAL=60

# 7) The CMD does three things in one line:
#    a) run converter once,
#    b) kick off a background loop to re-run every $INTERVALs,
#    c) start nginx in the foreground.
CMD /bin/bash -lc "\
    python3 /app/convert_ics_to_json.py && \
    ( while sleep \$INTERVAL; do \
        python3 /app/convert_ics_to_json.py; \
      done ) & \
    nginx -g 'daemon off;'"

