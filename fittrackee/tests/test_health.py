"""Independent liveness stays responsive while application workers are busy."""
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rootfs/opt/ha-fittrackee'))
sys.path.insert(0, '/opt/ha-fittrackee')
from health_monitor import HealthMonitor, probe_services


class HealthChecks(unittest.TestCase):
    def result(self, output):
        return subprocess.CompletedProcess([], 0, stdout=output)

    def wait_for(self, condition):
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.01)
        self.fail('Health state did not update')

    def test_busy_web_listener_needs_no_http_response(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            real_connect = socket.create_connection
            def connect(address, timeout):
                self.assertEqual(address, ('127.0.0.1', 8081))
                return real_connect(listener.getsockname(), timeout=timeout)
            child = Mock()
            child.poll.return_value = None
            with patch('health_monitor.subprocess.run', side_effect=[
                self.result(b'1\n'), self.result(b'PONG\n')
            ]) as run, patch('health_monitor.socket.create_connection', side_effect=connect):
                self.assertIsNone(probe_services([('web', child)]))
            self.assertTrue(all(call.kwargs['timeout'] == 2 for call in run.call_args_list))

    def test_exited_service_fails_without_probing(self):
        child = Mock()
        child.poll.return_value = 1
        with patch('health_monitor.subprocess.run') as run:
            self.assertEqual(probe_services([('worker', child)]), 'worker exited')
        run.assert_not_called()

    def test_database_failure_and_timeout(self):
        for result in [self.result(b'bad'), subprocess.TimeoutExpired('psql', 2)]:
            with self.subTest(result=result), patch('health_monitor.subprocess.run') as run:
                if isinstance(result, Exception):
                    run.side_effect = result
                else:
                    run.return_value = result
                self.assertEqual(probe_services([]), 'database probe failed')

    def test_redis_and_web_failure(self):
        with patch('health_monitor.subprocess.run', side_effect=[
            self.result(b'1'), self.result(b'bad')
        ]):
            self.assertEqual(probe_services([]), 'redis probe failed')
        with patch('health_monitor.subprocess.run', side_effect=[
            self.result(b'1'), self.result(b'PONG')
        ]), patch('health_monitor.socket.create_connection', side_effect=OSError):
            self.assertEqual(probe_services([]), 'web listener unavailable')

    def test_http_health_failure_and_recovery(self):
        failure = [None]
        messages = []
        monitor = HealthMonitor(lambda: failure[0], messages.append,
                                address=('127.0.0.1', 0), interval=0.01)
        url = 'http://127.0.0.1:%d/healthz' % monitor.server.server_address[1]
        monitor.start()
        try:
            self.wait_for(monitor.healthy)
            with urllib.request.urlopen(url, timeout=1) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b'healthy\n')
            failure[0] = 'database probe failed'
            self.wait_for(lambda: not monitor.healthy())
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(url, timeout=1)
            self.assertEqual(error.exception.code, 503)
            self.assertEqual(error.exception.read(), b'unhealthy\n')
            error.exception.close()
            failure[0] = None
            self.wait_for(monitor.healthy)
        finally:
            monitor.close()
        self.assertFalse(monitor.healthy())
        self.assertIn('Health: database probe failed', messages)

    def test_stalled_probe_does_not_block_http_and_becomes_unhealthy(self):
        release = threading.Event()
        calls = []
        def probe():
            calls.append(1)
            if len(calls) > 1:
                release.wait(3)
            return None
        monitor = HealthMonitor(probe, lambda _: None, address=('127.0.0.1', 0),
                                interval=0.01, max_age=0.15)
        url = 'http://127.0.0.1:%d/healthz' % monitor.server.server_address[1]
        monitor.start()
        try:
            self.wait_for(monitor.healthy)
            self.wait_for(lambda: len(calls) > 1)
            with urllib.request.urlopen(url, timeout=1) as response:
                self.assertEqual(response.status, 200)
            self.wait_for(lambda: not monitor.healthy())
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(url, timeout=1)
            self.assertEqual(error.exception.code, 503)
            error.exception.close()
        finally:
            release.set()
            monitor.close()

    def test_probe_exception_is_sanitized(self):
        def probe():
            raise RuntimeError('secret password')
        messages = []
        monitor = HealthMonitor(probe, messages.append, address=('127.0.0.1', 0), interval=0.01)
        monitor.start()
        try:
            self.wait_for(lambda: monitor.checked_at is not None)
            self.assertFalse(monitor.healthy())
        finally:
            monitor.close()
        self.assertEqual(messages, ['Health: probe failed'])


if __name__ == '__main__':
    unittest.main()
