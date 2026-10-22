#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
backup_dir="${1:?Usage: bash scripts/verify-backup.sh backups/TIMESTAMP}"
sha256sum -c "$backup_dir/SHA256SUMS"
# Restore into a separate database in the existing DB server; production is untouched.
restore_db="fittrackee_restore_check_$(date +%s)"
cleanup() {
  docker compose exec -T fittrackee-db sh -c 'dropdb -U "$POSTGRES_USER" "$1"' sh "$restore_db"
}
docker compose exec -T fittrackee-db sh -c 'createdb -U "$POSTGRES_USER" "$1"' sh "$restore_db"
trap cleanup EXIT
docker compose exec -T fittrackee-db sh -c 'pg_restore --exit-on-error --no-owner -U "$POSTGRES_USER" -d "$1"' sh "$restore_db" < "$backup_dir/database.dump"
docker compose exec -T fittrackee-db sh -c 'psql -U "$POSTGRES_USER" -d "$1" -c "SELECT version_num FROM alembic_version; SELECT count(*) AS users FROM users; SELECT count(*) AS workouts FROM workouts;"' sh "$restore_db"
# Verify archive extraction independently of the live uploaded files.
docker run --rm -i --user root --entrypoint sh fittrackee/fittrackee:v1.3.6 -c 'mkdir /tmp/restore-files; tar -xzf - -C /tmp/restore-files; test -d /tmp/restore-files/uploads; test -d /tmp/restore-files/.staticmap_cache; echo "File archive extraction passed"' < "$backup_dir/files.tar.gz"
echo 'Isolated database restore and file extraction passed'
