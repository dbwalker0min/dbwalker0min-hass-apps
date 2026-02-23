#!/bin/sh
(
    set -eu

    echo "Running as $(whoami) to start JupyterLab at $(date)..."

    PYSCRIPT_CONF="/opt/conda/share/jupyter/kernels/pyscript/pyscript.conf"

    # Generate pyscript.conf
    cat > "$PYSCRIPT_CONF" <<EOF
[homeassistant]
hass_host = ha.home
hass_url = http://ha.home:8123
hass_token = 
EOF

    if [ -f /data/options.json ]; then
        echo "Generating pyscript.conf from options..."

        # Defaults
        JUPYTER_TOKEN=""
        JUPYTER_PASSWORD=""
        NOTEBOOK_DIR="/config/pyscript"
        ALLOW_ORIGIN=""
        EXTRA_ARGS=""

        if [ -f /data/options.json ]; then
            echo "Loading options from /data/options.json"

            eval "$(
                python - << 'PY'
import json, shlex, pathlib

opts = json.loads(pathlib.Path("/data/options.json").read_text())

def emit(k, default=""):
    v = opts.get(k, default) or default
    print(f'{k.upper()}={shlex.quote(str(v))}')

emit("jupyter_token", "")
emit("jupyter_password", "")
emit("notebook_dir", "/config/pyscript")
emit("allow_origin", "")
emit("extra_args", "")
PY
            )"
        else
            echo "No options.json found, using defaults"
        fi
    fi

    # Build Jupyter args safely
    set -- \
    jupyter lab \
    --ip=0.0.0.0 \
    --no-browser \
    --notebook-dir="$NOTEBOOK_DIR"

    # Optional: CORS / origin handling (only if you need it)
    if [ -n "$ALLOW_ORIGIN" ]; then
        set -- "$@" --IdentityProvider.allow_origin="$ALLOW_ORIGIN"
    fi

    # Auth: password wins, else token, else default (auto-token)
    if [ -n "$JUPYTER_PASSWORD" ]; then
        HASHED_PASSWORD="$(python - << 'EOF'
from jupyter_server.auth import passwd
print(passwd(${JUPYTER_PASSWORD!r}))
EOF
        )"
        set -- "$@" --IdentityProvider.password="$HASHED_PASSWORD" --IdentityProvider.token=""
    elif [ -n "$JUPYTER_TOKEN" ]; then
        set -- "$@" --IdentityProvider.token="$JUPYTER_TOKEN"
    fi

    # Extra args (string) – let shell split intentionally
    # shellcheck disable=SC2086
    exec $@ $EXTRA_ARGS
)
