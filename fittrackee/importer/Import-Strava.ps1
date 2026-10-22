# Pass through the Python CLI arguments without executing them as shell text.
$ErrorActionPreference = 'Stop'
$runnerPython = $env:FITTRACKEE_PYTHON
if (-not $runnerPython) {
    $bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundledPython) { $runnerPython = $bundledPython }
    else { $runnerPython = 'python3' }
}
& $runnerPython -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ required. Set FITTRACKEE_PYTHON to its executable path.' }
& $runnerPython (Join-Path $PSScriptRoot 'strava_import.py') @args
exit $LASTEXITCODE
