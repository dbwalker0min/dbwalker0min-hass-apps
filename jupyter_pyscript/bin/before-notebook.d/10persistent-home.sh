#!/bin/bash
user="${NB_USER:-jovyan}"
persistent_home="/data/home/${user}"

current_home="$(
    getent passwd "${user}" |
    cut -d: -f6
)"

uid="$(id -u "${user}")"
gid="$(id -g "${user}")"

# Create the persistent home directory.
install \
    -d \
    -m 0700 \
    -o "${uid}" \
    -g "${gid}" \
    "${persistent_home}"

# Copy the image's default home contents on first use.
# --no-clobber preserves anything already stored persistently.
if [[ "${current_home}" != "${persistent_home}" ]]; then
    cp \
        -a \
        --no-clobber \
        "${current_home}/." \
        "${persistent_home}/"
fi

chown -R "${uid}:${gid}" "${persistent_home}"

# sudo --set-home will now set HOME to this directory.
usermod \
    --home "${persistent_home}" \
    "${user}"
