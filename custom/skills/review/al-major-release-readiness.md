---
kind: action-skill
id: al-major-release-readiness
version: 1
title: AL major release readiness review
description: Reviews a PR that bumps app.json application or platform versions against major-upgrade governance and the compatibility-testing gate, and emits a findings report.
inputs: [pr-diff, repository, deployment-context]
outputs: [findings-report]
bc-version: [all]
technologies: [al, json]
countries: [w1]
application-area: [all]
---

# AL major release readiness review

Reviews Business Central major version bumps against the supplied release policy and compatibility evidence. It distinguishes a deliberate minimum-version commitment from compatibility testing, evaluates the stated reason for a major-version branch, and reviews accompanying upgrade-sensitive changes. It sources from the `upgrade` knowledge domain and cites curated rules where a version-bump concern maps onto one; governance concerns the corpus does not encode are advisory agent findings within its release-governance domain. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with a `pr-diff` or a `repository`. Supply `deployment-context` when a candidate finding depends on customer-environment versions, a released baseline, or persisted production data; without that context, omit the deployment-dependent finding. The skill produces a single JSON document conforming to the DO output contract.

## Source

Read the BCQuality knowledge index once (the `knowledge-index.json` Entry's preparation step regenerates over the live, already-filtered clone). Take the index entries whose `domain` is `upgrade` as the citable candidate set across every enabled layer: breaking changes only on tables without data, enum values additive at the end, no external calls in an upgrade codeunit, and upgrade tags instead of version checks each map onto a curated rule and MUST cite it rather than be paraphrased. Do not open individual article files at this step; open an article's full body only once it enters the Worklist below. Release-policy concerns not encoded in the corpus may become agent findings only when the supplied policy and evidence make the defect concrete (see Action).

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version`: the target BC version from the PR branch `app.json`, or `unknown` if unavailable.
- `technologies`: the intersection of `[al, json]` present in source and app manifests.
- `countries`: the consuming app's declared countries, or `unknown`.
- `application-area`: the application areas of the changed objects, or `unknown`.

Discard files that are not applicable. Retain conditionally applicable files (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium`, and the finding `message` names the unknown dimensions.

## Worklist

Narrow to the governance signals in the PR:

- Changes to `app.json` `application` or `platform` minimum versions: whether the bump is a genuine commitment or compatibility testing that should not have touched the manifest.
- Whether the supplied compatibility evidence shows the change could instead be made on the currently supported version. Do not infer this from branch names or version numbers alone.
- The driving reason for a NextMajor branch when one is implied: a new API surface only on NextMajor, a Microsoft-required schema change, or a performance feature needed for a customer SLA; documented in the PR description.
- Schema and enum changes riding along with the bump that the `upgrade` corpus governs. Evaluate data-preservation requirements when `deployment-context` proves a released baseline or persisted data. Apply unreleased-schema negative guidance only when the context proves the schema is unreleased. When status is unknown, omit deployment-dependent findings.
- Deprecation-warning handling: warnings resolvable on the current version should be fixed forward, not deferred into a manifest bump.

A curated `upgrade` file enters the worklist when its `keywords` intersect these tokens (for example `breaking-change`, `enum`, `upgrade`, `version`). Read its full body only after it makes the worklist. Resolve layer-precedence conflicts per READ and record dropped files in `suppressed`.

## Action

Evaluate each signal and emit a finding only for a concrete violation.

When a defect maps onto a curated `upgrade` rule (a breaking change on a table with data, a non-additive enum change, an external call in an upgrade codeunit), emit a knowledge-backed finding citing that file: `id` equal to the file path, the file as primary reference, `severity` up to `blocker` only when the file states a platform-level guarantee otherwise `major`, `confidence` `high` for an unambiguous match.

When a governance defect has no curated rule (a manifest version bump made for compatibility testing rather than commitment, a change that supplied compatibility evidence shows could have stayed on the current version, a major-version commitment with no documented driving feature, or a deprecation warning deferred into a bump that was demonstrably resolvable forward), emit an agent finding within this skill's release-governance domain: `references: []`, `id` slug prefixed `agent:` (for example `agent:compatibility-test-changed-manifest`), `confidence` capped at `medium`, `severity` capped at `minor`, and a self-contained `message` describing the governance gap and the concrete remedy. Never infer customer upgrade state, production deployment, or persisted data when `deployment-context` is absent. Hold every candidate to the precision bar in `skills/do.md`: steelman that the bump is a deliberate, communicated decision before emitting, and omit when in doubt. Before emitting any agent candidate, check the worklisted knowledge for a match and upgrade it to a knowledge-backed finding if one exists.

Set `domain` to `Major Release` on every finding. Set `suggested-code` when the fix is a single contiguous manifest revert (restoring the prior `application` or `platform` value); otherwise set `suggested-code-omission-reason` (for example `requires release-decision context documenting the driving feature`). Do not emit findings for satisfied rules; compliant worklist items contribute only to coverage.

Outcome selection: `completed` when every signal was evaluated (including an empty `findings`); `no-knowledge` when no curated knowledge survived and no agent finding was raised; `not-applicable` when the PR does not bump the application or platform version; `partial` or `failed` per the DO contract with `outcome-reason`.

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "al-major-release-readiness", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 1, "info": 0 },
    "coverage": { "worklist-size": 2, "items-evaluated": 2 }
  },
  "findings": [
    {
      "id": "agent:compatibility-test-changed-manifest",
      "severity": "minor",
      "message": "This PR bumps app.json platform from 26.0 to 27.0 but the description frames it as compatibility testing for the next major. Compatibility testing is a check, not a commitment, and must not change the manifest versions, otherwise the build commits every tenant to the new platform. Revert the platform value and run compatibility testing against a Sandbox-NextMajor environment instead. This concern should be promoted to a knowledge-backed rule before it can gate.",
      "location": {
        "file": "app.json",
        "line": 22
      },
      "references": [],
      "confidence": "medium",
      "domain": "Major Release",
      "suggested-code": "  \"platform\": \"26.0.0.0\","
    }
  ],
  "suppressed": []
}
```
