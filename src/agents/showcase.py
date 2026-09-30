"""Stage-friendly rendering for the Agent Framework workflow.

Shows what normally stays invisible: which agent is running, which tools it calls (server-side
Foundry tools and local function tools), which memories it recalled, a clear approval card for
every write, and a final check against the FleetWise API (the system of record).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .common import API_URL

console = Console(highlight=False)

TOOL_LABELS = {
    "fleetwise_getDispatchLines": "FleetWise API  GET /api/dispatch",
    "fleetwise_getVehicle": "FleetWise API  GET /api/vehicles/{id}",
}


class Presenter:
    """Consumes workflow events and prints them as a readable story."""

    def __init__(self, agents: dict[str, dict[str, str]], manager: str, request: str) -> None:
        self.agents = agents  # name -> {"version", "role", "tools"}
        self.speaker: str | None = None
        self.step = 0
        self.buffer = ""
        self.live: Live | None = None
        self.calls: dict[str, dict[str, Any]] = {}  # call_id -> {"name", "args"}
        self.decisions: list[tuple[dict[str, Any], bool]] = []
        self.memory_shown: set[str] = set()
        self.citations: set[str] = set()
        chain = "  ->  ".join(f"{n}:{a['version']}" for n, a in agents.items())
        console.print(Panel.fit(
            f"[bold]Pattern[/]   Sequential orchestration (Microsoft Agent Framework)\n"
            f"[bold]Agents[/]    {chain}  (Foundry prompt agents)\n"
            f"[bold]Manager[/]   {manager}  (memory scope manager-{manager})\n"
            f"[bold]Request[/]   {request}",
            title="FleetWise dispatch", border_style="cyan"))

    # ---------- streaming text ----------
    def _stop_live(self) -> None:
        if self.live:
            self.live.stop()
            self.live = None
            self.buffer = ""
            console.line()

    def _start_agent(self, name: str) -> None:
        self._stop_live()
        self._flush_citations()
        self.speaker = name
        self.step += 1
        info = self.agents.get(name, {})
        console.print()
        console.rule(f"[bold]Step {self.step} of {len(self.agents)}   {name}:{info.get('version', '?')}   {info.get('role', '')}")
        console.print(f"[dim]tools: {info.get('tools', '')}[/]")

    def _text(self, text: str) -> None:
        self.buffer += text
        if self.live is None:
            self.live = Live(Markdown(self.buffer), console=console, refresh_per_second=8, vertical_overflow="visible")
            self.live.start()
        else:
            self.live.update(Markdown(self.buffer))

    def _event_line(self, label: str, detail: str) -> None:
        self._stop_live()
        key = (label, detail)
        if key == getattr(self, "_last_event", None):
            return  # identical parallel calls: show once
        self._last_event = key
        console.print(f"  [bold magenta]>[/] [bold]{label:<9}[/] {detail}")

    def _flush_citations(self) -> None:
        if self.citations:
            self._stop_live()
            console.print(f"  [dim]cited: {', '.join(sorted(self.citations))}[/]")
            self.citations.clear()

    # ---------- workflow events ----------
    def on_update(self, update: Any) -> None:
        name = getattr(update, "author_name", None) or getattr(update, "executor_id", None)
        if name and name != self.speaker:
            self._start_agent(name)
        self._server_side(update)
        for content in getattr(update, "contents", []) or []:
            if content.type == "text" and content.text:
                self._text(content.text)
            elif content.type == "function_call":
                args = _args(content.arguments)
                self.calls[content.call_id] = {"name": content.name, "args": args}
                if content.name != "approve_work_order":
                    self._event_line("tool", f"{content.name}({_fmt_args(args)})")
            elif content.type == "function_result":
                call = self.calls.get(content.call_id, {})
                self._event_line("result", _summarize(call.get("name", ""), str(content.result)))

    def _server_side(self, update: Any) -> None:
        """Foundry runs OpenAPI, File Search, and memory on the server; surface them from the raw stream."""
        raw = getattr(getattr(update, "raw_representation", None), "raw_representation", None)
        if getattr(raw, "type", "") != "response.output_item.done":
            return
        item = raw.item.model_dump() if hasattr(raw.item, "model_dump") else {}
        kind = item.get("type")
        if kind == "openapi_call":
            self._event_line("api", TOOL_LABELS.get(item.get("name"), item.get("name", "")))
        elif kind == "file_search_call":
            queries = item.get("queries") or []
            self._event_line("manuals", f"File Search: {queries[0] if queries else ''}")
        elif kind == "memory_search_call" and self.speaker not in self.memory_shown:
            self.memory_shown.add(self.speaker or "")
            memories = list(dict.fromkeys(
                m.get("content", "") for m in item.get("memories") or [] if m.get("kind") == "user_profile"))
            self._event_line("memory", f"recalled {len(memories)} fact(s) about this manager")
            for text in memories[:3]:
                console.print(f"             [dim]- {text[:170]}[/]")
        elif kind == "message":
            for part in item.get("content") or []:
                for ann in part.get("annotations") or []:
                    if ann.get("filename"):
                        self.citations.add(ann["filename"])

    # ---------- approvals ----------
    def approval(self, number: int, total: int, arguments: Any) -> bool | None:
        """Render an approval card; return None to ask interactively."""
        self._stop_live()
        self._flush_citations()
        args = _args(arguments)
        line = _dispatch_line(args.get("vehicle_id"), args.get("service_type"))
        named = args.get("technician_name")
        if isinstance(named, str) and named.strip().lower() in ("null", "none", "suggested", ""):
            named = None
        suggested = (line.get("suggestion") or {}).get("technicianName")
        technician = named or (f"{suggested} (the system's suggestion)" if suggested else "the system's suggestion")
        why = []
        if line.get("kmOverdue"):
            why.append(f"{line['kmOverdue']:,} km overdue")
        if line.get("daysUntilDue") is not None and line["daysUntilDue"] < 0:
            why.append(f"{-line['daysUntilDue']} days overdue")
        if named:
            from .workorder_tools import _qualified

            qualified = [t["name"] for t in _qualified(str(args.get("service_type")), line.get("vehicleClass"))]
            if named.lower() not in (q.lower() for q in qualified):
                technician += f"  [bold red](NOT qualified: the tool will refuse. Qualified: {', '.join(qualified)})[/]"
            else:
                technician += "  [green](qualified)[/]"
        table = Table.grid(padding=(0, 2))
        table.add_row("[bold]Vehicle[/]", f"{line.get('unitNumber', args.get('vehicle_id'))}  ({line.get('vehicleClass', '?')})")
        table.add_row("[bold]Service[/]", str(args.get("service_type")))
        table.add_row("[bold]Technician[/]", technician)
        table.add_row("[bold]Why[/]", ", ".join(why) or str(line.get("status", "")))
        table.add_row("[bold]Action[/]", "POST /api/dispatch/approve  (creates a scheduled work order)")
        console.print()
        console.print(Panel(table, title=f"HUMAN APPROVAL {number} of {total}", border_style="yellow", expand=False))
        self.decisions.append((args, False))
        return None

    def record_decision(self, approved: bool) -> None:
        args, _ = self.decisions[-1]
        self.decisions[-1] = (args, approved)
        mark = "[green]approved[/]" if approved else "[red]rejected[/]"
        console.print(f"  manager: {mark}")

    # ---------- the end ----------
    def finish(self) -> None:
        self._stop_live()
        self._flush_citations()
        if not self.decisions:
            return
        response = httpx.get(f"{API_URL}/api/dispatch", headers={"X-Tenant-Id": "1"}, timeout=30)
        lines = response.json().get("lines", []) if response.status_code == 200 else []
        table = Table(title="Verified in the FleetWise API (system of record), not the agent's words", title_justify="left")
        for column in ("Vehicle", "Class", "Service", "Manager decision", "Status in FleetWise now"):
            table.add_column(column)
        for args, approved in self.decisions:
            line = next((l for l in lines if l["vehicleId"] == args.get("vehicle_id") and l["serviceType"] == args.get("service_type")), {})
            status = line.get("status", "?")
            color = "green" if status == "AlreadyHandled" else "yellow"
            status = {"AlreadyHandled": "Booked (work order scheduled)", "Overdue": "Still overdue, not booked"}.get(status, status)
            table.add_row(line.get("unitNumber", str(args.get("vehicle_id"))), line.get("vehicleClass", "?"), str(args.get("service_type")),
                          "approved" if approved else "rejected", f"[{color}]{status}[/]")
        console.print()
        console.print(table)
        console.print("[dim]Read live from GET /api/dispatch.  Trace: Foundry portal > Agents > fleet-workorder > Traces[/]")


def _args(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    try:
        return json.loads(arguments or "{}")
    except (TypeError, ValueError):
        return {}


def _fmt_args(args: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in args.items())


def _summarize(name: str, result: str) -> str:
    try:
        data = json.loads(result)
    except ValueError:
        data = None
    if name == "get_dispatch_lines" and isinstance(data, list):
        return f"{len(data)} open maintenance lines"
    if name == "list_qualified_technicians" and isinstance(data, list):
        return "qualified: " + ", ".join(t["name"] for t in data)
    if "rejected by user" in result:
        return "[yellow]not booked: the manager said no, so the tool never ran[/]"
    if name == "approve_work_order":
        if result.startswith("HTTP 20"):
            return "[green]booked[/] (" + result.split(":")[0] + ")"
        return f"[red]{result[:120]}[/]"
    return result[:120]


_DISPATCH: list[dict] | None = None


def _dispatch_line(vehicle_id: Any, service_type: Any) -> dict:
    global _DISPATCH
    if _DISPATCH is None:
        try:
            _DISPATCH = httpx.get(f"{API_URL}/api/dispatch", headers={"X-Tenant-Id": "1"}, timeout=30).json()["lines"]
        except Exception:  # noqa: BLE001 - the card still renders without details
            _DISPATCH = []
    return next((l for l in _DISPATCH if l["vehicleId"] == vehicle_id and l["serviceType"] == service_type), {})
