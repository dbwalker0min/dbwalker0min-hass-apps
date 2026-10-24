# External identity API v1

App version 0.1.2; FitTrackee 1.3.6. This companion Flask blueprint is loaded by a local app factory; upstream source files and native workout/upload/update/media endpoints are unchanged. No archive parsing, provider login or synchronization service is included.

Base URL: configured external_url plus `/api/external-identities/v1`. Sandbox: `https://fittrackee-test.dbwalker0min.info`; production: `https://fittrackee.dbwalker0min.info`. Clients configure their target origin; do not hardcode a hostname in API paths.

## Authentication

Reuse FitTrackee OAuth2 access tokens, with `Authorization: Bearer ACCESS_TOKEN`. Reads require `workouts:read`; mutations and claims require `workouts:write`. Obtain and refresh tokens using FitTrackee's native OAuth authorization flow; this API has no token endpoint or shared API key. Expired/revoked tokens, inactive and suspended users retain upstream rejection behavior. Both scopes are recommended for ingestion clients.

First-party FitTrackee session cookies also work, with the native `X-CSRF-TOKEN` header required for mutations. Use HTTPS, keep secure cookies enabled, and do not log tokens. Ownership always comes from the authenticated user; sending user_id is rejected. Another user's public workout cannot be registered or listed.

Responses are JSON with `Cache-Control: no-store`, except empty 204 responses. Companion domain errors use `{"error":"code"}`. Authentication failures retain upstream response format. The internal nginx gate suppresses companion request-path access logging (identifiers may be private); Nginx Proxy Manager has its own logging configuration. Claim secrets are headers, never URL parameters.

## Identifiers

Each identity is `(authenticated user, source, external_id)`; source/external_id are case-sensitive and never converted to numbers. `001` and `1` are different. Sources are 1–64 ASCII letters/digits/underscore/dot/hyphen, starting with a letter or digit. There is no provider allowlist. External IDs are 1–512 UTF-8 bytes, without whitespace ASCII 0–32, DEL, slash/backslash, or the special segments `.`/`..`. Percent-encode each path segment once; do not insert raw fragments or query delimiters. These path constraints deliberately exclude provider IDs containing slashes; clients must use a documented reversible encoding consistently if a future provider needs them.

JSON bodies must have Content-Length, be at most 4096 bytes, and contain only the documented keys. Registration requires workout_id; claims accept `{}`. All database operations use bounded waits. 503 `storage_unavailable` is retryable with backoff; verify outcomes by lookup/same-token retry before repeating consequential native uploads.

## Mappings

Paths below are relative to the base URL.

| Method/path | Request | Result |
|---|---|---|
| GET `/identities/{source}/{external_id}` | none | 200 identity; 404 `identity_not_found` if not bound |
| PUT `/identities/{source}/{external_id}` | `{"workout_id":"NATIVE_ID"}` | 201 new; 200 same mapping retry; 409 `identity_already_mapped` for a different target |
| GET `/workouts/{workout_id}/identities` | none | 200 `{"identities":[...]}` ordered by source/external_id; owner only |
| DELETE `/identities/{source}/{external_id}` | none | 204, including already absent; does not release an unbound claim or delete a workout |

Identity response: `{"source":"provider","external_id":"001","workout_id":"NATIVE_ID"}`. Each identity maps to exactly one explicitly supplied workout ID. There is no provider table or provider-registration step: a successful PUT stores a previously unseen source as an ordinary identifier in the new mapping. The identity PUT registers a mapping to an existing workout; it does not create a workout. Registering or listing nonexistent/foreign workouts returns 404 `workout_not_found`, even if that workout is publicly visible. Each account has an independent namespace.

Registration is serialized in PostgreSQL, including absent identities. It cannot silently remap. Deliberate removal followed by registration is the explicit correction path; coordinate clients before doing this. Native workout/account deletion cascades companion rows. The API checks ownership and a companion-only database trigger independently enforces it. Native workout-owner transfers are not a supported operation; no upstream schema/trigger is added to implement transfers.

## Provider independence

The registry provides idempotency within a provider, not reconciliation across providers. For example, strava:12345 and rwgps:98765 normally refer to two separately uploaded FitTrackee workouts, even when they describe the same physical ride. The same external_id under two sources is also two independent identities.

Clients look up their own source/external_id, upload a new native workout when needed, then register its returned ID. The API never chooses a workout, associates providers automatically, searches another provider, merges activities, or matches timestamps, GPS tracks, distance or titles. Future cross-provider duplicate reporting and manual reconciliation are out of scope. Claims and partial-failure recovery use the exact same user/source/external_id, never a physical ride.

## Optional claims

Claims coordinate *cooperating* clients before using the native upload API. Clients that choose claims must acquire one BEFORE native upload. Direct registration remains available when no live claim blocks it. Claims do not control the native upload endpoint or prevent uploads by other software.

Generate a fresh cryptographically random, URL-safe token of at least 32 random bytes per import attempt (for example secrets.token_urlsafe(32)). Save it durably BEFORE requesting a claim. Send it as `X-Identity-Claim`; accepted format is 32–128 ASCII letters/digits/underscore/hyphen. Never reuse a token after release/expiry. Only its SHA256 digest is stored; the service cannot recover a lost token.

| Method/path | Request | Result |
|---|---|---|
| PUT `/claims/{source}/{external_id}` | `{}` or `{"lease_seconds":900}` plus claim header | 201 newly reserved; 200 renewal with same token; 409 `claim_busy` for another live owner |
| POST `/claims/{source}/{external_id}/begin-upload` | claim header | 201 first transition (`upload_authorized:true`); 200 repeat (`upload_authorized:false`, `recovery_required:true`) |
| DELETE `/claims/{source}/{external_id}` | claim header | 204 released/absent; wrong token 409 |

Reserved leases default to 900 seconds, allowed 30–3600. Renew with the same token before expiry. Expired tokens cannot begin upload or bind; reacquisition needs a NEW token. The old token is fenced out. Direct registration without a token may replace an expired reservation, so never treat a reservation as permission to upload until begin-upload succeeds.

When a claim PUT finds a bound mapping it returns 200 with state `bound` and the identity. Do not upload. When the same token finds state `uploading`, it returns 200 with `recovery_required:true`; this is not new permission to upload.

After a first successful begin-upload response, use FitTrackee's native upload API once. Persist the returned workout ID in the client's journal, then PUT the mapping with workout_id and the SAME claim header. Binding clears the claim and returns 201. Repeating the identical binding returns 200, even after its successful response was lost.

An uploading claim never expires automatically. A crash between native upload and binding is uncertain: inspect/reconcile the native workout, then bind its known ID. Repeating begin-upload or receiving a timeout does NOT authorize another upload. If a native request is still processing, wait; do not release or steal the claim.

Release of an uploading claim requires both its token and `X-Identity-Reconciled: true`, asserting the client/operator has confirmed that no earlier upload can still complete. This acknowledgement is not an automated proof. Releasing too early can permit duplicates. Lost tokens require administrator-assisted investigation; there is intentionally no unauthenticated/force-steal recovery endpoint.

These claims cannot guarantee exactly-once workout creation across independent HTTP transactions. A crash after native creation but before recording the returned ID still needs reconciliation. They prevent cooperative clients from automatically retrying uncertain uploads; they do not implement an ingestion pipeline or search/parse Strava data.

## Storage, backup and upgrades

Tables, schema version and ownership trigger live exclusively in `ha_identity` within the existing PostgreSQL database. No extra database service. Native public tables are referenced by foreign keys with deletion cascades; upstream migrations remain unmodified. Initialization is transactional and locked, occurs after native migrations, and rejects unknown companion versions. Startup fails closed rather than serving an unsupported companion schema.

Supervisor cold backups stop the shared application and all writers before archiving /data, capturing workouts, photos and identities at one restore point. Always take a current backup before a scoped restore. A logical dump/migration must include `ha_identity` as well as native data. Restore the same app/database major/architecture first; verify mappings and workout/photo consistency before upgrades. Do not copy a live PostgreSQL directory or mix a mapping-only restore with a newer workout database.

The provider-independent companion code is app-specific and pinned to this FitTrackee version. Re-test authentication, native table keys/deletion behavior and backup/restore before upgrading upstream FitTrackee. See tests/README.md and PROJECT_STATUS.md for actual verification versus pending device checks.
