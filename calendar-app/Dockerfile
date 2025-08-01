# Utilise Nginx pour servir du contenu statique
FROM nginx:stable-alpine

# On copie notre dossier public dans la racine d’Nginx
COPY public/ /usr/share/nginx/html/

# Expose le port 80
EXPOSE 80

# Pas de CMD à redéfinir, Nginx démarre automatiquement

