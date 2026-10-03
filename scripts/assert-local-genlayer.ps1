[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$expectedVersion = "0.39.1"
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$binary = Join-Path $repositoryRoot "node_modules\.bin\genlayer.cmd"

if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) {
    throw "Cogent requires the repository-local GenLayer CLI at $binary. Run npm install first."
}

$resolvedBinary = (Resolve-Path -LiteralPath $binary).Path
$actualVersion = (& $resolvedBinary --version | Select-Object -First 1).Trim()
Write-Host "Cogent local GenLayer CLI: $resolvedBinary"
Write-Host "Cogent local GenLayer version: $actualVersion"

if ($actualVersion -ne $expectedVersion) {
    throw "Cogent requires local GenLayer CLI $expectedVersion; found $actualVersion at $resolvedBinary."
}
