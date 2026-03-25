# Start Backend — runs preprocess + FastAPI server
Write-Host "Starting backend server..." -ForegroundColor Cyan
Set-Location "$PSScriptRoot\backend"
python preprocess.py
python -m uvicorn main:app --reload --port 8000
