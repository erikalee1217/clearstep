# Task extraction evaluations

Use these evaluations to check how ClearStep turns a brain dump into tasks,
deadlines, and first steps. Run the commands below from `backend/` after setting
up the project's Python environment.

## Run the offline tests

```sh
.venv/bin/python -m pytest tests/test_release_evaluation.py -q
```

These tests use sample outputs and mocked HTTP responses to check the evaluator
and reporting code. They make no API calls.

## Running live semantic evaluations

Set `OPENAI_API_KEY` and `OPENAI_MODEL` in your environment before running either
command. Both live runs make billable API requests.

### Run the 45-case suite with pytest

```sh
RUN_LIVE_EXTRACTION=1 .venv/bin/python -m pytest \
  -p evaluation.pytest_reporting --semantic-report \
  tests/test_extraction_semantics.py tests/test_first_step_semantics.py -v
```

Pytest reports which assertions failed. The optional reporting plugin writes an
`attempt.json` for each executed case under
`backend/.semantic-reports/<run-id>/<attempt-id>/`. Use it to inspect the parsed
tasks, model, prompt and schema fingerprints, response, token usage, and latency.
It redacts recognized credentials and reports recording errors separately from
test failures.

### Run the three release scenarios

```sh
.venv/bin/python -m evaluation.run --live --output /absolute/path/to/results
```

The default run makes one request per scenario. Use `--attempts N` to run each
scenario `N` times. The runner uses a fixed reference date and timezone so
relative deadlines can be compared across runs.

Each case attempt gets its own directory. Open `attempt.json` for the captured
response, parsed tasks, and automated findings. Open `manual-review.json` for
items that need a closer look. Keep both live suites' reports local because they
can contain input text and model output.

## Review a result

Start with failures the evaluator can identify, such as missing or duplicate
tasks, incorrect deadlines, or first steps attached to the wrong task. For items
flagged for review, compare the output against the original brain dump. Check
for valid paraphrases, preserved conditions and durations, justified importance,
and first steps that help the user get started.

The release runner can exit with code 0 while review items are still pending.
Resolve those items before treating the run as a pass. If a deadline is flagged,
check whether different timezone offsets represent the same instant.
