#!/usr/bin/env bash
# One command: Terraform platform -> build the FleetWise image in ACR -> point the container app at it -> write .env.
# Usage: SUBSCRIPTION_ID=<id> scripts/deploy.sh [location]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${SUBSCRIPTION_ID:?Set SUBSCRIPTION_ID}"
LOCATION="${1:-eastus2}"
cd "$ROOT/infra"

az account set --subscription "$SUBSCRIPTION_ID"
terraform init -input=false -upgrade >/dev/null
terraform apply -input=false -auto-approve -var "subscription_id=$SUBSCRIPTION_ID" -var "location=$LOCATION"

ACR="$(terraform output -raw acr_name)"
az acr build --registry "$ACR" --image fleetwise-api:v1 "$ROOT/src/legacy-api" --no-logs
terraform apply -input=false -auto-approve -var "subscription_id=$SUBSCRIPTION_ID" -var "location=$LOCATION" \
  -var "api_image=${ACR}.azurecr.io/fleetwise-api:v1"

"$ROOT/scripts/write-env.sh"
