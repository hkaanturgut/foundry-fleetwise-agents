"""Run both workflow agents in Foundry Agent Service as prompt agents, with Foundry memory attached as a tool.

  fleet-triage     hardened instructions + OpenAPI tool + File Search + memory search tool
  fleet-workorder  work-order instructions + function tools (declared in Foundry, executed by the
                   workflow behind the approval gate) + memory search tool

The memory tool is scoped with {{$userId}}: the workflow sends `x-memory-user-id: manager-<name>`,
so each fleet manager gets an isolated scope. Because memory is part of the agent definition, the
portal shows it on the agent (Tools) and the memories under the memory store.

Usage: python -m src.agents.setup_foundry_agents
"""

from __future__ import annotations

import json

from .common import ROOT, TRIAGE, WORKORDER, project
from .setup_memory import STORE
from .triage import agent as triage
from .workorder import agent as workorder


def main() -> None:
    client = project()
    path = ROOT / ".agents.json"
    versions = json.loads(path.read_text()) if path.exists() else {}

    triage_version = client.agents.create_version(
        agent_name=TRIAGE, definition=triage.definition("hardened", versions["vector_store"], memory=True)
    )
    workorder_version = client.agents.create_version(agent_name=WORKORDER, definition=workorder.definition())
    versions["triage_hosted"] = str(triage_version.version)
    versions["workorder_hosted"] = str(workorder_version.version)
    path.write_text(json.dumps(versions, indent=2))
    print(f"{TRIAGE} version {triage_version.version}: OpenAPI + File Search + memory (store {STORE})")
    print(f"{WORKORDER} version {workorder_version.version}: function tools + memory (store {STORE})")


if __name__ == "__main__":
    main()
