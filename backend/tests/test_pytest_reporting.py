import json
from pathlib import Path

import pytest

from evaluation.pytest_reporting import Recorder, sanitize

pytest_plugins = ["pytester"]

SAMPLE = '''
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
import pytest
from app.extraction import extract_tasks
from app.models import ExtractRequest

@pytest.mark.live
@pytest.mark.parametrize("mode", ["success", "assertion", "api", "invalid"])
def test_sample(mode, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret-credential")
    monkeypatch.setenv("OPENAI_MODEL", "mock-release")
    calls = []
    def post(client, url, **kwargs):
        calls.append(1)
        body = {"status": "completed", "model": "mock-returned",
                "usage": {"input_tokens": 10, "output_tokens": 5},
                "output": [{"type": "message", "content": [{"type": "output_text",
                           "text": json.dumps({"tasks": []})}]}]}
        if mode == "invalid":
            body["output"] = []
        if mode == "api":
            body = {"error": {"message": "Bearer test-secret-credential",
                              "api_key": "another-private-value"}}
        return httpx.Response(503 if mode == "api" else 200, json=body,
                              request=httpx.Request("POST", url))
    monkeypatch.setattr(httpx.Client, "post", post)
    try:
        result = extract_tasks(ExtractRequest(brain_dump="Feel overwhelmed", timezone="Asia/Taipei"),
            now=datetime(2026,10,6,10,tzinfo=ZoneInfo("Asia/Taipei")))
        assert mode != "assertion", "synthetic semantic failure"
        assert result == []
    finally:
        assert len(calls) == 1
'''


def prepare(pytester, monkeypatch, broken=False):
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1]))
    pytester.makepyfile(SAMPLE)
    # Redirect only the test plugin's run directory; real runs use the gitignored location.
    pytester.makeconftest('''
from pathlib import Path
import pytest
@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    if hasattr(config, "_semantic_run"):
        config._semantic_run = Path("reports")
''' + ('''
        Path("reports").write_text("Force reporting failure without affecting tests")
''' if broken else ""))


def test_plugin_captures_success_failures_without_changing_outcomes(pytester, monkeypatch):
    prepare(pytester, monkeypatch)
    result = pytester.runpytest_subprocess("-p", "evaluation.pytest_reporting", "--semantic-report", "-q")
    result.assert_outcomes(passed=1, failed=3)
    paths = list((pytester.path / "reports").glob("*/attempt.json"))
    assert len(paths) == 4
    reports = [json.loads(path.read_text()) for path in paths]
    categories = {phase["category"] for report in reports for phase in report["pytest_reports"]}
    assert {"semantic_assertion", "provider_api", "response_validation"} <= categories
    for report in reports:
        assert len(report["calls"]) == 1
        call = report["calls"][0]
        assert call["input"] == "Feel overwhelmed"
        assert call["reference"] == "2026-10-06T10:00:00+08:00"
        assert call["configured_model"] == "mock-release"
        assert len(call["prompt_sha256"]) == len(call["schema_sha256"]) == 64
        assert call["latency_seconds"] >= 0
    serialized = "".join(path.read_text() for path in paths)
    assert "test-secret-credential" not in serialized
    assert "another-private-value" not in serialized
    successful = next(r for r in reports if "[success]" in r["test_id"])
    assert successful["calls"][0]["parsed_tasks"] == []
    assert successful["calls"][0]["responses"][0]["returned_model"] == "mock-returned"
    assert successful["calls"][0]["responses"][0]["usage"]["input_tokens"] == 10
    # A second run retains each earlier attempt.
    pytester.runpytest_subprocess("-p", "evaluation.pytest_reporting", "--semantic-report", "-q")
    assert len(list((pytester.path / "reports").glob("*/attempt.json"))) == 8


def test_reporting_write_failure_does_not_change_pytest_outcomes(pytester, monkeypatch):
    prepare(pytester, monkeypatch, broken=True)
    result = pytester.runpytest_subprocess("-p", "evaluation.pytest_reporting", "--semantic-report", "-q")
    result.assert_outcomes(passed=1, failed=3)
    result.stdout.fnmatch_lines(["*REPORTING ERROR*"])


def test_plugin_without_flag_is_inert(pytester, monkeypatch):
    prepare(pytester, monkeypatch)
    result = pytester.runpytest_subprocess("-p", "evaluation.pytest_reporting", "-q")
    result.assert_outcomes(passed=1, failed=3)
    assert not (pytester.path / "reports").exists()


def test_credential_redaction(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-example")
    data = sanitize({"Authorization": "anything", "message": "secret-example sk-abcd Bearer abc",
                     "nested": {"password": "hidden"}, "usage": {"input_tokens": 12}})
    assert data["Authorization"] == "[REDACTED]"
    assert "secret-example" not in json.dumps(data)
    assert data["nested"]["password"] == "[REDACTED]"
    assert data["usage"]["input_tokens"] == 12
