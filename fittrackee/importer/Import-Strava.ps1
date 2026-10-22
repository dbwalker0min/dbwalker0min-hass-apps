# uv manages the importer environment; caller-relative data paths stay unchanged.
$ErrorActionPreference = 'Stop'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/'
}
& uv run --locked --project $PSScriptRoot python (Join-Path $PSScriptRoot 'strava_import.py') @args
exit $LASTEXITCODE
