#!/usr/bin/env python3
"""Check companion identities for one exact retained synthetic fixture over HTTPS.
No app restart, restore, native upload or personal account use is performed here.
"""
import argparse
import json
from pathlib import Path
import secrets
import urllib.error
import urllib.request

from live_tests import Client, DEFAULT_CONFIG, TestError, protect_credentials, save, verify

PREFIX='/api/external-identities/v1'


def request(client,path,method='GET',payload=None,token=None,reconciled=False):
    headers={}
    if payload is not None:
        headers['Content-Type']='application/json'
    if token:
        headers['X-Identity-Claim']=token
    if reconciled:
        headers['X-Identity-Reconciled']='true'
    csrf=next((c.value for c in client.jar if c.name=='csrf_access_token'),None)
    if csrf:
        headers['X-CSRF-TOKEN']=csrf
    req=urllib.request.Request(client.base+PREFIX+path,
        data=json.dumps(payload).encode() if payload is not None else None,headers=headers,method=method)
    try:
        with client.opener.open(req,timeout=30) as r:
            raw=r.read(); return r.status,json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return e.code,None


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['bind','verify','cleanup'])
    p.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    p.add_argument('--fixture',type=Path,required=True,help='Retained live_tests.py fixture checkpoint')
    p.add_argument('--state',type=Path,required=True,help='Private companion checkpoint, including test claim secret')
    args=p.parse_args()
    client=Client(json.loads(args.config.read_text())); client.login()
    fixture=json.loads(args.fixture.read_text()); verify(client,fixture)
    if args.command=='bind':
        if args.state.exists():
            raise TestError('State already exists; use verify rather than creating competing claims')
        state=dict(base_url=client.base,username=fixture['username'],run_id=fixture['run_id'],
                   workout_id=fixture['workout_id'],external_id='synthetic-'+fixture['run_id'],
                   token=secrets.token_urlsafe(32),pending_token=secrets.token_urlsafe(32))
        save(args.state,state); protect_credentials(args.state)
    else:
        state=json.loads(args.state.read_text())
    if any(state[k]!=fixture[k] for k in ('base_url','username','run_id','workout_id')):
        raise TestError('Companion checkpoint does not match this exact managed fixture')
    external=state['external_id']
    if external!='synthetic-'+fixture['run_id']:
        raise TestError('Not a managed synthetic identity')
    identity='/identities/synthetic/'+external
    claim='/claims/synthetic/'+external
    pending='/claims/synthetic-pending/'+external
    if args.command=='bind':
        assert request(client,claim,'PUT',{},state['token'])[0]==201
        assert request(client,claim+'/begin-upload','POST',token=state['token'])[0]==201
        # Bind an existing exact synthetic fixture; this tool never uploads workouts.
        assert request(client,identity,'PUT',dict(workout_id=state['workout_id']),state['token'])[0]==201
        assert request(client,identity,'PUT',dict(workout_id=state['workout_id']),state['token'])[0]==200
        assert request(client,pending,'PUT',{},state['pending_token'])[0]==201
        assert request(client,pending+'/begin-upload','POST',token=state['pending_token'])[0]==201
    if args.command in ('bind','verify'):
        status,mapping=request(client,identity)
        assert status==200 and mapping['workout_id']==state['workout_id']
        status,result=request(client,'/workouts/'+state['workout_id']+'/identities')
        assert status==200 and any(x['external_id']==external for x in result['identities'])
        status,result=request(client,pending,'PUT',{},state['pending_token'])
        assert status==200 and result['state']=='uploading' and result['recovery_required']
        assert request(client,pending,'PUT',{},secrets.token_urlsafe(32))[0]==409
        print('PASS: HTTPS mapping, identical retry, owner list and persistent uncertain claim; workout/photo checkpoint unchanged')
    else:
        assert request(client,pending,'DELETE',token=state['pending_token'],reconciled=True)[0]==204
        assert request(client,identity,'DELETE')[0]==204
        assert request(client,identity)[0]==404
        print('Removed only this synthetic mapping/claim; retained workout/photo unchanged')


if __name__=='__main__':
    main()
