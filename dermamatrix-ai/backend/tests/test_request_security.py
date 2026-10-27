"""Browser request boundary checks with real Flask dispatch and no database."""

from contextlib import ExitStack
from io import BytesIO
import unittest
from unittest.mock import Mock, patch

from flask import Request
from werkzeug.datastructures import Headers

from isolated_application import load_isolated_application
from request_security import canonical_origin, request_security_configuration
from test_consent_boundaries import ReadProbe


class OriginParsingTests(unittest.TestCase):
    def test_default_ports_hostname_case_and_ipv6_are_normalized(self):
        for value, expected in (
            ("http://LOCALHOST", ("http", "localhost", 80)),
            ("http://localhost:80", ("http", "localhost", 80)),
            ("https://EXAMPLE.TEST:443", ("https", "example.test", 443)),
            ("http://[0:0:0:0:0:0:0:1]:8001", ("http", "::1", 8001)),
        ):
            with self.subTest(value=value):
                self.assertEqual(canonical_origin(value), expected)

    def test_invalid_null_multiple_and_ambiguous_origins_reject(self):
        for value in (None, "", "null", "NULL", "http://localhost/", "http://localhost/a", "http://localhost?", "http://localhost#",
                      "http://user@localhost", "http://user:pass@localhost", "http://localhost:", "http://localhost:bad", "http://localhost:0",
                      "http://localhost:65536", "http://localhost http://evil.test", "http://localhost,http://evil.test", " http://localhost",
                      "http://localhost\n", "http://localhost\\@evil.test", "http://%6cocalhost", "https://sub..test", "https://test.",
                      "file://localhost", "https://[invalid]", "http://[::1]evil", "http://[::1]:80evil", "https://[::1%25zone]", "https://éxample.test"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_origin(value)

    def test_explicit_production_trusted_origins_are_required_and_exact(self):
        with self.assertRaises(ValueError):
            request_security_configuration({"DERMAMATRIX_ENV": "production"})
        for origin in ("https://app.example.test/", "null", "https://app.example.test,", "https://user@app.example.test"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                request_security_configuration({"DERMAMATRIX_ENV": "production", "DERMAMATRIX_TRUSTED_ORIGINS": origin})
        config = request_security_configuration({"DERMAMATRIX_ENV": "production", "DERMAMATRIX_TRUSTED_ORIGINS": "https://APP.EXAMPLE.TEST:443, https://second.example.test:8443"})
        self.assertTrue(config["REQUEST_SECURITY_PRODUCTION"])
        self.assertEqual(config["REQUEST_TRUSTED_ORIGINS"], (("https", "app.example.test", 443), ("https", "second.example.test", 8443)))


class RequestBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_isolated_application("_dermamatrix_request_security_test_app")

    def setUp(self):
        self.module.app.config.update(request_security_configuration({}))
        self.client = self.module.app.test_client()

    def test_cross_origin_requests_never_enter_any_unsafe_api_route(self):
        routes = [(rule.rule, method, rule.endpoint) for rule in self.module.app.url_map.iter_rules()
                  for method in rule.methods.intersection({"POST", "PUT", "PATCH", "DELETE"}) if rule.rule.startswith("/api/")]
        self.assertGreater(len(routes), 10)
        for path, method, endpoint in routes:
            with self.subTest(path=path, method=method), patch.dict(self.module.app.view_functions, {endpoint: Mock(side_effect=AssertionError("Unsafe view must not run"))}):
                response = self.client.open(path, method=method, headers={"Origin": "https://evil.example", "Sec-Fetch-Site": "cross-site"})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json()["code"], "REQUEST_ORIGIN_REJECTED")
                self.module.app.view_functions[endpoint].assert_not_called()

    def test_null_malformed_duplicate_or_mismatched_origin_stops_before_image_receipt_parsing(self):
        cases = [Headers({"Origin": origin}) for origin in ("null", "", "https://evil.test", "http://localhost:8001", "http://localhost/",
                 "http://localhost http://evil.test", "http://localhost,http://evil.test", "http://user@localhost", "http://localhost:")]
        cases.append(Headers([("Origin", "http://localhost"), ("Origin", "http://localhost")]))
        for headers in cases:
            with self.subTest(origin=headers.getlist("Origin")), ExitStack() as stack:
                streams = []
                def file_stream(*_args, **_kwargs):
                    stream = ReadProbe(); streams.append(stream); return stream
                parser = stack.enter_context(patch.object(Request, "_get_file_stream", side_effect=file_stream))
                probes = [stack.enter_context(patch.object(self.module, name, side_effect=AssertionError(name))) for name in
                          ("database", "_opened_image", "_image_quality_from_decoded", "presentation_case_for_image", "run_screening_model")]
                with self.assertNoLogs(self.module.app.logger, level="WARNING"):
                    response = self.client.post("/api/assessments", headers=headers,
                                                data={"image": (BytesIO(b"synthetic"), "fixture.png"), "image_consent": "true"},
                                                content_type="multipart/form-data")
                self.assertEqual(response.status_code, 403)
                parser.assert_not_called()
                self.assertEqual(streams, [])
                for probe in probes:
                    probe.assert_not_called()

    def test_fetch_site_is_only_same_origin_when_supplied(self):
        for site in ("cross-site", "same-site", "none", "", "Same-Origin", "same-origin,cross-site", "unknown"):
            for origin in (None, "http://localhost"):
                with self.subTest(site=site, origin=origin), patch.object(self.module, "database") as database:
                    headers = {"Sec-Fetch-Site": site}
                    if origin is not None:
                        headers["Origin"] = origin
                    response = self.client.post("/api/auth/logout", headers=headers)
                    self.assertEqual(response.status_code, 403)
                    database.assert_not_called()

    def test_local_same_origin_and_headerless_cli_keep_existing_json_and_form_contracts(self):
        for base in ("http://localhost", "http://localhost:8000", "http://127.0.0.1:8001", "http://[::1]:8000"):
            for headers in ({}, {"Origin": base}, {"Origin": base, "Sec-Fetch-Site": "same-origin"}, {"Sec-Fetch-Site": "same-origin"}):
                with self.subTest(base=base, headers=headers):
                    response = self.client.post("/api/auth/logout", base_url=base, headers=headers)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.get_json(), {"authenticated": False})
                    # Existing route validation remains distinguishable from
                    # the before_request guard for accepted same-origin forms.
                    response = self.client.post("/api/assessments", base_url=base, headers=headers,
                                                data={"image_consent": "true"}, content_type="multipart/form-data")
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.get_json()["error"], "An image is required.")

    def test_default_ports_normalize_but_different_local_origins_do_not(self):
        for base, origin in (("http://localhost", "http://LOCALHOST:80"), ("https://localhost", "https://localhost:443")):
            with self.subTest(base=base):
                self.assertEqual(self.client.post("/api/auth/logout", base_url=base, headers={"Origin": origin}).status_code, 200)
        for origin in ("https://localhost", "http://localhost:8000", "http://127.0.0.1"):
            with self.subTest(origin=origin):
                self.assertEqual(self.client.post("/api/auth/logout", base_url="http://localhost", headers={"Origin": origin}).status_code, 403)

    def test_full_referer_is_verified_only_as_an_origin_fallback(self):
        for referer in ("http://localhost/", "http://LOCALHOST:80/screen?tab=profile", "http://localhost/path%20with%20encoding"):
            with self.subTest(referer=referer):
                self.assertEqual(self.client.post("/api/auth/logout", headers={"Referer": referer}).status_code, 200)
        for referer in ("", "null", "https://evil.example/screen", "http://localhost:8001/", "http://user@localhost/",
                        "http://user:pass@localhost/", "http://localhost:/", "http://localhost\\@evil.example/screen", "http://localhost/ unsafe"):
            with self.subTest(referer=referer), patch.object(self.module, "database") as database:
                response = self.client.post("/api/auth/login", headers={"Referer": referer}, json={})
                self.assertEqual(response.status_code, 403)
                database.assert_not_called()
        # A supplied Origin is authoritative; Referer is only the fallback.
        self.assertEqual(self.client.post("/api/auth/logout", headers={"Origin": "null", "Referer": "http://localhost/"}).status_code, 403)

    def test_report_download_get_and_head_reject_before_metadata_view(self):
        for method in ("GET", "HEAD"):
            for headers in ({"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"},
                            {"Origin": "https://evil.example"}, {"Referer": "https://evil.example/link"}):
                with self.subTest(method=method, headers=headers), patch.object(self.module, "database") as database, \
                        patch.dict(self.module.app.view_functions, {"download_assessment_report": Mock(side_effect=AssertionError("Report view must not run"))}):
                    response = self.client.open("/api/reports/synthetic/download", method=method, headers=headers)
                    self.assertEqual(response.status_code, 403)
                    self.module.app.view_functions["download_assessment_report"].assert_not_called()
                    database.assert_not_called()
        endpoint = self.module.app.view_functions["download_assessment_report"]
        try:
            probe = Mock(return_value={"test": "allowed"})
            self.module.app.view_functions["download_assessment_report"] = probe
            for method in ("GET", "HEAD"):
                for headers in ({}, {"Sec-Fetch-Site": "same-origin"}, {"Sec-Fetch-Site": "none"}, {"Referer": "http://localhost/history"}):
                    with self.subTest(method=method, headers=headers):
                        self.assertEqual(self.client.open("/api/reports/synthetic/download", method=method, headers=headers).status_code, 200)
            self.assertEqual(probe.call_count, 8)
        finally:
            self.module.app.view_functions["download_assessment_report"] = endpoint

    def test_local_untrusted_host_blocks_all_requests_even_with_matching_attacker_origin(self):
        for host in ("evil.example", "localhost.evil.example", "127.0.0.1.evil.example", "192.168.1.2", "127.1", "2130706433"):
            for path, method in (("/", "GET"), ("/api/health", "GET"), ("/api/account-data/download", "GET"), ("/api/auth/logout", "POST")):
                with self.subTest(host=host, path=path), patch.object(self.module, "database") as database:
                    response = self.client.open(path, method=method, base_url=f"http://{host}:8000", headers={"Origin": f"http://{host}:8000"})
                    self.assertEqual(response.status_code, 403)
                    self.assertEqual(response.get_json()["code"], "UNTRUSTED_REQUEST_HOST")
                    database.assert_not_called()

    def test_external_https_requires_configured_origin_and_ignores_forwarding_headers(self):
        self.module.app.config.update(request_security_configuration({"DERMAMATRIX_ENV": "production", "DERMAMATRIX_TRUSTED_ORIGINS": "https://app.example.test,https://other.example.test"}))
        allowed = self.client.post("/api/auth/logout", base_url="https://app.example.test", headers={"Origin": "https://APP.EXAMPLE.TEST:443", "Sec-Fetch-Site": "same-origin"})
        self.assertEqual(allowed.status_code, 200)
        # Another configured origin is still a different origin for this host.
        rejected = self.client.post("/api/auth/logout", base_url="https://app.example.test", headers={"Origin": "https://other.example.test"})
        self.assertEqual(rejected.status_code, 403)
        for base in ("https://unconfigured.example.test", "http://app.example.test", "http://localhost"):
            with self.subTest(base=base):
                response = self.client.post("/api/auth/logout", base_url=base, headers={"Origin": "https://app.example.test",
                    "X-Forwarded-Host": "app.example.test", "X-Forwarded-Proto": "https", "Forwarded": 'host="app.example.test";proto=https'})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.get_json()["code"], "UNTRUSTED_REQUEST_HOST")


if __name__ == "__main__":
    unittest.main()
