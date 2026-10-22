# Changelog

## 0.1.1

- Restore ownership of persistent service files at startup after Supervisor backup extraction.

## 0.1.0

- Experimental HA app packaging for aarch64 and amd64, based on FitTrackee v1.3.6.
- Bundle PostgreSQL 18/PostGIS, Redis and background workers with private persistent storage.
- Require HTTPS origin and explicit reverse proxy IPs; retain secure cookies.
- Add ordered shutdown, health checks and Supervisor cold-backup configuration.
- Preserve the previous standalone deployment as legacy reference.

