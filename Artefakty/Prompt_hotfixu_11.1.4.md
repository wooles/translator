# PROMPT WDROŻENIOWY — HOTFIX 11.1.4: OBSŁUGA CODE-SWITCHINGU (JA/EN), MOST IDIOLEKTÓW YAKUWARIGO I SEPARACJA SŁOWNA ASR

- **Repozytorium referencyjne:** `https://github.com/wooles/translator` (gałąź `main`)
- **Punkt startowy (`HEAD`):** `7011407cc7b47d2ffb223f402dc8366d40041b7e` (`7011407` — `Standard 11.1.3a Production Certified Baseline`)
- **Baseline ochrony Z16 (Depuracja Legacy 1.0):** `d31096945a977d6a179891d87dcfd2a05c0c5bca` (`d310969`)
- **Podstawa architektoniczna:** `Artefakty/Raport_audytu_operacyjnego_2026-11-11.md` (Sekcje 3–8)
- **Docelowy standard po wdrożeniu:** `Standard 11.1.4 (Sociolinguistic & Code-Switching Certified Baseline)`

---

## 0. ROLA INŻYNIERA I CEL WDROŻENIA

Jesteś Głównym Inżynierem Systemowym AVT odpowiedzialnym za wdrożenie **Hotfixu 11.1.4** w repozytorium `https://github.com/wooles/translator`.

Audyt operacyjny przebiegu `<SERIA>` `<ODCINEK>` (`Artefakty/Raport_audytu_operacyjnego_2026-11-11.md`) potwierdził stuprocentową skuteczność poprawek `11.1.3 / 11.1.3a` w zakresie fleksji płci i higieny międzyzdaniowej, a jednocześnie zdiagnozował sześć luk integracyjnych w obsłudze zjawisk socjolingwistycznych (**code-switching JA/EN** oraz **gwara / rejestr *Yakuwarigo***):

1. **P1-1 (`whisper_disambiguator.py` + `rules.py`):** Detektor `WhisperDisambiguator.detect_batch_discourse_categories` wyzwala fałszywie `"DIALECT_JP"` na niezakotwiczonych podciągach `"べ"` i `"おら"` w zwykłych słowach (`述べた`, `比べれば`, `全て`, `直らない`), natomiast pomija rzeczywiste wykładniki *Yakuwarigo* (`-ある [-aru]`, `-やる [-yaru]`, `-ですわ [-desu wa]`, `-ますわ [-masu wa]`, `-ですこと [-desu koto]`, `-ありませんこと [-arimasen koto]`, `-っす [-ssu]`, `-なの [-nano]`) oraz nie posiada kategorii `"CODE_SWITCH_EN"` dla celowych wtrąceń angielskich w japońskim audio seiyū (np. `リフレクトします [rifurekuto shimasu]`, `オーケーオッケ [ookeeokke]`, `テンション上げ [tenshon age]`).
2. **P1-2 (`profiler.py` + `translator.py`):** Funkcja `format_lean_episode_brief` pomija pola `speech_style_pl` oraz `idiolect_matrix` wygenerowane przez `EpisodeProfiler` w `CharacterDossier`, gdy pole `dialect_category` ma wartość `"brak"`, a lista `batch_items_for_rules` w `translator.py` nie przekazuje kluczy `speech_style_pl` ani `notes` do `get_focused_rules_for_batch`.
3. **P1-3 (`series_memory.py`):** Schemat `CharacterRecord` w `SeriesBible` nie przechowuje pola `speech_register` między odcinkami oraz nie aktualizuje płci wyodrębnionej z heurystyki relacyjnej, gdy `EpisodeProfile` dostarcza zweryfikowaną płeć P0.
4. **P2-1 (`whisper_engine.py` + `translator.py`):** Metoda `transcribe_batch_scene` działa bez `word_timestamps=True`, przypisując wielozdaniowe segmenty VAD warunkiem `(overlap_end - overlap_start) > 80` do sąsiednich kwestii, a pętla deduplikacji w `translator.py` nie odcina sklejonego prefiksu z poprzedniej linii.
5. **P2-2 (`translator.py` + `verifier.py`):** Funkcja `detect_japanese_pragmatic_register` nie rozpoznaje rejestru `-aru/-yaru`, `-desu koto`, `-nano` ani code-switchingu JA+EN, jej wynik nie trafia do wektora `[TELEMETRIA: ...]`, a Faza 2 potrafi zastąpić dystyngowany rejestr *ojōsama* młodzieżowym slangiem gamingowym (`dropu / farta`).
6. **P3-1 (`rules.py` + `avt_linter.py` + `translator.py`):** Brak korekty ortograficznej dla literówki `Kope lat` -> `Kopę lat`, brak ochrony ksywek z sufiksem `-cchi` oraz obcinanie prefiksu `@` w nazwach postaci.

---

## 1. ZASADY NIENARUSZALNE I INWARIANTY (Z1–Z4, Z16)

1. **Z1 (Zero-Literal / Zakaz Hardcodingu Fabularnego):** W kodzie produkcyjnym (`*.py`) oraz w dokumentacji i komentarzach stosuj wyłącznie uogólnione reguły morfologiczne, fonotaktyczne i strukturalne. W testach używaj wyłącznie neutralnych identyfikatorów syntetycznych (`SpeakerAlpha`, `SpeakerBeta`, `SpeakerChi`, `@HandleName`, `Val`).
2. **Z2 (Pure Positive Domain):** Wszystkie instrukcje promptowe, opisy reguł w `rules.py`, `profiler.py`, `translator.py`, `verifier.py` oraz komentarze i docstringi formułuj wyłącznie w języku deklaratywno-pozytywnym (opisującym pożądany stan docelowy i warianty kanoniczne).
3. **Z3 (Zero-Regression):** Wszystkie dotychczasowe testy w `tests/` oraz `test_system.py` muszą przechodzić w 100% na zielono razem z nowymi testami regresyjnymi.
4. **Z16 (Ochrona Depuracji Legacy 1.0 i `Z16-amendment`):** Pliki `profiler.py`, `translator.py`, `verifier.py`, `series_memory.py`, `avt_linter.py` i `rules.py` podlegają ochronie rozmiarowej względem commita `d31096945a977d6a179891d87dcfd2a05c0c5bca`. Przed modyfikacją plików z listy Z16 uzyskaj potwierdzenie `Z16-amendment` od operatora i utrzymaj minimalny, chirurgiczny przyrost linii kodu.

---

## 2. SPECYFIKACJA TECHNICZNA ZADAŃ WDROŻENIOWYCH

### ZADANIE 1 (P1-1): Precyzyjna detekcja `DIALECT_JP` (*Yakuwarigo*) oraz nowa kategoria `CODE_SWITCH_EN` w `whisper_disambiguator.py` i `rules.py`

#### 1.1. Lokalizacja
- `whisper_disambiguator.py:667-708` (`WhisperDisambiguator.detect_batch_discourse_categories`)
- `rules.py:2560-2591` (`get_focused_rules_for_batch` — sekcja `DYN_1`)

#### 1.2. Mechanizm w `whisper_disambiguator.py`
1. W metodzie `detect_batch_discourse_categories(cls, combined_en: str, combined_jp: str) -> Set[str]` zaktualizuj sekcję `1. DIALECT_JP`:
   - Usuń niezakotwiczone pojedyncze znaki `"べ"` oraz `"おら"` z listy podciągów `jp_dialect_tokens` sprawdzanej operatorem `in`, które powodowały fałszywe trafienia wewnątrz słów `述べた`, `比べれば`, `全て`, `直らない`.
   - Zakotwicz wykładniki gwarowe i *Yakuwarigo* na granicach morfemów lub końcach fraz:
     - dla dialektów regionalnych i partykuły końcowej `べ` / `だべ` / `っぺ`:

           jp_dialect_pat = re.compile(
               r"\b(?:ya|yan|yade|yaro|nen|seya|akan|honma|dappe|dabe|ora|washi|atai|wai|wagahai|jaken|koraa|suitoo|nankurunaisa|haisai|namara|shibareru|"
               r"tanonderu\s*aru|hazu\s*aru|dake\s*aru|koto\s*aru|nani\s*yaru\s*ka|ii\s*yaru|ikena\s*yaru|nai\s*yaru\s*ne|naoranai\s*yaru|"
               r"desu\s*wa|masu\s*wa|desu\s*koto|arimasen\s*koto|masu\s*no\s*yo|"
               r"naissu|dessu|ssu\s*kedo|ssu\s*ne|sorotta\s*nano|kuretamae)\b",
               re.IGNORECASE
           )

     - dla tokenów w zapisie japońskim (Kana/Kanji) wydziel bezpieczną listę wieloznakowych sufiksów i wyrażeń:

           jp_dialect_tokens = [
               "だべ", "っぺ", "じゃけん", "やん", "やで", "やろ", "ねん", "せや", "あかん", "ほんま",
               "わし", "あたい", "わい", "吾輩",
               "頼んでるある", "はずある", "だけある", "ことある", "何やるか", "いいやる", "いけなやる", "ないやるね", "なおらないやる",
               "ですわ", "ますわ", "ですこと", "ありませんこと", "ますのよ",
               "ないっす", "っすけど", "っすね", "っすよ", "ったなの", "だなの", "くれたまえ"
           ]
           jp_anchored_dialect_re = re.compile(
               r"(?:(?:いく|すっ|やる|だ)べ(?:[！？!?。、\s]|$)|(?:^|[、。\s])おら(?:は|が|の|に|を|も|たち|っち)|"
               r"(?:てる|でる|はず|だけ|こと|いい|ない|な)ある(?:よ|ね|か|な)?(?:[！？!?。、\s]|$)|"
               r"(?:いい|ない|な|何)やる(?:か|ね|よ)?(?:[！？!?。、\s]|$))"
           )

   - Jeśli `jp_dialect_pat.search(jp_lower)` lub `jp_dialect_pat.search(en_lower)` lub `any(tok in jp_lower for tok in jp_dialect_tokens)` lub `jp_anchored_dialect_re.search(jp_lower)` lub `character_suffix_pat.search(full_text)` jest spełnione, dodaj `"DIALECT_JP"` do `categories`.
2. Dodaj sekcję `10. CODE_SWITCH_EN (Wtrącenia angielskie i hybrydy katakanowe w japońskim strumieniu mowy)`:
   - Wykrywaj hybrydowe konstrukcje japońsko-angielskie w `jp_lower`, w których postać wplata w japońską strukturę zdaniową angielskie czasowniki/zwroty w katakanie lub rōmaji:

         jp_codeswitch_pat = re.compile(
             r"(?:[ァ-ヶー]{4,}(?:します|した|して|する)|"
             r"オーケーオッケ|オッケーオッケ|テンション上げ|"
             r"\b(?:rifurekuto\s*shimasu|tenshon\s*age|ookee\s*okkee|ookeeokke)\b)",
             re.IGNORECASE
         )

   - Wyklucz z `jp_codeswitch_pat` standardowe japońskie rzeczowniki systemowe (`クリアします`, `装備します`, `ガードします`, `チェックします`, `スタートします`), aby kategoria `"CODE_SWITCH_EN"` zapalała się wyłącznie dla ekspresyjnego/komicznego code-switchingu w dialogu postaci.

#### 1.3. Mechanizm w `rules.py`
- W `rules.py:2574-2590` (`DYN_1`) uwzględnij `has_code_switch = "CODE_SWITCH_EN" in jp_categories`:
  - Włącz `has_code_switch` do warunku aktywacji `DYN_1`.
  - W pozytywnym opisie `DYN_1` dodaj na końcu zdanie:
    `"Gdy w japońskim audio postać celowo wplata pojedyncze angielskie słowa lub hybrydowe zwroty katakanowe dla efektu humorystycznego bądź charakterologicznego, zachowaj ten rejestr i ładunek komiczny w polskiej ripoście."`

---

### ZADANIE 2 (P1-2): Pełny most idiolektów `CharacterDossier` -> `format_lean_episode_brief` (`profiler.py`) oraz przekazywanie cech rejestru do `get_focused_rules_for_batch` (`translator.py`)

#### 2.1. Lokalizacja
- `profiler.py:121-125` (`RE_JP_DIALECT_MARKERS`) oraz `profiler.py:285-327` (`format_lean_episode_brief`)
- `translator.py:3917-3949` (`_process_single_batch`)

#### 2.2. Mechanizm w `profiler.py`
1. Rozszerz `RE_JP_DIALECT_MARKERS` (`profiler.py:121-124`) o markery *Yakuwarigo* (`desu wa`, `masu wa`, `desu koto`, `arimasen koto`, `tanonderu aru`, `hazu aru`, `dake aru`, `ii yaru`, `nani yaru ka`, `naissu`, `sorotta nano`, `kuretamae` oraz ich odpowiedniki w zapisie japońskim).
2. W funkcji `format_lean_episode_brief` (`profiler.py:299-315`) dla każdego rekordu `cd` w `dossiers`:
   - Pobierz `speech_style = _get(cd, "speech_style_pl", "")` oraz `idiolect = _get(cd, "idiolect_matrix", "")`.
   - Jeśli `speech_style` lub `idiolect` są niepuste, dołącz bezpośrednio pod linijką postaci skondensowany wiersz stylu (do 180 znaków):

         style_parts = [str(p).strip() for p in (speech_style, idiolect) if p and str(p).strip() and str(p).strip().lower() != "brak"]
         if style_parts:
             combined_style = " | ".join(style_parts)
             if len(combined_style) > 180:
                 combined_style = combined_style[:177].rstrip() + "..."
             lines.append(f"    Styl i idiolekt: {combined_style}")

   - Zachowaj dotychczasowy wiersz `"    Rejestr: wyrazista gwara / stylizacja środowiskowa"` dla kompatybilności wstecznej z istniejącym testem `test_t10_1_1_p2a_dialect_registry_guidance_in_episode_brief` w `tests/test_profiler.py:303`.

#### 2.3. Mechanizm w `translator.py`
- W `_process_single_batch` (`translator.py:3917-3948`) podczas tworzenia słowników w `batch_items_for_rules`:
  - Wyznacz `spk_style_pl` z `episode_profile.character_dossiers` (dopasowując po `ev.name`).
  - Wyznacz `line_pragmatic_reg = detect_japanese_pragmatic_register(audio_jp_val, clean_txt)` (gdy linia nie jest napisem ekranowym).
  - Przekaż `"speech_style_pl": spk_style_pl` oraz `"notes": line_pragmatic_reg or ""` do słownika w `batch_items_for_rules`, aktywując warunek `has_dialect_indicator` w `rules.py:2577-2581`.

---

### ZADANIE 3 (P1-3): Pole `speech_register` w `CharacterRecord` (`SeriesBible`) oraz priorytet zweryfikowanej płci P0 nad heurystyką relacyjną (`series_memory.py`)

#### 3.1. Lokalizacja
- `series_memory.py:4680-4785` (`register_character`, `sync_verified_profile_entity`)
- `series_memory.py:5120-5210` (`format_scoped_for_batch`)

#### 3.2. Mechanizm w `series_memory.py`
1. W metodach `register_character` oraz `sync_verified_profile_entity` dodaj obsługę opcjonalnego parametru `speech_register: Optional[str] = None` (lub odczyt z `kwargs.get("speech_style_pl")`):
   - Jeśli `speech_register` jest niepusty, zapisz go w słowniku rekordu postaci pod kluczem `"speech_register"`.
2. W `sync_verified_profile_entity`:
   - Jeżeli istniejący rekord postaci w `self.data["characters"]` ma w opisie `"wyodrębniono z relacji serii"` (płeć nadana wcześniej przez heurystykę relacyjną), a nowe wywołanie z `EpisodeProfiler` / `AniList` przekazuje jawnie zweryfikowaną płeć `gender in ("FEMALE", "MALE")` z `has_verified_gender=True`, zaktualizuj `gender`, `grammatical_gender`, `description` oraz przelicz paradygmat w `self.data["declensions"][clean_name]`, eliminując rozbieżność płci między starą relacją a aktualnym profilem P0.
3. W `format_scoped_for_batch`:
   - Jeśli aktywna postać posiada w rekordzie niepuste pole `"speech_register"`, dołącz je w nawiasie po opisie roli (`[Rejestr: {speech_register}]`).

---

### ZADANIE 4 (P2-1): Separacja słowna (`word_timestamps=True`) w `whisper_engine.py` oraz odcinanie sklejonych prefiksów ASR w `translator.py`

#### 4.1. Lokalizacja
- `whisper_engine.py:231-271` (`JapaneseWhisperEngine.transcribe_batch_scene`)
- `translator.py:3840-3882` (pętla sanityzacji i deduplikacji ASR w Kroku 4)

#### 4.2. Mechanizm w `whisper_engine.py`
1. W `transcribe_batch_scene` dodaj `"word_timestamps": True` do `transcribe_kwargs`.
2. Podczas przypisywania wyników do zdarzeń `(b_id, ev)`:
   - Jeśli segment `seg` posiada niepustą listę `getattr(seg, "words", None)`:
     Dla każdego słowa `w` wyznacz `w_start_abs = batch_start_ms + int(w.start * 1000)`, `w_end_abs = batch_start_ms + int(w.end * 1000)` oraz środek `w_mid_abs = (w_start_abs + w_end_abs) // 2`. Dołącz `w.word` do `result[b_id]`, gdy `(ev.start - 120) <= w_mid_abs <= (ev.end + 120)` lub gdy przekrój czasowy słowa z `[ev.start, ev.end]` przekracza `50%` czasu trwania słowa.
   - Jeśli `seg.words` jest puste (fallback segmentowy):
     Wymagaj, aby `overlap_dur = overlap_end - overlap_start > 80` **ORAZ** (`overlap_dur >= 0.25 * max(1, ev.end - ev.start)` lub `overlap_dur >= 0.35 * max(1, seg_end_abs - seg_start_abs)`), co blokuje rozlewanie wielozdaniowych segmentów z sąsiednich linii.

#### 4.3. Mechanizm w `translator.py`
- W pętli deduplikacji ASR (`translator.py:3859-3881`) przechowuj surowy japoński tekst poprzedniej kwestii `prev_raw_jp_kanji`. Jeżeli bieżący tekst `raw_jp_kanji` zaczyna się dokładnie od `prev_raw_jp_kanji` (`len(prev_raw_jp_kanji) >= 4` i `len(raw_jp_kanji) > len(prev_raw_jp_kanji)`), odetnij powtórzony prefiks z początku bieżącej transkrypcji przed konwersją rōmaji.

---

### ZADANIE 5 (P2-2): Rozszerzenie `detect_japanese_pragmatic_register` o *Yakuwarigo* i `CODE_SWITCH_EN` oraz ekspozycja w `[TELEMETRIA: ...]` (`translator.py` + `verifier.py`)

#### 5.1. Lokalizacja
- `translator.py:953-1020` (`detect_japanese_pragmatic_register`)
- `translator.py:4251-4320` (`format_dry_telemetry_tag` i przypięcie rejestru)
- `verifier.py:790-810` (`_prepare_verifier_prompt`)

#### 5.2. Mechanizm
1. W `detect_japanese_pragmatic_register` (`translator.py:970-1020`):
   - W punkcie `2. Aristocratic / Ojou-sama` dodaj wykrywanie `"ますわ"`, `"ですこと"`, `"ありませんこと"`, `"ますのよ"`, `"masu wa"`, `"desu koto"`, `"arimasen koto"`.
   - W punkcie `5. Rejestr dziewczęcy` dodaj wykrywanie końcówki `"-nano"` (`"ったなの"`, `"だなの"`, `"sorotta nano"`).
   - Dodaj punkt `15. Rejestr stylizowany (-aru / -yaru)`: wykrywający końcówki `-aru / -yaru` (`"頼んでるある"`, `"はずある"`, `"だけある"`, `"ことある"`, `"何やるか"`, `"いいやる"`, `"いけなやる"`, `"ないやるね"`, `"なおらないやる"`) i zwracający:
     `"Stylizowany rejestr wojowniczki (-aru/-yaru: wyrazista, cięta, potoczysta składnia indywidualna)"`.
   - Dodaj punkt `16. Code-switching JA+EN`: wykrywający celowe wtrącenia angielskie w strukturze japońskiej (`"リフレクトします"`, `"rifurekuto shimasu"`, `"オーケーオッケ"`, `"テンション上げ"`) i zwracający:
     `"Code-switching JA+EN (celowe wtrącenie angielskie w wypowiedzi japońskiej – zachowaj zabarwienie komiczne/stylistyczne)"`.
2. W `translator.py:4318` po wyznaczeniu `pragmatic_reg = detect_japanese_pragmatic_register(audio_jp_str, clean_en)`:
   - Jeśli `pragmatic_reg` jest niepuste, dołącz skrócony znacznik `| Rejestr: {pragmatic_reg.split('(')[0].strip()}` wewnątrz `line_dry_telemetry` (tak aby był widoczny zarówno dla Fazy 2, jak i w logu `EpisodeFlightRecorder`).
3. W `verifier.py:805-809` rozszerz instrukcję ochrony rejestru: gdy mówca posługuje się rejestrem `Arystokratyczny / Ojou-sama`, terminy ekwipunku i losowości wyrażaj polszczyzną literacką/dystyngowaną (`ekwipunek`, `rynsztunek`, `szczęście`), zachowując czystość wysokiego rejestru postaci.

---

### ZADANIE 6 (P3-1): Higiena ortograficzna (`Kopę lat!`), ochrona ksywek `-cchi` oraz prefiksu `@` (`rules.py`, `avt_linter.py`, `translator.py`)

#### 6.1. Lokalizacja
- `rules.py:1654-1666` (`FILAR CLXIV`) oraz `rules.py:1745-1748` (`FILAR CLXIX`)
- `avt_linter.py:700-750` (tablica deterministycznych korekt ortograficznych)
- `translator.py` (`detect_event_visual_type` / formatowanie nazwy własnej z prefiksem `@`)

#### 6.2. Mechanizm
1. W `avt_linter.py` (oraz na liście w `rules.py:1654-1666`) dodaj deterministyczną korektę ortograficzną:
   - `(r"\bKope\s+lat\b", "Kopę lat", "Filar CLXIV - Ortografia (Kopę lat)")`
   - `(r"\bkope\s+lat\b", "kopę lat", "Filar CLXIV - Ortografia (kopę lat)")`
2. W `rules.py:1745-1748` (`FILAR CLXIX`) doprecyzuj pozytywnie, że zdrobniałe ksywki z sufiksem `-cchi` używane przez postacie rówieśnicze w dialogu zachowują swoją formę z `-cchi` zgodnie z brzmieniem w audio JP i skrypcie EN.
3. W `translator.py` upewnij się, że pseudonim postaci rozpoczynający się od znaku `@` (zdefiniowany w `SeriesBible` / `EpisodeProfile`) zachowuje prefiks `@` przy normalizacji wielkości liter (`clean_display_text`) i w krótkich zawołaniach dialogowych w stylu `Default` bez tagów geometrycznych ASS jest klasyfikowany jako `is_sign=False`.

---

## 3. WYMAGANE NOWE TESTY REGRESYJNE

Dodaj w odpowiednich plikach testowych następujące 5 testów jednostkowych (pokrywających wszystkie luki wykazane w Sekcji 7 raportu audytu):

1. **`tests/test_discourse_and_translator.py` — `test_whisper_disambiguator_no_false_positive_dialect_on_common_verbs`:**
   - Wejście: `combined_en = "Everything is fine compared to before, isn't it fixed yet?"`, `combined_jp = "客観的事実を述べたまでのこと これに比べれば 全て私のものにしたい まだなおらない"`.
   - Asercja: `"DIALECT_JP" not in WhisperDisambiguator.detect_batch_discourse_categories(combined_en, combined_jp)`.
2. **`tests/test_discourse_and_translator.py` — `test_whisper_disambiguator_detects_yakuwarigo_aru_yaru_desuwa_ssu_nano`:**
   - Wejście: trzy próbki japońskie: (a) `"みんなに頼んでるある 何か事情があるはずあるよ 私はそれでいいやる 何やるか"`, (b) `"ありがたいですわね 頼りなさげな武器ですこと"`, (c) `"明かりは必要ないっすけど 全員揃ったなの"`.
   - Asercje: dla każdej próbki `"DIALECT_JP" in WhisperDisambiguator.detect_batch_discourse_categories("", sample)` oraz `"FILAR XIII" in get_focused_rules_for_batch([{"en": "Test", "audio_jp": sample}])`.
3. **`tests/test_translator.py` — `test_code_switching_detection_and_prompt_guidance`:**
   - Wejście: `en_text = "Right back at ya."`, `jp_audio = "その言葉リフレクトします [sono kotoba rifurekuto shimasu]"`.
   - Asercje: `"CODE_SWITCH_EN" in WhisperDisambiguator.detect_batch_discourse_categories(en_text, jp_audio)` oraz `detect_japanese_pragmatic_register(jp_audio, en_text)` zwraca opis zawierający `"Code-switching"`.
4. **`tests/test_profiler.py` — `test_format_lean_episode_brief_includes_character_speech_style_and_idiolect`:**
   - Wejście: `EpisodeProfile` z `CharacterDossier(name="SpeakerChi", gender="FEMALE", age_and_role="Wojowniczka", speech_style_pl="Ekspresyjny rejestr z teatralnymi powiedzeniami", dialect_category="brak", idiolect_matrix="Okrzyki bojowe, dynamiczne zwroty")`.
   - Asercje: `"Ekspresyjny rejestr" in format_lean_episode_brief(profile)` oraz `"Okrzyki bojowe" in format_lean_episode_brief(profile)`.
5. **`tests/test_series_memory.py` — `test_series_bible_character_record_persists_speech_register`:**
   - Wejście: `bible.sync_verified_profile_entity(name="SpeakerAlpha", gender="FEMALE", speech_register="Chłodny, arystokratyczny rejestr wyższościowy")` oraz `bible.format_scoped_for_batch(batch_text="SpeakerAlpha", active_speakers={"SpeakerAlpha"})`.
   - Asercje: `bible.data["characters"]["SpeakerAlpha"].get("speech_register") == "Chłodny, arystokratyczny rejestr wyższościowy"` oraz `"arystokratyczny rejestr" in scoped_str`.

---

## 4. PROCEDURA WERYFIKACJI I WARUNKI UKOŃCZENIA WDROŻENIA

1. Zweryfikuj przed startem `HEAD` repozytorium (`7011407cc7b47d2ffb223f402dc8366d40041b7e`) i poproś operatora o autoryzację `Z16-amendment` dla modyfikowanych plików z listy chronionej Z16.
2. Wdróż Zadania 1–6 oraz 5 nowych testów regresyjnych z zachowaniem `Z1 Zero-Literal` i `Z2 Pure Positive Domain`.
3. Uruchom celowane testy jednostkowe dla zmodyfikowanych modułów (a za zgodą operatora pełny przebieg `pytest`), potwierdzając wynik `0 failed`.
4. Wykonaj skan czystości `Z1` (brak nazw własnych z anime w plikach `.py`) oraz `Z2` (brak słów negatywnych w promptach i docstringach).
5. Zapisz raport wdrożenia w `Artefakty/Raport_wdrozenia_11.1.4.md` (UTF-8 bez BOM) i zaktualizuj `PROJECT_MEMORY.md`.