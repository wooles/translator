# Plik: C:\Users\Piotrek\Desktop\translator\Artefakty\Prompt_9.10.1.md

# PROMPT NAPRAWCZY POTOKU AVT — WERSJA 9.10.1 (HOTFIX REGRESJI 9.10)

## PREAMBUŁA

Dokument definiuje hotfix 9.10.1 dla regresji wykrytych przez audyt weryfikacyjny 9.10 (Etap 1/2 = 4/4 PASS, Etap 2/2 = 6/6 PASS, ale Cross-check 2 v2 ujawnił 3 regresje w testach `slow`/`network` + `bible.json` nieaktualny na dysku po sanityzacji). Hotfix jest mikro-iteracją: 5 poprawek kodu (H1–H5), 3 testy regresyjne (T10.1.1–T10.1.3), re-run pełnego pakietu testów (375/375), re-sanityzacja i zapis `bible.json` na dysku + kopia do `Artefakty/`.

Bazowy commit: `7143465` (HEAD po hotfixie agenta 9.10, zawiera `is_generic_actor_or_category` w `SeriesBible`). Poprzednia iteracja: 9.10 (commit `a246ba0`). Depuracja Legacy 1.0 (commit `474fb64`): 116 KEEP, 153 MARK_SLOW, 3 DEFENSIVE_FALLBACK, `tests/archive/` — bez zmian.

Numer wersji: **9.10.1**. Poprzednia: **9.10**. Depuracja Legacy: **1.0**.

---

## FAZA 0 — CZYTANIE KODU (OBOWIĄZKOWA)

### P0.1. Lista plików do przeczytania przed modyfikacją

1. `series_memory.py`:
   - `is_polish_adjective` (linia ~2314)
   - `_sanitize_loaded_bible_in_ram` (linie ~1700-1780)
   - `generate_polish_name_declension` (linie ~2820-2960)
   - `SeriesBible.__init__`, `SeriesBible.load()` i `SeriesBible.save()` (gdzie ustawiany `file_path`)
   - `COLLECTIVE_LABELS`, `FEMALE_LEXICON_NAMES`, `UNIVERSAL_FEMALE_NAMES_ON_A` (linie ~2050-2150)
2. `translator.py` — miejsce wywołania `series_bible._sanitize_loaded_bible_in_ram()` w `translate_file`; miejsce, gdzie powinien być `series_bible.save()`.
3. `test_system.py` — 3 oblane testy (TYLKO DO ODCZYTU — zakaz modyfikacji `test_system.py`):
   - `test_quality_gate_name_declension_vocative_and_micro_lines` (linia ~2880): `assert audited_subs.events[3].text == "Muszę uciekać z Töregene!"`
   - `test_tenmaku_ep12_holistic_domain_guard` (linia ~6100): `assert chulan_decl.get("gender") == "FEMALE"`
   - `test_hyouken_s2_root_cause_anilist_fallback_and_addressee_guard` (linia ~14897): `assert decl.get("Ariane Olgren", {}).get("D") == "Ariane Olgren"`

### P0.2. Tabela mapowania plan ↔ kod (do wypełnienia w `Raport_wdrozenia_9.10.1.md`)

| Operacja | Miejsce w planie | Rzeczywiste w kodzie (plik + linia + metoda) | Sygnatura | Zgodność | Uwagi |
|---|---|---|---|---|---|
| H1 | `is_polish_adjective` — zawęzić `-ne` i `-na` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` |
| H2 | `_sanitize_loaded_bible_in_ram` — propagacja płci z `terminology`/`glossary` oraz zapis `"gender"` w `declensions` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` |
| H3 | `generate_polish_name_declension` — dwuczłonowe imię żeńskie + żeńskie na spółgłoskę | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` |
| H4 | `SeriesBible.__init__` / `save()` — synchronizacja z `Artefakty/` + `save()` w pipeline i re-sanityzacja na dysku | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` |
| H5 | `_sanitize_loaded_bible_in_ram` — rozszerzenie `COLLECTIVE_LABELS` (`Animals` i in.) oraz regeneracja skażonych `declensions` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` | `<DO_WYPEŁNIENIA>` |

### P0.3. Tabela mapowania danych testowych (do wypełnienia w `Raport_wdrozenia_9.10.1.md`)

| Placeholder | Wartość rzeczywista (spoza Hyouken) | Źródło | Uwagi |
|---|---|---|---|
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_HISTORYCZNY_1>` | `<DO_WYPEŁNIENIA>` | `[Events]` | Żeńskie imię historyczne na `-e` spoza Hyouken (np. `Töregene`) |
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_HISTORYCZNY_2>` | `<DO_WYPEŁNIENIA>` | `[Events]` | Drugie żeńskie imię historyczne na `-e` lub spółgłoskę spoza Hyouken |
| `<RZECZYWISTY_PRZYMIOTNIK_MĘSKI_1>` | `<DO_WYPEŁNIENIA>` | Glosariusz | Przymiotnik męski na `-ny` |
| `<RZECZYWISTY_PRZYMIOTNIK_MĘSKI_N_1>` | `<DO_WYPEŁNIENIA>` | Glosariusz | Forma N. przymiotnika |
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_DWUCZŁONOWY_1>` | `<DO_WYPEŁNIENIA>` | P0 | Dwuczłonowe imię żeńskie spoza Hyouken (pierwszy człon na `-e` lub spółgłoskę, drugi na spółgłoskę, np. `Violet Evergarden`) |
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_DWUCZŁONOWY_2>` | `<DO_WYPEŁNIENIA>` | P0 | Drugie dwuczłonowe imię żeńskie spoza Hyouken |
| `<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_P0_1>` | `<DO_WYPEŁNIENIA>` | P0 | Żeńska postać P0 z `terminology`/`glossary` spoza Hyouken |
| `<RZECZYWISTY_CZŁON_ALIASU_1>` | `<DO_WYPEŁNIENIA>` | `terminology`/`glossary` | Alias z `terminology`/`glossary` (np. `Chulan` z `Khulan`) |

---

## SEKCJA 1: REGUŁY DLA MODELI LLM

Wszystkie reguły `R1.1–R1.11` z wersji 9.7–9.10 pozostają utrzymane w czystej formie pozytywnej.

---

## SEKCJA 2: OPERACJE (2A / 2B)

### 2A — Operacje potwierdzone z 9.10 (bez nowych akcji)

1. **`2A.1`** (9.10/2B.1): Ochrona strukturalnego `gender` w `get_anime_context`, dziedziczenie płci przez aliasy dwuczłonowe P0, ochrona `FEMALE_LEXICON_NAMES` — potwierdzone.
2. **`2A.2`** (9.10/2B.2): Filtracja `?`/`!`/Heart/Thought/Thoughts/Voice/Internal/Sign w `normalize_actor_tag`, `COLLECTIVE_LABELS`, `-ny/-na/-ne` bazowo w `is_polish_adjective`, `NUMERAL_PREFIXES` — potwierdzone (z doprecyzowaniem H1).
3. **`2A.3`** (9.10/2B.3): `prev_line_f1`/`prev_line_en` w `pass1_items`, fallback `batch_items[idx-1]`, reset ASR — potwierdzone.
4. **`2A.4`** (9.10/2B.4): `Artefakty` w `pytest.ini norecursedirs`, audyt per-assertion bramek (12/12, 15/15) — potwierdzone.

### 2B — Nowe operacje hotfixu 9.10.1

#### OPERACJA H1 — Zawęzić `-ne` i `-na` w `is_polish_adjective`

**Lokalizacja:** `series_memory.py` — `is_polish_adjective` (linia ~2314).

**Problem:** Imiona żeńskie kończące się na `-ne`, gdzie przed `-ne` występuje samogłoska (np. `Töregene`), są traktowane jako przymiotniki i odmieniane w N jako `Töregeneą`. Test `test_quality_gate_name_declension_vocative_and_micro_lines` oczekuje `Töregene!` (nieodmienne).

**Implementacja:**
1. W `is_polish_adjective` aktualny warunek `w.endswith(("ny", "na", "ne"))` (dla `len(w) >= 5`) rozbij na trzy niezależne przypadki:
   - `w.endswith("ny")` — przymiotnik męski (np. `obronny`) — zachowaj bez zmian.
   - `w.endswith("na")` — przymiotnik żeński (np. `obronna`) — zachowaj, ale wyklucz jeśli `w in FEMALE_LEXICON_NAMES` lub `w in INHERENT_FEMALE_NOUNS` lub `w in POLISH_FEMALE_NAMES` lub `w in UNIVERSAL_FEMALE_NAMES_ON_A`, oraz wymagaj, aby znak przed `na` (`w[-3]`) nie był samogłoską (`{"a", "e", "i", "o", "u", "y", "ó", "ą", "ę"}`).
   - `w.endswith("ne")` — przymiotnik nijaki/niemęskoosobowy (np. `obronne`, `ogólne`) — **wymagaj, aby znak bezpośrednio przed `ne` był spółgłoską**, tzn. `w[-3]` należy do zbioru `{"r", "l", "d", "t", "z", "ł", "s", "c", "b", "p", "w", "m", "n", "k", "g", "h", "f"}`. Jeśli `w[-3]` jest samogłoską (`a`, `e`, `i`, `o`, `u`, `y`, `ö`, `ä`, `ü`), zwróć `False` (nie przymiotnik).
2. Zachowaj wszystkie istniejące wykluczenia (`saki`, `zuki`, `zaki`, `yna`, `ina`, `anka`, `arka`, `anna`, `otta`, `etta`, `white`, lista rzeczowników żeńskich, `KNOWN_HEAD_NOUNS`, `KNOWN_HEAD_NOUN_DECLENSIONS`).

**Kryterium akceptacji:** `Töregene` (`w[-3] == "e"`) → `is_polish_adjective == False` → w N = `Töregene`; `obronny` / `obronne` → `is_polish_adjective == True` → w N = `obronnym`.

---

#### OPERACJA H2 — Propagacja płci z `terminology`/`glossary` do aliasów oraz synchronizacja `"gender"` w `declensions`

**Lokalizacja:** `series_memory.py` — `_sanitize_loaded_bible_in_ram` (po sekcji `0c` propagacji `multi_token_p0`).

**Problem:** Test `test_tenmaku_ep12_holistic_domain_guard` (linia ~6100) wczytuje `SeriesBible("Tenmaku no Jaadugar")` i wymaga: `chulan_decl.get("gender") == "FEMALE"`. W `Tenmaku_no_Jaadugar_bible.json` relacja aliasowa `{"Khulan": "cesarzowa Chulan"}` jest zapisana w `"glossary"` / `"terminology"`, a słownik `declensions["Chulan"]` po regeneracji w 9.10 zawierał wyłącznie klucze przypadków `M..W` bez klucza `"gender": "FEMALE"`.

**Implementacja:**
1. W `_sanitize_loaded_bible_in_ram` po sekcji `0c` dodaj sekcję `0d — terminology & glossary alias propagation`:
   - Przeskanuj połączone słowniki `self.data.get("terminology", {})` **oraz** `self.data.get("glossary", {})`.
   - Dla każdej pary `(key, val_str)`: sprawdź, czy `key` istnieje w `self.data["characters"]` z `gender` w `("FEMALE", "MALE")`, LUB czy `val_str` zaczyna się od jednoznacznego tytułu osobowego określającego płeć (np. `cesarzowa`, `królowa`, `księżniczka` → `FEMALE`; `cesarz`, `król`, `książę` → `MALE`).
   - Jeśli płeć jest ustalona (np. `Khulan` → `FEMALE`, `val_str = "cesarzowa Chulan"`), wyodrębnij z `val_str` tokeny pisane wielką literą, które nie są tytułami pospolitymi (nie należą do `INHERENT_FEMALE_NOUNS`, `INHERENT_MALE_NOUNS`, `COLLECTIVE_LABELS`, ani listy `{"cesarzowa", "cesarz", "królowa", "król", "księżniczka", "książę", "pani", "pan", "córka", "syn", "wielki", "wielka", "mistrz", "mistrzyni", "generał"}`).
   - Dla każdego takiego tokenu antroponimicznego (np. `Chulan`), jeśli była to para z antroponimem `key` w `characters` (lub z jawnym tytułem osobowym `cesarzowa` + pojedyncze imię własne):
     - utwórz lub zaktualizuj wpis w `self.data["characters"][token]` z `gender` i `grammatical_gender` odziedziczonym z `key` (`"FEMALE"` / `"FEMININE"`), `priority: "P0"`, `has_verified_gender: True`, `aliases: list({token, key})`, `entity_category: "ANTHROPONYM"`;
     - wygeneruj dla `token` paradygmat w `self.data["declensions"][token] = generate_polish_name_declension(token, inherited_gender)`.
2. **Bezwarunkowa synchronizacja klucza `"gender"` w `declensions`:**
   - Na końcu `_sanitize_loaded_bible_in_ram` (po wszystkich operacjach na `characters` i `declensions`), dla każdej postaci `c_name, c_info` w `self.data.get("characters", {}).items()`:
     - jeśli `isinstance(c_info, dict)` i `c_info.get("gender") in ("FEMALE", "MALE")`:
       - jeśli `c_name` znajduje się w `self.data.get("declensions", {})` i `isinstance(self.data["declensions"][c_name], dict)`:
         - ustaw `self.data["declensions"][c_name]["gender"] = c_info["gender"]`.

**Kryterium akceptacji:** `Chulan` w `characters` ma `gender: "FEMALE"`, a `declensions["Chulan"]` ma `"M": "Chulan"`, `"B": "Chulan"` oraz `"gender": "FEMALE"` (test `test_tenmaku_ep12_holistic_domain_guard` w linii 6100 przechodzi w 100%).

---

#### OPERACJA H3 — Uniwersalna deklinacja dwuczłonowych i jednoczłonowych antroponimów żeńskich (`gender == "FEMALE"`)

**Lokalizacja:** `series_memory.py` — `generate_polish_name_declension` (linie ~2820-2960).

**Problem:**
- Dwuczłonowe imiona żeńskie z członami niezakończonymi na `-a` (np. pierwszy człon na `-e`, drugi na spółgłoskę) wpadały w męską deklinację `D = "...ego ...a"` (powodując błąd w `test_hyouken_s2_root_cause_anilist_fallback_and_addressee_guard` w linii 14897).
- Jednoczłonowe imiona żeńskie zakończone na spółgłoskę (np. `Carol`, `Claris`, `Chulan`) w niektórych ścieżkach otrzymywały męskie końcówki `-a/-owi/-em`.
- Jednocześnie dwuczłonowe nazwy żeńskie, w których oba człony kończą się na `-a` (np. `Aura Gilotyna` w Teście 52), muszą nadal odmieniać oba człony (`D = "Aury Gilotyny"`).

**Implementacja:**
1. W `generate_polish_name_declension(name: str, gender: str = "UNKNOWN")` dla `is_female == True` (`gender.upper() in ("FEMALE", "FEMININE", "KOBIETA", "DZIEWCZYNA", "DZIEWCZYNKA")`), zanim kod przejdzie do reguł męskich:

   **(A) Dla antroponimów jednoczłonowych (brak spacji w `name`) z `is_female == True`:**
   - Jeśli `name.lower()` nie należy do `KNOWN_HEAD_NOUN_DECLENSIONS` i nie jest przymiotnikiem (`not is_polish_adjective(name)`):
     - Jeśli **nie kończy się na `-a`** (czyli kończy się na spółgłoskę lub samogłoskę `-e`, `-i`, `-o`, `-u`, `-y` — **wliczając w to wszystkie imiona z `FEMALE_LEXICON_NAMES` i `FOREIGN_FEMALE_CONSONANT_NAMES`**; UWAGA: NIE wykluczaj `FEMALE_LEXICON_NAMES`!): zwróć paradygmat całkowicie nieodmienny (`{k: name for k in ("M", "D", "C", "B", "N", "Ms", "W")}`).
     - Jeśli **kończy się na `-a`**: odmieniaj według istniejących w `generate_polish_name_declension` reguł deklinacji żeńskiej na `-a` (z zachowaniem alternacji fonetycznych `-ia/-ya -> -ii/-yi`, `-ka/-ga -> -ce/-dze`, `-ca -> -cy`).

   **(B) Dla antroponimów dwuczłonowych (`len(words) == 2`, `w1, w2 = words`) z `is_female == True`:**
   - Jeśli `w1.lower()` nie jest w `KNOWN_HEAD_NOUN_DECLENSIONS` / `KNOWN_HEAD_NOUNS` i nie jest frazą z `NUMERAL_PREFIXES`:
     - **Człon pierwszy (`w1`):** jeśli `w1.endswith(("a", "A"))`, odmieniaj `w1` żeńsko (rekurencyjnie przez `generate_polish_name_declension(w1, "FEMALE")` dla jednoczłonowego imienia na `-a`); w przeciwnym razie (gdy `w1` kończy się na `-e`, `-i`, `-o`, `-u`, `-y` lub spółgłoskę) pozostaw `w1` **nieodmienne** we wszystkich 7 przypadkach (`d1[c] = w1`).
     - **Człon drugi (`w2`):** jeśli `w2.endswith(("a", "A"))` i `w2.lower()` nie jest nieodmiennym toponimem/rzeczownikiem pospolitym w dopełniaczu, odmieniaj `w2` żeńsko (rekurencyjnie przez `generate_polish_name_declension(w2, "FEMALE")`, dzięki czemu `Aura Gilotyna` daje `D = "Aury Gilotyny"`); w przeciwnym razie (gdy `w2` kończy się na spółgłoskę lub `-e`, `-i`, `-o`, `-u`, `-y`) pozostaw `w2` **nieodmienne** we wszystkich 7 przypadkach (`d2[c] = w2`).
     - Złóż paradygmat jako `{c: f"{d1[c]} {d2[c]}" for c in ("M", "D", "C", "B", "N", "Ms", "W")}`.
2. Zachowaj istniejące reguły dla `gender == "MALE"` i `gender == "UNKNOWN"` oraz dla fraz rzeczownikowych (`KNOWN_HEAD_NOUN_DECLENSIONS`, `system obronny`, `Czterech Jeźdźców`).

**Kryterium akceptacji:**
- Dwuczłonowe żeńskie typu `Imię_na_-e Nazwisko_na_spółgłoskę` → `D == M` (nieodmienne, test linia 14897 PASS).
- Dwuczłonowe żeńskie typu `Imię_na_spółgłoskę Nazwisko_na_-e/spółgłoskę` → `D == M` (nieodmienne).
- Dwuczłonowe żeńskie typu `Imię_na_-a Nazwisko_na_spółgłoskę/-e` → odmieniany tylko pierwszy człon.
- Dwuczłonowe żeńskie typu `Aura Gilotyna` (oba na `-a`) → odmieniane oba człony (`D = "Aury Gilotyny"`, Test 52 PASS).
- Jednoczłonowe żeńskie na spółgłoskę lub `-e` → całkowicie nieodmienne.

---

#### OPERACJA H4 — Synchronizacja `bible.json` z katalogiem `Artefakty/` oraz gwarantowany zapis `save()` po sanityzacji

**Lokalizacja:** `series_memory.py` — `SeriesBible.__init__`, `SeriesBible.load()`, `SeriesBible.save()`; `translator.py` — `translate_file`.

**Problem:** `SeriesBible` zapisywało zmiany tylko w `series_memory/`, a plik `Artefakty/Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` nie był aktualizowany na dysku po `_sanitize_loaded_bible_in_ram()`.

**Implementacja:**
1. W `SeriesBible.__init__` zachowaj dotychczasowe `self.file_path` (kompatybilność z testami `tmp_path` i `:memory:`). Dodaj opcjonalną ścieżkę lustrzaną `self.artefakty_path`:
   - jeśli `self.file_path` wskazuje na rzeczywisty plik w domyślnym katalogu `series_memory/` (tj. `storage_dir` nie został nadpisany przez testowe `tmp_path` ani `db_path != ":memory:"`), wyznacz katalog `repo_root / "Artefakty"`; jeśli katalog ten istnieje i znajduje się w nim plik o tej samej nazwie `self.file_path.name`, ustaw `self.artefakty_path = repo_root / "Artefakty" / self.file_path.name` (w przeciwnym razie `None`).
2. W `SeriesBible.save()`:
   - po zapisaniu `self.file_path`, jeśli `getattr(self, "artefakty_path", None)` nie jest `None` i katalog istnieje, skopiuj zapisany plik do `self.artefakty_path` (`shutil.copy2(self.file_path, self.artefakty_path)`).
3. W `translator.py` (`translate_file`): po wywołaniu `self.series_bible._sanitize_loaded_bible_in_ram()` wywołaj `self.series_bible.save()`.
4. **Obowiązkowa regeneracja pliku na dysku w Etapie 4/6:** uruchom jednorazowo komendę Pythona wczytującą `SeriesBible("Hyouken no Majutsushi ga Sekai wo Suberu S2")`, wykonującą `_sanitize_loaded_bible_in_ram()` i wywołującą `save()`, tak aby zarówno `series_memory/Hyouken..._bible.json`, jak i `Artefakty/Hyouken..._bible.json` zostały fizycznie zaktualizowane na dysku.

**Kryterium akceptacji:** `series_memory/Hyouken..._bible.json` oraz `Artefakty/Hyouken..._bible.json` są identyczne i zawierają stan po pełnej re-sanityzacji 9.10.1.

---

#### OPERACJA H5 — Rozszerzenie `COLLECTIVE_LABELS`, rozpoznawanie pierwszego członu w `FEMALE_LEXICON_NAMES` i regeneracja skażonych `declensions` w `_sanitize_loaded_bible_in_ram`

**Lokalizacja:** `series_memory.py` — `COLLECTIVE_LABELS`, `UNIVERSAL_FEMALE_NAMES_ON_A`, `_sanitize_loaded_bible_in_ram`.

**Problem:** W pliku `Hyouken_..._bible.json` na dysku pozostały:
1. Etykieta zbiorowa `"Animals"`.
2. Nadpisania `"gender": "MALE"` dla dwuczłonowych postaci żeńskich (`"Helena Grady"`, `"Wanda Wykes"`) oraz jednoczłonowych imion żeńskich (`"Lily"`, `"Carla"`, `"Zuina"`), których nie było w `FEMALE_LEXICON_NAMES` lub których klucz sprawdzano wyłącznie w całości, a nie po pierwszym członie.
3. Stare męskie paradygmaty w `declensions` dla postaci żeńskich (np. `Carola`, `Clarisa`, `Wandy Wykesa`) oraz stare paradygmaty haseł glosariusza (`Magówa`, `koda wewnętrzny`, `Wojny ny Dalekima Wschodzie`, `Efekta Motyla`, `Festiwala Hymnów`).

**Implementacja:**
1. Rozszerz `COLLECTIVE_LABELS` o:
   `"animals"`, `"creatures"`, `"people"`, `"humans"`, `"students"`, `"children"`, `"men"`, `"women"`, `"boys"`, `"girls"`, `"soldiers"`, `"guards"`, `"crowd"`, `"group"`, `"zwierzęta"`, `"stwory"`, `"ludzie"`, `"dzieci"`, `"kobiety"`, `"mężczyźni"`, `"chłopcy"`, `"dziewczęta"`, `"żołnierze"`, `"strażnicy"`, `"tłum"`, `"grupa"`.
2. Rozszerz `UNIVERSAL_FEMALE_NAMES_ON_A` / `FEMALE_LEXICON_NAMES` o powszechne zachodnie/japońskie imiona żeńskie: `"lily"`, `"carla"`, `"zuina"`, `"ariane"`, `"lieselotte"`, `"dina"`, `"stella"`, `"rebecca"`, `"lydia"`, `"amelia"`.
3. W `_sanitize_loaded_bible_in_ram`:
   - **(a) Usuwanie nie-antroponimów:** usuń z `characters`, `declensions` i `entity_categories` klucze będące w `COLLECTIVE_LABELS`, pisane od małej litery (jednowyrazowe, np. `pants`), zawierające `?`/`!` lub sufiksy `Heart`/`Thought` (`Carol?`, `ElisaHeart`), a z `declensions` usuń również wszystkie klucze, które występują wyłącznie w `glossary` (lub są tłumaczeniami z `glossary.values()`), a nie są postaciami w `characters` (chyba że klucz ma w `characters` kategorię `ANTHROPONYM`).
   - **(b) Korekta `FEMALE` po pierwszym członie i leksykonie:** dla każdej postaci `k, v` w `characters`: jeśli `k.lower() in FEMALE_LEXICON_NAMES` **LUB pierwszy człon `k.split()[0].lower() in FEMALE_LEXICON_NAMES`** (i `k.split()[0].lower()` nie należy do `CANONICAL_MALE_NAMES_ON_A`), wymuś `v["gender"] = "FEMALE"`, `v["grammatical_gender"] = "FEMININE"` i zaktualizuj opis `"Postać (mężczyzna)"` → `"Postać (kobieta)"`. Następnie uruchom propagację płci z rekordów dwuczłonowych P0 na jednoczłonowe aliasy (dzięki czemu `Wanda Wykes (FEMALE)` → `Wanda (FEMALE)`, `Helena Grady (FEMALE)` → `Helena (FEMALE)`, `Carol Caroline (FEMALE)` → `Carol (FEMALE)`).
   - **(c) Regeneracja paradygmatów `declensions` dla postaci `FEMALE`:** dla każdej postaci `k, v` w `characters` o `v.get("gender") == "FEMALE"`, przelicz na nowo `self.data["declensions"][k] = generate_polish_name_declension(k, "FEMALE")` (i dopisz `"gender": "FEMALE"` zgodnie z H2 pkt 2), aby zastąpić historycznie zatrute formy (`Carola` → `Carol`, `Clarisa` → `Claris`, `Wandy Wykesa` → `Wandy Wykes`).

**Kryterium akceptacji:** Po uruchomieniu `_sanitize_loaded_bible_in_ram()` i `save()` na `Hyouken_..._bible.json`:
- 0 wystąpień: `pants`, `Both`, `All`, `Animals`, `Carol?`, `ElisaHeart`, `Magówa`, `koda wewnętrzny`, `Carola`, `Clarisa`, `Arianego Olgrena`, `Wandy Wykesa`, `Wojny ny Dalekima Wschodzie`;
- 100% postaci żeńskich (w tym `Carol`, `Francoise`, `Olivia`, `Maria`, `Bianca`, `Wanda`, `Waitress`, `Mia`, `Helena Grady`, `Wanda Wykes`, `Lily`, `Carla`) ma `"gender": "FEMALE"`.

---

## SEKCJA 3: REGUŁY PIPELINE'U DANYCH

Wszystkie `R3.1–R3.5` z 9.10 utrzymane. R3.1 uzupełniona o: „po `_sanitize_loaded_bible_in_ram` pipeline wywołuje `series_memory.save()` i synchronizuje plik `bible.json` z katalogiem `Artefakty/`".

---

## SEKCJA 4: KOLEJNOŚĆ WDROŻENIA

1. **ETAP 1:** Phase 0 (P0.1 + P0.2 + P0.3).
2. **ETAP 2:** Wdrożenie H1 + H5 w `series_memory.py`.
3. **ETAP 3:** Wdrożenie H2 + H3 w `series_memory.py`.
4. **ETAP 4:** Wdrożenie H4 w `series_memory.py` i `translator.py` oraz wykonanie komendy re-sanityzacji i zapisu `Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` (i `Tenmaku_no_Jaadugar_bible.json`).
5. **ETAP 5:** Dodanie testów regresyjnych T10.1.1–T10.1.3 w `tests/test_series_memory.py`.
6. **ETAP 6:** Re-run `pytest` (fast: 225/225 PASS) + re-run pełnego pakietu `pytest -m "slow or not slow"` (**378/378 PASS**, w tym wszystkie 3 naprawione testy z `test_system.py`) + re-run 4 bramek CI/CD + wypełnienie `Raport_wdrozenia_9.10.1.md`.

---

## SEKCJA 5: WALIDACJA TESTOWA

### 5A. Wykaz nowych testów T10.1.1–T10.1.3 (marker: unit)

```python
import pytest

# WZORZEC T10.1.1 (Operacja H1) -> tests/test_series_memory.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "name,gender,expected_n",
    [
        ("<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_HISTORYCZNY_1>", "FEMALE", "<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_HISTORYCZNY_1>"),
        ("<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_HISTORYCZNY_2>", "FEMALE", "<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_HISTORYCZNY_2>"),
        ("<RZECZYWISTY_PRZYMIOTNIK_MĘSKI_1>", "MALE", "<RZECZYWISTY_PRZYMIOTNIK_MĘSKI_N_1>"),
    ],
)
def test_female_consonant_historical_names_are_indeclinable(name, gender, expected_n):
    from series_memory import generate_polish_name_declension
    decl = generate_polish_name_declension(name, gender)
    assert decl["N"] == expected_n


# WZORZEC T10.1.2 (Operacja H3) -> tests/test_series_memory.py
@pytest.mark.unit
@pytest.mark.parametrize(
    "name,expected_d",
    [
        ("<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_DWUCZŁONOWY_1>", "<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_DWUCZŁONOWY_1>"),
        ("<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_DWUCZŁONOWY_2>", "<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_DWUCZŁONOWY_2>"),
    ],
)
def test_bipartite_female_name_indeclinable(name, expected_d):
    from series_memory import generate_polish_name_declension
    decl = generate_polish_name_declension(name, "FEMALE")
    assert decl["D"] == expected_d


# WZORZEC T10.1.3 (Operacja H2) -> tests/test_series_memory.py
@pytest.mark.unit
@pytest.mark.parametrize("dict_key", ["terminology", "glossary"])
def test_terminology_alias_propagates_female_gender(dict_key):
    from series_memory import SeriesBible
    bible = SeriesBible(slug="test_9_10_1_terminology", db_path=":memory:")
    bible.data["characters"]["<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_P0_1>"] = {
        "gender": "FEMALE",
        "grammatical_gender": "FEMININE",
        "priority": "P0",
        "has_verified_gender": True,
    }
    bible.data[dict_key] = {
        "<RZECZYWISTY_ANTROPONIM_ŻEŃSKI_P0_1>": "cesarzowa <RZECZYWISTY_CZŁON_ALIASU_1>"
    }
    bible._sanitize_loaded_bible_in_ram()
    assert "<RZECZYWISTY_CZŁON_ALIASU_1>" in bible.data["characters"]
    assert bible.data["characters"]["<RZECZYWISTY_CZŁON_ALIASU_1>"]["gender"] == "FEMALE"
    assert bible.data["declensions"]["<RZECZYWISTY_CZŁON_ALIASU_1>"]["gender"] == "FEMALE"
```

### 5A.3. Warunek ukończenia wdrożenia (definicja pozytywna — punkty (a)–(n))

- **(a)** Wszystkie operacje z Sekcji 2A (`2A.1–2A.4`) utrzymane.
- **(b)** Wszystkie operacje H1–H5 w pełni wdrożone.
- **(c)** 3 nowe testy regresyjne T10.1.1–T10.1.3 zaimplementowane i sparametryzowane (≥ 2 przypadki każdy).
- **(d)** `komenda_fast` (`pytest`): 100% PASS (222 dotychczasowe + nowe warianty T10.1.1–T10.1.3, 0 FAILED, 0 ERROR).
- **(e)** `komenda_full` (`pytest -m "slow or not slow"`): 100% PASS (0 FAILED, 0 ERROR) — wszystkie 3 regresje z 9.10 naprawione: `test_quality_gate_name_declension_vocative_and_micro_lines`, `test_tenmaku_ep12_holistic_domain_guard`, `test_hyouken_s2_root_cause_anilist_fallback_and_addressee_guard` (oraz zachowany PASS dla `test_frieren_manga_canon_aura_gilotyna_and_calque_shield`).
- **(f)** `komenda_network` (`pytest -m "network"`): 100% PASS.
- **(g)** 4 bramki CI/CD (`verify_purity.py`, `verify_ultimate_pipeline.py`, `verify_12_fixes.py`, `audit_diff.ps1`): 100% PASS (VICTORY CONFIRMED).
- **(h)** Walidacja `Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` po re-sanityzacji i zapisie na dysk: 0 wystąpień `pants`, `Both`, `All`, `Animals`, `Carol?`, `ElisaHeart`, `Magówa`, `koda wewnętrzny`, `Carola`, `Clarisa`, `Arianego Olgrena`, `Wandy Wykesa`, `Wojny ny Dalekima Wschodzie`; 12/12 bohaterek z `FEMALE`; w `Tenmaku_no_Jaadugar_bible.json` `Chulan` z `FEMALE` w `characters` i `declensions["Chulan"]["gender"] == "FEMALE"`.
- **(i)** `Artefakty/Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json` zaktualizowany na dysku i identyczny z `series_memory/Hyouken_no_Majutsushi_ga_Sekai_wo_Suberu_S2_bible.json`.
- **(j)** Phase 0 ukończona z tabelami P0.2 i P0.3.
- **(k)** Każdy nowy test T10.1.1–T10.1.3 zweryfikowany pod kątem falsyfikowalności i wolny od D1–D6.
- **(l)** Żaden z 222 testów domyślnych (116 KEEP + 106 z 9.4–9.10) nie został usunięty ani osłabiony.
- **(m)** Katalog `tests/archive/` oraz 3 gałęzie `# DEFENSIVE_FALLBACK` w `avt_linter.py` pozostają nietknięte.
- **(n)** Wszystkie pola `<DO_WYPEŁNIENIA_*>` w `Raport_wdrozenia_9.10.1.md` wypełnione (0 placeholderów).

---

## SEKCJA 6: ZAKAZY (DZIEDZICZONE Z 9.7–9.10 + ROZSZERZENIA 9.10.1)

1. **ZAKAZ 1** (mutacji tekstu poza `AVTLinter` i `EpisodeQualityGate`).
2. **ZAKAZ 2** (podmiany członów antroponimów wieloczłonowych).
3. **ZAKAZ 3** (globalnego dopisywania aliasów tytułowych).
4. **ZAKAZ 4** (Test-Only Wiring i mockowania logiki domenowej).
5. **ZAKAZ 5** (pomijania Phase 0 i walidacji empirycznej).
6. **ZAKAZ 6** (naruszania 222 testów domyślnych i 153 `MARK_SLOW`).
7. **ZAKAZ 7** (modyfikacji `DEFENSIVE_FALLBACK` i `tests/archive/`).
8. **ZAKAZ 8** (pozostawiania placeholderów w raporcie).
9. **ZAKAZ 9** (ręcznej edycji `.ass`/`.json` — Zero-Cosmetic; wyjątek: `Hyouken_..._bible.json` i `Tenmaku_..._bible.json` podlegają automatycznej regeneracji przez `_sanitize_loaded_bible_in_ram()` + `save()`, nie ręcznej edycji).
10. **ZAKAZ 10** (wycieku Zero-Literal — w testach T10.1.1–T10.1.3 używaj wyłącznie przykładów spoza audytowanego odcinka Hyouken).
11. **ZAKAZ 11** (generowania sztucznych `.ass`/`.log`).
12. **ZAKAZ 12** (manipulacji bramkami `verify_*.py` przez osłabianie asercji).
13. **ZAKAZ 13 (nowy):** Nie modyfikuj `test_system.py` — 3 regresje to błędy w `series_memory.py`, nie w testach. Wszystkie 3 testy w `test_system.py` muszą przejść bez jakichkolwiek zmian w ich kodzie.
14. **ZAKAZ 14 (nowy):** Nie generuj paradygmatów w `declensions` dla nie-antroponimów (`Animals`, `Both`, `All`, `pants`, haseł pospolitych z `glossary`).
15. **ZAKAZ 15 (nowy):** Nie zmieniaj `is_polish_adjective` ani `generate_polish_name_declension` w sposób, który złamie przymiotniki męskie na `-ny` (`system obronny` → `systemu obronnego`) lub dwuczłonowe imiona żeńskie na `-a -a` (`Aura Gilotyna` → `Aury Gilotyny`).

---

**Koniec Prompt_9.10.1.md.**