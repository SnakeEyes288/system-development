#!/usr/bin/env python3
"""Record project progress and decisions tied to a specific artifact revision."""

import argparse
import hashlib
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

VALID_STEPS = ["0", "1.0", "2.0", "2.5", "3.0", "3.5", "4.0", "5.0", "6.0", "6.5", "7.0"]
GATE_STEPS = {"G1": "2.5", "G2": "3.0", "G3": "6.5"}
GATE_NAMES = {
    "G1": "Architecture & Specification Approval",
    "G2": "UX/UI Design & Direction Selection",
    "G3": "Multi-Role Delivery Sign-off",
}
SCHEMA_VERSION = 3


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


@contextmanager
def lock_checkpoint(pipeline: Path):
    pipeline.mkdir(parents=True, exist_ok=True)
    with (pipeline / ".checkpoint.lock").open("a+b") as lock:
        if os.name == "nt":
            import msvcrt

            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield


def load_checkpoint(pipeline: Path) -> dict:
    path = pipeline / "CHECKPOINT.json"
    try:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
    except FileNotFoundError:
        raise ValueError("No active pipeline found. Run `init` first.") from None

    if (
        not isinstance(data, dict)
        or data.get("schema_version") not in (2, SCHEMA_VERSION)
        or not isinstance(data.get("gates"), dict)
        or any(not isinstance(record, dict) for record in data["gates"].values())
        or not isinstance(data.get("history"), list)
        or data.get("current_step") not in VALID_STEPS
    ):
        raise ValueError("Invalid or unsupported CHECKPOINT.json.")
    return data


def save_checkpoint(pipeline: Path, data: dict) -> None:
    path = pipeline / "CHECKPOINT.json"
    data["schema_version"] = SCHEMA_VERSION
    data["updated_at"] = now_iso()
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=".checkpoint-", dir=pipeline, delete=False
        ) as stream:
            temp_path = Path(stream.name)
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def append_log(pipeline: Path, step: str, message: str) -> None:
    path = pipeline / "PIPELINE_LOGS.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as stream:
        if stream.tell() == 0:
            stream.write("# PIPELINE_LOGS.md - Project Execution History\n\n")
        stream.write(f"- `[{timestamp}]` **[Step {step}]** {message}\n")


def record_event(pipeline: Path, checkpoint: dict, event: dict, message: str) -> None:
    checkpoint["history"].append({**event, "timestamp": now_iso()})
    save_checkpoint(pipeline, checkpoint)
    try:
        details = f" Evidence: {event['evidence']}" if event.get("evidence") else ""
        append_log(pipeline, checkpoint["current_step"], message + details)
    except OSError as error:
        print(f"WARNING: Checkpoint saved, but the Markdown log could not be updated: {error}",
              file=sys.stderr)
    print(f"SUCCESS: {message}")


def subject_revision(project: Path, subject: str) -> str:
    relative = Path(subject)
    if relative.anchor or ".." in relative.parts:
        raise ValueError("The subject must be a project-relative file path.")
    path = (project / relative).resolve(strict=True)
    if not path.is_relative_to(project) or not path.is_file():
        raise ValueError("The subject must be a file inside the project.")

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def revision_problem(project: Path, record: dict) -> str | None:
    if not nonblank(record.get("revision")):
        return "revision missing; request this gate again"
    subject = record.get("subject")
    if subject is None:
        return None
    try:
        if not nonblank(subject):
            return "invalid subject; request this gate again"
        if subject_revision(project, subject) != record["revision"]:
            return "subject changed; request this gate again"
    except (OSError, RuntimeError, ValueError):
        return "subject is unavailable; restore it or request this gate again"
    return None


def decision_problem(project: Path, gate: str, record: dict) -> str | None:
    status = record.get("status", "NOT_REQUESTED")
    if status != "APPROVED" and not (gate == "G2" and status == "WAIVED"):
        return f"{status}; {'approval or waiver' if gate == 'G2' else 'approval'} required"
    if not nonblank(record.get("evidence")):
        return "evidence missing; request this gate again"
    if status == "APPROVED" and not nonblank(record.get("approver")):
        return "approver missing; request this gate again"
    return revision_problem(project, record)


def gate_failures(project: Path, checkpoint: dict, step: str) -> list[str]:
    failures = []
    for gate, gate_step in GATE_STEPS.items():
        if VALID_STEPS.index(step) > VALID_STEPS.index(gate_step):
            problem = decision_problem(project, gate, checkpoint["gates"].get(gate, {}))
            if problem:
                failures.append(f"{gate}: {problem}")
    return failures


def cmd_init(pipeline: Path, project_name: str) -> None:
    if (pipeline / "CHECKPOINT.json").exists():
        load_checkpoint(pipeline)
        print(f"INFO: Pipeline already initialized in {pipeline}")
        return

    checkpoint = {
        "project_name": project_name,
        "current_step": "1.0",
        "gates": {
            gate: {"status": "NOT_REQUESTED", "evidence": None, "updated_at": now_iso()}
            for gate in GATE_STEPS
        },
        "selected_design": None,
        "history": [],
    }
    record_event(pipeline, checkpoint, {"action": "INIT", "step": "1.0", "evidence": "Pipeline initialized"},
                 f"Initialized project pipeline `{project_name}`.")


def cmd_status(project: Path, checkpoint: dict) -> None:
    print(f"Project: {checkpoint.get('project_name', 'Unknown')}")
    print(f"Current Step: {checkpoint['current_step']}")
    print(f"Last Updated: {checkpoint.get('updated_at', 'Unknown')}")
    for gate, step in GATE_STEPS.items():
        record = checkpoint["gates"].get(gate, {})
        status = record.get("status", "NOT_REQUESTED")
        problem = None
        if status == "PENDING":
            problem = revision_problem(project, record)
        elif status in ("APPROVED", "WAIVED"):
            problem = decision_problem(project, gate, record)

        label = f"STALE ({status})" if problem else status
        print(f"[{gate}] {GATE_NAMES[gate]} (Step {step}): {label}")
        for field in ("revision", "subject", "approver", "evidence"):
            if record.get(field):
                print(f"    {field.capitalize()}: {record[field]}")
        if problem:
            print(f"    {problem}")


def cmd_request(
    project: Path, pipeline: Path, checkpoint: dict, gate: str,
    revision: str | None, subject: str | None
) -> None:
    if subject is not None:
        if not nonblank(subject):
            raise ValueError("--subject must be a nonblank relative file path.")
        subject = Path(subject).as_posix()
        revision = subject_revision(project, subject)
    elif not nonblank(revision):
        raise ValueError("--revision must be nonblank.")
    revision = revision.strip()

    previous = checkpoint["gates"].get(gate, {})
    status = previous.get("status")
    same_subject = previous.get("revision") == revision and previous.get("subject") == subject
    if same_subject and (
        status == "PENDING" or decision_problem(project, gate, previous) is None
    ):
        print(f"INFO: Gate {gate} is already {status} for {revision}.")
        return

    record = {
        "status": "PENDING",
        "revision": revision,
        "subject": subject,
        "evidence": None,
        "updated_at": now_iso(),
    }
    checkpoint["gates"][gate] = record
    if gate == "G2":
        checkpoint["selected_design"] = None

    event = {
        "action": "REQUEST_GATE", "gate": gate, "revision": revision,
        "subject": subject, "step": checkpoint["current_step"],
    }
    if status in ("PENDING", "APPROVED", "WAIVED"):
        event["previous"] = previous
    record_event(pipeline, checkpoint, event, f"Gate {gate} PENDING for {revision}.")


def cmd_decide(
    project: Path, pipeline: Path, checkpoint: dict, gate: str,
    revision: str, evidence: str, approver: str | None, design: str | None, status: str
) -> None:
    if not nonblank(evidence) or not nonblank(revision):
        raise ValueError("--evidence and --revision must be nonblank.")
    if status == "APPROVED" and not nonblank(approver):
        raise ValueError("--approver must identify the person or authority that approved.")
    if design is not None and (gate != "G2" or not nonblank(design)):
        raise ValueError("--design is available only for G2 and must be nonblank.")

    revision = revision.strip()
    evidence = evidence.strip()
    approver = approver.strip() if approver is not None else None
    design = design.strip() if design is not None else None
    record = checkpoint["gates"].get(gate, {})
    if record.get("revision") != revision:
        raise ValueError(f"Gate {gate}: revision does not match the current request.")
    problem = revision_problem(project, record)
    if problem:
        raise ValueError(f"Gate {gate}: {problem}.")

    if record.get("status") == status and (
        record.get("evidence"), record.get("approver"),
        checkpoint.get("selected_design") if gate == "G2" else None,
    ) == (evidence, approver, design):
        print(f"INFO: Gate {gate} is already {status} for {revision}.")
        return
    if record.get("status") != "PENDING":
        raise ValueError(f"Gate {gate}: a pending request is required for this decision.")

    record.update(status=status, evidence=evidence, approver=approver, updated_at=now_iso())
    if gate == "G2":
        checkpoint["selected_design"] = design

    action = "APPROVE_GATE" if status == "APPROVED" else "WAIVE_GATE"
    record_event(pipeline, checkpoint, {
        "action": action, "gate": gate, "revision": revision, "subject": record.get("subject"),
        "approver": approver, "evidence": evidence, "design": design,
    }, f"Gate {gate} {status} for {revision}.")


def cmd_advance(
    project: Path, pipeline: Path, checkpoint: dict, target_step: str, evidence: str
) -> None:
    if not nonblank(evidence):
        raise ValueError("--evidence must be nonblank.")
    current = checkpoint["current_step"]
    if VALID_STEPS.index(target_step) <= VALID_STEPS.index(current):
        raise ValueError(f"Cannot advance backward or to the same step ({current} to {target_step}).")

    failures = gate_failures(project, checkpoint, target_step)
    if failures:
        raise ValueError("Cannot advance: " + "; ".join(failures))

    checkpoint["current_step"] = target_step
    record_event(pipeline, checkpoint, {
        "action": "ADVANCE", "from": current, "to": target_step, "evidence": evidence.strip(),
    }, f"Advanced from Step {current} to Step {target_step}.")


def parse_args():
    parser = argparse.ArgumentParser(description="Pipeline State & Gate Lock Manager")
    parser.add_argument("--project-dir", default=".", help="Project root directory")
    commands = parser.add_subparsers(dest="cmd", required=True)

    init = commands.add_parser("init", help="Initialize the project pipeline")
    init.add_argument("--project", default="Project", help="Project name")
    commands.add_parser("status", help="Show pipeline state and gate revisions")
    commands.add_parser("validate", help="Validate checkpoint state and required gates")

    request = commands.add_parser("request", help="Request a decision for a gate revision")
    request.add_argument("--gate", required=True, choices=GATE_STEPS)
    source = request.add_mutually_exclusive_group(required=True)
    source.add_argument("--subject", help="Project-relative file to fingerprint")
    source.add_argument("--revision", help="Immutable ID for an external subject")

    approve = commands.add_parser("approve", help="Record an approval for a pending revision")
    approve.add_argument("--gate", required=True, choices=GATE_STEPS)
    approve.add_argument("--revision", required=True, help="Revision from request or status")
    approve.add_argument("--approver", required=True, help="Person or authority who approved")
    approve.add_argument("--evidence", required=True, help="Reference to the actual approval")
    approve.add_argument("--design", help="Selected design direction (G2 only)")

    waive = commands.add_parser("waive", help="Record a technical waiver for G2")
    waive.add_argument("--gate", required=True, choices=("G2",))
    waive.add_argument("--revision", required=True, help="Revision from request or status")
    waive.add_argument("--evidence", required=True, help="Reason this release scope has no UI review")

    advance = commands.add_parser("advance", help="Advance to a later pipeline step")
    advance.add_argument("--step", required=True, choices=VALID_STEPS)
    advance.add_argument("--evidence", required=True, help="Summary of completed work")

    log = commands.add_parser("log", help="Append a log entry")
    log.add_argument("--step", required=True)
    log.add_argument("--message", required=True)
    return parser.parse_args()


def run_mutation(project: Path, pipeline: Path, args) -> None:
    with lock_checkpoint(pipeline):
        if args.cmd == "init":
            cmd_init(pipeline, args.project)
        elif args.cmd == "log":
            append_log(pipeline, args.step, args.message)
            print("SUCCESS: Log entry recorded.")
        else:
            checkpoint = load_checkpoint(pipeline)
            if args.cmd == "request":
                cmd_request(project, pipeline, checkpoint, args.gate, args.revision, args.subject)
            elif args.cmd in ("approve", "waive"):
                status = "APPROVED" if args.cmd == "approve" else "WAIVED"
                cmd_decide(project, pipeline, checkpoint, args.gate, args.revision, args.evidence,
                           getattr(args, "approver", None), getattr(args, "design", None), status)
            elif args.cmd == "advance":
                cmd_advance(project, pipeline, checkpoint, args.step, args.evidence)


def main() -> int:
    args = parse_args()
    try:
        project = Path(args.project_dir).resolve()
        pipeline = project / ".pipeline"
        if args.cmd in ("status", "validate"):
            checkpoint = load_checkpoint(pipeline)
            if args.cmd == "status":
                cmd_status(project, checkpoint)
            else:
                failures = gate_failures(project, checkpoint, checkpoint["current_step"])
                if failures:
                    raise ValueError("Checkpoint validation failed: " + "; ".join(failures))
                print("VALIDATION OK: Pipeline state and gates are consistent.")
        else:
            run_mutation(project, pipeline, args)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
