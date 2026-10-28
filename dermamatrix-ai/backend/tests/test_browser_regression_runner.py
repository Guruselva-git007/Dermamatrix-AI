"""Do not accept CLI exit success as evidence of a completed browser workflow."""
import importlib.util
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.request import build_opener, ProxyHandler, Request

urlopen = build_opener(ProxyHandler({})).open

spec = importlib.util.spec_from_file_location("browser_runner", Path(__file__).resolve().parents[2] / "frontend/tests/run_browser_regressions.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class BrowserEvidenceTests(unittest.TestCase):
    def test_valid_evidence_preserves_actual_checks(self):
        value = {"checks": ["account isolation", "real download"], "errors": []}
        self.assertEqual(runner.verified_result(json.dumps(value), 2), value)

    def test_exit_zero_cli_error_is_not_success(self):
        with self.assertRaises(ValueError):
            runner.verified_result("### Error\nTimeoutError", 1)

    def test_truncated_result_is_not_success(self):
        with self.assertRaises(ValueError):
            runner.verified_result('{"checks": [', 1)

    def test_missing_error_status_is_not_success(self):
        with self.assertRaises(ValueError):
            runner.verified_result('{"checks": ["rendered"]}', 1)

    def test_incomplete_workflow_is_not_success(self):
        with self.assertRaises(ValueError):
            runner.verified_result('{"checks": ["first step"], "errors": []}', 2)

    def test_uncaught_browser_error_is_not_success(self):
        with self.assertRaises(ValueError):
            runner.verified_result('{"checks": ["rendered"], "errors": ["uncaught"]}', 1)

    def test_invalid_check_labels_are_not_success(self):
        for checks in [[""], [True], "not an array"]:
            with self.subTest(checks=checks), self.assertRaises(ValueError):
                runner.verified_result(json.dumps({"checks": checks, "errors": []}), 1)


class TestOriginLifecycleTests(unittest.TestCase):
    def setUp(self):
        class Upstream(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b'Synthetic unchanged upstream'
                self.send_response(200)
                self.send_header('Cache-Control', 'no-store, max-age=0')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        self.upstream = ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        self.thread = threading.Thread(target=self.upstream.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
        self.thread.start()
        self.origin = runner.TestOrigin(self.upstream.server_address[1])

    def tearDown(self):
        self.origin.stop()
        self.upstream.shutdown()
        self.upstream.server_close()
        self.thread.join(timeout=5)

    def test_actual_outage_and_recovery_preserve_bytes_and_no_store(self):
        self.origin.start()
        url = self.origin.url
        with urlopen(url + '/sample', timeout=2) as response:
            self.assertEqual(response.read(), b'Synthetic unchanged upstream')
            self.assertEqual(response.headers['Cache-Control'], 'no-store, max-age=0')
        self.origin.stop()
        with self.assertRaises(OSError):
            urlopen(url + '/uncached-target', timeout=2)
        self.origin.start()
        self.assertEqual(self.origin.url, url)
        with urlopen(url, timeout=2) as response:
            self.assertEqual(response.read(), b'Synthetic unchanged upstream')

    def test_closed_origin_cannot_keep_accepting_browser_connections(self):
        self.origin.start()
        url = self.origin.url
        self.origin.stop()
        self.origin.stop()
        with self.assertRaises(OSError):
            urlopen(url, timeout=2)

    def test_relay_rejects_account_and_health_record_writes(self):
        self.origin.start()
        for path in ['/api/auth/register', '/api/progress-checkins']:
            with self.subTest(path=path), self.assertRaises(HTTPError) as caught:
                urlopen(Request(self.origin.url + path, data=b'{}'), timeout=2)
            self.assertEqual(caught.exception.code, 405)


class SyntheticBudgetIsolationTests(unittest.TestCase):
    def test_refuses_normal_database_wrong_environment_and_enabled_mail(self):
        for values in [
            {'DERMAMATRIX_ENV': 'test', 'MYSQL_DATABASE': 'real_account_database', 'DERMAMATRIX_MAIL_TRANSPORT': 'disabled'},
            {'DERMAMATRIX_ENV': 'local', 'MYSQL_DATABASE': 'isolated_synthetic', 'DERMAMATRIX_MAIL_TRANSPORT': 'disabled'},
            {'DERMAMATRIX_ENV': 'test', 'MYSQL_DATABASE': 'isolated_synthetic', 'DERMAMATRIX_MAIL_TRANSPORT': 'smtp'},
        ]:
            with self.subTest(values=values), patch.dict(os.environ, values), self.assertRaises(ValueError):
                runner.reset_synthetic_budgets()

    def test_reset_touches_only_technical_budgets_and_closes_the_connection(self):
        connection = MagicMock()
        connect = MagicMock(return_value=connection)
        values = {'DERMAMATRIX_ENV': 'test', 'MYSQL_DATABASE': 'isolated_synthetic', 'DERMAMATRIX_MAIL_TRANSPORT': 'disabled'}
        with patch.dict(os.environ, values), patch.dict('sys.modules', {'pymysql': SimpleNamespace(connect=connect)}):
            runner.reset_synthetic_budgets()
        self.assertEqual(connect.call_args.kwargs['database'], 'isolated_synthetic')
        connection.cursor.return_value.__enter__.return_value.execute.assert_called_once_with('DELETE FROM request_budgets')
        connection.commit.assert_called_once_with()
        connection.close.assert_called_once_with()
