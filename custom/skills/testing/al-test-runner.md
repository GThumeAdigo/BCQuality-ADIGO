---
kind: action-skill
id: al-test-runner
version: 1
title: AL test runner
description: Executes AL test codeunits via the AL-Go runner or a local container and returns the run result as a findings report.
inputs: [repository, object-list]
outputs: [findings-report]
bc-version: [all]
technologies: [al, powershell, xml, json]
countries: [w1]
application-area: [all]
---

# AL test runner

Executes Business Central AL test codeunits and reports the run result in a shape the rest of the verifier chain can consume. It detects the project's runner (AL-Go pipeline, a Docker BC sandbox via BcContainerHelper, or a project-local build script), invokes it, parses the XUnit-style results, and maps each failure to a finding. It does not judge coverage (that is `al-test-coverage-validator` and `al-test-coverage-enforcer`), test quality (that is `al-test-validator`), or write tests (that is `al-test-writer`). This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with a `repository` (the project root to run in) and optionally an `object-list` (a filter narrowing the run to specific test codeunits). It produces a single JSON document conforming to the DO output contract.

## Source

Read the BCQuality knowledge index once. Take the index entries whose `domain` is `testing` or `pipelines` as the citable candidate set across every enabled layer. Do not open individual articles until they enter the Worklist. A red test is direct `test-runner` evidence. A startup failure, timeout, unparseable result, or required-suite-without-runner result is direct `tool-envelope` evidence from runner invocation or deterministic runner discovery. None is an agent finding. A knowledge finding may separately explain a configuration defect but MUST NOT be merged with execution evidence.

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version`: the target BC version from the repository `app.json`, or `unknown` if unavailable.
- `technologies`: the intersection of `[al, powershell, xml, json]` present in tests, runner wiring, and result artifacts.
- `countries`: the consuming app's declared countries, or `unknown`.
- `application-area`: the application areas of the test objects, or `unknown`.

Discard files that are not applicable. Retain conditionally applicable files (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium`, and the finding `message` names the unknown dimensions.

## Worklist

Narrow to the run to perform and the artifacts it produces:

- Runner detection, in order: configured AL MCP `al_run_tests`; an AL-Go pipeline (`.AL-Go/settings.json` plus a `BuildALGoProject` script); a Docker BC sandbox via BcContainerHelper; a project-local test script.
- The test codeunits to run: every test codeunit in the repository, narrowed by the `object-list` filter when supplied.
- The results file the run emits (`TestResults.xml` or equivalent) and the runner console output.

A curated `testing` or `pipelines` file enters the worklist when its `keywords` intersect these tokens. Read its full body only after it makes the worklist. Resolve layer-precedence conflicts per READ and record dropped files in `suppressed`.

## Action

Invoke the detected runner with the project's standard arguments, capture its output and result artifact, and parse total, passed, failed, skipped, and not-executed counts. Put an explicit `summary.execution` object in every report. Emit one deterministic evidence finding per failed test with `id: evidence:test-failed` and a stable lower-case `occurrence-key` derived from `<test-codeunit-id-or-name>/<test-procedure>`; never include the run id or result-file path in that key. The evidence uses `kind: test-runner`, the named runner/report as source, `status: failed`, `gating: true`, `severity: blocker`, and `confidence: high` when attribution is unambiguous. A separate knowledge-backed finding may explain a configuration rule, but MUST NOT be merged with execution evidence.

If required execution cannot start, produces no parseable result, exceeds the configured timeout, or required tests exist but no runner is detected, return `failed` with a deterministic `evidence:required-test-execution-failed` blocker. Use the canonical `required-suite/<stable-suite-name-or-scope>` occurrence key, `evidence.kind: tool-envelope`, the attempted runner discovery/command as source, status `error` or `timeout`, and `gating: true`. A repository with no test codeunits remains `not-applicable`; a repository with required tests but no runner is never `not-applicable`. The runner owns pass/fail and never delegates it to coverage.

Outcome selection: `completed` when the run finished and every failure was mapped to a finding (including a green run with empty `findings`); `not-applicable` when the repository has no AL test codeunit or no runner could be detected; `partial` when the run was cancelled on timeout after some tests ran (`summary.coverage` reflects the executed subset); `failed` when the runner could not start, with `outcome-reason` required.

## Output

Output conforms to the DO output contract. Red tests and failed required execution are gating deterministic evidence. A green run has no evidence findings and records its passing counts in `summary.execution`.

```json
{
  "skill": { "id": "al-test-runner", "version": 1 },
  "outcome": "completed",
  "outcome-reason": "al-go-pipeline runner, 27 tests, 1 failed",
  "summary": {
    "counts": { "blocker": 1, "major": 0, "minor": 0, "info": 0 },
    "coverage": { "worklist-size": 27, "items-evaluated": 27 },
    "execution": { "status": "failed", "source": "al-go-pipeline/TestResults.xml", "total": 27, "passed": 25, "failed": 1, "skipped": 1, "not-executed": 0 }
  },
  "findings": [
    {
      "id": "evidence:test-failed",
      "occurrence-key": "codeunit-50202/releaseregistrationshouldfailwhenovercapacity",
      "severity": "blocker",
      "message": "al-go-pipeline reported Test ReleaseRegistrationShouldFailWhenOverCapacity in codeunit 50202 'Event Registration Tests' failed: expected error 'Capacity exceeded' but got 'Permission denied'.",
      "location": { "file": "test/EventRegistrationTests.al", "line": 88 },
      "references": [],
      "confidence": "high",
      "evidence": { "kind": "test-runner", "source": "al-go-pipeline/TestResults.xml", "status": "failed" },
      "gating": true,
      "suggested-code-omission-reason": "fix lives in the test or production source under change"
    }
  ],
  "suppressed": []
}
```
