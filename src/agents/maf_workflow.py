"""FleetWise dispatch with Microsoft Agent Framework: sequential orchestration, Foundry memory,
tools, and human-in-the-loop approval.

  fleet-triage     Foundry-hosted prompt agent (server-side tools: FleetWise OpenAPI, manuals
                   File Search, and the Foundry memory search tool).
  fleet-workorder  Foundry-hosted prompt agent whose tools are declared as function tools:
                   get_dispatch_lines, reject_work_order, and approve_work_order. They execute in
                   this process; approve_work_order is approval_mode="always_require", so the
                   workflow PAUSES until a human decides.

Both agents are versioned, traced, evaluated, and given memory in Foundry (memory store
fleetwise-manager-memory, one scope per manager). Agent Framework orchestrates them.

Pattern: SequentialBuilder(participants=[triage, workorder], output_from="all"). The approval pause is native:
the workflow emits a function_approval_request and resumes with the manager's answer.

Usage: python -m src.agents.maf_workflow ["request"] [--auto-approve] [--manager kaan]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from agent_framework import Content
from agent_framework.foundry import FoundryAgent
from agent_framework.orchestrations import SequentialBuilder
from azure.identity import AzureCliCredential

from .common import PROJECT_ENDPOINT, ROOT, TRIAGE, WORKORDER
from .workorder_tools import TOOLS


class _DropExpectedWarnings(logging.Filter):
    """Two warnings describe this design working as intended, so they are not shown on stage:
    - each approval response is bound twice; the second pass logs a harmless mismatch;
    - tool schemas live on the Foundry agent, so the client does not resend them."""

    EXPECTED = ("did not match the active approval", "tool declarations cannot be sent when an agent is specified")

    def filter(self, record: logging.LogRecord) -> bool:
        return not any(text in record.getMessage() for text in self.EXPECTED)


for _name in ("agent_framework", "agent_framework.foundry"):
    logging.getLogger(_name).addFilter(_DropExpectedWarnings())

def build_workflow(manager_scope: str):
    """Both participants are Foundry-hosted agent versions; memory is the Foundry memory search tool
    in their definitions, scoped per manager through the x-memory-user-id header."""
    credential = AzureCliCredential()
    versions = json.loads((ROOT / ".agents.json").read_text())
    headers = {"x-memory-user-id": manager_scope}

    triage = FoundryAgent(
        project_endpoint=PROJECT_ENDPOINT,
        agent_name=TRIAGE,
        agent_version=versions["triage_hosted"],
        credential=credential,
        default_headers=headers,
    )
    workorder = FoundryAgent(
        project_endpoint=PROJECT_ENDPOINT,
        agent_name=WORKORDER,
        agent_version=versions["workorder_hosted"],
        credential=credential,
        default_headers=headers,
        tools=TOOLS,  # declared in Foundry; executed here, behind the approval gate
    )
    return SequentialBuilder(participants=[triage, workorder], output_from="all").build()


async def _drain(stream, auto_approve: bool, presenter) -> dict[str, Content] | None:
    """Stream one leg of the workflow; return approval responses if the workflow paused."""
    requests: dict[str, Content] = {}
    async for event in stream:
        if event.type == "request_info" and isinstance(event.data, Content):
            requests[event.request_id] = event.data
        elif event.type == "output" and not isinstance(event.data, list):
            presenter.on_update(event.data)

    if not requests:
        return None
    responses: dict[str, Content] = {}
    approvals = [(rid, r) for rid, r in requests.items() if r.type == "function_approval_request" and r.function_call]
    for number, (request_id, request) in enumerate(approvals, start=1):
        presenter.approval(number, len(approvals), request.function_call.arguments)
        if auto_approve:
            answer = "y"
        else:
            answer = input("  Approve this booking? [y/n] ").strip().lower()
        presenter.record_decision(answer == "y")
        responses[request_id] = request.to_function_approval_response(approved=answer == "y")
    return responses


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", nargs="?", default="What are the 3 most urgent maintenance jobs? Get them booked.")
    parser.add_argument("--auto-approve", action="store_true")
    parser.add_argument("--manager", default="kaan", help="memory scope: one per fleet manager")
    args = parser.parse_args()

    from .showcase import Presenter

    versions = json.loads((ROOT / ".agents.json").read_text())
    presenter = Presenter(
        {
            TRIAGE: {"version": versions["triage_hosted"], "role": "read-only",
                     "tools": "FleetWise API (OpenAPI)  |  SOP manuals (File Search)  |  memory"},
            WORKORDER: {"version": versions["workorder_hosted"], "role": "can book, human-gated",
                        "tools": "get_dispatch_lines  |  list_qualified_technicians  |  approve_work_order (needs a human yes)  |  reject_work_order  |  memory"},
        },
        args.manager,
        args.request,
    )
    workflow = build_workflow(f"manager-{args.manager}")
    pending = await _drain(workflow.run(args.request, stream=True), args.auto_approve, presenter)
    while pending:
        pending = await _drain(workflow.run(stream=True, responses=pending), args.auto_approve, presenter)
    presenter.finish()


if __name__ == "__main__":
    asyncio.run(main())
