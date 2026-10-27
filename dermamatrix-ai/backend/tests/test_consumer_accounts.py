"""Real SQL account/privacy regression. Only disposable synthetic databases."""
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from isolated_application import load_isolated_application
from consumer_schema import migrate


@unittest.skipUnless(os.getenv('DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS') == '1', 'Requires disposable synthetic SQL')
class ConsumerAccounts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database_name = os.getenv('MYSQL_DATABASE') or os.getenv('MYSQLDATABASE', '')
        if 'synthetic' not in database_name.lower():
            raise RuntimeError('Consumer tests require an explicitly synthetic database.')
        cls.module = load_isolated_application('_consumer_accounts_test')
        cls.app = cls.module.app
        cls.app.config.update(CONSUMER_ENABLED=True)
        connection = cls.module.database()
        try:
            migrate(connection)
        finally:
            connection.close()

    def setUp(self):
        self.mailbox = tempfile.TemporaryDirectory(prefix='consumer-test-mail-')
        self.environment = patch.dict(os.environ, {'DERMAMATRIX_ENV': 'test', 'DERMAMATRIX_MAIL_TRANSPORT': 'sink', 'DERMAMATRIX_MAIL_SINK': self.mailbox.name, 'DERMAMATRIX_APP_ORIGIN': 'http://localhost'})
        self.environment.start()
        self.client = self.app.test_client()
        self.identifier = uuid.uuid4().hex
        self.email = self.identifier + '@synthetic.invalid'
        self.password = 'Synthetic-Password-27'
        self.address = self.identifier
        self.user_id = None
        r = self.call('/api/auth/register', {'full_name': 'Synthetic Consumer', 'email_address': self.email, 'password': self.password, 'confirm_password': self.password, 'account_consent': True})
        self.assertEqual(r.status_code, 201, r.get_json())
        self.user_id = r.get_json()['user']['id']

    def tearDown(self):
        if self.user_id:
            connection = self.module.database()
            try:
                with connection.cursor() as cursor:
                    for table in ['account_mail_jobs', 'reminder_jobs', 'consumer_records', 'account_tokens', 'account_sessions', 'account_security', 'reports', 'progress_checkins', 'care_routines', 'clinical_review_requests', 'analysis_records', 'assessments', 'user_preferences', 'consent_records', 'medical_histories', 'auth_accounts']:
                        cursor.execute(f'DELETE FROM {table} WHERE user_id=%s', (self.user_id,))
                    cursor.execute('DELETE FROM users WHERE id=%s', (self.user_id,))
                connection.commit()
            finally:
                connection.close()
        self.environment.stop(); self.mailbox.cleanup()

    def call(self, path, payload=None, method='POST', client=None, headers=None):
        client = client or self.client
        csrf = client.get('/api/security/csrf').get_json()['csrf_token']
        return client.open(path, method=method, json=payload, headers={'X-CSRF-Token': csrf, **(headers or {})}, environ_overrides={'REMOTE_ADDR': self.address})

    def last_token(self, purpose):
        if purpose == 'reset_password':
            from account_mail_worker import process_account_messages
            connection = self.module.database()
            try:
                with self.app.app_context():
                    process_account_messages(connection)
            finally:
                connection.close()
        messages = [json.loads(p.read_text()) for p in Path(self.mailbox.name).glob('*.json')]
        for item in reversed(messages):
            for line in item['body'].splitlines():
                if line.startswith('http'):
                    params = parse_qs(urlsplit(line).fragment)
                    if params['account_action'][0] == purpose:
                        return params['token'][0]
        self.fail('No expected synthetic message found')

    def test_csrf_and_malformed_json(self):
        self.assertEqual(self.client.post('/api/security/verify-email', json={}).status_code, 403)
        self.assertEqual(self.call('/api/security/password', []).status_code, 400)
        for value in [True, 1, ['unexpected']]:
            self.assertEqual(self.call('/api/profile', value, method='PATCH').status_code, 400)

    def test_verification_single_use_and_no_api_token(self):
        response = self.call('/api/security/verify-email', {})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['delivery']['state'], 'sink_written')
        token = self.last_token('verify_email')
        self.assertNotIn(token, response.get_data(as_text=True))
        self.assertEqual(self.call('/api/security/action', {'purpose': 'verify_email', 'token': token}).status_code, 200)
        self.assertTrue(self.client.get('/api/security/account').get_json()['email_verified'])
        self.assertEqual(self.call('/api/security/action', {'purpose': 'verify_email', 'token': token}).status_code, 400)

    def test_expired_and_tampered_token(self):
        self.call('/api/security/verify-email', {})
        token = self.last_token('verify_email')
        connection = self.module.database()
        try:
            with connection.cursor() as cursor:
                cursor.execute('UPDATE account_tokens SET expires_at=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 MINUTE) WHERE user_id=%s', (self.user_id,))
            connection.commit()
        finally:
            connection.close()
        for invalid in [token, 'a' * 43, '<script>']:
            self.assertEqual(self.call('/api/security/action', {'purpose': 'verify_email', 'token': invalid}).status_code, 400)

    def test_reset_generic_and_revokes_other_browser(self):
        other = self.app.test_client()
        self.assertEqual(self.call('/api/auth/login', {'email_address': self.email, 'password': self.password}, client=other).status_code, 200)
        known = self.call('/api/security/reset-password', {'email_address': self.email})
        unknown = self.call('/api/security/reset-password', {'email_address': 'missing-' + self.email})
        self.assertEqual(known.get_json(), unknown.get_json())
        token = self.last_token('reset_password')
        payload = {'purpose': 'reset_password', 'token': token, 'new_password': 'Changed-Synthetic-27'}
        self.assertEqual(self.call('/api/security/action', payload).status_code, 200)
        self.assertEqual(other.get('/api/profile').status_code, 401)
        self.assertEqual(self.call('/api/security/action', payload).status_code, 400)
        self.assertEqual(self.call('/api/auth/login', {'email_address': self.email, 'password': self.password}).status_code, 401)
        self.assertEqual(self.call('/api/auth/login', {'email_address': self.email, 'password': payload['new_password']}).status_code, 200)

    def test_change_password_reauth_and_session_rotation(self):
        other = self.app.test_client()
        self.call('/api/auth/login', {'email_address': self.email, 'password': self.password}, client=other)
        self.assertEqual(self.call('/api/security/password', {'current_password': 'incorrect', 'new_password': 'Changed-Synthetic-27'}).status_code, 401)
        self.assertEqual(self.call('/api/security/password', {'current_password': self.password, 'new_password': 'Changed-Synthetic-27'}).status_code, 200)
        self.assertEqual(other.get('/api/profile').status_code, 401)
        self.assertEqual(self.client.get('/api/profile').status_code, 200)

    def test_email_changes_only_after_confirmation(self):
        target = 'changed-' + self.email
        result = self.call('/api/security/email', {'current_password': self.password, 'new_email': target})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.get('/api/profile').get_json()['email_address'], self.email)
        token = self.last_token('change_email')
        self.assertEqual(self.call('/api/security/action', {'purpose': 'change_email', 'token': token}).status_code, 200)
        self.assertEqual(self.call('/api/auth/login', {'email_address': target, 'password': self.password}).status_code, 200)
        self.assertEqual(self.client.get('/api/profile').get_json()['email_address'], target)

    def test_revoke_specific_session_and_owner_isolation(self):
        other = self.app.test_client()
        self.call('/api/auth/login', {'email_address': self.email, 'password': self.password}, client=other)
        sessions = self.client.get('/api/security/account').get_json()['sessions']
        target = next(s['session_id'] for s in sessions if not s['current'])
        self.assertEqual(self.call('/api/security/sessions/revoke', {'current_password': self.password, 'session_id': target}).status_code, 200)
        self.assertEqual(other.get('/api/profile').status_code, 401)
        self.assertEqual(self.client.get('/api/profile').status_code, 200)

    def test_logout_revokes_replayed_signed_cookie(self):
        cookie = self.client.get_cookie('session').value
        self.assertEqual(self.call('/api/auth/logout', {}).status_code, 200)
        other = self.app.test_client(); other.set_cookie('session', cookie)
        self.assertEqual(other.get('/api/profile').status_code, 401)

    def test_pause_blocks_health_write_and_old_request_consent(self):
        self.assertEqual(self.call('/api/privacy/processing', {'paused': True, 'current_password': self.password}, method='PUT').status_code, 200)
        r = self.call('/api/sweat-assessments', {'consent': True})
        self.assertEqual(r.status_code, 403); self.assertEqual(r.get_json()['code'], 'PROCESSING_PAUSED')
        self.assertEqual(self.client.get('/api/account-data/download').status_code, 200)
        self.assertEqual(self.call('/api/privacy/processing', {'paused': False, 'current_password': 'incorrect'}, method='PUT').status_code, 401)
        self.assertEqual(self.call('/api/privacy/processing', {'paused': False, 'current_password': self.password}, method='PUT').status_code, 200)
        self.assertFalse(self.client.get('/api/privacy').get_json()['processing_paused'])

    def test_rights_requests_idempotent_conflict_and_no_erasure(self):
        headers = {'Idempotency-Key': uuid.uuid4().hex}
        payload = {'kind': 'account_closure', 'note': 'Synthetic closure request', 'current_password': self.password}
        first = self.call('/api/privacy/requests', payload, headers=headers)
        again = self.call('/api/privacy/requests', payload, headers=headers)
        self.assertEqual(first.status_code, 201); self.assertEqual(first.get_json(), again.get_json())
        self.assertFalse(first.get_json()['monitored'])
        payload['note'] = 'Changed details'
        self.assertEqual(self.call('/api/privacy/requests', payload, headers=headers).status_code, 409)
        self.assertEqual(self.client.get('/api/profile').status_code, 200)
        self.assertEqual(len(self.client.get('/api/privacy').get_json()['requests']), 1)

    def test_disabled_provider_truthful(self):
        with patch.dict(os.environ, {'DERMAMATRIX_MAIL_TRANSPORT': 'disabled'}):
            r = self.call('/api/security/verify-email', {})
            self.assertEqual(r.status_code, 503)
            self.assertEqual(list(Path(self.mailbox.name).glob('*.json')), [])

    def test_resend_invalidates_previous_link(self):
        self.call('/api/security/verify-email', {})
        first = self.last_token('verify_email')
        self.call('/api/security/verify-email', {})
        self.assertEqual(self.call('/api/security/action', {'purpose': 'verify_email', 'token': first}).status_code, 400)

    def test_resend_is_rate_limited(self):
        for _ in range(3):
            self.assertEqual(self.call('/api/security/verify-email', {}).status_code, 200)
        self.assertEqual(self.call('/api/security/verify-email', {}).status_code, 429)

    def test_guest_cannot_manage_privacy_or_sessions(self):
        guest = self.app.test_client()
        self.assertEqual(guest.get('/api/privacy').status_code, 401)
        self.assertEqual(guest.get('/api/security/account').status_code, 401)

    def test_legacy_cookie_requires_new_login(self):
        with self.client.session_transaction() as cookie:
            cookie.pop('security_session', None)
        self.assertEqual(self.client.get('/api/profile').status_code, 401)
