@echo off
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
title Tworzenie Kompletnego Backupu Ekosystemu (Master Backup)

echo ================================================================
echo   TWORZENIE PELNEGO BACKUPU EKOSYSTEMU (Zip64 Engine)
echo   Projekty: Translator, Sorter, Kalendarz
echo   Pamiec AI (.gemini), Modele (.cache), Klucze API i Bazy Danych
echo ================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%master_backup_engine.py"
) else (
    python "%SCRIPT_DIR%master_backup_engine.py"
)

echo.
echo ================================================================
echo Gotowe. Nacisnij dowolny klawisz, aby zamknac to okno.
echo ================================================================
pause >nul
