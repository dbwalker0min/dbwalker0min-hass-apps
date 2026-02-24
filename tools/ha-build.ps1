param(
    # A file path anywhere inside the add-on repo (usually a file you just edited). Used to determine which add-on to build.
    [Parameter(Mandatory = $true)]  
    [string]$input_file,
    
    # Your Samba server name/IP (must match your Windows share path)
    [string]$SambaHost = "homeassistant",

    # Where local add-ons live in the Samba share
    [string]$SambaAddonsShare = "addons",

    # HA SSH host (same as SambaHost usually)
    [string]$HaSshHost = "ha.home",

    # If set, do a rebuild (best match for local-build add-ons)
    [switch]$Rebuild,

    # If set, restart after reload/rebuild
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

# Find the slug of the add-on to build based on the input file path, which can be anywhere in the add-on repo. (Usually a file you just edited.)
$inputFilePath = (Resolve-Path $input_file).Path
$root = git rev-parse --show-toplevel
$current = (Get-Location).Path

$addonName = ""
$addonPath = ""
Get-ChildItem -Path $root -Directory | ForEach-Object {
    if ($current.StartsWith($_.FullName, [System.StringComparison]::OrdinalIgnoreCase)) {
        $addonName = $_.Name
        $addonPath = $_.FullName
    }
}

if (-not $addonName) {
    throw "Couldn't determine add-on name from input file path. Are you sure it's inside the repo? Input path: $inputFilePath"
}

$Slug = $addonName

# ---- 1) bump version ----
& uvx bump2version --no-commit --no-tag --allow-dirty

# ---- 2) copy repo to Samba add-ons folder ----
$dst = "\\$SambaHost\$SambaAddonsShare\$Slug"

Write-Host "Copying to: $dst"

# robocopy exit codes: 0-7 are success
$src = $addonPath

$excludeDirs = @(
    ".git", ".vscode", "__pycache__", ".pytest_cache", ".mypy_cache",
    "dist", "build", ".ruff_cache", ".venv", "node_modules"
)

$excludeFiles = @("*.pyc", "*.pyo", "*.tmp")

$rcArgs = @(
    $src, $dst,
    "/MIR",
    "/NFL", "/NDL", "/NJH", "/NJS", "/NP",
    "/R:2", "/W:1"
)

foreach ($d in $excludeDirs) { $rcArgs += @("/XD", (Join-Path $src $d)) }
foreach ($f in $excludeFiles) { $rcArgs += @("/XF", $f) }

& robocopy @rcArgs | Out-Host
$rc = $LASTEXITCODE
if ($rc -gt 7) { throw "robocopy failed with exit code $rc" }

# ---- 3) tell HA to reload add-on info ----
# Uses the HA CLI on the HA box, via SSH.
# (/addons/reload exists; CLI calls into Supervisor.) :contentReference[oaicite:2]{index=2}
Write-Host "Reloading add-on info on HA via SSH..."
& ssh "$HaSshHost" "ha addons reload" | Out-Host

# Optional: show info (nice feedback loop)
& ssh "$HaSshHost" "ha addons info $Slug" | Out-Host

# ---- 4) optional rebuild/update + restart ----
if ($Rebuild) {
    Write-Host "Rebuilding add-on..."
    # For local build add-ons, rebuild is often the right verb (Supervisor has /addons/<addon>/rebuild). :contentReference[oaicite:3]{index=3}
    & ssh "root@$HaSshHost" "ha addons rebuild $Slug" | Out-Host
}

if ($Restart) {
    Write-Host "Restarting add-on..."
    & ssh "root@$HaSshHost" "ha addons restart $Slug" | Out-Host
}

Write-Host "Done."