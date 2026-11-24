#!/usr/bin/env python3
"""Verify project files and publish a checked, allowlisted release bundle."""

import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

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
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS and not d.startswith(".release-")]
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

DEFAULT_MANIFEST = "release-files.txt"
ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template"}
EXCLUDED_NAMES = DEFAULT_IGNORE_DIRS | {
    ".ssh", ".gnupg", ".aws", ".azure", ".vscode", ".idea", ".npmrc", ".pypirc",
    ".netrc", "credentials.json", "secrets.json", "id_rsa", "id_ed25519",
}
EXCLUDED_SUFFIXES = (".pyc", ".tmp", ".key", ".pem", ".pfx", ".p12", ".jks")


def excluded_component(component: str) -> bool:
    name = component.casefold()
    if name in ENV_TEMPLATES:
        return False
    return (
        name in EXCLUDED_NAMES
        or name.startswith((".git", ".env.", ".release-"))
        or name == ".env"
        or name.endswith(EXCLUDED_SUFFIXES)
    )


def release_files(project: Path, manifest: Path) -> list[Path]:
    files = []
    seen = set()
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8-sig").splitlines(), 1):
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        parts = entry.split("/")
        if any(
            part in ("", ".", "..") or part.endswith((".", " "))
            or any(character in part for character in '\\:*?"<>|')
            for part in parts
        ):
            raise ValueError(f"Manifest line {line_number}: expected an exact project-relative file path.")
        if any(excluded_component(part) for part in parts):
            raise ValueError(f"Manifest line {line_number}: excluded file or directory `{entry}`.")
        if entry.casefold() in seen:
            raise ValueError(f"Manifest line {line_number}: duplicate path `{entry}`.")

        source = project.joinpath(*parts)
        if source.resolve(strict=True) != source or not source.is_file():
            raise ValueError(f"Manifest line {line_number}: `{entry}` must be a regular file without links.")
        files.append(source.relative_to(project))
        seen.add(entry.casefold())

    if not files:
        raise ValueError("Release manifest must list at least one file.")
    return files


def verification_issues(directory: Path) -> list[str]:
    return check_craft_floor(str(directory)) + check_package_portability(str(directory))


def report_issues(issues: list[str], scope: str) -> None:
    print(f"{scope}: {len(issues)} issue(s) to fix before release:", file=sys.stderr)
    for issue in issues:
        print(f"- {issue}", file=sys.stderr)


def publish_bundle(bundle: Path, destination: Path) -> None:
    if os.name == "nt":
        bundle.rename(destination)
        return

    # Reserve the name so concurrent publishers cannot replace an existing directory.
    destination.mkdir()
    try:
        bundle.replace(destination)
    except OSError:
        destination.rmdir()
        raise


def export_release_bundle(project: Path, destination: Path, manifest: Path) -> int:
    if os.path.lexists(destination):
        raise FileExistsError(f"Export destination already exists: `{destination}`.")

    files = release_files(project, manifest)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".release-", dir=destination.parent) as temp:
        bundle = Path(temp) / "bundle"
        bundle.mkdir()
        for relative in files:
            target = bundle / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project / relative, target)

        issues = verification_issues(bundle)
        if issues:
            report_issues(issues, "Staged release verification failed")
            return 2

        publish_bundle(bundle, destination)

    print(f"SUCCESS: Exported {len(files)} verified file(s) to `{destination}`.")
    return 0


def run_verification(
    project_dir: str, export_dir: str | None = None, manifest_path: str = DEFAULT_MANIFEST
) -> int:
    try:
        project = Path(project_dir).resolve(strict=True)
        if not project.is_dir():
            raise ValueError("Project path must be a directory.")

        issues = verification_issues(project)
        if issues:
            report_issues(issues, "Project verification failed")
            return 2
        if export_dir is not None:
            path = Path(export_dir).absolute()
            destination = path.parent.resolve() / path.name
            return export_release_bundle(project, destination, project / manifest_path)

        print("PASS: Project passed the content, viewport, and package metadata checks.")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Production Deliverable Verification Tool")
    parser.add_argument("project_dir", nargs="?", default=".", help="Project root directory")
    parser.add_argument("--export-release", metavar="DIR", help="Publish a checked bundle to a new directory")
    parser.add_argument("--manifest", metavar="FILE", default=DEFAULT_MANIFEST,
                        help=f"File allowlist for export (default: {DEFAULT_MANIFEST} in the project root)")
    args = parser.parse_args()
    sys.exit(run_verification(args.project_dir, args.export_release, args.manifest))


if __name__ == "__main__":
    main()
