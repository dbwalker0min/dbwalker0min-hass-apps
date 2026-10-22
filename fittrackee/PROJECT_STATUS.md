# Project status — FitTrackee Home Assistant app

Updated: 2026-10-22 (America/Los_Angeles)

## Current result
FitTrackee 1.3.6 is running as Home Assistant app 0.1.1 on the sandbox Raspberry Pi 5. Real HTTPS login, activity upload, restart/update persistence, and a scoped Supervisor cold backup/restore have passed. A separate bounded Strava API importer is implemented; no actual export activities have been uploaded.

Active source: C:\Users\dbwal\VSCode\HomeAssistant\dbwalker0min-hass-apps\fittrackee
Repository: https://github.com/dbwalker0min/dbwalker0min-hass-apps
PR #30 is merged. Repeatable test tooling is developed on fittrackee-repeatable-tests.
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
1. PR #30 is merged and both architecture CI builds passed. Use the custom repository for future installs/updates and test on the N100 HAOS server; AMD64 container testing alone is not AMD64 Supervisor verification.
2. Generated photo attachment, description and thumbnail tests now pass in the dedicated test account. Test photo persistence after app restart and a scoped backup/restore using a retained checkpoint; test queued archive tasks and realistic resource use. Photo-link access is an accepted limitation for this family installation and does not block personal photo imports.
3. Make a protected off-device copy of HA backups and verify recovery on a spare target before trusting a full archive. Cross-architecture database moves require logical dump/restore, not assumed portability of a PostgreSQL directory.
4. Choose production target/cutover timing and any distinct sandbox hostname; current public URL points to this sandbox app. No production instance or NPM certificate was replaced.
5. Review a one-ride real-export pilot in the dedicated test account, then validate recording metrics/sensors and photographs before broader import. The offline five-ride plan is a preview only. Decide how E-Bike Ride maps to the available electric-road/electric-mountain sports before selecting those activities. No direct database imports.

Maintain this file after meaningful changes. The owner deleted the earlier synthetic ride. New tests recreate their own fixtures in a dedicated account; cleanup is restricted to exact per-run IDs. Do not print credentials, Supervisor tokens, private runtime environment, or generated app secrets. Operations and scoped restore commands are in SANDBOX.md.

## Repeatable testing — 2026-10-22

Dedicated active regular user: fittrackee_test (fittrackee-test@example.com). A generated password is in local ignored .secrets/live-tests.json with file permissions restricted to the current user/SYSTEM on Windows; never commit or display it. No personal owner credentials are used by the runner.

Use tools/Test-FitTrackee.ps1 from the repository root (or Python 3.10+ tools/live_tests.py). See tests/LIVE_TESTS.md for run, --keep, verify and cleanup commands. Provisioning is one-time via the supported CLI over the existing ha-test SSH alias; ordinary tests use HTTPS only. They require no Docker Desktop and no application update. Default runs generate a unique private ride and checkerboard image, validate description/image/thumbnail, then delete only that run's resources. Kept/failed checkpoints live in ignored .test-results/. A deleted test activity is harmless: the next run creates a new one. State files may contain media URLs; keep them private.

Verified live: initial dedicated-account creation/login, repeat provisioning without password change, kept photo fixture, a second independent run with scoped cleanup, and retained-checkpoint verification. Six offline safety tests pass, including rejection of personal credentials, plain HTTP, cross-origin URLs, foreign checkpoints and changed fixture identities. CI executes offline tests only; no sandbox credentials are published to Actions.

Retained UI fixture: Automated attachment check 5ba8ee8a, checkpoint .test-results/5ba8ee8adf71480182e19c810d33fcc3.json. The owner's original synthetic activity was deleted by the user and is not recreated in that account.

Finding: actual anonymous HTTPS access to a generated photo URL succeeds on upstream FitTrackee 1.3.6. Private media/gallery visibility does not authenticate the static media URL (upstream media/routes.py get_media). Tests use generated images only and report this limitation; no authorization changes were made. Do not assume personal photographs are access-controlled solely by gallery visibility.

No app restart or backup/restore was performed in this tooling session. Use a retained run plus verify for those explicitly scheduled persistence tests; those operations affect the whole app, not only the test account. The installed app remains version 0.1.1.

## Accepted decision: photo-link access — 2026-10-22

The user explicitly accepts FitTrackee 1.3.6 serving an image without login to anyone who can reach the server and knows its exact randomly generated URL. Private gallery visibility does not make the underlying media URL require authentication. This is an upstream application behavior, not a TLS/Nginx Proxy Manager fault.

For this installation used by the user and spouse, retain the existing behavior. It is not a blocker for photo testing, personal photo imports, or the family deployment. No application authorization patch, additional proxy login, or VPN requirement is requested. Keep the observation in test reports as an informational known limitation, not a failing acceptance condition. Do not repeatedly request approval or propose remediation unless the user revisits the decision or the exposure materially changes. Secure cookies, TLS and existing proxy restrictions remain unchanged.

## Strava importer � 2026-10-22

Implemented on fittrackee-strava-import, based on repeatable-test PR #31. See importer/README.md for commands, preservation limits and recovery procedures. Python 3.10+ standard library; no app deployment change or direct database access. Inspect, plan and apply without --execute make zero network requests. Execution requires explicit target-account confirmation, protected credentials and a persistent journal; default one activity, hard maximum 20 per batch.

Private example archive: personal/strava-export.zip, about 422 MiB. Offline inspection found 3,064 activity rows, 3,045 recording references and 19 activities without recordings. Recording formats: 1,896 FIT, 829 GPX, 315 TCX and five unsupported BIN. There are 2,533 Ride and 286 E-Bike Ride rows. Duplicate CSV column names are preserved rather than overwritten. Unrelated profile/contact/login export files are not read.

Photo mapping uses only explicit activity references and media.csv captions. Found 22 missing referenced media files; 75 nonempty Media fields contain separators without usable paths. Missing files, video references and ambiguous sport mappings are reported; relationships are not guessed. Full selected CSV metadata remains in private plans; original recordings are uploaded without conversion after gzip decoding. FitTrackee calculates metrics from recording contents, so CSV totals are retained for review rather than forced into server metrics.

Ignored offline artifacts: personal/strava-inventory.json and personal/pilot-plan.json. The reviewed-preview candidate plan contains five Ride activities, 12 linked photos and one warning, spanning FIT, TCX and GPX. Its archive and payload hashes passed an offline apply validation. It has NOT been executed. All real export activities/photos remain unimported. Keep the ZIP, plans and journals private when moving machines; do not commit them. personal/ and importer/ are excluded from the app Docker context.

Validation: 20 offline tests pass. A separate tiny fictional export was imported through real HTTPS into fittrackee_test: one synthetic GPX ride, one generated checkerboard image, title/private note/source marker/caption/private visibility verified. Repeating with the same journal skipped it; a fresh journal reconciled the remote marker without another workout or photo upload. This retained synthetic fixture is titled Synthetic Strava importer verification; its ignored plans/journals have synthetic- prefixes under personal/. No actual FIT/TCX pilot, bulk import, app restart or backup/restore was performed in this session. Existing accepted photo-link behavior remains informational.

Resume uses account-scoped journals plus exact [strava:ID] private-note markers. Uncertain POST outcomes stop for review instead of automatic retry. Previously imported activities without these markers need separate reconciliation. One journal per account, no concurrent independent importers; the upstream API has no atomic source-ID uniqueness constraint. No automatic rollback, deletion or recreation of deliberately deleted completed activities.
