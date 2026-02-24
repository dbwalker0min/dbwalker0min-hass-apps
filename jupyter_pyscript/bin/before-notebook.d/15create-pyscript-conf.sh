#!/bin/sh

TOOLS_DIR="$(cd "$(dirname "$0")" && pwd)"

# This script creates `pyscript.conf` and defines environment variables for the Jupyter command line
NOTEBOOK_ARGS="$("$TOOLS_DIR/generate-pyscript-conf-and-notebook-args")"

export NOTEBOOK_ARGS
