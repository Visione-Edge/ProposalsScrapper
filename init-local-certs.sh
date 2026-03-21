#!/bin/bash
set -e

CERT_DIR="data/certbot/conf/live/proposals.visione-edge.com"

sudo mkdir -p "$CERT_DIR"

sudo openssl req -x509 -nodes \
  -newkey rsa:2048 \
  -days 365 \
  -keyout "$CERT_DIR/privkey.pem" \
  -out "$CERT_DIR/fullchain.pem" \
  -subj '/CN=localhost'

echo "Certificados self-signed creados en $CERT_DIR"
