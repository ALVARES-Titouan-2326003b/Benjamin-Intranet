#!/bin/sh
set -eu

compose_file="${COMPOSE_FILE:-compose.yaml}"
backup_root="${BACKUP_DIR:-./backups}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="${backup_root}/${timestamp}"

case "$backup_root" in
    ""|"/") echo "BACKUP_DIR non sûr" >&2; exit 2 ;;
esac

mkdir -p "$destination"

docker compose -f "$compose_file" exec -T db sh -c \
    'pg_dump --format=custom --no-owner --username="$POSTGRES_USER" "$POSTGRES_DB"' \
    > "${destination}/database.dump"

docker compose -f "$compose_file" exec -T web \
    tar -czf - -C /app/media . > "${destination}/media.tar.gz"

sha256sum "${destination}/database.dump" "${destination}/media.tar.gz" \
    > "${destination}/SHA256SUMS"

echo "Sauvegarde créée dans ${destination}"
