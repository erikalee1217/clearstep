from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.models import ConfirmedTask, DraftTask, RankRequest
from app.ranking import rank_tasks

ZONE = ZoneInfo("Asia/Taipei")
NOW = datetime(2026, 10, 6, 10, tzinfo=ZONE)


def task(number, **changes):
    data = dict(id=UUID(int=number), title=f"Task {number}", created_at=NOW - timedelta(days=1))
    data.update(changes)
    return ConfirmedTask(**data)


def order(*tasks):
    return [item.id.int for item in rank_tasks(list(tasks), NOW, ZONE)]


def step():
    return dict(first_step="Open the document", first_step_origin="suggested")


def test_five_examples():
    a = task(1, due_at=NOW.replace(hour=17), start_friction="high")
    b = task(2, importance="high", start_friction="low", created_at=NOW - timedelta(days=2), **step())
    c = task(3, importance="high", start_friction="low", due_date="2026-10-09", **step())
    d = task(4, importance="high", start_friction="low", due_date="2026-10-08", created_at=NOW - timedelta(days=5))
    e = task(5, start_friction="low", created_at=NOW - timedelta(days=6), **step())
    assert order(e, d, c, b, a) == [1, 4, 3, 2, 5]


@pytest.mark.parametrize("offset,expected", [(24, [1, 2]), (24.001, [2, 1]), (-1, [1, 2])])
def test_urgent_threshold(offset, expected):
    assert order(task(1, due_at=NOW + timedelta(hours=offset)), task(2, importance="high")) == expected


def test_urgent_deadline_precedes_importance():
    assert order(task(1, due_at=NOW + timedelta(hours=2)), task(2, due_at=NOW + timedelta(hours=3), importance="high", **step())) == [1, 2]


def test_date_only_today_and_overdue_are_urgent_but_tomorrow_is_not():
    assert order(task(1, due_date="2026-10-07"), task(2, importance="high"), task(3, due_date="2026-10-06"), task(4, due_date="2026-10-05")) == [4, 3, 2, 1]


def test_date_only_uses_local_end_of_day():
    assert order(task(1, due_date="2026-10-06"), task(2, due_at=NOW.replace(hour=23))) == [2, 1]


def test_importance_then_friction():
    assert order(task(1, **step(), start_friction="low"), task(2, importance="high"), task(3, importance="high", start_friction="high", **step()), task(4, importance="high", start_friction="low", **step())) == [4, 2, 3, 1]


def test_unknown_friction_equals_medium_not_low():
    assert order(task(1), task(2, start_friction="medium"), task(3, start_friction="low"), task(4, start_friction="high")) == [3, 1, 2, 4]


def test_deadline_then_age_then_input_order():
    assert order(task(4), task(3, created_at=NOW - timedelta(days=2)), task(2), task(1, due_date="2026-10-09")) == [1, 3, 4, 2]


def test_completed_excluded_and_empty_supported():
    assert order(task(1, status="done"), task(2)) == [2]
    assert order() == []


def test_timezone_equivalent_urgent_deadlines_preserve_input_order():
    a = task(1, due_at=NOW + timedelta(hours=1))
    b = task(2, due_at=(NOW + timedelta(hours=1)).astimezone(timezone.utc))
    assert order(a, b) == [1, 2]
    assert order(b, a) == [2, 1]


def test_exactly_seven_days_qualifies():
    dated = task(2, due_at=NOW + timedelta(days=7), created_at=NOW)
    assert order(task(1), dated) == [2, 1]
    assert "Due within 7 days" in rank_tasks([dated], NOW, ZONE)[0].reasons


@pytest.mark.parametrize("offset", [timedelta(days=7, microseconds=1), timedelta(days=21)])
def test_beyond_horizon_has_no_deadline_advantage(offset):
    dated = task(1, due_at=NOW + offset)
    undated = task(2)
    assert order(undated, dated) == [2, 1]
    assert order(dated, undated) == [1, 2]
    assert "Due within 7 days" not in rank_tasks([dated], NOW, ZONE)[0].reasons


def test_date_only_horizon_uses_local_end_of_day():
    assert order(task(1), task(2, due_date="2026-10-13"), task(3, due_date="2026-10-12")) == [3, 1, 2]


def test_fully_tied_batch_preserves_input_order():
    assert order(task(9), task(2), task(7)) == [9, 2, 7]


def test_uuid_changes_do_not_change_task_order():
    batch = [task(9, title="First"), task(2, title="Second"), task(7, title="Third")]
    def titles(items):
        names = {item.id: item.title for item in items}
        return [names[item.id] for item in rank_tasks(items, NOW, ZONE)]
    changed = [item.model_copy(update={"id": UUID(int=value)}) for item, value in zip(batch, [1, 8, 3])]
    assert titles(batch) == titles(changed) == ["First", "Second", "Third"]


def test_older_batch_keeps_age_advantage_and_internal_order():
    newer = [task(1, created_at=NOW), task(2, created_at=NOW)]
    older = [task(8), task(7)]
    assert order(*newer, *older) == [8, 7, 1, 2]


def test_near_deadlines_remain_after_importance_and_friction():
    dated = task(1, due_at=NOW + timedelta(days=2), start_friction="high")
    assert order(dated, task(2, importance="high")) == [2, 1]
    assert order(dated, task(2, start_friction="low")) == [2, 1]


@pytest.mark.parametrize("due_at", [None, NOW + timedelta(hours=2), NOW + timedelta(days=3)])
@pytest.mark.parametrize("origin", ["explicit", "suggested", "user"])
def test_adding_or_removing_first_step_does_not_affect_ranking(due_at, origin):
    a = task(9, due_at=due_at)
    b = task(2, due_at=due_at)
    with_step = a.model_copy(update={"first_step": "Open the document", "first_step_origin": origin})
    removed = with_step.model_copy(update={"first_step": None, "first_step_origin": None})
    for variant in (a, with_step, removed):
        assert order(variant, b) == [9, 2]
        assert order(b, variant) == [2, 9]


@pytest.mark.parametrize("due_at", [None, NOW + timedelta(hours=2)])
def test_atomic_task_keeps_age_and_input_order_advantages(due_at):
    atomic = task(9, title="Open the application form", due_at=due_at)
    equally_old = task(2, due_at=due_at, **step())
    newer = task(3, due_at=due_at, created_at=NOW, **step())
    assert order(newer, atomic) == [9, 3]
    assert order(atomic, equally_old) == [9, 2]


def test_near_deadline_beats_first_step_when_other_factors_match():
    assert order(task(1, **step()), task(2, due_at=NOW + timedelta(days=2))) == [2, 1]


@pytest.mark.parametrize("due_at", [None, NOW + timedelta(hours=2), NOW + timedelta(days=3)])
def test_first_step_does_not_affect_explanations(due_at):
    plain = task(1, due_at=due_at)
    with_step = task(1, due_at=due_at, **step())
    baseline = rank_tasks([plain], NOW, ZONE)[0].reasons
    result = rank_tasks([with_step], NOW, ZONE)[0].reasons
    assert result == baseline
    assert "Reviewed first step" not in result


def test_draft_cannot_enter_rank_request():
    with pytest.raises(ValidationError):
        RankRequest(tasks=[DraftTask(title="Draft").model_dump()], timezone="Asia/Taipei")


def test_duplicate_ids_and_invalid_timezone_rejected():
    with pytest.raises(ValidationError):
        RankRequest(tasks=[task(1), task(1)], timezone="Asia/Taipei")
    with pytest.raises(ValidationError):
        RankRequest(tasks=[], timezone="Invalid/Zone")


@pytest.mark.parametrize("changes", [dict(due_date="2026-10-06", due_at=NOW), dict(first_step="Open file"), dict(title="  "), dict(created_at=datetime(2026, 10, 6))])
def test_invalid_task_fields_rejected(changes):
    with pytest.raises(ValidationError):
        task(1, **changes)


def test_reason_comes_from_rules():
    result = rank_tasks([task(1, due_at=NOW - timedelta(hours=1))], NOW, ZONE)
    assert result[0].reasons == ["Overdue deadline"]
