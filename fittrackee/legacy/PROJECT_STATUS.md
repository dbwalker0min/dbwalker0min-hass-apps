# Project status

Updated: 2026-10-20 (America/Los_Angeles)

## Goal and current result
FitTrackee is running at http://desktop.home:3000. Initial deployment and infrastructure checks passed. Owner account dbwalker0min created. Password validation succeeds, but authenticated sessions over the requested HTTP LAN URL are blocked by the release cookie security settings. Activity upload and Mac access remain unverified. Strava migration has not started.

## Environment and architecture
- Runtime machine: Windows desktop.home, Ethernet 192.168.1.236.
- Deployment: Ubuntu 24.04.4 under WSL2, /home/dbwal/fittrackee.
- Docker Desktop 4.96.0, Engine 29.9.1, Compose v5.6.0; accessible inside Ubuntu.
- Images: fittrackee/fittrackee:v1.3.6 and postgis/postgis:18-3.6-alpine.
- Host 3000 maps to app 5000. PostgreSQL is private to Docker.
- Persistent bind mounts: data/db, data/uploads, data/staticmap_cache. Logs go to stdout.
- Generated .env permissions: 600. Secrets, data and backups are ignored by Git.
- Minimal app/database setup; Redis/workers deferred until needed for background features.
- Upstream app source is untouched. Local Compose follows the release-specific official production configuration.
- Remain in the existing Linux workspace. Move to preferred ~/projects/fittrackee only in a coordinated later session.

## Verified this session
- Compose configuration validates; both services are healthy.
- Windows requests to http://desktop.home:3000 return HTTP 200; /api/check-db returns success.
- Both containers were recreated. Database migration state 2e3a59ebbc59 persisted; an upload-directory marker survived and was removed after verification.
- Backup scripts/backup.sh succeeded at backups/20261021T012333Z.
- scripts/verify-backup.sh verified checksums, restored that dump into a separate temporary database, checked schema and user/workout tables, extracted files in an ephemeral container, and removed the temporary database. Backup contained zero users/workouts; repeat after real data exists.
- Windows SSH listens on port 22. Mac authentication and network path remain untested.
- No firewall/admin system changes were made. Port 3000 was free before deployment.

## Files and commands
Read AGENTS.md, README.md, docs/operations.md and docs/environment-audit.md.
Run commands inside Ubuntu from /home/dbwal/fittrackee:

```sh
docker compose up -d --wait
docker compose stop
docker compose restart
docker compose ps
docker compose logs --tail=100
bash scripts/backup.sh
bash scripts/verify-backup.sh backups/TIMESTAMP
```

## Next steps
1. Resolve HTTP/HTTPS authentication: v1.3.6 ProductionConfig sets JWT_COOKIE_SECURE=True. Login POST accepts credentials, but ordinary HTTP cookie clients cannot access the authenticated profile. Prefer HTTPS, or obtain explicit user approval for a local HTTP cookie override. Automatic approval review rejected disabling Secure without specific authorization; no override was applied.
2. Verify authenticated login and a small synthetic/test activity upload, then verify both survive recreation. The current persistence check proves storage/schema persistence, not account/activity end-to-end behavior.
3. Test the URL from the Mac. Use existing Windows SSH, then wsl -d Ubuntu and cd /home/dbwal/fittrackee. Confirm remote Windows username/authentication. No Ubuntu Codex executable was found; installation/authentication remains future work if CLI-based remote Codex is desired.
4. Repeat backup/restore with real account/test-activity data, then copy encrypted/protected backups off-machine.
5. Configure a user-selected Git remote for code handoff. No remote configured and nothing pushed. Secrets/data need separate secure transfer; a clone alone does not reproduce existing data.
6. Only after basic account/upload verification, inspect the actual Strava export before planning migration.

## Handoff and limitations
Update this file after meaningful changes. Another machine can edit the deployment repository, but the running app/data remain on desktop.home. Mac ARM cannot natively run the chosen amd64 PostGIS image; prefer remote operations on the desktop. Backups contain .env and personal data and must never be committed. Initial failed backup attempts may have left incomplete timestamped directories; only the successful path above is verified.

Official installation guidance was read from https://github.com/SamR1/FitTrackee/blob/v1.3.6/docsrc/source/installation/installation.rst after the old published installation URL returned 404. Docker entrypoint runs migrations automatically; back up before updates and do not casually change PostgreSQL major versions.

## Owner account follow-up
Created dbwalker0min using the supplied email/password through ftcli, owner role, America/Los_Angeles timezone. Credentials are in ignored .secrets/owner-account.json (mode 600; directory 700); never commit or display them. Login POST returned success, but authenticated profile returned 401 because of Secure cookies over HTTP. No password or token is recorded in tracked files. Backup backups/20261021T035041Z includes the new account. No cookie-security changes were applied.


The account backup passed isolated restore verification: one user, zero workouts; file archive extraction and checksums passed. Both services are healthy.
