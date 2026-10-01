#!/usr/bin/env bash
# Token consumption dashboard (idempotent; safe to rerun):
#  1. Foundry account platform metrics (InputTokens, OutputTokens, ...) -> Log Analytics (AzureMetrics)
#  2. "FleetWise token usage" Azure Workbook over Application Insights traces + those metrics
# Usage: scripts/setup-monitoring.sh   (reads AZURE_RESOURCE_GROUP from .env)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ -f "$ROOT/.env" ]] && { set -a; source "$ROOT/.env"; set +a; }
RG="${AZURE_RESOURCE_GROUP:?Set AZURE_RESOURCE_GROUP in .env}"

FOUNDRY_ID="$(az cognitiveservices account list -g "$RG" --query "[?kind=='AIServices'] | [0].id" -o tsv)"
LAW_ID="$(az monitor log-analytics workspace list -g "$RG" --query "[0].id" -o tsv)"
read -r RG_ID LOCATION < <(az group show -n "$RG" --query "[id, location]" -o tsv | paste -s -)

az monitor diagnostic-settings create --name foundry-metrics-to-law --resource "$FOUNDRY_ID" \
  --workspace "$LAW_ID" --metrics '[{"category":"AllMetrics","enabled":true}]' >/dev/null
echo "Diagnostic setting: Foundry metrics -> $(basename "$LAW_ID")"

# Stable workbook id per resource group, so reruns update the same workbook.
WORKBOOK_ID="$(python3 -c "import uuid,sys; print(uuid.uuid5(uuid.NAMESPACE_URL, sys.argv[1]))" "$LAW_ID/fleetwise-token-usage")"
BODY="$(mktemp)"
jq -n --arg loc "$LOCATION" --arg src "$LAW_ID" --rawfile data "$ROOT/infra/monitoring/token-usage.workbook.json" '{
  location: $loc, kind: "shared",
  properties: { displayName: "FleetWise token usage", category: "workbook", sourceId: $src, serializedData: $data }
}' > "$BODY"
az rest --method put --body "@$BODY" \
  --url "https://management.azure.com$RG_ID/providers/Microsoft.Insights/workbooks/$WORKBOOK_ID?api-version=2023-06-01" >/dev/null
rm -f "$BODY"
echo "Workbook: FleetWise token usage"
echo "  https://portal.azure.com/#@/resource$RG_ID/providers/Microsoft.Insights/workbooks/$WORKBOOK_ID/workbook"
