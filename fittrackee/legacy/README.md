# FitTrackee local deployment

Persistent FitTrackee on the Windows desktop's Ubuntu WSL2 filesystem, using Docker Desktop.

- URL: http://desktop.home:3000
- Current state and next steps: [PROJECT_STATUS.md](PROJECT_STATUS.md)
- Operations and backups: [docs/operations.md](docs/operations.md)
- Environment audit: [docs/environment-audit.md](docs/environment-audit.md)
- Agent instructions: [AGENTS.md](AGENTS.md)

Run deployment commands inside Ubuntu at `/home/dbwal/fittrackee`. `.env` contains locally generated secrets and is intentionally excluded from Git. Do not run the initialization helper on a different machine expecting to recover the desktop's data. See operations documentation for secure backup and restore.

The two-service configuration follows official FitTrackee v1.3.6 production Compose, with logs directed to stdout, local data bind mounts, and host port 3000. Redis/workers and migration tools are deferred. Upstream application source is not modified or vendored.
