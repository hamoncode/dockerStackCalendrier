FROM python:3.10-slim

WORKDIR /app

# scripts & deps
COPY requirements.txt télécharger_événements.py ./
RUN pip install --no-cache-dir -r requirements.txt

# config (these defaults are fine; compose overrides OUTPUT/IMAGES_DIR/etc)
ENV INTERVAL=60 \
    IMAGE_INTERVAL=300 \
    PYTHONUNBUFFERED=1

# Order matters: import images before generating events
CMD ["bash","-lc", "\
  set -euo pipefail; \
  python télécharger_événements.py; \
  ( while true; do sleep \"$INTERVAL\"; python télécharger_événements.py || true; done ) & \
  wait \
"]

