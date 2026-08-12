#!/bin/sh
set -eu

compose_file="${COMPOSE_FILE:-compose.yaml}"

test -f .env.production || {
    echo "Créez .env.production à partir de .env.production.example" >&2
    exit 2
}
test -f deploy/certs/fullchain.pem || { echo "Certificat TLS manquant" >&2; exit 2; }
test -f deploy/certs/privkey.pem || { echo "Clé privée TLS manquante" >&2; exit 2; }

docker compose -f "$compose_file" config --quiet
docker compose -f "$compose_file" build

if [ -n "$(docker compose -f "$compose_file" ps --status running -q db)" ] && \
   [ -n "$(docker compose -f "$compose_file" ps --status running -q web)" ]; then
    echo "Sauvegarde de sécurité avant migration..."
    sh deploy/backup.sh
fi

docker compose -f "$compose_file" up -d

echo "Attente de la disponibilité de l'application..."
attempt=0
until docker compose -f "$compose_file" exec -T web python -c \
    "import urllib.request; r=urllib.request.Request('http://127.0.0.1:8000/health/ready/', headers={'X-Forwarded-Proto':'https'}); urllib.request.urlopen(r, timeout=5)"
do
    attempt=$((attempt + 1))
    [ "$attempt" -lt 30 ] || { echo "Application indisponible" >&2; exit 1; }
    sleep 2
done

docker compose -f "$compose_file" exec -T web python manage.py check --deploy
docker compose -f "$compose_file" ps
echo "Release déployée avec succès."
