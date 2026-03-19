@echo off
cd /d e:\fitcheck_ai\fitcheck_ai\backend
set PYTHONPATH=e:\fitcheck_ai\fitcheck_ai\backend
e:\fitcheck_ai\fitcheck_ai\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000 --host 0.0.0.0
