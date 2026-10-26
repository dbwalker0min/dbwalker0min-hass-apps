# Validation notes

- Run test_configuration.py inside the app image; it uses Linux's pwd module.
- proxy_smoke.py is only for the isolated synthetic local test setup. It deliberately relays a Secure cookie over the private HTTP hop to emulate TLS termination, not disable cookie security.
- fixtures/synthetic-ride.gpx is fabricated at the equator and contains no personal route data.
- Native ARM installation, real NPM HTTPS, account and synthetic GPX upload were tested on HAOS Pi 5. Details live in PROJECT_STATUS.md/SANDBOX.md.
- Actual HA cold restore exposed root-owned descendants; 0.1.1 recursively repairs ownership. A simple Docker tar copy preserving Unix ownership would not catch this Supervisor-specific regression.
- A production release also needs a real photograph/metadata restore check, archive worker load test and AMD64 HAOS device validation.

For repeatable real HTTPS/photo checks using the dedicated regular account, read [LIVE_TESTS.md](LIVE_TESTS.md). Default runs clean up only their own fixtures; use --keep and a checkpoint for persistence tests. Generated-image upload and delivery have now passed, but photo backup/restore remains pending.

## Companion identity integration

From the repository root on a Docker-capable Linux CI runner: `sh fittrackee/tests/run_identity_tests.sh fittrackee-ha:test`. This boots an isolated container with PostgreSQL, no network, its own disposable volume and example-only options. It runs real cookie/CSRF and OAuth authentication, owner checks, concurrency, claim fencing/recovery, database constraints/deletion cleanup and schema-version tests. The script removes only its own named container/volume. No sandbox credentials, personal archives or existing runtime volumes are mounted.

On Windows, launch the same isolated image and test mounts, wait for the built-in healthcheck, then run `docker exec -e IDENTITY_TEST_MODE=isolated CONTAINER python /tests/test_identity_api.py`. That environment flag is a guard; never set it on the shared Pi instance. Tests create temporary users/workouts and use direct SQL only inside the isolated integration database.

For an exact retained live_tests.py checkpoint in the dedicated regular test account, use `python fittrackee/tools/identity_smoke.py bind --fixture CHECKPOINT --state PRIVATE_COMPANION_CHECKPOINT`. This binds only that existing synthetic workout and creates an unresolved synthetic claim. `verify` checks the mapping, claim and native workout/image hashes across an explicitly scheduled restart/backup/restore; `cleanup` removes only its exact synthetic mapping/claim, keeping the workout/photo. It does not perform HA administration. Companion checkpoints contain test claim secrets; they are ignored and protected like credentials. Never use personal accounts or old-origin checkpoints.

## Independent health regression

`test_health.py` uses only the Python standard library and runs both locally and
inside the app image. It checks bounded service probes, busy listeners, cached
HTTP health, failure/recovery, stale probes, and sanitized error reporting.

`run_identity_tests.sh` also runs `test_health_integration.py` before the identity
suite. It uses the same isolated disposable container, suspends only its Gunicorn
workers, confirms application HTTP is blocked while health stays responsive, then
resumes workers in a finally block. The IDENTITY_TEST_MODE=isolated guard is
required; never invoke this test on a shared app. Native AMD64/ARM64 CI runs both.