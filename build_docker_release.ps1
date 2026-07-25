param(
    [string]$Python = "",
    [string]$Repository = "ghcr.io/gjjisadog/douyin-live-recorder",
    [ValidateSet("daemon", "nas-web")]
    [string]$Target = "daemon",
    [switch]$Push,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Python) {
    $Python = Join-Path $repoRoot ".client-conda-env\python.exe"
}

if (-not (Test-Path $Python)) {
    Write-Host "Python executable not found: $Python" -ForegroundColor Yellow
    Write-Host "Install the client env first, then rerun this build script." -ForegroundColor Yellow
    exit 1
}

$arguments = @(
    "-m", "client.infra.docker.release",
    "buildx",
    "--repository", $Repository,
    "--target", $Target,
    "--repo-root", $repoRoot
)

if ($Push) {
    $arguments += "--push"
}
if ($DryRun) {
    $arguments += "--dry-run"
}

& $Python $arguments
exit $LASTEXITCODE
