#!/usr/bin/env bash
set -euo pipefail

OPTIONS=/data/options.json

NB_USER="${NB_USER:-jovyan}"
NB_HOME="/home/${NB_USER}"

opt() {
  local key="$1"

  python - "$key" <<'PY'
import json
import os
import sys
import urllib.request

KEY = sys.argv[1]

def load_from_file(path: str):
  try:
    with open(path, "r", encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return None

def load_from_supervisor(token: str):
  urls = [
    "http://supervisor/addons/self/options",
    "http://supervisor/addons/self/info",
  ]
  headers = {"Authorization": f"Bearer {token}"}

  for url in urls:
    try:
      req = urllib.request.Request(url, headers=headers)
      with urllib.request.urlopen(req, timeout=5) as resp:
        payload = json.load(resp)
      data = payload.get("data")
      if not isinstance(data, dict):
        continue

      if url.endswith("/options"):
        return data

      opts = data.get("options")
      if isinstance(opts, dict):
        return opts
    except Exception:
      continue
  return None

options = load_from_file("/data/options.json")
if options is None:
  token = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HASSIO_TOKEN")
  if token:
    options = load_from_supervisor(token)

if not isinstance(options, dict):
  options = {}

value = options.get(KEY, "")
print(value or "")
PY
}

NOTEBOOK_DIR="$(opt notebook_dir)"

HA_HOST="$(opt ha_host)"
HA_URL="$(opt ha_url)"
HA_TOKEN="$(opt ha_token)"

JUPYTER_TOKEN="$(opt jupyter_token)"
JUPYTER_PASSWORD="$(opt jupyter_password)"

ALLOW_ORIGIN="$(opt allow_origin)"
EXTRA_ARGS="$(opt extra_args)"

# ---- 1) notebooks -> ~/work (point to /config/pyscript) ----
: "${NOTEBOOK_DIR:=/config/pyscript}"
mkdir -p "$NOTEBOOK_DIR" || true
rm -rf "${NB_HOME}/work"
ln -s "$NOTEBOOK_DIR" "${NB_HOME}/work"

# ---- 3) generate pyscript.conf ----
USER_KERNEL_DIR="${NB_HOME}/.local/share/jupyter/kernels/pyscript"
mkdir -p "${NB_HOME}/.local/share/jupyter/kernels" || true

# Copy the existing pyscript kernelspec into the user's kernels dir so we can
# manage pyscript.conf without needing root (user kernels take precedence).
if [ ! -d "$USER_KERNEL_DIR" ]; then
  SYS_KERNEL_DIR="$(python - <<'PY'
from jupyter_client.kernelspec import KernelSpecManager
ksm = KernelSpecManager()
print(ksm.find_kernel_specs().get('pyscript',''))
PY
)"
  if [ -n "$SYS_KERNEL_DIR" ] && [ -d "$SYS_KERNEL_DIR" ]; then
    cp -a "$SYS_KERNEL_DIR" "$USER_KERNEL_DIR"
  else
    mkdir -p "$USER_KERNEL_DIR"
  fi
fi

CONF_PATH="${USER_KERNEL_DIR}/pyscript.conf"

# If you decide you *don’t* want to store a long-lived token,
# you can use SUPERVISOR_TOKEN here instead (see note below).
if [ -z "$HA_TOKEN" ] && [ -n "${SUPERVISOR_TOKEN:-}" ]; then
  HA_TOKEN="$SUPERVISOR_TOKEN"
fi

cat > "$CONF_PATH" <<EOF
[homeassistant]
hass_host = ${HA_HOST}
hass_url = ${HA_URL}
hass_token = ${HA_TOKEN}
EOF
chmod 0444 "$CONF_PATH" || true

# ---- Start Jupyter ----
ARGS=(--ip=0.0.0.0 --port=8888 --no-browser)

# Auth
if [ -n "$JUPYTER_TOKEN" ]; then
  ARGS+=(--ServerApp.token="$JUPYTER_TOKEN")
else
  ARGS+=(--ServerApp.token="")
fi

if [ -n "$JUPYTER_PASSWORD" ]; then
  # must be hashed form from jupyter_server.auth.passwd()
  ARGS+=(--ServerApp.password="$JUPYTER_PASSWORD")
fi

# CORS / remote access
if [ -n "$ALLOW_ORIGIN" ]; then
  ARGS+=(--ServerApp.allow_origin="$ALLOW_ORIGIN" --ServerApp.allow_remote_access=True)
fi

# Root dir
ARGS+=(--ServerApp.root_dir="${NB_HOME}/work")

EXTRA_ARR=()
if [ -n "${EXTRA_ARGS}" ]; then
  # shell-style splitting (same behavior as previous unquoted $EXTRA_ARGS)
  read -r -a EXTRA_ARR <<<"${EXTRA_ARGS}"
fi

exec jupyter lab "${ARGS[@]}" "${EXTRA_ARR[@]}"