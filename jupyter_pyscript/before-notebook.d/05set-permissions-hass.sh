#!/bin/sh

# This script runs as root at startup to fix permissions on any mounted volumes 
# and write the pyscript.conf file with the Home Assistant connection info.
fix-permissions /config/pyscript
fix-permissions /data
