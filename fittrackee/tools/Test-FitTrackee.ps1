param(
    [ValidateSet('provision','run','verify','cleanup')]
    [string]$Command = 'run',
    [switch]$Keep,
    [string]$State,
    [string]$Config,
    [string]$Python,
    [string]$Url = 'https://fittrackee.dbwalker0min.info',
    [string]$SshHost = 'ha-test',
    [string]$Container = 'app_local_fittrackee'
)
$ErrorActionPreference = 'Stop'
if (-not $Python) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython) { $Python = $bundledPython }
    else { $Python = 'python3' }
}
& $Python -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required. Specify its path using -Python.' }
$testArgs = @((Join-Path $PSScriptRoot 'live_tests.py'), $Command)
if ($Keep) { $testArgs += '--keep' }
if ($State) { $testArgs += @('--state', $State) }
if ($Config) { $testArgs += @('--config', $Config) }
$testArgs += @('--url', $Url, '--ssh-host', $SshHost, '--container', $Container)
& $Python @testArgs
exit $LASTEXITCODE
