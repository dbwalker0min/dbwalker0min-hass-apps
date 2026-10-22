# Project status — FitTrackee Home Assistant app

Updated: 2026-10-21 (America/Los_Angeles)

## Current result
FitTrackee 1.3.6 is running as Home Assistant app 0.1.1 on the sandbox Raspberry Pi 5. Real HTTPS login, activity upload, restart/update persistence, and a scoped Supervisor cold backup/restore have passed. No Strava importer is implemented.

Active source: C:\Users\dbwal\VSCode\HomeAssistant\dbwalker0min-hass-apps\fittrackee
Repository: https://github.com/dbwalker0min/dbwalker0min-hass-apps
Review branch: fittrackee-ha-app. Main remains unchanged pending review.
Read AGENTS.md, README.md, ARCHITECTURE.md and SANDBOX.md here before continuing.

## Runtime and network
- Sandbox SSH alias: ha-test; configured existing hassio user/key. Host ha-test.home / 192.168.99.10.
- Actual platform: HAOS 18.3, Supervisor 2026.10.3, HA Core 2026.10.1, raspberrypi5-64, aarch64.
- Supervisor app slug: local_fittrackee, installed from /addons/fittrackee. Version 0.1.1, auto boot and health watchdog enabled.
- Public URL: https://fittrackee.dbwalker0min.info. Existing NPM on ha.home / 192.168.1.10 terminates TLS using its existing certificate.
- NPM route points to sandbox 192.168.99.10:3001. App 8080 maps to 3001. Port 3000 belongs to Z-Wave JS UI; it was not changed.
- Proxy gate trusts only 192.168.1.10, verified in actual access logs. Requires HTTPS forwarding header, replaces Host/forwarded headers, and proxies to loopback Gunicorn. Secure cookies remain enabled. No certificate management in the app.
- PostgreSQL, Redis and Gunicorn bind to loopback, never published. Only restricted HTTP gate has a host mapping. No router/firewall changes made.

## Packaging
- Upstream multi-architecture FitTrackee v1.3.6 image pinned by index digest. Native Alpine PostgreSQL 18/PostGIS packages avoid the unsupported AMD64-only database-image dependency.
- Includes Redis and background workers. All durable database, original recordings/photos, queues, cache, options and generated secrets live in Supervisor /data.
- Lifecycle manager under tini starts dependencies/migrations before workers/web/proxy; stops writers before data services; exits if any child fails. Refuses PostgreSQL major-version mismatch.
- backup: cold requests a stopped, consistent Supervisor archive. Version 0.1.1 repairs descendant ownership before service startup: top-level-only ownership repair in 0.1.0 failed after a real Supervisor restore.
- No Docker Desktop, Windows paths, WSL services, host networking, Docker socket or HA API permission is required at runtime. SMTP not configured.
- Existing Jupyter release workflow scoped to Jupyter's version. FitTrackee has an independent native AMD64/ARM64 validation workflow. Initial custom-repository installs build from source; no nonexistent GHCR image is referenced.

## Verification passed
- AMD64 image build, configuration tests and YAML lint.
- Native ARM64 build/install and initialization on the actual Pi (local desktop cross-build failed only because ARM emulation is not installed; no privileged host changes made).
- Local trusted-proxy simulation: insecure scheme returns 400; untrusted source returns 403 even with spoofed forwarding headers; Secure/HttpOnly login cookie and authenticated profile pass.
- Real HTTPS login and authenticated profile pass through actual NPM with normal secure-cookie handling. The Pi itself cannot loop back through the public hostname, so client-side HTTPS tests ran from Windows; this is a network-test limitation, not a runtime dependency.
- Owner dbwalker0min created with explicitly approved supplied email/password. No credentials entered Git. They remain in the preserved ignored WSL secret file; the Pi stores its account hash in PostgreSQL.
- Private synthetic GPX ride uploaded through real HTTPS API: 'Deployment verification - synthetic ride', 2026-10-21, 0.33 km, 3 minutes. ID ChVUe7ChWDvUtKVeSNnt4T. This is not a real ride or a Strava import.
- App restart and 0.1.0 -> 0.1.1 update preserved account, activity and recordings.
- Actual app-only HA cold backup 18cb9211 (0.1.1) restored using --app local_fittrackee --homeassistant=false. Automatic ownership repair worked; HTTPS login/profile, ride metrics, and original GPX SHA256 exactly matching the uploaded fixture passed after restore.
- Earlier backup e9469828 contains the 0.1.0 image, which needs the 0.1.1 ownership fix to start after restore; prefer 18cb9211. Backup archives contain private data/secrets and are stored on HA; do not upload them to GitHub.
- Local stopped-volume backup/restore and image recreation also passed with isolated synthetic data. Local test containers are stopped; their volumes are retained.
- Observed idle Pi app memory about 350 MiB. Full historical-load performance untested.

## Preserved work
Original WSL repository /home/dbwal/fittrackee, runtime, account, .env and backups were not deleted or moved. It is historical, not a dependency of the Pi deployment. Non-secret source/docs from its last prior commit f739a4c are copied under legacy/ (excluded from image). The old WSL status/instructions point here. No original personal activity data existed there to migrate.

## Remaining before production
1. Review/merge the GitHub changes and use the custom repository for future installs/updates. Validate both architecture CI jobs and test on the N100 HAOS server; AMD64 container testing alone is not AMD64 Supervisor verification.
2. Test a photograph attachment and its backup/restore; test a queued archive task and realistic Pi storage/resource use. Existing original GPX/account restoration has passed.
3. Make a protected off-device copy of HA backups and verify recovery on a spare target before trusting a full archive. Cross-architecture database moves require logical dump/restore, not assumed portability of a PostgreSQL directory.
4. Choose production target/cutover timing and any distinct sandbox hostname; current public URL points to this sandbox app. No production instance or NPM certificate was replaced.
5. Examine the actual Strava export structure before designing a separate resumable, duplicate-safe Python API importer for recordings, metadata and photos. Do not implement direct database imports.

Maintain this file after meaningful changes. Do not delete the retained synthetic ride without approval. Do not print credentials, Supervisor tokens, private runtime environment, or generated app secrets. Operations and scoped restore commands are in SANDBOX.md.
