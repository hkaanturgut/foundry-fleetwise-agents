"""Create every agent version the demo uses (idempotent: each run adds new versions).

Stage map (fleet-triage versions are recorded in .agents.json):
  stage1  fleet-triage   OpenAPI tool only (legacy API)
  stage2  fleet-triage   + File Search over the maintenance manuals
  v1      fleet-triage   stage2 with NAIVE instructions (vulnerable to the planted note)
  v2      fleet-triage   stage2 with HARDENED instructions (data is untrusted)

The workflow agents (with memory) come from deploy.py or setup_foundry_agents.py.

Usage: python -m src.agents.setup_agents
"""

from __future__ import annotations

import json

from .common import ROOT, TRIAGE, project
from .triage import agent as triage


def main() -> None:
    client = project()
    openai = client.get_openai_client()

    manuals = sorted((ROOT / "data" / "manuals").glob("*.md"))
    store = openai.vector_stores.create(name="fleetwise-manuals")
    for path in manuals:
        with path.open("rb") as handle:
            openai.vector_stores.files.upload_and_poll(vector_store_id=store.id, file=handle)
    print(f"Vector store {store.id} with {len(manuals)} manuals")

    def create(label: str, profile: str, vector_store_id: str | None = None) -> str:
        agent = client.agents.create_version(agent_name=TRIAGE, definition=triage.definition(profile, vector_store_id))
        print(f"{label:8} {TRIAGE} version {agent.version}")
        return str(agent.version)

    versions = {
        "stage1": create("stage1", "hardened"),
        "stage2": create("stage2", "hardened", store.id),
        "v1": create("v1", "naive", store.id),
        "v2": create("v2", "hardened", store.id),
        "vector_store": store.id,
    }
    (ROOT / ".agents.json").write_text(json.dumps(versions, indent=2))
    print("Saved .agents.json")


if __name__ == "__main__":
    main()
