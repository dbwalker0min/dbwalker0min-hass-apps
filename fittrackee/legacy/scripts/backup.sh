#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
backup_dir="backups/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"
# Stop application writes while pairing the logical DB dump with uploaded files.
docker compose stop fittrackee
trap 'docker compose start fittrackee >/dev/null' EXIT
docker compose exec -T fittrackee-db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_dir/database.dump"

# Use the app image to read files regardless of host ownership.
docker run --rm --volumes-from "$(docker compose ps -aq fittrackee)" --user root --entrypoint tar fittrackee/fittrackee:v1.3.6 -czf - -C /usr/src/app uploads .staticmap_cache > "$backup_dir/files.tar.gz"
cp compose.yaml "$backup_dir/compose.yaml"
cp .env "$backup_dir/.env"
sha256sum "$backup_dir/database.dump" "$backup_dir/files.tar.gz" > "$backup_dir/SHA256SUMS"
echo "Backup created: $backup_dir (contains secrets and personal data)"
