FROM alpine:3.20
RUN apk add --no-cache bash inotify-tools imagemagick coreutils \
    libwebp-tools jpegoptim optipng pngquant gifsicle
WORKDIR /work
COPY optimize-one.sh /usr/local/bin/optimize-one.sh
COPY watch-optimize.sh /usr/local/bin/watch-optimize.sh
RUN chmod +x /usr/local/bin/*.sh
ENV WATCH_DIR=/mnt/images JPEG_QUALITY=85 PNG_MIN_QUALITY=65 PNG_MAX_QUALITY=85 WEBP_QUALITY=80
CMD ["bash","-lc","watch-optimize.sh"]

