# calendar-app/Dockerfile

FROM nginx:stable-alpine

# Copy your built static site (HTML, JS, JSON, images…) into nginx’s web root
COPY public/ /usr/share/nginx/html/

# Expose HTTP
EXPOSE 80

# (No CMD needed—nginx starts by default)

