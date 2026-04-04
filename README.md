# bh-audit-logger-examples

Examples and integration tests for **bh-audit-logger** (v0.5.0) — a pre-publish verification suite for schema vendoring, backward compatibility, and every public API surface.

All examples are **framework-agnostic**. No web framework is required.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate

# Install bh-audit-logger from local checkout (with all optional extras including CLI)
pip install -e "../bh-audit-logger[all,cli]"
pip install "pytest>=7.0.0,<9" "ruff>=0.1.0,<1" "moto[dynamodb]>=5.0,<6"

# Run everything
make all
```

## Examples

Each example is a standalone script that prints output and exits cleanly.

| Example | What it demonstrates |
|---|---|
| `basic_logging/` | Simplest usage: `AuditLogger` + `LoggingSink` with CRUD, LOGIN, and `audit_access()` |
| `file_sink/` | `JsonlFileSink` writing to a file, reading back, and verifying output |
| `schema_validation/` | Runtime `validate_events=True`, all failure modes, and standalone `validate_event()` |
| `denied_and_downgrade/` | `audit_access_denied()` under v1.1 (DENIED) and v1.0 (downgraded to FAILURE) |
| `custom_sink/` | Implementing the `AuditSink` protocol with custom backends |
| `async_queue/` | `EmitQueue` for non-blocking event delivery with bounded backpressure |
| `error_handling/` | `emit_failure_mode` behavior: silent, log, and raise |
| `metadata_and_phi/` | Metadata allowlists, error sanitization, PHI token detection and redaction |
| `batch_worker/` | Realistic ETL/cron job: batch exports, correlation IDs, DENIED outcomes, sink failures |
| `dynamodb_sink/` | DynamoDB sink with compliance query patterns: patient access, actor activity, denial review (moto-backed) |
| `chain_hashing/` | `enable_integrity=True` with MemorySink — integrity blocks, chain continuity, manual hash verification |
| `ledger_sink/` | `LedgerSink` writing tamper-evident JSONL, read-back verification, and tamper detection demo |
| `verifier/` | `verify_chain()` programmatic verification: intact chain PASS, tampered event FAIL, CLI usage reference |
| `telemetry/` | Opt-in telemetry: counter accumulation, report structure, privacy commitment (no PII/PHI) |

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
| `test_dynamodb_integration.py` | DynamoDB sink emit + query round-trips, stats tracking, failure isolation (moto-backed) |
| `test_chain_integration.py` | End-to-end chain hashing through AuditLogger with MemorySink, LedgerSink, and DynamoDBSink |
| `test_public_api_smoke.py` | All `__all__` exports importable, class structure correct |
| `test_verifier_integration.py` | End-to-end LedgerSink -> `verify_chain()` -> PASS; tamper -> FAIL |
| `test_telemetry_integration.py` | TelemetryEmitter counter accumulation, report structure, no PII |

**Run tests:**

```bash
make test
```

## Terraform (production deployment)

The `terraform/` directory contains a ready-to-use Terraform module for creating the DynamoDB audit events table in AWS with production defaults:

- On-demand billing (`PAY_PER_REQUEST`)
- Encryption at rest (AWS-managed key)
- Point-in-time recovery (35-day continuous backups)
- TTL enabled on the `ttl` attribute
- Three GSIs for HIPAA compliance queries
- Minimum-privilege IAM policy

```bash
cd terraform/
terraform init
terraform plan -var="environment=prod"
terraform apply -var="environment=prod"
```

See [`terraform/README.md`](terraform/README.md) for full variable and output reference, and [`bh-audit-logger/docs/deploying-dynamodb.md`](../bh-audit-logger/docs/deploying-dynamodb.md) for the complete deployment guide.

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
