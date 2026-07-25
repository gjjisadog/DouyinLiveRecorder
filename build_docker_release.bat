@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "PYTHON=%REPO_ROOT%.client-conda-env\python.exe"
set "REPOSITORY=ghcr.io/gjjisadog/douyin-live-recorder"
set "TARGET=daemon"
set "PUSH_ARG="
set "DRY_RUN_ARG="

:parse_args
if "%~1"=="" goto run
if /I "%~1"=="--repository" (
    set "REPOSITORY=%~2"
    shift
    shift
    goto parse_args
)
if /I "%~1"=="--push" (
    set "PUSH_ARG=--push"
    shift
    goto parse_args
)
if /I "%~1"=="--target" (
    set "TARGET=%~2"
    shift
    shift
    goto parse_args
)
if /I "%~1"=="--dry-run" (
    set "DRY_RUN_ARG=--dry-run"
    shift
    goto parse_args
)
shift
goto parse_args

:run
if not exist "%PYTHON%" (
    echo Python executable not found: %PYTHON%
    echo Install the client env first, then rerun this build script.
    exit /b 1
)

"%PYTHON%" -m client.infra.docker.release buildx --repository "%REPOSITORY%" --target "%TARGET%" --repo-root "%REPO_ROOT%" %PUSH_ARG% %DRY_RUN_ARG%
exit /b %ERRORLEVEL%
