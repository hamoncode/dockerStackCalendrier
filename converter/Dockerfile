FROM python:3.10-slim

WORKDIR /app

# scripts & deps
COPY requirements.txt import_events.py import_image.py ./
RUN pip install --no-cache-dir -r requirements.txt

# config (these defaults are fine; compose overrides OUTPUT/IMAGES_DIR/etc)
ENV INTERVAL=60 \
    IMAGE_INTERVAL=300 \
    PYTHONUNBUFFERED=1

# Order matters: import images before generating events
CMD ["bash","-lc", "\
  set -euo pipefail; \
  python import_image.py --once || true; \
  python import_events.py; \
  ( while true; do sleep \"$IMAGE_INTERVAL\"; python import_image.py || true; done ) & \
  ( while true; do sleep \"$INTERVAL\"; python import_events.py || true; done ) & \
  wait \
"]

