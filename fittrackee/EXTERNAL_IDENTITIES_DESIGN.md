# External identities: design

Status: implemented in app 0.1.2. Scope revised October 23, 2026. Exact endpoint contract: EXTERNAL_IDENTITIES_API.md; verification history: PROJECT_STATUS.md.

## Boundaries and integration

Keep upstream FitTrackee 1.3.6 pinned and its native APIs intact. Add a local application factory that calls upstream create_app(), registers a companion Flask blueprint, then returns the app. Gunicorn serves both through the existing gate and NPM hostname. No second listener, proxy, public hostname, or additional database service.

Use /api/external-identities/v1 as the companion prefix. Sources are ordinary bounded identifiers, not an enumerated provider list. External IDs are opaque case-sensitive strings, never coerced to numbers. Specify canonicalization, encoding and length bounds in the final contract.

## Authentication and ownership

Reuse upstream require_auth: workouts:read for reads, workouts:write for mutations. The installed protector validates OAuth scopes/token ownership, active/suspended status and first-party JWT cookies including CSRF enforcement. Do not invent a shared token or accept a client-supplied user ID. Use the authenticated native user ID internally.

Registration verifies native workout ownership directly using upstream models/read-only queries; merely seeing a public workout is insufficient. Reads, deletes and claims are account-scoped. Return non-disclosing not-found responses for other accounts' identities/workouts. No tokens or external IDs in access logs where avoidable; redact error diagnostics.

## Storage and consistency

Prefer dedicated companion-owned tables in a separate PostgreSQL schema within the existing database. This adds no columns/tables to upstream's public schema and no new database process. An identity row has owner user ID, source, external ID, native workout reference and timestamps. Database uniqueness enforces (user_id, source, external_id). Every identity binds exactly one caller-supplied workout. Sources are first-use identifiers, not separately registered records. Idempotency is strictly per user/source/external_id: different providers remain independent even for the same physical ride. There is no automatic association, duplicate detection, fuzzy matching, merging, cross-provider reporting or manual reconciliation feature. Foreign keys cascade native workout/account deletion. A companion-owned trigger validates user/workout ownership under a shared row lock without adding a composite constraint to upstream tables. API reads also verify native ownership. Upstream tables/constraints are unchanged.

Own migration versioning and startup initialization; fail startup on an unsupported schema. Serialize migrations and concurrent identity changes using PostgreSQL transactions/constraints. Insert-if-absent, then compare: same target is idempotent success; a different target is 409 without overwriting. References to native rows keep deletion consistent without polling. Test native schema upgrades against the pinned version before release.

The existing cold Supervisor backup stops all writers and captures /data/postgres, so workouts and companion tables share the same consistent snapshot and restore point. Logical migration must include the companion schema. Test actual backup/restore before claiming runtime recovery verified.

## Endpoints

All paths below are relative to /api/external-identities/v1.

- GET /identities/{source}/{external_id}: resolve the caller's mapping; 200 or 404.
- PUT /identities/{source}/{external_id}: JSON workout_id; 201 for new, 200 for identical retry, 409 for attempted remap.
- GET /workouts/{workout_id}/identities: owner-only list, stable ordering.
- DELETE /identities/{source}/{external_id}: idempotent removal, never deletes the workout.

No bulk deletion, workout upload forwarding, archive parsing, provider OAuth, polling or calendar integration.

## Claims and failure recovery

Use a small opt-in claim protocol because independent clients can otherwise upload duplicates before registration. Claims are unique per account/source/external ID, return an opaque secret, and are checked transactionally on bind/release. Another client receives mapped or busy/conflict status. Bound identities remain the authority; claims are coordination, not ingestion.

Before native upload, a client explicitly marks its claim as upload-started. Unstarted reservations can expire with fencing; an upload-started claim with an uncertain outcome must not automatically expire into permission for a second upload. It enters needs-reconciliation until the client binds a known workout ID or explicitly resolves the uncertainty. Persist returned workout IDs in the external client's own journal. Do not automatically steal claims on a timer.

This cannot guarantee exactly-once native upload: a crash after workout creation but before saving the returned ID leaves an ambiguity the native API cannot transactionally solve. Claims coordinate cooperating clients; they do not prevent manual or noncooperating uploads. Document a manual reconciliation/release path and test fencing, retries, simultaneous callers and lost responses. The concrete claim endpoints, token fencing, lease bounds and reconciliation acknowledgement are specified in EXTERNAL_IDENTITIES_API.md.

## Verification plan

Test authentication failures, CSRF, OAuth read/write scope separation, suspended users, own versus other users' public/private workouts, opaque identifiers, identical retries, conflicting mappings, multiple identities per workout and concurrent registrations. Test deletion/account cleanup, claim conflicts/fencing/uncertain outcomes, schema migration failure, app restarts, and cold backup/restore. Keep synthetic fixtures and dedicated test accounts; do not use the private archive. Preserve existing proxy/security and attachment tests.
