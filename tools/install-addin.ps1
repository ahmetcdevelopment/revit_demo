# Builds the RevitBridge add-in and installs it for the current user (Revit 2027).
#   .\tools\install-addin.ps1
# Files: %APPDATA%\Autodesk\Revit\Addins\2027\RevitBridge.addin + ...\RevitBridge\{RevitBridge,RevitBridge.Ops}.dll
# The host (RevitBridge.dll) is locked while Revit runs and only changes with the protocol; the ops assembly
# (RevitBridge.Ops.dll) is hot-reloaded by the host, so rebuilding + running this script is enough while Revit is open.
param([string]$Configuration = 'Release', [string]$RevitYear = '2027')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

dotnet build "$root\src\revit-addin\RevitBridge.slnx" -c $Configuration --nologo -v q
if ($LASTEXITCODE -ne 0) { throw 'build failed' }

# Revit 2027 refused (WrongAssembly: "does not exist") an assembly under %LOCALAPPDATA%; keep it beside the manifest.
$addins = Join-Path $env:APPDATA "Autodesk\Revit\Addins\$RevitYear"
$dst = Join-Path $addins 'RevitBridge'
New-Item -ItemType Directory -Force $dst | Out-Null

$host_ = "$root\src\revit-addin\RevitBridge\bin\$Configuration\net10.0-windows"
$ops = "$root\src\revit-addin\RevitBridge.Ops\bin\$Configuration\net10.0-windows"

foreach ($f in 'RevitBridge.Ops.dll', 'RevitBridge.Ops.pdb') {
    Copy-Item "$ops\$f" $dst -Force
}
$hostChanged = $false
foreach ($f in 'RevitBridge.dll', 'RevitBridge.pdb') {
    $src = "$host_\$f"
    $target = Join-Path $dst $f
    if ((Test-Path $target) -and ((Get-FileHash $src).Hash -eq (Get-FileHash $target).Hash)) { continue }
    try {
        Copy-Item $src $dst -Force
        $hostChanged = $true
    } catch {
        Write-Warning "Host $f is loaded by Revit and changed: restart Revit once to pick it up. Ops assembly was updated (hot)."
    }
}

$manifest = (Get-Content "$root\src\revit-addin\RevitBridge\RevitBridge.addin.template" -Raw).Replace('{{ASSEMBLY}}', "$dst\RevitBridge.dll")
Set-Content -Path "$addins\RevitBridge.addin" -Value $manifest -Encoding UTF8
Write-Host "Installed: $dst  (host changed: $hostChanged)"
