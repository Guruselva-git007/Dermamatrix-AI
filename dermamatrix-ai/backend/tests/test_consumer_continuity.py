"""Cross-feature tests against isolated synthetic SQL, never real accounts."""
import io
import json
import os
import unittest
import uuid
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Barrier

import test_consumer_accounts as accounts
import test_consumer_engagement as engagement_tests
from consumer_continuity import reminder_preview
from consumer_engagement import schedule_payload


class PreviewRules(unittest.TestCase):
    def test_public_guide_search_works_without_opening_private_database(self):
        from isolated_application import load_isolated_application
        module=load_isolated_application('_continuity_public_search')
        module.app.config.update(CONSUMER_ENABLED=True)
        with patch.object(module,'database',side_effect=AssertionError('Guest search must not open private storage')):
            response=module.app.test_client().get('/api/search?q=acne')
        self.assertEqual(response.status_code,200)
        data=response.get_json();self.assertFalse(data['private_results'])
        self.assertTrue(data['results']);self.assertTrue(all(r['category']=='guide' for r in data['results']))

    def test_quiet_pause_dst_and_no_delivery_claim(self):
        config = schedule_payload(dict(steps=['Synthetic step'], days=list(range(7)), times=['02:30','09:00','22:00'], timezone='America/New_York', quiet_start='21:00', quiet_end='08:00'))
        preview = reminder_preview(config, datetime(2026,3,8,5))
        self.assertEqual(preview['suppressed_times'], ['02:30','22:00'])
        self.assertEqual(preview['next_occurrence_utc'], '2026-03-08T13:00:00Z')
        config['status']='paused'
        self.assertIsNone(reminder_preview(config)['next_occurrence_utc'])

    def test_visit_pdf_keeps_questionnaire_and_recorded_values_explicit(self):
        from report_service import build_visit_brief_pdf
        from reportlab.platypus import Paragraph, SimpleDocTemplate
        text=[];original=SimpleDocTemplate.build
        def capture(document,story,*args,**kwargs):
            text.extend(item.getPlainText() for item in story if isinstance(item,Paragraph))
            return original(document,story,*args,**kwargs)
        brief=dict(episode=dict(label='Synthetic concern',area='Sweat',body_area='Hand'),start='2026-10-01',end='2026-10-28',timezone='Recorded dates',counts=dict(assessments=1,checkins=0,routine_actions=0,routines=0),photo_notice='Original photographs are unavailable; the app does not retain them.',questions='Synthetic question',checkins=[],events=[],assessments=[dict(assessment_id='synthetic-assessment',created_at='2026-10-28',area='Sweat',summary=dict(input_type='questionnaire',screening=dict(title='Self-reported pattern',summary='Synthetic reported summary'),manual_context=dict(sweat_questionnaire=dict(pattern='usual',daily_impact=False)),pirs=dict(score=23),severity=dict(level='MILD'),assessment_risk=dict(level='LOW')))])
        with patch.object(SimpleDocTemplate,'build',capture):
            self.assertTrue(build_visit_brief_pdf(brief).startswith(b'%PDF'))
        content=' '.join(text)
        for expected in ['Self-reported pattern','pattern: usual','daily impact: False','Questionnaire only; no image classifier','priority (PIRS): 23','not been recalculated','Synthetic question','not confirmed clinical diagnoses']:
            self.assertIn(expected,content)


@unittest.skipUnless(os.getenv('DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS') == '1', 'Disposable synthetic SQL only')
class ConsumerContinuity(unittest.TestCase):
    setUpClass = classmethod(accounts.ConsumerAccounts.setUpClass.__func__)
    setUp = accounts.ConsumerAccounts.setUp
    tearDown = accounts.ConsumerAccounts.tearDown
    call = accounts.ConsumerAccounts.call
    routine = engagement_tests.ConsumerEngagement.routine
    schedule = engagement_tests.ConsumerEngagement.schedule

    def keyed(self, path, data, method='POST', key=None):
        return self.call(path, data, method=method, headers={'Idempotency-Key':key or uuid.uuid4().hex})

    def episode(self, label='Synthetic hand concern', area='Skin'):
        response=self.keyed('/api/episodes',dict(label=label,area=area,body_area='Hand'))
        self.assertEqual(response.status_code,201,response.get_json())
        return response.get_json()['episode_id']

    def event(self, routine, action='completed'):
        response=self.keyed(f'/api/routine-schedules/{routine}/events',dict(action=action,step=0,time='09:00',date=datetime.now(timezone.utc).date().isoformat(),schedule_version=1))
        self.assertEqual(response.status_code,201,response.get_json())
        return response.get_json()['event_id']

    def test_corrections_today_history_export_and_recovery(self):
        r=self.routine();self.schedule(r);event=self.event(r)
        path='/api/corrections/event/'+event
        key=uuid.uuid4().hex;data=dict(revision=0,action='skipped',reason='Wrong button')
        self.assertEqual(self.keyed(path,data,key=key).status_code,200)
        self.assertTrue(self.keyed(path,data,key=key).get_json()['replayed'])
        self.assertEqual(self.keyed(path,data).status_code,409)
        tasks=self.client.get('/api/today').get_json()['tasks']
        self.assertEqual(tasks[0]['state'],'skipped')
        history=self.client.get('/api/routine-schedules/'+r).get_json()['events'][0]
        self.assertEqual(history['original']['action'],'completed')
        self.assertEqual(history['corrections'][0]['data']['actor_id'],self.user_id)
        self.assertEqual(self.keyed(path,dict(revision=1,action='pending')).status_code,200)
        self.assertEqual(self.client.get('/api/today').get_json()['tasks'][0]['state'],'pending')
        # Recover a previous effective state by another revision, never deletion.
        self.assertEqual(self.keyed(path,dict(revision=2,action='completed')).status_code,200)
        exported=self.client.get('/api/account-data/download').get_json()
        self.assertEqual(exported['effective_views']['routine_actions'][0]['action'],'completed')
        original=[r for r in exported['records']['consumer_records'] if r['kind']=='routine_event'][0]
        self.assertEqual(json.loads(original['data_json'])['action'],'completed')
        self.assertEqual(len([r for r in exported['records']['consumer_records'] if r['kind']=='event_correction']),3)

    def test_two_simultaneous_corrections_and_account_boundary(self):
        r=self.routine();self.schedule(r);event=self.event(r,'skipped')
        cookie=self.client.get_cookie('session').value;barrier=Barrier(2)
        def submit(action):
            client=self.app.test_client();client.set_cookie('session',cookie)
            csrf=client.get('/api/security/csrf').get_json()['csrf_token'];barrier.wait()
            return client.post('/api/corrections/event/'+event,json=dict(revision=0,action=action),headers={'X-CSRF-Token':csrf,'Idempotency-Key':uuid.uuid4().hex}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(submit,['completed','pending'])),[200,409])
        other=type(self)();other.setUp()
        try:
            self.assertEqual(other.call('/api/corrections/event/'+event,dict(revision=1,action='completed'),headers={'Idempotency-Key':uuid.uuid4().hex}).status_code,404)
            self.assertEqual(other.client.get('/api/search',query_string={'q':r}).get_json()['results'],[])
        finally:other.tearDown()

    def test_episode_assess_followup_brief_and_original_integrity(self):
        ep=self.episode(area='Sweat');r=self.routine();self.schedule(r,episode_id=ep,link_version=0)
        key=uuid.uuid4().hex;payload=dict(pattern='usual',questionnaire_consent=True,episode_id=ep)
        assessment=self.keyed('/api/sweat-assessments',payload,key=key)
        self.assertEqual(assessment.status_code,200,assessment.get_json())
        aid=assessment.get_json()['assessment_id']
        connection=self.module.database()
        with connection.cursor() as cursor:
            cursor.execute('SELECT result_json FROM analysis_records WHERE user_id=%s AND assessment_id=%s',(self.user_id,aid));original_result=cursor.fetchone()['result_json']
        connection.close()
        self.assertEqual(self.keyed('/api/sweat-assessments',payload,key=key).get_json()['assessment_id'],aid)
        event=self.event(r)
        cp=dict(routine_id=r,checkin_date=date.today().isoformat(),reported_trend='worsening',discomfort=7,change=5,note='Original synthetic note',episode_id=ep)
        key=uuid.uuid4().hex;created=self.keyed('/api/progress-checkins',cp,key=key)
        self.assertEqual(created.status_code,201,created.get_json());cid=created.get_json()['checkin_id']
        self.assertEqual(self.keyed('/api/progress-checkins',cp,key=key).get_json()['checkin_id'],cid)
        correction=dict(revision=0,checkin_date=date.today().isoformat(),reported_trend='improving',discomfort=1,change=2,note='Corrected synthetic note')
        self.assertEqual(self.keyed('/api/corrections/checkin/'+cid,correction).status_code,200)
        history=self.client.get('/api/journey/assessments',query_string={'episode_id':ep}).get_json()['analyses']
        self.assertEqual([v['assessment_id'] for v in history],[aid])
        checks=self.client.get('/api/progress-checkins').get_json()['checkins']
        self.assertEqual(checks[0]['reported_trend'],'improving');self.assertEqual(checks[0]['original']['reported_trend'],'worsening')
        params=dict(episode_id=ep,start=date.today().isoformat(),end=date.today().isoformat(),questions='What should I track?')
        brief=self.call('/api/visit-brief',params).get_json()['brief']
        self.assertEqual(brief['counts'],dict(assessments=1,checkins=1,routine_actions=1,routines=1))
        self.assertEqual(brief['checkins'][0]['reported_trend'],'improving')
        pdf=self.call('/api/visit-brief',{**params,'format':'pdf'})
        self.assertTrue(pdf.data.startswith(b'%PDF'));self.assertIn('does not retain',brief['photo_notice'])
        self.assertEqual(self.call('/api/visit-brief',{**params,'assessment_ids':['foreign']}).status_code,400)
        exported=self.client.get('/api/account-data/download').get_json()
        self.assertEqual(exported['records']['progress_checkins'][0]['reported_trend'],'worsening')
        self.assertEqual(exported['effective_views']['checkins'][0]['reported_trend'],'improving')
        self.assertEqual(self.client.get('/api/history/download').status_code,200)
        self.assertEqual(self.client.get('/api/reports/'+aid+'/download').status_code,200)
        separate=self.episode('Separate routine concern',area='Sweat')
        self.assertEqual(self.call('/api/episode-links/routine/'+r,dict(episode_id=separate,version=1),method='PUT').status_code,200)
        self.assertEqual(self.client.get('/api/today').get_json()['tasks'][0]['episode']['episode_id'],ep)
        self.assertEqual(self.call('/api/visit-brief',params).get_json()['brief']['counts']['routine_actions'],1)
        connection=self.module.database()
        with connection.cursor() as cursor:
            cursor.execute('SELECT result_json FROM analysis_records WHERE user_id=%s AND assessment_id=%s',(self.user_id,aid));self.assertEqual(cursor.fetchone()['result_json'],original_result)
        connection.close()
        self.assertEqual(self.keyed('/api/corrections/checkin/'+cid,dict(revision=1,voided=True)).status_code,200)
        self.assertEqual(self.client.get('/api/routines').get_json()['routines'][0]['checkin_count'],0)
        self.assertEqual(self.call('/api/visit-brief',params).get_json()['brief']['counts']['checkins'],0)

    def test_empty_legacy_many_records_search_and_links(self):
        self.assertEqual(self.client.get('/api/journey/assessments').get_json()['analyses'],[])
        ep=self.episode();other_ep=self.episode('Separate concern','Hair')
        key=uuid.uuid4().hex;payload=dict(label='Retry concern',area='Hair',body_area='Scalp')
        first=self.keyed('/api/episodes',payload,key=key).get_json()
        self.assertEqual(self.keyed('/api/episodes',payload,key=key).get_json(),first)
        connection=self.module.database()
        try:
            with connection.cursor() as cursor:
                for i in range(56):
                    cursor.execute('INSERT INTO analysis_records(assessment_id,user_id,area,result_json,created_at) VALUES(%s,%s,%s,%s,UTC_TIMESTAMP())',(f'legacy-{self.identifier[:10]}-{i}',self.user_id,'Skin' if i%2 else 'Hair',json.dumps({'synthetic_marker':i})))
            connection.commit()
        finally:connection.close()
        aid=f'legacy-{self.identifier[:10]}-1'
        self.assertEqual(self.call('/api/episode-links/assessment/'+aid,dict(episode_id=ep,version=0),method='PUT').status_code,200)
        self.assertEqual(self.call('/api/episode-links/assessment/'+aid,dict(episode_id=other_ep,version=0),method='PUT').status_code,409)
        ids=[];cursor=None
        while True:
            data=self.client.get('/api/search',query_string=dict(category='assessment',q='legacy-',**({'cursor':cursor} if cursor else {}))).get_json()
            ids += [r['id'] for r in data['results']];cursor=data['next_cursor']
            if not cursor:break
        self.assertEqual(len(ids),56);self.assertEqual(len(set(ids)),56)
        page=self.client.get('/api/search',query_string=dict(category='assessment',q='legacy-')).get_json()
        self.assertTrue(page['next_cursor'])
        self.assertEqual(self.client.get('/api/search',query_string=dict(category='routine',q='legacy-',cursor=page['next_cursor'])).status_code,400)
        self.assertEqual(self.app.test_client().get('/api/search',query_string=dict(category='assessment',q='legacy-',cursor=page['next_cursor'])).status_code,400)
        self.episode('Later concern')
        self.assertEqual(self.client.get('/api/search',query_string=dict(category='assessment',q='legacy-',cursor=page['next_cursor'])).status_code,409)
        self.assertEqual(len(self.client.get('/api/journey/assessments',query_string={'episode_id':ep}).get_json()['analyses']),1)
        export=self.client.get('/api/account-data/download').get_json()
        self.assertEqual(len(export['records']['analysis_records']),56)
        self.assertEqual(len([r for r in export['records']['consumer_records'] if r['kind']=='episode_link']),1)

    def test_bookmark_search_remove_feedback_and_guest_isolation(self):
        guide=self.client.get('/api/knowledge/conditions').get_json()['items'][0]
        path='/api/bookmarks/'+guide['id']
        self.assertEqual(self.call(path,dict(version=0),method='PUT').status_code,200)
        search=self.client.get('/api/search',query_string={'q':guide['name'],'category':'guide'}).get_json()
        self.assertTrue(search['results'][0]['bookmarked'])
        self.assertEqual(self.client.get('/api/knowledge/conditions/'+guide['id']).status_code,200)
        self.assertEqual(self.call(path+'?version=1',None,method='DELETE').status_code,200)
        self.assertFalse(self.client.get('/api/bookmarks').get_json()['bookmarks'][0]['saved'])
        self.assertEqual(self.call(path,dict(version=0),method='PUT').status_code,409)
        key=uuid.uuid4().hex;payload=dict(category='Accessibility',page='Journey',note='Synthetic feedback')
        first=self.keyed('/api/feedback',payload,key=key)
        self.assertEqual(first.status_code,201);self.assertEqual(first.get_json(),self.keyed('/api/feedback',payload,key=key).get_json())
        guest=self.app.test_client()
        self.assertFalse(guest.get('/api/search').get_json()['private_results'])
        self.assertTrue(all(r['category']=='guide' for r in guest.get('/api/search').get_json()['results']))
        self.assertEqual(guest.get('/api/bookmarks').status_code,401)
        key=uuid.uuid4().hex
        saved=self.keyed(path,dict(version=2),method='PUT',key=key)
        self.assertEqual(saved.status_code,200)
        self.assertEqual(self.keyed(path,dict(version=2),method='PUT',key=key).get_json(),saved.get_json())

    def test_corrected_date_is_current_beyond_old_history_window(self):
        routine=self.routine();connection=self.module.database()
        try:
            with connection.cursor() as cursor:
                for index in range(105):
                    cursor.execute('INSERT INTO progress_checkins(checkin_id,user_id,routine_id,checkin_date,reported_trend,discomfort_score,change_score,priority_score,note,image_stored,created_at) VALUES(%s,%s,%s,%s,%s,0,0,0,%s,FALSE,UTC_TIMESTAMP())',(f'old-{self.identifier[:10]}-{index}',self.user_id,routine,'2025-01-01' if index==0 else '2025-02-01','unchanged','Synthetic old check-in'))
            connection.commit()
        finally:connection.close()
        target=f'old-{self.identifier[:10]}-0'
        corrected=dict(revision=0,checkin_date=date.today().isoformat(),reported_trend='improving',discomfort=6,change=8,note='Date corrected')
        self.assertEqual(self.keyed('/api/corrections/checkin/'+target,corrected).status_code,200)
        checks=self.client.get('/api/progress-checkins').get_json()['checkins']
        self.assertEqual(checks[0]['checkin_id'],target)
        older=self.client.get('/api/checkins/'+f'old-{self.identifier[:10]}-104')
        self.assertEqual(older.status_code,200);self.assertEqual(older.get_json()['checkin']['note'],'Synthetic old check-in')
        routine=self.client.get('/api/routines').get_json()['routines'][0]
        self.assertEqual(routine['checkin_count'],105);self.assertEqual(routine['latest_checkin_date'],date.today().isoformat())
        export=self.client.get('/api/account-data/download').get_json()
        self.assertEqual(len(export['records']['progress_checkins']),105)
        original=next(r for r in export['records']['progress_checkins'] if r['checkin_id']==target)
        self.assertEqual(original['checkin_date'],'2025-01-01')

    def test_concurrent_checkin_retries_and_invalid_inputs(self):
        routine=self.routine();cookie=self.client.get_cookie('session').value;barrier=Barrier(2);key=uuid.uuid4().hex
        payload=dict(routine_id=routine,checkin_date=date.today().isoformat(),reported_trend='unchanged',discomfort=6,change=8,note='Synthetic concurrent retry')
        def submit(_):
            client=self.app.test_client();client.set_cookie('session',cookie);csrf=client.get('/api/security/csrf').get_json()['csrf_token'];barrier.wait()
            return client.post('/api/progress-checkins',json=payload,headers={'X-CSRF-Token':csrf,'Idempotency-Key':key})
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(submit,range(2)))
        self.assertEqual([r.status_code for r in responses],[201,201]);self.assertEqual(responses[0].get_json(),responses[1].get_json())
        self.assertEqual(len(self.client.get('/api/progress-checkins').get_json()['checkins']),1)
        self.assertEqual(self.keyed('/api/progress-checkins',{**payload,'note':'Changed'},key=key).status_code,409)
        for patch in [dict(discomfort=None),dict(discomfort=True),dict(change=-1),dict(checkin_date='bad')]:
            self.assertEqual(self.keyed('/api/progress-checkins',{**payload,**patch}).status_code,400)

    def test_routine_retry_and_search_cursor_invalidated_on_revision(self):
        payload=dict(condition_label='Synthetic label',routine_name='Retry routine',start_date=date.today().isoformat(),notes='Synthetic')
        key=uuid.uuid4().hex;first=self.keyed('/api/routines',payload,key=key)
        second=self.keyed('/api/routines',payload,key=key)
        self.assertEqual(first.status_code,201);self.assertEqual(first.get_json()['routine_id'],second.get_json()['routine_id'])
        self.assertEqual(len(self.client.get('/api/routines').get_json()['routines']),1)
        self.assertEqual(self.keyed('/api/routines',{**payload,'notes':'Other'},key=key).status_code,409)
