# Demo runbook

Short checklist to get the demo working every time. Full explanations: [README section 8](../README.md#8-walkthrough-run-it-yourself).

All commands run from the repo root.

## A. One-time setup (new subscription)

```bash
az login
SUBSCRIPTION_ID=<id> scripts/deploy.sh eastus2          # Terraform + API image + .env + token dashboard
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m src.agents.setup_agents                       # vector store + baseline versions (run ONCE)
python -m src.agents.setup_memory                       # memory store
python -m src.agents.deploy workorder                   # fleet-workorder
python -m src.agents.deploy triage hardened --memory    # fleet-triage used by the workflow
```

> Already deployed but `.env` is missing or `terraform output` is empty (new machine, lost state)?
> Do **not** run `deploy.sh`. Recreate `.env` by hand from the resource group (see README troubleshooting),
> then run `scripts/setup-monitoring.sh` once for the token dashboard.

## B. Before each run-through (T-10 min)

```bash
az login                                  # if the token expired
. .venv/bin/activate
scripts/reset-api.sh                      # re-seed demo data (wipes bookings from the last run)
sleep 20
scripts/preflight.sh                      # every line green
```

Open in the browser:
- Foundry portal > project `proj-fleetwise` (Agents, Evaluations, Memory tabs)
- Azure portal > Monitor > Workbooks > **FleetWise token usage** (time range: last hour)

## C. On stage

| # | Command | Expect |
| --- | --- | --- |
| 1 | `python -m src.agents.deploy triage naive` | `Deployed fleet-triage:N (naive instructions)` |
| 2 | `python -m src.agents.ask_agent live_naive "Which vehicles need service this week? Most urgent first."` | Ranked overdue list |
| 3 | `python -m evals.foundry_eval live_naive` | `GATE FAIL` (policy below 100%) |
| 4 | `python -m src.agents.deploy triage hardened` | New version |
| 5 | `python -m evals.foundry_eval live_hardened` | `GATE PASS` |
| 6 | `python -m src.agents.deploy triage hardened --memory` | Production version (`triage_hosted`) |
| 7 | `python -m src.agents.memory_demo --manager kaan --reset` | Session 2 recalls "Maria Lopez for brake jobs" |
| 8 | `python -m src.agents.maf_workflow --manager kaan` | Answer **y, n, y**; table shows 2 booked, 1 still overdue |
| 9 | Portal: Agents > `fleet-workorder` > Traces | The run just made |
| 10 | Workbook **FleetWise token usage** | One row per command above, tokens and cost per agent version |

Step 7 must run before step 8, or the workflow suggests Dave Chen instead of Maria Lopez.

Every command ends with a token table. While an eval runs (about a minute), switch to the portal's **Evaluations** page.
The workbook lags 1 to 3 minutes behind the terminal.

## D. If something breaks

| Symptom | Fix |
| --- | --- |
| `zsh: command not found: python` | `. .venv/bin/activate` |
| `FOUNDRY_PROJECT_ENDPOINT is not set` | `.env` missing: see the note in section A |
| Preflight: `Foundry agents with memory` FAIL | `python -m src.agents.deploy triage hardened --memory` |
| Vehicles already booked / table wrong | `scripts/reset-api.sh`, wait 20 s |
| Memory recall empty | Wait 10 s, then `python -m src.agents.memory_demo --recall-only --manager kaan` |
| Eval slow on stage | Show an earlier run in the portal's **Evaluations** page |
| Workbook empty | Wait 1 to 3 minutes, widen the time range; rerun `scripts/setup-monitoring.sh` |
| Telemetry error printed | Demo still works; `FLEETWISE_TELEMETRY=off` hides it |
| `KeyError` on `.agents.json` | Rerun the deploy command for the missing key (`live_naive`, `live_hardened`, `triage_hosted`, `workorder_hosted`) |
