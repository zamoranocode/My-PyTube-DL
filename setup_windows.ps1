# setup_windows.ps1
# Instala Python, Deno, FFmpeg, yt-dlp y dependencias de la GUI en Windows.
# Uso:  setup_windows.bat  (o: powershell -ExecutionPolicy Bypass -File setup_windows.ps1)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Msg)
    Write-Host ""
    Write-Host "[+] $Msg" -ForegroundColor Green
}

function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}

function Install-Winget {
    param([string]$Id, [string]$Name)
    if (winget list --id $Id --exact 2>$null | Select-String -Quiet $Id) {
        Write-Host "[=] $Name ya instalado" -ForegroundColor Cyan
    } else {
        Write-Host "[+] Instalando $Name..." -ForegroundColor Green
        winget install --id $Id --exact -e `
            --accept-source-agreements --accept-package-agreements --silent
        if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion de $Name" }
        Refresh-Path
    }
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  My PyTube-DL - Instalacion de dependencias " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget no esta� disponible. Usa Windows 10 21H2+ / Windows 11 o instala el App Installer."
}

# --- Python ---------------------------------------------------------------
Write-Step "Python"
Install-Winget -Id "Python.Python.3.12" -Name "Python 3.12"
Refresh-Path

$pyPath = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $pyPath = (py -3 -c "import sys; print(sys.executable)").Trim()
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pyPath = (python -c "import sys; print(sys.executable)").Trim()
}
if (-not $pyPath -or -not (Test-Path $pyPath)) {
    throw "No se encontro Python tras instalarlo. Abre un terminal nuevo y reintenta."
}
Write-Host "[=] Python: $($pyPath)" -ForegroundColor Cyan

# Python no a�ade su carpeta a PATH en la sesion actual: preparala manualmente.
$pyDir = Split-Path $pyPath
$env:Path = $pyDir + ";" + $env:Path

# --- FFmpeg (necesario para fusionar video+audio) ---------------------------
Write-Step "FFmpeg"
Install-Winget -Id "Gyan.FFmpeg" -Name "FFmpeg"
Refresh-Path

# --- Deno (runtime JS que usa yt-dlp para YouTube) ---------------------------
Write-Step "Deno"
Install-Winget -Id "DenoLand.Deno" -Name "Deno"
Refresh-Path

# --- yt-dlp ------------------------------------------------------------------
Write-Step "yt-dlp"
& $pyPath -m pip install --upgrade --user yt-dlp
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación de yt-dlp" }
if (Get-Command yt-dlp -ErrorAction SilentlyContinue) { yt-dlp --version } else {
    Write-Host "[!] yt-dlp se instala con --user. Abre un terminal nuevo para que se actualice el PATH." -ForegroundColor Yellow
}

# --- Dependencias de la GUI (venv del proyecto) -------------------------------
Write-Step "Entorno virtual de la GUI (.venv)"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $pyPath -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Fallo la creacion del venv" }
}
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion de las dependencias de la GUI" }

Write-Host ""
Write-Host "================ RESUMEN ================" -ForegroundColor Cyan
& $pyPath --version
& ".venv\Scripts\python.exe" -c "import customtkinter; print('customtkinter', customtkinter.__version__)"
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[OK] Instalacion completa." -ForegroundColor Green
Write-Host "EJECUTA:  launcher.bat" -ForegroundColor Green
Write-Host "(Si algun comando no se reconoce, cierra y abre el terminal para refrescar el PATH.)" -ForegroundColor Yellow