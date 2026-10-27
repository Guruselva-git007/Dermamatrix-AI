"""Account lifecycle, durable session revocation and privacy boundaries.

Opt-in after explicit migration. Uses existing users/auth_accounts and never
stores raw action tokens. No medical/policy/retention approval is inferred.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from urllib.parse import urlencode, urlsplit

from flask import Blueprint, current_app, jsonify, request, session
import pymysql
from werkzeug.security import check_password_hash, generate_password_hash
from delivery import DeliveryUnavailable, delivery_mode, send_message

TOKEN_PURPOSES = {'verify_email', 'reset_password', 'change_email'}
EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
DUMMY_HASH = generate_password_hash('synthetic-non-account-password')


def enabled():
    return current_app.config.get('CONSUMER_ENABLED', False)


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def token_digest(value):
    return hmac.new(str(current_app.secret_key).encode(), value.encode(), hashlib.sha256).hexdigest()


def json_object():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        raise ValueError('Send a JSON object.')
    return value


def password_value(value):
    if not isinstance(value, str) or not 8 <= len(value) <= 128:
        raise ValueError('Use a password of 8–128 characters.')
    return value


def valid_email(value):
    return isinstance(value, str) and len(value) <= 254 and bool(EMAIL_RE.fullmatch(value))


def csrf_token():
    if not session.get('csrf_token'):
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def device_label(user_agent):
    browser = 'Edge' if 'Edg/' in user_agent else 'Firefox' if 'Firefox/' in user_agent else 'Chrome' if 'Chrome/' in user_agent else 'Safari' if 'Safari/' in user_agent else 'Browser'
    platform = 'iPhone/iPad' if any(value in user_agent for value in ['iPhone', 'iPad']) else 'Android' if 'Android' in user_agent else 'macOS' if 'Macintosh' in user_agent else 'Windows' if 'Windows' in user_agent else 'Linux' if 'Linux' in user_agent else 'device'
    return browser + ' · ' + platform


def start_session(connection, user):
    raw = secrets.token_urlsafe(32)
    expires = utcnow() + current_app.permanent_session_lifetime
    with connection.cursor() as cursor:
        cursor.execute('INSERT INTO account_sessions(session_id,user_id,device_label,created_at,expires_at) VALUES(%s,%s,%s,%s,%s)',
                       (digest(raw), user['id'], device_label(request.user_agent.string), utcnow(), expires))
    connection.commit()
    session.clear()
    session.update(user_id=user['id'], patient_id=user['patient_id'], security_session=raw)
    session.permanent = True
    csrf_token()


def session_valid(connection, user_id):
    raw = session.get('security_session', '')
    if not isinstance(raw, str) or len(raw) != 43:
        return False
    with connection.cursor() as cursor:
        cursor.execute('SELECT session_id FROM account_sessions WHERE session_id=%s AND user_id=%s AND revoked=FALSE AND expires_at>UTC_TIMESTAMP()',
                       (digest(raw), user_id))
        return cursor.fetchone() is not None


def revoke_current(connection):
    raw = session.get('security_session', '')
    with connection.cursor() as cursor:
        cursor.execute('UPDATE account_sessions SET revoked=TRUE WHERE session_id=%s AND user_id=%s', (digest(raw), session.get('user_id')))
    connection.commit()


def budget(connection, scope, identifier, limit, seconds):
    """Atomic SQL budget shared across workers. No plaintext IP/email retained."""
    bucket = int(time.time()) // seconds
    key = token_digest(f'{scope}:{identifier}:{bucket}')
    with connection.cursor() as cursor:
        cursor.execute('INSERT INTO request_budgets(budget_key,window_start,attempts) VALUES(%s,%s,1) ON DUPLICATE KEY UPDATE attempts=attempts+1', (key, bucket * seconds))
    connection.commit()
    with connection.cursor() as cursor:
        cursor.execute('SELECT attempts FROM request_budgets WHERE budget_key=%s', (key,))
        allowed = cursor.fetchone()['attempts'] <= limit
    if not allowed:
        from werkzeug.exceptions import TooManyRequests
        raise TooManyRequests('Too many attempts. Try again later.')


def record(connection, user_id, kind, subject, data, dedupe=None):
    identifier = secrets.token_hex(16)
    key = digest(f'{user_id}:{kind}:{dedupe or identifier}')
    with connection.cursor() as cursor:
        cursor.execute('INSERT IGNORE INTO consumer_records(record_id,user_id,kind,subject_id,dedupe_key,data_json,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                       (identifier, user_id, kind, subject, key, json.dumps(data), utcnow(), utcnow()))
        cursor.execute('SELECT record_id,data_json,created_at FROM consumer_records WHERE dedupe_key=%s AND user_id=%s', (key, user_id))
        return cursor.fetchone()


def reauthenticate(connection, user_id, password):
    with connection.cursor() as cursor:
        cursor.execute('SELECT password_hash FROM auth_accounts WHERE user_id=%s', (user_id,))
        account = cursor.fetchone()
    if not isinstance(password, str) or len(password) > 128 or not account or not check_password_hash(account['password_hash'], password):
        from werkzeug.exceptions import Unauthorized
        raise Unauthorized('Confirm your current password to continue.')


def issue_token(connection, user_id, purpose, email):
    if purpose not in TOKEN_PURPOSES:
        raise ValueError('Unsupported account action.')
    if delivery_mode() == 'disabled':
        raise DeliveryUnavailable('Email delivery is not configured. No email was sent.')
    origin = os.getenv('DERMAMATRIX_APP_ORIGIN', '')
    parsed = urlsplit(origin)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.path not in {'', '/'} or parsed.query or parsed.fragment or parsed.username:
        raise DeliveryUnavailable('Configure the exact application origin for account links.')
    if os.getenv('DERMAMATRIX_ENV') != 'test' and parsed.scheme != 'https':
        raise DeliveryUnavailable('Account links require HTTPS outside isolated tests.')
    token = secrets.token_urlsafe(32)
    with connection.cursor() as cursor:
        cursor.execute('UPDATE account_tokens SET consumed=TRUE WHERE user_id=%s AND purpose=%s AND consumed=FALSE', (user_id, purpose))
        cursor.execute('INSERT INTO account_tokens(token_hash,user_id,purpose,target_email,expires_at,created_at) VALUES(%s,%s,%s,%s,%s,%s)',
                       (token_digest(token), user_id, purpose, email, utcnow() + timedelta(minutes=30), utcnow()))
    connection.commit()
    link = origin.rstrip('/') + '/#' + urlencode({'account_action': purpose, 'token': token})
    try:
        return send_message(email, 'DermaMatrix account action', f'Open this link to review and confirm your account action. It expires in 30 minutes and can be used once.\n\n{link}\n\nIf you did not request this, ignore this message.')
    except DeliveryUnavailable:
        with connection.cursor() as cursor:
            cursor.execute('UPDATE account_tokens SET consumed=TRUE WHERE token_hash=%s', (token_digest(token),))
        connection.commit()
        raise


def register_security(app, database, current_user):
    bp = Blueprint('consumer_security', __name__)

    @contextmanager
    def owned():
        connection = database()
        try:
            user = current_user(connection)
            if not user:
                from werkzeug.exceptions import Unauthorized
                raise Unauthorized('Sign in again to manage your account.')
            yield connection, user
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @bp.before_request
    def available():
        if not enabled():
            return jsonify(error='Account development features require the explicit consumer migration and configuration.', code='CONSUMER_NOT_ENABLED'), 503

    @app.before_request
    def consumer_boundary():
        if not enabled() or not request.path.startswith('/api/'):
            return
        unsafe = request.method not in {'GET', 'HEAD', 'OPTIONS'}
        if unsafe:
            supplied = request.headers.get('X-CSRF-Token', '')
            expected = session.get('csrf_token', '')
            if not expected or not hmac.compare_digest(supplied, expected):
                return jsonify(error='Refresh the page and retry.', code='CSRF_REQUIRED'), 403
        # A revoked/legacy cookie must not silently downgrade to guest processing.
        if session.get('user_id') and request.path not in {'/api/auth/login', '/api/auth/register', '/api/auth/logout', '/api/security/csrf', '/api/security/reset-password', '/api/security/action'}:
            connection = database()
            try:
                user = current_user(connection)
                if not user:
                    session.clear()
                    return jsonify(error='Your session ended. Sign in again.', code='SESSION_REVOKED'), 401
                profile_payload = request.get_json(silent=True) if request.path == '/api/profile' else None
                profile_health = isinstance(profile_payload, dict) and any(k in profile_payload for k in ['past_history', 'current_history'])
                protected = unsafe and (request.path.startswith(('/api/assessments', '/api/sweat-assessments', '/api/routines', '/api/progress-checkins', '/api/routine-schedules', '/api/journey/assessments', '/api/clinical-review-requests', '/api/profiles')) or profile_health)
                if request.method == 'DELETE' and request.path.startswith('/api/routines/'):
                    protected = False  # Archiving stops future work; it preserves history.
                if protected:
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT processing_paused FROM account_security WHERE user_id=%s', (user['id'],))
                        security = cursor.fetchone()
                    if security and security['processing_paused']:
                        return jsonify(error='New health processing is paused. Manage this in Privacy.', code='PROCESSING_PAUSED'), 403
            finally:
                connection.close()
        if request.path in {'/api/auth/login', '/api/auth/register', '/api/assessments', '/api/sweat-assessments'} and unsafe:
            connection = database()
            try:
                budget(connection, request.path, str(request.remote_addr), 30 if 'auth' in request.path else 20, 300)
                if 'auth' in request.path:
                    payload = request.get_json(silent=True) or {}
                    email = str(payload.get('email_address', ''))[:254] if isinstance(payload, dict) else ''
                    budget(connection, request.path + ':account', email.lower(), 10, 300)
            finally:
                connection.close()

    @app.after_request
    def csrf_response(response):
        if enabled() and request.path.startswith('/api/'):
            if session.get('csrf_token'):
                response.headers['X-CSRF-Token'] = session['csrf_token']
        return response

    @bp.get('/api/security/csrf')
    def get_csrf():
        return jsonify(csrf_token=csrf_token(), enabled=True)

    @bp.get('/api/security/account')
    def account_status():
        with owned() as (connection, user):
            with connection.cursor() as cursor:
                cursor.execute('SELECT email_verified_at,processing_paused FROM account_security WHERE user_id=%s', (user['id'],))
                security = cursor.fetchone() or {}
                cursor.execute('SELECT session_id,device_label,created_at,expires_at FROM account_sessions WHERE user_id=%s AND revoked=FALSE AND expires_at>UTC_TIMESTAMP() ORDER BY created_at DESC,session_id', (user['id'],))
                sessions = cursor.fetchall()
            for item in sessions:
                item['current'] = item['session_id'] == digest(session.get('security_session', ''))
            return jsonify(email_verified=bool(security.get('email_verified_at')), processing_paused=bool(security.get('processing_paused')), sessions=sessions,
                           delivery_mode=delivery_mode(), delivery_verified=False)

    @bp.post('/api/security/verify-email')
    def verify_email():
        with owned() as (connection, user):
            budget(connection, 'verification', str(user['id']), 3, 900)
            delivery = issue_token(connection, user['id'], 'verify_email', user['email_address'])
            return jsonify(message='Verification message prepared.', delivery=delivery)

    @bp.post('/api/security/reset-password')
    def request_reset():
        payload = json_object()
        email = str(payload.get('email_address', '')).strip().lower()
        if not valid_email(email):
            raise ValueError('Enter a valid email address.')
        connection = database()
        try:
            budget(connection, 'reset-ip', str(request.remote_addr), 10, 900)
            budget(connection, 'reset-email', email, 3, 900)
            if delivery_mode() == 'disabled':
                raise DeliveryUnavailable('Email delivery is not configured. No email was sent.')
            with connection.cursor() as cursor:
                cursor.execute('SELECT a.user_id FROM auth_accounts a JOIN users u ON u.id=a.user_id WHERE a.email_address=%s AND u.is_active=TRUE', (email,))
                account = cursor.fetchone()
            # Same password-hash work for existing/nonexistent accounts. Delivery
            # timing still needs measurement on a chosen external provider.
            check_password_hash(DUMMY_HASH, 'dummy-reset-work')
            # Queue the same operation for known/unknown accounts. Raw tokens
            # are minted only by the separate mail worker, never in a job payload.
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO account_mail_jobs(job_id,user_id,purpose,target_email,created_at,updated_at) VALUES(%s,%s,%s,%s,UTC_TIMESTAMP(),UTC_TIMESTAMP())',
                               (secrets.token_hex(16), account['user_id'] if account else None, 'reset_password', email if account else None))
            connection.commit()
            return jsonify(message='If an active account matches, a reset request has been queued. The configured mail worker must process it.', delivery_mode=delivery_mode())
        finally:
            connection.close()

    @bp.post('/api/security/password')
    def change_password():
        payload = json_object()
        password = password_value(payload.get('new_password'))
        with owned() as (connection, user):
            budget(connection, 'sensitive', str(user['id']), 10, 900)
            reauthenticate(connection, user['id'], payload.get('current_password'))
            with connection.cursor() as cursor:
                cursor.execute('UPDATE auth_accounts SET password_hash=%s WHERE user_id=%s', (generate_password_hash(password), user['id']))
                cursor.execute('UPDATE account_sessions SET revoked=TRUE WHERE user_id=%s', (user['id'],))
                cursor.execute('UPDATE account_tokens SET consumed=TRUE WHERE user_id=%s', (user['id'],))
            start_session(connection, user)
            record(connection, user['id'], 'security_event', '', {'action': 'password_changed'})
            notification = {'state': 'failed'}
            try:
                notification = send_message(user['email_address'], 'DermaMatrix account security', 'Your password was changed and other sessions were revoked. If this was not you, contact your application operator.')
            except DeliveryUnavailable:
                pass
            return jsonify(message='Password changed. Other sessions and outstanding account links have been revoked.', notification=notification)

    @bp.post('/api/security/email')
    def change_email():
        payload = json_object()
        email = str(payload.get('new_email', '')).strip().lower()
        if not valid_email(email):
            raise ValueError('Enter a valid email address.')
        with owned() as (connection, user):
            budget(connection, 'email-change', str(user['id']), 3, 900)
            reauthenticate(connection, user['id'], payload.get('current_password'))
            if email == user['email_address']:
                raise ValueError('Choose a different email address.')
            delivery = issue_token(connection, user['id'], 'change_email', email)
            return jsonify(message='Confirm the link sent to the new address. Your account email has not changed.', delivery=delivery)

    @bp.post('/api/security/sessions/revoke')
    def revoke_sessions():
        payload = json_object()
        with owned() as (connection, user):
            budget(connection, 'sensitive', str(user['id']), 10, 900)
            reauthenticate(connection, user['id'], payload.get('current_password'))
            identifier = payload.get('session_id')
            with connection.cursor() as cursor:
                if identifier == 'others':
                    cursor.execute('UPDATE account_sessions SET revoked=TRUE WHERE user_id=%s AND session_id<>%s', (user['id'], digest(session.get('security_session', ''))))
                elif isinstance(identifier, str) and re.fullmatch('[a-f0-9]{64}', identifier):
                    cursor.execute('UPDATE account_sessions SET revoked=TRUE WHERE user_id=%s AND session_id=%s', (user['id'], identifier))
                else:
                    raise ValueError('Choose a session to revoke.')
            if identifier == digest(session.get('security_session', '')):
                session.clear()
            return jsonify(message='Selected sessions revoked.')

    @bp.post('/api/security/action')
    def confirm_action():
        payload = json_object()
        raw = payload.get('token')
        purpose = payload.get('purpose')
        if not isinstance(raw, str) or not re.fullmatch('[A-Za-z0-9_-]{43}', raw) or purpose not in TOKEN_PURPOSES:
            raise ValueError('This account link is invalid or expired. Request a new one.')
        password = password_value(payload.get('new_password')) if purpose == 'reset_password' else None
        connection = database()
        old_email = None
        try:
            budget(connection, 'action-ip', str(request.remote_addr), 15, 900)
            with connection.cursor() as cursor:
                cursor.execute('SELECT t.*,u.is_active FROM account_tokens t JOIN users u ON u.id=t.user_id WHERE token_hash=%s AND purpose=%s FOR UPDATE', (token_digest(raw), purpose))
                token = cursor.fetchone()
                if not token or token['consumed'] or not token['is_active'] or token['expires_at'] <= utcnow():
                    raise ValueError('This account link is invalid or expired. Request a new one.')
                uid = token['user_id']
                cursor.execute('UPDATE account_tokens SET consumed=TRUE WHERE token_hash=%s AND consumed=FALSE', (token_digest(raw),))
                if purpose == 'reset_password':
                    cursor.execute('UPDATE auth_accounts SET password_hash=%s WHERE user_id=%s', (generate_password_hash(password), uid))
                    cursor.execute('UPDATE account_tokens SET consumed=TRUE WHERE user_id=%s', (uid,))
                    cursor.execute('UPDATE account_sessions SET revoked=TRUE WHERE user_id=%s', (uid,))
                else:
                    cursor.execute('SELECT email_address FROM auth_accounts WHERE user_id=%s FOR UPDATE', (uid,))
                    old_email = cursor.fetchone()['email_address']
                    if purpose == 'verify_email' and old_email != token['target_email']:
                        raise ValueError('The account email changed. Request a new verification link.')
                    if purpose == 'change_email':
                        cursor.execute('UPDATE auth_accounts SET email_address=%s WHERE user_id=%s', (token['target_email'], uid))
                        cursor.execute('UPDATE users SET email_address=%s,updated_at=UTC_TIMESTAMP() WHERE id=%s', (token['target_email'], uid))
                        cursor.execute('UPDATE account_tokens SET consumed=TRUE WHERE user_id=%s', (uid,))
                        cursor.execute('UPDATE account_sessions SET revoked=TRUE WHERE user_id=%s', (uid,))
                    cursor.execute('INSERT INTO account_security(user_id,email_verified_at,updated_at) VALUES(%s,UTC_TIMESTAMP(),UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE email_verified_at=UTC_TIMESTAMP(),updated_at=UTC_TIMESTAMP()', (uid,))
                record(connection, uid, 'security_event', '', {'action': purpose + '_completed'})
            connection.commit()
            if purpose in {'reset_password', 'change_email'}:
                session.clear()
            notification = {'state': 'not_requested'}
            if purpose in {'reset_password', 'change_email'}:
                try:
                    notification = send_message(old_email or token['target_email'], 'DermaMatrix account security', 'Your account credentials were changed. If you did not make this change, contact your application operator.')
                except DeliveryUnavailable:
                    notification = {'state': 'failed'}
            return jsonify(message='Account action confirmed.' + (' Sign in again.' if purpose != 'verify_email' else ''), notification=notification)
        except pymysql.IntegrityError:
            connection.rollback()
            return jsonify(error='That email change cannot be completed. Request another address.'), 409
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @bp.get('/api/privacy')
    def privacy_status():
        with owned() as (connection, user):
            with connection.cursor() as cursor:
                cursor.execute('SELECT processing_paused FROM account_security WHERE user_id=%s', (user['id'],))
                state = cursor.fetchone() or {}
                cursor.execute('SELECT consent_version,purpose,accepted_at FROM consent_records WHERE user_id=%s ORDER BY id DESC LIMIT 100', (user['id'],))
                consents = cursor.fetchall()
                cursor.execute("SELECT record_id,data_json,created_at FROM consumer_records WHERE user_id=%s AND kind='rights_request' ORDER BY id DESC LIMIT 100", (user['id'],))
                requests = cursor.fetchall()
            return jsonify(processing_paused=bool(state.get('processing_paused')), consents=consents, requests=[dict(id=r['record_id'], **json.loads(r['data_json']), created_at=r['created_at']) for r in requests],
                           policy_status='Retention, erasure exceptions and support ownership require operator approval. Requests are recorded locally, not submitted to a monitored service.',
                           source_images_stored=False)

    @bp.put('/api/privacy/processing')
    def processing_control():
        payload = json_object()
        paused = payload.get('paused')
        if not isinstance(paused, bool):
            raise ValueError('Choose pause or resume.')
        with owned() as (connection, user):
            budget(connection, 'sensitive', str(user['id']), 10, 900)
            reauthenticate(connection, user['id'], payload.get('current_password'))
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO account_security(user_id,processing_paused,updated_at) VALUES(%s,%s,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE processing_paused=%s,updated_at=UTC_TIMESTAMP()', (user['id'], paused, paused))
                if paused:
                    cursor.execute("UPDATE reminder_jobs SET state='cancelled',updated_at=UTC_TIMESTAMP() WHERE user_id=%s AND state IN ('scheduled','retry','sending')", (user['id'],))
                record(connection, user['id'], 'privacy_event', '', {'new_processing_paused': paused})
            return jsonify(processing_paused=paused, message='New health processing ' + ('paused.' if paused else 'resumed; each action still requires its own consent.'), historical_records='Retained and available for access/export; this control does not erase records.')

    @bp.post('/api/privacy/requests')
    def rights_request():
        payload = json_object()
        kind = payload.get('kind')
        if kind not in {'correction', 'deletion', 'account_closure', 'support', 'content_correction'}:
            raise ValueError('Choose a supported request type.')
        note = payload.get('note', '')
        key = request.headers.get('Idempotency-Key', '')
        if not isinstance(note, str) or len(note) > 2000 or not re.fullmatch('[A-Za-z0-9_-]{16,80}', key):
            raise ValueError('Provide a note up to 2,000 characters and a valid request identifier.')
        with owned() as (connection, user):
            budget(connection, 'rights', str(user['id']), 20, 900)
            if kind in {'deletion', 'account_closure'}:
                reauthenticate(connection, user['id'], payload.get('current_password'))
            data = {'kind': kind, 'note': note, 'status': 'recorded_locally_pending_operator', 'monitored': False}
            item = record(connection, user['id'], 'rights_request', '', data, key)
            if json.loads(item['data_json']) != data:
                return jsonify(error='This request identifier was already used for different details.'), 409
            return jsonify(request_id=item['record_id'], **data), 201

    @bp.errorhandler(ValueError)
    def validation(error):
        return jsonify(error=str(error), code='INVALID_INPUT'), 400

    @bp.errorhandler(DeliveryUnavailable)
    def unavailable(error):
        return jsonify(error=str(error), code='DELIVERY_UNAVAILABLE'), 503

    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def http_error(error):
        if not enabled():
            return error
        response = jsonify(error=error.description, code='HTTP_' + str(error.code))
        response.status_code = error.code
        if error.code == 429:
            response.headers['Retry-After'] = '900'
        return response

    app.register_blueprint(bp)
