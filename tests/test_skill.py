import concurrent.futures
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "pipeline_gate.py"
AUDIT = ROOT / "scripts" / "security_audit.py"
VERIFY = ROOT / "scripts" / "verify_delivery.py"


def run(*args):
    return subprocess.run(
        [sys.executable, "-X", "utf8", "-B", *map(str, args)],
        capture_output=True, text=True, encoding="utf-8",
    )


class GateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.project = Path(directory.name)
        self.checkpoint = self.project / ".pipeline" / "CHECKPOINT.json"
        self.gate("init", "--project", "TestApp")

    def gate(self, *args, code=0):
        result = run(GATE, "--project-dir", self.project, *args)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def state(self):
        return json.loads(self.checkpoint.read_text(encoding="utf-8"))

    def request(self, gate, revision):
        self.gate("request", "--gate", gate, "--revision", revision)

    def approve(self, gate, revision, *, code=0, evidence="Review item 42"):
        return self.gate("approve", "--gate", gate, "--revision", revision, "--approver",
                         "Project owner", "--evidence", evidence, code=code)

    def advance(self, target, *, code=0):
        return self.gate("advance", "--step", target, "--evidence", "Work reviewed", code=code)

    def ready_except_g3(self):
        self.request("G1", "spec-v1")
        self.approve("G1", "spec-v1")
        self.request("G2", "backend-v1")
        self.gate("waive", "--gate", "G2", "--revision", "backend-v1",
                  "--evidence", "Backend scope has no UI")
        self.advance("6.5")

    def test_requires_pending_matching_revision_and_approver(self):
        self.assertIn("G1", self.advance("3.0", code=1))
        self.approve("G1", "spec-v1", code=1)
        self.request("G1", "spec-v1")
        self.approve("G1", "spec-v2", code=1)
        self.approve("G1", "spec-v1", evidence="   ", code=1)
        self.gate("approve", "--gate", "G1", "--revision", "spec-v1", "--approver", " ",
                  "--evidence", "Review item 42", code=1)
        self.assertEqual(self.state()["gates"]["G1"]["status"], "PENDING")
        self.approve("G1", "spec-v1")
        before = self.checkpoint.read_bytes()
        self.approve("G1", "spec-v1")
        self.request("G1", "spec-v1")
        self.assertEqual(self.checkpoint.read_bytes(), before)
        self.advance("3.0")
        record = self.state()["gates"]["G1"]
        self.assertEqual(record["approver"], "Project owner")
        self.assertEqual(record["revision"], "spec-v1")
        self.assertEqual(record["evidence"], "Review item 42")

    def test_reopens_only_the_changed_file_gate(self):
        self.ready_except_g3()
        spec = self.project / "spec.md"
        spec.write_text("Draft one", encoding="utf-8")
        self.gate("request", "--gate", "G1", "--subject", "spec.md")
        old_revision = self.state()["gates"]["G1"]["revision"]
        self.assertRegex(old_revision, r"^sha256:[0-9a-f]{64}$")
        self.approve("G1", old_revision)
        before = self.state()["gates"]["G2"]
        self.request("G3", "artifact-v1")
        self.approve("G3", "artifact-v1")

        spec.write_text("Draft two", encoding="utf-8")
        self.assertIn("STALE (APPROVED)", self.gate("status"))
        self.assertIn("G1: subject changed", self.gate("validate", code=1))
        self.assertIn("G1: subject changed", self.advance("7.0", code=1))
        self.approve("G1", old_revision, code=1)

        self.gate("request", "--gate", "G1", "--subject", "spec.md")
        updated = self.state()
        new_revision = updated["gates"]["G1"]["revision"]
        self.assertNotEqual(old_revision, new_revision)
        self.assertEqual(updated["gates"]["G1"]["status"], "PENDING")
        self.assertEqual(updated["gates"]["G2"], before)
        self.assertEqual(updated["gates"]["G3"]["status"], "APPROVED")
        self.assertEqual(updated["history"][-1]["previous"]["revision"], old_revision)
        self.approve("G1", old_revision, code=1)
        self.approve("G1", new_revision)
        self.advance("7.0")
        self.gate("validate")

    def test_rejects_changed_pending_subject_and_clears_old_design(self):
        preview = self.project / "preview.html"
        preview.write_text("Design one", encoding="utf-8")
        self.gate("request", "--gate", "G2", "--subject", "preview.html")
        revision = self.state()["gates"]["G2"]["revision"]
        preview.write_text("Design two", encoding="utf-8")
        self.assertIn("subject changed", self.approve("G2", revision, code=1))
        self.gate("request", "--gate", "G2", "--subject", "preview.html")
        revision = self.state()["gates"]["G2"]["revision"]
        self.gate("approve", "--gate", "G2", "--revision", revision, "--approver", "Design owner",
                  "--evidence", "Review 51", "--design", "Theme C")
        self.assertEqual(self.state()["selected_design"], "Theme C")
        self.gate("request", "--gate", "G2", "--revision", "external-design-v3")
        self.assertIsNone(self.state()["selected_design"])
        self.gate("request", "--gate", "G1", "--subject", str(preview), code=1)

    def test_g3_rules_match_for_advancing_and_validating(self):
        self.ready_except_g3()
        self.assertIn("G3", self.advance("7.0", code=1))
        self.request("G3", "artifact-v1")
        self.gate("waive", "--gate", "G3", "--revision", "artifact-v1",
                  "--evidence", "Reason", code=2)
        self.approve("G3", "artifact-v1")
        self.advance("7.0")
        self.gate("validate")
        self.request("G3", "artifact-v2")
        self.assertIn("G3: PENDING", self.gate("validate", code=1))
        self.approve("G3", "artifact-v1", code=1)
        self.approve("G3", "artifact-v2")
        self.gate("validate")

    def test_legacy_checkpoint_preserves_history_and_requires_fresh_approval(self):
        data = self.state()
        data["schema_version"] = 2
        data["current_step"] = "3.0"
        data["gates"]["G1"] = {"status": "APPROVED", "evidence": "Legacy chat note"}
        original_history = list(data["history"])
        self.checkpoint.write_text(json.dumps(data), encoding="utf-8")
        self.assertIn("STALE (APPROVED)", self.gate("status"))
        self.gate("validate", code=1)
        self.assertEqual(self.state()["schema_version"], 2)
        self.request("G1", "spec-v1")
        migrated = self.state()
        self.assertEqual(migrated["schema_version"], 3)
        self.assertEqual(migrated["history"][:-1], original_history)
        self.assertEqual(migrated["history"][-1]["previous"]["evidence"], "Legacy chat note")
        self.approve("G1", "spec-v1")
        self.gate("validate")

    def test_concurrent_gate_requests_preserve_both_events(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as workers:
            g1 = workers.submit(self.request, "G1", "spec-v1")
            g2 = workers.submit(self.request, "G2", "design-v1")
            g1.result()
            g2.result()
        state = self.state()
        self.assertEqual(state["gates"]["G1"]["revision"], "spec-v1")
        self.assertEqual(state["gates"]["G2"]["revision"], "design-v1")
        self.assertEqual(len(state["history"]), 3)


class ExportTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.project = Path(directory.name)
        self.destination = self.project / "release_dist"
        self.manifest = self.project / "release-files.txt"
        self.manifest.write_text("index.html\npackage.json\n", encoding="utf-8")
        self.index = self.project / "index.html"
        self.index.write_text("<html><meta name='viewport' content='width=device-width'></html>",
                              encoding="utf-8")
        (self.project / "package.json").write_text(
            '{"name":"demo","scripts":{"test":"node --test"}}', encoding="utf-8",
        )

    def export(self, *args, code=0):
        result = run(VERIFY, self.project, "--export-release", self.destination, *args)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def test_publishes_only_allowlisted_files(self):
        for name in (".env", ".env.production", "unlisted.txt", "credentials.json"):
            (self.project / name).write_text("fixture only", encoding="utf-8")
        (self.project / ".pipeline").mkdir()
        (self.project / ".env.example").write_text("PORT=3000", encoding="utf-8")
        (self.project / "assets").mkdir()
        (self.project / "assets" / "style.css").write_text("body {}", encoding="utf-8")
        custom = self.project / "custom-files.txt"
        custom.write_text("# Release files\n\nindex.html\npackage.json\n.env.example\nassets/style.css\n",
                          encoding="utf-8")
        self.assertEqual(run(VERIFY, self.project).returncode, 0)
        self.export("--manifest", "custom-files.txt")
        self.assertEqual(
            {file.relative_to(self.destination).as_posix()
             for file in self.destination.rglob("*") if file.is_file()},
            {"index.html", "package.json", ".env.example", "assets/style.css"},
        )
        self.assertTrue((self.project / ".env").is_file())

    def test_rejects_invalid_or_excluded_manifest_entries(self):
        for name in (".env", ".ENV.production", "local.pem", "credentials.json", "unlisted.txt"):
            (self.project / name).write_text("fixture only", encoding="utf-8")
        for listing in (
            "", "../other.txt\n", "C:/outside.txt\n", "index.html:stream\n", "missing.txt\n",
            ".env\n", ".ENV.production\n", "local.pem\n", "credentials.json\n",
            "index.html\nINDEX.HTML\n",
        ):
            with self.subTest(listing=listing):
                self.manifest.write_text(listing, encoding="utf-8")
                self.export(code=1)
                self.assertFalse(self.destination.exists())
        self.manifest.unlink()
        self.export(code=1)
        self.assertFalse(self.destination.exists())

    def test_refuses_linked_files(self):
        if os.name == "nt":
            from _winapi import CreateJunction

            assets = self.project / "assets"
            assets.mkdir()
            (assets / "style.css").write_text("body {}", encoding="utf-8")
            link = self.project / "linked"
            CreateJunction(str(assets), str(link))
            self.addCleanup(link.rmdir)
            entry = "linked/style.css"
        else:
            link = self.project / "linked.html"
            link.symlink_to(self.index)
            entry = "linked.html"
        self.manifest.write_text(entry + "\n", encoding="utf-8")
        self.export(code=1)
        self.assertFalse(self.destination.exists())

    def test_concurrent_export_publishes_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as workers:
            jobs = [workers.submit(run, VERIFY, self.project, "--export-release", self.destination)
                    for _ in range(2)]
            results = [job.result() for job in jobs]
        self.assertEqual(sorted(result.returncode for result in results), [0, 1])
        self.assertEqual((self.destination / "index.html").read_bytes(), self.index.read_bytes())
        self.assertFalse(list(self.project.glob(".release-*")))

    def test_failed_project_check_blocks_export(self):
        self.index.write_text("<html><body></body></html>", encoding="utf-8")
        self.assertIn("Project verification failed", self.export(code=2))
        self.assertFalse(self.destination.exists())
        self.assertFalse(list(self.project.glob(".release-*")))

    def test_stage_is_checked_and_removed_on_failure(self):
        verify = runpy.run_path(str(VERIFY))["run_verification"]

        def stage_copy(source, target):
            target.write_bytes(source.read_bytes())
            if target.name == "index.html":
                target.write_text("<html><body></body></html>", encoding="utf-8")

        with patch("shutil.copy2", side_effect=stage_copy), patch("sys.stderr"):
            result = verify(str(self.project), str(self.destination))
        self.assertEqual(result, 2)
        self.assertFalse(self.destination.exists())
        self.assertFalse(list(self.project.glob(".release-*")))
        self.assertIn("viewport", self.index.read_text(encoding="utf-8"))

    def test_existing_destination_is_preserved(self):
        self.destination.mkdir()
        marker = self.destination / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        self.export(code=1)
        self.assertEqual(list(self.destination.iterdir()), [marker])
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")


class AuditTests(unittest.TestCase):
    def test_security_audit_clean_and_findings(self):
        with tempfile.TemporaryDirectory() as d:
            clean_file = Path(d) / "app.py"
            clean_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
            self.assertEqual(run(AUDIT, d).returncode, 0)

            sample = "sk_live_123456789012345678901234"
            (Path(d) / "config.js").write_text(f"const apiKey = '{sample}';\n", encoding="utf-8")
            result = run(AUDIT, d, "--format", "json")
            self.assertEqual(result.returncode, 2)
            self.assertGreater(json.loads(result.stdout)["total_findings"], 0)
            self.assertNotIn(sample, result.stdout)


if __name__ == "__main__":
    unittest.main()
