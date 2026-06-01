variable "project_id"   { type = string }
variable "region"       { type = string }
variable "env"          { type = string }
variable "db_password"  { type = string; sensitive = true }

resource "google_sql_database_instance" "postgres" {
  name             = "jobmatch-pg-${var.env}"
  database_version = "POSTGRES_16"
  region           = var.region
  project          = var.project_id

  deletion_protection = var.env == "prod"

  settings {
    tier              = var.env == "prod" ? "db-custom-4-15360" : "db-f1-micro"
    availability_type = var.env == "prod" ? "REGIONAL" : "ZONAL"
    disk_autoresize   = true
    disk_size         = var.env == "prod" ? 100 : 20
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.env == "prod"
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
      }
    }

    maintenance_window {
      day          = 7  # Sunday
      hour         = 4
      update_track = "stable"
    }

    database_flags {
      name  = "max_connections"
      value = var.env == "prod" ? "500" : "100"
    }
    database_flags {
      name  = "log_min_duration_statement"
      value = "1000"   # Log queries > 1s
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
    }
  }
}

resource "google_sql_database" "jobmatch" {
  name     = "jobmatch"
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

resource "google_sql_user" "app_user" {
  name     = "jobmatch_app"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
  project  = var.project_id
}

output "connection_name" { value = google_sql_database_instance.postgres.connection_name }
output "private_ip"      { value = google_sql_database_instance.postgres.private_ip_address }
