#!/usr/bin/env python3
"""Bounded, resumable Strava ZIP importer. Inspect/plan are entirely offline.
Python 3.10+, standard library only. No direct database access or bulk mode.
"""
import argparse
import collections
from datetime import datetime, timezone
import csv
import gzip
import hashlib
import http.cookiejar
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile

VERSION = 1
MAX_BATCH = 20
MAX_MEMBER = 64 * 1024 * 1024
SPORTS = {'Ride': 1, 'Virtual Ride': 13, 'Mountain Bike Ride': 4,
          'E-Mountain Bike Ride': 7, 'Walk': 6, 'Hike': 3, 'Canoe': 20, 'Kayaking': 19}
RECORDINGS = {'.fit', '.tcx', '.gpx', '.kml', '.kmz'}
IMAGES = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}


class ImportErrorSafe(Exception):
    pass


class ApiError(ImportErrorSafe):
    def __init__(self, method, path, status=None, detail=None):
        self.status = status
        self.detail = detail
        super().__init__(f'{method} {urllib.parse.urlsplit(path).path}: '+
                         (f'HTTP {status}' if status else 'network outcome uncertain'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save_json(path, value):
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        path.parent.chmod(0o700)
    temporary=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    try:
        with temporary.open('x',encoding='utf-8') as stream:
            temporary.chmod(0o600)
            json.dump(value,stream,ensure_ascii=False,indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():
            temporary.unlink()


def safe_member(name):
    name=name.strip().replace('\\','/')
    path=PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or ':' in name:
        raise ImportErrorSafe('Unsafe archive member reference')
    return str(path)


class Export:
    def __init__(self,path):
        self.path=Path(path).resolve()
        self.zip=zipfile.ZipFile(self.path)
        entries=[info for info in self.zip.infolist() if not info.is_dir()]
        names=[safe_member(info.filename) for info in entries]
        if len(set(names)) != len(names):
            self.close()
            raise ImportErrorSafe('Archive contains ambiguous duplicate member names')
        self.entries=dict(zip(names,entries))
        self.headers,self.rows=self.csv_rows('activities.csv')
        self.media={}
        if 'media.csv' in self.entries:
            _,rows=self.csv_rows('media.csv')
            for row in rows:
                self.media[safe_member(row['Media Filename'])]=row.get('Media Caption','')
        ids=[row.get('Activity ID','') for row in self.rows]
        if any(not re.fullmatch(r'[0-9]{1,30}', value) for value in ids) or len(set(ids)) != len(ids):
            self.close()
            raise ImportErrorSafe('Activity IDs must be unique numeric strings')

    def __enter__(self):
        return self

    def __exit__(self,*_):
        self.close()

    def close(self):
        self.zip.close()

    def read(self,member,decompress=False):
        member=safe_member(member)
        info=self.entries.get(member)
        if info is None:
            raise ImportErrorSafe('A referenced archive member is missing')
        if info.file_size > MAX_MEMBER:
            raise ImportErrorSafe('Archive member exceeds the 64 MiB safety limit')
        with self.zip.open(info) as stream:
            data=stream.read(MAX_MEMBER+1)
        if decompress and member.lower().endswith('.gz'):
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
                data=stream.read(MAX_MEMBER+1)
        if len(data)>MAX_MEMBER:
            raise ImportErrorSafe('Decompressed member exceeds the 64 MiB safety limit')
        return data

    def csv_rows(self,member):
        reader=csv.reader(io.StringIO(self.read(member).decode('utf-8-sig'),newline=''))
        headers=next(reader,[])
        count=collections.Counter()
        unique=[]
        for header in headers:
            count[header]+=1
            unique.append(header if count[header]==1 else f'{header}#{count[header]}')
        rows=[]
        for values in reader:
            if not values:
                continue
            if len(values)!=len(headers):
                raise ImportErrorSafe('CSV row length differs from header; refusing lossy parsing')
            rows.append(dict(zip(unique,values)))
        return headers,rows

    def photos(self,row):
        value=row.get('Media','').strip()
        return list(dict.fromkeys(safe_member(x) for x in value.split('|') if x.strip()))

    def recording(self,row):
        name=row.get('Filename','').strip()
        if not name:
            return None
        name=safe_member(name)
        plain=name[:-3] if name.lower().endswith('.gz') else name
        return (name,plain,Path(plain).suffix.lower())


def inventory(export):
    types=collections.Counter(row['Activity Type'] for row in export.rows)
    formats=collections.Counter()
    missing=0
    media_refs=set()
    markers_without_paths=0
    for row in export.rows:
        recording=export.recording(row)
        if recording:
            formats[recording[2]]+=1
            missing+=recording[0] not in export.entries
        photos=export.photos(row)
        media_refs.update(photos)
        markers_without_paths+=bool(row.get('Media','').strip()) and not photos
    return dict(schema_version=VERSION,activity_count=len(export.rows),activity_types=dict(types),
                recording_formats=dict(formats),activities_without_file=sum(not row.get('Filename','') for row in export.rows),
                missing_recording_references=missing,media_csv_entries=len(export.media),
                referenced_media=len(media_refs),missing_media_references=sum(x not in export.entries for x in media_refs),
                media_markers_without_paths=markers_without_paths,
                repeated_csv_headers=[key for key,count in collections.Counter(export.headers).items() if count>1],
                archive_files=len(export.entries),uncompressed_bytes=sum(x.file_size for x in export.entries.values()))


def bounded(value):
    value=int(value)
    if not 1<=value<=MAX_BATCH:
        raise argparse.ArgumentTypeError(f'Batch limit must be 1..{MAX_BATCH}; there is no bulk mode')
    return value


def make_plan(export,limit=5,ids=None,types=None,sample=False,sport_map=None):
    if not 1 <= limit <= MAX_BATCH:
        raise ImportErrorSafe('Plan limit must be within 1..20')
    mappings=dict(SPORTS,**(sport_map or {}))
    allowed=set(types or ['Ride'])
    eligible=[]
    for row in export.rows:
        recording=export.recording(row)
        if (row['Activity Type'] in allowed and row['Activity Type'] in mappings and recording
                and recording[0] in export.entries and recording[2] in RECORDINGS):
            eligible.append(row)
    if ids:
        indexed={row['Activity ID']:row for row in eligible}
        if len(set(ids))!=len(ids) or len(ids)>limit or any(x not in indexed for x in ids):
            raise ImportErrorSafe('Requested IDs must be unique, eligible, and within the explicit plan limit')
        chosen=[indexed[x] for x in ids]
    elif sample:
        chosen=[]
        for extension in ('.fit','.tcx','.gpx','.kml','.kmz'):
            group=[row for row in eligible if export.recording(row)[2]==extension]
            if group and len(chosen)<limit:
                chosen.append(next((row for row in group if export.photos(row)),group[0]))
        chosen+=(row for row in eligible if row not in chosen)
        chosen=chosen[:limit]
    else:
        chosen=eligible[:limit]
    if not chosen:
        raise ImportErrorSafe('No eligible activities for this selection')
    items=[]
    for row in chosen:
        warnings=[]
        member,plain,extension=export.recording(row)
        marker='[strava:'+row['Activity ID']+']'
        notes=marker+'\n'+row.get('Activity Private Note','')
        metadata=dict(sport_id=int(mappings[row['Activity Type']]),title=row['Activity Name'][:255],
                      description=row.get('Activity Description','')[:10000],notes=notes[:500],
                      workout_visibility='private',analysis_visibility='private',map_visibility='private',media_visibility='private')
        if len(row['Activity Name'])>255 or len(row.get('Activity Description',''))>10000 or len(notes)>500:
            warnings.append('metadata_truncated_for_api; complete source values retained in this plan')
        photos=[]
        for name in export.photos(row):
            if name not in export.entries:
                warnings.append('missing_media_reference')
            elif Path(name).suffix.lower() not in IMAGES:
                warnings.append('unsupported_media_type')
            elif len(photos)>=20:
                warnings.append('media_limit_20; excess media not selected')
            else:
                caption=export.media.get(name,'')
                if len(caption)>1500:
                    warnings.append('caption_truncated_for_api; full caption retained in this plan')
                photos.append(dict(member=name,sha256=sha(export.read(name)),caption=caption,description=caption[:1500]))
        if row.get('Media','').strip() and not export.photos(row):
            warnings.append('media_marker_without_paths; no association inferred')
        items.append(dict(strava_id=row['Activity ID'],marker=marker,recording_member=member,
                          upload_filename=Path(plain).name,recording_sha256=sha(export.read(member,decompress=True)),
                          source_csv=row,metadata=metadata,photos=photos,warnings=warnings))
    return dict(schema_version=VERSION,archive_path=str(export.path),archive_sha256=file_sha(export.path),
                selected_types=sorted(allowed),eligible_count=len(eligible),items=items,
                policy='private; recording-derived metrics; no inferred photo associations; bounded explicit batches')


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,message,headers,newurl):
        if urllib.parse.urlsplit(request.full_url)[:2]!=urllib.parse.urlsplit(newurl)[:2]:
            raise ImportErrorSafe('Refused redirect outside the authenticated HTTPS origin')
        return super().redirect_request(request,fp,code,message,headers,newurl)


class Api:
    def __init__(self,credentials,expected_username):
        self.config=credentials
        self.base=credentials['base_url'].rstrip('/')
        parsed=urllib.parse.urlsplit(self.base)
        if parsed.scheme!='https' or not parsed.hostname or parsed.path or parsed.username or parsed.query or parsed.fragment:
            raise ImportErrorSafe('Target must be a plain HTTPS origin')
        self.username=expected_username
        self.jar=http.cookiejar.CookieJar()
        self.opener=urllib.request.build_opener(SameOriginRedirect(),urllib.request.HTTPCookieProcessor(self.jar))

    def request(self,path,method='GET',payload=None,form=None):
        url=urllib.parse.urljoin(self.base+'/',path)
        if urllib.parse.urlsplit(url)[:2]!=urllib.parse.urlsplit(self.base)[:2]:
            raise ImportErrorSafe('Refused cross-origin API request')
        headers={}
        data=None
        if self.config.get('access_token'):
            headers['Authorization']='Bearer '+self.config['access_token']
        if payload is not None:
            data=json.dumps(payload).encode()
            headers['Content-Type']='application/json'
        if form is not None:
            boundary='strava-import-'+uuid.uuid4().hex
            parts=[]
            for name,value in form.items():
                parts.append(f'--{boundary}\r\n'.encode())
                if isinstance(value,tuple):
                    filename,content,mime=value
                    filename=re.sub(r'[^a-zA-Z0-9._-]','_',filename)
                    parts.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
                    parts.append(content)
                else:
                    parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}'.encode())
                parts.append(b'\r\n')
            parts.append(f'--{boundary}--\r\n'.encode())
            data=b''.join(parts)
            headers['Content-Type']='multipart/form-data; boundary='+boundary
        if method not in ('GET','HEAD'):
            csrf=next((cookie.value for cookie in self.jar if cookie.name=='csrf_access_token'),None)
            if csrf:
                headers['X-CSRF-TOKEN']=csrf
        try:
            with self.opener.open(urllib.request.Request(url,data=data,headers=headers,method=method),timeout=180) as response:
                raw=response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            detail = None
            try:
                error_payload = json.loads(error.read(8192))
                message = error_payload.get('message', error_payload.get('error', ''))
                if isinstance(message, str) and not re.search(r'password|secret|token', message, re.I):
                    detail = message[:500]
            except (ValueError, AttributeError):
                pass
            raise ApiError(method,path,error.code,detail) from None
        except (urllib.error.URLError,TimeoutError,OSError):
            raise ApiError(method,path) from None

    def login(self):
        if not self.config.get('access_token'):
            self.request('/api/auth/login','POST',dict(email=self.config['email'],password=self.config['password']))
            cookie=next((c for c in self.jar if c.name=='access_token_cookie'),None)
            if cookie is None or not cookie.secure:
                raise ImportErrorSafe('The expected Secure authentication cookie is missing')
        profile=self.request('/api/auth/profile')['data']
        if profile['username']!=self.username:
            raise ImportErrorSafe('Authenticated username differs from --confirm-account')

    def find(self,marker):
        query=urllib.parse.urlencode(dict(notes=marker,per_page=100))
        workouts=self.request('/api/workouts?'+query)['data']['workouts']
        if len(workouts)>1:
            raise ImportErrorSafe('Multiple workouts match this Strava marker; resolve duplicates manually')
        if workouts:
            detail=self.request('/api/workouts/'+workouts[0]['id'])['data']['workouts'][0]
            if marker not in detail.get('notes',''):
                raise ImportErrorSafe('Remote duplicate marker could not be confirmed')
            return detail
        return None


def validate_plan(plan,export):
    if plan.get('schema_version')!=VERSION or not 1<=len(plan.get('items',[]))<=MAX_BATCH:
        raise ImportErrorSafe('Unsupported or unbounded plan')
    if file_sha(export.path)!=plan['archive_sha256']:
        raise ImportErrorSafe('Export archive differs from the reviewed plan')
    ids=[]
    for item in plan['items']:
        ident=item['strava_id']
        if not re.fullmatch(r'[0-9]{1,30}',ident) or item['marker']!='[strava:'+ident+']':
            raise ImportErrorSafe('Invalid plan activity marker')
        ids.append(ident)
        metadata=item['metadata']
        if not metadata.get('notes','').startswith(item['marker']):
            raise ImportErrorSafe('Plan must retain the Strava duplicate marker in private notes')
        if any(metadata.get(key)!='private' for key in ('workout_visibility','analysis_visibility','map_visibility','media_visibility')):
            raise ImportErrorSafe('This pilot importer only creates private data')
        if sha(export.read(item['recording_member'],decompress=True))!=item['recording_sha256']:
            raise ImportErrorSafe('Recording hash differs from the plan')
        if len(item['photos'])>20:
            raise ImportErrorSafe('Plan exceeds the API photo limit')
        for photo in item['photos']:
            if sha(export.read(photo['member']))!=photo['sha256']:
                raise ImportErrorSafe('Photo hash differs from the plan')
    if len(set(ids))!=len(ids):
        raise ImportErrorSafe('Plan contains duplicate Strava activity IDs')


class StateLock:
    def __init__(self,path):
        self.path=Path(str(path)+'.lock')
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        try:
            self.fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError:
            raise ImportErrorSafe('State is locked by another run; investigate a stale lock before removing it') from None
        os.write(self.fd,str(os.getpid()).encode())
        return self
    def __exit__(self,*_):
        os.close(self.fd)
        self.path.unlink()


def apply_plan(plan,export,api,state_path,limit=1,retry_uncertain=None):
    if not 1 <= limit <= MAX_BATCH:
        raise ImportErrorSafe('Execution batch limit must be within 1..20')
    retry_uncertain=set(retry_uncertain or [])
    path=Path(state_path)
    with StateLock(path):
        state=json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else dict(schema_version=VERSION,base_url=api.base,username=api.username,activities={})
        if state.get('base_url')!=api.base or state.get('username')!=api.username or state.get('schema_version')!=VERSION:
            raise ImportErrorSafe('Journal belongs to a different target/account or schema')
        summary=collections.Counter()
        attempted=0
        for item in plan['items']:
            ident=item['strava_id']
            record=state['activities'].get(ident)
            fingerprint=sha(json.dumps(item,sort_keys=True,ensure_ascii=False).encode())
            if record and record['item_sha256']!=fingerprint:
                raise ImportErrorSafe('A previously journaled activity changed; do not silently overwrite it')
            if record and record.get('status')=='complete':
                summary['already_complete']+=1
                continue
            if attempted>=limit:
                break
            attempted+=1
            if record is None:
                record=dict(item_sha256=fingerprint,status='prepared',media={},events=[])
                state['activities'][ident]=record
            def persist(event):
                record['events'].append(dict(at=datetime.now(timezone.utc).isoformat(),event=event))
                save_json(path,state)
            remote=api.find(item['marker'])
            if remote:
                record.update(status='complete',workout_id=remote['id'])
                persist('reconciled_existing_marker')
                summary['reconciled']+=1
                continue
            if record.get('workout_attempted') and ident not in retry_uncertain:
                raise ImportErrorSafe('An earlier workout request has an uncertain outcome; no automatic retry. Reconcile before --retry-uncertain.')
            try:
                for photo in item['photos']:
                    entry=record['media'].setdefault(photo['member'],{})
                    if not entry.get('id'):
                        if entry.get('attempted') and ident not in retry_uncertain:
                            raise ImportErrorSafe('An earlier media request has an uncertain outcome; no automatic retry')
                        entry['attempted']=True
                        persist('media_request_started')
                        response=api.request('/api/media','POST',form={'file':(Path(photo['member']).name,export.read(photo['member']),{'.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png','.gif':'image/gif','.webp':'image/webp'}[Path(photo['member']).suffix.lower()])})
                        entry.update(id=response['id'],url=response['url'])
                        persist('media_response_saved')
                    if not entry.get('caption_done'):
                        api.request('/api/media/'+entry['id'],'PATCH',payload={'description':photo['description']})
                        entry['caption_done']=True
                        persist('caption_saved')
                metadata=dict(item['metadata'],media_attachment_ids=[record['media'][p['member']]['id'] for p in item['photos']])
                record['workout_attempted']=True
                persist('workout_request_started')
                response=api.request('/api/workouts','POST',form={
                    'file':(item['upload_filename'],export.read(item['recording_member'],decompress=True),'application/octet-stream'),
                    'data':json.dumps(metadata,ensure_ascii=False)})
                workouts=response.get('data',{}).get('workouts',[])
                if len(workouts)!=1:
                    raise ImportErrorSafe('Unexpected upload response; reconcile before retrying')
                workout=workouts[0]
                record.update(status='complete',workout_id=workout['id'],server_statistics={
                    key:workout.get(key) for key in ('workout_date','distance','duration','moving','ascent','descent','ave_hr','max_hr','ave_cadence','max_cadence','ave_power','max_power','calories')})
                persist('workout_response_saved')
                summary['imported']+=1
            except (ImportErrorSafe,KeyError,ValueError) as error:
                record.update(status='needs_review',last_error=str(error),last_error_detail=getattr(error,'detail',None))
                persist('stopped_after_error; no automatic POST retry')
                raise
        save_json(path,state)
        return dict(summary)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    inspect_parser=commands.add_parser('inspect',help='Offline aggregate inventory; no account data printed')
    inspect_parser.add_argument('export',type=Path)
    inspect_parser.add_argument('--report',type=Path)
    planner=commands.add_parser('plan',help='Offline bounded pilot plan; contains private metadata')
    planner.add_argument('export',type=Path)
    planner.add_argument('--output',type=Path,required=True)
    planner.add_argument('--limit',type=bounded,default=5)
    planner.add_argument('--activity-id',action='append')
    planner.add_argument('--type',dest='types',action='append',help='Default: Ride only')
    planner.add_argument('--sample',action='store_true',help='Prefer different recording formats and explicit photos')
    planner.add_argument('--sport-map',type=Path,help='Explicit Strava activity type to FitTrackee sport-ID mapping')
    apply_parser=commands.add_parser('apply',help='Dry-run unless --execute is supplied; default batch limit 1')
    apply_parser.add_argument('plan',type=Path)
    apply_parser.add_argument('--export',type=Path,help='Relocated copy of the same ZIP')
    apply_parser.add_argument('--credentials',type=Path)
    apply_parser.add_argument('--state',type=Path)
    apply_parser.add_argument('--confirm-account')
    apply_parser.add_argument('--limit',type=bounded,default=1)
    apply_parser.add_argument('--execute',action='store_true')
    apply_parser.add_argument('--retry-uncertain',action='append',default=[],help='Explicit activity ID after manual reconciliation')
    args=parser.parse_args()
    try:
        if args.command in ('inspect','plan'):
            with Export(args.export) as export:
                if args.command=='inspect':
                    report=inventory(export)
                    if args.report:
                        if args.report.resolve() == export.path:
                            raise ImportErrorSafe('Report must not overwrite the source ZIP')
                        save_json(args.report,report)
                    print(json.dumps(report,indent=2))
                else:
                    if args.output.resolve() == export.path:
                        raise ImportErrorSafe('Plan must not overwrite the source ZIP')
                    mappings=json.loads(args.sport_map.read_text(encoding='utf-8-sig')) if args.sport_map else None
                    plan=make_plan(export,args.limit,args.activity_id,args.types,args.sample,mappings)
                    save_json(args.output,plan)
                    print(json.dumps(dict(plan=str(args.output),selected_activities=len(plan['items']),
                                          selected_photos=sum(len(x['photos']) for x in plan['items']),
                                          warning_count=sum(len(x['warnings']) for x in plan['items']),network_requests=0)))
        else:
            plan=json.loads(args.plan.read_text(encoding='utf-8-sig'))
            with Export(args.export or Path(plan['archive_path'])) as export:
                validate_plan(plan,export)
                if not args.execute:
                    print(json.dumps(dict(mode='dry-run',planned_activities=len(plan['items']),maximum_batch=args.limit,network_requests=0)))
                    return
                if not args.credentials or not args.state or not args.confirm_account:
                    raise ImportErrorSafe('--execute requires --credentials, --state and --confirm-account')
                api=Api(json.loads(args.credentials.read_text(encoding='utf-8-sig')),args.confirm_account)
                api.login()
                print(json.dumps(apply_plan(plan,export,api,args.state,args.limit,args.retry_uncertain)))
    except (ImportErrorSafe,OSError,ValueError,KeyError,zipfile.BadZipFile,EOFError) as error:
        print('STOPPED: '+str(error),file=sys.stderr)
        sys.exit(1)


if __name__=='__main__':
    main()
