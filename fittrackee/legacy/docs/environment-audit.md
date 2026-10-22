# Environment audit — 2026-10-20

## Verified
- Ubuntu 24.04.4 LTS runs under WSL2; docker-desktop also runs under WSL2.
- Linux user dbwal (uid 1000), Git 2.43.0, and Docker CLI are available.
- Docker Desktop 4.96.0, Engine 29.9.1, Compose v5.6.0 respond. Ubuntu can reach the engine.
- Windows Git and OpenSSH clients are installed. Windows sshd runs and listens on IPv4/IPv6 port 22; local TCP connection succeeds.
- desktop.home resolves to 192.168.1.236, matching the Ethernet address.
- No Windows TCP listener on port 3000; no Wanderer container in the Docker inventory. One unrelated stopped jlab-haext-dev container was left untouched.
- /home/dbwal/fittrackee was empty. /home/dbwal/projects and its fittrackee subdirectory were absent.
- No parent AGENTS.md was found in the checked ancestors.

Read-only WSL/Docker checks required execution outside the tool sandbox. This did not require Windows UAC or change system configuration. Docker's Windows service reports Stopped, but the running Desktop Linux engine responds successfully; starting that service is not indicated by this audit.

## Minimum deployment steps
1. Use this existing Linux workspace initially, or coordinate reopening a new workspace at ~/projects/fittrackee. Do not move the active directory during a running session.
2. Initialize a local deployment repository and ignore secrets, personal data, and backups before generating .env. Keep any upstream checkout separate.
3. Download and review a release-pinned official production Compose and matching environment example. The reviewed master currently references fittrackee/fittrackee:v1.3.6 and postgis/postgis:18-3.6-alpine; confirm matching release files before deployment. Internal app port is 5000; set HOST_APP_PORT=3000 and UI_URL=http://desktop.home:3000. Generate database credentials and APP_SECRET_KEY locally.
4. Start with FitTrackee and PostGIS, with persistent database, uploads and static-map cache storage. Do not expose PostgreSQL. Follow the official entrypoint and permission setup. Redis/workers can wait until archive uploads or other background work is required.
5. Validate configuration, pull images, start services and inspect health. Create a local account using supported UI/CLI, verify login and a test upload, then recreate containers and verify persistence.
6. Verify http://desktop.home:3000 from the Mac. Change firewall settings only if this test demonstrates a block; any required Windows administrative action must be called out first.
7. Document start/stop/restart, version-pinned updates, database dumps, uploads backups and an isolated restore test. Do not implement migration yet.

## Mac workflow
Use the existing Windows OpenSSH endpoint: ssh <Windows-user>@desktop.home. From that Windows session enter wsl -d Ubuntu, then cd /home/dbwal/fittrackee (or the coordinated future location). Run Git and development tools inside Ubuntu. Avoid introducing a second SSH server initially. Windows SSH authentication, WSL access under the remote Windows account, Codex availability/authentication in Ubuntu, and actual Mac network access remain unverified. The Windows username must be confirmed rather than assumed from the Linux username.

## References and limits
- Official production Compose: https://github.com/SamR1/FitTrackee/blob/master/docker-compose.yml
- Official environment example: https://github.com/SamR1/FitTrackee/blob/master/.env.docker.example
- Documentation entrypoint: https://docs.fittrackee.org/
- Main upstream repository: https://codeberg.org/FitTrackee/FitTrackee (GitHub is a mirror).

The web reader could inspect the official Compose and environment example but could not retrieve the installation page at the tested URLs. Resolve and read the current installation instructions before deploying; do not infer missing requirements. No application was deployed, credentials generated, account created, Git repository initialized, firewall changed or migration started during this audit.
