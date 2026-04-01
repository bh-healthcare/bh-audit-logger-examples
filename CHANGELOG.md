# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
- **.github/workflows/ci.yml** — CI pipeline with lint, test, and example runs
- **README.md** — usage instructions, example table, test table, pre-publish
  workflow

[0.1.0]: https://github.com/bh-healthcare/bh-audit-logger-examples/releases/tag/v0.1.0
