#!/bin/sh

TOOLS_DIR="$(cd "$(dirname "$0")" && pwd)"

# This will set the environment variables for the notebook server based on the output of the python script, which includes the Home Assistant connection info and any extra Jupyter arguments specified in the add-on options.
eval "$("$TOOLS_DIR/generate-environment-vars")"
