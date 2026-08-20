@echo off
chcp 65001 >nul
title Inicjalizacja Tłumacza Napisów na Nowym Komputerze

echo ================================================================
echo   Uruchamianie automatycznej konfiguratora srodowiska...
echo ================================================================
echo.

PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_new_pc.ps1"

pause
