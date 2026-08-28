---
kind: action-skill
id: portable-implement-feature
version: 2
title: Feature Implementation Conformance Review
description: Portable implementation-conformance review of supplied Business Central specification and plan artifacts; it does not define scaffold governance.
inputs: [repository, deployment-context]
outputs: [findings-report]
bc-version: [all]
technologies: [al]
countries: [w1]
application-area: [all]
---

# Feature Implementation Conformance Review

Reviews implementation conformance at the end of implementation and before Test. The repository input must identify the implementation change, feature specification, technical plan, task list, project constraints, target Business Central context, and assigned object ID range. Supply `deployment-context` when the implementation changes schema and deployment-dependent migration coverage is in scope; without it, the skill omits those checks. It does not audit test completion, verifier execution, documentation, roadmap state, pull-request metadata, or deployment approval. Return `not-applicable` when the core implementation bundle cannot be identified.

## Source

Read the live BCQuality knowledge index and take entries relevant to the changed implementation from every enabled layer, especially `process`, `performance`, `privacy`, `security`, `style`, `ui`, and `upgrade`. The skill checks conformance, not general code quality: load only articles needed to validate a specification, plan, or supplied project constraint. Uncited conformance gaps may be emitted only as agent findings under the `Implementation Conformance` domain.

## Relevance

Apply READ's frontmatter matching rules using the implementation's target BC version, technologies, countries, and application areas. Deployment-dependent upgrade articles are relevant only when the supplied released baseline or deployment context proves that the affected schema shipped or may contain persisted production data. When the schema is unreleased, apply the corresponding negative knowledge and do not require migration. When release status is unknown, omit deployment-dependent migration findings.

## Worklist

Review only implementation conformance:

- Every implemented behaviour is within specification scope and each acceptance criterion has a corresponding implementation path.
- Implemented objects, extensions, integrations, permissions, and telemetry match the technical plan or carry an explicit plan amendment supplied in the bundle.
- New object IDs are inside the assigned range and do not collide with planned allocations.
- Planned standard Business Central reuse has not been replaced by unexplained custom code.
- Schema migration code is required only where the released baseline or deployment context establishes persisted production data or a shipped contract.
- No planned object or required cross-cutting implementation item is absent from the change.

Do not inspect whether tests pass or exist, whether separate reviewers ran, whether documentation or roadmap files changed, or whether a pull request links an artifact. Those are later workflow concerns, not implementation conformance.

## Action

For a knowledge-backed conformance defect, copy the opened article's repo-relative path verbatim into both `id` and `references[0].path`, select only article-supported severity and confidence, and set `domain` to `Implementation Conformance`.

For a concrete mismatch with no matching article, emit an agent finding with `references: []`, an `agent:`-prefixed stable id, `severity: minor`, confidence no higher than `medium`, `domain: Implementation Conformance`, and a self-contained recommendation. Never promote an uncited process or governance concern to `major` or `blocker`, and never assign it `high` confidence. Do not depend on local agent names, house-style documents, scaffold paths, or runtime skill names. Do not emit findings for satisfied requirements.

Return `completed` when implementation conformance and all context-supported checks were evaluated, `not-applicable` when required implementation or governing artifacts are missing, `no-knowledge` only when no applicable knowledge exists and no agent finding is emitted, and `partial` or `failed` as defined by DO. Missing deployment context reduces deployment-dependent coverage; it does not make unrelated conformance review inapplicable.

## Output

Output conforms to the DO output contract. Example agent finding:

```json
{
  "skill": { "id": "portable-implement-feature", "version": 2 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 1, "info": 0 },
    "coverage": { "worklist-size": 5, "items-evaluated": 5 }
  },
  "findings": [
    {
      "id": "agent:planned-object-not-implemented",
      "severity": "minor",
      "message": "The technical plan requires a permission set for the new processing codeunit, but the implementation bundle contains no corresponding permission-set change or plan amendment. Add the planned permission entry or amend the plan with the reason it is unnecessary.",
      "references": [],
      "confidence": "medium",
      "domain": "Implementation Conformance",
      "suggested-code-omission-reason": "the correct permission scope depends on the planned runtime entry points"
    }
  ],
  "suppressed": []
}
```
