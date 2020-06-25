resource "vault_gcp_secret_roleset" "pubsub-user" {
  backend = "${var.vault_backend_path}"
  project = "${var.project_id}"
  roleset = "${var.env}-${var.app}-pubsub-user"
  secret_type = "service_account_key"
  binding {
    resource = "//cloudresourcemanager.googleapis.com/projects/${var.project_id}"
    roles = ["roles/pubsub.publisher", "roles/pubsub.subscriber", "roles/pubsub.viewer", "roles/pubsub.editor", "roles/monitoring.viewer", "roles/iam.serviceAccountTokenCreator"]
  }
}

resource "vault_gcp_secret_roleset" "gcs-user" {
  backend = "${var.vault_backend_path}"
  project = "${var.project_id}"
  roleset = "${var.env}-${var.app}-gcs-user"
  secret_type = "service_account_key"
  binding {
    resource = "//cloudresourcemanager.googleapis.com/projects/${var.project_id}"
    roles = ["roles/iam.serviceAccountTokenCreator"]
  }
}

resource "google_storage_bucket_iam_binding" "predicted-creator-bucket-biding" {
  provider = "google-beta"
  bucket = google_storage_bucket.predicted-data-store.name
  role = "roles/storage.objectCreator"
  members = [
    "serviceAccount:${vault_gcp_secret_roleset.gcs-user.service_account_email}"
  ]

  depends_on = [google_storage_bucket.predicted-data-store]
}

resource "google_storage_bucket_iam_binding" "predicted-viewer-bucket-biding" {
  provider = "google-beta"
  bucket = google_storage_bucket.predicted-data-store.name
  role = "roles/storage.objectViewer"
  members = [
    "serviceAccount:${vault_gcp_secret_roleset.gcs-user.service_account_email}"
  ]

  depends_on = [google_storage_bucket.predicted-data-store]
}

resource "google_storage_bucket_iam_binding" "raw-viewer-bucket-biding" {
  provider = "google-beta"
  bucket = google_storage_bucket.raw-data-store.name
  role = "roles/storage.objectViewer"
  members = [
    "serviceAccount:${vault_gcp_secret_roleset.gcs-user.service_account_email}"
  ]

  depends_on = [google_storage_bucket.raw-data-store]
}

resource "google_storage_bucket_iam_binding" "raw-creator-bucket-biding" {
  provider = "google-beta"
  bucket = google_storage_bucket.predicted-data-store.name
  role = "roles/storage.objectCreator"
  members = [
    "serviceAccount:${vault_gcp_secret_roleset.gcs-user.service_account_email}"
  ]

  depends_on = [google_storage_bucket.predicted-data-store]
}