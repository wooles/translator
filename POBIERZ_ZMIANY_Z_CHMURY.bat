@echo off
chcp 65001 >nul
title Pobieranie i Scalanie Zmian z GitHuba
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ================================================================
echo   POBIERANIE I SCALANIE ZMIAN Z GITHUBA (GIT PULL)
echo ================================================================
echo.
echo [1/2] Sprawdzanie polaczenia i pobieranie najnowszych zmian...
git pull origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ================================================================
    echo [SUKCES] Twoj kod zostal pomyslnie zaktualizowany i scalony!
    echo Mozesz teraz bezpiecznie rozpoczac prace lub tlumaczenie.
    echo ================================================================
) else (
    echo.
    echo ================================================================
    echo [UWAGA] Wystapil problem podczas pobierania lub scalania zmian.
    echo.
    echo Jesli posiadasz lokalne zmiany, najpierw uruchom:
    echo   -> WYSLIJ_ZMIANY_DO_CHMURY.bat
    echo aby je zapisac, a nastepnie sprobuj ponownie pobrac.
    echo ================================================================
)

echo.
echo Nacisnij dowolny klawisz, aby zamknac to okno...
pause >nul
