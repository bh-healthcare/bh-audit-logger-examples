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
        audit_records = [r for r in caplog.records if r.name == "bh.audit.test"]
        assert len(audit_records) >= 1
        parsed = json.loads(audit_records[-1].message)
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


class TestDynamoDBSink:
    @pytest.fixture
    def _aws_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
        monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    @pytest.mark.skipif(
        not pytest.importorskip("boto3", reason="boto3 not installed"),
        reason="boto3 required",
    )
    def test_satisfies_audit_sink_protocol(self, _aws_env: None) -> None:
        from bh_audit_logger.sinks.dynamodb import DynamoDBSink
        from moto import mock_aws

        with mock_aws():
            sink = DynamoDBSink(
                table_name="test_sinks",
                region="us-east-1",
                create_table=True,
            )
            assert isinstance(sink, AuditSink)

    @pytest.mark.skipif(
        not pytest.importorskip("boto3", reason="boto3 not installed"),
        reason="boto3 required",
    )
    def test_emit_and_query(self, _aws_env: None) -> None:
        from bh_audit_logger.sinks.dynamodb import DynamoDBSink
        from moto import mock_aws

        with mock_aws():
            sink = DynamoDBSink(
                table_name="test_sinks",
                region="us-east-1",
                create_table=True,
            )
            logger = AuditLogger(
                config=AuditLoggerConfig(service_name="test", service_environment="test"),
                sink=sink,
            )
            logger.audit(
                "READ",
                actor={"subject_id": "u1", "subject_type": "human"},
                resource={"type": "Patient", "patient_id": "pat_1"},
            )
            results = sink.query_by_patient("pat_1")
            assert len(results) == 1


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
