@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ===============================================
echo   My PyTube-DL - Instalacion de dependencias
echo ===============================================
echo.

where powershell >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PowerShell no esta disponible en este equipo.
    exit /b 1
)

echo Ejecutando el instalador de PowerShell...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] La instalacion fallo. Revisa los mensajes anteriores.
    pause
    exit /b 1
)

echo.
pause
