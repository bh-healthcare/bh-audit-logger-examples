"""
Telemetry example.

Demonstrates the opt-in telemetry system:
1. Enabling telemetry via AuditLoggerConfig
2. Emitting events and observing counter accumulation
3. Showing what a telemetry report looks like (no PII/PHI)

Note: This example uses a mock endpoint -- no real HTTP requests are made.

Run:
    python examples/telemetry/main.py
"""

from __future__ import annotations

import json
import tempfile

from bh_audit_logger import AuditLogger, AuditLoggerConfig, MemorySink


def main() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AuditLoggerConfig(
            service_name="telemetry-demo",
            service_environment="demo",
            telemetry_enabled=True,
            telemetry_endpoint="https://example.com/telemetry",
            telemetry_deployment_id_path=tmpdir,
        )
        sink = MemorySink()
        logger = AuditLogger(config=config, sink=sink)

        print("=== Emitting 10 audit events with telemetry enabled ===")
        actions = [
            "READ",
            "READ",
            "CREATE",
            "READ",
            "UPDATE",
            "READ",
            "DELETE",
            "READ",
            "READ",
            "CREATE",
        ]
        for i, action in enumerate(actions):
            logger.audit(
                action,
                actor={"subject_id": f"user-{i % 3}", "subject_type": "human"},
                resource={"type": "Patient", "id": f"patient-{i}"},
                outcome={"status": "SUCCESS"},
            )

        print(f"  Emitted {len(sink.events)} events")
        print(f"  Stats: {logger.stats.snapshot()}")

        print("\n=== Telemetry counter snapshot ===")
        emitter = logger._telemetry
        if emitter is not None:
            counters = emitter.counters
            report = counters.to_report(
                deployment_id="demo-id-12345678",
                service_name="telemetry-demo",
                environment="demo",
                package_version="0.5.0",
            )
            print(json.dumps(report, indent=2))

            print("\n=== Privacy commitment ===")
            print("  The telemetry report contains ONLY aggregate counters:")
            print("  - events_emitted: total count")
            print("  - by_action_type: {READ: N, CREATE: N, ...}")
            print("  - by_outcome: {SUCCESS: N, FAILURE: N, ...}")
            print("  - by_data_classification: {PHI: N, UNKNOWN: N, ...}")
            print("  NO patient IDs, NO user IDs, NO event content, NO IP addresses.")

    print("\nDone.")


if __name__ == "__main__":
    main()
