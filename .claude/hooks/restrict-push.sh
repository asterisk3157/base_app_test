#!/bin/bash
# Restrict git push to only the "hi" branch.
# Exit code 2 = block the command with feedback to Claude.

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command')

# Only inspect git push commands
if echo "$COMMAND" | grep -qE '^\s*git\s+push'; then
  # Allow: git push origin hi, git push -u origin hi, etc.
  if echo "$COMMAND" | grep -qE 'git\s+push\s+.*\bhi\b'; then
    exit 0
  fi
  # Block everything else
  echo "BLOCKED: Push is only allowed to the 'hi' branch. Use: git push origin hi" >&2
  exit 2
fi

exit 0
