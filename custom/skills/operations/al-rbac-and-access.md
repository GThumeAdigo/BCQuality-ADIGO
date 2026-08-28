---
kind: action-skill
id: al-rbac-and-access
version: 1
title: Azure RBAC and Access Review
description: Reviews Azure role-based access control configuration against the least-privilege model and emits a findings report.
inputs: [repository, file-path]
outputs: [findings-report]
bc-version: [all]
technologies: [powershell, bicep, json]
countries: [w1]
application-area: [all]
---

# Azure RBAC and Access Review

Reviews how Azure role-based access control is configured for a workload, and emits a findings report. The governing principles are least privilege at the resource-group level, Managed Identity for runtime auth, RBAC (not access policies) on Key Vault, and the Owner role reserved for when role-assignment delegation itself is needed. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with a `repository` (an audit of infrastructure-as-code, role-assignment scripts, or access documentation across the workload) or a `file-path` (a targeted re-check of one Bicep, ARM, or PowerShell file that assigns roles or wires identities). The skill produces a single JSON document conforming to the DO output contract.

## Source

The rule set is the team's Azure RBAC and access model. BCQuality's curated knowledge domains do not cover Azure access control, so this skill carries its own rule set in full. Read the BCQuality knowledge index once to confirm no curated domain claims this area (the `knowledge-index.json` Entry's preparation step regenerates over the already-filtered clone); do not open individual article bodies. Because the corpus does not cover RBAC, findings are agent findings within this skill's access-governance domain.

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version` - not meaningful for an Azure access review; treat as `[all]`.
- `technologies` - the intersection of `[powershell, bicep, json]` present in RBAC scripts, ARM exports, and infrastructure definitions.
- `countries` - the configured context, else `unknown`.
- `application-area` - `[all]`.

Discard artifacts that do not declare or modify Azure role assignments, identities, or Key Vault permission models. Retain conditionally applicable rules (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium` and name the unknown dimension in the `message`.

## Worklist

Narrow the access model to the rules that apply to the configuration under review. Group the candidate worklist by area:

- **Least privilege and scope** - the minimum role for the job is granted (read-only where read-only will do); assignments are scoped at the resource group, not the individual resource (a sub-RG single-resource assignment is an exception that needs justifying); expected per-RG assignments hold (Platform team as Contributor; Support team as Reader on `rg-eql-prod-shared`; Key Vault Secrets User for Logic App MIs; Service Bus Data Owner for integration MIs; Monitoring Metrics Publisher for telemetry MIs).
- **Owner restraint** - no Owner at RG level unless role-assignment management is genuinely being delegated, since Contributor handles almost everything.
- **Managed Identity** - runtime auth uses Managed Identity, not stored connection strings or secrets; System-Assigned by default (lifecycle tied to the resource), User-Assigned only when several resources share an identity; the role is assigned to the MI at the target service's RG, not the source.
- **Key Vault** - new vaults use the RBAC permission model, not legacy access policies; Secrets User for consumers, Administrator for the platform team, Secrets Officer for principals that write secrets; Reader is not used expecting it to read secrets (it sees metadata only).
- **What not to do** - no custom roles unless built-ins are genuinely too broad; no persistent elevated assignments (use PIM just-in-time); no connection strings in code; no lingering "just for 5 minutes" assignments.
- **Lifecycle hygiene** - access flows through Entra group membership (no personal RG assignments); PIM eligibility covers occasional elevated roles; offboarding removes group membership and audits recent self-made assignments; a quarterly review reconciles assignments against the roster and documents who holds Owner and why.

A rule enters the worklist when the artifact under review declares, modifies, or documents a role assignment, an identity, or a Key Vault permission model.

## Action

For each worklist item, evaluate the configuration and emit findings (all are agent findings within this skill's domain: `references: []`, `id` prefixed `agent:`, `confidence` capped at `medium` per `skills/do.md`):

- A standing security exposure inferred from IaC is an agent finding capped at `minor` and `medium` unless curated knowledge applies. A direct Azure policy or deployment-validator failure is separate deterministic evidence with a stable resource/policy occurrence key and may carry hard severity.
- A least-privilege or scoping drift that is real but lower-risk (a single-resource assignment that belongs in its own RG; a custom role where a built-in fits; Reader granted at Key Vault expecting secret access; a personal RG assignment that should flow through an Entra group) is a `minor` agent finding.
- A hygiene gap (no documented quarterly review, an undocumented Owner holder, a lingering short-lived assignment past its deadline) is a `minor` agent finding.
- Record satisfied access checks in summary coverage; do not emit findings for them.

Uncited IaC review findings use confidence `medium` or lower. Direct Azure validator evidence or knowledge-backed findings may use `high`. Provide `suggested-code` only for mechanical local edits.

Outcome selection: `completed` when every worklist item was evaluated (including an empty `findings` array); `no-knowledge` when no applicable rule survived Relevance and configuration filtering; `not-applicable` when the task context declares no Azure role assignment, identity, or Key Vault config to review; `partial` when a budget was hit before the worklist was exhausted; `failed` on an unrecoverable error (`outcome-reason` required).

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "al-rbac-and-access", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 2, "info": 0 },
    "coverage": { "worklist-size": 6, "items-evaluated": 6 }
  },
  "findings": [
    {
      "id": "agent:owner-granted-without-delegation-need",
      "severity": "minor",
      "message": "The role assignment grants Owner to the platform-team group at rg-eql-prod-subscription, but the workload manages no role assignments of its own. Owner here over-privileges the group; Contributor covers every operation present. Recommendation: change the role to Contributor and reserve Owner for PIM-eligible activation when role-assignment delegation is actually required.",
      "location": { "file": "infra/rbac/subscription.bicep", "line": 31 },
      "references": [],
      "confidence": "medium",
      "domain": "RBAC"
    },
    {
      "id": "agent:connection-string-instead-of-managed-identity",
      "severity": "minor",
      "message": "The Logic App reads Key Vault via a stored connection string. Runtime auth should use the resource's System-Assigned Managed Identity with Key Vault Secrets User assigned at the vault. Recommendation: enable the MI and replace the connection string with an MI-backed reference.",
      "location": { "file": "infra/logicapp/subscription-workflow.bicep", "line": 58 },
      "references": [],
      "confidence": "medium",
      "domain": "RBAC"
    }
  ],
  "suppressed": []
}
```
