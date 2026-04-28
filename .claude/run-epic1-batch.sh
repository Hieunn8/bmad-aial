#!/usr/bin/env bash
set -euo pipefail

# Epic 1 non-stop orchestration checklist (manual trigger helper)
# This script prints the exact command sequence to run in Claude Code.

cat <<'EOF'
Run these commands in Claude Code, one by one:

/party-triage /bmad-dev-story Story 1.1
/party-triage /bmad-dev-story Story 1.2
/party-triage /bmad-dev-story Story 1.3
/party-triage /bmad-dev-story Story 1.4
/party-triage /bmad-dev-story Story 1.5
/party-triage /bmad-dev-story Story 1.6
/party-triage /bmad-dev-story Story 1.7
/party-triage /bmad-dev-story Story 1.8
/party-triage /bmad-dev-story Story 1.9

Stop only on hard blockers:
- tool failure
- permission denied
- required missing input
EOF
