# Changelog

## 0.1.3

- Prevent watchdog restarts during uploads by serving health independently of busy
  web workers. Both Docker and Supervisor probe cached service liveness through
  nginx, including direct bounded database/Redis checks and the web listener.
- Mark failed/stale probes unhealthy and log health transitions. Preserve service
  exit handling and Gunicorn worker timeouts; no public ports or data formats change.
- Add a regression test that suspends a disposable instance's web worker while
  health checks continue, plus dependency-failure and probe-staleness tests.

## 0.1.2

- Add an authenticated, provider-independent external-identity API through the existing Flask application.
- Persist account-scoped mappings and optional fenced claims in a companion PostgreSQL schema, covered by cold backups.
- Preserve native workout/media APIs and upstream source files; exclude superseded importer work and private exports.

## 0.1.1

- Restore ownership of persistent service files at startup after Supervisor backup extraction.

## 0.1.0

- Experimental HA app packaging for aarch64 and amd64, based on FitTrackee v1.3.6.
- Bundle PostgreSQL 18/PostGIS, Redis and background workers with private persistent storage.
- Require HTTPS origin and explicit reverse proxy IPs; retain secure cookies.
- Add ordered shutdown, health checks and Supervisor cold-backup configuration.
- Preserve the previous standalone deployment as legacy reference.
