param(
  [string]$Version = "",
  [switch]$SkipAppBuild,
  [switch]$NoSfx
)

$ErrorActionPreference = "Stop"

$InstallerRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$WindowsClientRoot = Split-Path -Parent $InstallerRoot
$RepoRoot = Split-Path -Parent $WindowsClientRoot
$ArtifactsDir = Join-Path $InstallerRoot "artifacts"
$BuildDir = Join-Path $InstallerRoot "build"
$StageDir = Join-Path $BuildDir "NirvNotes-win11"
$AppDist = Join-Path $WindowsClientRoot "dist\NirvNotes"
$SevenZip = "C:\Program Files\7-Zip\7z.exe"
$SevenZipSfx = "C:\Program Files\7-Zip\7z.sfx"

function Write-Step([string]$Text) {
  Write-Host ""
  Write-Host "== $Text ==" -ForegroundColor Cyan
}

function Get-GitValue([string]$ArgsLine) {
  try {
    $Value = & git $ArgsLine.Split(" ") 2>$null
    if ($LASTEXITCODE -eq 0) {
      return ($Value | Select-Object -First 1)
    }
  } catch {
    return ""
  }
  return ""
}

Push-Location $RepoRoot
try {
  if (-not $Version) {
    $Version = Get-GitValue "rev-parse --short HEAD"
    if (-not $Version) {
      $Version = Get-Date -Format "yyyyMMdd-HHmmss"
    }
  }

  if (-not $SkipAppBuild) {
    Write-Step "Building Windows app"
    & (Join-Path $WindowsClientRoot "build.ps1")
  }

  if (!(Test-Path (Join-Path $AppDist "NirvNotes.exe"))) {
    throw "Missing app build at $AppDist. Run windows-client\build.ps1 first."
  }

  Write-Step "Staging installer package"
  Remove-Item -LiteralPath $StageDir -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Path (Join-Path $StageDir "app") -Force | Out-Null
  New-Item -ItemType Directory -Path $ArtifactsDir -Force | Out-Null

  Copy-Item -Path (Join-Path $AppDist "*") -Destination (Join-Path $StageDir "app") -Recurse -Force
  Copy-Item -Path (Join-Path $InstallerRoot "Install-NirvNotes.ps1") -Destination $StageDir -Force
  Copy-Item -Path (Join-Path $InstallerRoot "Install-NirvNotes.cmd") -Destination $StageDir -Force
  Copy-Item -Path (Join-Path $InstallerRoot "Uninstall-NirvNotes.ps1") -Destination $StageDir -Force
  Copy-Item -Path (Join-Path $InstallerRoot "README.md") -Destination $StageDir -Force

  $Commit = Get-GitValue "rev-parse HEAD"
  $Manifest = [ordered]@{
    name = "NirvNotes Win11 installer"
    version = $Version
    commit = $Commit
    builtAt = (Get-Date).ToString("s")
    defaultServerUrl = "https://racknerd-31fcf0d.tail38b5b3.ts.net:8092"
    installCommand = "Install-NirvNotes.cmd"
  }
  $Manifest | ConvertTo-Json | Set-Content -Path (Join-Path $StageDir "installer-manifest.json") -Encoding UTF8

  Write-Step "Writing ZIP"
  $ZipPath = Join-Path $ArtifactsDir "NirvNotes-win11-$Version.zip"
  Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue
  Compress-Archive -Path (Join-Path $StageDir "*") -DestinationPath $ZipPath -Force
  Write-Host $ZipPath

  if (-not $NoSfx) {
    if ((Test-Path $SevenZip) -and (Test-Path $SevenZipSfx)) {
      Write-Step "Writing self-extracting EXE"
      $Payload7z = Join-Path $BuildDir "NirvNotes-win11-$Version.7z"
      $SfxConfig = Join-Path $BuildDir "sfx-config.txt"
      $SetupExe = Join-Path $ArtifactsDir "NirvNotes-Setup-$Version.exe"
      Remove-Item -LiteralPath $Payload7z, $SfxConfig, $SetupExe -Force -ErrorAction SilentlyContinue

      Push-Location $StageDir
      try {
        & $SevenZip a -t7z $Payload7z ".\*" | Out-Null
      } finally {
        Pop-Location
      }

      @"
;!@Install@!UTF-8!
Title="NirvNotes Setup"
BeginPrompt="Install NirvNotes for the current Windows user?"
RunProgram="Install-NirvNotes.cmd"
;!@InstallEnd@!
"@ | Set-Content -Path $SfxConfig -Encoding UTF8

      $Output = [System.IO.File]::Create($SetupExe)
      try {
        foreach ($Part in @($SevenZipSfx, $SfxConfig, $Payload7z)) {
          $Bytes = [System.IO.File]::ReadAllBytes($Part)
          $Output.Write($Bytes, 0, $Bytes.Length)
        }
      } finally {
        $Output.Dispose()
      }
      Write-Host $SetupExe
    } else {
      Write-Host "7-Zip SFX module not found; ZIP package was still created." -ForegroundColor Yellow
    }
  }

  Write-Step "Done"
  Get-ChildItem $ArtifactsDir | Sort-Object LastWriteTime -Descending | Select-Object Name,Length,LastWriteTime
} finally {
  Pop-Location
}
