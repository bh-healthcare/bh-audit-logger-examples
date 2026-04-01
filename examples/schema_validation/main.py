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


def invalid_event_drop_mode() -> None:
    """Show that invalid events are silently dropped in 'drop' mode."""
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

    logger.emit({"bad": "event", "missing": "everything"})
    snap = logger.stats.snapshot()
    print(f"  drop mode: events_in_sink={len(sink)}, dropped={snap['events_dropped_total']}")


def invalid_event_log_and_emit_mode() -> None:
    """Show that invalid events are logged AND emitted in 'log_and_emit' mode."""
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

    logger.emit({"bad": "event", "missing": "everything"})
    snap = logger.stats.snapshot()
    print(
        f"  log_and_emit mode: events_in_sink={len(sink)}, "
        f"validation_failures={snap['validation_failures_total']}"
    )


def invalid_event_raise_mode() -> None:
    """Show that invalid events raise AuditValidationError in 'raise' mode."""
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
        logger.emit({"bad": "event", "missing": "everything"})
        print("  raise mode: ERROR -- no exception raised!")
    except AuditValidationError as exc:
        print(f"  raise mode: caught AuditValidationError ({len(exc.errors)} errors)")


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

    print("\nAll schema validation examples passed.")
