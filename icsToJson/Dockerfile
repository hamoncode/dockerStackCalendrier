# calendar-converter/Dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt convert_ics_to_json.py ./

# install only what's needed
RUN pip install --no-cache-dir -r requirements.txt

# run once at startup, then every 30m
CMD bash -c "\
    python convert_ics_to_json.py && \
    while sleep 60; do \
      python convert_ics_to_json.py; \
    done"

