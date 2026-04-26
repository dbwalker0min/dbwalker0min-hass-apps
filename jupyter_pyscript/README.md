# Home Assistant App: Jupyter + Pyscript

Run JupyterLab with a pyscript-capable kernel inside Home Assistant OS.

This add-on is designed for interactive development under `/config/pyscript` and generates kernel-side `pyscript.conf` at startup so notebooks can call into Home Assistant. There is also a Jupyter extension to add an "HA" menu to regenerate Pyscript stubs and to reload the Home Assistant YAML configuration.

## Features

- JupyterLab plus Pyscript kernel in one add-on.
- JupyterLab extension for reloading YAML configuration and rebuilding Pyscript stubs.
- Notebook root defaults to `/config/pyscript`.
- Startup-generated `pyscript.conf` for kernel Home Assistant connectivity.
- Configurable Jupyter auth (password or token).
- Supports `amd64` and `aarch64`.

## Configuration options

From `jupyter_pyscript/config.yaml`:

- `notebook_dir` (string, default `/config/pyscript`)
  - Passed as `--ServerApp.root_dir=...`.

- `jupyter_auth` (object)
  - `jupyter_token` (optional string)
  - `jupyter_password` (optional string, hashed at startup)

- `hass_auth` (object)
  - `hass_host` (required string)
  - `hass_url` (required string)
  - `hass_token` (required string)

- `extra_args` (optional string)
  - Additional Jupyter CLI arguments; parsed with shell-style quoting.

### Jupyter authentication

Jupyter supports several different levels of authentication. If a password is specified, then password protection will be used. If a token is provided, then it will be used. Otherwise, a random token will be generated and used.

## Startup behavior

At app startup:

1. Options are read from `/data/options.json`.
2. Environment variables are generated:
   - `HASS_HOST`
   - `HASS_URL`
   - `HASS_TOKEN`
   - `NOTEBOOK_ARGS` (built from `extra_args`, `notebook_dir`, and Jupyter auth options)
3. `pyscript.conf` is written to:
   - `/opt/conda/share/jupyter/kernels/pyscript/pyscript.conf`
4. Jupyter starts using `NOTEBOOK_ARGS`.

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
