# dbwalker0min HA Apps

This repository hosts Home Assistant add-ons maintained as separate app folders.

## Available add-ons

### Jupyter + Pyscript

Run JupyterLab and a pyscript-capable kernel in Home Assistant OS.

- Add-on folder: `jupyter_pyscript/`
- Add-on docs: `jupyter_pyscript/README.md`
- Changelog: `jupyter_pyscript/CHANGELOG.md`
- Main add-on config: `jupyter_pyscript/config.yaml`

## Install this add-on repository in Home Assistant

1. Open **Settings → Add-ons → Add-on Store**.
2. Open the repository menu (three dots) and choose **Repositories**.
3. Add:
   - `https://github.com/dbwalker0min/dbwalker0min-hass-apps`
4. Install any add-on listed from this repository.

## Repository structure

- `repository.yaml`: metadata for this add-on repository.
- `<addon_slug>/`: each add-on lives in its own folder with its own docs/changelog.
- `tools/`: local build/deploy helpers.
- `docs/`: shared repository documentation.

## For maintainers

- Keep user-facing usage details in each add-on folder (`<addon_slug>/README.md`).
- Keep release notes per add-on (`<addon_slug>/CHANGELOG.md`).
- Keep this root README as a high-level index.

## License

See `LICENSE`.
