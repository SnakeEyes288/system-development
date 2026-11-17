#!/usr/bin/env python3
"""
Security & OWASP Compliance Scanner (security_audit.py)

Performs static security analysis on codebase for:
1. Hardcoded secrets, API keys, private keys, and credential strings (with redaction in output).
2. OWASP Top 10 common vulnerability patterns (SQL injection, unsafe eval, unescaped shell commands).
3. Comment filtering to prevent false positives in documentation and commented-out code.
"""
import argparse
import json
import os
import re
import sys

IGNORE_DIRS = {
    ".git", "node_modules", ".pipeline", "dist", "build", "coverage",
    ".next", ".cache", "__pycache__", ".vscode", ".idea", "vendor"
}

IGNORE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".webm", ".mp3", ".wav", ".pdf", ".zip",
    ".tar", ".gz", ".lock", "-lock.json", ".map"
}

# Rule definitions: (id, severity, regex, description)
RULES = [
    # Secrets & Credentials
    (
        "SEC-001",
        "HIGH",
        re.compile(r"(?i)(?:password|passwd|pwd|secret|api_key|apikey|access_token|auth_token)\s*[:=]\s*['\"]([^'\"]{8,})['\"]"),
        "Potential hardcoded password or API token",
    ),
    (
        "SEC-002",
        "CRITICAL",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        "Exposed private cryptographic key",
    ),
    (
        "SEC-003",
        "HIGH",
        re.compile(r"\b(?:sk_live_[0-9a-zA-Z]{24}|ghp_[0-9a-zA-Z]{36}|glpat-[0-9a-zA-Z_\-]{20}|AKIA[0-9A-Z]{16})\b"),
        "Recognized cloud provider token or access credential",
    ),
    # OWASP Top 10 Code Insecurity
    (
        "OWASP-A03-INJECTION",
        "HIGH",
        re.compile(r"(?i)\b(?:select\s+.*?\s+from|insert\s+into|update\s+.*?\s+set|delete\s+from)\s*.*?(?:\+|%|\.format|\$\{)"),
        "Potential SQL string concatenation / injection vulnerability",
    ),
    (
        "OWASP-A03-EVAL",
        "HIGH",
        re.compile(r"\b(?:eval\s*\(|Function\s*\(|exec\s*\(|setTimeout\s*\(\s*['\"])"),
        "Use of dynamic code execution (eval/Function/exec)",
    ),
    (
        "OWASP-A03-XSS",
        "MEDIUM",
        re.compile(r"(?i)(?:innerHTML\s*=|dangerouslySetInnerHTML\s*=|v-html\s*=)"),
        "Direct HTML injection without explicit sanitization",
    ),
    (
        "OWASP-A01-CORS",
        "MEDIUM",
        re.compile(r"(?i)(?:Access-Control-Allow-Origin\s*['\"]?\s*:\s*['\"]?\*['\"]?)"),
        "Overly permissive CORS wildcard configuration",
    ),
]

def is_comment_line(line: str, ext: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if ext in (".py", ".sh", ".yaml", ".yml"):
        return stripped.startswith("#")
    if ext in (".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".php"):
        return stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*")
    if ext in (".html", ".htm", ".xml"):
        return stripped.startswith("<!--")
    if ext in (".sql",):
        return stripped.startswith("--") or stripped.startswith("/*")
    return False

def redact_match(text: str) -> str:
    if len(text) <= 6:
        return "[REDACTED]"
    return text[:2] + "[REDACTED]" + text[-2:]

def scan_file(filepath: str, project_root: str):
    findings = []
    ext = os.path.splitext(filepath)[1].lower()
    rel_path = os.path.relpath(filepath, project_root)

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_idx, line in enumerate(f, start=1):
                if is_comment_line(line, ext):
                    continue
                for rule_id, severity, regex, desc in RULES:
                    match = regex.search(line)
                    if match:
                        sample = line.strip()
                        # Redact potential sensitive group
                        if match.groups():
                            for g in match.groups():
                                if g and len(g) > 4:
                                    sample = sample.replace(g, redact_match(g))
                        elif "PRIVATE KEY" not in rule_id:
                            sample = sample[:40] + "... [REDACTED]"
                        
                        findings.append({
                            "rule_id": rule_id,
                            "severity": severity,
                            "file": rel_path,
                            "line": line_idx,
                            "description": desc,
                            "sample": sample[:120],
                        })
    except Exception as e:
        print(f"WARN: Could not read {rel_path}: {e}", file=sys.stderr)
    return findings

def run_audit(target_dir: str, as_json: bool = False, fail_on_medium: bool = False) -> int:
    target_dir = os.path.abspath(target_dir)
    if not os.path.exists(target_dir):
        print(f"ERROR: Directory does not exist: {target_dir}", file=sys.stderr)
        return 1

    all_findings = []
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in IGNORE_EXTENSIONS:
                continue
            fpath = os.path.join(root, file)
            all_findings.extend(scan_file(fpath, target_dir))

    critical_count = sum(1 for f in all_findings if f["severity"] == "CRITICAL")
    high_count = sum(1 for f in all_findings if f["severity"] == "HIGH")
    medium_count = sum(1 for f in all_findings if f["severity"] == "MEDIUM")

    if as_json:
        output = {
            "target": target_dir,
            "total_findings": len(all_findings),
            "summary": {"critical": critical_count, "high": high_count, "medium": medium_count},
            "findings": all_findings,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print("=" * 65)
        print(f" Security & OWASP Audit Report: {target_dir}")
        print("=" * 65)
        if not all_findings:
            print(" PASS: No hardcoded secrets or common OWASP vulnerabilities detected.")
            print("=" * 65)
            return 0

        for f in all_findings:
            print(f"[{f['severity']}] {f['rule_id']} - {f['description']}")
            print(f"  Location: {f['file']}:{f['line']}")
            print(f"  Evidence: {f['sample']}")
            print("-" * 65)

        print(f"Summary: {critical_count} Critical, {high_count} High, {medium_count} Medium.")
        print("=" * 65)

    if critical_count > 0 or high_count > 0 or (fail_on_medium and medium_count > 0):
        return 2
    return 0

def main():
    parser = argparse.ArgumentParser(description="Security & OWASP Compliance Scanner")
    parser.add_argument("target", nargs="?", default=".", help="Directory to scan (default: current directory)")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--fail-on-medium", action="store_true", help="Fail with exit code 2 if medium severity issues found")
    args = parser.parse_args()

    sys.exit(run_audit(args.target, as_json=(args.format == "json"), fail_on_medium=args.fail_on_medium))

if __name__ == "__main__":
    main()
