@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "PYTHON=%REPO_ROOT%.client-conda-env\python.exe"
set "ENTRY=%REPO_ROOT%client\main.py"

if not exist "%PYTHON%" (
    echo Client env not found: %PYTHON%
    echo Create it first with `start_client.ps1` or `environment.client.yml`.
    exit /b 1
)

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

"%PYTHON%" "%ENTRY%"
exit /b %ERRORLEVEL%
