@echo off
chcp 65001 > nul
title Synchronizator Bazy Napisow (Translation Memory)

echo ======================================================================
echo    SYNCHRONIZATOR BAZY NAPISOW (TRANSLATION MEMORY CORPUS)
echo ======================================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" sync_baza_napisow.py %*

echo.
echo ======================================================================
echo  Nacisnij dowolny klawisz, aby zakonczyc...
echo ======================================================================
pause > nul
