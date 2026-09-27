@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "VENV=%~dp0.venv-build"
set "PY=%VENV%\Scripts\python.exe"

echo [1/3] Preparando entorno virtual...
if not exist "%PY%" (
    py -3 -m venv "%VENV%" 2>nul || python -m venv "%VENV%"
    if errorlevel 1 goto :fail
)

echo [2/3] Instalando dependencias...
"%PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%PY%" -m pip install customtkinter pyinstaller
if errorlevel 1 goto :fail

echo [3/3] Compilando My-PyTube-DL.exe...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "My-PyTube-DL" ^
    --icon "icono-app.ico" ^
    --add-data "icono-app.ico;." ^
    --add-data "icono-app.png;." ^
    --collect-all customtkinter ^
    "yt_gui.py"
if errorlevel 1 goto :fail

echo.
echo ==========================================
echo  COMPILADO: dist\My-PyTube-DL.exe
echo ==========================================
echo.
echo  IMPORTANTE para la maquina donde se use el .exe:
echo   - yt-dlp en el PATH (pip install yt-dlp)
echo   - Deno en el PATH (winget install DenoLand.Deno)
pause
exit /b 0

:fail
echo.
echo  ERROR durante la compilacion.
pause
exit /b 1
