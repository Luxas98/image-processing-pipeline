module "consul" {
  source = "../terraform-consul"
  appname = "${var.app}"
  cluster_name = "${var.cluster_name}"
  env = "${var.env}"
  project_id = "${var.project_id}"
  vault_addr = "${var.vault_address}"
  vault_ca = "${var.vault_ca}"
}

resource "google_project_service" "project-redis-service" {
 provider = "google-beta"
 project = "${var.project_id}"
 service = "redis.googleapis.com"
 disable_dependent_services = false
 disable_on_destroy = false
}