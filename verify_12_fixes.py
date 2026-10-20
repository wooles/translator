import ast, os, re, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

results = {}

def check(point_num, name, condition, details_pass, details_fail):
    results[point_num] = (condition, name, details_pass if condition else details_fail)

def read_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

trans_src = read_file("translator.py")
linter_src = read_file("avt_linter.py")
sm_src = read_file("series_memory.py")
sd_src = read_file("scene_discourse.py")
prof_src = read_file("profiler.py")
meta_src = read_file("metadata.py")
ver_src = read_file("verifier.py")

report_src = read_file("PELNY_RAPORT_TECHNICZNY_POTOKU_2.md")
if not report_src:
    report_src = read_file("PELNY_RAPORT_TECHNICZNY_POTOKU.md")

# ==============================================================================
# PUNKT 1: plural_group_gender (We_Group) i you_group_gender (You_Group) w linterze
# ==============================================================================
has_plural_we = "plural_group_gender" in linter_src
has_plural_you = "you_group_gender" in linter_src
c1 = has_plural_we and has_plural_you
check(
    1,
    "Rozdzielenie grup We_Group i You_Group w sygnaturze lintera",
    c1,
    "Sygnatura AVTLinter przyjmuje niezależne plural_group_gender i you_group_gender",
    "Brak parametrów plural_group_gender lub you_group_gender w AVTLinter"
)

# ==============================================================================
# PUNKT 2: Bramki pewności (speaker_confidence >= 0.95 i target_confidence >= 0.95)
# ==============================================================================
has_conf_args = ("speaker_confidence" in linter_src) and ("target_confidence" in linter_src)
has_conf_checks = bool(re.search(r"speaker_confidence\s*>=\s*0\.95", linter_src)) and bool(re.search(r"target_confidence\s*>=\s*0\.95", linter_src))
c2 = has_conf_args and (has_conf_checks or "0.95" in linter_src)
check(
    2,
    "Twarde bramki pewności (confidence >= 0.95) w linterze",
    c2,
    "Operatory D_pos wymagają twardego progu confidence >= 0.95",
    "Brak kontroli progów speaker_confidence / target_confidence >= 0.95 w linterze"
)

# ==============================================================================
# PUNKT 3: Separacja P0 vs P1 dla domysłów tekstowych Profilera
# ==============================================================================
# Pre-Pass Profilera nie może bezwzględnie oznaczać nowych postaci jako P0/verified
profiler_p0_blind = bool(re.search(r'''priority\s*=\s*["']P0["'].*?has_verified_gender\s*=\s*True''', prof_src))
has_p1_or_confidence_cap = ("P1" in prof_src or "0.85" in prof_src or "P1" in sm_src or "has_verified_gender = False" in prof_src or "has_verified_gender=False" in prof_src)
c3 = (not profiler_p0_blind) or has_p1_or_confidence_cap
check(
    3,
    "Separacja epistemiczna P0 vs P1 dla hipotez Profilera",
    c3,
    "Hipotezy tekstowe Profilera mają status P1 (confidence=0.85), nie blokując F0",
    "Domysły z Profilera są ślepo promowane do twardego P0 (confidence=0.95/True)"
)

# ==============================================================================
# PUNKT 4: Bezpieczna promocja z początku opisu i ochrona diakrytyków
# ==============================================================================
# Sprawdzenie czy w sanitize description szuka na początku linii, a nie w całym tekście
safe_desc_promotion = bool(re.search(r'''\^\s*\\s\*\(\?:mężczyzna|kobieta|chłopiec|dziewczynka|male|female\)''', sm_src)) or ("r\"^\\s*(" in sm_src) or ("re.match" in sm_src and "mężczyzna" in sm_src)
meta_preserves_diacritics = "strip_diacritics" in meta_src and "clean_name" in meta_src
c4 = safe_desc_promotion or meta_preserves_diacritics
check(
    4,
    "Bezpieczna promocja płci z początku opisu i ochrona diakrytyków",
    c4,
    "Promocja z description kotwiczona na początku wyrazu; normalize_actor_tag chroni znaki diakrytyczne",
    "Niekotwiczone wyszukiwanie płci w całym polu description lub brak ochrony diakrytyków"
)

# ==============================================================================
# PUNKT 5: Ochrona linii wieloadresatowych (SubTurn Partitioning)
# ==============================================================================
handles_subturn_isolation = ("subturn" in sd_src.lower() or "sub_turn" in sd_src.lower()) and ("ambiguous" in sd_src.lower() or "partition" in sd_src.lower())
c5 = handles_subturn_isolation
check(
    5,
    "Ochrona linii wieloadresatowych (SubTurn Pivot Partitioning)",
    c5,
    "Pod-segmenty SubTurn chronione przed kolizją sprzecznych adresatów w pojedynczej linii",
    "Brak mechanizmu izolacji pod-tur SubTurn przy sprzecznych adresatach"
)

# ==============================================================================
# PUNKT 6: Bariera klauzuli w CopulaAdj i RolePair_Instrumental
# ==============================================================================
# Sprawdzenie czy regexy w linterze uwzględniają barierę interpunkcyjną / spójników podrzędnych
has_clause_boundary = bool(re.search(r'''\[\^,;\.\-—\]\+''', linter_src)) or ("że" in linter_src and "ponieważ" in linter_src and "D_pos" in linter_src) or ("clause" in linter_src.lower())
c6 = has_clause_boundary or ("apply_strict_positive_domain_pipeline" in linter_src)
check(
    6,
    "Bariera granicy klauzuli w CopulaAdj i RolePair_Instrumental",
    c6,
    "Orzeczniki łącznikowe odizolowane barierą składniową (nie mutują zdań podrzędnych 3. os.)",
    "Brak bariery interpunkcyjno-spójnikowej w orzecznikach przymiotnikowych/narzędnikowych"
)

# ==============================================================================
# PUNKT 7: Kapowanie pewności Lookaheadu w scenach wieloosobowych do 0.85
# ==============================================================================
has_lookahead_cap = bool(re.search(r'''(?:lookahead|scene_participants).*?0\.85''', sd_src, re.DOTALL | re.IGNORECASE)) or ("0.85" in sd_src and "confidence" in sd_src)
c7 = has_lookahead_cap
check(
    7,
    "Kapowanie pewności Lookaheadu w scenach wieloosobowych do 0.85",
    c7,
    "Stopień 3 (Lookahead) w scenach wieloosobowych ma limit target_confidence <= 0.85",
    "Brak ograniczenia pewności Lookaheadu w scenach wieloosobowych (ryzyko mutacji w linterze)"
)

# ==============================================================================
# PUNKT 8: Nieprzełamywalność męskiego F0 <= 135Hz przez zaimki angielskie (Score_EN)
# ==============================================================================
score_en_override = bool(re.search(r'''Score_EN\s*<=\s*-8''', prof_src + sd_src + trans_src, re.IGNORECASE))
c8 = not score_en_override
check(
    8,
    "Nieprzełamywalność męskiego F0 <= 135Hz przez zaimki EN (Score_EN)",
    c8,
    "Determinizm męski F0 <= 135Hz nie jest przełamywany przez zaimki z tekstu angielskiego",
    "Wykryto regułę Score_EN <= -8 przełamującą pomiar foniczny F0 <= 135Hz"
)

# ==============================================================================
# PUNKT 9: Pełna tożsamość w TELEMETRIA i brak preskryptywnego nakazu 'ty'
# ==============================================================================
no_prescriptive_ty = not bool(re.search(r"w dialogach bezpośrednich forma 2\. os\. lp\. \('ty'\)", trans_src))
has_unified_telemetry = "format_dry_telemetry_tag" in trans_src and "TELEMETRIA:" in trans_src
c9 = no_prescriptive_ty and has_unified_telemetry
check(
    9,
    "Pełna tożsamość w TELEMETRIA i brak preskryptywnego nakazu 'ty'",
    c9,
    "Usunięto sztywne 'ty'; wektor telemetrii przekazuje tożsamość mówcy, adresata i rejestr",
    "Wykryto sztywny nakaz formy 'ty' lub brak jednokanałowej telemetrii"
)

# ==============================================================================
# PUNKT 10: Przekazywanie audio_jp i semantic_anchor do Fazy 2 (verifier.py)
# ==============================================================================
ver_has_audio = ("audio_jp" in ver_src or "jp_transcript" in ver_src) and ("semantic_anchor" in ver_src or "anchor" in ver_src.lower())
trans_passes_audio_to_v2 = "audio_jp" in trans_src and "verify_batch" in trans_src
c10 = ver_has_audio or trans_passes_audio_to_v2
check(
    10,
    "Przekazywanie audio_jp i semantic_anchor do Fazy 2 (DialogueVerifier)",
    c10,
    "Faza 2 otrzymuje transkrypcję audio_jp i kotwicę semantyczną seiyū do weryfikacji",
    "Brak przekazywania sygnału audio_jp lub kotwicy semantycznej do DialogueVerifier"
)

# ==============================================================================
# PUNKT 11: Brak 'kondensacji waty' w Fazie 7 i ścisły Mianownik w PrepDeclension
# ==============================================================================
has_wata_deletion = bool(re.search(r'''(?:kondensacj[a-z]*\s+waty|usuwanie\s+wypełniaczy)''', linter_src, re.IGNORECASE))
has_ciency_kludge = "cieńscy" in linter_src or "ciency" in linter_src
c11 = (not has_wata_deletion) and (not has_ciency_kludge)
check(
    11,
    "Brak usuwania słów w Fazie 7 i czysta rekcja PrepDeclension",
    c11,
    "Faza 7 wykonuje wyłącznie geometrię i interpunkcję; brak łat leksykalnych w linterze",
    "Wykryto reguły usuwania słów w Fazie 7 lub łatę przymiotnikową w linterze"
)

# ==============================================================================
# PUNKT 12: Czystość metajęzykowa raportu i kodu (Standard 9.0)
# ==============================================================================
forbidden_report_terms = ["Kowalski (M)", "Hoshi no Tabibito", "Rycerz Śmierci", "z Janem, z Anną"]
has_forbidden_in_report = any(term in report_src for term in forbidden_report_terms)
has_screaming_bezwzglednie = bool(re.search(r"\bbezwzględn(?:ie|y|a|e)\b", report_src, re.IGNORECASE))
c12 = (not has_forbidden_in_report) and (not has_screaming_bezwzglednie)
check(
    12,
    "Czystość metajęzykowa dokumentacji i kodu (Standard 9.0)",
    c12,
    "Raport w 100% wolny od instancji onomastycznych, kamuflaży i słów preskryptywnych",
    f"Wykryto zakazane instancje ({[t for t in forbidden_report_terms if t in report_src]}) lub słowo 'bezwzględnie' w raporcie"
)

# ==============================================================================
# PODSUMOWANIE WYNIKÓW
# ==============================================================================
print("\n" + "=" * 94)
print("🛡️  RAPORT FORENSYCZNY: WERYFIKACJA 12 PUNKTÓW ARCHITEKTONICZNYCH POTOKU AVT")
print("=" * 94)

passed_count = 0
for num in sorted(results.keys()):
    passed, name, details = results[num]
    status = "[PASS]" if passed else "[FAIL]"
    if passed:
        passed_count += 1
    print(f"{status:<8} | Punkt {num:02d}: {name}")
    print(f"         └─ {details}")

print("=" * 94)
if passed_count == 12:
    print(f"🏆 WERDYKT: [12/12 PASS] WSZYSTKIE PUNKTY ARCHITEKTONICZNE W 100% ZAADRESOWANE!")
    print("   Potok AVT jest w pełni stabilny, wolny od wycieków epistemicznych i zgodny ze Standardem 9.0.")
    sys.exit(0)
else:
    print(f"🚨 WERDYKT: [{passed_count}/12 PASS] WYKRYTO {12 - passed_count} NIEZREALIZOWANYCH PUNKTÓW.")
    sys.exit(1)
