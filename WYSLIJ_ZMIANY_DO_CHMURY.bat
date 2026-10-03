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

:: Sprawdz czy git ma skonfigurowanego uzytkownika (zabezpieczenie nowego PC)
git config user.name >nul 2>&1
if %ERRORLEVEL% neq 0 (
    git config user.name "Piotrek"
    git config user.email "piotrek@translator.local"
)

echo [2/3] Zapisywanie zmian (git commit)...
git commit -m "%COMMIT_MSG%"

echo [3/3] Wysylanie do chmury GitHuba (git push)...
git push origin main

if %ERRORLEVEL% equ 0 goto :success_push

echo.
echo [INFO] W chmurze znajduja sie nowsze zmiany z drugiego komputera.
echo Proba automatycznego scalenia (git pull --no-rebase)...
git pull --no-rebase origin main --no-edit
if %ERRORLEVEL% neq 0 goto :error_push

echo [OK] Zmiany zostaly pomyslnie scalone! Ponawiam wysylanie...
git push origin main
if %ERRORLEVEL% equ 0 goto :success_merge_push

:error_push
echo.
echo ================================================================
echo [BLAD] Nie udalo sie wyslac zmian do GitHuba.
echo Sprawdz polaczenie internetowe lub uprawnienia do repozytorium.
echo ================================================================
goto :end_script

:success_merge_push
echo.
echo ================================================================
echo [SUKCES] Zmiany zostaly pomyslnie scalone i wyslane do GitHuba!
echo ================================================================
goto :end_script

:success_push
echo.
echo ================================================================
echo [SUKCES] Zmiany zostaly pomyslnie wyslane do GitHuba!
echo Mozesz teraz przejsc na drugi komputer i uruchomic tam:
echo   -> POBIERZ_ZMIANY_Z_CHMURY.bat
echo ================================================================
goto :end_script

:end_script
echo.
echo Nacisnij dowolny klawisz, aby zamknac to okno...
pause >nul
