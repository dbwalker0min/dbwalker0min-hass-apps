# Operations

Run commands in Ubuntu at `/home/dbwal/fittrackee`.

```sh
docker compose up -d --wait           # start
docker compose stop                   # stop without removing data
docker compose restart                # restart
docker compose ps                     # status
docker compose logs --tail=100         # logs
bash scripts/backup.sh                # brief write outage; timestamped backup
```

Open http://desktop.home:3000. The app runs on port 5000 inside Docker. Windows Docker Desktop must be running. The database is not published to the host. Logs use stdout; cache and uploads are writable persistent bind mounts. The official entrypoint applies database migrations automatically at startup.

## Account setup
Supply the intended username and email, then use `docker compose exec fittrackee ftcli users create USERNAME --email EMAIL --role owner --tz America/Los_Angeles`. Without --password, a temporary password is generated. Treat its output as a secret. Alternatively register in the UI and run `docker compose exec fittrackee ftcli users update USERNAME --set-role owner` to activate/promote it. No SMTP is configured.

## Backup and restore
The backup script stops application writes, takes a custom-format PostgreSQL dump, archives uploads and cache, and restarts the app even if backup fails. The backup contains `.env` and must be protected like a password. Copy completed backups off the PC through a secure channel; local backups alone do not protect against disk loss. Run `sha256sum -c backups/TIMESTAMP/SHA256SUMS` from the project directory to verify archives.

For recovery, use an EMPTY deployment directory, the backed-up Compose and .env, and the SAME database/app versions. Start only the database. Copy database.dump into that DB container and restore with `pg_restore --clean --if-exists --no-owner -U fittrackee -d fittrackee /tmp/database.dump`. Restore files.tar.gz into the app's mounted uploads/cache locations using the app image as root, then start normally so the official permission hook runs. Never restore over a live deployment without a separate fresh backup and explicit approval. A backup is not fully verified until restored into an isolated database and files compared.

## Update
1. Read upstream release notes, especially migrations and compatibility.
2. Run a backup and verify its restore before changing versions.
3. Update the pinned app tag in compose.yaml; keep the database major version unchanged.
4. Run `docker compose pull` then `docker compose up -d --wait`.
5. Verify login, activity files, and health. Update PROJECT_STATUS.md with versions and results.

Do not use `docker compose down -v`, remove data/, or downgrade the app against a migrated database. Roll back by restoring the matching backup into an isolated clean deployment.

## Remote work and handoff
From the Mac, SSH into the existing Windows account at desktop.home, run `wsl -d Ubuntu`, and enter this project directory. Continue using Linux Git and Docker there. SSH authentication and access from the Mac still require verification. No additional SSH server or firewall changes are configured.

Read PROJECT_STATUS.md and AGENTS.md at the beginning of each work session; update status before handoff. Commit only configuration and documentation. No Git remote is configured: to transfer source to another machine, configure a user-selected remote or securely copy the non-secret project files. Running data and .env remain on this desktop and need separate secure backups. A Mac checkout can edit configuration, but deployment commands should run on this desktop; the selected PostGIS image is amd64.

Verify a completed backup with: bash scripts/verify-backup.sh backups/TIMESTAMP. This restores into a uniquely named temporary database on the same server, checks migration/user/workout tables, extracts the file archive in an ephemeral container, and drops only that temporary database. It does not test recovery on a separate physical host. Use bash scripts/backup.sh before updates. The files in a backup include secrets; do not publish or commit them.
