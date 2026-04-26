# Changelog

All notable changes to this add-on are documented in this file.

## Unreleased

### Added
- 

### Changed
- 

### Fixed
- 

### Security
- 

## 0.2.8 - 2026-03-15

### Fixed
- Fixed `PYTHONPATH` environment variable configuration.

## 0.2.7 - 2026-03-15

### Changed
- Version bump for release alignment.

## 0.2.6 - 2026-03-15

### Added
- Added GitHub Actions workflow for automated add-on image builds.
- Introduced `latest` version channel support.

## 0.2.5 - 2026-03-14

### Added
- Enabled `hassio_api` in add-on configuration.

### Fixed
- Fixed container image reference on GitHub.
- Fixed Python typehints issues.

### Changed
- Minor documentation updates.

## 0.2.4 - 2026-03-04

### Added
- Added `lnav` log viewer to image.

### Changed
- Normalized line endings across repository files.

## 0.2.3 - 2026-03-03

### Changed
- Updated Jupyter pyscript extension to 0.1.2.

## 0.2.2 - 2026-03-03

### Changed
- Updated Jupyter pyscript extension to 0.1.1.

## 0.2.1 - 2026-03-02

### Added
- Added `aarch64` support in add-on architecture list.
- Integrated JupyterLab Home Assistant extension.

### Changed
- Pinned Python dependency versions in `requirements.txt` for reproducible builds.
- Stopped installing `notebook` and `jupyterlab` explicitly from `requirements.txt` (provided by base image).
- Clarified `host_network` rationale in `config.yaml` comments.
- Split docs into user-facing root README and development notes.

### Fixed
- Fixed documentation issues.

### Security
- Removed startup logging of generated notebook arguments.
- Removed committed token value from test helper workflow.

## 0.0.1 - 2026-02-24

### Added
- Initial repository/app documentation and local development notes.
- First functional version of the Jupyter + Pyscript add-on.

---

## How to update this file quickly

1. Add new bullets under **Unreleased** while you work.
2. When releasing, copy **Unreleased** into a new version section:
   - `## <version> - YYYY-MM-DD`
3. Clear the **Unreleased** bullets back to blank placeholders.
4. Keep entries short and user-focused (what changed and why it matters).
