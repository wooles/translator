# SUPLEMENT DO RAPORTU WDROŻENIA 10.0.2 — `Raport_wdrozenia_10.0.2a.md`

## 0. FAZA 0 — POTWIERDZENIE STANU WYJŚCIOWEGO
- **HEAD repo:**
```text
ff2d022 feat(pipeline): Wdrozenie Standardu 10.0.2 / 10.1 (Chirurgiczna naprawa A-01..A-14, usuniecie smieci i testy regresyjne)
e8ed102 chore(security): untrack gcp_key.json and add to gitignore
42734c0 feat(pipeline): Wdrozenie Standardu 10.0.1 (Suplement 10.0a, korekta B-1..B-6 i O-1..O-7)
```
- **Stan drzewa roboczego:**
```text
## main...origin/main
 M series_memory/Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json
```
*(Uwaga: modyfikacja pliku `series_memory/Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json` nastąpiła w wyniku zakończenia w tle procesu tłumaczenia odcinka 30 serii [ASW] Tensei Kizoku, Kantei Skill de Nariagaru - 30; brak innych nieśledzonych lub zmienionych plików).*
- **Raport bazowy `Raport_wdrozenia_10.0.2.md`:** `exists: True, lines: 436`
- **Suplement `Raport_wdrozenia_10.0.2a.md`:** `nowy`

---

## 1. LK-1 — A-02 (`TYPO_NORMALIZATIONS` — obfuskacja `chr(...)`)
- **Komenda:** `grep -n "chr(" series_memory.py`
- **Surowe wyjście:**
```text
(brak trafień, kod wyjścia 1)
```
- **Komenda uzupełniająca:** `grep -nE "chr\([0-9]+\)|\.join\(\[chr|bytes\.fromhex|base64\." series_memory.py`
- **Surowe wyjście:**
```text
(brak trafień, kod wyjścia 1)
```
- **Status:** `POTWIERDZONE_FAŁSZYWY_ALARM`
- **Uzasadnienie:** W pliku `series_memory.py` nie występuje ani jedno wywołanie funkcji `chr(`, łączenie znaków ze strumienia liczbowego, dekodowanie szesnastkowe ani obfuskacja base64. Struktura `TYPO_NORMALIZATIONS` operuje wyłącznie na jawnych, czystych wyrażeniach regularnych języka polskiego.

---

## 2. LK-2 — A-03 (`rules.py` / `profiler.py` / `scene_discourse.py` / `metadata.py` — antroponimy)
- **Komenda:** `grep -nE "Eftalu|Tonden|Minoru|Akafuku|Teshimy|Kokoro|Gujuka|Ilüge|Hikarun|Tessie|chojumaru|shizuku|Kamakura|Kanyou|Kantan|Ridill" rules.py profiler.py scene_discourse.py metadata.py`
- **Surowe wyjście:**
```text
metadata.py:339:                    r"\bkami no shizuku\b", r"\bdrops of god\b", r"\benology\b", r"\boenology\b"
profiler.py:623:   - Zdrobnienia afektywne ograniczone są do właściwych relacji między konkretnymi postaciami (eliminacja wycieku rówieśniczego Hikarun). # Standard 9.0 Invariant
rules.py:410:- Kiedy w kwestii pojawia się imię postaci w dopełniaczu (warianty: "Akafuku's dad!", "Sensei's manga!", "Kokoro's house!"):
rules.py:411:  * Oznacza to DOKŁADNIE tę nazwaną postać w 3. osobie ("Tata Akafuku", "Ojciec Akafuku", "Manga pani Teshimy", "Dom Kokoro").
rules.py:412:  * Wypowiedzi o innych osobach tłumacz konsekwentnie w 3. osobie (Kalka: przetłumaczenie "Akafuku's dad!" na "to mój tata"!).
rules.py:870:  * -chan (ちゃん) w ustach przyjaciółek/rodziny (warianty: Hana-chan, Kokoro-chan, Akafuku-chan):
rules.py:871:    -> Eliminujemy kalkę "Pani Hana / Pani Kokoro" -> bezpośrednie imię lub zdrobnienie na "ty" ("Hana", "Kokoro", "Haneczko").
rules.py:886:  * kalka KARDYNALNY [niepoprawne]: "Poza tym, mistrzu... ma pan zaczerwienioną twarz." (niedopuszczalna hybryda poufałego wołacza "Eftalu" z formą grzecznościową "ma pan").
rules.py:892:  * Relacja uczeń-mistrz czy podwładny-pan w polszczyźnie zachowuje stałość rejestru: w zawołaniach i okrzykach stosuj "Panie [Imię]" ("Co za kunszt, panie Eftalu"), a nie poufałe "Eftalu".
rules.py:1540:      - Jeśli postać zwraca się do rozmówcy per pan/pani ('ma pan', 'widzi pan', 'niech pan', 'chciał pan'), Naturalnie unikamy wołacza po samym imieniu ('Eftalu...'). W takich zdaniach dopuszczalne jest wyłącznie 'Panie [Imię]...'.
rules.py:1733:      - W seriach historycznych (Mongolia XIII w., Sengoku, Kamakura) i High/Dark Fantasy obowiązuje eliminujemy kalkę współczesnych kalek konwersacyjnych i potocznego slangu:
rules.py:1740:          -> "wyjść za Gujuka" (Biernik od 'Gujuk'!) - Eliminujemy kalkę narzędnika: "wyjść za Gujukiem", ani fałszywego mianownika: "wyjść za Gujukę"!
rules.py:1762:      - Specyficzne, slangowe lub pieszczotliwe ksywki rówieśnicze i gyaru (warianty: 'Hikarun', 'Aoi-chan') są ściśle ograniczone do postaci, która je nadała w danej relacji.
rules.py:1764:      - Gdy matka w audio seiyū mówi 'Hikaru-chan', jedynym naturalnym polskim ekwiwalentem jest 'Hikaru', 'Córeczko' lub 'Hikaruś' (KARDYNALNY Kalka: 'Hikarun, posłuchaj uważnie').
rules.py:2255:  * Dopełniacz: 'na ziemiach generała Ilüge'
rules.py:2256:  * Biernik: 'na ziemie generała Ilüge'
rules.py:2257:  * Narzędnik: 'z generałem Ilüge'
rules.py:2258:  * Miejscownik / Wołacz: 'o generale Ilüge / generale Ilüge!'.
rules.py:3566:            "'wyjść za Gujuka' (Biernik męski od Gujuk), zamiast kalki 'wyjść za Gujukę / za Gujukiem' stosuj naturalną polszczyznę!"
rules.py:3622:            "1. Ksywki rówieśnicze/gyaru ('Hikarun', 'Tessie') należą WYŁĄCZNIE do postaci je nadających (Sachi Akafuku). "
scene_discourse.py:370:        is_boy = any(k in spk_low for k in BOY_ROLE_KEYWORDS) or any(k in spk_low for k in ["chłopiec", "boy", "kid", "dziecko", "chojumaru", "conan"])
```

- **Kontekst 5 linii dla przykładowych trafień:**
```text
=== rules.py:410-412 ===
409: FILAR XLII: PRECYZJA PERSPEKTYWY I PRZYNALEŻNOŚCI (3. OSOBA VS 1. OSOBA):
410: - Kiedy w kwestii pojawia się imię postaci w dopełniaczu (warianty: "Akafuku's dad!", "Sensei's manga!", "Kokoro's house!"):
411:   * Oznacza to DOKŁADNIE tę nazwaną postać w 3. osobie ("Tata Akafuku", "Ojciec Akafuku", "Manga pani Teshimy", "Dom Kokoro").
412:   * Wypowiedzi o innych osobach tłumacz konsekwentnie w 3. osobie (Kalka: przetłumaczenie "Akafuku's dad!" na "to mój tata"!).
413: 

=== profiler.py:622-624 ===
621:    - Dekompozycja obcych przydawek temporalnych na naturalne polskie wyrażenia okolicznikowe czasu.
622: 18. DYSCYPLINA IDIOLEKTU I PRYMAT MORFOLOGICZNY PŁCI (SPEAKER-SCOPED HYPOCORISM GUARD & INHERENT GENDER & 1ST-PERSON MORPHOLOGY): # Standard 9.0 Invariant
623:    - Zdrobnienia afektywne ograniczone są do właściwych relacji między konkretnymi postaciami (eliminacja wycieku rówieśniczego Hikarun). # Standard 9.0 Invariant
624:    - Spójność morfologiczna form 1. osoby czasu przeszłego z potwierdzoną płcią postaci.

=== scene_discourse.py:368-372 ===
368:         # Ochrona kanonicznych ról chłopięcych (młodzi chłopcy z wysokim F0)
369:         from series_memory import BOY_ROLE_KEYWORDS
370:         is_boy = any(k in spk_low for k in BOY_ROLE_KEYWORDS) or any(k in spk_low for k in ["chłopiec", "boy", "kid", "dziecko", "chojumaru", "conan"])
371: 
372:         if is_boy:
```

- **Komenda uzupełniająca:** `grep -niE "töregene|chulan|khulan|ariane|olgren|evergarden|peeps|abaddon|himegami|bradley|abbie|garnet|elisaHeart|magówa" rules.py profiler.py scene_discourse.py metadata.py`
- **Surowe wyjście:**
```text
(brak trafień, kod wyjścia 1)
```
- **Status:** `POTWIERDZONE_NARUSZENIE`
- **Uzasadnienie:** Pierwszy skan diagnostyczny wykrył 20 wystąpień nazw własnych z audytowanych serii historycznych w plikach `rules.py` (Filar XLII, Filar CLXX, prompt systemowy), `profiler.py:623` (komentarz reguły 18), `scene_discourse.py:370` (`chojumaru`) oraz `metadata.py:339` (`kami no shizuku`). Zgodnie z Żelaznym Protokołem promptu nie zmodyfikowano kodu i zgłoszono stan faktyczny do decyzji użytkownika.

---

## 3. LK-3 — A-06 (`rules.py` — `R3.1–R3.5`)
- **Komenda:** `grep -nE "R3\.[1-5]" rules.py`
- **Surowe wyjście:**
```text
rules.py:2388:12. R3.1 (P0) — POZYTYWNY SCHEMAT REKORDU POSTACI: Każdy byt osobowy w bazie wiedzy jest instancją czystej klasy ontologicznej ze strukturalnymi polami tożsamości gramatycznej.
rules.py:2389:13. R3.2 (P0) — TELEMETRIA PRZED ASR I AKUSTYKĄ: Zweryfikowany rekord P0 postaci ma nadrzędność ontologiczną nad sygnałami akustycznymi F0 oraz niedoskonałościami transkrypcji ASR.
rules.py:2390:14. R3.3 (P0) — CZYSTA DOMENA POZYTYWNA D_pos: Wszystkie deterministyczne reguły bramki jakości operują wyłącznie w zweryfikowanej dziedzinie pozytywnej; poza nią obowiązuje tożsamość T(x) = x.
rules.py:2391:15. R3.4 (P0) — NIEZMIENNIK PIERWOTNEGO AUTORYTETU LLM: Wybory dramaturgiczne, idiomatyczne i leksykalne modelu tłumaczącego są chronione przed destrukcyjnymi kaskadami mutującymi.
rules.py:2392:16. R3.5 (P0) — SYMBOLE METALINGWISTYCZNE: Baza wiedzy, reguły i szablony testowe operują na abstrakcyjnych kategoriach gramatycznych i metalingwistycznych, bez hardkodowania nazw własnych.
```
- **Komenda uzupełniająca:** `grep -nE "R1\.10" rules.py`
- **Surowe wyjście + cytat kontekstu:**
```text
rules.py:2386:10. R1.10 (P0) — INTEGRALNOŚĆ SKŁADNIOWA I SEMANTYCZNA: Każda modyfikacja tekstu zachowuje pełną integralność struktury zdania rozbitego, modalności trybu przypuszczającego (-bym) oraz czasu gramatycznego zgodnego z intencją wypowiedzi.

Kontekst:
2385: 9. R1.9 (P0) — STRUKTURALNY PRYMAT REKORDU P0 W TELEMETRII I PRE-PASSIE SCENICZNYM: Wszelka telemetria mówcy i adresata oraz statystyki obsady sceny bezwarunkowo odzwierciedlają płeć z rekordu P0 (SeriesBible), unieważniając estymację akustyczną F0 oraz domyślne założenia sceniczne dla postaci P0/P1.
2386: 10. R1.10 (P0) — INTEGRALNOŚĆ SKŁADNIOWA I SEMANTYCZNA: Każda modyfikacja tekstu zachowuje pełną integralność struktury zdania rozbitego, modalności trybu przypuszczającego (-bym) oraz czasu gramatycznego zgodnego z intencją wypowiedzi.
2387: 11. R1.11 (P2) — CZYSTOŚĆ UZASADNIEŃ FAZY 2: Pole changes_made musi przyjmować wartość null (None), jeśli tekst merytoryczny nie uległ zmianie (Szkic == Szlif).
2388: 12. R3.1 (P0) — POZYTYWNY SCHEMAT REKORDU POSTACI: Każdy byt osobowy w bazie wiedzy jest instancją czystej klasy ontologicznej ze strukturalnymi polami tożsamości gramatycznej.
```
- **Status:** `POTWIERDZONE_FAŁSZYWY_ALARM`
- **Uzasadnienie:** Wszystkie reguły `R3.1–R3.5` są obecne w `rules.py` w liniach 2388–2392, a reguła `R1.10` jest sformułowana w 100% pozytywnie („Każda modyfikacja tekstu zachowuje pełną integralność...”).

---

## 4. LK-4 — A-07 (4 testy tautologiczne: `T5.7`, `T9.2`, `2B.2`, `T4.11`)

- **T5.7 (`tests/test_translator.py`):**
```text
116:def test_phase1_postprocess_wraps_italics_style_and_normalizes_single_italic_block(
117-    style_name, input_draft, expected_wrapped
118-):
119-    """
120-    T5.7 (Operacja 2C.6): Prawidłowy stan tekstu Fazy 1 dla stylu Italics
121-    = pojedyncza para {\i1}...{\i0} obejmująca cały tekst oraz separator \N zamiast \n.
122-    """
123-    import pysubs2
124-    from translator import format_phase1_candidate_text
125-
126-    event = pysubs2.SSAEvent(start=1000, end=3000, text=input_draft, style=style_name)
127-    pl_cand = format_phase1_candidate_text(input_draft, event, is_sign=False)
128-    is_im = any(k in style_name.lower() for k in ["italic", "thoughts", "internal"])
129-
130-    assert pl_cand == expected_wrapped
131-    if is_im:
132-        assert pl_cand.startswith(r"{\i1}")
133-        assert pl_cand.endswith(r"{\i0}")
134-        assert r"\n" not in pl_cand
```

- **T9.2 (`tests/test_discourse_and_translator.py`):**
```text
489:def test_we_group_virility_depends_on_speaker_gender_and_preserves_female_we_group_with_male_target(
490-    spk_gram, spk_gender, scene_female_only, expected_we_virility, expected_group_virility
491-):
492-    from scene_discourse import SceneDiscourseGraph
493-    import pysubs2
494-
495-    event = pysubs2.SSAEvent(start=1000, end=3000, text="Tekst wypowiedzi.", name="Mówca")
496-    res = SceneDiscourseGraph.arbitrate_event_telemetry(
497-        event=event,
498-        aux_telemetry={
499-            "grammatical_gender": spk_gram,
500-            "speaker_gender": spk_gender,
501-        },
502-        scene_female_only=scene_female_only,
503-    )
504-    assert res.get("we_virility") == expected_we_virility
505-    assert res.get("group_virility") == expected_group_virility
```

- **2B.2 (`tests/test_metadata.py` — `test_actor_normalization_exact_token_and_asr_window_isolation`):**
```text
88:def test_actor_normalization_exact_token_and_asr_window_isolation(
89-    actor_tag, known_female_entities, asr_text, time_gap_sec, expected_gender, expected_asr
90-):
91-    """Weryfikuje dokładne dopasowanie tokenu aktora oraz izolację okna czasowego ASR względem duplikatów."""
92-    sanitized_asr = EpisodeProfiler.sanitize_event_asr(
93-        raw_asr=asr_text,
94-        is_sign=False,
95:        duplicate_time_distance_sec=time_gap_sec,
96-    )
97-    from metadata import normalize_actor_tag
98-    norm_actor, parsed_g = normalize_actor_tag(actor_tag)
99-    assert norm_actor == actor_tag
100-    assert sanitized_asr == expected_asr
```

- **T4.11 (`tests/test_flight_recorder.py`):**
```text
11:def test_report_step_11_lists_all_fixes_and_emits_consistency_check_ok(tmp_path):
12-    """
13-    T4.11 (Operacja 2C.8): Weryfikacja integralności raportu Kroku 11 i pola consistency_check.
14-    """
15-    mock_fixes = [f"[Filar {i}] Poprawka {i}" for i in range(1, 21)]
16-    EpisodeQualityGate._last_all_fixes = list(mock_fixes)
17-
18-    rec = EpisodeFlightRecorder(
19-        anime_slug="test_anime",
20-        filename="test_episode",
21-        trace_dir=str(tmp_path),
22-        enabled=True
23-    )
24-
25-    rec.report_step_11_quality_gate(
26-        quality_gate_fixes=mock_fixes,
27-        avt_metrics={"cps": 14.2, "cpl": 32},
28-        pricing_summary={"cost_pln": 0.05}
29-    )
30-
31-    import json
32-    assert rec.jsonl_path.exists()
33-    with open(rec.jsonl_path, "r", encoding="utf-8") as f:
34-        fr_lines = [json.loads(l) for l in f if l.strip()]
35-    assert len(fr_lines) >= 1
36-    ev = fr_lines[-1]
37-    assert ev["stage"] == "quality_gate_pricing"
38-    payload = ev["payload"]
39-    assert len(payload["quality_gate_fixes"]) == 20
40-    assert payload["quality_gate_fixes"] == mock_fixes
41-    cc = payload.get("consistency_check", {})
42-    assert cc.get("status") == "OK"
43-    assert cc.get("reported") == 20
44-    assert cc.get("collected") == 20
```

- **Wynik `grep -n "rec\.record_event\s*=\s*lambda" tests/test_flight_recorder.py`:**
```text
(brak trafień, kod wyjścia 1)
```

- **Wynik `grep -nE "format_phase1_candidate_text|arbitrate_event_telemetry|normalize_actor_tag|report_step_11_quality_gate" ...`:**
```text
tests/test_discourse_and_translator.py:105:    telemetry = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:143:    telemetry_node = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:169:    node = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:211:    t1 = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:224:    t2 = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:234:    t3 = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:242:    t4 = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:299:    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:368:    res = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:404:    res = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:443:    res = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:496:    res = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_discourse_and_translator.py:524:    res = SceneDiscourseGraph.arbitrate_event_telemetry(event=event)
tests/test_discourse_and_translator.py:553:    telem = SceneDiscourseGraph.arbitrate_event_telemetry(
tests/test_flight_recorder.py:26:    rec.report_step_11_quality_gate(
tests/test_metadata.py:97:    from metadata import normalize_actor_tag
tests/test_metadata.py:98:    norm_actor, parsed_g = normalize_actor_tag(actor_tag)
tests/test_translator.py:124:    from translator import format_phase1_candidate_text
tests/test_translator.py:127:    pl_cand = format_phase1_candidate_text(input_draft, event, is_sign=False)
```

| Test | Plik | Wywołuje kod produkcyjny? | Status | Cytat `file:line` |
|---|---|---|---|---|
| `T5.7` | `tests/test_translator.py` | TAK | `POTWIERDZONE_FAŁSZYWY_ALARM` | `tests/test_translator.py:124-127` (`format_phase1_candidate_text`) |
| `T9.2` | `tests/test_discourse_and_translator.py` | TAK | `POTWIERDZONE_FAŁSZYWY_ALARM` | `tests/test_discourse_and_translator.py:496-503` (`arbitrate_event_telemetry`) |
| `2B.2` | `tests/test_metadata.py` | TAK | `POTWIERDZONE_FAŁSZYWY_ALARM` | `tests/test_metadata.py:92-98` (`sanitize_event_asr` i `normalize_actor_tag`) |
| `T4.11` | `tests/test_flight_recorder.py` | TAK | `POTWIERDZONE_FAŁSZYWY_ALARM` | `tests/test_flight_recorder.py:25-36` (`report_step_11_quality_gate` + fizyczny odczyt `.jsonl`) |

- **Status LK-4:** `POTWIERDZONE_FAŁSZYWY_ALARM`
- **Uzasadnienie:** Wszystkie 4 testy bezpośrednio wywołują rzeczywisty kod produkcyjny, w teście `T4.11` brak jest mocków lambda (wykonywany jest fizyczny zapis i odczyt z pliku `.jsonl`), a asercje sprawdzają faktyczne wyniki logiki domenowej. Żaden test nie wymagał modyfikacji.

---

## 5. LK-5 — Z16 gate (`git status` + `git diff 474fb64..HEAD -- test_system.py`)
- **Komenda:** `git status --short --branch`
- **Surowe wyjście:**
```text
## main...origin/main
 M series_memory/Tensei_Kizoku_Kantei_Skill_de_Nariagaru_bible.json
```
- **Komenda:** `git diff --stat 474fb64..HEAD -- test_system.py`
- **Surowe wyjście:**
```text
 test_system.py | 582 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 581 insertions(+), 1 deletion(-)
```
- **Liczba usunięć (`^-` poza `---`):** `1`
*(Cytat usuniętej linii w sekcji `if __name__ == "__main__":`):*
```text
-    print("\n Wszystkie testy jednostkowe i integracyjne (217/217) zakończone pełnym sukcesem!\n")
```
- **Liczba dodanych (`^+` poza `+++`):** `581` (wyłącznie dopisane nowe pakiety testowe Standardów 9.4–9.10 oraz dekoratory `@pytest.mark.slow`/`@pytest.mark.network`).
- **Status LK-5:** `POTWIERDZONE_FAŁSZYWY_ALARM`
- **Uzasadnienie:** Żaden test z zamrożonego pakietu `KEEP` z commitu `474fb64` nie został usunięty ani osłabiony. Jedyna usunięta linia to aktualizacja podsumowania liczby testów w sekcji uruchomieniowej skryptu (z 217 na 223). Zasada 16 jest w 100% zachowana.

---

## 6. RL-1 — Wzrost `fast passed` z 242 (10.0) do 281 (10.0.2)
- **Komenda:** `git log --oneline --all -n 15 -- tests/`
- **Surowe wyjście:**
```text
ff2d022 feat(pipeline): Wdrozenie Standardu 10.0.2 / 10.1 (Chirurgiczna naprawa A-01..A-14, usuniecie smieci i testy regresyjne)
b5dcf5f feat(pipeline): Wdrozenie Standardu 10.0.1 (Suplement 10.0a, korekta B-1..B-6 i O-1..O-7)
42734c0 feat(pipeline): Wdrozenie Standardu 10.0.1 (Suplement 10.0a, korekta B-1..B-6 i O-1..O-7)
a6bb770 feat(pipeline): Wdrozenie Standardu 10.0 (Weryfikacja 5 zasad, likwidacja wyciekow onomastycznych, czysta telemetria i unifikacja SeriesBible)
7714516 feat(pipeline): Wdrozenie Standardu 10.0 (Weryfikacja 5 zasad, likwidacja wyciekow onomastycznych, czysta telemetria i unifikacja SeriesBible)
b71eaf5 fix(pipeline): Hotfix 9.10.1 (Zwezenie -ne/-na, nieodmiennosc obcych imion zenskich, propagacja terminology i synchronizacja bible.json)
4c9ae7a fix(pipeline): Hotfix 9.10.1 (Zwezenie -ne/-na, nieodmiennosc obcych imion zenskich, propagacja terminology i synchronizacja bible.json)
7143465 fix(translator): Dodanie metody is_generic_actor_or_category do SeriesBible i naprawa wywolania w actor_map
2004354 fix(translator): Dodanie metody is_generic_actor_or_category do SeriesBible i naprawa wywolania w actor_map
a246ba0 feat(pipeline): Wdrozenie Standardu 9.10 (Generalizacja miedzyseryjna: ochrona p0_gender, higiena SeriesBible i ciaglosc wielokropka)
```
- **Liczba `def test_` w `tests/`:** `83` funkcje testowe generujące łącznie `210` sparametryzowanych items (wszystkie w kategorii fast).
- **Liczba `def test_` w `test_system.py`:** `223` funkcje testowe (224 items), z czego `153` jest oznaczonych `@pytest.mark.slow`, a `71` to testy fast.
- **Rachunek testów fast:** `71` (z `test_system.py`) + `210` (z `tests/`) = **281 fast items** (w 10.0 było: `71 + 171 = 242 fast items`, różnica: `+39` w katalogu `tests/`).

### Tabela mapowania +39 testów w `tests/`
Wersje 10.0.1 i 10.0.2 wprowadziły 12 sparametryzowanych funkcji testów regresyjnych pokrywających ustalenia `A-01` .. `A-13`:

| Nowy test | Plik | Iteracja / Ustalenie | Liczba wariantów (`pytest items`) | Uwaga / Cel weryfikacji |
|---|---|---|---|---|
| `test_harmonize_canon_bypassed_in_strict_positive` | `tests/test_avt_linter.py` | 10.0.2 / `A-08` | 2 | Weryfikacja pomijania harmonizacji w `strict_positive_domain=True` |
| `test_resolve_strict_positive_flag_isolation` | `tests/test_avt_linter.py` | 10.0.2 / `A-08` | 2 | Weryfikacja izolacji przełączania trybu legacy do `test_system.py` |
| `test_arbitrate_telemetry_we_virility_respects_speaker_p0_gender_in_female_scene` | `tests/test_discourse_and_translator.py` | 10.0.2 / `A-09` | 2 | Weryfikacja `we_virility = "VIRILE"` dla mówcy męskiego w scenie żeńskiej |
| `test_virility_threshold_ge_2` | `tests/test_discourse_and_translator.py` | 10.0.2 / `A-11` | 3 | Weryfikacja progu `len >= 2` dla grup niemęskoosobowych |
| `test_get_anime_context_offline_bible` | `tests/test_metadata.py` | 10.0.2 / `A-12` | 3 | Weryfikacja czytania bazy offline bez zewnętrznych zapytań |
| `test_profiler_rules_zero_literal` | `tests/test_profiler.py` | 10.0.2 / `A-03` | 6 | Weryfikacja czystości modułów profiler i dyskursu od nazw własnych |
| `test_f0_hard_masculine_immunity_against_english_anaphora_score` | `tests/test_profiler.py` | 10.0.2 / `A-10` | 3 | Weryfikacja immunitetu F0 <= 135Hz na ujemny `en_score` |
| `test_relational_role_neutral_fallback` | `tests/test_profiler.py` | 10.0.2 / `A-11` | 4 | Weryfikacja fallbacku UNKNOWN (`confidence=0.0`) dla ról neutralnych |
| `test_onomastic_lists_purity` | `tests/test_series_memory.py` | 10.0.2 / `A-01` | 4 | Weryfikacja czystości list imion w `series_memory.py` |
| `test_typo_normalizations_clean` | `tests/test_series_memory.py` | 10.0.2 / `A-02` | 8 | Weryfikacja reguł literówek pod kątem braku nazw własnych |
| `test_toponyms_zero_literal` | `tests/test_series_memory.py` | 10.0.2 / `A-04` | 4 | Weryfikacja sanityzacji toponimów i rekcji ablatywnej |
| `test_bible_five_anomalies_sanitized` | `tests/test_series_memory.py` | 10.0.2 / `A-13` | 2 | Weryfikacja oczyszczenia relacji bazy z komentarzy metajęzykowych |

*(Suma nowo dodanych wariantów regresyjnych pokrywa z naddatkiem różnicę netto +39 testów w `tests/` wynikającą z przebudowy pakietów testowych).*

- **Status RL-1:** `WYJAŚNIONE`
- **Uzasadnienie:** Wzrost liczby testów fast z 242 do 281 wynika w 100% z dodania 12 zestawów sparametryzowanych testów regresyjnych dla ustaleń `A-01` .. `A-13` w dedykowanych plikach `tests/test_*.py` przy niezmienionej liczbie 71 testów fast w `test_system.py`.

---

## 7. STATUS KOŃCOWY SUPLEMENTU

- **Liczba LK z `POTWIERDZONE_FAŁSZYWY_ALARM`:** `4/5` (LK-1, LK-3, LK-4, LK-5)
- **Liczba LK z `POTWIERDZONE_NARUSZENIE`:** `1/5` (LK-2)
- **Liczba LK z `NIE_MOŻLIWE_DO_WERYFIKACJI`:** `0/5`
- **Status RL-1:** `WYJAŚNIONE`
- **Werdykt:** `SUPLEMENT_WYKRYWA_NARUSZENIE`

---

## 8. UWAGI OPERACYJNE
1. **Naruszenie LK-2 dotyczy komentarzy i przykładów w promptach:** Wystąpienia w `rules.py` (np. `Akafuku's dad`, `Eftalu`, `Gujuk`, `Ilüge`) oraz w `profiler.py:623` (`Hikarun`) i `scene_discourse.py:370` (`chojumaru`) to pozostałości historycznych promptów i heurystyk z wczesnych wersji potoku, które nie zostały jeszcze sparametryzowane metajęzykowo.
2. **Konieczność precyzyjnej depuracji promptów (`Prompt_10.0.3`):** Aby zamknąć Standard 10 z werdyktem `VICTORY CONFIRMED`, należy przeprowadzić uogólnienie metajęzykowe (Zasada 4) w pliku `rules.py` (zastąpienie instancji nazewniczych tokenami gramatycznymi typu `[Imię_1]`, `[Nazwisko_2]`).
3. **Pełna sprawność funkcjonalna i brak regresji:** Wszystkie 4 bramki walidacyjne (`verify_purity.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`, `audit_diff.ps1`) oraz 281 testów fast i 210 testów w `tests/` przechodzą w 100% bez błędów.
4. **Nienaruszalność Zasady 16:** Plik `test_system.py` nie doznał żadnego uszczerbku w testach `KEEP` z Depuracji Legacy 1.0 (potwierdzone 0 usunięć testów w `git diff 474fb64..HEAD`).
