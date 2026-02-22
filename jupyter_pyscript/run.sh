#!/usr/bin/env bash
set -euo pipefail

echo "Loading options from /data/options.json..."
echo $SUPERVISOR_TOKEN
echo `whoami`
curl -sSL -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/addons/self/config
