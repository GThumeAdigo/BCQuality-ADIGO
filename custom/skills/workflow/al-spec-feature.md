---
kind: action-skill
id: portable-spec-feature
version: 2
title: Feature Specification Review
description: Portable review of a supplied Business Central feature specification; it checks scope and testability without defining scaffold governance.
inputs: [repository]
outputs: [findings-report]
bc-version: [all]
technologies: [al]
countries: [w1]
application-area: [all]
---

# Feature Specification Review

Reviews one feature specification before technical planning. The repository input must identify the feature specification and the project definition it is governed by, including business brief, technical design, target Business Central context, and relevant roadmap outcome. Filenames, approval markers, and document templates are consumer-defined. Return `not-applicable` when this review bundle cannot be identified.

## Source

Read the live BCQuality knowledge index and take entries in the `process` and `testing` domains across every enabled layer. Use them only for Business Central-specific requirements they actually define. Specification structure and clarity gaps without a matching article may be emitted only as agent findings under the `Feature Specification` domain.

## Relevance

Apply READ's frontmatter matching rules using the target BC version, technologies, countries, and application areas supplied with the feature context. Retain conditionally applicable articles only when configured. Findings affected by unknown context have confidence no higher than `medium` and identify the unknown dimension.

## Worklist

Review the supplied specification for:

- Consistency with project goals, non-goals, constraints, standard Business Central reuse decisions, and the relevant roadmap outcome.
- A concrete problem, affected users and roles, in-scope and out-of-scope behaviour, user flow, business data and rules, permissions, telemetry or observability needs, and open decisions.
- Acceptance criteria stated as observable outcomes with enough preconditions and expected results to be verified later.
- Ambiguities recorded explicitly rather than silently resolved by unsupported assumptions.
- Separation of behavioural requirements from implementation design; technical object allocation belongs in the later plan unless an object name is itself part of a public compatibility contract.

Open a knowledge article only after its indexed metadata enters the worklist. Resolve layer precedence per READ and record discarded articles in `suppressed`.

## Action

For a knowledge-backed finding, copy the opened article's repo-relative path verbatim to both `id` and `references[0].path`, select only severity and confidence supported by the article and evidence, and set `domain` to `Feature Specification`.

For a concrete gap with no matching article, emit an agent finding with `references: []`, an `agent:`-prefixed stable id, `severity: minor`, confidence no higher than `medium`, `domain: Feature Specification`, and a self-contained recommendation. Do not require a specific template, path, numbering convention, approval token, roadmap status word, or local runtime skill name. Do not emit findings for satisfied requirements.

Return `completed` when all worklist items were evaluated, `not-applicable` when the specification or governing context is missing, `no-knowledge` only when no applicable knowledge exists and no agent finding is emitted, and `partial` or `failed` as defined by DO.

## Output

Output conforms to the DO output contract. Example agent finding:

```json
{
  "skill": { "id": "portable-spec-feature", "version": 2 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 1, "info": 0 },
    "coverage": { "worklist-size": 6, "items-evaluated": 6 }
  },
  "findings": [
    {
      "id": "agent:acceptance-outcome-not-observable",
      "severity": "minor",
      "message": "The criterion says processing must be user-friendly but defines no observable result. Replace it with the user action, relevant preconditions, and the result the user or an automated check can observe.",
      "references": [],
      "confidence": "medium",
      "domain": "Feature Specification",
      "suggested-code-omission-reason": "the measurable outcome depends on a product decision"
    }
  ],
  "suppressed": []
}
```
