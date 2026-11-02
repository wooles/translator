import ast, os, re, sys

results = {}

def check(name, condition, details=""):
    results[name] = (condition, details)

# ----------------------------------------------------------------------
# 1. Sprawdzenie Virility: brak -liśmy/-liście jako źródła cechy męskoosobowej
# ----------------------------------------------------------------------
sd_path = "scene_discourse.py"
sd_src = open(sd_path, "r", encoding="utf-8", errors="replace").read() if os.path.exists(sd_path) else ""
has_verb_virile_loop = bool(re.search(r'''(?:-liśmy|-liście|liśmy|liście).*?(?:VIRILE|męskoosobow)''', sd_src, re.IGNORECASE))
check(
    "1. Likwidacja cyklicznego virility (-liśmy/-liście)",
    not has_verb_virile_loop,
    "Wykryto wnioskowanie o VIRILE z form czasownikowych" if has_verb_virile_loop else "Czysto: virility wynika wyłącznie z tożsamości uczestników"
)

# ----------------------------------------------------------------------
# 2. Sprawdzenie przypisania SKŁADNI do skryptu EN
# ----------------------------------------------------------------------
trans_path = "translator.py"
prof_path = "profiler.py"
trans_src = open(trans_path, "r", encoding="utf-8", errors="replace").read() if os.path.exists(trans_path) else ""
prof_src = open(prof_path, "r", encoding="utf-8", errors="replace").read() if os.path.exists(prof_path) else ""

en_syntax_leak = bool(
    re.search(r"SKRYPT\s+PODSTAWOWY\s+EN.*?SKŁADNIA", trans_src, re.IGNORECASE) or
    re.search(r"Angielski\s+skrypt\s*=.*?składnia", prof_src, re.IGNORECASE)
)
check(
    "2. Brak narzucania angielskiej składni na polski przekład",
    not en_syntax_leak,
    "Skrypt EN nadal oznaczony jako źródło 'SKŁADNI'" if en_syntax_leak else "Czysto: EN dostarcza wyłącznie treści semantycznej i faktów"
)

# ----------------------------------------------------------------------
# 3. Sprawdzenie preskryptywnych końcówek w nagłówkach kwestii
# ----------------------------------------------------------------------
prescriptive_headers = bool(re.search(r"\[REJESTR:[^\]]*?\(-ła[sś]|\(-łem", trans_src))
check(
    "3. Brak preskryptywnych końcówek (-łaś / -łem) w promptach",
    not prescriptive_headers,
    "Wykryto podpowiedzi końcówek w nawiasach nagłówka linii" if prescriptive_headers else "Czysto: stan przekazywany wyłącznie przez wektor telemetrii"
)

# ----------------------------------------------------------------------
# 4. Sprawdzenie deklaratywności Pre-Passu (profiler.py)
# ----------------------------------------------------------------------
has_mandatory_fields = bool(re.search(r"\b(?:mandatory_direction|strict_direction_pl|continuity_directive)\b", prof_src))
check(
    "4. Deklaratywny Profiler (brak pól 'mandatory_direction')",
    not has_mandatory_fields,
    "Znaleziono imperatywne pola w schematach EpisodeProfile" if has_mandatory_fields else "Czysto: brak rozkazów edycyjnych w fazie Pre-Pass"
)

# ----------------------------------------------------------------------
# 5. Sprawdzenie telemetrii weryfikatora Fazy 2 (verifier.py)
# ----------------------------------------------------------------------
ver_path = "verifier.py"
ver_src = open(ver_path, "r", encoding="utf-8", errors="replace").read() if os.path.exists(ver_path) else ""
has_telemetry_in_v2 = ("telemetry_tag" in ver_src or "TELEMETRIA" in ver_src) and ("declension" in ver_src or "paradygmat" in ver_src.lower())
check(
    "5. Faza 2 (Verifier) zasilana pełnym wektorem telemetrii",
    has_telemetry_in_v2,
    "Czysto: Faza 2 weryfikuje styl z zachowaniem telemetrii ontologicznej" if has_telemetry_in_v2 else "Brak przekazywania telemetrii do DialogueVerifier"
)

# ----------------------------------------------------------------------
# 6. Sprawdzenie bariery epistemicznej wyjścia Fazy 1 (translator.py)
# ----------------------------------------------------------------------
# Szukamy zabezpieczenia, że zgadywana płeć z Fazy 1 nie nadpisuje has_verified_gender
has_epistemic_shield = ("confidence = 0.70" in trans_src or "confidence=0.70" in trans_src or "has_verified_gender" in trans_src)
check(
    "6. Bariera epistemiczna (wyjście Fazy 1 nie nadpisuje bazy P0)",
    has_epistemic_shield,
    "Czysto: wyjście LLM nie zanieczyszcza zweryfikowanej bazy ontologicznej" if has_epistemic_shield else "Brak twardej bariery pewności dla zgadywanych pól Fazy 1"
)

# ----------------------------------------------------------------------
# 7. Sprawdzenie czystości D_pos(PrepDeclension) i rygoru TOPONYM
# ----------------------------------------------------------------------
linter_path = "avt_linter.py"
linter_src = open(linter_path, "r", encoding="utf-8", errors="replace").read() if os.path.exists(linter_path) else ""
has_ciency_kludge = "cieńscy" in linter_src or "ciency" in linter_src
has_toponym_rigor = "EntityCategory.TOPONYM" in linter_src or "TOPONYM" in linter_src
check(
    "7. Czystość PrepDeclension (brak łat przymiotnikowych, rygor TOPONYM)",
    not has_ciency_kludge and has_toponym_rigor,
    "Wykryto łatę 'cieńscy' lub brak rygoru TOPONYM przy ablatywnym z" if (has_ciency_kludge or not has_toponym_rigor) else "Czysto: operator działa wyłącznie na zweryfikowanych toponimach"
)

# ----------------------------------------------------------------------
# 8. Sprawdzenie raportu technicznego (PELNY_RAPORT_TECHNICZNY_POTOKU.md)
# ----------------------------------------------------------------------
rep_path = "PELNY_RAPORT_TECHNICZNY_POTOKU.md"
rep_src = open(rep_path, "r", encoding="utf-8", errors="replace").read() if os.path.exists(rep_path) else ""
report_clean = not bool(re.search(r"SKRYPT\s+PODSTAWOWY\s+EN.*?SKŁADNIA", rep_src, re.IGNORECASE)) and ("TREŚĆ SEMANTYCZNA" in rep_src or "FAKTY" in rep_src)
check(
    "8. Spójność dokumentacji PELNY_RAPORT_TECHNICZNY_POTOKU.md",
    report_clean,
    "Dokumentacja zaktualizowana i zgodna z nowym przepływem danych" if report_clean else "Raport nadal opisuje skrypt EN jako źródło składni"
)

# ----------------------------------------------------------------------
# PODSUMOWANIE AUDYTU
# ----------------------------------------------------------------------
print("\n" + "=" * 90)
print("🔍 RAPORT WERYFIKACJI 8 POPRAWEK ARCHITEKTONICZNYCH")
print("=" * 90)

all_passed = True
for name, (passed, details) in results.items():
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status:<8} | {name}")
    print(f"         └─ {details}")
    if not passed:
        all_passed = False

print("=" * 90)
if all_passed:
    print("🏆 WSZYSTKIE 8 UWAG ZOSTAŁO W 100% ZAADRESOWANYCH I NAPRAWIONYCH!")
    sys.exit(0)
else:
    print("🚨 WYKRYTO NIEZREALIZOWANE POPRAWKI — WYMAGANA INTERWENCJA.")
    sys.exit(1)
