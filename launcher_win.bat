@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "APP=%~dp0My-PyTube-DL.py"
if not exist "%APP%" goto :noapp

REM --- Prioridad: .exe compilado > .venv > Python del sistema ---------------

if exist "%~dp0dist\My-PyTube-DL.exe" (
    start "" "%~dp0dist\My-PyTube-DL.exe"
    exit /b 0
)

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYCMD=%~dp0.venv\Scripts\python.exe"
    goto :run
)

where py >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=py -3"
    goto :run
)

where python >nul 2>&1
if not errorlevel 1 (
    set "PYCMD=python"
    goto :run
)

echo.
echo  No se encontro Python en el sistema.
echo  Ejecuta setup_windows.bat para preparar el entorno.
pause
exit /b 1

:run
%PYCMD% -c "import customtkinter" >nul 2>&1
if errorlevel 1 goto :nodeps

where yt-dlp >nul 2>&1
if errorlevel 1 echo [!] yt-dlp no esta en el PATH: las descargas fallaran.
where ffmpeg >nul 2>&1
if errorlevel 1 echo [!] ffmpeg no esta en el PATH: no se podra fusionar video+audio.

%PYCMD% "%APP%"
goto :after

:nodeps
echo.
echo  Falta 'customtkinter' para: %PYCMD%
echo  Ejecuta setup_windows.bat para preparar el entorno.
pause
exit /b 1

:noapp
echo.
echo  No se encuentra My-PyTube-DL.py en %~dp0
pause
exit /b 1

:after
if errorlevel 1 (
    echo.
    echo  La app se cerro con error.
    pause
)
exit /b 0
