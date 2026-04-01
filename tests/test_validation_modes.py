"""
Validation behavior matrix tests.

Exercises validate_events, validation_failure_mode, and the standalone
validation functions from an external consumer's perspective.
"""

from __future__ import annotations

import pytest

pytest.importorskip("jsonschema", reason="jsonschema required for validation mode tests")

from bh_audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    AuditValidationError,
    MemorySink,
    ValidationError,
    validate_event_minimal,
    validate_event_schema,
)

from tests.conftest import make_event


class TestValidateEventsDisabled:
    def test_invalid_pre_built_event_still_dropped_by_minimal(self) -> None:
        """Even without jsonschema, minimal validation catches missing fields."""
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                validate_events=False,
            ),
            sink=sink,
        )
        logger.emit({"bad": "event"})
        assert len(sink) == 0


class TestValidateEventsDropMode:
    def test_invalid_event_dropped(self) -> None:
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
        event = make_event()
        event["outcome"] = {"status": "BOGUS"}
        logger.emit(event)
        assert len(sink) == 0
        snap = logger.stats.snapshot()
        assert snap["events_dropped_total"] >= 1
        assert snap["validation_failures_total"] >= 1

    def test_valid_event_passes(self) -> None:
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
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert len(sink) == 1


class TestValidateEventsLogAndEmitMode:
    def test_invalid_event_still_emitted(self) -> None:
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
        event = make_event()
        event["outcome"] = {"status": "BOGUS"}
        logger.emit(event)
        assert len(sink) == 1
        snap = logger.stats.snapshot()
        assert snap["validation_failures_total"] >= 1


class TestValidateEventsRaiseMode:
    def test_invalid_event_raises(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                validate_events=True,
                validation_failure_mode="raise",
            ),
            sink=sink,
        )
        event = make_event()
        event["outcome"] = {"status": "BOGUS"}
        with pytest.raises(AuditValidationError) as exc_info:
            logger.emit(event)
        assert len(exc_info.value.errors) > 0

    def test_valid_event_no_exception(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                validate_events=True,
                validation_failure_mode="raise",
            ),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert len(sink) == 1


class TestStandaloneValidation:
    def test_validate_event_minimal_rejects_missing_keys(self) -> None:
        with pytest.raises(ValidationError, match="Missing required keys"):
            validate_event_minimal({"bad": "event"})

    def test_validate_event_minimal_accepts_valid(self) -> None:
        validate_event_minimal(make_event())

    def test_validate_event_schema_returns_errors_for_invalid(self) -> None:
        errors = validate_event_schema({"bad": "event"}, "1.1")
        assert len(errors) > 0

    def test_validate_event_schema_returns_empty_for_valid(self) -> None:
        errors = validate_event_schema(make_event(), "1.1")
        assert errors == []

    def test_validate_event_schema_version_routing(self) -> None:
        event_1_0 = make_event(schema_version="1.0")
        errors = validate_event_schema(event_1_0, "1.0")
        assert errors == []

        errors_wrong = validate_event_schema(event_1_0, "1.1")
        assert len(errors_wrong) > 0, "v1.0 event should fail v1.1 schema (version const mismatch)"
