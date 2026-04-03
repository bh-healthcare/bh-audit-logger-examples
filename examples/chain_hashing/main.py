"""
Chain hashing (integrity) demonstration.

Shows how ``enable_integrity=True`` on AuditLogger injects a tamper-evident
integrity block into every emitted event, and how to verify the chain
manually using ``canonical_serialize`` and ``compute_chain_hash``.

Requires:
    pip install bh-audit-logger

Run:
    python examples/chain_hashing/main.py
"""

from __future__ import annotations

import json

from bh_audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    MemorySink,
    compute_chain_hash,
)


def main() -> None:
    print("=== Chain hashing (integrity) example ===\n")

    sink = MemorySink()
    config = AuditLoggerConfig(
        service_name="intake-api",
        service_environment="dev",
        service_version="0.4.0",
        enable_integrity=True,
        hash_algorithm="sha256",
    )
    logger = AuditLogger(config, sink=sink)

    for i in range(5):
        logger.audit(
            "READ",
            actor={"subject_id": f"clinician_{i:02d}", "subject_type": "human"},
            resource={"type": "Patient", "id": f"res_{i}", "patient_id": f"pat_{i}"},
            phi_touched=True,
            data_classification="PHI",
        )

    events = sink.events
    print(f"Emitted {len(events)} events with integrity blocks.\n")

    # --- Show integrity blocks ---

    print("--- Integrity chain ---")
    for i, evt in enumerate(events):
        integrity = evt["integrity"]
        prev = integrity.get("prev_event_hash", "(none — chain start)")
        hash_short = integrity["event_hash"][:16]
        prev_short = prev[:16] + ("…" if len(prev) > 16 else "")
        print(f"  Event {i}: hash={hash_short}…  prev={prev_short}")

    # --- Verify continuity ---

    print("\n--- Chain continuity check ---")
    for i in range(1, len(events)):
        cur_prev = events[i]["integrity"]["prev_event_hash"]
        prev_hash = events[i - 1]["integrity"]["event_hash"]
        ok = cur_prev == prev_hash
        print(f"  Event {i}: prev_event_hash matches event {i - 1}? {'YES' if ok else 'NO'}")

    # --- Manual hash verification ---

    print("\n--- Manual hash verification ---")
    prev_hash = None
    all_ok = True
    for i, evt in enumerate(events):
        recomputed = compute_chain_hash(evt, prev_hash, evt["integrity"]["hash_alg"])
        match = recomputed["event_hash"] == evt["integrity"]["event_hash"]
        if not match:
            all_ok = False
        print(f"  Event {i}: recomputed hash matches? {'YES' if match else 'NO'}")
        prev_hash = evt["integrity"]["event_hash"]

    print(f"\nAll hashes verified: {'YES' if all_ok else 'NO'}")

    # --- Pretty-print first event ---

    print("\n--- First event (with integrity block) ---")
    print(json.dumps(events[0], indent=2))

    print("\nDone.")


if __name__ == "__main__":
    main()
