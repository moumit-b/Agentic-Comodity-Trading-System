$ErrorActionPreference = 'Stop'

Write-Output "[QA] ruff check"
ruff check .

Write-Output "[QA] ruff format"
ruff format .

Write-Output "[QA] pytest"
pytest -q

Write-Output "[QA] OK"