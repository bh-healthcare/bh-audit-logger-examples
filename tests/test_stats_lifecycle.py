"""
AuditStats counter correctness tests.

Verifies that stats counters track events, failures, drops, and
validation timing correctly from an external consumer's perspective.
"""

from __future__ import annotations

from typing import Any

import pytest
from bh_audit_logger import AuditLogger, AuditLoggerConfig, MemorySink

jsonschema = pytest.importorskip("jsonschema", reason="jsonschema required for validation stats")


class TestStatsZeroBaseline:
    def test_fresh_logger_all_zero(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        snap = logger.stats.snapshot()
        assert snap["events_emitted_total"] == 0
        assert snap["emit_failures_total"] == 0
        assert snap["events_dropped_total"] == 0
        assert snap["validation_failures_total"] == 0

    def test_snapshot_has_all_expected_keys(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        snap = logger.stats.snapshot()
        expected_keys = {
            "events_emitted_total",
            "emit_failures_total",
            "events_dropped_total",
            "validation_failures_total",
            "validation_time_ms_total",
        }
        assert expected_keys.issubset(set(snap.keys()))


class TestEmitCounting:
    def test_successful_emits_counted(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        for _ in range(3):
            logger.audit(
                "READ",
                actor={"subject_id": "u1", "subject_type": "human"},
                resource={"type": "Patient"},
            )
        assert logger.stats.snapshot()["events_emitted_total"] == 3

    def test_multiple_action_types_counted(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        for action in ("READ", "CREATE", "UPDATE", "DELETE", "LOGIN"):
            logger.audit(
                action,
                actor={"subject_id": "u1", "subject_type": "human"},
                resource={"type": "Patient"},
            )
        assert logger.stats.snapshot()["events_emitted_total"] == 5


class TestFailureCounting:
    def test_broken_sink_increments_emit_failures(self) -> None:
        class _ExplodingSink:
            def emit(self, event: dict[str, Any]) -> None:
                raise ConnectionError("boom")

        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                emit_failure_mode="log",
            ),
            sink=_ExplodingSink(),  # type: ignore[arg-type]
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        snap = logger.stats.snapshot()
        assert snap["emit_failures_total"] == 1
        assert snap["events_emitted_total"] == 0


class TestValidationStats:
    def test_drop_mode_increments_dropped_and_validation_failures(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                validate_events=True,
                validation_failure_mode="drop",
            ),
            sink=sink,
        )
        from tests.conftest import make_event

        event = make_event()
        event["outcome"] = {"status": "INVALID_STATUS"}
        logger.emit(event)
        snap = logger.stats.snapshot()
        assert snap["validation_failures_total"] >= 1
        assert snap["events_dropped_total"] >= 1

    def test_validation_timing_recorded(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                validate_events=True,
                validation_failure_mode="log_and_emit",
            ),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        snap = logger.stats.snapshot()
        assert snap["validation_time_ms_total"] > 0

    def test_minimal_validation_failure_drops_and_counts(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                emit_failure_mode="log",
            ),
            sink=sink,
        )
        logger.emit({"totally": "invalid"})
        snap = logger.stats.snapshot()
        assert snap["validation_failures_total"] >= 1
        assert snap["events_dropped_total"] >= 1
        assert len(sink) == 0
