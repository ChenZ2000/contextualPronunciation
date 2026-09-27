<#
.SYNOPSIS
Remove reproducible project caches; optionally archive old outputs locally.
.EXAMPLE
pwsh -File scripts/clean_workspace.ps1 -WhatIf
.EXAMPLE
pwsh -File scripts/clean_workspace.ps1 -ArchiveOutputs
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param([switch]$ArchiveOutputs)

$ErrorActionPreference = 'Stop'
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$workspacePrefix = $workspaceRoot.TrimEnd('\') + '\'
$changes = [System.Collections.Generic.List[object]]::new()

function Assert-WorkspacePath([string]$Path) {
    $resolved = [IO.Path]::GetFullPath($Path)
    if (-not $resolved.StartsWith($workspacePrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing a path outside the workspace: $resolved"
    }
    # Do not traverse a junction/symlink, including any ancestor.
    $probe = $resolved
    while ($probe -ne $workspaceRoot) {
        if (Test-Path -LiteralPath $probe) {
            $item = Get-Item -LiteralPath $probe -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Refusing a reparse point: $probe"
            }
        }
        $probe = [IO.Path]::GetDirectoryName($probe)
    }
    return $resolved
}

$cachePaths = [System.Collections.Generic.List[string]]::new()
foreach ($name in @('.ruff_cache', '.pytest_cache', '.mypy_cache', '__pycache__')) {
    $candidate = Join-Path $workspaceRoot $name
    if (Test-Path -LiteralPath $candidate) { $cachePaths.Add($candidate) }
}
foreach ($name in @('addon', 'tests', 'tools', 'scripts', 'diagnostics')) {
    $sourceRoot = Assert-WorkspacePath (Join-Path $workspaceRoot $name)
    if (Test-Path -LiteralPath $sourceRoot) {
        Get-ChildItem -LiteralPath $sourceRoot -Directory -Recurse -Force |
            Where-Object { $_.Name -eq '__pycache__' } |
            ForEach-Object { $cachePaths.Add($_.FullName) }
    }
}
foreach ($candidate in $cachePaths) {
    $target = Assert-WorkspacePath $candidate
    $files = @(Get-ChildItem -LiteralPath $target -File -Recurse -Force)
    $bytes = ($files | Measure-Object -Property Length -Sum).Sum
    if ($PSCmdlet.ShouldProcess($target, 'Remove reproducible cache')) {
        Remove-Item -LiteralPath $target -Recurse -Force
        $changes.Add([pscustomobject]@{ action = 'remove-cache'; path = $target; files = $files.Count; bytes = $bytes })
    }
}

if ($ArchiveOutputs) {
    $archiveRoot = Assert-WorkspacePath (Join-Path $workspaceRoot ('local/archive/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff')))
    foreach ($name in @('artifacts', 'dist')) {
        $source = Assert-WorkspacePath (Join-Path $workspaceRoot $name)
        $destination = Assert-WorkspacePath (Join-Path $archiveRoot $name)
        if ((Test-Path -LiteralPath $source) -and $PSCmdlet.ShouldProcess($source, "Archive to $destination")) {
            New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
            # Same-volume atomic directory rename. Move-Item can recursively
            # move a subset before failing on hidden/read-only Git metadata.
            [IO.Directory]::Move($source, $destination)
            New-Item -ItemType Directory -Path $source | Out-Null
            $changes.Add([pscustomobject]@{ action = 'archive'; path = $source; destination = $destination })
        }
    }
}

if ($changes.Count) {
    $reportRoot = Assert-WorkspacePath (Join-Path $workspaceRoot 'local/maintenance')
    New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null
    $report = Join-Path $reportRoot ('cleanup-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.json')
    @($changes) | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $report -Encoding utf8
    Write-Output "Cleanup record: $report"
    $changes | Format-Table -AutoSize
}
