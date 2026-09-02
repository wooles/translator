@echo off
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
title Przywracanie Ekosystemu na Nowym Komputerze (Master Restore)

echo ================================================================
echo   PRZYWRACANIE EKOSYSTEMU Z BACKUPU (KOMPLETNY_BACKUP_SYSTEMU.zip)
echo   Projekty: Translator, Sorter, Kalendarz
echo   Pamiec AI (.gemini), Modele (.cache), Klucze API i Bazy Danych
echo ================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%master_backup_engine.py" restore
) else (
    python "%SCRIPT_DIR%master_backup_engine.py" restore
)

echo.
echo ================================================================
echo Gotowe. Nacisnij dowolny klawisz, aby zamknac to okno.
echo ================================================================
pause >nul
