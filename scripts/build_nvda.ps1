param([int]$Jobs = 2, [string]$LlvmBin = '', [switch]$UseSpectreAtlFallback,
    [ValidateSet('2026.2', '2026.3beta2')][string]$NvdaVersion = '2026.2')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$nvdaRoot = Join-Path $projectRoot "vendor/nvda-$NvdaVersion"
if ($Jobs -lt 1) { throw 'Jobs must be positive' }
if ($LlvmBin) {
    $LlvmBin = (Resolve-Path -LiteralPath $LlvmBin).Path
    if (-not (Test-Path -LiteralPath (Join-Path $LlvmBin 'clang-cl.exe'))) { throw 'LlvmBin must contain clang-cl.exe' }
    $env:PATH = "$LlvmBin;$env:PATH"
    $env:CONTEXTUAL_PRONUNCIATION_LLVM_BIN = $LlvmBin
}
# A private uv-managed Python matches NVDA's pin; nothing replaces system Python.
# Run in the pinned tool's environment so upstream ensureuv never self-updates
# the user's uv installation. uv tool run prepends its cached executable to PATH.
if ($NvdaVersion -eq '2026.3beta2' -and (& uv --version) -notmatch '^uv 0\.12\.5\b') {
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath,
        '-NvdaVersion', $NvdaVersion, '-Jobs', "$Jobs")
    if ($LlvmBin) { $arguments += @('-LlvmBin', $LlvmBin) }
    if ($UseSpectreAtlFallback) { $arguments += '-UseSpectreAtlFallback' }
    & uv tool run --from uv==0.12.5 powershell.exe @arguments
    exit $LASTEXITCODE
}
$nvdaPythonSpec = (Get-Content -LiteralPath (Join-Path $nvdaRoot '.python-versions') -Raw).Trim()
& uv python install $nvdaPythonSpec
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare pinned Python' }
$env:UV_PYTHON = (& uv python find --python-preference only-managed $nvdaPythonSpec).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Pinned Python not found' }
$env:UV_FROZEN = 'true'
$env:UV_LINK_MODE = 'copy'
if ($UseSpectreAtlFallback) {
    if (-not $LlvmBin) { throw 'Spectre ATL adapter requires the explicit local LLVM site adapter' }
    $env:CONTEXTUAL_PRONUNCIATION_SPECTRE_ATL = '1'
}
Push-Location -LiteralPath $nvdaRoot
try {
    $sconsArguments = @('source', '-j', "$Jobs")
    if ($LlvmBin) { $sconsArguments += @('--site-dir', (Join-Path $PSScriptRoot 'nvda_scons')) }
    & .\scons.bat @sconsArguments
    if ($LASTEXITCODE -ne 0) { throw "NVDA native source build failed: $LASTEXITCODE" }
}
finally { Pop-Location }
