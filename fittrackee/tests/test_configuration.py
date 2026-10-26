import importlib.util
from pathlib import Path
import unittest
import sys

path = Path('/opt/ha-fittrackee/launcher.py')
sys.path.insert(0, str(path.parent))
spec = importlib.util.spec_from_file_location('launcher', path)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class ConfigurationSecurity(unittest.TestCase):
    def test_valid_proxy(self):
        url, host, proxies, workers = app.options_config({
            'external_url': 'https://fittrackee.example.test',
            'trusted_proxy_ips': ['192.0.2.10']})
        self.assertEqual(host, 'fittrackee.example.test')
        config = app.nginx_config(host, proxies)
        self.assertIn('allow 192.0.2.10;', config)
        self.assertIn('deny all;', config)
        self.assertIn('proxy_set_header X-Forwarded-Proto https;', config)
        self.assertIn('proxy_set_header X-Forwarded-For $remote_addr;', config)
        self.assertIn('proxy_pass http://127.0.0.1:8082/healthz;', config)
        self.assertNotIn('/api/check-db', config)

    def test_reject_unsafe_options(self):
        for url, ips in [
            ('http://fittrackee.example.test', ['192.0.2.10']),
            ('https://fittrackee.example.test/path', ['192.0.2.10']),
            ('https://fittrackee.example.test', []),
            ('https://fittrackee.example.test', ['*']),
            ('https://fittrackee.example.test', ['192.0.2.0/24']),
            ('https://fittrackee.example.test', ['0.0.0.0']),
            ('https://fittrackee.example.test', ['192.0.2.10; allow all']),
        ]:
            with self.subTest(url=url, ips=ips), self.assertRaises(ValueError):
                app.options_config({'external_url': url, 'trusted_proxy_ips': ips})


if __name__ == '__main__':
    unittest.main()
