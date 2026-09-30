#!/usr/bin/env bash
# Green/red check before going on stage.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
set -a; source "$ROOT/.env"; set +a
ok(){ printf '  \033[32mOK\033[0m    %s\n' "$1"; }; bad(){ printf '  \033[31mFAIL\033[0m  %s\n' "$1"; }
az account show >/dev/null 2>&1 && ok "az signed in ($(az account show --query user.name -o tsv))" || bad "az not signed in"
code=$(curl -s -o /dev/null -w '%{http_code}' "$FLEETWISE_API_URL/health"); [[ $code == 200 ]] && ok "FleetWise API healthy" || bad "API health $code"
n=$(curl -s "$FLEETWISE_API_URL/api/dispatch" -H 'X-Tenant-Id: 1' | python3 -c 'import json,sys;print(json.load(sys.stdin)["count"])' 2>/dev/null); [[ -n "$n" ]] && ok "dispatch lines for tenant 1: $n" || bad "dispatch call failed"
[[ -f "$ROOT/.agents.json" ]] && ok "backup agents created (.agents.json)" || bad "run: python -m src.agents.setup_agents"
grep -q triage_hosted "$ROOT/.agents.json" 2>/dev/null && ok "hosted agents with memory (triage v$(python3 -c "import json;print(json.load(open('$ROOT/.agents.json'))['triage_hosted'])"), workorder v$(python3 -c "import json;print(json.load(open('$ROOT/.agents.json'))['workorder_hosted'])"))" || bad "run: python -m src.agents.setup_hosted_agents"
