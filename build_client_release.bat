@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "PYTHON=%REPO_ROOT%.client-conda-env\python.exe"

if not exist "%PYTHON%" (
    echo Python executable not found: %PYTHON%
    echo Install the client env first, then rerun this build script.
    exit /b 1
)

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

"%PYTHON%" -m client.build_release --python "%PYTHON%" --repo-root "%REPO_ROOT%"
exit /b %ERRORLEVEL%
