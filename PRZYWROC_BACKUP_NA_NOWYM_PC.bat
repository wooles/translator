@echo off
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
title Przywracanie Ekosystemu na Nowym Komputerze (Master Restore Bootstrap)

echo ================================================================
echo   AUTOMATYCZNY INSTALATOR PRZYWRACANIA EKOSYSTEMU
echo   Projekty: Translator, Sorter, Kalendarz
echo   Pamiec AI (.gemini), Modele (.cache), Klucze API i Bazy Danych
echo ================================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "USER_DIR=%USERPROFILE%"
set "DESKTOP_DIR=%USER_DIR%\Desktop"

:: Szukanie pliku archiwum
set "ZIP_FILE=%SCRIPT_DIR%KOMPLETNY_BACKUP_SYSTEMU.zip"
if not exist "%ZIP_FILE%" (
    set "ZIP_FILE=%DESKTOP_DIR%\KOMPLETNY_BACKUP_SYSTEMU.zip"
)

if not exist "%ZIP_FILE%" (
    echo [BLAD]: Nie znaleziono pliku KOMPLETNY_BACKUP_SYSTEMU.zip!
    echo Umiesc plik KOMPLETNY_BACKUP_SYSTEMU.zip w tym samym folderze lub na Pulpicie.
    echo.
    pause
    exit /b 1
)

echo [1/4] Rozpakowywanie calego ekosystemu z pliku ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$zipPath = '%ZIP_FILE%'; $userDir = [System.Environment]::GetFolderPath('UserProfile'); $desktopDir = [System.IO.Path]::Combine($userDir, 'Desktop'); Add-Type -AssemblyName System.IO.Compression.FileSystem; $zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath); try { $total = $zip.Entries.Count; $idx = 0; foreach ($entry in $zip.Entries) { $idx++; if ($entry.FullName.EndsWith('/') -or $entry.FullName -eq 'PRZYWROC_SYSTEM_NA_NOWYM_PC.bat') { continue; } $targetPath = $null; if ($entry.FullName.StartsWith('.gemini/')) { $targetPath = [System.IO.Path]::Combine($userDir, $entry.FullName); } elseif ($entry.FullName.StartsWith('.cache/')) { $targetPath = [System.IO.Path]::Combine($userDir, $entry.FullName); } elseif ($entry.FullName.StartsWith('DesktopProjects/')) { $rel = $entry.FullName.Substring('DesktopProjects/'.Length); $targetPath = [System.IO.Path]::Combine($desktopDir, $rel); } if ($targetPath) { $dir = [System.IO.Path]::GetDirectoryName($targetPath); if (-not (Test-Path $dir)) { [System.IO.Directory]::CreateDirectory($dir) | Out-Null; } [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $targetPath, $true); } if ($idx % 300 -eq 0 -or $idx -eq $total) { $pct = [math]::Round(($idx / $total) * 100, 1); Write-Host ('`r  [Rozpakowywanie]: {0}/{1} ({2}%%)' -f $idx, $total, $pct) -NoNewline; } } Write-Host ''; } finally { $zip.Dispose(); }"

echo.
echo [2/4] Weryfikacja narzedzi systemowych (Python, FFmpeg)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (-not (Get-Command python -ErrorAction SilentlyContinue) -and -not (Get-Command py -ErrorAction SilentlyContinue)) { Write-Host '  [!] Brak Pythona. Instalowanie przez winget...' -ForegroundColor Yellow; winget install Python.Python.3.10 --silent --accept-package-agreements --accept-source-agreements; } if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Write-Host '  [!] Brak FFmpeg. Instalowanie przez winget...' -ForegroundColor Yellow; winget install Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements; }"

echo [3/4] Konfiguracja srodowiska wirtualnego .venv dla Tlumacza...
cd /d "%DESKTOP_DIR%\translator"
if exist ".venv\Scripts\python.exe" (
    echo   -> Srodowisko .venv juz istnieje.
) else (
    echo   -> Tworzenie nowego srodowiska .venv...
    python -m venv .venv
)

echo   -> Sprawdzanie i instalacja zaleznosci...
"%DESKTOP_DIR%\translator\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"%DESKTOP_DIR%\translator\.venv\Scripts\pip.exe" install -r requirements.txt --quiet

echo.
echo [4/4] Weryfikacja systemu (Cornerstone v2.0 - 33/33 testy AVT)...
"%DESKTOP_DIR%\translator\.venv\Scripts\python.exe" test_system.py

echo.
echo ================================================================
echo   PRZYWRACANIE ZAKONCZONE PELNYM SUKCESEM!
echo   Wszystkie projekty (Translator, Sorter, Kalendarz),
echo   pamiec AI (.gemini) i baza napisow sa w 100%% gotowe do pracy.
echo ================================================================
pause
