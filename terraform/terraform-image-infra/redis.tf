resource "google_redis_instance" "redis-store" {
  name = "${var.app}-redis"
  memory_size_gb = 1
  tier = "STANDARD_HA"
  location_id = "${var.region}-${var.zone}"
  region = "${var.region}"
  project = "${var.project_id}"

  depends_on = ["google_project_service.project-redis-service"]
  labels = {
    component = local.component_name
  }
}