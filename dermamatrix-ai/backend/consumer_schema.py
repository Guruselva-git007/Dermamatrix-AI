"""Explicit, additive consumer migrations. Never run from normal app startup."""
from __future__ import annotations

VERSION = '20261027_consumer_v2'
STATEMENTS = [
'''CREATE TABLE IF NOT EXISTS account_mail_jobs (
 job_id CHAR(32) PRIMARY KEY, user_id BIGINT NULL, purpose VARCHAR(30) NOT NULL,
 target_email VARCHAR(254) NULL, state VARCHAR(24) NOT NULL DEFAULT 'queued',
 created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
 INDEX idx_mail_pending(state,created_at), FOREIGN KEY(user_id) REFERENCES users(id)) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS account_security (
 user_id BIGINT PRIMARY KEY, email_verified_at DATETIME NULL,
 processing_paused BOOLEAN NOT NULL DEFAULT FALSE,
 updated_at DATETIME NOT NULL,
 FOREIGN KEY(user_id) REFERENCES users(id)) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS account_sessions (
 session_id CHAR(64) PRIMARY KEY, user_id BIGINT NOT NULL,
 device_label VARCHAR(160) NOT NULL, created_at DATETIME NOT NULL,
 expires_at DATETIME NOT NULL, revoked BOOLEAN NOT NULL DEFAULT FALSE,
 INDEX idx_session_owner(user_id,revoked,expires_at),
 FOREIGN KEY(user_id) REFERENCES users(id)) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS account_tokens (
 token_hash CHAR(64) PRIMARY KEY, user_id BIGINT NOT NULL,
 purpose VARCHAR(30) NOT NULL, target_email VARCHAR(254) NOT NULL,
 expires_at DATETIME NOT NULL, consumed BOOLEAN NOT NULL DEFAULT FALSE,
 created_at DATETIME NOT NULL, INDEX idx_token_owner(user_id,purpose),
 FOREIGN KEY(user_id) REFERENCES users(id)) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS request_budgets (
 budget_key CHAR(64) PRIMARY KEY, window_start BIGINT NOT NULL,
 attempts INT NOT NULL, INDEX idx_budget_window(window_start)) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS consumer_records (
 id BIGINT PRIMARY KEY AUTO_INCREMENT, record_id VARCHAR(64) UNIQUE NOT NULL,
 user_id BIGINT NOT NULL, kind VARCHAR(30) NOT NULL, subject_id VARCHAR(64) NOT NULL,
 dedupe_key CHAR(64) UNIQUE NOT NULL, data_json LONGTEXT NOT NULL,
 created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
 INDEX idx_consumer_owner(user_id,kind,id), INDEX idx_consumer_subject(user_id,kind,subject_id),
 FOREIGN KEY(user_id) REFERENCES users(id)) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS reminder_jobs (
 job_id CHAR(64) PRIMARY KEY, user_id BIGINT NOT NULL, routine_id VARCHAR(50) NOT NULL,
 due_at DATETIME NOT NULL, state VARCHAR(24) NOT NULL DEFAULT 'scheduled',
 attempts INT NOT NULL DEFAULT 0, available_at DATETIME NOT NULL,
 lease_until DATETIME NULL, provider_reference VARCHAR(160) NULL,
 created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
 INDEX idx_reminder_due(state,available_at), INDEX idx_reminder_owner(user_id,due_at),
 FOREIGN KEY(user_id) REFERENCES users(id)) ENGINE=InnoDB''',
]


def migrate(connection):
    """Idempotent on interrupted DDL: each table is additive; no historical rewrite."""
    with connection.cursor() as cursor:
        cursor.execute('SELECT GET_LOCK(%s,10) AS acquired', ('dmx-consumer-schema',))
        if not cursor.fetchone()['acquired']:
            raise RuntimeError('Another migration is running.')
        try:
            cursor.execute('SELECT version FROM schema_migrations WHERE version=%s', (VERSION,))
            if cursor.fetchone():
                return False
            for statement in STATEMENTS:
                cursor.execute(statement)
            cursor.execute('CREATE INDEX idx_analysis_owner_id ON analysis_records(user_id,id)') if not _has_index(cursor) else None
            cursor.execute('INSERT INTO schema_migrations(version,applied_at) VALUES(%s,UTC_TIMESTAMP())', (VERSION,))
            connection.commit()
            return True
        finally:
            cursor.execute('SELECT RELEASE_LOCK(%s)', ('dmx-consumer-schema',))


def _has_index(cursor):
    cursor.execute("SELECT 1 FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='analysis_records' AND INDEX_NAME='idx_analysis_owner_id'")
    return cursor.fetchone() is not None
