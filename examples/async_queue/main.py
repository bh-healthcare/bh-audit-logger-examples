"""
EmitQueue for async / non-blocking audit event delivery.

Demonstrates the bounded async queue that decouples event building from
sink I/O, including queue overflow behavior and graceful shutdown.

Run:
    python examples/async_queue/main.py
"""

from __future__ import annotations

import asyncio

from bh_audit_logger import AuditStats, EmitQueue, MemorySink


def _make_event(n: int) -> dict:
    """Build a minimal valid audit event dict for testing."""
    return {
        "schema_version": "1.1",
        "event_id": f"00000000-0000-0000-0000-{n:012d}",
        "timestamp": "2026-04-01T12:00:00.000Z",
        "service": {"name": "example-async", "environment": "dev"},
        "actor": {"subject_id": "svc_worker", "subject_type": "service"},
        "action": {"type": "READ", "data_classification": "UNKNOWN"},
        "resource": {"type": "Patient"},
        "outcome": {"status": "SUCCESS"},
    }


async def normal_queue_usage() -> None:
    """Standard pattern: enqueue events, drain, shut down."""
    sink = MemorySink()
    stats = AuditStats()
    queue = EmitQueue(sink, stats, maxsize=100)

    queue.start()

    for i in range(5):
        ok = queue.enqueue(_make_event(i))
        assert ok, f"Failed to enqueue event {i}"

    await queue.shutdown(timeout=5.0)

    snap = stats.snapshot()
    emitted = snap["events_emitted_total"]
    dropped = snap["events_dropped_total"]
    print(f"  Enqueued 5, emitted {emitted}, dropped {dropped}")
    print(f"  Sink received {len(sink)} events")


async def queue_overflow() -> None:
    """Show what happens when the queue is full."""
    sink = MemorySink()
    stats = AuditStats()
    queue = EmitQueue(sink, stats, maxsize=2)

    for i in range(5):
        queue.enqueue(_make_event(i))

    await queue.shutdown(timeout=5.0)

    snap = stats.snapshot()
    print("  Tried to enqueue 5 into maxsize=2 queue")
    print(f"  emitted={snap['events_emitted_total']}, dropped={snap['events_dropped_total']}")


async def main() -> None:
    print("=== Async EmitQueue examples ===\n")

    print("Normal queue usage:")
    await normal_queue_usage()

    print("\nQueue overflow (bounded backpressure):")
    await queue_overflow()

    print("\nAll async queue examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
