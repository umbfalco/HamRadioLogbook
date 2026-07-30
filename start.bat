@echo off
title Ham Radio Logbook
cd /d "%~dp0"

echo Avvio Ham Radio Logbook...

:: ── Cerca Python in posizioni comuni ─────────────────────────
set PYTHON_EXE=

:: 1. PATH standard
where python >nul 2>&1
if not errorlevel 1 (
    python --version >nul 2>&1
    if not errorlevel 1 ( set PYTHON_EXE=python & goto :found_python )
)

:: 2. Launcher py
where py >nul 2>&1
if not errorlevel 1 ( set PYTHON_EXE=py & goto :found_python )

:: 3. AppData\Local\Programs\Python\Python3*
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%d\python.exe" ( set PYTHON_EXE=%%d\python.exe & goto :found_python )
)

:: 4. ProgramFiles
for /d %%d in ("%ProgramFiles%\Python*") do (
    if exist "%%d\python.exe" ( set PYTHON_EXE=%%d\python.exe & goto :found_python )
)

echo.
echo ============================================================
echo  ERRORE: Python non trovato!
echo  Scarica e installa Python 3.9+ da:
echo    https://www.python.org/downloads/
echo  Assicurati di spuntare "Add Python to PATH" durante l'installazione.
echo ============================================================
echo.
pause
exit /b 1

:found_python
echo Python trovato: %PYTHON_EXE%
%PYTHON_EXE% --version

:: Installa dipendenze
echo Verifica dipendenze...
%PYTHON_EXE% -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo ATTENZIONE: impossibile installare alcune dipendenze. Continuo...
)

:: Ottieni IP LAN
set LAN_IP=
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    set LAN_IP=%%a
    goto :found_ip
)
:found_ip
if defined LAN_IP set LAN_IP=%LAN_IP: =%

echo.
echo ============================================
echo  Ham Radio Logbook avviato!
echo  Apri nel browser: http://localhost:5000
if defined LAN_IP (
    echo  Accesso LAN / smartphone: http://%LAN_IP%:5000
)
echo  Premi Ctrl+C per fermare il server
echo ============================================
echo.

:: Apri browser dopo 2 secondi
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: Avvia Flask
%PYTHON_EXE% app.py

pause
