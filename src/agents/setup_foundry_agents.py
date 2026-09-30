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

from azure.ai.projects.models import FileSearchTool, MemorySearchPreviewTool, PromptAgentDefinition

from .common import MODEL, ROOT, TRIAGE, WORKORDER, project
from .setup_agents import HARDENED, openapi_tool
from .setup_memory import STORE
from .workorder_tools import WORKORDER_INSTRUCTIONS, foundry_tool_definitions

MEMORY_UPDATE_DELAY = 5  # seconds of inactivity before Foundry writes new memories (default 300)


def memory_tool() -> MemorySearchPreviewTool:
    return MemorySearchPreviewTool(memory_store_name=STORE, scope="{{$userId}}", update_delay=MEMORY_UPDATE_DELAY)


def main() -> None:
    client = project()
    path = ROOT / ".agents.json"
    versions = json.loads(path.read_text()) if path.exists() else {}

    triage = client.agents.create_version(
        agent_name=TRIAGE,
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=HARDENED,
            tools=[openapi_tool(), FileSearchTool(vector_store_ids=[versions["vector_store"]]), memory_tool()],
        ),
    )
    workorder = client.agents.create_version(
        agent_name=WORKORDER,
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=WORKORDER_INSTRUCTIONS,
            tools=[*foundry_tool_definitions(), memory_tool()],
        ),
    )
    versions["triage_hosted"] = str(triage.version)
    versions["workorder_hosted"] = str(workorder.version)
    path.write_text(json.dumps(versions, indent=2))
    print(f"{TRIAGE} version {triage.version}: OpenAPI + File Search + memory (store {STORE})")
    print(f"{WORKORDER} version {workorder.version}: function tools + memory (store {STORE})")


if __name__ == "__main__":
    main()
