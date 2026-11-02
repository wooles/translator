$ErrorActionPreference = "Continue"
$RepoRoot     = "C:\Users\Piotrek\Desktop\translator"
$ArtifactsDir = Join-Path $RepoRoot "Artefakty"
$TargetDir    = Join-Path $ArtifactsDir "_AUDYT_KUMULATYWNY_9_10_1"

if (Test-Path -LiteralPath $TargetDir) { Remove-Item -LiteralPath $TargetDir -Recurse -Force }
New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  MAPOWANIE KUMULATYWNE 9.3 -> 9.10.1" -ForegroundColor Cyan
Write-Host "  Target: $TargetDir" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$allMissing = @()

function Copy-ToBatch {
    param(
        [string]$BatchName,
        [array]$Items
    )
    $batchDir = Join-Path $TargetDir $BatchName
    New-Item -ItemType Directory -Path $batchDir -Force | Out-Null
    $count = 0
    $bytes = 0
    foreach ($item in $Items) {
        $src = $item.Src
        $dst = $item.Dst
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination (Join-Path $batchDir $dst) -Force
            $size = (Get-Item -LiteralPath $src).Length
            $bytes = $bytes + $size
            $count = $count + 1
            Write-Host ("  [OK]   {0,-45} {1,10} B" -f $dst, $size) -ForegroundColor Green
        } else {
            Write-Host ("  [MISS] {0}" -f $dst) -ForegroundColor Red
            $script:allMissing = $script:allMissing + $dst
        }
    }
    $kb = [math]::Round($bytes / 1024, 1)
    Write-Host ("  -> {0}: {1} plikow, {2} KB" -f $BatchName, $count, $kb) -ForegroundColor Cyan
    Write-Host ""
}

# --- BATCH_01: Prompty 9.3 -> 9.10.1 ---
Write-Host "[BATCH_01] Prompty historyczne" -ForegroundColor Yellow
$prompts = @(
    @{Src=(Join-Path $ArtifactsDir "Prompt_9.3.md");       Dst="Prompt_9.3.md"},
    @{Src=(Join-Path $ArtifactsDir "Prompt_9.4.md");       Dst="Prompt_9.4.md"},
    @{Src=(Join-Path $ArtifactsDir "Prompt_9.5.md");       Dst="Prompt_9.5.md"},
    @{Src=(Join-Path $ArtifactsDir "Prompt_9.6.md");       Dst="Prompt_9.6.md"},
    @{Src=(Join-Path $ArtifactsDir "Prompt_9.7.md");       Dst="Prompt_9.7.md"},
    @{Src=(Join-Path $ArtifactsDir "Prompt_9.8.md");       Dst="Prompt_9.8.md"},
    @{Src=(Join-Path $ArtifactsDir "Prompt_9.9.md");       Dst="Prompt_9.9.md"},
    @{Src=(Join-Path $ArtifactsDir "Prompt_9.10.md");      Dst="Prompt_9.10.md"},
    @{Src=(Join-Path $ArtifactsDir "Prompt_9.10.1.md");    Dst="Prompt_9.10.1.md"},
    @{Src=(Join-Path $ArtifactsDir "Prompt_Depuracja_Legacy_1.0.md"); Dst="Prompt_Depuracja_Legacy_1.0.md"}
)
Copy-ToBatch -BatchName "BATCH_01_Prompts" -Items $prompts

# --- BATCH_02: Raporty 9.3 -> 9.10.1 + Depuracja ---
Write-Host "[BATCH_02] Raporty historyczne" -ForegroundColor Yellow
$reports = @(
    @{Src=(Join-Path $ArtifactsDir "Raport_wdrozenia_9.3.md");       Dst="Raport_wdrozenia_9.3.md"},
    @{Src=(Join-Path $ArtifactsDir "Raport_wdrozenia_9.4.md");       Dst="Raport_wdrozenia_9.4.md"},
    @{Src=(Join-Path $ArtifactsDir "Raport_wdrozenia_9.5.md");       Dst="Raport_wdrozenia_9.5.md"},
    @{Src=(Join-Path $ArtifactsDir "Raport_wdrozenia_9.6.md");       Dst="Raport_wdrozenia_9.6.md"},
    @{Src=(Join-Path $ArtifactsDir "Raport_wdrozenia_9.7.md");       Dst="Raport_wdrozenia_9.7.md"},
    @{Src=(Join-Path $ArtifactsDir "Raport_wdrozenia_9.8.md");       Dst="Raport_wdrozenia_9.8.md"},
    @{Src=(Join-Path $ArtifactsDir "Raport_wdrozenia_9.9.md");       Dst="Raport_wdrozenia_9.9.md"},
    @{Src=(Join-Path $ArtifactsDir "Raport_wdrozenia_9.10.md");      Dst="Raport_wdrozenia_9.10.md"},
    @{Src=(Join-Path $ArtifactsDir "Raport_wdrozenia_9.10.1.md");    Dst="Raport_wdrozenia_9.10.1.md"},
    @{Src=(Join-Path $ArtifactsDir "Raport_wdrozenia_Depuracja_1.0.md"); Dst="Raport_wdrozenia_Depuracja_1.0.md"}
)
Copy-ToBatch -BatchName "BATCH_02_Reports" -Items $reports

# --- BATCH_03: Rdzen kodu produkcyjnego (5 najwiekszych) ---
Write-Host "[BATCH_03] Kod produkcyjny - rdzen (5 najwiekszych)" -ForegroundColor Yellow
$core = @(
    @{Src=(Join-Path $RepoRoot "main.py");            Dst="main.py"},
    @{Src=(Join-Path $RepoRoot "translator.py");      Dst="translator.py"},
    @{Src=(Join-Path $RepoRoot "series_memory.py");   Dst="series_memory.py"},
    @{Src=(Join-Path $RepoRoot "verifier.py");        Dst="verifier.py"},
    @{Src=(Join-Path $RepoRoot "avt_linter.py");      Dst="avt_linter.py"}
)
Copy-ToBatch -BatchName "BATCH_03_Production_Core" -Items $core

# --- BATCH_04: Reszta kodu produkcyjnego ---
Write-Host "[BATCH_04] Kod produkcyjny - reszta" -ForegroundColor Yellow
$rest = @(
    @{Src=(Join-Path $RepoRoot "metadata.py");         Dst="metadata.py"},
    @{Src=(Join-Path $RepoRoot "scene_discourse.py");  Dst="scene_discourse.py"},
    @{Src=(Join-Path $RepoRoot "profiler.py");         Dst="profiler.py"},
    @{Src=(Join-Path $RepoRoot "sign_detector.py");    Dst="sign_detector.py"},
    @{Src=(Join-Path $RepoRoot "flight_recorder.py");  Dst="flight_recorder.py"},
    @{Src=(Join-Path $RepoRoot "pipeline_logger.py");  Dst="pipeline_logger.py"},
    @{Src=(Join-Path $RepoRoot "rules.py");            Dst="rules.py"}
)
Copy-ToBatch -BatchName "BATCH_04_Production_Rest" -Items $rest

# --- BATCH_05: Testy ---
Write-Host "[BATCH_05] Testy" -ForegroundColor Yellow
$tests = @(
    @{Src=(Join-Path $RepoRoot "test_system.py");                                     Dst="test_system.py"},
    @{Src=(Join-Path $RepoRoot "tests\test_avt_linter.py");                           Dst="tests__test_avt_linter.py"},
    @{Src=(Join-Path $RepoRoot "tests\test_verifier.py");                             Dst="tests__test_verifier.py"},
    @{Src=(Join-Path $RepoRoot "tests\test_series_memory.py");                        Dst="tests__test_series_memory.py"},
    @{Src=(Join-Path $RepoRoot "tests\test_discourse_and_translator.py");             Dst="tests__test_discourse_and_translator.py"},
    @{Src=(Join-Path $RepoRoot "tests\test_metadata.py");                             Dst="tests__test_metadata.py"},
    @{Src=(Join-Path $RepoRoot "tests\test_profiler.py");                             Dst="tests__test_profiler.py"},
    @{Src=(Join-Path $RepoRoot "tests\test_translator.py");                           Dst="tests__test_translator.py"},
    @{Src=(Join-Path $RepoRoot "tests\test_flight_recorder.py");                      Dst="tests__test_flight_recorder.py"}
)
Copy-ToBatch -BatchName "BATCH_05_Tests" -Items $tests

# --- BATCH_06: Konfiguracja + CI/CD + Bible ---
Write-Host "[BATCH_06] Konfiguracja + CI/CD + Bible" -ForegroundColor Yellow
$config = @(
    @{Src=(Join-Path $RepoRoot "pytest.ini");                                    Dst="pytest.ini"},
    @{Src=(Join-Path $RepoRoot "pyproject.toml");                                Dst="pyproject.toml"},
    @{Src=(Join-Path $RepoRoot "verify_purity.py");                              Dst="verify_purity.py"},
    @{Src=(Join-Path $RepoRoot "verify_ultimate_pipeline.py");                   Dst="verify_ultimate_pipeline.py"},
    @{Src=(Join-Path $RepoRoot "verify_12_fixes.py");                            Dst="verify_12_fixes.py"},
    @{Src=(Join-Path $RepoRoot "audit_diff.ps1");                                Dst="audit_diff.ps1"}
)
# Bible - wildcard lookup w Artefakty
$bibleCandidates = @(
    "Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json",
    "Sasaki_to_Pii_chan_S2_bible.json",
    "Tenmaku_no_Jaadugar_bible.json"
)
foreach ($b in $bibleCandidates) {
    $p = Join-Path $ArtifactsDir $b
    if (Test-Path -LiteralPath $p) {
        $config = $config + @{Src=$p; Dst=$b}
    }
}
Copy-ToBatch -BatchName "BATCH_06_Config_Bible" -Items $config

# --- Manifest ---
$manifest = Join-Path $TargetDir "MANIFEST_KUMULATYWNY.txt"
$lines = @()
$lines += "================================================================"
$lines += "  MANIFEST AUDYTU KUMULATYWNEGO 9.3 -> 9.10.1"
$lines += ("  Data: {0}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
$lines += "  RepoRoot: $RepoRoot"
$lines += "  TargetDir: $TargetDir"
$lines += "================================================================"
$lines += ""

Get-ChildItem -LiteralPath $TargetDir -Directory | Sort-Object Name | ForEach-Object {
    $batchDir = $_.FullName
    $files = @(Get-ChildItem -LiteralPath $batchDir -File)
    $bytes = ($files | Measure-Object -Property Length -Sum).Sum
    if (-not $bytes) { $bytes = 0 }
    $kb = [math]::Round($bytes / 1024, 1)
    $lines += "================================================================"
    $lines += ("  {0} - {1} plikow, {2} KB" -f $_.Name, $files.Count, $kb)
    $lines += "================================================================"
    $idx = 1
    foreach ($f in ($files | Sort-Object Name)) {
        $lines += ("  {0}. {1} ({2} B)" -f $idx, $f.Name, $f.Length)
        $idx++
    }
    $lines += ""
}

$lines += "================================================================"
$lines += "  INSTRUKCJA WYSYLKI"
$lines += "================================================================"
$lines += ""
$lines += "  Wiadomosc #1: prompt audytorski kumulatywny (NIE dolaczaj plikow)"
$lines += "  Wiadomosc #2: BATCH_01_Prompts (10 plikow)"
$lines += "  Wiadomosc #3: BATCH_02_Reports (10 plikow)"
$lines += "  Wiadomosc #4: BATCH_03_Production_Core (5 plikow, ok. 1 MB)"
$lines += "  Wiadomosc #5: BATCH_04_Production_Rest (7 plikow)"
$lines += "  Wiadomosc #6: BATCH_05_Tests (9 plikow)"
$lines += "  Wiadomosc #7: BATCH_06_Config_Bible (8-9 plikow)"
$lines += "  Wiadomosc #8: 'Kontynuuj Etap 1/2'"
$lines += "  Wiadomosc #9: 'Kontynuuj Etap 2/2'"
$lines += ""
$lines += "  MODEL: wymagany context >= 1M tokenow, output >= 20K tokenow."
$lines += ""
$lines | Out-File -LiteralPath $manifest -Encoding UTF8

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  MANIFEST: $manifest" -ForegroundColor Green
Write-Host ""

if ($allMissing.Count -gt 0) {
    Write-Host "BRAKUJACE PLIKI:" -ForegroundColor Red
    foreach ($m in $allMissing) { Write-Host ("  - {0}" -f $m) -ForegroundColor Red }
    Write-Host ""
}

Write-Host "Struktura batchy:" -ForegroundColor Cyan
Get-ChildItem -LiteralPath $TargetDir -Directory | Sort-Object Name | ForEach-Object {
    $files = @(Get-ChildItem -LiteralPath $_.FullName -File)
    $bytes = ($files | Measure-Object -Property Length -Sum).Sum
    if (-not $bytes) { $bytes = 0 }
    $kb = [math]::Round($bytes / 1024, 1)
    Write-Host ("  {0,-30} {1,3} plikow  {2,8} KB" -f $_.Name, $files.Count, $kb) -ForegroundColor Cyan
}
Write-Host ""