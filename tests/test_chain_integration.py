"""
End-to-end chain hashing integration tests.

Verifies chain hashing through AuditLogger with multiple sink types,
chain continuity, and integrity block schema compliance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from bh_audit_logger import (
    AuditLogger,
    AuditLoggerConfig,
    ChainState,
    LedgerSink,
    MemorySink,
    compute_chain_hash,
)


class TestChainHashingWithMemorySink:
    """Chain hashing end-to-end through MemorySink."""

    @pytest.fixture
    def logger_and_sink(self) -> tuple[AuditLogger, MemorySink]:
        sink = MemorySink()
        config = AuditLoggerConfig(
            service_name="integration-test",
            service_environment="test",
            enable_integrity=True,
        )
        return AuditLogger(config, sink=sink), sink

    def test_all_events_have_integrity(
        self, logger_and_sink: tuple[AuditLogger, MemorySink]
    ) -> None:
        logger, sink = logger_and_sink
        for i in range(3):
            logger.audit(
                "READ",
                actor={"subject_id": f"user_{i}", "subject_type": "human"},
                resource={"type": "Patient"},
            )
        for evt in sink.events:
            assert "integrity" in evt
            assert "event_hash" in evt["integrity"]
            assert evt["integrity"]["hash_alg"] == "sha256"

    def test_chain_continuity(self, logger_and_sink: tuple[AuditLogger, MemorySink]) -> None:
        logger, sink = logger_and_sink
        for _i in range(5):
            logger.audit(
                "READ",
                actor={"subject_id": "u1", "subject_type": "human"},
                resource={"type": "Patient"},
            )
        events = sink.events
        assert "prev_event_hash" not in events[0]["integrity"]
        for i in range(1, len(events)):
            assert (
                events[i]["integrity"]["prev_event_hash"]
                == events[i - 1]["integrity"]["event_hash"]
            )

    def test_hashes_verify(self, logger_and_sink: tuple[AuditLogger, MemorySink]) -> None:
        logger, sink = logger_and_sink
        for _ in range(3):
            logger.audit(
                "CREATE",
                actor={"subject_id": "u1", "subject_type": "human"},
                resource={"type": "Note"},
            )
        prev_hash = None
        for evt in sink.events:
            recomputed = compute_chain_hash(evt, prev_hash, "sha256")
            assert recomputed["event_hash"] == evt["integrity"]["event_hash"]
            prev_hash = evt["integrity"]["event_hash"]

    def test_integrity_block_schema_compliant(
        self, logger_and_sink: tuple[AuditLogger, MemorySink]
    ) -> None:
        logger, sink = logger_and_sink
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        integrity = sink.events[0]["integrity"]
        assert set(integrity.keys()) <= {"event_hash", "prev_event_hash", "hash_alg"}
        assert isinstance(integrity["event_hash"], str)
        assert len(integrity["event_hash"]) == 64

    def test_custom_chain_state_resume(self) -> None:
        cs = ChainState(initial_hash="seed_from_previous_run")
        sink = MemorySink()
        logger = AuditLogger(
            AuditLoggerConfig(
                service_name="svc", service_environment="test", enable_integrity=True
            ),
            sink=sink,
            chain_state=cs,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert sink.events[0]["integrity"]["prev_event_hash"] == "seed_from_previous_run"


class TestChainHashingWithLedgerSink:
    """Chain hashing through LedgerSink (file + built-in integrity)."""

    def test_ledger_writes_integrity(self, tmp_path: Path) -> None:
        path = tmp_path / "audit.jsonl"
        config = AuditLoggerConfig(service_name="svc", service_environment="test")
        with LedgerSink(path) as sink:
            logger = AuditLogger(config, sink=sink)
            for i in range(3):
                logger.audit(
                    "READ",
                    actor={"subject_id": f"u{i}", "subject_type": "human"},
                    resource={"type": "Patient"},
                )

        lines = path.read_text().strip().splitlines()
        events = [json.loads(line) for line in lines]
        for evt in events:
            assert "integrity" in evt

    def test_ledger_chain_verifiable(self, tmp_path: Path) -> None:
        path = tmp_path / "audit.jsonl"
        with LedgerSink(path) as sink:
            config = AuditLoggerConfig(service_name="svc", service_environment="test")
            logger = AuditLogger(config, sink=sink)
            for _i in range(5):
                logger.audit(
                    "READ",
                    actor={"subject_id": "u1", "subject_type": "human"},
                    resource={"type": "Patient"},
                )

        events = [json.loads(line) for line in path.read_text().strip().splitlines()]
        prev_hash = None
        for evt in events:
            recomputed = compute_chain_hash(evt, prev_hash, "sha256")
            assert recomputed["event_hash"] == evt["integrity"]["event_hash"]
            prev_hash = evt["integrity"]["event_hash"]


class TestChainHashingWithDynamoDBSink:
    """Chain hashing through DynamoDBSink (moto-backed)."""

    @pytest.fixture
    def _aws_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
        monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")

    def test_integrity_fields_stored_in_dynamo(self, _aws_env: None) -> None:
        pytest.importorskip("boto3")
        import boto3
        from bh_audit_logger.sinks.dynamodb import DynamoDBSink
        from moto import mock_aws

        with mock_aws():
            sink = DynamoDBSink(
                table_name="test_chain",
                region="us-east-1",
                create_table=True,
            )
            config = AuditLoggerConfig(
                service_name="test",
                service_environment="test",
                enable_integrity=True,
            )
            logger = AuditLogger(config, sink=sink)
            logger.audit(
                "READ",
                actor={"subject_id": "u1", "subject_type": "human"},
                resource={"type": "Patient", "patient_id": "pat_1"},
            )

            client = boto3.client("dynamodb", region_name="us-east-1")
            resp = client.scan(TableName="test_chain")
            item = resp["Items"][0]
            assert "chain_hash" in item
            assert item["chain_hash"]["S"] != ""


class TestIntegrityDisabledByDefault:
    """Sanity check: integrity is not added when not enabled."""

    def test_no_integrity_block(self) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            AuditLoggerConfig(service_name="svc", service_environment="test"),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert "integrity" not in sink.events[0]


class TestMultipleAlgorithms:
    """Verify different hash algorithms work end-to-end."""

    @pytest.mark.parametrize("algo,hex_len", [("sha256", 64), ("sha384", 96), ("sha512", 128)])
    def test_algorithm_produces_correct_length(self, algo: str, hex_len: int) -> None:
        sink = MemorySink()
        logger = AuditLogger(
            AuditLoggerConfig(
                service_name="svc",
                service_environment="test",
                enable_integrity=True,
                hash_algorithm=algo,
            ),
            sink=sink,
        )
        logger.audit(
            "READ",
            actor={"subject_id": "u1", "subject_type": "human"},
            resource={"type": "Patient"},
        )
        assert len(sink.events[0]["integrity"]["event_hash"]) == hex_len
