import json
import os
import unittest
from datetime import date, datetime, timedelta, timezone
import uuid
from unittest.mock import patch

from consumer_engagement import schedule_payload, local_occurrences
from reminder_worker import plan, run_due
import test_consumer_accounts as account_tests


class ScheduleRules(unittest.TestCase):
    def config(self, **overrides):
        return schedule_payload(dict(steps=['User-selected step'], days=list(range(7)), times=['02:30'], timezone='America/New_York', quiet_start='00:00', quiet_end='00:00', **overrides))

    def test_dst_gap_skipped_fold_once(self):
        config = self.config()
        self.assertEqual(local_occurrences(config, date(2026, 3, 8)), [])
        config['times'] = ['01:30']
        self.assertEqual(len(local_occurrences(config, date(2026, 11, 1))), 1)
        self.assertEqual(local_occurrences(config, date(2026, 11, 1))[0].hour, 5)

    def test_quiet_hours_and_pause(self):
        config = self.config(); config.update(times=['07:00','09:00','22:00'], quiet_start='21:00', quiet_end='08:00')
        self.assertEqual(len(local_occurrences(config, date(2026, 10, 27))), 1)
        config['status'] = 'paused'
        self.assertEqual(local_occurrences(config, date(2026, 10, 27)), [])

    def test_invalid_contracts(self):
        base = dict(steps=['Step'], days=[0], times=['09:00'], timezone='UTC')
        for patch_value in [dict(days=[True]), dict(timezone='not/a/zone'), dict(steps=[]), dict(times=['25:00']),dict(reminders='true')]:
            with self.subTest(patch=patch_value), self.assertRaises(ValueError):
                schedule_payload({**base, **patch_value})


@unittest.skipUnless(os.getenv('DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS') == '1', 'Requires disposable synthetic SQL')
class ConsumerEngagement(unittest.TestCase):
    setUpClass = classmethod(account_tests.ConsumerAccounts.setUpClass.__func__)
    setUp = account_tests.ConsumerAccounts.setUp
    tearDown = account_tests.ConsumerAccounts.tearDown
    call = account_tests.ConsumerAccounts.call
    last_token = account_tests.ConsumerAccounts.last_token

    def routine(self):
        response = self.call('/api/routines', dict(condition_label='Self-selected routine focus', routine_name='Synthetic daily routine', start_date=date.today().isoformat(), notes='Synthetic'))
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()['routine_id']

    def schedule(self, routine, **patch_value):
        config = dict(steps=['Gentle daily step','Note any discomfort'], days=list(range(7)), times=['09:00'], timezone='UTC', version=0, area='Skin', episode='Synthetic episode', body_area='Hand', reminders=False, quiet_start='00:00', quiet_end='00:00')
        config.update(patch_value)
        return self.call('/api/routine-schedules/' + routine, config, method='PUT')

    def test_schedule_edit_keeps_event_snapshot_and_conflict(self):
        routine = self.routine()
        response = self.schedule(routine)
        self.assertEqual(response.status_code, 200, response.get_json())
        key = {'Idempotency-Key': uuid.uuid4().hex}
        data = dict(action='completed',step=0,time='09:00',date=date.today().isoformat())
        path = f'/api/routine-schedules/{routine}/events'
        first = self.call(path, data, headers=key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.call(path, data, headers=key).get_json(), first.get_json())
        self.assertEqual(self.schedule(routine).status_code, 409)
        self.assertEqual(self.schedule(routine, version=1,steps=['Edited step']).status_code, 200)
        history = self.client.get('/api/routine-schedules/' + routine).get_json()
        self.assertEqual(history['events'][0]['step_text'], 'Gentle daily step')
        self.assertEqual(history['events'][0]['schedule_version'], 1)
        self.assertEqual(history['schedule']['version'], 2)

    def test_today_completion_skip_pause_resume(self):
        routine = self.routine(); self.schedule(routine)
        tasks = self.client.get('/api/today').get_json()['tasks']
        self.assertEqual(len(tasks), 2)
        for index, action in enumerate(['completed', 'skipped']):
            self.assertEqual(self.call(f'/api/routine-schedules/{routine}/events', dict(action=action,step=index,time='09:00',date=date.today().isoformat()), headers={'Idempotency-Key':uuid.uuid4().hex}).status_code,201)
        tasks = self.client.get('/api/today').get_json()['tasks']
        self.assertEqual([x['state'] for x in tasks], ['completed','skipped'])
        self.schedule(routine, version=1,status='paused')
        self.assertEqual(self.client.get('/api/today').get_json()['tasks'], [])
        self.schedule(routine, version=2,status='active')
        self.assertEqual(len(self.client.get('/api/today').get_json()['tasks']), 2)

    def test_history_past_fifty_stable_and_filtered(self):
        connection = self.module.database()
        try:
            with connection.cursor() as cursor:
                for index in range(55):
                    cursor.execute('INSERT INTO analysis_records(assessment_id,user_id,area,result_json,created_at) VALUES(%s,%s,%s,%s,UTC_TIMESTAMP())', (f'consumer-{self.identifier[:12]}-{index}', self.user_id, 'Skin' if index%2 else 'Hair', json.dumps({'id':str(index),'text':'Synthetic history'})))
            connection.commit()
        finally:
            connection.close()
        path = '/api/journey/assessments'; ids=[]; cursor=None
        while True:
            data = self.client.get(path, query_string={'cursor':cursor} if cursor else {}).get_json()
            ids += [r['assessment_id'] for r in data['analyses']]
            cursor=data['next_cursor']
            if not cursor: break
        self.assertEqual(len(ids),55); self.assertEqual(len(set(ids)),55)
        first=self.client.get(path).get_json()
        self.assertEqual(self.client.get(path,query_string={'cursor':first['next_cursor'],'area':'Skin'}).status_code,400)
        filtered=self.client.get(path,query_string={'area':'Skin','q':'Synthetic'}).get_json()
        self.assertTrue(all(r['area']=='Skin' for r in filtered['analyses']))
        self.assertEqual(self.client.get(path,query_string={'q':"%' OR 1=1--"}).get_json()['analyses'],[])
        self.assertEqual(self.client.get(path,query_string={'cursor':'tampered'}).status_code,400)

    def test_schedule_owner_and_guest_rejected(self):
        routine=self.routine(); self.schedule(routine)
        self.assertEqual(self.client.get('/api/routine-schedules/missing').status_code,404)
        guest=self.app.test_client()
        self.assertEqual(guest.get('/api/routine-schedules/'+routine).status_code,401)
        self.assertEqual(guest.get('/api/journey/assessments').status_code,401)

    def test_reminder_sink_dedup_and_opt_out(self):
        routine=self.routine()
        at=datetime.now(timezone.utc).replace(tzinfo=None,second=0,microsecond=0)
        self.schedule(routine,times=[at.strftime('%H:%M')],reminders=True)
        self.call('/api/security/verify-email',{})
        self.call('/api/security/action',dict(purpose='verify_email',token=self.last_token('verify_email')))
        connection=self.module.database()
        try:
            self.assertGreaterEqual(plan(connection,at),1)
            self.assertEqual(plan(connection,at),0)
            outcomes=run_due(connection,at=at)
            self.assertEqual(len(outcomes),1)
            self.assertEqual(outcomes[0]['state'],'sink_written')
            self.assertEqual(run_due(connection,at=at),[])
            self.schedule(routine,version=1,times=[at.strftime('%H:%M')],reminders=True)
            plan(connection,at)
            self.call('/api/preferences',dict(notifications_enabled=False),method='PUT')
            self.assertEqual(run_due(connection,at=at)[0]['state'],'cancelled')
        finally:
            connection.close()

    def test_reminder_failure_retries_bounded_and_honest(self):
        from delivery import DeliveryUnavailable
        routine=self.routine(); at=datetime.now(timezone.utc).replace(tzinfo=None,second=0,microsecond=0)
        self.schedule(routine,times=[at.strftime('%H:%M')],reminders=True)
        self.call('/api/security/verify-email',{})
        self.call('/api/security/action',dict(purpose='verify_email',token=self.last_token('verify_email')))
        connection=self.module.database()
        try:
            plan(connection,at)
            with patch('reminder_worker.send_message',side_effect=DeliveryUnavailable('Synthetic failure')):
                self.assertEqual(run_due(connection,at=at)[0]['state'],'retry')
                self.assertEqual(run_due(connection,at=at+timedelta(minutes=5))[0]['state'],'retry')
                self.assertEqual(run_due(connection,at=at+timedelta(minutes=10))[0]['state'],'failed')
        finally:
            connection.close()

    def test_export_includes_consumer_records_excludes_authentication_secrets(self):
        routine=self.routine(); self.schedule(routine)
        self.call('/api/security/verify-email',{})
        data=self.client.get('/api/account-data/download').get_json()
        self.assertIn('consumer_records',data['records'])
        self.assertIn('account_tokens',data['records'])
        self.assertNotIn('token_hash',json.dumps(data))
        self.assertNotIn('session_id',json.dumps(data['records']['account_sessions']))
        self.assertEqual(len(data['records']['consumer_records']),2)

    def test_paused_account_cannot_write_schedule_or_completion(self):
        routine=self.routine();self.schedule(routine)
        self.call('/api/privacy/processing',dict(paused=True,current_password=self.password),method='PUT')
        self.assertEqual(self.schedule(routine,version=1).status_code,403)
        result=self.call(f'/api/routine-schedules/{routine}/events',dict(action='completed',step=0,time='09:00',date=date.today().isoformat()),headers={'Idempotency-Key':uuid.uuid4().hex})
        self.assertEqual(result.status_code,403)
        self.assertEqual(self.client.get('/api/routine-schedules/'+routine).status_code,200)

    def test_capacity_rejects_without_running_image_pipeline(self):
        connection=self.module.database()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT GET_LOCK('dmx-inference-capacity:0',0)")
            result=self.call('/api/assessments',{})
            self.assertEqual(result.status_code,503)
            self.assertEqual(result.get_json()['code'],'ASSESSMENT_CAPACITY_BUSY')
        finally:
            connection.close()

    def test_episode_labels_filter_without_rewriting_original(self):
        connection=self.module.database();assessment='context-'+self.identifier[:20];original='{"original":"unchanged"}'
        try:
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO analysis_records(assessment_id,user_id,area,result_json,created_at) VALUES(%s,%s,%s,%s,UTC_TIMESTAMP())',(assessment,self.user_id,'Skin',original))
            connection.commit()
            result=self.call('/api/journey/assessments/'+assessment+'/context',dict(episode='Hand episode',body_area='Left hand'),method='PUT')
            self.assertEqual(result.status_code,200,result.get_json())
            rows=self.client.get('/api/journey/assessments',query_string={'episode':'Hand episode','body_area':'Left hand'}).get_json()['analyses']
            self.assertEqual(len(rows),1);self.assertEqual(rows[0]['assessment_id'],assessment)
            self.assertEqual(rows[0]['context']['episode'],'Hand episode')
            with connection.cursor() as cursor:
                cursor.execute('SELECT result_json FROM analysis_records WHERE assessment_id=%s',(assessment,))
                self.assertEqual(cursor.fetchone()['result_json'],original)
            self.assertEqual(self.call('/api/journey/assessments/missing/context',dict(episode='x'),method='PUT').status_code,404)
        finally:connection.close()

    def test_other_account_cannot_open_schedule_label_result_or_reuse_cursor(self):
        routine=self.routine();self.schedule(routine)
        connection=self.module.database()
        with connection.cursor() as cursor:
            for index in range(22):
                cursor.execute('INSERT INTO analysis_records(assessment_id,user_id,area,result_json,created_at) VALUES(%s,%s,%s,%s,UTC_TIMESTAMP())',(f'owner-{self.identifier[:16]}-{index}',self.user_id,'Hair','{}'))
        connection.commit();connection.close()
        first=self.client.get('/api/journey/assessments').get_json();self.assertTrue(first['next_cursor'])
        other=self.app.test_client();uid=None
        try:
            response=self.call('/api/auth/register',dict(full_name='Other synthetic owner',email_address='other-'+self.email,password=self.password,confirm_password=self.password,account_consent=True),client=other)
            self.assertEqual(response.status_code,201);uid=response.get_json()['user']['id']
            self.assertEqual(other.get('/api/routine-schedules/'+routine).status_code,404)
            self.assertEqual(other.get('/api/journey/assessments',query_string={'cursor':first['next_cursor']}).status_code,400)
            target=first['analyses'][0]['assessment_id']
            self.assertEqual(self.call('/api/journey/assessments/'+target+'/context',dict(episode='Foreign label'),method='PUT',client=other).status_code,404)
            self.assertEqual(other.get('/api/assessments/'+target).status_code,404)
            self.assertEqual(other.get('/api/journey/assessments').get_json()['analyses'],[])
        finally:
            if uid:
                connection=self.module.database()
                with connection.cursor() as cursor:
                    for table in ['account_sessions','auth_accounts','medical_histories','consent_records','user_preferences','users']:
                        cursor.execute(f'DELETE FROM {table} WHERE {"id" if table=="users" else "user_id"}=%s',(uid,))
                connection.commit();connection.close()

    def test_archiving_retains_routine_and_completion_history(self):
        routine=self.routine();self.schedule(routine)
        self.call(f'/api/routine-schedules/{routine}/events',dict(action='completed',step=0,time='09:00',date=date.today().isoformat()),headers={'Idempotency-Key':uuid.uuid4().hex})
        result=self.call('/api/routines/'+routine,{},method='DELETE')
        self.assertEqual(result.status_code,200)
        record=self.client.get('/api/routine-schedules/'+routine).get_json()
        self.assertEqual(record['schedule']['status'],'archived');self.assertEqual(len(record['events']),1)
        routines=self.client.get('/api/routines').get_json()['routines']
        self.assertEqual(routines[0]['status'],'archived')
        self.assertEqual(self.client.get('/api/today').get_json()['tasks'],[])

    def test_different_request_keys_still_record_one_occurrence(self):
        routine=self.routine();self.schedule(routine)
        payload=dict(action='completed',step=0,time='09:00',date=date.today().isoformat(),schedule_version=1)
        path=f'/api/routine-schedules/{routine}/events'
        first=self.call(path,payload,headers={'Idempotency-Key':uuid.uuid4().hex})
        again=self.call(path,payload,headers={'Idempotency-Key':uuid.uuid4().hex})
        self.assertEqual(first.status_code,201);self.assertEqual(first.get_json(),again.get_json())
        conflict=self.call(path,{**payload,'action':'skipped'},headers={'Idempotency-Key':uuid.uuid4().hex})
        self.assertEqual(conflict.status_code,409)
        self.assertEqual(conflict.get_json()['code'],'EVENT_ALREADY_RECORDED')
        self.assertEqual(len(self.client.get('/api/routine-schedules/'+routine).get_json()['events']),1)

    def test_stale_today_step_does_not_mark_a_changed_schedule(self):
        routine=self.routine();self.schedule(routine)
        task=self.client.get('/api/today').get_json()['tasks'][0]
        self.assertEqual(task['schedule_version'],1)
        self.schedule(routine,version=1,steps=['Changed step'])
        response=self.call(f'/api/routine-schedules/{routine}/events',dict(action='completed',step=0,time='09:00',date=date.today().isoformat(),schedule_version=task['schedule_version']),headers={'Idempotency-Key':uuid.uuid4().hex})
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.get_json()['code'],'SCHEDULE_CHANGED')
        self.assertEqual(self.client.get('/api/routine-schedules/'+routine).get_json()['events'],[])

    def test_two_tabs_cannot_duplicate_one_scheduled_occurrence(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        routine=self.routine();self.schedule(routine)
        cookie=self.client.get_cookie('session').value;barrier=Barrier(2)
        def submit(_):
            client=self.app.test_client();client.set_cookie('session',cookie)
            csrf=client.get('/api/security/csrf').get_json()['csrf_token']
            barrier.wait()
            return client.post(f'/api/routine-schedules/{routine}/events',json=dict(action='completed',step=0,time='09:00',date=date.today().isoformat(),schedule_version=1),headers={'X-CSRF-Token':csrf,'Idempotency-Key':uuid.uuid4().hex})
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(submit,range(2)))
        self.assertEqual([r.status_code for r in responses],[201,201])
        self.assertEqual(responses[0].get_json()['event_id'],responses[1].get_json()['event_id'])
        self.assertEqual(len(self.client.get('/api/routine-schedules/'+routine).get_json()['events']),1)
