import json
from dataclasses import replace

import httpx
import pytest

from evaluation.evaluator import evaluate
from evaluation.fixtures import CONDITIONAL, FIXTURES, LONG, PROJECT, REPEATED
from evaluation.run import run_attempt

TITLES = {
    "laundry": "Hang up laundry", "shampoo": "Buy shampoo", "groceries": "Buy groceries",
    "application": "Submit the application", "resume": "Update resume", "maya": "Reply to Maya",
    "card": "Buy Dad a birthday card", "dentist": "Book dentist appointment",
    "kitchen": "Clean kitchen", "bill": "Pay electricity bill", "trial": "Cancel free trial",
    "walk": "Take a twenty-minute walk", "writeup": "Finish project write-up",
    "project_addition": "Add the project to my resume", "desk": "Clear current desk",
    "lease": "Send signed lease",
}


def output(fixture):
    expected = list(fixture.required) + ([PROJECT] if fixture is LONG else [])
    return [dict(title=TITLES[item.identity], importance=item.importance or "normal",
                 first_step=item.explicit, first_step_origin="explicit" if item.explicit else None,
                 due_date=item.due_date, due_at=item.due_at) for item in expected]


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda fixture: fixture.id)
def test_reference_outputs_have_no_strict_failures(fixture):
    result = evaluate(fixture, output(fixture))
    assert result["failures"] == []
    assert result["manual_review"]  # Quality is not certified by synthetic success.


@pytest.mark.parametrize("identity", [item.identity for item in LONG.required])
def test_each_long_commitment_is_required(identity):
    tasks = [task for task in output(LONG) if task["title"] != TITLES[identity]]
    assert any(identity in failure for failure in evaluate(LONG, tasks)["failures"])


def test_duplicate_and_forbidden_hallucination():
    tasks = output(REPEATED)
    assert any("duplicate" in failure for failure in evaluate(REPEATED, tasks + [tasks[0]])["failures"])
    tasks = output(CONDITIONAL)
    tasks.append({**tasks[0], "title": "Buy a new desk", "first_step": None, "first_step_origin": None})
    assert any("forbidden" in failure for failure in evaluate(CONDITIONAL, tasks)["failures"])


def test_unfamiliar_paraphrase_is_pending_not_automatic_failure_or_pass():
    tasks = output(REPEATED)
    tasks[1]["title"] = "Get back to Maya"
    result = evaluate(REPEATED, tasks)
    assert result["status"] == "manual_review"
    assert not result["failures"]
    assert any(item["category"] == "missing_identity" for item in result["manual_review"])


def test_unrecognized_extra_action_requires_manual_hallucination_review():
    tasks = output(REPEATED)
    tasks.append({**tasks[1], "title": "Order a telescope"})
    result = evaluate(REPEATED, tasks)
    assert result["status"] == "manual_review"
    assert any(item["category"] == "identity" for item in result["manual_review"])


@pytest.mark.parametrize("change", [
    {"due_date": "2026-10-16", "due_at": None},
    {"due_at": "2026-10-16T17:00:00+08:00"},
])
def test_deadline_precision_and_time(change):
    tasks = output(CONDITIONAL)
    tasks[1].update(change)
    assert any("deadline" in failure for failure in evaluate(CONDITIONAL, tasks)["failures"])


def test_deadline_leakage_onto_other_task():
    tasks = output(CONDITIONAL)
    tasks[0]["due_at"] = tasks[1]["due_at"]
    assert any("desk: deadline" in failure for failure in evaluate(CONDITIONAL, tasks)["failures"])


def test_explicit_origin_and_attribution():
    tasks = output(LONG)
    tasks[2]["first_step"], tasks[3]["first_step"] = tasks[3]["first_step"], tasks[2]["first_step"]
    assert sum("wrong task" in failure for failure in evaluate(LONG, tasks)["failures"]) == 2
    tasks = output(REPEATED)
    tasks[0]["first_step_origin"] = "suggested"
    assert any("origin" in failure for failure in evaluate(REPEATED, tasks)["failures"])


def test_project_addition_separate_or_explicitly_merged_not_generic():
    tasks = output(LONG)[:-1]
    assert any("project_addition" in failure for failure in evaluate(LONG, tasks)["failures"])
    tasks[4]["title"] = "Update resume and add project to resume"
    result = evaluate(LONG, tasks)
    assert not result["failures"]
    assert result["matches"]["resume"] == [4]
    assert not any(item["category"] in ("identity", "missing_identity", "project_addition")
                   for item in result["manual_review"])


def test_project_addition_can_be_preserved_in_resume_step():
    tasks = output(LONG)[:-1]
    tasks[4]["first_step"] = "Add the project to my resume"
    tasks[4]["first_step_origin"] = "suggested"
    assert not evaluate(LONG, tasks)["failures"]


def test_unfamiliar_explicit_wording_needs_review():
    tasks = output(REPEATED)
    tasks[0]["first_step"] = "Locate the bill in your inbox"
    result = evaluate(REPEATED, tasks)
    assert any(item["category"] == "explicit_wording" for item in result["manual_review"])


@pytest.mark.parametrize("step", ["check the fridge", "check the fridge first"])
def test_groceries_valid_variants_keep_origin_and_attribution_strict(step):
    tasks = output(LONG)
    tasks[2]["first_step"] = step
    result = evaluate(LONG, tasks)
    assert not result["failures"]
    assert not any(item["category"] == "explicit_wording" for item in result["manual_review"])
    tasks[2]["first_step_origin"] = "suggested"
    assert "groceries: explicit first-step origin" in evaluate(LONG, tasks)["failures"]
    tasks[2]["first_step_origin"] = "explicit"
    tasks[2]["first_step"], tasks[3]["first_step"] = tasks[3]["first_step"], tasks[2]["first_step"]
    failures = evaluate(LONG, tasks)["failures"]
    assert "groceries: explicit first step attributed to wrong task" in failures
    assert "application: explicit first step attributed to wrong task" in failures


def test_groceries_allowance_does_not_generalize_or_erase_laundry_failure():
    tasks = output(LONG)
    tasks[2]["first_step"] = "check the fridge first"
    result = evaluate(replace(LONG, id="different_fixture"), tasks)
    assert any(item["category"] == "explicit_wording" for item in result["manual_review"])
    tasks[0].update(first_step="hang it up", first_step_origin="explicit")
    assert "laundry: unsupported explicit origin" in evaluate(LONG, tasks)["failures"]
    tasks[3]["first_step"] += " first"
    result = evaluate(LONG, tasks)
    assert any(item["category"] == "explicit_wording" and item["task"] == 3
               for item in result["manual_review"])


def test_importance_anchor_and_schema():
    tasks = output(CONDITIONAL)
    tasks[1]["importance"] = "normal"
    assert any("importance" in failure for failure in evaluate(CONDITIONAL, tasks)["failures"])
    tasks[1]["status"] = "done"
    assert evaluate(CONDITIONAL, tasks)["status"] == "fail"


def test_reports_capture_all_attempts_raw_models_errors_and_fingerprints(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-only")
    monkeypatch.setenv("OPENAI_MODEL", "mock-configured")
    replies = [
        {"status": "completed", "model": "mock-returned", "output": [{
            "type": "message", "content": [{"type": "output_text",
                "text": json.dumps({"tasks": output(REPEATED)})}]}]},
        {"error": {"message": "synthetic provider error"}},
    ]

    def post(client, url, **kwargs):
        body = replies.pop(0)
        return httpx.Response(503 if "error" in body else 200, json=body,
                              request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.Client, "post", post)
    first = run_attempt(REPEATED, tmp_path)
    second = run_attempt(REPEATED, tmp_path)
    assert first["returned_models"] == ["mock-returned"]
    assert first["configured_model"] == "mock-configured"
    assert len(first["prompt_sha256"]) == len(first["schema_sha256"]) == 64
    assert first["latency_seconds"] >= 0
    assert second["provider_error"] and second["evaluation"]["status"] == "error"
    assert second["raw_responses"][0]["http_status"] == 503
    assert len(list(tmp_path.glob("*/attempt.json"))) == 2
    assert len(list(tmp_path.glob("*/manual-review.json"))) == 2
    assert "offline-test-only" not in "".join(path.read_text() for path in tmp_path.glob("*/*.json"))
