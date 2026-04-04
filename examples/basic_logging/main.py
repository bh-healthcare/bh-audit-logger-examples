"""
Basic audit logging with bh-audit-logger (v1.0.0).

Demonstrates the simplest usage: AuditLogger + LoggingSink emitting
READ, CREATE, UPDATE, DELETE, and LOGIN events with default config.

Run:
    python examples/basic_logging/main.py
"""

from __future__ import annotations

import logging

from bh_audit_logger import AuditLogger, AuditLoggerConfig, LoggingSink

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")

logger = AuditLogger(
    config=AuditLoggerConfig(
        service_name="example-basic",
        service_environment="dev",
        service_version="1.0.0",
    ),
    sink=LoggingSink(logger_name="bh.audit", level="INFO"),
)


def main() -> None:
    print("=== Basic audit logging ===\n")

    logger.audit(
        "READ",
        actor={"subject_id": "clinician_42", "subject_type": "human"},
        resource={"type": "Patient", "id": "pat_001"},
    )

    logger.audit(
        "CREATE",
        actor={"subject_id": "clinician_42", "subject_type": "human"},
        resource={"type": "Note", "id": "note_100"},
    )

    logger.audit(
        "UPDATE",
        actor={"subject_id": "clinician_42", "subject_type": "human"},
        resource={"type": "Note", "id": "note_100"},
    )

    logger.audit(
        "DELETE",
        actor={"subject_id": "admin_01", "subject_type": "human", "roles": ["admin"]},
        resource={"type": "Note", "id": "note_100"},
    )

    logger.audit_access(
        "READ",
        actor={"subject_id": "clinician_42", "subject_type": "human"},
        resource={"type": "Patient", "id": "pat_002"},
    )

    logger.audit_login_success(
        actor={"subject_id": "clinician_42", "subject_type": "human"},
    )

    logger.audit_login_failure(
        actor={"subject_id": "unknown_user", "subject_type": "human"},
        error="Invalid credentials",
    )

    snap = logger.stats.snapshot()
    print(f"\nStats: {snap}")
    print(f"  events_emitted_total: {snap['events_emitted_total']}")


if __name__ == "__main__":
    main()
