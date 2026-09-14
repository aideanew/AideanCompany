# export-fleet.ps1 - Pack AideanAgentFleet (console + profiles + configs + demo
# projects) into ONE zip for migration to another Windows PC.
#
# Usage (run on the OLD machine, PowerShell):
#   .\export-fleet.ps1                # recommended: secrets scrubbed out of the archive
#   .\export-fleet.ps1 -WithKeys      # include real keys (USB / local transfer ONLY)
#
# Output: fleet-export-<date>.zip on the Desktop + MANIFEST.txt inside.

param(
    [string]$OutZip = "",
    [switch]$WithKeys
)
$ErrorActionPreference = "Stop"

$Fleet    = "E:\Code\AideanCompany\fleet"
$Hermes   = Join-Path $env:LOCALAPPDATA "hermes"
# 演示项目：自动发现 E:\Demo 下所有目录（新项目无需改脚本）
$DemoDirs = @(Get-ChildItem "E:\Demo" -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notlike "import-test*" } | ForEach-Object { $_.FullName })

if (-not (Test-Path $Fleet))  { throw "Fleet folder not found: $Fleet" }
if (-not (Test-Path $Hermes)) { throw "Hermes home not found: $Hermes" }

if (-not $OutZip) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $OutZip  = Join-Path $desktop ("fleet-export-" + (Get-Date -Format "yyyyMMdd-HHmm") + ".zip")
}

# ---------- collect real secret values from every .env (for scrubbing) ----------
$secretMap = @{}          # value -> variable name
$envFiles = @(Join-Path $Hermes ".env")
if (Test-Path (Join-Path $Hermes "profiles")) {
    Get-ChildItem (Join-Path $Hermes "profiles") -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { $e = Join-Path $_.FullName ".env"; if (Test-Path $e) { $envFiles += $e } }
}
foreach ($f in $envFiles) {
    foreach ($ln in (Get-Content $f -ErrorAction SilentlyContinue)) {
        if ($ln -match "^([A-Za-z_][A-Za-z0-9_]*)=(.+)$") {
            $name = $Matches[1]; $val = $Matches[2].Trim()
            if ($val.Length -ge 16 -and -not $secretMap.ContainsKey($val)) { $secretMap[$val] = $name }
        }
    }
}
Write-Host ("Found {0} distinct secret values to scrub (not counting -WithKeys mode)." -f $secretMap.Count)

# ---------- staging ----------
$stage = Join-Path $env:TEMP ("fleet-export-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $stage | Out-Null
Write-Host "[1/6] Staging fleet ..."
$exclude = @((Join-Path $Fleet "console\logs"))
Get-ChildItem (Join-Path $Fleet "configs") -Directory -Filter "skills-backup-*" -ErrorAction SilentlyContinue |
    ForEach-Object { $exclude += $_.FullName }
robocopy $Fleet (Join-Path $stage "fleet") /E /NFL /NDL /NJH /NJS /XD @exclude | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy fleet failed ($LASTEXITCODE)" }

Write-Host "[2/6] Staging demo projects ..."
foreach ($d in $DemoDirs) {
    if (Test-Path $d) {
        $dst = Join-Path (Join-Path $stage "demo") (Split-Path $d -Leaf)
        robocopy $d $dst /E /NFL /NDL /NJH /NJS | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy demo failed: $d" }
    }
}

Write-Host "[3/6] Staging hermes home (config / SOUL / .env) ..."
$hh = Join-Path $stage "hermes-home"
New-Item -ItemType Directory -Path $hh | Out-Null
foreach ($f in @("config.yaml", "SOUL.md")) {
    if (Test-Path (Join-Path $Hermes $f)) { Copy-Item (Join-Path $Hermes $f) (Join-Path $hh $f) -Force }
}
$keepEnv = @("A2A_AGENT_NAME", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY",
             "TERMINAL_TIMEOUT", "TERMINAL_LIFETIME_SECONDS")
function Copy-EnvScrubbed([string]$src, [string]$dst) {
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($ln in (Get-Content $src)) {
        if ($ln -match "^([A-Za-z_][A-Za-z0-9_]*)=(.*)$") {
            $k = $Matches[1]; $v = $Matches[2]
            if ($keepEnv -contains $k -or $v.Trim() -eq "") { $out.Add($ln) }
            else { $out.Add("$k=   # FILL_ME (name from MANIFEST)") }
        } else { $out.Add($ln) }
    }
    Set-Content -Path $dst -Value $out -Encoding UTF8
}
if (Test-Path (Join-Path $Hermes ".env")) {
    if ($WithKeys) { Copy-Item (Join-Path $Hermes ".env") (Join-Path $hh ".env") -Force }
    else           { Copy-EnvScrubbed (Join-Path $Hermes ".env") (Join-Path $hh ".env") }
}

Write-Host "[4/6] Staging role profiles (config / SOUL / .env skeleton) ..."
$pdst = Join-Path $stage "profiles"
New-Item -ItemType Directory -Path $pdst | Out-Null
$profileIds = @()
Get-ChildItem (Join-Path $Hermes "profiles") -Directory | Where-Object { $_.Name -ne ".deleted" } |
    ForEach-Object {
        $profileIds += $_.Name
        $dst = Join-Path $pdst $_.Name
        New-Item -ItemType Directory -Path $dst | Out-Null
        foreach ($f in @("config.yaml", "SOUL.md")) {
            $s = Join-Path $_.FullName $f
            if (Test-Path $s) { Copy-Item $s (Join-Path $dst $f) -Force }
        }
        $e = Join-Path $_.FullName ".env"
        if (Test-Path $e) {
            if ($WithKeys) { Copy-Item $e (Join-Path $dst ".env") -Force }
            else           { Copy-EnvScrubbed $e (Join-Path $dst ".env") }
        }
    }

# ---------- scrub real key values from staged text files (keyless mode) ----------
$scrubbed = 0
if (-not $WithKeys -and $secretMap.Count -gt 0) {
    Write-Host "[5/6] Scrubbing secret values from staged text files ..."
    # every text-ish file regardless of extension (catches .bak, .tmpl, no-ext files);
    # skip binaries (pyc/images) and files >= 2MB to keep it fast
    $binExt = @(".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".exe", ".dll")
    Get-ChildItem $stage -Recurse -File | Where-Object {
        ($binExt -notcontains $_.Extension.ToLower()) -and
        ($_.Length -lt 2MB) -and
        ($_.FullName -notmatch "__pycache__")
    } | ForEach-Object {
        $t = [System.IO.File]::ReadAllText($_.FullName)
        $o = $t
        foreach ($v in $secretMap.Keys) { if ($t.Contains($v)) { $t = $t.Replace($v, ('${' + $secretMap[$v] + '}')); $scrubbed++ } }
        if ($t -ne $o) { [System.IO.File]::WriteAllText($_.FullName, $t, (New-Object System.Text.UTF8Encoding($false))) }
    }
    Write-Host ("      scrubbed {0} occurrences." -f $scrubbed)
} else {
    Write-Host "[5/6] Skipped scrubbing (WithKeys mode - keys travel inside the zip)."
}

# ---------- manifest ----------
$ver = "n/a"; $nver = "n/a"; $pver = "n/a"; $gver = "n/a"
try { $ver  = (hermes --version 2>&1 | Out-String).Trim() } catch { }
try { $nver = (node --version 2>&1 | Out-String).Trim() } catch { }
try { $pver = (python --version 2>&1 | Out-String).Trim() } catch { }
try { $gver = (git --version 2>&1 | Out-String).Trim() } catch { }

$lines = @()
$lines += "Fleet Export Manifest"
$lines += "Date          : " + (Get-Date -Format "yyyy-MM-dd HH:mm")
$lines += "hermes        : $ver"
$lines += "node          : $nver"
$lines += "python        : $pver"
$lines += "git           : $gver"
$lines += "Old fleet     : $Fleet"
$lines += "Old hermes    : $Hermes"
$lines += "Old demo root : E:\Demo"
$lines += "Profiles      : " + ($profileIds -join ", ")
$lines += "Keys included : $WithKeys"
if (-not $WithKeys) {
    $lines += ""
    $lines += "Fill these variables on the target machine (values NOT exported):"
    $secretMap.Values | Sort-Object -Unique | ForEach-Object { $lines += "  $_" }
}
Set-Content -Path (Join-Path $stage "MANIFEST.txt") -Value $lines -Encoding UTF8

# ---------- zip ----------
if (Test-Path $OutZip) { Remove-Item $OutZip -Force }
$tared = $false
if (Get-Command tar -ErrorAction SilentlyContinue) {
    tar -a -c -f $OutZip -C $stage "." 2>$null
    if ($LASTEXITCODE -eq 0 -and (Test-Path $OutZip)) { $tared = $true }
}
if (-not $tared) { Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $OutZip -Force }
Remove-Item $stage -Recurse -Force

$mb = [math]::Round((Get-Item $OutZip).Length / 1MB, 1)
Write-Host ""
Write-Host "Export done: $OutZip ($mb MB)"
if ($WithKeys) {
    Write-Host "WARNING: real API keys inside. USB/local transfer only; delete after import."
} else {
    Write-Host "No keys inside. On the target PC, fill the FILL_ME lines in the .env"
    Write-Host "files (variable names are in MANIFEST.txt)."
}
Write-Host "Next step on the new PC: import-fleet.ps1 -Zip <this file> -Root <drive>:\Code"
