# Gera dist\LocalTube\ (PyInstaller + ffmpeg) e dist\LocalTube-<versão>-Setup.exe (Inno Setup).
#   .\packaging\build.ps1
#   ... -FFmpegDir C:\ffmpeg\bin     usa outro ffmpeg (pasta com ffmpeg.exe e ffprobe.exe)
#   ... -SkipInstaller               só a pasta, sem o instalador
param(
    [string]$FFmpegDir = "",
    [switch]$SkipInstaller
)
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Dist = Join-Path $Root "dist"
$Build = Join-Path $Root "build"
$AppDir = Join-Path $Dist "LocalTube"

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    # Com "Stop", o PowerShell 5.1 trataria como erro cada linha que o programa escreve no stderr
    # quando a saída é redirecionada (o PyInstaller registra tudo no stderr).
    $ErrorActionPreference = "Continue"
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program terminou com o código $LASTEXITCODE" }
}

Push-Location $Root
try {
    Invoke-Checked $Python @("-m", "pip", "install", "--disable-pip-version-check", "-q", "-e", ".[build]")
    $Version = & $Python -c "import localtube; print(localtube.__version__)"

    if (-not $FFmpegDir) {
        $found = & $Python -c "from localtube.core.tools import find_tool; print(find_tool('ffmpeg') or '')"
        if (-not $found) { throw "ffmpeg não encontrado. Instale com: winget install --id Gyan.FFmpeg -e (ou use -FFmpegDir)" }
        $FFmpegDir = Split-Path $found -Parent
    }
    foreach ($tool in "ffmpeg.exe", "ffprobe.exe") {
        if (-not (Test-Path (Join-Path $FFmpegDir $tool))) { throw "$tool não está em $FFmpegDir" }
    }

    New-Item -ItemType Directory -Force $Build | Out-Null
    Write-Host "Ícone"
    Invoke-Checked $Python @("packaging\make_icon.py", (Join-Path $Build "localtube.ico"))

    Write-Host "PyInstaller"
    Invoke-Checked $Python @("-m", "PyInstaller", "packaging\localtube.spec", "--noconfirm", "--clean",
        "--distpath", $Dist, "--workpath", (Join-Path $Build "pyinstaller"))

    Write-Host "ffmpeg ($FFmpegDir)"
    $FFmpegOut = Join-Path $AppDir "ffmpeg"
    New-Item -ItemType Directory -Force $FFmpegOut | Out-Null
    Copy-Item (Join-Path $FFmpegDir "ffmpeg.exe"), (Join-Path $FFmpegDir "ffprobe.exe") $FFmpegOut
    Get-ChildItem $FFmpegDir -Filter *.dll | Copy-Item -Destination $FFmpegOut  # builds "shared"
    $License = @(Join-Path $FFmpegDir "LICENSE*") + @(Join-Path (Split-Path $FFmpegDir -Parent) "LICENSE*")
    Get-ChildItem $License -ErrorAction SilentlyContinue | Select-Object -First 1 |
        Copy-Item -Destination (Join-Path $FFmpegOut "LICENSE.txt")
    Copy-Item "packaging\THIRD-PARTY-NOTICES.txt" $AppDir

    if ($SkipInstaller) { return }

    $Iscc = @(
        (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source,
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if (-not $Iscc) { throw "Inno Setup não encontrado. Instale com: winget install --id JRSoftware.InnoSetup -e" }

    Write-Host "Inno Setup"
    Invoke-Checked $Iscc @("/Qp", "/DAppVersion=$Version", "/DSourceDir=$AppDir", "/DOutputDir=$Dist",
        "/DIconFile=$(Join-Path $Build 'localtube.ico')", "packaging\installer.iss")
    Write-Host "Pronto: $(Join-Path $Dist "LocalTube-$Version-Setup.exe")"
}
finally {
    Pop-Location
}
