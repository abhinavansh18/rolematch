terraform {
  required_version = ">= 1.7"
  required_providers {
    google     = { source = "hashicorp/google",     version = "~> 5.0" }
    confluent  = { source = "confluentinc/confluent", version = "~> 1.76" }
  }
  backend "gcs" {
    bucket = "jobmatch-tfstate-prod"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id"  { type = string }
variable "region"      { type = string; default = "us-central1" }
variable "db_password" { type = string; sensitive = true }

module "gke" {
  source       = "../../modules/gke"
  project_id   = var.project_id
  region       = var.region
  cluster_name = "jobmatch-prod"
  env          = "prod"
}

module "postgres" {
  source      = "../../modules/rds"
  project_id  = var.project_id
  region      = var.region
  env         = "prod"
  db_password = var.db_password
}

module "redis" {
  source     = "../../modules/redis"
  project_id = var.project_id
  region     = var.region
  env        = "prod"
}

module "kafka" {
  source     = "../../modules/kafka"
  project_id = var.project_id
  region     = var.region
  env        = "prod"
}

output "gke_endpoint"        { value = module.gke.cluster_endpoint }
output "postgres_connection" { value = module.postgres.connection_name }
output "redis_host"          { value = module.redis.host }
output "kafka_bootstrap"     { value = module.kafka.bootstrap_endpoint }
