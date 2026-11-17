#!/usr/bin/env python3
"""
Pipeline State & Gate Lock Manager (pipeline_gate.py)

Manages continuous project lifecycle state, monotonic phase progression,
and explicit human-in-the-loop approval gates (G1: Architecture, G2: Design).
Stores state artifacts cleanly under `.pipeline/` to preserve repository organization
while maintaining a complete, verifiable audit trail.
"""
from datetime import datetime, timezone
import argparse
import json
import os
import sys

VALID_STEPS = ["0", "1.0", "2.0", "2.5", "3.0", "3.5", "4.0", "5.0", "6.0", "6.5", "7.0"]

GATE_DEFINITIONS = {
    "G1": {"step": "2.5", "name": "Architecture & Specification Approval"},
    "G2": {"step": "3.0", "name": "UX/UI Design & Direction Selection"},
    "G3": {"step": "6.5", "name": "Multi-Role Delivery Sign-off"},
}

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def get_pipeline_dir(project_dir: str) -> str:
    return os.path.join(os.path.abspath(project_dir), ".pipeline")

def load_checkpoint(pipeline_dir: str) -> dict:
    cp_path = os.path.join(pipeline_dir, "CHECKPOINT.json")
    if not os.path.exists(cp_path):
        return {}
    try:
        with open(cp_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to read CHECKPOINT.json: {e}", file=sys.stderr)
        return {}

def save_checkpoint(pipeline_dir: str, data: dict) -> None:
    os.makedirs(pipeline_dir, exist_ok=True)
    cp_path = os.path.join(pipeline_dir, "CHECKPOINT.json")
    data["updated_at"] = now_iso()
    with open(cp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def append_log(pipeline_dir: str, step: str, message: str) -> None:
    os.makedirs(pipeline_dir, exist_ok=True)
    log_path = os.path.join(pipeline_dir, "PIPELINE_LOGS.md")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"- `[{timestamp}]` **[Step {step}]** {message}\n"
    if not os.path.exists(log_path):
        header = "# PIPELINE_LOGS.md - Project Execution History\n\n"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(header + entry)
    else:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(entry)

def cmd_init(project_dir: str, project_name: str) -> int:
    pipeline_dir = get_pipeline_dir(project_dir)
    os.makedirs(pipeline_dir, exist_ok=True)
    
    cp_path = os.path.join(pipeline_dir, "CHECKPOINT.json")
    if os.path.exists(cp_path):
        print(f"INFO: Pipeline already initialized in {pipeline_dir}")
        return 0

    init_data = {
        "schema_version": 2,
        "project_name": project_name,
        "current_step": "1.0",
        "gates": {
            "G1": {"status": "NOT_REQUESTED", "evidence": None, "updated_at": now_iso()},
            "G2": {"status": "NOT_REQUESTED", "evidence": None, "updated_at": now_iso()},
            "G3": {"status": "NOT_REQUESTED", "evidence": None, "updated_at": now_iso()},
        },
        "selected_design": None,
        "history": [
            {"action": "INIT", "step": "1.0", "evidence": "Pipeline initialized", "timestamp": now_iso()}
        ],
        "updated_at": now_iso(),
    }
    save_checkpoint(pipeline_dir, init_data)
    append_log(pipeline_dir, "1.0", f"Initialized project pipeline `{project_name}`.")
    print(f"SUCCESS: Pipeline initialized for `{project_name}` in {pipeline_dir}")
    return 0

def cmd_status(project_dir: str) -> int:
    pipeline_dir = get_pipeline_dir(project_dir)
    cp = load_checkpoint(pipeline_dir)
    if not cp:
        print(f"ERROR: No active pipeline found in {pipeline_dir}. Run `init` first.", file=sys.stderr)
        return 1

    print("=" * 60)
    print(f" Project:      {cp.get('project_name', 'Unknown')}")
    print(f" Current Step: {cp.get('current_step', 'Unknown')}")
    print(f" Last Updated: {cp.get('updated_at', 'Unknown')}")
    print("-" * 60)
    print(" Human Approval Gates:")
    gates = cp.get("gates", {})
    for gid, ginfo in GATE_DEFINITIONS.items():
        gstate = gates.get(gid, {})
        status = gstate.get("status", "UNKNOWN")
        evidence = gstate.get("evidence") or "None"
        print(f"   [{gid}] {ginfo['name']} (Step {ginfo['step']}): {status}")
        if status in ("APPROVED", "WAIVED"):
            print(f"         Evidence: {evidence}")
    print("=" * 60)
    return 0

def cmd_request(project_dir: str, gate: str) -> int:
    pipeline_dir = get_pipeline_dir(project_dir)
    cp = load_checkpoint(pipeline_dir)
    if not cp:
        print(f"ERROR: No active pipeline found.", file=sys.stderr)
        return 1

    if gate not in GATE_DEFINITIONS:
        print(f"ERROR: Unknown gate `{gate}`. Valid gates: {', '.join(GATE_DEFINITIONS.keys())}", file=sys.stderr)
        return 1

    gates = cp.setdefault("gates", {})
    gate_data = gates.setdefault(gate, {})
    current_status = gate_data.get("status", "NOT_REQUESTED")

    if current_status in ("APPROVED", "WAIVED"):
        print(f"INFO: Gate `{gate}` is already {current_status}.")
        return 0

    gate_data["status"] = "PENDING"
    gate_data["updated_at"] = now_iso()
    cp["history"].append({"action": "REQUEST_GATE", "gate": gate, "step": cp.get("current_step"), "timestamp": now_iso()})
    save_checkpoint(pipeline_dir, cp)
    append_log(pipeline_dir, cp.get("current_step", "2.0"), f"Gate `{gate}` ({GATE_DEFINITIONS[gate]['name']}) requested. Awaiting explicit user approval.")
    print(f"SUCCESS: Gate `{gate}` set to PENDING. Waiting for explicit user approval.")
    return 0

def cmd_approve(project_dir: str, gate: str, evidence: str, design: str | None = None) -> int:
    if not evidence or not evidence.strip():
        print("ERROR: --evidence is required and cannot be empty when approving a gate.", file=sys.stderr)
        return 1

    pipeline_dir = get_pipeline_dir(project_dir)
    cp = load_checkpoint(pipeline_dir)
    if not cp:
        print(f"ERROR: No active pipeline found.", file=sys.stderr)
        return 1

    if gate not in GATE_DEFINITIONS:
        print(f"ERROR: Unknown gate `{gate}`. Valid gates: {', '.join(GATE_DEFINITIONS.keys())}", file=sys.stderr)
        return 1

    gates = cp.setdefault("gates", {})
    gate_data = gates.setdefault(gate, {})
    gate_data["status"] = "APPROVED"
    gate_data["evidence"] = evidence.strip()
    gate_data["updated_at"] = now_iso()

    if design:
        cp["selected_design"] = design.strip()

    cp["history"].append({"action": "APPROVE_GATE", "gate": gate, "evidence": evidence.strip(), "timestamp": now_iso()})
    save_checkpoint(pipeline_dir, cp)
    append_log(pipeline_dir, cp.get("current_step", "2.0"), f"Gate `{gate}` APPROVED with evidence: \"{evidence.strip()}\"")
    print(f"SUCCESS: Gate `{gate}` APPROVED. Evidence recorded.")
    return 0

def cmd_waive(project_dir: str, gate: str, evidence: str) -> int:
    if not evidence or not evidence.strip():
        print("ERROR: --evidence is required explaining why the gate is waived (e.g. backend-only service).", file=sys.stderr)
        return 1

    pipeline_dir = get_pipeline_dir(project_dir)
    cp = load_checkpoint(pipeline_dir)
    if not cp:
        print(f"ERROR: No active pipeline found.", file=sys.stderr)
        return 1

    if gate not in GATE_DEFINITIONS:
        print(f"ERROR: Unknown gate `{gate}`. Valid gates: {', '.join(GATE_DEFINITIONS.keys())}", file=sys.stderr)
        return 1

    gates = cp.setdefault("gates", {})
    gate_data = gates.setdefault(gate, {})
    gate_data["status"] = "WAIVED"
    gate_data["evidence"] = evidence.strip()
    gate_data["updated_at"] = now_iso()

    cp["history"].append({"action": "WAIVE_GATE", "gate": gate, "evidence": evidence.strip(), "timestamp": now_iso()})
    save_checkpoint(pipeline_dir, cp)
    append_log(pipeline_dir, cp.get("current_step", "2.0"), f"Gate `{gate}` WAIVED with rationale: \"{evidence.strip()}\"")
    print(f"SUCCESS: Gate `{gate}` WAIVED. Rationale recorded.")
    return 0

def cmd_advance(project_dir: str, target_step: str, evidence: str) -> int:
    if target_step not in VALID_STEPS:
        print(f"ERROR: Invalid step `{target_step}`. Valid steps: {', '.join(VALID_STEPS)}", file=sys.stderr)
        return 1

    if not evidence or not evidence.strip():
        print("ERROR: --evidence is required explaining what work was completed before advancing.", file=sys.stderr)
        return 1

    pipeline_dir = get_pipeline_dir(project_dir)
    cp = load_checkpoint(pipeline_dir)
    if not cp:
        print(f"ERROR: No active pipeline found. Run `init` first.", file=sys.stderr)
        return 1

    curr_step = cp.get("current_step", "1.0")
    curr_idx = VALID_STEPS.index(curr_step) if curr_step in VALID_STEPS else 0
    target_idx = VALID_STEPS.index(target_step)

    if target_idx <= curr_idx:
        print(f"ERROR: Cannot advance backward or to the same step (from {curr_step} to {target_step}).", file=sys.stderr)
        return 1

    gates = cp.get("gates", {})

    # Check G1 lock: moving past 2.5 requires G1 approved or waived
    if target_idx > VALID_STEPS.index("2.5"):
        g1_status = gates.get("G1", {}).get("status")
        if g1_status not in ("APPROVED", "WAIVED"):
            print(f"BLOCKED: Cannot advance past Step 2.5 without Gate G1 approval or waiver (Status: {g1_status}).", file=sys.stderr)
            return 1

    # Check G2 lock: moving past 3.0 requires G2 approved or waived
    if target_idx > VALID_STEPS.index("3.0"):
        g2_status = gates.get("G2", {}).get("status")
        if g2_status not in ("APPROVED", "WAIVED"):
            print(f"BLOCKED: Cannot advance past Step 3.0 without Gate G2 approval or waiver (Status: {g2_status}).", file=sys.stderr)
            return 1

    # Check G3 lock: moving to Step 7.0 requires G3 approved
    if target_step == "7.0":
        g3_status = gates.get("G3", {}).get("status")
        if g3_status not in ("APPROVED", "WAIVED"):
            print(f"BLOCKED: Cannot advance to Step 7.0 without Gate G3 review sign-off (Status: {g3_status}).", file=sys.stderr)
            return 1

    cp["current_step"] = target_step
    cp["history"].append({"action": "ADVANCE", "from": curr_step, "to": target_step, "evidence": evidence.strip(), "timestamp": now_iso()})
    save_checkpoint(pipeline_dir, cp)
    append_log(pipeline_dir, target_step, f"Advanced from {curr_step} to {target_step}. Evidence: {evidence.strip()}")
    print(f"SUCCESS: Advanced pipeline to Step {target_step}.")
    return 0

def cmd_validate(project_dir: str) -> int:
    pipeline_dir = get_pipeline_dir(project_dir)
    cp = load_checkpoint(pipeline_dir)
    if not cp:
        print(f"ERROR: CHECKPOINT.json not found in {pipeline_dir}", file=sys.stderr)
        return 1

    errs = []
    step = cp.get("current_step")
    if step not in VALID_STEPS:
        errs.append(f"Invalid current_step: {step}")

    gates = cp.get("gates", {})
    if step in VALID_STEPS:
        s_idx = VALID_STEPS.index(step)
        if s_idx > VALID_STEPS.index("2.5") and gates.get("G1", {}).get("status") not in ("APPROVED", "WAIVED"):
            errs.append("G1 gate is not APPROVED or WAIVED past step 2.5")
        if s_idx > VALID_STEPS.index("3.0") and gates.get("G2", {}).get("status") not in ("APPROVED", "WAIVED"):
            errs.append("G2 gate is not APPROVED or WAIVED past step 3.0")

    if errs:
        for e in errs:
            print(f"VALIDATION ERROR: {e}", file=sys.stderr)
        return 1

    print("VALIDATION OK: Pipeline state and gates are consistent.")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Pipeline State & Gate Lock Manager")
    parser.add_argument("--project-dir", default=".", help="Project root directory (default: current directory)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize project pipeline")
    p_init.add_argument("--project", default="Project", help="Project name")

    sub.add_parser("status", help="Show current pipeline status")

    p_req = sub.add_parser("request", help="Request user approval for a gate")
    p_req.add_argument("--gate", required=True, choices=["G1", "G2", "G3"], help="Gate identifier")

    p_app = sub.add_parser("approve", help="Approve a gate with verified evidence")
    p_app.add_argument("--gate", required=True, choices=["G1", "G2", "G3"], help="Gate identifier")
    p_app.add_argument("--evidence", required=True, help="Specific quote or proof of user approval in conversation")
    p_app.add_argument("--design", default=None, help="Selected design theme/direction (for G2)")

    p_waive = sub.add_parser("waive", help="Waive a gate with technical justification")
    p_waive.add_argument("--gate", required=True, choices=["G1", "G2", "G3"], help="Gate identifier")
    p_waive.add_argument("--evidence", required=True, help="Technical justification for waiver (e.g. backend-only service)")

    p_adv = sub.add_parser("advance", help="Advance to the next pipeline step")
    p_adv.add_argument("--step", required=True, choices=VALID_STEPS, help="Target step")
    p_adv.add_argument("--evidence", required=True, help="Summary of work completed in current step")

    p_log = sub.add_parser("log", help="Append a log entry")
    p_log.add_argument("--step", required=True, help="Current step number")
    p_log.add_argument("--message", required=True, help="Log message text")

    sub.add_parser("validate", help="Validate checkpoint state consistency")

    args = parser.parse_args()

    if args.cmd == "init":
        sys.exit(cmd_init(args.project_dir, args.project))
    elif args.cmd == "status":
        sys.exit(cmd_status(args.project_dir))
    elif args.cmd == "request":
        sys.exit(cmd_request(args.project_dir, args.gate))
    elif args.cmd == "approve":
        sys.exit(cmd_approve(args.project_dir, args.gate, args.evidence, args.design))
    elif args.cmd == "waive":
        sys.exit(cmd_waive(args.project_dir, args.gate, args.evidence))
    elif args.cmd == "advance":
        sys.exit(cmd_advance(args.project_dir, args.step, args.evidence))
    elif args.cmd == "log":
        pipeline_dir = get_pipeline_dir(args.project_dir)
        append_log(pipeline_dir, args.step, args.message)
        print("SUCCESS: Log entry recorded.")
        sys.exit(0)
    elif args.cmd == "validate":
        sys.exit(cmd_validate(args.project_dir))

if __name__ == "__main__":
    main()
