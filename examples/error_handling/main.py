"""
Failure isolation and emit_failure_mode behavior.

Demonstrates that audit failures never crash the application, with
each of the three emit_failure_mode values: silent, log, raise.

Run:
    python examples/error_handling/main.py
"""

from __future__ import annotations

import logging
from typing import Any

from bh_audit_logger import AuditLogger, AuditLoggerConfig

logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s %(message)s")


class _BrokenSink:
    """A sink that always raises, simulating a backend outage."""

    def emit(self, event: dict[str, Any]) -> None:
        raise ConnectionError("database unavailable")


def failure_mode_log() -> None:
    """emit_failure_mode='log': warns but doesn't crash."""
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-errors",
            service_environment="dev",
            emit_failure_mode="log",
        ),
        sink=_BrokenSink(),  # type: ignore[arg-type]
    )

    logger.audit(
        "READ",
        actor={"subject_id": "user-1", "subject_type": "human"},
        resource={"type": "Patient"},
    )

    snap = logger.stats.snapshot()
    print(f"  'log' mode: emit_failures={snap['emit_failures_total']}, no crash")


def failure_mode_silent() -> None:
    """emit_failure_mode='silent': logs at DEBUG only."""
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-errors",
            service_environment="dev",
            emit_failure_mode="silent",
        ),
        sink=_BrokenSink(),  # type: ignore[arg-type]
    )

    logger.audit(
        "READ",
        actor={"subject_id": "user-1", "subject_type": "human"},
        resource={"type": "Patient"},
    )

    snap = logger.stats.snapshot()
    print(f"  'silent' mode: emit_failures={snap['emit_failures_total']}, no crash")


def failure_mode_raise() -> None:
    """emit_failure_mode='raise': propagates the exception."""
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-errors",
            service_environment="dev",
            emit_failure_mode="raise",
        ),
        sink=_BrokenSink(),  # type: ignore[arg-type]
    )

    try:
        logger.audit(
            "READ",
            actor={"subject_id": "user-1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        print("  'raise' mode: ERROR -- no exception raised!")
    except ConnectionError as exc:
        print(f"  'raise' mode: caught {type(exc).__name__}: {exc}")


def main() -> None:
    print("=== Error handling / failure isolation ===\n")

    print("emit_failure_mode='log':")
    failure_mode_log()

    print("\nemit_failure_mode='silent':")
    failure_mode_silent()

    print("\nemit_failure_mode='raise':")
    failure_mode_raise()

    print("\nAll error handling examples passed.")


if __name__ == "__main__":
    main()
