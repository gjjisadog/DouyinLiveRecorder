param(
    [switch]$Delete,
    [switch]$IncludeEvidence
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$tmpDirs = Get-ChildItem -Path $repoRoot -Directory -Filter "tmp*" -ErrorAction SilentlyContinue | Sort-Object Name
$sessionDocs = Get-ChildItem -Path (Join-Path $repoRoot "docs\sessions") -File -ErrorAction SilentlyContinue
$sessionText = if ($sessionDocs) { ($sessionDocs | Get-Content -Raw -Encoding UTF8) -join "`n" } else { "" }

$report = foreach ($dir in $tmpDirs) {
    $isReferenced = $sessionText -match [regex]::Escape($dir.Name)
    $reason = if ($isReferenced) { "referenced-in-session-docs" } else { "unreferenced-temp-artifact" }
    $action = if ($Delete) {
        if ($IncludeEvidence -or -not $isReferenced) { "delete" } else { "preserve" }
    } else {
        if ($isReferenced) { "preserve" } else { "candidate" }
    }

    $fileCount = $null
    $totalBytes = $null
    $scanError = $null
    try {
        $files = Get-ChildItem -Path $dir.FullName -Recurse -File -Force -ErrorAction Stop
        $fileCount = @($files).Count
        $totalBytes = (@($files) | Measure-Object -Property Length -Sum).Sum
        if ($null -eq $totalBytes) { $totalBytes = 0 }
    } catch {
        $scanError = $_.Exception.Message
    }

    [PSCustomObject]@{
        Name = $dir.Name
        Action = $action
        Reason = $reason
        Referenced = $isReferenced
        FileCount = $fileCount
        TotalBytes = $totalBytes
        ScanError = $scanError
    }
}

$report | Format-Table -AutoSize

if ($Delete) {
    foreach ($item in $report | Where-Object { $_.Action -eq "delete" }) {
        $target = Join-Path $repoRoot $item.Name
        try {
            Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction Stop
            Write-Host "Deleted: $($item.Name)" -ForegroundColor Green
        } catch {
            Write-Warning "Failed to delete $($item.Name): $($_.Exception.Message)"
        }
    }
}

Write-Host ""
if ($Delete) {
    Write-Host "Done. Use -IncludeEvidence to also delete directories referenced by session docs." -ForegroundColor Cyan
} else {
    Write-Host "Dry-run only. Add -Delete to remove unreferenced tmp directories." -ForegroundColor Cyan
    Write-Host "Add -IncludeEvidence together with -Delete to also remove directories referenced by session docs." -ForegroundColor Cyan
}
