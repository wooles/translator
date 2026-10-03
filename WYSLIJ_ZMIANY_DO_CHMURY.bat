@echo off
chcp 65001 >nul
title Wysylanie Zmian do GitHuba
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ================================================================
echo   WYSLANIE NOWYCH ZMIAN NA GITHUB (GIT PUSH)
echo ================================================================
echo.

set "HAS_CHANGES="
for /f "tokens=*" %%a in ('git status --porcelain') do (
    set "HAS_CHANGES=1"
    goto :check_done
)

:check_done
if not defined HAS_CHANGES (
    echo [INFO] Brak nowych zmian w kodzie do wyslania.
    echo Twoj projekt na tym komputerze jest w 100%% zsynchronizowany z GitHubem.
    echo.
    echo Nacisnij dowolny klawisz, aby zamknac to okno...
    pause >nul
    exit /b 0
)

echo Wykryto zmiany w projekcie:
git status -s
echo.
echo ----------------------------------------------------------------
set "COMMIT_MSG="
set /p COMMIT_MSG="Podaj krotki opis zmian (lub wcisnij Enter dla automatycznego): "
if not defined COMMIT_MSG (
    set "COMMIT_MSG=Aktualizacja projektu i pamieci serii [%DATE%]"
)

echo.
echo [1/3] Dodawanie plikow do paczki (git add)...
git add .

echo [2/3] Zapisywanie zmian (git commit)...
git commit -m "%COMMIT_MSG%"

echo [3/3] Wysylanie do chmury GitHuba (git push)...
git push origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ================================================================
    echo [SUKCES] Zmiany zostaly pomyslnie wyslane do GitHuba!
    echo Mozesz teraz przejsc na drugi komputer i uruchomic tam:
    echo   -> POBIERZ_ZMIANY_Z_CHMURY.bat
    echo ================================================================
) else (
    echo.
    echo ================================================================
    echo [BLAD] Nie udalo sie wyslac zmian do GitHuba.
    echo Sprawdz polaczenie internetowe lub uprawnienia do repozytorium.
    echo ================================================================
)

echo.
echo Nacisnij dowolny klawisz, aby zamknac to okno...
pause >nul
