# FitTrackee app agent instructions

This Windows folder is the active deployment source under dbwalker0min-hass-apps. Treat legacy/ as historical reference, not current instructions. Preserve the old WSL installation and data until the user explicitly authorizes retirement.

- config.yaml: Supervisor metadata/options. Both aarch64 and amd64 are targets, not proof of device testing.
- Dockerfile: pinned upstream image with native PostgreSQL/PostGIS packages. No nested Docker.
- rootfs/opt/ha-fittrackee/: service lifecycle, proxy gate, health and CLI helper.
- tests/: security/configuration and lifecycle checks.
- PROJECT_STATUS.md: actual verification, pending device work, decisions and next steps. Update after meaningful changes.
- legacy/: non-secret original Compose, docs and helpers; excluded from image.

Build with Docker from this Windows folder. Runtime must only depend on HAOS and private /data. Keep Unix scripts LF. Test native amd64 and ARM64; do not label a local container test as HAOS verification. Verify a complete cold HA backup and restore before production. Keep upstream application code unchanged, pin FitTrackee releases, refuse PostgreSQL major-version reuse, and do not auto-upgrade database majors.

Secure cookies must remain enabled. Trust only explicit NPM source addresses at the HTTP gate; trust only the loopback gate in Gunicorn. Never publish PostgreSQL/Redis. Avoid wildcard forwarded-header trust. The app must not manage certificates. No privileged mode, Docker socket, host network or Supervisor API access is required.

Secrets, actual options, credentials, database files, user uploads and backup archives must never enter Git or build context. Ask before destructive operations or significant system changes. Do not implement Strava migration until authenticated HTTPS access and actual archive inspection are complete. Future importer is a separate Python API client.
