# bh-audit-logger-examples

Examples and integration tests for **bh-audit-logger** (v0.4.0) — a pre-publish verification suite for schema vendoring, backward compatibility, and every public API surface.

All examples are **framework-agnostic**. No web framework is required.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate

# Install bh-audit-logger from local checkout (with jsonschema extra)
pip install -e "../bh-audit-logger[jsonschema]"
pip install pytest ruff

# Run everything
make all
```

## Examples

Each example is a standalone script that prints output and exits cleanly.

| Example | What it demonstrates |
|---|---|
| `basic_logging/` | Simplest usage: `AuditLogger` + `LoggingSink` with READ/CREATE/UPDATE/DELETE events |
| `file_sink/` | `JsonlFileSink` writing to a file, reading back, and verifying output |
| `schema_validation/` | Runtime `validate_events=True` with both schema versions and all failure modes |
| `denied_and_downgrade/` | `audit_access_denied()` under v1.1 (DENIED) and v1.0 (downgraded to FAILURE) |
| `custom_sink/` | Implementing the `AuditSink` protocol with custom backends |
| `async_queue/` | `EmitQueue` for non-blocking event delivery with bounded backpressure |
| `error_handling/` | `emit_failure_mode` behavior: silent, log, and raise |
| `metadata_and_phi/` | Metadata allowlists, error sanitization, PHI token detection and redaction |
| `batch_worker/` | Realistic ETL/cron job: batch exports, correlation IDs, DENIED outcomes, sink failures |

**Run a single example:**

```bash
python examples/basic_logging/main.py
```

**Run all examples:**

```bash
make examples
```

## Tests

Integration tests verify bh-audit-logger from an external consumer's perspective.

| Test module | Focus |
|---|---|
| `test_schema_contract.py` | Vendored schemas match bh-audit-schema; canonical examples validate |
| `test_backward_compat.py` | v1.0/v1.1 interop; DENIED downgrade path |
| `test_all_sinks.py` | Every sink type works: Memory, Logging, JSONL, custom |
| `test_validation_modes.py` | drop / log_and_emit / raise behavior matrix |
| `test_stats_lifecycle.py` | Counter correctness across emit, failure, and validation paths |
| `test_phi_safety_integration.py` | Metadata filtering, error redaction, PHI token detection |
| `test_examples_runnable.py` | Every example script exits with code 0 and no tracebacks |
| `test_public_api_smoke.py` | All `__all__` exports importable, class structure correct |

**Run tests:**

```bash
make test
```

## Pre-publish workflow

When bumping `bh-audit-logger` or `bh-audit-schema`:

1. Make changes in the source package
2. Run that package's own test suite
3. `cd bh-audit-logger-examples && make all`
4. If green, tag and publish

## What this catches

- Vendored schemas drifting from canonical bh-audit-schema
- Backward compatibility regressions between schema v1.0 and v1.1
- Broken public API surface (missing exports, changed signatures)
- PHI safety regressions (metadata leaks, unsanitized errors)
- Example scripts that no longer run cleanly after library changes

## Related projects

- [bh-audit-logger](https://github.com/bh-healthcare/bh-audit-logger) — Cloud-agnostic audit logger
- [bh-audit-schema](https://github.com/bh-healthcare/bh-audit-schema) — The audit event schema standard
- [bh-fastapi-audit](https://github.com/bh-healthcare/bh-fastapi-audit) — FastAPI audit middleware
- [bh-fastapi-examples](https://github.com/bh-healthcare/bh-fastapi-examples) — FastAPI middleware examples

## License

Apache 2.0
