#!/usr/bin/env bash
set -euo pipefail

f="$1"
[ -f "$f" ] || exit 0

# Per-file state so we don't re-optimize endlessly when the file changes
STATE_DIR="${STATE_DIR:-/work/.imgworker_state}"
mkdir -p "$STATE_DIR"
key="$(printf '%s' "$f" | sha1sum | awk '{print $1}')"
stamp="$STATE_DIR/$key"

cur="$(stat -c '%Y:%s' "$f")"
if [ -f "$stamp" ] && [ "$(<"$stamp")" = "$cur" ]; then
  exit 0  # unchanged since last run
fi

ext="${f##*.}"
ext="${ext,,}"  # lowercase
before=$(stat -c %s "$f")

optjpg() {
  if command -v jpegoptim >/dev/null; then
    jpegoptim --strip-all --all-progressive --max="${JPEG_QUALITY:-85}" "$f" >/dev/null || true
  else
    mogrify -strip -interlace Plane -sampling-factor 4:2:0 -quality "${JPEG_QUALITY:-85}" "$f"
  fi
}

optpng() {
  if command -v pngquant >/dev/null; then
    pngquant --force --skip-if-larger --ext .png --quality="${PNG_MIN_QUALITY:-65}-${PNG_MAX_QUALITY:-85}" "$f" || true
  fi
  if command -v optipng >/dev/null; then
    optipng -o2 -quiet "$f" || true
  else
    mogrify -strip -define png:compression-level=9 "$f"
  fi
}

optgif() {
  if command -v gifsicle >/dev/null; then
    gifsicle -O3 -b "$f" || true   # in-place
  else
    mogrify -strip "$f"
  fi
}

optwebp() {
  # Recompress webp via temp file, then atomic replace
  tmp="$(mktemp --suffix=.webp)"
  cwebp -quiet -q "${WEBP_QUALITY:-80}" "$f" -o "$tmp"
  mv -f "$tmp" "$f"
}

case "$ext" in
  jpg|jpeg) optjpg ;;
  png)      optpng ;;
  gif)      optgif ;;
  webp)     optwebp ;;
  *)        ;;    # unknown -> skip
esac

after=$(stat -c %s "$f")
echo "$cur" > "$stamp"   # mark processed for this mtime/size

printf '✓ optimized %s (%s → %s bytes)\n' "$f" "$before" "$after"

