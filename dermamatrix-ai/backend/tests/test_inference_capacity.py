import unittest
from unittest.mock import MagicMock
from flask import Flask
import pymysql
from inference_capacity import bounded_inference


class InferenceCapacity(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__);self.app.config['CONSUMER_ENABLED']=True
        self.connection=MagicMock();self.cursor=self.connection.cursor.return_value.__enter__.return_value
        self.called=MagicMock(return_value='actual result')
        self.view=bounded_inference(lambda:self.connection)(self.called)

    def test_busy_does_not_run_and_closes(self):
        self.cursor.fetchone.return_value={'acquired':0}
        with self.app.test_request_context():
            result,status=self.view()
            self.assertEqual(status,503);self.assertEqual(result.headers['Retry-After'],'5')
        self.called.assert_not_called();self.connection.close.assert_called_once()

    def test_success_and_original_exception_close(self):
        self.cursor.fetchone.return_value={'acquired':1}
        with self.app.test_request_context():
            self.assertEqual(self.view(),'actual result')
            self.called.side_effect=RuntimeError('synthetic')
            with self.assertRaises(RuntimeError):self.view()
        self.assertEqual(self.connection.close.call_count,2)

    def test_cleanup_error_preserves_success(self):
        self.cursor.fetchone.return_value={'acquired':1}
        def execute(query,params):
            if 'RELEASE_LOCK' in query:raise pymysql.OperationalError('synthetic')
        self.cursor.execute.side_effect=execute
        with self.app.test_request_context():self.assertEqual(self.view(),'actual result')
        self.connection.close.assert_called_once()
