"""Integration tests against real native authentication and PostgreSQL.
Run only inside an isolated test app container with IDENTITY_TEST_MODE=isolated.
"""
import concurrent.futures
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import sys
import time
import unittest

if os.environ.get('IDENTITY_TEST_MODE') != 'isolated':
    raise RuntimeError('Use an isolated test container, never the shared sandbox')
os.environ.update(json.loads(Path('/run/ha-fittrackee/app-env.json').read_text()))
sys.path.insert(0, '/opt/ha-fittrackee')
from identity_api import create_app, initialize, check_schema, PREFIX
from fittrackee import db
from fittrackee.users.models import User
from fittrackee.workouts.models import Workout
from fittrackee.users.utils.tokens import get_user_token
from fittrackee.oauth2.models import OAuth2Client, OAuth2Token
from flask_jwt_extended import decode_token
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


class Identities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['RATELIMIT_ENABLED'] = False
        with cls.app.app_context():
            cls.users, cls.workouts, cls.tokens, cls.csrf = [], [], [], []
            for _ in range(2):
                name = 'identity_' + secrets.token_hex(5)
                u = User(name, name+'@example.com', secrets.token_urlsafe(24))
                u.is_active = True
                db.session.add(u); db.session.flush()
                w = Workout(u.id, 1, datetime.now(timezone.utc))
                w.title = 'Synthetic identity API check'
                db.session.add(w); db.session.commit()
                cls.users.append(u.id); cls.workouts.append(w.short_id)
                token = get_user_token(u.id)
                cls.tokens.append(token); cls.csrf.append(decode_token(token)['csrf'])
            cls.workout_ids = [db.session.query(Workout.id).filter_by(user_id=uid).scalar() for uid in cls.users]

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            # Exact synthetic resources created by this class; no account-wide resets.
            for wid in cls.workout_ids:
                db.session.execute(text('DELETE FROM public.workouts WHERE id=:id'), dict(id=wid))
            for uid in cls.users:
                db.session.execute(text('DELETE FROM public.oauth2_token WHERE user_id=:id'), dict(id=uid))
                db.session.execute(text('DELETE FROM public.oauth2_client WHERE user_id=:id'), dict(id=uid))
                db.session.execute(text('DELETE FROM public.users WHERE id=:id'), dict(id=uid))
            db.session.commit()

    def setUp(self):
        self.key = secrets.token_hex(8)
        self.path = PREFIX+'/identities/provider/'+self.key
        self.claim = PREFIX+'/claims/provider/'+self.key
        self.secret = secrets.token_urlsafe(32)

    def call(self, path=None, method='GET', data=None, user=0, claim=None, csrf=True, bearer=None, headers=None):
        h = dict(headers or {})
        with self.app.test_client() as c:
            if bearer:
                h['Authorization'] = 'Bearer '+bearer
            elif user is not None:
                c.set_cookie('access_token_cookie', self.tokens[user], domain='identity.example.test')
                if csrf:
                    h['X-CSRF-TOKEN'] = self.csrf[user]
            if claim:
                h['X-Identity-Claim'] = claim
            return c.open(path or self.path, method=method, json=data, headers=h, base_url='https://identity.example.test')

    def bind(self, **kwargs):
        return self.call(method='PUT', data=dict(workout_id=self.workouts[0]), **kwargs)

    def sql(self, statement, **args):
        with self.app.app_context(), db.engine.begin() as c:
            return c.execute(text(statement), args).scalar() if statement.startswith('SELECT') else c.execute(text(statement), args)

    def test_no_anonymous_access(self):
        for method in ('GET','PUT','DELETE'):
            self.assertEqual(self.call(method=method,user=None).status_code,401)
        self.assertEqual(self.call(self.claim,method='PUT',data={},user=None).status_code,401)

    def test_cookie_csrf_required(self):
        self.assertEqual(self.bind(csrf=False).status_code,401)
        self.assertEqual(self.bind().status_code,201)

    def test_retry_and_conflict(self):
        self.assertEqual(self.bind().status_code,201)
        self.assertEqual(self.bind().status_code,200)
        with self.app.app_context():
            w=Workout(self.users[0],1,datetime.now(timezone.utc)); db.session.add(w); db.session.commit(); sid=w.short_id; wid=w.id
        try:
            self.assertEqual(self.call(method='PUT',data=dict(workout_id=sid)).status_code,409)
            self.assertEqual(self.call().json['workout_id'],self.workouts[0])
        finally:
            self.sql('DELETE FROM public.workouts WHERE id=:id',id=wid)

    def test_other_user_cannot_register_or_see_mapping(self):
        self.assertEqual(self.bind(user=1).status_code,404)
        self.assertEqual(self.bind().status_code,201)
        self.assertEqual(self.call(user=1).status_code,404)
        self.assertEqual(self.call(PREFIX+'/workouts/'+self.workouts[0]+'/identities',user=1).status_code,404)
        self.assertEqual(self.call(method='DELETE',user=1).status_code,204)
        self.assertEqual(self.call().status_code,200)

    def test_same_identity_can_exist_per_account(self):
        self.assertEqual(self.bind().status_code,201)
        self.assertEqual(self.call(method='PUT',user=1,data=dict(workout_id=self.workouts[1])).status_code,201)
        self.assertEqual(self.call(user=1).json['workout_id'],self.workouts[1])

    def test_new_sources_keep_identical_rides_independent(self):
        # First-use source strings need no provider creation endpoint.
        path_a=PREFIX+'/identities/first_'+self.key+'/'+self.key
        path_b=PREFIX+'/identities/second_'+self.key+'/'+self.key
        with self.app.app_context():
            original=db.session.get(Workout,self.workout_ids[0])
            duplicate=Workout(self.users[0],original.sport_id,original.workout_date,
                              distance=original.distance,duration=original.duration)
            duplicate.title=original.title
            db.session.add(duplicate); db.session.commit(); sid=duplicate.short_id; wid=duplicate.id
        try:
            self.assertEqual(self.call(path_a,'PUT',dict(workout_id=self.workouts[0])).status_code,201)
            self.assertEqual(self.call(path_b).status_code,404)
            self.assertEqual(self.call(path_b,'PUT',dict(workout_id=sid)).status_code,201)
            self.assertEqual(self.call(path_a).json['workout_id'],self.workouts[0])
            self.assertEqual(self.call(path_b).json['workout_id'],sid)
            self.assertNotEqual(self.call(path_a).json['workout_id'],self.call(path_b).json['workout_id'])
            for path,target in ((path_a,self.workouts[0]),(path_b,sid)):
                self.assertEqual(self.call(path,'PUT',dict(workout_id=target)).status_code,200)
            self.assertEqual(self.call(path_a,'PUT',dict(workout_id=sid)).status_code,409)
            self.assertEqual(self.call(path_a,'DELETE').status_code,204)
            self.assertEqual(self.call(path_a,'DELETE').status_code,204)
            self.assertEqual(self.call(path_b).json['workout_id'],sid)
            self.assertEqual(self.call('/api/workouts/'+self.workouts[0]).status_code,200)
        finally:
            self.sql('DELETE FROM public.workouts WHERE id=:id',id=wid)

    def test_claims_are_independent_across_sources(self):
        other=PREFIX+'/claims/another/'+self.key
        self.assertEqual(self.call(self.claim,'PUT',{},claim=self.secret).status_code,201)
        self.assertEqual(self.call(self.claim+'/begin-upload','POST',claim=self.secret).status_code,201)
        self.assertEqual(self.call(other,'PUT',{},claim=secrets.token_urlsafe(32)).status_code,201)
        self.assertEqual(self.call().status_code,404)
        self.assertEqual(self.call(PREFIX+'/identities/another/'+self.key).status_code,404)

    def test_concurrent_registration(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            statuses=list(pool.map(lambda _:self.bind().status_code,range(6)))
        self.assertEqual(sorted(statuses),[200]*5+[201])

    def test_concurrent_claim_and_direct_bind_fenced(self):
        tokens=[secrets.token_urlsafe(32) for _ in range(4)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda t:self.call(self.claim,'PUT',{},claim=t).status_code,tokens))
        self.assertEqual(sorted(results),[201,409,409,409])
        winner=tokens[results.index(201)]
        self.assertEqual(self.bind().status_code,409)
        self.assertEqual(self.bind(claim=winner).status_code,201)
        self.assertEqual(self.call(self.claim,'PUT',{},claim=winner).json['state'],'bound')

    def test_lost_claim_response_retry_and_renewal(self):
        self.assertEqual(self.call(self.claim,'PUT',{},claim=self.secret).status_code,201)
        self.assertEqual(self.call(self.claim,'PUT',{},claim=self.secret).status_code,200)
        self.assertEqual(self.call(self.claim,'PUT',{},claim=secrets.token_urlsafe(32)).status_code,409)

    def expire(self):
        self.sql("UPDATE ha_identity.slots SET expires_at=now()-interval '1 second' WHERE user_id=:uid AND source='provider' AND external_id=:key",uid=self.users[0],key=self.key)

    def test_expiry_and_stale_token_fencing(self):
        self.call(self.claim,'PUT',{},claim=self.secret); self.expire()
        self.assertEqual(self.call(self.claim+'/begin-upload','POST',claim=self.secret).status_code,409)
        self.assertEqual(self.call(self.claim,'PUT',{},claim=self.secret).status_code,409)
        fresh=secrets.token_urlsafe(32)
        self.assertEqual(self.call(self.claim,'PUT',{},claim=fresh).status_code,201)
        self.assertEqual(self.bind(claim=self.secret).status_code,409)
        self.assertEqual(self.bind(claim=fresh).status_code,201)

    def test_upload_uncertainty_no_expiry_and_explicit_recovery(self):
        self.call(self.claim,'PUT',{},claim=self.secret)
        first=self.call(self.claim+'/begin-upload','POST',claim=self.secret)
        self.assertEqual(first.status_code,201)
        self.assertTrue(first.json['upload_authorized'])
        retry=self.call(self.claim+'/begin-upload','POST',claim=self.secret)
        self.assertEqual(retry.status_code,200)
        self.assertFalse(retry.json['upload_authorized'])
        self.assertEqual(self.call(self.claim,'PUT',{},claim=secrets.token_urlsafe(32)).status_code,409)
        self.assertEqual(self.call(self.claim,'DELETE',claim=self.secret).status_code,409)
        self.assertEqual(self.call(self.claim,'DELETE',claim=self.secret,headers={'X-Identity-Reconciled':'true'}).status_code,204)
        self.assertEqual(self.call(self.claim,'DELETE',claim=self.secret).status_code,204)

    def test_lost_bind_response_safe_retry(self):
        self.call(self.claim,'PUT',{},claim=self.secret)
        self.call(self.claim+'/begin-upload','POST',claim=self.secret)
        self.assertEqual(self.bind(claim=self.secret).status_code,201)
        self.assertEqual(self.bind(claim=self.secret).status_code,200)

    def test_database_rejects_cross_user_reference(self):
        with self.assertRaises(IntegrityError):
            self.sql("INSERT INTO ha_identity.slots(user_id,source,external_id,state,workout_id) VALUES (:uid,'bad',:key,'bound',:wid)",uid=self.users[1],key=self.key,wid=self.workout_ids[0])

    def test_native_delete_cascades(self):
        with self.app.app_context():
            w=Workout(self.users[0],1,datetime.now(timezone.utc)); db.session.add(w); db.session.commit(); sid=w.short_id; wid=w.id
        self.assertEqual(self.call(method='PUT',data=dict(workout_id=sid)).status_code,201)
        self.sql('DELETE FROM public.workouts WHERE id=:id',id=wid)
        self.assertEqual(self.call().status_code,404)

    def test_public_workout_still_requires_ownership(self):
        self.sql("UPDATE workouts SET workout_visibility='PUBLIC' WHERE id=:id",id=self.workout_ids[0])
        try:
            self.assertEqual(self.call('/api/workouts/'+self.workouts[0],user=1).status_code,200)
            self.assertEqual(self.bind(user=1).status_code,404)
        finally:
            self.sql("UPDATE workouts SET workout_visibility='PRIVATE' WHERE id=:id",id=self.workout_ids[0])

    def test_concurrent_conflicting_registration(self):
        with self.app.app_context():
            w=Workout(self.users[0],1,datetime.now(timezone.utc)); db.session.add(w); db.session.commit(); sid=w.short_id; wid=w.id
        try:
            targets=[self.workouts[0],sid]
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                result=list(pool.map(lambda t:self.call(method='PUT',data=dict(workout_id=t)).status_code, targets))
            self.assertEqual(sorted(result),[201,409])
        finally:
            self.sql('DELETE FROM workouts WHERE id=:id',id=wid)

    def test_wrong_claim_cannot_release_or_begin(self):
        self.call(self.claim,'PUT',{},claim=self.secret)
        other=secrets.token_urlsafe(32)
        self.assertEqual(self.call(self.claim,'DELETE',claim=other).status_code,409)
        self.assertEqual(self.call(self.claim+'/begin-upload','POST',claim=other).status_code,409)
        self.assertEqual(self.bind(claim=other).status_code,409)
        self.assertEqual(self.call(self.claim,'DELETE',claim=self.secret).status_code,204)
        self.assertEqual(self.bind(claim=self.secret).status_code,409)

    def test_deleted_account_cascades_unbound_claim(self):
        with self.app.app_context():
            name='claim_cleanup_'+secrets.token_hex(4)
            u=User(name,name+'@example.com',secrets.token_urlsafe(24)); db.session.add(u); db.session.commit(); uid=u.id
        self.sql("INSERT INTO ha_identity.slots(user_id,source,external_id,state,token_hash,expires_at) VALUES (:uid,'cleanup',:key,'reserved',:hash,now()+interval '1 hour')",uid=uid,key=self.key,hash='a'*64)
        self.sql('DELETE FROM users WHERE id=:id',id=uid)
        self.assertEqual(self.sql('SELECT count(*) FROM ha_identity.slots WHERE user_id=:id',id=uid),0)

    def test_validation_and_opaque_ids(self):
        self.assertEqual(self.call(method='PUT',data=dict(workout_id=self.workouts[0],user_id=self.users[0])).status_code,400)
        self.assertEqual(self.call(PREFIX+'/identities/bad!/'+self.key).status_code,400)
        self.assertEqual(self.call(self.claim,'PUT',dict(lease_seconds=True),claim=self.secret).status_code,400)
        self.assertEqual(self.call(self.claim,'PUT',{},claim='short').status_code,400)
        self.assertEqual(self.call().headers['Cache-Control'],'no-store')
        for suffix in ('001','1','A','a'):
            self.assertEqual(self.call(self.path+suffix,'PUT',dict(workout_id=self.workouts[0])).status_code,201)

    def test_inactive_and_suspended_rejected(self):
        try:
            self.sql('UPDATE users SET is_active=false WHERE id=:uid',uid=self.users[0])
            self.assertEqual(self.call().status_code,401)
            self.sql('UPDATE users SET is_active=true,suspended_at=now() WHERE id=:uid',uid=self.users[0])
            self.assertEqual(self.call().status_code,403)
        finally:
            self.sql('UPDATE users SET is_active=true,suspended_at=NULL WHERE id=:uid',uid=self.users[0])

    def oauth(self, scope, revoked=False):
        with self.app.app_context():
            client=OAuth2Client(user_id=self.users[0],client_id=secrets.token_hex(12),client_secret='unused')
            client.set_client_metadata({'scope':scope}); db.session.add(client)
            tok=secrets.token_urlsafe(32)
            db.session.add(OAuth2Token(user_id=self.users[0],client_id=client.client_id,token_type='Bearer',access_token=tok,scope=scope,issued_at=int(time.time()),expires_in=3600,access_token_revoked_at=int(time.time()) if revoked else 0))
            db.session.commit(); return tok

    def test_oauth_scope_and_revocation(self):
        read=self.oauth('workouts:read'); write=self.oauth('workouts:write'); both=self.oauth('workouts:read workouts:write')
        self.assertEqual(self.bind(bearer=read).status_code,403)
        self.assertEqual(self.bind(bearer=write).status_code,201)
        self.assertEqual(self.call(bearer=read).status_code,200)
        self.assertEqual(self.call(bearer=write).status_code,403)
        self.assertEqual(self.bind(bearer=both).status_code,200)
        self.assertEqual(self.call(bearer=self.oauth('workouts:read',True)).status_code,401)

    def test_migration_idempotent_and_unknown_version_fails(self):
        with self.app.app_context():
            initialize(db.engine); initialize(db.engine)
            self.sql('UPDATE ha_identity.schema_version SET version=99')
            try:
                with self.assertRaises(RuntimeError): check_schema(db.engine)
                with self.assertRaises(RuntimeError): initialize(db.engine)
            finally: self.sql('UPDATE ha_identity.schema_version SET version=1')


if __name__ == '__main__':
    unittest.main(verbosity=2)
