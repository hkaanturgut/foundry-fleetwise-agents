#!/usr/bin/env bash
# Restores the demo data (approvals and work orders created on stage) by restarting the API revision.
# The API keeps its SQLite data inside the container, so a restart re-seeds it.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ -f "$ROOT/.env" ]] && { set -a; source "$ROOT/.env"; set +a; }
RG="${AZURE_RESOURCE_GROUP:-}"
if [[ -z "$RG" ]]; then
  RG="$(cd "$ROOT/infra" && terraform output -raw resource_group 2>/dev/null || true)"
fi
[[ -n "$RG" ]] || { echo "Set AZURE_RESOURCE_GROUP in .env (for example rg-fleetwise-xxxxx)"; exit 1; }
REV="$(az containerapp show -g "$RG" -n ca-fleetwise-api --query properties.latestRevisionName -o tsv)"
az containerapp revision restart -g "$RG" -n ca-fleetwise-api --revision "$REV" >/dev/null
echo "Restarted $REV; demo data re-seeded (the API is back in about 20 seconds)."
