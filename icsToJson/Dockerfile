FROM python:3.10-slim

WORKDIR /app

# scripts & deps
COPY requirements.txt convert_ics_to_json.py import_image.py ./

RUN pip install --no-cache-dir -r requirements.txt

# config
ENV INTERVAL=60 \
    IMAGE_INTERVAL=300 \
    IMAGE_OUT_DIR=/out/images \
    IMAGE_FEEDS_FILE=/config/image_feeds.txt

# Ordrer matters: import image before importing events
CMD ["bash","-lc", "\
  set -euo pipefail; \
  python import_image.py --once || true; \
  python import_events.py; \
  ( while true; do sleep \"$IMAGE_INTERVAL\"; python import_image.py || true; done ) & \
  ( while true; do sleep \"$INTERVAL\"; python convert_ics_to_json.py || true; done ) & \
  wait \
"]

