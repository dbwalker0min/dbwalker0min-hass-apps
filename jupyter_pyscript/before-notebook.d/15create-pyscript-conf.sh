#!/bin/sh

# This script creates `pyscript.conf` and defines environment variables for the Jupyter command line
eval "$(python /usr/local/bin/before-notebook.d/15create-pyscript-conf.py)"

