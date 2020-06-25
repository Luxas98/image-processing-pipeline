resource "google_storage_bucket" "raw-data-store" {
  provider = "google-beta"
  name = "${var.project_id}-${var.app}-data-raw"
  location = "${var.region}"
  project = "${var.project_id}"
  storage_class = "REGIONAL"
  force_destroy = true

  labels = {
    component = local.component_name
  }
}

resource "google_storage_bucket" "predicted-data-store" {
  provider = "google-beta"
  name = "${var.project_id}-${var.app}-data-predicted"
  location = "${var.region}"
  project = "${var.project_id}"
  storage_class = "REGIONAL"
  force_destroy = true

  labels = {
    component = local.component_name
  }
}

data "google_storage_project_service_account" "gcs_account" {
    project = "${var.project_id}"
}

resource "google_pubsub_topic_iam_binding" "binding" {
    project = "${var.project_id}"
    topic       = module.ingestion-pubsub.topic_name
    role        = "roles/pubsub.publisher"
    members     = ["serviceAccount:${data.google_storage_project_service_account.gcs_account.email_address}"]
}

resource "google_storage_notification" "raw-bucket-notification" {
    provider = google-beta
    bucket            = google_storage_bucket.raw-data-store.name
    payload_format    = "JSON_API_V1"
    topic             = module.ingestion-pubsub.topic_name
    event_types       = ["OBJECT_FINALIZE"]
    depends_on = [google_storage_bucket.raw-data-store, module.ingestion-pubsub, google_pubsub_topic_iam_binding.binding]
}

resource "google_storage_notification" "predicted-bucket-notification" {
    provider = google-beta
    bucket            = google_storage_bucket.predicted-data-store.name
    payload_format    = "JSON_API_V1"
    topic             = module.ingestion-pubsub.topic_name
    event_types       = ["OBJECT_FINALIZE"]
    depends_on = [google_storage_bucket.predicted-data-store, module.ingestion-pubsub, google_pubsub_topic_iam_binding.binding]
}