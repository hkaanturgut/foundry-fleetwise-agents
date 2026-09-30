# Your Legacy App Just Got a Brain: FleetWise Agents on Microsoft Foundry

Build, test, and trust AI agents on top of an existing application with [Microsoft Foundry](https://learn.microsoft.com/azure/foundry/) and the [Microsoft Agent Framework](https://learn.microsoft.com/agent-framework/). The legacy FleetWise .NET API stays unchanged: agents reach it through its OpenAPI contract, ground answers in maintenance manuals, remember each fleet manager's preferences, book work only after a human approves, and must pass an eval gate before anyone trusts them.

> The companion Spec Kit demo lives in [spec-kit-fleetwise](https://github.com/hkaanturgut/spec-kit-fleetwise).

## Quick start

```bash
az login
SUBSCRIPTION_ID=<your-subscription-id> scripts/deploy.sh eastus2   # Terraform + image build + .env
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python -m src.agents.setup_agents      # Foundry agent versions + manuals vector store
python -m src.agents.setup_memory      # Foundry memory store
scripts/preflight.sh

python -m src.agents.maf_workflow      # multi-agent workflow: triage -> work order, manager approves
python -m src.agents.memory_demo       # long-term memory across two separate sessions
python -m evals.run v1 && python -m evals.run v2      # domain rule evals: break-fix proof
python -m evals.foundry_eval v2                       # Foundry cloud eval: quality + safety
```

## Design at a glance

| Question | Answer |
| --- | --- |
| Where are the agents hosted? | `fleet-triage` is a **Foundry prompt agent**: versioned, server-side, with server-side tools. `fleet-workorder` is an **Agent Framework agent** that runs in the workflow process and calls the Foundry model deployment. |
| Which framework? | **Microsoft Agent Framework** (`agent-framework-core`, `-foundry`, `-orchestrations`). |
| Orchestration pattern | **Sequential** (`SequentialBuilder`): triage output becomes work-order input, with a native **human-in-the-loop** pause on every booking. |
| Tools | Triage: OpenAPI tool (FleetWise read API) + File Search (manuals). Work order: Python function tools `get_dispatch_lines`, `reject_work_order`, and `approve_work_order` (`approval_mode="always_require"`). |
| Memory | **Foundry memory store** (`FoundryMemoryProvider`): user profile + chat summary, one scope per fleet manager, shared by both agents. |
| Evaluation | Two layers, both gate CI: **domain rule evals** (tenant isolation, prompt injection, grounding) and **Foundry cloud evals** (task adherence, intent resolution, relevance, coherence, violence). |
| Observability | Foundry tracing to Application Insights. |

## Architecture

```mermaid
flowchart LR
    Mgr["Fleet manager"]
    subgraph Proc["Workflow process: Microsoft Agent Framework"]
        SEQ["SequentialBuilder"]
        WO["fleet-workorder<br/>Agent Framework agent<br/>function tools"]
    end
    subgraph TF["Built by terraform apply (azapi + azurerm)"]
        subgraph F["Microsoft Foundry project"]
            TRI["fleet-triage<br/>hosted prompt agent v1..v4"]
            MEM[("Memory store<br/>per-manager scope")]
            VS[("Vector store<br/>SOP manuals")]
            MD["gpt-4o +<br/>text-embedding-3-small"]
            EV["Evaluations"]
        end
        API["FleetWise legacy API<br/>.NET 8 on Container Apps"]
        AI["App Insights"]
    end
    Mgr -- "request / approve" --> SEQ
    SEQ --> TRI --> WO
    TRI -- "OpenAPI tool (read)" --> API
    TRI -- "File Search" --> VS
    WO -- "approve / reject (write)" --> API
    TRI & WO <-- "recall + remember" --> MEM
    WO --> MD
    F -- traces --> AI
```

## Agent flow with a human in the loop

```mermaid
sequenceDiagram
    autonumber
    actor Mgr as Fleet manager
    participant Tri as fleet-triage (Foundry)
    participant WO as fleet-workorder (Agent Framework)
    participant Mem as Foundry memory
    participant API as FleetWise API
    Mgr->>Tri: "3 most urgent jobs, get them booked"
    Mem-->>Tri: manager preferences
    Tri->>API: getDispatchLines, getVehicle (OpenAPI tool)
    Tri->>WO: urgent list with reasons and SOPs
    WO->>API: get_dispatch_lines (exact ids)
    WO-->>Mgr: approve_work_order? (workflow pauses)
    Mgr->>WO: yes / no per job
    WO->>API: POST /api/dispatch/approve (only if yes)
    WO-->>Mgr: booked / not booked
    Tri-->>Mem: new facts learned
```

## Eval gate

```mermaid
flowchart LR
    PR["Pull request<br/>instructions, tools, cases"] --> R["Domain rule evals<br/>evals/run.py"]
    PR --> C["Foundry cloud eval<br/>evals/foundry_eval.py"]
    R -- "any case fails" --> X["Block merge"]
    C -- "pass rate below 80%" --> X
    R & C -- "all green" --> OK["Merge + promote version"]
```

Generic judges and domain rules catch different things. In rehearsal the naive `v1` scored 5/5 on the Foundry quality and safety evaluators, yet failed the domain rules because it relayed a prompt injection hidden in a technician note. Both layers gate the merge.

## Repository map

| Path | Purpose |
| --- | --- |
| `infra/` | Terraform: Foundry account + project, model deployments, App Insights, ACR, Container Apps, RBAC |
| `src/legacy-api/` | The FleetWise .NET 8 API with its dispatch endpoints, containerized |
| `src/agents/` | Agent setup, memory store, Agent Framework workflow, memory demo |
| `openapi/` | The read-only OpenAPI contract the triage agent uses as a tool |
| `data/manuals/` | SOP documents for File Search |
| `evals/` | Test cases, rule-based runner, Foundry cloud eval |
| `.github/workflows/` | `agent-eval-gate`: both eval layers on every agent change |
| `scripts/` | deploy, write-env, preflight, reset-api |

## License

[MIT](LICENSE)
