"""Shared configuration and clients for the FleetWise agent demo.

Reads settings from environment variables or the repo-root .env written by scripts/write-env.sh:
  FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL, FLEETWISE_API_URL
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

ROOT = Path(__file__).resolve().parents[2]


def load_env() -> None:
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"'))


load_env()

PROJECT_ENDPOINT = os.environ.get("FOUNDRY_PROJECT_ENDPOINT", "")
MODEL = os.environ.get("FOUNDRY_MODEL", "gpt-4.1")
API_URL = os.environ.get("FLEETWISE_API_URL", "").rstrip("/")

TRIAGE = "fleet-triage"
WORKORDER = "fleet-workorder"


def project() -> AIProjectClient:
    if not PROJECT_ENDPOINT:
        raise SystemExit("FOUNDRY_PROJECT_ENDPOINT is not set. Run scripts/write-env.sh first.")
    return AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())


def tool_spec() -> dict:
    spec = json.loads((ROOT / "openapi" / "fleetwise-agent-tools.json").read_text())
    spec["servers"] = [{"url": API_URL}]
    return spec


def ask(openai_client, agent_name: str, question: str, version: str | None = None) -> str:
    """Send one question to a Foundry agent and return its text answer."""
    ref = {"name": agent_name, "type": "agent_reference"}
    if version:
        ref["version"] = version
    response = openai_client.responses.create(input=question, extra_body={"agent_reference": ref})
    return response.output_text
