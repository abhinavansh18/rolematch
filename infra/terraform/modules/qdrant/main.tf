variable "env"           { type = string }
variable "qdrant_api_key" { type = string; sensitive = true }

# Qdrant Cloud managed cluster
resource "qdrant_cluster" "main" {
  name          = "jobmatch-${var.env}"
  cloud_provider = "gcp"
  cloud_region   = "us-central1"

  configuration {
    number_of_nodes = var.env == "prod" ? 3 : 1
    node_configuration {
      package_id = var.env == "prod" ? "qdrant-2-advanced" : "qdrant-0-basic"
    }
  }
}

output "url"     { value = qdrant_cluster.main.url }
output "api_key" {
  value     = var.qdrant_api_key
  sensitive = true
}
