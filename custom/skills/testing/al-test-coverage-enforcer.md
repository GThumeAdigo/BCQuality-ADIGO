---
kind: action-skill
id: al-test-coverage-enforcer
version: 1
title: AL test coverage enforcer
description: Hard coverage gate, passing only when AL coverage meets the threshold and otherwise naming every uncovered path.
inputs: [pr-diff, repository]
outputs: [findings-report]
bc-version: [all]
technologies: [al, xml, json]
countries: [w1]
application-area: [all]
---

# AL test coverage enforcer

Enforces a configured hard coverage-tool threshold and separately reports statically inferred coverage gaps. A parsed threshold failure is gating deterministic evidence; source-inferred gaps remain capped agent or cited knowledge findings. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with a `pr-diff` (the production change to gate) and a `repository` (so the test index and any coverage report can be read). It produces a single JSON document conforming to the DO output contract.

## Source

Read the BCQuality knowledge index once (the `knowledge-index.json` Entry's preparation step regenerates over the live, already-filtered clone). Take the index entries whose `domain` is `testing` as the citable candidate set across every enabled layer: a curated rule about a coverage threshold or a mandatory regression test is the authoritative basis that lets this skill gate at `major` or `blocker`. Do not open individual article files at this step; open an article's full body only once it enters the Worklist below. Where the project threshold is a house default with no curated backing, see Action for how severity is handled.

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version`: the target BC version from the repository `app.json`, or `unknown` if unavailable.
- `technologies`: the intersection of `[al, xml, json]` present in source and coverage artifacts.
- `countries`: the consuming app's declared countries, or `unknown`.
- `application-area`: the application areas of the changed objects, or `unknown`.

Discard files that are not applicable. Retain conditionally applicable files (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium`, and the finding `message` names the unknown dimensions.

## Worklist

Narrow to the production surfaces the threshold applies to:

- New public procedures (default threshold: every one must have at least one direct or indirect covering test, no exceptions).
- New event subscribers (must have a test that fires the publisher in a realistic context).
- New table triggers (`OnInsert`, `OnModify`, `OnDelete`, field `OnValidate`): each must have a covering test.
- Modified procedures with a behaviour change: an existing or new test must assert the new behaviour. A behaviour change whose existing tests still pass unchanged is itself a gap (the tests do not exercise the new behaviour).
- Bug fixes: must add a regression test that names the bug and fails without the fix.
- Pure refactors with no behaviour change: existing covering tests must still apply; no new test required.

Compute the covering set from the test index (procedure to referencing tests) and any supplied coverage report. A curated `testing` file enters the worklist when its `keywords` intersect a coverage-threshold rule. Read its full body only after it makes the worklist. Resolve layer-precedence conflicts per READ and record dropped files in `suppressed`.

## Action

For each worklisted surface, decide PASS or FAIL against the configured threshold. When a named coverage tool directly reports that a hard threshold failed, emit `evidence:coverage-threshold-failed` with a stable `<app-id-or-scope>/line-coverage` occurrence key, `evidence.kind: coverage-tool`, the tool/report in `source`, `status: threshold-failed`, `gating: true`, `severity: blocker`, and `confidence: high`. Static model inference is not evidence. A separate knowledge-backed finding may explain a rule but MUST NOT be merged with the threshold evidence. Put passing evidence in `summary.coverage-execution`.

When hard coverage enforcement is required but no fresh, parseable coverage report is supplied, return `outcome: partial` with `outcome-reason`; do not claim the gate passed and do not fabricate evidence. Static analysis may still produce capped agent findings, but cannot satisfy or fail the hard coverage-tool gate.

Outcome selection: `completed` when every worklisted surface was decided (an empty `findings` array means PASS, the gate is satisfied); `not-applicable` when the diff has no new or behaviour-changed production surface (a pure refactor or doc-only change); `partial` or `failed` per the DO contract with `outcome-reason`.

## Output

Output conforms to the DO output contract. An empty `findings` array with `outcome: completed` and `summary.coverage-execution.status: passed` is the PASS signal. A failed hard tool threshold is gating deterministic evidence.

```json
{
  "skill": { "id": "al-test-coverage-enforcer", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 1, "major": 0, "minor": 0, "info": 0 },
    "coverage": { "worklist-size": 3, "items-evaluated": 3 },
    "coverage-execution": { "status": "failed", "source": "AL test tool/coverage.json", "percentage": 72.4, "threshold": 80.0, "covered": 181, "total": 250 }
  },
  "findings": [
    {
      "id": "evidence:coverage-threshold-failed",
      "occurrence-key": "event-registration-app/line-coverage",
      "severity": "blocker",
      "message": "AL test tool reported 72.4% line coverage (181 of 250 lines) against the configured hard threshold of 80.0%.",
      "references": [],
      "confidence": "high",
      "evidence": { "kind": "coverage-tool", "source": "AL test tool/coverage.json", "status": "threshold-failed" },
      "gating": true,
      "suggested-code-omission-reason": "the gap is closed by adding a covering test"
    }
  ],
  "suppressed": []
}
```
