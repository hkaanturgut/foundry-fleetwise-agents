"""fleet-workorder: books the most urgent jobs, each one approved by a FleetManager.

Its function tools are declared in Foundry (schema only) and executed in the Agent Framework
workflow (tools.py), so a human approval gate wraps every write.
"""

from __future__ import annotations

from azure.ai.projects.models import PromptAgentDefinition

from ..common import MODEL
from ..setup_memory import memory_tool
from .instructions import INSTRUCTIONS
from .tools import foundry_tool_definitions


def definition() -> PromptAgentDefinition:
    return PromptAgentDefinition(model=MODEL, instructions=INSTRUCTIONS, tools=[*foundry_tool_definitions(), memory_tool()])
