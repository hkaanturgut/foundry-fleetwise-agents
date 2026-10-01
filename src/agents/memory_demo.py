"""Foundry long-term memory, shown in two separate sessions.

Session 1: the fleet manager states a standing preference.
Session 2: a brand-new session (new thread, no chat history) with the same memory scope.
The agent recalls the preference from the Foundry memory store, not from the conversation.
Memory is the Foundry memory search tool on the hosted agent; the scope comes from the
x-memory-user-id header. Prove it in the portal: Memory stores > fleetwise-manager-memory.

Usage: python -m src.agents.memory_demo [--manager kaan] [--reset] [--recall-only] [--wait 30]
"""

from __future__ import annotations

import argparse
import asyncio
import json

from agent_framework.foundry import FoundryAgent
from azure.identity import AzureCliCredential

from . import telemetry
from .common import PROJECT_ENDPOINT, ROOT, TRIAGE
from .setup_memory import STORE

TELL = (
    "A standing preference for all future sessions: for brake jobs I prefer Maria Lopez as the technician. "
    "She knows our brake fleet best."
)
ASK = "Before we start: which technician do I prefer for brake jobs?"


def _agent(scope: str) -> FoundryAgent:
    """The Foundry-hosted fleet-triage version with the memory search tool in its definition."""
    versions = json.loads((ROOT / ".agents.json").read_text())
    return FoundryAgent(
        project_endpoint=PROJECT_ENDPOINT,
        agent_name=TRIAGE,
        agent_version=versions["triage_hosted"],
        credential=AzureCliCredential(),
        default_headers={"x-memory-user-id": scope},
    )


async def main(args: argparse.Namespace) -> None:
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
        telemetry.count(TRIAGE, reply.usage_details)
        print(f"[fleet-triage] {reply.text}\n")
        print(f"... waiting {args.wait}s while Foundry extracts and indexes the memory ...\n")
        await asyncio.sleep(args.wait)

    agent = _agent(scope)
    print(f"[session 2 | NEW session, same scope {scope}] manager: {ASK}")
    reply = await agent.run(ASK, session=agent.create_session())
    telemetry.count(TRIAGE, reply.usage_details)
    print(f"[fleet-triage] {reply.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manager", default="kaan")
    parser.add_argument("--wait", type=int, default=30, help="seconds for the store to index the new memory")
    parser.add_argument("--recall-only", action="store_true")
    parser.add_argument("--reset", action="store_true", help="forget everything in this scope first")
    cli = parser.parse_args()
    with telemetry.run("memory_demo", manager=cli.manager):
        asyncio.run(main(cli))
