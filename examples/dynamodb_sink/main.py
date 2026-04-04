"""
DynamoDB sink with compliance query patterns.

Demonstrates writing audit events to DynamoDB (mocked via moto) and
querying by patient, actor, and denied outcomes -- the three GSI patterns
needed for HIPAA compliance reviews.

Requires:
    pip install bh-audit-logger[dynamodb] "moto[dynamodb]>=5.0,<6"

Run:
    python examples/dynamodb_sink/main.py
"""

from __future__ import annotations

import json
import os

from bh_audit_logger import AuditLogger, AuditLoggerConfig
from bh_audit_logger.sinks.dynamodb import DynamoDBSink
from moto import mock_aws

TABLE = "demo_audit_events"
REGION = "us-east-1"


def main() -> None:
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
    os.environ.setdefault("AWS_DEFAULT_REGION", REGION)

    with mock_aws():
        print("=== DynamoDB sink example (moto-backed) ===\n")

        sink = DynamoDBSink(
            table_name=TABLE,
            region=REGION,
            ttl_days=2190,
            create_table=True,
        )

        config = AuditLoggerConfig(
            service_name="intake-api",
            service_environment="dev",
            service_version="1.0.0",
        )
        logger = AuditLogger(config, sink=sink)

        # --- Emit a mix of events ---

        logger.audit(
            "READ",
            actor={"subject_id": "clinician_01", "subject_type": "human"},
            resource={"type": "Patient", "id": "res_1", "patient_id": "pat_100"},
            phi_touched=True,
            data_classification="PHI",
        )

        logger.audit(
            "CREATE",
            actor={"subject_id": "clinician_01", "subject_type": "human"},
            resource={"type": "Note", "id": "note_42", "patient_id": "pat_100"},
            data_classification="PHI",
        )

        logger.audit(
            "READ",
            actor={"subject_id": "clinician_02", "subject_type": "human"},
            resource={"type": "Patient", "id": "res_2", "patient_id": "pat_200"},
            phi_touched=True,
            data_classification="PHI",
        )

        logger.audit_access_denied(
            "READ",
            error_type="CrossOrgAccessDenied",
            actor={"subject_id": "clinician_03", "subject_type": "human"},
            resource={"type": "Patient", "id": "res_3", "patient_id": "pat_100"},
            data_classification="PHI",
        )

        print(f"Emitted {logger.stats.events_emitted_total} events")
        print(f"Stats: {logger.stats.snapshot()}\n")

        # --- Query by patient ---

        print("--- Query: all access to patient pat_100 ---")
        patient_events = sink.query_by_patient("pat_100")
        print(f"Found {len(patient_events)} events for pat_100")
        for evt in patient_events:
            print(
                f"  {evt['action']['type']:8s} by {evt['actor']['subject_id']}"
                f"  -> {evt['outcome']['status']}"
            )

        # --- Query by actor ---

        print("\n--- Query: all actions by clinician_01 ---")
        actor_events = sink.query_by_actor("clinician_01")
        print(f"Found {len(actor_events)} events for clinician_01")
        for evt in actor_events:
            print(
                f"  {evt['action']['type']:8s} on {evt['resource']['type']}"
                f"  -> {evt['outcome']['status']}"
            )

        # --- Query denials ---

        print("\n--- Query: all DENIED outcomes ---")
        denied = sink.query_denials()
        print(f"Found {len(denied)} denied events")
        for evt in denied:
            print(
                f"  {evt['action']['type']:8s} by {evt['actor']['subject_id']}"
                f"  error_type={evt['outcome'].get('error_type', 'N/A')}"
            )

        # --- Show a full stored event ---

        print("\n--- First patient event (pretty-printed) ---")
        if patient_events:
            print(json.dumps(patient_events[0], indent=2))

        print("\nDone.")


if __name__ == "__main__":
    main()
