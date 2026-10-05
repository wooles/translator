@echo off
chcp 65001 >nul
title Wysylanie Zmian do GitHuba
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ================================================================
echo   WYSLANIE NOWYCH ZMIAN NA GITHUB [GIT PUSH]
echo ================================================================
echo.

:: 1. Sprawdz czy Git jest zainstalowany w systemie
where git >nul 2>&1
if %ERRORLEVEL% neq 0 goto :error_no_git

:: 2. Sprawdz czy jestesmy w repozytorium Git
if not exist ".git" goto :error_no_repo

:: 3. Sprawdz i skonfiguruj tozsamosc Git [zabezpieczenie nowego PC]
git config user.name >nul 2>&1
if %ERRORLEVEL% neq 0 git config user.name "Piotrek"
git config user.email >nul 2>&1
if %ERRORLEVEL% neq 0 git config user.email "piotrek@translator.local"

:: 4. Sprawdz czy sa niezapisane zmiany w plikach roboczych
set "HAS_CHANGES="
for /f "tokens=*" %%a in ('git status --porcelain') do (
    set "HAS_CHANGES=1"
    goto :check_changes_done
)

:check_changes_done
if not defined HAS_CHANGES goto :check_clean_state

echo Wykryto niezapisane zmiany w projekcie:
git status -s
echo.
echo ----------------------------------------------------------------
set "COMMIT_MSG=Aktualizacja projektu i pamieci serii [%DATE%]"
set "USER_INPUT="
set /p USER_INPUT="Podaj krotki opis zmian [lub wcisnij Enter dla automatycznego]: "
if defined USER_INPUT (
    for /f "tokens=* delims= " %%a in ("%USER_INPUT%") do set "USER_INPUT=%%a"
)
if not "%USER_INPUT%"=="" set "COMMIT_MSG=%USER_INPUT%"

echo.
echo [1/3] Dodawanie plikow do paczki [git add]...
git add .

echo [2/3] Zapisywanie zmian [git commit]...
git commit -m "%COMMIT_MSG%"
goto :do_push

:check_clean_state
echo [INFO] Brak nowych niezapisanych zmian w plikach roboczych.
echo Sprawdzam polaczenie i wysylam ewentualne wczesniejsze zatwierdzenia...
echo.

:do_push
echo [3/3] Wysylanie do chmury GitHuba [git push]...
git push origin main

if %ERRORLEVEL% equ 0 goto :success_push

echo.
echo [INFO] W chmurze znajduja sie nowsze zmiany z drugiego komputera.
echo Proba automatycznego scalenia [git pull --no-rebase]...
git pull --no-rebase origin main --no-edit
if %ERRORLEVEL% neq 0 goto :error_merge

echo [OK] Zmiany zostaly pomyslnie scalone! Ponawiam wysylanie...
git push origin main
if %ERRORLEVEL% equ 0 goto :success_merge_push

:error_merge
echo.
echo ================================================================
echo [BLAD] Nie udalo sie automatycznie wyslac zmian do GitHuba.
echo Przyczyna moze byc:
echo   1. Brak polaczenia z internetem.
echo   2. Konflikt w tych samych linijkach kodu [wymaga recznego sprawdzenia].
echo   3. Brak autoryzacji do repozytorium GitHub.
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
echo [SUKCES] Wszystko aktualne! Zmiany sa bezpiecznie zapisane na GitHubie!
echo Mozesz teraz przejsc na drugi komputer i uruchomic tam:
echo   [URUCHOM]: POBIERZ_ZMIANY_Z_CHMURY.bat
echo ================================================================
goto :end_script

:error_no_git
echo ================================================================
echo [BLAD] Program Git nie zostal znaleziony w systemie!
echo Zainstaluj Git ze strony: https://git-scm.com/download/win
echo i upewnij sie, ze zaznaczono dodanie Git do zmiennej PATH.
echo ================================================================
goto :end_script

:error_no_repo
echo ================================================================
echo [BLAD] Ten folder nie jest repozytorium Git!
echo Upewnij sie, ze skrypt znajduje sie w glownym folderze projektu:
echo %SCRIPT_DIR%
echo ================================================================
goto :end_script

:end_script
echo.
echo Nacisnij dowolny klawisz, aby zamknac to okno...
pause >nul
