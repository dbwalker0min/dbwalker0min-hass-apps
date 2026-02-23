param(
  [string]$Slug,

  # Your Samba server name/IP (must match your Windows share path)
  [string]$SambaHost = "homeassistant",

  # Where local add-ons live in the Samba share
  [string]$SambaAddonsShare = "addons",

  # HA SSH host (same as SambaHost usually)
  [string]$HaSshHost = "homeassistant",

  # Optional: which part of semver to bump
  [ValidateSet("patch","minor","major")]
  [string]$Bump = "patch",

  # If set, do a rebuild (best match for local-build add-ons)
  [switch]$Rebuild,

  # If set, restart after reload/rebuild
  [switch]$Restart
)

$ErrorActionPreference = "Stop"

# ---- 1) bump version in config.yaml ----
$configPath = Join-Path $PSScriptRoot "..\config.yaml"
$configPath = (Resolve-Path $configPath).Path

if (-not (Test-Path $configPath)) {
  throw "Can't find config.yaml at $configPath"
}

$content = Get-Content $configPath -Raw

# match a line like: version: 1.2.3
if ($content -notmatch '(?m)^\s*version:\s*(?<ver>[^\s#]+)\s*$') {
  throw "Couldn't find a 'version:' line in config.yaml"
}

$oldVer = $Matches.ver
$newVer = Bump-Semver $oldVer $Bump

$content2 = [regex]::Replace(
  $content,
  '(?m)^(\s*version:\s*)([^\s#]+)\s*$',
  "`$1$newVer",
  1
)

Set-Content -Path $configPath -Value $content2 -NoNewline
Write-Host "Version bumped: $oldVer -> $newVer"

# ---- 2) copy repo to Samba add-ons folder ----
$dst = "\\$SambaHost\$SambaAddonsShare\$Slug"

Write-Host "Copying to: $dst"

# robocopy exit codes: 0-7 are success
$src = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path

$excludeDirs = @(
  ".git", ".vscode", "__pycache__", ".pytest_cache", ".mypy_cache",
  "dist", "build", ".ruff_cache", ".venv", "node_modules"
)

$excludeFiles = @("*.pyc", "*.pyo", "*.tmp")

$rcArgs = @(
  $src, $dst,
  "/MIR",
  "/NFL","/NDL","/NJH","/NJS","/NP",
  "/R:2","/W:1"
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
& ssh "root@$HaSshHost" "ha addons reload" | Out-Host

# Optional: show info (nice feedback loop)
& ssh "root@$HaSshHost" "ha addons info $Slug" | Out-Host

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