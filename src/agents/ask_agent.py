"""Ask a FleetWise agent one question.  Usage: python -m src.agents.ask_agent <stage1|stage2|v1|v2> "question" """

import json
import sys

from .common import ROOT, TRIAGE, ask, project

label, question = sys.argv[1], sys.argv[2]
version = json.loads((ROOT / ".agents.json").read_text())[label]
print(ask(project().get_openai_client(), TRIAGE, question, version))
