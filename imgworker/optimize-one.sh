#!/usr/bin/env bash
set -euo pipefail
src="$1"
bn="$(basename "$src")"
[[ "$bn" = .* ]] && exit 0
[[ "$src" =~ /_optimized/ ]] && exit 0
[[ ! -f "$src" ]] && exit 0

dir="$(dirname "$src")"
outdir="$dir/_optimized"
mkdir -p "$outdir"

base="${bn%.*}"
ext="${bn##*.}"; ext="${ext,,}"

is_anim_gif=false
if [[ "$ext" == "gif" ]]; then
  frames="$(magick identify -format "%n" "$src" 2>/dev/null || echo 1)"
  [[ "${frames:-1}" -gt 1 ]] && is_anim_gif=true
fi

make_variant () {
  local w="$1"
  local dest="$outdir/${base}-${w}.webp"
  if [[ -f "$dest" && "$dest" -nt "$src" ]]; then
    echo "✓ up-to-date: $dest"; return 0
  fi
  local tmp="$dest.tmp"
  echo "→ building:  $dest"
  if $is_anim_gif; then
    gif2webp -q 70 -m 6 -mt -loop 0 -resize "$w" 0 "$src" -o "$tmp"
  else
    magick "$src" -auto-orient -strip -filter Lanczos -resize "${w}x>" -quality 72 "$tmp"
  fi
  mv -f "$tmp" "$dest"
}

make_variant 400
make_variant 800
make_variant 1200

tiny="$outdir/${base}-tiny.b64"
if [[ ! -f "$tiny" || "$tiny" -ot "$src" ]]; then
  echo "→ tiny b64:  $tiny"
  frame="$src"; $is_anim_gif && frame="$src[0]"
  magick "$frame" -auto-orient -resize 24 -blur 0x1 -quality 40 jpg:- \
    | base64 | tr -d '\n' > "$tiny"
fi

