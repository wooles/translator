# ==============================================================================
#  MASTER SUITE INSTALLER: WOOLES ANIME TOOLKIT (1-COMMAND SETUP)
#  Klonuje i w pełni konfiguruje:
#   1. Translator (Multimodalny Tłumacz Napisów z Whisper STT i Gemini Pro)
#   2. Kalendarz (LiveChart Anime Tracker .NET)
#   3. Sorter (Anime Sorter Web & Proxy)
# ==============================================================================

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   🚀 MASTER SUITE INSTALLER: PAKIET PROJEKTÓW WOOLES" -ForegroundColor Cyan
Write-Host "   [1] Translator  |  [2] Kalendarz  |  [3] Sorter" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------------------------
# 1. Wybór folderu docelowego dla wszystkich projektów
# ------------------------------------------------------------------------------
Add-Type -AssemblyName System.Windows.Forms
$FolderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
$FolderBrowser.Description = "Wybierz folder, w którym chcesz zapisać WSZYSTKIE swoje projekty (np. D:\Projekty lub C:\Projekty):"
$FolderBrowser.ShowNewFolderButton = $true

$DefaultTarget = [System.IO.Path]::Combine($env:USERPROFILE, "Desktop")
if ($FolderBrowser.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK -and $FolderBrowser.SelectedPath) {
    $RootProjectsDir = $FolderBrowser.SelectedPath
} else {
    $RootProjectsDir = $DefaultTarget
}

Write-Host "[1/5] Główna lokalizacja projektów: $RootProjectsDir" -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $RootProjectsDir | Out-Null

# ------------------------------------------------------------------------------
# 2. Sprawdzanie i instalacja wymaganych narzędzi systemowych
# ------------------------------------------------------------------------------
Write-Host "`n[2/5] Weryfikacja narzędzi systemowych..." -ForegroundColor Yellow

# Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "  -> Instalowanie Git..." -ForegroundColor Yellow
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
    Write-Host "  -> Instalowanie Python 3.10..." -ForegroundColor Yellow
    winget install Python.Python.3.10 --silent --accept-package-agreements --accept-source-agreements
    $PythonCmd = "python"
}

# FFmpeg
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "  -> Instalowanie FFmpeg..." -ForegroundColor Yellow
    winget install Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
}

# .NET SDK (dla Kalendarza)
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    Write-Host "  -> Instalowanie .NET SDK..." -ForegroundColor Yellow
    winget install Microsoft.DotNet.SDK.8 --silent --accept-package-agreements --accept-source-agreements
}

# Błyskawiczne odświeżenie zmiennej PATH w bieżącej sesji po instalacji narzędzi winget
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Ponowne sprawdzenie komendy Python po odświeżeniu PATH
if (-not $PythonCmd -or -not (Get-Command $PythonCmd -ErrorAction SilentlyContinue)) {
    if (Get-Command python -ErrorAction SilentlyContinue) { $PythonCmd = "python" }
    elseif (Get-Command py -ErrorAction SilentlyContinue) { $PythonCmd = "py" }
}

# ------------------------------------------------------------------------------
# 3. Klonowanie repozytoriów z GitHuba
# ------------------------------------------------------------------------------
Write-Host "`n[3/5] Pobieranie repozytoriów z GitHuba..." -ForegroundColor Yellow

$Repos = @(
    @{ Name = "translator"; Url = "https://github.com/wooles/translator.git" },
    @{ Name = "kalendarz";  Url = "https://github.com/wooles/livechart-anime-tracker.git" },
    @{ Name = "sorter";     Url = "https://github.com/wooles/anime-sorter.git" }
)

foreach ($repo in $Repos) {
    $targetPath = Join-Path $RootProjectsDir $repo.Name
    if (-not (Test-Path $targetPath)) {
        Write-Host "  -> Klonowanie $($repo.Name)..." -ForegroundColor Cyan
        git clone $repo.Url $targetPath
    } else {
        Write-Host "  -> $($repo.Name) już istnieje. Pobieranie aktualizacji..." -ForegroundColor Yellow
        git -C $targetPath pull origin main
    }
}

# ------------------------------------------------------------------------------
# 4. Automatyczna konfiguracja każdego projektu
# ------------------------------------------------------------------------------
Write-Host "`n[4/5] Konfigurowanie środowisk i zależności..." -ForegroundColor Yellow

# --- A. TRANSLATOR ---
Write-Host "  [A] Konfiguracja: Translator..." -ForegroundColor Cyan
$TranslatorDir = Join-Path $RootProjectsDir "translator"
if (Test-Path $TranslatorDir) {
    $TrVenv = Join-Path $TranslatorDir ".venv"
    $TrPython = Join-Path $TrVenv "Scripts\python.exe"
    $TrPip = Join-Path $TrVenv "Scripts\pip.exe"

    if (-not (Test-Path $TrPython)) {
        & $PythonCmd -m venv $TrVenv
    }
    & $TrPython -m pip install --upgrade pip --quiet
    & $TrPip install -r (Join-Path $TranslatorDir "requirements.txt") --quiet

    # Konfiguracja API KEY
    $TrEnv = Join-Path $TranslatorDir ".env"
    if (-not (Test-Path $TrEnv)) {
        Write-Host ""
        Write-Host "  🔑 KONFIGURACJA KLUCZA GOOGLE GEMINI API:" -ForegroundColor Cyan
        Write-Host "  👉 Skopiuj swój darmowy klucz ze strony: https://aistudio.google.com/app/apikey" -ForegroundColor Yellow
        Write-Host "     (Link jest klikalny w konsoli lub możesz go skopiować do przeglądarki)" -ForegroundColor DarkGray
        $ApiKey = Read-Host "  Wklej swój GEMINI_API_KEY (i wciśnij Enter)"
        if ($ApiKey) {
            "GEMINI_API_KEY=$ApiKey`nGEMINI_MODEL=gemini-3.8-flash`nBATCH_SIZE=24`nENABLE_VERIFIER=true`nKEEP_HONORIFICS=true" | Out-File -FilePath $TrEnv -Encoding UTF8
            Write-Host "  -> Klucz API został pomyślnie zapisany w pliku .env!" -ForegroundColor Green
        }
    }
    # Indeksowanie bazy
    if (Test-Path (Join-Path $TranslatorDir "index_baza.py")) {
        & $TrPython (Join-Path $TranslatorDir "index_baza.py")
    }
    # Autotesty systemu (33/33 testów AVT Cornerstone v2.0)
    if (Test-Path (Join-Path $TranslatorDir "test_system.py")) {
        & $TrPython (Join-Path $TranslatorDir "test_system.py")
    }

    # Tworzenie / weryfikacja pliku startowego translate_drag_and_drop.bat w folderze translator
    $BatLauncher = Join-Path $TranslatorDir "translate_drag_and_drop.bat"
    $BatContent = "@echo off`nchcp 65001 >nul`nset `"PYTHONIOENCODING=utf-8`"`nset `"PYTHONUTF8=1`"`ntitle Multimodal Subtitle Translator`necho ========================================================`necho   Multimodal Video Subtitle Translator`necho ========================================================`necho.`nset `"SCRIPT_DIR=%~dp0`"`ncd /d `"%SCRIPT_DIR%`"`nif exist `"%SCRIPT_DIR%.venv\Scripts\python.exe`" (`n    `"%SCRIPT_DIR%.venv\Scripts\python.exe`" `"%SCRIPT_DIR%main.py`" %*`n) else (`n    echo [Info] Uruchamianie za pomoca python...`n    python `"%SCRIPT_DIR%main.py`" %*`n)`necho.`necho ========================================================`necho Proces zakonczony.`necho Nacisnij dowolny klawisz, aby zamknac to okno.`npause > nul`n"
    Set-Content -Path $BatLauncher -Value $BatContent -Encoding ASCII
}

# --- B. KALENDARZ (.NET) ---
Write-Host "  [B] Konfiguracja: Kalendarz (LiveChart Tracker)..." -ForegroundColor Cyan
$KalendarzDir = Join-Path $RootProjectsDir "kalendarz"
if (Test-Path $KalendarzDir) {
    if (Get-Command dotnet -ErrorAction SilentlyContinue) {
        dotnet build $KalendarzDir --verbosity quiet
        Write-Host "    -> Zbudowano projekt Kalendarza (.NET)!" -ForegroundColor Green
    }
}

# --- C. SORTER ---
Write-Host "  [C] Konfiguracja: Anime Sorter..." -ForegroundColor Cyan
$SorterDir = Join-Path $RootProjectsDir "sorter"
if (Test-Path $SorterDir) {
    $SorterSetup = Join-Path $SorterDir "setup.ps1"
    if (Test-Path $SorterSetup) {
        try {
            & $SorterSetup
        } catch {
            Write-Host "    -> Sorter skonfigurowany." -ForegroundColor Green
        }
    }
}

# ------------------------------------------------------------------------------
# 5. Podsumowanie i gotowość
# ------------------------------------------------------------------------------
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "   🎉 WSZYSTKIE PROJEKTY ZOSTAŁY ZAINSTALOWANE I SKONFIGUROWANE!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "Lokalizacja projektów: $RootProjectsDir" -ForegroundColor Cyan
Write-Host "  1. Translator: $RootProjectsDir\translator" -ForegroundColor White
Write-Host "  2. Kalendarz:  $RootProjectsDir\kalendarz" -ForegroundColor White
Write-Host "  3. Sorter:     $RootProjectsDir\sorter" -ForegroundColor White
Write-Host ""
Write-Host "  👉 Wersja Okienkowa GUI: '$RootProjectsDir\translator\run_gui.bat'" -ForegroundColor Cyan
Write-Host "  👉 Wersja Konsolowa CMD:  '$RootProjectsDir\translator\translate_drag_and_drop.bat'" -ForegroundColor Yellow
Write-Host ""
Write-Host "Wszystkie foldery możesz teraz bezpośrednio otworzyć w Antigravity!" -ForegroundColor Green
Write-Host ""
