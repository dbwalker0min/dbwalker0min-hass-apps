# Packaging decision — 2026-10-21

One HA app is selected for the first implementation: a single release/backup boundary is useful for a private, single-user Pi installation. A small Python lifecycle manager under tini owns ordering and fail-fast behavior. PostgreSQL, Redis, workers, web and nginx remain separate child processes and users. This costs more lifecycle maintenance than separate apps, but avoids cross-app database credentials, dependency ordering and inconsistent backups. No Docker-in-Docker or host service is used.

The official postgis/postgis image still has an open ARM64 support issue (https://github.com/postgis/docker-postgis/issues/216). The FitTrackee release image publishes both amd64 and arm64. Its inspected pinned index is Alpine 3.24.2, with PostgreSQL 18.6 and PostGIS 3.6.3 packages available. Alpine publishes PostGIS for both architectures (https://pkgs.alpinelinux.org/packages?name=postgis). Native distro packages inside the multi-architecture app avoid a third-party database image and building PostGIS from source on every Pi.

FitTrackee index pinned to sha256:d452fd42d2a0255e33a9838673496f53f3aa44a43316622edda6298d19a6cc30. Alpine package patch versions are resolved at build time for updates; this is versioned source, not a bit-for-bit reproducible package lock. PostgreSQL major stays 18. Validate package availability and behavior on both architectures before release.

Supervisor cold backups stop all writers before /data is archived: https://developers.home-assistant.io/docs/apps/configuration/#backups. This is simpler than coordinating live SQL dumps with file snapshots. It introduces a brief outage. Same-version recovery must be tested on HAOS; cross-architecture recovery uses logical database dumps, not assumed physical-directory compatibility.

The reverse proxy receives only explicit NPM source IPs, requires the TLS scheme header, overwrites Host/forwarding headers and sends to loopback Gunicorn. This preserves upstream secure cookies and URL scheme handling without ProxyFix accepting arbitrary request headers. NPM owns TLS. No Internet-facing port except NPM HTTPS is required.

Legacy WSL deployment remains untouched. Only non-secret tracked files are copied for reference. The new app starts with its own database and generated secrets; importing the existing account requires an explicit logical transfer later, not copying Windows/WSL runtime paths.

The actual Supervisor restore test exposed restored descendant ownership incompatible with service users. Version 0.1.1 repairs ownership recursively at startup before opening PostgreSQL/Redis or uploads. Top-level-only chown was insufficient. The observed Pi starts all bundled services at roughly 350 MiB RAM; full historical-load performance remains untested.

## Independent liveness — 0.1.3

Both Supervisor `/healthz` and Docker's healthcheck now pass through nginx to a
loopback-only HTTP listener on 127.0.0.1:8082 in the lifecycle manager. Its background
thread probes live child processes, a direct PostgreSQL SELECT 1 over the private
Unix socket, Redis PING, and the Gunicorn TCP listener. Each subprocess is bounded
to two seconds and TCP connection to half a second. Results are refreshed every
five seconds, cached for HTTP consumers, and fail closed if stale for twenty
seconds or stopped. No query, credential, process detail or error body is exposed
by the health endpoint; only transitions with fixed diagnostic labels reach logs.

A single synchronous Gunicorn worker can spend a long time parsing recordings.
Sending liveness HTTP requests through that worker caused false unhealthy results
and Supervisor replacement during an in-flight upload. Liveness therefore checks
the listener without waiting for an application response. Gunicorn retains its
120-second worker timeout, and the existing lifecycle loop still exits when any
managed service dies. The monitor closes before service shutdown. Database checks
are read-only and the Redis probe is PING. No schema, upstream application source,
TLS trust boundary, public port, privilege grant or persistent path changes.

A disposable-container regression suspends the sole Gunicorn worker, confirms the
old HTTP database probe cannot respond, verifies nginx/Docker liveness across
multiple independent probe cycles, resumes the worker, and confirms normal HTTP
requests recover. This test must never be run against the shared HA instance.