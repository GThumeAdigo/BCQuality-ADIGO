---
kind: action-skill
id: al-go-pipelines
version: 1
title: AL-Go Pipeline Configuration Review
description: Reviews an AL-Go for GitHub CI/CD setup against the team's framework rules and emits a findings report.
inputs: [repository, file-path]
outputs: [findings-report]
bc-version: [all]
technologies: [al, powershell, yaml, json, github-actions]
countries: [w1]
application-area: [all]
---

# AL-Go Pipeline Configuration Review

Reviews how a Business Central repo runs CI/CD with AL-Go for GitHub - the settings model, repo and branching strategy, release procedure, self-upgrade auth, and any AL MCP Server wiring - and emits a findings report. AL-Go is the chosen framework for BC CI/CD on GitHub Actions, and its workflows are downloaded at runtime from upstream, so the central concern is that customisation happens through settings and never by hand-editing the AL-Go-owned workflow scripts. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with a `repository` (a whole-repo audit of the AL-Go setup) or a `file-path` (a targeted re-check of `.AL-Go/settings.json`, `.github/AL-Go-Settings.json`, or a workflow file). The skill produces a single JSON document conforming to the DO output contract.

## Source

The rule set is the team's AL-Go for GitHub framework governance: the hard rules below, the two-file settings model, repo/branching strategy, the release procedure, the self-upgrade auth setup, and the AL MCP Server CI integration. This is pipeline governance that the curated BCQuality knowledge domains do not cover. Read the BCQuality knowledge index once (the `knowledge-index.json` Entry's preparation step regenerates over the already-filtered clone); no curated domain maps onto AL-Go configuration, so for each concrete violation emit an agent finding within this skill's pipeline-governance domain. Do not open individual article bodies at this step; open an article only once it enters the Worklist.

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version` - the target BC version from the extension's `app.json`, or `unknown` if unavailable.
- `technologies` - the intersection of `[al, powershell, yaml, json, github-actions]` present in the extension, settings, and workflows.
- `countries` - the countries declared in the app's `app.json`; default to the orchestrator's configured context, else `unknown`.
- `application-area` - the union of application areas declared by the extension; pass the actual set, do not substitute `[all]`.

Discard tasks with no AL-Go repo to review. Retain conditionally applicable rules (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium` and name the unknown dimension in the `message`.

## Worklist

Narrow the framework rules to the artifacts present in the repo or change under review. Group the candidate worklist by area:

- **Hard rules** - AL-Go workflow scripts under `.github/workflows/AL-Go-*` are never hand-edited (they auto-upgrade from upstream); releases use semantic version tags (`v1.2.0`), are marked **Pre-release**, and use **Create Release Branch**; one repo per AppSource or customer PTE app (multi-project only when apps are tightly coupled); `main` is always the latest code and is never rolled back.
- **Settings model** - build/test settings live in `.AL-Go/settings.json` (per project: `projects`, `appFolders`, container country, AppSourceCop config, `appDependencyProbingPaths`); CI/CD wiring lives in `.github/AL-Go-Settings.json` (per repo: PR/CI-CD trigger branches, `environments`, `ContinuousDeployment`, dependent apps); settings changes that affect workflow shape are followed by **Update AL-Go System Files**.
- **Repo and branching** - default branch `main`; release branches are independent heads cut from `main` at release time, not long-lived forks; hotfixes are `hotfix/<description>` branches off the release branch; shared assets live in a separate `d365-dependent-artifacts` submodule.
- **d365-dependent-artifacts** - never public, never shared externally; `main` protected, PR required, no direct commits; no CI/CD by design; signed apps live here, not in the AL-Go repo.
- **Release procedure** - Create Release from `main` (first release) or the latest release branch (subsequent), semantic tag, Pre-release until validated, Create Release Branch ticked, hotfixes via `hotfix/<description>`.
- **Self-upgrade auth** - the shared AL-Go GitHub App is installed, `GHTOKENWORKFLOW` repo secret is set, and Update AL-Go System Files has been run and its PR merged.
- **AL MCP Server in CI** - `altool launchmcpserver` is used only for agent-driven or PR-gate cases AL-Go does not cover; the canonical build/test/publish path stays with AL-Go's own workflows; CI symbol pulls use `globalSourcesOnly: true`.

A rule enters the worklist when the repo's settings, workflows, branch layout, or MCP wiring touches its area.

## Action

For each worklist item, evaluate the repo or change and emit findings. These are agent findings within this skill's pipeline-governance domain (`references: []`, `id` prefixed `agent:`, severity capped per `skills/do.md`), since no curated knowledge file covers AL-Go configuration:

- Framework and governance defects inferred from repository configuration are capped agent findings. A named AL-Go/GitHub validator or workflow run that directly reports failure is separate deterministic evidence with a stable workflow/job/check occurrence key and may gate according to that result.
- A hygiene gap is `minor`: a multi-project repo combining apps that are not tightly coupled, a CI symbol pull without `globalSourcesOnly: true`, or a hotfix committed directly to a release branch rather than via a `hotfix/<description>` branch.
- Record satisfied pipeline checks in summary coverage; do not emit findings for them.

Use `high` confidence only for direct named-validator/tool evidence or knowledge-backed findings. Uncited pipeline review findings remain at `medium` or lower. For mechanical settings fixes, emit `suggested-code`; otherwise set an omission reason.

Outcome selection: `completed` when every worklist item was evaluated (including an empty `findings` array); `no-knowledge` when no applicable rule survived Source, Relevance, and configuration filtering; `not-applicable` when the task context has no AL-Go repo to review; `partial` when a budget was hit before the worklist was exhausted; `failed` on an unrecoverable error (`outcome-reason` required).

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "al-go-pipelines", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 2, "info": 0 },
    "coverage": { "worklist-size": 7, "items-evaluated": 7 }
  },
  "findings": [
    {
      "id": "agent:al-go-workflow-script-hand-edited",
      "severity": "minor",
      "message": "A file under .github/workflows/AL-Go-CICD.yaml has been hand-edited. AL-Go downloads these workflows at runtime from upstream; editing them in the repo breaks the auto-upgrade path. Recommendation: revert the edit and customise via .AL-Go/settings.json or .github/AL-Go-Settings.json, then run Update AL-Go System Files.",
      "location": { "file": ".github/workflows/AL-Go-CICD.yaml", "line": 1 },
      "references": [],
      "confidence": "medium",
      "domain": "AL-Go Pipelines"
    },
    {
      "id": "agent:settings-changed-without-update-system-files",
      "severity": "minor",
      "message": "The PR changes the environments array in .github/AL-Go-Settings.json but does not run Update AL-Go System Files, so the workflow scripts that consume the new setting are not regenerated. Recommendation: run the Update AL-Go System Files workflow and merge its PR.",
      "location": { "file": ".github/AL-Go-Settings.json", "line": 3 },
      "references": [],
      "confidence": "medium",
      "domain": "AL-Go Pipelines"
    }
  ],
  "suppressed": []
}
```
