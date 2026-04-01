param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $repoRoot ".client-conda-env\\python.exe"
$entry = Join-Path $repoRoot "client\\main.py"

if (-not (Test-Path $python)) {
    Write-Host "Client env not found: $python" -ForegroundColor Yellow
    Write-Host "Create it first with:" -ForegroundColor Yellow
    Write-Host "conda create --solver classic -p `"$repoRoot\\.client-conda-env`" python=3.11 pyside6=6.9.2 pip" -ForegroundColor Yellow
    Write-Host "& `"$repoRoot\\.client-conda-env\\python.exe`" -m pip install requests loguru pycryptodome distro tqdm `"httpx[http2]`" PyExecJS" -ForegroundColor Yellow
    exit 1
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& $python $entry
exit $LASTEXITCODE
