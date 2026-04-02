"""
Metadata allowlists, redaction, and PHI safety.

Demonstrates how bh-audit-logger enforces PHI safety through metadata
filtering, error sanitization, and explicit redaction utilities.

Run:
    python examples/metadata_and_phi/main.py
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


def metadata_allowlist_filtering() -> None:
    """Only allowlisted keys survive; others are dropped."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-phi",
            service_environment="dev",
            metadata_allowlist=frozenset({"batch_id", "record_count"}),
        ),
        sink=sink,
    )

    logger.audit(
        "READ",
        actor={"subject_id": "user-1", "subject_type": "human"},
        resource={"type": "Patient"},
        metadata={
            "batch_id": "batch-001",
            "record_count": 42,
            "secret_ssn": "123-45-6789",
            "patient_name": "John Doe",
        },
    )

    event = sink.events[0]
    meta = event.get("metadata", {})
    print(f"  Allowlisted keys present: {sorted(meta.keys())}")
    assert "secret_ssn" not in meta
    assert "patient_name" not in meta
    assert meta["batch_id"] == "batch-001"


def empty_allowlist_strips_all() -> None:
    """Empty allowlist removes the metadata block entirely."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-phi",
            service_environment="dev",
        ),
        sink=sink,
    )

    logger.audit(
        "READ",
        actor={"subject_id": "user-1", "subject_type": "human"},
        resource={"type": "Patient"},
        metadata={"anything": "gets_dropped"},
    )

    event = sink.events[0]
    assert "metadata" not in event
    print("  Empty allowlist: metadata block removed entirely")


def error_message_sanitization() -> None:
    """SSN, email, and phone patterns are redacted from error messages."""
    sanitized = sanitize_error_message(
        "Failed for patient SSN 123-45-6789, email john@example.com, phone 555-123-4567"
    )
    print(f"  Sanitized: {sanitized}")
    assert "123-45-6789" not in sanitized
    assert "john@example.com" not in sanitized
    assert "555-123-4567" not in sanitized


def error_sanitization_in_events() -> None:
    """Error messages in emitted events are automatically sanitized."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-phi",
            service_environment="dev",
        ),
        sink=sink,
    )

    logger.audit(
        "READ",
        actor={"subject_id": "user-1", "subject_type": "human"},
        resource={"type": "Patient"},
        error="Patient SSN 123-45-6789 not found in system",
    )

    event = sink.events[0]
    error_msg = event["outcome"]["error_message"]
    print(f"  Event error_message: {error_msg}")
    assert "123-45-6789" not in error_msg


def phi_token_detection() -> None:
    """contains_phi_tokens finds known sensitive values in text."""
    tokens = ["John Doe", "123-45-6789", "pat_1234"]
    text = "Processing record for John Doe, patient pat_1234"

    found = contains_phi_tokens(text, tokens)
    print(f"  PHI tokens found: {found}")
    assert "John Doe" in found
    assert "pat_1234" in found


def explicit_redaction() -> None:
    """redact_tokens replaces known values in text."""
    tokens = ["John Doe", "pat_1234"]
    text = "Record for John Doe (pat_1234) updated"

    redacted = redact_tokens(text, tokens)
    print(f"  Redacted: {redacted}")
    assert "John Doe" not in redacted
    assert "pat_1234" not in redacted


def metadata_string_truncation() -> None:
    """Long metadata strings are truncated to max_metadata_value_length."""
    sink = MemorySink()
    logger = AuditLogger(
        config=AuditLoggerConfig(
            service_name="example-phi",
            service_environment="dev",
            metadata_allowlist=frozenset({"note"}),
            max_metadata_value_length=20,
        ),
        sink=sink,
    )

    logger.audit(
        "READ",
        actor={"subject_id": "user-1", "subject_type": "human"},
        resource={"type": "Patient"},
        metadata={"note": "This is a very long metadata value that exceeds the limit"},
    )

    event = sink.events[0]
    note_value = event["metadata"]["note"]
    print(f"  Truncated metadata: '{note_value}' (len={len(note_value)})")
    assert note_value.endswith("...")
    assert len(note_value) <= 23  # value[:20] + "..."


def main() -> None:
    print("=== Metadata and PHI safety ===\n")

    print("Metadata allowlist filtering:")
    metadata_allowlist_filtering()

    print("\nEmpty allowlist:")
    empty_allowlist_strips_all()

    print("\nError message sanitization (standalone):")
    error_message_sanitization()

    print("\nError sanitization in emitted events:")
    error_sanitization_in_events()

    print("\nPHI token detection:")
    phi_token_detection()

    print("\nExplicit token redaction:")
    explicit_redaction()

    print("\nMetadata string truncation:")
    metadata_string_truncation()

    print("\nAll metadata/PHI examples passed.")


if __name__ == "__main__":
    main()
