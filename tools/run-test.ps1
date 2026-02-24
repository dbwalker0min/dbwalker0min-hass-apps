

& docker run --rm -it `
    -v "$((Resolve-Path "jupyter_pyscript\config").Path):/config:rw" `
    -v "$((Resolve-Path "jupyter_pyscript\data").Path):/data:rw" `
    -p 8888:8888 `
    haaddonjupyterpyscript:latest


