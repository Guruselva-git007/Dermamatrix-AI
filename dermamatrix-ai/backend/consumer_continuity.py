"""Continuity over existing records: append-only corrections and explicit links.

No schema migration or historical backfill. consumer_records is the existing
owner-indexed store; original assessment/check-in/event rows are never changed.
All readers use the same effective projections below, including exports.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import io
import json
import re
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request, send_file, session
from itsdangerous import URLSafeTimedSerializer, BadSignature
from werkzeug.exceptions import BadRequest, Conflict, NotFound, Unauthorized

from consumer_security import enabled, json_object, record, digest

AREAS = {'Skin', 'Hair', 'Nails', 'Sweat', 'General'}
BODY_AREAS = ('Unspecified', 'Face', 'Scalp', 'Neck', 'Chest', 'Back', 'Arm', 'Hand', 'Leg', 'Foot', 'Fingernail', 'Toenail', 'Underarm', 'Multiple areas', 'Other')
ENTITY_TABLES = {'assessment': ('analysis_records', 'assessment_id'), 'routine': ('care_routines', 'routine_id'), 'checkin': ('progress_checkins', 'checkin_id')}


def utc_iso(value):
    """The existing DB save-time contract is UTC; don't let browsers infer local."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    return str(value)


def records(connection, owner, kind, subject=None, lock=False):
    with connection.cursor() as cursor:
        cursor.execute('SELECT id,record_id,subject_id,data_json,created_at FROM consumer_records WHERE user_id=%s AND kind=%s' + (' AND subject_id=%s' if subject is not None else '') + ' ORDER BY id' + (' FOR UPDATE' if lock else ''), (owner, kind, subject) if subject is not None else (owner, kind))
        return [dict(id=r['record_id'], sequence=r['id'], subject_id=r['subject_id'], data=json.loads(r['data_json']), created_at=r['created_at']) for r in cursor.fetchall()]


def effective_records(connection, owner, kind, rows, id_field, lock=False):
    """One authoritative adapter. Preserve original and full correction lineage."""
    corrections = {}
    for revision in records(connection, owner, kind + '_correction', lock=lock):
        corrections.setdefault(revision['subject_id'], []).append(revision)
    result = []
    for row in rows:
        history = corrections.get(row[id_field], [])
        original = dict(row)
        effective = dict(row)
        for revision in history:
            effective.update(revision['data']['effective'])
        effective.update(revision=len(history), corrections=history, original=original)
        result.append(effective)
    return result


def effective_events(connection, owner, rows):
    return effective_records(connection, owner, 'event', rows, 'id')


def effective_checkins(connection, owner, rows):
    if not enabled():
        return rows
    projected = effective_records(connection, owner, 'checkin', rows, 'checkin_id')
    return sorted(projected, key=lambda r: (str(r.get('checkin_date', ''))[:10], r.get('id', 0), r['checkin_id']), reverse=True)


def episode_links(connection, owner, lock=False):
    # Mutable link is a projection of the separately appended link revisions.
    return {r['subject_id']: r['data'] for r in records(connection, owner, 'episode_link', lock=lock)}


def require_episode(connection, owner, identifier):
    with connection.cursor() as cursor:
        cursor.execute("SELECT data_json FROM consumer_records WHERE user_id=%s AND kind='concern_episode' AND record_id=%s", (owner, identifier))
        row = cursor.fetchone()
    if not row:
        raise NotFound('Concern not found in this account.')
    return json.loads(row['data_json'])


def link_episode(connection, owner, entity, identifier, episode_id, expected=None):
    if entity not in ENTITY_TABLES:
        raise ValueError('Choose an assessment, routine or check-in.')
    table, column = ENTITY_TABLES[entity]
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT {column}' + (',area' if entity == 'assessment' else '') + f' FROM {table} WHERE user_id=%s AND {column}=%s FOR UPDATE', (owner, identifier))
        entity_row = cursor.fetchone()
        if not entity_row:
            raise NotFound('Record not found in this account.')
        episode = require_episode(connection, owner, episode_id) if episode_id else None
        subject = entity + ':' + identifier
        cursor.execute("SELECT record_id,data_json FROM consumer_records WHERE user_id=%s AND kind='episode_link' AND subject_id=%s FOR UPDATE", (owner, subject))
        existing = cursor.fetchone()
        previous = json.loads(existing['data_json']) if existing else {}
        if expected is not None and (type(expected) is not int or expected != previous.get('version', 0)):
            raise Conflict('This concern association changed. Reload before editing.')
        if episode and entity == 'assessment' and episode['area'] not in {'General', entity_row['area']}:
            raise BadRequest('This concern category does not match the saved assessment. Choose a matching concern or leave it unassigned.')
        if previous.get('episode_id', '') == (episode_id or ''):
            return previous
        data = dict(episode_id=episode_id or '', label=episode['label'] if episode else '', body_area=episode['body_area'] if episode else '', version=previous.get('version', 0) + 1, actor_id=owner)
        key = digest(f'{owner}:episode_link:{subject}')
        cursor.execute('INSERT INTO consumer_records(record_id,user_id,kind,subject_id,dedupe_key,data_json,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(),UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE data_json=VALUES(data_json),updated_at=UTC_TIMESTAMP()', ('link-' + key[:32], owner, 'episode_link', subject, key, json.dumps(data)))
        record(connection, owner, 'episode_link_revision', subject, data)
        return data


def request_key():
    key = request.headers.get('Idempotency-Key', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', key):
        raise ValueError('A valid retry identifier is required. Reload this action.')
    return key


def lock_owner(connection, owner):
    # Serializes append/check/replay even when no revision row yet exists.
    with connection.cursor() as cursor:
        cursor.execute('SELECT id FROM users WHERE id=%s FOR UPDATE', (owner,))
        cursor.fetchone()


def checkin_values(payload, score):
    trend, note = payload.get('reported_trend'), payload.get('note', '')
    try:
        day = date.fromisoformat(payload.get('checkin_date', ''))
    except (ValueError, TypeError):
        raise ValueError('Choose a valid check-in date.') from None
    if day > datetime.now(timezone.utc).date() + timedelta(days=1):
        raise ValueError('A check-in cannot describe a future date.')
    if trend not in {'improving', 'unchanged', 'worsening'} or not isinstance(note, str) or len(note) > 2000:
        raise ValueError('Choose a self-reported trend and a note up to 2,000 characters.')
    values = []
    for field, maximum in [('discomfort', 25), ('change', 18)]:
        raw = payload.get(field, 0)
        if isinstance(raw, bool) or not isinstance(raw, (str, int)) or not re.fullmatch(r'\d{1,2}', str(raw)) or not 0 <= int(raw) <= maximum:
            raise ValueError(f'Choose a valid reported {field} input (0 to {maximum}).')
        values.append(int(raw))
    discomfort, change = values
    return dict(checkin_date=day.isoformat(), reported_trend=trend, discomfort_score=discomfort, change_score=change, priority_score=score(discomfort, change), note=note.strip(), voided=False)


def reminder_preview(config, at=None):
    from consumer_engagement import local_occurrences, quiet_time
    at = at or datetime.now(timezone.utc).replace(tzinfo=None)
    local_day = at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(config['timezone'])).date()
    next_due = None
    for offset in range(15):
        future = [v for v in local_occurrences(config, local_day + timedelta(days=offset)) if v > at]
        if future:
            next_due = min(future)
            break
    return dict(timezone=config['timezone'], status=config['status'], days=config['days'], times=config['times'], quiet_start=config['quiet_start'], quiet_end=config['quiet_end'], suppressed_times=[v for v in config['times'] if quiet_time(v, config['quiet_start'], config['quiet_end'])], next_occurrence_utc=next_due.isoformat() + 'Z' if next_due else None, opted_in=config['reminders'], meaning='Preview only. Quiet-hour occurrences and nonexistent DST times are skipped; repeated DST times occur once. No reminder is queued or delivered by this preview.')


def continuity_data(connection, owner, read_summary):
    """Read one account snapshot; the caller owns transaction lifetime."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT id,assessment_id,area,result_json,created_at FROM analysis_records WHERE user_id=%s ORDER BY id DESC', (owner,))
        assessments = [dict(r, summary=read_summary(r['result_json'])) for r in cursor.fetchall()]
        cursor.execute('SELECT id,routine_id,routine_name,condition_label,start_date,notes,created_at FROM care_routines WHERE user_id=%s ORDER BY id DESC', (owner,))
        routines = cursor.fetchall()
        cursor.execute('SELECT id,checkin_id,routine_id,checkin_date,reported_trend,discomfort_score,change_score,priority_score,note,created_at FROM progress_checkins WHERE user_id=%s ORDER BY id DESC', (owner,))
        checkins = effective_checkins(connection, owner, cursor.fetchall())
    events = effective_events(connection, owner, [dict(id=r['id'], routine_id=r['subject_id'], **r['data'], created_at=r['created_at']) for r in records(connection, owner, 'routine_event')])
    return dict(assessments=assessments, routines=routines, checkins=checkins, events=events, links=episode_links(connection, owner), episodes=records(connection, owner, 'concern_episode'))


def routine_counts(connection, owner, routines):
    with connection.cursor() as cursor:
        cursor.execute('SELECT checkin_id,routine_id,checkin_date FROM progress_checkins WHERE user_id=%s', (owner,))
        checkins = effective_checkins(connection, owner, cursor.fetchall())
    for routine in routines:
        relevant = [c for c in checkins if c['routine_id'] == routine.get('routine_id') and not c.get('voided')]
        routine['checkin_count'] = len(relevant)
        routine['latest_checkin_date'] = max((str(c['checkin_date'])[:10] for c in relevant), default=None)
    return routines


def visit_brief(data, payload, owner, connection):
    episode_id = payload.get('episode_id')
    if not isinstance(episode_id, str) or not episode_id:
        raise ValueError('Choose one concern for this brief.')
    episode = require_episode(connection, owner, episode_id)
    try:
        start, end = date.fromisoformat(payload.get('start', '')), date.fromisoformat(payload.get('end', ''))
    except (ValueError, TypeError):
        raise ValueError('Choose valid start and end dates.') from None
    if end < start:
        raise ValueError('The end date must follow the start date.')
    questions = payload.get('questions', '')
    if not isinstance(questions, str) or len(questions) > 3000:
        raise ValueError('Use personal questions up to 3,000 characters.')
    def linked(kind, identifier):
        return data['links'].get(kind + ':' + identifier, {}).get('episode_id') == episode_id
    def inside(value):
        return start.isoformat() <= str(value)[:10] <= end.isoformat()
    assessments = [r for r in data['assessments'] if linked('assessment', r['assessment_id']) and inside(r['created_at'])]
    selection = payload.get('assessment_ids')
    if selection is not None:
        if not isinstance(selection, list) or len(selection) > 1000 or any(not isinstance(v, str) for v in selection) or len(set(selection)) != len(selection):
            raise ValueError('Choose distinct saved assessments.')
        if not set(selection).issubset({r['assessment_id'] for r in assessments}):
            raise ValueError('A selected assessment is outside this concern or date range.')
        assessments = [r for r in assessments if r['assessment_id'] in selection]
    checkins = [r for r in data['checkins'] if linked('checkin', r['checkin_id']) and inside(r['checkin_date']) and not r.get('voided')]
    events = [r for r in data['events'] if r.get('episode_id') == episode_id and inside(r['date'])]
    routines = [r for r in data['routines'] if linked('routine', r['routine_id']) and str(r['start_date'])[:10] <= end.isoformat()]
    if len(assessments) + len(checkins) + len(events) > 1000:
        raise ValueError('This brief has more than 1,000 records. Narrow the date range or assessment selection; no records were omitted silently.')
    return dict(episode_id=episode_id, episode=episode, start=start.isoformat(), end=end.isoformat(), timezone='UTC for assessment save times; check-ins and actions use their recorded local dates', assessments=assessments, checkins=checkins, events=events, routines=routines, questions=questions.strip(), counts=dict(assessments=len(assessments), checkins=len(checkins), routine_actions=len(events), routines=len(routines)), photo_notice='Original photographs and overlays are unavailable because the app does not retain them. Recorded findings and self-reports are not confirmed diagnoses.')


def register_continuity(app, database, current_user, read_summary, score):
    bp = Blueprint('consumer_continuity', __name__)

    @contextmanager
    def owned():
        connection = database()
        try:
            user = current_user(connection)
            if not user:
                raise Unauthorized('Sign in to use your private records.')
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
            return jsonify(error='Consumer development features are unavailable.'), 503

    @bp.post('/api/corrections/<kind>/<identifier>')
    def correct(kind, identifier):
        payload, key = json_object(), request_key()
        if kind not in {'event', 'checkin'} or type(payload.get('revision')) is not int:
            raise ValueError('Choose a record and its current revision.')
        reason = payload.get('reason', '')
        if not isinstance(reason, str) or len(reason) > 500:
            raise ValueError('Use a reason up to 500 characters.')
        with owned() as (connection, user):
            owner = user['id']; lock_owner(connection, owner)
            with connection.cursor() as cursor:
                if kind == 'event':
                    cursor.execute("SELECT record_id AS id,data_json FROM consumer_records WHERE user_id=%s AND kind='routine_event' AND record_id=%s FOR UPDATE", (owner, identifier))
                    row = cursor.fetchone()
                    original = dict(id=row['id'], **json.loads(row['data_json'])) if row else None
                    action = payload.get('action')
                    if action not in {'completed', 'skipped', 'pending'}:
                        raise ValueError('Choose completed, skipped or not recorded.')
                    effective = dict(action=action)
                else:
                    cursor.execute('SELECT checkin_id,checkin_date,reported_trend,discomfort_score,change_score,priority_score,note FROM progress_checkins WHERE user_id=%s AND checkin_id=%s FOR UPDATE', (owner, identifier))
                    original = cursor.fetchone()
                    effective = dict(voided=True) if payload.get('voided') is True else checkin_values(payload, score)
                if not original:
                    raise NotFound('Record not found in this account.')
                rows = effective_records(connection, owner, kind, [original], 'id' if kind == 'event' else 'checkin_id', lock=True)
                data = dict(effective=effective, previous_revision=payload['revision'], actor_id=owner, reason=reason.strip(), contract='correction-v1')
                cursor.execute('SELECT record_id,subject_id,data_json FROM consumer_records WHERE user_id=%s AND dedupe_key=%s FOR UPDATE', (owner, digest(f'{owner}:{kind}_correction:{key}')))
                replay = cursor.fetchone()
                if replay:
                    if replay['subject_id'] != identifier or json.loads(replay['data_json']) != data:
                        raise Conflict('This retry identifier belongs to a different correction.')
                    return jsonify(correction_id=replay['record_id'], replayed=True, message='Correction already saved; original preserved.')
                if payload['revision'] != rows[0]['revision']:
                    raise Conflict('This record changed in another tab. Reload before correcting it.')
                saved = record(connection, owner, kind + '_correction', identifier, data, key)
            return jsonify(correction_id=saved['record_id'], revision=payload['revision'] + 1, message='Correction saved. The original record is preserved.')

    @bp.route('/api/episodes', methods=['GET', 'POST'])
    def episodes():
        with owned() as (connection, user):
            owner = user['id']
            if request.method == 'GET':
                return jsonify(episodes=[dict(episode_id=r['id'], **r['data'], created_at=r['created_at']) for r in reversed(records(connection, owner, 'concern_episode'))], body_areas=BODY_AREAS)
            payload, key = json_object(), request_key()
            label, area, body = payload.get('label'), payload.get('area'), payload.get('body_area', 'Unspecified')
            if not isinstance(label, str) or not 1 <= len(label.strip()) <= 120 or area not in AREAS or body not in BODY_AREAS:
                raise ValueError('Choose a concern label, category and body area.')
            lock_owner(connection, owner)
            data = dict(label=label.strip(), area=area, body_area=body, contract='concern-episode-v1')
            saved = record(connection, owner, 'concern_episode', '', data, key)
            if json.loads(saved['data_json']) != data:
                raise Conflict('This retry identifier was used for another concern.')
            return jsonify(episode_id=saved['record_id'], **data), 201

    @bp.put('/api/episode-links/<entity>/<identifier>')
    def associate(entity, identifier):
        payload = json_object()
        if not isinstance(payload.get('episode_id', ''), str) or type(payload.get('version')) is not int:
            raise ValueError('Choose a concern and the current association version.')
        with owned() as (connection, user):
            lock_owner(connection, user['id'])
            return jsonify(link=link_episode(connection, user['id'], entity, identifier, payload.get('episode_id', ''), payload['version']))

    @bp.get('/api/episode-links')
    def associations():
        with owned() as (connection, user):
            return jsonify(links=episode_links(connection, user['id']))

    @bp.get('/api/checkins/<identifier>')
    def checkin_detail(identifier):
        with owned() as (connection, user):
            with connection.cursor() as cursor:
                cursor.execute('SELECT c.id,c.checkin_id,c.routine_id,c.checkin_date,c.reported_trend,c.discomfort_score,c.change_score,c.priority_score,c.note,r.routine_name FROM progress_checkins c JOIN care_routines r ON r.routine_id=c.routine_id AND r.user_id=c.user_id WHERE c.user_id=%s AND c.checkin_id=%s', (user['id'], identifier))
                row = cursor.fetchone()
            if not row:
                raise NotFound('Check-in not found in this account.')
            result = effective_checkins(connection, user['id'], [row])[0]
            result['checkin_date'] = str(result['checkin_date'])[:10]
            return jsonify(checkin=result, episode_link=episode_links(connection, user['id']).get('checkin:' + identifier, {}))

    @bp.post('/api/reminders/preview')
    def preview():
        from consumer_engagement import schedule_payload
        from delivery import delivery_mode
        with owned():
            return jsonify(preview=reminder_preview(schedule_payload(json_object())), transport=delivery_mode(), delivery_verified=False)

    @bp.route('/api/bookmarks/<guide_id>', methods=['PUT', 'DELETE'])
    def bookmark(guide_id):
        from condition_knowledge import educational_condition_topic
        topic = educational_condition_topic(guide_id)
        if not topic:
            raise NotFound('Guide not found.')
        with owned() as (connection, user):
            owner = user['id']; lock_owner(connection, owner)
            existing = records(connection, owner, 'guide_bookmark', guide_id, lock=True)
            previous = existing[0]['data'] if existing else {}
            version = (json_object() if request.method == 'PUT' else request.args).get('version')
            if request.method == 'PUT' and type(version) is not int:
                raise ValueError('Use the current integer bookmark version.')
            try:
                version = int(version)
            except (ValueError, TypeError):
                raise ValueError('Reload saved guides before editing a bookmark.') from None
            retry = request_key() if request.headers.get('Idempotency-Key') else ''
            if retry and previous.get('last_request') == digest(retry):
                if previous['saved'] != (request.method == 'PUT') or previous.get('request_version') != version:
                    raise Conflict('This retry identifier belongs to another bookmark action.')
                return jsonify(bookmark=previous, message='Guide saved.' if previous['saved'] else 'Bookmark removed.')
            if version != previous.get('version', 0):
                raise Conflict('This bookmark changed. Reload saved guides.')
            data = dict(saved=request.method == 'PUT', guide_id=guide_id, title=topic['name'], content_version=topic.get('version'), content_date=topic.get('last_reviewed'), sources=topic.get('evidence_references', []), version=version + 1)
            if retry:
                data.update(last_request=digest(retry), request_version=version)
            key = digest(f'{owner}:guide_bookmark:{guide_id}')
            with connection.cursor() as cursor:
                cursor.execute('INSERT INTO consumer_records(record_id,user_id,kind,subject_id,dedupe_key,data_json,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP(),UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE data_json=VALUES(data_json),updated_at=UTC_TIMESTAMP()', ('bookmark-' + key[:32], owner, 'guide_bookmark', guide_id, key, json.dumps(data)))
            record(connection, owner, 'bookmark_revision', guide_id, data)
            return jsonify(bookmark=data, message='Guide saved.' if data['saved'] else 'Bookmark removed.')

    @bp.get('/api/bookmarks')
    def bookmarks():
        with owned() as (connection, user):
            return jsonify(bookmarks=[r['data'] for r in records(connection, user['id'], 'guide_bookmark')])

    @bp.post('/api/feedback')
    def feedback():
        payload, key = json_object(), request_key()
        category, page, note = payload.get('category'), payload.get('page'), payload.get('note', '')
        if category not in {'Confusing screen', 'Save or loading problem', 'Accessibility', 'Other'} or page not in {'Today', 'Check', 'Journey', 'Learn', 'Profile'} or not isinstance(note, str) or len(note) > 2000:
            raise ValueError('Choose a category, page and optional explanation up to 2,000 characters.')
        with owned() as (connection, user):
            data = dict(category=category, page=page, note=note.strip(), app_version='consumer-continuity-v1', status='collected_locally_unmonitored')
            saved = record(connection, user['id'], 'product_feedback', '', data, key)
            if json.loads(saved['data_json']) != data:
                raise Conflict('This retry identifier belongs to different feedback.')
            return jsonify(feedback_id=saved['record_id'], status=data['status'], message='Feedback saved in your local account. No monitored support channel is configured; this is not an urgent-care or support service.'), 201

    @bp.post('/api/visit-brief')
    def brief():
        from account_data_export import begin_account_data_snapshot
        from report_service import build_visit_brief_pdf
        payload = json_object()
        with owned() as (connection, user):
            # End authentication reads, then use one stable read-only snapshot.
            connection.commit(); begin_account_data_snapshot(connection)
            result = visit_brief(continuity_data(connection, user['id'], read_summary), payload, user['id'], connection)
            if payload.get('format') == 'pdf':
                return send_file(io.BytesIO(build_visit_brief_pdf(result)), mimetype='application/pdf', as_attachment=True, download_name='dermamatrix-visit-brief.pdf', max_age=0)
            # Do not duplicate raw historical JSON in a compact preview.
            for row in result['assessments']:
                row.pop('result_json', None)
            return jsonify(brief=result)

    @bp.get('/api/search')
    def search():
        from condition_knowledge import educational_condition_catalog
        query, category = request.args.get('q', '').strip(), request.args.get('category', '')
        allowed = {'assessment', 'episode', 'routine', 'checkin', 'guide'}
        if len(query) > 120 or category and category not in allowed:
            raise ValueError('Use a search up to 120 characters and a supported category.')
        serializer = URLSafeTimedSerializer(current_app.secret_key, salt='consumer-search-v1')
        connection = database() if session.get('user_id') else None
        try:
            user = current_user(connection) if connection else None
            owner = user['id'] if user else None
            items = []
            snapshot = 0
            if owner and category != 'guide':
                with connection.cursor() as cursor:
                    cursor.execute('SELECT COALESCE(MAX(id),0) AS maximum FROM consumer_records WHERE user_id=%s', (owner,))
                    snapshot = cursor.fetchone()['maximum']
                data = continuity_data(connection, owner, read_summary)
                for kind, rows, key, title in [('assessment', data['assessments'], 'assessment_id', lambda r: r['area'] + ' assessment'), ('routine', data['routines'], 'routine_id', lambda r: r['routine_name']), ('checkin', data['checkins'], 'checkin_id', lambda r: ('Removed from current tracking' if r.get('voided') else r['reported_trend']) + ' - self-reported check-in')]:
                    for row in rows:
                        link = data['links'].get(kind + ':' + row[key], {})
                        content = json.dumps({k:v for k,v in row.items() if k not in {'original', 'corrections'}}, default=str)
                        if query.casefold() in (content + json.dumps(link)).casefold():
                            items.append(dict(category=kind, id=row[key], title=title(row), detail=link.get('label', ''), created_at=str(row['created_at']), revision=row.get('revision', 0), episode_id=link.get('episode_id', '')))
                for row in data['episodes']:
                    if query.casefold() in json.dumps(row['data']).casefold():
                        items.append(dict(category='episode', id=row['id'], title=row['data']['label'], detail=row['data']['body_area'], created_at=str(row['created_at'])))
            saved = {r['subject_id']: r['data'] for r in records(connection, owner, 'guide_bookmark')} if owner else {}
            for guide in educational_condition_catalog():
                if query.casefold() in (guide['name'] + ' '.join(guide.get('aliases', []))).casefold():
                    items.append(dict(category='guide', id=guide['id'], title=guide['name'], detail=guide['health_area'], created_at='', bookmarked=bool(saved.get(guide['id'], {}).get('saved'))))
            items = [r for r in items if not category or r['category'] == category]
            items.sort(key=lambda r: (r['created_at'], r['category'], r['id']), reverse=True)
            token = request.args.get('cursor')
            if token:
                try:
                    state = serializer.loads(token, max_age=3600)
                    if state['owner'] != owner or state['q'] != query or state['category'] != category:
                        raise BadSignature('Changed scope')
                    if state['snapshot'] != snapshot:
                        raise Conflict('Your records changed. Start this search again to see the current information.')
                    items = [r for r in items if (r['created_at'], r['category'], r['id']) < tuple(state['before'])]
                except (BadSignature, KeyError, TypeError):
                    raise ValueError('This search page expired or changed. Start your search again.') from None
            page = items[:20]
            cursor = serializer.dumps(dict(owner=owner, q=query, category=category, snapshot=snapshot, before=[page[-1]['created_at'], page[-1]['category'], page[-1]['id']])) if len(items) > 20 else None
            return jsonify(results=page, next_cursor=cursor, private_results=bool(owner), meaning='Private records are scoped to the signed-in account; educational guides are public.')
        finally:
            if connection:
                connection.close()

    @bp.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error), code='INVALID_INPUT'), 400

    app.register_blueprint(bp)
