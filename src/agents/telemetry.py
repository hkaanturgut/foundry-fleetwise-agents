"""Token consumption telemetry: every run is one trace in Application Insights.

Foundry already writes a server-side `chat` span with gen_ai.usage.input_tokens / output_tokens for
every model call an agent makes, into the Application Insights resource connected to the project.
This module adds the client side: the Agent Framework's OpenTelemetry spans, under one root span per
run (`fleetwise.run`, with the script and manager). Trace context flows to Foundry, so the server
spans share the run's operation id. At the end it prints a per-agent token table.

The dashboard is the "FleetWise token usage" workbook (scripts/setup-monitoring.sh).
Set FLEETWISE_TELEMETRY=off to run without it.

Usage:
    with telemetry.run("maf_workflow", manager="kaan"):
        ...
"""

from __future__ import annotations

import os
import uuid
from collections import defaultdict
from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace

INPUT, OUTPUT = "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"

# Per agent: [responses, input tokens, output tokens] for the terminal summary. Counted from the
# usage each response reports, the same numbers Foundry records on its server-side chat spans.
_tally: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])


def count(agent: str, usage: dict | None) -> None:
    """Add one model response's usage (Agent Framework usage_details) to the summary."""
    if usage:
        row = _tally[agent]
        row[0] += 1
        row[1] += int(usage.get("input_token_count") or 0)
        row[2] += int(usage.get("output_token_count") or 0)


def _configure() -> bool:
    if os.environ.get("FLEETWISE_TELEMETRY", "").lower() == "off":
        return False
    try:
        from agent_framework.observability import enable_instrumentation
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry.sdk.resources import Resource

        from .common import project

        connection = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING") or (
            project().telemetry.get_application_insights_connection_string()
        )
        configure_azure_monitor(
            connection_string=connection,
            resource=Resource.create({"service.name": "fleetwise-agents"}),
            enable_live_metrics=False,
            sampling_ratio=1.0,  # keep every span: the default rate-limited sampler can drop the run root
        )
        enable_instrumentation()
        return True
    except Exception as error:  # telemetry must never break the demo
        print(f"(telemetry off: {error})")
        return False


def record_usage(agent: str, version: str | None, usage) -> None:
    """One invoke_agent span for calls made with the plain OpenAI client (outside Agent Framework)."""
    tracer = trace.get_tracer("fleetwise")
    with tracer.start_as_current_span(f"invoke_agent {agent}") as span:
        span.set_attribute("gen_ai.operation.name", "invoke_agent")
        span.set_attribute("gen_ai.agent.name", agent)
        if version:
            span.set_attribute("gen_ai.agent.version", version)
        if usage is not None:
            span.set_attribute(INPUT, usage.input_tokens)
            span.set_attribute(OUTPUT, usage.output_tokens)
            count(agent, {"input_token_count": usage.input_tokens, "output_token_count": usage.output_tokens})


def _print_summary(run_id: str) -> None:
    if not _tally:
        return
    from rich.console import Console
    from rich.table import Table

    table = Table(title=f"Token usage, run {run_id}", title_justify="left")
    for column in ("agent", "responses", "input", "output", "total"):
        table.add_column(column, justify="left" if column == "agent" else "right")
    totals = [0, 0, 0]
    for agent, (calls, tokens_in, tokens_out) in sorted(_tally.items()):
        table.add_row(agent, str(calls), f"{tokens_in:,}", f"{tokens_out:,}", f"{tokens_in + tokens_out:,}")
        totals = [totals[0] + calls, totals[1] + tokens_in, totals[2] + tokens_out]
    table.add_row("[b]all[/b]", str(totals[0]), f"{totals[1]:,}", f"{totals[2]:,}", f"[b]{totals[1] + totals[2]:,}[/b]")
    console = Console()
    console.print(table)
    console.print("[dim]Dashboard: Monitor > Workbooks > FleetWise token usage[/dim]")


@contextmanager
def run(script: str, **attributes: str) -> Iterator[str]:
    """Root span for one run; every agent call inside it shares the same operation id."""
    enabled = _configure()
    run_id = uuid.uuid4().hex[:8]
    tracer = trace.get_tracer("fleetwise")
    with tracer.start_as_current_span("fleetwise.run") as span:
        span.set_attribute("fleetwise.script", script)
        span.set_attribute("fleetwise.run_id", run_id)
        for key, value in attributes.items():
            span.set_attribute(f"fleetwise.{key}", value)
        yield run_id
    _print_summary(run_id)
    if enabled:
        trace.get_tracer_provider().force_flush()
