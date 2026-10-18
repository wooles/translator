# 🏛️ PEŁNY TECHNICZNY RAPORT POTOKU AVT (STANDARD 8.0 / 9.0)
**Kompletna dokumentacja inżynieryjna architektury, przepływu danych i cyklu życia tłumaczenia multimodalnego**

---

## CZĘŚĆ I: ARCHITEKTURA NADRZĘDNA I PUNKT WEJŚCIA (ENTRYPOINT & LIFECYCLE)

### 1. Inicjalizacja Procesu i CLI (`main.py` -> `translator.py`)

#### A. Punkt startowy CLI (`main.py:main()`)
Proces uruchamiania potoku translacji rozpoczyna się od sparsowania argumentów wiersza poleceń przez moduł `main.py` za pomocą biblioteki `argparse.ArgumentParser`. Parser przyjmuje następujący kompletny zestaw parametrów:
- `input` (`str`): Ścieżka do pojedynczego pliku wejściowego (`.ass`, `.srt`, `.mkv`, `.mp4`) lub katalogu zawierającego pliki wideo/napisy.
- `--video` (`Optional[str]`, domyślnie `None`): Jawna ścieżka do skorelowanego pliku wideo.
- `--subs` (`Optional[str]`, domyślnie `None`): Jawna ścieżka do zewnętrznego pliku napisów.
- `--track` (`int`, domyślnie `0`): Indeks ścieżki napisów do ekstrakcji z kontenera MKV/MP4.
- `--model` (`Optional[str]`, domyślnie `None`): Identyfikator modelu LLM Fazy 1 (np. `gemini-2.5-pro`, `gemini-2.5-flash`).
- `--model-phase2` (`Optional[str]`, domyślnie `None`): Identyfikator modelu LLM Fazy 2 (Verifier / Script Doctor).
- `--profile` (`str`, wartości: `standard`, `studio`, `pro`, `master`, `ultra`, `cinema`, domyślnie `standard`): Profil jakościowy definiujący domyślny dobór modeli i budżetów myślenia.
- `--no-whisper` (`bool`, flaga `action="store_true"`): Wyłączenie japońskiej transkrypcji ASR (Whisper).
- `--whisper-model` (`str`, domyślnie `large-v3`): Rozmiar modelu Faster-Whisper.
- `--batch-size` (`int`, domyślnie `18`): Bazowy rozmiar paczki dialogowej podziału adaptacyjnego.
- `--no-verify` (`bool`, flaga `action="store_true"`): Pominięcie weryfikacji Fazy 2 (`DialogueVerifier`).
- `--honorifics` / `--no-honorifics`: Wymuszenie zachowania lub spolszczenia japońskich przyrostków honoryfikatywnych (`-san`, `-kun`, `-chan`, `-senpai`).
- `--play` (`bool`, flaga `action="store_true"`): Automatyczne odtworzenie pliku w odtwarzaczu MPV po zakończeniu translacji.
- `--output` (`Optional[str]`, domyślnie `None`): Niestandardowa ścieżka zapisu gotowego pliku napisów.

#### B. Mapowanie profili jakościowych i resolwer modeli (`model_resolver.py`)
W przypadku braku jawnego wskazania modeli w CLI, funkcja `resolve_best_models(profile)` dobiera pary modeli Fazy 1 i Fazy 2:
- Profil `standard`: Faza 1 = `gemini-2.5-flash`, Faza 2 = `gemini-2.5-flash`.
- Profil `studio`: Faza 1 = `gemini-2.5-flash`, Faza 2 = `gemini-2.5-pro`.
- Profile `pro` / `master`: Faza 1 = `gemini-2.5-pro`, Faza 2 = `gemini-2.5-pro`.
- Profile `ultra` / `cinema`: Faza 1 = `gemini-2.5-pro` (z maksymalnym budżetem CoT), Faza 2 = `gemini-2.5-pro` (pełny audyt reżyserski).
Przed zatwierdzeniem modeli funkcja `probe_all_models_health()` testuje dostępność i opóźnienia endpointów Google Gemini API, odrzucając modele zablokowane lub przeciążone.

#### C. Asynchroniczna kolejka wsadowa i wątek prefetchera (`preload_executor`)
Gdy w parametrze `input` przekazano katalog lub listę plików, funkcja `collect_input_files()` sortuje je w porządku naturalnym (`natural_sort_key`). Następnie uruchamiany jest dedykowany wątek tła `ThreadPoolExecutor(max_workers=1)` (`preload_executor`), który podczas tłumaczenia odcinka $N$ realizuje ekstrakcję audio i transkrypcję Whisper dla odcinka $N+1$, skracając czas bezczynności procesora do 0 sekund.

#### D. Inicjalizacja instancji `MultimodalTranslator` (`translator.py:__init__`)
Klasa `MultimodalTranslator` stanowi główny rdzeń koordynujący. W konstruktorze inicjalizuje swój stan wewnętrzny:
- `self.model`: Ciąg znaków identyfikujący model Fazy 1.
- `self.model_phase2`: Ciąg znaków identyfikujący model Fazy 2.
- `self.api_keys`: Lista kluczy API pobrana ze zmiennych środowiskowych `GEMINI_API_KEY`, `GEMINI_API_KEYS` lub pliku `.env`.
- `self.client_pool`: Obiekt `ClientPool` zarządzający rotacją instancji `genai.Client` z automatycznym przełączaniem po napotkaniu błędu `429 ResourceExhausted`.
- `self.context_cache`: Obiekt `ContextCacheManager` odpowiadający za tworzenie i ponowne wykorzystanie keszu kontekstu Gemini (`google.genai.types.CachedContent`), co redukuje koszt tokenów wejściowych o 90%.
- `self.profiler`: Obiekt `EpisodeProfiler` realizujący analizę wstępną odcinka.
- `self.verifier`: Obiekt `DialogueVerifier` realizujący redakcję Fazy 2.
- `self.linter`: Obiekt `AVTLinter` wykonujący deterministyczną korektę morfosyntaktyczną.
- `self.quality_gate`: Klasa `EpisodeQualityGate` audytująca metryki techniczne planszy w skali całego odcinka.
- `self.character_registry`: Słownik `Dict[str, str]` w pamięci RAM mapujący znormalizowane miana postaci na ich płeć i rolę.
- `self.whisper_engine`: Obiekt `JapaneseWhisperEngine` ładujący model Faster-Whisper z akceleracją CUDA (lub CPU fallback).
- `self.style_matrix`: Obiekt `StyleMatrixEngine` klasyfikujący style wizualne ASS.

---

### 2. Ingestia Pliku Napisów i Parsowanie (`pysubs2`)

#### A. Wczytanie pliku i dekodowanie odporne (`avt_linter.py:load_subtitle_file_resilient`)
Wczytanie pliku napisów odbywa się za pośrednictwem funkcji `load_subtitle_file_resilient(subs_path)`. Funkcja testuje sekwencyjnie kodowania: `utf-8-sig`, `utf-8`, `cp1250`, `iso-8859-2` oraz `shift_jis`. Zwracany jest obiekt `pysubs2.SSAFile`, którego struktura wewnętrzna zawiera listę zdarzeń `SSAFile.events` złożoną z obiektów `pysubs2.SSAEvent`.

Każdy obiekt `pysubs2.SSAEvent` posiada następujące fizyczne atrybuty:
- `start` (`int`): Czas początku wyświetlania w milisekundach.
- `end` (`int`): Czas końca wyświetlania w milisekundach.
- `style` (`str`): Nazwa przypisanego stylu ASS (np. `Default`, `Italics`, `Top`, `Sign`, `Flashback`).
- `name` (`str`): Etykieta aktora / mówcy (np. `Kowalski (M)`, `Heroine`, `Narrator`).
- `text` (`str`): Surowy tekst kwestii zawierający znaczniki formatowania ASS (np. `{\i1}Tekst{\i0}`, `\N`, `{\pos(960,540)}`).
- `effect` (`str`): Dodatkowe efekty ASS (np. `karaoke`, `banner`).
- `margin_l`, `margin_r`, `margin_v` (`int`): Niestandardowe marginesy geometrii planszy.

#### B. Klasyfikacja semantyczna i geometryczna linii (`detect_event_visual_type`)
Każde zdarzenie przechodzi przez funkcję `detect_event_visual_type(event, ts_prefix, style_report)` w `translator.py`, która zwraca słownik `Dict[str, Any]` o strukturze:
- `is_sign` (`bool`): `True`, jeśli linia reprezentuje napis ekranowy, tablicę, szyld, tytuł odcinka lub sms w kadrze.
- `is_top` (`bool`): `True`, jeśli linia posiada styl górny (`Top`, `Upper`) lub znacznik `\an8`, oznaczający dialog w tle lub wypowiedź równoległą.
- `is_song` (`bool`): `True`, jeśli styl wskazuje na utwór muzyczny (`OP`, `ED`, `Song`, `Lyrics`) lub w tekście występują nuty `♪`, `♫`.
- `is_internal` (`bool`): `True`, jeśli linia spełnia kryteria monologu wewnętrznego (styl `Thoughts`, nawiasy `( )` wokół całej wypowiedzi lub kursywa `{\i1}` przy braku rozmówcy).
- `type_label` (`str`): Etykieta diagnostyczna (np. `DIALOG`, `NAPIS`, `MYŚL`, `PIOSENKA`, `NARRACJA`).
- `visual_details` (`str`): Opis położenia geometrycznego wyliczony ze znaczników `\pos`, `\an`, `\move`.

---

## CZĘŚĆ II: WARSTWA 1 — METADANE ZEWNĘTRZNE, AKUSTYKA DSP I WHISPER

### 1. Pobieranie i Normalizacja Metadanych Serii (`metadata.py`)

#### A. Ekstrakcja tytułu i czyszczenie nazwy pliku
1. `clean_anime_filename(file_path: str) -> str`: Usuwa sumy kontrolne CRC32 (np. `[A1B2C3D4]`), prefiksy grup fansuberskich (np. `[Erai-raws]`, `[SubsPlease]`), oznaczenia rozdzielczości (`1080p`, `720p`), kodeków (`x264`, `HEVC`, `AAC`) oraz numer odcinka, pozostawiając czysty tytuł serii.
2. `strip_season_suffix(title: str) -> str`: Odrzyna sufiksy sezonowe (`Season 2`, `2nd Season`, `S2`, `Part II`, `Cour 2`, `IV`), umożliwiając odpytanie bazy AniList o sezon macierzysty w przypadku braku wyników dla sequela.
3. `normalize_anime_slug(title: str) -> str`: Przekształca tytuł w jednolity identyfikator alfanumeryczny w formacie snake_case (np. `Hoshi no Tabibito` -> `hoshi_no_tabibito`).

#### B. Zapytanie AniList GraphQL API (`fetch_anilist_metadata`)
Metadane pobierane są metodą POST z endpointu `https://graphql.anilist.co`. Zapytanie ma następującą strukturę GraphQL:
```graphql
query ($search: String) {
  Media (search: $search, type: ANIME) {
    id
    title {
      romaji
      english
      native
    }
    description(asHtml: false)
    genres
    tags {
      name
      category
      rank
    }
    countryOfOrigin
    startDate {
      year
    }
    characters(sort: [ROLE, RELEVANCE], perPage: 16) {
      edges {
        role
        node {
          name {
            full
            native
          }
          gender
          description
        }
      }
    }
  }
}
```
Zwrócona odpowiedź JSON parsowana jest do słownika metadanych zawierającego:
- `title_romaji`, `title_english`, `title_native` (`str`).
- `synopsis` (`str`): Oczyszczony z tagów HTML opis fabularny.
- `genres` (`List[str]`): Lista gatunków (np. `["Action", "Fantasy", "Historical"]`).
- `tags` (`List[str]`): Tagi tematyczne o randze >= 60% (np. `["Medieval", "Magic", "Politics"]`).
- `characters` (`List[Dict[str, Any]]`): Lista 16 głównych postaci, gdzie każda postać posiada pola: `name_full` (`str`), `name_native` (`str`), `gender` (`Optional[str]`), `role` (`"MAIN"` lub `"SUPPORTING"`).

#### C. Normalizacja etykiet aktora (`normalize_actor_tag` & `normalize_ascii_diacritics`)
Funkcja `normalize_actor_tag(raw_name: str, strip_diacritics: bool = False) -> Tuple[str, Optional[str]]`:
1. Przyjmuje surową etykietę z pola `SSAEvent.name` (np. `Aktor (M)`, `Bohaterka [Female]`, `Rycerz (S1E4)`).
2. Wywołuje `normalize_ascii_diacritics(raw_name)`, realizując dekompozycję Unicode NFKD i usuwając znaki diakrytyczne do czystego ASCII.
3. Za pomocą wyrażenia regularnego:
   `r"[\(\[\{（【［〔]\s*(m|male|mezczyzna|mezczyzn|f|female|k|kobieta|kobiet)\s*(?:[,;/\|].*?)?[\)\]\}）】］〕]"`
   ekstrahuje jawny znacznik płci. Jeśli dopasowano `m/male/mezczyzna` -> zwraca `gender = "MALE"`. Jeśli dopasowano `f/female/k/kobieta` -> zwraca `gender = "FEMALE"`.
4. Za pomocą wyrażenia `r"\s*[\(\[\{（【［〔].*?[\)\]\}）】］〕]"` wycina wszelkie nawiasy techniczne, zwracając czyste miano bazowe `clean_name`.
5. Wynikiem jest krotka `(clean_name, extracted_gender)`, np. `("Aktor", "MALE")`.

#### D. Formatowanie kontekstu dla promptu (`format_anime_context_for_prompt`)
Generuje jednolity blok tekstowy wstrzykiwany do promptu Fazy 1:
```text
=== KONTEKST I REALIA SERII (ANILIST METADATA) ===
Tytuł: [Romaji / English]
Gatunki: Fantasy, Historical, Drama
Tagi świata: Medieval, Magic, Military
Zarys fabuły: [Opis uniwersum i założeń fabularnych]
Główne postacie (Kanon):
- Imię Postaci 1 (MĘŻCZYZNA, Rola: MAIN)
- Imię Postaci 2 (KOBIETA, Rola: MAIN)
```

---

### 2. Analiza Sygnału Audio, Ekstrakcja F0 i Triangulacja Epistemiczna

#### A. Wycinanie segmentów audio i buforowanie PCM
Dla każdej kwestii dialogowej potok ekstrahuje powiązany fragment japońskiej ścieżki audio:
1. Polecenie FFmpeg mapuje strumień japoński: `-map 0:a:m:language:jpn? -map 0:a:0 -vn -acodec pcm_s16le -ar 16000 -ac 1`.
2. Segment czasowy `[start_ms - 100 ms, end_ms + 100 ms]` ładowany jest do pamięci RAM jako tablica NumPy `np.ndarray` próbek mono 16-bitowych o częstotliwości próbkowania 16 000 Hz.

#### B. Przetwarzanie DSP (`librosa.pyin`) w `EpistemicAudioTriangulator`
Algorytm `EpistemicAudioTriangulator.estimate_f0_pyin` realizuje estymację częstotliwości podstawowej $F_0$:
1. **Voiced-Frame Pooling:** Zamiast odrzucać krótkie kwestie (<0.5 s), agreguje ramki dźwięczne z maksymalnie 8 najczystszych wypowiedzi danej postaci (maksymalny łączny budżet wynosi 10.0 s audio).
2. **Kryterium Dźwięczności:** Ramka uznawana jest za dźwięczną, gdy `voiced_flag == True` oraz `voiced_prob >= 0.60` w paśmie poszukiwań $f_{\min} = 60\text{ Hz}$, $f_{\max} = 400\text{ Hz}$.
3. **Próg Ważności Pomiaru:** Pomiar jest statystycznie wiążący wyłącznie wtedy, gdy zebrano $\ge 25$ ramek dźwięcznych (`len(all_valid_f0) >= 25`).
4. **Filtracja Szumu i Intonacji (IQR Filter):**
   Wyliczany jest rozstęp międzykwartylowy $\text{IQR}(F_0) = Q_{75}(F_0) - Q_{25}(F_0)$ oraz odchylenie standardowe $\text{std}(F_0)$. Próbka zostaje zdyskwalifikowana jako szum tła, muzyka (BGM) lub krzyk, jeśli:
   $$\frac{\text{IQR}(F_0)}{\text{median}(F_0)} > 0.35 \quad \text{ORAZ} \quad \text{std}(F_0) > 50.0\text{ Hz}$$

#### C. Asymetria fizjologiczna krtani i wagi akustyczne
1. **Twardy Determinizm Męski ($F_0 \le 135\text{ Hz}$):**
   Jeśli $\text{median}(F_0) \le 135.0\text{ Hz}$, algorytm ustawia flagę `F0_hard_masculine = True` z wagą męską $+5.0$ i pewnością `confidence = 1.0`. Prawo weta męskiego może zostać przełamane wyłącznie przy potężnym skumulowanym dowodzie anaforycznym języka angielskiego ($\text{Score}_{\text{EN}} \le -8$, oznaczającym błąd rozbicia na głosy lub dekonspirację tożsamości).
2. **Likwidacja Martwej Strefy ($F_0 > 135\text{ Hz}$):**
   Dla całego pasma $F_0 > 135.0\text{ Hz}$ waga sygnału akustycznego wynosi **$0.0$**. Eliminuje to fałszywą feminizację niskich głosów kobiecych (140–170 Hz) oraz dorastających chłopców dubbingowanych przez kobiety seiyū (>170 Hz). Decyzję o płci w tym paśmie podejmują wyłącznie wektory morfosyntaktyczne i dyskursywne.

#### D. Transkrypcja Whisper i obiekt `DisambiguationTag` (`whisper_disambiguator.py`)
Ścieżka audio transkrybowana jest lokalnie przez Faster-Whisper. Następnie funkcja `WhisperDisambiguator.disambiguate_line` buduje obiekt klasy `DisambiguationTag` posiadający następujące pola:
- `speaker_gender` (`Optional[str]`): Płeć mówcy (`MALE`, `FEMALE`, `None`).
- `speaker_age_class` (`Optional[str]`): Klasa wieku (`CHILD`, `TEEN`, `ADULT`, `ELDER`).
- `addressee_gender` (`Optional[str]`): Płeć adresata 2. osoby.
- `addressee_age_class` (`Optional[str]`): Klasa wieku adresata.
- `addressee_number` (`str`): Liczba adresata (`SINGULAR`, `PLURAL`, `DUAL`).
- `social_register` (`str`): Rejestr społeczny (`FORMAL_KEIGO`, `INFORMAL_TY`, `HOSTILE`).
- `pragmatic_attitude` (`Optional[str]`): Postawa pragmatyczna seiyū.
- `polar_response` (`Optional[str]`): Wartość odwróconej polaryzacji odpowiedzi.
- `kinship_role` (`Optional[str]`): Wykryta rola pokrewieństwa.
- `benefactive` (`Optional[str]`): Wektor przysługi (`FOR_SPEAKER`, `FOR_ADDRESSEE`).
- `spatial_deictic` (`Optional[str]`): Deiksa przestrzenna (`KO_PROXIMAL`, `SO_MEDIAL`, `A_DISTAL`).
- `is_phantom_audio` (`bool`): Detekcja ciszy lub szumu tła bez mowy.
- `low_acoustic_confidence` (`bool`): Niska pewność modelu ASR.
- `is_hallucination_loop` (`bool`): Zapętlenie halucynacyjne dekodera Whisper.
- `is_shock_drop` (`bool`): Nagłe załamanie energii seiyū (Ac=SHOCK_DROP).
- `detected_markers` (`List[str]`): Lista kodów kategorii znaczników K1–K8.

**Taksonomia 8 Kategorii Znaczników Fonicznych K1–K8:**
- **K1 (Płeć i wiek adresata 2. os.):** Twarde dowody tytularne w wołaczu: `-chan` -> żeński; `-kun` -> męski; `bouya` -> chłopiec; `shoujo` -> dziewczynka.
- **K2 (Liczba gramatyczna adresata 2. os.):** Wykładniki liczby mnogiej: `omaera`, `kisamara`, `temeera`, `minna`, `-tachi` -> `PLURAL`; `futari` -> `DUAL`.
- **K3 (Autoreferencja 1. os. - zaimki i imperatywy):** `ore`, `boku`, `washi`, `sessha` -> męski; `atashi`, `atai` -> żeński; imperatywy: `kurenai ka` -> żeński; `kure / kure yo` -> męski; formalne `watakushi` -> waga neutralna 0.0.
- **K4 (Role społeczne i pokrewieństwo):** `aniki`, `ani` -> starszy brat; `otouto` -> młodszy brat; `ane` -> starsza siostra; `imouto` -> młodsza siostra; `chichi/otousan` -> ojciec; `haha/okaasan` -> matka; `ojiisan` -> dziadek; `obaasan` -> babcia.
- **K5 (Wektory przysługi - benefactives):** `kureru / kudasaru` -> czynność skierowana do mówcy (dla mnie); `ageru / yaru` -> czynność wykonana dla adresata (dla ciebie).
- **K6 (Odwrócona biegunowość pytań - Echo Agreement):** Japońskie potwierdzenie `hai` po pytaniu z negacją oznacza zgodę z formą gramatyczną pytania, co w polszczyźnie wymaga odwrócenia znaku na przeczenie: *"Tak, nie przyszedł"* -> *"Nie, nie przyszedł"*.
- **K7 (Rejestr pragmatyczny T-V):** `temee`, `kisama` -> rejestr wrogi/pogardliwy; `desu`, `masu`, formy honoryfikatywne -> formalny (Pan/Pani); `omae`, `anta` -> bezpośredni poufały (Ty).
- **K8 (Deiksa przestrzenna Ko-So-A-Do):** `kore/kono` -> obiekt blisko mówcy (ten); `sore/sono` -> obiekt blisko słuchacza (tamten); `are/ano` -> obiekt oddalony od obu rozmówców (ów, tamten odległy); `dore/dono` -> zaimek pytający (który).

#### E. Obliczanie Directional Consensus Purity i synteza epistemiczna
W `SpaCyAnaphoraDiscourseAnalyzer.triangulate_epistemic_gender` agregowane są wagi dowodowe:
$$\text{tot\_weight} = \text{male\_weight} + \text{female\_weight}$$
$$\text{purity} = \frac{|\text{male\_weight} - \text{female\_weight}|}{\max(1.0, \text{tot\_weight})}$$
- Jeśli $\text{purity} == 1.0$ i liczba niezależnych dowodów $\ge 2$ -> `confidence >= 0.85`.
- Jeśli w sygnałach występuje sprzeczność ($\text{purity} < 0.65$) -> pewność jest tłumiona poniżej progu interwencji: `confidence = 0.70`, co zapobiega błędnym podmianom w linterze.

---

## CZĘŚĆ III: WARSTWA 2 — PAMIĘĆ SERII (SERIES BIBLE) I ONTOLOGIA FLEKSYJNA

### 1. Struktura i Cykl Życia Bazy Wiedzy (`series_memory.py`)

#### A. Schemat pliku `*_bible.json` na dysku
Baza wiedzy serii przechowywana jest w pliku `series_memory/{anime_slug}_bible.json`. Fizyczny schemat JSON zawiera sekcje:
```json
{
  "anime_title": "Tytuł Serii",
  "characters": {},
  "relations": {},
  "glossary": {},
  "plot_anchors": {},
  "declensions": {}
}
```

#### B. Samolecząca sanitacja bazy w pamięci RAM (`_sanitize_loaded_bible_in_ram`)
Po załadowaniu pliku z dysku metoda `_sanitize_loaded_bible_in_ram` wykonuje procedurę uzgadniania stanu bez modyfikacji dysku (koszt 0.00 PLN):
1. **Owijanie w `CharacterRegistryDict`:** Słownik `characters` zostaje zastąpiony strukturą `CharacterRegistryDict(self.data["characters"], bible_data=self.data)`. Wrapper ten przechwytuje zapytania o relacje skierowane, delegując je bezpośrednio do sekcji `relations`.
2. **Separacja relacji skierowanych:** Wszystkie klucze zawierające operator skierowany `->` (np. `PostaćA -> PostaćB`) są bezwzględnie usuwane ze słownika `characters` i przenoszone do sekcji `relations`.
3. **Ekstrakcja płci P0 i odcinanie nawiasów:** Każdy klucz postaci poddawany jest funkcji `normalize_actor_tag`. Jeśli klucz zawierał znacznik techniczny (np. `Bohater (M)`), rekord zostaje przeniesiony pod czysty identyfikator `Bohater`, a w polu `gender` ustawiana jest wartość `MALE` z `confidence = 1.0`, `priority = "P0"` oraz `has_verified_gender = True`.
4. **Promocja płci z opisów fabularnych:** Jeśli pole `gender` miało wartość `None` lub `UNKNOWN`, a w tekście pola `description` znajduje się znacznik `[MĘŻCZYZNA (Adresat)...]` lub słowo `mężczyzna`/`kobieta`, cecha płci zostaje wypromowana do strukturalnego pola `gender`, a pole `description` oczyszczone ze zbędnych instrukcji gramatycznych.
5. **Budowa indeksu aliasów pierwszych imion w czasie $O(1)$:**
   Dla każdej postaci o wieloczłonowym mianie (`FirstName LastName`) pierwszy człon (`FirstName`) jest automatycznie dodawany do tablicy `aliases`, jeśli jednoznacznie identyfikuje postać w serii. Następnie budowany jest płaski indeks RAM `self._actor_aliases_index: Dict[str, str]`, mapujący każde małe i zdekodowane z diakrytyków imię na kanoniczny klucz postaci.

#### C. Pełna specyfikacja `CharacterRecord Positive Schema`
Każdy rekord bytu osobowego w słowniku `characters` posiada następującą strukturę pól:
- `gender` (`str`): Płeć biologiczna postaci (`"MALE"` lub `"FEMALE"`).
- `grammatical_gender` (`str`): Rodzaj gramatyczny w języku polskim (`"MASCULINE"` lub `"FEMININE"`).
- `confidence` (`float`): Poziom pewności atrybutu (dla rekordów zweryfikowanych P0 wynosi `0.95` lub `1.0`).
- `priority` (`str`): Priorytet źródła wiedzy (`"P0"` dla danych zweryfikowanych w kanonie mangi/AniList/profilerze).
- `has_verified_gender` (`bool`): Twarda flaga blokująca nadpisywanie płci przez heurystyki Fazy 1.
- `aliases` (`List[str]`): Lista alternatywnych form imienia, w tym pierwsze imię, przydomki i warianty pisowni.
- `description` (`str`): Czysty opis roli fabularnej i powiązań społecznych postaci.
- `entity_category` (`str`): Wartość enumu `EntityCategory.ANTHROPONYM`.

---

### 2. Klasyfikacja Ontologiczna i Generator Fleksyjny (`EntityCategory` & `DeclensionParadigm`)

#### A. Klasyfikacja ontologiczna (`EntityCategory`)
Wszystkie encje występujące w napisach i glosariuszu przypisywane są do jednej z trzech rozłącznych kategorii:
- `EntityCategory.ANTHROPONYM`: Byty osobowe, postacie, ludzie, bóstwa o cechach antropomorficznych. Podlegają regułom uzgadniania płci gramatycznej orzeczeń i zaimków.
- `EntityCategory.TOPONYM`: Nazwy geograficzne, krainy, miasta, rzeki, twierdze. Podlegają regułom rekcji ablatywnej po przyimku pochodzenia `z` (*z Krainy*, a nie *z Krainą*).
- `EntityCategory.CHREMATONYM`: Przedmioty nieożywione, artefakty, miecze, zwoje, tytuły traktatów, zaklęcia. Nigdy nie mogą być traktowane jako mówcy ani adresaci dialogu.

#### B. Klasa `DeclensionParadigm` (Pydantic BaseModel)
Model reprezentuje pełny paradygmat 7 przypadków gramatycznych języka polskiego:
```python
class DeclensionParadigm(BaseModel):
    nominative: str = Field(description="Mianownik (M) - Kto? Co?")
    genitive: str = Field(description="Dopełniacz (D) - Kogo? Czego?")
    dative: str = Field(description="Celownik (C) - Komu? Czemu?")
    accusative: str = Field(description="Biernik (B) - Kogo? Co?")
    instrumental: str = Field(description="Narzędnik (N) - Z kim? Z czym?")
    locative: str = Field(description="Miejscownik (Ms) - O kim? O czym?")
    vocative: str = Field(description="Wołacz (W) - O!")
```
Klasa udostępnia skrócone właściwości dostępowe `@property`: `M`, `D`, `C`, `B`, `N`, `Ms`, `W`.

#### C. Algorytm generatora deklinacji (`generate_polish_name_declension`)
Funkcja przyjmuje `(name: str, gender: str = "UNKNOWN") -> Dict[str, str]`:
1. **Ochrona form odmienionych i deskrypcji:** Jeśli funkcja `is_complex_description(name)` lub `is_adjectival_oblique_token(name)` wykryje, że leksem kończy się już na polski sufiks przymiotnikowy w przypadku zależnym (`-ego`, `-emu`, `-ym`, `-im`, `-ych`, `-ich`, `-ymi`, `-imi`, `-ą`), generator natychmiast zwraca odwzorowanie tożsamościowe:
   $$\forall c \in \{M, D, C, B, N, Ms, W\}, \quad \text{decl}[c] = \text{name}$$
   Zapobiega to potworkom językowym typu *-ymem*.
2. **Obsługa przydawki dopełniaczowej i złożeń:** W nazwach wieloczłonowych typu *"X z Y"* lub *"Rycerz Śmierci"*, odmieniany jest wyłącznie człon główny (*Rycerz -> Rycerza, Rycerzowi*), a człon określający pozostaje zamrożony.
3. **Fonotaktyka imion męskich obcych:**
   - Zakończone na spółgłoskę twardą: Mianownik $-\emptyset$; Dopełniacz/Biernik `-a`; Celownik `-owi`; Narzędnik `-em`; Miejscownik/Wołacz `-ie` (z alternacją fonetyczną tematu).
   - Zakończone na afrykaty `-tz`, `-z`: Miejscownik i Wołacz przyjmują końcówkę `-u` (*tematy na -tz: końcówka -tzu* zamiast błędnego *-tzie*).
   - Imiona męskie na niemą samogłoskę `-e` po spółgłosce: Dopełniacz z apostrofem lub wymianą tematu.
4. **Ładowanie leksykonów fansuberskich:** Generator weryfikuje obecność plików leksykalnych w katalogu `series_memory/fansub_lexicons/{slug}.json`, pobierając zweryfikowane formy kanoniczne ustalone przez wydawnictwa.

---

## CZĘŚĆ IV: WARSTWA 1/2 — PROFILOWANIE ODCINKA (PRE-PASS / PROFILER 4.0)

### 1. Przebieg Profilowania (`profiler.py:EpisodeProfiler.profile_episode`)

#### A. Wejście profilera i mechanizm keszowania
Metoda `profile_episode(subs_text_sample, anime_metadata_str, cache_path)` przyjmuje:
- `subs_text_sample` (`str`): Zbiór pierwszych 100 000 znaków dialogów ze skryptu odcinka.
- `anime_metadata_str` (`str`): Sformatowany kontekst serii z AniList.
- `cache_path` (`Optional[str]`): Ścieżka do pliku keszu `episode_profile_{hash}.json`.
Jeśli plik keszu istnieje na dysku, jest natychmiast weryfikowany i ładowany za pomocą `EpisodeProfile.model_validate(json_data)`, co eliminuje ponowne zapytanie LLM (koszt 0.00 PLN).

#### B. Konstrukcja promptu profilera
Prompt definiuje rolę LLM jako *Głównego Reżysera i Script Doctora Lokalizacji Anime*. Narzuca strukturalną ekstrakcję wiedzy w 12 punktach:
1. Identyfikacja polskiego kanonu mangowego i wydawnictwa drukowanego.
2. Skaner pułapek językowych (`danger_lines_prescan`): idiomy, odwrócone pytania przeczące, fałszywe pokrewieństwo, konstrukcje rezultatywne.
3. Punkty zwrotne relacji (`relationship_pivots`): zmiany rejestru i hierarchii społecznej.
4. Powiedzonka i motywy przewodnie (`character_catchphrases`).
5. Plany transkreacji piosenek (`song_transcreation_plans`): sylabotonizm, metrum.
6. Gry słowne i kalambury (`puns_and_wordplays`): polskie ekwiwalenty fonetyczne.
7. Alerty ciągłości fabularnej (`continuity_bridge_alerts`).
8. Mapa sekwencji dramatycznych (`dramatic_sequences`): podział na sceny, wykrywanie scen wyłącznie kobiecych (`female_only_scene`).
9. Kartoteka obsady (`character_dossiers`): zaimki podmiotowe, wiek, rejestr.
10. Pełne paradygmaty deklinacji imion (`name_declensions`) i relacje postaci (`characters`).
11. Glosariusz terminów uniwersum (`glossary`).
12. Realia świata, epoka i stylizacja historyczna.

Zapytanie wysyłane jest do modelu Gemini z parametrami: `temperature = 0.2`, `response_mime_type = "application/json"` oraz `response_schema = EpisodeProfile`.

#### C. Pełna specyfikacja schematów Pydantic profilera
1. `EpisodeProfile`:
   - `episode_summary` (`str`): Zwięzłe streszczenie dramaturgiczne odcinka.
   - `setting_and_era` (`str`): Czas akcji, ustrój, realia materialne i poziom technologii.
   - `domain_expertise` (`str`): Specjalistyczna wiedza domenowa (np. szermierka, medycyna, magia).
   - `dialogue_stylization` (`str`): Rejestr stylistyczny języka polskiego (np. stylizacja szlachecka, współczesna).
   - `manga_canon_source` (`str`): Źródło polskiego kanonu mangowego.
   - `tone_and_genre` (`str`): Dominująca tonacja emocjonalna.
   - `danger_lines_prescan` (`List[DangerLinePreScan]`):
     * `approx_time` (`str`): Przybliżony czas kwestii (np. `04:15`).
     * `english_phrase` (`str`): Fraza źródłowa EN.
     * `speaker` (`str`): Domniemany mówca.
     * `contextual_trap` (`str`): Opis pułapki translacyjnej (np. dosłowna kalka).
     * `contextual_guidance` (`str`): Deklaratywna analiza kontekstu semantycznego i idiomatycznego (opis znaczenia frazy dla autonomii modelu Fazy 1 bez dyrektyw nakazowych).
   - `relationship_pivots` (`List[RelationshipPivot]`):
     * `approx_time` (`str`), `characters_involved` (`str`), `nature_of_shift` (`str`), `relational_guidance` (`str`): Deklaratywny opis charakteru relacji i dynamiki społecznej (np. przejście na 'ty' lub zwrot grzecznościowy).
   - `character_catchphrases` (`List[CharacterCatchphrase]`):
     * `character_name` (`str`), `original_phrase` (`str`), `canonical_pl` (`str`), `context_notes` (`str`).
   - `song_transcreation_plans` (`List[SongTranscreationPlan]`):
     * `song_type` (`str`), `time_range` (`str`), `metre_and_syllables` (`str`), `poetic_theme` (`str`).
   - `puns_and_wordplays` (`List[PunWordplayPlan]`):
     * `approx_time` (`str`), `original_joke_or_pun` (`str`), `polish_transcreation` (`str`).
   - `continuity_bridge_alerts` (`List[ContinuityBridgeAlert]`):
     * `term_or_event` (`str`), `canon_source_episode` (`str`), `continuity_guidance` (`str`): Deklaratywny opis ciągłości terminologicznej i zgodności ze źródłem kanonicznym.
   - `dramatic_sequences` (`List[DramaticSequence]`):
     * `sequence_name` (`str`), `time_range` (`str`), `dramatic_summary` (`str`), `dominant_tone` (`str`), `characters_present` (`List[str]`), `female_only_scene` (`bool`), `male_only_scene` (`bool`), `topology_type` (`str`).
   - `character_dossiers` (`List[CharacterDossier]`):
     * `name` (`str`): Kanoniczne miano postaci.
     * `gender` (`str`): Płeć (`MALE` / `FEMALE`).
     * `age_and_role` (`str`): Wiek i funkcja społeczna.
     * `age_class` (`str`): Klasa wieku (`CHILD`, `TEEN`, `ADULT`, `ELDER`).
     * `speech_style_pl` (`str`): Indywidualny styl wypowiedzi.
     * `first_person_pronoun` (`str`): Japoński zaimek 1. osoby (`ore`, `boku`, `watashi`).
     * `speaker_entity_type` (`str`): Kategoria ontologiczna (`ANTHROPONYM`).
     * `declension` (`Dict[str, str]`): Przypadki `M, D, C, B, N, Ms, W`.
     * `dialect_category` (`Optional[str]`), `idiolect_matrix` (`Optional[str]`), `vocal_profile` (`Optional[str]`).
   - `name_declensions` (`List[NameDeclension]`):
     * `character_name` (`str`), `gender` (`str`), `declension_summary` (`str`).
   - `characters` (`Dict[str, str]`): Słownik relacji społecznych i skróconych deskryptorów.
   - `glossary` (`Dict[str, str]`): Tłumaczenia kluczowych pojęć uniwersum.
   - `yojijukugo_and_idioms` (`Dict[str, str]`): Polskie transkreacje idiomów.
   - `key_conventions` (`List[str]`): Twarde konwencje nazewnicze.

#### D. Zasilanie `SeriesBible` i formatowanie dla promptu
Wygenerowany profil zasila bazę `SeriesBible`:
1. Nowo odkryte postacie z `character_dossiers` trafiają do `SeriesBible.data["characters"]`.
2. Słownik `glossary` zasila `SeriesBible.data["glossary"]`.
3. Paradygmaty deklinacji trafiają do `SeriesBible.data["declensions"]`.
4. Funkcja `format_episode_profile_for_prompt(profile)` generuje zwarty blok wiedzy do promptu Fazy 1, a `format_lean_episode_brief(profile)` tworzy zwięzłe podsumowanie dla Fazy 2 (Verifiera).

---

## CZĘŚĆ V: WARSTWA 2/3 — DYSKURS SCENICZNY, TOPOLOGIA I GRUPOWANIE PACZEK

### 1. Modelowanie Sceny i Rozpoznawanie Adresata (`scene_discourse.py`)

#### A. Granice sceny (`SceneBoundaryWall`) i `SubTurn Pivot Partitioning`
1. **Ściana Granicy Sceny (`SceneBoundaryWall`):** Dyskurs zostaje twardo rozcięty, tworząc nową scenę, gdy:
   - Odstęp czasowy między końcem poprzedniej linii a początkiem bieżącej wynosi $\Delta t \ge 3.5\text{ s}$ (3500 ms).
   - Wystąpiło cięcie montażowe wykryte przez FFmpeg / przejście przez czerń (`is_black_fade`).
   - Zmienił się styl ASS z dialogu na narrację, retrospekcję (`Flashback`) lub napis ekranowy (`Sign`).
   Uczestnicy i stan adresata z poprzedniej sceny nie przenikają przez `SceneBoundaryWall`.
2. **SubTurn Pivot Partitioning:** Wypowiedź jednego mówcy złożona z kilku zdań zostaje rozcięta na niezależne pod-segmenty (`SubTurn`), gdy wewnątrz wypowiedzi następuje zmiana adresata (np. zwrot do towarzysza, a po spójniku zwrot do wroga).

#### B. Trójstopniowy automat wyznaczania adresata 2. osoby
W ramach tury `SpeakerTurn` adresat (`target_speaker`, `target_gender`, `target_confidence`) wyznaczany jest hierarchicznie:
1. **Stopień 1: Wewnątrzzdaniowy Wołacz (Vocative Lock):**
   Jeśli w linii występuje jawny wołacz imienny (`decl["W"]` lub tytuł) oddzielony przecinkiem lub wykrzyknikiem: adresat zostaje natychmiast przypisany z `confidence = 0.98`. Wołacz męski bezwzględnie blokuje formy żeńskie w orzeczeniu.
2. **Stopień 2: Naprzemienność Diadyczna 1-na-1 (Dyadic Turn-Taking):**
   Gdy w scenie uczestniczą dwie osoby i nie wystąpił wołacz, adresatem wypowiedzi mówcy $A$ staje się poprzedni mówca $B$ (pod warunkiem $\Delta t < 5.0\text{ s}$).
3. **Stopień 3: Progresywny Lookahead i Ciągłość Tury:**
   W pytaniach otwartych algorytm bada wypowiedź następną ($\Delta t < 2.0\text{ s}$). Osoba udzielająca odpowiedzi zostaje wstecznie uznana za adresata pytania. Monologi wewnętrzne (`is_internal_monologue == True`), napisy i narratorzy są wykluczeni z roli adresata.

#### C. Matematyczne wyznaczanie rozłącznych zbiorów liczby mnogiej
Potok rozdziela algebrę grupy mówiącej ("My", 1. os. lm.) od grupy słuchaczy ("Wy", 2. os. lm.):
1. **Grupa 1. osoby lm. (`We_Group`):**
   $$\text{We\_Group} = \text{scene\_participants} \setminus \text{excluded\_addressee}$$
   Gdy mówca zwraca się w 2. osobie do słuchacza jako zewnętrznego obiektu (*"Musimy ci pomóc"*), słuchacz jest odejmowany ze zbioru. Przy czynności inkluzywnej (*"Chodźmy razem"*), `We_Group` obejmuje wszystkich obecnych.
2. **Grupa 2. osoby lm. (`You_Group`):**
   $$\text{You\_Group} = \text{scene\_participants} \setminus \{\text{speaker}\}$$
   Grupę odbiorców stanowią wszyscy uczestnicy sceny z wyjątkiem bieżącego mówcy.
3. **Trójstanowa Kategoryzacja Virility (`VIRILE` / `NON_VIRILE` / `AMBIGUOUS`):**
   - **`VIRILE` (Męskoosobowy):** Występuje przynajmniej jeden potwierdzony mężczyzna w zbiorze (wyłącznie na podstawie ontologii P0 z bazy `SeriesBible`, aliasów pierwszego imienia, jawnego znacznika płci w tagu aktora z `normalize_actor_tag` lub twardego determinizmu akustycznego $F_0 \le 135\text{ Hz}$). Całkowicie wykluczone jest wnioskowanie virility z form czasownikowych polskiego tekstu (-liśmy / -liście). Wymusza formy: *-liśmy / -liście*, *byliśmy / byliście*.
   - **`NON_VIRILE` (Niemęskoosobowy):** Zbiór liczy $\ge 2$ osoby i **każdy** uczestnik posiada zweryfikowaną płeć żeńską P0 (`confidence >= 0.95`), przy czym liczba mężczyzn wynosi zero i liczba postaci nieznanych wynosi zero (`unknown_count == 0`). Wymusza formy: *-łyśmy / -łyście*, *byłyśmy / byłyście*.
   - **`AMBIGUOUS` (Niejednoznaczny):** Brak pełnej wiedzy o składzie płciowym grupy. Obowiązuje funkcja tożsamościowa $T(x) = x$ (zakaz arbitralnego wymuszania końcówek).

---

### 2. Grupowanie w Paczki (Batching) i JIT Scoping

#### A. Algorytm dzielenia na paczki (`create_adaptive_batches`)
Dzieli odcinek na spójne dramaturgicznie paczki podlegające równoległemu tłumaczeniu:
1. Bazowy rozmiar paczki wynosi od 12 do 18 linii dialogowych.
2. **Koalescencja scen:** Paczka nigdy nie jest rozcinana wewnątrz dynamicznej wymiany zdań ($\Delta t < 1.5\text{ s}$).
3. **Cięcie w cezurach naturalnych:** Podział następuje w miejscach ciszy ($\Delta t \ge 3.0\text{ s}$), cięć montażowych lub plansz tytułowych.
4. **Kontekst poprzedzający (History Context):** Do każdej paczki dołączane są 2–4 ostatnie przetłumaczone kwestie z paczki poprzedniej wraz z ich polskim przekładem i znacznikami czasu, co gwarantuje płynność anaforyczną i leksykalną między paczkami.

#### B. Just-In-Time (JIT) Scoping wiedzy (`format_scoped_for_batch`)
Aby uniknąć zjawiska rozproszenia uwagi modelu (*"Lost in the Middle"*), funkcja `format_scoped_for_batch` skanuje tekst angielski kwestii w danej paczce:
- Ze słownika `SeriesBible.characters` wybiera wyłącznie te postacie, których imiona lub aliasy faktycznie padają w bieżącej paczce lub biorą udział w scenie.
- Ze słownika `glossary` wybiera wyłącznie terminy obecne w tekście paczki.
Dzięki temu prompt nie jest zanieczyszczany setkami nieistotnych w danym momencie definicji.

---

## CZĘŚĆ VI: WARSTWA 3 — KONSTRUKCJA PROMPTU FAZY 1, TELEMETRIA I PRZEKŁAD LLM

### 1. Dynamiczny Dyspozytor Reguł (`rules.py`)

#### A. Statyczny kanon rzemiosła i keszowanie kontekstu
Kanon translatorski zdefiniowany jest w stałych:
- `CORE_AVT_MASTER_CANON`: Podstawowe zasady filmowego przekładu AVT (naturalność polszczyzny mówionej, unikanie kalk syntaktycznych z angielskiego, zwięzłość ekranowa).
- `BELCZYK_AVT_MASTER_CANON`: Kanon sztuki przekładu audiowizualnego Arkadiusza Belczyka (inwersja orzeczenia, elipsa zaimków, polska frazeologia).
- `ACTIVE_AVT_CRAFT_CANON`: Zasady dynamicznego prymatu afektu seiyū nad tekstem pisanym.
Gdy aktywny jest `ContextCacheManager`, cały kanon statyczny oraz metadane serii są pieczone w obiekcie `CachedContent` Gemini API ze statusem TTL = 300 s, co zapewnia 90% zniżki kosztowej.

#### B. Selekcja i punktacja reguł (`get_focused_rules_for_batch`)
Dyspozytor reguł analizuje specyfikę danej paczki (obecność pytań, piosenek, wołaczy, załamań głosu, napisów) i przypisuje filarom wagi punktowe za pomocą funkcji `calculate_rule_tier(rule_text)`:
- **Tier 1 (Supreme Affect - 120 pkt):** Filar CXXIV (Prymat afektu seiyū, drżenie głosu, płacz, krzyk).
- **Tier 2 (Drama & Discourse - 100 pkt):** Filar CLXV (Dyskontinuitet czasowy i cięcia scen), Filar CLXVI (Audyt poznawczy i pułapki idiomatyczne).
- **Tier 3 (Active Craft - 70 pkt):** Filar CLXIX (Szeregi współrzędne przymiotników), Filar CLXXII (Polszczyzna bezterminowa vs archaizmy).
- **Tier 4 (Dialogue Flow - 50 pkt):** Płynność dialogowa, unikanie zaimkozy.
- **Tier 5 (Lexical & Realia - 10 pkt):** Specyficzne jednostki miar i toponimy.
Do promptu paczki wstrzykiwane są wyłącznie 4 najwyżej punktowane reguły, zapobiegając przeładowaniu okna uwagi modelu.

---

### 2. Generowanie Deklaratywnej Telemetrii Linii (`translator.py`)

Dla każdej linii w paczce potok generuje zestaw pasywnych metadanych:
1. `_arbitrate_speaker_gender`: Ustala płeć mówcy na podstawie bazy wiedzy P0, jawnego tagu aktora `normalize_actor_tag` oraz triangulacji F0.
2. `detect_audio_discrepancy`: Wykrywa rozbieżności między skryptem EN a japońskim audio seiyū, generując deskryptor:
   `"Sygnał audio JP: [treść okrzyku / potwierdzenia]"`
3. `get_audio_semantic_anchor`: Wykrywa kluczowe kotwice semantyczne (np. formy przeczące, honoryfikatory).
4. `detect_japanese_pragmatic_register`: Zwraca deskryptor stylu (np. `"Rejestr formalny dworski"`, `"Rejestr wrogi/bojowy"`).
5. **Jednokanałowy Wektor Telemetrii (`format_dry_telemetry_tag`):**
   Buduje zwięzły mikro-tag dołączając wyłącznie segmenty o pewności $\ge 0.80$:
   ```text
   [Mówca: MASCULINE | Adresat: FEMININE | Grupa_1os_lm: VIRILE]
   ```
   Wartości `None`, `UNKNOWN` oraz `AMBIGUOUS` są bezwzględnie pomijane.
6. **Czystość Nagłówków Kwestii i Brak Preskryptywności (Standard 9.0):**
   W szablonach formatowania linii dialogowych wewnątrz `_prepare_batch_prompt` oraz `_process_single_batch` kategorycznie wyeliminowano wstrzykiwanie preskryptywnych podpowiedzi końcówek fleksyjnych w nawiasach (takich jak `(-łaś)`, `(-łem)`, `(-łabym)`, `(-łbym)` czy `(-łyście)`). Płeć i liczba przekazywane są do modelu wyłącznie jako czyste miano roli w nagłówku oraz jednokanałowy wektor telemetrii w wierszu `📡 TELEMETRIA: [Mówca: ... | Adresat: ...]`, bez sugerowania czasów gramatycznych ani konkretnych morfemów w tekście pomocniczym. Skrypt angielski dostarcza wyłącznie treści semantycznej i faktów, nie narzucając polskiej składni, co gwarantuje pełną autonomię stylistyczną modelu LLM.

---

### 3. Składanie Promptu Paczki (`_prepare_batch_prompt` & `_process_single_batch`)

#### A. Kompletny szablon finalnego promptu Fazy 1
Poniżej przedstawiono dokładną strukturę promptu wysyłanego do LLM:

```text
Przekład kwestii na naturalną, żywą polszczyznę mówioną z zachowaniem filmowego rytmu dialogu:
1. Syntaktyka i ciągłość: całe zdania rozbite na linijki tworzą spójną całość z naturalnym polskim szykiem wyrazów.
2. Liczba i płeć: w dialogach bezpośrednich forma 2. os. lp. ('ty'), formy przeszłe zgodne z wektorem stanu sceny i audio seiyū.
3. Triangulacja EN+JP+obraz: skrypt EN dostarcza treść i fakty, japońskie audio rejestr emocjonalny, a kadr obrazu napisy ekranowe.
4. Kwestie wielogłosu: wypowiedzi dwóch osób w jednej kwestii rozdzielane na osobne linie ('- Kwestia 1\N- Kwestia 2').
5. Naturalność: żywy język dialogowy zamiast kalek dosłownych i struktur obcojęzycznych:

=== SKONCENTROWANE REGUŁY WARSZTATOWE (FOCUSED AVT RULES) ===
[Wyselekcjonowane filary o najwyższych wagach punktowych]

=== KONTEKST ODCINKA I PROFILE POSTACI ===
[Wygenerowany profil odcinka, kartoteki obecnych postaci, oficjalny kanon mangi]

=== POPRZEDNIE KWESTIE (HISTORIA DIALOGU) ===
[ID: 14] [EN: "Are you ready?"] -> [PL: "Jesteś gotowy?"] (Mówca: Bohater, Czas: 00:01:12.100 - 00:01:13.400)

=== KWESTIE DO PRZEKŁADU W BIEŻĄCEJ PACZCE ===
Kwestia [ID: 1] [TYP: [DIALOG] Standard] (Czas: 00:01:14.200 - 00:01:16.500):
  📄 SKRYPT PODSTAWOWY EN (TREŚĆ SEMANTYCZNA I FAKTY): I told you that we couldn't trust them from the start.
  📡 TELEMETRIA: [Mówca: MASCULINE | Adresat: FEMININE | Grupa_1os_lm: VIRILE]
  📖 Paradygmat odmiany: Bohater(D:Bohatera, C:Bohaterowi, B:Bohatera, N:Bohaterem, Ms:Bohaterze, W:Bohaterze)
  🎙️ Audio JP (Whisper ASR): dakara saisho kara aitsura wo信用できないって言ったんだ
  🏷️ Wykryte znaczniki foniczne: K3:Mówca_M, K7:Nieformalny (Ty)
  Parametry planszy: budżet 39 znaków (tempo czytania do 17.0 z/s, max 2 wiersze).
```

#### B. Schemat Pydantic odpowiedzi LLM (`BatchTranslationResponse`)
Model LLM zwraca odpowiedź zgodną ze schematem strukturalnym:
```python
class LineTranslation(BaseModel):
    id: int = Field(description="Identyfikator kwestii z promptu")
    polish_text: str = Field(description="Gotowy polski przekład dialogu lub napisu")
    speaker_name: Optional[str] = Field(description="Kanoniczne imię mówcy")
    speaker_gender: Optional[str] = Field(description="Płeć mówcy: MALE, FEMALE, UNKNOWN")
    speaker_grammatical_gender: Optional[str] = Field(description="Rodzaj gramatyczny: MASCULINE, FEMININE")
    addressee: Optional[str] = Field(description="Imię lub rola adresata")
    target_gender: Optional[str] = Field(description="Płeć adresata: MALE, FEMALE, UNKNOWN")
    addressee_number: Optional[str] = Field(description="Liczba adresata: SINGULAR, PLURAL")
    semiotic_layer: Optional[str] = Field(description="Warstwa semiotyczna: DIALOGUE, INTERNAL_MONOLOGUE, SIGN, SONG")
    screen_region: Optional[str] = Field(description="Położenie na ekranie: BOTTOM, TOP, MIDDLE")
    visual_typesetting: Optional[Dict[str, Any]] = Field(description="Współrzędne kadru i parametry ASS")
    visual_subtext: Optional[str] = Field(description="Subtekst wizualny i mimika seiyū")
    literal_meaning: Optional[str] = Field(description="Dosłowne znaczenie źródłowe")
    notes: Optional[str] = Field(description="Uzasadnienie wyborów dramaturgicznych")
    ambiguity_note: Optional[str] = Field(description="Wątpliwości translacyjne dla Fazy 2")

class BatchTranslationResponse(BaseModel):
    scene_diagnosis: Optional[str] = Field(description="Diagnoza relacji dramatycznej w scenie")
    translations: List[LineTranslation] = Field(description="Lista przetłumaczonych linii")
    characters_identified: Optional[List[str]] = Field(description="Lista zidentyfikowanych postaci")
```

Odpowiedź jest rozpakowywana, a pole `polish_text` przypisywane z powrotem do odpowiadającego indeksu w liście zdarzeń `SSAEvent`.

#### C. Twarda Bariera Epistemiczna dla Danych Wyjściowych `LineTranslation` (Standard 9.0)
Wartości `speaker_gender` i `target_gender` zwrócone przez model LLM w obiekcie `LineTranslation` traktowane są wyłącznie jako hipotezy o ograniczonej wiarygodności (`confidence = 0.70`), co uniemożliwia:
1. Nadpisanie lub utworzenie wpisu w bazie `SeriesBible` z flagą `has_verified_gender = True` (status P0).
2. Aktywację inwazyjnych operatorów morfosyntaktycznych w `AVTLinter` pod flagą `strict_positive_domain=True` (które wymagają twardego progu $\text{confidence} \ge 0.95$).
Jeśli tożsamość lub płeć postaci nie została zweryfikowana w źródłach ontologicznych P0 (`SeriesBible`, tag aktora z `normalize_actor_tag` lub determinizm akustyczny $F_0 \le 135\text{ Hz}$), tekst wyjściowy podlega regule identyczności $T(x) = x$, zachowując nadrzędny autorytet przekładu modelu LLM (Primary LLM Translation Authority).

---

## CZĘŚĆ VII: FAZY KOREKCYJNE — VERIFIER (FAZA 2), AVT LINTER I EPISODE QUALITY GATE

### 1. Weryfikator Fazy 2 (`verifier.py:DialogueVerifier.verify_batch`)

#### A. Warunki uruchomienia i struktura wejściowa
Faza 2 uruchamiana jest automatycznie, chyba że w CLI podano flagę `--no-verify`. Jako wejście przyjmuje:
- `batch_items`: Listę słowników przetłumaczonych w Fazie 1, wzbogaconą o wektor telemetrii i paradygmaty:
  `[{'id': int, 'en': str, 'pl': str, 'speaker_gender': str, 'telemetry_tag': str, 'declension_paradigms': list, 'notes': str, 'ambiguity_note': str}, ...]`.
- `scene_diagnosis`: Wnioski dramaturgiczne z Fazy 1.
- `focused_rules_str`: Reguły warsztatowe AVT.
- `history_context`: Podgląd poprzednich kwestii.
- **Klauzula Niezmiennika Telemetrii w Prompcie:** Weryfikator otrzymuje jednoznaczną dyrektywę deklaratywną: wszelkie poprawki stylistyczne i redakcyjne respektują ustaloną telemetrię ontologiczną sceny (płeć mówcy, adresata, virility grup We/You o pewności $\ge 0.95$ oraz podane paradygmaty odmiany imion), zachowując uzgodnienia fleksyjne ustalone w Fazie 1 na podstawie telemetrii.

#### B. Elastyczny budżet myślenia (Elastic CoT Budgeting)
Metoda `calculate_effective_budget(batch_items)` dynamicznie przydziela liczbę tokenów rozumowania (Thinking Tokens) w zależności od złożoności paczki:
- **Dla modeli Pro (`gemini-2.5-pro`):**
  * Tier 1 (Piosenki OP/ED, kalambury, alarmy foniczne, wątpliwości): **2048 tokenów**.
  * Tier 2 (Rejestry feudalne, narady, szybki ping-pong dialogowy): **1536 tokenów**.
  * Tier 3 (Proste, krótkie dialogi codzienne): **1024 tokeny**.
- **Dla modeli Flash (`gemini-2.5-flash`):**
  * Tier 1 (Piosenki, kalambury, rozbieżności audio): **4096 – 6144 tokeny**.
  * Tier 2 (Średnia złożoność): **3072 tokeny**.
  * Tier 3 (Proste dialogi): **2048 tokenów**.

#### C. Dwuetapowy Audyt Poznawczy i schemat wyjściowy `RefinedLine`
Verifier działa w trybie Script Doctora. W procesie myślenia CoT realizuje:
1. *Autonomiczną ślepą lekturę dialogu:* Czyta wyłącznie polski tekst bez patrzenia na angielski oryginał, sprawdzając naturalność frazy w ustach aktora.
2. *Weryfikację z japońskim oryginałem:* Sprawdza, czy polski dialog oddaje właściwą intencję i ładunek emocjonalny seiyū.

Model zwraca obiekt `RefinedBatchResponse` zawierający listę `RefinedLine`:
```python
class RefinedLine(BaseModel):
    id: int = Field(description="Identyfikator kwestii")
    refined_pl: str = Field(description="Zredagowany, ostateczny polski tekst")
    screen_region: Optional[str] = Field(description="Położenie na ekranie")
    visual_typesetting: Optional[Dict[str, Any]] = Field(description="Parametry typograficzne")
    changes_made: Optional[str] = Field(description="Opis wprowadzonych poprawek redakcyjnych")
```

---

### 2. Post-Processing Liniowy (`avt_linter.py:AVTLinter.lint_and_fix_line`)

#### A. Parametry wejściowe metody
Metoda `AVTLinter.lint_and_fix_line` przyjmuje następujący kompletny zestaw argumentów:
- `text` (`str`): Tekst pojedynczej kwestii do weryfikacji.
- `speaker_gender` (`Optional[str]`): Płeć mówcy (`MALE`, `FEMALE`, `UNKNOWN`).
- `addressee_gender` (`Optional[str]`): Płeć adresata z Fazy 1.
- `is_all_girls_scene` (`bool`): Flaga sceny wyłącznie kobiecej.
- `is_sign` (`bool`): Flaga napisu ekranowego.
- `user_feedback_rules` (`Optional[List[Dict[str, Any]]]`): Niestandardowe reguły użytkownika.
- `custom_glossary` (`Optional[Dict[str, str]]`): Aktywny glosariusz serii.
- `is_informal_ty` (`bool`): Flaga rejestru bezpośredniego.
- `audio_jp` (`str`): Transkrypcja audio Whisper.
- `prev_line_text` (`str`): Tekst linii poprzedzającej.
- `source_en` (`str`): Oryginalny tekst angielski.
- `anime_title` (`str`): Tytuł serii.
- `target_gender` (`Optional[str]`): Autorytatywna płeć adresata z grafu dyskursu.
- `addressee_number` (`Optional[str]`): Liczba adresata (`SINGULAR`, `PLURAL`).
- `series_bible` (`Optional[Any]`): Instancja bazy wiedzy serii.
- `scene_has_male_participant` (`bool`): Obecność mężczyzny w scenie.
- `is_production` (`Optional[bool]`): Flaga środowiska produkcyjnego.
- `strict_positive_domain` (`bool`, **domyślnie `True`**): Wymuszenie czystej domeny pozytywnej.

#### B. Mechanizm QuoteShield (`mask_ass_tags_and_quotes`)
Przed uruchomieniem jakichkolwiek reguł tekst poddawany jest maskowaniu:
1. Wszystkie tagi formatujące ASS w nawiasach klamrowych `{...}` są zastępowane unikalnymi tokenami technicznymi `__ASS_TAG_SHIELD_X__`.
2. Wszystkie cytaty dialogowe w cudzysłowach `„...”`, `"..."` oraz `»...«` są maskowane tokenami `__QUOTE_SHIELD_X__`.
Po zakończeniu przetwarzania funkcja `unmask_ass_tags_and_quotes` bezstratnie przywraca oryginalne tagi i cytaty.

#### C. Przebieg 5 Operatorów Czystej Domeny Pozytywnej $D_{\text{pos}}$
W trybie `strict_positive_domain=True` linter pomija arbitralne podmiany słownikowe ($T(x) = x$), wykonując wyłącznie 5 niezmienników morfosyntaktycznych o pewności $\ge 0.95$:

1. **$D_{\text{pos}}(\text{VerbalGender})$ — Fleksja czasownikowa i predykat modalny `powinien`:**
   - Uzgadnia końcówki czasu przeszłego i trybu przypuszczającego 1. osoby (`speaker_gender`) oraz 2. osoby (`target_gender`):
     * Męskie: `-łem, -łeś, -łbym, -łbyś`.
     * Żeńskie: `-łam, -łaś, -łabym, -łabyś`.
   - **Stem-First Execution Order:** Oboczności rdzenne samogłosek ($o:ó$, $ę:ą$) wykonywane są przed wymianą końcówki fleksyjnej (*mogłaś -> mógłbyś*, *pomogłaś -> pomógłbyś*, *wzięłaś -> wziąłeś*, *zaczęłaś -> zacząłeś*).
   - **Inwariant Morfemu `-ł-`:** Czas teraźniejszy na `-am/-em` (*mam, znam, wiem, rozumiem*) posiada twardy immunitet i nigdy nie jest modyfikowany.
   - **Paradygmat czasownika ułomnego `powinien`:**
     * 1. os. lp.: `powinienem był <-> powinnam była`, `powinienem <-> powinnam`.
     * 2. os. lp.: `powinieneś był <-> powinnaś była`, `powinieneś <-> powinnaś`.
     * 1. i 2. os. lm.: `powinniśmy byli <-> powinnyśmy były`, `powinniście byli <-> powinnyście były`.

2. **$D_{\text{pos}}(\text{CopulaAdj})$ — Orzeczniki przymiotnikowe i imiesłowowe:**
   - Uzgadnia rodzaj przymiotników i imiesłowów po czasownikach łącznikowych (*być, stać się, zostać*):
     * 1. os. lp.: *jestem gotowy <-> jestem gotowa* (według `speaker_gender`).
     * 2. os. lp.: *jesteś pewien <-> jesteś pewna*, *bądź ostrożny <-> bądź ostrożna* (według `target_gender`).
   - **Koordynacja Szeregów Współrzędnych:** W konstrukcjach z przymiotnikami połączonymi spójnikiem (*czy, i, oraz, albo, lub, ani, ale*) oba człony szeregu są harmonizowane symetrycznie jako jeden wektor (*jesteś naiwna czy głupia -> jesteś naiwny czy głupi*).

3. **$D_{\text{pos}}(\text{RolePair\_Instrumental})$ — Pary ról społecznych w narzędniku:**
   - Działa **wyłącznie** na rzeczownikach w Narzędniku rządzonych przez łącznik 1. lub 2. osoby (*jesteś moim najlepszym uczniem <-> jesteś moją najlepszą uczennicą*).
   - **Immunitet Mianownika 3. Osoby:** Zdania prezentacyjne i deiktyczne 3. osoby w mianowniku (*"To wspaniały syn"*, *"To nasza jedyna nadzieja"*) posiadają bezwzględny immunitet i nie podlegają modyfikacjom na formy żeńskie.
   - Ochrona rzeczowników metaforycznych i epikoenicznych (*jesteś moją nadzieją / zgubą* pozostaje nienaruszone).

4. **$D_{\text{pos}}(\text{PluralGroup})$ — Virility grup We i You:**
   - Uzgadnia formy 1. os. lm. według `plural_group_gender` oraz 2. os. lm. według `you_group_gender`.
   - Grupa o statusie `VIRILE` (obecny mężczyzna) wymusza końcówki męskoosobowe: *-liśmy*, *-liście*, *byliśmy*, *byliście*. Błędne formy niemęskoosobowe są korygowane (*poszłyście -> poszliście*, *zrobiłyście -> zrobiliście*).
   - Grupa o statusie `NON_VIRILE` chroni formy niemęskoosobowe: *-łyśmy*, *-łyście*.
   - Grupa o statusie `AMBIGUOUS` zachowuje tożsamość $T(x) = x$.

5. **$D_{\text{pos}}(\text{PrepDeclension})$ — Rekcja przyimkowa i higiena onomastyczna:**
   - Koryguje formy mianownikowe imion po przyimkach nieablatywnych (*dla [Imię] -> dla [Imienia]*).
   - **Ochrona przed podwójną deklinacją:** Blokuje doklejanie końcówek do wyrazów posiadających już sufiksy przymiotnikowe w przypadkach zależnych (*-ymem -> -ym*).
   - **Rygor ontologiczny EntityCategory.TOPONYM:** Funkcja `strip_false_ablative_instrumental` usuwa fałszywy narzędnik ablatywny po przyimku pochodzenia `z` (*z [Toponim]* zamiast *-em*) wyłącznie dla bytów zweryfikowanych w ontologii jako toponimy, bezwzględnie chroniąc relację towarzyszenia dla `EntityCategory.ANTHROPONYM` (*z Janem*, *z Anną* pozostają w 100% nienaruszone).
   - Koryguje wołacz tematów na afrykaty (*-tzu*, np. tematy obcojęzyczne zakończone na afrykaty: *-tz -> -tzu* zamiast *-tzie*).
   - **Eliminacja kazuistycznych łat przymiotnikowych:** Zgodnie z zasadą Primary LLM Translation Authority i Zero-Literal, usunięto protezę `fix_virile_adjective_orthography` – model LLM stanowi nadrzędny autorytet w doborze naturalnych form przymiotnikowych polszczyzny.

---

### 3. Bramka Jakości Całego Odcinka (`avt_linter.py:EpisodeQualityGate.audit_and_fix_entire_episode`)

#### A. Obejście monolitu w trybie `strict_positive_domain=True` ($T(x) = x$)
W trybie produkcyjnym `EpisodeQualityGate` nie wykonuje inwazyjnych pętli regexowych z historycznych Faz 1–6 monolitu (linie kodu 6830–10097). Kaskady te zostają całkowicie pominięte:
$$\forall x \notin D_{\text{pos}}, \quad T(x) = x$$
Dzięki temu model LLM zachowuje pełną suwerenność stylistyczną, leksykalną i frazeologiczną.

#### B. Faza 0: Deduplikacja techniczna i formatowanie wielogłosów
1. Deduplikuje zagnieżdżone i powtarzające się tagi stylizacyjne ASS.
2. Formatuje kwestie wielogłosowe (dwie osoby mówiące równocześnie w jednej planszy), rozbijając je znacznikiem `\N` na dwuwiersz z myślnikami dialogowymi:
   ```text
   - Pierwsza kwestia.\N- Druga kwestia.
   ```

#### C. Faza 7: Geometria planszy, metryki ekranowe i higiena interpunkcji
1. **Pomiary Metryk AVT:**
   - **CPS (Znaki na sekundę):** $\text{CPS} = \frac{\text{długość czystego tekstu}}{\max(\Delta t, 0.5)} \le 17.0\text{ z/s}$.
   - **CPL (Znaki w wierszu):** Maksymalnie 38 znaków na wiersz ($\text{CPL} \le 38$).
   - **Maksymalna liczba wierszy:** Dokładnie 2 wiersze na planszę (niedopuszczalne 3 wiersze w dialogu).
2. **Syntaktyczny podział linii w cezurach naturalnych:**
   Długie kwestie przekraczające limit 38 znaków są łamane znacznikiem `\N` w miejscach cezur składniowych (przed spójnikami, po przecinkach, między frazą podmiotu a orzeczenia), eliminując sierotki i nienaturalne rozbicia związków frazeologicznych.
3. **Higiena interpunkcji:**
   - Zamiana podwójnych spacji i spacji przed znakami interpunkcyjnymi na pojedyncze.
   - Zamiana potrójnych kropek `...` na kanoniczny znak wielokropka `…` (lub odwrotnie, w zależności od konfiguracji stylu).
   - Usuwanie osamotnionych myślników z kwestii pojedynczych mówców.

#### D. Końcowy zapis pliku i telemetria kosztowa (`PricingGuard`)
1. Zmodyfikowany obiekt `SSAFile` zostaje zapisany na dysku w formacie `.ass` (kodowanie UTF-8 ze znacznikiem BOM `utf-8-sig`, zapewniającym poprawność wyświetlania w odtwarzaczach VSFilter, libass i MPV).
2. Moduł `PricingGuard` oblicza łączne zużycie tokenów:
   - Liczba tokenów promptu Fazy 1 i Fazy 2.
   - Liczba tokenów wygenerowanych (w tym tokeny myślenia CoT).
   - Liczba tokenów odczytanych z keszu kontekstu (-90% ceny).
   - Ostateczny koszt finansowy odcinka w PLN (dla zoptymalizowanego potoku Standardu 8.0/9.0 wynosi od 0.05 do 0.25 PLN za odcinek).

---

## CZĘŚĆ VIII: TABELA PRZEPŁYWU DANYCH END-TO-END (DATA-FLOW MATRIX)

Poniższa macierz przedstawia kompletny, fizyczny przepływ informacji przez wszystkie komponenty potoku od wejścia do wyjścia:

| Krok | Moduł źródłowy | Metoda / Funkcja | Typ i struktura danych | Moduł docelowy | Fizyczna forma danych | Rola w zachowaniu spójności kanonu |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | System plików / CLI | `main.py:main` | Argumenty CLI (`argparse.Namespace`) | `translator.py` | Zmienne wiersza poleceń | Konfiguracja parametrów, modeli LLM i ścieżek wejścia |
| **2** | System plików | `avt_linter.py:load_subtitle_file_resilient` | Plik `.ass` / `.srt` na dysku | `translator.py` | Obiekt `pysubs2.SSAFile` (lista `SSAEvent`) | Bezstratne załadowanie bazy czasowej i stylów napisów |
| **3** | `metadata.py` | `clean_anime_filename` & `strip_season_suffix` | Nazwa pliku wideo / napisów (`str`) | `metadata.py` | Czysty ciąg znaków tytułu (`str`) | Usunięcie sum kontrolnych, tagów fansub i sufiksów sequeli |
| **4** | AniList API | `metadata.py:fetch_anilist_metadata` | GraphQL HTTP POST (`graphql.anilist.co`) | `metadata.py` | Słownik JSON metadanych serii | Pozyskanie oficjalnych realiów, gatunków i 16 głównych postaci |
| **5** | Kontener MKV/MP4 | FFmpeg subprocess | Strumień japońskiego audio PCM 16kHz mono | `profiler.py` | Tablica próbek `np.ndarray` float32 w RAM | Przygotowanie sygnału do analizy DSP i transkrypcji |
| **6** | `profiler.py` | `EpistemicAudioTriangulator.estimate_f0_pyin` | Próbki audio PCM (`np.ndarray`) | `profiler.py` | Wartość numeryczna $\text{median}(F_0)$ (`float`) | Wyznaczenie wysokości głosu seiyū i twardego determinizmu męskiego |
| **7** | Faster-Whisper | `whisper_disambiguator.py:disambiguate_line` | Próbki audio + tekst EN | `translator.py` | Obiekt `DisambiguationTag` | Identyfikacja rejestru K1–K8, deiksy i polaryzacji |
| **8** | Dysk / Gemini | `profiler.py:EpisodeProfiler.profile_episode` | Pierwsze 100k znaków dialogu + metadane | `series_memory.py` | Obiekt Pydantic `EpisodeProfile` | Ekstrakcja relacji, kanonu mangi, pułapek i idiolektów |
| **9** | Dysk / RAM | `series_memory.py:_sanitize_loaded_bible_in_ram` | Plik `{slug}_bible.json` | `series_memory.py` | Wrapper `CharacterRegistryDict` w RAM | Samolecząca promocja płci do P0, separacja relacji i indeks $O(1)$ |
| **10** | `scene_discourse.py` | `SceneDiscourseGraph.build_discourse_topology` | Lista zdarzeń `SSAEvent` + `SeriesBible` | `translator.py` | Lista obiektów `SpeakerTurn` / `SubTurn` | Rozpoznanie adresata, rozcięcie scen i virility We/You |
| **11** | `translator.py` | `create_adaptive_batches` | Pełna lista zdarzeń `SSAEvent` | `translator.py` | Lista paczek `List[Tuple[int, SSAEvent, ...]]` | Adaptacyjny podział na 12–18 linii w naturalnych cezurach |
| **12** | `rules.py` | `get_focused_rules_for_batch` | Tekst i atrybuty paczki (`List[Dict]`) | `translator.py` | Wyselekcjonowany blok tekstu reguł (`str`) | Wstrzyknięcie 4 najistotniejszych filarów rzemiosła AVT |
| **13** | `translator.py` | `format_dry_telemetry_tag` | Cechy gramatyczne sceny ($\text{conf} \ge 0.80$) | `translator.py` | Mikro-tag `[Mówca: ... \| Adresat: ...]` | Pasywna informacja o stanie świata dla modelu LLM |
| **14** | `translator.py` | `_prepare_batch_prompt` | Metadane, historia, telemetria, audio JP | Google Gemini API | Pełny wyrenderowany ciąg promptu Fazy 1 | Autorytatywny przekład literacki dialogów przez LLM |
| **15** | Google Gemini API | Model LLM Fazy 1 (`generate_content`) | Prompt Fazy 1 zdefiniowany schematem JSON | `translator.py` | Obiekt Pydantic `BatchTranslationResponse` | Wygenerowanie wstępnego przekładu z uwzględnieniem afektu |
| **16** | `verifier.py` | `DialogueVerifier.verify_batch` | Przekład Fazy 1 + historia + budżet CoT | `translator.py` | Obiekt Pydantic `RefinedBatchResponse` | Redakcja Script Doctora w estetyce polszczyzny bezterminowej |
| **17** | `avt_linter.py` | `AVTLinter.lint_and_fix_line` | Tekst po F2 (`strict_positive_domain=True`) | `translator.py` | Krotka `(dpos_text, applied_fixes)` | Niezmienniki $D_{\text{pos}}$ (fleksja, modalne, szeregi przymiotników) |
| **18** | `avt_linter.py` | `EpisodeQualityGate.audit_and_fix_entire_episode` | Kompletny obiekt `pysubs2.SSAFile` odcinka | `translator.py` | Zaudytowany obiekt `SSAFile` | Faza 0 (deduplikacja ASS) + Faza 7 (metryki CPS/CPL, łamanie linii) |
| **19** | `translator.py` | `pysubs2.SSAFile.save` | Zaudytowany obiekt `SSAFile` w RAM | System plików | Fizyczny plik wyjściowy `.ass` (UTF-8 BOM) | Gotowy do projekcji kinowej plik napisów z pełnym typesettingiem |
| **20** | `translator.py` | `PricingGuard.log_summary` | Liczniki tokenów z puli `ClientPool` | Konsola / Logi | Raport telemetryczny kosztu (PLN / USD) | Rozliczenie kosztowe i audyt oszczędności keszu kontekstu (-90%) |

---

## CZĘŚĆ IX: WARSTWA 5 — TARCZA REGRESYJNA CI/CD, AUDYT AST I WERYFIKACJA INTEGRALNOŚCI

W celu zagwarantowania niezmienności reguł architektonicznych i eliminacji regresji, potok chroniony jest przez 4 zautomatyzowane bramki weryfikacyjne:

### 1. Weryfikator Integralności 8 Poprawek Architektonicznych (`verify_8_fixes.py`)
Skrypt audytuje 8 kluczowych filarów architektury (8/8 [PASS]):
1. **Likwidacja cyklicznego virility:** Virility wynika wyłącznie z tożsamości uczestników sceny (zakaz wnioskowania z polskich form czasownikowych `-liśmy / -liście`).
2. **Autonomia składniowa polskiego przekładu:** Skrypt EN dostarcza wyłącznie treści semantycznej i faktów, bez narzucania polskiej składni.
3. **Czystość nagłówków kwestii:** Brak preskryptywnych podpowiedzi końcówek (`-łaś / -łem`) w promptach; stan przekazywany jednokanałowo przez wektor telemetrii.
4. **Deklaratywny Profiler:** Zastąpienie imperatywnych pól polami opisowymi (`contextual_guidance`, `relational_guidance`, `continuity_guidance` zamiast `mandatory_direction`, `strict_direction_pl`, `continuity_directive`).
5. **Zasilanie Fazy 2 wektorem telemetrii:** Verifier weryfikuje styl z zachowaniem ustalonej telemetrii ontologicznej i paradygmatów fleksyjnych.
6. **Bariera epistemiczna wyjścia Fazy 1:** Zgadywana płeć z wyjścia LLM (`confidence = 0.70`) nie zanieczyszcza zweryfikowanej bazy P0 (`has_verified_gender = True`).
7. **Czystość PrepDeclension i rygor TOPONYM:** Eliminacja protezy przymiotnikowej `fix_virile_adjective_orthography` oraz twardy rygor `EntityCategory.TOPONYM` przy ablatywnym `z`.
8. **Spójność dokumentacji:** Pełna zgodność raportu technicznego z faktycznym kodem.

### 2. Skaner Czystości Strukturalnej i Zakazu Instancji (`verify_purity.py`)
11-bramkowy walidator AST (11/11 [PASS], Standard 9.0):
- **Bramka 1:** Składnia i integralność AST we wszystkich plikach `.py`.
- **Bramki 2–4:** Zakaz instancji postaci i krain ze zgłoszeń, zakaz cytowanych dialogów w regułach, zakaz etykiet kontrastowych.
- **Bramki 5–6:** Zakaz słów ALL-CAPS w tekście opisowym, zakaz preskryptywności i alarmów w promptach.
- **Bramki 7–9:** Zakaz zahardkodowanych slugów serii, statycznych kolekcji nazw i ręcznych łat odmian.
- **Bramki 10–11:** Czystość kodu DSP/NumPy oraz obowiązkowy domyślny parametr `strict_positive_domain=True`.

### 3. Forensic Diff & AST Auditor (`audit_diff.ps1`)
Audytor zmian w systemie kontroli wersji Git (VICTORY CONFIRMED):
- **1/4 Zero-Cosmetic Gate:** Wymóg fizycznej modyfikacji rdzenia silnika (Warstwy 1–4) przy zakazie ręcznej edycji plików `.ass`/`.srt`/`*_bible.json`.
- **2/4 Zero-Onomastic & Stem Leakage Gate:** Zero wycieku nazw własnych ani ich rdzeni do kodu produkcyjnego.
- **3/4 End-to-End Wiring Gate:** Brak martwego kodu (każda nowa definicja musi mieć min. 2 wystąpienia).
- **4/4 Test Integrity Gate:** Wymóg testów jednostkowych i zakaz mockowania logiki domenowej silnika (`unittest.mock.patch`).

### 4. Pakiet Testów Regresyjnych Pytest (`test_system.py`)
- **179/179 PASSED (100% testów zielonych, Zero Regression Lock):**
  * **Testy 1–171:** Testy historyczne kompatybilności wstecznej (morfosyntaktyka, deiksa, akustyka, QuoteShield, deklinacja onomastyczna).
  * **Testy 172–175:** Testy normalizacji aktorów, naprawy hybryd, koordynacji przymiotników i paradygmatu modalnego `powinien`.
  * **Testy 176–179:** Testy czystej domeny pozytywnej $D_{\text{pos}}$, promocji płci do P0, rygoru `EntityCategory.TOPONYM` oraz zero wycieku nazw do kodu produkcyjnego.

---
**KONIEC PEŁNEGO RAPORTU TECHNICZNEGO POTOKU AVT — TRANSLATOR STANDARD 8.0 / 9.0**
