"""Ask a FleetWise agent one question.  Usage: python -m src.agents.ask_agent <stage1|stage2|v1|v2|live_naive|live_hardened|number> "question" """

import sys

from .common import TRIAGE, ask, project, resolve_version

label, question = sys.argv[1], sys.argv[2]
version = resolve_version(label)
print(ask(project().get_openai_client(), TRIAGE, question, version))
