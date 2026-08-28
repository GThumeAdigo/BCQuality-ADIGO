---
kind: action-skill
id: al-go-environment-onboarding
version: 1
title: AL-Go Environment Onboarding Review
description: Reviews how a Business Central environment is wired into an AL-Go repo for deployment and emits a findings report.
inputs: [repository, file-path]
outputs: [findings-report]
bc-version: [all]
technologies: [al, powershell, yaml, json, github-actions]
countries: [w1]
application-area: [all]
---

# AL-Go Environment Onboarding Review

Reviews how a Business Central environment is registered for AL-Go deployment - the Entra App Registration, the BC application user, the GitHub environment with its `AUTHCONTEXT` secret, and the `DeployTo<Env>` block in AL-Go settings - and emits a findings report. The governing concern is that a misconfigured environment fails silently: a Continuous Deployment run that did not fire, fired but deployed nothing, or deployed the wrong version. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with a `repository` (a whole-repo audit of the environment wiring before or after onboarding a customer environment) or a `file-path` (a targeted re-check of `.github/AL-Go-Settings.json` alone). The skill produces a single JSON document conforming to the DO output contract.

## Source

The rule set is the AL-Go environment-onboarding procedure: Entra App Registration (S2S) correctness, BC application-user provisioning, the GitHub environment and its `AUTHCONTEXT` secret, the `DeployTo<Env>` settings block, and explicit versioning. None of this is covered by the curated BCQuality knowledge domains - it is deployment governance specific to the AL-Go framework. Read the BCQuality knowledge index once (the `knowledge-index.json` Entry's preparation step regenerates over the already-filtered clone); no curated domain maps onto environment wiring, so for each concrete violation emit an agent finding within this skill's deployment-onboarding domain. Do not open individual article bodies at this step; open an article only once it enters the Worklist.

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version` - the target BC version from the extension's `app.json`, or `unknown` if unavailable.
- `technologies` - the intersection of `[al, powershell, yaml, json, github-actions]` present in AL-Go environment settings and workflows.
- `countries` - the countries declared in the app's `app.json`; default to the orchestrator's configured context, else `unknown`.
- `application-area` - the union of application areas declared by the extension; pass the actual set, do not substitute `[all]`.

Discard tasks with no AL-Go repo to review. Retain conditionally applicable rules (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium` and name the unknown dimension in the `message`.

## Worklist

Narrow the onboarding procedure to the artifacts present in the repo or change under review. Group the candidate worklist by area:

- **Entra App Registration (S2S)** - a shared registration (`BC-CICD-NonProd` or its production equivalent) is reused rather than a per-customer app; auth is Service-to-Service client credentials; the `Dynamics 365 Business Central` `app_access` application permission is granted with admin consent; the client secret has a tracked expiry.
- **BC application user** - an Application-type user exists in both Production and Sandbox with `D365 AUTOMATION` and `EXTEN. MGT. - ADMIN` permission sets; the user is disabled in Production and enabled in Sandbox.
- **GitHub environment** - the environment name matches the BC environment name character for character; an `AUTHCONTEXT` environment secret carries a whitespace-free JSON payload with all four fields (`tenantId`, `scopes`, `clientId`, `clientSecret`).
- **DeployTo<Env> block** - `.github/AL-Go-Settings.json` lists the environment in `environments` and defines a `DeployTo<EnvName>` block with `EnvironmentType` (`SaaS` for customer environments), an `EnvironmentName` matching both the BC and GitHub names, `Branches` that include the branch meant to deploy, `SyncMode`, and `ContinuousDeployment` set appropriately.
- **Versioning** - versioning is defined explicitly in AL-Go settings rather than inherited from AL-Go defaults; the deployed version is validated against `app.json`.

A rule enters the worklist when the repo's settings, secrets, or environment configuration touches its area.

## Action

For each worklist item, evaluate the environment wiring and emit findings. These are agent findings within this skill's deployment-onboarding domain (`references: []`, `id` prefixed `agent:`, severity capped per `skills/do.md`), since no curated knowledge file covers AL-Go environment setup:

- Wiring and deployment-intent defects inferred from configuration are capped agent findings. A named deployment/platform validator or workflow run that directly reports failure is separate deterministic evidence with a stable environment/check occurrence key and may gate according to that result.
- A hygiene gap that weakens the setup without breaking it is `minor`: a per-customer App Registration created where the shared one would do, a client secret with no tracked expiry/rotation reminder, or skipping a continuous-deployment test on a throwaway sandbox before wiring a real customer environment.
- Record satisfied onboarding checks in summary coverage; do not emit findings for them.

Use `high` confidence only for direct named-validator/tool evidence or knowledge-backed findings. Uncited onboarding review findings remain at `medium` or lower. Emit `suggested-code` for mechanical settings fixes; otherwise set an omission reason.

Outcome selection: `completed` when every worklist item was evaluated (including an empty `findings` array); `no-knowledge` when no applicable rule survived Source, Relevance, and configuration filtering; `not-applicable` when the task context has no AL-Go repo to review; `partial` when a budget was hit before the worklist was exhausted; `failed` on an unrecoverable error (`outcome-reason` required).

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "al-go-environment-onboarding", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 2, "info": 0 },
    "coverage": { "worklist-size": 5, "items-evaluated": 5 }
  },
  "findings": [
    {
      "id": "agent:bc-application-user-enabled-in-production",
      "severity": "minor",
      "message": "The AL-Go application user is enabled in the customer Production environment. AL-Go CI/CD only deploys to non-production unless explicitly opted in; leaving the user enabled in Production is an outage risk. Recommendation: disable the Application-type user in Production and keep it enabled only in Sandbox.",
      "location": { "file": ".github/AL-Go-Settings.json", "line": 4 },
      "references": [],
      "confidence": "medium",
      "domain": "AL-Go Environment"
    },
    {
      "id": "agent:deployto-branches-excludes-pushed-branch",
      "severity": "minor",
      "message": "DeployToTest-NZ defines Branches without 'main', so a push to main never triggers Continuous Deployment. Recommendation: add the deploying branch to Branches and run Update AL-Go System Files.",
      "location": { "file": ".github/AL-Go-Settings.json", "line": 8 },
      "references": [],
      "confidence": "medium",
      "domain": "AL-Go Environment",
      "suggested-code": "    \"Branches\": [\"main\"],"
    }
  ],
  "suppressed": []
}
```
