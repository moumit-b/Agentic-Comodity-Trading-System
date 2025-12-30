param(
  [string]$Question = "",
  [switch]$Force
)

$ErrorActionPreference = 'Stop'

# Load .env if present
if (Test-Path .env) {
  Get-Content .env | ForEach-Object {
    if ($_ -match '^(.*?)=(.*)$') {
      $name=$matches[1].Trim(); $value=$matches[2].Trim()
      if ($name -and $value) { Set-Item -Path Env:$name -Value $value }
    }
  }
}

$model = $env:GEMINI_MODEL
if (-not $model) { $model = 'gemini-3-pro-preview' }

$cooldown = $env:CTX_REFRESH_COOLDOWN_MINUTES
if (-not $cooldown) { $cooldown = 45 }
$cooldown = [int]$cooldown

$statePath = ".claude/.state/ctx_last_run.json"
$now = Get-Date

function ShouldRun {
  if ($Force) { return $true }
  if (-not (Test-Path $statePath)) { return $true }
  $s = Get-Content $statePath -Raw | ConvertFrom-Json
  $last = Get-Date $s.lastRun
  return ((New-TimeSpan -Start $last -End $now).TotalMinutes -ge $cooldown)
}

if (-not (ShouldRun)) {
  Write-Output "[Gemini] Skipping context pack (cooldown active)."
  exit 0
}

New-Item -Force -ItemType Directory context/local | Out-Null

$prompt = @"
You are updating project context for a Python codebase.

Read repository structure and key entrypoints. Produce:
1) context/local/repo_map.md: repo tree + important files
2) context/local/context_pack.md: current system snapshot (goals, modules, APIs, TODOs, risks)
3) context/local/decision_notes.md: open decisions and recommended next actions

If a question is provided, answer it in decision_notes.md under a section called ANSWER.

QUESTION:
$Question
"@

# Headless Gemini run
# Note: exact flags may differ by CLI version. Primary pattern is: gemini -p "..." --model ...

gemini -p "$prompt" --model "$model"

@{ lastRun = $now.ToString('o'); model = $model } | ConvertTo-Json | Set-Content $statePath
Write-Output "[Gemini] Context pack refreshed using $model"