"""
Custom AuditSink implementations.

Demonstrates that any object with an emit(event: dict) -> None method
satisfies the AuditSink protocol, enabling integration with any backend.

Run:
    python examples/custom_sink/main.py
"""

from __future__ import annotations

import json
from typing import Any

from bh_audit_logger import AuditLogger, AuditLoggerConfig, AuditSink


class PostgresSink:
    """Stub sink that prints a SQL INSERT instead of executing it."""

    def __init__(self, table: str = "audit_events") -> None:
        self._table = table
        self.call_count = 0

    def emit(self, event: dict[str, Any]) -> None:
        self.call_count += 1
        event_id = event.get("event_id", "?")
        action = event.get("action", {}).get("type", "?")
        payload = json.dumps(event, separators=(",", ":"))
        print(f"  [PostgresSink] INSERT INTO {self._table} (event_id, action, payload)")
        print(f"    VALUES ('{event_id}', '{action}', '{payload[:80]}...')")


class WebhookSink:
    """Stub sink that prints an HTTP POST payload instead of sending it."""

    def __init__(self, url: str = "https://audit.example.com/events") -> None:
        self._url = url
        self.call_count = 0

    def emit(self, event: dict[str, Any]) -> None:
        self.call_count += 1
        print(f"  [WebhookSink] POST {self._url}")
        print("    Content-Type: application/json")
        print(f"    Body: {json.dumps(event, separators=(',', ':'))[:80]}...")


def main() -> None:
    print("=== Custom sink examples ===\n")

    pg_sink = PostgresSink(table="hipaa_audit_log")
    assert isinstance(pg_sink, AuditSink), "PostgresSink does not satisfy AuditSink protocol"
    print("PostgresSink satisfies AuditSink protocol: True")

    webhook_sink = WebhookSink()
    assert isinstance(webhook_sink, AuditSink), "WebhookSink does not satisfy AuditSink protocol"
    print("WebhookSink satisfies AuditSink protocol: True\n")

    print("PostgresSink:")
    pg_logger = AuditLogger(
        config=AuditLoggerConfig(service_name="example-custom-sink", service_environment="dev"),
        sink=pg_sink,
    )
    pg_logger.audit(
        "READ",
        actor={"subject_id": "clinician_01", "subject_type": "human"},
        resource={"type": "Patient", "id": "pat_001"},
    )

    print("\nWebhookSink:")
    wh_logger = AuditLogger(
        config=AuditLoggerConfig(service_name="example-custom-sink", service_environment="dev"),
        sink=webhook_sink,
    )
    wh_logger.audit(
        "CREATE",
        actor={"subject_id": "clinician_01", "subject_type": "human"},
        resource={"type": "Note", "id": "note_42"},
    )

    print(f"\nPostgresSink calls: {pg_sink.call_count}")
    print(f"WebhookSink calls: {webhook_sink.call_count}")


if __name__ == "__main__":
    main()
