# Terraform: bh-audit-logger DynamoDB Table

Production-ready Terraform module for the `bh_audit_events` DynamoDB table used by `DynamoDBSink`.

## What it creates

- **DynamoDB table** (`bh_audit_events`) with on-demand billing, encryption at rest, point-in-time recovery, and TTL
- **Three GSIs** for HIPAA compliance queries: patient access, actor activity, access denials
- **IAM policy** with minimum permissions (`PutItem`, `Query`, `DescribeTable`)

## Quick start

```bash
cd terraform/

# Initialize Terraform
terraform init

# Preview changes
terraform plan -var="environment=prod"

# Apply
terraform apply -var="environment=prod"
```

## Variables

| Variable | Default | Description |
|---|---|---|
| `table_name` | `bh_audit_events` | DynamoDB table name |
| `environment` | `dev` | Deployment environment tag |
| `ttl_attribute` | `ttl` | TTL attribute name (empty string disables) |
| `point_in_time_recovery` | `true` | Enable PITR backups |
| `tags` | `{}` | Additional resource tags |

## Outputs

| Output | Description |
|---|---|
| `table_name` | Created table name |
| `table_arn` | Table ARN (for cross-referencing in other modules) |
| `iam_policy_arn` | IAM policy ARN to attach to your service role |
| `python_sink_config` | Copy-pasteable Python snippet for `DynamoDBSink` |

## Connecting to your service

After `terraform apply`:

1. Attach the IAM policy to your ECS task role / Lambda execution role / EC2 instance profile
2. Configure your Python service:

```python
from bh_audit_logger import AuditLogger, AuditLoggerConfig
from bh_audit_logger.sinks.dynamodb import DynamoDBSink

sink = DynamoDBSink(
    table_name="bh_audit_events",   # or from env: os.environ["BH_AUDIT_TABLE"]
    region="us-east-1",             # or from env: os.environ["AWS_REGION"]
)

logger = AuditLogger(
    config=AuditLoggerConfig(service_name="my-service", service_environment="prod"),
    sink=sink,
)
```

## Cost estimate

For a typical BH Healthcare deployment (100-500 patients):

| Metric | Estimate |
|---|---|
| Daily events | 500 - 2,000 |
| Daily storage | ~1 - 3 MB |
| Monthly storage at 6-year retention | ~$1.50/month |
| Write cost | Well under free tier |
| Read cost (compliance queries) | Negligible |

See the [design document](../../bh-fastapi-audit-v05-design.md) for full capacity planning details.
