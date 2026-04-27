# Home Assistant App: Jupyter + PyScript

Run JupyterLab inside Home Assistant OS with a PyScript-capable kernel for interactive automation development.

This app is intended for interactive PyScript development, with notebooks and code living directly under `/config/pyscript`.

It also includes a JupyterLab extension that adds an **HA** menu for common development actions, such as regenerating PyScript stubs and reloading Home Assistant YAML configuration.

This setup provides an IDE-like experience for PyScript development inside Home Assistant. You can prototype and test ideas interactively in a Jupyter notebook, inspect state and services in real time, and then move working code directly into PyScript automations or apps.

This short feedback loop makes it much easier to develop, debug, and iterate on Home Assistant automations compared to editing YAML or restarting components. It effectively turns Home Assistant into a live development environment for automation logic.

## Features

- JupyterLab with a PyScript-capable kernel
- JupyterLab extension for:
  - Reloading YAML configuration
  - Rebuilding PyScript stubs
- Notebook root defaults to `/config/pyscript`
- Startup-generated `pyscript.conf` for Home Assistant connectivity
- Configurable Jupyter authentication (password or token)
- Supports `amd64` and `aarch64`

## Configuration options

From `jupyter_pyscript/config.yaml`:

- `notebook_dir` (string, default `/config/pyscript`)
  - Passed as `--ServerApp.root_dir=...`.

- `jupyter_token` (optional string)
  - Token used for Jupyter authentication. If not set (and `jupyter_password` is not set), Jupyter will start with a random token.

- `jupyter_password` (optional string, hashed at startup)
  - Password for Jupyter authentication. If set, takes precedence over `jupyter_token`.

- `hass_host` (required string)
  - Hostname or IP address of your Home Assistant instance.

- `hass_url` (required string)
  - URL of your Home Assistant instance.

- `hass_token` (required string)
  - Long-lived access token for your Home Assistant instance.

- `extra_args` (optional string)
  - Additional Jupyter CLI arguments; parsed with shell-style quoting.

**Note:** `hass_url` and `hass_host` may appear redundant, but both are required by the Jupyter PyScript connector.

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

## Quick Start

> **Supported architectures:** This app runs only on `amd64` and `aarch64` (arm64) hosts.

1. Open **Settings → Apps → App Store** in Home Assistant.
2. Open the repository menu (the **⋮** icon in the top-right corner) and select **Repositories**.
3. Click **Add** and enter the repository URL:
   ```
   https://github.com/dbwalker0min/dbwalker0min-hass-apps
   ```
4. Close the Repositories dialog and return to the App Store. Scroll to the **dbwalker0min HA Apps** section.
5. Click **Jupyter + PyScript** and then click **Install**.
6. Once installed, open the **Configuration** tab to set required options (at minimum, `hass_host`, `hass_url`, and `hass_token`).
7. Return to the **Info** tab and click **Start**.
8. Open JupyterLab from the app Web UI button, or browse to: `http://<home-assistant-host>:8888`.

## Development and releases

- Development workflow: `../docs/development.md`
- Release notes: `CHANGELOG.md`

## Security notes

JupyterLab has broad access to your Home Assistant configuration and mounted files. Treat access to this app as highly privileged.

- Use Jupyter password or token authentication.
- Prefer access through a VPN, Tailscale, or Cloudflare Access if remote access is needed.
- Do not commit long-lived Home Assistant tokens or other secrets.
- Rotate Home Assistant long-lived access tokens periodically.
- Jupyter on port `8888` is powerful. Do not expose it publicly without strong authentication, a VPN, or Cloudflare Access.

## License

See `LICENSE`.
