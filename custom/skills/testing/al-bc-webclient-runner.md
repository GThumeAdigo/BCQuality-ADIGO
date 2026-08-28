---
kind: action-skill
id: al-bc-webclient-runner
version: 1
title: BC web client runner
description: Drives the rendered BC web client through a documented flow to catch UI residue AL TestPage cannot observe.
inputs: [repository, file-path]
outputs: [findings-report]
bc-version: [all]
technologies: [al]
countries: [w1]
application-area: [all]
---

# BC web client runner

Drives a real Business Central web client through a documented user flow (typically `USER_GUIDE.md`), capturing screenshots and asserting on rendered UI state at every step. It catches the class of bug AL TestPage is structurally blind to: page layout, action enable and disable state, FactBox refresh timing, notification toasts, modal stacking, lookup usability, delayed-insert behaviour on subpages, and state-label drift between the guide and the enum. It executes scripted flows; it does not author AL. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with a `repository` (the extension source, so page and action names and the documented sandbox URL and company can be resolved) and a `file-path` (the user-guide markdown to walk). It produces a single JSON document conforming to the DO output contract.

## Source

Read the BCQuality knowledge index once (the `knowledge-index.json` Entry's preparation step regenerates over the live, already-filtered clone). Take the index entries whose `domain` is `ux` or `testing` as the citable candidate set across every enabled layer: rendered-UI rules (delayed-insert, lookup usability, refresh-after-validate, state-label consistency) can back a finding the run surfaces. Do not open individual article files at this step; open an article's full body only once it enters the Worklist below. Where no curated rule covers an observed rendered-UI defect, this skill emits an agent finding within its own domain (see Action).

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version`: the target BC version from the repository `app.json`, or `unknown` if unavailable.
- `technologies`: `[al]`.
- `countries`: the consuming app's declared countries, or `unknown`.
- `application-area`: the application areas of the pages walked, or `unknown`.

Discard files that are not applicable. Retain conditionally applicable files (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium`, and the finding `message` names the unknown dimensions.

## Worklist

Narrow to the flow to drive and the rendered checks per step. The environment must be non-production: refuse an on-prem host lacking `sandbox`, `dev`, `test`, or `staging`, and for a SaaS host on `businesscentral.dynamics.com` inspect the environment-name path segment and refuse if it matches `Production` or starts with `Prod`. Then build the worklist:

- Each top-level guide section (or the supplied subset), and within it each documented step.
- Step-level state checks: read the documented outcome (status pill text, field value, subpage row count) after each action.
- Action availability: confirm a button is enabled or disabled exactly as the guide states, reading `aria-disabled` from the accessibility tree.
- Notification toasts: screenshot the toast region before auto-dismiss and read its content.
- FactBox totals: read the numbers and compare to the documented arithmetic.
- Lookup usability on every lookup-bearing field: open the lookup, confirm it lists records and a selection writes back.
- Delayed-insert behaviour on every editable subpage: type into the first non-PK field, tab off, and watch for an out-of-filter banner, a blank PK column, or the row falling out of the parent filter.
- Missing affordances the guide implies (a lookup drop-down a documented path needs).
- State-label drift: compare the displayed status value and enum dropdown values against the names the guide uses.
- Page-level errors: any `Error` notification, inline validation message, or console `ServerError`, captured even if the guide does not mention it.

A curated `ux` or `testing` file enters the worklist when its `keywords` intersect these tokens. Read its full body only after it makes the worklist. Resolve layer-precedence conflicts per READ and record dropped files in `suppressed`.

## Action

Drive the web client through each worklisted step, screenshot the result, and assert on the documented outcome. Accept a `continue-on-fail` option, default `false`; when true, capture the failed step and continue with independent steps, marking dependent steps skipped in the summary. After every step and after every failure, capture browser console errors and failed network requests (HTTP failure or transport error) and associate their artifact paths with the step. The skill requires a Chrome automation surface in the calling session; if it is unavailable, emit `outcome: "failed"` with `outcome-reason` stating the surface is missing.

Emit deterministic evidence when a direct browser assertion against a documented expected outcome fails. Use `id: evidence:browser-assertion-failed` and a stable lower-case `<guide-section>/<step>/<assertion>` occurrence key, `kind: browser-assertion`, the flow/step artifact bundle as source, `status: assertion-failed`, and set `gating` from whether the expected outcome is required. A directly captured console error or failed request uses a separate `evidence:browser-console-error` or `evidence:browser-network-request-failed` finding with its own stable section/step/assertion occurrence key only when the browser tool attributes it to the step; otherwise it is context in the summary. Curated rule violations and AL root-cause hypotheses are separate findings and MUST NOT be merged with browser evidence. Record role, URL, continue-on-fail, assertion counts, console artifact, failed-request artifact, and screenshots in `summary.execution`. Passing assertions belong only in the summary.

Outcome selection: `completed` when every attempted step was driven and asserted (including a clean run with empty `findings`); `not-applicable` when the supplied path is not a user guide or the repository drives no rendered page; `partial` when a block stopped the run mid-flow and not every section was attempted (`summary.coverage` reflects the attempted subset); `failed` when the Chrome surface was unavailable or the run could not start, with `outcome-reason` required.

## Output

Output conforms to the DO output contract. Direct required expected-outcome failures are gating deterministic browser evidence. Root-cause hypotheses remain separate capped agent findings.

```json
{
  "skill": { "id": "al-bc-webclient-runner", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 2, "major": 0, "minor": 1, "info": 0 },
    "coverage": { "worklist-size": 9, "items-evaluated": 9 },
    "execution": { "status": "failed", "continue-on-fail": true, "assertions-attempted": 9, "assertions-passed": 7, "assertions-failed": 2, "assertions-skipped": 0, "console-artifact": "artifacts/console.json", "failed-requests-artifact": "artifacts/failed-requests.json" }
  },
  "findings": [
    {
      "id": "evidence:browser-assertion-failed",
      "occurrence-key": "section-3.2/step-2/release-action-enabled",
      "severity": "blocker",
      "message": "Section 3.2 step 2 required Release to be enabled after the header was filled; the browser accessibility assertion observed aria-disabled=true.",
      "references": [],
      "confidence": "high",
      "evidence": { "kind": "browser-assertion", "source": "section-3.2/step-2/screenshots/release-disabled.png", "status": "assertion-failed" },
      "gating": true,
      "suggested-code-omission-reason": "fix is an AL change the developer applies after reading the report"
    },
    {
      "id": "evidence:browser-assertion-failed",
      "occurrence-key": "section-5.1/step-1/subpage-row-remains-in-parent-filter",
      "severity": "blocker",
      "message": "Section 5.1 step 1 required the new line to remain in the parent filter after tabbing off; the browser observed an out-of-filter banner and a blank No. column.",
      "references": [],
      "confidence": "high",
      "evidence": { "kind": "browser-assertion", "source": "section-5.1/step-1/screenshots/out-of-filter.png", "status": "assertion-failed" },
      "gating": true,
      "suggested-code-omission-reason": "fix is an AL change the developer applies after reading the report"
    },
    {
      "id": "agent:subpage-may-need-delayed-insert",
      "severity": "minor",
      "message": "The section 5.1 browser failure is consistent with missing or incorrect DelayedInsert and SubPageLink handling, but the browser does not prove that AL root cause. Inspect the subpage properties and insert trigger.",
      "references": [],
      "confidence": "medium",
      "suggested-code-omission-reason": "fix is an AL change the developer applies after reading the report"
    }
  ],
  "suppressed": []
}
```
