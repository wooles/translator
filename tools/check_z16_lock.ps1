param(
    [Parameter(Mandatory=$false)][string]$BaseRef = "HEAD",
    [Parameter(Mandatory=$false)][string[]]$AllowZ16Amendment = @(),
    [Parameter(Mandatory=$false)][switch]$AllowSceneDiscourse
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $RepoRoot

function Normalize-RepoPath {
    param([string]$PathValue)
    $clean = $PathValue.Trim().Trim('"').Trim("'")
    $clean = $clean -replace '\\', '/'
    $clean = $clean -replace '^\./', ''
    return $clean
}

try {
    Write-Host ""
    Write-Host "=== DETERMINISTYCZNA BRAMKA Z16 & DEF-02 LOCK (check_z16_lock.ps1) ===" -ForegroundColor Cyan
    Write-Host "[INFO] BaseRef: $BaseRef" -ForegroundColor Gray

    $Z16CoreFiles = @(
        "avt_linter.py",
        "verifier.py",
        "client_factory.py",
        "rules.py",
        "test_system.py",
        "verify_purity.py",
        "pricing_guard.py",
        "main.py",
        "context_cache.py",
        "series_memory/.onomastic_lexicon.json"
    )
    $Z16BibleRegex = '^series_memory/.*_bible\.json$'
    $Def02File = "scene_discourse.py"

    # Normalizacja jawnej listy wyjatkow Z16-amendment (np. "verifier.py:790","avt_linter.py:7570-7579")
    $AllowedZ16Paths = @()
    foreach ($item in $AllowZ16Amendment) {
        if ([string]::IsNullOrWhiteSpace($item)) { continue }
        foreach ($entry in ($item -split '[,;]')) {
            $trimmed = $entry.Trim().Trim('"').Trim("'")
            if ([string]::IsNullOrWhiteSpace($trimmed)) { continue }
            $rawPath = ($trimmed -split ':', 2)[0]
            $normPath = Normalize-RepoPath -PathValue $rawPath
            if ($normPath) {
                $AllowedZ16Paths += $normPath
            }
        }
    }
    $AllowedZ16Paths = @($AllowedZ16Paths | Select-Object -Unique)

    # Zbieranie zmienionych plikow (git diff + git status --porcelain dla HEAD)
    $changedSet = New-Object 'System.Collections.Generic.List[string]'

    $diffFiles = @(git -c core.quotepath=false diff --name-only $BaseRef 2>$null)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[REJECT] Nieprawidlowa referencja git BaseRef: $BaseRef" -ForegroundColor Red
        Write-Host "WERDYKT: [REJECT - NARUSZENIE Z16/DEF-02]" -ForegroundColor Red
        exit 1
    }
    foreach ($df in $diffFiles) {
        if (-not [string]::IsNullOrWhiteSpace($df)) {
            $changedSet.Add((Normalize-RepoPath -PathValue $df))
        }
    }

    if ($BaseRef -eq "HEAD") {
        $porcelain = @(git -c core.quotepath=false status --porcelain 2>$null)
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[REJECT] Nie udalo sie odczytac git status --porcelain" -ForegroundColor Red
            Write-Host "WERDYKT: [REJECT - NARUSZENIE Z16/DEF-02]" -ForegroundColor Red
            exit 1
        }
        foreach ($pline in $porcelain) {
            if ([string]::IsNullOrWhiteSpace($pline) -or $pline.Length -lt 4) { continue }
            $payload = $pline.Substring(3).Trim()
            if ($payload -match '^(.+?)\s+->\s+(.+)$') {
                $changedSet.Add((Normalize-RepoPath -PathValue $Matches[1]))
                $changedSet.Add((Normalize-RepoPath -PathValue $Matches[2]))
            } else {
                $changedSet.Add((Normalize-RepoPath -PathValue $payload))
            }
        }
    }

    $changedFiles = @($changedSet | Where-Object { $_ } | Sort-Object -Unique)
    Write-Host "[INFO] Wykryte zmienione/nowe pliki: $($changedFiles.Count)" -ForegroundColor Gray

    $Z16Violations = @()
    $Def02Violations = @()

    foreach ($file in $changedFiles) {
        $isZ16 = ($file -in $Z16CoreFiles) -or ($file -match $Z16BibleRegex)
        if ($isZ16) {
            if ($file -in $AllowedZ16Paths) {
                Write-Host "[AMENDMENT ALLOWED] $file (wg parametru -AllowZ16Amendment)" -ForegroundColor Yellow
                $statLines = @(git -c core.quotepath=false diff --stat $BaseRef -- $file 2>$null)
                foreach ($sl in $statLines) {
                    Write-Host "  $sl" -ForegroundColor DarkYellow
                }
            } else {
                $Z16Violations += $file
            }
        }

        if ($file -eq $Def02File) {
            if ($AllowSceneDiscourse) {
                Write-Host "[DEF-02 OVERRIDE ALLOWED] $file (wg przelacznika -AllowSceneDiscourse)" -ForegroundColor Yellow
                $statLines = @(git -c core.quotepath=false diff --stat $BaseRef -- $file 2>$null)
                foreach ($sl in $statLines) {
                    Write-Host "  $sl" -ForegroundColor DarkYellow
                }
            } else {
                $Def02Violations += $file
            }
        }
    }

    # Monitorowanie naruszenia sygnatury/ciala _resolve_line_addressee w translator.py
    if ($changedFiles -contains "translator.py") {
        $translatorDiff = @(git -c core.quotepath=false diff -U0 $BaseRef -- "translator.py" 2>$null)
        $touchedResolveAddressee = $translatorDiff | Where-Object {
            $_ -match '@@.*def\s+_resolve_line_addressee\b' -or $_ -match '^[+-]\s*(?:async\s+)?def\s+_resolve_line_addressee\b'
        }

        if (-not $touchedResolveAddressee) {
            # Git bez diff=python w .gitattributes raportuje w @@ naglowek klasy (np. class MultimodalTranslator).
            # Wyznaczamy zakres linii def _resolve_line_addressee w docelowej rewizji translator.py.
            $targetTranslatorLines = $null
            if ($BaseRef -match '\.\.\.?([^\.]+)$') {
                $targetRef = $Matches[1]
                $targetTranslatorLines = @(git -c core.quotepath=false show "${targetRef}:translator.py" 2>$null)
            } elseif (Test-Path "translator.py") {
                $targetTranslatorLines = @(Get-Content -Path "translator.py" -Encoding UTF8)
            }

            if ($targetTranslatorLines) {
                $methodStart = -1
                $methodEnd = $targetTranslatorLines.Count
                $methodIndent = -1
                for ($idx = 0; $idx -lt $targetTranslatorLines.Count; $idx++) {
                    $lineText = $targetTranslatorLines[$idx]
                    $lineNum = $idx + 1
                    if ($methodStart -lt 0) {
                        if ($lineText -match '^(\s*)(?:async\s+)?def\s+_resolve_line_addressee\b') {
                            $methodIndent = $Matches[1].Length
                            $methodStart = $lineNum
                        }
                    } else {
                        if ($lineText -match '^(\s*)(?:(?:async\s+)?def|class)\s+') {
                            if ($Matches[1].Length -le $methodIndent) {
                                $methodEnd = $lineNum - 1
                                break
                            }
                        }
                    }
                }

                if ($methodStart -gt 0) {
                    foreach ($dline in $translatorDiff) {
                        if ($dline -match '^@@\s+-\d+(?:,\d+)?\s+\+(\d+)(?:,(\d+))?\s+@@') {
                            $hStart = [int]$Matches[1]
                            $hCount = if ($Matches[2]) { [int]$Matches[2] } else { 1 }
                            $hEnd = if ($hCount -le 0) { $hStart } else { $hStart + $hCount - 1 }
                            if ($hStart -le $methodEnd -and $hEnd -ge $methodStart) {
                                $touchedResolveAddressee = @($dline)
                                break
                            }
                        }
                    }
                }
            }
        }

        if ($touchedResolveAddressee) {
            Write-Host "[INFO / DEF-02 WATCH] Zmodyfikowano translator.py:_resolve_line_addressee - wymagana pelna regresja DEF-02 (tests/test_standard_11_2_23..27.py)" -ForegroundColor Yellow
        }
    }

    if ($Z16Violations.Count -gt 0 -or $Def02Violations.Count -gt 0) {
        foreach ($zv in $Z16Violations) {
            Write-Host "[REJECT / Z16] Niedozwolona modyfikacja chronionego pliku Z16: $zv" -ForegroundColor Red
        }
        foreach ($dv in $Def02Violations) {
            Write-Host "[REJECT / DEF-02] Niedozwolona modyfikacja zamrozonego modulu DEF-02: $dv" -ForegroundColor Red
        }
        Write-Host "WERDYKT: [REJECT - NARUSZENIE Z16/DEF-02]" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "WERDYKT: [PASS - Z16 (0 B DIFF) & DEF-02 CHRONIONE]" -ForegroundColor Green
        exit 0
    }
} finally {
    Pop-Location
}
