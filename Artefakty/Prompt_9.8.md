# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.8.md

# PROMPT NAPRAWCZY POTOKU AVT — WERSJA 9.8 (MIKRO-DOMKNIĘCIE OPERACJI 2C.2)

## PREAMBUŁA

Dokument definiuje operację domykającą potok AVT z wersji 9.7 (commit `1e27a17`) oraz utrzymującą stan po Depuracji Legacy 1.0 (commit `474fb64`) do wersji **9.8**. Podstawa empiryczna: audyt weryfikacyjny przebiegu odcinka testowego po wdrożeniu wersji 9.7 (Etap 1/2), który potwierdził pełne wyeliminowanie 3 z 4 problemów z wersji 9.6 (`2C.1`: zero duplikacji dwuczłonowych antroponimów P0 w `ID: 48` i `ID: 52` oraz czyste listy `aliases` w Kroku 6; `2C.3`: zero pustych wpisów `[Redaktor Dialogów]` przy różnicy spacja vs `\N`; `2C.4`: zero artefaktów `.? ??000` w ASR w `ID: 79`), a jednocześnie zidentyfikował **1 mikro-lukę w runtime w operacji `2C.2`**:
- **Kategoria Problemu 1 (Nadpisywanie w RAM płci leksykalnej etykiety `Boy` przez `audit_speaker_metadata_against_audio` oraz wymuszanie `Grupa_1os_lm: NON_VIRILE` na liniach z udziałem mówców męskich — z operacji `2C.2` w 9.7):**
  1. W `SeriesBible.populate_secondary_actor_tags` (`series_memory.py:6287, 6299`) etykiety o jednoznacznej płci leksykalnej (`Boy`, `Girl`, `Man`, `Woman`) otrzymały `"has_verified_gender": False`.
  2. Podczas analizy `[Linia #58 | Aktor: Girl]` (`0:04:56.83`) funkcja `_resolve_line_addressee` (`translator.py:2911, 2945`) wywołała `self.series_bible.audit_speaker_metadata_against_audio("Boy", audio_gender=next_audio_g, scene_gender="FEMALE")`, która z braku flagi `has_verified_gender: True` uznała etykietę `"Boy"` za niezweryfikowany tag i nadpisała jej płeć na `"FEMALE"`, generując w Kroku 10 `Adresat: Boy (FEMININE)`.
  3. Ponadto w `_precompute_episode_scene_genders` (`translator.py:1788-1793`) flaga `female_only_scene: True` z `dramatic_sequences` przypisała `episode_scene_genders[orig_idx] = "kobieta"` całemu przedziałowi czasowemu sekwencji bez sprawdzenia, czy w danej linii lub scenie występuje mówca/adresat męski (`MALE`), co w `_prepare_batch_prompt` (`translator.py:3145`) i `_process_single_batch` (`translator.py:3960, 4000`) wymusiło `Grupa_1os_lm: NON_VIRILE | Grupa_2os_lm: NON_VIRILE` na liniach wypowiadanych przez postacie męskie (`Sasaki`, `Boy` w `ID: 36–60`).

Niniejszy dokument przestrzega zasad Standardu 9.0–9.8:
1. **Zero-Literal (Zasada 1)** — brak literalnych nazw własnych i cytatów z odcinka audytowanego w kodzie, regułach, testach i raporcie.
2. **Pure Positive Domain Invariant (Zasada 2)** — wyłącznie pozytywne sformułowania reguł i kryteriów akceptacji.
3. **Primary LLM Translation Authority (Zasada 3)** — nienaruszalność tekstu autorytatywnego Fazy 1/2.
4. **Instance-Free Metalinguistic Architecture (Zasada 4)** — operowanie na kategoriach metajęzyka architektury.
5. **Ochrona nienaruszalności Depuracji Legacy 1.0 (Zasada 16)** — zachowanie wszystkich 204 testów domyślnych w trybie fast, 153 testów `slow`, 12 testów `network`, katalogu `tests/archive/` oraz 3 gałęzi `# DEFENSIVE_FALLBACK` w `avt_linter.py`.

Numer wersji: **9.8**. Poprzednia wersja toru naprawczego: **9.7** (commit `1e27a17`). Wersja toru Depuracji Legacy w tle: **1.0** (commit `474fb64`).

---

## FAZA 0 — CZYTANIE KODU (OBOWIĄZKOWA)

### P0.1. Lista plików do przeczytania i weryfikacji ścieżek wywołań runtime
1. `series_memory.py` — inspekcja `populate_secondary_actor_tags` (`linia ~6253`) oraz `audit_speaker_metadata_against_audio` (sprawdzenie, dlaczego etykieta o inherentnej płci leksykalnej z `masculine_lexicon` / `feminine_lexicon` uległa nadpisaniu pod wpływem `scene_gender="FEMALE"`).
2. `translator.py` — inspekcja `_precompute_episode_scene_genders` (`linie 1775-1850`), `_resolve_line_addressee` (`linie 2890-2950`), `_prepare_batch_prompt` (`linie 3045-3165`) oraz `_process_single_batch` (`linie 3950-4035`) pod kątem wyznaczania `is_fem_scene`, `line_pl_grp` (`Grupa_1os_lm`) i `line_you_grp` (`Grupa_2os_lm`), gdy mówcą lub adresatem linii jest postać męska (`MALE` / `MASCULINE`).

### P0.2. Tabela mapowania plan ↔ kod (do wypełnienia w `Raport_wdrozenia_9.8.md`)

| Operacja (sekcja 9.8) | Miejsce wywołania / metoda w planie | Rzeczywiste miejsce wywołania w kodzie (plik + linia + metoda) | Rzeczywista sygnatura w kodzie | Zgodność | Uwagi / Rozstrzygnięcie |
|---|---|---|---|---|---|
| 2C.1 | Flaga `has_verified_gender: True` dla jednoznacznych leksykalnie etykiet płciowych w `populate_secondary_actor_tags`, blokada ich mutacji w `audit_speaker_metadata_against_audio` oraz wykluczenie `is_fem_scene` / `NON_VIRILE` przy mówcy lub adresacie męskim (`series_memory.py`, `translator.py`) | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` | `<DO_WYPEŁNIENIA_PRZEZ_AGENTA_KODUJĄCEGO>` |

### P0.3. Tabela mapowania danych testowych (do wypełnienia w `Raport_wdrozenia_9.8.md`)

| Placeholder | Wartość rzeczywista (z odcinka testowego, spoza audytu) | Źródło (P0 / EN / ASS) | Uwagi |
|---|---|---|---|
| `<RZECZYWISTA_ETYKIETA_MĘSKA_P1_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | `[Events]` | Jednoznaczna leksykalnie etykieta męska (np. `Boy`) |
| `<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P1_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | `[Events]` | Jednoznaczna leksykalnie etykieta żeńska (np. `Girl`) |
| `<RZECZYWISTY_ANTROPONIM_MĘSKI_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | P0 (`SeriesBible`) | Mówca męski P0 |
| `<WARTOŚĆ_ENUM_TECHNICZNA_1>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | KOD | `MASCULINE` |
| `<WARTOŚĆ_ENUM_TECHNICZNA_2>` | `<DO_WYPEŁNIENIA_MAPOWANIE_P0_3>` | KOD | `VIRILE` |

### P0.4. Weryfikacja flag Phase 0 (Flaga 0.P dla wersji 9.8)
1. **FLAGA PHASE 0.P (Interakcja `populate_secondary_actor_tags` z `audit_speaker_metadata_against_audio` oraz `is_fem_scene` w `translator.py`):**
   - *Pytanie weryfikacyjne:* Dlaczego w `_resolve_line_addressee` (`translator.py:2911, 2945`) wywołanie `audit_speaker_metadata_against_audio` zmieniło płeć `next_spk = "Boy"` z `"MALE"` na `"FEMALE"` przy `next_sc_g = "FEMALE"`, oraz dlaczego w `_prepare_batch_prompt` (`translator.py:3145`) i `_process_single_batch` (`translator.py:3960, 4000`) zmienna `is_fem_scene` pozostawała `True` na liniach, w których mówcą lub adresatem jest postać męska (`MALE` / `MASCULINE`)?

---

## SEKCJA 1: REGUŁY DLA MODELI LLM (Faza 1 i Faza 2)

Wszystkie reguły `R1.1–R1.11` z wersji 9.7 pozostają w 100% utrzymane w czystej formie pozytywnej.

---

## SEKCJA 2: OPERACJE (2A / 2B / 2C)

### 2A — Operacje potwierdzone z wersji 9.7 (bez nowych akcji)
1. **`2A.1` (z 9.7/2C.1):** Selektywne przypisanie aliasów z tytułu serii wyłącznie do pasującej fonetycznie encji P0 oraz pełna blokada duplikacji członów wieloczłonowych antroponimów (`ID: 48` i `ID: 52` w 100% czyste) — potwierdzona empirycznie.
2. **`2A.2` (z 9.7/2C.3):** Tożsamość leksykalna przy zamianie spacji `" "` na `\N` (`is_lexically_identical_ignoring_linebreak`) i brak pustych wpisów `[Redaktor Dialogów]` — potwierdzona empirycznie.
3. **`2A.3` (z 9.7/2C.4):** Wycinanie artefaktów `.? ??000` i `???000` z japońskiego segmentu ASR w `EpisodeProfiler.sanitize_event_asr` — potwierdzona empirycznie.
4. **`2A.4` (z 9.4–9.6):** Wszystkie operacje potwierdzone w 9.6 (`2A.1–2A.7` z 9.7) — utrzymane w 100%.

### 2B — Nowe operacje
Brak nowych operacji spoza domknięcia `2C.1`.

### 2C — Domknięcie operacji z poprzedniego promptu 9.7

#### OPERACJA 2C.1 (z 9.7/2C.2) — Niezmienność płci leksykalnej etykiet osobowych (`Boy`, `Girl`) wobec `audit_speaker_metadata_against_audio` oraz blokada `is_fem_scene` / `NON_VIRILE` w obecności mówcy lub adresata męskiego (`series_memory.py` + `translator.py`)
- **Konflikt z 9.7:** W `post97_full_trace.log` w `[Linia #58 | Aktor: Girl]` wyemitowano `Adresat: Boy (FEMININE)`, ponieważ `audit_speaker_metadata_against_audio("Boy", ..., scene_gender="FEMALE")` nadpisało `"gender": "MALE"` dla etykiety `"Boy"` (posiadającej `"has_verified_gender": False`), a na liniach `ID: 36–60` wypowiadanych przez mężczyzn (`Sasaki`, `Boy`) wyemitowano `Grupa_1os_lm: NON_VIRILE | Grupa_2os_lm: NON_VIRILE`, ponieważ `episode_scene_genders[orig_idx] == "kobieta"` z pre-passu sekwencji nie zostało uchylone w obecności mówcy/adresata męskiego.
- **Rozstrzygnięcie:** **ROZSZERZYĆ** `SeriesBible.populate_secondary_actor_tags`, `SeriesBible.audit_speaker_metadata_against_audio` (`series_memory.py`) oraz wyznaczanie `is_fem_scene` i `episode_scene_genders` w `translator.py`.
- **Implementacja:**
  1. **Twarda weryfikacja leksykalna (`has_verified_gender: True`) w `populate_secondary_actor_tags` (`series_memory.py`):**
     W `SeriesBible.populate_secondary_actor_tags` dla etykiet dopasowanych do `masculine_lexicon` lub `feminine_lexicon` (takich jak `Boy`, `Girl`, `Man`, `Woman`) ustaw `"has_verified_gender": True` oraz `"confidence": 0.95` — słownikowe znaczenie rzeczownika pospolitego oznaczającego płeć ludzką (`Boy` = chłopiec, `Girl` = dziewczyna) stanowi twardy niezmiennik leksykalny i nie podlega odwróceniu przez estymację akustyczną ani statystykę sceny.
  2. **Ochrona etykiet o inherentnej płci leksykalnej w `audit_speaker_metadata_against_audio` (`series_memory.py`):**
     Na samym początku `SeriesBible.audit_speaker_metadata_against_audio(speaker_name, ...)`: jeśli `speaker_name` posiada w `self.data["characters"]` flagę `has_verified_gender: True` LUB jego tokeny należą do `INHERENT_MALE_NOUNS` / `INHERENT_FEMALE_NOUNS` (w tym `boy`, `man`, `girl`, `woman`), natychmiast zwróć `(canonical_gender, False)` bez modyfikowania płci na podstawie `scene_gender` lub `audio_gender`.
  3. **Wykluczenie `is_fem_scene = True` i `NON_VIRILE` w obecności mówcy lub adresata męskiego (`translator.py`):**
     - W `_precompute_episode_scene_genders` (`translator.py`): po przypisaniu `scene_genders` z `dramatic_sequences`, dla każdego zdarzenia `(orig_idx, ev)` sprawdź płeć jawnego aktora `ev.name` w `SeriesBible` / `resolve_actor_gender`: jeśli aktor ma płeć `"MALE"` (`MASCULINE`), ustaw `scene_genders[orig_idx] = "mężczyzna"` (pojedyncza kwestia wypowiadana przez mężczyznę nigdy nie ma `scene_gender == "kobieta"`).
     - W `_prepare_batch_prompt` (`translator.py:3045, 3145`) oraz `_process_single_batch` (`translator.py:3960, 4000`): zdefiniuj `has_male_participant_in_line = (spk_gram_tag == "MASCULINE") or (tgt_gram_tag == "MASCULINE") or (line_spk_gender == "mężczyzna") or (line_addr_cat in ["mężczyzna", "mężczyzna_dual", "grupa_mężczyzn"])`. Jeśli `has_male_participant_in_line` jest `True`, ustaw bezwarunkowo `is_fem_scene = False`, a dla grup wieloosobowych z udziałem mówcy męskiego `Grupa_1os_lm = "VIRILE"`.
- **Kryterium akceptacji:** Prawidłowy stan pola `Telemetria:` w Kroku 10 dla każdej linii, w której mówcą lub adresatem jest postać męska P0/P1 (w tym `Boy` i `Sasaki`) = `Adresat: Boy (MASCULINE)` w `ID: 58` (`0` wystąpień `Boy (FEMININE)` w całym logu) oraz całkowity brak tagu `Grupa_1os_lm: NON_VIRILE` na liniach wypowiadanych przez mówców męskich (`MASCULINE`) (źródło autorytetu: semantyka leksykalna etykiety `[Events]` oraz polska gramatyka rodzaju męskoosobowego).

---

## SEKCJA 3: REGUŁY DLA PIPELINE'U DANYCH

Wszystkie reguły `R3.1–R3.5` z wersji 9.7 pozostają utrzymane, ze wzmocnieniem `R3.2`:
- **R3.2 (P0) — Nienaruszalność Płci Leksykalnej Etykiet P1 (`Boy`, `Girl`) i Spójność `VIRILE`/`NON_VIRILE` z Płcią Mówcy w `Telemetria:`:**
  - **Definicja pozytywna:** Prawidłowy stan wektora `Telemetria:` w Kroku 10 = zachowanie `MASCULINE` dla etykiety `Boy` i `FEMININE` dla etykiety `Girl` niezależnie od domyślnej flagi sceny (`audit_speaker_metadata_against_audio` zachowuje płeć leksykalną bez zmian) oraz wykluczenie kategorii `NON_VIRILE` w polu `Grupa_1os_lm` na każdej linii, w której mówca ma rodzaj `MASCULINE`.

---

## SEKCJA 4: KOLEJNOŚĆ WDROŻENIA

1. **ETAP 1:** Wykonanie Phase 0 (weryfikacja `populate_secondary_actor_tags`, `audit_speaker_metadata_against_audio` i `is_fem_scene` oraz wypełnienie P0.2, P0.3 i Flagi 0.P w `Raport_wdrozenia_9.8.md`).
2. **ETAP 2:** Wdrożenie Operacji `2C.1` w `series_memory.py` i `translator.py`.
3. **ETAP 3:** Dodanie testu jednostkowego `T8.1` w `tests/test_discourse_and_translator.py`, uruchomienie `pytest` (fast + full) oraz 4 bramek CI/CD i potwierdzenie weryfikacji empirycznej w `Raport_wdrozenia_9.8.md`.

---

## SEKCJA 5: WALIDACJA TESTOWA I WARUNEK UKOŃCZENIA

### Wykaz nowego testu `T8.1` (marker: `unit`)

```python
import pytest

# WZORZEC T8.1 (Operacja 2C.1) -> tests/test_discourse_and_translator.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "secondary_tag,scene_gender_override,expected_audited_gender,expected_telemetry_gender",
    [
        ("<RZECZYWISTA_ETYKIETA_MĘSKA_P1_1>", "FEMALE", "MALE", "<WARTOŚĆ_ENUM_TECHNICZNA_1>"),
        ("<RZECZYWISTA_ETYKIETA_ŻEŃSKA_P1_1>", "MALE", "FEMALE", "FEMININE"),
    ],
)
def test_secondary_lexical_gender_immunity_against_scene_gender_override_and_male_speaker_non_virile_ban(
    secondary_tag, scene_gender_override, expected_audited_gender, expected_telemetry_gender
):
    from series_memory import SeriesBible
    from scene_discourse import SceneDiscourseGraph

    bible = SeriesBible(slug="test_lexical_gender_immunity_98")
    bible.populate_secondary_actor_tags([secondary_tag])
    char_entry = bible.get_character(secondary_tag)
    assert char_entry is not None
    assert char_entry.get("has_verified_gender") is True

    audited_g, is_cont = bible.audit_speaker_metadata_against_audio(
        secondary_tag, audio_gender=scene_gender_override, scene_gender=scene_gender_override
    )
    assert is_cont is False
    assert audited_g == expected_audited_gender
    assert bible.get_character(secondary_tag).get("gender") == expected_audited_gender

    res = SceneDiscourseGraph.arbitrate_event_telemetry(
        raw_actor="<RZECZYWISTY_ANTROPONIM_MĘSKI_1>",
        verified_p0_gender="MALE",
        target_actor=f"{secondary_tag} (Kobieta)",
        series_bible=bible,
        scene_female_only=True,
        is_internal_monologue=False,
    )
    assert res.get("target_gender") == expected_telemetry_gender