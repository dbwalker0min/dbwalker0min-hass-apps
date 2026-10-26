"""Suspend web workers only inside the disposable integration instance."""
import os
from pathlib import Path
import signal
import subprocess
import time
import unittest
import urllib.request


@unittest.skipUnless(os.environ.get('IDENTITY_TEST_MODE') == 'isolated',
                     'Requires the isolated integration container')
class BusyWorkerHealth(unittest.TestCase):
    def test_suspended_web_worker_does_not_starve_health(self):
        workers = []
        for path in Path('/proc').glob('[0-9]*/cmdline'):
            try:
                command = path.read_bytes()
                if b'gunicorn' not in command or b'identity_api:create_app()' not in command:
                    continue
                pid = int(path.parent.name)
                children = Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
                workers.extend(int(child) for child in children)
            except (FileNotFoundError, ProcessLookupError):
                pass
        self.assertTrue(workers, 'Could not identify disposable Gunicorn workers')
        try:
            for pid in workers:
                os.kill(pid, signal.SIGSTOP)
            with self.assertRaises((TimeoutError, OSError)):
                urllib.request.urlopen('http://127.0.0.1:8081/api/check-db', timeout=0.5)
            # Exercise more than one independent dependency-probe interval.
            for _ in range(7):
                with urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2) as response:
                    self.assertEqual(response.status, 200)
                time.sleep(1)
            subprocess.run(['python', '/opt/ha-fittrackee/healthcheck.py'], check=True, timeout=5)
        finally:
            for pid in workers:
                try:
                    os.kill(pid, signal.SIGCONT)
                except ProcessLookupError:
                    pass
        with urllib.request.urlopen('http://127.0.0.1:8081/api/check-db', timeout=5) as response:
            self.assertEqual(response.status, 200)


if __name__ == '__main__':
    unittest.main()
