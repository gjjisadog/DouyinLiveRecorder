[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$RepoRoot
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $scriptPath = $PSCommandPath
    if (-not $scriptPath) {
        $scriptPath = $MyInvocation.MyCommand.Path
    }
    if (-not $scriptPath) {
        throw "Unable to determine script path."
    }
    $RepoRoot = (Resolve-Path (Join-Path (Split-Path -Parent $scriptPath) "..")).Path
}

$allowedNames = @(
    "tmp7qf85p61",
    "tmpbape0idz"
)

Write-Host "RepoRoot: $RepoRoot"

foreach ($name in $allowedNames) {
    $target = Join-Path $RepoRoot $name
    if (-not $target.StartsWith($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to touch path outside repo root: $target"
    }

    if (-not (Test-Path -LiteralPath $target)) {
        Write-Host "Skip missing: $target"
        continue
    }

    if (-not $PSCmdlet.ShouldProcess($target, "Take ownership, grant Administrators full control, and delete orphan directory")) {
        continue
    }

    Write-Host "Cleaning: $target"
    & takeown.exe /F $target /R /D Y | Out-Host
    & icacls.exe $target /grant Administrators:F /T /C | Out-Host
    & attrib.exe -R -S -H "$target" /S /D | Out-Host
    & cmd.exe /c "rd /s /q ""$target"""

    if (Test-Path -LiteralPath $target) {
        throw "Delete failed: $target"
    }

    Write-Host "Removed: $target"
}

Write-Host "Done."
