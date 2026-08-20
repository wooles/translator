@echo off
chcp 65001 >nul
title Master Suite Installer - Wooles Anime Toolkit

echo ================================================================
echo   Inicjalizacja instalatora wszystkich projektow...
echo ================================================================
echo.

PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_all_projects.ps1"

pause
