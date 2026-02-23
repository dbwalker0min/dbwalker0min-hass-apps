#!/bin/sh
(
    set -eu

    echo "Running as $(whoami) to perform setup tasks..."

    #### 1. Fix ownership of any writable mounts (only if needed) ####
    # Determine target UID/GID for NB_USER
    nb_user="${NB_USER:-jovyan}"
    nb_uid="$(id -u "${nb_user}")"
    nb_gid="$(id -g "${nb_user}")"

    paths=""
    [ -d /config/pyscript ] && paths="$paths /config/pyscript"
    [ -d /data ] && paths="$paths /data"

    # Only do this if there are target paths
    [ -n "${paths}" ] && find $paths \
            -ignore_readdir_race -xdev -not -type l \
            \( ! -user "$nb_uid" -o ! -group "$nb_gid" \) \
            -exec chown "$nb_uid":"$nb_gid" -v {} +    
)