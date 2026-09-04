# 🏛️ CORNERSTONE v2.0 — ŻELAZNY FUNDAMENT I STANDARD ZŁOTEGO ŚRODKA

> **DATA USTANOWIENIA / AKTUALIZACJI:** 2026-09-05  
> **GIT COMMIT:** 1208154  
> **GIT TAG:** cornerstone-v2.0  
> **STATUS:** ZABLOKOWANY / NIENARUSZALNY (IMMUTABLE PEAK QUALITY BASELINE)

---

## 🎯 METRYKI BAZOWE ZŁOTEGO STANDARDU (BASELINE BENCHMARK)

Każda przyszła zmiana w kodzie musi traktować obecny stan jako nienaruszalną bazę referencyjną i bezwzględnie zachować lub polepszyć poniższe parametry:

* ⏱️ **PRĘDKOŚĆ TŁUMACZENIA:** **~1.90 – 2.05 linii/s** (Odcinek ~360 linii w **3:00 – 3:15 min**).
* 💰 **KOSZT ODCINKA (POZIOM 3):** **~2.30 – 2.66 PLN** (przy rabacie Context Cache **-90%** i oszczędności **~4.00 PLN / odcinek**).
* 🧠 **GŁĘBIA SCRIPT DOCTORA (FAZA 2):** Budżet myślenia Gemini 3.7 Flash zablokowany na **6144 CoT tokenów** (Multi-Tier Elastic 6144 / 3072 / 2048).
* 🛡️ **PAMIĘĆ PODRĘCZNA CONTEXT CACHE:** Pełny pre-warming wielokluczowy (*Multi-Key Pre-warming*) na wszystkich projektach przed startem tłumaczenia.
* 📚 **OFICJALNY KANON MANGOWY:** 83 zweryfikowane serie z oficjalnymi polskimi wydaniami papierowymi (Kotori, Waneko, JPF, Studio JG, Hanami, Dango, Egmont).
* 💾 **PAMIĘĆ TŁUMACZENIOWA (TM):** 173 906 autentycznych par dialogowych w `translation_memory.db`.
* 🧪 **REGRESYJNY ZESTAW TESTÓW:** **34/34 TESTY W `test_system.py`** muszą kończyć się statusem **PASSED** (100% bez regresji).
* 🎯 **ARCHITEKTURA ZEROWEJ LUKI (ZERO-GAP ARCHITECTURE):** 100% bezstratny przepływ kontekstu między fazami, automatyczny Healing Pass, obsługa pytań otwartych i przeczeń (Echo Agreement) oraz globalny EpisodeQualityGate.

---

## 👑 TRZY ŻELAZNE ZASADY PROJEKTU (W KOLEJNOŚCI OD NAJWAŻNIEJSZEJ DO NAJMNIEJ WAŻNEJ)

1. **CZYSTOŚĆ I REŻIM REJESTRU KANONU MANGI (OFICJALNE ŹRÓDŁA ONLY, ZERO AI):**
   * W rejestrze (`manga_canon.py`) znajdują się **wyłącznie terminy z oficjalnych i sprawdzonych źródeł** (licencjonowane polskie wydania papierowe: Waneko, J.P.Fantastica, Studio JG, Kotori, Hanami, Dango, Egmont oraz baza Tanuki Manga).
   * Rejestr ogranicza się **wyłącznie do oryginalnego słowa (klucza) i jego oficjalnego polskiego odpowiednika** (czyste pary klucz $\rightarrow$ wartość, bez zbędnych komentarzy, nawiasów i opisów).
   * **KATEGORYCZNY ZAKAZ** stosowania jakichkolwiek treści wygenerowanych syntetycznie przez AI lub pochodzących z niesprawdzonych źródeł. Asystent ma bezwzględny obowiązek dbania o utrzymanie rejestru w tym surowym reżimie.

2. **NADRZĘDNOŚĆ KANONU MANGI JAKO POZIOMU 1:**
   * Kanon mangi stanowi **nadrzędny Poziom 1 w hierarchii przekładu**.
   * Wszystkie zawarte w nim terminy **muszą być bezwzględnie i obligatoryjnie uwzględniane oraz deterministycznie wymuszane przy tłumaczeniu**.

3. **UWAGI UŻYTKOWNIKA JAKO POZIOM 5 (WSKAZÓWKI SYSTEMOWE):**
   * Uwagi i korekty użytkownika mają **najniższy, Poziom 5 w hierarchii przekładu**.
   * Należy traktować je jako **wskazówki do poprawy przyszłych tłumaczeń** (systemowe reguły, ulepszenia lintera, wzorce Few-Shot i optymalizacja triangulacji), a nie jako doraźne burzenie hierarchii Poziomów 1–4.

---

## ⚖️ NIENARUSZALNE PRAWA TŁUMACZA (THE IMMUTABLE LAWS)

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

### 8. PRAWO OFICJALNEJ HIERARCHII PRZEKŁADU (THE 5-TIER TRANSLATION HIERARCHY)
Rozstrzyganie wszelkich konfliktów translacyjnych i priorytetów w silniku odbywa się ściśle według następującej hierarchii:
* **Poziom 1: OFICJALNY KANON POLSKICH WYDAŃ MANGOWYCH** (Najwyższy, nienaruszalny autorytet terminologiczny licencjonowanych tomików papierowych. Jeśli dane pojęcie, imię, atak lub lokacja znajduje się w rejestrze kanonu, tłumacz ma bezwzględny obowiązek jego użycia z poprawną polską odmianą).
* **ZASADA FALLBACKU (WŁASNY PRZEKŁAD):** Tylko i wyłącznie wtedy, gdy danego terminu **nie ma w rejestrze kanonu (Poziom 1)**, tłumacz przekłada go we własnym zakresie, stosując kolejne szczeble hierarchii:
  * **Poziom 2: TRIANGULACJA: JAPOŃSKIE AUDIO I KADR > ANGIELSKI SKRYPT** (Japoński dźwięk i obraz stoją bezwzględnie wyżej niż angielski skrypt pośredni).
  * **Poziom 3: TRZY ZŁOTE SOCZEWKI** (Ucho, Świat, Obraz – żywa, naturalnie odmieniona polszczyzna kinowa wg szkoły Barańczaka i Belczyka).
  * **Poziom 4: ERGONOMIA I LIMITY AVT** (17 CPS, semantyczny podział linii, eliminacja sierotek, brak naruszeń montażowych).
  * **Poziom 5: WSKAZÓWKI I KOREKTY UŻYTKOWNIKA** (Uwagi użytkownika traktowane są jako cenne wskazówki jakościowe i impuls do systemowego doskonalenia kodu silnika, a nie jako sztywna dogmatyka ponad regułami profesjonalnego AVT).

### 9. PRAWO ZERO-AI I CZYSTEGO KANONU PAPIEROWEGO (ZERO-AI KNOWLEDGE POLICY)
* Kategoryczny, dożywotni ZAKAZ wprowadzania do słowników, rejestrów kanonu (`manga_canon.py`) i pamięci tłumaczeniowej jakichkolwiek terminów wygenerowanych syntetycznie przez AI lub automatyczne translatory.
* 100% terminów w rejestrze musi pochodzić bezpośrednio z licencjonowanych fizycznych wydań papierowych polskich wydawnictw (Waneko, JPF, Studio JG, Kotori, Hanami, Dango, Egmont) lub recenzowanej bazy Tanuki Manga.
* Wszelkie wartości słownika muszą być czystymi, docelowymi terminami polskimi (bez zanieczyszczeń nawiasami wyjaśniającymi w wartościach docelowych).

### 10. PRAWO MACIERZY INTENCJI PRAGMATYCZNYCH I ZWIĘZŁOŚCI KINOWEJ (PRAGMATIC INTENT & ANTI-BLOAT POLICY)
* Krótkie, wieloznaczne zwroty japońskie (np. *Daijoubu*, *Wakatta*, *Sou da na*, *Shikata ga nai*) muszą być przekładane na podstawie **Macierzy Intencji Pragmatycznych** seiyuu (uspokojenie lęku $\rightarrow$ *„Spokojnie” / „Wszystko w porządku” / „Nie martw się”*, grzeczna odmowa $\rightarrow$ *„Dziękuję, nie trzeba”*, stan fizyczny $\rightarrow$ *„Nic mi nie jest”*, gotowość $\rightarrow$ *„Dam radę”*).
* Bezwzględny zakaz mechanicznego przejmowania rozwlekłych angielskich konstrukcji (np. angielskie *„You don't have to worry”* $\rightarrow$ zakaz rozdmuchiwania do *„Nie musisz się martwić”*, gdy japońskie audio zawiera zwięzłe *Daijoubu*). Tłumacz ma obowiązek zachowania zwięzłości kinowej i naturalnej ekonomii sylab.

### 11. PRAWO NIENARUSZALNOŚCI JAKOŚCI PRZEKŁADU I ZEROWEJ LUKI (ZERO-GAP & PEAK TRANSLATION BASELINE)
* Obecny stan kodu silnika (`cornerstone-v2.0` / commit `1208154`) stanowi **absolutną bazę referencyjną i złoty standard jakości tłumaczenia**.
* Wszystkie przyszłe modyfikacje kodu **MUSZĄ** traktować ten poziom jako nienaruszalne minimum — jakakolwiek regresja językowa, utrata kontekstu lub spłaszczenie dialogu jest traktowana jako błąd krytyczny.
* **Nienaruszalne elementy architektury jakości:**
  1. **100% Bezstratny Przepływ Kontekstu**: Pomiędzy Fazą 1 a Fazą 2 przekazywane są zawsze: `history_context` (z atrybucją mówcy i stanem myśli), `lookahead_events` (z atrybucją mówcy), `character_registry` (z płcią i statusem) oraz ustrukturyzowana `scene_diagnosis` (z Teorią Umysłu).
  2. **Gwarancja Zerowej Luki (Zero-Gap Guarantee)**: Automatyczny Healing Pass w `translate_file` gwarantuje 100% przetłumaczonych linii bez pominięć przez błędy sieciowe lub usterki API.
  3. **Naturalny Ping-Pong Dialogowy (Kognitywistyka AVT)**: Bezwzględny zakaz samotnego „Tak/T-Tak” w odpowiedzi na ostrzeżenia/dyrektywy, pytania otwarte (Wh-questions) oraz pytania z przeczeniem (Echo Agreement / Filar CLIV).
  4. **Całościowy Audytor Jakości Odcinka (`EpisodeQualityGate`)**: Nienaruszalność form adresatywnych (T-V Invariance), higiena interpunkcji, bariera myśli wewnętrznej oraz skaner pozostałości języka angielskiego (English Remainder Sweep).

---

## 🔒 ZASADA WERYFIKACJI PRZYSZŁYCH ZMIAN (REGRESSION GUARD)
Przed zaakceptowaniem i scommitowaniem jakiejkolwiek przyszłej zmiany w kodzie, programista/agent AI jest **bezwzględnie zobowiązany** do:
1. Uruchomienia `.venv\Scripts\python test_system.py` i uzyskania wyniku **34/34 PASSED** (100% skuteczności bez regresji).
2. Weryfikacji, że żadna zmiana nie obniża jakości tłumaczenia, nie narusza reguł lingwistycznych Filarów I – CLXI ani nie usuwa żadnego z mechanizmów Zero-Gap.
3. Potwierdzenia niezmiennika zerowego kosztu (**0.00 PLN**) dla mechanizmów audytu i optymalizacji.
4. Upewnienia się, że żadna zmiana nie spowalnia asynchronicznego dispatchera paczek ani nie zwiększa zużycia tokenów wejściowych.
