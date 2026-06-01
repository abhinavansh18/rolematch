variable "project_id"   { type = string }
variable "region"       { type = string }
variable "cluster_name" { type = string }
variable "env"          { type = string }

resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region
  project  = var.project_id

  # Use separately managed node pools
  remove_default_node_pool = true
  initial_node_count       = 1

  network_policy {
    enabled  = true
    provider = "CALICO"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  addons_config {
    http_load_balancing        { disabled = false }
    horizontal_pod_autoscaling { disabled = false }
    gce_persistent_disk_csi_driver_config { enabled = true }
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  release_channel {
    channel = var.env == "prod" ? "STABLE" : "REGULAR"
  }
}

# General purpose node pool
resource "google_container_node_pool" "general" {
  name       = "general"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  project    = var.project_id

  autoscaling {
    min_node_count = 2
    max_node_count = var.env == "prod" ? 20 : 6
  }

  node_config {
    machine_type = var.env == "prod" ? "n2-standard-4" : "n2-standard-2"
    disk_size_gb = 50
    disk_type    = "pd-ssd"

    workload_metadata_config { mode = "GKE_METADATA" }
    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# GPU node pool for vLLM inference
resource "google_container_node_pool" "gpu" {
  name       = "gpu-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  project    = var.project_id

  autoscaling {
    min_node_count = 0
    max_node_count = var.env == "prod" ? 4 : 1
  }

  node_config {
    machine_type = "g2-standard-4"  # NVIDIA L4
    disk_size_gb = 100
    disk_type    = "pd-ssd"

    guest_accelerator {
      type  = "nvidia-l4"
      count = 1
      gpu_driver_installation_config {
        gpu_driver_version = "LATEST"
      }
    }

    taint {
      key    = "nvidia.com/gpu"
      value  = "present"
      effect = "NO_SCHEDULE"
    }

    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }
}

output "cluster_endpoint"        { value = google_container_cluster.primary.endpoint }
output "cluster_ca_certificate"  { value = google_container_cluster.primary.master_auth[0].cluster_ca_certificate }
