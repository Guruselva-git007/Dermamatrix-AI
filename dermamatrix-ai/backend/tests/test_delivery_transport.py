"""Transport behaviour with synthetic addresses and mocked network connections."""
import os
import ssl
import unittest
from unittest.mock import patch
from delivery import DeliveryUnavailable, send_message


class DeliveryTransport(unittest.TestCase):
    def setUp(self):
        self.environment=patch.dict(os.environ,{'DERMAMATRIX_MAIL_TRANSPORT':'smtp','DERMAMATRIX_SMTP_HOST':'smtp.synthetic.invalid','DERMAMATRIX_MAIL_FROM':'sender@synthetic.invalid','DERMAMATRIX_SMTP_PORT':'465','DERMAMATRIX_SMTP_USER':'synthetic-user','DERMAMATRIX_SMTP_PASSWORD':'synthetic-secret'})
        self.environment.start();self.addCleanup(self.environment.stop)

    def test_smtp_requires_certificate_and_hostname_verification(self):
        with patch('delivery.smtplib.SMTP_SSL') as connection:
            smtp=connection.return_value.__enter__.return_value;smtp.send_message.return_value={}
            result=send_message('recipient@synthetic.invalid','Synthetic subject','Synthetic body')
            context=connection.call_args.kwargs['context']
            self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            smtp.login.assert_called_once_with('synthetic-user','synthetic-secret')
            self.assertEqual(result['state'],'provider_accepted')
            self.assertNotEqual(result['state'],'delivered')

    def test_invalid_certificate_does_not_fall_back_or_send(self):
        with patch('delivery.smtplib.SMTP_SSL',side_effect=ssl.SSLCertVerificationError('synthetic certificate mismatch')) as connection:
            with self.assertRaises(DeliveryUnavailable) as error:
                send_message('recipient@synthetic.invalid','Subject','Synthetic body')
            self.assertNotIn('synthetic-secret',str(error.exception));connection.assert_called_once()

    def test_rejected_recipient_is_not_success(self):
        with patch('delivery.smtplib.SMTP_SSL') as connection:
            connection.return_value.__enter__.return_value.send_message.return_value={'recipient@synthetic.invalid':(550,b'rejected')}
            with self.assertRaises(DeliveryUnavailable):send_message('recipient@synthetic.invalid','Subject','Body')

    def test_disabled_transport_makes_no_network_request(self):
        with patch.dict(os.environ,{'DERMAMATRIX_MAIL_TRANSPORT':'disabled'}),patch('delivery.smtplib.SMTP_SSL') as connection:
            with self.assertRaises(DeliveryUnavailable):send_message('recipient@synthetic.invalid','Subject','Body')
            connection.assert_not_called()
