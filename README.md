# Le calendrier centralisé des Associations Universitaires

Solution pour gérer des calendriers partagés entre plusieurs associations universitaires et diffuser les événements publiquement tout au même endroit.

## Prérequis

**Docker** (>=20.10) et **Docker Compose** installés

---

## Comment le stack fonctionne


```mermaid
flowchart TD
    %% --- Frontend public ---
    U[(Utilisateurs)] -->|"HTTP :8081"| CAL[calendar (nginx)\nsert ./calendar-app/public]
    CAL -->|"sert"| EVENTS[(events.json)]
    CAL -->|"sert"| IMGS[(images/)]

    %% --- Génération événements & images ---
    CV[converter\nICS → JSON + import d'images\nINTERVAL=60s] -->|"écrit"| EVENTS
    CV -->|"dépose / met à jour"| IMGS
    FEEDS[(feeds.txt\nURLs ICS publics)] -. "monté RO" .-> CV

    %% --- Nextcloud (sources fichiers & images) ---
    A2[[Admins/Users]] -->|"HTTP :8080"| NC[nextcloud:31-apache]
    NC <--> DB[(mariadb:10.11)]
    NC --- NCD[(volume nextcloud_data)]
    NCD -. "monté RO" .-> CV
    note right of NCD
      Images attendues dans :
      /ncdata/data/{slug}/files/Calendar
    end

    %% --- Optimisation d'images ---
    IMGW[imgworker\nsurveille /mnt/images] -->|"optimise"| IMGS

    %% --- Mises à jour automatisées ---
    WT[watchtower\n--label-enable] -. "met à jour" .-> NC
    WT -. "met à jour" .-> DB
    note right of WT
      Surveille seulement les conteneurs
      avec le label watchtower.enable=true
    end

    %% Styles pour repérer rapidement les volumes/fichiers
    classDef vol fill:#eef,stroke:#88a,stroke-width:1px;
    class EVENTS,IMGS,NCD,FEEDS vol;

```

## Comment déployer le stack

1. Cloner ce dépôt Git :

```bash

git clone https\://github.com/votre-utilisateur/votre-repo.git

cd dockerStackCalendrier

```

2. Créer et éditer le fichier `.env` en vous basant sur `.env.example` :

```bash

cp .env.example .env

# Éditez `.env` avec vos valeurs (ex. `NEXTCLOUD_HOST`, `DB_PASSWORD`, etc.)

nano .env

```

3. créer réseaux docker web

```bash
docker network create web || true

```

4. Partir le stack avec Docker Compose 

```bash

docker-compose up -d --build

```

4. Accéder à l'interface web de Nextcloud pour finaliser l'installation.

example: 
port 8080 --> http://localhost:8080 (nextcloud)
port 8081 --> http://localhost:8081 (Calendrier des Assos)

---


