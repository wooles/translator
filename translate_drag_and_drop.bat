@echo off
chcp 65001 > nul
title Multimodal Subtitle Translator (Gemini 3.7 Flash)

echo ========================================================
echo   Multimodal Video Subtitle Translator (Gemini 3.7 Flash)
echo ========================================================
echo.

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py %*
) else (
    py -3.10 main.py %*
)

echo.
echo ========================================================
echo Proces zakonczony.
echo Nacisnij dowolny klawisz, aby zamknac to okno.
pause > nul
