# Repeatable live attachment tests

Use the dedicated regular account `fittrackee_test` (`fittrackee-test@example.com`), not your personal owner account. It has no administrative role. Its strong random password is stored in ignored `.secrets/live-tests.json`, with private file permissions. Do not commit this file, include it in the app image, or paste it in logs. You can open it locally to sign in manually using the email/password.

From the Windows repository root:

```powershell
# One-time setup; safe to repeat when the saved credentials still exist.
.\fittrackee\tools\Test-FitTrackee.ps1 provision

# Normal on-demand test: generate fixtures, check them, then clean up this run.
.\fittrackee\tools\Test-FitTrackee.ps1 run

# Retain a labeled test ride/photo for browser inspection or persistence checks.
.\fittrackee\tools\Test-FitTrackee.ps1 run -Keep

# Use the checkpoint path printed by the retained run.
.\fittrackee\tools\Test-FitTrackee.ps1 verify -State PATH-TO-CHECKPOINT.json
.\fittrackee\tools\Test-FitTrackee.ps1 cleanup -State PATH-TO-CHECKPOINT.json
```

The wrapper uses Codex's bundled Python if available; otherwise specify `-Python` with a Python 3.10+ executable. No third-party Python packages or Docker Desktop are needed to run the client tests. On Mac/Linux:

```sh
python3 fittrackee/tools/live_tests.py run --config /secure/path/live-tests.json
python3 fittrackee/tools/live_tests.py run --keep --config /secure/path/live-tests.json
python3 fittrackee/tools/live_tests.py verify --state /path/to/checkpoint.json --config /secure/path/live-tests.json
```

Provisioning requires the existing `ha-test` SSH alias and passwordless container administration. It creates the account through FitTrackee's supported CLI. Subsequent run/verify/cleanup commands only need HTTPS and the test credentials. Other machines should securely copy that ignored config file, or use `--config` to point to a protected copy. Do not reprovision an existing account with newly generated credentials if the original file is lost; account recovery/reset requires an explicit separate action.

## What a run checks

- Real HTTPS login and Secure/HttpOnly session cookie, authenticated dedicated profile.
- Upload a generated checkerboard PNG; save its description.
- Create a unique private synthetic GPX activity and attach the image via the documented API.
- Read the activity back; verify the attachment and description.
- Fetch both stored image and thumbnail, validate PNG responses, and save their SHA256 digests.
- Check whether a photo URL is accessible without authentication; report the result.
- By default remove only the exact activity and media created during this run. No bulk cleanup, account reset, personal credentials or direct database manipulation.

Each run writes an ignored `.test-results/RUN-ID.json` report/checkpoint. A failed run preserves its IDs for inspection and explicit cleanup. Retained runs remain until explicitly cleaned up. If a retained activity is manually deleted, a new run can create a fresh one; tests do not depend on an immortal synthetic ride. Do not share checkpoint files casually: they contain media URLs.

`verify` compares the retained image/thumbnail digests after a restart, update, or backup/restore. The ordinary runner does not restart the app, restore HA, or interrupt other users. Schedule those persistence operations explicitly, then rerun verify with the same checkpoint. Restore only a backup that contains that retained run; a test account is data isolation, not an independent deployment, so app restarts/restores still affect everybody.

## Known upstream privacy behavior

On installed FitTrackee 1.3.6, the test image URL is retrievable without a session, despite the activity/media gallery visibility being private. The app uses unguessable media filenames; possessing a URL permits access. This behavior is visible in upstream `fittrackee/media/routes.py` (`get_media`) and was reproduced using only the generated checkerboard. Do not treat gallery visibility as authenticated protection of the underlying image URL. Investigate this before importing personal photographs; this tooling does not change upstream authorization.

No personal photograph is required. No Strava archive is imported. Live test credentials are not sent to GitHub Actions: CI runs only the offline safety tests, not the live sandbox test.
