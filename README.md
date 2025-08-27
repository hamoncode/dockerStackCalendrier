# Installation du serveur docker

## Prérequis

**Docker** (>=20.10) et **Docker Compose** installés sur votre machine.

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

3. Partir le stack avec Docker Compose 

```bash

docker-compose up -d --build

```

4. Accéder à l'interface web de Nextcloud pour finaliser l'installation.

example: 
port 8080 --> http://localhost:8080 (nextcloud)
port 8081 --> http://localhost:8081 (Calendrier des Assos)

---


## 1. importer les secrets dans `.env`

```bash
cp .env.secret .env
```

## 2. Rendre le script d’initialisation exécutable

```bash
chmod +x scripts/initialize.sh
```

## 3. Lancer le stack

```bash
# démarre la base de données, Nextcloud et le Tunnel Cloudflare
docker-compose up -d
```

## 4. Finaliser l’installation via l’interface Web

1. Ouvrez votre navigateur sur **https\://`${NEXTCLOUD_HOST}`**.
2. Créez l’utilisateur **admin** et son mot de passe.
3. Les informations de la base de données sont pré-remplies depuis `.env`.
4. Terminez l’assistant d’installation.

> Dès le démarrage, `scripts/initialize.sh` s’exécute automatiquement pour :
>
> * activer uniquement l’application **Calendrier**,
> * désactiver les apps inutiles,
> * créer le groupe `calendar-creators` et ses utilisateurs,
> * partager le calendrier en lecture publique et avec droits d’édition pour le groupe.

## 5. Configurer le tunnel Cloudflare (ou le port forwarding au choix)

pour tester l'application on la host sur un serveur proxmox avec un tunnel Cloudflare. 

## 6. Étapes post-installation

```bash
# réparer la configuration et vider le cache
docker-compose exec nextcloud occ maintenance:repair
# optionnel : nettoyer le cache des fichiers
docker-compose exec nextcloud occ files:cleanup
```

## steps d'installation docker-compose

```bash
# créer le réseau Docker si nécessaire
docker network create web || true

# lancer le stack

docker-compose up -d

# vérifier que tout est en ordre
docker-compose ps

# vérifier les logs

docker-compose logs -f

# pour arrêter le stack
docker-compose down
```
