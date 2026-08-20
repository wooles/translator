@echo off
chcp 65001 > nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
title Multimodal Subtitle Translator (Gemini 3.7 Flash)

echo ========================================================
echo   Multimodal Video Subtitle Translator (Gemini 3.7 Flash)
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%main.py" %*
) else (
    echo [Info] Uruchamianie za pomoca python...
    python "%SCRIPT_DIR%main.py" %*
)

echo.
echo ========================================================
echo Proces zakonczony.
echo Nacisnij dowolny klawisz, aby zamknac to okno.
pause > nul
