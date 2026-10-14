"""Opt-in runner: python -m evaluation.run --live --output PATH [--attempts 1]."""
import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx

from app.extraction import EXTRACTION_SCHEMA, SYSTEM_PROMPT, extract_tasks
from app.models import ExtractRequest
from .evaluator import evaluate
from .fixtures import FIXTURES, REFERENCE, ZONE


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def run_attempt(fixture, output):
    attempt_id = str(uuid4())
    directory = Path(output) / attempt_id
    directory.mkdir(parents=True, exist_ok=False)
    record = {
        "attempt_id": attempt_id, "test_id": fixture.id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "configured_model": os.getenv("OPENAI_MODEL"),
        "prompt_sha256": fingerprint(SYSTEM_PROMPT),
        "schema_sha256": fingerprint(EXTRACTION_SCHEMA),
        "fixture_sha256": fingerprint(fixture.text),
        "reference": REFERENCE, "timezone": ZONE, "input": fixture.text,
        "raw_responses": [], "tasks": None, "provider_error": None,
    }
    # Save metadata before the request so interrupted attempts are still visible.
    target = directory / "attempt.json"
    target.write_text(json.dumps(record, indent=2, ensure_ascii=False))
    original_post = httpx.Client.post

    def capture(client, *args, **kwargs):
        response = original_post(client, *args, **kwargs)
        try:
            body = response.json()
        except ValueError:
            body = response.text
        record["raw_responses"].append({"http_status": response.status_code, "body": body})
        target.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        return response

    start = time.perf_counter()
    try:
        with patch.object(httpx.Client, "post", capture):
            tasks = extract_tasks(ExtractRequest(brain_dump=fixture.text, timezone=ZONE),
                                  now=datetime.fromisoformat(REFERENCE))
        record["tasks"] = [task.model_dump(mode="json") for task in tasks]
        record["evaluation"] = evaluate(fixture, record["tasks"])
    except Exception as error:
        record["provider_error"] = {"type": type(error).__name__, "message": str(error)}
        record["evaluation"] = {"status": "error", "failures": [], "manual_review": []}
    finally:
        record["latency_seconds"] = time.perf_counter() - start
        record["returned_models"] = [item["body"].get("model") for item in record["raw_responses"]
                                     if isinstance(item["body"], dict)]
        target.write_text(json.dumps(record, indent=2, ensure_ascii=False))
        (directory / "manual-review.json").write_text(json.dumps({
            "test_id": fixture.id, "attempt_id": attempt_id,
            "reviewer": None, "decision": "pending",
            "items": record.get("evaluation", {}).get("manual_review", []),
        }, indent=2, ensure_ascii=False))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", required=True)
    parser.add_argument("--attempts", type=int, default=1)
    args = parser.parse_args()
    if not args.live or args.attempts < 1:
        parser.error("Explicit --live and positive --attempts required; each case makes a paid call.")
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("OPENAI_MODEL"):
        parser.error("OPENAI_API_KEY and OPENAI_MODEL must already be configured.")
    records = [run_attempt(fixture, args.output)
               for _ in range(args.attempts) for fixture in FIXTURES]
    print(json.dumps([{"test_id": r["test_id"], "attempt_id": r["attempt_id"],
                       "status": r["evaluation"]["status"]} for r in records], indent=2))
    return int(any(r["evaluation"]["status"] in ("error", "fail") for r in records))


if __name__ == "__main__":
    raise SystemExit(main())
