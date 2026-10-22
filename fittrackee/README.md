# FitTrackee Home Assistant app

Self-contained FitTrackee, PostgreSQL 18/PostGIS, Redis and background workers. Supported targets: Raspberry Pi 5 (`aarch64`) and Intel N100 (`amd64`). This is an experimental app. Native Pi installation and HTTPS have been tested; see PROJECT_STATUS.md for the current recovery results and remaining production checks.

## Install

Add `https://github.com/dbwalker0min/dbwalker0min-hass-apps` to the Home Assistant app store repositories, then install FitTrackee. This first version builds locally on the HA device; no unpublished image is referenced. Initial builds download the release image and Alpine packages. Future releases should publish a tested multi-architecture GHCR image.

Set `external_url` to `https://fittrackee.dbwalker0min.info` and `trusted_proxy_ips` to the exact source IP address(es) Nginx Proxy Manager uses to reach this app. Empty trust lists deliberately prevent startup. CIDRs and wildcards are rejected. Choose a host mapping for port 8080 only if NPM is outside the HA app network; it is disabled by default. The database, Redis and Gunicorn are loopback-only and never published.

## HTTPS through Nginx Proxy Manager

Create a proxy host for `fittrackee.dbwalker0min.info`, forwarding using HTTP to the HA host and mapped backend port (or the app's internal hostname:8080 if NPM shares its Supervisor network). Select the existing wildcard certificate and enable Force SSL. NPM must overwrite `X-Forwarded-Proto` with `$scheme`, preserve the host, and forward the request body; allow sufficiently large uploads (256 MB by default here). Do not copy client-provided forwarding headers blindly. Do not forward the backend port at your router.

The bundled HTTP gate allows only the configured proxy IPs and requires `X-Forwarded-Proto: https`. It then overwrites forwarding headers and the canonical Host before forwarding to loopback Gunicorn. Gunicorn trusts only that loopback gate. Production cookie security remains enabled. `/healthz` is an unauthenticated database-health check only. If routing/NAT makes multiple clients appear as one source, enforce the NPM-only boundary in the network firewall as well; an IP allowlist cannot identify traffic hidden behind that shared address.

Certificates and renewal stay exclusively in NPM. No ingress or Home Assistant authentication bypass is used. FitTrackee retains its own accounts.

## State, shutdown, and backups

Supervisor's private `/data` stores PostgreSQL, Redis queues, uploaded recordings/photos, map cache, options and generated secrets. No Windows paths, WSL services or external database are required. App processes run under separate unprivileged users; only the lifecycle manager performs initialization. It starts PostgreSQL, creates the restricted app role/database/PostGIS extension, starts Redis, applies upstream migrations, then starts workers, web server and HTTP gate. Unexpected service exit stops the entire app.

`backup: cold` makes Supervisor stop the app before archiving `/data`. Shutdown drains web/workers before Redis and PostgreSQL; PostgreSQL receives a fast shutdown and checkpoint. Expect a short outage for backups. Include this app in HA backups. Restore the backup with the same app/PostgreSQL version and architecture first, then verify login, activity statistics, original recording downloads and photographs before upgrading. Physical PostgreSQL data should not be treated as a portable architecture migration format: use a logical dump for cross-architecture moves. A different PostgreSQL major version is refused; no automatic major upgrade occurs.

Do not copy the live PostgreSQL directory. Test an actual HA backup and restore on the sandbox before production. Package installation and migrations are not proof of Supervisor backup correctness.

## Account administration

Register through HTTPS. When shell/container administration is available, supported commands can run through `python /opt/ha-fittrackee/admin.py users update USERNAME --set-role owner`, inside this app container. For creation, use `users create USERNAME --email EMAIL --role owner --tz America/Los_Angeles`; omit a password to generate one and protect its output. The helper loads the private runtime environment; do not print that environment or secrets. SMTP is not configured. The previous Windows account is NOT automatically transferred.

## Development

Build from this folder using `docker build -t fittrackee-ha:test .`. Local Docker is optional development tooling, not a runtime dependency. Use named Docker volumes for `/data` in local lifecycle tests. Never point a development container at the preserved legacy data.

Read [PROJECT_STATUS.md](PROJECT_STATUS.md) and [AGENTS.md](AGENTS.md). `legacy/` preserves the previous deployment source and docs for reference; it is excluded from the image. The original WSL repository, credentials and data remain untouched. The separate [Strava importer](importer/README.md) inspects ZIP exports offline, prepares bounded review plans and imports explicitly selected activities through HTTPS. It stays outside the HA app image.

Current sandbox details and safe scoped commands: [SANDBOX.md](SANDBOX.md).

Repeatable attachment tests use a separate non-admin account: [tests/LIVE_TESTS.md](tests/LIVE_TESTS.md).
