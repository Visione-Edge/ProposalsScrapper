#!/bin/bash

# Script de inicialización de certificados Let's Encrypt
# Ejecutar una sola vez en el servidor para obtener el primer certificado

set -e

domains=(sicop.visione-edge.com)
rsa_key_size=4096
data_path="./data/certbot"
email="admin@visione-edge.com"
staging=0 # Poner 1 para probar sin gastar rate limits

echo "### Descargando parámetros TLS recomendados ..."
mkdir -p "$data_path/conf"
if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
fi

echo "### Creando certificado dummy para que Nginx pueda arrancar ..."
path="/etc/letsencrypt/live/$domains"
mkdir -p "$data_path/conf/live/$domains"
docker compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1 \
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot

echo "### Arrancando Nginx ..."
docker compose up --force-recreate -d nginx

echo "### Eliminando certificado dummy ..."
docker compose run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$domains && \
  rm -Rf /etc/letsencrypt/archive/$domains && \
  rm -Rf /etc/letsencrypt/renewal/$domains.conf" certbot

echo "### Solicitando certificado real de Let's Encrypt ..."
if [ $staging != "0" ]; then staging_arg="--staging"; fi

docker compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    --email $email \
    -d ${domains[0]} \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --force-renewal" certbot

echo "### Recargando Nginx con certificado real ..."
docker compose exec nginx nginx -s reload

echo ""
echo "=== HTTPS configurado exitosamente para ${domains[0]} ==="
echo "=== Visitá https://${domains[0]} ==="
