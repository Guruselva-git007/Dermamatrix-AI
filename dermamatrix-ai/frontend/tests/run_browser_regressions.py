"""Run existing synthetic workflows sequentially in isolated test browsers.

Requires the existing playwright-cli and explicitly installed engines. No
dependency installation, provider activation or normal-account target is inferred.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
from urllib.request import urlopen


APP = Path(__file__).resolve().parents[2]
SUITES = (("browser-smoke.js", 15), ("browser-continuity.js", 12), ("browser-product-quality.js", 10))


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


def run_suite(cli: str, session: str, filename: str, minimum: int, folder: Path, record: dict) -> None:
    suite = folder / Path(filename).stem
    suite.mkdir(exist_ok=True)
    source = (APP / "frontend/tests" / filename).read_text(encoding="utf-8").strip()
    wrapper = suite / "run.js"
    options = json.dumps({"artifactRoot": str(suite) + "/"})
    wrapper.write_text(f"async page => await ({source})(page, {options})\n", encoding="utf-8")
    output = command(cli, session, ["--raw", "run-code", "--filename=" + str(wrapper)], suite / "result.json")
    try:
        result = verified_result(output, minimum)
    except ValueError as error:
        raise RuntimeError(f"{filename}: {error}: {output[-5000:]}") from error
    record["suites"].append({"suite": filename, "checks": len(result["checks"]), "errors": []})
    print(f"{record['browser']}: {filename}: {len(result['checks'])} checks passed", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browsers", nargs="+", choices=("chrome", "firefox", "webkit"), default=["chrome"])
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    cli = shutil.which("playwright-cli")
    if not cli:
        parser.error("Install the documented playwright-cli first; this runner installs nothing")
    if os.environ.get("DERMAMATRIX_ENV") != "test" or not os.environ.get("MYSQL_DATABASE", "").endswith("_synthetic") or os.environ.get("DERMAMATRIX_MAIL_TRANSPORT") != "disabled":
        parser.error("Use the isolated *_synthetic database, DERMAMATRIX_ENV=test and disabled mail transport")
    try:
        with urlopen("http://127.0.0.1:8001/api/readiness", timeout=10) as response:
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
        try:
            arguments = ["open", summary["target"], "--browser=" + browser, "--config=" + str(config)]
            command(cli, session, arguments, folder / "open.txt", 60)
            metadata = command(cli, session, ["--raw", "run-code", "async page => ({userAgent: await page.evaluate(() => navigator.userAgent)})"], folder / "engine.json")
            record.update(json.loads(metadata))
            for filename, minimum in SUITES:
                run_suite(cli, session, filename, minimum, folder, record)
            command(cli, session, ["close"], folder / "close-network.txt", 30)
            config.write_text(json.dumps({"browser": {"contextOptions": {"serviceWorkers": "allow"}}}), encoding="utf-8")
            command(cli, session, arguments, folder / "open-offline.txt", 60)
            run_suite(cli, session, "browser-offline.js", 4, folder, record)
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            record["errors"].append(str(error))
            summary["errors"].append({"browser": browser, "message": str(error)})
            print(f"{browser}: verification failed; preserved evidence in {folder}: {error}", flush=True)
        finally:
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
