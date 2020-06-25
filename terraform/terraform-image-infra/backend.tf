terraform {
  required_version = ">= 0.12"
  backend "gcs" {
    bucket  = "dev-ops-155255-terraform-states"
    prefix  = "terraform/image-state"
  }
}
