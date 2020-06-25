output "topic_name" {
  value = "${google_pubsub_topic.topic.name}"
}

output "subscription_name" {
  value = "${google_pubsub_subscription.subscription.name}"
}