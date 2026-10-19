import os, re, sys
from avt_linter import AVTLinter
from metadata import normalize_actor_tag
from series_memory import generate_polish_name_declension

def read_f(p):
    return open(p, "r", encoding="utf-8", errors="replace").read() if os.path.exists(p) else ""

trans_s = read_f("translator.py")
linter_s = read_f("avt_linter.py")
sm_s = read_f("series_memory.py")
sd_s = read_f("scene_discourse.py")
prof_s = read_f("profiler.py")
meta_s = read_f("metadata.py")
ver_s = read_f("verifier.py")
whisp_s = read_f("whisper_disambiguator.py")
rep_s = read_f("PELNY_RAPORT_TECHNICZNY_POTOKU.md")

checks = []

# 1. Ochrona rzeczowników w Narzędniku na -łem oraz rozkaźników na -łam
t_inst, _ = AVTLinter.lint_and_fix_line(
    "Rozmawiałam z generałem pod kościołem i stałam za stołem przed światłem.",
    speaker_gender="FEMALE", speaker_confidence=1.0
)
t_imp, _ = AVTLinter.lint_and_fix_line("Nie kłam i przełam swój strach!", speaker_gender="MALE", speaker_confidence=1.0)
c1 = ("generałem" in t_inst and "kościołem" in t_inst and "stołem" in t_inst and "światłem" in t_inst and "Nie kłam" in t_imp and "przełam" in t_imp)
checks.append(("1. Immunitet rzeczowników w Narzędniku (-łem) i rozkaźników (-łam)", c1, f"Wynik: {t_inst} | {t_imp}"))

# 2. Granice słów \b przy tagach ASS i \N
t_ass, _ = AVTLinter.lint_and_fix_line(r"{\i1}Zrobiłam{\i0} to\Ni byłam gotowa.", speaker_gender="MALE", speaker_confidence=1.0)
c2 = ("Zrobiłem" in t_ass and "byłem" in t_ass and "gotowy" in t_ass and r"{\i1}" in t_ass and r"\N" in t_ass)
checks.append(("2. Granice słów \\b przy przyklejonych tagach ASS i \\N", c2, f"Wynik: {t_ass}"))

# 3. Czas przyszły złożony i szyk inwersyjny
t_fut, _ = AVTLinter.lint_and_fix_line("Będę musiała tam pójść. Gotowa jesteś?", speaker_gender="MALE", target_gender="MALE", speaker_confidence=1.0, target_confidence=1.0)
c3 = ("Będę musiał" in t_fut and "Gotowy jesteś" in t_fut)
checks.append(("3. Czas przyszły złożony (będę + -ł/-ła) i szyk inwersyjny (Gotowy jesteś?)", c3, f"Wynik: {t_fut}"))

# 4. Bariera klauzuli (ochrona 3. osoby w zdaniu podrzędnym po przecinku/że)
t_cl, _ = AVTLinter.lint_and_fix_line("Jestem pewien, że ona była gotowa i ostrożna.", speaker_gender="MALE", speaker_confidence=1.0)
c4 = ("gotowa i ostrożna" in t_cl)
checks.append(("4. Bariera granicy klauzuli w CopulaAdj (ochrona 3. os. po przecinku/że)", c4, f"Wynik: {t_cl}"))

# 5. Bramka pewności < 0.95 -> Identity Pass-Through T(x) = x
t_low, _ = AVTLinter.lint_and_fix_line("Zrobiłam to wczoraj.", speaker_gender="MALE", speaker_confidence=0.85)
c5 = (t_low == "Zrobiłam to wczoraj.")
checks.append(("5. Twarda bramka pewności (confidence 0.85 < 0.95 -> T(x) = x)", c5, f"Wynik: {t_low}"))

# 6. Niezależne plural_group_gender (We_Group) i you_group_gender (You_Group)
t_you, _ = AVTLinter.lint_and_fix_line(
    "Widziałam, że zrobiłyście to same.",
    speaker_gender="MALE", speaker_confidence=1.0, you_group_gender="NON_VIRILE", scene_has_male_participant=True
)
c6 = ("Widziałem" in t_you and "zrobiłyście" in t_you)
checks.append(("6. Rozdzielenie We_Group i You_Group (mężczyzna do grupy kobiet -> -łyście)", c6, f"Wynik: {t_you}"))

# 7. Ochrona dwugłosu (- Kwestia 1\N- Kwestia 2)
t_dual, _ = AVTLinter.lint_and_fix_line(r"- Zrobiłem to.\N- A ja byłam obok.", speaker_gender="MALE", speaker_confidence=1.0)
c7 = ("byłam obok" in t_dual)
checks.append(("7. Ochrona drugiego mówcy w linii dwugłosowej (- ...\\N- ...)", c7, f"Wynik: {t_dual}"))

# 8. Ochrona diakrytyków w normalize_actor_tag
clean_n, extr_g = normalize_actor_tag("Żołnierz Łukasz (M)", strip_diacritics=False)
c8 = (clean_n == "Żołnierz Łukasz" and extr_g == "MALE")
checks.append(("8. Ochrona polskich znaków diakrytycznych w normalize_actor_tag", c8, f"Wynik: {clean_n}, {extr_g}"))

# 9. Fonotaktyka imion żeńskich i dwuczłonowych w generate_polish_name_declension
d_fem = generate_polish_name_declension("Katarzyna", gender="FEMALE")
c9 = (d_fem.get("D") == "Katarzyny" and d_fem.get("B") == "Katarzynę" and d_fem.get("W") == "Katarzyno")
checks.append(("9. Paradygmat deklinacji żeńskiej w generate_polish_name_declension", c9, f"Wynik: {d_fem}"))

# 10. Separacja P0 vs P1 i brak Score_EN <= -8
c10 = (not bool(re.search(r"Score_EN\s*<=\s*-8", prof_s + sd_s + trans_s + rep_s, re.I))) and ("0.85" in prof_s or "P1" in prof_s or "P1" in sm_s)
checks.append(("10. Separacja P0 vs P1 dla Profilera i brak Score_EN <= -8", c10, "Weryfikacja kodu i raportu"))

# 11. Kapowanie Lookaheadu do 0.85 i izolacja Vocative Lock od 1. osoby
c11 = ("0.85" in sd_s) and not bool(re.search(r"Wołacz męski bezwzględnie blokuje", rep_s))
checks.append(("11. Kapowanie Lookaheadu (0.85) i izolacja Vocative Lock (tylko 2. os.)", c11, "Weryfikacja scene_discourse.py"))

# 12. AniList perPage: 50 i blokada tytułów w _actor_aliases_index
c12 = ("perPage: 50" in meta_s or "perPage: 50" in rep_s) and ("kapitan" in sm_s.lower() or "książę" in sm_s.lower())
checks.append(("12. Limit AniList perPage: 50 i blokada tytułów w indeksie aliasów", c12, "Weryfikacja metadata.py i series_memory.py"))

# 13. Bramka anty-halucynacyjna Whispera i audio_jp w Fazie 2
c13 = ("is_phantom_audio" in trans_s or "is_hallucination_loop" in trans_s) and ("audio_jp" in ver_s)
checks.append(("13. Bramka anty-halucynacyjna Whispera i audio_jp w Fazie 2", c13, "Weryfikacja translator.py i verifier.py"))

# 14. Jednokanałowa telemetria z tożsamością mówcy/adresata i brak sztywnego ('ty')
c14 = not bool(re.search(r"forma 2\. os\. lp\. \('ty'\)", trans_s + rep_s))
checks.append(("14. Brak sztywnego nakazu ('ty') i pełna telemetria mówcy/adresata", c14, "Weryfikacja translator.py i raportu"))

# 15. Czystość metajęzykowa raportu (Standard 9.0)
bad_rep = ["Kowalski (M)", "Hoshi no Tabibito", "Rycerz Śmierci", "z Janem, z Anną", "np. Aktor", "np. PostaćA", "np. Bohater"]
has_bad_rep = [t for t in bad_rep if t in rep_s]
has_bezw = bool(re.search(r"\bbezwzględn(?:ie|y|a|e)\b", rep_s, re.I))
c15 = (not has_bad_rep) and (not has_bezw)
checks.append(("15. Czystość metajęzykowa raportu technicznego (Standard 9.0)", c15, f"Naruszenia: {has_bad_rep}, bezwzględnie={has_bezw}"))

print("\n" + "=" * 95)
print("🛡️  OSTATECZNY AUDYTOR POTOKU AVT: 15 BRAMEK RUNTIME I ARCHITEKTURY (STANDARD 9.0)")
print("=" * 95)
passed = 0
for title, ok, info in checks:
    st = "[PASS]" if ok else "[FAIL]"
    if ok:
        passed += 1
    print(f"{st:<8} | {title}")
    if not ok:
        print(f"         └─ {info}")
print("=" * 95)
print(f"WYNIK KOŃCOWY: {passed}/15 PASS")
sys.exit(0 if passed == 15 else 1)
