"""
Runtime schema validation with both schema versions.

Demonstrates validate_events=True, target_schema_version negotiation,
and all three validation_failure_mode values (drop, log_and_emit, raise).

Requires: pip install bh-audit-logger[jsonschema]

Run:
    python examples/schema_validation/main.py
"""

from __future__ import annotations

import logging

from bh_audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    AuditValidationError,
    MemorySink,
    ValidationError,
    validate_event,
    validate_event_schema,
)

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")


def valid_events_1_1() -> None:
    """Emit valid v1.1 events with runtime validation enabled."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-validation",
            service_environment="dev",
            validate_events=True,
            validation_failure_mode="log_and_emit",
            target_schema_version="1.1",
        ),
        sink=sink,
    )

    result = logger.audit(
        "READ",
        actor={"subject_id": "user-1", "subject_type": "human"},
        resource={"type": "Patient", "id": "pat_001"},
    )
    assert result is not None
    assert result["schema_version"] == "1.1"

    errors = validate_event_schema(result, "1.1")
    assert errors == [], f"Unexpected validation errors: {errors}"
    print(f"  v1.1 event valid: {result['action']['type']} / {result['outcome']['status']}")


def valid_events_1_0() -> None:
    """Emit valid v1.0 events with runtime validation enabled."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-validation",
            service_environment="dev",
            validate_events=True,
            validation_failure_mode="log_and_emit",
            target_schema_version="1.0",
        ),
        sink=sink,
    )

    result = logger.audit(
        "READ",
        actor={"subject_id": "user-1", "subject_type": "human"},
        resource={"type": "Patient"},
    )
    assert result is not None
    assert result["schema_version"] == "1.0"

    errors = validate_event_schema(result, "1.0")
    assert errors == [], f"Unexpected validation errors: {errors}"
    print(f"  v1.0 event valid: {result['action']['type']} / {result['outcome']['status']}")


def _make_schema_invalid_event() -> dict:
    """Build a structurally valid event that fails JSON schema validation.

    Passes validate_event_minimal() (has all required keys, UUID event_id,
    ISO timestamp) but fails the JSON schema (outcome.status is not in the
    enum of allowed values).
    """
    return {
        "schema_version": "1.1",
        "event_id": "12345678-1234-5678-1234-567812345678",
        "timestamp": "2026-04-01T12:00:00.000Z",
        "service": {"name": "example-validation", "environment": "dev"},
        "actor": {"subject_id": "user-1", "subject_type": "human"},
        "action": {"type": "READ", "data_classification": "UNKNOWN"},
        "resource": {"type": "Patient"},
        "outcome": {"status": "BOGUS"},
    }


def invalid_event_drop_mode() -> None:
    """Show that schema-invalid events are silently dropped in 'drop' mode."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-validation",
            service_environment="dev",
            validate_events=True,
            validation_failure_mode="drop",
            target_schema_version="1.1",
        ),
        sink=sink,
    )

    logger.emit(_make_schema_invalid_event())
    snap = logger.stats.snapshot()
    print(f"  drop mode: events_in_sink={len(sink)}, dropped={snap['events_dropped_total']}")


def invalid_event_log_and_emit_mode() -> None:
    """Show that schema-invalid events are logged AND still emitted in 'log_and_emit' mode."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-validation",
            service_environment="dev",
            validate_events=True,
            validation_failure_mode="log_and_emit",
            target_schema_version="1.1",
        ),
        sink=sink,
    )

    logger.emit(_make_schema_invalid_event())
    snap = logger.stats.snapshot()
    print(
        f"  log_and_emit mode: events_in_sink={len(sink)}, "
        f"validation_failures={snap['validation_failures_total']}"
    )
    assert len(sink) == 1, "log_and_emit should still emit the event despite validation failure"


def invalid_event_raise_mode() -> None:
    """Show that schema-invalid events raise AuditValidationError in 'raise' mode."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-validation",
            service_environment="dev",
            validate_events=True,
            validation_failure_mode="raise",
            target_schema_version="1.1",
        ),
        sink=sink,
    )

    try:
        logger.emit(_make_schema_invalid_event())
        print("  raise mode: ERROR -- no exception raised!")
    except AuditValidationError as exc:
        print(f"  raise mode: caught AuditValidationError ({len(exc.errors)} errors)")


def standalone_validate_event() -> None:
    """Demonstrate validate_event(): raises ValidationError on invalid events.

    Unlike validate_event_schema() which returns a list of error strings,
    validate_event() raises ValidationError directly — a simpler API when
    you just want pass-or-fail semantics.
    """
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-validation",
            service_environment="dev",
            target_schema_version="1.1",
        ),
        sink=sink,
    )
    event = logger.audit(
        "READ",
        actor={"subject_id": "user-1", "subject_type": "human"},
        resource={"type": "Patient"},
    )
    assert event is not None

    validate_event(event)
    print("  Valid event: validate_event() passed (no exception)")

    try:
        validate_event(_make_schema_invalid_event())
        print("  Invalid event: ERROR -- no exception raised!")
    except ValidationError as exc:
        print(f"  Invalid event: validate_event() raised ValidationError: {exc}")


if __name__ == "__main__":
    print("=== Schema validation examples ===\n")

    print("Valid v1.1 events:")
    valid_events_1_1()

    print("\nValid v1.0 events:")
    valid_events_1_0()

    print("\nInvalid event handling:")
    invalid_event_drop_mode()
    invalid_event_log_and_emit_mode()
    invalid_event_raise_mode()

    print("\nStandalone validate_event():")
    standalone_validate_event()

    print("\nAll schema validation examples passed.")
