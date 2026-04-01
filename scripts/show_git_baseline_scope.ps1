param()

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$includePaths = @(
    ".agents",
    ".codex",
    ".dockerignore",
    ".env.docker.example",
    ".github",
    ".gitignore",
    "AGENTS.md",
    "CLIENT_RELEASE.md",
    "CLIENT_STORAGE_STRATEGY.md",
    "CLIENT_TASK_TRACKER.md",
    "DOCKER_FLYINNAS.md",
    "DOCKER_FLYINNAS_CHECKLIST.md",
    "DOCKER_FLYINNAS_REGRESSION.md",
    "Dockerfile",
    "LICENSE",
    "README.md",
    "StopRecording.vbs",
    "build_client_release.bat",
    "build_client_release.ps1",
    "build_docker_release.bat",
    "build_docker_release.ps1",
    "client",
    "config",
    "demo.py",
    "deploy_flyinnas.ps1",
    "deploy_flyinnas.sh",
    "docker-compose.flyinnas.yaml",
    "docker-compose.yaml",
    "docs",
    "environment.client.yml",
    "ffmpeg_install.py",
    "i18n",
    "i18n.py",
    "index.html",
    "main.py",
    "msg_push.py",
    "prompts",
    "requirements.client-build.txt",
    "requirements.docker.txt",
    "requirements.txt",
    "scripts",
    "src",
    "start_client.bat",
    "start_client.ps1"
)

$existing = $includePaths | Where-Object { Test-Path $_ }

Write-Host "Recommended baseline include paths:" -ForegroundColor Cyan
$existing | ForEach-Object { Write-Host "  git add -- $_" }

Write-Host ""
Write-Host "Recommended excluded paths are controlled by .gitignore, including:" -ForegroundColor Cyan
@(
    ".client-conda-env/",
    "build/",
    "dist/",
    "downloads/",
    "logs/",
    "backup_config/",
    "client_data/",
    "tmp*/",
    "tmp_*.log"
) | ForEach-Object { Write-Host "  $_" }

Write-Host ""
Write-Host "Before creating a first recovery commit, re-check these orphan paths manually:" -ForegroundColor Yellow
@(
    "deploy/",
    "tmp7qf85p61/",
    "tmpbape0idz/"
) | ForEach-Object { Write-Host "  $_" }
