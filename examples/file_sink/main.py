"""
Persistent JSONL output with JsonlFileSink.

Demonstrates writing audit events to a JSONL file, reading them back,
and verifying the output. Uses a temporary directory to avoid leaving
files behind.

Run:
    python examples/file_sink/main.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from bh_audit_logger import AuditLogger, AuditLoggerConfig, JsonlFileSink


def main() -> None:
    print("=== File sink (JSONL) example ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        audit_log_path = Path(tmpdir) / "audit.jsonl"

        sink = JsonlFileSink(path=audit_log_path, flush=True)
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="example-file-sink",
                service_environment="dev",
                service_version="0.4.0",
            ),
            sink=sink,
        )

        logger.audit(
            "READ",
            actor={"subject_id": "clinician_01", "subject_type": "human"},
            resource={"type": "Patient", "id": "pat_001", "patient_id": "pat_001"},
            phi_touched=True,
            data_classification="PHI",
        )

        logger.audit(
            "EXPORT",
            actor={"subject_id": "svc_nightly_export", "subject_type": "service"},
            resource={"type": "PatientExport"},
            phi_touched=True,
            data_classification="PHI",
            correlation={"request_id": "batch-20260401-001"},
        )

        logger.audit(
            "UPDATE",
            actor={"subject_id": "clinician_01", "subject_type": "human"},
            resource={"type": "Note", "id": "note_42"},
        )

        sink.close()

        lines = audit_log_path.read_text().strip().splitlines()
        print(f"Wrote {len(lines)} events to {audit_log_path.name}\n")

        print("First event (pretty-printed):")
        first_event = json.loads(lines[0])
        print(json.dumps(first_event, indent=2))

        types = [json.loads(line)["action"]["type"] for line in lines]
        print(f"\nAll event types: {types}")
        print(f"Stats: {logger.stats.snapshot()}")


if __name__ == "__main__":
    main()
