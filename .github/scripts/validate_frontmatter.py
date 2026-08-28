#!/usr/bin/env python3
"""
BCQuality content validator.

Validates frontmatter, sections, and structural rules for knowledge files,
action skills, meta-skills, and the entry-point skill. Rules derived from
/skills/read.md, /skills/write.md, /skills/do.md, and /skills/entry.md.

Usage:
    python .github/scripts/validate_frontmatter.py [--root PATH]

Exit status: 0 on success (no errors), 1 on any error. Warnings do not fail.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: PyYAML is required. Install with: pip install pyyaml\n")
    sys.exit(2)


# --- Schema constants -------------------------------------------------------

KNOWLEDGE_REQUIRED_KEYS = {
    "bc-version", "domain", "keywords", "technologies",
    "countries", "application-area",
}
ACTION_SKILL_REQUIRED_KEYS = {
    "kind", "id", "version", "title", "description", "inputs", "outputs",
}
ACTION_SKILL_OPTIONAL_KEYS = {
    "bc-version", "technologies", "countries", "application-area", "sub-skills",
}
META_SKILL_REQUIRED_KEYS = {"kind", "id", "version", "title"}
ENTRY_SKILL_REQUIRED_KEYS = {"kind", "id", "version", "title"}

STANDARD_INPUTS = {
    "pr-diff", "object-list", "file-path", "repository", "telemetry-query",
    "deployment-context",
}
ALLOWED_OUTPUTS = {"findings-report"}
VALID_SAMPLE_KINDS = {"good", "bad"}

ACTION_SKILL_SECTIONS = ["Source", "Relevance", "Worklist", "Action", "Output"]

LAYERS = ("microsoft", "community", "custom")
META_SKILL_FILES = {"read.md", "write.md", "do.md"}
ENTRY_SKILL_FILE = "entry.md"

MAX_KNOWLEDGE_LINES = 100

KEBAB_CASE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ISO_ALPHA2 = re.compile(r"^[a-z]{2}$")
RANGE_SHORTHAND = re.compile(r"^(\d+)\.\.(\d+)?$")
FENCED_CODE_BLOCK = re.compile(r"^```", re.MULTILINE)
JSON_CODE_BLOCK = re.compile(r"^```json\s*\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)
HEADING_H2 = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
SAMPLE_REFERENCE = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*\.(?:good|bad)\.[a-z0-9]+(?:\.txt)?)`")


# --- Diagnostics ------------------------------------------------------------

@dataclass
class Diagnostic:
    level: str            # "error" | "warning"
    path: Path
    rule: str             # e.g. "R03"
    message: str
    line: int | None = None

    def format_plain(self, root: Path) -> str:
        rel = self.path.relative_to(root).as_posix()
        prefix = rel if self.line is None else f"{rel}:{self.line}"
        return f"{prefix}: [{self.rule}] {self.level}: {self.message}"

    def format_gha(self, root: Path) -> str:
        rel = self.path.relative_to(root).as_posix()
        loc = f"file={rel}"
        if self.line is not None:
            loc += f",line={self.line}"
        return f"::{self.level} {loc}::[{self.rule}] {self.message}"


@dataclass
class Report:
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def error(self, path: Path, rule: str, message: str, line: int | None = None) -> None:
        self.diagnostics.append(Diagnostic("error", path, rule, message, line))

    def warn(self, path: Path, rule: str, message: str, line: int | None = None) -> None:
        self.diagnostics.append(Diagnostic("warning", path, rule, message, line))

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.level == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.level == "warning"]


# --- Frontmatter parsing ----------------------------------------------------

@dataclass
class Parsed:
    frontmatter: dict[str, Any] | None
    body: str
    body_start_line: int              # 1-based line number where body begins
    raw_lines: list[str]
    frontmatter_error: str | None     # yaml or delimiter issue


def parse_markdown(text: str) -> Parsed:
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return Parsed(None, text, 1, lines, "missing opening '---' frontmatter delimiter")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return Parsed(None, text, 1, lines, "missing closing '---' frontmatter delimiter")
    yaml_text = "\n".join(lines[1:end_idx])
    try:
        fm = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as e:
        return Parsed(None, text, end_idx + 2, lines, f"YAML parse error: {e}")
    if not isinstance(fm, dict):
        return Parsed(None, text, end_idx + 2, lines, "frontmatter must be a YAML mapping")
    body = "\n".join(lines[end_idx + 1:])
    return Parsed(fm, body, end_idx + 2, lines, None)


# --- Small helpers ----------------------------------------------------------

def is_non_empty_list_of_str(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0 and all(isinstance(v, str) and v for v in value)


def expand_bc_version(value: Any) -> tuple[list[int] | str | None, str | None]:
    """Return (expanded, error-message). One of the two is None.

    For the universal sentinel ["all"], `expanded` is the string "all".
    For an open-ended range like ["26.."], `expanded` is the normalized
    string "26.." (it cannot be enumerated; consumers match target >= 26).
    Otherwise it is the expanded list of version integers.
    """
    if not isinstance(value, list) or not value:
        return None, "must be a non-empty list"
    # Case 0: universal sentinel
    if len(value) == 1 and value[0] == "all":
        return "all", None
    if "all" in value:
        return None, "'all' is mutually exclusive with explicit versions"
    # Case 1: all integers
    if all(isinstance(v, int) and not isinstance(v, bool) for v in value):
        if any(v <= 0 for v in value):
            return None, "integers must be positive"
        return sorted(set(value)), None
    # Case 2: single-element range shorthand — closed "[26..28]" or open-ended "[26..]"
    if len(value) == 1 and isinstance(value[0], str):
        m = RANGE_SHORTHAND.match(value[0].strip())
        if m:
            start = int(m.group(1))
            if m.group(2) is None:
                # Open-ended: "start.." applies from start onwards, no upper bound.
                return f"{start}..", None
            end = int(m.group(2))
            if start > end:
                return None, f"range '{value[0]}' is not ascending"
            return list(range(start, end + 1)), None
    return None, "must be [all], a list of integers, or a range shorthand like [26..28] or [26..]"


def headings_in_order(body: str) -> list[tuple[str, int]]:
    """Return list of (heading-text, 1-based line-number-within-body) pairs."""
    out = []
    for i, line in enumerate(body.splitlines(), start=1):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            out.append((m.group(1).strip(), i))
    return out


# --- Validators -------------------------------------------------------------

def validate_knowledge(path: Path, parsed: Parsed, report: Report) -> None:
    # R01 frontmatter parseable
    if parsed.frontmatter_error:
        report.error(path, "R01", parsed.frontmatter_error, 1)
        return
    fm = parsed.frontmatter
    assert fm is not None

    # R02 required keys, no extras, none empty
    missing = KNOWLEDGE_REQUIRED_KEYS - fm.keys()
    extras = fm.keys() - KNOWLEDGE_REQUIRED_KEYS
    if missing:
        report.error(path, "R02", f"missing required frontmatter keys: {sorted(missing)}", 1)
    if extras:
        report.error(path, "R02", f"unexpected frontmatter keys: {sorted(extras)}", 1)
    for k in KNOWLEDGE_REQUIRED_KEYS & fm.keys():
        v = fm[k]
        if v is None or v == "" or v == []:
            report.error(path, "R02", f"frontmatter key '{k}' must not be empty", 1)

    # R03 bc-version
    if "bc-version" in fm:
        _, err = expand_bc_version(fm["bc-version"])
        if err:
            report.error(path, "R03", f"bc-version: {err}", 1)

    # R04 domain
    if "domain" in fm:
        if not isinstance(fm["domain"], str) or not fm["domain"].strip():
            report.error(path, "R04", "domain must be a non-empty string", 1)
        elif fm["domain"] != path.parent.name:
            report.error(
                path,
                "R27",
                f"frontmatter domain '{fm['domain']}' must match directory '{path.parent.name}'",
                1,
            )

    # R05 keywords
    if "keywords" in fm:
        kw = fm["keywords"]
        if not is_non_empty_list_of_str(kw):
            report.error(path, "R05", "keywords must be a non-empty list of strings", 1)
        else:
            bad = [k for k in kw if not KEBAB_CASE.match(k)]
            if bad:
                report.error(path, "R05", f"keywords must be lowercase kebab-case: {bad}", 1)
            if len(kw) > 10:
                report.warn(path, "R05", f"keywords count is {len(kw)}; consider trimming toward ≤10", 1)

    # R06 technologies
    if "technologies" in fm:
        t = fm["technologies"]
        if not is_non_empty_list_of_str(t):
            report.error(path, "R06", "technologies must be a non-empty list of strings", 1)
        elif "all" in t:
            report.error(path, "R06", "technologies must not use the 'all' sentinel; list each technology explicitly", 1)

    # R07 countries
    if "countries" in fm:
        c = fm["countries"]
        if not is_non_empty_list_of_str(c):
            report.error(path, "R07", "countries must be a non-empty list of strings", 1)
        elif "w1" in c and len(c) > 1:
            report.error(path, "R07", "'w1' is mutually exclusive with country codes", 1)
        elif "w1" not in c:
            bad = [x for x in c if not ISO_ALPHA2.match(x)]
            if bad:
                report.error(path, "R07", f"countries must be lowercase ISO alpha-2 codes or [w1]: {bad}", 1)

    # R08 application-area
    if "application-area" in fm:
        a = fm["application-area"]
        if not is_non_empty_list_of_str(a):
            report.error(path, "R08", "application-area must be a non-empty list of strings", 1)
        elif "all" in a and len(a) > 1:
            report.error(path, "R08", "'all' is mutually exclusive with specific application areas", 1)

    # R09 has ## Description
    headings = [h for h, _ in headings_in_order(parsed.body)]
    if "Description" not in headings:
        report.error(path, "R09", "missing required '## Description' section")

    # R10 no fenced code blocks
    for match in FENCED_CODE_BLOCK.finditer(parsed.body):
        # offset to a 1-based line number in the original file
        prefix = parsed.body[: match.start()]
        body_line = prefix.count("\n") + 1
        file_line = parsed.body_start_line + body_line - 1
        report.error(path, "R10", "knowledge files must not contain fenced code blocks", file_line)
        break  # one is enough; don't spam

    # R11 file size ≤ 100 lines
    total_lines = len(parsed.raw_lines)
    if total_lines > MAX_KNOWLEDGE_LINES:
        report.error(path, "R11", f"file is {total_lines} lines; max is {MAX_KNOWLEDGE_LINES}")


def validate_action_skill(path: Path, parsed: Parsed, report: Report) -> None:
    if parsed.frontmatter_error:
        report.error(path, "R01", parsed.frontmatter_error, 1)
        return
    fm = parsed.frontmatter
    assert fm is not None

    # R15 required keys; warn on unknown
    missing = ACTION_SKILL_REQUIRED_KEYS - fm.keys()
    if missing:
        report.error(path, "R15", f"missing required action-skill keys: {sorted(missing)}", 1)
    unknown = fm.keys() - ACTION_SKILL_REQUIRED_KEYS - ACTION_SKILL_OPTIONAL_KEYS
    if unknown:
        report.warn(path, "R15", f"unknown action-skill keys: {sorted(unknown)}", 1)
    for k in ACTION_SKILL_REQUIRED_KEYS & fm.keys():
        v = fm[k]
        if v is None or v == "" or v == []:
            report.error(path, "R15", f"action-skill key '{k}' must not be empty", 1)

    # R25 kind matches path
    if fm.get("kind") != "action-skill":
        report.error(path, "R25", f"file is in a layer skills folder but kind is '{fm.get('kind')}', expected 'action-skill'", 1)

    # R16 id kebab-case, version positive int
    if "id" in fm:
        if not isinstance(fm["id"], str) or not KEBAB_CASE.match(fm["id"]):
            report.error(path, "R16", f"id must be lowercase kebab-case: '{fm['id']}'", 1)
    if "version" in fm:
        v = fm["version"]
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            report.error(path, "R16", f"version must be a positive integer: {v!r}", 1)

    # R17 inputs
    if "inputs" in fm:
        inp = fm["inputs"]
        if not is_non_empty_list_of_str(inp):
            report.error(path, "R17", "inputs must be a non-empty list of strings", 1)
        else:
            unknown_inputs = [x for x in inp if x not in STANDARD_INPUTS]
            if unknown_inputs:
                report.warn(path, "R17", f"inputs contains non-standard values {unknown_inputs}; standard set is {sorted(STANDARD_INPUTS)}", 1)

    # R18 outputs
    if "outputs" in fm:
        out = fm["outputs"]
        if not is_non_empty_list_of_str(out):
            report.error(path, "R18", "outputs must be a non-empty list of strings", 1)
        else:
            bad = [x for x in out if x not in ALLOWED_OUTPUTS]
            if bad:
                report.error(path, "R18", f"outputs contains non-allowed values {bad}; currently only {sorted(ALLOWED_OUTPUTS)} is defined", 1)

    # R19 optional filter dimensions, if present
    if "bc-version" in fm:
        _, err = expand_bc_version(fm["bc-version"])
        if err:
            report.error(path, "R19", f"bc-version: {err}", 1)
    if "technologies" in fm:
        t = fm["technologies"]
        if not is_non_empty_list_of_str(t):
            report.error(path, "R19", "technologies must be a non-empty list of strings", 1)
        elif "all" in t:
            report.error(path, "R19", "technologies must not use the 'all' sentinel", 1)
    if "countries" in fm:
        c = fm["countries"]
        if not is_non_empty_list_of_str(c):
            report.error(path, "R19", "countries must be a non-empty list of strings", 1)
        elif "w1" in c and len(c) > 1:
            report.error(path, "R19", "'w1' is mutually exclusive with country codes", 1)
        elif "w1" not in c:
            bad = [x for x in c if not ISO_ALPHA2.match(x)]
            if bad:
                report.error(path, "R19", f"countries must be ISO alpha-2 or [w1]: {bad}", 1)
    if "application-area" in fm:
        a = fm["application-area"]
        if not is_non_empty_list_of_str(a):
            report.error(path, "R19", "application-area must be a non-empty list of strings", 1)
        elif "all" in a and len(a) > 1:
            report.error(path, "R19", "'all' is mutually exclusive with specific application areas", 1)

    # R20 sub-skills shape
    if "sub-skills" in fm:
        ss = fm["sub-skills"]
        if not is_non_empty_list_of_str(ss):
            report.error(path, "R20", "sub-skills must be a non-empty list of repo-relative paths", 1)
        else:
            normalized_entries = [entry.lstrip("./") for entry in ss]
            duplicates = sorted({entry for entry in normalized_entries if normalized_entries.count(entry) > 1})
            if duplicates:
                report.error(path, "R20", f"sub-skills contains duplicate entries: {duplicates}", 1)
            bad = [x for x in ss if not x.endswith(".md")]
            if bad:
                report.error(path, "R20", f"sub-skills entries must end in '.md': {bad}", 1)

    # R21 five required sections, in order, each exactly once
    heads = [h for h, _ in headings_in_order(parsed.body)]
    indices: list[int] = []
    for required in ACTION_SKILL_SECTIONS:
        occurrences = [i for i, h in enumerate(heads) if h == required]
        if not occurrences:
            report.error(path, "R21", f"missing required section '## {required}'")
        elif len(occurrences) > 1:
            report.error(path, "R21", f"section '## {required}' appears {len(occurrences)} times; must appear once")
            indices.append(occurrences[0])
        else:
            indices.append(occurrences[0])
    if len(indices) == len(ACTION_SKILL_SECTIONS) and indices != sorted(indices):
        order = [heads[i] for i in indices]
        report.error(path, "R21", f"required sections out of order: {order}; expected {ACTION_SKILL_SECTIONS}")

    validate_report_examples(path, parsed, report)


def is_review_skill(path: Path, frontmatter: dict[str, Any]) -> bool:
    review_text = f"{frontmatter.get('title', '')} {frontmatter.get('description', '')}"
    return path.parent.name == "review" or bool(re.search(r"\b(review|reviews|audit|audits|validat\w*)\b", review_text, re.IGNORECASE))


def validate_finding(path: Path, finding: Any, report: Report, line: int, review_skill: bool) -> None:
    if not isinstance(finding, dict):
        report.error(path, "R29", "findings entries must be JSON objects", line)
        return
    required = {"id", "severity", "message", "references", "confidence"}
    missing = required - finding.keys()
    if missing:
        report.error(path, "R29", f"finding missing required fields: {sorted(missing)}", line)
    if not isinstance(finding.get("id"), str) or not finding["id"].strip():
        report.error(path, "R29", "finding id must be a non-empty string", line)
    if finding.get("severity") not in {"blocker", "major", "minor", "info"}:
        report.error(path, "R29", f"invalid finding severity: {finding.get('severity')!r}", line)
    if not isinstance(finding.get("message"), str) or not finding["message"].strip():
        report.error(path, "R29", "finding message must be a non-empty string", line)
    if finding.get("confidence") not in {"high", "medium", "low"}:
        report.error(path, "R29", f"invalid finding confidence: {finding.get('confidence')!r}", line)
    finding_id = finding.get("id")
    references = finding.get("references")
    if not isinstance(references, list):
        report.error(path, "R29", "finding references must be an array", line)
        return
    if references:
        primary = references[0]
        if not isinstance(primary, dict) or finding_id != primary.get("path"):
            report.error(path, "R30", "citation finding id must equal references[0].path", line)
        if any(field in finding for field in ("occurrence-key", "evidence", "gating")):
            report.error(path, "R29", "knowledge-backed findings must not carry occurrence-key, evidence, or gating", line)
    elif isinstance(finding_id, str) and finding_id.startswith("agent:"):
        if not re.fullmatch(r"agent:[a-z0-9]+(?:-[a-z0-9]+)*", finding_id):
            report.error(path, "R31", "agent finding id must be agent: followed by a stable kebab-case slug", line)
        if finding.get("severity") in {"major", "blocker"}:
            report.error(path, "R31", "uncited agent finding severity is capped at minor", line)
        if finding.get("confidence") == "high":
            report.error(path, "R31", "uncited agent finding confidence is capped at medium", line)
        if any(field in finding for field in ("occurrence-key", "evidence", "gating")):
            report.error(path, "R31", "agent findings must not carry occurrence-key, evidence, or gating", line)
    elif isinstance(finding_id, str) and finding_id.startswith("evidence:"):
        if not re.fullmatch(r"evidence:[a-z0-9]+(?:-[a-z0-9]+)*", finding_id):
            report.error(path, "R32", "evidence finding id must be evidence: followed by a stable kebab-case slug", line)
        evidence = finding.get("evidence")
        allowed_kinds = {"compiler", "analyzer", "platform-validator", "test-runner", "coverage-tool", "browser-assertion", "tool-envelope"}
        allowed_statuses = {"failed", "error", "timeout", "threshold-failed", "assertion-failed"}
        if not isinstance(evidence, dict):
            report.error(path, "R32", "evidence finding requires an evidence object", line)
        else:
            if set(evidence) != {"kind", "source", "status"}:
                report.error(path, "R32", "evidence object must contain exactly kind, source, and status", line)
            if evidence.get("kind") not in allowed_kinds:
                report.error(path, "R32", f"invalid evidence kind: {evidence.get('kind')!r}", line)
            if not isinstance(evidence.get("source"), str) or not evidence["source"].strip():
                report.error(path, "R32", "evidence source must be a non-empty string", line)
            if evidence.get("status") not in allowed_statuses:
                report.error(path, "R32", f"invalid or passing evidence status: {evidence.get('status')!r}", line)
        if not isinstance(finding.get("gating"), bool):
            report.error(path, "R32", "evidence finding requires boolean gating", line)
        occurrence_key = finding.get("occurrence-key")
        if not isinstance(occurrence_key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._:/-]*", occurrence_key):
            report.error(path, "R32", "evidence finding requires a stable lower-case occurrence-key", line)
    else:
        report.error(path, "R29", "uncited finding id must start with agent: or evidence:", line)
    if review_skill:
        domain = finding.get("domain")
        if not isinstance(domain, str) or not domain.strip():
            report.error(path, "R33", "every review-skill finding requires a non-empty domain", line)
        elif domain != domain.strip() or any(char in domain for char in "\r\n\t"):
            report.error(path, "R33", "review finding domain must be trimmed, single-line display text", line)


def finding_counts(findings: list[Any]) -> dict[str, int]:
    result = {severity: 0 for severity in ("blocker", "major", "minor", "info")}
    for finding in findings:
        if isinstance(finding, dict) and finding.get("severity") in result:
            result[finding["severity"]] += 1
    return result


def rolled_outcome(sub_results: list[dict[str, Any]]) -> str | None:
    outcomes = [result.get("outcome") for result in sub_results]
    if not outcomes:
        return None
    if all(outcome == "failed" for outcome in outcomes):
        return "failed"
    if "partial" in outcomes or ("failed" in outcomes and any(outcome != "failed" for outcome in outcomes)):
        return "partial"
    if all(outcome == "not-applicable" for outcome in outcomes):
        return "not-applicable"
    if all(outcome in {"no-knowledge", "not-applicable"} for outcome in outcomes) and "no-knowledge" in outcomes:
        return "no-knowledge"
    return "completed"


def validate_report_object(path: Path, value: Any, report: Report, line: int, review_skill: bool) -> None:
    if not isinstance(value, dict):
        return
    if not ({"skill", "outcome", "summary", "findings"} & value.keys()):
        return
    required = {"skill", "outcome", "summary", "findings", "suppressed"}
    missing = required - value.keys()
    if missing:
        report.error(path, "R36", f"report missing required fields: {sorted(missing)}", line)
    skill = value.get("skill")
    if (
        not isinstance(skill, dict)
        or set(skill) != {"id", "version"}
        or not isinstance(skill.get("id"), str)
        or not skill.get("id")
        or not isinstance(skill.get("version"), int)
        or isinstance(skill.get("version"), bool)
        or skill.get("version", 0) <= 0
    ):
        report.error(path, "R36", "report skill must contain exactly non-empty string id and positive integer version", line)
    outcome = value.get("outcome")
    allowed_outcomes = {"completed", "not-applicable", "no-knowledge", "partial", "failed"}
    if outcome not in allowed_outcomes:
        report.error(path, "R36", f"invalid report outcome: {outcome!r}", line)
    if outcome in {"partial", "failed"} and (not isinstance(value.get("outcome-reason"), str) or not value["outcome-reason"].strip()):
        report.error(path, "R36", f"outcome-reason is required for {outcome}", line)
    findings = value.get("findings")
    if not isinstance(findings, list):
        report.error(path, "R29", "report findings must be an array", line)
        return
    for finding in findings:
        validate_finding(path, finding, report, line, review_skill)
    evidence_identities = [
        (finding.get("id"), finding.get("occurrence-key"))
        for finding in findings
        if isinstance(finding, dict) and str(finding.get("id", "")).startswith("evidence:")
    ]
    if len(evidence_identities) != len(set(evidence_identities)):
        report.error(path, "R32", "deterministic evidence identities (id, occurrence-key) must be unique within a report", line)
    non_evidence_ids = [
        finding.get("id")
        for finding in findings
        if isinstance(finding, dict) and not str(finding.get("id", "")).startswith("evidence:")
    ]
    if len(non_evidence_ids) != len(set(non_evidence_ids)):
        report.error(path, "R39", "knowledge-backed and agent findings must be deduplicated by id within a report", line)
    if outcome in {"not-applicable", "no-knowledge"} and findings:
        report.error(path, "R36", f"{outcome} reports must have empty findings", line)
    if outcome == "failed" and any(not isinstance(finding, dict) or not str(finding.get("id", "")).startswith("evidence:") for finding in findings):
        report.error(path, "R36", "failed reports may contain only deterministic evidence findings", line)
    summary = value.get("summary")
    if not isinstance(summary, dict):
        report.error(path, "R37", "report summary must be an object", line)
    else:
        counts = summary.get("counts")
        expected_counts = finding_counts(findings)
        if not isinstance(counts, dict) or set(counts) != set(expected_counts) or any(not isinstance(count, int) or isinstance(count, bool) or count < 0 for count in counts.values()):
            report.error(path, "R37", "summary.counts must contain exactly non-negative integer blocker, major, minor, and info counts", line)
        elif counts != expected_counts:
            report.error(path, "R37", f"summary.counts {counts} do not equal findings counts {expected_counts}", line)
        coverage = summary.get("coverage")
        if not isinstance(coverage, dict) or set(coverage) != {"worklist-size", "items-evaluated"}:
            report.error(path, "R37", "summary.coverage must contain exactly worklist-size and items-evaluated", line)
        elif any(not isinstance(count, int) or isinstance(count, bool) or count < 0 for count in coverage.values()) or coverage["items-evaluated"] > coverage["worklist-size"]:
            report.error(path, "R37", "summary.coverage values must be non-negative integers with items-evaluated <= worklist-size", line)
    if not isinstance(value.get("suppressed"), list):
        report.error(path, "R36", "report suppressed must be an array", line)
    sub_results = value.get("sub-results", [])
    if not isinstance(sub_results, list):
        report.error(path, "R38", "sub-results must be an array", line)
    else:
        for sub_result in sub_results:
            validate_report_object(path, sub_result, report, line, review_skill)
        if sub_results:
            expected_outcome = rolled_outcome([result for result in sub_results if isinstance(result, dict)])
            if expected_outcome and outcome != expected_outcome:
                report.error(path, "R38", f"super-skill outcome {outcome!r} does not match rolled outcome {expected_outcome!r}", line)
            if isinstance(summary, dict) and isinstance(summary.get("coverage"), dict):
                expected_coverage = {
                    key: sum(
                        result.get("summary", {}).get("coverage", {}).get(key, 0)
                        for result in sub_results if isinstance(result, dict)
                    )
                    for key in ("worklist-size", "items-evaluated")
                }
                if summary["coverage"] != expected_coverage:
                    report.error(path, "R38", f"super-skill coverage {summary['coverage']} does not equal sub-result rollup {expected_coverage}", line)
            top_findings = [finding for finding in findings if isinstance(finding, dict)]
            producers = {
                result.get("skill", {}).get("id")
                for result in sub_results
                if isinstance(result, dict) and isinstance(result.get("skill"), dict)
            }
            for top_finding in top_findings:
                if top_finding.get("from-sub-skill") not in producers | {"agent"}:
                    report.error(path, "R38", "every super-skill finding must identify a sub-skill producer or agent", line)
            for sub_result in sub_results:
                if not isinstance(sub_result, dict) or not isinstance(sub_result.get("skill"), dict):
                    continue
                producer = sub_result["skill"].get("id")
                for sub_finding in sub_result.get("findings", []):
                    if not isinstance(sub_finding, dict):
                        continue
                    is_evidence = str(sub_finding.get("id", "")).startswith("evidence:")
                    if sub_result.get("outcome") == "failed" and not is_evidence:
                        continue
                    candidates = [finding for finding in top_findings if finding.get("from-sub-skill") == producer]
                    if is_evidence:
                        candidates = [
                            finding for finding in candidates
                            if finding.get("id") == sub_finding.get("id")
                            and finding.get("occurrence-key") == sub_finding.get("occurrence-key")
                        ]
                        if not candidates:
                            report.error(path, "R38", f"rolled evidence from {producer} must preserve id and occurrence-key", line)
                            continue
                        expected = dict(sub_finding)
                        actual = dict(candidates[0])
                        actual.pop("from-sub-skill", None)
                        if actual != expected:
                            report.error(path, "R38", f"rolled evidence from {producer} must be preserved verbatim except from-sub-skill", line)
                    else:
                        references = sub_finding.get("references", [])
                        expected_id = sub_finding.get("id") if references else f"{producer}:{sub_finding.get('id')}"
                        candidates = [finding for finding in candidates if finding.get("id") == expected_id]
                        if not candidates:
                            report.error(path, "R38", f"sub-result finding from {producer} is missing from top-level rollup", line)
                            continue
                        expected = dict(sub_finding)
                        actual = dict(candidates[0])
                        actual.pop("from-sub-skill", None)
                        if not references:
                            actual["id"] = sub_finding.get("id")
                        if actual != expected:
                            report.error(path, "R38", f"rolled finding from {producer} is not preserved by composition rules", line)


def validate_report_examples(path: Path, parsed: Parsed, report: Report) -> None:
    for match in JSON_CODE_BLOCK.finditer(parsed.body):
        line = parsed.body_start_line + parsed.body[:match.start()].count("\n")
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            report.error(path, "R29", f"invalid JSON example: {exc.msg}", line + exc.lineno)
            continue
        frontmatter = parsed.frontmatter or {}
        if isinstance(value, dict) and ({"skill", "outcome", "summary", "findings"} & value.keys()):
            skill = value.get("skill")
            if not isinstance(skill, dict) or skill.get("id") != frontmatter.get("id") or skill.get("version") != frontmatter.get("version"):
                report.error(path, "R35", "top-level report skill id/version must match action-skill frontmatter", line)
        validate_report_object(path, value, report, line, is_review_skill(path, frontmatter))

    action_match = re.search(r"^## Action\s*$\n(.*?)(?=^## Output\s*$)", parsed.body, re.MULTILINE | re.DOTALL)
    if action_match and re.search(
        r"(?:no violation|satisfied|compliant|passes?).{0,80}emit(?:s|ted)?\s+(?:an?\s+)?`?info|emit(?:s|ted)?\s+(?:an?\s+)?`?info.{0,80}(?:no violation|satisfied|compliant|passes?)",
        action_match.group(1), re.IGNORECASE | re.DOTALL,
    ):
        line = parsed.body_start_line + parsed.body[:action_match.start()].count("\n")
        report.error(path, "R34", "satisfied rules and passing checks belong in summary, not info findings", line)


def validate_meta_skill(path: Path, parsed: Parsed, report: Report) -> None:
    if parsed.frontmatter_error:
        report.error(path, "R01", parsed.frontmatter_error, 1)
        return
    fm = parsed.frontmatter
    assert fm is not None
    missing = META_SKILL_REQUIRED_KEYS - fm.keys()
    if missing:
        report.error(path, "R22", f"missing required meta-skill keys: {sorted(missing)}", 1)
    for k in META_SKILL_REQUIRED_KEYS & fm.keys():
        v = fm[k]
        if v is None or v == "" or v == []:
            report.error(path, "R22", f"meta-skill key '{k}' must not be empty", 1)
    if fm.get("kind") != "meta-skill":
        report.error(path, "R25", f"file in /skills/ is a meta-skill by path but kind is '{fm.get('kind')}', expected 'meta-skill'", 1)
    if "id" in fm and (not isinstance(fm["id"], str) or not KEBAB_CASE.match(fm["id"])):
        report.error(path, "R22", f"id must be lowercase kebab-case: '{fm['id']}'", 1)
    if "version" in fm:
        v = fm["version"]
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            report.error(path, "R22", f"version must be a positive integer: {v!r}", 1)


def validate_entry_skill(path: Path, parsed: Parsed, report: Report) -> None:
    if parsed.frontmatter_error:
        report.error(path, "R01", parsed.frontmatter_error, 1)
        return
    fm = parsed.frontmatter
    assert fm is not None
    missing = ENTRY_SKILL_REQUIRED_KEYS - fm.keys()
    if missing:
        report.error(path, "R23", f"missing required entry-point keys: {sorted(missing)}", 1)
    for k in ENTRY_SKILL_REQUIRED_KEYS & fm.keys():
        v = fm[k]
        if v is None or v == "" or v == []:
            report.error(path, "R23", f"entry-point key '{k}' must not be empty", 1)
    if fm.get("kind") != "entry-point":
        report.error(path, "R25", f"file is /skills/entry.md but kind is '{fm.get('kind')}', expected 'entry-point'", 1)
    if fm.get("id") != "entry":
        report.error(path, "R23", f"entry-point id must be 'entry', got '{fm.get('id')}'", 1)
    if "version" in fm:
        v = fm["version"]
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            report.error(path, "R23", f"version must be a positive integer: {v!r}", 1)


# --- Path and sample checks -------------------------------------------------

def classify(path_from_root: Path) -> str | None:
    """Return 'knowledge' | 'action-skill' | 'meta' | 'entry' | None."""
    parts = path_from_root.parts
    if len(parts) < 2:
        return None
    top = parts[0]
    if top == "skills":
        if len(parts) == 2:
            name = parts[1]
            if name == ENTRY_SKILL_FILE:
                return "entry"
            if name in META_SKILL_FILES:
                return "meta"
        return None
    if top in LAYERS and path_from_root.suffix == ".md":
        if len(parts) >= 3 and parts[1] == "skills":
            return "action-skill"
        if len(parts) >= 4 and parts[1] == "knowledge":
            return "knowledge"
    return None


def validate_knowledge_path(path: Path, root: Path, report: Report) -> None:
    rel = path.relative_to(root)
    parts = rel.parts
    # R13 expected shape: <layer>/knowledge/<domain>/<slug>.md
    if len(parts) != 4:
        report.error(path, "R13", f"knowledge file must live at <layer>/knowledge/<domain>/<slug>.md; got {rel.as_posix()}")
        return
    slug = path.stem
    # R12 filename kebab-case
    if not KEBAB_CASE.match(slug):
        report.error(path, "R12", f"filename slug must be lowercase kebab-case: '{slug}'")


def validate_samples_in_domain(domain_dir: Path, root: Path, report: Report) -> None:
    """R14: every sample must match <slug>.<kind>.<ext>[.txt] with <slug>.md present."""
    if not domain_dir.is_dir():
        return
    articles = {p.stem: p for p in domain_dir.glob("*.md")}
    article_slugs = set(articles)
    article_texts: dict[str, str] = {}
    for slug, article in articles.items():
        try:
            article_texts[slug] = article.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # R01 reports this during the article pass.
            continue

    for entry in domain_dir.iterdir():
        if not entry.is_file() or entry.suffix == ".md":
            continue
        name = entry.name
        # AL samples use a trailing .txt so consuming AL compilers ignore them.
        m = re.match(r"^(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.(?P<kind>[a-z0-9]+)\.(?P<ext>[a-z0-9]+)(?:\.txt)?$", name)
        if not m:
            report.error(entry, "R14", f"sample file name must match '<slug>.<kind>.<ext>[.txt]' with kebab-case slug: '{name}'")
            continue
        slug = m.group("slug")
        kind = m.group("kind")
        if slug not in article_slugs:
            report.error(entry, "R14", f"orphan sample: no matching article '{slug}.md' in {domain_dir.relative_to(root).as_posix()}")
        elif entry.name not in article_texts.get(slug, ""):
            report.error(
                entry,
                "R28",
                f"sample is not referenced by its article '{slug}.md'",
            )
        if kind not in VALID_SAMPLE_KINDS:
            report.warn(entry, "R14", f"non-standard sample kind '{kind}'; standard kinds are {sorted(VALID_SAMPLE_KINDS)}")

    for slug, article in articles.items():
        for sample_name in SAMPLE_REFERENCE.findall(article_texts.get(slug, "")):
            if not (domain_dir / sample_name).is_file():
                report.error(
                    article,
                    "R28",
                    f"referenced sample does not exist: '{sample_name}'",
                )


# --- Orchestration ----------------------------------------------------------

@dataclass
class SkillRecord:
    path: Path
    kind: str            # frontmatter kind
    skill_id: str | None


def validate_sub_skills_registry(path: Path, fm: dict[str, Any], root: Path, report: Report) -> None:
    """R26: declared sub-skills must be existing action-skill leaves."""
    ss = fm.get("sub-skills")
    if not is_non_empty_list_of_str(ss):
        return

    declared = {s.lstrip("./") for s in ss}
    for entry in sorted(declared):
        entry_path = root / entry
        if not entry_path.exists():
            report.error(path, "R26", f"declared sub-skill does not exist on disk: {entry}", 1)
            continue
        try:
            target = parse_markdown(entry_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as exc:
            report.error(path, "R26", f"cannot read declared sub-skill {entry}: {exc}", 1)
            continue
        target_fm = target.frontmatter or {}
        if target_fm.get("kind") != "action-skill":
            report.error(
                path, "R26",
                f"sub-skills entry is not an action skill: {entry}", 1,
            )
        elif target_fm.get("sub-skills"):
            report.error(path, "R26", f"nested super-skill is not permitted: {entry}", 1)
        if entry_path.resolve() == path.resolve():
            report.error(path, "R26", "super-skill cannot include itself", 1)


def run(root: Path) -> Report:
    report = Report()
    skill_records: list[SkillRecord] = []
    action_skill_fms: list[tuple[Path, dict[str, Any]]] = []

    # Walk declared top-level folders only; avoid wandering into .git, etc.
    walk_roots = [root / "skills"] + [root / layer for layer in LAYERS]
    candidate_files: list[Path] = []
    for wr in walk_roots:
        if wr.exists():
            candidate_files.extend(p for p in wr.rglob("*") if p.is_file())

    # First pass: classify and validate each file
    for path in candidate_files:
        rel = path.relative_to(root)
        kind = classify(rel)
        if kind is None:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            report.error(path, "R01", f"file is not valid UTF-8: {e}")
            continue
        parsed = parse_markdown(text)

        if kind == "knowledge":
            validate_knowledge_path(path, root, report)
            validate_knowledge(path, parsed, report)
        elif kind == "action-skill":
            validate_action_skill(path, parsed, report)
            if parsed.frontmatter:
                action_skill_fms.append((path, parsed.frontmatter))
            if parsed.frontmatter and isinstance(parsed.frontmatter.get("id"), str):
                skill_records.append(SkillRecord(path, "action-skill", parsed.frontmatter["id"]))
        elif kind == "meta":
            validate_meta_skill(path, parsed, report)
            if parsed.frontmatter and isinstance(parsed.frontmatter.get("id"), str):
                skill_records.append(SkillRecord(path, "meta-skill", parsed.frontmatter["id"]))
        elif kind == "entry":
            validate_entry_skill(path, parsed, report)
            if parsed.frontmatter and isinstance(parsed.frontmatter.get("id"), str):
                skill_records.append(SkillRecord(path, "entry-point", parsed.frontmatter["id"]))

    # Second pass: sample files per knowledge domain
    for layer in LAYERS:
        kn_root = root / layer / "knowledge"
        if not kn_root.is_dir():
            continue
        for domain_dir in kn_root.iterdir():
            if domain_dir.is_dir():
                validate_samples_in_domain(domain_dir, root, report)

    # Third pass: R24 unique ids within kind and layer. Cross-layer duplicates
    # are intentional overrides resolved by Entry precedence.
    by_kind: dict[tuple[str, str], dict[str, list[Path]]] = {}
    for rec in skill_records:
        if rec.skill_id is None:
            continue
        rel = rec.path.relative_to(root)
        layer = rel.parts[0] if rel.parts[0] in LAYERS else "root"
        by_kind.setdefault((rec.kind, layer), {}).setdefault(rec.skill_id, []).append(rec.path)
    for (kind, layer), by_id in by_kind.items():
        for sid, paths in by_id.items():
            if len(paths) > 1:
                for p in paths:
                    others = [q.relative_to(root).as_posix() for q in paths if q != p]
                    report.error(p, "R24", f"skill id '{sid}' ({kind}) is not unique within layer '{layer}'; also defined in: {others}")

    # Fourth pass: R26 sub-skills registry matches leaf files on disk
    for path, fm in action_skill_fms:
        validate_sub_skills_registry(path, fm, root, report)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BCQuality frontmatter and structure validator.")
    parser.add_argument("--root", default=".", help="Repository root (default: current directory).")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    report = run(root)

    gha = os.environ.get("GITHUB_ACTIONS") == "true"
    for d in report.diagnostics:
        line = d.format_gha(root) if gha else d.format_plain(root)
        print(line)

    n_err = len(report.errors)
    n_warn = len(report.warnings)
    print(f"\nValidator: {n_err} error(s), {n_warn} warning(s)")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
