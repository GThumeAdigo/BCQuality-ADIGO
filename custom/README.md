# Custom layer

This folder is the populated Custom layer of the GThumeAdigo BCQuality fork. It holds partner-specific knowledge and portable action skills that are not authority for canonical Microsoft or Community content. It follows the same READ and DO contracts as the other layers, so consumers can load it alongside `/microsoft/` and `/community/`.

## Structure

```
custom/
├── knowledge/    # Knowledge files (same format as /microsoft/knowledge/)
└── skills/       # Action skills (Source -> Relevance -> Worklist -> Action -> Output)
```

Knowledge files in `/custom/knowledge/` follow the frontmatter schema and section rules in [`/skills/read.md`](../skills/read.md) and [`/skills/write.md`](../skills/write.md). Action skills in `/custom/skills/` follow the contract in [`/skills/do.md`](../skills/do.md).

## What is here

This layer was seeded by migrating the Business Central AL assets from the `community-integration` project into BCQuality formats.

### Knowledge (`custom/knowledge/`)

| Domain | Articles | Covers |
|---|---|---|
| `integration` | 15 | The modern integration pattern catalog from the BCTechDays 2026 "Designing Modern Integrations" session: staging through the Integration Message, inbound and outbound idempotency, polling framing records, the single staging endpoint, the wait-loop anti-pattern, Business Event versioning and payload safety, correlation propagation, long-running 202 / status-url flows, staged pipelines, batching trade-offs, error classification, manual resolution, and the hard anti-patterns. |
| `api` | 2 | Exposing BC entities as API pages for external agents, and least-privilege MCP tool surfaces. |
| `operations` | 2 | SaaS point-in-time restore limits, and inspecting the AL runtime during a debug session. |
| `process` | 1 | Mapping each feature to a reserved AL object ID range during planning. |
| `performance` | 1 | Profiling before optimising with the built-in Performance Profiler. |

Most integration articles ship `.good.al.txt` / `.bad.al.txt` companion samples.

### Skills (`custom/skills/`)

| Folder | Skills | Notes |
|---|---|---|
| `review/` | 14 | AL review leaves for code quality, readability, performance, tables, permissions, events, translations, multi-tenancy, obsolescence, upgrade, integrations, AppSource, and major-release readiness, plus the `al-extended-review` super-skill. |
| `testing/` | 10 | Test writing, validation, execution, coverage, user-guide testing, web-client verification, extension test-guide review, Page Scripting e2e review, and AI test-driven development. |
| `integration/` | 4 | Modern BC integration patterns, Azure integration review, general BC integration architecture, and Business Central MCP data-surface review. |
| `appsource/` | 2 | AppSource validation and major-release governance. |
| `pipelines/` | 3 | AL-Go pipeline review, environment onboarding, and AL MCP Server workflow review. |
| `copilot/` | 4 | Copilot PromptDialog, Copilot capability, AI Agent SDK, and AI development toolkit reviews. |
| `workflow/` | 4 | `portable-*` project-definition, feature-specification, feature-plan, and implementation-conformance reviews. These evaluate supplied artifacts and cannot be confused with a consumer scaffold's governance gates. |
| `meta/` | 1 | BCQuality consumption and fork/submodule integration review. |
| `operations/` | 5 | Performance profiling, SaaS restore, RBAC, security-group setup, and MCP troubleshooting procedures. |
| **Total** | **47** | **Nine skill categories.** |

## How to use

Use this fork as a Git submodule or as a filtered committed vendor tree. Knowledge files in `/custom/knowledge/` follow the same frontmatter schema and section requirements as every other layer. Action skills in `/custom/skills/` follow the Action Skill template defined in `/skills/`; consumer-specific agent names, paths, and gates belong in the consuming scaffold rather than in these portable skills.

When agents consume BCQuality, the custom layer is loaded alongside Microsoft and Community — your overrides apply automatically. Portable workflow action ids are `portable-spec-init`, `portable-spec-feature`, `portable-plan-feature`, and `portable-implement-feature`.
