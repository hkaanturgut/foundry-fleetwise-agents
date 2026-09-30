"""fleet-triage: read-only agent. Finds what needs service, explains why, cites the SOP manuals.

Every tool runs server-side in Foundry: the FleetWise OpenAPI tool (read-only), File Search over
the manuals, and optionally the memory search tool. It has no way to book anything.
"""

from __future__ import annotations

from azure.ai.projects.models import (
    FileSearchTool,
    OpenApiAnonymousAuthDetails,
    OpenApiFunctionDefinition,
    OpenApiTool,
    PromptAgentDefinition,
)

from ..common import MODEL, tool_spec
from ..setup_memory import memory_tool
from .instructions import HARDENED, NAIVE

INSTRUCTIONS = {"naive": NAIVE, "hardened": HARDENED}


def openapi_tool() -> OpenApiTool:
    return OpenApiTool(
        openapi=OpenApiFunctionDefinition(
            name="fleetwise",
            description="Read-only FleetWise legacy API: dispatch list and vehicle maintenance history.",
            spec=tool_spec(),
            auth=OpenApiAnonymousAuthDetails(),
        )
    )


def definition(profile: str = "hardened", vector_store_id: str | None = None, memory: bool = False) -> PromptAgentDefinition:
    """Model + instructions + tools. No vector store = no File Search (stage1)."""
    tools = [openapi_tool()]
    if vector_store_id:
        tools.append(FileSearchTool(vector_store_ids=[vector_store_id]))
    if memory:
        tools.append(memory_tool())
    return PromptAgentDefinition(model=MODEL, instructions=INSTRUCTIONS[profile], tools=tools)
