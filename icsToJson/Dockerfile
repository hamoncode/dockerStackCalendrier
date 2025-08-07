FROM python:3.10-slim

WORKDIR /app

# 1) copy in your converter + deps
COPY requirements.txt convert_ics_to_json.py ./

# 2) install only what's needed
RUN pip install --no-cache-dir -r requirements.txt

# 3) default interval = 60 s (every minute)
ENV INTERVAL=60

# 4) run once, then loop every $INTERVAL seconds
#    use JSON form so Docker can forward signals correctly
CMD ["bash","-lc","\
    python convert_ics_to_json.py && \
    while sleep \"$INTERVAL\"; do \
      python convert_ics_to_json.py; \
    done"]

