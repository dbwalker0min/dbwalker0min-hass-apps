# Project status â€” FitTrackee Home Assistant app

Updated: 2026-10-23 (America/Los_Angeles)

## Current result
FitTrackee 1.3.6 is running as Home Assistant app 0.1.2 on the sandbox Raspberry Pi 5. Real HTTPS login, activity upload, restart/update persistence, and a scoped Supervisor cold backup/restore have passed. Bulk importing and incremental synchronization are out of scope for this repository.

Active source: C:\Users\dbwal\VSCode\HomeAssistant\dbwalker0min-hass-apps\fittrackee
Repository: https://github.com/dbwalker0min/dbwalker0min-hass-apps
PRs #30 and #31 are merged. PR #32 is superseded and must not be merged. New work starts from merged main on fittrackee-external-identities.
Read AGENTS.md, README.md, ARCHITECTURE.md and SANDBOX.md here before continuing.

## Runtime and network
- Sandbox SSH alias: ha-test; configured existing hassio user/key. Host ha-test.home / 192.168.99.10.
- Actual platform: HAOS 18.3, Supervisor 2026.10.3, HA Core 2026.10.1, raspberrypi5-64, aarch64.
- Supervisor app slug: local_fittrackee, installed from /addons/fittrackee. Version 0.1.2, auto boot and health watchdog enabled.
- Sandbox URL: https://fittrackee-test.dbwalker0min.info. Production URL: https://fittrackee.dbwalker0min.info. Existing NPM on ha.home / 192.168.1.10 terminates TLS using its existing certificate.
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
5. Implement the provider-independent companion external-identity API described in EXTERNAL_IDENTITIES_DESIGN.md. Do not implement a bulk importer or PyScript synchronizer here.

Maintain this file after meaningful changes. The owner deleted the earlier synthetic ride. New tests recreate their own fixtures in a dedicated account; cleanup is restricted to exact per-run IDs. Do not print credentials, Supervisor tokens, private runtime environment, or generated app secrets. Operations and scoped restore commands are in SANDBOX.md.

## Repeatable testing â€” 2026-10-22

Dedicated active regular user: fittrackee_test (fittrackee-test@example.com). A generated password is in local ignored .secrets/live-tests.json with file permissions restricted to the current user/SYSTEM on Windows; never commit or display it. No personal owner credentials are used by the runner.

Use tools/Test-FitTrackee.ps1 from the repository root (or Python 3.10+ tools/live_tests.py). See tests/LIVE_TESTS.md for run, --keep, verify and cleanup commands. Provisioning is one-time via the supported CLI over the existing ha-test SSH alias; ordinary tests use HTTPS only. They require no Docker Desktop and no application update. Default runs generate a unique private ride and checkerboard image, validate description/image/thumbnail, then delete only that run's resources. Kept/failed checkpoints live in ignored .test-results/. A deleted test activity is harmless: the next run creates a new one. State files may contain media URLs; keep them private.

Verified live: initial dedicated-account creation/login, repeat provisioning without password change, kept photo fixture, a second independent run with scoped cleanup, and retained-checkpoint verification. Six offline safety tests pass, including rejection of personal credentials, plain HTTP, cross-origin URLs, foreign checkpoints and changed fixture identities. CI executes offline tests only; no sandbox credentials are published to Actions.

Retained UI fixture: Automated attachment check 5ba8ee8a, checkpoint .test-results/5ba8ee8adf71480182e19c810d33fcc3.json. The owner's original synthetic activity was deleted by the user and is not recreated in that account.

Finding: actual anonymous HTTPS access to a generated photo URL succeeds on upstream FitTrackee 1.3.6. Private media/gallery visibility does not authenticate the static media URL (upstream media/routes.py get_media). Tests use generated images only and report this limitation; no authorization changes were made. Do not assume personal photographs are access-controlled solely by gallery visibility.

No app restart or backup/restore was performed in this tooling session. Use a retained run plus verify for those explicitly scheduled persistence tests; those operations affect the whole app, not only the test account. The installed app remains version 0.1.1.

## Accepted decision: photo-link access â€” 2026-10-22

The user explicitly accepts FitTrackee 1.3.6 serving an image without login to anyone who can reach the server and knows its exact randomly generated URL. Private gallery visibility does not make the underlying media URL require authentication. This is an upstream application behavior, not a TLS/Nginx Proxy Manager fault.

For this installation used by the user and spouse, retain the existing behavior. It is not a blocker for photo testing, personal photo imports, or the family deployment. No application authorization patch, additional proxy login, or VPN requirement is requested. Keep the observation in test reports as an informational known limitation, not a failing acceptance condition. Do not repeatedly request approval or propose remediation unless the user revisits the decision or the exposure materially changes. Secure cookies, TLS and existing proxy restrictions remain unchanged.

## Scope revision — 2026-10-23

User explicitly split the system into three separately maintained components. This repository owns only the FitTrackee HA app and its authenticated provider-independent external-identity API. A future PyPI/uvx bulk importer and a separate HA PyScript synchronizer are out of scope. Do not merge or reuse PR #32 importer code, CLI, archive processing, packaging or tests. PR #31 is confirmed merged; #32 can be closed by the user. Its branch preserves the superseded work; private local archive and artifacts remain untouched and excluded locally.

Review completed against merged main and pinned FitTrackee 1.3.6 code. Design is in EXTERNAL_IDENTITIES_DESIGN.md; the companion API is implemented and deployed to the sandbox as app 0.1.2. See the verification entry below. Existing app and upstream upload/update/media endpoints remain intact. The explicit new feature supersedes earlier instructions requiring upstream code to stay unchanged where necessary; prefer a wrapper rather than modifying upstream files.

Preserved operational corrections from the superseded branch: Supervisor external_url was changed to the sandbox hostname and app restarted on October 22. API image and thumbnail URLs then returned valid PNGs with HTTP 200; browser visually rendered the synthetic checkerboard. Production keeps its own hostname. Actual photos are under /data/files/uploads/media/<user ID>/; the test user is 2. No actual Strava archive activities/photos have been uploaded.

## Companion identity API implementation — 2026-10-23

New branch fittrackee-external-identities starts from merged main/PR #31. PR #32 is closed and none of its importer/CLI/archive code, package or workflow is included. Its operational hostname/storage corrections were documented independently. No bulk importer, PyScript synchronization or provider-specific API logic is implemented here.

App 0.1.2 uses a local Flask app factory and blueprint, reusing upstream 1.3.6 authentication. OAuth read/write scopes and cookie CSRF are enforced; authenticated user IDs come from native auth. Mapping registration/listing requires native workout ownership even for public workouts. PostgreSQL ha_identity schema owns its version table, identity/claim slots, uniqueness and ownership trigger. Upstream public schema/source/API behavior is unchanged. Native workout/account deletion cascades companion references. Startup initializes after upstream migrations, serializes companion migrations and rejects unsupported versions.

Mapping registration is transactional, idempotent for the same target, conflict-only for remaps. Optional claims use hashed client-generated secrets, expiring/fenced reservations and non-expiring uploading state. A repeated begin-upload never grants fresh upload permission. Uncertain upload claims need reconciliation; no exactly-once native upload guarantee is claimed. Contract and failure recovery: EXTERNAL_IDENTITIES_API.md. No new service, proxy, public port or hostname. Companion paths are suppressed in internal access logs; NPM logging remains separately configured.

Validation so far: AMD64 image built; 22 integration tests passed against real PostgreSQL/native auth, including concurrent same/different targets, claim contention/expiry/recovery, per-account namespace, public/private ownership, OAuth scope/revocation, CSRF, native deletion cascades and migration versions. Existing two proxy-configuration and six live-runner guard tests passed. Workflow/config YAML lint passed. CI now runs the isolated identity integration suite on both native architecture runners with no network or real credentials.

Sandbox Pi native update to 0.1.2 completed through Supervisor after pre-update backup 4c3450a9. Real HTTPS anonymous companion request returned 401. Dedicated-account native GPX/photo upload, Secure/HttpOnly login, captions, image/thumbnail delivery, companion mapping registration/retry/listing, and uploading-claim contention all passed. App restart preserved mapping/claim and exact image/thumbnail hashes.

Retained generated fixture: Automated attachment check 2ade8553. Native checkpoint .test-results/2ade855349374b67833147d165762e10.json; protected companion checkpoint .test-results/identity-2ade855349374b67833147d165762e10.json includes synthetic claim secrets. The HTTPS-only tools/identity_smoke.py is restricted to an exact retained managed fixture in fittrackee_test, with bind/verify/cleanup commands; it never uploads workouts or controls HA. No real export data was uploaded. Actual Supervisor cold backup bd30333a (0.1.2) was restored with --app local_fittrackee --homeassistant=false. HTTPS verification passed after restore: the mapping still resolves the exact native workout, the unresolved uploading claim still blocks a competitor, native attachment/caption remain intact, and full image/thumbnail SHA256 match the pre-backup checkpoint. This validates the companion and native data at the same restore point. Protected off-device backup and N100 HAOS device verification remain pending.
