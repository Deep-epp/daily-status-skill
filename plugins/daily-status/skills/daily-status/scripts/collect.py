#!/usr/bin/env python3
"""Collect a developer's raw activity for a day: git commits, working-tree state,
open PRs (if `gh` exists), and Claude Code / Codex session activity.

Prints one JSON document to stdout. Nothing is sent anywhere. Raw prompts are
truncated and secret-looking strings are redacted; the skill turns this into a
summary the developer reviews before using.

Usage:
  collect.py [--date YYYY-MM-DD] [--days N] [--repos PATH ...] [--author EMAIL]
             [--root PATH ...] [--prompt-chars 200]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude" / "projects"
CODEX_DIR = HOME / ".codex" / "sessions"

SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    r"xox[abp]-[A-Za-z0-9\-]{10,}|eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+|"
    r"(?i:(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S+))"
)
NOISE_PREFIXES = ("<", "Caveat:", "[Request interrupted", "# AGENTS.md", "<environment_context")


def run(cmd, cwd=None, timeout=30):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def clean(text, limit):
    text = SECRET_RE.sub("[redacted]", " ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def parse_ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def find_repo_root(path):
    p = Path(path)
    while True:
        if (p / ".git").exists():
            return p
        if p.parent == p:
            return None
        p = p.parent


# ---------------------------------------------------------------- sessions
def user_texts_claude(obj):
    if obj.get("type") != "user" or obj.get("isSidechain") or obj.get("isMeta"):
        return []
    content = obj.get("message", {}).get("content")
    if isinstance(content, str):
        return [content]
    return [c.get("text", "") for c in content or []
            if isinstance(c, dict) and c.get("type") == "text"]


def user_texts_codex(obj):
    p = obj.get("payload") or {}
    if obj.get("type") == "event_msg" and p.get("type") == "user_message":
        return [p.get("message", "")]
    return []


def scan_sessions(base, tool, start, end, prompt_chars):
    out = []
    if not base.exists():
        return out
    floor = start.timestamp() - 86400
    for f in base.rglob("*.jsonl"):
        try:
            if f.stat().st_mtime < floor:
                continue
        except OSError:
            continue
        cwd, prompts, first, last, turns = None, [], None, None, 0
        try:
            with f.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        continue
                    ts = parse_ts(obj.get("timestamp"))
                    if tool == "codex" and obj.get("type") == "session_meta":
                        cwd = (obj.get("payload") or {}).get("cwd") or cwd
                    if tool == "claude-code":
                        cwd = obj.get("cwd") or cwd
                    if not ts or not (start <= ts < end):
                        continue
                    first = first or ts
                    last = ts
                    texts = user_texts_claude(obj) if tool == "claude-code" else user_texts_codex(obj)
                    for t in texts:
                        t = t.strip()
                        if t and not t.startswith(NOISE_PREFIXES):
                            turns += 1
                            if len(prompts) < 12:
                                prompts.append(clean(t, prompt_chars))
        except OSError:
            continue
        if turns:
            out.append({"tool": tool, "cwd": cwd, "session": f.stem[:8],
                        "first": first.astimezone().strftime("%H:%M"),
                        "last": last.astimezone().strftime("%H:%M"),
                        "user_turns": turns, "prompts": prompts})
    return out


# --------------------------------------------------------------------- git
def git_info(repo, start, end, author):
    fmt = "%h\x1f%an\x1f%ad\x1f%s"
    base = ["git", "log", "--all", "--no-merges", f"--since={start.isoformat()}",
            f"--until={end.isoformat()}", "--date=format-local:%H:%M",
            f"--pretty=format:{fmt}", "--shortstat"]
    if author:
        base.append(f"--author={author}")
    raw = run(base, cwd=repo)
    commits, cur = [], None
    for line in raw.splitlines():
        if "\x1f" in line:
            h, an, at, subj = line.split("\x1f", 3)
            cur = {"hash": h, "time": at, "subject": clean(subj, 200), "stat": ""}
            commits.append(cur)
        elif line.strip() and cur:
            cur["stat"] = line.strip()
    status = run(["git", "status", "--porcelain"], cwd=repo)
    changed = [l for l in status.splitlines() if l.strip()]
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    unpushed = run(["git", "log", "--oneline", "@{u}..HEAD"], cwd=repo)
    info = {
        "repo": repo.name, "path": str(repo), "branch": branch,
        "remote": re.sub(r"//[^@/]+@", "//", run(["git", "remote", "get-url", "origin"], cwd=repo)),
        "commits": commits,
        "uncommitted_files": len(changed),
        "uncommitted_sample": [l[3:] for l in changed[:10]],
        "unpushed_commits": len(unpushed.splitlines()) if unpushed else 0,
    }
    return info


def open_prs(repo):
    if not run(["gh", "--version"]):
        return []
    raw = run(["gh", "pr", "list", "--author", "@me", "--state", "open",
               "--json", "number,title,url,isDraft,reviewDecision"], cwd=repo, timeout=20)
    try:
        return json.loads(raw) if raw else []
    except ValueError:
        return []


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap =argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (local). Default: today")
    ap.add_argument("--days", type=int, default=1, help="window length ending on --date")
    ap.add_argument("--repos", nargs="*", default=[], help="extra repo paths")
    ap.add_argument("--root", nargs="*", default=[], help="folders to scan one level deep for repos")
    ap.add_argument("--author", help="git author filter (default: git config user.email)")
    ap.add_argument("--prompt-chars", type=int, default=200)
    a = ap.parse_args()

    day = datetime.strptime(a.date, "%Y-%m-%d") if a.date else datetime.now()
    end = day.replace(hour=0, minute=0, second=0, microsecond=0).astimezone() + timedelta(days=1)
    start = end - timedelta(days=a.days)
    author = a.author or run(["git", "config", "--global", "user.email"])

    sessions = (scan_sessions(CLAUDE_DIR, "claude-code", start, end, a.prompt_chars)
                + scan_sessions(CODEX_DIR, "codex", start, end, a.prompt_chars))

    repos = {}
    def add(p):
        r = find_repo_root(p) if p and Path(p).exists() else None
        if r:
            repos[str(r).lower()] = r
    for s in sessions:
        add(s["cwd"])
    for p in a.repos:
        add(p)
    for root in a.root:
        rp = Path(root)
        if rp.is_dir():
            for child in rp.iterdir():
                if (child / ".git").exists():
                    add(child)

    report = {
        "window": {"from": start.strftime("%Y-%m-%d %H:%M"), "to": end.strftime("%Y-%m-%d %H:%M")},
        "author": author, "machine_user": os.environ.get("USERNAME") or os.environ.get("USER"),
        "repos": [], "ai_sessions": sessions,
    }
    for r in repos.values():
        info = git_info(r, start, end, author)
        info["open_prs"] = open_prs(r)
        if info["commits"] or info["uncommitted_files"] or info["unpushed_commits"] or info["open_prs"] \
                or any(s["cwd"] and find_repo_root(s["cwd"]) == r for s in sessions):
            report["repos"].append(info)
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
