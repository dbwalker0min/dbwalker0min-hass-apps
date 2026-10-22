# Strava export importer — bounded pilot

This separate Python 3.10+ utility reads a Strava account-export ZIP and uses the documented FitTrackee API. It is excluded from the HA app image. Standard library only; no direct database access, desktop service dependency, Strava login, or bulk-import command.

**The real export has only been inspected and planned. No real Strava ride or photograph has been uploaded.** The only live importer validation used a fabricated one-ride/one-checkerboard ZIP in fittrackee_test.

## Your example export

The ignored personal/strava-export.zip contains 3,064 activity rows, 3,045 referenced recording files (all present), and 613 media.csv entries. Recording payloads: 1,896 FIT, 829 GPX, 315 TCX and 5 unsupported BIN. Most are individually gzip-compressed. There are 19 activities without recording files.

Photo associations come only from explicit pipe-separated paths in activities.csv's Media column, with captions from media.csv. There are 22 missing referenced media files and 75 activities with only a media marker and no usable filenames. Those are reported; no association is inferred from dates, filenames or directory order. Videos are skipped. Other export files (contacts, messages, logins, payments, profile, etc.) are not used by the importer.

Several activity CSV headers repeat. Both copies are retained (for example Distance and Distance#2), rather than silently overwriting one. The plan preserves all selected original CSV fields and full captions locally.

## Offline first

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run from the Windows repository root. The wrapper uses the committed pyproject.toml, Python version and uv.lock to create/update importer/.venv automatically; no manual activation or Codex-bundled Python is needed:

```powershell
.\fittrackee\importer\Import-Strava.ps1 inspect .\fittrackee\personal\strava-export.zip --report .\fittrackee\personal\strava-inventory.json

.\fittrackee\importer\Import-Strava.ps1 plan .\fittrackee\personal\strava-export.zip --sample --limit 5 --output .\fittrackee\personal\pilot-plan.json

# Validate files/hashes and display the batch bound. No credentials or network calls.
.\fittrackee\importer\Import-Strava.ps1 apply .\fittrackee\personal\pilot-plan.json
```

Inspect the private pilot-plan.json locally before execution: it contains actual titles, dates, source IDs, notes, recording references, captions, selected photos and warnings. The prepared sample covers FIT/TCX/GPX, five Ride activities and 12 selected photos. To choose one exact ride, create a new plan with --activity-id STRAVA_ID --limit 1. Repeat --activity-id for a small explicit selection. Plans default to five activities and cannot exceed 20.

By default only Strava Ride maps to Cycling (Sport), sport 1. The example also contains 286 E-Bike Ride activities; these are left out until you explicitly choose an appropriate sport mapping. FitTrackee's electric option is Mountain Biking (Electric), which may not describe road cycling. A JSON --sport-map can specify a chosen mapping, and repeatable --type selects activity types. Unsupported activities, BIN files and no-file/manual activities remain in the original export for a later supported import path.

The equivalent cross-platform command from the repository root is:

```sh
uv run --locked --project fittrackee/importer python fittrackee/importer/strava_import.py --help
uv run --locked --project fittrackee/importer python -m unittest discover -s fittrackee/importer/tests -v
```

The project pins Python 3.13 for development while the utility supports Python 3.10+. uv can provision the interpreter. Commit uv.lock and .python-version; keep .venv local. Standard-library-only currently means no third-party dependencies; future dependencies belong in this uv project.

## Explicit pilot execution — not yet performed on real data

Only after reviewing a selected plan and choosing the target account:

```powershell
.\fittrackee\importer\Import-Strava.ps1 apply .\fittrackee\personal\one-ride-plan.json --execute --credentials .\fittrackee\.secrets\live-tests.json --confirm-account fittrackee_test --state .\fittrackee\personal\journal-test.json --limit 1
```

--execute, credentials, a journal path and --confirm-account are all required for uploads. The default execution batch is one activity; maximum 20. Repeating the command resumes the next unfinished items within that reviewed plan, up to the batch limit. There is no full-archive mode in this initial pilot implementation. Do not use a personal owner account until the pilot has been reviewed.

Credentials JSON uses base_url plus email/password, or base_url plus an OAuth access_token. The profile must match --confirm-account. Use protected ignored files; never pass credentials in command arguments or commit them. Existing dedicated test credentials work. OAuth needs profile:read, workouts:read/write and media:write. TLS certificates are validated; redirects outside the authenticated origin are refused.

## Preservation and limits

- FIT/TCX/GPX payloads are uploaded without conversion by this utility. Individual .gz wrappers are decompressed; the decoded original recording is hashed and preserved by FitTrackee. The source ZIP is never extracted in bulk, edited or deleted.
- Workout timestamps, GPS, durations, distance, elevation and sensor streams come from the recording and FitTrackee's parser. CSV summaries may differ from calculated values. They remain in source_csv in the private plan and the journal records returned server statistics; the importer does not overwrite recording-derived metrics to force a match.
- CSV title and description populate their API fields. Private notes begin with a unique [strava:ID] marker, followed by the original private note. API length limits are respected; full source text remains in the plan and truncation is warned about.
- Explicit photo references are uploaded and attached; captions become media descriptions. Up to 20 supported images per activity. No guesswork for missing files/associations. Native FitTrackee image handling may reencode images and strip EXIF; source photos remain unchanged in the ZIP.
- Gear/bikes, social data and unsupported fields are retained in the export/selected source metadata, not automatically recreated as application entities. Original photo capture times and arbitrary CSV sensor summaries are not claimed to be separately imported.
- Existing accepted photo-URL privacy behavior is unchanged and is not a blocker.
- A 64 MiB per-member/decompressed-payload bound prevents accidental oversized expansion. Larger recordings need explicit future assessment, not an automatic limit increase.

## Resume and duplicate protection

Use one journal per target account and retain it across plans. A file lock prevents concurrent use of that journal. Do not run competing journals/importers for the same account; the API has no atomic Strava-ID uniqueness guarantee. Keep the journal with the original export when changing machines.

The journal records each uploaded media ID before proceeding, then the returned workout ID and statistics. Completed entries are skipped. Before creating a workout, the importer searches the authenticated account for the exact [strava:ID] private-note marker. That also reconciles a successful server upload whose response or local journal was lost. The fabricated live test verified both repeated-journal skipping and a fresh-journal remote reconciliation, without duplicate uploads.

A timeout or failed POST is never automatically retried. An uncertain operation stops for review; rerunning first checks the remote workout marker. --retry-uncertain ID is an explicit recovery override only after confirming the old request cannot still complete. An uncertain image upload can leave an unattached orphan whose ID was not returned; do not delete arbitrary media to guess at cleanup. Successful media IDs are reused on resume. Error events include timestamps and safe HTTP diagnostics, without credentials/cookies.

Metadata or recording changes for a previously journaled ID stop rather than silently overwrite it. Activities imported manually/by another tool without these markers require separate reconciliation. A completed activity deliberately deleted from FitTrackee is not automatically resurrected from its journal entry. No account reset, bulk deletion or rollback is performed.

## Current validation

Offline synthetic tests cover repeated headers, Unicode, gzip expansion limits, missing/unsafe paths, private visibility, bounded plans/execution, source ZIP preservation, dry-run/no credentials, account-isolated journals, locking, normal resume, remote reconciliation and lost responses. A fabricated one-recording/one-image export was imported over real HTTPS into fittrackee_test; title, private note, source marker, image association and caption verified. Repeating it skipped the completed entry; a fresh journal reconciled the marker without creating another workout.

An actual FIT/TCX export pilot and its metrics/sensors/photo review remain to be approved. Do not equate a parsed plan or synthetic GPX test with validating thousands of real recordings.

All export ZIPs, plans, inventories, journals and private test artifacts stay under ignored personal/. That directory is also excluded from Docker contexts. The original archive and your existing ignore rule are preserved. No personal data enters GitHub/CI; tests create small fictional archives in temporary directories.

## Finding the generated test photograph

Log in as fittrackee_test and open **Synthetic Strava importer verification**, dated October 21, 2026. Its direct activity page is https://fittrackee.dbwalker0min.info/workouts/F3PhMai3ubFbnVh2DUvzGT#photos . The generated checkerboard is an attachment on that workout; it is not a real photograph from your export. The earlier attachment runner also retained Automated attachment check 5ba8ee8a. The dashboard/calendar may not display the photo directly; open the workout detail and scroll to Photos, or use the #photos link above.

Follow-up verification: a read-only check on the Pi confirmed both retained workouts still have one linked image, and each full image and thumbnail exists. Browser rendering could not be rechecked because the public hostname returned TLS unrecognized_name at that time; do not treat file existence as visual confirmation.
