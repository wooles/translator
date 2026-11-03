# 🏛️ KANONICZNA KOTWICA ARCHITEKTURY (GOLDEN CORNERSTONE ANCHOR v2.0 / STANDARD 10.1 BASELINE)
**Status:** NIENARUSZALNY PUNKT ODNIESIENIA (PRODUCTION CERTIFIED BASELINE)  
**Wersja:** `Standard 10.1 (Production Certified Baseline)`  
**Commit certyfikacji kodu:** `b9b9e2a` (`b9b9e2a7c63bdf2f70711a5f9e5ed538debb35d7`)  
**Commit ochrony Depuracji Legacy 1.0 (Z16):** `474fb64`  
**Data certyfikacji:** 3 listopada 2026 r.  
**Stan metryk:** `468 collected` (`315 passed` fast unit/integration + `153 deselected` slow/network), `20` produkcyjnych baz `SeriesBible`, `42` produkcyjne leksykony `fansub_lexicons`, `4/4` bramki (`verify_purity.py`, `verify_12_fixes.py`, `verify_ultimate_pipeline.py`, `audit_diff.ps1`) w stanie `PASS`.  
**Zasada utrzymaniowa post-10.1:** Wszelkie przyszłe prace rozwojowe startują z certyfikowanego baseline'u `Standard 10.1` i podlegają nienaruszalnym zasadom `Z1`, `Z2`, `Z3`, `Z4` oraz `Z16`.

Dokument ten definiuje reguły, niezmienniki architektoniczne i standardy jakościowe, które stanowią fundament bezwzględnie zachowywany przy modyfikacjach, refaktoryzacjach czy rozbudowie potoku.

---

## 1. ⚡ WYDAJNOŚĆ I RÓWNOLEGŁOŚĆ (CONCURRENCY & THREAD-SAFETY)
1. **Pula Wielokluczowa Zero-Wait (`MultiKeyClientPool`)**:
   * Obsługa wielu kluczy API równolegle (domyślnie 6 paczek jednocześnie na 3 kluczach).
   * Czas przekładu 24-minutowego odcinka (ok. 350–435 linii): **zaledwie ~2 minuty**.
2. **Bezpieczeństwo Wątkowe (`self.lock`)**:
   * Każda instancja `MultimodalTranslator` i `DialogueVerifier` **MUSI** posiadać zainicjalizowany obiekt `self.lock = threading.Lock()`.
   * Zakaz współdzielenia niezabezpieczonych struktur danych pomiędzy wątkami tłumaczącymi paczki.
3. **Brak Pętli Retry (`Retry Loops`)**:
   * Każda paczka napisów w normalnych warunkach wykonuje dokładnie **1 zapytanie w Fazie 1 i 1 zapytanie w Fazie 2**.
   * Błędy sieciowe/przeciążenia TPU obsługiwane są z błyskawicznym przełączaniem klucza (rotacja 200 ms).

---

## 2. 🛡️ BEZPIECZEŃSTWO FINANSOWE I CONTEXT CACHE (0.00 PLN IDLE)
1. **Rabat Context Caching (-90%)**:
   * Wszystkie 133 Filary AVT, Biblia Serialu i Słownik są buforowane na serwerach Google za pomocą `ContextCacheManager` z hashem SHA-256.
2. **Całkowite Czyszczenie Pamięci Podręcznej (`Multi-Key Teardown`)**:
   * W bloku `finally` każdego tłumaczenia funkcja `ContextCacheManager.cleanup_all_active_caches()` **MUSI** iterować po wszystkich klientach w puli (`self.client_pool.clients`), a nie tylko po pierwszym kliencie.
   * Gwarantuje to **0,00 PLN kosztów pasywnych** po zakończeniu pracy programu.
3. **Rzetelne Wskaźniki Kosztów (`PricingGuard`)**:
   * Poziom 1 (Lite): **0,00 PLN**
   * Poziom 2 (Studio Flash): **~1,90 – 2,05 PLN**
   * Poziom 3 (Mistrzowski Flash - Cornerstone): **~3,15 – 3,30 PLN**
   * Poziom 4 (Kinowy Pro): **~5,50 – 6,50 PLN**

---

## 3. 🎬 CZYSTOŚĆ NAPISÓW AVT (STANDARD NETFLIX / CANAL+)
1. **Żelazny Zakaz Osieroconych Myślników (`clean_orphaned_dialogue_dashes`)**:
   * Myślnik dialogowy (`- `) stosuje się **WYŁĄCZNIE** w wypowiedziach dwugłosowych w obrębie jednego bloku (`- Kwestia A \N - Kwestia B`).
   * Pojedyncza kwestia jednoosobowa **NIGDY** nie może zaczynać się od myślnika.
2. **Filtr Szumu Paralingwistycznego (`is_isolated_paralinguistic_clutter`)**:
   * Samotne westchnienia (*„Och!”*, *„Uch!”*, *„Ah!”*, *„Hmph!”*, *„Tsk!”*, *„Uff!”*) są automatycznie usuwane z napisów, gdy mimika i gra aktorska seiyuu w 100% przekazują emocję.
3. **Ścisły Przełącznik Honoryfikatorów (`keep_honorifics`)**:
   * W trybie bez honoryfikatorów (`keep_honorifics=False`):
     - Słownik deterministyczny nie narzuca japońskich przyrostków (`Senpai`, `Sensei`).
     - Krok 7 automatycznie oczyszcza imiona z sufiksów (`Shinomiya-senpai` -> `Shinomiya`).

---

## 4. 🎙️ TRIANGULACJA AUDIO & KORELACJA Z JAPOŃSZCZYZNĄ
1. **Lokalny Silnik Audio GPU (Kotoba-Whisper v2.0 Faster-Whisper)**:
   * 100% transkrypcji audio działa lokalnie na karcie NVIDIA (CUDA float16) — 0 tokenów audio wysyłanych do Google API.
2. **Strażnik Rozbieżności Audio (`detect_audio_discrepancy`)**:
   * `Warukatta na / Warui` (悪かったな) -> Zawsze liczba pojedyncza (*„Wybacz...”* / *„Moja wina...”*), zakaz liczby mnogiej (*„Wybaczcie”*).
   * `Sasuga` (さすが) -> Pochwała kunsztu (*„Jak przystało na...”*), zakaz kalki (*„Całe...”*).
   * `Sumimasen` (済みません) w kontekście Giri -> Dług wdzięczności (*„Wybacz kłopot...”*).
   * `Ii desu` (いいです) -> Odmowa (*„Ja... podziękuję”*), zakaz błędnego stanu zdrowia (*„Nic mi nie jest”*).

---

## 5. 🧠 KOGNITYWISTYKA AVT I ARCHITEKTURA ZEROWEJ LUKI (ZERO-GAP BASELINE)
1. **100% Bezstratny Przepływ Kontekstu**:
   * Faza 2 (Script Doctor) otrzymuje pełen zestaw: `history_context` (poprzednie kwestie z polskim przekładem, mówcami i stanem myśli), `lookahead_events` (przyszłe kwestie z mówcami), `character_registry` (płeć, role) oraz ustrukturyzowaną `scene_diagnosis` (z Teorią Umysłu).
2. **Ping-Pong Dialogowy i Logika Odpowiedzi**:
   * Kategoryczny zakaz samotnego „Tak/T-Tak” w odpowiedzi na ostrzeżenia/dyrektywy, pytania otwarte (Wh-questions) oraz pytania z przeczeniem (Echo Agreement / Filar CLIV).
3. **Gwarancja Zerowej Luki (Zero-Gap Healing Pass)**:
   * Automatyczny pasaż uzupełniający w `translate_file` eliminuje jakiekolwiek pominięte kwestie wynikające z błędów sieciowych.
4. **Całościowy Audyt Odcinka (`EpisodeQualityGate`)**:
   * Analiza pełnej osi czasu: spójność T-V, higiena interpunkcji, bariera myśli wewnętrznej i skaner pozostałości angielskich.

---

## 6. 🧪 PAKIET TESTÓW INTEGRACYJNYCH (34/34 PASSED)
Przed zatwierdzeniem jakichkolwiek przyszłych zmian należy bezwzględnie wykonać:
```powershell
.venv\Scripts\python test_system.py
```
Wszystkie 34 testy jednostkowe i integracyjne **muszą zakończyć się statusem PASSED**. Naruszenie któregokolwiek z powyższych punktów traktowane jest jako regresja krytyczna i natychmiastowo blokuje wdrożenie.
