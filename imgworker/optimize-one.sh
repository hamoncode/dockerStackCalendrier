#!/usr/bin/env bash
# cSpell: disable
set -euo pipefail

f="$1"
[ -f "$f" ] || exit 0
rep=$(echo "$f" | cut -d"." -f1)  # Ne conserver que ce qui vient avant le point
nom=$(echo "$rep" | rev | cut -d "/" -f1 | rev)  # Reverser le string, séparer par '/', prendre le premier (dernier) mot, re-renverser le string
rep=$(echo "$rep" | sed "s/\/${nom}$//g") # Retirer le nom du fichier du chemin
ext=$(echo "$f" | cut -d"." -f2)  # Ne conserver que ce qui vient après le point
echo "répertoire : $rep"
echo "nom : $nom"
echo "extension : $ext"

if [ -f "${rep}/tailles.txt" ]; then
  echo "Déjà fait!"
  exit 0
fi

optjpg() {
  jpegoptim --strip-all --all-progressive --max="${JPEG_QUALITY:-85}" "$1" >/dev/null || true
}

optpng() {
  pngquant --force --skip-if-larger --ext .png --quality="${PNG_MIN_QUALITY:-65}-${PNG_MAX_QUALITY:-85}" "$1" || true
  optipng -o2 -quiet "$1" || true
}

optgif() {
  gifsicle -O3 -b "$1" || true   # in-place
}

optwebp() {
  # Recompress webp via temp file, then atomic replace
  tmp="$(mktemp --suffix=.webp)"
  cwebp -quiet -q "${WEBP_QUALITY:-80}" "$1" -o "$tmp"
  mv -f "$tmp" "$1"
}

echo "optimisation de ${rep}/${nom}.${ext}"
echo "création de ${rep}/${nom}_${ext}/"
mkdir "${rep}/${nom}_${ext}/"
chmod 777 "${rep}/${nom}_${ext}/"

# Créer le registre de tailles
echo "création de ${rep}/${nom}_${ext}/tailles.txt"
registre="${rep}/${nom}_${ext}/tailles.txt"
touch "$registre"
chmod 777 "$registre"

# Détecter la taille de l'image
echo "détection de la taille"
taille=$(file "$f" | grep -E -o "[^A-Z|a-z] [0-9]+ ?x ?[0-9]+" | sed "s/[, ]*//g")
largeur=$(echo "$taille" | cut -d"x" -f1)
hauteur=$(echo "$taille" | cut -d"x" -f2)
n_tailles=$(echo "l($largeur)/l(2)" | bc -l -q | cut -d"." -f1)
echo "déplacement de ${rep}/${nom}.${ext} vers ${rep}/${nom}_${ext}/${nom}-${largeur}.${ext}"
ib="${rep}/${nom}_${ext}/${nom}-${largeur}.${ext}"
mv "$f" "$ib"
echo $taille > $registre

# Optimiser l'image de base
echo "optimisation"
case "$ext" in
  jpg|jpeg) optjpg $ib;;
  png)      optpng $ib;;
  gif)      optgif $ib;;
  webp)     optwebp $ib;;
  *)        ;;    # unknown -> skip
esac
chmod 777 "$ib"

largeur_i=$largeur
hauteur_i=$hauteur
# Changer les tailles
echo "Création de ${n_tailles} images..."
for (( i = 0; i < $n_tailles; i++))
do
  largeur_i=$((largeur_i/2))
  if (($largeur_i < 100));then
    break
  fi
  hauteur_i=$((hauteur_i/2))
  nf="${rep}/${nom}_${ext}/${nom}-${largeur_i}.${ext}"
  # Convertir la taille
  echo "Création de ${nf}"
  convert -resize ${largeur_i}x${hauteur_i} "$ib" "$nf"
  # Optimiser l'image
  case "$ext" in
    jpg|jpeg) optjpg $nf;;
    png)      optpng $nf;;
    gif)      optgif $nf;;
    webp)     optwebp $nf;;
    *)        ;;    # unknown -> skip
  esac
  chmod 777 "$nf"
  echo "${largeur_i}x${hauteur_i}" >> $registre
done