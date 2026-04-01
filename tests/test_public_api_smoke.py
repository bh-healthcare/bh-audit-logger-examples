"""
Public API smoke tests.

Verifies that bh-audit-logger's public surface is importable and
structurally correct from an external consumer's perspective.
"""

from __future__ import annotations

import dataclasses

import bh_audit_logger
from bh_audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    AuditSink,
    AuditStats,
    EmitQueue,
    JsonlFileSink,
    LoggingSink,
    MemorySink,
)
from bh_audit_logger.schema import SCHEMA_VERSION


class TestVersionAndExports:
    def test_version_is_string(self) -> None:
        assert isinstance(bh_audit_logger.__version__, str)
        assert len(bh_audit_logger.__version__) > 0

    def test_all_exports_importable(self) -> None:
        for name in bh_audit_logger.__all__:
            obj = getattr(bh_audit_logger, name)
            assert obj is not None, f"{name} resolved to None"

    def test_schema_version_constant(self) -> None:
        assert SCHEMA_VERSION == "1.1"


class TestClassStructure:
    def test_audit_logger_config_is_frozen_dataclass(self) -> None:
        assert dataclasses.is_dataclass(AuditLoggerConfig)
        assert AuditLoggerConfig.__dataclass_params__.frozen  # type: ignore[attr-defined]

    def test_audit_sink_is_runtime_checkable(self) -> None:
        class _TestSink:
            def emit(self, event: dict) -> None:
                pass

        assert isinstance(_TestSink(), AuditSink), "AuditSink should be runtime_checkable"

    def test_audit_logger_has_public_methods(self) -> None:
        expected = {
            "emit",
            "audit",
            "audit_login_success",
            "audit_login_failure",
            "audit_access",
            "audit_access_denied",
        }
        actual = {m for m in dir(AuditLogger) if not m.startswith("_")}
        missing = expected - actual
        assert not missing, f"AuditLogger missing methods: {missing}"

    def test_audit_logger_has_properties(self) -> None:
        expected = {"config", "sink", "stats"}
        actual = {m for m in dir(AuditLogger) if not m.startswith("_")}
        assert expected.issubset(actual)

    def test_memory_sink_has_events_and_clear(self) -> None:
        sink = MemorySink()
        assert hasattr(sink, "events")
        assert hasattr(sink, "clear")
        assert callable(sink.clear)

    def test_logging_sink_has_emit(self) -> None:
        sink = LoggingSink()
        assert callable(sink.emit)

    def test_jsonl_file_sink_has_close(self) -> None:
        assert hasattr(JsonlFileSink, "close")

    def test_emit_queue_has_public_api(self) -> None:
        expected = {"start", "enqueue", "shutdown", "pending"}
        actual = {m for m in dir(EmitQueue) if not m.startswith("_")}
        assert expected.issubset(actual)

    def test_audit_stats_has_snapshot(self) -> None:
        stats = AuditStats()
        snap = stats.snapshot()
        assert isinstance(snap, dict)
