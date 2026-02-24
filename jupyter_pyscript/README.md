# Home Assistant Add-on: Jupyter + Pyscript

Run JupyterLab and a pyscript-capable kernel together inside Home Assistant OS.

This add-on is designed for interactive development under `/config/pyscript`, and auto-generates kernel-side `pyscript.conf` at startup so notebook code can call into Home Assistant.

## Features

- JupyterLab + pyscript kernel in one add-on.
- Notebook root defaults to `/config/pyscript`.
- Auto-generated `pyscript.conf` at startup.
- Authentication via Jupyter token or password.
- Supports `amd64` and `aarch64`.

## How startup works

At add-on startup:

1. Options are read from `/data/options.json`.
2. `pyscript.conf` is written to:
   - `/opt/conda/share/jupyter/kernels/pyscript/pyscript.conf`
3. Jupyter args are built from configured options and exported through `NOTEBOOK_ARGS`.

Home Assistant API access for the kernel is provided through Supervisor (`homeassistant_api: true` and `http://supervisor/core`). The
token from the environment variable `SUPERVISOR_TOKEN` is used to authenticate access.

## Configuration options

From `jupyter_pyscript/config.yaml`:

- `notebook_dir` (optional string)
  - Passed as `--ServerApp.root_dir=...`
  - Default: `/config/pyscript`
- `jupyter_token` (optional string)
  - Explicit Jupyter token.
- `jupyter_password` (optional string)
  - Plain password in add-on config; hashed at startup before being passed to Jupyter.
- `extra_args` (optional string)
  - Additional command-line args appended to Jupyter launch args.

Authentication precedence:

1. `jupyter_password`
2. `jupyter_token`
3. auto-generated Jupyter token

## Install and run

1. Add this repository to the Home Assistant Add-on Store:
  - `https://github.com/dbwalker0min/dbwalker0min-hass-apps`
2. Install **Jupyter + Pyscript** from that repository.
3. Configure options (at minimum verify `notebook_dir`).
4. Start the add-on.
5. Open Jupyter from the add-on network endpoint.

## Development docs

For local build/smoke test/deploy details, see `../docs/development.md`.
For release notes, see `CHANGELOG.md`.

## Security notes

- Do not commit long-lived tokens/secrets.
- Do not log full startup args if they can contain auth values.
- Prefer token/password auth; avoid unauthenticated Jupyter on shared or untrusted networks.
- `host_network: true` is used for direct host/LAN reachability. It is not required for Supervisor API access, and it increases exposure versus ingress-first designs.

## Current trade-offs

- `host_network: true` is convenient for direct access but has broader network exposure.
- Dependency pins are explicit for reproducibility; they should be reviewed periodically.

## License

See `LICENSE`.
