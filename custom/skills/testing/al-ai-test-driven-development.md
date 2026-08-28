---
kind: action-skill
id: al-ai-test-driven-development
version: 1
title: AI Test-Driven Development Review
description: Reviews Business Central Copilot and agent test suites against the Evaluation-tool TDD discipline and emits a findings report.
inputs: [pr-diff, file-path, repository]
outputs: [findings-report]
bc-version: [all]
technologies: [al, json, xml]
countries: [w1]
application-area: [all]
---

# AI Test-Driven Development Review

Reviews how Copilot features and custom agents in Business Central are tested with the Evaluation tool (formerly "AI Test Toolkit"), and emits a findings report. The framework is data-driven: datasets describe inputs and expected outputs while the test codeunit drives the loop, so this skill checks that the test codeunit attributes, the dataset shapes, the turn loop, intervention contracts, suite-setup discipline, and credit handling all follow the framework rules. This is a leaf action skill: it invokes no sub-skills.

An orchestrator invokes this skill with a `pr-diff` (a change to prompts, metaprompts, agent instructions, test codeunits, or datasets), a `file-path` (a single test codeunit, dataset, or suite XML), or a `repository` (an audit of an existing AI test suite). The skill produces a single JSON document conforming to the DO output contract.

## Source

The rule set is the Evaluation-tool TDD discipline for Copilot features and agents: test-codeunit attributes, the AI-test versus agent-test flows, the turn loop, intervention validation, dataset shapes, suite XML, suite-setup stickiness, and Copilot credit tracking. Where a check maps onto a curated BCQuality rule (test isolation, telemetry tagging, label usage), read the BCQuality knowledge index once and take the `testing` and `style` domain entries as the citable candidate set across every enabled layer; do not open an article's body until it enters the Worklist. The Evaluation-tool, intervention-contract, and credit-budget rules are not covered by the corpus; for a concrete violation there, emit an agent finding within this skill's AI-testing domain.

Reference material the rules derive from:

- Evaluation: https://learn.microsoft.com/dynamics365/business-central/dev-itpro/developer/ai-test-copilot-testtool
- Datasets: https://learn.microsoft.com/dynamics365/business-central/dev-itpro/developer/ai-test-copilot-datasets
- Write agent tests: https://learn.microsoft.com/dynamics365/business-central/dev-itpro/developer/ai-test-copilot-agent-tests
- BC-Bench (release plan): https://learn.microsoft.com/dynamics365/release-plan/2026wave1/smb/dynamics365-business-central/evaluate-al-coding-agents-bc-bench
- BCApps AI Test Toolkit README: https://github.com/microsoft/BCApps/blob/main/src/Tools/AI%20Test%20Toolkit/README.md
- BCTech SalesValidationAgent sample: https://github.com/microsoft/BCTech/tree/master/samples/BCAgents/SalesValidationAgent

## Relevance

Apply the frontmatter matching rules defined in READ against the task context:

- `bc-version` - the target BC version from the test app's `app.json`, or `unknown` if unavailable.
- `technologies` - the intersection of `[al, json, xml]` present in tests, datasets, and suite definitions.
- `countries` - the countries declared in the consuming app's `app.json`; default to the orchestrator's configured context, else `unknown`.
- `application-area` - the union of application areas exercised by the tested Copilot capability or agent; pass the actual set, do not substitute `[all]`.

Discard files not applicable to AL Copilot or agent tests. Retain conditionally applicable rules (any dimension `unknown`) only when configuration permits; findings derived from them have `confidence` no higher than `medium` and name the unknown dimension in the `message`.

## Worklist

Narrow to the rules that apply to the test artifacts under review. A rule enters the worklist when the diff, file, or repository touches the corresponding token or artifact.

- **Test codeunit attributes** - an agent test must set `Subtype = Test`, `TestType = AITest`, `TestPermissions = Disabled`, and `RequiredTestIsolation = Disabled`. Agent tasks run in a different session and span transactions, so isolation cannot be enforced. A prompt-only AI test uses `TestType = AITest` but runs inline and does not need disabled isolation.
- **Two test flows** - an AI test (prompt-based Copilot features, PromptDialog plus AOAI call) accepts JSONL or YAML. An agent test (multi-turn agents with intervention) is YAML only. The dataset shape and the codeunit's `TestType` must match the flow.
- **Required codeunits** - `AIT Test Context` (read dataset values), `Library - Agent` (turn dispatcher, agent tests only), `Library Assert`, `Test Input Json`, `Agent Task Builder`, `Agent Task Message Builder`.
- **The agent turn loop** - a `repeat ... until not ContinueWithNextTurn` loop delegating to `Library - Agent`, using `RunTurnAndWait(AgentUserSecurityId, var AgentTask)` and `FinalizeTurn(var AgentTask, TurnSuccessful, ErrorReason)`. Validators must return `false` with a populated `ErrorReason` rather than calling `Error()`, so `FinalizeTurn` can log the failure on the turn.
- **Initialize and agent resolution** - `Initialize()` resolves the agent (optionally via `GetAgentUnderTest()` for A/B), stops old tasks, ensures the agent is active, and guards on an `Initialized` flag.
- **Dataset shapes** - AI-test datasets use `test_setup`/`expected_data`; agent datasets always use `turns:` even for single-turn, under conventional `.resources/` folders. Date placeholders `$DateFormula-<formula>$` (and the `$DateTimeFormula-...$` variants) must be quoted in YAML because `< >` conflict with flow syntax.
- **Intervention validation** - `expected_data.intervention_request` is the only sub-key the framework reads automatically. `FinalizeTurn` enforces both directions: a declared `intervention_request` requires the agent to pause with matching type and suggestions; no declaration requires the agent not to pause. A later turn resumes via `query.intervention` using either `suggestion` or `instruction`, never both.
- **Suite XML** - `TestRunnerId="130451"` (Test Runner - Isol. Disabled) is required for agent tests; `TestType="Agent"` opts into the agent runner versus `"AITest"` for prompt-only; `<Language>` children enable multilingual evaluation.
- **Suite-setup discipline** - `IsSuiteSetupDone()` is sticky across runs; after `SetEvalSuiteSetupCompleted()` the suite skips setup until **Reset Suite Setup** is used.
- **Dataset loading** - ship datasets as test-app `.resources/` files and import them in an Install codeunit via `NavApp.ListResources`/`GetResource` and `AITALTestSuiteMgt.ImportTestInputs`.
- **Copilot credits** - runs consume credits tracked per suite run, per test line, and per dataset entry; limits are enforced at environment and company levels. For agent tests the displayed token usage is AI-evaluator tokens only, not the agent's runtime tokens.
- **Results, sensitivity, permissions** - page `149038` `AIT Log Entry API` exposes results; the `Sensitive` flag hides PII/proprietary datasets; running Evaluation needs the `AI TEST TOOLKIT` permission set and credit-limit edits need the `agent admin` role.

## Action

For each worklist item, evaluate the test artifacts and emit findings:

- Missing isolation, invalid dataset shape, validator-contract, intervention, placeholder, and runner-id defects found by source review are capped agent findings unless a curated rule applies. A named test runner's direct refusal or failed execution is separate deterministic evidence with a stable suite/test occurrence key and may gate.
- A missing **Reset Suite Setup** step after editing setup YAML (new setup silently ignored), confusing AI-evaluator tokens with runtime tokens when budgeting credits, or a missing `Sensitive` flag on a dataset that carries PII, is `minor`.
- Record satisfied test-design checks in summary coverage; do not emit findings for them.

Cite a `testing` or `style` knowledge file when one matches; otherwise emit a capped agent finding. `high` confidence is available only to unambiguous knowledge-backed findings or deterministic tool observations; agent findings remain at `medium` or lower. Provide `suggested-code` for mechanical fixes. BC-Bench (April 2026 GA) is out of scope for project-specific tests and must not be flagged here.

Outcome selection: `completed` when every worklist item was evaluated (including an empty `findings` array); `no-knowledge` when no applicable rule survived Source, Relevance, and configuration filtering; `not-applicable` when the task context has no Copilot or agent test to review; `partial` when a budget was hit before the worklist was exhausted; `failed` on an unrecoverable error (`outcome-reason` required).

## Output

Output conforms to the DO output contract. A populated example:

```json
{
  "skill": { "id": "al-ai-test-driven-development", "version": 1 },
  "outcome": "completed",
  "summary": {
    "counts": { "blocker": 0, "major": 0, "minor": 2, "info": 0 },
    "coverage": { "worklist-size": 5, "items-evaluated": 5 }
  },
  "findings": [
    {
      "id": "agent:agent-test-missing-disabled-isolation",
      "severity": "minor",
      "message": "Codeunit 50200 is an agent test (TestType = AITest, drives Library - Agent turns) but does not set RequiredTestIsolation = Disabled. Agent tasks run in a separate session and span transactions, so the suite cannot run. Recommendation: add RequiredTestIsolation = Disabled; to the codeunit properties.",
      "location": { "file": "test/MyAgentAccuracy.Codeunit.al", "line": 4 },
      "references": [],
      "confidence": "medium",
      "domain": "AI Test-Driven Development",
      "suggested-code": "    RequiredTestIsolation = Disabled;"
    },
    {
      "id": "agent:unquoted-dateformula-placeholder",
      "severity": "minor",
      "message": "A dataset value uses $DateFormula-<CW+1M>$ without quotes. The < > characters conflict with YAML flow syntax and the placeholder will fail to parse. Recommendation: wrap the value in double quotes.",
      "location": { "file": "test/.resources/datasets/MY-DATASET.yaml", "line": 14 },
      "references": [],
      "confidence": "medium",
      "domain": "AI Test-Driven Development",
      "suggested-code": "          Shipment Date: \"$DateFormula-<CW+1M>$\""
    }
  ],
  "suppressed": []
}
```
