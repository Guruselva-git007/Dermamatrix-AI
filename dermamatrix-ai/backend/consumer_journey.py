"""Read-only consumer activity and explicit, version-aware record comparison."""
from datetime import date, datetime, timezone
import json
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request
from itsdangerous import URLSafeTimedSerializer, BadSignature
from werkzeug.exceptions import Conflict, NotFound

from account_data_export import begin_account_data_snapshot
from consumer_security import json_object
from consumer_continuity import effective_checkins, effective_events, require_episode, utc_iso
from longitudinal_service import build_progress_comparison

PAGE_SIZE = 20


def date_scope(arguments):
    start, end = arguments.get('start', ''), arguments.get('end', '')
    try:
        if start:
            date.fromisoformat(start)
        if end:
            date.fromisoformat(end)
    except (TypeError, ValueError):
        raise ValueError('Choose valid dates.') from None
    if start and end and end < start:
        raise ValueError('The end date must follow the start date.')
    return start or '0001-01-01', end or '9999-12-31'


def assessment_title(summary, area):
    summary = summary or {}
    return ((summary.get('assessment_result') or {}).get('consumer') or {}).get('primary_result', {}).get('title') or (summary.get('screening') or {}).get('title') or area + ' assessment'


def routine_day(revisions, events, day, start_date, now):
    """Project immutable plan intervals and effective events; never infer adherence."""
    from consumer_engagement import local_occurrences
    slots = {}
    for index, revision in enumerate(revisions):
        config = revision['data']
        end = revisions[index + 1]['created_at'] if index + 1 < len(revisions) else datetime.max
        if day < start_date:
            continue
        for occurrence in local_occurrences(config, day):
            if not revision['created_at'] <= occurrence < end:
                continue
            clock = occurrence.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(config['timezone'])).strftime('%H:%M')
            for step, label in enumerate(config['steps']):
                key = (config['version'], clock, step)
                slots[key] = dict(step_text=label, time=clock, timezone=config['timezone'],
                                  schedule_version=config['version'], state='unrecorded' if occurrence <= now else 'scheduled',
                                  occurrence_utc=occurrence.isoformat() + 'Z', event_id=None, revision=0)
    for event in events:
        key = (event['schedule_version'], event['time'], event['step'])
        slot = slots.get(key, dict(step_text=event['step_text'], time=event['time'], timezone=event['timezone'],
                                  schedule_version=event['schedule_version'], occurrence_utc='', recorded_outside_plan=True))
        slot.update(state=event['action'] if event['action'] in {'completed', 'skipped'} else slot.get('state', 'unrecorded'),
                    event_id=event['id'], revision=event.get('revision', 0))
        slots[key] = slot
    return sorted(slots.values(), key=lambda row: (row['time'], row['schedule_version'], row['step_text']))


def register_journey(bp, owned, read_summary):
    @bp.get('/api/journey/routines/<routine_id>/day')
    def day_view(routine_id):
        try:
            day = date.fromisoformat(request.args.get('date', ''))
        except (ValueError, TypeError):
            raise ValueError('Choose a valid routine date.') from None
        with owned() as (connection, user):
            connection.commit()
            begin_account_data_snapshot(connection)
            with connection.cursor() as cursor:
                cursor.execute('SELECT routine_name,start_date FROM care_routines WHERE user_id=%s AND routine_id=%s', (user['id'], routine_id))
                routine = cursor.fetchone()
                if not routine:
                    raise NotFound('Routine not found in this account.')
                cursor.execute("SELECT data_json,created_at FROM consumer_records WHERE user_id=%s AND kind='routine_revision' AND subject_id=%s ORDER BY id LIMIT 501", (user['id'], routine_id))
                rows = cursor.fetchall()
                if len(rows) > 500:
                    raise Conflict('This routine has more plan revisions than this daily view can read. Use its recorded activity journal.')
                revisions = [dict(data=json.loads(row['data_json']), created_at=row['created_at']) for row in rows]
                cursor.execute("SELECT record_id,data_json,created_at FROM consumer_records WHERE user_id=%s AND kind='routine_event' AND subject_id=%s AND JSON_UNQUOTE(JSON_EXTRACT(data_json,'$.date'))=%s ORDER BY id LIMIT 401", (user['id'], routine_id, day.isoformat()))
                rows = cursor.fetchall()
                if len(rows) > 400:
                    raise Conflict('This date has too many recorded actions for the daily view. Use the paginated activity journal.')
                events = effective_events(connection, user['id'], [dict(id=row['record_id'], **json.loads(row['data_json'])) for row in rows])
            return jsonify(date=day.isoformat(), routine=routine['routine_name'], slots=routine_day(revisions, events, day, routine['start_date'], datetime.now(timezone.utc).replace(tzinfo=None)),
                           meaning='Scheduled means a future planned occurrence; unrecorded means no current completion or skip is recorded. Neither proves a missed routine. Times use each saved plan’s timezone. Quiet hours and nonexistent DST times are excluded.',
                           history_available=bool(revisions))

    @bp.get('/api/journey/activity')
    def activity():
        scope = {key: request.args.get(key, '') for key in ('episode_id', 'routine_id', 'kind', 'start', 'end')}
        if any(len(value) > 100 for value in scope.values()) or scope['kind'] not in {'', 'assessment', 'checkin', 'event'}:
            raise ValueError('Choose a supported activity scope.')
        start, end = date_scope(scope)
        serializer = URLSafeTimedSerializer(current_app.secret_key, salt='consumer-activity-v1')
        with owned() as (connection, user):
            owner = user['id']
            connection.commit()
            begin_account_data_snapshot(connection)
            if scope['episode_id'] and scope['episode_id'] != 'unassigned':
                require_episode(connection, owner, scope['episode_id'])
            with connection.cursor() as cursor:
                if scope['routine_id']:
                    cursor.execute('SELECT routine_id FROM care_routines WHERE user_id=%s AND routine_id=%s', (owner, scope['routine_id']))
                    if not cursor.fetchone():
                        raise NotFound('Routine not found in this account.')
                cursor.execute("""SELECT
                    (SELECT COALESCE(MAX(id),0) FROM consumer_records WHERE user_id=%s) AS revisions,
                    (SELECT COALESCE(MAX(id),0) FROM analysis_records WHERE user_id=%s) AS assessments,
                    (SELECT COALESCE(MAX(id),0) FROM progress_checkins WHERE user_id=%s) AS checkins""", (owner, owner, owner))
                snapshot = cursor.fetchone()
                before = None
                if request.args.get('cursor'):
                    try:
                        token = serializer.loads(request.args['cursor'], max_age=3600)
                        if token['owner'] != owner or token['scope'] != scope:
                            raise BadSignature('Scope changed')
                        if token['snapshot'] != snapshot:
                            raise Conflict('Your records changed. Refresh this activity view.')
                        before = token['before']
                        if not isinstance(before, list) or len(before) != 3:
                            raise BadSignature('Invalid cursor')
                    except (BadSignature, KeyError, TypeError):
                        raise ValueError('This activity page expired. Refresh the view.') from None
                items = []
                for kind in ('assessment', 'checkin', 'event'):
                    if scope['kind'] and kind != scope['kind'] or scope['routine_id'] and kind == 'assessment':
                        continue
                    conditions, values = ['r.user_id=%s'], [owner]
                    if kind == 'event':
                        table, identifier = 'consumer_records', 'record_id'
                        day = "JSON_UNQUOTE(JSON_EXTRACT(r.data_json,'$.date'))"
                        conditions.append("r.kind='routine_event'")
                        if scope['episode_id']:
                            episode = "JSON_UNQUOTE(JSON_EXTRACT(r.data_json,'$.episode_id'))"
                            if scope['episode_id'] == 'unassigned':
                                conditions.append(f"COALESCE({episode},'')=''")
                            else:
                                conditions.append(f'{episode}=%s')
                                values.append(scope['episode_id'])
                    else:
                        table, identifier = ('analysis_records', 'assessment_id') if kind == 'assessment' else ('progress_checkins', 'checkin_id')
                        day = "DATE_FORMAT(r.created_at,'%%Y-%%m-%%d')" if kind == 'assessment' else """COALESCE(
                            (SELECT JSON_UNQUOTE(JSON_EXTRACT(c.data_json,'$.effective.checkin_date'))
                             FROM consumer_records c WHERE c.user_id=r.user_id AND c.kind='checkin_correction'
                               AND c.subject_id=r.checkin_id AND JSON_CONTAINS_PATH(c.data_json,'one','$.effective.checkin_date')
                             ORDER BY c.id DESC LIMIT 1), DATE_FORMAT(r.checkin_date,'%%Y-%%m-%%d'))"""
                        if scope['episode_id']:
                            exists = f"""EXISTS (SELECT 1 FROM consumer_records l WHERE l.user_id=r.user_id
                                AND l.kind='episode_link' AND l.subject_id=CONCAT('{kind}:',r.{identifier})
                                AND COALESCE(JSON_UNQUOTE(JSON_EXTRACT(l.data_json,'$.episode_id')),'')"""
                            if scope['episode_id'] == 'unassigned':
                                conditions.append('NOT ' + exists + "!='')")
                            else:
                                conditions.append(exists + '=%s)')
                                values.append(scope['episode_id'])
                    if scope['routine_id']:
                        conditions.append('r.' + ('subject_id' if kind == 'event' else 'routine_id') + '=%s')
                        values.append(scope['routine_id'])
                    conditions.append(f'{day} BETWEEN %s AND %s')
                    values.extend([start, end])
                    if before:
                        conditions.append(f'({day},%s,r.id)<(%s,%s,%s)')
                        values.extend([kind, *before])
                    cursor.execute(f"SELECT r.*, {day} AS recorded_date FROM {table} r WHERE " + ' AND '.join(conditions) + f' ORDER BY recorded_date DESC,r.id DESC LIMIT {PAGE_SIZE + 1}', tuple(values))
                    rows = cursor.fetchall()
                    if kind == 'checkin':
                        rows = effective_checkins(connection, owner, rows)
                    if kind == 'event':
                        rows = effective_events(connection, owner, [dict(sequence=row['id'], id=row['record_id'], recorded_date=row['recorded_date'], created_at=row['created_at'], **json.loads(row['data_json'])) for row in rows])
                    for row in rows:
                        summary = read_summary(row['result_json']) if kind == 'assessment' else None
                        title = assessment_title(summary, row['area']) if kind == 'assessment' else (
                            row.get('step_text', 'Routine action') if kind == 'event' else
                            ('Removed from current tracking' if row.get('voided') else row['reported_trend'] + ' — self-reported'))
                        item = dict(kind=kind, id=row[identifier] if kind != 'event' else row['id'],
                                    sequence=row['sequence'] if kind == 'event' else row['id'],
                                    recorded_date=str(row['recorded_date'])[:10], saved_at=utc_iso(row['created_at']),
                                    title=title, revision=row.get('revision', 0),
                                    corrections=row.get('corrections', []), original=row.get('original'),
                                    detail=row.get('note') or (row.get('date','') + ' ' + row.get('time','') + ' ' + row.get('timezone','') if kind == 'event' else ''),
                                    action=row.get('action'), voided=row.get('voided', False),
                                    area=row.get('area'), unavailable=kind == 'assessment' and summary is None)
                        # The original projection contains only the selected record, never source pixels.
                        if item['original']:
                            item['original'] = {key: item['original'].get(key) for key in ('checkin_date','reported_trend','note','action','date','time','timezone') if key in item['original']}
                        items.append(item)
            items.sort(key=lambda item: (item['recorded_date'], item['kind'], item['sequence']), reverse=True)
            more, page = len(items) > PAGE_SIZE, items[:PAGE_SIZE]
            cursor = serializer.dumps(dict(owner=owner, scope=scope, snapshot=snapshot,
                before=[page[-1]['recorded_date'], page[-1]['kind'], page[-1]['sequence']])) if more else None
            return jsonify(activity=page, next_cursor=cursor, meaning='Assessment save dates use UTC. Check-ins and routine actions use their recorded local dates.')

    @bp.post('/api/journey/compare')
    def compare():
        payload = json_object()
        identifiers = payload.get('assessment_ids')
        if not isinstance(identifiers, list) or len(identifiers) != 2 or any(not isinstance(value, str) or not 1 <= len(value) <= 80 for value in identifiers) or len(set(identifiers)) != 2:
            raise ValueError('Choose two distinct saved assessments.')
        with owned() as (connection, user):
            connection.commit()
            begin_account_data_snapshot(connection)
            with connection.cursor() as cursor:
                cursor.execute("""SELECT a.assessment_id,a.area,a.created_at,a.result_json,l.data_json AS link_json
                    FROM analysis_records a LEFT JOIN consumer_records l ON l.user_id=a.user_id
                    AND l.kind='episode_link' AND l.subject_id=CONCAT('assessment:',a.assessment_id)
                    WHERE a.user_id=%s AND a.assessment_id IN (%s,%s) ORDER BY a.created_at,a.id""", (user['id'], *identifiers))
                rows = cursor.fetchall()
            if len(rows) != 2:
                raise NotFound('Choose assessments from this account.')
            links = [json.loads(row['link_json'] or '{}').get('episode_id') for row in rows]
            if not links[0] or links[0] != links[1] or rows[0]['area'] != rows[1]['area']:
                raise ValueError('Choose two assessments linked to the same concern and health area.')
            concern = require_episode(connection, user['id'], links[0])
            summaries = []
            views = []
            for row in rows:
                summary = read_summary(row['result_json'])
                if summary is None:
                    raise Conflict('One original record is unreadable. Open its history for available information.')
                saved = dict(summary, assessment_id=row['assessment_id'], created_at=utc_iso(row['created_at']))
                summaries.append(saved)
                result = summary.get('assessment_result') or {}
                canonical = result.get('canonical_evidence') or summary.get('canonical_evidence') or {}
                risk = canonical.get('assessment_risk') or summary.get('assessment_risk') or result.get('assessment_risk') or summary.get('risk') or {}
                classifier = summary.get('classification') or summary.get('research_classifier') or {}
                views.append(dict(assessment_id=row['assessment_id'], area=row['area'], created_at=utc_iso(row['created_at']),
                    title=assessment_title(summary,row['area']), status=result.get('status') or {},
                    context=summary.get('manual_context') or {}, inputs=summary.get('patient_context') or {},
                    indicator=risk, model_id=classifier.get('model_id'), model_version=classifier.get('model_version'),
                    pipeline_version=classifier.get('pipeline_version'), calibration_version=(classifier.get('calibration') or {}).get('calibration_version')))
            comparison = build_progress_comparison(user_id=user['id'], area=rows[1]['area'], current=summaries[1], historical=[dict(assessment_id=rows[0]['assessment_id'], created_at=utc_iso(rows[0]['created_at']), summary=summaries[0])], historical_count=1)
            return jsonify(concern=concern, records=views, comparison=comparison,
                           meaning='Recorded values and self-reports support discussion. Differences do not establish healing or treatment effectiveness.')
