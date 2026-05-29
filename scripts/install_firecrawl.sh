#!/bin/bash
# Installs the Firecrawl CLI in Claude Code cloud sessions.
# Runs from the SessionStart hook in .claude/settings.json.

# Only run in cloud (web) sessions; skip local machines.
if [ "$CLAUDE_CODE_REMOTE" != "true" ]; then
  exit 0
fi

# Idempotent: skip if already installed (e.g. restored from the env cache).
if command -v firecrawl >/dev/null 2>&1; then
  exit 0
fi

npm install -g firecrawl-cli || true
exit 0
