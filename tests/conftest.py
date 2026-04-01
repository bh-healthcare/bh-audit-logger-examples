"""
Shared fixtures for bh-audit-logger-examples integration tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def schema_repo_path() -> Path:
    """Path to the sibling bh-audit-schema repository.

    Skips the test if the sibling repo is not present (e.g. in CI
    that only checks out this repo).
    """
    path = Path(__file__).resolve().parent.parent.parent / "bh-audit-schema"
    if not path.is_dir():
        pytest.skip("bh-audit-schema sibling repo not found")
    return path


def make_event(**overrides: Any) -> dict[str, Any]:
    """Return a minimal valid v1.1 event dict with optional overrides."""
    event: dict[str, Any] = {
        "schema_version": "1.1",
        "event_id": "12345678-1234-5678-1234-567812345678",
        "timestamp": "2026-04-01T12:00:00.000Z",
        "service": {"name": "test-service", "environment": "test"},
        "actor": {"subject_id": "test-user", "subject_type": "human"},
        "action": {"type": "READ", "data_classification": "UNKNOWN"},
        "resource": {"type": "TestResource"},
        "outcome": {"status": "SUCCESS"},
    }
    event.update(overrides)
    return event
