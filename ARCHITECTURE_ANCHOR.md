# 🏛️ KANONICZNA KOTWICA ARCHITEKTURY (GOLDEN CORNERSTONE ANCHOR v2.0)
**Status:** NIENARUSZALNY PUNKT ODNIESIENIA (GOLD STANDARD)  
**Wersja:** `cornerstone-v2.0`  
**Data zablokowania:** 29 sierpnia 2026 r.

Dokument ten definiuje żelazne zasady, niezmienniki architektoniczne i standardy jakościowe, które **MUSZĄ** być bezwzględnie zachowane przy jakichkolwiek przyszłych modyfikacjach, refaktoryzacjach czy rozbudowie tłumacza.

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

## 5. 🧪 PAKIET TESTÓW INTEGRACYJNYCH (32/32 PASSED)
Przed zatwierdzeniem jakichkolwiek przyszłych zmian należy bezwzględnie wykonać:
```powershell
.venv\Scripts\python test_system.py
```
Wszystkie 32 testy jednostkowe i integracyjne **muszą zakończyć się statusem PASSED**. Naruszenie któregokolwiek z powyższych punktów traktowane jest jako regresja krytyczna.
