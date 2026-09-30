#!/usr/bin/env bash
# Writes .env for the agent scripts from Terraform outputs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/infra"
cat > "$ROOT/.env" <<ENV
FOUNDRY_PROJECT_ENDPOINT=$(terraform output -raw project_endpoint)
FOUNDRY_MODEL=$(terraform output -raw chat_deployment)
FLEETWISE_API_URL=$(terraform output -raw api_url)
FOUNDRY_EMBEDDING_MODEL=$(terraform output -raw embedding_deployment)
ENV
cat "$ROOT/.env"
