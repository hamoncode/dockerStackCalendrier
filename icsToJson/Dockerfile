FROM python:3.10-slim

WORKDIR /app

# 1) Copy your script & its requirements
COPY requirements.txt convert_ics_to_json.py ./

# 2) Install exactly what the script needs
RUN pip install --no-cache-dir -r requirements.txt

# 3) How often to refresh (in seconds)
ENV INTERVAL=60

# 4) On start: run once, then every $INTERVAL seconds
CMD ["bash","-lc","\
    python convert_ics_to_json.py && \
    while sleep \"$INTERVAL\"; do \
      python convert_ics_to_json.py; \
    done"]

