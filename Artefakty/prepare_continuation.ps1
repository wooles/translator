# prepare_continuation.ps1
# Skrypt przygotowuje pliki wymagane do kontynuacji rozmowy w nowym oknie czatu.
# Uruchom z katalogu repo: C:\Users\Piotrek\Desktop\translator
# Wersja: pure ASCII (bez polskich znakow diakrytycznych) - kompatybilna z Windows PowerShell 5.1

$ErrorActionPreference = "Stop"

# === KONFIGURACJA ===
$RepoRoot     = "C:\Users\Piotrek\Desktop\translator"
$ArtefaktyDir = Join-Path $RepoRoot "Artefakty"
$OutDir       = Join-Path $ArtefaktyDir "_KONTYNUACJA_CZATU"

# === WALIDACJA ===
if (-not (Test-Path $RepoRoot)) {
    Write-Host "BLAD: Repo nie istnieje: $RepoRoot" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $ArtefaktyDir)) {
    Write-Host "BLAD: Katalog Artefakty nie istnieje: $ArtefaktyDir" -ForegroundColor Red
    Write-Host "Utworz go recznie i uruchom ponownie." -ForegroundColor Yellow
    exit 1
}

# === PRZYGOTOWANIE KATALOGU WYJSCIOWEGO ===
if (Test-Path $OutDir) {
    Write-Host "Katalog docelowy juz istnieje: $OutDir" -ForegroundColor Yellow
    $resp = Read-Host "Nadpisac? (t/n)"
    if ($resp -ne "t") {
        Write-Host "Przerwano." -ForegroundColor Yellow
        exit 0
    }
    Remove-Item -Recurse -Force $OutDir
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
Write-Host "Katalog docelowy: $OutDir" -ForegroundColor Cyan
Write-Host ""

# === STRUKTURA KOPIOWANIA ===
# Kazda pozycja: sciezka zrodlowa (wzgledem RepoRoot), sciezka docelowa w OutDir, tier, wymagany
$files = @(
    # === TIER 1 - BEZWZGLEDNIE WYMAGANE ===
    @{ Src = "Artefakty\Prompt_10.0.3.md";                                              Dst = "TIER1\Prompt_10.0.3.md";                                              Tier = 1; Req = $true  },
    @{ Src = "Artefakty\Raport_wdrozenia_10.0.3.md";                                    Dst = "TIER1\Raport_wdrozenia_10.0.3.md";                                    Tier = 1; Req = $true  },
    @{ Src = "Artefakty\Wdrozenie_Standardu_10.0.3_10.1.txt";                           Dst = "TIER1\Wdrozenie_Standardu_10.0.3_10.1.txt";                           Tier = 1; Req = $false },
    @{ Src = "series_memory\Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json";        Dst = "TIER1\Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json";            Tier = 1; Req = $true  },
    @{ Src = "series_memory.py";                                                        Dst = "TIER1\series_memory.py";                                              Tier = 1; Req = $true  },
    @{ Src = "scene_discourse.py";                                                      Dst = "TIER1\scene_discourse.py";                                            Tier = 1; Req = $true  },
    @{ Src = "translator.py";                                                           Dst = "TIER1\translator.py";                                                 Tier = 1; Req = $true  },

    # === TIER 2 - KONTEKST HISTORYCZNY ===
    @{ Src = "Artefakty\Prompt_9.7.md";                                                 Dst = "TIER2\Prompt_9.7.md";                                                 Tier = 2; Req = $true  },
    @{ Src = "Artefakty\Prompt_9.10.md";                                                Dst = "TIER2\Prompt_9.10.md";                                                Tier = 2; Req = $false },
    @{ Src = "Artefakty\Prompt_9.10.1.md";                                              Dst = "TIER2\Prompt_9.10.1.md";                                              Tier = 2; Req = $false },
    @{ Src = "Artefakty\Prompt_10.0.md";                                                Dst = "TIER2\Prompt_10.0.md";                                                Tier = 2; Req = $false },
    @{ Src = "Artefakty\Raport_wdrozenia_9.10.md";                                      Dst = "TIER2\Raport_wdrozenia_9.10.md";                                      Tier = 2; Req = $false },
    @{ Src = "Artefakty\Raport_wdrozenia_9.10.1.md";                                    Dst = "TIER2\Raport_wdrozenia_9.10.1.md";                                    Tier = 2; Req = $false },
    @{ Src = "Artefakty\Raport_wdrozenia_10.0.md";                                      Dst = "TIER2\Raport_wdrozenia_10.0.md";                                      Tier = 2; Req = $false },
    @{ Src = "Artefakty\Raport_wdrozenia_10.0a.md";                                     Dst = "TIER2\Raport_wdrozenia_10.0a.md";                                     Tier = 2; Req = $false },
    @{ Src = "Artefakty\Raport_wdrozenia_10.0.2.md";                                    Dst = "TIER2\Raport_wdrozenia_10.0.2.md";                                    Tier = 2; Req = $false },
    @{ Src = "Artefakty\Raport_wdrozenia_10.0.2a.md";                                   Dst = "TIER2\Raport_wdrozenia_10.0.2a.md";                                   Tier = 2; Req = $false },

    # === TIER 3 - CLEANUP (opcjonalne - jesli wracasz z raportem) ===
    @{ Src = "Artefakty\cleanup_report.md";                                             Dst = "TIER3\cleanup_report.md";                                             Tier = 3; Req = $false },
    @{ Src = "Artefakty\cleanup_runtime_modules.txt";                                   Dst = "TIER3\cleanup_runtime_modules.txt";                                   Tier = 3; Req = $false },
    @{ Src = "Artefakty\cleanup_before_tracked.txt";                                    Dst = "TIER3\cleanup_before_tracked.txt";                                    Tier = 3; Req = $false },
    @{ Src = "Artefakty\cleanup_before_py.txt";                                         Dst = "TIER3\cleanup_before_py.txt";                                         Tier = 3; Req = $false },
    @{ Src = "Artefakty\cleanup_before_bibles.txt";                                     Dst = "TIER3\cleanup_before_bibles.txt";                                     Tier = 3; Req = $false },

    # === TIER 4 - AUDYT KUMULATYWNY (opcjonalne - jesli uruchamiasz) ===
    @{ Src = "Artefakty\Prompt_audyt_kumulatywny_9_3_10_0_3.md";                        Dst = "TIER4\Prompt_audyt_kumulatywny_9_3_10_0_3.md";                        Tier = 4; Req = $false },

    # === TIER 5 - DECYZJE I BACKLOG (opcjonalne) ===
    @{ Src = "Artefakty\Backlog_10.1.md";                                               Dst = "TIER5\Backlog_10.1.md";                                               Tier = 5; Req = $false },
    @{ Src = "Artefakty\Prompt_10.1.md";                                                Dst = "TIER5\Prompt_10.1.md";                                                Tier = 5; Req = $false }
)

# === KOPIOWANIE ===
$copied   = @()
$missing  = @()
$optional = @()

foreach ($f in $files) {
    $srcFull = Join-Path $RepoRoot $f.Src
    $dstFull = Join-Path $OutDir $f.Dst
    $dstDir  = Split-Path $dstFull -Parent

    if (-not (Test-Path $dstDir)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }

    if (Test-Path $srcFull) {
        Copy-Item -Path $srcFull -Destination $dstFull -Force
        $copied += [PSCustomObject]@{ Tier = $f.Tier; Src = $f.Src; Dst = $f.Dst; Required = $f.Req }
        Write-Host ("  [OK]   TIER {0}  {1}" -f $f.Tier, $f.Src) -ForegroundColor Green
    } else {
        if ($f.Req) {
            $missing += [PSCustomObject]@{ Tier = $f.Tier; Src = $f.Src; Required = $true }
            Write-Host ("  [BRAK] TIER {0}  {1}  <-- WYMAGANY" -f $f.Tier, $f.Src) -ForegroundColor Red
        } else {
            $optional += [PSCustomObject]@{ Tier = $f.Tier; Src = $f.Src; Required = $false }
            Write-Host ("  [opcj] TIER {0}  {1}  (brak - nie jest wymagany)" -f $f.Tier, $f.Src) -ForegroundColor DarkGray
        }
    }
}

# === DODATKOWE PLIKI - jesli istnieja w repo ===
Write-Host ""
Write-Host "=== Dodatkowe pliki (opcjonalne) ===" -ForegroundColor Cyan
$extraFiles = @(
    @{ Src = "avt_linter.py";                                                            Dst = "TIER1_DODATKOWE\avt_linter.py";                                       Tier = 1 },
    @{ Src = "verifier.py";                                                              Dst = "TIER1_DODATKOWE\verifier.py";                                         Tier = 1 },
    @{ Src = "main.py";                                                                  Dst = "TIER1_DODATKOWE\main.py";                                             Tier = 1 },
    @{ Src = "rules.py";                                                                 Dst = "TIER1_DODATKOWE\rules.py";                                            Tier = 1 },
    @{ Src = "metadata.py";                                                              Dst = "TIER1_DODATKOWE\metadata.py";                                         Tier = 1 },
    @{ Src = "profiler.py";                                                              Dst = "TIER1_DODATKOWE\profiler.py";                                         Tier = 1 },
    @{ Src = "pytest.ini";                                                               Dst = "TIER1_DODATKOWE\pytest.ini";                                          Tier = 1 },
    @{ Src = "test_system.py";                                                           Dst = "TIER1_DODATKOWE\test_system.py";                                      Tier = 1 },
    @{ Src = "series_memory\Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json";     Dst = "TIER1_DODATKOWE\Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json"; Tier = 1 },
    @{ Src = "series_memory\Tenmaku_no_Jaadugar_bible.json";                             Dst = "TIER1_DODATKOWE\Tenmaku_no_Jaadugar_bible.json";                      Tier = 1 }
)

foreach ($f in $extraFiles) {
    $srcFull = Join-Path $RepoRoot $f.Src
    $dstFull = Join-Path $OutDir $f.Dst
    $dstDir  = Split-Path $dstFull -Parent

    if (Test-Path $srcFull) {
        if (-not (Test-Path $dstDir)) {
            New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
        }
        Copy-Item -Path $srcFull -Destination $dstFull -Force
        Write-Host ("  [OK]   {0}" -f $f.Src) -ForegroundColor Green
        $copied += [PSCustomObject]@{ Tier = $f.Tier; Src = $f.Src; Dst = $f.Dst; Required = $false }
    } else {
        Write-Host ("  [opcj] {0}  (brak - nie jest wymagany)" -f $f.Src) -ForegroundColor DarkGray
    }
}

# === GENEROWANIE MANIFESTU ===
$manifestPath = Join-Path $OutDir "MANIFEST_KONTYNUACJA.txt"
$manifest = @()
$manifest += "MANIFEST KONTYNUACJI CZATU"
$manifest += "Wygenerowano: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$manifest += "Repo: $RepoRoot"
$manifest += "Katalog: $OutDir"
$manifest += ""
$manifest += "=== SKOPIOWANE PLIKI ($($copied.Count)) ==="
foreach ($c in $copied) {
    $manifest += ("TIER {0}  {1}" -f $c.Tier, $c.Dst)
}
$manifest += ""
$manifest += "=== BRAKUJACE PLIKI WYMAGANE ($($missing.Count)) ==="
if ($missing.Count -eq 0) {
    $manifest += "(brak - wszystkie wymagane pliki skopiowane)"
} else {
    foreach ($m in $missing) {
        $manifest += ("TIER {0}  {1}" -f $m.Tier, $m.Src)
    }
}
$manifest += ""
$manifest += "=== BRAKUJACE PLIKI OPCJONALNE ($($optional.Count)) ==="
if ($optional.Count -eq 0) {
    $manifest += "(brak - wszystkie opcjonalne pliki skopiowane)"
} else {
    foreach ($o in $optional) {
        $manifest += ("TIER {0}  {1}" -f $o.Tier, $o.Src)
    }
}
$manifest += ""
$manifest += "=== INSTRUKCJA ==="
$manifest += "1. Otworz nowe okno czatu."
$manifest += "2. Wklej tresc promptu kontynuacyjnego jako pierwsza wiadomosc."
$manifest += "3. Zalacz pliki z katalogow TIER1 i TIER2."
$manifest += "4. Jesli wracasz z raportem cleanupu - zalacz rowniez katalog TIER3."
$manifest += "5. Jesli uruchamiasz audyt kumulatywny - zalacz katalog TIER4."

$manifest | Out-File -FilePath $manifestPath -Encoding UTF8
Write-Host ""
Write-Host "Manifest: $manifestPath" -ForegroundColor Cyan

# === PODSUMOWANIE ===
Write-Host ""
Write-Host "================ PODSUMOWANIE ================" -ForegroundColor Cyan
Write-Host "Skopiowane:           $($copied.Count)" -ForegroundColor Green
if ($missing.Count -eq 0) {
    Write-Host "Brakujace wymagane:   0" -ForegroundColor Green
} else {
    Write-Host "Brakujace wymagane:   $($missing.Count)" -ForegroundColor Red
}
Write-Host "Brakujace opcjonalne: $($optional.Count)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Katalog docelowy: $OutDir" -ForegroundColor Cyan
Write-Host ""

if ($missing.Count -gt 0) {
    Write-Host "UWAGA: Brakuje $($missing.Count) wymaganych plikow." -ForegroundColor Red
    Write-Host "Uzupelnij je recznie lub sprawdz sciezki w skrypcie." -ForegroundColor Yellow
    exit 2
}

Write-Host "Wszystkie wymagane pliki skopiowane. Gotowe do kontynuacji." -ForegroundColor Green
Write-Host ""
Write-Host "Kolejne kroki:" -ForegroundColor Cyan
Write-Host "1. Otworz nowe okno czatu."
Write-Host "2. Wklej prompt kontynuacyjny jako pierwsza wiadomosc."
Write-Host "3. Zalacz pliki z: $OutDir\TIER1"
Write-Host "4. Zalacz pliki z: $OutDir\TIER2"
Write-Host "5. (Opcjonalnie) Zalacz TIER3 (cleanup) lub TIER4 (audyt)."
exit 0