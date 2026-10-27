"""Owner-scoped routine schedules/events, keyset history and factual Today data."""
from __future__ import annotations
from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Blueprint, current_app, jsonify, request
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.exceptions import Unauthorized
from consumer_security import enabled, json_object, record, digest, utcnow
from consumer_continuity import effective_events, episode_links, link_episode, lock_owner, utc_iso, records as consumer_records

AREAS = {'Skin', 'Hair', 'Nails', 'Sweat', 'General'}


def schedule_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError('Send a schedule object.')
    steps = payload.get('steps', [])
    days = payload.get('days', list(range(7)))
    times = payload.get('times', ['09:00'])
    zone = payload.get('timezone', '')
    if not isinstance(steps, list) or not 1 <= len(steps) <= 20 or any(not isinstance(s, str) or not s.strip() or len(s) > 180 for s in steps):
        raise ValueError('Provide 1–20 routine steps, up to 180 characters each.')
    if not isinstance(days, list) or not days or len(days) > 7 or any(type(d) is not int or d not in range(7) for d in days):
        raise ValueError('Select one or more days.')
    if not isinstance(times, list) or not 1 <= len(times) <= 4 or any(not isinstance(t, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', t) for t in times):
        raise ValueError('Select 1–4 valid local times.')
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ValueError('Choose a valid IANA timezone.') from None
    status = payload.get('status', 'active')
    area = payload.get('area', 'General')
    if status not in {'active', 'paused', 'archived'} or area not in AREAS:
        raise ValueError('Choose a supported routine status and area.')
    reminders = payload.get('reminders', False)
    if not isinstance(reminders, bool):
        raise ValueError('Reminder opt-in must be true or false.')
    quiet_start, quiet_end = payload.get('quiet_start', '21:00'), payload.get('quiet_end', '08:00')
    if any(not isinstance(t, str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', t) for t in [quiet_start, quiet_end]):
        raise ValueError('Choose valid quiet hours.')
    episode, body_area = payload.get('episode', ''), payload.get('body_area', '')
    if not isinstance(episode, str) or not isinstance(body_area, str) or len(episode) > 120 or len(body_area) > 80:
        raise ValueError('Use a short concern/episode and body-area label.')
    return dict(steps=[s.strip() for s in steps], days=sorted(set(days)), times=sorted(set(times)), timezone=zone, status=status,
                area=area, episode=episode.strip(), body_area=body_area.strip(), reminders=reminders, quiet_start=quiet_start, quiet_end=quiet_end)


def get_schedule(cursor, user_id, routine_id, lock=False):
    cursor.execute("SELECT data_json FROM consumer_records WHERE user_id=%s AND kind='routine_schedule' AND subject_id=%s" + (' FOR UPDATE' if lock else ''), (user_id, routine_id))
    row = cursor.fetchone()
    return json.loads(row['data_json']) if row else None


def quiet_time(value, start, end):
    return start <= value < end if start < end else value >= start or value < end if start != end else False


def local_occurrences(config, day):
    """DST gaps skipped, folds sent once at first occurrence; no fake local times."""
    zone = ZoneInfo(config['timezone'])
    if day.weekday() not in config['days'] or config['status'] != 'active':
        return []
    result = []
    for value in config['times']:
        if quiet_time(value, config['quiet_start'], config['quiet_end']):
            continue
        naive = datetime.combine(day, time.fromisoformat(value))
        aware = naive.replace(tzinfo=zone, fold=0)
        from datetime import timezone
        utc = aware.astimezone(timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None) != naive:
            continue
        result.append(utc.replace(tzinfo=None))
    return result


def archive_routine(connection, user_id, routine_id):
    lock_owner(connection, user_id)
    with connection.cursor() as cursor:
        cursor.execute('SELECT routine_name FROM care_routines WHERE user_id=%s AND routine_id=%s FOR UPDATE', (user_id, routine_id))
        routine = cursor.fetchone()
        if not routine:
            return False
        config = get_schedule(cursor, user_id, routine_id, lock=True) or schedule_payload(dict(steps=[routine['routine_name']], timezone='UTC'))
        config.update(status='archived', reminders=False, version=config.get('version', 0) + 1)
        key = digest(f"{user_id}:routine_schedule:{routine_id}")
        cursor.execute('INSERT INTO consumer_records(record_id,user_id,kind,subject_id,dedupe_key,data_json,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(),UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE data_json=VALUES(data_json),updated_at=UTC_TIMESTAMP()',
                       ('schedule-' + digest(routine_id)[:32], user_id, 'routine_schedule', routine_id, key, json.dumps(config)))
        record(connection, user_id, 'routine_revision', routine_id, config)
        cursor.execute("UPDATE reminder_jobs SET state='cancelled',updated_at=UTC_TIMESTAMP() WHERE user_id=%s AND routine_id=%s AND state IN ('scheduled','retry','sending')", (user_id, routine_id))
    return True


def register_engagement(app, database, current_user, read_summary):
    bp = Blueprint('consumer_engagement', __name__)

    @contextmanager
    def owned():
        connection = database()
        try:
            user = current_user(connection)
            if not user:
                raise Unauthorized('Sign in to use your Journey.')
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
            return jsonify(error='Consumer development features are not enabled.'), 503

    @bp.route('/api/routine-schedules/<routine_id>', methods=['GET', 'PUT'])
    def routine_schedule(routine_id):
        with owned() as (connection, user):
            if request.method == 'PUT':
                lock_owner(connection, user['id'])
            with connection.cursor() as cursor:
                cursor.execute('SELECT routine_id FROM care_routines WHERE user_id=%s AND routine_id=%s FOR UPDATE', (user['id'], routine_id))
                if not cursor.fetchone():
                    return jsonify(error='Routine not found.'), 404
                existing = get_schedule(cursor, user['id'], routine_id, lock=True)
                if request.method == 'GET':
                    cursor.execute("SELECT record_id,data_json,created_at FROM consumer_records WHERE user_id=%s AND kind='routine_event' AND subject_id=%s ORDER BY id DESC LIMIT 100", (user['id'], routine_id))
                    events = effective_events(connection, user['id'], [dict(id=r['record_id'], **json.loads(r['data_json']), created_at=r['created_at']) for r in cursor.fetchall()])
                    return jsonify(schedule=existing, events=events, episode_link=episode_links(connection, user['id']).get('routine:' + routine_id, {}))
                payload = json_object()
                config = schedule_payload(payload)
                if type(payload.get('version')) is not int or payload['version'] != (existing or {}).get('version', 0):
                    return jsonify(error='This routine changed in another tab. Reload its schedule before editing.', code='SCHEDULE_CHANGED'), 409
                config['version'] = payload['version'] + 1
                if 'episode_id' in payload:
                    if not isinstance(payload['episode_id'], str) or type(payload.get('link_version')) is not int:
                        raise ValueError('Choose a concern and its current association version.')
                    link_episode(connection, user['id'], 'routine', routine_id, payload['episode_id'], payload['link_version'])
                key = digest(f"{user['id']}:routine_schedule:{routine_id}")
                cursor.execute('INSERT INTO consumer_records(record_id,user_id,kind,subject_id,dedupe_key,data_json,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(),UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE data_json=VALUES(data_json),updated_at=UTC_TIMESTAMP()',
                               ('schedule-' + digest(routine_id)[:32], user['id'], 'routine_schedule', routine_id, key, json.dumps(config)))
                record(connection, user['id'], 'routine_revision', routine_id, config)
                cursor.execute("UPDATE reminder_jobs SET state='cancelled',updated_at=UTC_TIMESTAMP() WHERE user_id=%s AND routine_id=%s AND state IN ('scheduled','retry','sending')", (user['id'], routine_id))
            return jsonify(schedule=config, episode_link=episode_links(connection, user['id']).get('routine:' + routine_id, {}), message='Schedule saved. Existing completion history is preserved.', reminder_state='configured' if config['reminders'] else 'not_opted_in')

    @bp.post('/api/routine-schedules/<routine_id>/events')
    def routine_event(routine_id):
        payload = json_object()
        action, step, slot = payload.get('action'), payload.get('step'), payload.get('time')
        key = request.headers.get('Idempotency-Key', '')
        if action not in {'completed', 'skipped'} or type(step) is not int or not isinstance(slot, str) or not re.fullmatch('[A-Za-z0-9_-]{16,80}', key):
            raise ValueError('Choose a step, time and completion or skip action.')
        try:
            day = date.fromisoformat(payload.get('date', ''))
        except (ValueError, TypeError):
            raise ValueError('Choose a valid local date.') from None
        with owned() as (connection, user):
            lock_owner(connection, user['id'])
            with connection.cursor() as cursor:
                cursor.execute('SELECT routine_id FROM care_routines WHERE user_id=%s AND routine_id=%s', (user['id'], routine_id))
                if not cursor.fetchone():
                    return jsonify(error='Routine not found.'), 404
                config = get_schedule(cursor, user['id'], routine_id, lock=True)
                if not config or config['status'] != 'active' or not 0 <= step < len(config['steps']) or slot not in config['times'] or day.weekday() not in config['days']:
                    raise ValueError('Choose an active scheduled step.')
                today = datetime.now(ZoneInfo(config['timezone'])).date()
                if day > today or day < today - timedelta(days=365):
                    raise ValueError('Choose today or a date within the past year.')
                supplied_version = payload.get('schedule_version')
                if supplied_version is not None and (type(supplied_version) is not int or supplied_version != config['version']):
                    return jsonify(error='This scheduled step changed. Refresh Today before recording it.', code='SCHEDULE_CHANGED'), 409
                data = dict(action=action, step=step, step_text=config['steps'][step], time=slot, date=day.isoformat(), schedule_version=config['version'], timezone=config['timezone'])
                episode = episode_links(connection, user['id'], lock=True).get('routine:' + routine_id, {})
                if episode.get('episode_id'):
                    data['episode_id'] = episode['episode_id']
                # The schedule row is locked above. Two tabs with different
                # request keys still represent one occurrence, not two events.
                cursor.execute("SELECT record_id,data_json FROM consumer_records WHERE user_id=%s AND kind='routine_event' AND subject_id=%s AND JSON_UNQUOTE(JSON_EXTRACT(data_json,'$.date'))=%s AND JSON_UNQUOTE(JSON_EXTRACT(data_json,'$.time'))=%s AND JSON_EXTRACT(data_json,'$.step')=%s AND JSON_EXTRACT(data_json,'$.schedule_version')=%s ORDER BY id DESC LIMIT 1 FOR UPDATE",
                               (user['id'], routine_id, day.isoformat(), slot, step, config['version']))
                existing_event = cursor.fetchone()
                if existing_event:
                    if json.loads(existing_event['data_json']) != data:
                        return jsonify(error='This scheduled step already has a different recorded action. Refresh Today.', code='EVENT_ALREADY_RECORDED'), 409
                    return jsonify(event_id=existing_event['record_id'], event=data), 201
                result = record(connection, user['id'], 'routine_event', routine_id, data, key)
                if json.loads(result['data_json']) != data:
                    return jsonify(error='This action identifier was already used for different details.'), 409
            return jsonify(event_id=result['record_id'], event=data), 201

    @bp.get('/api/today')
    def today():
        with owned() as (connection, user):
            with connection.cursor() as cursor:
                cursor.execute("SELECT r.routine_id,r.routine_name,r.start_date,s.data_json FROM care_routines r JOIN consumer_records s ON s.subject_id=r.routine_id AND s.user_id=r.user_id AND s.kind='routine_schedule' WHERE r.user_id=%s ORDER BY r.id DESC LIMIT 100", (user['id'],))
                routines = cursor.fetchall()
                cursor.execute("SELECT record_id,subject_id,data_json,created_at FROM consumer_records WHERE user_id=%s AND kind='routine_event' AND JSON_UNQUOTE(JSON_EXTRACT(data_json,'$.date'))>=DATE_FORMAT(DATE_SUB(UTC_TIMESTAMP(),INTERVAL 2 DAY),'%%Y-%%m-%%d') ORDER BY id DESC", (user['id'],))
                events = cursor.fetchall()
                cursor.execute('SELECT assessment_id,area,created_at FROM analysis_records WHERE user_id=%s ORDER BY id DESC LIMIT 1', (user['id'],))
                recent = cursor.fetchone()
            events = effective_events(connection, user['id'], [dict(id=r['record_id'], subject_id=r['subject_id'], **json.loads(r['data_json']), created_at=r['created_at']) for r in events])
            links = episode_links(connection, user['id'])
            episodes = {r['id']: dict(episode_id=r['id'], **r['data']) for r in consumer_records(connection, user['id'], 'concern_episode')}
            tasks = []
            seen = set()
            for entry in routines:
                config = json.loads(entry['data_json']); day = datetime.now(ZoneInfo(config['timezone'])).date()
                if config['status'] != 'active' or day.weekday() not in config['days'] or str(entry['start_date'])[:10] > day.isoformat():
                    continue
                completed = {}
                for event in events:
                    if event['subject_id'] != entry['routine_id']:
                        continue
                    data = event; marker = (data['date'], data['time'], data['step'], data['schedule_version'])
                    if marker not in completed:
                        completed[marker] = data
                for slot in config['times']:
                    for index, label in enumerate(config['steps']):
                        event = completed.get((day.isoformat(), slot, index, config['version']), {})
                        association = episodes.get(event.get('episode_id'), {}) if event.get('id') else links.get('routine:' + entry['routine_id'], {})
                        tasks.append(dict(routine_id=entry['routine_id'], routine_name=entry['routine_name'], step=index, label=label, time=slot, date=day.isoformat(), timezone=config['timezone'], schedule_version=config['version'], state=event.get('action', 'pending'), event_id=event.get('id'), revision=event.get('revision', 0), episode=association))
            return jsonify(tasks=tasks, recent_result=recent, meaning='Completion and trends are user-reported, not measured healing.', routine_window_limit=100)

    @bp.put('/api/journey/assessments/<assessment_id>/context')
    def label_assessment(assessment_id):
        payload = json_object()
        episode, body_area = payload.get('episode', ''), payload.get('body_area', '')
        if not isinstance(episode, str) or not isinstance(body_area, str) or len(episode) > 120 or len(body_area) > 80:
            raise ValueError('Use an episode label up to 120 characters and body-area label up to 80.')
        data = dict(episode=episode.strip(), body_area=body_area.strip())
        with owned() as (connection, user):
            with connection.cursor() as cursor:
                cursor.execute('SELECT assessment_id FROM analysis_records WHERE user_id=%s AND assessment_id=%s FOR UPDATE', (user['id'], assessment_id))
                if not cursor.fetchone():
                    return jsonify(error='Saved result not found.'), 404
                key = digest(f"{user['id']}:assessment_context:{assessment_id}")
                cursor.execute('INSERT INTO consumer_records(record_id,user_id,kind,subject_id,dedupe_key,data_json,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(),UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE data_json=VALUES(data_json),updated_at=UTC_TIMESTAMP()',
                               ('context-' + key[:32], user['id'], 'assessment_context', assessment_id, key, json.dumps(data)))
                record(connection, user['id'], 'context_revision', assessment_id, data)
            return jsonify(context=data, message='Your labels were saved separately. The original assessment is unchanged.')

    @bp.get('/api/journey/assessments')
    def history():
        query = request.args.get('q', '').strip()
        area = request.args.get('area', '')
        episode, body_area = request.args.get('episode', '').strip(), request.args.get('body_area', '').strip()
        episode_id = request.args.get('episode_id', '')
        if len(episode) > 120 or len(body_area) > 80:
            raise ValueError('Use shorter episode and body-area filters.')
        if len(query) > 120 or area and area not in AREAS:
            raise ValueError('Use a search up to 120 characters and a supported area.')
        serializer = URLSafeTimedSerializer(current_app.secret_key, salt='journey-keyset-v1')
        with owned() as (connection, user):
            cursor_token = request.args.get('cursor', '')
            before = None
            with connection.cursor() as cursor:
                if cursor_token:
                    try:
                        state = serializer.loads(cursor_token, max_age=86400)
                        if state['owner'] != user['id'] or state['q'] != query or state['area'] != area or state.get('episode','') != episode or state.get('body_area','') != body_area or state.get('episode_id','') != episode_id:
                            raise BadSignature('Owner/filter mismatch')
                        before, snapshot = state['before'], state['snapshot']
                    except (BadSignature, SignatureExpired, KeyError, TypeError):
                        raise ValueError('This history page expired or its filters changed. Start the search again.') from None
                else:
                    cursor.execute('SELECT COALESCE(MAX(id),0) AS snapshot FROM analysis_records WHERE user_id=%s', (user['id'],))
                    snapshot = cursor.fetchone()['snapshot']
                conditions, values = ['a.user_id=%s', 'a.id<=%s'], [user['id'], snapshot]
                if before is not None:
                    conditions.append('a.id<%s'); values.append(before)
                if area:
                    conditions.append('a.area=%s'); values.append(area)
                if query:
                    escaped = query.replace('!', '!!').replace('%', '!%').replace('_', '!_')
                    conditions.append("(a.assessment_id LIKE %s ESCAPE '!' OR a.result_json LIKE %s ESCAPE '!')"); values.extend(['%' + escaped + '%'] * 2)
                if episode:
                    conditions.append("JSON_UNQUOTE(JSON_EXTRACT(c.data_json,'$.episode'))=%s"); values.append(episode)
                if body_area:
                    conditions.append("JSON_UNQUOTE(JSON_EXTRACT(c.data_json,'$.body_area'))=%s"); values.append(body_area)
                if episode_id:
                    conditions.append("EXISTS(SELECT 1 FROM consumer_records l WHERE l.user_id=a.user_id AND l.kind='episode_link' AND l.subject_id=CONCAT('assessment:',a.assessment_id) AND JSON_UNQUOTE(JSON_EXTRACT(l.data_json,'$.episode_id'))=%s)"); values.append(episode_id)
                cursor.execute("SELECT a.id,a.assessment_id,a.area,a.result_json,a.image_stored,a.created_at,c.data_json AS context_json FROM analysis_records a LEFT JOIN consumer_records c ON c.user_id=a.user_id AND c.subject_id=a.assessment_id AND c.kind='assessment_context' WHERE " + ' AND '.join(conditions) + ' ORDER BY a.id DESC LIMIT 21', tuple(values))
                rows = cursor.fetchall()
            links = episode_links(connection, user['id'])
            more = len(rows) > 20; rows = rows[:20]
            analyses = []
            for row in rows:
                summary = read_summary(row['result_json'])
                analyses.append(dict(assessment_id=row['assessment_id'], area=row['area'], created_at=utc_iso(row['created_at']), summary=summary or {}, unavailable=summary is None, image_stored=bool(row['image_stored']), context=json.loads(row['context_json']) if row.get('context_json') else {}, episode_link=links.get('assessment:' + row['assessment_id'], {})))
            next_cursor = serializer.dumps(dict(owner=user['id'], q=query, area=area, episode=episode, body_area=body_area, episode_id=episode_id, snapshot=snapshot, before=rows[-1]['id'])) if more else None
            return jsonify(analyses=analyses, next_cursor=next_cursor, order='newest_saved_first', snapshot=snapshot)

    @bp.get('/api/reminders')
    def reminders():
        from delivery import delivery_mode
        with owned() as (connection, user):
            with connection.cursor() as cursor:
                cursor.execute('SELECT job_id,routine_id,due_at,state,attempts,provider_reference FROM reminder_jobs WHERE user_id=%s ORDER BY due_at DESC LIMIT 100', (user['id'],))
                jobs = cursor.fetchall()
            return jsonify(jobs=jobs, transport=delivery_mode(), delivery_verified=False, worker='Explicit development command; no background system service is installed.')

    @bp.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error), code='INVALID_INPUT'), 400

    app.register_blueprint(bp)
