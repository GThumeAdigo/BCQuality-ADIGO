---
kind: action-skill
id: al-ai-agent-sdk
version: 1
title: BC Agent SDK Definition Review
description: Reviews AL source that defines and registers a custom Business Central agent with the AI Agent SDK and emits a findings report.
inputs: [pr-diff, file-path]
outputs: [findings-report]
bc-version: [all]
technologies: [al]
countries: [w1]
application-area: [all]
---

# BC Agent SDK Definition Review

Reviews AL source that defines and registers a custom Business Central agent through the AI Agent SDK (the `IAgentFactory`, `IAgentMetadata`, and `IAgentTaskExecution` triple-interface pattern, the `Agent Metadata Provider` enum extension, and the paired Copilot Capability registration) and emits a findings report. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with either a `pr-diff` (the standard PR-review entry point for an agent extension change) or a `file-path` (single-file review of an agent factory, metadata, task-execution, or install codeunit). The skill produces a single JSON document conforming to the DO output contract. The Agent SDK is a preview feature, so the review treats preview-lifecycle gaps as real findings rather than ignoring them.

## Source

The rule set is this skill's own agent-definition knowledge plus any BCQuality knowledge entries whose domain covers the concerns it touches (style for labels and captions, security for permission and entitlement gates). Read the BCQuality knowledge index once (the `knowledge-index.json` regenerated at the root of the live, already-filtered clone) and take the `style` and `security` domain entries as the citable candidate set across every enabled layer. Do not open an individual article body at this step; open an article only once it enters the Worklist. The Agent SDK interface contract, the paired capability registration, and the BC 28.1+ permission model are not covered by the corpus; for a concrete violation there, emit an agent finding within this skill's agent-definition domain.

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version` - the target BC version from the consuming app's `app.json`, or `unknown` if unavailable. The permission default changes at BC 28.1, so this dimension is load-bearing.
- `technologies` - `[al]`.
- `countries` - the countries declared in the app's `app.json`; default to the orchestrator's configured context, else `unknown`.
- `application-area` - the union of application areas declared by the changed objects; pass the actual set, do not substitute `[all]`.

Discard files not applicable to AL agent extensions. Retain conditionally applicable rules (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium` and name the unknown dimension in the `message`.

## Worklist

Narrow to the rules that apply to the agent definition under review. A rule enters the worklist when the diff or file touches its area:

- **Provider registration** - an `enumextension` of `Agent Metadata Provider` wires all three interfaces (`IAgentFactory`, `IAgentMetadata`, `IAgentTaskExecution`) onto each agent value.
- **`IAgentFactory`** - `GetFirstTimeSetupPageId` returns a page whose source table holds a `User Security ID : Guid` field; `ShowCanCreateAgent` gates correctly; `GetDefaultProfile` and `GetDefaultAccessControls` are provided.
- **`IAgentMetadata`** - `GetSetupPageId`, `GetAgentTaskMessagePageId`, `GetAgentAnnotations`, and `GetSummaryPageId` are implemented; the summary page stays a focused numeric KPI view.
- **`IAgentTaskExecution`** - `AnalyzeAgentTaskMessage` mutates only `Type::Output`; text is changed via `codeunit "Agent Message".UpdateText`; `Severity::Error` versus `Severity::Warning` is chosen deliberately; `GetAgentTaskUserInterventionSuggestions` supplies meaningful suggestions.
- **Paired Copilot Capability** - an `enumextension` of `Copilot Capability` exists and is registered at install with an `IsCapabilityRegistered` guard before `RegisterCapability`, with valid availability and billing values.
- **Permissions (BC 28.1+)** - admin-only creation, when intended, is enforced via `ShowCanCreateAgent` returning `AgentSystemPermissions.CurrentUserHasCanManageAllAgentsPermission()`.

## Action

For each worklist item, evaluate the AL and emit findings. Reframe the correct-build rules as defects to flag:

- **Missing setup identity field or capability registration guard.** Emit capped agent findings unless curated knowledge applies; direct install/platform failures are separate evidence with a stable agent-type/check occurrence key. Suggest the mechanical guard where determinable:

  ```al
  if not CopilotCapability.IsCapabilityRegistered(Enum::"Copilot Capability"::"My Agent Capability") then
      CopilotCapability.RegisterCapability(
          Enum::"Copilot Capability"::"My Agent Capability",
          Enum::"Copilot Availability"::Preview,
          Enum::"Copilot Billing Type"::"Microsoft Billed",
          LearnMoreUrlTxt);
  ```

- **Missing paired capability or input-message mutation.** Emit capped agent findings unless curated knowledge applies; direct runtime/platform failures are separate evidence with a stable agent-type/check occurrence key.
- **Raising `Severity::Error` on minor or recoverable issues.** `Error` halts the task; prefer `Warning` plus intervention suggestions. Flag `minor` when a recoverable condition is escalated to `Error`.
- **Creation-path and enum-value defects.** Emit capped agent findings unless curated knowledge applies; direct compiler/platform validation is separate evidence with a stable agent-type/check occurrence key.
- **Bypassing `Agent Message.UpdateText` for text changes.** Direct field writes to message text are unsafe; flag `minor` and recommend `UpdateText`.

Cite a `style` or `security` knowledge file when one maps; otherwise emit a capped agent finding. A direct compiler/install/platform failure is separate evidence with a stable agent-type/check occurrence key. `high` confidence is available only to unambiguous knowledge-backed findings or deterministic tool observations; agent findings remain at `medium` or lower.

Outcome selection: `completed` when every worklist item was evaluated (including an empty `findings` array); `no-knowledge` when no applicable rule survived Source, Relevance, and configuration filtering; `not-applicable` when the change defines no agent and touches no Agent SDK surface; `partial` when a budget was hit before the worklist was exhausted; `failed` on an unrecoverable error (`outcome-reason` required).

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "al-ai-agent-sdk", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 2, "info": 0 },
    "coverage": { "worklist-size": 6, "items-evaluated": 6 }
  },
  "findings": [
    {
      "id": "agent:setup-page-missing-user-security-id",
      "severity": "minor",
      "message": "The first-time setup page returned by GetFirstTimeSetupPageId has a source table with no 'User Security ID : Guid' field. BC injects the new agent's user id into that field, so creation will fail. Recommendation: add a field of type Guid named 'User Security ID' to the source table.",
      "location": { "file": "src/Agent/MyAgentSetup.Page.al", "line": 12 },
      "references": [],
      "confidence": "medium",
      "domain": "AI Agent SDK"
    },
    {
      "id": "agent:register-capability-unguarded",
      "severity": "minor",
      "message": "RegisterCapability is called without a preceding IsCapabilityRegistered check, so a re-install throws on duplicate registration. Recommendation: guard the call with IsCapabilityRegistered.",
      "location": { "file": "src/Agent/MyAgentInstall.Codeunit.al", "line": 18 },
      "references": [],
      "confidence": "medium",
      "domain": "AI Agent SDK",
      "suggested-code": "        if not CopilotCapability.IsCapabilityRegistered(Enum::\"Copilot Capability\"::\"My Agent Capability\") then\n            CopilotCapability.RegisterCapability("
    }
  ],
  "suppressed": []
}
```
