#!/bin/sh

CONF_FILE="/opt/conda/share/jupyter/kernels/pyscript/pyscript.conf"

cat > "$CONF_FILE" <<EOL
[homeassistant]
host = ${HASS_HOST:-supervisor}
url = ${HASS_URL:-http://supervisor/core}
token = ${HASS_TOKEN:-${SUPERVISOR_TOKEN-}}
EOL