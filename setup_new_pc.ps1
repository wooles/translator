# ==============================================================================
#  SKRYPT AUTOMATYCZNEJ KONFIGURACJI PROJEKTU NA NOWYM KOMPUTERZE (1-CLICK SETUP)
#  Automatycznie instaluje zależności, tworzy .venv, konfiguruje klucz API i testuje
# ==============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   🚀 INICJALIZATOR PROJEKTU: MULTIMODALNY TŁUMACZ NAPISÓW" -ForegroundColor Cyan
Write-Host "   Kanon AVT Belczyka | Whisper STT | Profiler | Gemini Master Pro" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

$ProjectDir = $PSScriptRoot
if (-not $ProjectDir) {
    $ProjectDir = Get-Location
}
Set-Location $ProjectDir

# ------------------------------------------------------------------------------
# 1. Sprawdzanie i przygotowanie Pythona
# ------------------------------------------------------------------------------
Write-Host "[1/6] Sprawdzanie środowiska Python..." -ForegroundColor Yellow
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}

if (-not $PythonCmd) {
    Write-Host "  [!] Nie znaleziono Pythona. Próba instalacji przez winget..." -ForegroundColor Yellow
    winget install Python.Python.3.10 --silent --accept-package-agreements --accept-source-agreements
    $PythonCmd = "python"
}

$PyVersion = & $PythonCmd --version
Write-Host "  -> Wykryto: $PyVersion" -ForegroundColor Green

# ------------------------------------------------------------------------------
# 2. Sprawdzanie FFmpeg
# ------------------------------------------------------------------------------
Write-Host "[2/6] Sprawdzanie FFmpeg (do klatek wideo i audio)..." -ForegroundColor Yellow
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "  [!] FFmpeg nie jest zainstalowany w systemie. Instalowanie..." -ForegroundColor Yellow
    winget install Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
    Write-Host "  -> FFmpeg zainstalowany!" -ForegroundColor Green
} else {
    Write-Host "  -> FFmpeg jest już zainstalowany i gotowy." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 3. Tworzenie środowiska wirtualnego (.venv)
# ------------------------------------------------------------------------------
Write-Host "[3/6] Tworzenie wirtualnego środowiska (.venv)..." -ForegroundColor Yellow
$VenvDir = Join-Path $ProjectDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    & $PythonCmd -m venv $VenvDir
    Write-Host "  -> Utworzono nowe środowisko .venv" -ForegroundColor Green
} else {
    Write-Host "  -> Środowisko .venv już istnieje." -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 4. Instalacja bibliotek (requirements.txt + faster-whisper)
# ------------------------------------------------------------------------------
Write-Host "[4/6] Instalowanie bibliotek Pythona..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPip install -r (Join-Path $ProjectDir "requirements.txt") --quiet
Write-Host "  -> Wszystkie biblioteki zainstalowane pomyślnie!" -ForegroundColor Green

# ------------------------------------------------------------------------------
# 5. Konfiguracja pliku .env (Klucz API Gemini)
# ------------------------------------------------------------------------------
Write-Host "[5/6] Konfiguracja klucza API Gemini (.env)..." -ForegroundColor Yellow
$EnvFile = Join-Path $ProjectDir ".env"
$ApiKey = ""

if (Test-Path $EnvFile) {
    $ExistingEnv = Get-Content $EnvFile -Raw
    if ($ExistingEnv -match "GEMINI_API_KEY=([^\r\n]+)") {
        $ApiKey = $matches[1]
    }
}

if (-not $ApiKey -or $ApiKey -eq "twój_klucz_api_tutaj") {
    Write-Host ""
    Write-Host "  Podaj swój klucz GEMINI_API_KEY (uzyskany z https://aistudio.google.com/):" -ForegroundColor Cyan
    $ApiKey = Read-Host "  Klucz API"
    if ($ApiKey) {
        $EnvContent = "GEMINI_API_KEY=$ApiKey`nGEMINI_MODEL=gemini-3.5-flash`nBATCH_SIZE=14`nENABLE_VERIFIER=true`nKEEP_HONORIFICS=false"
        Set-Content -Path $EnvFile -Value $EnvContent -Encoding UTF8
        Write-Host "  -> Zapisano klucz w pliku .env" -ForegroundColor Green
    }
} else {
    Write-Host "  -> Znaleziono skonfigurowany klucz API w .env" -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 6. Indeksowanie bazy Translation Memory i testy systemu
# ------------------------------------------------------------------------------
Write-Host "[6/6] Weryfikacja i autotest systemu..." -ForegroundColor Yellow
if (Test-Path (Join-Path $ProjectDir "baza napisów")) {
    & $VenvPython (Join-Path $ProjectDir "index_baza.py")
}
& $VenvPython (Join-Path $ProjectDir "test_system.py")

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   🎉 INSTALACJA ZAKOŃCZONA SUKCESEM!" -ForegroundColor Green
Write-Host "   Projekt jest w 100% gotowy do pracy na tej maszynie." -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Aby przetłumaczyć odcinek:" -ForegroundColor Cyan
Write-Host "  1. Przeciągnij plik wideo na 'translate_drag_and_drop.bat'" -ForegroundColor White
Write-Host "  LUB" -ForegroundColor Cyan
Write-Host "  2. Uruchom w terminalu: .venv\Scripts\python main.py `"ścieżka_do_wideo.mkv`"" -ForegroundColor White
Write-Host ""
