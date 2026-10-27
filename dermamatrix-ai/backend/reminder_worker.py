"""Explicit bounded reminder worker. Payloads contain IDs/time, never photos.

No worker starts with the web server. Run the CLI deliberately with a configured
transport. SMTP acceptance is not confirmed delivery. Ambiguous sends are held
for review instead of automatically duplicating potentially accepted messages.
"""
from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo

from consumer_engagement import get_schedule, local_occurrences
from consumer_security import digest, utcnow
from delivery import delivery_mode, send_message, DeliveryUnavailable


def plan(connection, at=None):
    at = at or utcnow()
    count = 0
    with connection.cursor() as cursor:
        cursor.execute("SELECT r.routine_id,r.user_id,r.start_date,s.data_json FROM care_routines r JOIN consumer_records s ON s.subject_id=r.routine_id AND s.user_id=r.user_id AND s.kind='routine_schedule' JOIN users u ON u.id=r.user_id WHERE u.is_active=TRUE ORDER BY s.id LIMIT 1000")
        schedules = cursor.fetchall()
        for row in schedules:
            config = json.loads(row['data_json'])
            if config['status'] != 'active' or not config['reminders']:
                continue
            from datetime import timezone
            local_day = at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(config['timezone'])).date()
            for offset in [0, 1]:
                day = local_day + timedelta(days=offset)
                if day.isoformat() < str(row['start_date'])[:10]:
                    continue
                for due in local_occurrences(config, day):
                    # No stale catch-up notifications after a day without a worker.
                    if not at - timedelta(minutes=10) <= due <= at + timedelta(days=1):
                        continue
                    identifier = digest(f"{row['user_id']}:{row['routine_id']}:{config['version']}:{due.isoformat()}")
                    cursor.execute('INSERT IGNORE INTO reminder_jobs(job_id,user_id,routine_id,due_at,available_at,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s)', (identifier, row['user_id'], row['routine_id'], due, due, at, at))
                    count += cursor.rowcount
    connection.commit()
    return count


def run_due(connection, *, at=None, limit=25):
    at = at or utcnow()
    processed = []
    with connection.cursor() as cursor:
        # Crash-after-handoff is ambiguous. Do not auto-redeliver expired leases.
        cursor.execute("UPDATE reminder_jobs SET state='uncertain',updated_at=%s WHERE state='sending' AND lease_until<%s", (at, at))
    connection.commit()
    for _ in range(min(max(limit, 1), 100)):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM reminder_jobs WHERE state IN ('scheduled','retry') AND available_at<=%s ORDER BY available_at,job_id LIMIT 1 FOR UPDATE SKIP LOCKED", (at,))
            job = cursor.fetchone()
            if not job:
                connection.rollback(); break
            cursor.execute("UPDATE reminder_jobs SET state='sending',attempts=attempts+1,lease_until=%s,updated_at=%s WHERE job_id=%s", (at + timedelta(minutes=2), at, job['job_id']))
        connection.commit()
        state, reference = 'failed', None
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT u.email_address,u.is_active,s.processing_paused,s.email_verified_at,p.notifications_enabled FROM users u LEFT JOIN account_security s ON s.user_id=u.id LEFT JOIN user_preferences p ON p.user_id=u.id WHERE u.id=%s FOR UPDATE', (job['user_id'],))
                user = cursor.fetchone()
                config = get_schedule(cursor, job['user_id'], job['routine_id'])
                cursor.execute('SELECT routine_id FROM care_routines WHERE user_id=%s AND routine_id=%s', (job['user_id'], job['routine_id']))
                routine = cursor.fetchone()
                expected = digest(f"{job['user_id']}:{job['routine_id']}:{config['version']}:{job['due_at'].isoformat()}") if config else ''
                if not user or not user['is_active'] or user['processing_paused'] or not user['notifications_enabled'] or not routine or not config or config['status'] != 'active' or not config['reminders'] or expected != job['job_id'] or at - job['due_at'] > timedelta(minutes=30):
                    state = 'cancelled'
                elif not user['email_verified_at']:
                    state = 'blocked_unverified'
                elif delivery_mode() == 'disabled':
                    state = 'blocked_provider'
                else:
                    result = send_message(user['email_address'], 'Your DermaMatrix reminder', 'You chose a reminder. Open your DermaMatrix workspace when convenient. You can pause reminders in your routine settings.', message_id=job['job_id'])
                    state, reference = result['state'], result['reference']
                cursor.execute('UPDATE reminder_jobs SET state=%s,provider_reference=%s,lease_until=NULL,updated_at=%s WHERE job_id=%s AND state=\'sending\'', (state, reference, at, job['job_id']))
            connection.commit()
        except DeliveryUnavailable:
            connection.rollback()
            # SMTP failures may happen after acceptance. Explicit operator review
            # avoids pretending that a retry is guaranteed not to duplicate.
            state = 'uncertain' if delivery_mode() == 'smtp' else ('retry' if job['attempts'] < 2 else 'failed')
            with connection.cursor() as cursor:
                cursor.execute('UPDATE reminder_jobs SET state=%s,available_at=%s,lease_until=NULL,updated_at=%s WHERE job_id=%s AND state=\'sending\'', (state, at + timedelta(minutes=5), at, job['job_id']))
            connection.commit()
        processed.append({'job_id': job['job_id'], 'state': state})
    return processed
