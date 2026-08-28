---
bc-version: [all]
domain: process
keywords: [plan, object-id-range, al-objects, task-list, data-model, feature-development]
technologies: [al]
countries: [w1]
application-area: [all]
---

# Map each feature to an object ID range

## Description

Between a feature specification and implementation comes a technical plan that maps the what onto the how: which standard BC modules to reuse, which custom AL objects are genuinely needed, and an object table giving each new object a name, type, and an ID inside the feature's reserved object ID range. The plan also captures the data model, integration points, applicable cross-cutting concerns, and an ordered, checkable task list. Doing this before writing production AL keeps object IDs inside the assigned range, surfaces the standard-versus-custom decision explicitly, and gives implementation a sequenced list rather than an open-ended coding task.

The object table turns a reserved range into concrete allocations. Choosing each object's ID up front, against the range assigned by the project or solution owner, prevents feature collisions and exposes an out-of-range object as a plan defect rather than late rework. The task list does the same for sequencing: by naming the implementation and applicable cross-cutting work, it prevents required work from being remembered only after the feature code is written.

## Best Practice

Before implementing, write a plan that decides what standard BC to reuse and what custom AL is needed, with every new object assigned an ID inside the feature's reserved range. Produce an ordered task list that covers the planned objects and the permissions, privacy, security, telemetry, performance, integration, and upgrade work that actually applies. Require a migration step only when supplied release or deployment context establishes that the affected schema has shipped or may contain persisted data. Review the plan and object list before writing production AL.

## Anti Pattern

Implementing a feature with no object plan, so object IDs are picked ad hoc outside the reserved range, the reuse-versus-custom decision is made implicitly while coding, and there is no ordered task list to work through. The consequence is ID collisions, missed cross-cutting work, and late rework. The signal is new AL objects outside the assigned range or implementation beginning without a plan that maps the feature to a concrete object list and task sequence.
