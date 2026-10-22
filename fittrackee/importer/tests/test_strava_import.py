import copy
import csv
import gzip
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('strava_import',Path(__file__).resolve().parents[1]/'strava_import.py')
app=importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def fixture(path, media=True, extra=0, unsafe=False, payload=b'<gpx>recording payload</gpx>'):
    headers=['Activity ID','Activity Name','Activity Type','Activity Description','Activity Private Note',
             'Filename','Distance','Distance','Media']
    rows=[['101','Ridé 🌲','Ride','A description','private source note','activities/101.gpx.gz',
           '1.2','1200','media/photo.png' if media else '']]
    rows += [[str(102+i),'Extra','Ride','','',f'activities/{102+i}.gpx','2','2000',''] for i in range(extra)]
    rows += [['999','Manual','Ride','','','','0','0','|'],
             ['998','Electric','E-Bike Ride','','','activities/e.gpx','2','2000','']]
    stream=io.StringIO(newline='')
    writer=csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('activities.csv',stream.getvalue())
        z.writestr('activities/101.gpx.gz',gzip.compress(payload))
        z.writestr('activities/e.gpx',b'<gpx>electric</gpx>')
        for i in range(extra):
            z.writestr(f'activities/{102+i}.gpx',b'<gpx>extra</gpx>')
        z.writestr('media.csv','Media Filename,Media Caption\r\nmedia/photo.png,A caption\r\n')
        z.writestr('media/photo.png',b'synthetic-image-payload')
        if unsafe:
            z.writestr('../escape.gpx',b'never extract')


class FakeApi:
    base='https://fittrackee.example.test'
    username='fittrackee_test'
    def __init__(self):
        self.calls=[]
        self.existing=None
        self.fail_workout=False
    def find(self,marker):
        return self.existing
    def request(self,path,method='GET',payload=None,form=None):
        self.calls.append((path,method))
        if path=='/api/media' and method=='POST':
            return {'id':'media1','url':self.base+'/media/generated.png'}
        if method=='PATCH':
            return {}
        if path=='/api/workouts' and method=='POST':
            if self.fail_workout:
                raise app.ApiError(method,path)
            return {'data':{'workouts':[{'id':'workout1','distance':1.2}]}}
        raise AssertionError((path,method))


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.archive=self.root/'export.zip'
        fixture(self.archive)
        self.state=self.root/'state.json'
    def tearDown(self):
        self.temp.cleanup()
    def plan(self,**kwargs):
        with app.Export(self.archive) as export:
            return app.make_plan(export,**kwargs)
    def apply(self,plan,api,**kwargs):
        with app.Export(self.archive) as export:
            app.validate_plan(plan,export)
            return app.apply_plan(plan,export,api,self.state,**kwargs)
    def test_duplicate_headers_and_unicode_are_preserved(self):
        plan=self.plan()
        row=plan['items'][0]['source_csv']
        self.assertEqual(row['Distance'],'1.2')
        self.assertEqual(row['Distance#2'],'1200')
        self.assertEqual(plan['items'][0]['metadata']['title'],'Ridé 🌲')
    def test_compressed_payload_is_hashed_after_decompression(self):
        item=self.plan()['items'][0]
        self.assertEqual(item['recording_sha256'],app.sha(b'<gpx>recording payload</gpx>'))
        self.assertEqual(item['upload_filename'],'101.gpx')
    def test_photo_mapping_and_caption(self):
        photo=self.plan()['items'][0]['photos'][0]
        self.assertEqual(photo['member'],'media/photo.png')
        self.assertEqual(photo['caption'],'A caption')
    def test_no_file_and_ambiguous_e_bike_mapping_not_imported(self):
        plan=self.plan()
        self.assertEqual([x['strava_id'] for x in plan['items']],['101'])
    def test_explicit_id_and_batch_limits(self):
        with self.assertRaises(app.ImportErrorSafe):
            self.plan(limit=21)
        with self.assertRaises(app.ImportErrorSafe):
            self.plan(ids=['999'])
    def test_unsafe_zip_path_rejected(self):
        fixture(self.archive,unsafe=True)
        with self.assertRaises(app.ImportErrorSafe):
            app.Export(self.archive)
    def test_decompression_size_limit(self):
        fixture(self.archive,payload=b'A'*4096)
        with app.Export(self.archive) as export:
            previous=app.MAX_MEMBER
            try:
                app.MAX_MEMBER=100
                with self.assertRaises(app.ImportErrorSafe):
                    export.read('activities/101.gpx.gz',decompress=True)
            finally:
                app.MAX_MEMBER=previous
    def test_plan_dry_run_needs_no_credentials_and_makes_no_state(self):
        path=self.root/'plan.json'
        app.save_json(path,self.plan())
        result=subprocess.run([sys.executable,str(Path(app.__file__)), 'apply',str(path)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['network_requests'],0)
        self.assertFalse(self.state.exists())
    def test_upload_resume_does_not_duplicate(self):
        api=FakeApi()
        plan=self.plan()
        self.assertEqual(self.apply(plan,api),{'imported':1})
        self.assertEqual(self.apply(plan,api),{'already_complete':1})
        self.assertEqual(api.calls.count(('/api/workouts','POST')),1)
        self.assertEqual(api.calls.count(('/api/media','POST')),1)
    def test_remote_marker_reconciles_without_uploads(self):
        api=FakeApi()
        api.existing={'id':'already-created'}
        self.assertEqual(self.apply(self.plan(),api),{'reconciled':1})
        self.assertEqual(api.calls,[])
    def test_lost_response_stops_automatic_retry(self):
        api=FakeApi()
        api.fail_workout=True
        plan=self.plan()
        with self.assertRaises(app.ApiError):
            self.apply(plan,api)
        api.fail_workout=False
        with self.assertRaises(app.ImportErrorSafe):
            self.apply(plan,api)
        self.assertEqual(api.calls.count(('/api/workouts','POST')),1)
        api.existing={'id':'completed-after-timeout'}
        self.assertEqual(self.apply(plan,api),{'reconciled':1})
    def test_explicit_retry_reuses_uploaded_photo(self):
        api=FakeApi()
        api.fail_workout=True
        plan=self.plan()
        with self.assertRaises(app.ApiError):
            self.apply(plan,api)
        api.fail_workout=False
        self.assertEqual(self.apply(plan,api,retry_uncertain=['101']),{'imported':1})
        self.assertEqual(api.calls.count(('/api/media','POST')),1)
    def test_journal_cannot_cross_accounts(self):
        api=FakeApi()
        plan=self.plan()
        self.apply(plan,api)
        api.username='another-person'
        with self.assertRaises(app.ImportErrorSafe):
            self.apply(plan,api)
    def test_metadata_changes_are_not_silent_overwrites(self):
        api=FakeApi()
        plan=self.plan()
        self.apply(plan,api)
        plan['items'][0]['metadata']['title']='Edited after import'
        with self.assertRaises(app.ImportErrorSafe):
            self.apply(plan,api)
    def test_archive_tampering_prevents_execution(self):
        plan=self.plan()
        with zipfile.ZipFile(self.archive,'a') as archive:
            archive.writestr('unrelated.txt','changed archive')
        with app.Export(self.archive) as export, self.assertRaises(app.ImportErrorSafe):
            app.validate_plan(plan,export)
    def test_private_visibility_required(self):
        plan=self.plan()
        plan['items'][0]['metadata']['media_visibility']='public'
        with app.Export(self.archive) as export, self.assertRaises(app.ImportErrorSafe):
            app.validate_plan(plan,export)
    def test_concurrent_writer_lock(self):
        with app.StateLock(self.state), self.assertRaises(app.ImportErrorSafe):
            with app.StateLock(self.state):
                pass
        self.assertFalse(Path(str(self.state)+'.lock').exists())
    def test_execution_limit_stops_at_one(self):
        fixture(self.archive,extra=3)
        api=FakeApi()
        self.assertEqual(self.apply(self.plan(),api,limit=1),{'imported':1})
        self.assertEqual(api.calls.count(('/api/workouts','POST')),1)
    def test_plan_cannot_overwrite_source_archive(self):
        digest=app.file_sha(self.archive)
        result=subprocess.run([sys.executable,str(Path(app.__file__)), 'plan',str(self.archive),
                               '--output',str(self.archive)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(app.file_sha(self.archive),digest)
    def test_plain_http_target_rejected(self):
        with self.assertRaises(app.ImportErrorSafe):
            app.Api({'base_url':'http://example.test'},'fittrackee_test')


if __name__=='__main__':
    unittest.main()
