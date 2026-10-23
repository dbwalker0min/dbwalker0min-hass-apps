#!/usr/bin/env python3
"""Repeatable HTTPS smoke test using a dedicated, non-admin FitTrackee account.

Python 3.10+, standard library only. Uses generated fixtures and supported CLI/API calls; no direct database access.
"""
import argparse
import base64
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import struct
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib

USERNAME = 'fittrackee_test'
EMAIL = 'fittrackee-test@example.com'
PREFIX = 'Automated attachment check '
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / '.secrets' / 'live-tests.json'
DEFAULT_RESULTS = ROOT / '.test-results'


class TestError(Exception):
    pass


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        if urllib.parse.urlsplit(request.full_url)[:2] != urllib.parse.urlsplit(newurl)[:2]:
            raise TestError('Refused redirect to a different origin')
        return super().redirect_request(request, fp, code, message, headers, newurl)


class Client:
    def __init__(self, config):
        self.config = config
        self.base = config['base_url'].rstrip('/')
        parsed = urllib.parse.urlsplit(self.base)
        if parsed.scheme != 'https' or parsed.path or parsed.username or parsed.query or parsed.fragment:
            raise TestError('The target must be an HTTPS origin')
        if config['username'] != USERNAME or config['email'] != EMAIL:
            raise TestError('Refusing credentials for a personal or unexpected account')
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(SafeRedirect(), urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, path, method='GET', payload=None, form=None, missing_ok=False, raw=False):
        url = urllib.parse.urljoin(self.base+'/', path)
        if urllib.parse.urlsplit(url)[:2] != urllib.parse.urlsplit(self.base)[:2]:
            raise TestError('Refused a URL outside the configured origin')
        headers = {}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers['Content-Type'] = 'application/json'
        if form is not None:
            data, headers['Content-Type'] = multipart(form)
        if method not in ('GET', 'HEAD'):
            csrf = next((c.value for c in self.jar if c.name == 'csrf_access_token'), None)
            if csrf:
                headers['X-CSRF-TOKEN'] = csrf
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=90) as response:
                content = response.read()
                return content if raw else (json.loads(content) if content else None)
        except urllib.error.HTTPError as error:
            if missing_ok and error.code == 404:
                return None
            raise TestError(f'{method} {urllib.parse.urlsplit(url).path}: HTTP {error.code}') from None

    def login(self):
        self.request('/api/auth/login', 'POST', {
            'email': self.config['email'], 'password': self.config['password']})
        cookie = next((c for c in self.jar if c.name == 'access_token_cookie'), None)
        if cookie is None or not cookie.secure or not cookie.has_nonstandard_attr('HttpOnly'):
            raise TestError('Expected a Secure, HttpOnly session cookie')
        profile = self.request('/api/auth/profile')['data']
        if profile['username'] != USERNAME or profile['email'] != EMAIL:
            raise TestError('Authenticated profile is not the dedicated test account')
        if profile.get('role') in ('admin', 'owner', 'moderator'):
            raise TestError('The test account must not have administrative privileges')


def multipart(fields):
    boundary = 'ft-test-'+uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\n'.encode())
        if isinstance(value, tuple):
            filename, content, mime = value
            parts.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
            parts.append(content)
        else:
            parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}'.encode())
        parts.append(b'\r\n')
    parts.append(f'--{boundary}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


def test_png():
    """Generate a recognizable checkerboard without any personal image or EXIF."""
    def chunk(kind, data):
        return struct.pack('!I', len(data))+kind+data+struct.pack('!I', zlib.crc32(kind+data) & 0xffffffff)
    pixels = b''.join(b'\x00'+b''.join(bytes((40, 130, 210) if (x//16+y//16)%2 else (240, 190, 50))
                                       for x in range(128)) for y in range(96))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!2I5B',128,96,8,2,0,0,0))
            +chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b''))


def protect_credentials(path):
    path.chmod(0o600)
    if os.name == 'nt':
        identity = subprocess.check_output(['whoami'], text=True).strip()
        result = subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r',
                                 identity+':F', '*S-1-5-18:F'], capture_output=True)
        if result.returncode:
            raise TestError('Could not restrict the local credential file permissions')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        path.parent.chmod(0o700)
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
    path.chmod(0o600)


def provision(args):
    if args.config.exists():
        protect_credentials(args.config)
        config = json.loads(args.config.read_text())
        client = Client(config)
        client.login()
        print('Existing dedicated test account verified; credentials unchanged')
        return
    config = dict(base_url=args.url, username=USERNAME, email=EMAIL, password=secrets.token_urlsafe(32))
    Client(config)  # Validate before sending anything.
    # Persist before creation so an interrupted setup never loses its generated password.
    save(args.config, config)
    protect_credentials(args.config)
    code = """
import json,subprocess,sys
from pathlib import Path
c=json.load(sys.stdin)
assert c['username']=='fittrackee_test' and c['email']=='fittrackee-test@example.com'
env=json.loads(Path('/run/ha-fittrackee/app-env.json').read_text())
r=subprocess.run(['su-exec','fittrackee','ftcli','users','create',c['username'],'--email',c['email'],
                  '--password',c['password'],'--role','user','--tz','America/Los_Angeles'],
                 env=env,capture_output=True,text=True)
if r.returncode: raise SystemExit('Creation failed. No existing account was modified; do not overwrite saved credentials.')
print('Dedicated non-admin test account created')
"""
    encoded = base64.b64encode(code.encode()).decode()
    command = (f"sudo -n docker exec -i {args.container} python -c "
               f"\"import base64; exec(base64.b64decode('{encoded}'))\"")
    if not all(c.isalnum() or c in '_.-' for c in args.container):
        raise TestError('Invalid container name')
    result = subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','IdentitiesOnly=yes',
                             '-o','IdentityAgent=none',args.ssh_host,command],
                            input=json.dumps(config),capture_output=True,text=True,timeout=120)
    if result.returncode:
        raise TestError('Provisioning failed; generated credentials retained. Check SSH access and account state before retrying.')
    client = Client(config)
    client.login()
    print(f'Non-admin account {USERNAME} created and HTTPS login verified. Credentials: {args.config}')


def verify(client, state):
    if state.get('base_url') != client.base or state.get('username') != USERNAME:
        raise TestError('Checkpoint belongs to another target/account')
    if not state.get('title', '').startswith(PREFIX):
        raise TestError('Checkpoint is not a managed test fixture')
    response = client.request('/api/workouts/'+state['workout_id'])
    workout = response['data']['workouts'][0]
    if workout['title'] != state['title']:
        raise TestError('Managed fixture identity changed')
    attachments = workout.get('media_attachments', [])
    if not any(item['id'] == state['media_id'] for item in attachments):
        raise TestError('Photo is not attached to the test workout')
    if not any(item.get('description') == state['description'] for item in attachments):
        raise TestError('Photo description was not preserved')
    for key in ('media_url', 'thumbnail_url'):
        image = client.request(state[key], raw=True)
        if not image.startswith(b'\x89PNG\r\n\x1a\n'):
            raise TestError(f'{key} is not a PNG')
        digest = hashlib.sha256(image).hexdigest()
        previous = state.get(key+'_sha256')
        if previous and digest != previous:
            raise TestError(f'{key} changed since the checkpoint')
        state[key+'_sha256'] = digest
    return workout


def cleanup(client, state):
    if (state.get('base_url') != client.base or state.get('username') != USERNAME
            or not state.get('title', '').startswith(PREFIX)):
        raise TestError('Refusing a checkpoint for a different account, target, or fixture')
    # No bulk deletion or account reset: only exact resources recorded by this run.
    if state.get('workout_id'):
        response = client.request('/api/workouts/'+state['workout_id'], missing_ok=True)
        if response:
            workout = response['data']['workouts'][0]
            if workout['title'] != state['title']:
                raise TestError('Refusing to delete a workout whose fixture identity changed')
            client.request('/api/workouts/'+state['workout_id'], 'DELETE')
    if state.get('media_id'):
        client.request('/api/media/'+state['media_id'], 'DELETE', missing_ok=True)
    state['status'] = 'cleaned'


def run_test(args, client):
    run_id = uuid.uuid4().hex
    state = dict(run_id=run_id, base_url=client.base, username=USERNAME, title=PREFIX+run_id[:8],
                 description='Generated checkerboard attachment '+run_id, status='started')
    path = args.results / (run_id+'.json')
    save(path,state)
    try:
        media = client.request('/api/media','POST',form={'file':('checkerboard.png',test_png(),'image/png')})
        state.update(media_id=media['id'], media_url=media['url'], thumbnail_url=media['meta']['thumbnail_url'])
        save(path,state)
        client.request('/api/media/'+media['id'],'PATCH',{'description':state['description']})
        gpx = (ROOT/'tests/fixtures/synthetic-ride.gpx').read_bytes()
        gpx = gpx.replace(b'HA deployment verification', ('HA test '+run_id).encode())
        # Each run uses distinct times so duplicate recording detection cannot collide.
        day = 1 + int(run_id[:2],16)%27
        minute = int(run_id[2:4],16)%55
        gpx = gpx.replace(b'2026-10-21', f'2026-09-{day:02}'.encode())
        for index in range(4):
            gpx = gpx.replace(f'18:0{index}:00'.encode(), f'12:{minute+index:02}:{int(run_id[4:6],16)%60:02}'.encode())
        metadata=dict(sport_id=1,title=state['title'],description='Synthetic automated test; not a real ride.',
                      workout_visibility='private',analysis_visibility='private',map_visibility='private',
                      media_visibility='private',media_attachment_ids=[media['id']])
        uploaded=client.request('/api/workouts','POST',form={
            'file':('synthetic.gpx',gpx,'application/gpx+xml'),'data':json.dumps(metadata)})
        workouts=uploaded.get('data',{}).get('workouts',[])
        if len(workouts)!=1:
            raise TestError('Expected exactly one newly created workout')
        state['workout_id']=workouts[0]['id']
        save(path,state)
        verify(client,state)
        # Record upstream media-link privacy behavior with a generated image only.
        try:
            anonymous = urllib.request.build_opener(SafeRedirect())
            with anonymous.open(state['media_url'], timeout=20) as response:
                state['anonymous_media_access'] = response.status == 200 and response.read(8) == b'\x89PNG\r\n\x1a\n'
        except urllib.error.HTTPError as error:
            if error.code not in (401,403,404):
                raise TestError(f'Anonymous media check: HTTP {error.code}') from None
            state['anonymous_media_access'] = False
        if state['anonymous_media_access']:
            print('NOTE: This FitTrackee release serves photo URLs without authentication; generated test image only.')
        state['status']='passed'
        save(path,state)
        print('PASS: HTTPS login, Secure/HttpOnly cookie, GPX upload, photo attachment, description, image and thumbnail')
        if args.keep:
            print('Kept fixture for UI/restart/backup checks:',state['title'])
        else:
            cleanup(client,state)
            print('Removed only this run\'s generated workout and media')
        save(path,state)
        print('Checkpoint:',path)
    except Exception:
        state['status']='failed'
        save(path,state)
        print('Failed-run resources retained for inspection. Checkpoint:',path, file=sys.stderr)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['provision','run','verify','cleanup'])
    parser.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    parser.add_argument('--results',type=Path,default=DEFAULT_RESULTS)
    parser.add_argument('--state',type=Path,help='Exact retained run checkpoint for verify/cleanup')
    parser.add_argument('--keep',action='store_true',help='Retain this run for manual inspection/persistence checks')
    parser.add_argument('--url',default='https://fittrackee.dbwalker0min.info',help='HTTPS origin for initial provisioning')
    parser.add_argument('--ssh-host',default='ha-test')
    parser.add_argument('--container',default='app_local_fittrackee')
    args=parser.parse_args()
    try:
        if args.command=='provision':
            provision(args)
            return
        client=Client(json.loads(args.config.read_text()))
        client.login()
        if args.command=='run':
            run_test(args,client)
        else:
            if args.state is None:
                raise TestError('--state is required; no implicit bulk cleanup')
            state=json.loads(args.state.read_text())
            if args.command=='verify':
                verify(client,state)
                print('PASS: retained workout, image, thumbnail and description match checkpoint')
            else:
                cleanup(client,state)
                save(args.state,state)
                print('Managed checkpoint resources cleaned')
    except (TestError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        # Never print raw responses, request bodies, cookies, or credential dictionaries.
        print(f'FAIL: {error}',file=sys.stderr)
        sys.exit(1)


if __name__=='__main__':
    main()
