@echo off
cd /d "%~dp0"
echo Starting AI-Testing Backend...
if exist "venv\Scripts\python.exe" (
    cd backend
    ..\venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload --reload-exclude "sessions" --reload-exclude "data"
) else (
    cd backend
    python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload --reload-exclude "sessions" --reload-exclude "data"
)
pause
