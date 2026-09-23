# Optional project-local compiler: extract the official installer, NEVER execute it.
param([string]$SevenZip = 'C:\Program Files\7-Zip\7z.exe')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$downloadDir = Join-Path $projectRoot 'vendor/llvm-download'
$compilerDir = Join-Path $projectRoot 'vendor/llvm-20.1.8'
$archive = Join-Path $downloadDir 'LLVM-20.1.8-win64.exe'
$expectedHash = '3197846a2b19063687dd56e93e34cd941e3548d907f23a6131571321bdf9fe7b'
if (-not (Test-Path -LiteralPath $SevenZip -PathType Leaf)) { throw '7-Zip is required for extraction; no installer will be run.' }
New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null
if (-not (Test-Path -LiteralPath $archive)) {
    Invoke-WebRequest -Uri 'https://github.com/llvm/llvm-project/releases/download/llvmorg-20.1.8/LLVM-20.1.8-win64.exe' -OutFile $archive
}
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
    throw 'LLVM download hash mismatch. Preserve and inspect the download; do not execute it.'
}
if (-not (Test-Path -LiteralPath (Join-Path $compilerDir 'bin/clang-cl.exe'))) {
    if (Test-Path -LiteralPath $compilerDir) { throw "Partial/existing compiler directory: $compilerDir. Inspect it before retrying." }
    & $SevenZip x $archive "-o$compilerDir" -bso0
    if ($LASTEXITCODE -ne 0) { throw "7-Zip failed: $LASTEXITCODE" }
}
& (Join-Path $compilerDir 'bin/clang-cl.exe') --version
if ($LASTEXITCODE -ne 0) { throw 'Extracted clang-cl cannot run' }
Write-Output "Compiler ready: $compilerDir/bin; no registry or global PATH changes."
