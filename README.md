# daily-status skill

Drafts your daily status update (Completed / In progress / Next steps, plus Blockers when relevant)
from your git commits and Claude Code + Codex sessions. Summaries only; you review before sharing.

## Install (Claude Code and/or Codex, whichever you have)

Windows (PowerShell):

    irm https://raw.githubusercontent.com/Deep-epp/daily-status-skill/main/install.ps1 | iex

Mac / Linux:

    curl -fsSL https://raw.githubusercontent.com/Deep-epp/daily-status-skill/main/install.sh | bash

Restart the tools, then run `/daily-status` in Claude Code or `$daily-status` in Codex.
Requires Python 3 and git. Re-run the install command to update.
