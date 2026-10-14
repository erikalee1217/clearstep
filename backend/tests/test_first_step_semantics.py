"""Opt-in live checks. Printed suggestions also require qualitative review.

RUN_LIVE_EXTRACTION=1 .venv/bin/pytest tests/test_first_step_semantics.py -v -s
"""
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.extraction import extract_tasks
from app.models import ExtractRequest

pytestmark = [pytest.mark.live, pytest.mark.skipif(
    os.getenv("RUN_LIVE_EXTRACTION") != "1", reason="Opt-in paid semantic evaluation.",
)]

# None permits conservative omission; 'omit' expects missing-context omission.
CASES = [
    ("application", "Submit my application; the form is online.", None),
    ("resume", "Finish my current resume draft.", None),
    ("interview", "Prepare examples for my interview.", None),
    ("slides", "Prepare slides for my presentation.", None),
    ("desk", "Clean my desk.", None),
    ("portfolio", "Work on my portfolio.", None),
    ("email", "Draft an email to my landlord about the leaking tap.", None),
    ("packing", "Pack my suitcase for the trip.", None),
    ("reading", "Read the assigned chapter.", None),
    ("missing_context", "Fix the issue we discussed.", "omit"),
    ("explicit_broad", "Finish the application. First gather all materials and complete the submission.", "gather all materials and complete the submission"),
    ("explicit_small", "Finish my resume. First open my current draft.", "open my current draft"),
    ("resume_no_draft", "Finish my resume.", None),
    ("already_small", "Open the application form.", "omit"),
    ("direct_action", "Read the next two pages of my assigned chapter.", "omit"),
    ("no_extra_planning", "Put the dirty mug in the dishwasher.", "omit"),
]


@pytest.mark.parametrize("name,text,expected", CASES, ids=[case[0] for case in CASES])
def test_first_steps(name, text, expected):
    tasks = extract_tasks(ExtractRequest(brain_dump=text, timezone="Asia/Taipei"),
                          now=datetime(2026, 10, 6, 10, tzinfo=ZoneInfo("Asia/Taipei")))
    print(json.dumps({"case": name, "tasks": [task.model_dump(mode="json") for task in tasks]}))
    assert len(tasks) == 1
    task = tasks[0]
    if expected == "omit":
        assert task.first_step is None and task.first_step_origin is None
    elif expected:
        assert task.first_step_origin == "explicit"
        # A retained discourse marker/punctuation does not rewrite the action.
        assert task.first_step.removeprefix("First ").removesuffix(".") == expected
    else:
        assert task.first_step_origin in ("suggested", None)


def test_mixed_explicit_and_suggested():
    tasks = extract_tasks(ExtractRequest(
        brain_dump="Finish my resume. First open my current draft. Also pack my suitcase for the trip.",
        timezone="Asia/Taipei"), now=datetime(2026, 10, 6, 10, tzinfo=ZoneInfo("Asia/Taipei")))
    print(json.dumps({"case": "mixed", "tasks": [task.model_dump(mode="json") for task in tasks]}))
    assert len(tasks) == 2
    explicit = [task for task in tasks if task.first_step_origin == "explicit"]
    assert len(explicit) == 1
    assert explicit[0].first_step.removeprefix("First ").removesuffix(".") == "open my current draft"
    assert all(task.first_step_origin in ("explicit", "suggested", None) for task in tasks)
