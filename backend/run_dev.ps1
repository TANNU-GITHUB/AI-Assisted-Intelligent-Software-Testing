# Stable backend for Live Lab: do not reload on session file writes.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
& "..\venv\Scripts\uvicorn.exe" app:app --port 8000
