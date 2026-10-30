#!/usr/bin/env bash
# One-line install of the daily-status skill for Claude Code and/or Codex.
#   curl -fsSL https://raw.githubusercontent.com/Deep-epp/daily-status-skill/main/install.sh | bash
# Private repo: export GITHUB_TOKEN (read access) first. Works with no clone.
set -e
BASE="https://raw.githubusercontent.com/Deep-epp/daily-status-skill/main/plugins/daily-status/skills/daily-status"
auth=(); [ -n "$GITHUB_TOKEN" ] && auth=(-H "Authorization: Bearer $GITHUB_TOKEN")
n=0
for t in "Claude Code:$HOME/.claude" "Codex:$HOME/.codex"; do
  name="${t%%:*}"; base="${t#*:}"
  if [ ! -d "$base" ]; then echo "$name not found, skipped"; continue; fi
  dst="$base/skills/daily-status"; mkdir -p "$dst/scripts"
  for f in SKILL.md scripts/collect.py; do curl -fsSL "${auth[@]}" "$BASE/$f" -o "$dst/$f"; done
  echo "$name: installed to $dst"; n=$((n+1))
done
[ "$n" -eq 0 ] && { echo "Neither Claude Code nor Codex found."; exit 1; }
command -v python3 >/dev/null || echo "WARNING: Python 3 not found."
echo "Restart the tools. Claude Code: /daily-status   Codex: \$daily-status"
