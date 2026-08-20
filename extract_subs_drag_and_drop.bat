@echo off
chcp 65001 >nul
title Ekstraktor Angielskich Napisow z Wideo

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [Blad]: Nie znaleziono srodowiska wirtualnego .venv!
    pause
    exit /b 1
)

echo =======================================================
echo   Ekstraktor Angielskich Napisow (MKV / MP4 -^> .ass / .srt)
echo =======================================================
echo.

if "%~1"=="" (
    echo Uruchamianie okna wyboru plikow...
    .venv\Scripts\python.exe extract_subtitles.py
) else (
    echo Przetwarzanie przekazanych plikow...
    .venv\Scripts\python.exe extract_subtitles.py %*
)

echo.
echo Wcisnij dowolny klawisz, aby zamknac to okno...
pause >nul
