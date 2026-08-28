---
kind: action-skill
id: al-troubleshooting-mcp-server
version: 1
title: Troubleshooting MCP Server Usage Review
description: Reviews how the Troubleshooting MCP Server is used to inspect the AL runtime during a debug session and emits a findings report.
inputs: [pr-diff, file-path]
outputs: [findings-report]
bc-version: [all]
technologies: [al, json]
countries: [w1]
application-area: [all]
---

# Troubleshooting MCP Server Usage Review

Reviews whether the Troubleshooting MCP Server for AL is used correctly to inspect the runtime during a debug session, and emits a findings report. The governing principle is that the server is only live while paused at a breakpoint or runtime error, surfaces AL-side state and Database Statistics but not time-travel or compiled `.app` source, and suggests rather than applies fixes, so guidance or instructions that assume otherwise will mislead. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with a `pr-diff` (a change to debugging documentation, runbooks, or Copilot-prompt guidance that references the Troubleshooting MCP) or a `file-path` (a single such file under review). The skill produces a single JSON document conforming to the DO output contract.

## Source

The rule set is the Troubleshooting MCP Server usage guidance: when to use it versus the regular debugger, its prerequisites, the four tools Copilot can call, what it surfaces, and its hard limits. BCQuality's curated knowledge domains do not cover the debugging MCP surface, so this skill carries its own rule set in full. Read the BCQuality knowledge index once to confirm no curated domain claims this area (the `knowledge-index.json` Entry's preparation step regenerates over the already-filtered clone); do not open individual article bodies. Findings here are agent findings within this skill's debug-tooling domain. AL standards that Copilot's suggestions should align with are owned by `al-code-review`; performance-side triage is owned by `al-performance-profiler`.

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version` - the targeted BC version; the server requires BC 28 (2026 release wave 1) or later, so a lower target is itself a relevance signal. Use `unknown` if unavailable.
- `technologies` - the intersection of `[al, json]` present in AL debug guidance and MCP envelopes.
- `countries` - the configured context, else `unknown`.
- `application-area` - `[all]`.

Discard files that do not reference the Troubleshooting MCP Server, AL debug-session guidance, or its tools. Retain conditionally applicable rules (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium` and name the unknown dimension in the `message`.

## Worklist

Narrow the guidance to the rules that apply to the change or file under review. Group the candidate worklist by area:

- **When to use versus not** - reach for it to explain a runtime error along the call stack, to summarise a deep cross-object stack, to learn why a branch took a path, or to set a follow-up breakpoint while paused; do not use it for interactive step-through (the regular debugger is better), quick single-variable inspection, or learning unfamiliar flow cold.
- **Prerequisites** - BC 2026 release wave 1 (BC 28) or later; VS Code with the AL Language extension; GitHub Copilot Chat enabled; an active debug session paused at a breakpoint or runtime error (the server is invisible otherwise, and there is no history replay).
- **The four tools** - `Get Stack Frames` (zero-based frame IDs, 0 is current); `Get Variables(frameid)` returning `{Name, Value, TypeName, Children}` with `<Uninitialized>` and `<Database Statistics>` for SQL latency, executes, and row reads; `Get Source Code(frameid)`, which may be empty for compiled `.app` frames; `Add Breakpoint(ApplicationObjectId, ApplicationObjectType, LineNumber)`. On a runtime error Copilot auto-invokes the three diagnostic tools.
- **Forcing its use** - explicit phrasing helps because Copilot does not always reach for it (for example, "Use the Troubleshooting MCP Server to analyze the error at the current breakpoint and suggest a fix").
- **What it does not do** - no time-travel (only what is in scope now); no source for compiled `.app` frames (fall back to variable inspection); no automatic fixes (Copilot suggests, the developer decides).
- **Common confusions held as rules** - "no debug session" means the server is not live; an empty Get Source Code means a compiled frame; BC 26 is unsupported.

A rule enters the worklist when the change or file under review describes when, how, or with what prerequisites the Troubleshooting MCP Server is used.

## Action

For each worklist item, evaluate the change or file and emit findings (all are agent findings within this skill's domain: `references: []`, `id` prefixed `agent:`, `confidence` capped at `medium` per `skills/do.md`):

- Guidance defects inferred from text are agent findings capped at `minor` and `medium`. A direct MCP tool-envelope failure is separate deterministic evidence with a stable tool/operation occurrence key and may carry hard severity.
- Guidance that misdescribes a tool or its output in a way that misleads (treating frame IDs as one-based, expecting Get Source Code to return source for compiled `.app` frames, omitting that Database Statistics is where hidden DB calls surface) is a `minor` agent finding.
- A scoping or hygiene gap (recommending the MCP for interactive step-through or single-variable peeks where the regular debugger is better, omitting the explicit-phrasing tip where Copilot would otherwise not engage) is a `minor` agent finding.
- Record satisfied tool checks in summary coverage; do not emit findings for them.

Uncited textual-review findings use confidence `medium` or lower. A direct tool-envelope observation or knowledge-backed finding may use `high`. Emit `suggested-code` for mechanical wording fixes.

Outcome selection: `completed` when every worklist item was evaluated (including an empty `findings` array); `no-knowledge` when no applicable rule survived Relevance and configuration filtering; `not-applicable` when the change references no Troubleshooting MCP or AL debug guidance; `partial` when a budget was hit before the worklist was exhausted; `failed` on an unrecoverable error (`outcome-reason` required).

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "al-troubleshooting-mcp-server", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 2, "info": 0 },
    "coverage": { "worklist-size": 5, "items-evaluated": 5 }
  },
  "findings": [
    {
      "id": "agent:troubleshooting-mcp-wrong-bc-version",
      "severity": "minor",
      "message": "The debugging guide tells developers to use the Troubleshooting MCP Server on BC 26. The server requires BC 28 (2026 release wave 1) or later and is unavailable on BC 26, so this instruction will not work. Recommendation: state the BC 28 minimum and point BC 26 users to the regular debugger.",
      "location": { "file": "docs/debugging/mcp-guide.md", "line": 14 },
      "references": [],
      "confidence": "medium",
      "domain": "Troubleshooting MCP",
      "suggested-code": "Requires BC 2026 release wave 1 (BC 28) or later."
    },
    {
      "id": "agent:get-source-code-empty-frame-misdescribed",
      "severity": "minor",
      "message": "The guide treats an empty Get Source Code result as an error to retry. An empty result means the frame is in compiled .app code; the correct fallback is to inspect variables at that frame. Recommendation: document the compiled-frame case and the variable-inspection fallback.",
      "location": { "file": "docs/debugging/mcp-guide.md", "line": 33 },
      "references": [],
      "confidence": "medium",
      "domain": "Troubleshooting MCP"
    }
  ],
  "suppressed": []
}
```
