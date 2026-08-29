# 🏛️ CORNERSTONE v2.0 — ŻELAZNY FUNDAMENT I STANDARD ZŁOTEGO ŚRODKA

> **DATA USTANOWIENIA:** 2026-08-29  
> **GIT COMMIT:** 432d979  
> **GIT TAG:** cornerstone-v2.0  
> **STATUS:** ZABLOKOWANY / NIENARUSZALNY (IMMUTABLE BASELINE)

---

## 🎯 METRYKI BAZOWE ZŁOTEGO STANDARDU (BASELINE BENCHMARK)

Każda przyszła zmiana w kodzie musi zachować lub polepszyć poniższe parametry referencyjne:

* ⏱️ **PRĘDKOŚĆ TŁUMACZENIA:** **~1.90 – 2.05 linii/s** (Odcinek ~360 linii w **3:00 – 3:15 min**).
* 💰 **KOSZT ODCINKA (POZIOM 3):** **~2.30 – 2.66 PLN** (przy rabacie Context Cache **-90%** i oszczędności **~4.00 PLN / odcinek**).
* 🧠 **GŁĘBIA SCRIPT DOCTORA (FAZA 2):** Budżet myślenia Gemini 3.7 Flash zablokowany na **6144 CoT tokenów**.
* 🛡️ **PAMIĘĆ PODRĘCZNA CONTEXT CACHE:** Pełny pre-warming wielokluczowy (*Multi-Key Pre-warming*) na wszystkich projektach przed startem tłumaczenia.
* 📚 **OFICJALNY KANON MANGOWY:** 83 zweryfikowane serie z oficjalnymi polskimi wydaniami papierowymi (Kotori, Waneko, JPF, Studio JG, Hanami, Dango, Egmont).
* 💾 **PAMIĘĆ TŁUMACZENIOWA (TM):** 173 906 autentycznych par dialogowych w 	ranslation_memory.db.
* 🧪 **REGRESYJNY ZESTAW TESTÓW:** **33/33 TESTY W 	est_system.py** muszą kończyć się statusem **PASSED**.

---

## ⚖️ 5 NIENARUSZALNYCH PRAW TŁUMACZA (THE 5 IMMUTABLE LAWS)

### 1. PRAWO JAKOŚCI KINOWEJ (ZERO DEGRADATION)
* **Zakaz obniżania modeli:** Faza 1 musi zawsze działać na flagowym modelu Flash (np. Gemini 3.6/3.7 Flash), a Faza 2 na modelu z pełnym budżetem myślenia CoT (6144).
* **Zakaz wycinania diagnostyki:** Pola scene_diagnosis, changes_made, 	one, speaker_gender oraz coustic_cues są integralną częścią kognitywnej analizy i nie mogą być usuwane.
* **Integralność zdań rozbitych (...):** Każda linijka zdania rozbitego wielokropkiem musi zachować swój sens semantyczny (bezwzględny zakaz nadmiernej kondensacji i zastępowania treści linijki obcymi terminami).

### 2. PRAWO WIELOKLUCZOWEGO PRE-WARMINGU CACHE (ZERO COLD MISSES)
* Wszystkie klucze API w puli client_pool.clients muszą mieć zablokowany bufor Context Cache przed rozpoczęciem przetwarzania pierwszej paczki.
* Żadne zapytanie w Fazie 1 ani w Fazie 2 nie ma prawa trafić na serwery Google jako pełnopłatny Uncached Input (3,00 zł / 1M). Wszystkie wątki pracują z gwarantowanym rabatem -90% (0,30 zł / 1M).

### 3. PRAWO DEDUPLIKACJI WIEDZY ODCINKA (ZERO REDUNDANT TOKENS)
* Profil Odcinka, Słownik Deterministyczny, Biblia Serialu, Kanon Mangowy i Złote Wzorce Użytkownika są wstrzykiwane bezpośrednio do instrukcji systemowej przed zbuforowaniem (_episode_knowledge_cached = True).
* Indywidualne paczki przesyłają wyłącznie czyste kwestie dialogowe, chroniąc przed spaleniem ~315 000 zbędnych tokenów na odcinek.

### 4. PRAWO BŁYSKAWICZNEGO CZYSZCZENIA (ZERO POST-SESSION FEES)
* Po zakończeniu tłumaczenia lub w przypadku przerwania, funkcja cleanup_all_active_caches natychmiast usuwa obiekty bufora ze wszystkich kluczy na serwerach Google.
* Koszt po wyłączeniu programu wynosi zawsze dokładnie **0,00 PLN**.

### 5. PRAWO CZYSTYCH KOMUNIKATÓW (HUMAN-FRIENDLY LOGS)
* Wszelkie błędy sieciowe (503, 429, 504) muszą być prezentowane użytkownikowi w czystym, zrozumiałym języku polskim, bez surowych zrzutów słowników JSON czy kodów technicznych.

### 6. PRAWO CZYSTYCH ŹRÓDEŁ I ZAKAZ CRUNCHYROLL PL (TRUSTED SOURCES ONLY)
* Baza terminologiczna i dynamiczne pobieranie danych opierają się WYŁĄCZNIE na fizycznych polskich wydaniach papierowych (Waneko, JPF, Studio JG, Kotori, Hanami, Dango, Egmont) oraz recenzowanej encyklopedii Tanuki Manga.
* Kategorycznie ZAKAZANE jest pobieranie lub sugerowanie się tłumaczeniami z Crunchyroll PL (ze względu na niską jakość literacką, kalki z języka angielskiego i błędy gramatyczne).

### 7. PRAWO TRZECH ZŁOTYCH SOCZEWEK POZNAWCZYCH (THE 3 GOLDEN COGNITIVE LENSES)
* Faza 2 (Script Doctor) ocenia każdą kwestię dialogową przez 3 nadrzędne pytania bez rozpraszania uwagi zbędnymi podpunktami:
  1. 👂 **UCHO:** Czy gdy żywy polski aktor dubbingowy przeczyta to na głos, kwestia brzmi gładko, naturalnie i bez potknięć?
  2. 🌍 **ŚWIAT:** Czy język i dobór słów idealnie oddają duszę świata przedstawionego i tożsamość postaci?
  3. 🎬 **OBRAZ I AUDIO:** Czy tekst idealnie harmonizuje z mimiką, ruchem postaci na kadrze i odgłosami z japońskiego audio?

---

## 🔒 ZASADA WERYFIKACJI PRZYSZŁYCH ZMIAN
Przed zaakceptowaniem i scommitowaniem jakiejkolwiek przyszłej zmiany w kodzie, programista/agent AI jest **bezwzględnie zobowiązany** do:
1. Uruchomienia `.venv\Scripts\python test_system.py` i uzyskania wyniku **33/33 PASSED**.
2. Weryfikacji, że żadna zmiana nie spowalnia asynchronicznego dispatchera paczek ani nie zwiększa zużycia tokenów wejściowych.
