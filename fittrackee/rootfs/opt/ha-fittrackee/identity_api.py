"""Companion identity API. No upstream source/schema changes or ingestion logic."""
import hashlib
import hmac
import re
from functools import wraps

from flask import Blueprint, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from fittrackee import create_app as upstream_create_app, db
from fittrackee.oauth2.server import require_auth
from fittrackee.utils import decode_short_id, encode_uuid

PREFIX = '/api/external-identities/v1'
KEY = 'user_id=:user_id AND source=:source AND external_id=:external_id'
bp = Blueprint('external_identities', __name__, url_prefix=PREFIX)


class Problem(Exception):
    def __init__(self, code, status=409):
        self.code, self.status = code, status


@bp.errorhandler(Problem)
def problem(error):
    return jsonify(error=error.code), error.status


@bp.errorhandler(SQLAlchemyError)
def unavailable(error):
    # Never log SQL parameters (external identifiers or claim hashes).
    return jsonify(error='storage_unavailable'), 503


@bp.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


def body(allowed):
    if request.content_length is None or request.content_length > 4096:
        raise Problem('invalid_body_size', 400)
    value = request.get_json(silent=True)
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise Problem('invalid_json', 400)
    return value


def protected(scope):
    def decorate(fn):
        @wraps(fn)
        @require_auth(scopes=[scope])
        def endpoint(user, source=None, external_id=None, **kwargs):
            if source is not None:
                # No case folding or numeric conversion; URL segments are opaque.
                if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', source):
                    raise Problem('invalid_source', 400)
                if (not external_id or external_id in ('.', '..') or len(external_id.encode('utf-8')) > 512
                        or any(ord(c) < 33 or ord(c) == 127 or c in '/\\' for c in external_id)):
                    raise Problem('invalid_external_id', 400)
            with db.engine.begin() as conn:
                conn.execute(text("SET LOCAL lock_timeout = '5s'"))
                conn.execute(text("SET LOCAL statement_timeout = '10s'"))
                args = dict(user_id=user.id, source=source, external_id=external_id)
                if source is not None:
                    # Transaction lock also serializes creation of absent rows.
                    # hash collisions only serialize unrelated identities; correctness uses PK.
                    lock = int.from_bytes(hashlib.sha256(
                        f'{user.id}\0{source}\0{external_id}'.encode()).digest()[:8], 'big', signed=True)
                    conn.execute(text('SELECT pg_advisory_xact_lock(:lock)'), dict(lock=lock))
                return fn(conn, args, **kwargs)
        return endpoint
    return decorate


def slot(conn, args):
    return conn.execute(text('SELECT *, expires_at > now() AS live FROM ha_identity.slots WHERE '+KEY), args).mappings().first()


def token_hash(required=False):
    token = request.headers.get('X-Identity-Claim')
    if token is None and not required:
        return None
    if not token or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token):
        raise Problem('invalid_claim_token', 400)
    return hashlib.sha256(token.encode()).hexdigest()


def owns_token(row, digest):
    return digest is not None and row['token_hash'] is not None and hmac.compare_digest(row['token_hash'], digest)


def owned_workout(conn, user_id, short_id):
    try:
        if not isinstance(short_id, str) or len(short_id) > 30:
            raise ValueError()
        uuid = decode_short_id(short_id)
    except Exception:
        raise Problem('workout_not_found', 404) from None
    workout = conn.execute(text('SELECT id, uuid FROM public.workouts WHERE uuid=:uuid AND user_id=:user_id FOR SHARE'),
                           dict(uuid=uuid, user_id=user_id)).mappings().first()
    if workout is None:
        raise Problem('workout_not_found', 404)
    return workout


def mapping(conn, row):
    workout = conn.execute(text('SELECT uuid FROM public.workouts WHERE id=:id AND user_id=:user_id'),
                           dict(id=row['workout_id'], user_id=row['user_id'])).scalar()
    if workout is None:
        raise Problem('identity_not_found', 404)
    return dict(source=row['source'], external_id=row['external_id'], workout_id=encode_uuid(workout))


@bp.get('/identities/<source>/<external_id>')
@protected('workouts:read')
def lookup(conn, args):
    row = slot(conn, args)
    if row is None or row['state'] != 'bound':
        raise Problem('identity_not_found', 404)
    return jsonify(mapping(conn, row))


@bp.put('/identities/<source>/<external_id>')
@protected('workouts:write')
def register(conn, args):
    data = body(['workout_id'])
    workout = owned_workout(conn, args['user_id'], data.get('workout_id'))
    row = slot(conn, args)
    digest = token_hash()
    if row and row['state'] == 'bound':
        if row['workout_id'] != workout['id']:
            raise Problem('identity_already_mapped')
        return jsonify(mapping(conn, row)), 200
    if row:
        if row['state'] == 'uploading' or row['live']:
            if not owns_token(row, digest):
                raise Problem('claim_busy')
        elif digest is not None:
            raise Problem('claim_expired')
    elif digest is not None:
        raise Problem('claim_not_found')
    conn.execute(text("""INSERT INTO ha_identity.slots (user_id,source,external_id,state,workout_id)
        VALUES (:user_id,:source,:external_id,'bound',:workout_id)
        ON CONFLICT (user_id,source,external_id) DO UPDATE SET state='bound',workout_id=EXCLUDED.workout_id,
        token_hash=NULL, expires_at=NULL,updated_at=now()"""), dict(args, workout_id=workout['id']))
    return jsonify(mapping(conn, slot(conn, args))), 201


@bp.get('/workouts/<workout_id>/identities')
@protected('workouts:read')
def identities(conn, args, workout_id):
    workout = owned_workout(conn, args['user_id'], workout_id)
    rows = conn.execute(text("SELECT * FROM ha_identity.slots WHERE user_id=:user_id AND workout_id=:workout_id AND state='bound' ORDER BY source,external_id"),
                        dict(user_id=args['user_id'], workout_id=workout['id'])).mappings()
    return jsonify(identities=[dict(source=row['source'], external_id=row['external_id'],
                                    workout_id=encode_uuid(workout['uuid'])) for row in rows])


@bp.delete('/identities/<source>/<external_id>')
@protected('workouts:write')
def remove(conn, args):
    conn.execute(text("DELETE FROM ha_identity.slots WHERE "+KEY+" AND state='bound'"), args)
    return '', 204


@bp.put('/claims/<source>/<external_id>')
@protected('workouts:write')
def claim(conn, args):
    data = body(['lease_seconds'])
    lease = data.get('lease_seconds', 900)
    if type(lease) is not int or not 30 <= lease <= 3600:
        raise Problem('invalid_lease', 400)
    digest = token_hash(required=True)
    row = slot(conn, args)
    if row and row['state'] == 'bound':
        return jsonify(state='bound', **mapping(conn, row)), 200
    if row and (row['state'] == 'uploading' or row['live']):
        if not owns_token(row, digest):
            raise Problem('claim_busy')
        if row['state'] == 'uploading':
            return jsonify(state='uploading', recovery_required=True), 200
    elif row and owns_token(row, digest):
        raise Problem('claim_expired_use_new_token')
    conn.execute(text("""INSERT INTO ha_identity.slots (user_id,source,external_id,state,token_hash,expires_at)
        VALUES (:user_id,:source,:external_id,'reserved',:digest,now()+(:lease * interval '1 second'))
        ON CONFLICT (user_id,source,external_id) DO UPDATE SET state='reserved',token_hash=EXCLUDED.token_hash,
        expires_at=EXCLUDED.expires_at,updated_at=now()"""), dict(args, digest=digest, lease=lease))
    return jsonify(state='reserved', expires_at=slot(conn, args)['expires_at'].isoformat()), 200 if row and row['live'] else 201


@bp.post('/claims/<source>/<external_id>/begin-upload')
@protected('workouts:write')
def begin_upload(conn, args):
    digest = token_hash(required=True)
    row = slot(conn, args)
    if row is None or row['state'] == 'bound':
        raise Problem('claim_not_found', 404)
    if not owns_token(row, digest):
        raise Problem('claim_busy')
    if row['state'] == 'reserved' and not row['live']:
        raise Problem('claim_expired')
    already_started = row['state'] == 'uploading'
    conn.execute(text("UPDATE ha_identity.slots SET state='uploading',expires_at=NULL,updated_at=now() WHERE "+KEY), args)
    return jsonify(state='uploading', recovery_required=already_started,
                   upload_authorized=not already_started), 200 if already_started else 201


@bp.delete('/claims/<source>/<external_id>')
@protected('workouts:write')
def release(conn, args):
    digest = token_hash(required=True)
    row = slot(conn, args)
    if row is None or row['state'] == 'bound':
        return '', 204
    if not owns_token(row, digest):
        raise Problem('claim_busy')
    if row['state'] == 'uploading' and request.headers.get('X-Identity-Reconciled') != 'true':
        raise Problem('reconciliation_required')
    conn.execute(text('DELETE FROM ha_identity.slots WHERE '+KEY), args)
    return '', 204


def initialize(engine):
    with engine.begin() as conn:
        conn.execute(text('SELECT pg_advisory_xact_lock(729610231)'))
        conn.execute(text('CREATE SCHEMA IF NOT EXISTS ha_identity'))
        conn.execute(text('CREATE TABLE IF NOT EXISTS ha_identity.schema_version (singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton), version integer NOT NULL)'))
        version = conn.execute(text('SELECT version FROM ha_identity.schema_version')).scalar()
        if version not in (None, 1):
            raise RuntimeError('Unsupported companion identity schema version')
        if version is None:
            conn.execute(text("""CREATE TABLE ha_identity.slots (
                user_id integer NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
                source varchar(64) NOT NULL, external_id varchar(512) NOT NULL,
                state text NOT NULL CHECK(state IN ('reserved','uploading','bound')),
                workout_id integer REFERENCES public.workouts(id) ON DELETE CASCADE,
                token_hash char(64), expires_at timestamptz,
                created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now(),
                PRIMARY KEY(user_id,source,external_id),
                CHECK ((state='bound' AND workout_id IS NOT NULL AND token_hash IS NULL AND expires_at IS NULL)
                    OR (state='reserved' AND workout_id IS NULL AND token_hash IS NOT NULL AND expires_at IS NOT NULL)
                    OR (state='uploading' AND workout_id IS NULL AND token_hash IS NOT NULL AND expires_at IS NULL)))"""))
            conn.execute(text('CREATE INDEX slots_workout ON ha_identity.slots(workout_id)'))
            # All new objects belong to our schema. No upstream constraints are changed.
            conn.execute(text("""CREATE FUNCTION ha_identity.check_owner() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF NEW.workout_id IS NOT NULL THEN
                        PERFORM id FROM public.workouts WHERE id=NEW.workout_id AND user_id=NEW.user_id FOR SHARE;
                        IF NOT FOUND THEN RAISE EXCEPTION 'identity ownership mismatch' USING ERRCODE='23514'; END IF;
                    END IF;
                    RETURN NEW;
                END $$"""))
            conn.execute(text('CREATE TRIGGER slots_owner BEFORE INSERT OR UPDATE ON ha_identity.slots FOR EACH ROW EXECUTE FUNCTION ha_identity.check_owner()'))
            conn.execute(text('INSERT INTO ha_identity.schema_version(version) VALUES (1)'))


def check_schema(engine):
    with engine.connect() as conn:
        if conn.execute(text('SELECT version FROM ha_identity.schema_version')).scalar() != 1:
            raise RuntimeError('Unsupported companion identity schema version')


def create_app():
    app = upstream_create_app()
    with app.app_context():
        check_schema(db.engine)
    app.register_blueprint(bp)
    return app


if __name__ == '__main__':
    app = upstream_create_app()
    with app.app_context():
        initialize(db.engine)
