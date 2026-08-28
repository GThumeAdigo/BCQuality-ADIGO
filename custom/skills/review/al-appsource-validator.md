---
kind: action-skill
id: al-appsource-validator
version: 1
title: AL AppSource submission validation
description: Audits an AL extension against AppSourceCop rules, app.json metadata, artefacts, links, and the dependency chain, and emits a findings report.
inputs: [repository, object-list]
outputs: [findings-report]
bc-version: [all]
technologies: [al, json, xml]
countries: [w1]
application-area: [all]
---

# AL AppSource submission validation

Audits a Business Central extension against Microsoft's AppSource validation rules and manual-review conventions. Coverage spans manifest metadata, object naming and ranges, permissions, translations, assets and links, dependency alignment, telemetry consent, and listing readiness. It sources from the `appsource`, `security`, and `style` knowledge domains and cites curated rules where present; direct validator output is separate deterministic evidence with a stable validator/rule/subject occurrence key, while uncited source inference remains capped agent review. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with a `repository` or an `object-list`. It produces a single JSON document conforming to the DO output contract.

## Source

Read the BCQuality knowledge index once. Take the index entries whose `domain` is `appsource`, `security`, or `style` as the citable candidate set across every enabled layer. Do not open individual article files at this step; open an article's full body only once it enters the Worklist below. AppSource-specific source inferences not encoded in the corpus are capped agent findings; direct AppSourceCop or platform-validator failures are separate deterministic evidence with a stable validator/rule/subject occurrence key.

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version`: the target BC version from the branch `app.json`, or `unknown` if unavailable.
- `technologies`: the intersection of `[al, json, xml]` present in source, manifests, analyzer output, and translations.
- `countries`: the consuming app's declared countries (the `supportedCountries`), or `unknown`.
- `application-area`: the application areas of the extension's objects, or `unknown`.

Discard files that are not applicable. Retain conditionally applicable files (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium`, and the finding `message` names the unknown dimensions.

## Worklist

Narrow to the submission gates for the extension under review:

- `app.json` metadata: `id` a stable GUID, `name`/`publisher`/`version` matching the listing, `brief` (empty is AS0036) and `description`, `privacyStatement`, `EULA`, `help`, `url`, `logo`, `runtime`, `target` (`Cloud` for AppSource), `application`, `platform`, all set and not the AL scaffold default; `showMyCode` set only when intentional.
- Object suffix discipline against the `AppSourceCop.json` `mandatorySuffix` (AS0040/AS0041), object ids inside `idRanges` (AS0072), no objects in the system range, no use of Microsoft `Access = Internal` platform objects.
- Permission-set coverage (the AS0029-class tabledata gap), and `supportedCountries` each having an xliff (AS0091).
- Logo PNG at least 350 by 350 and square; at least one screenshot present per the manifest; EULA, privacy, help, and url links resolving with a 2xx HEAD response.
- Dependencies each with `id`/`name`/`publisher`/`version`, version either `0.0.0.0` or a real published version, `propagateDependencies` set when downstream consumers need access (AS0078/AS0079); `runtime` aligned with `target` and `application`; object ids not colliding with the platform or other dependency-chain extensions.
- No demo or dev artefacts in src (`RunModal` in startup paths, hardcoded passwords, demo `Confirm` boxes, `Sleep` in production codeunits); telemetry consent stated in the privacy statement when `applicationInsightsConnectionString` is set.
- Marketplace listing checklist folded in from the AppSource validation playbook: search summary 100 characters or under, description leading with the value proposition, signing via the Key Vault pipeline, README/SETUP/SUPPORT files, support email pointing at the team inbox rather than a personal address, privacy and terms URLs live.
- Fresh analyzer evidence covering the current commit plus working-tree state: command, CodeCop/AppSourceCop/UICop versions, ruleset, source revision, timestamp, exit status, warning count, and error count.

A curated `appsource`, `security`, or `style` file enters the worklist when its `keywords` intersect these tokens. Read its full body only after it makes the worklist. Resolve layer-precedence conflicts per READ and record dropped files in `suppressed`.

## Action

Require fresh analyzer evidence before claiming AppSource readiness. If it is absent or stale, return `partial`; if required execution failed or cannot be parsed, return `failed`. A named analyzer or platform validator's direct failure is a separate gating evidence finding with a stable validator/rule/subject occurrence key; source inspection is not evidence.

Evaluate each remaining gate and emit a finding only for a concrete violation.

When the gate maps onto a curated `appsource`, `security`, or `style` rule, emit a knowledge-backed finding citing that file. A direct AppSourceCop or platform-validator failure is a separate evidence finding with a stable `<validator>/<rule>/<subject>` occurrence key; never merge it with the knowledge finding.

When the gate is an AppSource-specific defect with no curated rule, emit an agent finding within this skill's AppSource compliance domain: `references: []`, `id` slug prefixed `agent:` (for example `agent:as0036-empty-brief` or `agent:runtime-target-mismatch`), `confidence` capped at `medium`, `severity` capped at `minor`, and a self-contained `message` naming the `AS0xxx` rule or listing requirement and the concrete fix. Where the impact would normally gate (any hard AppSource rejection), keep `severity` at `minor` but say so plainly in the `message` and note the concern should be promoted to a knowledge-backed rule before it can gate. Hold every candidate to the precision bar in `skills/do.md`: steelman that the field is intentionally set as-is before emitting, and omit when in doubt. Before emitting any agent candidate, check the worklisted knowledge for a match and upgrade it to a knowledge-backed finding if one exists.

Set `domain` to `AppSource` on every finding. Set `suggested-code` when the fix is a single contiguous metadata edit (setting a `brief` value, correcting a `runtime` number); otherwise set `suggested-code-omission-reason` (for example `requires creating a logo asset` or `requires a live privacy-policy URL`). Do not emit findings for satisfied rules; compliant worklist items contribute only to coverage.

Outcome selection: `completed` only when every gate was evaluated with fresh required analyzer evidence; `not-applicable` when the task has no extension manifest; `partial` when required evidence is missing/stale or only part of the worklist was evaluated; `failed` when required validation could not execute or its result is unreliable. An empty finding set never overrides missing evidence.

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "al-appsource-validator", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 1, "info": 0 },
    "coverage": { "worklist-size": 14, "items-evaluated": 14 }
  },
  "findings": [
    {
      "id": "agent:as0036-empty-brief",
      "severity": "minor",
      "message": "app.json brief is empty. Source review indicates AS0036 will reject it; set brief to a one-sentence summary of 100 characters or fewer. This uncited inference is advisory until a fresh AppSourceCop result confirms it.",
      "location": {
        "file": "app.json",
        "line": 9
      },
      "references": [],
      "confidence": "medium",
      "domain": "AppSource",
      "suggested-code": "  \"brief\": \"Stage-and-forward integration for warehouse shipments.\","
    }
  ],
  "suppressed": []
}
```
