param(
    [string]$Python = "",
    [string]$RemoteHost = "",
    [string]$User = "",
    [int]$Port = 22,
    [string]$RemoteDir = "/vol1/docker/douyin-live-recorder",
    [ValidateSet("first-deploy", "upgrade-deploy", "rollback-deploy")]
    [string]$Scenario = "first-deploy",
    [string]$RemotePython = "python3",
    [string]$ExpectedTag = "4.0.7",
    [string]$ImageRepository = "",
    [string]$IdentityFile = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Python) {
    $embeddedPython = Join-Path $repoRoot ".client-conda-env\python.exe"
    if (Test-Path $embeddedPython) {
        $Python = $embeddedPython
    } else {
        $Python = "python"
    }
}

$arguments = @(
    "-m", "client.infra.docker.flyinnas_deploy",
    "--host", $RemoteHost,
    "--user", $User,
    "--port", "$Port",
    "--remote-dir", $RemoteDir,
    "--scenario", $Scenario,
    "--remote-python", $RemotePython,
    "--expected-tag", $ExpectedTag,
    "--repo-root", $repoRoot
)

if ($ImageRepository) {
    $arguments += @("--image-repository", $ImageRepository)
}
if ($IdentityFile) {
    $arguments += @("--identity-file", $IdentityFile)
}
if ($DryRun) {
    $arguments += "--dry-run"
}

& $Python $arguments
exit $LASTEXITCODE
