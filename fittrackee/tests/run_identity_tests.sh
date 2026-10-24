#!/bin/sh
# Isolated disposable integration instance; never mount real app data here.
set -eu
image="${1:-fittrackee-ha:test}"
name="fittrackee-identity-ci-$$"
volume="$name-data"
cleanup() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker volume rm "$volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
docker run -d --name "$name" --network none \
  -v "$volume:/data" \
  -v "$PWD/fittrackee/tests/identity-options.json:/data/options.json:ro" \
  -v "$PWD/fittrackee/tests:/tests:ro" "$image" >/dev/null
ready=false
for attempt in $(seq 1 120); do
  if docker exec "$name" python /opt/ha-fittrackee/healthcheck.py >/dev/null 2>&1; then
    ready=true
    break
  fi
  if [ "$(docker inspect -f '{{.State.Running}}' "$name")" != true ]; then
    docker logs "$name"
    exit 1
  fi
  sleep 2
done
if [ "$ready" != true ]; then docker logs "$name"; exit 1; fi
docker exec -e IDENTITY_TEST_MODE=isolated "$name" python /tests/test_identity_api.py
