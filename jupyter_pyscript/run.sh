#!/usr/bin/env bash
set -euo pipefail

OPTIONS=/data/options.json

opt() {
  python - "$1" <<'PY'
import json,sys
o=json.load(open("/data/options.json"))
print(o.get(sys.argv[1], "") or "")
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

# ---- 1) notebooks -> /home/jovyan/work (point to /config/pyscript) ----
: "${NOTEBOOK_DIR:=/config/pyscript}"
mkdir -p "$NOTEBOOK_DIR"
rm -rf /home/jovyan/work
ln -s "$NOTEBOOK_DIR" /home/jovyan/work

# ---- 2) jupyter-data -> ~/.local/share/jupyter (persist in /data) ----
mkdir -p /data/jupyter
mkdir -p /home/jovyan/.local/share
rm -rf /home/jovyan/.local/share/jupyter
ln -s /data/jupyter /home/jovyan/.local/share/jupyter

# ---- 3) generate pyscript.conf ----
CONF_DIR="/opt/conda/share/jupyter/kernels/pyscript"
CONF_PATH="${CONF_DIR}/pyscript.conf"
mkdir -p "$CONF_DIR"

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
ARGS+=(--ServerApp.root_dir="/home/jovyan/work")

exec jupyter lab "${ARGS[@]}" $EXTRA_ARGS