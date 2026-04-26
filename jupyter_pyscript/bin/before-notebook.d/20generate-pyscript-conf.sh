#!/bin/sh

CONF_FILE="/opt/conda/share/jupyter/kernels/pyscript/pyscript.conf"

cat > "$CONF_FILE" <<EOL
[homeassistant]
hass_host = ${HASS_HOST}
hass_url = ${HASS_URL}
hass_token = ${HASS_TOKEN}
EOL