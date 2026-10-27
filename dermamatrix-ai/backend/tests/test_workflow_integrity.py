"""Retry and input contracts, isolated routes plus opt-in synthetic SQL."""
import os
import unittest
from unittest.mock import patch
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from isolated_application import load_isolated_application


class WorkflowInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_isolated_application('_workflow_input_tests')

    def test_login_non_objects_are_validation_errors_before_database(self):
        with patch.object(self.module, 'database', side_effect=AssertionError('unexpected database')):
            for value in (None, True, 1, 'text', [], ['item']):
                with self.subTest(value=value):
                    response = self.module.app.test_client().post('/api/auth/login', json=value)
                    self.assertEqual(response.status_code, 400)

    def test_key_never_bypasses_current_consent_or_reads_upload(self):
        with patch.object(self.module, 'database', side_effect=AssertionError('unexpected database')):
            client = self.module.app.test_client()
            with client.session_transaction() as session:
                session['user_id'] = 8
            response = client.post('/api/sweat-assessments', json={'questionnaire_consent': False}, headers={'Idempotency-Key': uuid.uuid4().hex})
            self.assertEqual(response.status_code, 400)
            response = client.post('/api/assessments', data={'image_consent': 'false'}, headers={'Idempotency-Key': uuid.uuid4().hex})
            self.assertEqual(response.status_code, 400)

    def test_retry_key_requires_bounded_valid_string(self):
        client = self.module.app.test_client()
        for key in ('', 'short', 'x' * 81, '<script>' * 3):
            response = client.post('/api/sweat-assessments', json={'questionnaire_consent': True}, headers={'Idempotency-Key': key})
            self.assertEqual(response.status_code, 400)

    def test_malformed_questionnaire_flags_and_values_reject_before_processing(self):
        with patch.object(self.module, 'sweat_questionnaire_result', side_effect=AssertionError('unexpected scoring')):
            for field, value in [('urgent_concern', 'false'), ('medication_change', 1), ('daily_impact', [])]:
                with self.subTest(field=field):
                    response = self.module.app.test_client().post('/api/sweat-assessments', json={'questionnaire_consent': True, field: value})
                    self.assertEqual(response.status_code, 400)


@unittest.skipUnless(os.getenv('DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS') == '1', 'Requires disposable synthetic SQL')
class WorkflowMySQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app
        cls.module = app
        app.app.config.update(TESTING=True)

    def setUp(self):
        self.ids = []
        self.client = self.register()

    def register(self):
        client = self.module.app.test_client()
        response = client.post('/api/auth/register', json={'full_name': 'Workflow Synthetic', 'email_address': f'workflow-{uuid.uuid4().hex}@example.test', 'password': 'Synthetic-password-25', 'confirm_password': 'Synthetic-password-25', 'account_consent': True})
        self.assertEqual(response.status_code, 201, response.get_json())
        self.ids.append(response.get_json()['user']['id'])
        return client

    def tearDown(self):
        connection = self.module.database()
        try:
            with connection.cursor() as cursor:
                for uid in self.ids:
                    for table in ('reports','clinical_review_requests','progress_checkins','care_routines','analysis_records','assessments','medical_histories','consent_records','user_preferences','auth_accounts','users'):
                        cursor.execute(f'DELETE FROM {table} WHERE {"id" if table == "users" else "user_id"}=%s', (uid,))
            connection.commit()
        finally:
            connection.close()

    def post(self, client, key, **payload):
        return client.post('/api/sweat-assessments', json={'questionnaire_consent': True, 'pattern': 'usual', **payload}, headers={'Idempotency-Key': key})

    def test_committed_retry_same_evidence_one_record_and_owner_isolation(self):
        key = uuid.uuid4().hex
        first = self.post(self.client, key)
        self.assertEqual(first.status_code, 200, first.get_json())
        replay = self.post(self.client, key)
        self.assertEqual(replay.status_code, 200, replay.get_json())
        a, b = first.get_json(), replay.get_json()
        self.assertTrue(b['replayed'])
        for field in ('assessment_id','assessment_result','risk','severity','pirs','assessment_risk','created_at'):
            self.assertEqual(a[field], b[field], field)
        self.assertNotIn('submission_fingerprint', b)
        self.assertEqual(len(self.client.get('/api/analysis-history').get_json()['analyses']), 1)
        self.assertEqual(self.post(self.client, key, frequency=2).status_code, 409)
        self.assertEqual(self.post(self.client, key, questionnaire_consent=False).status_code, 400)
        other = self.register()
        self.assertEqual(other.get(f"/api/assessments/{a['assessment_id']}").status_code, 404)
        self.assertNotEqual(self.post(other, key).get_json()['assessment_id'], a['assessment_id'])
        self.client.post('/api/auth/logout')
        self.assertEqual(self.client.get(f"/api/reports/{a['assessment_id']}/download").status_code, 401)

    def test_concurrent_same_submission_is_saved_once(self):
        key = uuid.uuid4().hex
        cookie = self.client.get_cookie('session').value
        barrier = Barrier(2)
        def submit(_):
            client = self.module.app.test_client(); client.set_cookie('session', cookie)
            barrier.wait()
            return self.post(client, key)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
        self.assertEqual([r.status_code for r in results], [200,200])
        self.assertEqual(results[0].get_json()['assessment_id'], results[1].get_json()['assessment_id'])
        self.assertEqual(len(self.client.get('/api/analysis-history').get_json()['analyses']), 1)

    def test_rollback_can_retry_without_orphan_result(self):
        key = uuid.uuid4().hex
        with patch.object(self.module, 'stored_analysis_summary', side_effect=RuntimeError('synthetic failure')):
            with self.assertRaises(RuntimeError):
                self.post(self.client, key)
        self.assertEqual(self.client.get('/api/analysis-history').get_json()['analyses'], [])
        self.assertEqual(self.post(self.client, key).status_code, 200)
        self.assertEqual(len(self.client.get('/api/analysis-history').get_json()['analyses']), 1)

    def test_preferences_change_only_submitted_fields_and_reject_policy_fields(self):
        self.client.put('/api/preferences', json={'reduced_motion': True})
        self.client.put('/api/preferences', json={'theme': 'dark'})
        preferences = self.client.get('/api/preferences').get_json()['preferences']
        self.assertTrue(preferences['reduced_motion']); self.assertEqual(preferences['theme'], 'dark')
        self.assertEqual(self.client.put('/api/preferences', json={'health_data_consent': False}).status_code, 400)
        self.assertEqual(self.client.put('/api/preferences', json=['theme']).status_code, 400)

    def test_malformed_historical_record_does_not_break_other_history_or_fake_pdf(self):
        key = uuid.uuid4().hex
        result = self.post(self.client, key).get_json()
        assessment_id = result['assessment_id']
        connection = self.module.database()
        try:
            for malformed in ('not-json', '[]', 'null'):
                with connection.cursor() as cursor:
                    cursor.execute('UPDATE analysis_records SET result_json=%s WHERE assessment_id=%s AND user_id=%s', (malformed,assessment_id,self.ids[0]))
                connection.commit()
                history = self.client.get('/api/analysis-history')
                self.assertEqual(history.status_code, 200)
                self.assertTrue(history.get_json()['analyses'][0]['unavailable'])
                self.assertEqual(self.post(self.client, key).status_code, 409)
                self.assertEqual(self.client.get(f'/api/assessments/{assessment_id}').status_code, 409)
                self.assertEqual(self.client.get(f'/api/reports/{assessment_id}/download').status_code, 409)
                with connection.cursor() as cursor:
                    cursor.execute('SELECT result_json FROM analysis_records WHERE assessment_id=%s', (assessment_id,))
                    self.assertEqual(cursor.fetchone()['result_json'], malformed)
                connection.commit()
        finally:
            connection.close()

    def test_image_retry_replays_exact_evidence_and_rejects_changed_bytes(self):
        from io import BytesIO
        from PIL import Image, ImageDraw
        key = uuid.uuid4().hex
        image = Image.new('RGB', (320, 320), '#aa785b')
        draw = ImageDraw.Draw(image)
        for x in range(0,320,7):
            draw.line((x,0,320-x,320), fill='#382d24', width=2)
        buffer = BytesIO(); image.save(buffer, format='PNG'); content=buffer.getvalue()
        def post(data=content, consent='true', **extra):
            return self.client.post('/api/assessments', data={'image':(BytesIO(data),'synthetic.png'), 'area':'Hair', 'image_context':'scalp', 'image_consent':consent, **extra}, headers={'Idempotency-Key':key})
        first = post(); self.assertEqual(first.status_code,200,first.get_json())
        replay = post(); self.assertEqual(replay.status_code,200,replay.get_json())
        self.assertTrue(replay.get_json()['replayed'])
        self.assertEqual(first.get_json()['assessment_result'],replay.get_json()['assessment_result'])
        self.assertEqual(len(self.client.get('/api/analysis-history').get_json()['analyses']),1)
        self.assertEqual(post(consent='false').status_code,400)
        self.assertEqual(post(consent_notice_version='old-notice').status_code,400)
        self.assertEqual(post(data=content+b'different').status_code,409)
        self.assertNotIn('data:image', self.client.get('/api/analysis-history').get_data(as_text=True))

    def test_busy_retry_is_explicit_and_never_runs_scoring(self):
        import hashlib
        key = uuid.uuid4().hex
        token = hashlib.sha256(f'{self.ids[0]}:questionnaire_assessment:{key}'.encode()).hexdigest()
        connection=self.module.database()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT GET_LOCK(%s,0) AS acquired',('dmx:'+token[:60],))
                self.assertEqual(cursor.fetchone()['acquired'],1)
            with patch.object(self.module,'sweat_questionnaire_result',side_effect=AssertionError('duplicate processing')):
                response=self.post(self.client,key)
                self.assertEqual(response.status_code,409)
                self.assertEqual(response.get_json()['code'],'ASSESSMENT_IN_PROGRESS')
        finally:
            connection.close()
