"""Run existing synthetic workflows sequentially in isolated test browsers.

Requires the existing playwright-cli and explicitly installed engines. No
dependency installation, provider activation or normal-account target is inferred.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
from urllib.request import build_opener, ProxyHandler


APP = Path(__file__).resolve().parents[2]
SUITES = (("browser-smoke.js", 15), ("browser-continuity.js", 12), ("browser-product-quality.js", 16), ("browser-accessibility.js", 12))


def reset_synthetic_budgets() -> None:
    """Separate engine test fixtures without disabling the application's limits."""
    database = os.environ.get("MYSQL_DATABASE", "")
    if os.environ.get("DERMAMATRIX_ENV") != "test" or not database.endswith("_synthetic") or os.environ.get("DERMAMATRIX_MAIL_TRANSPORT") != "disabled":
        raise ValueError("Technical-budget reset requires an isolated test *_synthetic database and disabled mail")
    import pymysql
    connection = pymysql.connect(host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
                                 port=int(os.environ.get("MYSQL_PORT", "3306")),
                                 user=os.environ.get("MYSQL_USER", "root"),
                                 password=os.environ.get("MYSQL_PASSWORD", ""),
                                 database=database, connect_timeout=10)
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM request_budgets")
        connection.commit()
    finally:
        connection.close()


class TestOrigin:
    """Loopback relay for reads/guest sign-out; close its socket for an outage."""

    def __init__(self, upstream_port: int = 8001):
        self.upstream_port = upstream_port
        self.port = 0
        self.server = None
        self.thread = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        if self.server is not None:
            raise RuntimeError("Test origin is already running")
        upstream_port = self.upstream_port

        class Relay(BaseHTTPRequestHandler):
            def do_GET(self):
                self.forward()

            def do_POST(self):
                if self.path != "/api/auth/logout":
                    self.send_error(405, "Only guest sign-out is allowed")
                    return
                self.forward()

            def forward(self):
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= 4096:
                    self.send_error(413)
                    return
                connection = http.client.HTTPConnection("127.0.0.1", upstream_port, timeout=15)
                try:
                    headers = {key: value for key, value in self.headers.items() if key.lower() != "connection"}
                    body = self.rfile.read(length) if length else None
                    connection.request(self.command, self.path, body=body, headers=headers)
                    response = connection.getresponse()
                    body = response.read()
                    self.send_response(response.status)
                    for key, value in response.getheaders():
                        if key.lower() not in {"connection", "keep-alive", "transfer-encoding", "content-length", "server", "date"}:
                            self.send_header(key, value)
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
                except (OSError, http.client.HTTPException):
                    self.send_error(502, "Synthetic upstream unavailable")
                finally:
                    connection.close()

            def log_message(self, *_):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), Relay)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server is None:
            return
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.server = None
        try:
            connection = socket.create_connection(("127.0.0.1", self.port), timeout=1)
        except OSError:
            return
        connection.close()
        raise RuntimeError("Owned test origin did not close")


def verified_result(output: str, minimum: int) -> dict:
    """An exit-zero CLI error or incomplete JSON must never become a pass."""
    data = json.loads(output)
    if not isinstance(data, dict) or not isinstance(data.get("checks"), list):
        raise ValueError("Missing browser check results")
    if len(data["checks"]) < minimum or not all(isinstance(check, str) and check.strip() for check in data["checks"]):
        raise ValueError("Browser workflow checks are incomplete")
    if data.get("errors") != []:
        raise ValueError("Browser errors were reported or their status is missing")
    return data


def command(cli: str, session: str, arguments: list[str], log: Path, timeout: int = 180) -> str:
    result = subprocess.run([cli, "-s=" + session, *arguments], cwd=APP, capture_output=True, text=True, timeout=timeout)
    log.write_text(result.stdout, encoding="utf-8")
    log.with_suffix(".stderr.txt").write_text(result.stderr, encoding="utf-8")
    if result.returncode:
        detail = (result.stdout.strip() or result.stderr.strip())[-5000:]
        raise RuntimeError(f"Browser command failed; see {log.name}: {detail}")
    return result.stdout


def run_suite(cli: str, session: str, filename: str, minimum: int, folder: Path, record: dict, extra_options: dict | None = None) -> dict:
    extra_options = extra_options or {}
    phase = extra_options.get("phase")
    suite = folder / (Path(filename).stem + ("-" + phase if phase else ""))
    suite.mkdir(exist_ok=True)
    source = (APP / "frontend/tests" / filename).read_text(encoding="utf-8").strip()
    wrapper = suite / "run.js"
    options = json.dumps({"artifactRoot": str(suite) + "/", **extra_options})
    wrapper.write_text(f"async page => await ({source})(page, {options})\n", encoding="utf-8")
    output = command(cli, session, ["--raw", "run-code", "--filename=" + str(wrapper)], suite / "result.json")
    try:
        result = verified_result(output, minimum)
    except ValueError as error:
        raise RuntimeError(f"{filename}: {error}: {output[-5000:]}") from error
    record["suites"].append({"suite": filename, **({"phase": phase} if phase else {}), "checks": len(result["checks"]), "errors": []})
    print(f"{record['browser']}: {filename}{':' + phase if phase else ''}: {len(result['checks'])} checks passed", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browsers", nargs="+", choices=("chrome", "firefox", "webkit"), default=["chrome"])
    parser.add_argument("--artifacts", type=Path)
    parser.add_argument("--reset-synthetic-budgets", action="store_true", help="Reset only technical request budgets before each engine in the isolated synthetic database")
    args = parser.parse_args()
    cli = shutil.which("playwright-cli")
    if not cli:
        parser.error("Install the documented playwright-cli first; this runner installs nothing")
    if os.environ.get("DERMAMATRIX_ENV") != "test" or not os.environ.get("MYSQL_DATABASE", "").endswith("_synthetic") or os.environ.get("DERMAMATRIX_MAIL_TRANSPORT") != "disabled":
        parser.error("Use the isolated *_synthetic database, DERMAMATRIX_ENV=test and disabled mail transport")
    try:
        with build_opener(ProxyHandler({})).open("http://127.0.0.1:8001/api/readiness", timeout=10) as response:
            readiness = json.load(response)
    except (OSError, ValueError):
        parser.error("The isolated test stack on port 8001 is unavailable")
    if readiness.get("status") != "ready" or readiness.get("consumer_enabled") is not True:
        parser.error("Start the isolated consumer test stack on port 8001 first")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifacts = (args.artifacts or APP.parent / "local-artifacts/browser-regressions" / stamp).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    if any(artifacts.iterdir()):
        parser.error("Choose a fresh artifact directory to preserve earlier verification")
    summary = {"target": "http://127.0.0.1:8001", "synthetic_only": True, "browsers": [], "errors": []}
    for browser in dict.fromkeys(args.browsers):
        folder = artifacts / browser
        folder.mkdir(exist_ok=True)
        session = f"dm-{browser}-{stamp.lower()}-{os.getpid()}"
        record = {"browser": browser, "session": session, "suites": [], "errors": []}
        config = folder / "browser.json"
        # Service workers can hide requests from Playwright routing. These
        # suites inject response loss/latency, so use the documented test option.
        config.write_text(json.dumps({"browser": {"contextOptions": {"serviceWorkers": "block"}}}), encoding="utf-8")
        record["service_workers"] = {"network_fault_suites": "blocked", "offline_suite": "enabled_in_a_separate_context"}
        origin = TestOrigin()
        try:
            if args.reset_synthetic_budgets:
                reset_synthetic_budgets()
                record["technical_budget_fixture_reset"] = True
                print(f"{browser}: reset only synthetic technical request budgets; app limits unchanged", flush=True)
            arguments = ["open", summary["target"], "--browser=" + browser, "--config=" + str(config)]
            command(cli, session, arguments, folder / "open.txt", 60)
            metadata = command(cli, session, ["--raw", "run-code", "async page => ({userAgent: await page.evaluate(() => navigator.userAgent)})"], folder / "engine.json")
            record.update(json.loads(metadata))
            for filename, minimum in SUITES:
                run_suite(cli, session, filename, minimum, folder, record)
            command(cli, session, ["close"], folder / "close-network.txt", 30)
            config.write_text(json.dumps({"browser": {"contextOptions": {"serviceWorkers": "allow"}}}), encoding="utf-8")
            # Firefox can keep fetching from a worker despite setOffline(true).
            # Use an actually closed owned origin instead of weakening fallback assertions.
            origin.start()
            record["offline_disruption"] = "owned_loopback_origin_stopped_and_restarted"
            command(cli, session, ["open", origin.url, "--browser=" + browser, "--config=" + str(config)], folder / "open-offline.txt", 60)
            prepared = run_suite(cli, session, "browser-offline.js", 2, folder, record, {"phase": "prepare", "origin": origin.url})
            origin.stop()
            run_suite(cli, session, "browser-offline.js", 1, folder, record, {"phase": "outage", "origin": origin.url})
            origin.start()
            run_suite(cli, session, "browser-offline.js", 1, folder, record, {"phase": "recover", "origin": origin.url, "cachedPaths": prepared["cachedPaths"]})
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            record["errors"].append(str(error))
            summary["errors"].append({"browser": browser, "message": str(error)})
            print(f"{browser}: verification failed; preserved evidence in {folder}: {error}", flush=True)
        finally:
            try:
                origin.stop()
            except (OSError, RuntimeError) as error:
                record["errors"].append("Test origin cleanup: " + str(error))
                summary["errors"].append({"browser": browser, "message": "Test origin cleanup failed"})
            try:
                command(cli, session, ["close"], folder / "close.txt", 30)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                record["errors"].append("Browser cleanup: " + str(error))
                summary["errors"].append({"browser": browser, "message": "Browser cleanup failed"})
            summary["browsers"].append(record)
            (artifacts / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary), flush=True)
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
