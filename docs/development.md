# Development Notes

This document covers local development workflow for the Home Assistant add-on in this repository.

## Prerequisites

- Docker installed and available on PATH.
- PowerShell 7 (`pwsh`).
- Access to your Home Assistant Samba add-ons share.
- `uvx` + `bump2version` available for version bumping in `tools/ha-build.ps1`.

## Project structure

- `jupyter_pyscript/`: add-on root
  - `config.yaml`: add-on metadata/options
  - `Dockerfile`: container image definition
  - `requirements.txt`: pinned extra dependencies
  - `bin/`: startup helper scripts
- `tools/`: local helper scripts

## Local image smoke test

Use the helper script:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\run-test.ps1
```

This runs the local image and mounts:

- `jupyter_pyscript/config` → `/config`
- `jupyter_pyscript/data` → `/data`

## Build + deploy to Home Assistant add-ons share

Use:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\ha-build.ps1 .\jupyter_pyscript\config.yaml
```

Current behavior of `tools/ha-build.ps1`:

1. Determines add-on slug from input path.
2. Bumps patch version via `bump2version`.
3. Mirrors add-on files to Samba add-ons share via `robocopy`.

## Notes on networking and API access

- Add-on config does not enable `host_network`; it exposes Jupyter on port `8888`.
- Local smoke test (`tools/run-test.ps1`) uses Docker `--network=host` for convenience during local runs.
- Home Assistant API access for the kernel is provided via Supervisor (`homeassistant_api: true`) with default URL `http://supervisor/core`.

## Runtime option handling

- Jupyter auth options (`jupyter_token`, `jupyter_password`) are top-level configuration keys.
- Home Assistant connection parameters (`hass_host`, `hass_url`, `hass_token`) are top-level configuration keys and are **required** with no defaults.
- Startup scripts generate `HASS_HOST`, `HASS_URL`, `HASS_TOKEN`, and `NOTEBOOK_ARGS`, then write `pyscript.conf` for the kernel.

## Safe update checklist

1. Update files in `jupyter_pyscript/`.
2. Run local smoke test (`tools/run-test.ps1`).
3. Deploy with `tools/ha-build.ps1`.
4. Start/restart add-on in Home Assistant.
5. Confirm Jupyter launch and pyscript kernel connectivity.
