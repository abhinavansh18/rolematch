variable "project_id" { type = string }
variable "region"     { type = string }
variable "env"        { type = string }

# Using Confluent Cloud Kafka via Terraform provider
# For MSK on AWS, swap resource types accordingly

resource "confluent_environment" "jobmatch" {
  display_name = "jobmatch-${var.env}"
}

resource "confluent_kafka_cluster" "main" {
  display_name = "jobmatch-kafka-${var.env}"
  availability = var.env == "prod" ? "MULTI_ZONE" : "SINGLE_ZONE"
  cloud        = "GCP"
  region       = var.region

  dynamic "basic"    { for_each = var.env != "prod" ? [1] : []; content {} }
  dynamic "standard" { for_each = var.env == "prod" ? [1] : []; content {} }

  environment { id = confluent_environment.jobmatch.id }
}

# Core topics
locals {
  topics = {
    "job.scraped"      = { partitions = 24, retention_ms = "172800000"  }
    "job.normalized"   = { partitions = 12, retention_ms = "604800000"  }
    "job.embedded"     = { partitions = 12, retention_ms = "86400000"   }
    "resume.parse"     = { partitions = 6,  retention_ms = "604800000"  }
    "resume.parsed"    = { partitions = 6,  retention_ms = "604800000"  }
    "match.requested"  = { partitions = 12, retention_ms = "3600000"    }
    "match.completed"  = { partitions = 12, retention_ms = "2592000000" }
    "analytics.event"  = { partitions = 24, retention_ms = "2592000000" }
    "scrape.requested" = { partitions = 6,  retention_ms = "3600000"    }
    "user.deletion_requested" = { partitions = 3, retention_ms = "604800000" }
  }
}

resource "confluent_kafka_topic" "topics" {
  for_each          = local.topics
  topic_name        = each.key
  partitions_count  = each.value.partitions
  rest_endpoint     = confluent_kafka_cluster.main.rest_endpoint

  config = {
    "retention.ms"        = each.value.retention_ms
    "compression.type"    = "snappy"
    "min.insync.replicas" = var.env == "prod" ? "2" : "1"
    "replication.factor"  = var.env == "prod" ? "3" : "1"
  }

  kafka_cluster { id = confluent_kafka_cluster.main.id }
  environment   { id = confluent_environment.jobmatch.id }
}

output "bootstrap_endpoint" { value = confluent_kafka_cluster.main.bootstrap_endpoint }
