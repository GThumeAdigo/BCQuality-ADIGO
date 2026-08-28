---
kind: action-skill
id: al-bcquality-integration
version: 2
title: BCQuality Consumption Review
description: Reviews whether a consuming repository discovers, pins, and cites a BCQuality fork or vendored corpus correctly, and emits a findings report.
inputs: [repository, file-path]
outputs: [findings-report]
bc-version: [all]
technologies: [al]
countries: [w1]
application-area: [all]
---

# BCQuality Consumption Review

Reviews how a consumer makes BCQuality available to its agents and preserves citation integrity. It supports both a Git submodule containing the full fork, commonly at `.opencode/BCQuality-ADIGO`, and a plain committed filtered vendor tree, commonly at `.opencode/bcquality`. The configured BCQuality content root is authoritative; no particular consumer-root path or runtime agent name is required.

The current full fork has three layers. Microsoft contains 16 knowledge domains and 17 review action skills including its super-skill, Community contains three populated knowledge domains, and Custom contains five populated knowledge domains plus 47 action skills in nine categories. Treat these as point-in-time inventory checks and derive actual coverage from the live checkout and generated knowledge index.

## Source

This skill reviews integration mechanics defined by DO, READ, the consumer's configured content root, and its Git or vendoring metadata. These mechanics are not knowledge-domain rules, so findings are agent findings under the `BCQuality Integration` domain. Read the live knowledge index to verify layers, domains, paths, and article existence, but do not cite an article merely because it is present.

## Relevance

Apply READ's frontmatter matching rules using the consuming extension's target context when available. Return `not-applicable` when the supplied repository or file does not configure or consume BCQuality. Unknown Business Central dimensions do not prevent a structural integration review, but any finding whose applicability depends on them has confidence no higher than `medium`.

## Worklist

Identify the configured BCQuality content root and its mode:

- **Fork submodule mode**: a Git submodule points to a BCQuality fork such as `.opencode/BCQuality-ADIGO`; the checkout contains `skills/`, all enabled layer directories, `tools/`, `LICENSE`, `README.md`, and `agent-consumption.md`; the parent repository records a gitlink commit.
- **Committed vendor mode**: a normal tracked directory such as `.opencode/bcquality` contains the intentionally filtered files; provenance records the upstream or fork commit used to produce it. A submodule is not required in this mode.
- **Discovery**: the consumer invokes `skills/entry.md` from the configured content root or otherwise follows its dispatch record, then action skills follow `skills/do.md` and knowledge lookup follows `skills/read.md`.
- **Citation integrity**: a knowledge-backed finding uses a repo-relative path copied from the live BCQuality knowledge index, with `id` exactly equal to `references[0].path`; the exact article exists and was opened. The configured content root resolves that path. A `sha` is optional under DO and, when present, identifies the reviewed BCQuality commit.
- **Domain mapping**: consumers derive reviewer coverage from the live index and action-skill sources. In this fork, code-quality review includes `performance`, `security`, and `privacy`; readability includes `style` and `ui`; performance uses `performance`; upgrade uses `upgrade`; and test validation uses `testing`.
- **Fork updates**: commit Custom-layer or fork-maintained changes in the BCQuality fork first, then update and commit the parent repository's submodule gitlink. In committed vendor mode, regenerate the filtered tree from a pinned source commit and review the resulting content diff.

A worklist item exists only when the consumer's configuration, report shape, or update change touches that area.

## Action

Emit only concrete integration defects. Because no knowledge article defines these consumption mechanics, each finding MUST use `references: []`, an `agent:`-prefixed stable id, `severity: minor`, confidence no higher than `medium`, and `domain: BCQuality Integration`. The message must state the observed break and a concrete repair. Examples include a configured content root that does not exist, a submodule checkout whose gitlink is not updated after a fork commit, or a citation id that differs from its primary reference path.

Do not require `.opencode/bcquality`, plain committed files, a specific agent filename, a `Knowledge sources` heading, or a `sha` when the consumer uses a valid alternative. Do not label project-specific rules as Microsoft knowledge. Do not emit findings for satisfied checks; compliant items contribute only to coverage. Hold all findings to DO's agent-finding precision bar.

Return `completed` when all applicable integration items were evaluated, `not-applicable` when no BCQuality consumption is configured, `no-knowledge` only when Source yields no applicable material and no agent finding is emitted, and `partial` or `failed` as defined by DO.

## Output

Output conforms to the DO output contract. Example:

```json
{
  "skill": { "id": "al-bcquality-integration", "version": 2 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 1, "info": 0 },
    "coverage": { "worklist-size": 5, "items-evaluated": 5 }
  },
  "findings": [
    {
      "id": "agent:submodule-gitlink-not-bumped",
      "severity": "minor",
      "message": "The BCQuality fork contains the reviewed Custom-layer commit, but the parent repository still points `.opencode/BCQuality-ADIGO` at the previous commit. Update the submodule gitlink so consumers receive the reviewed content.",
      "location": { "file": ".opencode/BCQuality-ADIGO" },
      "references": [],
      "confidence": "medium",
      "domain": "BCQuality Integration",
      "suggested-code-omission-reason": "the replacement is a parent-repository gitlink update"
    }
  ],
  "suppressed": []
}
```
