@echo off
chcp 65001 >nul
title Pobieranie i Scalanie Zmian z GitHuba
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ================================================================
echo   POBIERANIE I SCALANIE ZMIAN Z GITHUBA [GIT PULL]
echo ================================================================
echo.

:: Sprawdz czy git ma skonfigurowanego uzytkownika [zabezpieczenie nowego PC]
git config user.name >nul 2>&1
if %ERRORLEVEL% equ 0 goto :identity_ok
git config user.name "Piotrek"
git config user.email "piotrek@translator.local"

:identity_ok

:: 1. Bezpieczenstwo: jesli sa niezapisane zmiany lokalne, zabezpiecz je przed scaleniem
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

:: 2. Pobranie i bezpieczne scalenie uzupelniajace [3-way merge]
echo [1/2] Pobieranie i uzupelnianie kodu o zmiany z drugiego komputera...
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

:end_script
echo.
echo Nacisnij dowolny klawisz, aby zamknac to okno...
pause >nul
