import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "pipeline_gate.py"
AUDIT = ROOT / "scripts" / "security_audit.py"
VERIFY = ROOT / "scripts" / "verify_delivery.py"

def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)

class SkillTests(unittest.TestCase):
    def test_gate_progression_and_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            # 1. Init
            r = run(GATE, "--project-dir", d, "init", "--project", "TestApp")
            self.assertEqual(r.returncode, 0)
            
            # 2. Cannot jump past 2.5 without G1
            r = run(GATE, "--project-dir", d, "advance", "--step", "3.0", "--evidence", "skipped ahead")
            self.assertNotEqual(r.returncode, 0)

            # 3. Request G1
            r = run(GATE, "--project-dir", d, "request", "--gate", "G1")
            self.assertEqual(r.returncode, 0)

            # 4. Approve G1 without evidence must fail
            r = run(GATE, "--project-dir", d, "approve", "--gate", "G1", "--evidence", "   ")
            self.assertNotEqual(r.returncode, 0)

            # 5. Approve G1 with evidence
            r = run(GATE, "--project-dir", d, "approve", "--gate", "G1", "--evidence", "User approved spec in chat")
            self.assertEqual(r.returncode, 0)

            # 6. Waive G2 (e.g. backend service)
            r = run(GATE, "--project-dir", d, "waive", "--gate", "G2", "--evidence", "Backend service: no UI")
            self.assertEqual(r.returncode, 0)

            # 7. Advance to step 4.0
            r = run(GATE, "--project-dir", d, "advance", "--step", "4.0", "--evidence", "Architecture and test cases completed")
            self.assertEqual(r.returncode, 0)

            # 8. Validate
            r = run(GATE, "--project-dir", d, "validate")
            self.assertEqual(r.returncode, 0)

            # 9. Verify CHECKPOINT.json contents
            cp_file = Path(d) / ".pipeline" / "CHECKPOINT.json"
            self.assertTrue(cp_file.is_file())
            data = json.loads(cp_file.read_text(encoding="utf-8"))
            self.assertEqual(data["current_step"], "4.0")
            self.assertEqual(data["gates"]["G1"]["status"], "APPROVED")
            self.assertEqual(data["gates"]["G2"]["status"], "WAIVED")

    def test_security_audit_clean_and_findings(self):
        with tempfile.TemporaryDirectory() as d:
            # Clean file
            clean_file = Path(d) / "app.py"
            clean_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
            r = run(AUDIT, d)
            self.assertEqual(r.returncode, 0)

            # File with secret
            secret_file = Path(d) / "config.js"
            secret_file.write_text("const apiKey = 'sk_live_123456789012345678901234';\n", encoding="utf-8")
            r = run(AUDIT, d, "--format", "json")
            self.assertEqual(r.returncode, 2)
            data = json.loads(r.stdout)
            self.assertGreater(data["total_findings"], 0)
            # Make sure secret is redacted in output
            self.assertNotIn("sk_live_123456789012345678901234", r.stdout)

    def test_verify_delivery_and_export(self):
        with tempfile.TemporaryDirectory() as d:
            src_file = Path(d) / "index.html"
            src_file.write_text("<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width'></head><body><button><svg></svg> Click</button></body></html>", encoding="utf-8")
            pkg_file = Path(d) / "package.json"
            pkg_file.write_text('{"name": "demo", "scripts": {"test": "node --test"}}', encoding="utf-8")

            # Verification should pass
            r = run(VERIFY, d)
            self.assertEqual(r.returncode, 0)

            # Export release
            export_target = Path(d) / "release_dist"
            r = run(VERIFY, d, "--export-release", export_target)
            self.assertEqual(r.returncode, 0)
            self.assertTrue((export_target / "index.html").is_file())
            self.assertFalse((export_target / ".pipeline").exists())

if __name__ == "__main__":
    unittest.main()
