provider "google-beta" {
  region = "${var.region}"
  project = "${var.project_id}"
}

provider "vault" {
  address = "https://${var.vault_address}"
  token = "${var.vault_token}"
  ca_cert_file = "${var.vault_ca}"
}