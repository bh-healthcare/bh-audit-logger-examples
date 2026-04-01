"""
Schema vendoring verification.

Confirms that the schemas vendored inside bh-audit-logger match the
canonical bh-audit-schema, and that every official example validates
against the vendored copy.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("jsonschema", reason="jsonschema required for schema contract tests")

from bh_audit_logger import validate_event_schema
from bh_audit_logger.schema import SCHEMA_VERSION, load_schema

# ------------------------------------------------------------------
# Vendored schema structure
# ------------------------------------------------------------------


class TestVendoredSchemaStructure:
    def test_load_schema_1_0(self) -> None:
        schema = load_schema("1.0")
        assert schema["properties"]["schema_version"]["const"] == "1.0"

    def test_load_schema_1_1(self) -> None:
        schema = load_schema("1.1")
        assert schema["properties"]["schema_version"]["const"] == "1.1"

    def test_schema_version_constant_is_latest(self) -> None:
        assert SCHEMA_VERSION == "1.1"

    def test_root_schema_matches_latest(self) -> None:
        root = load_schema()
        explicit = load_schema("1.1")
        assert root == explicit

    def test_both_schemas_have_required_top_level_fields(self) -> None:
        expected = {
            "schema_version",
            "event_id",
            "timestamp",
            "service",
            "actor",
            "action",
            "resource",
            "outcome",
        }
        for ver in ("1.0", "1.1"):
            schema = load_schema(ver)
            assert set(schema["required"]) == expected, f"v{ver} required fields mismatch"

    def test_1_1_has_denied_status(self) -> None:
        schema = load_schema("1.1")
        statuses = schema["properties"]["outcome"]["properties"]["status"]["enum"]
        assert "DENIED" in statuses

    def test_1_0_has_no_denied_status(self) -> None:
        schema = load_schema("1.0")
        statuses = schema["properties"]["outcome"]["properties"]["status"]["enum"]
        assert "DENIED" not in statuses

    def test_1_1_has_conditional_failure_requirements(self) -> None:
        schema = load_schema("1.1")
        assert "allOf" in schema, "v1.1 should have allOf conditional rules"


# ------------------------------------------------------------------
# Cross-repo example validation
# ------------------------------------------------------------------


class TestCanonicalExamplesValidateAgainstVendored:
    """Validate bh-audit-schema example JSONs against vendored schemas.

    This is the key cross-package contract test: if the vendored schema
    in bh-audit-logger doesn't match the canonical schema in bh-audit-schema,
    these tests will fail.
    """

    @staticmethod
    def _collect_examples(schema_repo: Path) -> list[tuple[str, Path]]:
        examples_dir = schema_repo / "examples"
        if not examples_dir.is_dir():
            return []
        pairs = []
        for version_dir in sorted(examples_dir.iterdir()):
            if not version_dir.is_dir():
                continue
            ver = version_dir.name
            for json_file in sorted(version_dir.glob("*.json")):
                pairs.append((ver, json_file))
        return pairs

    def test_all_canonical_examples_validate(self, schema_repo_path: Path) -> None:
        pairs = self._collect_examples(schema_repo_path)
        assert len(pairs) > 0, "No example files found in bh-audit-schema/examples/"

        failures = []
        for ver, json_file in pairs:
            with open(json_file) as f:
                event = json.load(f)
            errors = validate_event_schema(event, ver)
            if errors:
                failures.append(f"{ver}/{json_file.name}: {errors}")

        assert not failures, "Canonical examples failed vendored validation:\n" + "\n".join(
            failures
        )

    def test_schema_structural_compare(self, schema_repo_path: Path) -> None:
        """Vendored schemas should be structurally identical to canonical copies."""
        for ver in ("1.0", "1.1"):
            canonical = schema_repo_path / "schema" / "versions" / ver / "audit_event.schema.json"
            if not canonical.exists():
                pytest.skip(f"Canonical schema v{ver} not found")
            vendored = load_schema(ver)
            with open(canonical) as f:
                canonical_data = json.load(f)
            assert vendored == canonical_data, (
                f"Vendored v{ver} schema does not match canonical copy"
            )
