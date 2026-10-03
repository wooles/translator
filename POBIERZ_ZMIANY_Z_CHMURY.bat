@echo off
chcp 65001 >nul
title Pobieranie i Scalanie Zmian z GitHuba
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ================================================================
echo   POBIERANIE I SCALANIE ZMIAN Z GITHUBA (GIT PULL)
echo ================================================================
echo.

:: 1. Bezpieczenstwo: jesli sa niezapisane zmiany lokalne, zabezpiecz je przed scaleniem
set "HAS_LOCAL="
for /f "tokens=*" %%a in ('git status --porcelain') do (
    set "HAS_LOCAL=1"
    goto :local_check_done
)

:local_check_done
if defined HAS_LOCAL (
    echo [INFO] Wykryto niezapisane zmiany lokalne na tym komputerze.
    echo Zabezpieczam je automatycznie przed scaleniem (auto-commit)...
    git add .
    git commit -m "Automatyczny zapis lokalnych zmian przed pobraniem [%DATE% %TIME%]"
    echo [OK] Lokalne zmiany zostaly bezpiecznie utrwalone.
    echo.
)

:: 2. Pobranie i bezpieczne scalenie uzupelniajace (3-way merge)
echo [1/2] Pobieranie i uzupelnianie kodu o zmiany z drugiego komputera...
git pull --no-rebase origin main

if %ERRORLEVEL% equ 0 (
    echo.
    echo ================================================================
    echo [SUKCES] Twoj kod zostal pomyslnie zaktualizowany i uzupelniony!
    echo Zmiany z obu komputerow zostaly bezpiecznie scalone.
    echo Mozesz teraz bezpiecznie rozpoczac prace lub tlumaczenie.
    echo ================================================================
) else (
    echo.
    echo ================================================================
    echo [UWAGA] Wystapil konflikt w tych samych linijkach kodu.
    echo Zaden plik nie zostal skasowany. Sprawdz pliki oznaczone jako CONFLICT.
    echo ================================================================
)

echo.
echo Nacisnij dowolny klawisz, aby zamknac to okno...
pause >nul
