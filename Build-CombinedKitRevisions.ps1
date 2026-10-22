param([string]$WeiDU = '')
$ErrorActionPreference = 'Stop'
$buildArgs = @((Join-Path $PSScriptRoot 'tools/build.py'))
if ($WeiDU) { $buildArgs += @('--weidu', (Resolve-Path -LiteralPath $WeiDU).Path) }
Push-Location $PSScriptRoot
try {
    & py @buildArgs
    if ($LASTEXITCODE -ne 0) { throw 'Combined Kit Revisions build failed.' }
    Write-Host 'Package ready in build/package. Copy its contents to a fresh BG2EE/EET build.'
} finally { Pop-Location }
