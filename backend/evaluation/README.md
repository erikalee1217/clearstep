# Release semantic fixtures

## Existing 45-case baseline reporting

No calls are made by loading this plugin. Both explicit reporting and the existing
live-test opt-in are needed for a recorded paid run. From backend, load the
existing environment without printing credentials, then run:

```sh
set -a
source .env
set +a
RUN_LIVE_EXTRACTION=1 .venv/bin/python -m pytest \
  -p evaluation.pytest_reporting --semantic-report \
  tests/test_extraction_semantics.py tests/test_first_step_semantics.py -v
```

Reports go to gitignored backend/.semantic-reports/<run UUID>/<attempt UUID>/attempt.json.
Every run and executed live case gets fresh IDs. Repeated calls within a case are
retained in its calls array; the plugin never initiates or retries a call.
Records include input, reference timestamp/timezone, configured model,
prompt/schema fingerprints, raw response body/status, returned model, usage,
parsed tasks, call latency, errors, and pytest call/teardown outcomes.

Categories distinguish semantic_assertion, provider_api, response_validation,
unexpected_extraction and test_error. Instrumentation errors are a separate list
and terminal warning; they never replace the original pytest outcome.
If filesystem writes fail completely, the warning is the only surviving evidence.
Skipped/setup-failed cases have no extraction attempt; pytest's standard summary
remains authoritative for collection and setup failures.

Credentials are redacted using sensitive field names, known secret environment
values, and standard bearer/API-key patterns. No request headers, environment
dump, traceback source or locals are stored. Raw bodies are therefore redacted
copies, not byte-identical archival responses. Review artifacts as sensitive local
data regardless. Assertion messages are retained, not full traceback source.
Do not use pytest --showlocals or redirect unfiltered pytest console output to
an artifact if it might contain secrets from third-party exception rendering.

Reporting is synchronous/sequential for the current suite. These reports do not
manually adjudicate subjective suggestions. A failed assertion still fails, and
a provider error is re-raised without repair. Production extraction and existing
semantic test assertions are unchanged.

This evaluation-only package does not alter production prompts, schema, model
configuration, ranking, or the original 45 live tests.

## Offline checks

From backend:

```sh
.venv/bin/python -m pytest tests/test_release_evaluation.py -q
```

The checks use synthetic outputs and mocked HTTP responses. They are not
evidence of live model quality.

## Paid execution (only after approval)

Use an already configured OPENAI_API_KEY and OPENAI_MODEL:

```sh
.venv/bin/python -m evaluation.run --live --output /absolute/path/to/results
```

One execution makes three calls. --attempts N makes 3*N calls without retries.
The original 45-case suite remains separate; running it plus these cases is
48 calls. Two extra runs of an approved ten-case risk subset would total 68
calls; this runner does not implement that combined orchestration.

Each attempt gets a UUID directory, attempt.json and manual-review.json.
Metadata is written before requesting; raw response bodies are written before
validation. Final reports include parsed tasks, configured/returned model IDs,
prompt/schema/input fingerprints, reference date/timezone, elapsed time,
errors, identity matches, strict failures and manual-review items.
Never overwrite earlier attempts. No request headers or API keys are recorded.
Raw outputs may contain user input; keep reports local. An interrupted attempt
may have only the initial metadata/raw response and no final evaluation.

The fixed reference for these three fixtures is October 12, 2026, 10:00 Taipei.
The original suite retains its October 6 reference. Fixtures contain no runtime
relative expectations.

## Acceptance and manual review

Identity aliases are action/object heuristics, not an LLM judge. Output order
is irrelevant. Recognized omissions, duplicate identities, forbidden tasks,
deadline errors, known cross-task explicit-step leakage, origin errors and
unambiguous importance errors fail. Unknown titles or unfamiliar explicit-step
wording require review. When unknown outputs exist, unmatched required
identities also remain pending: a valid paraphrase may explain the mismatch.
No pending result is a release pass. CLI exit 0 means no strict/provider failure,
not manual approval.

Reviewers must resolve every identity/omission ambiguity and check exact
original intent, including twenty-minute duration and conditional plans.
Suggested-step quality and borderline importance are separate review items.
Quote evidence for high importance; deadlines alone do not justify it.
Conservative null suggestions are allowed where useful steps cannot be grounded.
Long-form project addition must be separate or explicit in the resume title/step.
Check that merged tasks do not silently omit part of a commitment.

Due timestamps currently compare serialized strings exactly, consistent with
the existing semantic suite. An equivalent UTC representation can therefore
require adjudication rather than indicating a wrong instant.
