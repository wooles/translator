@echo off
chcp 65001 >nul
title Anime Subtitle Translator Pro (GUI)

REM Sprawdzenie srodowiska wirtualnego
if exist .venv\Scripts\python.exe (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

REM Uruchomienie aplikacji okienkowej GUI
start "" %PYTHON_EXE% gui_app.py %*
