#!/usr/bin/env bash
APP_NAME=image
CLIENT_NAME=${CLIENT_NAME:=$1}
RESOURCE_NAME=${RESOURCE_NAME:=$2}

cd ../clients
terraform init
terraform workspace select ${CLIENT_NAME}
PROJECT_ID=$(terraform output project_id)
REGION=$(terraform output region)
ZONE=$(terraform output zone)

PRIMARY_CLUSTER_NAME=$(terraform output primary_cluster_name)
VAULT_ADDRESS=$(terraform output vault_address)
VAULT_CA=$(terraform output vault_ca)
VAULT_TOKEN=$(terraform output vault_token)

cd ../clients-setup
terraform init
terraform workspace select ${CLIENT_NAME}
VAULT_BACKEND_PATH=$(terraform output vault_backend_path)


cd ../terraform-image-infra
terraform init
# Create or select terraform workspace
terraform workspace new ${CLIENT_NAME} || terraform workspace select ${CLIENT_NAME}
terraform destroy -target=${RESOURCE_NAME} -var="app=${APP_NAME}" -var="env=${CLIENT_NAME}" -var="project_id=${PROJECT_ID}" -var="region=${REGION}" -var="zone=${ZONE}" -var="cluster_name=${PRIMARY_CLUSTER_NAME}" -var="vault_address=${VAULT_ADDRESS}" -var="vault_ca=${VAULT_CA}" -var="vault_token=${VAULT_TOKEN}" -var="vault_backend_path=${VAULT_BACKEND_PATH}"
