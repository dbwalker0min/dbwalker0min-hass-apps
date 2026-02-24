

& docker run --rm -it `
    -v "$((Resolve-Path "jupyter_pyscript\config").Path):/config:rw" `
    -v "$((Resolve-Path "jupyter_pyscript\data").Path):/data:rw" `
    -e "JUPYTER_CONFIG_DIR=/data/.jupyter" -e "PYTHONPATH=/config/pyscript/modules" `
    -e "CHOWN_EXTRA=/config/pyscript,/data" -e "CHOWN_EXTRA_OPTS=-R" `
    --network=host `
    haaddonjupyterpyscript:latest


