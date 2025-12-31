param([Parameter(Mandatory=$true)][string]$Question)

New-Item -Force -ItemType Directory context/local | Out-Null

.\scripts\gemini_context_pack.ps1 -Question $Question -Force