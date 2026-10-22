#!/usr/bin/env python3
import json
from pathlib import Path
import subprocess
import sys

env = json.loads(Path('/run/ha-fittrackee/app-env.json').read_text())
raise SystemExit(subprocess.call(['su-exec', 'fittrackee', 'ftcli', *sys.argv[1:]], env=env))
