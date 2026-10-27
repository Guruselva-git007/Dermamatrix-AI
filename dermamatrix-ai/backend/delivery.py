"""Explicit email transport. Tokens appear only in intended email, never logs/API.

The development sink is a private mailbox containing synthetic test emails.
It must be explicitly configured outside served directories, and is forbidden
in production. SMTP uses verified implicit TLS and has no automatic fallback.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import smtplib
from email.message import EmailMessage
import uuid


class DeliveryUnavailable(RuntimeError):
    pass


def delivery_mode():
    mode = os.getenv('DERMAMATRIX_MAIL_TRANSPORT', 'disabled')
    return mode if mode in {'sink', 'smtp'} else 'disabled'


def send_message(recipient, subject, body, *, message_id=None):
    mode = delivery_mode()
    if mode == 'sink':
        if os.getenv('DERMAMATRIX_ENV', 'local') != 'test':
            raise DeliveryUnavailable('The isolated mailbox requires DERMAMATRIX_ENV=test.')
        folder = Path(os.environ.get('DERMAMATRIX_MAIL_SINK', '')).expanduser()
        if not folder.is_absolute() or not folder.is_dir() or 'frontend' in folder.parts:
            raise DeliveryUnavailable('Configure a private absolute test mailbox directory.')
        folder = folder.resolve()
        if 'frontend' in folder.parts:
            raise DeliveryUnavailable('The test mailbox must be outside served directories.')
        folder.chmod(0o700)
        reference = message_id or uuid.uuid4().hex
        if not reference.replace('-', '').isalnum():
            raise DeliveryUnavailable('Invalid delivery identifier.')
        destination = folder / (reference + '.json')
        # Exclusive creation gives the test transport deterministic deduplication.
        try:
            fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return {'state': 'sink_written', 'reference': reference}
        with os.fdopen(fd, 'w') as stream:
            json.dump({'to': recipient, 'subject': subject, 'body': body}, stream)
        return {'state': 'sink_written', 'reference': reference}
    if mode != 'smtp':
        raise DeliveryUnavailable('Email delivery is not configured. No email was sent.')
    try:
        host = os.environ['DERMAMATRIX_SMTP_HOST']
        sender = os.environ['DERMAMATRIX_MAIL_FROM']
        message = EmailMessage()
        message['From'] = sender; message['To'] = recipient; message['Subject'] = subject
        if message_id:
            message['Message-ID'] = f'<{message_id}@dermamatrix.local>'
        message.set_content(body)
        with smtplib.SMTP_SSL(host, int(os.getenv('DERMAMATRIX_SMTP_PORT', '465')), timeout=10) as smtp:
            if os.getenv('DERMAMATRIX_SMTP_USER'):
                smtp.login(os.environ['DERMAMATRIX_SMTP_USER'], os.environ['DERMAMATRIX_SMTP_PASSWORD'])
            rejected = smtp.send_message(message)
            if rejected:
                raise DeliveryUnavailable('Email was not accepted.')
        return {'state': 'provider_accepted', 'reference': message_id or ''}
    except (OSError, smtplib.SMTPException, KeyError, ValueError) as error:
        raise DeliveryUnavailable('Email could not be accepted. Retry later.') from error
