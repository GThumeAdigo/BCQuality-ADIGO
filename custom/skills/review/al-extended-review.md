---
kind: action-skill
id: al-extended-review
version: 2
title: AL extended review
description: Composes the Custom-layer AL review leaves for multi-tenancy, permissions, events, obsolescence, integration, and upgrade concerns.
inputs: [pr-diff, file-path, repository, deployment-context]
outputs: [findings-report]
bc-version: [all]
technologies: [al]
countries: [w1]
application-area: [all]
sub-skills:
  - custom/skills/review/al-multitenancy-review.md
  - custom/skills/review/al-permission-set-review.md
  - custom/skills/review/al-event-subscriber-review.md
  - custom/skills/review/al-obsolete-tracker-review.md
  - custom/skills/review/al-integration-pattern-review.md
  - custom/skills/review/al-upgrade-review.md
---

# AL extended review

Composes six Custom-layer review leaves that complement the Microsoft review skills: multi-tenant and cross-company safety, permission-set coverage, event-subscriber discipline, obsolescence hygiene, modern integration patterns, and deployment-aware upgrade coverage. This super-skill evaluates no knowledge files directly.

## Source

Invoke exactly the leaf paths listed in `sub-skills`. Composition is flat; do not discover additional leaves or invoke another super-skill.

## Relevance

A sub-skill is relevant when the orchestrator supplies at least one of its declared inputs and has not disabled it. Do not inspect task content to pre-filter leaves. Each invoked leaf determines task-level applicability and returns `not-applicable` or `no-knowledge` when appropriate. Pass `deployment-context` to the obsolescence and upgrade leaves when available; its absence does not justify deployment-dependent findings.

## Worklist

The worklist is every sub-skill that passes the input and configuration checks. Record disabled leaves in `skipped-sub-skills` with `reason: configuration`, and leaves accepting none of the supplied input types with `reason: not-applicable`.

## Action

Invoke each worklisted leaf with only its declared inputs and preserve its complete report in `sub-results`. Do not copy findings from a failed leaf into the top-level findings or counts. For every other leaf, copy each finding to the top level, preserve `domain` and every other field verbatim, and set `from-sub-skill` to the leaf's `skill.id`. Leave citation-based ids unchanged. Prefix a non-citation id with `<leaf-skill-id>:`; therefore a leaf id such as `agent:object-missing-from-permission-set` becomes `al-permission-set-auditor:agent:object-missing-from-permission-set`.

A super-skill self-review may emit only a concrete cross-cutting defect that no leaf owns. Validate it against the union of opened knowledge first. If no article applies, emit an agent finding with `from-sub-skill: agent`, `references: []`, an `agent:`-prefixed id, `severity: minor`, confidence no higher than `medium`, and `domain: Agent`. Do not emit findings for satisfied rules.

Derive `outcome`, `summary`, suppression, and skip handling exactly as specified by DO. The top-level `suppressed` array remains empty; leaf suppression remains in each sub-result.

## Output

Output conforms to the DO composition contract. This example shows one enabled leaf and five configuration skips:

```json
{
  "skill": { "id": "al-extended-review", "version": 2 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 1, "minor": 0, "info": 0 },
    "coverage": { "worklist-size": 1, "items-evaluated": 1 }
  },
  "findings": [
    {
      "id": "custom/knowledge/integration/al-never-call-external-services-from-posting.md",
      "severity": "major",
      "message": "HttpClient.Send is called from a posting subscriber. Stage the call and let asynchronous processing send it after posting completes.",
      "location": { "file": "src/Integration/PostHooks.Codeunit.al", "line": 42 },
      "references": [
        { "path": "custom/knowledge/integration/al-never-call-external-services-from-posting.md" }
      ],
      "confidence": "high",
      "domain": "Integration",
      "from-sub-skill": "al-integration-pattern-reviewer"
    }
  ],
  "suppressed": [],
  "sub-results": [
    {
      "skill": { "id": "al-integration-pattern-reviewer", "version": 1 },
      "outcome": "completed",
      "summary": {
        "counts": { "blocker": 0, "major": 1, "minor": 0, "info": 0 },
        "coverage": { "worklist-size": 1, "items-evaluated": 1 }
      },
      "findings": [
        {
          "id": "custom/knowledge/integration/al-never-call-external-services-from-posting.md",
          "severity": "major",
          "message": "HttpClient.Send is called from a posting subscriber. Stage the call and let asynchronous processing send it after posting completes.",
          "location": { "file": "src/Integration/PostHooks.Codeunit.al", "line": 42 },
          "references": [
            { "path": "custom/knowledge/integration/al-never-call-external-services-from-posting.md" }
          ],
          "confidence": "high",
          "domain": "Integration"
        }
      ],
      "suppressed": []
    }
  ],
  "skipped-sub-skills": [
    { "skill": { "id": "al-multitenancy-reviewer", "version": 1 }, "reason": "configuration" },
    { "skill": { "id": "al-permission-set-auditor", "version": 1 }, "reason": "configuration" },
    { "skill": { "id": "al-event-subscriber-auditor", "version": 1 }, "reason": "configuration" },
    { "skill": { "id": "al-obsolete-tracker", "version": 1 }, "reason": "configuration" },
    { "skill": { "id": "al-upgrade-checker", "version": 1 }, "reason": "configuration" }
  ]
}
```
