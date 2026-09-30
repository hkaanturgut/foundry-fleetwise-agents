"""Two agents and a manager: triage -> draft work orders -> human approval -> booking.

The agents only read and draft. The booking call to the legacy API happens in this code,
and only after the manager types "y" for that line. That is the human-in-the-loop gate.

Usage: python -m src.agents.dispatch_workflow [--auto-approve]   (auto-approve is for rehearsal only)
"""

from __future__ import annotations

import argparse
import json
import re

import httpx

from .common import API_URL, ROOT, TRIAGE, WORKORDER, ask, project

TENANT = "1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-approve", action="store_true")
    parser.add_argument("--top", type=int, default=3)
    args = parser.parse_args()

    versions = json.loads((ROOT / ".agents.json").read_text())
    openai = project().get_openai_client()

    print("\n[1/3] fleet-triage: finding what needs service...\n")
    triage = ask(openai, TRIAGE, f"List the {args.top} most urgent vehicles that need service, with unit number, "
                 "service type, suggested technician and why. Keep it short.", versions.get("v2"))
    print(triage)

    print("\n[2/3] fleet-workorder: drafting work orders...\n")
    drafts = ask(openai, WORKORDER, f"Draft work orders for this triage summary:\n{triage}", versions.get("workorder"))
    print(drafts)

    lines = requests_lines()
    print("\n[3/3] Manager approval (nothing is booked without a yes)\n")
    for unit, service in re.findall(r"(LSL-\d{3})\s*\|\s*([A-Za-z]+)", drafts):
        match = next((l for l in lines if l["unitNumber"] == unit and l["serviceType"] == service), None)
        if match is None:
            print(f"  {unit} {service}: not on the dispatch list, skipped")
            continue
        answer = "y" if args.auto_approve else input(f"  Approve {unit} {service}? [y/n] ").strip().lower()
        endpoint = "approve" if answer == "y" else "reject"
        result = httpx.post(
            f"{API_URL}/api/dispatch/{endpoint}",
            headers={"X-Tenant-Id": TENANT, "X-User-Role": "FleetManager", "X-User-Name": "stage-manager"},
            json={"vehicleId": match["vehicleId"], "serviceType": service},
            timeout=30,
        )
        print(f"    -> {endpoint}: HTTP {result.status_code}")


def requests_lines() -> list[dict]:
    response = httpx.get(f"{API_URL}/api/dispatch", headers={"X-Tenant-Id": TENANT}, timeout=30)
    response.raise_for_status()
    return response.json()["lines"]


if __name__ == "__main__":
    main()
