"""Cloud evaluation in Microsoft Foundry.

Foundry sends each test query to the hosted agent version itself (target completions),
then built-in evaluators score every answer: LLM judges for quality, a classifier for safety.
Results appear in the Foundry portal under Evaluations; the link is printed here.

Usage: python -m evals.foundry_eval v2 | latest | <version number> [--min-pass-rate 0.8]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from src.agents.common import MODEL, TRIAGE, project, resolve_version

JUDGED = ["task_adherence", "intent_resolution", "relevance", "coherence"]  # LLM-judge evaluators
SAFETY = ["violence"]  # content-safety evaluator, no judge model needed


def criteria() -> list[dict]:
    items = []
    for name in JUDGED + SAFETY:
        criterion = {
            "type": "azure_ai_evaluator",
            "name": name,
            "evaluator_name": f"builtin.{name}",
            "data_mapping": {
                "query": "{{item.query}}",
                # task adherence judges the full output (tool calls included), the rest judge the text
                "response": "{{sample.output_items}}" if name == "task_adherence" else "{{sample.output_text}}",
            },
        }
        if name in JUDGED:
            criterion["initialization_parameters"] = {"deployment_name": MODEL}
        items.append(criterion)
    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("label", nargs="?", default="v2")
    parser.add_argument("--min-pass-rate", type=float, default=0.8)
    args = parser.parse_args()

    version = resolve_version(args.label)
    queries = [json.loads(l)["question"] for l in (Path(__file__).parent / "cases.jsonl").read_text().splitlines()]
    openai = project().get_openai_client()

    evaluation = openai.evals.create(
        name=f"{TRIAGE}-{args.label}",
        data_source_config={
            "type": "custom",
            "item_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            "include_sample_schema": True,
        },
        testing_criteria=criteria(),
    )
    run = openai.evals.runs.create(
        eval_id=evaluation.id,
        name=f"{TRIAGE} v{version}",
        data_source={
            "type": "azure_ai_target_completions",
            "source": {"type": "file_content", "content": [{"item": {"query": q}} for q in queries]},
            "input_messages": {
                "type": "template",
                "template": [{"type": "message", "role": "user", "content": {"type": "input_text", "text": "{{item.query}}"}}],
            },
            "target": {"type": "azure_ai_agent", "name": TRIAGE, "version": version},
        },
    )
    print(f"Foundry cloud eval: {TRIAGE} version {version} ({args.label}) | {len(queries)} queries | {', '.join(JUDGED + SAFETY)}")
    while run.status not in ("completed", "failed", "canceled"):
        time.sleep(10)
        run = openai.evals.runs.retrieve(run_id=run.id, eval_id=evaluation.id)
        print(f"  status: {run.status}")

    if run.status != "completed":
        print(f"Run {run.status}: {getattr(run, 'error', None)}")
        return 1
    for result in run.per_testing_criteria_results or []:
        print(f"  {result.testing_criteria:20} passed {result.passed}/{result.passed + result.failed}")
    counts = run.result_counts
    rate = counts.passed / counts.total if counts.total else 0
    print(f"rows passed (all evaluators): {counts.passed}/{counts.total}")
    print(f"portal: {run.report_url}")
    ok = rate >= args.min_pass_rate
    print(f"GATE {'PASS' if ok else 'FAIL'}: {rate:.0%} (min {args.min_pass_rate:.0%})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
