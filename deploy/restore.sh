#!/bin/sh
set -eu

if [ "$#" -ne 3 ] || [ "$1" != "--confirm" ]; then
    echo "Usage: $0 --confirm CHEMIN_DATABASE.dump CHEMIN_MEDIA.tar.gz" >&2
    exit 2
fi

database_dump="$2"
media_archive="$3"
compose_file="${COMPOSE_FILE:-compose.yaml}"

[ -f "$database_dump" ] || { echo "Dump PostgreSQL introuvable" >&2; exit 2; }
[ -f "$media_archive" ] || { echo "Archive média introuvable" >&2; exit 2; }

echo "Arrêt des services applicatifs..."
docker compose -f "$compose_file" stop web worker beat

docker compose -f "$compose_file" exec -T db sh -c \
    'pg_restore --clean --if-exists --no-owner --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' \
    < "$database_dump"

docker compose -f "$compose_file" run --rm --no-deps web \
    sh -c 'find /app/media -mindepth 1 -delete && tar -xzf - -C /app/media' \
    < "$media_archive"

docker compose -f "$compose_file" up -d web worker beat nginx
echo "Restauration terminée. Vérifiez /health/ready/ et les parcours métier critiques."
