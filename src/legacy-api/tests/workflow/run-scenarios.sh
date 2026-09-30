#!/usr/bin/env bash
# Rehearses the sdd-autopilot workflow against a throwaway copy of this repo,
# using a stub Copilot CLI, and asserts which Spec Kit steps ran in each scenario.
#
# Requires: specify (Spec Kit CLI), git, python3, dotnet.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
STUB_DIR="$WORK/bin"
export STUB_LOG="$WORK/calls.log"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$STUB_DIR"
cp "$REPO/tests/workflow/stub-copilot" "$STUB_DIR/copilot"
chmod +x "$STUB_DIR/copilot"
export PATH="$STUB_DIR:$PATH"

git -C "$REPO" ls-files -z | (cd "$REPO" && xargs -0 tar -cf -) | (mkdir -p "$WORK/repo" && tar -xf - -C "$WORK/repo")
cd "$WORK/repo"
git init -q -b main
git config user.email "ci@example.com"
git config user.name "ci"
git add -A && git commit -qm "baseline"

specify init --here --force --integration copilot --ignore-agent-tools >/dev/null
specify workflow add --dev ./workflows/sdd-autopilot >/dev/null

fail=0
run() { : > "$STUB_LOG"; specify workflow run sdd-autopilot "$@" < /dev/null > "$WORK/run.out" 2>&1 || true; }
calls() { paste -sd' ' "$STUB_LOG" 2>/dev/null || true; }
status() { grep -o 'Status: [a-z]*' "$WORK/run.out" | awk '{print $2}' | tail -1; }
expect() {
  local name="$1" want_calls="$2" want_status="$3"
  local got_calls got_status
  got_calls="$(calls)"; got_status="$(status)"
  if [[ "$got_calls" == "$want_calls" && "$got_status" == "$want_status" ]]; then
    echo "PASS  $name  [$got_status] $got_calls"
  else
    echo "FAIL  $name"; echo "      want [$want_status] $want_calls"; echo "      got  [$got_status] $got_calls"
    sed 's/^/      | /' "$WORK/run.out" | tail -15
    fail=1
  fi
}

# A: template constitution -> the run stops at the constitution gate.
run -i approval=approve
expect "A no constitution stops" "" "paused"

printf '# FleetWise Constitution\n\n## Principles\n\n1. Tenant isolation is mandatory.\n' > .specify/memory/constitution.md
git add -A && git commit -qm "constitution"

# B: empty feature, build until converged.
run -i until=converge -i approval=approve -i spec="Overdue dispatcher"
expect "B full run" "/speckit-specify /speckit-plan /speckit-tasks /speckit-analyze /speckit-implement /speckit-converge" "completed"
git add -A && git commit -qm "feature"

# C: spec changed -> only plan, tasks, analyze.
echo "- The overdue window is configurable per tenant (default 7 days)." >> specs/001-overdue-dispatcher/spec.md
run -i approval=approve
expect "C spec change reruns only stale steps" "/speckit-plan /speckit-tasks /speckit-analyze" "completed"
git add -A && git commit -qm "spec change"

# D: nothing changed -> only analyze (always runs) and the gate.
run -i approval=approve
expect "D nothing stale" "/speckit-analyze" "completed"

# E: open question in the spec -> pauses at the clarify gate before anything else.
echo "[NEEDS CLARIFICATION: who can approve a work order?]" >> specs/001-overdue-dispatcher/spec.md
run -i approval=approve
expect "E open question pauses for a human" "" "paused"

exit $fail
