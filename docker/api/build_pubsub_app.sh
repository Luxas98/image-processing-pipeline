#!/usr/bin/env bash
ADMIN_PROJECT_ID=${ADMIN_PROJECT_ID:=dev-lukas}
docker build --build-arg ADMIN_PROJECT_ID=${ADMIN_PROJECT_ID} -t eu.gcr.io/${ADMIN_PROJECT_ID}/api-base:pubsub -f Dockerfile .

