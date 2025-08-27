FROM alpine:3.20
RUN apk add --no-cache bash inotify-tools imagemagick coreutils libwebp-tools
WORKDIR /work
COPY optimize-one.sh /usr/local/bin/optimize-one.sh
COPY watch-optimize.sh /usr/local/bin/watch-optimize.sh
RUN chmod +x /usr/local/bin/*.sh
ENV WATCH_DIR=/mnt/images
CMD ["bash","-lc","watch-optimize.sh"]

