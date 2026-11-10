"""Isolated account contracts for activity, comparison and scoped discovery."""
import hashlib
import json
import os
import unittest
from unittest.mock import patch

import test_consumer_accounts as accounts
import test_consumer_continuity as continuity_tests
from consumer_continuity import continuity_data


@unittest.skipUnless(os.getenv('DERMAMATRIX_RUN_MYSQL_INTEGRATION_TESTS') == '1', 'Disposable synthetic SQL only')
class ConsumerJourney(unittest.TestCase):
    setUpClass = classmethod(accounts.ConsumerAccounts.setUpClass.__func__)
    setUp = accounts.ConsumerAccounts.setUp
    tearDown = accounts.ConsumerAccounts.tearDown
    call = accounts.ConsumerAccounts.call
    keyed = continuity_tests.ConsumerContinuity.keyed
    episode = continuity_tests.ConsumerContinuity.episode
    routine = continuity_tests.ConsumerContinuity.routine
    schedule = continuity_tests.ConsumerContinuity.schedule
    event = continuity_tests.ConsumerContinuity.event

    def assessments(self, episode, count=2):
        connection = self.module.database()
        identifiers = []
        try:
            with connection.cursor() as cursor:
                for index in range(count):
                    identifier = self.identifier[:14] + '-saved-' + str(index)
                    summary = dict(assessment_risk=dict(score=10+index,methodology_version='synthetic-v1'),
                                   assessment_result=dict(status=dict(code='QUESTIONNAIRE_ASSESSMENT'),
                                       consumer=dict(primary_result=dict(title='Recorded synthetic result '+str(index)))),
                                   manual_context=dict(pattern='Synthetic only'))
                    cursor.execute('INSERT INTO analysis_records(assessment_id,user_id,area,result_json,created_at) VALUES(%s,%s,%s,%s,%s)',
                                   (identifier,self.user_id,'Skin',json.dumps(summary),'2025-01-01 09:00:00'))
                    identifiers.append(identifier)
            connection.commit()
        finally:
            connection.close()
        for identifier in identifiers:
            self.assertEqual(self.call('/api/episode-links/assessment/'+identifier,dict(episode_id=episode,version=0),method='PUT').status_code,200)
        return identifiers

    def test_activity_keyset_filters_and_original_history(self):
        episode = self.episode()
        identifiers = self.assessments(episode,24)
        path = '/api/journey/activity?episode_id='+episode
        page = self.client.get(path).get_json()
        self.assertEqual(len(page['activity']),20)
        more = self.client.get(path+'&cursor='+page['next_cursor']).get_json()
        self.assertEqual(len(more['activity']),4)
        all_ids = [row['id'] for row in page['activity']+more['activity']]
        self.assertEqual(len(set(all_ids)),24)
        self.assertEqual(set(all_ids),set(identifiers))
        self.assertEqual(self.client.get(path+'&start=2025-02-01').get_json()['activity'],[])
        self.assertEqual(self.client.get(path+'&kind=invalid').status_code,400)
        self.assertEqual(self.client.get(path+'&cursor=broken').status_code,400)
        self.assertEqual(self.client.get('/api/journey/activity?episode_id=missing').status_code,404)
        self.assertEqual(self.app.test_client().get(path).status_code,401)
        self.assertEqual(self.client.get(path+'&kind=checkin&cursor='+page['next_cursor']).status_code,400)
        self.episode('New revision')
        self.assertEqual(self.client.get(path+'&cursor='+page['next_cursor']).status_code,409)

    def test_activity_uses_effective_dates_and_event_time_links(self):
        episode = self.episode()
        routine = self.routine()
        self.schedule(routine)
        self.assertEqual(self.call('/api/episode-links/routine/'+routine,dict(episode_id=episode,version=0),method='PUT').status_code,200)
        event = self.event(routine)
        checkin = self.keyed('/api/progress-checkins',dict(routine_id=routine,checkin_date='2025-01-01',reported_trend='unchanged',episode_id=episode)).get_json()['checkin_id']
        response = self.keyed('/api/corrections/checkin/'+checkin,dict(revision=0,checkin_date='2025-03-01',reported_trend='improving',note='Corrected synthetic note'))
        self.assertEqual(response.status_code,200,response.get_json())
        rows = self.client.get('/api/journey/activity?episode_id='+episode).get_json()['activity']
        effective = next(row for row in rows if row['id']==checkin)
        self.assertEqual(effective['recorded_date'],'2025-03-01')
        self.assertEqual(effective['revision'],1)
        self.assertEqual(effective['original']['checkin_date'].isoformat(),'2025-01-01') if hasattr(effective['original']['checkin_date'],'isoformat') else self.assertIn('2025',effective['original']['checkin_date'])
        self.assertEqual(self.keyed('/api/corrections/checkin/'+checkin,dict(revision=1,voided=True)).status_code,200)
        removed = self.client.get('/api/journey/activity?routine_id='+routine+'&start=2025-03-01&end=2025-03-01').get_json()['activity']
        self.assertEqual(len(removed),1)
        self.assertTrue(removed[0]['voided'])
        self.assertEqual(self.call('/api/episode-links/routine/'+routine,dict(episode_id='',version=1),method='PUT').status_code,200)
        event_rows = self.client.get('/api/journey/activity?episode_id='+episode+'&kind=event').get_json()['activity']
        self.assertIn(event,[row['id'] for row in event_rows])
        self.assertEqual(self.call('/api/routines/'+routine,method='DELETE').status_code,200)
        self.assertIn(checkin,[row['id'] for row in self.client.get('/api/journey/activity?routine_id='+routine).get_json()['activity']])

    def test_comparison_uses_saved_rules_and_does_not_mutate(self):
        episode = self.episode()
        identifiers = self.assessments(episode)
        connection = self.module.database()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT result_json FROM analysis_records WHERE user_id=%s ORDER BY id',(self.user_id,))
                before = hashlib.sha256(repr(cursor.fetchall()).encode()).hexdigest()
        finally:
            connection.close()
        result = self.call('/api/journey/compare',dict(assessment_ids=identifiers))
        self.assertEqual(result.status_code,200,result.get_json())
        data = result.get_json()
        self.assertEqual([row['assessment_id'] for row in data['records']],identifiers)
        self.assertEqual(data['comparison']['comparison']['risk_change'],1)
        self.assertIsNone(data['comparison']['comparison']['likelihood_change'])
        self.assertEqual(self.call('/api/journey/compare',dict(assessment_ids=[identifiers[0]]*2)).status_code,400)
        self.assertEqual(self.call('/api/journey/compare',dict(assessment_ids=[{},{}])).status_code,400)
        self.assertEqual(self.call('/api/journey/compare',dict(assessment_ids=[identifiers[0],'foreign-record'])).status_code,404)
        other = self.episode('Other concern')
        self.assertEqual(self.call('/api/episode-links/assessment/'+identifiers[1],dict(episode_id=other,version=1),method='PUT').status_code,200)
        self.assertEqual(self.call('/api/journey/compare',dict(assessment_ids=identifiers)).status_code,400)
        connection = self.module.database()
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT result_json FROM analysis_records WHERE user_id=%s ORDER BY id',(self.user_id,))
                self.assertEqual(hashlib.sha256(repr(cursor.fetchall()).encode()).hexdigest(),before)
        finally:
            connection.close()

    def test_discovery_scopes_titles_and_skips_unrelated_assessment_parsing(self):
        episode = self.episode()
        identifiers = self.assessments(episode,25)
        response = self.client.get('/api/search?category=assessment&area=Skin&episode_id='+episode)
        self.assertEqual(response.status_code,200,response.get_json())
        page = response.get_json()
        self.assertEqual(len(page['results']),20)
        self.assertTrue(all(row['title'].startswith('Recorded synthetic result') for row in page['results']))
        self.assertEqual(self.client.get('/api/search?category=assessment&area=Hair').get_json()['results'],[])
        self.assertEqual(self.client.get('/api/search?category=assessment&start=2025-02-01').get_json()['results'],[])
        self.assertEqual(self.client.get('/api/search?category=assessment&area=Hair&cursor='+page['next_cursor']).status_code,400)
        original = self.module.read_saved_summary
        with patch.object(self.module,'read_saved_summary',wraps=original) as parser:
            self.assertEqual(self.client.get('/api/search?category=routine').status_code,200)
            self.assertEqual(parser.call_count,0)
        connection = self.module.database()
        try:
            calls=[]
            with self.app.app_context():
                continuity_data(connection,self.user_id,lambda value:calls.append(value) or {})
            self.assertEqual(len(calls),len(identifiers))
        finally:
            connection.close()

    def test_daily_view_is_owned_and_retains_archived_events(self):
        from datetime import datetime, timezone
        routine = self.routine()
        self.schedule(routine)
        event = self.event(routine)
        path = '/api/journey/routines/'+routine+'/day?date='+datetime.now(timezone.utc).date().isoformat()
        response = self.client.get(path)
        self.assertEqual(response.status_code,200,response.get_json())
        self.assertTrue(any(row['event_id']==event and row['state']=='completed' for row in response.get_json()['slots']))
        self.assertEqual(self.app.test_client().get(path).status_code,401)
        self.assertEqual(self.client.get(path.replace(routine,'missing')).status_code,404)
        self.assertEqual(self.client.get(path.replace('date=','date=invalid')).status_code,400)
        self.assertEqual(self.call('/api/routines/'+routine,method='DELETE').status_code,200)
        self.assertTrue(any(row['event_id']==event for row in self.client.get(path).get_json()['slots']))


class RoutineDayProjection(unittest.TestCase):
    def test_plan_intervals_corrections_and_future_are_distinct(self):
        from datetime import date, datetime
        from consumer_journey import routine_day
        from consumer_engagement import schedule_payload
        first = schedule_payload(dict(steps=['Original step'], timezone='Asia/Kolkata', times=['09:00','18:00'], quiet_start='00:00',quiet_end='00:00'))
        first['version'] = 1
        paused = dict(first,status='paused',version=2)
        revisions = [dict(data=first,created_at=datetime(2026,1,1)),dict(data=paused,created_at=datetime(2026,1,2,6))]
        event = dict(id='original-event',schedule_version=1,step=0,step_text='Original step',time='09:00',timezone='Asia/Kolkata',action='completed',revision=1)
        original = json.dumps(event,sort_keys=True)
        slots = routine_day(revisions,[event],date(2026,1,2),date(2026,1,1),datetime(2026,1,2,4))
        self.assertEqual([(s['time'],s['state']) for s in slots],[('09:00','completed')])
        self.assertEqual(slots[0]['revision'],1)
        self.assertEqual(json.dumps(event,sort_keys=True),original)
        future = routine_day(revisions[:1],[],date(2026,1,2),date(2026,1,1),datetime(2026,1,2,4))
        self.assertEqual([s['state'] for s in future],['unrecorded','scheduled'])
        self.assertEqual(routine_day(revisions,[],date(2026,1,3),date(2026,1,1),datetime(2026,1,4)),[])
        self.assertEqual(routine_day(revisions[:1],[],date(2025,12,31),date(2026,1,1),datetime(2026,1,4)),[])

    def test_dst_gap_fold_and_quiet_hours_reuse_schedule_rules(self):
        from datetime import date, datetime
        from consumer_journey import routine_day
        from consumer_engagement import schedule_payload
        config = schedule_payload(dict(steps=['Own observation'],timezone='America/New_York',times=['01:30','02:30'],quiet_start='00:00',quiet_end='00:00'))
        config['version'] = 1
        revisions = [dict(data=config,created_at=datetime(2025,1,1))]
        self.assertEqual(len(routine_day(revisions,[],date(2025,3,9),date(2025,1,1),datetime(2026,1,1))),1)
        self.assertEqual(len(routine_day(revisions,[],date(2025,11,2),date(2025,1,1),datetime(2026,1,1))),2)
        config.update(quiet_start='01:00',quiet_end='03:00')
        self.assertEqual(routine_day(revisions,[],date(2025,11,2),date(2025,1,1),datetime(2026,1,1)),[])
