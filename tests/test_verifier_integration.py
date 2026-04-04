"""Integration tests for the chain verifier with LedgerSink end-to-end."""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from bh_audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    LedgerSink,
    verify_chain,
)


def _load_events(path: str) -> list[dict[str, Any]]:
    events = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def test_ledger_to_verify_chain_pass() -> None:
    """Write events via LedgerSink, verify -> PASS."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "audit.jsonl")
        sink = LedgerSink(path)
        config = AuditLoggerConfig(
            service_name="verifier-test",
            service_environment="test",
        )
        logger = AuditLogger(config=config, sink=sink)

        for i in range(5):
            logger.audit(
                "READ",
                actor={"subject_id": f"user-{i}", "subject_type": "human"},
                resource={"type": "Patient", "id": f"patient-{i}"},
                outcome={"status": "SUCCESS"},
            )

        events = _load_events(path)
        result = verify_chain(events)
        assert result.result == "PASS"
        assert result.events_scanned == 5
        assert result.chain_length == 5
        assert result.hash_mismatches == 0
        assert result.chain_gaps == 0


def test_tampered_event_detected() -> None:
    """Tamper with a ledger event -> verify detects FAIL."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "audit.jsonl")
        sink = LedgerSink(path)
        config = AuditLoggerConfig(
            service_name="verifier-test",
            service_environment="test",
        )
        logger = AuditLogger(config=config, sink=sink)

        for i in range(3):
            logger.audit(
                "READ",
                actor={"subject_id": f"user-{i}", "subject_type": "human"},
                resource={"type": "Patient"},
                outcome={"status": "SUCCESS"},
            )

        events = _load_events(path)
        events[1]["action"]["type"] = "DELETE"

        result = verify_chain(events)
        assert result.result == "FAIL"
        assert result.hash_mismatches >= 1
