import re

from app.extraction import ExtractionOutput
from .fixtures import LONG, PROJECT


def normalized(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def matches(expected, title):
    return any(re.search(alias, normalized(title)) for alias in expected.aliases)


def explicit_variants(fixture, expected):
    variants = {normalized(expected.explicit)}
    if fixture.id == LONG.id and expected.identity == "groceries":
        variants.add("check the fridge first")
    return variants


def evaluate(fixture, raw_tasks):
    failures, review = [], []
    try:
        tasks = ExtractionOutput.model_validate({"tasks": raw_tasks}).tasks
    except ValueError as error:
        return {"status": "fail", "failures": ["schema: " + str(error)], "manual_review": [], "matches": {}}
    found = {}
    unknown = []
    for index, task in enumerate(tasks):
        title = normalized(task.title)
        identities = [item for item in (*fixture.required, *fixture.optional) if matches(item, task.title)]
        if fixture.id == LONG.id and {item.identity for item in identities} == {"resume", "project_addition"}:
            identities = [item for item in identities if item.identity == "resume"]
        forbidden = any(re.search(pattern, title) for pattern in fixture.forbidden)
        if forbidden:
            failures.append(f"task[{index}]: forbidden task: {task.title}")
        if len(identities) != 1:
            unknown.append(index)
            review.append({"task": index, "category": "identity", "question":
                           "Unmatched or overlapping identity: valid paraphrase, merge, or invented task?"})
            continue
        expected = identities[0]
        found.setdefault(expected.identity, []).append(index)
        if len(found[expected.identity]) > 1:
            failures.append(f"{expected.identity}: duplicate")
        data = task.model_dump(mode="json")
        if (data["due_date"], data["due_at"]) != (expected.due_date, expected.due_at):
            failures.append(f"{expected.identity}: deadline precision/value or field attribution")
        step = task.first_step
        if expected.explicit:
            if not step:
                failures.append(f"{expected.identity}: missing explicit first step")
            elif task.first_step_origin != "explicit":
                failures.append(f"{expected.identity}: explicit first-step origin")
            elif normalized(step).removeprefix("first ") not in explicit_variants(fixture, expected):
                # Known steps belonging to another task are leakage, not paraphrase.
                other_steps = {variant for item in fixture.required
                               if item.explicit and item.identity != expected.identity
                               for variant in explicit_variants(fixture, item)}
                if normalized(step).removeprefix("first ") in other_steps:
                    failures.append(f"{expected.identity}: explicit first step attributed to wrong task")
                else:
                    review.append({"task": index, "category": "explicit_wording",
                                   "expected": expected.explicit, "actual": step,
                                   "question": "Preserved original wording/action, or rewritten/incomplete?"})
        elif task.first_step_origin == "explicit":
            failures.append(f"{expected.identity}: unsupported explicit origin")
        if expected.importance and task.importance != expected.importance:
            failures.append(f"{expected.identity}: importance expected {expected.importance}")
        if not expected.importance:
            review.append({"task": index, "category": "importance",
                           "question": "For high, quote meaningful consequence/significance; urgency alone is insufficient."})
        if task.first_step_origin == "suggested" or not step:
            review.append({"task": index, "category": "suggested_step",
                           "question": "Grounded, bounded, useful without extra work? Is omission appropriate?"})
        if expected.identity == "portfolio_decision":
            review.append({"task": index, "category": "conditional_plan",
                           "question": "Decision only, without converting tentative portfolio use into commitment?"})
    for expected in fixture.required:
        if expected.identity not in found:
            if unknown:
                review.append({"category": "missing_identity", "identity": expected.identity,
                               "question": "Does an unmatched output preserve this required commitment?"})
            else:
                failures.append(f"{expected.identity}: required commitment omitted")
    if fixture.id == LONG.id:
        represented = "project_addition" in found
        for index in found.get("resume", []):
            task = tasks[index]
            represented |= matches(PROJECT, task.title + " " + (task.first_step or ""))
        if not represented:
            if unknown:
                review.append({"category": "project_addition", "question": "Locate explicit project-to-resume commitment; generic resume updating is insufficient."})
            else:
                failures.append("project_addition: neither separate nor explicitly represented within resume")
        for index in found.get("walk", []):
            if not re.search(r"(20|twenty).*min", normalized(tasks[index].title)):
                review.append({"task": index, "category": "duration", "question": "Is the twenty-minute walking commitment preserved?"})
    return {"status": "fail" if failures else "manual_review" if review else "pass",
            "failures": failures, "manual_review": review, "matches": found}
