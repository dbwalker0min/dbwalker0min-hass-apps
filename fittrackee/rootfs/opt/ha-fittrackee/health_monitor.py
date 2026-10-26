"""Bounded service probes independent of FitTrackee's HTTP request workers."""
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


def probe_services(children):
    for name, process in children:
        if process.poll() is not None:
            return f'{name} exited'
    commands = [
        ('database', ['su-exec', 'postgres', '/usr/libexec/postgresql18/psql',
                      '-h', '/run/ha-fittrackee/postgres', '-U', 'postgres',
                      '-d', 'fittrackee', '-At', '-v', 'ON_ERROR_STOP=1', '-c', 'SELECT 1'], b'1'),
        ('redis', ['redis-cli', '-h', '127.0.0.1', 'PING'], b'PONG'),
    ]
    for name, command, expected in commands:
        try:
            result = subprocess.run(command, timeout=2, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return f'{name} probe failed'
        if result.returncode or result.stdout.strip() != expected:
            return f'{name} probe failed'
    try:
        # A busy synchronous worker must not delay liveness. Gunicorn's worker
        # timeout remains responsible for workers stuck processing a request.
        with socket.create_connection(('127.0.0.1', 8081), timeout=0.5):
            pass
    except OSError:
        return 'web listener unavailable'
    return None


class HealthMonitor:
    """Cache probes so public /healthz requests cannot spawn service queries."""

    def __init__(self, probe, log, *, address=('127.0.0.1', 8082), interval=5, max_age=20):
        self.probe = probe
        self.log = log
        self.interval = interval
        self.max_age = max_age
        self.checked_at = None
        self.failure = 'starting'
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        monitor = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != '/healthz':
                    self.send_error(404)
                    return
                healthy = monitor.healthy()
                body = b'healthy\n' if healthy else b'unhealthy\n'
                self.send_response(200 if healthy else 503)
                self.send_header('Content-Type', 'text/plain')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        self.server = HTTPServer(address, Handler)
        self.server.timeout = 1
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.probe_thread = threading.Thread(target=self.refresh, daemon=True)

    def healthy(self):
        with self.lock:
            return (not self.stopped.is_set() and self.failure is None
                    and self.checked_at is not None
                    and time.monotonic() - self.checked_at <= self.max_age)

    def refresh(self):
        while not self.stopped.is_set():
            try:
                failure = self.probe()
            except Exception:
                # Never log exception text: probes must not leak runtime secrets.
                failure = 'probe failed'
            with self.lock:
                previous = self.failure
                self.failure = failure
                self.checked_at = time.monotonic()
            if failure != previous:
                self.log('Health: ' + (failure or 'healthy'))
            self.stopped.wait(self.interval)

    def start(self):
        self.probe_thread.start()
        self.server_thread.start()

    def close(self):
        self.stopped.set()
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=2)
        self.probe_thread.join(timeout=5)
