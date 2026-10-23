# Validation notes

- Run test_configuration.py inside the app image; it uses Linux's pwd module.
- proxy_smoke.py is only for the isolated synthetic local test setup. It deliberately relays a Secure cookie over the private HTTP hop to emulate TLS termination, not disable cookie security.
- fixtures/synthetic-ride.gpx is fabricated at the equator and contains no personal route data.
- Native ARM installation, real NPM HTTPS, account and synthetic GPX upload were tested on HAOS Pi 5. Details live in PROJECT_STATUS.md/SANDBOX.md.
- Actual HA cold restore exposed root-owned descendants; 0.1.1 recursively repairs ownership. A simple Docker tar copy preserving Unix ownership would not catch this Supervisor-specific regression.
- A production release also needs a real photograph/metadata restore check, archive worker load test and AMD64 HAOS device validation.

For repeatable real HTTPS/photo checks using the dedicated regular account, read [LIVE_TESTS.md](LIVE_TESTS.md). Default runs clean up only their own fixtures; use --keep and a checkpoint for persistence tests. Generated-image upload and delivery have now passed, but photo backup/restore remains pending.
