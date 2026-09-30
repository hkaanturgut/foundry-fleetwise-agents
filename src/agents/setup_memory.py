"""Create (or reuse) the Foundry memory store that gives the agents long-term memory.

The store extracts user-profile facts (for example "our shop is closed on Fridays",
"prefer Maria Lopez for brake jobs") and chat summaries, per scope (one scope per manager).

Usage: python -m src.agents.setup_memory
"""

from __future__ import annotations

import os

from azure.ai.projects.models import MemorySearchPreviewTool, MemoryStoreDefaultDefinition, MemoryStoreDefaultOptions
from azure.core.exceptions import ResourceNotFoundError

from .common import MODEL, project

STORE = "fleetwise-manager-memory"
MEMORY_UPDATE_DELAY = 5  # seconds of inactivity before Foundry writes new memories (default 300)


def memory_tool() -> MemorySearchPreviewTool:
    """Memory search tool for an agent definition. {{$userId}} comes from the x-memory-user-id header,
    so each fleet manager gets an isolated scope."""
    return MemorySearchPreviewTool(memory_store_name=STORE, scope="{{$userId}}", update_delay=MEMORY_UPDATE_DELAY)


def main() -> None:
    client = project()
    try:
        store = client.beta.memory_stores.get(STORE)
        print(f"Memory store {store.name} already exists")
        return
    except ResourceNotFoundError:
        pass

    store = client.beta.memory_stores.create(
        name=STORE,
        description="Long-term memory for FleetWise fleet managers: preferences and past decisions.",
        definition=MemoryStoreDefaultDefinition(
            chat_model=MODEL,
            embedding_model=os.environ.get("FOUNDRY_EMBEDDING_MODEL", "text-embedding-3-small"),
            options=MemoryStoreDefaultOptions(
                user_profile_enabled=True,
                chat_summary_enabled=True,
                user_profile_details="Fleet manager preferences: preferred technicians, shop schedule, "
                "service priorities, vehicles to watch. Never store personal or sensitive data.",
            ),
        ),
    )
    print(f"Created memory store {store.name}")


if __name__ == "__main__":
    main()
