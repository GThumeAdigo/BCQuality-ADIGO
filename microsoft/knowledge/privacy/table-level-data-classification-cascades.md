---
bc-version: [all]
domain: privacy
keywords: [data-classification, table-level, field-inheritance, appsourcecop, as0016, false-positive]
technologies: [al]
countries: [w1]
application-area: [all]
---

# Table-level DataClassification is inherited by fields

## Description

A valid table-level `DataClassification` is the effective default for fields that do not declare their own value. A field-level value overrides that default only for the field on which it is set. AppSourceCop AS0016 accepts Normal fields that inherit a valid table classification; they do not remain `ToBeClassified`. FlowFields and FlowFilters are handled separately by the platform and are covered by `flowfield-flowfilter-classification-systemmetadata.md`.

## Best Practice

Use a table-level classification when it accurately describes the table's fields, and add a field-level classification only where a field stores a different kind of data. Do not flag a Normal field solely because it omits an explicit property when its table supplies a valid default; verify whether the inherited value matches the field's data instead.

See sample: `table-level-data-classification-cascades.good.al`.

## Anti Pattern

Reporting every Normal field without an explicit `DataClassification` when the table already supplies a valid default, or requiring redundant field-level declarations that repeat the table value. A real issue exists when neither scope supplies a valid classification, or when a field's data requires an override of the inherited value.
