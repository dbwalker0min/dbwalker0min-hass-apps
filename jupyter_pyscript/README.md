# Home Assistant Add-on: Jupyter + Pyscript

Run JupyterLab with a pyscript-capable kernel inside Home Assistant OS.

This add-on is designed for interactive development under `/config/pyscript` and generates kernel-side `pyscript.conf` at startup so notebooks can call into Home Assistant.

## Features

- JupyterLab plus pyscript kernel in one add-on.
- Notebook root defaults to `/config/pyscript`.
- Startup-generated `pyscript.conf` for kernel Home Assistant connectivity.
- Configurable Jupyter auth (password or token).
- Configurable Home Assistant connection overrides.
- Supports `amd64` and `aarch64`.

## Startup behavior

At add-on startup:

1. Options are read from `/data/options.json`.
2. Environment variables are generated:
   - `HASS_HOST` (default `supervisor`)
   - `HASS_URL` (default `http://supervisor/core`)
   - `HASS_TOKEN` (default `$SUPERVISOR_TOKEN`)
   - `NOTEBOOK_ARGS` (built from `extra_args`, `notebook_dir`, and Jupyter auth options)
3. `pyscript.conf` is written to:
   - `/opt/conda/share/jupyter/kernels/pyscript/pyscript.conf`
4. Jupyter starts using `NOTEBOOK_ARGS`.

## Configuration options

From `jupyter_pyscript/config.yaml`:

- `notebook_dir` (string, default `/config/pyscript`)
  - Passed as `--ServerApp.root_dir=...`.

- `jupyter_auth` (object)
  - `jupyter_token` (optional string)
  - `jupyter_password` (optional string, hashed at startup)

- `hass_auth` (object)
  - `hass_host` (optional string, default `supervisor`)
  - `hass_url` (optional string, default `http://supervisor/core`)
  - `hass_token` (optional string, falls back to `$SUPERVISOR_TOKEN`)

- `extra_args` (optional string)
  - Additional Jupyter CLI arguments; parsed with shell-style quoting.

### Jupyter authentication precedence

1. `jupyter_auth.jupyter_password`
2. `jupyter_auth.jupyter_token`
3. Jupyter auto-generated token

## Install and run

1. Add this repository to Home Assistant Add-on Store repositories:
   - `https://github.com/dbwalker0min/dbwalker0min-hass-apps`
2. Install **Jupyter + Pyscript**.
3. Configure add-on options (minimum: verify `notebook_dir`).
4. Start the add-on.
5. Open Jupyter via port `8888` on your Home Assistant host.

## Development and releases

- Development workflow: `../docs/development.md`
- Release notes: `CHANGELOG.md`

## Security notes

- Do not commit long-lived secrets.
- Prefer password or token auth for Jupyter.
- Keep Home Assistant token scope minimal and rotate when needed.

## License

See `LICENSE`.
