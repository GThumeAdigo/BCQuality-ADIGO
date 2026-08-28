---
kind: action-skill
id: appsource-validation
version: 1
title: AppSource submission validation
description: Reviews a Business Central extension against the AppSource marketplace submission checklist and emits a findings report.
inputs: [repository, file-path]
outputs: [findings-report]
bc-version: [all]
technologies: [al, json, xml]
countries: [w1]
application-area: [all]
---

# AppSource submission validation

Reviews a Business Central extension for AppSource submission readiness against the marketplace checklist and emits a findings report. This is a leaf action skill: it invokes no sub-skills. Run it before a first submission, or before publishing a new version of an already-listed app.

An orchestrator invokes this skill with a `repository` (whole-extension audit before submission) or a `file-path` (a targeted re-check, for example `app.json` alone). The skill produces a single JSON document conforming to the DO output contract.

## Source

The rule set is the AppSource marketplace submission requirements: manifest correctness, signing, code constraints, test coverage, and Partner Center listing metadata. Read the BCQuality knowledge index once and take the `appsource`, `security`, `style`, and `upgrade` domain entries as the citable candidate set across every enabled layer. Do not open individual article bodies at this step; open an article only once it enters the Worklist. Marketplace-listing and Partner Center rules not covered by the corpus remain capped agent findings unless a named validator directly reports them.

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version` - the target BC version from the extension's `app.json`, or `unknown` if unavailable.
- `technologies` - the intersection of `[al, json, xml]` present in source, manifests, analyzer output, and translations.
- `countries` - the countries declared in the app's `app.json`; default to the orchestrator's configured context, else `unknown`.
- `application-area` - the union of application areas declared by the extension; pass the actual set, do not substitute `[all]`.

Discard files not applicable to AL extensions. Retain conditionally applicable rules (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium` and name the unknown dimension in the `message`.

## Worklist

Narrow the checklist to the items that apply to the extension or changes under review. Group the candidate worklist by area:

- **app.json manifest** - `id` is a stable, never-reused GUID; `name`/`publisher`/`version` match the Partner Center listing exactly; `application` and `platform` set to the current minimum supported versions; `dependencies` include the System and Base Application; `idRanges` match the publisher's assigned range; `target` is `Cloud`; `runtime` matches the targeted BC runtime; `showMyCode` is `true` only when intentional.
- **Signing** - the `.app` is signed via Azure Key Vault through the AL-Go pipeline; `NavSip.dll` is present on the build runner for local verification.
- **Code** - no `Confirm` dialogs in event subscribers; upgrade codeunits carry a corresponding `previousVersionTag`; user-facing strings use `Label` declarations with translations; telemetry is tagged with the publisher tag.
- **Tests** - a test app exists and runs; a coverage report is attached; the permission set is published and used by tests.
- **Partner Center listing** - search summary 100 characters or under; description leads with the value proposition; logo SVG meets size requirements; demo video (if any) under 90 seconds; privacy policy and T&C URLs live and reachable.
- **Project-specific** - the shared T&Cs template is used (not hand-rolled per app); the privacy policy aligns with NZ and Australian privacy law; the support email points to the project support inbox, not a personal address.
- **Fresh analyzer evidence** - a compiler/analyzer report generated from the current commit plus working-tree state with CodeCop, AppSourceCop, UICop, and the repository ruleset; record command, analyzer versions, source revision, timestamp, exit status, errors, and warnings.

A rule enters the worklist when the manifest, source, or listing metadata under review touches its area. Curated candidates come from the `appsource`, `security`, `style`, and `upgrade` domains selected in Source.

## Action

First validate that the required analyzer evidence is fresh and covers the source under review. If it is absent, stale, or cannot be tied to the current source state, return `outcome: "partial"` with an explicit `outcome-reason`; never return a clean AppSource result. If required analyzer execution failed or its report is unparseable, return `outcome: "failed"` and emit deterministic gating evidence with a stable validator/rule/subject occurrence key when the tool envelope directly reports that failure.

For each remaining worklist item, evaluate the extension and emit findings:

- When an `appsource`, `security`, `style`, or `upgrade` knowledge rule matches, emit a separate knowledge-backed finding with that file as the primary reference.
- A compiler, AppSourceCop, CodeCop, UICop, signing validator, or Partner Center validator failure is deterministic evidence when its named report directly records the failure. Use an `evidence:` id plus a stable `<validator>/<rule>/<subject>` occurrence key, the appropriate evidence kind/source/status, `gating: true`, and severity based on deterministic impact. Do not recast source inspection as validator evidence or merge evidence with a knowledge finding.
- A submission defect inferred from source or metadata without a curated rule is an `agent:` finding capped at `minor`/`medium`.
- A requirement inferred from source without curated backing is a capped agent finding; direct AppSourceCop/platform failures are separate deterministic evidence with a stable validator/rule/subject occurrence key and may carry hard severity.
- A listing or hygiene gap that weakens the submission without failing it (description that leads with a feature list, missing demo video) is `minor`.
- Passing analyzer and checklist evidence belongs in `summary.validation`, including execution status and error/warning counts, not in findings.

Use `high` confidence only for direct analyzer/platform evidence carrying its stable occurrence key or unambiguous knowledge-backed findings. Uncited manifest review findings remain at `medium` or lower. For mechanical fixes, emit `suggested-code`; otherwise set an omission reason.

Outcome selection: `completed` only when every worklist item was evaluated with fresh required analyzer evidence; `not-applicable` when the task context has no AL extension; `partial` when required evidence is missing/stale or a budget stopped evaluation; `failed` when required validation could not execute or produced no reliable result.

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "appsource-validation", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 1, "major": 1, "minor": 0, "info": 0 },
    "coverage": { "worklist-size": 6, "items-evaluated": 6 }
  },
  "findings": [
    {
      "id": "evidence:appsourcecop-failed",
      "occurrence-key": "appsourcecop/as0098/app-json-target",
      "severity": "blocker",
      "message": "AppSourceCop 14.0 reported AS0098 for app.json line 14 because target is 'Internal'; the required analyzer execution failed.",
      "location": { "file": "app.json", "line": 14 },
      "references": [],
      "confidence": "high",
      "evidence": { "kind": "analyzer", "source": "AppSourceCop 14.0/artifacts/analyzers.sarif", "status": "failed" },
      "gating": true,
      "domain": "AppSource",
      "suggested-code": "  \"target\": \"Cloud\","
    },
    {
      "id": "microsoft/knowledge/style/user-facing-text-uses-labels.md",
      "severity": "major",
      "message": "A user-facing message is built from a string literal rather than a Label, so it cannot be translated for the marketplace listing's supported languages.",
      "location": { "file": "src/Setup/Onboarding.Codeunit.al", "line": 88 },
      "references": [
        { "path": "microsoft/knowledge/style/user-facing-text-uses-labels.md" }
      ],
      "confidence": "medium",
      "domain": "AppSource"
    }
  ],
  "suppressed": []
}
```
