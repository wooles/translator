@echo off
chcp 65001 >nul
title Pobieranie i Scalanie Zmian z GitHuba
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ================================================================
echo   POBIERANIE I SCALANIE ZMIAN Z GITHUBA [GIT PULL]
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

:: 4. Bezpieczenstwo: jesli sa niezapisane zmiany lokalne, zabezpiecz je przed scaleniem
set "HAS_LOCAL="
for /f "tokens=*" %%a in ('git status --porcelain') do (
    set "HAS_LOCAL=1"
    goto :local_check_done
)

:local_check_done
if not defined HAS_LOCAL goto :skip_local_commit

echo [INFO] Wykryto niezapisane zmiany lokalne na tym komputerze.
echo Zabezpieczam je automatycznie przed scaleniem [auto-commit]...
git add .
git commit -m "Automatyczny zapis lokalnych zmian przed pobraniem [%DATE% %TIME%]"
echo [OK] Lokalne zmiany zostaly bezpiecznie utrwalone.
echo.

:skip_local_commit

:: 5. Pobranie i bezpieczne scalenie uzupelniajace [3-way merge]
echo [1/1] Pobieranie i uzupelnianie kodu o zmiany z drugiego komputera...
git pull --no-rebase origin main --no-edit

if %ERRORLEVEL% equ 0 goto :pull_success

echo.
echo ================================================================
echo [UWAGA] Wystapil konflikt w tych samych linijkach kodu.
echo Zaden plik nie zostal skasowany. Sprawdz pliki oznaczone jako CONFLICT.
echo ================================================================
goto :end_script

:pull_success
echo.
echo ================================================================
echo [SUKCES] Twoj kod zostal pomyslnie zaktualizowany i uzupelniony!
echo Zmiany z obu komputerow zostaly bezpiecznie scalone.
echo Mozesz teraz bezpiecznie rozpoczac prace lub tlumaczenie.
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
