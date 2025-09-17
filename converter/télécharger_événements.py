#!/usr/bin/env python3
"""
Ce module importe les événements des calendriers Nextcloud, les convertis dans leur format json lisible par la page web et télécharge les images.
"""
import json
import hashlib
import shutil
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

import requests
from icalendar import Calendar, Event

EXTENSIONS_PERMISES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

FILS_ICALENDAR = Path("/config/fils_ics.txt")
SORTIE_ÉVÉNEMENTS = Path("calendar-app/public/events.json")
SORTIE_IMAGES = Path("calendar-app/public/images/")
RACINE_NEXTCLOUD = Path("/ncdata")

def analyser_fichier_fils_ics(répertoire: str) -> dict[str, str]:
    """
    Renvoie un dictionnaire qui lie le nom de chaque association avec le lien du fil icalendar qui lui est associée dans un fichier texte
    Le fichier doit être formaté comme suit :
    ```
    NOM=http://nom.domaine.com/reste-de-l'url
    NOM2=http://nom.domaine.com/reste-de-l'url
    ```
    Le nom indiqué est utilisé pour identifier l'association plus tard dans le reste de ce script. 
    Il est donc important que le nom soit identique au nom de l'association.
    """
    fils_ics = {}
    rép = Path(répertoire)
    if not rép.exists():
        print("[ERREUR] import_events.analyser_fichier_fils_ics(): le répertoire spécifié n'existe pas")
        return fils_ics
    
    for ligne in rép.read_text('utf-8').splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        assoc, lien = ligne.split("=", 1)
        fils_ics[assoc.strip()] = lien.strip()
    return fils_ics

def hacher_fichier(rép: Path) -> str:
    """
    Renvoie un hache d'un fichier spécifié par 'rép'
    """
    h = hashlib.sha256()
    with rép.open("rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

def enregistrer_fichiers_joints(vévénement: Event, assoc: str, utilisateur: str) -> Path | None:
    """
    Enregistre les fichiers joints à l'événement spécifié dans calendar-app/public/images/<assoc>/<nom-image>
    vévénement -- Événement source
    assoc -- Association étudiante avec laquelle l'événement est associé
    utilisateur -- Nom d'utilisateur du compte Nextcloud qui a créé l'événement
    Renvoie le répertoire dans lequel a été enregistré la ressource 
    """
    
    # Le conteneur docker qui roule ce script monte les volumes du conteneur Nextcloud et de celui de la page web dans son volume.
    # Afin de télécharger les images attachées à l'événement, cette fonction ira directement copier le fichier du volume Nextcloud
    #   à celui de la page web, évitant ainsi de passer par webdav et d'avoir à gérer les mots de passes.
    #
    # !! CETTE MÉTHODE IMPLIQUE QUE LES IMAGES SUR LES CALENDRIERS EXTÉRIEURS NE SONT PAS SUPPORTÉS !!
    #
    # Les images ajoutées aux événements en les téléchargeant depuis l'interface de l'application Calendrier se trouveront dans le 
    #   volume de Nextcloud sous le répertoire '/data/<assoc>/files/Calendar/'. Comme ce volume est monté sous '/ncdata', le répertoire
    #   complet devient : '/ncdata/data/<assoc>/files/Calendar/<nom-du-fichier>'.
    # TODO: Ajouter du support pour les fichiers téléchargés, puis liés à l'événement par la suite
    #
    # Afin de détecter le fichier joint dans l'événement, le standard iCalendar propose l'attribut 'ATTACH', contenant des informations
    #   sur les fichiers joints. L'une de ces information est le nom du fichier, sous 'FILENAME'.
    
    # Passer à travers les attributs de l'événement jusqu'à frapper le 'ATTACH'
    attributs: list[tuple[str,object]] = vévénement.property_items()
    for clé, attribut in attributs:
        if not clé == "ATTACH":
            continue
        
        nom_fichier = attribut.params.get("FILENAME")[1:] # Le nom est toujours écrit en débutant avec "/", ce qui mélange la combinaison de répertoires.
        if not nom_fichier:
            break
        # Si le fichier ne correspond pas à une image, ne pas s'en soucier
        if not "."+nom_fichier.split(".")[-1] in EXTENSIONS_PERMISES:
            break
        
        répertoire_source = RACINE_NEXTCLOUD / "data" / utilisateur / "files/Calendar" / nom_fichier
        répertoire_sortie = SORTIE_IMAGES / assoc / nom_fichier
        répertoire_sortie.parent.mkdir(parents=True, exist_ok=True)
        
        try :
            # Vérifier si le fichier est déjà là avant de le copier
            if répertoire_sortie.exists():
                if (
                    répertoire_source.stat().st_size != répertoire_sortie.stat().st_size or # Première vérification rapide de base
                    hacher_fichier(répertoire_source) != hacher_fichier(répertoire_sortie)  # Vérifier par hache
                    ):
                    shutil.copy2(répertoire_source, répertoire_sortie)  # Copier le fichier
            else :
                shutil.copy2(répertoire_source, répertoire_sortie) # Copier le fichier
        except Exception as e:
            print(e)
            return None # Le fichier n'a pas été copié, affirmer qu'il n'y en a pas

        return répertoire_sortie
    
    return None # Aucun attribut 'ATTACH' trouvé

def main():
    # Charger les fils iCalendars
    fils_ics = analyser_fichier_fils_ics(FILS_ICALENDAR)

    if not fils_ics:
        print("!! Aucun fil iCalendar configuré, rien à faire")
        return 0

    SORTIE_ÉVÉNEMENTS.parent.mkdir(parents=True, exist_ok=True)

    événements_json = []
    compte = 1  # Compte des événements créés. Utilisé pour leur donner un ID

    # Passer à travers les fils ics configurés. Chaque fil est un calendrier, associé à une association.
    for assoc, url_brute in fils_ics.items():
        # request ne supporte pas le préfixe 'webcal://'. Remplacer par 'http://'
        url = url_brute if not url_brute.startswith("webcal://") else "http://"+url_brute[len("webcal://"):]
        
        print(f"Extraction {assoc} → {url}")
        if not url:
            print(f"!! {assoc}: URL vide, sauté.")
            continue

        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            cal = Calendar.from_ical(resp.content)
        except Exception as e:
            print(f"!! {assoc}: extraction/analyse échouée: {e}")
            continue
        
        # Il se pourrait que le nom d'utilisateur Nextcloud soit différent du nom du calendrier. 
        # Nextcloud fournit le nom d'utilisateur dans le nom du calendrier, sous le format suivant : 
        # NOM_CAL (NOM_UTILISATEUR)
        utilisateur = cal.calendar_name.split(" ")[1].replace("(","").replace(")","")
        
        for vévénement in cal.walk("VEVENT"):
            évén_début = vévénement.get("dtstart").dt.strftime("%Y-%m-%d")
            évén_fin   = vévénement.get("dtend").dt.strftime("%Y-%m-%d") if vévénement.get("dtend") else None

            description = str(vévénement.get("description", ""))

            img_extraites = enregistrer_fichiers_joints(vévénement, assoc, utilisateur)

            img_lien = None
            if img_extraites:
                try:
                    rel = img_extraites.relative_to(Path("calendar-app/public"))
                    img_lien = "/"+str(rel).replace("\\", "/")
                except ValueError:
                    img_lien = f"images/{img_extraites.name}"
            else:
                # TODO use category directive instead of a global default
                img_lien = None
             
            try:
                img_lien = quote(img_lien)
            except Exception as e:
                print(f"[WARN] normalize_root_url failed for {img_lien!r}: {e}")
                img_lien = None

            lien_inscription = None
            mots = re.split("[ \n\t\(\)\{\}\[\]]",description)
            for m in mots:
                if m.startswith("http://") or m.startswith("https://"):
                    lien_inscription = m

            événement_json = {
                "id":     str(compte),
                "title":  str(vévénement.get("summary")),
                "start":  évén_début,
                **({"end": évén_fin} if évén_fin else {}),
                "allDay": not isinstance(évén_début, datetime),
                "extendedProps": {
                    "association": assoc,
                    "description": description,
                    "location":    str(vévénement.get("location", "")),
                    "image": img_lien,
                    "registrationLink": lien_inscription
                }
            }

            événements_json.append(événement_json)
            compte += 1

    with SORTIE_ÉVÉNEMENTS.open("w", encoding="utf-8") as fichier:
        json.dump(événements_json, fichier, ensure_ascii=False, indent=2)

    print(f"Wrote {len(événements_json)} events to {SORTIE_ÉVÉNEMENTS}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
