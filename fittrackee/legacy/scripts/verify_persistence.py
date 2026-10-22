import subprocess
from pathlib import Path
import urllib.request

def run(*args):
    return subprocess.check_output(args, text=True).strip()

# A tiny marker proves the uploads mount survives recreation without inventing an activity.
run('docker','compose','exec','-T','fittrackee','sh','-c','printf persistence-check > /usr/src/app/uploads/.deployment-persistence-check')
before = run('docker','compose','ps','-q','fittrackee-db')
subprocess.run(['docker','compose','up','-d','--force-recreate','--wait','--wait-timeout','120'], check=True)
after = run('docker','compose','ps','-q','fittrackee-db')
assert before != after, 'DB container was not recreated'
assert run('docker','compose','exec','-T','fittrackee','cat','/usr/src/app/uploads/.deployment-persistence-check') == 'persistence-check'
run('docker','compose','exec','-T','fittrackee','rm','/usr/src/app/uploads/.deployment-persistence-check')
print('Uploads mount persisted across app and DB container recreation')
print(urllib.request.urlopen('http://localhost:3000/api/check-db').read().decode())
print('Database migration state:')
print(run('docker','compose','exec','-T','fittrackee-db','psql','-U','fittrackee','-d','fittrackee','-Atc','SELECT version_num FROM alembic_version'))
