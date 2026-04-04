"""
LedgerSink demonstration: JSONL file with built-in chain hashing.

Writes audit events to a JSONL file with automatic integrity blocks,
then reads them back to verify the chain and demonstrates tamper
detection by modifying an event and re-verifying.

Requires:
    pip install bh-audit-logger

Run:
    python examples/ledger_sink/main.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from bh_audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    LedgerSink,
    compute_chain_hash,
)


def _verify_chain(events: list[dict]) -> tuple[bool, int]:
    """Verify chain integrity.  Returns (all_ok, break_index)."""
    prev_hash = None
    for i, evt in enumerate(events):
        integrity = evt.get("integrity", {})
        recomputed = compute_chain_hash(evt, prev_hash, integrity.get("hash_alg", "sha256"))
        if recomputed["event_hash"] != integrity.get("event_hash"):
            return False, i
        prev_hash = integrity["event_hash"]
    return True, -1


def main() -> None:
    print("=== LedgerSink example ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = Path(tmpdir) / "audit_ledger.jsonl"

        # --- Write events ---

        config = AuditLoggerConfig(
            service_name="intake-api",
            service_environment="dev",
        )
        with LedgerSink(ledger_path, algorithm="sha256") as sink:
            logger = AuditLogger(config, sink=sink)
            for i in range(5):
                logger.audit(
                    "READ",
                    actor={"subject_id": f"user_{i}", "subject_type": "human"},
                    resource={"type": "Patient", "id": f"p_{i}", "patient_id": f"pat_{i}"},
                    data_classification="PHI",
                )

        print(f"Wrote {5} events to {ledger_path.name}\n")

        # --- Read back and verify ---

        lines = ledger_path.read_text().strip().splitlines()
        events = [json.loads(line) for line in lines]

        print("--- Chain verification (untampered) ---")
        ok, break_idx = _verify_chain(events)
        print(f"  Chain intact: {'YES' if ok else f'NO — breaks at event {break_idx}'}\n")

        # --- Tamper with an event ---

        print("--- Tamper detection demo ---")
        print("  Modifying event 2: action type READ → DELETE")
        tampered = [json.loads(line) for line in lines]
        tampered[2]["action"]["type"] = "DELETE"

        ok, break_idx = _verify_chain(tampered)
        print(f"  Chain intact: {'YES' if ok else f'NO — break detected at event {break_idx}'}\n")

        # --- Show a ledger entry ---

        print("--- First ledger entry (pretty-printed) ---")
        print(json.dumps(events[0], indent=2))

    print("\nDone.")


if __name__ == "__main__":
    main()
