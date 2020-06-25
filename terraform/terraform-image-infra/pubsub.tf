module "ingestion-pubsub" {
  source = "../terraform-pubsub"
  env = "${var.env}"
  project_id = "${var.project_id}"
  app = "${var.app}"
  component = local.component_name
  topic_name = "ingestion"
}

module "processing-pubsub" {
  source = "../terraform-pubsub"
  env = "${var.env}"
  project_id = "${var.project_id}"
  app = "${var.app}"
  component = local.component_name
  topic_name = "processing"
}

module "model-prediction-pubsub" {
  source = "../terraform-pubsub"
  env = "${var.env}"
  project_id = "${var.project_id}"
  app = "${var.app}"
  component = local.component_name
  topic_name = "model-prediction"
}

module "post-processing-pubsub" {
  source = "../terraform-pubsub"
  env = "${var.env}"
  project_id = "${var.project_id}"
  app = "${var.app}"
  component = local.component_name
  topic_name = "post-processing"
}