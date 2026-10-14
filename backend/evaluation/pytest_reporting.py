"""Opt in with -p evaluation.pytest_reporting --semantic-report."""
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx
import pytest

from app import extraction


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def sanitize(value, known_secrets=()):
    secrets = list(known_secrets) + [v for k, v in os.environ.items()
               if v and re.search(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", k, re.I)]
    sensitive = re.compile(r"authorization|api.?key|token$|secret|password|credential", re.I)

    def clean(item):
        if isinstance(item, dict):
            return {key: "[REDACTED]" if sensitive.search(key) else clean(val)
                    for key, val in item.items()}
        if isinstance(item, list):
            return [clean(val) for val in item]
        if isinstance(item, str):
            for secret in secrets:
                item = item.replace(secret, "[REDACTED]")
            item = re.sub(r"(?i)Bearer\s+[^\s\"']+", "Bearer [REDACTED]", item)
            return re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", item)
        return item
    return clean(value)


class Recorder:
    def __init__(self, directory, test_id):
        self.directory = directory
        self.secrets = set()
        self.data = {"test_id": test_id, "started_at": datetime.now(timezone.utc).isoformat(),
                     "calls": [], "pytest_reports": [], "instrumentation_errors": []}

    def error(self, error):
        # Do not serialize exception text: it can contain credentials or request headers.
        self.data["instrumentation_errors"].append(type(error).__name__)

    def save(self):
        try:
            self.secrets.update(v for k, v in os.environ.items()
                                if v and re.search(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", k, re.I))
            self.directory.mkdir(parents=True, exist_ok=True)
            target = self.directory / "attempt.json"
            temporary = self.directory / "attempt.tmp"
            temporary.write_text(json.dumps(sanitize(self.data, self.secrets), indent=2, ensure_ascii=False))
            temporary.replace(target)
        except Exception as error:
            self.error(error)

    def extract(self, original, request, **kwargs):
        call = {"input": request.brain_dump, "timezone": request.timezone,
                "reference": kwargs.get("now").isoformat() if kwargs.get("now") else None,
                "configured_model": os.getenv("OPENAI_MODEL"),
                "prompt_sha256": digest(extraction.SYSTEM_PROMPT),
                "schema_sha256": digest(extraction.EXTRACTION_SCHEMA),
                "responses": [], "parsed_tasks": None, "error": None}
        self.data["calls"].append(call)
        self.save()
        original_post = httpx.Client.post

        def capture(client, *args, **options):
            try:
                response = original_post(client, *args, **options)
            except Exception as error:
                call["error"] = {"category": "provider_api", "type": type(error).__name__}
                raise
            try:
                try:
                    body = response.json()
                except ValueError:
                    body = response.text
                call["responses"].append({
                    "http_status": response.status_code, "raw_body": body,
                    "returned_model": body.get("model") if isinstance(body, dict) else None,
                    "usage": body.get("usage") if isinstance(body, dict) else None,
                })
                self.save()
            except Exception as error:
                self.error(error)
            return response

        start = time.perf_counter()
        try:
            with patch.object(httpx.Client, "post", capture):
                result = original(request, **kwargs)
            try:
                call["parsed_tasks"] = [task.model_dump(mode="json") for task in result]
            except Exception as error:
                self.error(error)
            return result
        except extraction.ExtractionError as error:
            category = "provider_api"
            if str(error) == "Extraction returned invalid or incomplete tasks. Try again.":
                category = "response_validation"
            call["error"] = {"category": category, "type": type(error).__name__,
                             "status_code": error.status_code, "message": str(error)}
            raise
        except Exception as error:
            call["error"] = call["error"] or {"category": "unexpected_extraction",
                                              "type": type(error).__name__}
            raise
        finally:
            call["latency_seconds"] = time.perf_counter() - start
            self.save()


def pytest_addoption(parser):
    parser.addoption("--semantic-report", action="store_true",
                     help="Capture live cases under backend/.semantic-reports/<unique-run>.")


def pytest_configure(config):
    if not config.getoption("--semantic-report"):
        return
    config._semantic_recorders = {}
    config._semantic_run = Path(__file__).resolve().parents[1] / ".semantic-reports" / str(uuid4())


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if not hasattr(item.config, "_semantic_run") or not item.get_closest_marker("live"):
        yield
        return
    recorder = Recorder(item.config._semantic_run / str(uuid4()), item.nodeid)
    item.config._semantic_recorders[item.nodeid] = recorder
    recorder.save()
    # Existing live tests import extract_tasks into their own module.
    original = getattr(item.module, "extract_tasks", None)
    if original is None:
        recorder.data["instrumentation_errors"].append("MissingExtractTasksBinding")
        yield
    else:
        with patch.object(item.module, "extract_tasks",
                          lambda request, **kwargs: recorder.extract(original, request, **kwargs)):
            yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    recorder = getattr(item.config, "_semantic_recorders", {}).get(item.nodeid)
    if recorder is None:
        return
    try:
        report = outcome.get_result()
        category = None
        if report.failed:
            errors = [entry["error"] for entry in recorder.data["calls"] if entry["error"]]
            category = errors[-1]["category"] if errors else (
                "semantic_assertion" if call.excinfo and call.excinfo.errisinstance(AssertionError)
                else "test_error")
        recorder.data["pytest_reports"].append({
            "phase": report.when, "outcome": report.outcome, "category": category,
            "duration_seconds": report.duration,
            # Traceback source/locals can expose credentials. Retain the assertion
            # or exception message, not arbitrary test source or request objects.
            "failure": str(call.excinfo.value) if report.failed and call.excinfo else None,
        })
        recorder.save()
    except Exception as error:
        recorder.error(error)


def pytest_terminal_summary(terminalreporter, config):
    if not hasattr(config, "_semantic_run"):
        return
    terminalreporter.write_line(f"Semantic artifacts: {config._semantic_run}")
    for recorder in config._semantic_recorders.values():
        if recorder.data["instrumentation_errors"]:
            terminalreporter.write_line(
                f"REPORTING ERROR: {recorder.data['test_id']}: "
                + ", ".join(recorder.data["instrumentation_errors"]))
