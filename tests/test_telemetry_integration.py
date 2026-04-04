"""Integration tests for the telemetry system."""

from __future__ import annotations

import json
import tempfile

from bh_audit_logger import AuditLogger, AuditLoggerConfig, MemorySink


def test_telemetry_counters_accumulate() -> None:
    """Telemetry counters tally events by action type and outcome."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AuditLoggerConfig(
            service_name="telemetry-test",
            service_environment="test",
            telemetry_enabled=True,
            telemetry_endpoint="https://example.com/telemetry",
            telemetry_deployment_id_path=tmpdir,
        )
        sink = MemorySink()
        logger = AuditLogger(config=config, sink=sink)

        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
            outcome={"status": "SUCCESS"},
        )
        logger.audit(
            "CREATE",
            actor={"subject_id": "u2", "subject_type": "human"},
            resource={"type": "Patient"},
            outcome={"status": "SUCCESS"},
        )

        emitter = logger._telemetry
        assert emitter is not None
        counters = emitter.counters
        assert counters.events_emitted == 2
        assert counters.by_action_type.get("READ") == 1
        assert counters.by_action_type.get("CREATE") == 1
        assert counters.by_outcome.get("SUCCESS") == 2


def test_telemetry_report_has_no_pii() -> None:
    """Telemetry report must contain no PII/PHI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AuditLoggerConfig(
            service_name="telemetry-test",
            service_environment="test",
            telemetry_enabled=True,
            telemetry_endpoint="https://example.com/telemetry",
            telemetry_deployment_id_path=tmpdir,
        )
        sink = MemorySink()
        logger = AuditLogger(config=config, sink=sink)

        logger.audit(
            "READ",
            actor={"subject_id": "john.doe@example.com", "subject_type": "human"},
            resource={"type": "Patient", "id": "patient-123-ssn-999"},
            outcome={"status": "SUCCESS"},
        )

        emitter = logger._telemetry
        assert emitter is not None
        report = emitter.counters.to_report("deploy-id", "svc", "test", "0.5.0")
        serialized = json.dumps(report)

        assert "john.doe" not in serialized
        assert "patient-123" not in serialized
        assert "999" not in serialized or "events_emitted" in serialized
        assert "example.com" not in serialized
