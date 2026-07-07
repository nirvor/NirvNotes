param(
  [string]$Name = "NirvNotes"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Venv = Join-Path $PSScriptRoot ".venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$Icon = Join-Path $Root "client\assets\favicon.ico"
$Entry = Join-Path $PSScriptRoot "nirvnotes_client.py"
$Dist = Join-Path $PSScriptRoot "dist"
$Build = Join-Path $PSScriptRoot "build"

Get-CimInstance Win32_Process |
  Where-Object {
    $_.Name -eq "NirvNotes.exe" -or
    ($_.Name -eq "msedgewebview2.exe" -and $_.CommandLine -like "*NirvNotes.exe*")
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }
Start-Sleep -Seconds 2

if (!(Test-Path $Python)) {
  python -m venv $Venv
  & $Python -m pip install --upgrade pip
  & $Python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
}

if (Test-Path $Dist) {
  Remove-Item -LiteralPath $Dist -Recurse -Force
}
if (Test-Path $Build) {
  Remove-Item -LiteralPath $Build -Recurse -Force
}

Push-Location $Root
try {
  & $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name $Name `
    --icon $Icon `
    --distpath $Dist `
    --workpath $Build `
    --specpath $Build `
    --add-data "$Icon;client\assets" `
    $Entry
} finally {
  Pop-Location
}

$Exe = Join-Path $Dist "$Name\$Name.exe"
if (!(Test-Path $Exe)) {
  throw "Build finished but $Exe was not created."
}

Write-Host "Built $Exe"
