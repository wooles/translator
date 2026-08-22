$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  ANIME AVT TRANSLATOR - AUTOMATYCZNY INSTALATOR I RUNNER" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".venv")) {
    Write-Host "[1/3] Tworzenie srodowiska wirtualnego .venv..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "[2/3] Instalacja i aktualizacja bibliotek..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt --quiet

if (-not (Test-Path ".env")) {
    Write-Host ""
    $key = Read-Host "[!] Wpisz swoj GEMINI_API_KEY (lub nacisnij Enter, aby wpisac pozniej)"
    if ($key) {
        "GEMINI_API_KEY=$key" | Out-File -FilePath ".env" -Encoding utf8
        Write-Host "[OK] Zapisano klucz w pliku .env" -ForegroundColor Green
    } else {
        "GEMINI_API_KEY=twoj_klucz_api_tutaj" | Out-File -FilePath ".env" -Encoding utf8
        Write-Host "[!] Utworzono szablon .env. Uzupelnij go swoim kluczem API." -ForegroundColor DarkYellow
    }
}

Write-Host ""
Write-Host "[3/3] Uruchamianie aplikacji Anime Translator GUI..." -ForegroundColor Green
Write-Host ""
& .\.venv\Scripts\python.exe gui_app.py

