"""Safety checks for a runner which can delete its own synthetic fixtures."""
import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'tools/live_tests.py'
spec=importlib.util.spec_from_file_location('live_tests',path)
app=importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class RunnerSafety(unittest.TestCase):
    def config(self, **updates):
        return dict(base_url='https://fittrackee.example.test',username=app.USERNAME,
                    email=app.EMAIL,password='synthetic-unit-test',**updates)

    def test_personal_credentials_rejected(self):
        config=self.config()
        config['username']='personal_owner'
        with self.assertRaises(app.TestError):
            app.Client(config)

    def test_plain_http_rejected(self):
        config=self.config()
        config['base_url']='http://fittrackee.example.test'
        with self.assertRaises(app.TestError):
            app.Client(config)

    def test_cross_origin_request_rejected_before_network(self):
        client=app.Client(self.config())
        with self.assertRaises(app.TestError):
            client.request('https://other.example.test/media/image.png')

    def test_foreign_checkpoint_cannot_be_cleaned(self):
        client=app.Client(self.config())
        with self.assertRaises(app.TestError):
            app.cleanup(client,dict(base_url=client.base,username='personal_owner',title=app.PREFIX+'x'))

    def test_changed_fixture_title_prevents_deletion(self):
        class FakeClient:
            base='https://fittrackee.example.test'
            def request(self,path,method='GET',**kwargs):
                if method != 'GET':
                    raise AssertionError('A delete must never happen')
                return {'data':{'workouts':[{'title':'Someone changed this fixture'}]}}
        with self.assertRaises(app.TestError):
            app.cleanup(FakeClient(),dict(base_url=FakeClient.base,username=app.USERNAME,
                        title=app.PREFIX+'expected',workout_id='owned-fixture'))

    def test_partial_failed_run_only_deletes_recorded_media(self):
        calls=[]
        class FakeClient:
            base='https://fittrackee.example.test'
            def request(self,path,method='GET',**kwargs):
                calls.append((path,method))
        state=dict(base_url=FakeClient.base,username=app.USERNAME,title=app.PREFIX+'x',media_id='generated-media')
        app.cleanup(FakeClient(),state)
        self.assertEqual(calls,[('/api/media/generated-media','DELETE')])


if __name__=='__main__':
    unittest.main()
