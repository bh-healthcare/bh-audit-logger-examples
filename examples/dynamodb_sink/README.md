# DynamoDB Sink Example

Demonstrates `DynamoDBSink` with the three GSI compliance query patterns:
patient access history, actor activity review, and access denial monitoring.

## Quick demo (moto)

No Docker or AWS credentials required -- runs entirely in-process:

```bash
python examples/dynamodb_sink/main.py
```

## DynamoDB Local (realistic dev)

Uses a real DynamoDB-compatible endpoint for latency, capacity-unit behavior,
and persistence testing:

```bash
cd examples/dynamodb_sink/
docker compose up -d          # start DynamoDB Local on port 8123
python main.py --live         # run against DynamoDB Local
docker compose down           # clean up
```

## Production deployment (Terraform)

The `terraform/` subdirectory contains a ready-to-use module for AWS:

```bash
cd examples/dynamodb_sink/terraform/
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars
terraform init && terraform apply
```

See [`terraform/README.md`](terraform/README.md) for full variable and output
reference, and [`bh-audit-logger/docs/deploying-dynamodb.md`](../../../bh-audit-logger/docs/deploying-dynamodb.md)
for the complete deployment guide.
