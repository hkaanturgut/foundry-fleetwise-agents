"""Deploy an agent version to Microsoft Foundry, live, from code.

Each call creates a NEW immutable version of the agent in Foundry Agent Service (prompt agent):
model + instructions + tools + memory. Nothing is overwritten; you can compare, evaluate, and roll
back by version number.

  python -m src.agents.deploy triage naive       # fleet-triage with naive instructions (the "before")
  python -m src.agents.deploy triage hardened    # fleet-triage with hardened instructions (the "after")
  python -m src.agents.deploy triage hardened --memory   # production version: + memory, used by the workflow
  python -m src.agents.deploy workorder          # fleet-workorder with approval-gated function tools
  python -m src.agents.deploy tool-spec          # print the OpenAPI tool spec to paste in the portal

Versions are recorded in .agents.json as live_naive / live_hardened / workorder_hosted.
Versions under evaluation have NO memory tool: memory personalizes answers per user, which makes
eval results depend on who ran them. The --memory version is what the workflow uses (triage_hosted).
"""

from __future__ import annotations

import base64
import json
import os
import sys
import uuid

from azure.ai.projects.models import FileSearchTool, PromptAgentDefinition

from .common import MODEL, PROJECT_ENDPOINT, ROOT, TRIAGE, WORKORDER, project, tool_spec
from .setup_agents import HARDENED, NAIVE, openapi_tool
from .setup_foundry_agents import memory_tool
from .workorder_tools import WORKORDER_INSTRUCTIONS, foundry_tool_definitions

AGENTS_FILE = ROOT / ".agents.json"


def portal_link(agent_name: str) -> str:
    """Deep link to the agent in the Foundry portal (needs AZURE_SUBSCRIPTION_ID and AZURE_RESOURCE_GROUP)."""
    sub, rg = os.environ.get("AZURE_SUBSCRIPTION_ID"), os.environ.get("AZURE_RESOURCE_GROUP")
    if not (sub and rg):
        return "https://ai.azure.com (Build > Agents)"
    account = PROJECT_ENDPOINT.split("//")[1].split(".")[0]
    proj = PROJECT_ENDPOINT.rstrip("/").split("/")[-1]
    sub_id = base64.urlsafe_b64encode(uuid.UUID(sub).bytes).decode().rstrip("=")
    return f"https://ai.azure.com/nextgen/r/{sub_id},{rg},,{account},{proj}/build/agents/{agent_name}/build"


def _save(**keys: str) -> None:
    versions = json.loads(AGENTS_FILE.read_text()) if AGENTS_FILE.exists() else {}
    versions.update(keys)
    AGENTS_FILE.write_text(json.dumps(versions, indent=2))


def deploy_triage(profile: str, with_memory: bool) -> None:
    instructions = {"naive": NAIVE, "hardened": HARDENED}[profile]
    versions = json.loads(AGENTS_FILE.read_text())
    tools = [openapi_tool(), FileSearchTool(vector_store_ids=[versions["vector_store"]])]
    if with_memory:
        tools.append(memory_tool())
    agent = project().agents.create_version(
        agent_name=TRIAGE,
        definition=PromptAgentDefinition(model=MODEL, instructions=instructions, tools=tools),
    )
    key = "triage_hosted" if with_memory else f"live_{profile}"
    _save(**{key: str(agent.version)})
    print(f"Deployed {TRIAGE}:{agent.version}  ({profile} instructions{', with memory' if with_memory else ''})")
    print(f"  model   {MODEL}")
    print("  tools   fleetwise (OpenAPI, read-only)  |  file_search (SOP manuals)" + ("  |  memory_search (per manager)" if with_memory else ""))
    print(f"  saved   .agents.json -> {key} = {agent.version}")
    print(f"  portal  {portal_link(TRIAGE)}")
    if not with_memory:
        print(f"\nNext: python -m evals.foundry_eval {key}")


def deploy_workorder() -> None:
    agent = project().agents.create_version(
        agent_name=WORKORDER,
        definition=PromptAgentDefinition(
            model=MODEL, instructions=WORKORDER_INSTRUCTIONS, tools=[*foundry_tool_definitions(), memory_tool()]
        ),
    )
    _save(workorder_hosted=str(agent.version))
    print(f"Deployed {WORKORDER}:{agent.version}")
    print(f"  model   {MODEL}")
    print("  tools   get_dispatch_lines | list_qualified_technicians | approve_work_order (human approval) | reject_work_order  +  memory_search")
    print(f"  portal  {portal_link(WORKORDER)}")


def main() -> None:
    args = sys.argv[1:]
    memory = "--memory" in args
    args = [a for a in args if a != "--memory"]
    if args[:1] == ["triage"] and len(args) == 2 and args[1] in ("naive", "hardened"):
        deploy_triage(args[1], memory)
    elif args == ["workorder"]:
        deploy_workorder()
    elif args == ["tool-spec"]:
        print(json.dumps(tool_spec(), indent=2))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
