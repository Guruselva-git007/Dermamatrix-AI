"""Bounded recovery email worker. Queue entries contain no raw action token."""
from datetime import timedelta
from consumer_security import issue_token, utcnow
from delivery import DeliveryUnavailable


def process_account_messages(connection, limit=25):
    result=[]
    with connection.cursor() as cursor:
        cursor.execute("UPDATE account_mail_jobs SET state='uncertain',updated_at=UTC_TIMESTAMP() WHERE state='sending' AND updated_at<DATE_SUB(UTC_TIMESTAMP(),INTERVAL 2 MINUTE)")
    connection.commit()
    for _ in range(min(max(limit,1),100)):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM account_mail_jobs WHERE state='queued' ORDER BY created_at,job_id LIMIT 1 FOR UPDATE SKIP LOCKED")
            job=cursor.fetchone()
            if not job:
                connection.rollback();break
            cursor.execute("UPDATE account_mail_jobs SET state='sending',updated_at=UTC_TIMESTAMP() WHERE job_id=%s",(job['job_id'],))
        connection.commit()
        state='ignored'
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT a.email_address FROM auth_accounts a JOIN users u ON a.user_id=u.id WHERE a.user_id=%s AND u.is_active=TRUE',(job['user_id'],))
                user=cursor.fetchone()
            if job['created_at']<utcnow()-timedelta(minutes=30):
                state='expired'
            elif user and user['email_address']==job['target_email']:
                state=issue_token(connection,job['user_id'],job['purpose'],job['target_email'])['state']
        except DeliveryUnavailable:
            state='failed'
        with connection.cursor() as cursor:
            cursor.execute('UPDATE account_mail_jobs SET state=%s,updated_at=UTC_TIMESTAMP() WHERE job_id=%s',(state,job['job_id']))
        connection.commit();result.append(state)
    return result
