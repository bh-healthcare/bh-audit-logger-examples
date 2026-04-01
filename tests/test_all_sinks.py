"""
Integration tests for every AuditSink implementation.

Verifies that each built-in sink and the custom sink protocol work
correctly when used with AuditLogger from an external consumer's
perspective.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest
from bh_audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    AuditSink,
    JsonlFileSink,
    LoggingSink,
    MemorySink,
)


class TestMemorySink:
    def test_emit_stores_event(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        result = logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert len(sink) == 1
        assert sink.events[0]["action"]["type"] == "READ"
        assert result is not None

    def test_clear_empties_events(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert len(sink) == 1
        sink.clear()
        assert len(sink) == 0

    def test_satisfies_audit_sink_protocol(self) -> None:
        assert isinstance(MemorySink(), AuditSink)

    def test_maxlen_bounds_events(self) -> None:
        sink = MemorySink(maxlen=2)
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        for _ in range(5):
            logger.audit(
                "READ",
                actor={"subject_id": "u1", "subject_type": "human"},
                resource={"type": "Patient"},
            )
        assert len(sink) == 2


class TestLoggingSink:
    def test_emit_produces_log_record(self, caplog: pytest.LogCaptureFixture) -> None:
        sink = LoggingSink(logger_name="bh.audit.test", level="INFO")
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        with caplog.at_level(logging.INFO, logger="bh.audit.test"):
            logger.audit(
                "READ",
                actor={"subject_id": "u1", "subject_type": "human"},
                resource={"type": "Patient"},
            )
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        parsed = json.loads(record.message)
        assert parsed["action"]["type"] == "READ"

    def test_satisfies_audit_sink_protocol(self) -> None:
        assert isinstance(LoggingSink(), AuditSink)


class TestJsonlFileSink:
    def test_write_and_read_back(self, tmp_path: Path) -> None:
        path = tmp_path / "audit.jsonl"
        sink = JsonlFileSink(path=path, flush=True)
        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        logger.audit(
            "CREATE",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Note"},
        )
        sink.close()

        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["action"]["type"] == "READ"
        second = json.loads(lines[1])
        assert second["action"]["type"] == "CREATE"

    def test_satisfies_audit_sink_protocol(self, tmp_path: Path) -> None:
        sink = JsonlFileSink(path=tmp_path / "test.jsonl")
        assert isinstance(sink, AuditSink)
        sink.close()


class TestCustomSink:
    def test_custom_class_satisfies_protocol(self) -> None:
        class MySink:
            def __init__(self) -> None:
                self.events: list[dict[str, Any]] = []

            def emit(self, event: dict[str, Any]) -> None:
                self.events.append(event)

        sink = MySink()
        assert isinstance(sink, AuditSink)

    def test_custom_sink_receives_events(self) -> None:
        received: list[dict[str, Any]] = []

        class CollectorSink:
            def emit(self, event: dict[str, Any]) -> None:
                received.append(event)

        logger = AuditLogger(
            config=AuditLoggerConfig(service_name="test", service_environment="test"),
            sink=CollectorSink(),
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert len(received) == 1
        assert received[0]["service"]["name"] == "test"
