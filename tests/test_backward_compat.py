"""
Schema version backward compatibility tests.

Verifies that events built for v1.0 validate against the v1.0 schema,
events built for v1.1 validate against v1.1, and that the DENIED
downgrade path works correctly.
"""

from __future__ import annotations

import pytest

pytest.importorskip("jsonschema", reason="jsonschema required for backward compat tests")

from bh_audit_logger import AuditLogger, AuditLoggerConfig, MemorySink, validate_event_schema

from tests.conftest import make_event


class TestSchemaVersionInterop:
    def test_1_0_events_pass_1_0_schema(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="compat-test",
                service_environment="test",
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
        errors = validate_event_schema(result, "1.0")
        assert errors == [], f"v1.0 event failed v1.0 schema: {errors}"

    def test_1_1_events_pass_1_1_schema(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="compat-test",
                service_environment="test",
                target_schema_version="1.1",
            ),
            sink=sink,
        )
        result = logger.audit(
            "READ",
            actor={"subject_id": "user-1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert result is not None
        errors = validate_event_schema(result, "1.1")
        assert errors == [], f"v1.1 event failed v1.1 schema: {errors}"

    def test_1_1_failure_events_pass_1_1_schema(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="compat-test",
                service_environment="test",
                target_schema_version="1.1",
            ),
            sink=sink,
        )
        result = logger.audit(
            "READ",
            actor={"subject_id": "user-1", "subject_type": "human"},
            resource={"type": "Patient"},
            error="Something went wrong",
        )
        assert result is not None
        assert result["outcome"]["status"] == "FAILURE"
        errors = validate_event_schema(result, "1.1")
        assert errors == [], f"v1.1 FAILURE event failed schema: {errors}"

    def test_1_0_failure_events_pass_1_0_schema(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="compat-test",
                service_environment="test",
                target_schema_version="1.0",
            ),
            sink=sink,
        )
        result = logger.audit(
            "READ",
            actor={"subject_id": "user-1", "subject_type": "human"},
            resource={"type": "Patient"},
            error="Something went wrong",
        )
        assert result is not None
        assert result["outcome"]["status"] == "FAILURE"
        errors = validate_event_schema(result, "1.0")
        assert errors == [], f"v1.0 FAILURE event failed schema: {errors}"


class TestDeniedDowngrade:
    def test_denied_preserved_under_1_1(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="compat-test",
                service_environment="test",
                target_schema_version="1.1",
            ),
            sink=sink,
        )
        result = logger.audit_access_denied(
            "READ",
            error_type="RoleDenied",
            actor={"subject_id": "user-1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert result is not None
        assert result["outcome"]["status"] == "DENIED"
        errors = validate_event_schema(result, "1.1")
        assert errors == [], f"DENIED event failed v1.1 schema: {errors}"

    def test_denied_becomes_failure_under_1_0(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="compat-test",
                service_environment="test",
                target_schema_version="1.0",
            ),
            sink=sink,
        )
        result = logger.audit_access_denied(
            "READ",
            error_type="RoleDenied",
            actor={"subject_id": "user-1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert result is not None
        assert result["outcome"]["status"] == "FAILURE"
        assert result["schema_version"] == "1.0"
        errors = validate_event_schema(result, "1.0")
        assert errors == [], f"Downgraded DENIED event failed v1.0 schema: {errors}"

    def test_denied_fails_1_0_schema_directly(self) -> None:
        """A raw DENIED event should fail v1.0 schema (DENIED not in enum)."""
        event = make_event(
            schema_version="1.0",
            outcome={"status": "DENIED", "error_type": "RoleDenied"},
        )
        errors = validate_event_schema(event, "1.0")
        assert len(errors) > 0, "DENIED should fail v1.0 schema validation"

    def test_cross_org_denied_validates(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="compat-test",
                service_environment="test",
                target_schema_version="1.1",
            ),
            sink=sink,
        )
        result = logger.audit_access_denied(
            "READ",
            error_type="ConsentRequired",
            error_message="Consent not on file",
            actor={
                "subject_id": "user-1",
                "subject_type": "human",
                "org_id": "org_partner",
                "owner_org_id": "org_primary",
            },
            resource={"type": "Patient", "id": "pat_1"},
        )
        assert result is not None
        assert result["actor"]["owner_org_id"] == "org_primary"
        errors = validate_event_schema(result, "1.1")
        assert errors == [], f"Cross-org DENIED failed schema: {errors}"

    def test_login_events_validate_both_versions(self) -> None:
        for ver in ("1.0", "1.1"):
            sink = MemorySink()
            logger = AuditLogger(
                config=AuditLoggerConfig(
                    service_name="compat-test",
                    service_environment="test",
                    target_schema_version=ver,  # type: ignore[arg-type]
                ),
                sink=sink,
            )
            success = logger.audit_login_success(
                actor={"subject_id": "user-1", "subject_type": "human"},
            )
            failure = logger.audit_login_failure(
                actor={"subject_id": "user-1", "subject_type": "human"},
                error="Bad password",
            )
            assert success is not None
            assert failure is not None
            for event in (success, failure):
                errors = validate_event_schema(event, ver)
                assert errors == [], f"Login event failed v{ver} schema: {errors}"
