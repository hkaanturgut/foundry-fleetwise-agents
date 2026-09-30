"""Foundry long-term memory, shown in two separate sessions.

Session 1: the fleet manager states a standing preference.
Session 2: a brand-new session (new thread, no chat history) with the same memory scope.
The agent recalls the preference from the Foundry memory store, not from the conversation.

Usage: python -m src.agents.memory_demo [--manager kaan] [--reset] [--recall-only] [--wait 30]
"""

from __future__ import annotations

import argparse
import asyncio
import json

from agent_framework.foundry import FoundryAgent, FoundryMemoryProvider
from azure.identity import AzureCliCredential

from .common import PROJECT_ENDPOINT, ROOT, TRIAGE
from .setup_memory import STORE

TELL = (
    "A standing preference for all future sessions: I manage the HeavyDuty trucks personally, "
    "so always list HeavyDuty vehicles first, and I prefer Aisha Khan for brake jobs when she is qualified."
)
ASK = "Before we start: how do I like my maintenance list ordered, and who do I prefer for brake jobs?"


def _agent(scope: str) -> FoundryAgent:
    credential = AzureCliCredential()
    versions = json.loads((ROOT / ".agents.json").read_text())
    return FoundryAgent(
        project_endpoint=PROJECT_ENDPOINT,
        agent_name=TRIAGE,
        agent_version=versions["v2"],
        credential=credential,
        context_providers=[
            FoundryMemoryProvider(
                project_endpoint=PROJECT_ENDPOINT,
                credential=credential,
                memory_store_name=STORE,
                scope=scope,
                update_delay=0,
            )
        ],
    )


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manager", default="kaan")
    parser.add_argument("--wait", type=int, default=30, help="seconds for the store to index the new memory")
    parser.add_argument("--recall-only", action="store_true")
    parser.add_argument("--reset", action="store_true", help="forget everything in this scope first")
    args = parser.parse_args()
    scope = f"manager-{args.manager}"

    if args.reset:
        from azure.ai.projects import AIProjectClient

        client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=AzureCliCredential())
        client.beta.memory_stores.delete_scope(name=STORE, scope=scope)
        print(f"Memory scope {scope} cleared.\n")

    if not args.recall_only:
        agent = _agent(scope)
        print(f"[session 1 | scope {scope}] manager: {TELL}")
        reply = await agent.run(TELL, session=agent.create_session())
        print(f"[fleet-triage] {reply.text}\n")
        print(f"... waiting {args.wait}s while Foundry extracts and indexes the memory ...\n")
        await asyncio.sleep(args.wait)

    agent = _agent(scope)
    print(f"[session 2 | NEW session, same scope {scope}] manager: {ASK}")
    reply = await agent.run(ASK, session=agent.create_session())
    print(f"[fleet-triage] {reply.text}")


if __name__ == "__main__":
    asyncio.run(main())
