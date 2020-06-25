resource "google_pubsub_topic" "topic" {
  name = "${var.app}-${var.topic_name}"
  project = "${var.project_id}"
  labels = {
    component = "${var.component}"
    env = "${var.env}"
  }
}

resource "google_pubsub_subscription" "subscription" {
  name = "${google_pubsub_topic.topic.name}-sub"
  topic = "${google_pubsub_topic.topic.name}"
  project = "${var.project_id}"
  labels = {
    component = "${var.component}"
    env = "${var.env}"
  }
}