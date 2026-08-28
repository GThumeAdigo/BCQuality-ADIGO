---
kind: action-skill
id: al-copilot-promptdialog
version: 1
title: Copilot PromptDialog Page Review
description: Reviews Business Central Copilot UX implemented with the PromptDialog page type and emits a findings report.
inputs: [pr-diff, file-path]
outputs: [findings-report]
bc-version: [all]
technologies: [al]
countries: [w1]
application-area: [all]
---

# Copilot PromptDialog Page Review

Reviews Business Central Copilot UX built on the `PageType = PromptDialog` surface: the required page properties, the three sanctioned layout areas, the two sanctioned action areas, the `OnQueryClosePage` persistence pattern, and the AOAI retry loop. It emits a findings report. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with either a `pr-diff` (the standard PR-review entry point for a PromptDialog page change) or a `file-path` (single-file review of a PromptDialog page object). The skill produces a single JSON document conforming to the DO output contract.

## Source

The rule set is this skill's own PromptDialog knowledge plus BCQuality knowledge entries whose domain covers the concerns it touches (style for captions, tooltips, and action naming). Read the BCQuality knowledge index once and take the `style` domain entries as the citable candidate set across every enabled layer; do not open an article body until it enters the Worklist. The PromptDialog framework contract (allowed areas, system actions, mandatory properties) is not covered by the corpus; for a concrete violation there, emit an agent finding within this skill's PromptDialog domain.

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version` - the target BC version from the consuming app's `app.json`, or `unknown`. PromptDialog requires AL runtime 12.1 or later, so this dimension is load-bearing.
- `technologies` - `[al]`.
- `countries` - from the app's `app.json`, else `unknown`.
- `application-area` - the union of areas declared by the changed objects; pass the actual set.

Discard files not applicable to AL. Retain conditionally applicable rules (any dimension `unknown`) only when configuration permits; cap their findings at `medium` confidence and name the unknown dimension.

## Worklist

Narrow to the rules that apply to the page under review. A rule enters the worklist when the diff or file touches its area:

- **Page properties** - `PageType = PromptDialog`; `Extensible = false`; `Image = Sparkle` (or `SparkleFilled`); `IsPreview` set during the preview lifecycle; deliberate `PromptMode`.
- **Layout areas** - only `Prompt`, `Content`, and `PromptOptions`; no repeater controls in `Prompt` or `Content`; `PromptOptions` carries only option-type fields.
- **Action areas** - only `SystemActions` and `PromptGuide`; only the five system actions (`Generate`, `Regenerate`, `Attach`, `OK`, `Cancel`); no custom system actions; prompt-guide actions set the input variable and render only in `Prompt` mode.
- **Action naming** - no trailing whitespace in action `Name` (the caption may have it, the name may not).
- **Persistence** - `OnQueryClosePage` saves generated content when `CloseAction = Action::OK`.
- **Generation robustness** - the AOAI call is wrapped in a bounded retry loop terminating in a friendly `Error`.
- **Discoverability** - a complex feature provides a prompt guide (at least three examples).

## Action

For each worklist item, evaluate the page object and emit findings. Reframe the correct-build rules as defects to flag:

- **Trailing whitespace in an action `Name`.** Emit a capped agent finding unless a curated rule applies; a direct compiler/platform rejection is separate deterministic evidence with a stable page/control/check occurrence key.
- **`Extensible = true` (or omitted) on a PromptDialog page.** Emit a capped agent finding unless a curated rule applies:

  ```al
  page 54320 "Copilot Job Proposal"
  {
      PageType = PromptDialog;
      Extensible = false;   // mandatory
  }
  ```

- **Repeater/control, PromptOptions, action-area, Generate, and persistence defects.** Emit capped agent findings unless curated knowledge applies. Direct compiler/platform-validator failures are separate evidence with a stable page/control/check occurrence key and may gate.
- **AOAI call with no retry loop or no terminal friendly `Error`.** A single attempt that surfaces a raw failure is poor UX. Flag `minor` and recommend the bounded retry pattern (zero-indexed up to N attempts, each `Codeunit.Run()` swallowing errors, terminal `Error` with a label).
- **`IsPreview` omitted during a preview release.** The user-facing preview note is missing. Flag `minor`.
- **No prompt guide on a complex feature.** Users cannot phrase prompts; provide at least three examples. Flag `minor`.

Cite a `style` knowledge file in `references` when a finding maps onto one; otherwise emit a capped agent finding within this skill's domain. A direct compiler/platform failure is separate evidence with a stable page/control/check occurrence key. `high` confidence is available only to an unambiguous knowledge-backed finding or deterministic tool observation; agent findings remain at `medium` or lower.

Outcome selection: `completed` when every worklist item was evaluated (including an empty `findings` array); `no-knowledge` when no applicable rule survived filtering; `not-applicable` when the change touches no PromptDialog page; `partial` on a budget cutoff; `failed` on an unrecoverable error (`outcome-reason` required).

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "al-copilot-promptdialog", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 2, "info": 0 },
    "coverage": { "worklist-size": 7, "items-evaluated": 7 }
  },
  "findings": [
    {
      "id": "agent:promptdialog-extensible-true",
      "severity": "minor",
      "message": "This PromptDialog page does not set Extensible = false, which is mandatory for Copilot pages. Recommendation: add Extensible = false to the page properties.",
      "location": { "file": "src/Copilot/CopilotJobProposal.Page.al", "line": 4 },
      "references": [],
      "confidence": "medium",
      "domain": "Copilot PromptDialog",
      "suggested-code": "    Extensible = false;"
    },
    {
      "id": "agent:promptoptions-non-option-field",
      "severity": "minor",
      "message": "area(PromptOptions) contains a Text field; PromptOptions accepts only option-type (enum) fields, so the field will not render as an option button. Recommendation: model the choice as an enum and bind that field instead.",
      "location": { "file": "src/Copilot/CopilotJobProposal.Page.al", "line": 41 },
      "references": [],
      "confidence": "medium",
      "domain": "Copilot PromptDialog"
    }
  ],
  "suppressed": []
}
```
