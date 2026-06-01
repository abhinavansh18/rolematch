terraform {
  required_version = ">= 1.7"
  backend "local" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id"  { type = string }
variable "region"      { type = string; default = "us-central1" }
variable "db_password" { type = string; sensitive = true; default = "devpassword" }

module "gke"     { source = "../../modules/gke";   project_id = var.project_id; region = var.region; cluster_name = "jobmatch-dev"; env = "dev" }
module "postgres"{ source = "../../modules/rds";   project_id = var.project_id; region = var.region; env = "dev"; db_password = var.db_password }
module "redis"   { source = "../../modules/redis"; project_id = var.project_id; region = var.region; env = "dev" }
