---
kind: action-skill
id: portable-plan-feature
version: 2
title: Feature Plan Review
description: Portable review of supplied Business Central feature-plan artifacts; it checks traceability and AL feasibility without defining scaffold governance.
inputs: [repository, deployment-context]
outputs: [findings-report]
bc-version: [all]
technologies: [al]
countries: [w1]
application-area: [all]
---

# Feature Plan Review

Reviews the technical plan before implementation. The repository input must identify the feature specification, technical plan, task list, project constraints, assigned object ID range, and target Business Central context. Supply `deployment-context` when the plan changes schema and deployment-dependent migration coverage is in scope; without it, the skill omits those checks. Filenames and task syntax are consumer-defined. Return `not-applicable` when the core planning bundle is incomplete.

## Source

Read the live BCQuality knowledge index and take entries in the `process`, `performance`, `security`, `privacy`, and `upgrade` domains across every enabled layer. Use only opened articles as citable rules. Planning completeness without a matching article may be emitted only as an agent finding under the `Feature Plan` domain.

## Relevance

Apply READ's frontmatter matching rules using the plan's target BC version, technologies, countries, and application areas. Deployment-dependent upgrade articles are relevant only when the supplied released baseline or deployment context establishes that the affected schema has shipped and may contain persisted data. If the context establishes that the schema is unreleased, include the applicable negative knowledge and do not require migration. If release status is unknown, omit deployment-dependent findings rather than assuming persisted data.

## Worklist

Review the supplied plan for:

- Traceability from each planned behaviour to the feature specification and acceptance criteria.
- Explicit standard Business Central capabilities to reuse and justified custom AL gaps.
- An object inventory with type, purpose, new-or-extended status, and IDs inside the assigned range.
- Data model, integration boundaries, permissions, privacy, security, telemetry, performance, and failure-handling decisions that apply to the feature.
- Ordered, checkable implementation tasks that cover the planned objects and cross-cutting work without requiring a consumer-specific task format.
- Schema migration steps only for elements proven by the supplied baseline or deployment context to have shipped or to hold persisted production data.

Open each candidate article in full only after it enters the worklist. Resolve layer precedence per READ and record discarded articles in `suppressed`.

## Action

For a knowledge-backed defect, copy the opened article path verbatim into both `id` and `references[0].path`, use only article-supported severity and confidence, and set `domain` to `Feature Plan`.

For a concrete planning defect with no matching article, emit an agent finding with `references: []`, an `agent:`-prefixed stable id, `severity: minor`, confidence no higher than `medium`, `domain: Feature Plan`, and a concrete recommendation. Never infer that production data exists. Do not require named interfaces, prohibited properties, tests, documentation tasks, verifier passes, roadmap statuses, or local skill names unless an opened article or supplied project constraint establishes that requirement. Do not emit findings for satisfied requirements.

Return `completed` when the core planning bundle and all context-supported checks were evaluated, `not-applicable` when required planning artifacts are missing, `no-knowledge` only when no applicable knowledge exists and no agent finding is emitted, and `partial` or `failed` as defined by DO. Missing deployment context reduces deployment-dependent coverage; it does not make unrelated planning review inapplicable.

## Output

Output conforms to the DO output contract. Example knowledge-backed finding:

```json
{
  "skill": { "id": "portable-plan-feature", "version": 2 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 1, "minor": 0, "info": 0 },
    "coverage": { "worklist-size": 5, "items-evaluated": 5 }
  },
  "findings": [
    {
      "id": "custom/knowledge/process/al-map-each-feature-to-an-object-id-range.md",
      "severity": "major",
      "message": "The plan allocates table 60110 while the supplied feature range is 50100..50149. Allocate the object inside the reserved range before implementation.",
      "references": [
        { "path": "custom/knowledge/process/al-map-each-feature-to-an-object-id-range.md" }
      ],
      "confidence": "high",
      "domain": "Feature Plan",
      "suggested-code-omission-reason": "requires selecting an unused ID from the assigned range"
    }
  ],
  "suppressed": []
}
```
