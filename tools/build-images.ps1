$Version="0.2.4"

docker buildx build `
  --platform linux/amd64,linux/arm64 `
  --cache-from type=local,src=.buildx-cache `
  --cache-to type=local,dest=.buildx-cache,mode=max `
  -f .\jupyter_pyscript\Dockerfile `
  -t "ghcr.io/dbwalker0min/amd64-addon-jupyter_pyscript:$Version" `
  -t "ghcr.io/dbwalker0min/aarch64-addon-jupyter_pyscript:$Version" `
  --push `
  .\jupyter_pyscript