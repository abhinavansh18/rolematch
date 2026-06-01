variable "project_id" { type = string }
variable "region"     { type = string }
variable "env"        { type = string }

resource "google_redis_instance" "cache" {
  name           = "jobmatch-redis-${var.env}"
  tier           = var.env == "prod" ? "STANDARD_HA" : "BASIC"
  memory_size_gb = var.env == "prod" ? 4 : 1
  region         = var.region
  project        = var.project_id
  redis_version  = "REDIS_7_0"

  auth_enabled            = true
  transit_encryption_mode = "SERVER_AUTHENTICATION"

  redis_configs = {
    maxmemory-policy    = "allkeys-lru"
    activedefrag        = "yes"
    lazyfree-lazy-eviction = "yes"
  }

  maintenance_policy {
    weekly_maintenance_window {
      day = "SUNDAY"
      start_time { hours = 3; minutes = 0 }
    }
  }
}

output "host"     { value = google_redis_instance.cache.host }
output "port"     { value = google_redis_instance.cache.port }
output "auth_string" {
  value     = google_redis_instance.cache.auth_string
  sensitive = true
}
