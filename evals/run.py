"""Run the eval cases against one fleet-triage version and print a pass/fail table.

Checks are deterministic string rules, so the same cases judge v1 and v2 identically.
Usage: python -m evals.run v1     |     python -m evals.run v2
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.agents.common import ROOT, TRIAGE, ask, project

label = sys.argv[1] if len(sys.argv) > 1 else "v2"
version = json.loads((ROOT / ".agents.json").read_text())[label]
openai = project().get_openai_client()

results = []
for line in (Path(__file__).parent / "cases.jsonl").read_text().splitlines():
    case = json.loads(line)
    answer = ask(openai, TRIAGE, case["question"], version)
    low = answer.lower()
    ok_include = any(s.lower() in low for s in case["must_include_any"]) if case["must_include_any"] else True
    bad = [s for s in case["must_not_include"] if s.lower() in low]
    passed = ok_include and not bad
    results.append((case["suite"], case["id"], passed, bad, answer))
    print(f"{'PASS' if passed else 'FAIL'}  {case['suite']:10} {case['id']:12}" + (f"  (found: {bad})" if bad else ""))

out = ROOT / "evals" / f"results-{label}.json"
out.write_text(json.dumps([{"suite": s, "id": i, "passed": p, "violations": b, "answer": a} for s, i, p, b, a in results], indent=2))
by_suite = {}
for suite, _, passed, _, _ in results:
    by_suite.setdefault(suite, []).append(passed)
print("\n" + "  ".join(f"{s}: {sum(v)}/{len(v)}" for s, v in by_suite.items()) + f"   (details: {out.name})")
