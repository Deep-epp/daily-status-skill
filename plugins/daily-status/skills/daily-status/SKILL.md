---
name: daily-status
description: Generate the developer's daily status update (Completed / In progress / Next steps, plus Blockers when relevant) from today's git commits, working-tree state, open PRs, and Claude Code + Codex session activity on this machine. Use when the user says "daily status", "status update", "what did I do today", "standup", or invokes /daily-status.
argument-hint: "[YYYY-MM-DD] [extra repo paths...]"
allowed-tools: Bash(python *), Bash(python3 *), Bash(py *)
---

# Daily status update

Produce a management-ready status update for the current developer. The output is
shown in chat only; the developer decides where to paste it. Never send it anywhere.

## Steps

1. **Collect.** Run the bundled collector (use `python`, `python3`, or `py -3`, whichever exists):

   ```
   python "<this skill's folder>/scripts/collect.py" [--date YYYY-MM-DD] [--repos <paths>] [--root <folder>]
   ```

   `<this skill's folder>` is the directory containing this SKILL.md (`~/.claude/skills/daily-status`
   in Claude Code, `~/.codex/skills/daily-status` in Codex). The script reads both tools' session
   logs regardless of which one is running it.

   - Default window is today (local time). If the user gave a date, pass `--date`.
   - Repos are auto-discovered from today's Claude Code/Codex session folders. Pass
     `--repos` / `--root` if the user names other repos or a projects folder.
   - If the user works across a Monday gap or asks for "since Friday", use `--days N`.
   - The JSON contains `repos` (commits, uncommitted files, unpushed commits, open PRs)
     and `ai_sessions` (tool, folder, time range, truncated user prompts).

2. **Understand, don't transcribe.** Group by project/repo, then by outcome:
   - Commit subjects and session prompts are evidence of *what was worked on*. Merge
     related commits and prompts into one human-readable line per outcome.
   - If a session has prompts but no commit, it is likely investigation, review, or
     in-progress work. Say that honestly; do not claim it was completed.
   - Use ticket keys (e.g. `PROJ-123`) from branch names, commits, or prompts when present.

3. **Classify:**
   - **Completed**: committed and pushed, merged PRs, or explicitly finished tasks.
   - **In progress**: uncommitted changes, unpushed commits, open/draft PRs, unfinished sessions.
   - **Next steps**: logical follow-ups from in-progress work (review, tests, deploy,
     remaining items). Mark inferred items as "(proposed)" and ask the user to confirm or edit.
   - **Blockers**: include this section only if something in the evidence suggests one
     (failing tests/builds discussed, waiting on review/access/API, repeated retries of the
     same problem). Otherwise omit it entirely. Never invent blockers.

4. **Output format**, in this order, for the developer to review:

   ```
   Daily Status: <Name> (<YYYY-MM-DD>)

   Completed
   - [<project>] <outcome in plain language> (<ticket/PR if any>)

   In progress
   - [<project>] <what's underway and its current state>

   Next steps
   - [<project>] <planned action>

   Blockers          <- only when there are real ones
   - <blocker and what is needed to unblock>
   ```

   Style: outcomes for a non-technical manager (what changed and why it matters), not
   file names or commit hashes. One line per item, no filler, no emojis.

5. **Review gate.** After the draft, ask: "Anything to add, correct, or remove before you send this?"
   Apply edits and reprint the final version. Work done outside git/AI tools (meetings,
   calls, design discussions) is invisible to the collector, so prompt for it.

## Privacy rules

- Summaries only. Never paste raw prompts, code, file contents, or secrets into the update.
- Do not read session logs beyond what the collector outputs.
- If the collector finds nothing, say so and ask the user what they worked on instead of guessing.
