@echo off
setlocal

set "ROOT=%~dp0..\.."
for %%I in ("%ROOT%") do set "ROOT=%%~fI"

set NEXT_PUBLIC_API_URL=/api/v1
set FRONTEND_BACKEND_PROXY_TARGET=http://localhost:8000

cd /d "%ROOT%\frontend"
npm run dev -- --hostname 127.0.0.1 --port 3000
