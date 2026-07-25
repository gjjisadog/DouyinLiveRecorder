param(
    [string]$Python = ""
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

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& $Python "-m" "client.build_release" "--python" $Python "--repo-root" $repoRoot
exit $LASTEXITCODE
