#!/bin/sh

CONF_FILE="/opt/conda/share/jupyter/kernels/pyscript/pyscript.conf"

cat > "$CONF_FILE" <<EOL
[homeassistant]
hass_host = ${HASS_HOST:-supervisor}
hass_url = ${HASS_URL:-http://supervisor/core}
hass_token = ${HASS_TOKEN:-${SUPERVISOR_TOKEN-}}
EOL