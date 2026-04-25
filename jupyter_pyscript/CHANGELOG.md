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

## 0.2.8 - 2026-02-24

### Changed
- Added `aarch64` support in add-on architecture list.
- Clarified `host_network` rationale in `config.yaml` comments.
- Split docs into user-facing root README and development notes.

### Security
- Removed startup logging of generated notebook arguments.
- Removed committed token value from test helper workflow.

## 0.2.7 - 2026-02-24

### Changed
- Pinned Python dependency versions in `requirements.txt` for reproducible builds.
- Stopped installing `notebook` and `jupyterlab` explicitly from `requirements.txt` (provided by base image).

## 0.2.6 - 2026-02-24

### Added
- Initial repository/app documentation and local development notes.

---

## How to update this file quickly

1. Add new bullets under **Unreleased** while you work.
2. When releasing, copy **Unreleased** into a new version section:
   - `## <version> - YYYY-MM-DD`
3. Clear the **Unreleased** bullets back to blank placeholders.
4. Keep entries short and user-focused (what changed and why it matters).
