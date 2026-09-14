# import-fleet.ps1 - Import a fleet-export zip on a NEW Windows PC.
#
# Usage (new machine, PowerShell):
#   .\import-fleet.ps1 -Zip "C:\Users\me\Desktop\fleet-export-xxxx.zip" -Root "E:\Code"
#
# Safety rules (v2, after a real incident):
#   - If hermes home already exists with a NON-template .env, we are probably on a
#     machine that already runs a fleet. Import then only refreshes fleet files,
#     demo projects and profiles' config/SOUL, and NEVER overwrites any .env.
#   - On a genuinely fresh machine (no hermes config), .env skeletons are restored.
#   - -DryRun shows everything the import would do without touching the disk.

param(
    [Parameter(Mandatory = $true)][string]$Zip,
    [string]$Root = "E:\Code",
    [string]$DemoRoot = "E:\Demo",
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$Act = if ($DryRun) { { Write-Host "  [dryrun] $args" } } else { $null }

if (-not (Test-Path $Zip)) { throw "Zip not found: $Zip" }

# ---------- 0) prerequisites ----------
$pre = @()
foreach ($c in @("hermes", "node", "python", "git")) {
    $ok = $false
    try { & $c --version *> $null; $ok = ($LASTEXITCODE -eq 0) } catch { }
    if (-not $ok) { $pre += $c }
}
if ($pre.Count -gt 0) {
    throw "Missing on PATH: $($pre -join ', '). Install first (node LTS, python 3.11+, git, hermes), then re-run."
}

# ---------- 1) unzip ----------
$stage = Join-Path $env:TEMP ("fleet-import-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
Expand-Archive -Path $Zip -DestinationPath $stage -Force

$oldFleet = "E:\Code\AideanCompany\fleet"
$oldDemo  = "E:\Demo"
$oldUser  = $env:USERPROFILE
if (Test-Path (Join-Path $stage "MANIFEST.txt")) {
    foreach ($ln in (Get-Content (Join-Path $stage "MANIFEST.txt"))) {
        if ($ln -match "^Old fleet     : (.+)$") { $oldFleet = $Matches[1].Trim() }
        if ($ln -match "^Old demo root : (.+)$") { $oldDemo  = $Matches[1].Trim() }
        if ($ln -match "^Old hermes    : (.+)$") {
            if ($Matches[1].Trim() -match "^(.+?)\\AppData\\Local\\hermes$") { $oldUser = $Matches[1] }
        }
    }
}

$newFleet = Join-Path $Root "AideanCompany\fleet"
$hh       = Join-Path $env:LOCALAPPDATA "hermes"
$newUser  = $env:USERPROFILE

# ---------- safety probe: does a live fleet already exist here? ----------
$liveHome = (Test-Path (Join-Path $hh "config.yaml"))
$liveEnvHasKeys = $false
$hhEnv = Join-Path $hh ".env"
if ($liveHome -and (Test-Path $hhEnv)) {
    $valLines = Get-Content $hhEnv | Where-Object { $_ -match "^[A-Za-z_][A-Za-z0-9_]*=.+$" -and $_ -notmatch "FILL_ME" }
    $liveEnvHasKeys = ($valLines.Count -gt 0)
}
if ($liveEnvHasKeys) {
    Write-Host ""
    Write-Host "SAFETY: existing hermes home with real .env detected -> PROTECT MODE"
    Write-Host "  .env files will NOT be touched. Fleet/demo/profile-config/SOUL still imported."
    Write-Host ""
} elseif ($DryRun) {
    Write-Host "DRYRUN: no live keys detected - .env skeletons WOULD be restored."
}

function Copy-Safe([string]$src, [string]$dst, [switch]$NoEnv) {
    if ($NoEnv -and (Split-Path $src -Leaf) -eq ".env") { return }
    if ($DryRun) { Write-Host "  [dryrun] copy $src -> $dst"; return }
    Copy-Item $src $dst -Force
}

function Robo-Safe([string]$src, [string]$dst) {
    if ($DryRun) { Write-Host "  [dryrun] robocopy $src -> $dst"; return }
    robocopy $src $dst /E /NFL /NDL /NJH /NJS | Out-Null
}

Write-Host "[1/6] Plan: fleet -> $newFleet"
Write-Host "[2/6] Restoring fleet files"
if (Test-Path (Join-Path $stage "fleet")) {
    New-Item -ItemType Directory -Path (Split-Path $newFleet -Parent) -Force | Out-Null
    Robo-Safe (Join-Path $stage "fleet") $newFleet
}

Write-Host "[3/6] Restoring demo projects -> $DemoRoot"
if (Test-Path (Join-Path $stage "demo")) {
    if (-not $DryRun) { New-Item -ItemType Directory -Path $DemoRoot -Force | Out-Null }
    Get-ChildItem (Join-Path $stage "demo") -Directory | ForEach-Object {
        Robo-Safe $_.FullName (Join-Path $DemoRoot $_.Name)
    }
}

Write-Host "[4/6] Restoring hermes home (config / SOUL / .env)"
if (-not $DryRun) { New-Item -ItemType Directory -Path $hh -Force | Out-Null }
foreach ($f in @("config.yaml", "SOUL.md", ".env")) {
    $s = Join-Path (Join-Path $stage "hermes-home") $f
    if (Test-Path $s) {
        if ($liveEnvHasKeys -and $f -ne "SOUL.md" -and $f -ne "config.yaml") { continue }
        if ($liveEnvHasKeys -and $f -eq "config.yaml") {
            Write-Host "  PROTECT: existing config.yaml kept (merge manually if needed). Zip copy: $($s)"
            continue
        }
        Copy-Safe $s (Join-Path $hh $f)
    }
}

Write-Host "[5/6] Restoring role profiles"
if (-not $DryRun) { New-Item -ItemType Directory -Path (Join-Path $hh "profiles") -Force | Out-Null }
if (Test-Path (Join-Path $stage "profiles")) {
    Get-ChildItem (Join-Path $stage "profiles") -Directory | ForEach-Object {
        $dst = Join-Path (Join-Path $hh "profiles") $_.Name
        if ($DryRun) { Write-Host "  [dryrun] profile $($_.Name)"; return }
        New-Item -ItemType Directory -Path $dst -Force | Out-Null
        foreach ($f in @("config.yaml", "SOUL.md")) {
            $s = Join-Path $_.FullName $f
            if (Test-Path $s) { Copy-Item $s (Join-Path $dst $f) -Force }
        }
        $e = Join-Path $_.FullName ".env"
        if ((Test-Path $e) -and -not $liveEnvHasKeys) {
            Copy-Item $e (Join-Path $dst ".env") -Force
        }
    }
}

# ---------- 6) path rewriting ----------
Write-Host "[6/6] Rewriting machine-specific paths ..."
$pynewDir = $null
try { $pynewDir = Split-Path (Get-Command python).Source -Parent } catch { }

function Rewrite-File([string]$path) {
    if ($DryRun -or -not (Test-Path $path)) { return }
    $t = [System.IO.File]::ReadAllText($path)
    $orig = $t
    if ($pynewDir) { $t = $t.Replace("C:\Program Files\Python313", $pynewDir) }
    if ($oldUser -and $oldUser -ne $newUser) { $t = $t.Replace($oldUser + "\", $newUser + "\") }
    if ($oldFleet -ne $newFleet)             { $t = $t.Replace($oldFleet, $newFleet) }
    if ($oldDemo -ne $DemoRoot)              { $t = $t.Replace($oldDemo, $DemoRoot) }
    if ($t -ne $orig) { [System.IO.File]::WriteAllText($path, $t, (New-Object System.Text.UTF8Encoding($false))) }
}

foreach ($rel in @("console\console.py", "start-fleet.ps1", "tools\new-project.ps1",
                   "tools\export-fleet.ps1", "tools\import-fleet.ps1",
                   "configs\manager-SOUL.md", "console\state\roster.json",
                   "console\state\tasks.json", "console\state\projects.json")) {
    Rewrite-File (Join-Path $newFleet $rel)
}
if (Test-Path (Join-Path $hh "SOUL.md")) { Rewrite-File (Join-Path $hh "SOUL.md") }
if (Test-Path (Join-Path $hh "profiles")) {
    Get-ChildItem (Join-Path $hh "profiles") -Directory | ForEach-Object {
        Rewrite-File (Join-Path $_.FullName "SOUL.md")
    }
}

Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Import done$(if ($DryRun) { ' (DRYRUN - nothing was written)' }). Manual checklist:"
if ($liveEnvHasKeys) {
    Write-Host "  1) PROTECT MODE: your existing .env was kept. If this zip came from another"
    Write-Host "     machine, verify each role's key names exist in $hh\profiles\<id>\.env"
} elseif (Test-Path (Join-Path $hh ".env")) {
    Write-Host "  1) KEYS MISSING (keyless export): open MANIFEST.txt for names, fill every"
    Write-Host "     FILL_ME line in $hh\.env and $hh\profiles\<id>\.env"
} else {
    Write-Host "  1) No .env restored - create $hh\.env (names in MANIFEST.txt)"
}
Write-Host "  2) Start:  powershell -File $newFleet\start-fleet.ps1"
Write-Host "  3) Health: curl.exe http://127.0.0.1:5000/api/health   (all checks true)"
Write-Host "  4) Brain:  hermes --yolo -z `"reply OK`"   (~10s = healthy)"
Write-Host "  5) Smoke every role once: console -> roles -> smoke test"
Write-Host "  6) Optional: shortcut to start-fleet.ps1 into shell:startup"
