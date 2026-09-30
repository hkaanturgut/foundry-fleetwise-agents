# Your Legacy App Just Got a Brain: FleetWise Agents on Microsoft Foundry

Build, test, and trust AI agents on top of an existing application with [Microsoft Foundry](https://learn.microsoft.com/azure/foundry/). The legacy FleetWise .NET API stays unchanged; agents reach it through its OpenAPI contract, ground answers in maintenance manuals, hand off work between agents with a human approval step, and are evaluated and red-teamed before anyone trusts them.

> **Status: under construction.** The companion Spec Kit demo lives in [spec-kit-fleetwise](https://github.com/hkaanturgut/spec-kit-fleetwise).

## Target architecture

One `terraform apply` builds the platform. A bootstrap script creates the agents, because agents live in the Foundry data plane.

```mermaid
flowchart LR
    M["Manager<br/>approves bookings"]
    W["Workflow (Python)<br/>Microsoft Agent Framework"]
    subgraph TF["Built by one terraform apply (azapi + azurerm)"]
        subgraph F["Microsoft Foundry project"]
            A["Agents<br/>dispatcher, triage, work-order"]
            MD["Model deployments"]
            EV["Evals + red teaming"]
        end
        API["FleetWise legacy API<br/>.NET 8 on Container Apps"]
        SQL[("Azure SQL")]
        S["AI Search<br/>manuals + SOPs"]
        ST[("Storage")]
        AI["App Insights"]
        ID["Managed identities<br/>+ Key Vault"]
    end
    W -- "asks for approval" --> M
    W --> A
    A -- "OpenAPI tool" --> API --> SQL
    A -- "knowledge" --> S
    ST --> S
    F -- traces --> AI
```

## Agent flow with a human in the loop

```mermaid
sequenceDiagram
    autonumber
    actor Mgr as Fleet manager
    participant Tri as Triage agent
    participant WO as Work-order agent
    participant API as FleetWise API
    participant KB as Manuals (AI Search)
    Mgr->>Tri: "Which vehicles need service this week?"
    Tri->>API: GET vehicles, maintenance history
    Tri->>KB: service intervals and procedures
    Tri->>WO: overdue list with reasons
    WO->>API: draft work orders
    WO-->>Mgr: proposed work orders for approval
    Mgr->>WO: approve 3, reject 1
    WO->>API: schedule approved work orders
```

## Planned layout

| Path | Purpose |
| --- | --- |
| `infra/` | Terraform root, modules (`foundation`, `foundry`, `knowledge`, `legacy`, `identity`), `demo.tfvars` |
| `src/legacy-api/` | Pinned copy of the FleetWise API, containerized |
| `src/agents/` | Python agents and the approval workflow |
| `data/` | Seed SQL, maintenance manuals and SOPs |
| `evals/` | Quality datasets and red-team prompts |
| `scripts/` | bootstrap, seed, preflight, reset, destroy |

## License

[MIT](LICENSE)
