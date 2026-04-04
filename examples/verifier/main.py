"""
Chain verification example.

Demonstrates:
1. Writing events to a LedgerSink (JSONL with built-in chain hashing)
2. Verifying the intact chain programmatically via verify_chain()
3. Tampering with an event and re-verifying to show detection

Run:
    python examples/verifier/main.py
"""

from __future__ import annotations

import json
import os
import tempfile

from bh_audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    LedgerSink,
    VerifyResult,
    verify_chain,
)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = os.path.join(tmpdir, "audit.jsonl")

        sink = LedgerSink(ledger_path)
        config = AuditLoggerConfig(
            service_name="verifier-demo",
            service_environment="demo",
        )
        logger = AuditLogger(config=config, sink=sink)

        print("=== Writing 5 chained audit events ===")
        for i in range(5):
            logger.audit(
                "READ",
                actor={"subject_id": f"user-{i}", "subject_type": "human"},
                resource={"type": "Patient", "id": f"patient-{i}"},
                outcome={"status": "SUCCESS"},
            )
        print(f"Wrote 5 events to {ledger_path}")

        print("\n=== Verifying intact chain ===")
        events = _load_events(ledger_path)
        result = verify_chain(events)
        _print_result(result)

        print("\n=== Tampering with event #3 (changing action type) ===")
        events[2]["action"]["type"] = "DELETE"

        result = verify_chain(events)
        _print_result(result)

        print("\n=== CLI usage (informational) ===")
        print(f"  bh-audit verify --source file --path {ledger_path}")
        print("  bh-audit verify --source file --path events.jsonl --format json")

    print("\nDone.")


def _load_events(path: str) -> list[dict]:
    events = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def _print_result(result: VerifyResult) -> None:
    print(f"  Result:          {result.result}")
    print(f"  Events scanned:  {result.events_scanned}")
    print(f"  Chain length:    {result.chain_length}")
    print(f"  Hash mismatches: {result.hash_mismatches}")
    print(f"  Chain gaps:      {result.chain_gaps}")
    if result.failures:
        for f in result.failures:
            print(f"  FAILURE: event #{f.event_index} ({f.event_id}): {f.failure_type}")


if __name__ == "__main__":
    main()
