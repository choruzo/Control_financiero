#!/usr/bin/env bash
# generate-certs.sh — Genera certificados SSL locales con mkcert
#
# Prerrequisitos:
#   - mkcert instalado: https://github.com/FiloSottile/mkcert
#     Windows (Chocolatey): choco install mkcert
#     macOS (Homebrew):     brew install mkcert
#     Linux:                ver instrucciones en el README
#
# Uso:
#   bash scripts/generate-certs.sh

set -euo pipefail

CERT_DIR="$(dirname "$0")/../nginx/certs"

if ! command -v mkcert &>/dev/null; then
    echo "ERROR: mkcert no está instalado."
    echo "Instálalo desde: https://github.com/FiloSottile/mkcert"
    echo ""
    echo "  Windows (Chocolatey): choco install mkcert"
    echo "  macOS (Homebrew):     brew install mkcert"
    exit 1
fi

echo "Instalando CA raíz local de mkcert..."
mkcert -install

echo "Generando certificados para localhost..."
mkcert \
    -cert-file "${CERT_DIR}/localhost.pem" \
    -key-file  "${CERT_DIR}/localhost-key.pem" \
    localhost 127.0.0.1

echo ""
echo "Certificados generados en ${CERT_DIR}/"
echo "  localhost.pem"
echo "  localhost-key.pem"
echo ""
echo "Ahora puedes levantar producción con:"
echo "  docker compose up -d --build"
