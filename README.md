# Le calendrier centralisé des Associations Universitaires

Solution pour gérer des calendriers partagés entre plusieurs associations universitaires et diffuser les événements publiquement tout au même endroit.

## Prérequis

**Docker** (>=20.10) et **Docker Compose** installés

---

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


