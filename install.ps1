# ==============================================================================
#  UNIVERSAL 1-COMMAND INSTALLER FOR MULTIMODAL TRANSLATOR
#  Uruchomienie: irm https://raw.githubusercontent.com/wooles/translator/main/install.ps1 | iex
# ==============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   🚀 UNIWERSALNY INSTALATOR: MULTIMODALNY TŁUMACZ NAPISÓW" -ForegroundColor Cyan
Write-Host "   Kanon AVT Belczyka | Whisper STT | Profiler | Gemini Master Pro" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------------------
# 1. Wybór folderu docelowego przez natywne okienko Windows
# ------------------------------------------------------------------------------
Add-Type -AssemblyName System.Windows.Forms
$FolderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
$FolderBrowser.Description = "Wybierz folder, w którym chcesz zapisać projekt tłumacza (np. na dysku D:\ lub C:\):"
$FolderBrowser.ShowNewFolderButton = $true

$DefaultTargetParent = [System.IO.Path]::Combine($env:USERPROFILE, "Desktop")
if ($FolderBrowser.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK -and $FolderBrowser.SelectedPath) {
    $TargetParent = $FolderBrowser.SelectedPath
} else {
    $TargetParent = $DefaultTargetParent
}

$InstallDir = Join-Path $TargetParent "translator"
Write-Host "[1/6] Lokalizacja instalacji: $InstallDir" -ForegroundColor Green

# ------------------------------------------------------------------------------
# 2. Sprawdzanie i instalacja narzędzi systemowych (Git, Python, FFmpeg)
# ------------------------------------------------------------------------------
Write-Host "[2/6] Sprawdzanie narzędzi systemowych..." -ForegroundColor Yellow

# Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "  -> Instalowanie Git przez winget..." -ForegroundColor Yellow
    winget install Git.Git --silent --accept-package-agreements --accept-source-agreements
}

# Python
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
}
if (-not $PythonCmd) {
    Write-Host "  -> Instalowanie Python 3.10 przez winget..." -ForegroundColor Yellow
    winget install Python.Python.3.10 --silent --accept-package-agreements --accept-source-agreements
    $PythonCmd = "python"
}

# FFmpeg
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "  -> Instalowanie FFmpeg przez winget..." -ForegroundColor Yellow
    winget install Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
}

# ------------------------------------------------------------------------------
# 3. Klonowanie repozytorium do wybranego folderu
# ------------------------------------------------------------------------------
Write-Host "[3/6] Pobieranie repozytorium z GitHuba..." -ForegroundColor Yellow
if (-not (Test-Path $InstallDir)) {
    git clone https://github.com/wooles/translator.git $InstallDir
    Write-Host "  -> Sklonowano repozytorium do: $InstallDir" -ForegroundColor Green
} else {
    Write-Host "  -> Folder $InstallDir już istnieje. Aktualizowanie kodu..." -ForegroundColor Yellow
    Set-Location $InstallDir
    git pull origin main
}

Set-Location $InstallDir

# ------------------------------------------------------------------------------
# 4. Tworzenie środowiska wirtualnego i instalacja bibliotek
# ------------------------------------------------------------------------------
Write-Host "[4/6] Konfiguracja środowiska wirtualnego (.venv)..." -ForegroundColor Yellow
$VenvDir = Join-Path $InstallDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    & $PythonCmd -m venv $VenvDir
}

Write-Host "  -> Instalowanie bibliotek Pythona (Whisper STT, Gemini API, PySubs2)..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPip install -r (Join-Path $InstallDir "requirements.txt") --quiet
Write-Host "  -> Biblioteki zainstalowane pomyślnie!" -ForegroundColor Green

# ------------------------------------------------------------------------------
# 5. Konfiguracja klucza API Gemini (.env)
# ------------------------------------------------------------------------------
Write-Host "[5/6] Konfiguracja klucza API Gemini..." -ForegroundColor Yellow
$EnvFile = Join-Path $InstallDir ".env"
$ApiKey = ""

if (Test-Path $EnvFile) {
    $ExistingEnv = Get-Content $EnvFile -Raw
    if ($ExistingEnv -match "GEMINI_API_KEY=([^\r\n]+)") {
        $ApiKey = $matches[1]
    }
}

if (-not $ApiKey -or $ApiKey -eq "twój_klucz_api_tutaj") {
    Write-Host ""
    Write-Host "  Wpisz swój klucz GEMINI_API_KEY (z https://aistudio.google.com/):" -ForegroundColor Cyan
    $ApiKey = Read-Host "  GEMINI_API_KEY"
    if ($ApiKey) {
        $EnvContent = "GEMINI_API_KEY=$ApiKey`nGEMINI_MODEL=gemini-3.7-flash`nBATCH_SIZE=24`nENABLE_VERIFIER=true`nKEEP_HONORIFICS=true"
        Set-Content -Path $EnvFile -Value $EnvContent -Encoding UTF8
        Write-Host "  -> Zapisano klucz w pliku .env" -ForegroundColor Green
    }
} else {
    Write-Host "  -> Wykryto istniejący klucz API w .env" -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 6. Indeksowanie bazy i weryfikacja
# ------------------------------------------------------------------------------
Write-Host "[6/6] Indeksowanie Pamięci Tłumaczeniowej i testy..." -ForegroundColor Yellow
if (Test-Path (Join-Path $InstallDir "baza napisów")) {
    & $VenvPython (Join-Path $InstallDir "index_baza.py")
}
& $VenvPython (Join-Path $InstallDir "test_system.py")

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   🎉 INSTALACJA ZAKOŃCZONA SUKCESEM!" -ForegroundColor Green
Write-Host "   Projekt został zainstalowany w: $InstallDir" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Możesz teraz przeciągać pliki wideo na:" -ForegroundColor Cyan
Write-Host "  $InstallDir\translate_drag_and_drop.bat" -ForegroundColor White
Write-Host ""
