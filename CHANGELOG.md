# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-04-02

### Added

- **examples/verifier/** — chain verification demonstration: `verify_chain()` with
  intact chain (PASS), tampered event (FAIL), and CLI usage reference.
- **examples/telemetry/** — opt-in telemetry demonstration: counter accumulation,
  report structure, privacy commitment showing no PII/PHI in telemetry payloads.
- **tests/test_verifier_integration.py** — end-to-end LedgerSink -> `verify_chain()`
  -> PASS; tamper event -> FAIL detection.
- **tests/test_telemetry_integration.py** — TelemetryEmitter counter accumulation
  across action types, report structure verification, no PII in report.
- **examples/chain_hashing/** — chain hashing demonstration: `enable_integrity=True`
  with MemorySink, integrity blocks, chain continuity verification, and manual
  hash re-computation.
- **examples/ledger_sink/** — LedgerSink demonstration: JSONL file with built-in
  chain hashing, read-back verification, and tamper detection demo.
- **tests/test_chain_integration.py** — end-to-end chain hashing integration
  tests through AuditLogger with MemorySink, LedgerSink, and DynamoDBSink;
  chain continuity, hash verification, multiple algorithms, custom chain state.
- **tests/test_all_sinks.py** — added LedgerSink write/read-back, chain
  continuity, and protocol conformance tests.
- **examples/dynamodb_sink/** — DynamoDB sink example using moto for local
  demo of compliance query patterns: patient access, actor activity, and
  denial review via three GSIs.
- **tests/test_dynamodb_integration.py** — integration tests for DynamoDBSink
  through AuditLogger with moto: emit + query round-trips, stats tracking,
  failure isolation, protocol conformance, mixed event types.
- **tests/test_all_sinks.py** — added DynamoDBSink protocol and round-trip
  tests (guarded by `importorskip("boto3")`).
- **terraform/** — production-ready Terraform module for the DynamoDB audit
  events table with on-demand billing, encryption at rest, point-in-time
  recovery, TTL, three GSIs, and a minimum-privilege IAM policy.

### Changed

- **README.md** — updated install instructions to include `[all]` extra and
  moto; added `chain_hashing`, `ledger_sink`, and `dynamodb_sink` to examples
  table; added `test_chain_integration` and `test_dynamodb_integration` to
  test modules table.

## [0.1.1] - 2026-04-01

### Fixed

- **test_schema_contract.py** — parametrized `test_schema_structural_compare` so
  each schema version is an independent test case (previously `pytest.skip()` in a
  loop would abort remaining versions)
- **test_examples_runnable.py** — added `test_at_least_one_example_exists` guard to
  prevent silent zero-test-case pass if the examples directory is restructured
- **test_stats_lifecycle.py** — narrowed `importorskip("jsonschema")` to only the
  `TestValidationStats` class; stats baseline, emit counting, and failure counting
  tests no longer skip when jsonschema is absent
- **test_validation_modes.py** — clarified docstring for `test_invalid_pre_built_event_still_dropped_by_minimal`
- **test_all_sinks.py** — made caplog record lookup filter by logger name instead of
  relying on `records[-1]` position
- **test_public_api_smoke.py** — replaced `__dataclass_params__.frozen` CPython
  detail with behavioral `FrozenInstanceError` assertion
- **metadata_and_phi/main.py** — fixed off-by-one assertion bound (`<= 24` → `<= 23`)
- **basic_logging/main.py** — updated docstring to include LOGIN events
- **Makefile** — version-bounded `pytest` and `ruff` installs to match
  pyproject.toml `[dev]` extra

### Added

- **pyproject.toml** — `[build-system]` table (hatchling) for PEP 517/518 compliance
- **schema_validation/main.py** — `standalone_validate_event()` demonstrating
  `validate_event()` (raises `ValidationError` on invalid, distinct from
  `validate_event_schema()` which returns a list)
- **basic_logging/main.py** — `audit_access()` convenience method example
- **test_validation_modes.py** — `test_validate_event_passes_valid` and
  `test_validate_event_raises_on_invalid` covering the `validate_event()` function

### Changed

- Consistent top-level `make_event` imports across all test files (removed local
  imports in `test_backward_compat.py` and `test_stats_lifecycle.py`)

## [0.1.0] - 2026-04-01

### Added

- **examples/basic_logging/** — simplest AuditLogger + LoggingSink usage with
  READ/CREATE/UPDATE/DELETE events, login success/failure
- **examples/file_sink/** — JsonlFileSink writing to a temp file, reading back,
  and verifying output with the context-manager pattern
- **examples/batch_worker/** — realistic ETL/cron job with batch exports,
  correlation IDs, DENIED outcomes, sink failure isolation, and validation
  failure isolation (migrated and expanded from bh-fastapi-examples/worker_audit_example)
- **examples/schema_validation/** — runtime validate_events with both schema
  versions and all three validation_failure_mode values
- **examples/denied_and_downgrade/** — audit_access_denied() under v1.1
  (DENIED preserved) and v1.0 (downgraded to FAILURE), cross-org denial
- **examples/custom_sink/** — implementing the AuditSink protocol with
  PostgresSink and WebhookSink stubs, runtime_checkable verification
- **examples/async_queue/** — EmitQueue for non-blocking event delivery with
  bounded backpressure and graceful shutdown
- **examples/error_handling/** — emit_failure_mode behavior: silent, log, raise
  with broken sink demonstrating failure isolation
- **examples/metadata_and_phi/** — metadata allowlist filtering, error
  sanitization, contains_phi_tokens, redact_tokens, string truncation
- **tests/test_schema_contract.py** — vendored schema structure verification,
  canonical example validation against vendored copies, byte-compare
- **tests/test_backward_compat.py** — v1.0/v1.1 interop, DENIED downgrade,
  cross-org denied, login event validation across versions
- **tests/test_all_sinks.py** — MemorySink, LoggingSink, JsonlFileSink, custom
  sink protocol verification
- **tests/test_validation_modes.py** — drop/log_and_emit/raise behavior matrix,
  standalone validation function tests
- **tests/test_stats_lifecycle.py** — counter correctness for emit, failure,
  drop, and validation timing
- **tests/test_phi_safety_integration.py** — metadata filtering, error
  redaction, PHI token detection through the full emit path
- **tests/test_examples_runnable.py** — smoke test that every example script
  exits cleanly with no tracebacks
- **tests/test_public_api_smoke.py** — all __all__ exports importable, class
  structure, frozen dataclass, runtime_checkable protocol
- **pyproject.toml** — project metadata and dev dependencies
- **Makefile** — install, lint, test, examples, and all targets
- **README.md** — usage instructions, example table, test table, pre-publish
  workflow

[0.2.0]: https://github.com/bh-healthcare/bh-audit-logger-examples/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/bh-healthcare/bh-audit-logger-examples/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/bh-healthcare/bh-audit-logger-examples/releases/tag/v0.1.0
