# Sandbox operations

Current sandbox: SSH alias `ha-test`, HAOS Pi 5 at `ha-test.home`. The existing SSH user is `hassio`; use its configured key. Windows SCP needs `-O` because this SSH app has no SFTP subsystem.

The app is installed as `local_fittrackee` from `/addons/fittrackee`. Its source of truth is the Windows Git repository, not the SSH home staging copy. Use Supervisor to install/update/start/stop the app; do not launch an unmanaged production container with docker run.

For SSH administrative commands, the HA CLI token exists in the SSH app's s6 environment but is not exported by the non-root shell. Inside a passwordless sudo shell, export it without displaying it:

```sh
export SUPERVISOR_TOKEN="$(cat /run/s6/container_environment/SUPERVISOR_TOKEN)"
ha apps info local_fittrackee
ha apps logs local_fittrackee
ha apps restart local_fittrackee
ha apps stats local_fittrackee
ha backups new --app local_fittrackee --name 'FitTrackee before update'
```

Never print the token or save it in Git. The app itself does not receive HA administration access. The sudo/SSH pathway is development administration only.

NPM is on the other HA server (`ha.home`, 192.168.1.10). Its already configured public hostname now forwards to sandbox `192.168.99.10:3001`. The app maps container 8080 to host 3001, allows only 192.168.1.10, and retains secure cookies. Z-Wave JS UI owns sandbox port 3000 and was left unchanged. Do not route public Internet traffic directly to 3001. Both LAN endpoints and the observed NPM source were verified.

Actual options are managed by Supervisor, not committed as a credentials file:

```yaml
external_url: https://fittrackee.dbwalker0min.info
trusted_proxy_ips:
  - 192.168.1.10
workers: 1
```

For an app-only restore use `ha backups restore BACKUP_SLUG --app local_fittrackee --homeassistant=false`. This replaces FitTrackee state with that snapshot and must only be done after a current backup and appropriate authorization. Never omit the app scope or the Home Assistant exclusion during sandbox tests. Wait for app health after restore before testing HTTPS; initial startup can briefly return 502.

Backup 0.1.0 restored files with different ownership; 0.1.1 repairs service-directory ownership recursively before opening the database. Restoring the old 0.1.0 image can reproduce its startup issue; keep the 0.1.1 source/image available. Backups contain credentials, private activities and the local app image; protect them and keep off-device copies. No public upload of backups is authorized.

The owner account is dbwalker0min, created with explicitly approved credentials. Sign in using the supplied email/password. One private synthetic activity is intentionally retained for verification: 'Deployment verification - synthetic ride' (2026-10-21, roughly 0.33 km and 3 minutes). It is not a real ride and is not a Strava import. Do not delete it without the user's approval.

Check original recordings, activity metadata and future photos after each update/restore. Photos and bulk archive jobs have not yet been tested. The future Strava utility stays separate and uses the API after export inspection.
