param(
    [Parameter(Mandatory=$false)][string]$ForbiddenTerms = "",
    [Parameter(Mandatory=$false)][string]$NotesFile = "",
    [Parameter(Mandatory=$false)][string]$BaseRef = "HEAD"
)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$ErrorActionPreference = "Continue"
Push-Location $PSScriptRoot
$AuditFailed = $false

try {
    Write-Host ""
    Write-Host "=== FORENSIC DIFF & AST AUDITOR (STANDARD 4.0) ===" -ForegroundColor Cyan

    $porcelain = git status --porcelain 2>$null
    $codeChangesInWorktree = $porcelain | Where-Object { $_ -match '\.py$' }
    if (-not $codeChangesInWorktree -and $BaseRef -eq "HEAD") {
        Write-Host "[INFO] Brak niezapisanych zmian w .py -> sprawdzam ostatni commit (HEAD~1)" -ForegroundColor Gray
        $BaseRef = "HEAD~1"
    }

    $CleanTerms = @()
    if ($ForbiddenTerms -ne "") {
        foreach ($sub in ($ForbiddenTerms -split '[,|;]')) {
            $trimmed = $sub.Trim().Trim('"').Trim("'")
            if ($trimmed.Length -ge 3 -and $trimmed -notmatch '^<.*>$') {
                $CleanTerms += $trimmed
            }
        }
    }
    $CleanTerms = $CleanTerms | Select-Object -Unique

    # 1. ZERO-COSMETIC GATE
    $changedFiles = @()
    if ($porcelain -and $BaseRef -eq "HEAD") {
        $changedFiles += ($porcelain | ForEach-Object { $_.Substring(3).Trim() })
    }
    $diffFiles = git diff --name-only $BaseRef 2>$null
    if ($diffFiles) { $changedFiles += $diffFiles }
    $changedFiles = $changedFiles | Select-Object -Unique

    $changedFiles = $changedFiles | Where-Object {
        $_ -notmatch '\.no_canon_cache\.json$' -and $_ -notmatch 'testbible\.json$' -and $_ -notmatch 'audit_diff\.ps1$'
    }

    $coreEnginePy = $changedFiles | Where-Object {
        $_ -match '\.py$' -and $_ -notmatch 'test_system\.py$' -and $_ -notmatch 'avt_linter\.py$'
    }
    $assOrSrtEdits = $changedFiles | Where-Object { $_ -match '\.(ass|srt)$' }

    if ($assOrSrtEdits) {
        Write-Host "[REJECT] Nielegalna reczna modyfikacja napisow wyjsciowych: $($assOrSrtEdits -join ', ')" -ForegroundColor Red
        $AuditFailed = $true
    } elseif (-not $coreEnginePy) {
        Write-Host "[REJECT] Brak zmian w kodzie silnika .py (Warstwy 1-3)! Wykryto jedynie: $($changedFiles -join ', ')" -ForegroundColor Red
        $AuditFailed = $true
    } else {
        Write-Host "[PASS] 1/4 Zero-Cosmetic Gate (zmodyfikowano rdzen silnika: $($coreEnginePy -join ', '))" -ForegroundColor Green
    }

    # 2. ZERO-ONOMASTIC & STEM LEAKAGE GATE
    $prodDiffLines = git diff $BaseRef -- "*.py" ":!test_system.py" ":!*test*.py" 2>$null | Where-Object { $_ -match '^\+[^+]' }
    if ($CleanTerms.Count -gt 0) {
        $SearchPatterns = @()
        foreach ($term in $CleanTerms) {
            $SearchPatterns += [regex]::Escape($term)
            if ($term.Length -ge 6) { $SearchPatterns += [regex]::Escape($term.Substring(0, $term.Length - 2)) }
            elseif ($term.Length -eq 5) { $SearchPatterns += [regex]::Escape($term.Substring(0, 4)) }
        }
        $combinedRegex = "(" + (($SearchPatterns | Select-Object -Unique) -join "|") + ")"
        $leakedLines = @()
        foreach ($line in $prodDiffLines) {
            if ($line -match $combinedRegex) { $leakedLines += "Matched '$($Matches[0])' in: $($line.Trim())" }
        }
        if ($leakedLines.Count -gt 0) {
            Write-Host "[REJECT] Wyciek nazw wlasnych/rdzeni ze zgloszenia do kodu produkcyjnego:" -ForegroundColor Red
            $leakedLines | ForEach-Object { Write-Host "  -> $_" -ForegroundColor Red }
            $AuditFailed = $true
        } else {
            Write-Host "[PASS] 2/4 Zero-Onomastic & Stem Leakage Gate ($($CleanTerms.Count) sprawdzonych nazw)" -ForegroundColor Green
        }
    } else {
        Write-Host "[PASS] 2/4 Zero-Onomastic Gate (brak nazw wlasnych na liscie)" -ForegroundColor Green
    }

    # 3. END-TO-END WIRING (DEAD CODE GATE Z OCHRONA DEKORATOROW PYDANTIC V2)
    $fullProdDiff = git diff $BaseRef -- "*.py" ":!test_system.py" ":!*test*.py" 2>$null
    $newSymbols = @()
    $recentLines = @("", "", "", "")
    foreach ($line in $fullProdDiff) {
        if ($line -match '^\+\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(') {
            $fn = $Matches[1]
            $decoratorContext = ($recentLines -join " ")
            if ($fn -notmatch '^__' -and ($decoratorContext -notmatch 'validator|property')) {
                $newSymbols += $fn
            }
        } elseif ($line -match '^\+\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]') {
            $newSymbols += $Matches[1]
        }
        if ($line -match '^\+') {
            $recentLines = @($recentLines[1], $recentLines[2], $recentLines[3], $line)
        }
    }
    $prodPyFiles = Get-ChildItem -Path . -Filter "*.py" -Recurse | Where-Object { $_.FullName -notmatch '\\\.venv\\' -and $_.Name -notmatch '^test_' }
    $deadCode = @()
    foreach ($sym in ($newSymbols | Select-Object -Unique)) {
        $occ = 0
        foreach ($py in $prodPyFiles) {
            $occ += ([regex]::Matches((Get-Content $py.FullName -Raw -Encoding UTF8), "\b$([regex]::Escape($sym))\b")).Count
        }
        if ($occ -le 1) { $deadCode += $sym }
    }
    if ($deadCode.Count -gt 0) {
        Write-Host "[REJECT] Wykryto MARTWY KOD (brak wywolania w potoku produkcyjnym): $($deadCode -join ', ')" -ForegroundColor Red
        $AuditFailed = $true
    } else {
        Write-Host "[PASS] 3/4 End-to-End Wiring Gate" -ForegroundColor Green
    }

    # 4. TEST INTEGRITY GATE
    $testDiffLines = git diff $BaseRef -- "test_system.py" 2>$null | Where-Object { $_ -match '^\+[^+]' }
    if (-not $testDiffLines) {
        Write-Host "[REJECT] Brak nowych testow w test_system.py!" -ForegroundColor Red
        $AuditFailed = $true
    } else {
        $illegalMocks = $testDiffLines | Where-Object { $_ -match 'patch\s*\(\s*[''"](?:pipeline\.|translator|series_memory|scene_discourse|profiler|character_profiler)' }
        if ($illegalMocks) {
            Write-Host "[REJECT] Nielegalne mockowanie logiki domenowej w test_system.py!" -ForegroundColor Red
            $AuditFailed = $true
        } else {
            Write-Host "[PASS] 4/4 Test Integrity Gate" -ForegroundColor Green
        }
    }

    if ($AuditFailed) {
        Write-Host "WERDYKT: [REJECT]" -ForegroundColor Red
        exit 1
    } else {
        Write-Host "WERDYKT: [VICTORY CONFIRMED -- KOD CZYSTY I UOGOLNIONY]" -ForegroundColor Green
        exit 0
    }
} finally {
    Pop-Location
}
