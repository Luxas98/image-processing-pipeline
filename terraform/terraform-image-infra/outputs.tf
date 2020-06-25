output "redis-ip" {
  value = google_redis_instance.redis-store.host
}

output "consul-secret-reader-key" {
  value = module.consul.consul_reader_service_account_key
}

output "consul-secret-reader" {
  value = module.consul.consul_reader_service_account
}