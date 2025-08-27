# Le calendrier centralisé des Associations Universitaires

Solution pour gérer des calendriers partagés entre plusieurs associations universitaires et diffuser les événements publiquement tout au même endroit.

## Prérequis

**Docker** (>=20.10) et **Docker Compose** installés

---

## Comment le stack fonctionne


```mermaid
flowchart TD
  %% --- Frontend public ---
  subgraph Public
    U[Utilisateurs]
    CAL[calendar (nginx)<br/>sert ./calendar-app/public]
    U -->|HTTP 8081| CAL
    EVENTS[(events.json)]
    IMGS[(images/)]
    CAL -->|sert| EVENTS
    CAL -->|sert| IMGS
  end

  %% --- Génération événements & images ---
  subgraph Données["Génération des données"]
    CV[converter<br/>ICS -> JSON & images<br/>INTERVAL=60s]
    FEEDS[(feeds.txt<br/>URLs ICS publics)]
    FEEDS -. RO .-> CV
    CV -->|écrit| EVENTS
    CV -->|copie| IMGS
  end

  %% --- Nextcloud (sources fichiers & images) ---
  subgraph Nextcloud
    A2[Admins/Users]
    NC[nextcloud:31-apache]
    DB[(mariadb:10.11)]
    NCD[(volume nextcloud_data)]
    A2 -->|HTTP 8080| NC
    NC <--> DB
    NCD -. RO pour converter .-> CV
  end

  %% --- Optimisation d'images ---
  subgraph Images
    IMGW[imgworker<br/>surveille /mnt/images<br/>optimise]
    IMGW --> IMGS
  end

  %% --- Mises à jour automatisées ---
  WT[watchtower<br/>--label-enable]
  WT -. met à jour .-> NC
  WT -. met à jour .-> DB

  %% Styles
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


