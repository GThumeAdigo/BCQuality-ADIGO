#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("validate_frontmatter", ROOT / ".github/scripts/validate_frontmatter.py")
ROUTER = load_module("route_entry", ROOT / "tools/route_entry.py")
INDEX = load_module("build_knowledge_index", ROOT / "tools/build_knowledge_index.py")


def base_evidence() -> dict[str, object]:
    return {
        "id": "evidence:test-failed",
        "occurrence-key": "codeunit-50100/should-fail",
        "severity": "blocker",
        "message": "runner reported failure",
        "references": [],
        "confidence": "high",
        "evidence": {"kind": "test-runner", "source": "results.xml", "status": "failed"},
        "gating": True,
    }


def base_report(findings: list[dict[str, object]] | None = None) -> dict[str, object]:
    values = findings or []
    counts = {severity: 0 for severity in ("blocker", "major", "minor", "info")}
    for finding in values:
        counts[str(finding["severity"])] += 1
    return {
        "skill": {"id": "example", "version": 1},
        "outcome": "completed",
        "summary": {"counts": counts, "coverage": {"worklist-size": len(values), "items-evaluated": len(values)}},
        "findings": values,
        "suppressed": [],
    }


def action_skill_text(
    skill_id: str,
    *,
    sub_skills: list[str] | None = None,
    bc_version: str = "[all]",
    countries: str = "[w1]",
    application_area: str = "[all]",
) -> str:
    sub_skill_line = f"sub-skills: {json.dumps(sub_skills)}\n" if sub_skills is not None else ""
    return (
        "---\nkind: action-skill\n"
        f"id: {skill_id}\nversion: 1\ntitle: Example\ndescription: Reviews example input.\n"
        f"inputs: [repository]\noutputs: [findings-report]\nbc-version: {bc_version}\ntechnologies: [al]\n"
        f"countries: {countries}\napplication-area: {application_area}\n"
        f"{sub_skill_line}---\n# Example\n\n## Source\nSource.\n\n## Relevance\nRelevant.\n\n"
        "## Worklist\nWork.\n\n## Action\nAct.\n\n## Output\nOutput conforms to the DO output contract.\n"
    )


class EvidenceContractTests(unittest.TestCase):
    def validate_finding(self, finding: dict[str, object], review: bool = False) -> list[str]:
        report = VALIDATOR.Report()
        VALIDATOR.validate_finding(Path("custom/skills/testing/example.md"), finding, report, 1, review)
        return [diagnostic.rule for diagnostic in report.errors]

    def validate_report(self, value: dict[str, object]) -> list[str]:
        report = VALIDATOR.Report()
        VALIDATOR.validate_report_object(Path("custom/skills/testing/example.md"), value, report, 1, False)
        return [diagnostic.rule for diagnostic in report.errors]

    def test_accepts_gating_evidence_with_occurrence_identity(self) -> None:
        self.assertEqual([], self.validate_finding(base_evidence()))

    def test_rejects_evidence_without_occurrence_key(self) -> None:
        finding = base_evidence()
        del finding["occurrence-key"]
        self.assertIn("R32", self.validate_finding(finding))

    def test_rejects_extra_evidence_key(self) -> None:
        finding = base_evidence()
        finding["evidence"]["run-id"] = "volatile"
        self.assertIn("R32", self.validate_finding(finding))

    def test_rejects_uncited_hard_agent_finding(self) -> None:
        rules = self.validate_finding({
            "id": "agent:inferred", "severity": "blocker", "message": "inferred",
            "references": [], "confidence": "high",
        })
        self.assertEqual(["R31", "R31"], rules)

    def test_rejects_general_required_fields_and_enums(self) -> None:
        rules = self.validate_finding({"id": "agent:bad", "severity": "urgent", "references": [], "confidence": "certain"})
        self.assertGreaterEqual(rules.count("R29"), 3)

    def test_rejects_citation_id_mismatch(self) -> None:
        rules = self.validate_finding({
            "id": "wrong", "severity": "major", "message": "cited",
            "references": [{"path": "microsoft/knowledge/testing/rule.md"}], "confidence": "high",
        })
        self.assertEqual(["R30"], rules)

    def test_rejects_non_agent_uncited_id(self) -> None:
        rules = self.validate_finding({
            "id": "house:rule", "severity": "minor", "message": "uncited",
            "references": [], "confidence": "medium",
        })
        self.assertEqual(["R29"], rules)

    def test_review_finding_requires_domain(self) -> None:
        finding = {"id": "agent:review-gap", "severity": "minor", "message": "gap", "references": [], "confidence": "medium"}
        self.assertEqual(["R33"], self.validate_finding(finding, True))

    def test_rejects_stale_summary_counts(self) -> None:
        report = base_report([base_evidence()])
        report["summary"]["counts"]["blocker"] = 0
        self.assertIn("R37", self.validate_report(report))

    def test_rejects_duplicate_evidence_identity(self) -> None:
        report = base_report([base_evidence(), dict(base_evidence())])
        self.assertIn("R32", self.validate_report(report))

    def test_rejects_duplicate_non_evidence_id(self) -> None:
        finding = {"id": "agent:same", "severity": "minor", "message": "one", "references": [], "confidence": "medium"}
        report = base_report([finding, dict(finding, message="two")])
        self.assertIn("R39", self.validate_report(report))

    def test_rejects_invalid_report_skill_and_suppressed_shape(self) -> None:
        report = base_report()
        report["skill"] = {"id": "", "version": True}
        report["suppressed"] = {}
        rules = self.validate_report(report)
        self.assertGreaterEqual(rules.count("R36"), 2)

    def test_rejects_report_missing_findings(self) -> None:
        report = base_report()
        del report["findings"]
        self.assertIn("R36", self.validate_report(report))

    def test_rejects_example_skill_identity_mismatch(self) -> None:
        value = base_report()
        value["skill"] = {"id": "wrong", "version": 2}
        parsed = VALIDATOR.parse_markdown(action_skill_text("expected") + f"\n```json\n{json.dumps(value)}\n```\n")
        report = VALIDATOR.Report()
        VALIDATOR.validate_action_skill(Path("custom/skills/testing/expected.md"), parsed, report)
        self.assertIn("R35", [diagnostic.rule for diagnostic in report.errors])

    def test_rejects_missing_outcome_reason(self) -> None:
        report = base_report([base_evidence()])
        report["outcome"] = "failed"
        self.assertIn("R36", self.validate_report(report))

    def test_rollup_preserves_evidence_identity_and_payload(self) -> None:
        child = base_report([base_evidence()])
        child["skill"] = {"id": "child", "version": 1}
        rolled = dict(base_evidence())
        rolled["from-sub-skill"] = "child"
        parent = base_report([rolled])
        parent["skill"] = {"id": "parent", "version": 1}
        parent["sub-results"] = [child]
        self.assertEqual([], self.validate_report(parent))
        parent["findings"][0]["occurrence-key"] = "changed/key"
        self.assertIn("R38", self.validate_report(parent))


class EntryRoutingTests(unittest.TestCase):
    def test_every_custom_action_routes_with_honest_metadata(self) -> None:
        records = ROUTER.load_action_skills(ROOT, list(ROUTER.LAYERS))
        custom = [record for record in records if record["layer"] == "custom"]
        self.assertEqual(47, len(custom))
        for expected in custom:
            technology = expected["technologies"][0]
            result = ROUTER.route_exact(ROOT, {
                "requested-skill-id": expected["id"],
                "inputs-available": [expected["inputs"][0]],
                "technologies": [technology],
                "bc-version": 28,
                "countries": ["us"],
                "application-area": ["all"],
                "enabled-layers": list(ROUTER.LAYERS),
                "disabled-skills": [],
            })
            self.assertEqual("routed", result["outcome"], expected["id"])
            self.assertEqual(expected["path"], result["dispatch"][0]["skill"]["path"])

    def test_goal_is_optional_and_nonmatching_ids_are_not_considered(self) -> None:
        result = ROUTER.route_exact(ROOT, {
            "requested-skill-id": "does-not-exist",
            "inputs-available": ["repository"],
        })
        self.assertEqual("no-match", result["outcome"])
        self.assertEqual([], result["skipped"])

    def test_filters_inputs_technologies_and_configuration(self) -> None:
        base = {"requested-skill-id": "al-test-runner", "inputs-available": ["file-path"], "technologies": ["bicep"]}
        self.assertEqual("no-match", ROUTER.route_exact(ROOT, base)["outcome"])
        base["inputs-available"] = ["repository"]
        self.assertEqual("no-match", ROUTER.route_exact(ROOT, base)["outcome"])
        base["technologies"] = ["al"]
        base["disabled-skills"] = ["custom/skills/testing/al-test-runner.md"]
        self.assertEqual("configuration", ROUTER.route_exact(ROOT, base)["skipped"][0]["reason"])

    def test_rejects_unknown_and_duplicate_enabled_layers(self) -> None:
        for layers in (["custom", "custom"], ["custom", "unknown"]):
            result = ROUTER.route_exact(ROOT, {
                "requested-skill-id": "al-test-runner", "inputs-available": ["repository"], "enabled-layers": layers,
            })
            self.assertEqual("failed", result["outcome"])

    def test_exact_overlap_uses_custom_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for layer in ROUTER.LAYERS:
                path = root / layer / "skills" / "same.md"
                path.parent.mkdir(parents=True)
                path.write_text(action_skill_text("same"), encoding="utf-8")
            result = ROUTER.route_exact(root, {"requested-skill-id": "same", "inputs-available": ["repository"], "technologies": ["al"]})
            self.assertEqual("custom/skills/same.md", result["dispatch"][0]["skill"]["path"])
            self.assertEqual(2, len(result["skipped"]))
            microsoft_only = ROUTER.route_exact(root, {
                "requested-skill-id": "same", "inputs-available": ["repository"],
                "technologies": ["al"], "enabled-layers": ["microsoft"],
            })
            self.assertEqual("microsoft/skills/same.md", microsoft_only["dispatch"][0]["skill"]["path"])

    def test_exact_router_honors_all_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "custom/skills/scoped.md"
            path.parent.mkdir(parents=True)
            path.write_text(action_skill_text(
                "scoped", bc_version="[28]", countries="[de]", application_area="[finance]"
            ), encoding="utf-8")
            context = {
                "requested-skill-id": "scoped", "inputs-available": ["repository"],
                "technologies": ["al"], "bc-version": 28, "countries": ["de"],
                "application-area": ["finance"], "enabled-layers": ["custom"],
            }
            self.assertEqual("routed", ROUTER.route_exact(root, context)["outcome"])
            for key, bad_value in (("bc-version", 27), ("countries", ["fr"]), ("application-area", ["sales"])):
                mutated = dict(context)
                mutated[key] = bad_value
                result = ROUTER.route_exact(root, mutated)
                self.assertEqual("no-match", result["outcome"])
                self.assertEqual("filter-mismatch", result["skipped"][0]["reason"])

    def test_router_cli_uses_supported_task_context_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            task_path = Path(directory) / "task.json"
            task_path.write_text(json.dumps({"task-context": {
                "requested-skill-id": "al-test-runner",
                "inputs-available": ["repository"],
                "technologies": ["al"],
                "bc-version": 28,
                "countries": ["us"],
                "application-area": ["all"],
                "enabled-layers": ["microsoft", "community", "custom"],
                "disabled-skills": [],
            }}), encoding="utf-8")
            completed = subprocess.run([
                sys.executable, str(ROOT / "tools/route_entry.py"),
                "--root", str(ROOT), "--task-context", str(task_path),
            ], check=True, capture_output=True, text=True)
            result = json.loads(completed.stdout)
            self.assertEqual("routed", result["outcome"])
            self.assertEqual("custom/skills/testing/al-test-runner.md", result["dispatch"][0]["skill"]["path"])


class IndexBuilderTests(unittest.TestCase):
    def test_full_and_filtered_article_sets_and_digest(self) -> None:
        full = INDEX.build_index(ROOT)
        expected_full = sorted(
            path.relative_to(ROOT).as_posix()
            for layer in INDEX.LAYERS
            for path in (ROOT / layer / "knowledge").rglob("*.md")
        )
        self.assertEqual(expected_full, sorted(article["path"] for article in full["articles"]))
        self.assertEqual(len(expected_full), full["articleCount"])
        self.assertRegex(full["sourceTreeDigest"], r"^[0-9a-f]{64}$")
        filtered = INDEX.build_index(ROOT, ["microsoft", "custom"])
        expected_filtered = [path for path in expected_full if path.startswith(("microsoft/", "custom/"))]
        self.assertEqual(expected_filtered, sorted(article["path"] for article in filtered["articles"]))
        self.assertEqual(["microsoft", "custom"], filtered["enabledLayers"])

    def test_digest_is_deterministic_and_content_sensitive(self) -> None:
        first = INDEX.build_index(ROOT, ["custom"])
        second = INDEX.build_index(ROOT, ["custom"])
        self.assertEqual(first["sourceTreeDigest"], second["sourceTreeDigest"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            article = root / "custom/knowledge/test/example.md"
            article.parent.mkdir(parents=True)
            article.write_text("---\ndomain: test\n---\n# A\n\n## Description\nOne.\n", encoding="utf-8")
            before = INDEX.build_index(root)["sourceTreeDigest"]
            article.write_text(article.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")
            self.assertNotEqual(before, INDEX.build_index(root)["sourceTreeDigest"])

    def test_rejects_unknown_and_duplicate_layers(self) -> None:
        with self.assertRaises(ValueError):
            INDEX.build_index(ROOT, ["custom", "custom"])
        with self.assertRaises(ValueError):
            INDEX.build_index(ROOT, ["unknown"])

    def test_index_cli_builds_exact_filtered_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "index.json"
            subprocess.run([
                sys.executable, str(ROOT / "tools/build_knowledge_index.py"),
                "--root", str(ROOT), "--index-path", str(output),
                "--enabled-layer", "microsoft,custom",
            ], check=True, capture_output=True, text=True)
            index = json.loads(output.read_text(encoding="utf-8"))
            expected = [
                path.relative_to(ROOT).as_posix()
                for layer in ("microsoft", "custom")
                for path in sorted((ROOT / layer / "knowledge").rglob("*.md"))
            ]
            self.assertEqual(expected, [article["path"] for article in index["articles"]])
            self.assertEqual(["microsoft", "custom"], index["enabledLayers"])

    def test_index_cli_rejects_bad_and_duplicate_layers(self) -> None:
        for layers in ("custom,custom", "custom,unknown"):
            completed = subprocess.run([
                sys.executable, str(ROOT / "tools/build_knowledge_index.py"),
                "--root", str(ROOT), "--index-path", str(Path(tempfile.gettempdir()) / "unused-index.json"),
                "--enabled-layer", layers,
            ], capture_output=True, text=True)
            self.assertNotEqual(0, completed.returncode)

    @unittest.skipUnless(shutil.which("pwsh"), "pwsh is not installed")
    def test_powershell_python_parity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ps_path = Path(directory) / "ps.json"
            command = (
                f"& '{ROOT / 'tools/Build-KnowledgeIndex.ps1'}' "
                f"-BCQualityRoot '{ROOT}' -IndexPath '{ps_path}' -EnabledLayers @('microsoft','custom')"
            )
            subprocess.run(["pwsh", "-NoProfile", "-Command", command], check=True)
            powershell = json.loads(ps_path.read_text(encoding="utf-8-sig"))
            python = INDEX.build_index(ROOT, ["microsoft", "custom"])
            self.assertEqual(python["enabledLayers"], powershell["enabledLayers"])
            self.assertEqual(python["sourceTreeDigest"], powershell["sourceTreeDigest"])
            self.assertEqual(
                [article["path"] for article in python["articles"]],
                [article["path"] for article in powershell["articles"]],
            )


class StructureMutationTests(unittest.TestCase):
    def test_rejects_duplicate_ids_within_layer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "custom/skills/test"
            skill_root.mkdir(parents=True)
            (skill_root / "one.md").write_text(action_skill_text("duplicate"), encoding="utf-8")
            (skill_root / "two.md").write_text(action_skill_text("duplicate"), encoding="utf-8")
            rules = [diagnostic.rule for diagnostic in VALIDATOR.run(root).errors]
            self.assertIn("R24", rules)

    def test_rejects_duplicate_and_invalid_sub_skills(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "custom/skills/test"
            skill_root.mkdir(parents=True)
            child = "custom/skills/test/child.md"
            (root / child).write_text(action_skill_text("child"), encoding="utf-8")
            (skill_root / "parent.md").write_text(action_skill_text("parent", sub_skills=[child, f"./{child}"]), encoding="utf-8")
            rules = [diagnostic.rule for diagnostic in VALIDATOR.run(root).errors]
            self.assertIn("R20", rules)
            (skill_root / "parent.md").write_text(action_skill_text("parent", sub_skills=["custom/skills/test/missing.md"]), encoding="utf-8")
            rules = [diagnostic.rule for diagnostic in VALIDATOR.run(root).errors]
            self.assertIn("R26", rules)

    def test_rejects_nested_super_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "custom/skills/test"
            skill_root.mkdir(parents=True)
            leaf = "custom/skills/test/leaf.md"
            child = "custom/skills/test/child.md"
            (root / leaf).write_text(action_skill_text("leaf"), encoding="utf-8")
            (root / child).write_text(action_skill_text("child", sub_skills=[leaf]), encoding="utf-8")
            (skill_root / "parent.md").write_text(action_skill_text("parent", sub_skills=[child]), encoding="utf-8")
            rules = [diagnostic.rule for diagnostic in VALIDATOR.run(root).errors]
            self.assertIn("R26", rules)

    def test_rejects_self_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "custom/skills/test"
            skill_root.mkdir(parents=True)
            parent = "custom/skills/test/parent.md"
            (root / parent).write_text(action_skill_text("parent", sub_skills=[parent]), encoding="utf-8")
            rules = [diagnostic.rule for diagnostic in VALIDATOR.run(root).errors]
            self.assertIn("R26", rules)


if __name__ == "__main__":
    unittest.main()
