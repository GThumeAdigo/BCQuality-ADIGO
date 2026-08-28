---
kind: action-skill
id: al-obsolete-tracker
version: 1
title: AL obsolete marking audit
description: Audits Obsolete markings on AL objects for reason, tag, removal plan, and progress, and emits a findings report.
inputs: [object-list, repository, pr-diff, deployment-context]
outputs: [findings-report]
bc-version: [all]
technologies: [al]
countries: [w1]
application-area: [all]
---

# AL obsolete marking audit

Walks the AL source for every `ObsoleteState` marking and reports whether each is well-formed and progressing toward removal. Every object, field, procedure, or enum value marked `ObsoleteState = Pending` should carry a clear `ObsoleteReason`, an `ObsoleteTag` encoding a target removal version, and a planned removal path. The skill flags orphans (Pending with no plan), broken removals (Removed with no prior Pending cycle), and abandoned obsolescence (Pending for several majors with no progress). It sources from the `upgrade` knowledge domain and cites curated obsoletion guidance where present; the hygiene checks the corpus does not encode are agent findings within its obsolescence domain. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with an `object-list`, a `repository`, or a `pr-diff`. Supply `deployment-context` when a finding depends on prior released states, removal timing, or persisted data; without it, review only the markings visible in the supplied source and omit deployment-dependent lifecycle findings. It produces a single JSON document conforming to the DO output contract.

## Source

Read the BCQuality knowledge index once (the `knowledge-index.json` Entry's preparation step regenerates over the live, already-filtered clone). Take the index entries whose `domain` is `upgrade` as the citable candidate set across every enabled layer: obsoletion requires a reason and a tag, an enum value made obsolete must keep its ordinal with the new value appended, and the Pending-to-Removed staging cycle each map onto a curated rule and MUST cite it rather than be paraphrased. Do not open individual article files at this step; open an article's full body only once it enters the Worklist below. The progress and orphan checks (Pending extending beyond two majors, a Pending symbol with live internal callers, removal versions that do not converge) are mostly not encoded; for those concrete defects, emit an agent finding within this skill's obsolescence domain (see Action).

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version`: the target BC version from the branch `app.json`, or `unknown` if unavailable.
- `technologies`: `[al]`.
- `countries`: the consuming app's declared countries, or `unknown`.
- `application-area`: the application areas of the changed objects, or `unknown`.

Discard files that are not applicable. Retain conditionally applicable files (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium`, and the finding `message` names the unknown dimensions.

## Worklist

Narrow to the obsolescence markings under review:

- Every `ObsoleteState` property on tables, table extensions, fields, codeunits, procedures, pages, page extensions, enums, enum values, reports, queries, and xmlports in the supplied `object-list` or `repository`. When a `pr-diff` is the input, narrow to markings the diff adds or changes.
- `Pending` markings missing an `ObsoleteReason`, missing an `ObsoleteTag` with a removal version, or carrying a generic reason such as "Deprecated".
- `Removed` markings with no prior `Pending` cycle only when the supplied released baseline establishes the prior public state.
- `Pending` markings that have extended across supplied released baselines, `Pending` symbols still called from inside the extension, `Pending` procedures whose reason names no replacement, obsoleted enum values whose ordinal moved, and removal versions that do not converge on a declared target. Do not infer release age from an `ObsoleteTag` alone.
- Migration or data-loss concerns only when `deployment-context` establishes that the affected element shipped or may hold persisted data. If the element is unreleased, apply the matching negative knowledge and do not require a migration path; if release status is unknown, omit the deployment-dependent finding.
- Compatibility-relevant removals and ordinal/signature changes require the supplied released baseline. If one is missing, retain those checks as unevaluated and return `partial` rather than clean.

A curated `upgrade` file enters the worklist when its `keywords` intersect these tokens (for example `obsolete`, `obsoletion`, `enum`, `staging`, `removal`). Read its full body only after it makes the worklist. Resolve layer-precedence conflicts per READ and record dropped files in `suppressed`.

## Action

Evaluate each marking and emit a finding only for a concrete violation.

When a defect maps onto a curated `upgrade` rule (a Pending with no reason or tag, an obsoleted enum value whose ordinal changed, or a Removed state proven by the released baseline to have skipped Pending), emit a knowledge-backed finding citing that file: `id` equal to the file path, the file as primary reference, `severity` up to `blocker` only when the file states a platform-level guarantee otherwise `major`, `confidence` `high` for an unambiguous match.

When a concrete hygiene defect has no curated rule (Pending abandoned for several majors, a Pending symbol with live internal callers, a Pending procedure whose reason names no migration path, removal versions that do not converge), emit an agent finding within this skill's obsolescence domain: `references: []`, `id` slug prefixed `agent:` (for example `agent:obsolete-pending-with-live-callers`), `confidence` capped at `medium`, `severity` capped at `minor`, and a self-contained `message` describing the hygiene gap and a concrete fix (migrate the internal callers in this PR, commit to a removal version). Where the impact would normally gate, keep `severity` at `minor` but say so plainly in the `message` and note the concern should be promoted to a knowledge-backed rule before it can gate. Hold every candidate to the precision bar in `skills/do.md`: steelman that the long-lived Pending is a deliberate, documented deferral before emitting, and omit when in doubt. Before emitting any agent candidate, check the worklisted knowledge for a match and upgrade it to a knowledge-backed finding if one exists.

Set `domain` to `Obsolescence` on every finding. Set `suggested-code` when the fix is mechanical (adding an `ObsoleteTag` line next to an existing `ObsoleteReason` using the supplied release target); otherwise set `suggested-code-omission-reason` (for example `requires migrating internal callers across multiple files`). Do not emit findings for satisfied rules; compliant worklist items contribute only to coverage.

Outcome selection: `completed` when every marking and applicable compatibility check was evaluated; `not-applicable` when the task has no obsolescence markings; `partial` when compatibility applies but the released baseline or required deployment context is missing; `failed` when supplied baseline evidence cannot be read. Missing baseline evidence cannot produce a clean result.

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "al-obsolete-tracker", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 1, "minor": 0, "info": 0 },
    "coverage": { "worklist-size": 8, "items-evaluated": 8 }
  },
  "findings": [
    {
      "id": "microsoft/knowledge/upgrade/obsoletion-requires-reason-and-tag.md",
      "severity": "major",
      "message": "Field 20 Old Reference No. on table Event Log has ObsoleteState = Pending and an ObsoleteReason but no ObsoleteTag, so no removal version is planned. Add an ObsoleteTag naming the next major in which the field is removed.",
      "location": {
        "file": "src/EventLog.Table.al",
        "line": 54
      },
      "references": [
        { "path": "microsoft/knowledge/upgrade/obsoletion-requires-reason-and-tag.md" }
      ],
      "confidence": "high",
      "domain": "Obsolescence",
      "suggested-code": "            ObsoleteTag = '2.0.0';"
    }
  ],
  "suppressed": []
}
```
