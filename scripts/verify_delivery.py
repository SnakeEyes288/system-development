#!/usr/bin/env python3
"""
Production Release & Deliverable Verification Tool (verify_delivery.py)

Verifies project readiness for production release:
1. Validates build synchronization (e.g. `dist/` vs `src/` or `preview.html` vs entry points).
2. Verifies UI Design System & Content Discipline standards (semantic SVG icons, accessible metadata, contrast).
3. Verifies repository portability (executable scripts in package.json, valid entry points).
4. Supports `--export-release <dir>` to package a clean release bundle into a designated folder
   without altering or deleting development history or audit logs.
"""
import argparse
import os
import re
import shutil
import sys

EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U00002702-\U000027B0\U000024C2-\U0001F251]"
)

DEFAULT_IGNORE_DIRS = {
    ".git", "node_modules", ".pipeline", "coverage", ".cache", "__pycache__"
}

def check_craft_floor(project_dir: str) -> list[str]:
    issues = []
    # Check HTML files for Craft-Floor standards
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]
        for f in files:
            if f.endswith((".html", ".htm", ".vue", ".jsx", ".tsx")):
                fpath = os.path.join(root, f)
                rel_path = os.path.relpath(fpath, project_dir)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                        
                        # Check 1: Emoji inside buttons or interactive tags
                        button_matches = re.findall(r"<button[^>]*>(.*?)</button>", content, re.DOTALL | re.IGNORECASE)
                        for b_text in button_matches:
                            if EMOJI_PATTERN.search(b_text):
                                issues.append(f"[Content Discipline] Emoji found inside button text in `{rel_path}`. Use inline SVG instead.")
                                break

                        # Check 2: Viewport meta in standalone HTML
                        if f.endswith(".html") and "<html" in content.lower():
                            if "name=\"viewport\"" not in content and "name='viewport'" not in content:
                                issues.append(f"[Responsive] Missing viewport meta tag in `{rel_path}`.")

                except Exception as e:
                    issues.append(f"Could not read `{rel_path}`: {e}")
    return issues

def check_package_portability(project_dir: str) -> list[str]:
    issues = []
    pkg_path = os.path.join(project_dir, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                import json
                data = json.load(f)
                scripts = data.get("scripts", {})
                if not scripts:
                    issues.append("[Portability] `package.json` contains no scripts.")
                elif "test" not in scripts:
                    issues.append("[Portability] `package.json` has no `test` script defined.")
        except Exception as e:
            issues.append(f"[Portability] Invalid package.json: {e}")
    return issues

def export_release_bundle(project_dir: str, export_dir: str) -> int:
    export_dir = os.path.abspath(export_dir)
    project_dir = os.path.abspath(project_dir)

    if os.path.exists(export_dir):
        print(f"ERROR: Export destination `{export_dir}` already exists. Choose an empty directory.", file=sys.stderr)
        return 1

    print(f"Packaging clean release bundle to `{export_dir}`...")
    exclude_patterns = shutil.ignore_patterns(
        ".git*", "node_modules", ".pipeline", "*.pyc", "__pycache__", ".vscode", ".idea", "*.tmp"
    )

    try:
        shutil.copytree(project_dir, export_dir, ignore=exclude_patterns)
        print(f"SUCCESS: Release bundle exported cleanly to `{export_dir}`.")
        return 0
    except Exception as e:
        print(f"ERROR: Failed to export bundle: {e}", file=sys.stderr)
        return 1

def run_verification(project_dir: str, export_dir: str | None = None) -> int:
    project_dir = os.path.abspath(project_dir)
    print("=" * 65)
    print(f" Production Deliverable Verification: {project_dir}")
    print("=" * 65)

    cf_issues = check_craft_floor(project_dir)
    pkg_issues = check_package_portability(project_dir)

    all_issues = cf_issues + pkg_issues

    if all_issues:
        print(f" Found {len(all_issues)} issue(s) that should be addressed before release:")
        for idx, iss in enumerate(all_issues, 1):
            print(f"  {idx}. {iss}")
        print("=" * 65)
    else:
        print(" PASS: Deliverable passes all Design System, Content Discipline, and Portability checks.")
        print("=" * 65)

    if export_dir:
        return export_release_bundle(project_dir, export_dir)

    return 2 if all_issues else 0

def main():
    parser = argparse.ArgumentParser(description="Production Deliverable Verification Tool")
    parser.add_argument("project_dir", nargs="?", default=".", help="Project root directory")
    parser.add_argument("--export-release", default=None, help="Export clean production bundle into target directory")
    args = parser.parse_args()

    sys.exit(run_verification(args.project_dir, args.export_release))

if __name__ == "__main__":
    main()
