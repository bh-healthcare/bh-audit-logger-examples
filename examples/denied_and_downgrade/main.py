"""
DENIED outcomes and v1.0 downgrade behavior.

Demonstrates:
- audit_access_denied() preserving DENIED under v1.1
- audit_access_denied() downgrading DENIED to FAILURE under v1.0
- Cross-org denial with owner_org_id
- Schema validation of both versions

Requires: pip install bh-audit-logger[jsonschema]

Run:
    python examples/denied_and_downgrade/main.py
"""

from __future__ import annotations

from bh_audit_logger import AuditLogger, AuditLoggerConfig, MemorySink, validate_event_schema


def denied_v1_1() -> None:
    """DENIED is preserved as-is under schema v1.1."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-denied",
            service_environment="dev",
            target_schema_version="1.1",
        ),
        sink=sink,
    )

    result = logger.audit_access_denied(
        "READ",
        error_type="RoleDenied",
        actor={
            "subject_id": "user_frontdesk_042",
            "subject_type": "human",
            "roles": ["front_desk"],
        },
        resource={"type": "Note", "id": "note_5567", "patient_id": "pat_1234"},
    )

    assert result is not None
    assert result["outcome"]["status"] == "DENIED"
    assert result["outcome"]["error_type"] == "RoleDenied"

    errors = validate_event_schema(result, "1.1")
    assert errors == [], f"v1.1 validation errors: {errors}"
    status = result["outcome"]["status"]
    etype = result["outcome"]["error_type"]
    print(f"  v1.1: status={status}, error_type={etype}")


def denied_v1_0_downgrade() -> None:
    """DENIED is downgraded to FAILURE under schema v1.0 (no DENIED in v1.0)."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-denied",
            service_environment="dev",
            target_schema_version="1.0",
        ),
        sink=sink,
    )

    result = logger.audit_access_denied(
        "READ",
        error_type="RoleDenied",
        actor={"subject_id": "user_frontdesk_042", "subject_type": "human"},
        resource={"type": "Note", "id": "note_5567"},
    )

    assert result is not None
    assert result["outcome"]["status"] == "FAILURE"
    assert result["schema_version"] == "1.0"

    errors = validate_event_schema(result, "1.0")
    assert errors == [], f"v1.0 validation errors: {errors}"
    print(
        f"  v1.0: status={result['outcome']['status']}, "
        f"error_message={result['outcome'].get('error_message')}"
    )


def cross_org_denied() -> None:
    """Cross-org access denied with owner_org_id."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-denied",
            service_environment="dev",
            target_schema_version="1.1",
        ),
        sink=sink,
    )

    result = logger.audit_access_denied(
        "READ",
        error_type="ConsentRequired",
        error_message="Patient consent not on file for external provider",
        actor={
            "subject_id": "user_therapist_017",
            "subject_type": "human",
            "org_id": "org_partner_clinic",
            "owner_org_id": "sample_org_id",
        },
        resource={"type": "Patient", "id": "pat_5678", "patient_id": "pat_5678"},
        phi_touched=True,
        data_classification="PHI",
    )

    assert result is not None
    assert result["outcome"]["status"] == "DENIED"
    assert result["actor"]["owner_org_id"] == "sample_org_id"

    errors = validate_event_schema(result, "1.1")
    assert errors == [], f"Cross-org validation errors: {errors}"
    print(
        f"  cross-org: actor_org={result['actor']['org_id']}, "
        f"owner_org={result['actor']['owner_org_id']}, "
        f"error_type={result['outcome']['error_type']}"
    )


if __name__ == "__main__":
    print("=== DENIED outcomes and v1.0 downgrade ===\n")

    print("DENIED under v1.1:")
    denied_v1_1()

    print("\nDENIED downgraded to FAILURE under v1.0:")
    denied_v1_0_downgrade()

    print("\nCross-org access denied:")
    cross_org_denied()

    print("\nAll denied/downgrade examples passed.")
