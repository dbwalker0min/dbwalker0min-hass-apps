#!/usr/bin/env python3
"""Supervise a self-contained HA app; durable state is confined to /data."""
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit

DATA = Path('/data')
RUN = Path('/run/ha-fittrackee')
PG = '/usr/libexec/postgresql18/'
children = []
stopping = False


def log(message):
    print(f'[ha-fittrackee] {message}', flush=True)


def options_config(options):
    url = options.get('external_url', '').rstrip('/')
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment or parsed.port not in (None, 443)):
        raise ValueError('external_url must be an HTTPS origin without a path or credentials')
    if not re.fullmatch(r'[a-zA-Z0-9.-]+', parsed.hostname):
        raise ValueError('external_url must use a DNS hostname')
    addresses = [str(ipaddress.ip_address(x)) for x in options.get('trusted_proxy_ips', [])]
    if not addresses or any(ipaddress.ip_address(x).is_unspecified or
                            ipaddress.ip_address(x).is_multicast for x in addresses):
        raise ValueError('Set trusted_proxy_ips to actual NPM unicast addresses; no wildcard or CIDR')
    workers = int(options.get('workers', 1))
    if workers not in (1, 2):
        raise ValueError('workers must be 1 or 2')
    return url, parsed.hostname, addresses, workers


def nginx_config(host, proxies):
    allow = '\n'.join(f'allow {address};' for address in proxies)
    return f'''user nginx;
worker_processes 1;
error_log /dev/stderr warn;
pid /run/nginx.pid;
events {{ worker_connections 256; }}
http {{
  access_log /dev/stdout;
  client_body_temp_path /tmp/nginx-body;
  proxy_temp_path /tmp/nginx-proxy;
  server {{
    listen 8080;
    listen [::]:8080;
    server_name _;
    client_max_body_size 256m;
    location = /healthz {{
      access_log off;
      proxy_pass http://127.0.0.1:8081/api/check-db;
    }}
    location / {{
      {allow}
      deny all;
      if ($http_x_forwarded_proto != "https") {{ return 400; }}
      proxy_pass http://127.0.0.1:8081;
      proxy_set_header Host {host};
      proxy_set_header X-Forwarded-Host {host};
      proxy_set_header X-Forwarded-Proto https;
      proxy_set_header X-Forwarded-For $remote_addr;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_read_timeout 180s;
      proxy_request_buffering off;
    }}
  }}
}}
'''


def run(command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


def spawn(name, command, env=None):
    process = subprocess.Popen(command, env=env, start_new_session=True)
    children.append((name, process))
    log(f'{name} started')
    return process


def own(path, user):
    path.mkdir(parents=True, exist_ok=True)
    entry = pwd.getpwnam(user)
    # Supervisor backup extraction may restore descendants as root.
    run(['chown', '-R', f'{entry.pw_uid}:{entry.pw_gid}', str(path)])
    path.chmod(0o700)


def pgsql(statement, database='postgres'):
    return subprocess.check_output(
        ['su-exec', 'postgres', PG+'psql', '-h', str(RUN/'postgres'), '-U', 'postgres',
         '-d', database, '-At', '-v', 'ON_ERROR_STOP=1', '-c', statement], text=True).strip()


def stop_requested(*_):
    global stopping
    stopping = True


def shutdown():
    for name, process in reversed(children):
        if process.poll() is not None:
            continue
        log(f'Stopping {name}')
        os.kill(process.pid, signal.SIGINT if name == 'postgres' else signal.SIGTERM)
        try:
            process.wait(timeout=35 if name == 'worker' else 15)
        except subprocess.TimeoutExpired:
            log(f'{name} exceeded shutdown timeout')
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def main():
    signal.signal(signal.SIGTERM, stop_requested)
    signal.signal(signal.SIGINT, stop_requested)
    url, host, proxies, worker_count = options_config(json.loads((DATA/'options.json').read_text()))
    RUN.mkdir(parents=True, exist_ok=True)
    secret_file = DATA/'runtime-secrets.json'
    if not secret_file.exists():
        fd = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({name: secrets.token_hex(32) for name in ('database', 'app', 'jwt')}, stream)
    saved = json.loads(secret_file.read_text())
    for directory, user in [('postgres', 'postgres'), ('redis', 'redis'),
                            ('files', 'fittrackee'), ('staticmaps', 'fittrackee')]:
        own(DATA/directory, user)
    own(RUN/'postgres', 'postgres')
    if (DATA/'postgres/PG_VERSION').exists():
        if (DATA/'postgres/PG_VERSION').read_text().strip() != '18':
            raise RuntimeError('Database major version differs; logical backup/restore required')
    else:
        run(['su-exec', 'postgres', PG+'initdb', '-D', str(DATA/'postgres'),
             '--auth-local=peer', '--auth-host=scram-sha-256', '--encoding=UTF8', '--locale=C'])
    postgres = spawn('postgres', ['su-exec', 'postgres', PG+'postgres', '-D', str(DATA/'postgres'),
                                '-k', str(RUN/'postgres'), '-h', '127.0.0.1',
                                '-c', 'shared_buffers=64MB', '-c', 'max_connections=30'])
    for _ in range(120):
        if stopping or postgres.poll() is not None:
            raise RuntimeError('Database startup interrupted')
        if subprocess.run(['su-exec', 'postgres', PG+'pg_isready', '-h', str(RUN/'postgres')],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError('Database readiness timed out')
    if not pgsql("SELECT 1 FROM pg_roles WHERE rolname='fittrackee'"):
        pgsql(f"CREATE ROLE fittrackee LOGIN PASSWORD '{saved['database']}'")
    if not pgsql("SELECT 1 FROM pg_database WHERE datname='fittrackee'"):
        pgsql('CREATE DATABASE fittrackee OWNER fittrackee')
    pgsql('CREATE EXTENSION IF NOT EXISTS postgis', 'fittrackee')
    env = dict(os.environ, FLASK_APP='fittrackee', FLASK_SKIP_DOTENV='1',
               APP_SETTINGS='fittrackee.config.ProductionConfig', UI_URL=url,
               APP_SECRET_KEY=saved['app'], JWT_SECRET_KEY=saved['jwt'],
               DATABASE_URL=f"postgresql://fittrackee:{saved['database']}@127.0.0.1:5432/fittrackee",
               UPLOAD_FOLDER=str(DATA/'files'), STATICMAP_CACHE_DIR=str(DATA/'staticmaps'),
               REDIS_URL='redis://127.0.0.1:6379', GUNICORN_LOG='-')
    env.pop('APP_LOG', None)
    env.pop('SUPERVISOR_TOKEN', None)
    env.pop('HASSIO_TOKEN', None)
    spawn('redis', ['su-exec', 'redis', 'redis-server', '--bind', '127.0.0.1',
                    '--protected-mode', 'yes', '--dir', str(DATA/'redis'),
                    '--appendonly', 'yes', '--save', '60', '1'])
    run(['su-exec', 'fittrackee', 'ftcli', 'db', 'upgrade'], env=env)
    env_file = RUN/'app-env.json'
    env_file.write_text(json.dumps(env))
    env_file.chmod(0o600)
    spawn('worker', ['su-exec', 'fittrackee', 'dramatiq', 'fittrackee.tasks:broker',
                     '--processes', '1', '--threads', '2'], env)
    spawn('web', ['su-exec', 'fittrackee', 'gunicorn', '-b', '127.0.0.1:8081',
                  '--workers', str(worker_count), '--timeout', '120', '--graceful-timeout', '10',
                  '--forwarded-allow-ips', '127.0.0.1', '--no-control-socket',
                  '--error-logfile', '-', 'fittrackee:create_app()'], env)
    config = RUN/'nginx.conf'
    config.write_text(nginx_config(host, proxies))
    run(['nginx', '-t', '-c', str(config)])
    spawn('proxy', ['nginx', '-c', str(config), '-g', 'daemon off;'])
    log('Services started; TLS is managed by Nginx Proxy Manager')
    while not stopping:
        for name, process in children:
            if process.poll() is not None:
                raise RuntimeError(f'{name} exited with status {process.returncode}')
        time.sleep(1)


if __name__ == '__main__':
    result = 0
    try:
        main()
    except Exception as error:
        if isinstance(error, subprocess.CalledProcessError):
            log(f'Service command failed with exit status {error.returncode}')
        else:
            log(str(error))
        result = 1
    finally:
        shutdown()
    sys.exit(result)
