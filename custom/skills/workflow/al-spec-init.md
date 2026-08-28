---
kind: action-skill
id: portable-spec-init
version: 2
title: Project Definition Review
description: Portable review of a supplied Business Central project definition; it checks completeness without defining scaffold initialization governance.
inputs: [repository]
outputs: [findings-report]
bc-version: [all]
technologies: [al]
countries: [w1]
application-area: [all]
---

# Project Definition Review

Reviews the durable project-level definition that guides later feature decisions. The repository input must identify the business brief, technical design, delivery roadmap, target Business Central version, localisation, application areas, and assigned object ID range. Filenames and document templates are consumer-defined. Return `not-applicable` when the orchestrator cannot identify this complete review bundle.

## Source

Read the live BCQuality knowledge index and take entries in the `process` domain across every enabled layer. These entries may support Business Central-specific planning constraints such as object ID allocation. Project-document structure and internal consistency are not BCQuality facts; a concrete defect without a matching article may be emitted only as an agent finding under the `Project Definition` domain.

## Relevance

Apply READ's frontmatter matching rules using the target BC version, technologies, countries, and application areas supplied with the project definition. Retain a conditionally applicable article only when consumer configuration permits. A finding affected by an unknown dimension has confidence no higher than `medium` and names that unknown in its message.

## Worklist

Review only evidence available in the supplied bundle:

- The business problem, intended users, goals, non-goals, constraints, and observable success measures.
- The technical design's standard Business Central capabilities to reuse, justified custom gaps, high-level data model, integrations, permissions, privacy, security, telemetry, performance, and upgrade considerations.
- The assigned object ID range and any allocation boundaries needed by later feature plans.
- The delivery roadmap's ordered outcomes, dependencies, and ownership, without requiring a particular numbering scheme, status vocabulary, folder layout, or filename.
- Contradictions, unsupported assertions, and unresolved decisions that materially prevent a feature from being specified.

Open a knowledge article in full only after its indexed metadata enters the worklist. Resolve layer precedence per READ and record discarded articles in `suppressed`.

## Action

For each concrete defect, first test whether an opened knowledge article defines it. A knowledge-backed finding MUST use the article's repo-relative path verbatim as both `id` and `references[0].path`, may use the article-supported severity and confidence, and MUST set `domain` to `Project Definition`.

When no article applies, emit only a conservative agent finding: `references: []`, an `agent:`-prefixed stable id, `severity: minor`, confidence no higher than `medium`, `domain: Project Definition`, and a self-contained message with a concrete remedy. Do not turn a missing preferred heading, template, filename, status token, local agent, or local workflow convention into a finding. Do not emit findings for satisfied rules; compliant items contribute only to coverage.

Return `completed` when the complete bundle was evaluated, `not-applicable` when required artifacts or context are absent, `no-knowledge` only when no applicable knowledge exists and no agent finding is emitted, and `partial` or `failed` as defined by DO.

## Output

Output conforms to the DO output contract. Example agent finding:

```json
{
  "skill": { "id": "portable-spec-init", "version": 2 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 1, "info": 0 },
    "coverage": { "worklist-size": 5, "items-evaluated": 5 }
  },
  "findings": [
    {
      "id": "agent:contradictory-scope-boundary",
      "severity": "minor",
      "message": "The business brief excludes automated posting, while the technical design requires unattended posting as the primary flow. Resolve the scope contradiction and update one of the two artifacts before feature planning.",
      "references": [],
      "confidence": "medium",
      "domain": "Project Definition",
      "suggested-code-omission-reason": "requires a product decision rather than a mechanical document edit"
    }
  ],
  "suppressed": []
}
```
