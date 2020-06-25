#!/usr/bin/env bash
ADMIN_PROJECT_ID=${ADMIN_PROJECT_ID:=dev-lukas}
docker build --build-arg ADMIN_PROJECT_ID=${ADMIN_PROJECT_ID} -t eu.gcr.io/${ADMIN_PROJECT_ID}/pubsub-base:python3.6-alpine -f Dockerfile .