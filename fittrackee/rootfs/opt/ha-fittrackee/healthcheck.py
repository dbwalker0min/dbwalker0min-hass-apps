#!/usr/bin/env python3
import urllib.request
with urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4) as response:
    assert response.status == 200
