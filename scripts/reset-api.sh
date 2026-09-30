#!/usr/bin/env bash
# Restores the demo data (approvals and work orders created on stage) by restarting the API revision.
# The API keeps its SQLite data inside the container, so a restart re-seeds it.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/infra"
RG="$(terraform output -raw resource_group)"
REV="$(az containerapp revision list -g "$RG" -n ca-fleetwise-api --query '[0].name' -o tsv)"
az containerapp revision restart -g "$RG" -n ca-fleetwise-api --revision "$REV" >/dev/null
echo "Restarted $REV; demo data re-seeded."
