# --------------------------------------------------------------------------
# bh-audit-logger DynamoDB table
#
# Production-ready single-table design for healthcare audit events.
# On-demand billing, encryption at rest, point-in-time recovery, and TTL.
#
# Usage:
#   cd terraform/
#   terraform init
#   terraform plan -var="environment=prod"
#   terraform apply -var="environment=prod"
# --------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 6.0"
    }
  }
}

# --------------------------------------------------------------------------
# Variables
# --------------------------------------------------------------------------

variable "table_name" {
  description = "Name of the DynamoDB audit events table"
  type        = string
  default     = "bh_audit_events"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "ttl_attribute" {
  description = "Attribute used for DynamoDB TTL (set to empty string to disable)"
  type        = string
  default     = "ttl"
}

variable "point_in_time_recovery" {
  description = "Enable point-in-time recovery (strongly recommended for prod)"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

locals {
  common_tags = merge(var.tags, {
    Project     = "bh-healthcare"
    Component   = "audit-logger"
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

# --------------------------------------------------------------------------
# DynamoDB Table
# --------------------------------------------------------------------------

resource "aws_dynamodb_table" "audit_events" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"

  # Composite primary key: service+date partition, timestamp+id sort
  hash_key  = "service_date"
  range_key = "ts_event"

  # Key attributes (DynamoDB only needs declarations for keys and GSI keys)
  attribute {
    name = "service_date"
    type = "S"
  }

  attribute {
    name = "ts_event"
    type = "S"
  }

  attribute {
    name = "patient_id"
    type = "S"
  }

  attribute {
    name = "actor_subject_id"
    type = "S"
  }

  attribute {
    name = "outcome_status"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  # GSI1: Patient access history (HIPAA §164.312(b) audit controls)
  global_secondary_index {
    name     = "patient_id-index"
    hash_key = "patient_id"
    range_key = "timestamp"

    projection_type    = "INCLUDE"
    non_key_attributes = [
      "event_id",
      "action_type",
      "actor_subject_id",
      "outcome_status",
      "data_classification",
      "http_route_template",
      "event_json",
    ]
  }

  # GSI2: Actor activity review (HIPAA §164.308(a)(1)(ii)(D))
  global_secondary_index {
    name      = "actor-index"
    hash_key  = "actor_subject_id"
    range_key = "timestamp"

    projection_type    = "INCLUDE"
    non_key_attributes = [
      "event_id",
      "action_type",
      "resource_type",
      "patient_id",
      "outcome_status",
      "http_route_template",
      "event_json",
    ]
  }

  # GSI3: Access denial monitoring (§164.308(a)(5)(ii)(C))
  global_secondary_index {
    name      = "outcome-index"
    hash_key  = "outcome_status"
    range_key = "timestamp"

    projection_type    = "INCLUDE"
    non_key_attributes = [
      "event_id",
      "actor_subject_id",
      "action_type",
      "resource_type",
      "patient_id",
      "error_type",
      "event_json",
    ]
  }

  # TTL: DynamoDB automatically deletes expired items at no cost
  dynamic "ttl" {
    for_each = var.ttl_attribute != "" ? [1] : []
    content {
      attribute_name = var.ttl_attribute
      enabled        = true
    }
  }

  # Encryption at rest with AWS-managed key (no extra cost)
  server_side_encryption {
    enabled = true
  }

  # Point-in-time recovery: continuous backups for the last 35 days
  point_in_time_recovery {
    enabled = var.point_in_time_recovery
  }

  tags = local.common_tags
}

# --------------------------------------------------------------------------
# IAM Policy: Minimum permissions for the audit logger service
# --------------------------------------------------------------------------

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_iam_policy" "audit_logger" {
  name        = "bh-audit-logger-${var.environment}"
  description = "Minimum IAM permissions for bh-audit-logger DynamoDBSink"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AuditEventWrite"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
        ]
        Resource = [
          aws_dynamodb_table.audit_events.arn,
        ]
      },
      {
        Sid    = "AuditEventQuery"
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
        ]
        Resource = [
          aws_dynamodb_table.audit_events.arn,
          "${aws_dynamodb_table.audit_events.arn}/index/*",
        ]
      },
      {
        Sid    = "AuditTableDescribe"
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeTable",
        ]
        Resource = [
          aws_dynamodb_table.audit_events.arn,
        ]
      },
    ]
  })

  tags = local.common_tags
}

# --------------------------------------------------------------------------
# Outputs
# --------------------------------------------------------------------------

output "table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.audit_events.name
}

output "table_arn" {
  description = "DynamoDB table ARN"
  value       = aws_dynamodb_table.audit_events.arn
}

output "iam_policy_arn" {
  description = "ARN of the IAM policy for audit logger services"
  value       = aws_iam_policy.audit_logger.arn
}

output "python_sink_config" {
  description = "Example Python configuration for DynamoDBSink"
  value       = <<-EOT
    from bh_audit_logger.sinks.dynamodb import DynamoDBSink

    sink = DynamoDBSink(
        table_name="${aws_dynamodb_table.audit_events.name}",
        region="${data.aws_region.current.name}",
    )
  EOT
}
