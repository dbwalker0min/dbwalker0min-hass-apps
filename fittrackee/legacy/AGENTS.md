# FitTrackee workspace instructions

## Scope and structure
This is a local deployment workspace, currently at /home/dbwal/fittrackee in Ubuntu WSL2. It is not an upstream FitTrackee source checkout. The preferred future location is /home/dbwal/projects/fittrackee; do not move the active workspace without coordinating the workspace change.

Repository structure:
- compose.yaml: local production deployment derived from official upstream Compose.
- .env: local credentials and application configuration; never commit or print secrets.
- .env.example: non-secret configuration template.
- docs/: audit, operations, architectural decisions and backup/restore instructions.
- scripts/: deployment and backup helpers; future migration scripts only after examining the actual export.
- upstream/: optional separate upstream checkout; avoid changing application code for deployment.

## Commands and services
Run Docker Compose from Ubuntu in the deployment directory. Docker Desktop provides the engine through WSL integration; do not install another Docker daemon.
Deployment files are present. Operational commands are docker compose config --quiet, docker compose up -d, docker compose ps, docker compose logs --tail=100, docker compose stop, and docker compose restart. Do not use down -v or delete data directories.
Use the official version-pinned FitTrackee image and compatible PostGIS database. The reviewed production configuration uses internal application port 5000; publish Windows host port 3000. Keep the database private. Start with app and database for one user. Redis and workers are needed for archive uploads and other background features; evaluate before migration.

## Verification
Validate Compose without printing expanded secrets. Check database and app health, /api/check-db, the login flow, and desktop.home:3000 access. Verify a test activity and account survive container recreation. Test remote access from the Mac; a Windows-local request alone does not prove LAN access. Run backup and isolated restore verification before bulk import or upgrades.

## Secrets and data
Exclude .env, data/, backups/, logs, exports and personal activity files from Git before creating them. Use generated credentials and a stable application secret. Store database and uploads persistently; back them up together. Pin image versions and review release migrations before updates. Never upgrade the PostgreSQL major version by just changing its image tag.

## Decisions and limits
Use official installation guidance and production Compose, not the retired docker-fittrackee sample. Prefer existing Windows SSH plus wsl -d Ubuntu for Mac access. Avoid new SSH daemons, firewall rules, port proxies or elevation unless demonstrated necessary. Keep deployment changes separate from upstream code. Do not implement Strava migration until deployment works and the real archive has been examined. Ask before destructive actions or significant system changes.

## Handoff
Maintain PROJECT_STATUS.md after each meaningful change. It must record actual verification, remaining work, deployment location and versions without secrets. See docs/operations.md for operational commands. Deployment configuration now exists; use docker compose config --quiet before changes.

