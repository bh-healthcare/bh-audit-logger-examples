"""
End-to-end PHI safety integration tests.

Verifies metadata filtering, error sanitization, and redaction utilities
work correctly through the full AuditLogger emit path.
"""

from __future__ import annotations

from bh_audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    MemorySink,
    contains_phi_tokens,
    redact_tokens,
    sanitize_error_message,
)


class TestMetadataAllowlist:
    def test_only_allowlisted_keys_survive(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                metadata_allowlist=frozenset({"batch_id", "count"}),
            ),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
            metadata={"batch_id": "b1", "count": 5, "secret": "hidden"},
        )
        meta = sink.events[0].get("metadata", {})
        assert "batch_id" in meta
        assert "count" in meta
        assert "secret" not in meta

    def test_empty_allowlist_strips_all_metadata(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
            metadata={"anything": "dropped"},
        )
        assert "metadata" not in sink.events[0]

    def test_non_scalar_values_dropped(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                metadata_allowlist=frozenset({"good", "bad"}),
            ),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
            metadata={"good": "scalar", "bad": {"nested": "dict"}},
        )
        meta = sink.events[0].get("metadata", {})
        assert "good" in meta
        assert "bad" not in meta

    def test_long_strings_truncated(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                metadata_allowlist=frozenset({"note"}),
                max_metadata_value_length=10,
            ),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
            metadata={"note": "This is way too long for the limit"},
        )
        note = sink.events[0]["metadata"]["note"]
        assert note.endswith("...")
        assert len(note) <= 14  # 10 + "..."


class TestErrorSanitization:
    def test_ssn_pattern_redacted(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
            error="SSN 123-45-6789 not found",
        )
        msg = sink.events[0]["outcome"]["error_message"]
        assert "123-45-6789" not in msg
        assert "REDACTED" in msg

    def test_email_pattern_redacted(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
            error="Contact john@example.com for help",
        )
        msg = sink.events[0]["outcome"]["error_message"]
        assert "john@example.com" not in msg

    def test_phone_pattern_redacted(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
            error="Call 555-123-4567 for support",
        )
        msg = sink.events[0]["outcome"]["error_message"]
        assert "555-123-4567" not in msg

    def test_sanitize_errors_false_preserves_original(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                sanitize_errors=False,
            ),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
            error="SSN 123-45-6789 visible",
        )
        msg = sink.events[0]["outcome"]["error_message"]
        assert "123-45-6789" in msg


class TestStandaloneRedactionUtilities:
    def test_sanitize_error_message_basic(self) -> None:
        result = sanitize_error_message("SSN 123-45-6789 leaked")
        assert "123-45-6789" not in result

    def test_sanitize_error_message_truncation(self) -> None:
        long_msg = "x" * 300
        result = sanitize_error_message(long_msg, max_len=50)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_contains_phi_tokens_finds_matches(self) -> None:
        found = contains_phi_tokens("John Doe visited clinic", ["John Doe", "pat_123"])
        assert "John Doe" in found
        assert "pat_123" not in found

    def test_contains_phi_tokens_case_insensitive(self) -> None:
        found = contains_phi_tokens("JOHN DOE visited", ["john doe"])
        assert "john doe" in found

    def test_redact_tokens_replaces(self) -> None:
        result = redact_tokens("Patient John Doe (ID: pat_123)", ["John Doe", "pat_123"])
        assert "John Doe" not in result
        assert "pat_123" not in result
        assert "[REDACTED]" in result

    def test_redact_tokens_custom_replacement(self) -> None:
        result = redact_tokens("Secret value here", ["Secret"], replacement="***")
        assert "Secret" not in result
        assert "***" in result
