@echo off
setlocal

set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set "PYTHON_BIN=%ROOT%\ai\.venv311\Scripts\python.exe"
if not exist "%PYTHON_BIN%" (
  set "PYTHON_BIN=%ROOT%\ai\.venv\Scripts\python.exe"
)
if not exist "%PYTHON_BIN%" (
  echo AI virtualenv is missing. Checked:
  echo   %ROOT%\ai\.venv311\Scripts\python.exe
  echo   %ROOT%\ai\.venv\Scripts\python.exe
  exit /b 1
)

if exist "%ROOT%\.env" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%\.env") do (
    if not "%%A"=="" if not "%%A:~0,1%"=="#" set "%%A=%%B"
  )
)

cd /d "%ROOT%\ai"
set "HF_HOME=%ROOT%\infra\hf_models"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
"%PYTHON_BIN%" -m uvicorn app.main:app --host 127.0.0.1 --port 8001
