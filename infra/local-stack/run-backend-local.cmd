@echo off
setlocal

set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set DATABASE_URL=postgresql+asyncpg://hiringos@localhost:56432/hiringos
set REDIS_URL=redis://localhost:6379/0
set CELERY_BROKER_URL=memory://
set CELERY_RESULT_BACKEND=cache+memory://
set MINIO_ENDPOINT=localhost:9000
set MINIO_ACCESS_KEY=minioadmin
set MINIO_SECRET_KEY=minioadmin
set MINIO_SECURE=false
set AI_SERVICE_URL=http://localhost:8001
set CORS_ORIGINS=http://localhost:3000

set "PYTHON_BIN=%ROOT%\backend\.venv\Scripts\python.exe"
if not exist "%PYTHON_BIN%" (
  echo backend virtualenv is missing: %PYTHON_BIN%
  exit /b 1
)

cd /d "%ROOT%\backend"
"%PYTHON_BIN%" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
