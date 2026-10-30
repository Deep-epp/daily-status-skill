# One-line install of the daily-status skill for Claude Code and/or Codex.
#   irm https://raw.githubusercontent.com/Deep-epp/daily-status-skill/main/install.ps1 | iex
# Private repo: set $env:GITHUB_TOKEN (read access) first. Works with no clone.
$Base  = "https://raw.githubusercontent.com/Deep-epp/daily-status-skill/main/plugins/daily-status/skills/daily-status"
$Files = @("SKILL.md", "scripts/collect.py")
$hdr = @{}
if ($env:GITHUB_TOKEN) { $hdr["Authorization"] = "Bearer $env:GITHUB_TOKEN" }

$targets = [ordered]@{
  "Claude Code" = Join-Path $env:USERPROFILE ".claude"
  "Codex"       = Join-Path $env:USERPROFILE ".codex"
}
$installed = 0
foreach ($name in $targets.Keys) {
  $home_ = $targets[$name]
  if (-not (Test-Path $home_)) { Write-Host "${name} not found, skipped"; continue }
  $dst = Join-Path $home_ "skills\daily-status"
  New-Item -ItemType Directory -Force (Join-Path $dst "scripts") | Out-Null
  foreach ($f in $Files) {
    Invoke-WebRequest -UseBasicParsing -Headers $hdr -Uri "$Base/$f" -OutFile (Join-Path $dst $f)
  }
  Write-Host "${name}: installed to $dst"; $installed++
}
if (-not $installed) { Write-Host "Neither Claude Code nor Codex found."; return }
if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Host "WARNING: Python 3 not found. Install it from python.org."
}
Write-Host "Restart the tools. Claude Code: /daily-status   Codex: `$daily-status"
