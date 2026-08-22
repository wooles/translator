@echo off
chcp 65001 >nul
echo ========================================================
echo   ANIME AVT TRANSLATOR - AUTOMATYCZNY INSTALATOR I RUNNER
echo ========================================================
echo.

if not exist .venv (
    echo [1/3] Tworzenie srodowiska wirtualnego .venv...
    python -m venv .venv
)

echo [2/3] Instalacja i aktualizacja bibliotek...
.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet

if not exist .env (
    echo.
    echo [!] Brak pliku .env z kluczem API.
    set /p API_KEY="Wpisz swoj GEMINI_API_KEY (lub nacisnij Enter, aby wpisac pozniej): "
    if not "%API_KEY%"=="" (
        echo GEMINI_API_KEY=%API_KEY% > .env
        echo [OK] Zapisano klucz w pliku .env
    ) else (
        echo GEMINI_API_KEY=twoj_klucz_api_tutaj > .env
        echo [!] Utworzono szablon .env. Uzupelnij go swoim kluczem API.
    )
)

echo.
echo [3/3] Uruchamianie aplikacji Anime Translator GUI...
echo.
.venv\Scripts\python.exe gui_app.py
pause
