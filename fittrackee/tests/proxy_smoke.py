"""Run in the synthetic trusted-proxy container, never against a real account.
This checks the HTTP hop only; it does not verify an actual NPM TLS connection.
"""
import json
import os
import urllib.request
import urllib.error

BASE = os.getenv('HA_TEST_BASE', 'http://fittrackee-ha-dev:8080')

def request(path, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    supplied = {'X-Forwarded-Proto': 'https', 'Content-Type': 'application/json'}
    supplied.update(headers or {})
    return urllib.request.urlopen(urllib.request.Request(BASE+path, data=data, headers=supplied), timeout=20)

with request('/') as response:
    assert response.status == 200
try:
    request('/', headers={'X-Forwarded-Proto': 'http'})
    raise AssertionError('HTTP scheme accepted')
except urllib.error.HTTPError as error:
    assert error.code == 400
with request('/api/auth/login', {'email':'ha-smoke@example.com', 'password':'Synthetic-Test-Only-2026!'}) as response:
    assert json.load(response)['status'] == 'success'
    cookies = response.headers.get_all('Set-Cookie')
    assert any('Secure' in item and 'HttpOnly' in item for item in cookies)
    # Manually relay the secure cookie to emulate NPM's internal HTTP hop.
    # A real client must access NPM via HTTPS; do not change cookie policy.
    cookie = '; '.join(item.split(';')[0] for item in cookies)
with request('/api/auth/profile', headers={'Cookie': cookie}) as response:
    profile = json.load(response)
    assert profile['data']['username'] == 'ha_smoke'
print('Trusted proxy, HTTPS scheme enforcement, Secure/HttpOnly cookies and authenticated profile passed')
