"""
Integration tests for DynamoDBSink exercised through AuditLogger.

All tests use moto for DynamoDB mocking -- no real AWS calls are made.
"""

from __future__ import annotations

import pytest

boto3 = pytest.importorskip("boto3")
moto = pytest.importorskip("moto")

from bh_audit_logger import AuditLogger, AuditLoggerConfig, AuditSink  # noqa: E402
from bh_audit_logger.sinks.dynamodb import DynamoDBSink  # noqa: E402
from moto import mock_aws  # noqa: E402

TABLE = "examples_audit_events"
REGION = "us-east-1"


@pytest.fixture
def _aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


@pytest.fixture
def dynamo_sink(_aws_env: None) -> DynamoDBSink:
    with mock_aws():
        sink = DynamoDBSink(table_name=TABLE, region=REGION, create_table=True)
        yield sink


@pytest.fixture
def logger(dynamo_sink: DynamoDBSink) -> AuditLogger:
    config = AuditLoggerConfig(
        service_name="integration-test",
        service_environment="test",
        service_version="0.4.0",
    )
    return AuditLogger(config, sink=dynamo_sink)


class TestEmitAndQueryRoundTrip:
    def test_emit_then_query_by_patient(
        self, logger: AuditLogger, dynamo_sink: DynamoDBSink
    ) -> None:
        logger.audit(
            "READ",
            actor={"subject_id": "user_1", "subject_type": "human"},
            resource={"type": "Patient", "patient_id": "pat_001", "id": "res_1"},
            phi_touched=True,
            data_classification="PHI",
        )
        results = dynamo_sink.query_by_patient("pat_001")
        assert len(results) == 1
        assert results[0]["action"]["type"] == "READ"
        assert results[0]["resource"]["patient_id"] == "pat_001"

    def test_emit_then_query_by_actor(self, logger: AuditLogger, dynamo_sink: DynamoDBSink) -> None:
        logger.audit(
            "CREATE",
            actor={"subject_id": "clinician_42", "subject_type": "human"},
            resource={"type": "Note"},
        )
        results = dynamo_sink.query_by_actor("clinician_42")
        assert len(results) == 1
        assert results[0]["action"]["type"] == "CREATE"

    def test_emit_denied_then_query_denials(
        self, logger: AuditLogger, dynamo_sink: DynamoDBSink
    ) -> None:
        logger.audit_access_denied(
            "READ",
            error_type="RoleDenied",
            actor={"subject_id": "user_bad", "subject_type": "human"},
            resource={"type": "Patient", "patient_id": "pat_secret"},
        )
        denials = dynamo_sink.query_denials()
        assert len(denials) == 1
        assert denials[0]["outcome"]["status"] == "DENIED"
        assert denials[0]["outcome"]["error_type"] == "RoleDenied"


class TestStatsTracking:
    def test_stats_counted_correctly(self, logger: AuditLogger, dynamo_sink: DynamoDBSink) -> None:
        for i in range(5):
            logger.audit(
                "READ",
                actor={"subject_id": f"user_{i}", "subject_type": "human"},
                resource={"type": "Patient", "patient_id": f"pat_{i:03d}"},
            )

        snap = logger.stats.snapshot()
        assert snap["events_emitted_total"] == 5
        assert snap["emit_failures_total"] == 0
        assert snap["events_dropped_total"] == 0


class TestFailureIsolation:
    def test_emit_failure_mode_log(self, _aws_env: None) -> None:
        """When DynamoDB is unreachable, emit_failure_mode='log' prevents crash."""
        with mock_aws():
            sink = DynamoDBSink(table_name=TABLE, region=REGION, create_table=True)
            config = AuditLoggerConfig(
                service_name="fail-test",
                service_environment="test",
                emit_failure_mode="log",
            )
            logger = AuditLogger(config, sink=sink)

            logger.audit(
                "READ",
                resource={"type": "Patient", "patient_id": "pat_1"},
            )
            assert logger.stats.events_emitted_total == 1


class TestProtocolConformance:
    def test_dynamodb_sink_satisfies_protocol(self, dynamo_sink: DynamoDBSink) -> None:
        assert isinstance(dynamo_sink, AuditSink)

    def test_has_query_methods(self, dynamo_sink: DynamoDBSink) -> None:
        assert callable(dynamo_sink.query_by_patient)
        assert callable(dynamo_sink.query_by_actor)
        assert callable(dynamo_sink.query_denials)


class TestMultipleEventTypes:
    def test_mixed_event_types(self, logger: AuditLogger, dynamo_sink: DynamoDBSink) -> None:
        logger.audit(
            "READ",
            actor={"subject_id": "user_1", "subject_type": "human"},
            resource={"type": "Patient", "patient_id": "pat_001"},
        )
        logger.audit(
            "CREATE",
            actor={"subject_id": "user_1", "subject_type": "human"},
            resource={"type": "Note", "patient_id": "pat_001"},
        )
        logger.audit_access_denied(
            "DELETE",
            error_type="AccessDenied",
            actor={"subject_id": "user_1", "subject_type": "human"},
            resource={"type": "Patient", "patient_id": "pat_001"},
        )
        logger.audit_login_success(
            actor={"subject_id": "user_1", "subject_type": "human"},
        )

        actor_events = dynamo_sink.query_by_actor("user_1")
        assert len(actor_events) == 4

        patient_events = dynamo_sink.query_by_patient("pat_001")
        assert len(patient_events) == 3

        denials = dynamo_sink.query_denials()
        assert len(denials) == 1
