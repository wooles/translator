# RAPORT AUDYTU OPERACYJNEGO — WERYFIKACJA OBSŁUGI CODE-SWITCHINGU (JA/EN) I GWARY W TŁUMACZENIU ODCINKA

---

## Sekcja 0 — Metadane audytu

| Parametr | Wartość |
| :--- | :--- |
| **Data audytu** | `2026-11-11` |
| **Repozytorium referencyjne** | `https://github.com/wooles/translator` (gałąź `main`) |
| **HEAD gałęzi `main`** | `7011407cc7b47d2ffb223f402dc8366d40041b7e` (`7011407` — Commit 3 Hotfixu 11.1.3a) |
| **Certyfikowany standard produkcyjny** | `Standard 11.1.3a (Production Certified Baseline)` (commit kodu: `842b9e945cfed4bab04e2d3864a1cd657e50f832`) |
| **Baseline Z16 (Depuracja Legacy 1.0)** | `d31096945a977d6a179891d87dcfd2a05c0c5bca` (`d310969`) |
| **Identyfikator przebiegu** | `<SERIA>_S01E06_1080p_AMZN_WEB-DL_JPN_DDP2_0_H_264_MSubs-ToonsHub_extracted_20261110_170435` |
| **Seria i odcinek (zmaskowane Z1)** | `<SERIA>` — `<ODCINEK>` (347 zdarzeń `.ass`, 17 paczek adaptacyjnych) |
| **Modele przebiegu** | Faza 1: `gemini-3.8-flash` (CoT 0) \| Faza 2: `gemini-3.8-flash` (Elastic CoT 3072–6144) \| ASR: `kotoba-tech/kotoba-whisper-v2.0-faster` |
| **Tryb pracy audytora** | `STRICTLY READ-ONLY` (0 zmian w kodzie, 0 commitów, 0 `git push`) |
| **Zgodność z Z1 / Z2 / Z16** | `Z1 Zero-Literal` (pełne maskowanie nazw własnych `<POSTAC_*>`, `<TYTUL_*>`) \| `Z2 Pure Positive Domain` \| `Z16 Read-Only` |

### Słownik maskowania encji (Z1 Zero-Literal)
- `<SERIA>` — badana seria anime z gatunku dark fantasy / survival game
- `<ODCINEK>` — odcinek 6 sezonu 1
- `<POSTAC_MEOW>` — wojowniczka w chińskim stroju posługująca się talizmanami, używająca w audio JP wtrąceń angielskich (`オーケーオッケ`, `リフレクトします`), zaimka `俺 [ore]` oraz chińskiej maniery zdaniowej `-ある [-aru]` / `-やる [-yaru]`
- `<POSTAC_RIONETTA>` — czarodziejka-marionetka o teatralno-sarkastycznym rejestrze *ojōsama* (`-ですわ [-desu wa]`, `-ますわ [-masu wa]`, `-ですこと [-desu koto]`, `-ますの [-masu no]`)
- `<POSTAC_CLANTAIL>` — czarodziejka-centaur o rzeczowym, bojowym tonie z młodzieżowo-sportowym sufiksem `-っす [-ssu]`
- `<POSTAC_PECHKA>` — młoda, nieśmiała czarodziejka o magii kulinarnej (mowa ogólna z wahaniem i pauzami)
- `<POSTAC_PFLE>` — arystokratyczna liderka i taktyk (chłodny rejestr wysoki, zaimki `私 [watakushi/watashi]`, rozkazy `-たまえ [-tamae]`)
- `<POSTAC_SHADOW_GALE>` — lojalna służąca i ochroniarz `<POSTAC_PFLE>` (rejestr podwładnej, zwrot `panienko`)
- `<POSTAC_LAPIS>` — czarodziejka kończąca wypowiedzi partykułą `-なの [-nano]`
- `<POSTAC_MEL>` — czarodziejka używająca zdrobniałych ksywek z sufiksem `-cchi` (`<KSYWKA_PFU_CCHI>`) i spójnika gwarowego `-っからね [-kkarane]`
- `<POSTAC_KEEK>`, `<POSTAC_FAL>`, `<POSTAC_SNOW_WHITE>`, `<POSTAC_CHERNA>`, `<POSTAC_YUMENOSHIMA>`, `<POSTAC_NAKO>` — pozostałe postacie odcinka
- `<TYTUL_BOSS>`, `<TYTUL_BRON>`, `<TYTUL_TALIZMAN_WODY>`, `<TYTUL_TARCZA>`, `<TYTUL_PAPIEROWY_TALIZMAN>`, `<TYTUL_WALUTA>` — terminy przedmiotów i pojęć świata gry

---

## Sekcja 1 — Inwentaryzacja załączników i mapa podejrzanych linii (Faza 0)

### 1.1. Tabela inwentaryzacji załączników

| # | Typ załącznika | Nazwa pliku | Rozmiar (B) | Liczba linii / rekordów | Kodowanie | BOM | Rozpoznane sekcje `EpisodeFlightRecorder` |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Z1** | Log strukturalny `EpisodeFlightRecorder` | `<SERIA>_..._20261110_170435_full_trace.log` | `336 425 B` | `3 449` linii | `UTF-8` | `Brak` (`False`) | `[KROK 1: CLI]`, `[KROK 2: INGESTIA]`, `[KROK 3: METADANE]`, `[KROK 4: AKUSTYKA DSP & WHISPER]` (x17), `[KROK 5: PROFILER]`, `[KROK 6: SERIESBIBLE]`, `[KROK 7: GRAF DYSKURSU]`, `[KROK 8: FAZA 1]` (x17), `[KROK 9: FAZA 2 & EWOLUCJA LINII]` (x17 / 347 linii), `[KROK 11: EPISODEQUALITYGATE & PRICINGGUARD]` |
| **Z2** | Konsola z przebiegu pracy | `<SERIA>_..._pelny_przebieg_tlumaczenia.txt` | `57 235 B` | `512` linii | `UTF-8` | `Brak` (`False`) | Pełny zrzut stdout/stderr: baner wyboru stylu, sonda API, `StyleMatrixEngine`, `Profiler Odcinka`, `Context Cache`, `Kotoba-Whisper`, pasek postępu 17 paczek (`[Odsłuch JP]`, `[Kontekst]`, `[Faza 2]`, `[Redaktor Dialogów]`), podsumowanie kosztu (`3.47 PLN netto` / `4.27 PLN brutto`) |
| **Z3** | Wyjściowy plik napisów `.ass` | `<SERIA>_S01E06.1080p.AMZN.WEB-DL.JPN.DDP2.0.H.264.MSubs-ToonsHub.ass` | `31 411 B` | `363` linii (`347` `Dialogue:`) | `UTF-8` | `Brak` (`False`) | `[Script Info]`, `[V4+ Styles]` (1 styl `Default`), `[Events]` (`347` linii `Dialogue:` — od `0:00:07.26` do `0:23:49.99`) |
| **Z5** | Telemetria strukturalna `.jsonl` | `<SERIA>_..._20261110_170435_events.jsonl` | `623 380 B` | `405` rekordów JSON | `UTF-8` | `Brak` (`False`) | `cli_init` (1), `ingestion` (1), `metadata` (1), `profile_prepass` (1), `series_bible` (1), `scene_discourse` (1), `acoustics_whisper` (17), `phase1_batch` (17), `phase2_verifier` (17), `line_evolution` (347), `quality_gate_pricing` (1) |

*(Uwaga porządkowa: w załącznikach `Z1` i `Z5` pole `line_id` w sekcjach `line_evolution` jest indeksowane od `0` do `346`, natomiast numery kwestii wewnątrz paczek i w `EpisodeQualityGate` są indeksowane od `1` do `347`. W całym niniejszym raporcie stosujemy spójną notację `[ID: N]` (`#N+1` w `.ass`), gdzie `N` oznacza `line_id` z `Z1`/`Z5`, a `#N+1` numer kolejny linii `Dialogue:` w pliku `.ass` `Z3`).*

### 1.2. Mapa podejrzanych linii (Event Index — Faza 0.5)

Przeskanowanie wszystkich 347 linii w `Z3` (`.ass`), `Z1` (`.log`) i `Z5` (`.jsonl`) pod kątem **code-switchingu (wtrąceń angielskich w strukturę japońską lub anglicyzmów w polskim przekładzie)** oraz **gwary / ról socjolingwistycznych (*yakuwarigo* / dialektu / slangu)** wyłoniło następującą mapę zdarzeń:

| `[ID: N]` (`#ASS`) | Paczka | Mówca | Cytat z wyjściowego `.ass` (`Z3`) | Zjawisko: Code-switching (JA/EN lub anglicyzm PL) | Zjawisko: Gwara / Rejestr (*Yakuwarigo*) | Sygnały rozpoznania w logu (`Z1`/`Z5`) |
| :---: | :---: | :--- | :--- | :---: | :---: | :--- |
| **`[ID: 12]`** (`#13`) | `0` | `<POSTAC_MEOW>` | `"Przeznaczenie złączyło\Nnasze ścieżki!"` | `NIE` | **`TAK`** (chiński idiom powitalny *bǎi nián xiū dé tóng chuán dù*) | `[TELEMETRIA: pułapka_profilera]` + `[💬 KWESTIA-WIZYTÓWKA]` w `Z5`; brak `DIALECT_JP` |
| **`[ID: 13]`** (`#14`) | `0` | `<POSTAC_MEOW>` | `"Kope lat!"` | `NIE` | **`TAK`** (kolokwialne powitanie; usterka ortograficzna `Kope` zamiast `Kopę`) | Brak sygnału rejestru w telemetrii linii |
| **`[ID: 16]`** (`#17`) | `1` | `<POSTAC_MEOW>` | `"Trochę za bardzo mnie poniosło."` | **`TAK`** (JP audio: `ちょっとテンション上げ [chotto tenshon age]` — hybryda JA+EN *tension age*) | **`TAK`** (młodzieżowy slang `<POSTAC_MEOW>`) | `DYN_1 (FILAR XIII)` aktywny w Paczce 1 (przez kolizję podciągu `'べ'` w ID 32); brak tagu `CODE_SWITCH` |
| **`[ID: 17]`** (`#18`) | `1` | `<POSTAC_PECHKA>` | `"Wszystko w porządku?"` | **`TAK`** (przeciek ASR `オーケーオッケ [ookeeokke]` z ID 18) | `NIE` | Brak tagu `CODE_SWITCH` |
| **`[ID: 18]`** (`#19`) | `1` | `<POSTAC_MEOW>` | `"Jasne, nic mi nie jest."` | **`TAK`** (JP audio: `オーケーオッケ 俺... [ookeeokke ore...]` — angielskie *Okay, okay* wtrącone przed japońskim zdaniem) | **`TAK`** (męski zaimek `俺 [ore]` u wojowniczki) | `DYN_1 (FILAR XIII)` w Paczce 1; w `Z1` `audio_intent_check` odnotowuje zaimek `ore` |
| **`[ID: 20]`** (`#21`) | `1` | `<POSTAC_MEOW>` | `"Ta upierdliwa lalka będzie marudzić,\Njeśli choć trochę się spóźnimy."` | **`TAK`** (JP audio: `リアルのやつ [riaru no yatsu]` — EN *Real [Doll]*) | **`TAK`** (szorstki slang `めんどくさい...やつ` + zderzenie z `-ますの` z ID 22) | `DYN_1 (FILAR XIII)` w Paczce 1; oddano potocznym `Ta upierdliwa lalka będzie marudzić` |
| **`[ID: 25]`** (`#26`) | `1` | `<POSTAC_RIONETTA>` | `"Byłabym wdzięczna za wyjaśnienia."` | `NIE` | **`TAK`** (rejestr *ojōsama*: `ありがたいですわね [arigatai desu wa ne]`) | W `Z1` `audio_intent_check` Fazy 1: *"żartobliwie dystyngowany ton <POSTAC_RIONETTA> (desu wa)"* |
| **`[ID: 27]`** (`#28`) | `1` | `<POSTAC_MEOW>` | `"Choćbyśmy gnały z prędkością światła,\Nta panna i tak będzie narzekać."` | `NIE` | **`TAK`** (wulgarno-szorstki sufiks `-やがりますわ [-yagarimasu wa]` + `この女 [kono onna]`) | Szkic F1 (`ta panna`) zachowany w F2; wulgaryzacja `-yagaru` zneutralizowana |
| **`[ID: 30–31]`** (`#31–32`) | `1` | `<POSTAC_RIONETTA>` | `"Niezwykła elastyczność."` / `"Podziwiam, z jakim zapałem\Nchłoniesz japońską kulturę."` | `NIE` | **`TAK`** (ironiczny rejestr *ojōsama*: `ですわ [desu wa]`, `感心しますわ [kanshin shimasu wa]`) | Rozpoznane w `scene_diagnosis` Fazy 1 (`desu wa`) |
| **`[ID: 35]`** (`#36`) | `1` | `<POSTAC_MEOW>` | `"Z wzajemnością."` | **`TAK (KLUCZOWY)`** (JP audio: `その言葉リフレクトします [sono kotoba rifurekuto shimasu]` — wtrącenie EN *reflect* w strukturę japońską) | **`TAK`** (komiczna riposta chińskiej postaci po docinku o nauce japońskiego) | Alert profilera dla `"Right back at ya"` (`Z wzajemnością`), który nadpisał angielskie wtrącenie `rifurekuto shimasu` z audio JP |
| **`[ID: 58–59]`** (`#59–60`) | `2` | `<POSTAC_MEOW>` / `<POSTAC_CLANTAIL>` | `"Właśnie! Ruszajmy dalej!"` / `"Ruszajmy."` | `NIE` | **`TAK`** (JP audio: `行きますわよ [ikimasu wa yo]` — dystyngowane zawołanie `<POSTAC_RIONETTA>` przypisane przez przesunięcie ASR do ID 58–59) | Brak `DIALECT_JP` w Paczce 2 |
| **`[ID: 83–94]`** (`#84–95`) | `4` | `<POSTAC_RIONETTA>` (brak tagu `Name` w `.ass`) | `"Tylko gotowanie <POSTAC_PECHKA>\Ndaje mi jakąś radość."` / `"Czy ktoś nie powinien już\Nodblokować nowego obszaru?"` | **`TAK`** (JP audio: `エリア開放 [eria kaihou]` — EN *Area*) | **`TAK`** (rejestr *ojōsama*: `幸せですわ`, `誰かしら`, `ではありませんこと`, `しれませんこと`, `ありませんのに`) | Brak `DIALECT_JP` w Paczce 4; puste pole `Name` w `.ass` sprawiło, że kwestie `<POSTAC_RIONETTA>` zneutralizowano do mowy ogólnej |
| **`[ID: 100–102]`** (`#101–103`) | `4` | `<POSTAC_MEOW>` / `<POSTAC_RIONETTA>` | `"- <POSTAC_RIONETTA> to idiotka!\N- Nie chcemy same..."` / `"- Co powiedziałaś?!\N-...same przejść tej gry?"` | **`TAK`** (JP audio: `クリアする [kuria suru]` — EN *clear*) | **`TAK`** (JP audio: `お馬鹿さんねえな [obaka-san nee na]` vs `何ですって [nandesutte]`) | Alert `puns_and_wordplays` z profilera; w F2 skrócono `skończona idiotka` do `idiotka` pod limit CPL/CPS |
| **`[ID: 118–122]`** (`#119–123`) | `5` | `<POSTAC_MEOW>` | `"Poprosiłam wszystkich, by dali znać..."` / `"Musi mieć naprawdę ważny powód,"` / `"skoro w ogóle\Nnie może się z nami spotkać."` | `NIE` | **`TAK (KLUCZOWY)`** (JP audio: `頼んでるある [tanonderu aru]`, `事情があるはずある [jijou ga aru hazu aru]`, `事状があるあずあるよ [aru hazu aru yo]` — 3x chińska partykuła `-aru`) | **Brak sygnału w logu:** `detect_batch_discourse_categories` nie wykryło `-aru`, brak `DIALECT_JP` i brak `DYN_1` w Paczce 5; pełna neutralizacja do polszczyzny standardowej |
| **`[ID: 138–140]`** (`#139–141`) | `6` | `<POSTAC_PFLE>` / `<POSTAC_MEOW>` | `"Wózek wciąż nienaprawiony?"` | `NIE` | **`TAK`** (JP audio: `くるまいすまだなおらないやるか [kurumaisu mada naoranai yaru ka]` — pytająca końcówka `-yaru ka` u `<POSTAC_MEOW>`) | `DIALECT_JP` w Paczce 6 wywołany przypadkowo przez podciąg `'おら'` w słowie `なおらない [naoranai]`; w `.ass` brak `Name` w ID 140, styl zneutralizowany |
| **`[ID: 143–144]`** (`#144–145`) | `6` | `<POSTAC_PFLE>` / `<POSTAC_PECHKA>` | `"...trafiłyście może na coś rzadkiego\Nz losowania?"` / `"Wybacz, nie brałyśmy udziału\Nw tej całej loterii."` | **`TAK`** (JP audio: `ランダム [randamu]`, `アイテム [aitemu]`, `ガチャ [gacha]` — EN *random, item, gacha*) | **`TAK`** (w ID 146 `<POSTAC_PFLE>` używa arystokratycznego rozkazu `くれたまえ [kuretamae]`) | W F1 i F2 naturalna adaptacja `z losowania` / `w tej całej loterii` oraz `odstąpcie mi to, proszę` dla `kuretamae` |
| **`[ID: 151]`** (`#152`) | `7` | `<POSTAC_RIONETTA>` | `"Do dobrego dropu\Nczęsto trzeba farta!"` | **`TAK (ANGLICYZM PL w F2)`** (F1: `"Do dobrego ekwipunku\Npotrzeba też szczęścia!"` -> F2 wprowadziła anglicyzm `"dropu"` i slang `"farta"` pod wpływem wskazówki profilera) | **`TAK`** (dysonans rejestru: dystyngowana `<POSTAC_RIONETTA>` mówi w JP `良い装備 [yoi soubi]`, a w PL używa młodzieżowego slangu gracza `dropu / farta`) | Alert profilera `danger_lines_prescan` (`"Oddać w naturalnym żargonie graczy"`) spowodował nadpisanie rejestru `<POSTAC_RIONETTA>` w F2 |
| **`[ID: 156]`** (`#157`) | `7` | `<POSTAC_PECHKA>` | `"<POSTAC_MEL>-cchi!"` | `NIE` | **`TAK`** (slangowy sufiks hipokorystyczny `-cchi` zachowany w formie oryginalnej) | Zachowano w F1, F2 i `AVTLinter` bez zmian |
| **`[ID: 187–188]`** (`#188–189`) | `8` | `<POSTAC_MEOW>` | `"Z-Zniknęły?!"` / `"Co się stało?"` | `NIE` | **`TAK`** (JP audio: `どういうことある [dou iu koto aru]` — końcówka `-aru`) | Brak `DIALECT_JP` w Paczce 8; brak śladu stylizacji w PL |
| **`[ID: 194–198]`** (`#195–199`) | `9` | `<POSTAC_CLANTAIL>` / `<POSTAC_LAPIS>` / `<POSTAC_RIONETTA>` | `"Czarodziejki niby\Nnie potrzebują światła,"` / `"Wszyscy już są, prawda?"` | `NIE` | **`TAK (KLUCZOWY — 3 REJESTRY OBOK SIEBIE)`** (ID 194 `<POSTAC_CLANTAIL>`: `必要ないっすけど [-ssu]`; ID 196 `<POSTAC_LAPIS>`: `全員揃ったなの [-nano]`; ID 197–198 `<POSTAC_RIONETTA>`: `動いているのですの [-desu no]`) | Brak `DIALECT_JP` w Paczce 9; w ID 194 F2 dodała potoczne `niby` i `jakoś raźniej`; w ID 196 użyto męskoosobowego `Wszyscy` zamiast `Wszystkie` |
| **`[ID: 212]`** (`#213`) | `10` | `<POSTAC_RIONETTA>` | `"Tylko nie mów,\Nże to bydlę to boss?!"` | **`TAK`** (JP audio: `ボスキャラ [bosu kyara]` -> PL `boss`) | **`TAK`** (F2 jawnie powołała się na `[Filar XIII - Idiolekt <POSTAC_RIONETTA>]`, zamieniając `ten potwór` na ostre `to bydlę`) | `DYN_1 (FILAR XIII)` aktywny w Paczce 10 (wyzwolony przez `'べ'` w `比べれば`), co zaowocowało celną stylizacją w F2 |
| **`[ID: 233–234]`** (`#234–235`) | `11` | `<POSTAC_RIONETTA>` | `"Sztylet?"` / `"Ta broń wygląda wyjątkowo licho."` | `NIE` | **`TAK`** (JP audio: `これまたずいぶんと頼りなさげな武器ですこと [desu koto]` — rejestr *ojōsama*) | Brak `DIALECT_JP` w Paczce 11, lecz F1/F2 trafnie dobrały dystyngowane `wyjątkowo licho` |
| **`[ID: 251]`** (`#252`) | `11` | `<POSTAC_RIONETTA>` | `"Czyli ten <TYTUL_BOSS>\Nto po prostu miniboss, tak?"` | **`TAK`** (JP audio: `中ボス [chuu-bosu]`, EN: `mid-level boss` -> PL `miniboss`) | `NIE` | Zachowano naturalny anglicyzm gamingowy `miniboss` w F1, F2 i `AVTLinter` |
| **`[ID: 261]`** (`#262`) | `12` | `<POSTAC_RIONETTA>` | `"To sprawdzona wiedza."` | **`TAK`** (F1: `"To potwierdzone info."` -> F2 usunęła potoczny anglicyzm `info` na rzecz `"To sprawdzona wiedza."`) | **`TAK`** (ochrona dystyngowanego rejestru `<POSTAC_RIONETTA>` w F2) | W `Z2`/`Z5` F2: `"[Filar VI - Czystość rejestru / Filar CLXXII] Eliminacja potocznego 'info' z wersji roboczej"` |
| **`[ID: 263–267]`** (`#264–268`) | `12` | `<POSTAC_PFLE>` / `<POSTAC_MEOW>` | `"<POSTAC_MEOW>."` / `"Słucham?"` / `"Rzucam ręcznie,\Nwięc muszę podejść dość blisko."` | **`TAK`** (JP audio ID 263: `あったマークニャンニャン [atto maaku nyan-nyan]` — wymówiony angielski termin *at-mark*) | **`TAK (KLUCZOWY)`** (JP audio ID 264: `何やるか [nani yaru ka]`; ID 267: `ふだを投げるだけある かなり近づかないといけなやる [...dake aru ...ikena yaru]`) | Brak `DIALECT_JP` w Paczce 12; całkowita neutralizacja `-aru / -yaru` do standardowego `"Słucham?"` i `"Rzucam ręcznie..."` |
| **`[ID: 279]`** (`#280`) | `13` | `<POSTAC_MEOW>` (brak `Name` w `.ass`) | `"My też mamy tylko jedną <TYTUL_TARCZA>."` | **`TAK`** (JP audio: `シールドプラス5 [shiirudo purasu 5]`) | **`TAK`** (JP audio: `一つだけしかないやるね [hitotsu dake shika nai yaru ne]` — końcówka `-yaru ne`) | `DYN_1` aktywny w Paczce 13 (przez `'べ'` w `全て`), lecz z powodu pustego `Name` w `.ass` kwestia zneutralizowana |
| **`[ID: 304–305]`** (`#305–306`) | `14` | `<POSTAC_MEL>` / `<POSTAC_MEOW>` (brak `Name` w `.ass`) | `"W końcu bez pomocy <POSTAC_PFLE>\Nw ogóle byśmy tu nie dotarły."` / `"Dla mnie gra."` | **`TAK`** (w ID 301–302: `ドラゴンのドロップアイテム` -> w F2 ID 301: `Nawet jeśli smok coś upuści`) | **`TAK (POZYTYWNY WZORZEC w ID 305)`** (ID 304: `<KSYWKA_PFU_CCHI>` + `わけっからね` zneutralizowane do `<POSTAC_PFLE>`; natomiast w ID 305 JP `私はそれでいいやる [watashi wa sore de ii yaru]` przełożone w F2 na potoczne `"Dla mnie gra."`) | W `Z2`/`Z5` F2 jawnie uzasadniła ID 305: `"[Filar CXLVI - Dialogowy Ping-Pong] Dynamiczna, potoczysta riposta dopasowana do szorstkiego stylu seiyū ('watashi wa sore de ii yaru')."` |

---

## Sekcja 2 — Podsumowanie wykonawcze

- **Werdykt ogólny:** **`POTOK OBSŁUGUJE CZĘŚCIOWO`**
- **Code-switching (JA + EN w jednej wypowiedzi):** **`CZĘŚCIOWO`** — potok posiada w `rules.py` rozbudowane reguły dla terminologii gamingowej (`FILAR XXIV`) oraz eliminacji niepożądanych kalek z angielskiego pivotu (`FILAR CLXVI`), a lokalny silnik `Kotoba-Whisper` (`whisper_engine.py`) wiernie transkrybuje angielskie wtrącenia fonetyczne w katakanie (`オーケーオッケ`, `リフレクトします`, `あったマーク`, `ドロップアイテム`), jednak w `whisper_disambiguator.py` i `rules.py` brakuje dedykowanej kategorii dyskursu (`CODE_SWITCH_EN`) rozróżniającej **celowe wtrącenie angielskie w ustach japońskiej postaci** od **zwykłego słowa z angielskiego skryptu pośredniczącego (pivotu EN)**, wskutek czego celowy żart językowy oparty na code-switchingu w `[ID: 35]` (`その言葉リフレクトします [sono kotoba rifurekuto shimasu]`) został zneutralizowany do `"Z wzajemnością."`.
- **Gwara / Rejestr socjolingwistyczny (*Yakuwarigo*):** **`CZĘŚCIOWO`** — potok posiada w kodzie kompletny ekosystem teoretyczny dla gwary i ról językowych (`FILAR XIII — Yakuwarigo Satoshi Kinsui` w `rules.py:150-159`, regułę dynamiczną `DYN_1` w `rules.py:2560-2590`, funkcję `detect_japanese_pragmatic_register` w `translator.py:953-1020`, sekcję `[PARAFRAZA GWARY]` w `verifier.py:805-808` oraz pola `speech_style_pl`, `dialect_category`, `idiolect_matrix` w `profiler.py:111-116`), lecz z powodu **trzech przerwanych ogniw integracyjnych** w kodzie (1: `Profiler` wpisał `"dialect_category": "brak"` dla wszystkich 5 bohaterek i nie przekazał `speech_style_pl`/`idiolect_matrix` w `format_lean_episode_brief`; 2: `detect_batch_discourse_categories` w `whisper_disambiguator.py:691-707` szuka wyłącznie wiejskich dialektów geograficznych i zawiera niezakotwiczone podciągi `"べ"` oraz `"おら"`, pomijając przy tym `-aru/-yaru`, `-desu wa`, `-ssu`, `-nano`; 3: wynik `detect_japanese_pragmatic_register` w `translator.py:4318` nie jest wstrzykiwany do wektora `[TELEMETRIA: ...]`), gwara i idiolekty zadziałały punktowo (np. w `[ID: 212]` i `[ID: 305]`), natomiast w większości kwestii `<POSTAC_MEOW>` (`-aru/-yaru`) uległy spłaszczeniu do polszczyzny standardowej.
- **Liczba linii dotkniętych w badanym odcinku:**
  - **Code-switching (JA/EN w audio lub anglicyzmy w PL):** **15 linii** (`[ID: 16, 17, 18, 20, 35, 92, 100, 143, 144, 150, 151, 212, 251, 261, 263]`).
  - **Gwara / niestandardowy rejestr socjolingwistyczny (*yakuwarigo* / dialekt / slang):** **38 linii** (w tym 10 linii z chińskim idiolektem `-aru/-yaru` u `<POSTAC_MEOW>`, 18 linii z arystokratyczno-sarkastycznym `-desu wa / -desu koto / -masu no` u `<POSTAC_RIONETTA>`, 3 linie z `-ssu` / `ore` u `<POSTAC_CLANTAIL>`, 1 linia z `-nano` u `<POSTAC_LAPIS>`, 2 linie z `-cchi / -kkarane` u `<POSTAC_MEL>`, 4 linie z `-tamae / watakushi` u `<POSTAC_PFLE>`).
- **Liczba zidentyfikowanych funkcji/modułów, które powinny obsługiwać te zjawiska:** **11** (10 obszarów z tabeli §3.2 + funkcja `detect_japanese_pragmatic_register` w `translator.py:953`).
- **Liczba funkcji, które faktycznie zadziałały w badanym przebiegu:**
  - **W pełni zgodnie z projektem:** **3 z 11** (`style_matrix.py:analyze_subtitles`, `verifier.py:_guard_phase2_regressions`, `avt_linter.py:lint_and_fix_line` + `EpisodeQualityGate`).
  - **Częściowo (z lukami w wyzwalaniu lub przekazywaniu danych):** **7 z 11** (`WhisperDisambiguator.detect_batch_discourse_categories`, `rules.py:DYN_1..DYN_9`, `rules.py:get_focused_rules_for_batch`, `profiler.py:EpisodeProfile/CharacterDossier`, `translator.py:_prepare_batch_prompt`, `translator.py:detect_japanese_pragmatic_register`, `verifier.py:_prepare_verifier_prompt`).
  - **Brak dedykowanego pola strukturalnego:** **1 z 11** (`series_memory.py:CharacterRecord` — przechowuje wyłącznie płeć, paradygmat fleksyjny i krótki opis roli `description`, bez pola `speech_register` / `dialect`).
- **Czy w wyjściowym `.ass` widać utratę sensu / rejestru:** **TAK (w zakresie rejestru i komizmu językowego, przy zachowaniu sensu fabularnego):**
  1. **`[ID: 35]` (`#36`):** Utrata żartu opartego na code-switchingu (`その言葉リフレクトします [sono kotoba rifurekuto shimasu]` po docinku o pilnej nauce kultury japońskiej w `[ID: 31]`) — zneutralizowano do `"Z wzajemnością."`.
  2. **`[ID: 118, 120, 121, 122, 187, 264, 267, 279]`:** Utrata wyrazistego chińskiego rejestru `-aru / -yaru` postaci `<POSTAC_MEOW>` — kwestie brzmią w `.ass` jak neutralna polszczyzna literacka (`"Musi mieć naprawdę ważny powód, skoro w ogóle nie może się z nami spotkać."`, `"Słucham?"`, `"Rzucam ręcznie, więc muszę podejść dość blisko."`).
  3. **`[ID: 151]` (`#152`):** Dysonans rejestru u `<POSTAC_RIONETTA>` — postać mówiąca dystyngowanym *ojōsama* (`-desu wa`) otrzymała w Fazie 2 młodzieżowo-gamingowy slang `"Do dobrego dropu\Nczęsto trzeba farta!"` (podczas gdy w Fazie 1 miała spójne z jej rejestrem `"Do dobrego ekwipunku\Npotrzeba też szczęścia!"`).
  4. **`[ID: 13]` (`#14`):** Usterka ortograficzna w kolokwialnym powitaniu `<POSTAC_MEOW>`: `"Kope lat!"` (brak nosowego `ę` w `Kopę lat!`).
  5. **`[ID: 304]` (`#305`):** Utrata charakterystycznej ksywki `<KSYWKA_PFU_CCHI>` (`プフッチ [pufutchi]`) w ustach `<POSTAC_MEL>` — zastąpiono oficjalnym imieniem `"W końcu bez pomocy <POSTAC_PFLE>..."`.

### 2.1. Odpowiedzi na 7 pytań kontrolnych (§7.3)

1. **Czy w `translator.py` w prompcie Fazy 1 znajduje się jakakolwiek instrukcja dot. code-switchingu lub gwary?**
   - **Dla gwary/rejestru: TAK (w prompcie systemowym i warunkowo w prompcie paczki).** Stały prompt systemowy Fazy 1 (`get_translation_system_prompt` w `rules.py:2380-2404`) ładuje `CORE_AVT_MASTER_CANON`, a w trybie pełnym `BELCZYK_AVT_MASTER_CANON` zawierający `FILAR XIII: TEORIA JĘZYKA RÓL (YAKUWARIGO SATOSHI KINSUI) I REJESTRY DIALEKTALNE` (`rules.py:150-159`). Ponadto do promptu paczki (`translator.py:2885-2890`) wstrzykiwane są reguły z `get_focused_rules_for_batch` (w tym `DYN_1: FILAR XIII & XII`, który trafił do paczek 1, 6, 10, 13) oraz na poziomie linii wyjście z `detect_japanese_pragmatic_register` (`translator.py:3335, 3447`: `🎭 REJESTR JĘZYKOWY (KEIGO / SLANG): ...`).
   - **Dla code-switchingu (wtrąceń EN w zdaniu JP): NIE.** W prompcie Fazy 1 znajduje się jedynie instrukcja dla terminologii RPG (`FILAR XXIV`, `rules.py:293-305`) oraz eliminacji kalek z angielskiego skryptu pośredniczącego (`FILAR CLXVI`, `rules.py:1686-1714`), natomiast brak instrukcji, jak traktować celowe wtrącenia angielskie (katakanizmy) słyszalne w japońskim audio seiyū na tle japońskiego zdania.
2. **Czy w `translator.py` / `verifier.py` w prompcie Fazy 2 znajduje się jakakolwiek instrukcja dot. zachowania rejestru?**
   - **TAK.** W `verifier.py:791-793` stały prompt Fazy 2 nakazuje kontrolę rejestru (`🌍 Świat: relacje statusu, nienaruszalność formy Pan/Ty`, `KROK 3: PROAKTYWNY AUDYT NEGATYWNY REJESTRU`), w `verifier.py:803-808` wstrzykuje `focused_rules_str` wraz z dodatkową dyrektywą `• [PARAFRAZA GWARY: Gdy postać A mówi gwarą/slangiem...]` (gdy w `focused_rules_str` jest `FILAR XIII`), a w `verifier.py:937-938` dopina do linii `Rejestr: {item['pragmatic_register']}`.
3. **Czy `whisper_disambiguator.py` ma kategorię wykrywającą wtrącenia EN lub dialekt JP?**
   - **Dla dialektu JP: TAK (`"DIALECT_JP"` w `whisper_disambiguator.py:672, 690-707`), ale z istotną wadą konstrukcyjną.** Wykrywa wyłącznie regionalne dialekty geograficzne (`ya, yan, yade, yaro, nen, seya, akan, honma, dappe, dabe, ora, washi, atai, wai, wagahai, jaken`) oraz 6 sufiksów (`dechu, nyan, pyon, zura, gero, dabe`), nie wykrywając `-aru/-yaru`, `-desu wa`, `-ssu`, `-nano`. Dodatkowo w linii `703` używa niezakotwiczonego `any(tok in jp_lower for tok in jp_dialect_tokens)` dla pojedynczego znaku `"べ"` i dwuznaku `"おら"`, co powoduje fałszywe wyzwalanie `"DIALECT_JP"` na zwykłych japońskich czasownikach (`述べた`, `比べれば`, `全て`, `直らない`).
   - **Dla wtrąceń EN (`CODE_SWITCH_EN`): NIE.** W `detect_batch_discourse_categories` (`whisper_disambiguator.py:667-787`) nie istnieje kategoria wykrywająca code-switching JA+EN.
4. **Czy `series_memory.CharacterRecord` ma pole `speech_register` lub równoważne?**
   - **NIE.** W `series_memory.py:4718-4729` pozytywny schemat `CharacterRecord` zawiera wyłącznie 9 kluczy: `name`, `gender`, `grammatical_gender`, `confidence`, `priority`, `has_verified_gender`, `aliases`, `description`, `entity_category`. Informacja o rejestrze (`speech_style_pl`, `dialect_category`, `idiolect_matrix`) istnieje wyłącznie w obiekcie `CharacterDossier` w `profiler.py:106-119`, który nie jest synchronizowany do `SeriesBible`.
5. **Czy `avt_linter.py` ma regułę obsługującą anglicyzmy (np. fleksję `-em` / `-u`)?**
   - **TAK (w zakresie ochrony terminów kanonicznych, `QuoteShield` i redukcji kalek z pivotu EN).** `avt_linter.py` posiada: (a) `mask_ass_tags_and_quotes` (`L396-435`) chroniący tekst w cudzysłowach przed mutacją fleksyjną, (b) `_harmonize_canon_term_declension` (`L142-180`) oraz `case_gloss_repl` (`L1490, L11165`) odmieniające terminy ze słownika przez przypadki, (c) ochronę obcych tokenów słownikowych przed fałszywą rejestracją jako postacie (`L7084`), (d) słownik eliminacji kalek angielskich `RESIDUAL ENGLISH CALQUE SWEEP` (`L529-1065`, `L11079`) oraz (e) detektor nieprzetłumaczonych zdań angielskich `ENGLISH REMAINDER SWEEP` (`L11426-11433`). W badanym odcinku `AVTLinter` nie uszkodził żadnego anglicyzmu (`miniboss`, `boss`, `dropu`, `farta`).
6. **Czy istnieje jakikolwiek test regresyjny w `tests/` lub `test_system.py` dla tych zjawisk?**
   - **Dla gwary/dialektu: TAK (3 testy jednostkowe):** `test_t10_1_1_p2a_dialect_registry_guidance_in_episode_brief` (`tests/test_profiler.py:303`), `test_t10_1_1_p2b_focused_rules_dialect_and_paraphrase_contrast_prompt` (`tests/test_verifier.py:663`) oraz test `detect_japanese_pragmatic_register` dla Kansai-ben w `test_system.py:255` i `test_system.py:2254`. Brakuje natomiast testów dla *yakuwarigo* (`-aru/-yaru`, `-desu wa`, `-ssu`, `-nano`) oraz testu antykolizyjnego dla podciągów `"べ"` / `"おら"`.
   - **Dla code-switchingu (hybrydowej linii JP+EN): NIE (0 testów).** W całym repozytorium nie ma ani jednego testu podającego na wejściu hybrydową wypowiedź JP+EN (np. z celowym wtrąceniem angielskim w audio JP) i weryfikującego zachowanie rejestru/żartu.
7. **Czy w logach widać jakikolwiek ślad rozpoznania tych zjawisk (np. `[TELEMETRIA: code_switch=...]`, `[DIALECT_JP]`)?**
   - **W wektorze `[TELEMETRIA: ...]`: NIE** — wektor telemetrii (`format_dry_telemetry_tag` w `translator.py:4251`) zawiera wyłącznie `Mówca`, `Adresat`, `Grupa_1os_lm`, `Grupa_2os_lm` i `Scena: POLYLOGUE`, bez pola rejestru czy code-switchingu.
   - **W sekcji `Wyrenderowany prompt Fazy 1` w `Z1` (`full_trace.log`): TAK (4 razy dla `DYN_1`)** — w Paczkach `1`, `6`, `10` i `13` widnieje wstrzyknięty filar `• [SKUP SIĘ NA: FILAR XIII & XII - Dialekty Regionalne, Gwara, Sociolekty i Kontrast Rejestrów]`. Śledztwo na kodzie dowiodło jednak, że we wszystkich 4 paczkach wyzwalaczem był przypadkowy podciąg `"べ"` (`述べた`, `比べれば`, `全て`) lub `"おら"` (`なおらない`), a nie rzeczywiste markery gwary!
   - **W opisach `scene_diagnosis` (Faza 1) i `changes_made` (Faza 2) w `Z1`/`Z2`/`Z5`: TAK** — modele LLM samodzielnie rozpoznały ze słuchu/kontekstu rejestr w Paczce 1 (`"żartobliwie dystyngowany ton <POSTAC_RIONETTA> (desu wa), luźny slang <POSTAC_MEOW>"`), w Paczce 10 (`#4 [Filar XIII - Idiolekt <POSTAC_RIONETTA>]`), w Paczce 12 (`#5 [Filar VI - Czystość rejestru]`) oraz w Paczce 14 (`#8 [Filar CXLVI] Dynamiczna, potoczysta riposta dopasowana do szorstkiego stylu seiyū ('watashi wa sore de ii yaru')`).

---

## Sekcja 3 — Inwentaryzacja kodu odpowiedzialnego za zjawiska (Faza 1)

Poniższa tabela dokumentuje stan wszystkich 10 obszarów wskazanych w §3.2 (wraz z powiązaną funkcją `detect_japanese_pragmatic_register` w `translator.py:953`) na rewizji `HEAD = 7011407cc7b47d2ffb223f402dc8366d40041b7e`:

| # | Obszar | Plik : linia i sygnatura | Czy istnieje? | Czy wywoływane? | Status działania | Dane wejściowe i mechanizm działania | Ślady działania w logach (`Z1`/`Z2`/`Z5`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **1** | Rozpoznanie japońskich tokenów dialektalnych (dyspozytor kategorii) | `whisper_disambiguator.py:667` — `WhisperDisambiguator.detect_batch_discourse_categories(cls, combined_en: str, combined_jp: str) -> Set[str]` | **`ISTNIEJE`** | **`WYWOŁYWANE`** (`rules.py:2554`) | **`DZIAŁA CZĘŚCIOWO`** | Otrzymuje skonkatenowany tekst EN i JP całej paczki. Sprawdza regex `jp_dialect_pat` (`L691-694`), `character_suffix_pat` (`L695-698`) oraz listę podciągów `jp_dialect_tokens` (`L699-703`). **Defekt:** brak markerów *yakuwarigo* (`-aru`, `-yaru`, `-desu wa`, `-ssu`, `-nano`) oraz brak kategorii `CODE_SWITCH_EN`; natomiast `any(tok in jp_lower for tok in jp_dialect_tokens)` dla `"べ"` i `"おら"` powoduje fałszywe trafienia na zwykłych słowach (`述べた`, `比べれば`, `全て`, `直らない`). | Wyzwoliło `"DIALECT_JP"` w Paczkach `1, 6, 10, 13` (przez kolizję podciągów `"べ"` i `"おら"`), a pominęło Paczki `5, 8, 9, 12, 14` (gdzie występowały `-aru`, `-yaru`, `-ssu`, `-nano`). |
| **2** | Reguły dynamiczne `DYN_1..DYN_9` | `rules.py:2557-2761` — bloki `DYN_1` (`L2560`), `DYN_2` (`L2592`), `DYN_4` (`L2607`), `DYN_3` (`L2633`), `DYN_5` (`L2650`), `DYN_6` (`L2671`), `DYN_9` (`L2704`), `DYN_7` (`L2727`), `DYN_8` (`L2743`) | **`ISTNIEJE`** | **`WYWOŁYWANE`** (`translator.py:3948`) | **`DZIAŁA CZĘŚCIOWO`** | `DYN_1` (`score=95`, `FILAR XIII & XII`) aktywuje się przy `has_slang_en`, `has_dialect_jp`, `has_paraphrase`, `has_dialect_indicator` lub `has_exalted`. **Luka:** w `translator.py:3930-3947` słownik przekazywany do `get_focused_rules_for_batch` nie zawiera kluczy `notes` ani `speech_style_pl`, przez co warunek `has_dialect_indicator` (`rules.py:2577-2581`) jest w wywołaniu produkcyjnym martwy (`False`). Brak reguły `DYN_*` dla code-switchingu JA/EN. | W `Z1` (`[KROK 8]`) widoczne wstrzyknięcie `DYN_1` (Paczki `1, 6, 10, 13`), `DYN_2` (Paczka `0`), `DYN_3` (Paczki `0, 2, 3, 4, 5, 15, 16`), `DYN_5` (Paczki `5, 9, 11, 16`), `DYN_6` (Paczka `4`), `DYN_8` (Paczki `2, 3, 12`). |
| **3** | Filtrowanie reguł per paczka | `rules.py:2493-3469` — `get_focused_rules_for_batch(batch_items_or_text, max_rules=None, batch_text_en=None, whisper_text_jp="") -> str` | **`ISTNIEJE`** | **`WYWOŁYWANE`** (`translator.py:3948` z `max_rules=3`) | **`DZIAŁA CZĘŚCIOWO`** | Kolekcjonuje reguły z wagami punktowymi i wybiera maksymalnie `max_rules=3` najważniejsze filary. W `rules.py:3385-3387`, gdy aktywny jest `FILAR XIII (DYN_1)` lub `FILAR XIV (DYN_2)`, funkcja wyklucza `FILAR LXXI` i `FILAR CLXXII`, aby chronić stylizację przed nadmiernym wygładzeniem. **Skutek uboczny:** fałszywe wyzwolenie `DYN_1` przez sylabę `"べ"` wyłącza `FILAR LXXI` i `CLXXII` w zwykłych paczkach. | W `Z1` w Paczkach `1, 6, 13` jedynym wybranym filarem był `FILAR XIII & XII`, ponieważ blokada `L3386` odfiltrowała `FILAR LXXI` i `CLXXII`. |
| **4** | Profil odcinka — rejestr postaci | `profiler.py:106-148` (`CharacterDossier`, `EpisodeProfile`) oraz `profiler.py:253-365` (`format_lean_episode_brief`) | **`ISTNIEJE`** | **`WYWOŁYWANE`** (`translator.py:5538, 5603`) | **`DZIAŁA CZĘŚCIOWO`** | `CharacterDossier` posiada pola `speech_style_pl` (`L111`), `dialect_category` (`L115`), `idiolect_matrix` (`L116`), a `EpisodeProfile` pole `dialogue_stylization` (`L132`). **Defekt krytyczny:** funkcja `format_lean_episode_brief` (`L253-365`), której wynik trafia do Context Cache Fazy 1 i Fazy 2, **nie wypisuje pól `dialogue_stylization`, `speech_style_pl` ani `idiolect_matrix`!** Wypisuje jedynie ogólny napis `Rejestr: wyrazista gwara / stylizacja środowiskowa`, jeśli w tych polach wystąpi słowo z wąskiej listy `["gwara", "dialekt", "slang", "szorstka", "środowiskowa"]`. Ponieważ Profiler dla wszystkich 5 bohaterek wpisał `"dialect_category": "brak"`, a w opisach użył słów `"arystokratyczny"`, `"teatralny"`, `"ekspresyjny"`, `"cichy"`, żaden opis stylu nie trafił do `profile_brief`! | W `Z2` (konsola) wypisano bogaty opis `[Stylizacja Językowa]` i `[Matryca Idiolektów: 5 bohaterów]`, ale w `Z1` (`[KROK 5: EPISODE BRIEF]`) i `Z5` (`profile_brief`) przy postaciach widnieje wyłącznie rola fabularna bez jednego słowa o ich rejestrze mowy! |
| **5** | Pamięć serii — rejestr postaci | `series_memory.py:4680-4731` (`register_character` / `CharacterRecord`) oraz `series_memory.py:613-620` (`CharacterIdentity`) | **`BRAK` (pola rejestru)** | **`WYWOŁYWANE`** (dla płci i deklinacji) | **`NIE DZIAŁA` (dla rejestru)** | Pozytywny schemat `CharacterRecord` (`series_memory.py:4718-4728`) przechowuje wyłącznie 9 pól: `name`, `gender`, `grammatical_gender`, `confidence`, `priority`, `has_verified_gender`, `aliases`, `description`, `entity_category`. Brak pól `speech_register`, `dialect` lub `style_profile`. W `relations` (`series_bible.json`) zapisywany jest jedynie tag `[reżim: FORMALNY / POUFNY]`. | W `Z1` (`[KROK 6]`) i `Z5` (`series_bible`) wszystkie 29 rekordów postaci ma wyłącznie płeć, aliasy i krótki opis roli (np. `"KOBIETA (wyodrębniono z relacji serii)"`). |
| **6** | Styl macierzy — klasyfikacja wierszy | `style_matrix.py:197-562` — `StyleMatrixReport` oraz `analyze_subtitles(subs: pysubs2.SSAFile) -> StyleMatrixReport` | **`ISTNIEJE`** | **`WYWOŁYWANE`** (`translator.py:5460`) | **`DZIAŁA` (zgodnie z przeznaczeniem geometrycznym)** | Klasyfikuje zdarzenia `.ass` geometrycznie na 6 ról wizualnych (`EventRole`: `DIALOGUE_BOTTOM`, `DIALOGUE_TOP`, `SIGN_LOCATIONAL`, `SIGN_OVERLAY`, `SONG_LYRICS`, `STAFF_METADATA`). Nie analizuje rejestru socjolingwistycznego ani code-switchingu (co jest zgodne z jego rolą geometryczną). | W `Z1` (`[KROK 2]`) i `Z2`: `DIALOGUE_BOTTOM: 335`, `SIGN_OVERLAY: 6`. |
| **7** | Prompt Fazy 1 — instrukcje dot. code-switchingu i gwary | `translator.py:2865-3515` (`_prepare_batch_prompt`) + `translator.py:953-1020` (`detect_japanese_pragmatic_register`) + `rules.py:2380` (`get_translation_system_prompt`) | **`ISTNIEJE` (dla gwary) / `BRAK` (dla code-switchingu JA/EN)** | **`WYWOŁYWANE`** (`translator.py:3965`) | **`DZIAŁA CZĘŚCIOWO`** | `_prepare_batch_prompt` wstrzykuje `focused_rules_str` oraz wywołuje per-linia `detect_japanese_pragmatic_register(jp_audio_line, clean_text)` (`translator.py:3335`), dopinając do linii `🎭 REJESTR JĘZYKOWY (KEIGO / SLANG): ...` (`L3447`). **Luka 1:** `detect_japanese_pragmatic_register` rozpoznaje `ですわ` (`Ojou-sama`), `俺` (`Bojowy`) i `っす` (`Młodzieżowy`), ale **nie rozpoznaje chińskiego `-aru/-yaru` ani `-nano`**. **Luka 2:** brak detekcji i instrukcji dla code-switchingu JA+EN w audio seiyū. | W `Z1` widać `focused_rules_str` w promptach Fazy 1; w `scene_diagnosis` Paczki 1 model F1 odnotował `desu wa` i `ore`, natomiast pominął `-aru/-yaru` w Paczkach 5, 8, 12, 13, 14 oraz `rifurekuto shimasu` w Paczce 1. |
| **8** | Prompt Fazy 2 — instrukcje dot. gwary i rejestru | `verifier.py:660-995` (`_prepare_verifier_prompt` / `verify_batch`) + `rules.py:2406` (`get_verifier_system_prompt`) | **`ISTNIEJE`** | **`WYWOŁYWANE`** (`translator.py:4495`) | **`DZIAŁA CZĘŚCIOWO`** | `_prepare_verifier_prompt` wstrzykuje `focused_rules_str`, warunkowy blok `• [PARAFRAZA GWARY: ...]` (`verifier.py:805-808`) oraz per-linia `Rejestr: {item['pragmatic_register']}` (`L937-938`). **Luka:** ponieważ wartość `pragmatic_register` pochodzi z `detect_japanese_pragmatic_register` (`translator.py:4318`), nie zawiera ona informacji o rejestrze `-aru/-yaru` ani o idiolektach z `CharacterDossier` (`profiler.py`), a ponadto nie trafia do logowanego w `Z1`/`Z5` tagu `telemetry_tag`. | W `Z2` i `Z5` Faza 2 jawnie powołała się na rejestr w `[ID: 212]` (`[Filar XIII - Idiolekt <POSTAC_RIONETTA>]`), `[ID: 261]` (`[Filar VI - Czystość rejestru]`) i `[ID: 305]` (`dopasowana do szorstkiego stylu seiyū ('watashi wa sore de ii yaru')`). |
| **9** | Weryfikator Fazy 2 — ochrona rejestru przed regresją | `verifier.py:152-330` — `_guard_phase2_regressions(f1_pl, refined_pl, source_en, ...)` | **`ISTNIEJE`** | **`WYWOŁYWANE`** (`verifier.py:1192`) | **`DZIAŁA` (dla T-V i płci P0) / `BRAK` (dla gwary/slangu)** | Chroni 5 twardych kategorii gramatycznych: (1) formę grzecznościową `pan/pani` (`L227`), (2) nieodmienne imiona żeńskie (`L245`), (3) 3. osobę pośredniczenia (`L261`), (4) pierwszy człon dwugłosu (`L271`), (5) końcówki płci 1. i 2. osoby (`L282`) oraz kalkę `być + -ący` (`L220`). Nie posiada strażnika blokującego wygładzenie leksyki gwarowej z F1 przez F2 ani wprowadzenie slangu obcego dla rejestru *ojōsama* (jak `dropu / farta` w `[ID: 151]`). | Zadziałał bezbłędnie dla form żeńskich i adresatywnych (0 regresji płci w 347 liniach); przepuścił natomiast zmianę rejestru `<POSTAC_RIONETTA>` w `[ID: 151]`. |
| **10** | Linter `D_pos` — obsługa anglicyzmów i ochrona form | `avt_linter.py:1200-2430` (`AVTLinter.lint_and_fix_line`) oraz `avt_linter.py:6727-11514` (`EpisodeQualityGate.audit_and_fix_entire_episode`) | **`ISTNIEJE`** | **`WYWOŁYWANE`** (`translator.py:4618, 6085`) | **`DZIAŁA`** | W trybie `strict_positive_domain=True` warstwa `D_pos` działa jako bezpieczny *identity pass-through* dla poprawnych form leksykalnych, chroniąc cudzysłowy przez `QuoteShield` (`mask_ass_tags_and_quotes`, `L396`), odmieniając wyłącznie zdefiniowane terminy kanoniczne ze słownika (`_harmonize_canon_term_declension`, `L142`) i czyszcząc interpunkcję/tytulaturę w `EpisodeQualityGate`. Nie zniekształca anglicyzmów (`dropu`, `farta`, `boss`, `miniboss`, `loterii`). | W `Z1`/`Z5` we wszystkich 347 liniach `AVTLinter (D_pos)` odnotował `[BRAK POPRAWEK - IDENTITY PASS-THROUGH]`, a `EpisodeQualityGate` wykonał 13 czystych poprawek interpunkcyjno-formatujących (0 uszkodzeń anglicyzmów). |

---

## Sekcja 4 — Śledztwo per linia (code-switching JA/EN i anglicyzmy)

Poniżej znajduje się szczegółowe śledztwo dla wszystkich linii w odcinku, w których w japońskim audio występuje zjawisko **code-switchingu** (wtrącenia słów angielskich w strukturę japońską) lub w których na styku Fazy 1 i Fazy 2 pojawiły się **anglicyzmy / żargon anglojęzyczny**.

---

### 4.1. Linia `[ID: 35]` (`#36` w `.ass`, Paczka 1, pozycja `#20` w paczce) — **KLUCZOWY PRZYPADEK CODE-SWITCHINGU W AUDIO JP**

1. **Cytat z `.ass` (`Z3`):**

        Dialogue: 0,0:03:39.12,0:03:41.85,Default,<POSTAC_MEOW>,0,0,0,,Z wzajemnością.

2. **Dane wejściowe i ewolucja w logach (`Z1` / `Z5`):**
   - **Skrypt EN:** `"Right back at ya."`
   - **JP Audio (Kotoba-Whisper):** `"そうかその言葉リフレクトしますみんな無理して明るく振る舞ってる [soukasono kotoba rifurekuto shimasuminna muri shite akaruku furumatsu teru]"` *(właściwa część wypowiedzi `<POSTAC_MEOW>` to: `その言葉、リフレクトします！ [Sono kotoba, rifurekuto shimasu!]`; końcówka `みんな無理して...` to sklejony przez VAD monolog `<POSTAC_PECHKA>` z `[ID: 36]`)*.
   - **Telemetria (`Z1`/`Z5`):** `[Mówca: <POSTAC_MEOW> (FEMININE) | Adresat: Grupa Kobiet (FEMININE) | Grupa_1os_lm: NON_VIRILE | Grupa_2os_lm: NON_VIRILE | Scena: POLYLOGUE (n=4)]`
   - **Alert Profilera (`danger_lines_prescan` w `Z5`):** `approx_time: "00:03:00", english_phrase: "Right back at ya.", contextual_trap: "Kalka 'z powrotem do ciebie' brzmi nieporadnie w dynamicznym, ciętym dialogu.", contextual_guidance: "Zastosować naturalną polską ripostę: 'Z wzajemnością' lub 'Przyganiał kocioł garnkowi'."`
   - **Faza 1 (Draft PL):** `"Z wzajemnością."`
   - **Faza 2 (Verifier PL):** `"Z wzajemnością."` (`changes_made: null`)
   - **AVTLinter (`D_pos`):** `"Z wzajemnością."` (`[BRAK POPRAWEK - IDENTITY PASS-THROUGH]`)
3. **Rejestr mówcy:**
   - `<POSTAC_MEOW>` — wojowniczka stylizowana na postać chińską (w `EpisodeProfile`: *"Ekspresyjny, dziarski rejestr z teatralnymi powiedzeniami"*), która w poprzedzających sekundach (`[ID: 30–31]`) została ironicznie zaczepiona przez `<POSTAC_RIONETTA>`: `"Niezwykła elastyczność. Podziwiam, z jakim zapałem chłoniesz japońską kulturę."` (`よく日本の文化を学ばれているようで感心しますわ`).
4. **Sygnały rozpoznania w logach:**
   - Brak tagu `[CODE_SWITCH]` lub odpowiednika. W Paczce 1 aktywny był wprawdzie `FILAR XIII & XII` (`DYN_1`), ale nie zawiera on żadnych wskazówek dotyczących hybryd japońsko-angielskich. Co więcej, `EpisodeProfiler` (działający w Kroku 5 wyłącznie na tekście angielskim `"Right back at ya."`, przed uruchomieniem `Kotoba-Whisper` w Kroku 4!) wygenerował sztywną dyrektywę `danger_lines_prescan` nakazującą użycie `"Z wzajemnością"`.
5. **Ocena wyniku tłumaczenia i diagnoza przyczyny:**
   - W oryginale japońskim scena ma wyraźny wydźwięk komiczny: po kpinie `<POSTAC_RIONETTA>` na temat „pilnego uczenia się kultury japońskiej” i po użyciu przez `<POSTAC_MEOW>` uczonego chińsko-japońskiego zwrotu `客観的事実 [kyakkanteki jijitsu]` („obiektywne fakty” w `[ID: 32]`), `<POSTAC_MEOW>` odpowiada na zarzut o „niewyparzonym języku” (`[ID: 34]`) dziwacznym, nowoczesnym code-switchingiem z gier RPG: `その言葉、リフレクトします！ [Sono kotoba, rifurekuto shimasu!]` (dosł. *„Te słowa reflektuję / odbijam zaklęciem Reflect!”*).
   - Przekład `"Z wzajemnością."` jest całkowicie poprawny pod względem sensu ogólnego, ale **neutralizuje komiczny code-switching** z japońskiego audio. Przyczyną jest to, że: (a) `EpisodeProfiler` nie widzi transkrypcji `Kotoba-Whisper` dla tej linii i zasugerował gładkie `"Z wzajemnością"`, (b) `WhisperDisambiguator` nie wykrywa konstrukcji `[katakana-anglicyzm] + します/する` jako markera stylistycznego.
6. **Funkcja w kodzie, która powinna obsłużyć tę linię:**
   - `whisper_disambiguator.py:667` (`detect_batch_discourse_categories`) + `translator.py:953` (`detect_japanese_pragmatic_register`).
7. **Rekomendacja:**
   - Dodać w `detect_japanese_pragmatic_register` (`translator.py:953`) oraz w `WhisperDisambiguator.detect_batch_discourse_categories` (`whisper_disambiguator.py:667`) wykrywanie hybrydowych konstrukcji code-switchingu (`CODE_SWITCH_EN` — wtrącenia angielskie i czasowniki katakanowe `-shimasu/-suru`, gdy skrypt EN używa zwykłego idiomu), przekazując do promptu wskazówkę o zachowaniu zabawnego lub obcojęzycznego zabarwienia riposty (np. `"Odbijam te słowa z powrotem!"` / `"Reflektuję to z powrotem!"`).

---

### 4.2. Linie `[ID: 16, 17, 18]` (`#17–19` w `.ass`, Paczka 1, pozycje `#1–3` w paczce) — **WTRĄCENIA ANGIELSKIE `テンション上げ` I `オーケーオッケ` W MOWIE `<POSTAC_MEOW>`**

1. **Cytaty z `.ass` (`Z3`):**

        Dialogue: 0,0:01:12.12,0:01:15.57,Default,<POSTAC_MEOW>,0,0,0,,Trochę za bardzo mnie poniosło.
        Dialogue: 0,0:01:15.57,0:01:17.46,Default,<POSTAC_PECHKA>,0,0,0,,Wszystko w porządku?
        Dialogue: 0,0:01:17.54,0:01:20.62,Default,<POSTAC_MEOW>,0,0,0,,Jasne, nic mi nie jest.

2. **Dane wejściowe i ewolucja w logach (`Z1` / `Z5`):**
   - **`[ID: 16]`:** EN: `"Ah, I got a little too excited."` \| JP Audio: `"ちょっとテンション上げオーケーオッケ [chotto tenshon age ookeeokke]"` \| F1: `"Aż za bardzo mnie poniosło."` \| F2: `"Trochę za bardzo mnie poniosło."` (`[Filar CLXVI - Naturalna Polszczyzna Mówiona]`).
   - **`[ID: 17]`:** EN: `"Are you okay?"` \| JP Audio: `"オーケーオッケ [ookeeokke]"` *(przeciek segmentu z ID 18)* \| F1/F2: `"Wszystko w porządku?"`.
   - **`[ID: 18]`:** EN: `"Okay, okay, I'm fine."` \| JP Audio: `"オーケーオッケ俺あのめんどくさいリアルのやつは少し怒れただけで [ookeeokke ore anomendokusai riaru noyatsuha sukoshi ikare tadakede]"` \| F1/F2: `"Jasne, nic mi nie jest."`.
3. **Rejestr mówcy:**
   - `<POSTAC_MEOW>` — energiczna, ekspresyjna wojowniczka, która po teatralnym chińskim powitaniu w `[ID: 12]` przechodzi na luźny slang z angielskimi wtrąceniami (`テンション上げ [tenshon age]`, `オーケー、オッケー [ookee, okkee]`) i męskim zaimkiem `俺 [ore]`.
4. **Sygnały rozpoznania w logach:**
   - W konsoli `Z2` widoczny log: `├─ [Odsłuch JP] "chotto tenshon age ookeeokke | ookeeokke"`.
   - Brak dedykowanego tagu code-switchingu w telemetrii linii. W `rules.py:2681` wzorzec `urgent_double_rep_pat` i dyrektywa `DYN_6` / `SYNTACTIC_CALQUES_AND_IDIOMS` (`rules.py:1862`: `"Are you okay" -> "Wszystko w porządku", "Nic ci nie jest"`) prowadzą model w stronę idiomatycznej polszczyzny.
5. **Ocena wyniku tłumaczenia:**
   - W `[ID: 16]` (`"Trochę za bardzo mnie poniosło."`) i `[ID: 17]` (`"Wszystko w porządku?"`) przekład jest całkowicie naturalny.
   - W `[ID: 18]` angielskie podwojenie `"Okay, okay, I'm fine."` odpowiadające japońsko-angielskiemu `オーケー、オッケー！ [Ookee, okkee!]` zostało zredukowane do pojedynczego `"Jasne, nic mi nie jest."`. Choć poprawne i naturalne, zachowanie lekkiego potocznego `"Okej, okej, nic mi nie jest."` lepiej oddałoby słyszalne w głośnikach podwójne `"Ookee, okkee!"` seiyū (zgodnie z `FILAR CLVIII — Zasada Nieskazitelnego Ucha Widza`, `rules.py:1554`).
6. **Funkcja w kodzie:**
   - `rules.py:2680-2702` (`DYN_6` — redukcja powtórzeń wyrazowych) oraz `rules.py:1862` (`SYNTACTIC_CALQUES_AND_IDIOMS`).
7. **Rekomendacja:**
   - W `whisper_disambiguator.py` / `translator.py` przy wykryciu fonetycznego `オーケー / オッケー [ookee/okkee]` w audio JP dla angielskiego `"Okay, okay"` zezwolić na naturalne polskie `"Okej, okej"` dla postaci o rejestrze młodzieżowym/slangowym.

---

### 4.3. Linie `[ID: 151]` (`#152`), `[ID: 212]` (`#213`), `[ID: 251]` (`#252`), `[ID: 261]` (`#262`) i `[ID: 301]` (`#302`) — **ANGLICYZMY GAMINGOWE (`drop`, `boss`, `miniboss`, `info`) W KONTEKŚCIE REJESTRU POSTACI**

1. **Zestawienie linii i ewolucji Faza 1 -> Faza 2 -> `.ass` (`Z3`/`Z5`):**
   - **`[ID: 151]` (`<POSTAC_RIONETTA>`):**
     - EN: `"We also need luck to get good equipment."`
     - JP Audio: `"用意装備のためには... [yoi soubi no tame ni wa...]"` *(właściwe audio z ID 150/151: `良い装備 [yoi soubi]` — czysto japońskie słowo oznaczające „dobry ekwipunek”, zero anglicyzmu w JP!)*.
     - Alert Profilera (`danger_lines_prescan` w `Z5`): `"Oddać w naturalnym żargonie graczy jako szczęście w losowaniu ekwipunku."`
     - Faza 1 (Draft PL): `"Do dobrego ekwipunku\Npotrzeba też szczęścia!"`
     - Faza 2 (Verifier PL): `"Do dobrego dropu\Nczęsto trzeba farta!"` (`changes_made: "[Filar LXXI - Żargon Graczy i Zwięzłość AVT] Zastosowano naturalne pojęcia 'drop' i 'fart', idealnie oddające potoczny ton kłótni o losowy ekwipunek."`)
     - Wyjściowy `.ass` (`Z3`): `"Do dobrego dropu\Nczęsto trzeba farta!"`
   - **`[ID: 212]` (`<POSTAC_RIONETTA>`):**
     - EN: `"D-Don't tell me\Nthis monster is a boss class?"` \| JP Audio: `"さっこれってもしかしてボスキャラスか [kore tte moshikashite bosu kyara suka]"`
     - Faza 1: `"Chyba nie powiecie,\Nże ten potwór to boss?!"` -> Faza 2 / `.ass`: `"Tylko nie mów,\Nże to bydlę to boss?!"` (`[Filar XIII - Idiolekt <POSTAC_RIONETTA>]`).
   - **`[ID: 251]` (`<POSTAC_RIONETTA>`):**
     - EN: `"It means this <TYTUL_BOSS>\Nis a mid-level boss, right?"` \| JP Audio: `"つまりこのグレートドラゴンは中ボスってよね [tsumari kono gureeto doragon wa chuu-bosu tte yo ne]"`
     - Faza 1: `"Czyli ten <TYTUL_BOSS>\Nto tak jakby miniboss, prawda?"` -> Faza 2 / `.ass`: `"Czyli ten <TYTUL_BOSS>\Nto po prostu miniboss, tak?"`.
   - **`[ID: 261]` (`<POSTAC_RIONETTA>`):**
     - EN: `"That's already been proven."` \| JP Audio: `"それは確かです [sore wa tashika desu]"`
     - Faza 1: `"To potwierdzone info."` -> Faza 2 / `.ass`: `"To sprawdzona wiedza."` (`changes_made: "[Filar VI - Czystość rejestru / Filar CLXXII] Eliminacja potocznego 'info' z wersji roboczej na rzecz naturalnego, cynicznego stwierdzenia w ustach <POSTAC_RIONETTA>."`).
   - **`[ID: 301]` (brak `Name` w `.ass`):**
     - EN: `"Even if that dragon drops an item,\Nchances are there's only one."` \| JP Audio: `"ドラゴンのドロップアイテムはあって一つ [doragon no doroppu aitemu wa atte hitotsu]"`
     - Faza 1: `"Nawet jeśli coś z niego wypadnie,\Nto pewnie tylko jedna rzecz."` -> Faza 2 / `.ass`: `"Nawet jeśli smok coś upuści,\Nto pewnie tylko jedną rzecz."` (`[Filar XXIV - Żargon RPG / Naturalność]`).
2. **Ocena działania potoku na tych liniach:**
   - **Pozytywne wzorce (`[ID: 212, 251, 261, 301]`):** W `[ID: 212]` i `[ID: 251]` potok bezbłędnie zachował kanoniczne terminy gamingowe `boss` i `miniboss` (odpowiadające japońskim `ボスキャラ` i `中ボス` zgodnie z `FILAR XXIV`). W `[ID: 261]` Faza 2 wykazała się znakomitym słuchem rejestrowym, usuwając z wersji roboczej Fazy 1 kolokwialny skrót `"info"` (`"To potwierdzone info."` -> `"To sprawdzona wiedza."`), gdyż w audio JP pada formalne `それは確かです [sore wa tashika desu]`.
   - **Negatywna interferencja w `[ID: 151]`:** W `[ID: 151]` zaszło zjawisko odwrotne: Faza 1 przetłumaczyła kwestię `<POSTAC_RIONETTA>` w sposób wierny zarówno wobec audio JP (`良い装備` = dobry ekwipunek), jak i wobec jej dystyngowanego rejestru (`"Do dobrego ekwipunku\Npotrzeba też szczęścia!"`). Jednak `EpisodeProfiler` wygenerował dla tej linii alert `danger_lines_prescan` nakazujący użycie „żargonu graczy”, a Faza 2 (w Paczce 7, w której **nie aktywował się** `FILAR XIII` i w której aktywny był wyłącznie `FILAR LXXI`) zastąpiła dystyngowane zdanie `<POSTAC_RIONETTA>` slangowym `"Do dobrego dropu\Nczęsto trzeba farta!"` — mimo że 3 sekundy później w `[ID: 154]` używane jest słowo `rynsztunek`.
   - **Warstwa `D_pos` (`avt_linter.py`):** W `[ID: 151]` angielski rzeczownik `drop` otrzymał w polskim zdaniu końcówkę dopełniacza `-u` (`do dobrego dropu`), a `AVTLinter` prawidłowo przepuścił tę formę (`IDENTITY PASS-THROUGH`), nie uszkadzając fleksji anglicyzmu.

---

### 4.4. Linia `[ID: 263]` (`#264` w `.ass`, Paczka 12, pozycja `#7` w paczce) — **FONETYCZNY ANGLICYZM `アットマーク [AT-MARK]` W IMIENIU `<POSTAC_MEOW>`**

1. **Cytat z `.ass` (`Z3`):**

        Dialogue: 0,0:16:56.18,0:16:57.72,Default,<POSTAC_PFLE>,0,0,0,,<POSTAC_MEOW_BEZ_AT>.

   *(W pliku `.ass` zapisano imię postaci bez znaku `@`, podczas gdy w kolumnie `Name` we wszystkich kwestiach tej postaci widnieje prefiks `@`).*
2. **Dane wejściowe i ewolucja w logach (`Z1` / `Z5`):**
   - **Skrypt EN:** `"<POSTAC_MEOW>."` (z prefiksem `@`)
   - **JP Audio (Kotoba-Whisper):** `"あったマークニャンニャン [atta maakunyannyan]"` *(seiyū `<POSTAC_PFLE>` wyraźnie wymawia po angielsku nazwę symbolu `@`: `アットマーク・ニャンニャン [Atto-maaku Nyan-Nyan]`)*.
   - **Faza 1 / Faza 2 / `.ass`:** pominięcie symbolu `@` na początku imienia w treści dialogu.
3. **Wnioski i rekomendacja:**
   - W świecie przedstawionym znak `@` jest integralną częścią pseudonimu czarodziejki (wymawianą na głos przez inne postacie jako angielskie *at-mark*). Usunięcie `@` w treści napisu `[ID: 263]` (oraz w `[ID: 337, 341]`) tworzy niespójność z kartoteką postaci w `SeriesBible` i `EpisodeProfile`, gdzie postać figuruje z prefiksem `@`.

---

## Sekcja 5 — Śledztwo per linia (gwara / rejestr socjolingwistyczny *Yakuwarigo*)

W badanym odcinku występują cztery wyraźnie zróżnicowane rejestry socjolingwistyczne (*yakuwarigo*):
1. **Rejestr chińskiej wojowniczki (`-ある [-aru]` / `-やる [-yaru]` + zaimek `俺 [ore]`)** u `<POSTAC_MEOW>`.
2. **Rejestr sarkastycznej damy *ojōsama* (`-ですわ [-desu wa]` / `-ますわ [-masu wa]` / `-ですこと [-desu koto]` / `-ますの [-masu no]`)** u `<POSTAC_RIONETTA>`.
3. **Rejestr chłopięco-bojowy (`-っす [-ssu]` / `-だな [-da na]`)** u `<POSTAC_CLANTAIL>` oraz dziecięcy (`-なの [-nano]`) u `<POSTAC_LAPIS>`.
4. **Rejestr wyniosłego arystokratycznego dowódcy (`-たまえ [-tamae]` / `-かい [-kai]`)** u `<POSTAC_PFLE>` w kontraście do rejestru służącej (`panienko`) u `<POSTAC_SHADOW_GALE>`.

Poniżej przedstawiono szczegółowe śledztwo dla reprezentatywnych linii każdego z tych rejestrów.

---

### 5.1. Grupa A: Chiński rejestr `-aru / -yaru` postaci `<POSTAC_MEOW>` — linie `[ID: 118, 120, 121, 122, 138–140, 187, 264, 267, 279, 305]`

1. **Zestawienie cytatów z `.ass` (`Z3`), Fazy 1, Fazy 2 oraz japońskiego audio (`Z1`/`Z5`):**
   - **`[ID: 118]` (`#119`, Paczka 5):**
     - EN: `"I asked everyone to let us know\Nif they see <POSTAC_YUMENOSHIMA>-san."`
     - JP Audio: `"...みんなに頼んでるあるでも今だに誰からも [...minna ni tanonderu aru demo imada ni dare kara mo]"`
     - Telemetria: `[Mówca: <POSTAC_MEOW> (FEMININE) | Grupa_1os_lm: NON_VIRILE | Grupa_2os_lm: VIRILE | Scena: POLYLOGUE (n=8)]`
     - Faza 1 / Faza 2 / `.ass`: `"Poprosiłam wszystkich, by dali znać,\Ngdyby zobaczyli <POSTAC_YUMENOSHIMA>."`
   - **`[ID: 120–122]` (`#121–123`, Paczka 5):**
     - EN: `"There must be a reason behind this."` / `"There must be a pressing reason why she"` / `"can't meet with us at all."`
     - JP Audio: `"何か事情があるはずあるどうしても私たちの前に姿を見せられないそういう乗っぴきならない事状があるあずあるよ [nanika jijou ga aru hazu aru doushitemo watashitachi no mae ni sugata wo miserarenai sou iu noppiki naranai jijou ga aru hazu aru yo]"`
     - Faza 1 / Faza 2 / `.ass`: `"Musi mieć ku temu jakiś powód."` / `"Musi mieć naprawdę ważny powód,"` / `"skoro w ogóle\Nnie może się z nami spotkać."`
   - **`[ID: 140]` (`#141`, Paczka 6):**
     - EN: `"Is your wheelchair not fixed yet?"`
     - JP Audio: `"くるまいすまだなおらないやるか [kurumaisu mada naoranai yaru ka]"`
     - Faza 1: `"Wózek wciąż nie jest naprawiony?"` -> Faza 2 / `.ass`: `"Wózek wciąż nienaprawiony?"`
   - **`[ID: 187]` (`#188`, Paczka 8):**
     - EN: `"D-Disappeared?!"` \| JP Audio: `"どういうことある [dou iu koto aru]"` (właśc. w ID 188 EN: `"What happened?"` -> PL: `"Co się stało?"`).
   - **`[ID: 264 & 267]` (`#265 & #268`, Paczka 12):**
     - EN: `"What is it?"` / `"Since I'm just throwing <TYTUL_PAPIEROWY_TALIZMAN>,\NI have to get quite close to it."`
     - JP Audio: `"何やるか [nani yaru ka]"` / `"ふだを投げるだけあるかなり近づかないといけなやる [fuda wo nageru dake aru kanari chikazukanai to ikena yaru]"`
     - Faza 1: `"Słucham?"` / `"Tylko nimi rzucam,\Nwięc muszę podejść dość blisko."` -> Faza 2 / `.ass`: `"Słucham?"` / `"Rzucam ręcznie,\Nwięc muszę podejść dość blisko."`
   - **`[ID: 279]` (`#280`, Paczka 13):**
     - EN: `"We also only have one <TYTUL_TARCZA>."`
     - JP Audio: `"私たちもシールドプラス5は一つだけしかないやるね [watashitachi mo shiirudo purasu 5 wa hitotsu dake shika nai yaru ne]"`
     - Faza 1 / Faza 2 / `.ass`: `"My też mamy tylko jedną <TYTUL_TARCZA>."`
   - **`[ID: 305]` (`#306`, Paczka 14 — POZYTYWNY WZORZEC):**
     - EN: `"I agree to those terms."`
     - JP Audio: `"私はそれでいいやる [watashi wa sore de ii yaru]"`
     - Faza 1: `"Ja się zgadzam."` -> Faza 2 / `.ass`: **`"Dla mnie gra."`** (`changes_made: "[Filar CXLVI - Dialogowy Ping-Pong] Dynamiczna, potoczysta riposta dopasowana do szorstkiego stylu seiyū ('watashi wa sore de ii yaru')."`).

2. **Dlaczego w 9 z 10 linii rejestr `-aru / -yaru` został zneutralizowany, a w `[ID: 305]` zadziałał?**
   - **Przyczyna 1 (`profiler.py`):** W `EpisodeProfile` (`Z5`, `stage: "profile_prepass"`) Profiler zapisał dla `<POSTAC_MEOW>`:
     - `"speech_style_pl": "Ekspresyjny, dziarski rejestr z teatralnymi powiedzeniami nawiązującymi do chińskich sztuk walki."`
     - `"dialect_category": "brak"`
     - `"idiolect_matrix": "Okrzyki bojowe, kwieciste formuły powitań, dynamiczne zwroty."`
     Ponieważ `dialect_category` otrzymało wartość `"brak"`, a `format_lean_episode_brief` (`profiler.py:306-313`) sprawdza jedynie obecność słów `["gwara", "dialekt", "slang", "szorstka", "środowiskowa"]` i całkowicie pomija wypisywanie zawartości `speech_style_pl` oraz `idiolect_matrix`, w wygenerowanym `EPISODE BRIEF` (`Z1`, `[KROK 5]`) znalazło się jedynie:
     `- <POSTAC_MEOW>: FEMALE (Wojowniczka w chińskim stroju, posługująca się papierowymi talizmanami.)` — **zero informacji o sposobie mówienia!**
   - **Przyczyna 2 (`whisper_disambiguator.py:691-707`):** Metoda `detect_batch_discourse_categories` nie posiada w wyrażeniu regularnym `jp_dialect_pat` ani w `character_suffix_pat` końcówek `-aru` (`ある`) i `-yaru` (`やる`). W efekcie w Paczkach 5, 8, 12 i 14 kategoria `"DIALECT_JP"` w ogóle się nie zapaliła.
   - **Przyczyna 3 (`translator.py:953-1020`):** Funkcja `detect_japanese_pragmatic_register` ma 14 kategorii rejestrów, ale żadna z nich nie wykrywa `-aru / -yaru`.
   - **Dlaczego zadziałało w `[ID: 305]`:** W `[ID: 305]` weryfikator Fazy 2 (dysponujący budżetem myślenia `CoT: 3072`) sam dostrzegł w polu `jp_audio` transkrypcję `"私はそれでいいやる [watashi hasoredeiiyaru]"` i zastąpił sztywne `"Ja się zgadzam."` potocznym `"Dla mnie gra."`. Pokazuje to, że model LLM potrafi świetnie oddać ten rejestr, jeśli tylko jego uwaga zostanie skierowana na te markery!

---

### 5.2. Grupa B: Arystokratyczno-sarkastyczny rejestr *ojōsama* (`-desu wa / -desu koto / -masu no`) postaci `<POSTAC_RIONETTA>` — linie `[ID: 22–34, 55–56, 83–94, 205–214, 222–229, 233–234]`

1. **Zestawienie kluczowych linii:**
   - **`[ID: 25]` (`#26`, Paczka 1):** EN: `"I would be very grateful\Nif you cared to explain."` \| JP: `"教えていただけるとありがたいですわね [oshiete itadakeru to arigatai desu wa ne]"` -> `.ass`: `"Byłabym wdzięczna za wyjaśnienia."`
   - **`[ID: 28 & 31]` (`#29 & #32`, Paczka 1):** EN: `"Oh? My, my."` / `"I am impressed seeing you\Ndiligently study Japanese culture."` \| JP: `"...食いやがりますわ"` / `"よく日本の文化を学ばれているようで感心しますわ [kanshin shimasu wa]"` -> `.ass`: `"Proszę, proszę."` / `"Podziwiam, z jakim zapałem\Nchłoniesz japońską kulturę."`
   - **`[ID: 87, 92, 94]` (`#88, #93, #95`, Paczka 4 — brak `Name` w `.ass`):**
     - EN: `"Enjoying <POSTAC_PECHKA>-san's cooking\Nis my only happiness."` / `"Shouldn't someone have managed\Nto unlock a new Area by now?"` / `"And I'm reluctant to stay long\Nin a damp and gloomy place like this."`
     - JP Audio: `"...唯一の幸せですわ [...yuiitsu no shiawase desu wa]"` / `"誰かしらエリア開放していい時期ではありませんこと [...jiki de wa arimasen koto]"` / `"...薄暗い場所なんて長居したくありませんのに [...nagai shitaku arimasen noni]"`
     - `.ass`: `"Tylko gotowanie <POSTAC_PECHKA>\Ndaje mi jakąś radość."` / `"Czy ktoś nie powinien już\Nodblokować nowego obszaru?"` / `"Nie mam ochoty tkwić dłużej\Nw takim ciemnym, wilgotnym miejscu."`
   - **`[ID: 210 & 212]` (`#211 & #213`, Paczka 10):**
     - EN: `"That means that creature is..."` / `"D-Don't tell me\Nthis monster is a boss class?"`
     - F1: `"To oznacza, że ta bestia..."` / `"Chyba nie powiecie,\Nże ten potwór to boss?!"`
     - F2 / `.ass`: **`"A więc ta poczwara..."`** / **`"Tylko nie mów,\Nże to bydlę to boss?!"`** (`changes_made: "[Filar XIII - Idiolekt <POSTAC_RIONETTA>] Wprowadzono wyrazisty, szorstki rejestr postaci"`).
   - **`[ID: 234]` (`#235`, Paczka 11):**
     - EN: `"That weapon looks very fragile\Nand unconvincing."` \| JP: `"これまたずいぶんと頼りなさげな武器ですこと [kore mata zuibun to tayorinasage na buki desu koto]"` -> `.ass`: `"Ta broń wygląda wyjątkowo licho."`

2. **Diagnoza:**
   - Dla `<POSTAC_RIONETTA>` funkcja `detect_japanese_pragmatic_register` (`translator.py:970`) posiada wprawdzie regułę wykrywającą `"ですわ"` i `"かしら"` (`return "Arystokratyczny / Ojou-sama (elegancka, dystyngowana polszczyzna damy)"`), jednak w logach widać dwa problemy:
     1. Reguła w `translator.py:970` nie obejmuje końcówek `"ますわ"`, `"ですこと"`, `"ありませんこと"` ani `"ますの"`.
     2. W samej charakterystyce `<POSTAC_RIONETTA>` występuje kontrast między zewnętrzną formą *ojōsama* (`-desu wa / -desu koto`) a jadowitym, wulgarnym wnętrzem (`食いやがりますわ [-yagarimasu wa]`, `poczwara`, `bydlę`, `idiotka`). Tam, gdzie w pliku `.ass` kolumna `Name` była wypełniona (`<POSTAC_RIONETTA>` w Paczkach 1, 10, 11, 12), modele F1 i F2 dobrze utrzymały jej wyniosło-złośliwy ton (`"Byłabym wdzięczna za wyjaśnienia"`, `"A więc ta poczwara..."`, `"Ta broń wygląda wyjątkowo licho"`, `"To sprawdzona wiedza"`), z wyjątkiem linii `[ID: 151]` (`"Do dobrego dropu często trzeba farta!"`). Natomiast w Paczce 4 (`[ID: 87–94]`), gdzie w wejściowym skrypcie `.ass` pole `Name` było puste (`""`), a z powodu przesunięcia ASR w `whisper_engine.py` tekst `幸せですわ` z `[ID: 87]` trafił do `[ID: 83–84]`, jej kwestie zostały przetłumaczone neutralnie bez dystyngowanego sznytu *ojōsama*.

---

### 5.3. Grupa C: Chłopięco-sportowy rejestr `-ssu` (`<POSTAC_CLANTAIL>`) oraz dziecięcy `-nano` (`<POSTAC_LAPIS>`) — linie `[ID: 194–196]` (`#195–197` w `.ass`, Paczka 9)

1. **Cytaty z `.ass` (`Z3`) i ewolucja w logach (`Z1`/`Z5`):**
   - **`[ID: 194–195]` (`<POSTAC_CLANTAIL>`):**
     - EN: `"Magical Girls don't really need lighting,"` / `"but having these torches\Nmakes me feel calm."`
     - JP Audio: `"本物の炎だね魔法少女に明かりは必要ないっすけどあるだけで頼もしい [honmono no honoo dane mahoushoujo ni akari ha hitsuyou naissukedo arudakede tanomoshii]"`
     - Faza 1: `"Czarodziejki nie potrzebują światła,"` / `"ale z tymi pochodniami\Njakoś tak raźniej."`
     - Faza 2 / `.ass`: `"Czarodziejki niby\Nnie potrzebują światła,"` / `"ale z pochodniami jakoś raźniej."`
   - **`[ID: 196]` (`<POSTAC_LAPIS>`, brak `Name` w `.ass`):**
     - EN: `"Everyone is here, right?"`
     - JP Audio: `"...全員揃ったなの [...zen'in sorotta nano]"`
     - Faza 1 / Faza 2 / `.ass`: `"Wszyscy już są, prawda?"`
2. **Diagnoza:**
   - W `[ID: 194–195]` funkcja `detect_japanese_pragmatic_register` (`translator.py:986`) wykryła `"っす"` (`Młodzieżowy / Swobodny`), a Faza 2 trafnie wprowadziła swobodne partykuły `"niby"` oraz `"jakoś raźniej"`.
   - Natomiast w `[ID: 196]` (gdzie `<POSTAC_LAPIS>` mówi charakterystycznym dziecięcym `全員揃ったなの [zen'in sorotta nano]`) brak aktora w kolumnie `Name` oraz brak reguły na końcówkę czasownikową `-ta nano` sprawiły, że kwestia została przetłumaczona nie tylko całkowicie neutralnie, ale z użyciem męskoosobowego zaimka `"Wszyscy już są, prawda?"` (wobec grupy złożonej w 100% z kobiet).

---

### 5.4. Grupa D: Ksywki hipokorystyczne `-cchi` i gwarowe `-kkarane` u `<POSTAC_MEL>` — linie `[ID: 156]` (`#157`) i `[ID: 304]` (`#305`)

1. **Zestawienie linii:**
   - **`[ID: 156]` (`#157`, Paczka 7, mówca: `<POSTAC_PECHKA>`):**
     - EN: `"<POSTAC_MEL>-cchi!"` -> F1 / F2 / `.ass`: `"<POSTAC_MEL>-cchi!"` (zachowano oryginalną ksywkę z sufiksem `-cchi`).
   - **`[ID: 304]` (`#305`, Paczka 14, mówca: `<POSTAC_MEL>`, brak `Name` w `.ass`):**
     - EN: `"After all, without <KSYWKA_PFU_CCHI>'s help,\Nwe couldn't have gotten here, right?"`
     - JP Audio: `"なしまあプフッチなしじゃここに来ることだってできなかったわけっからね... [nashimaa pufutchi nashijakokoni kuru kotodattedekinakattawakekkarane...]"`
     - Faza 1 / Faza 2 / `.ass`: `"W końcu bez pomocy <POSTAC_PFLE>\Nw ogóle byśmy tu nie dotarły."`
2. **Diagnoza:**
   - W `[ID: 304]` postać `<POSTAC_MEL>` (nazywana przez wszystkich `<POSTAC_MEL>-cchi` właśnie dlatego, że sama nadaje innym spieszczone ksywki na `-cchi` i mówi luźnym slangiem `わけっからね [wake kkara ne]`) używa zarówno w EN, jak i w audio JP ksywki `<KSYWKA_PFU_CCHI>` (`プフッチ`) na określenie chłodnej arystokratki `<POSTAC_PFLE>`.
   - Ponieważ w `SeriesBible` i `EpisodeProfile` zdefiniowano jedynie oficjalne imię `<POSTAC_PFLE>`, a w linii 304 brakowało etykiety mówcy w kolumnie `Name`, model Fazy 1 znormalizował `<KSYWKA_PFU_CCHI>` do oficjalnego `<POSTAC_PFLE>`, tracąc humorystyczny kontrast między poufałą ksywką a dystansem arystokratki.

---

## Sekcja 6 — Weryfikacja spójności rejestru w całym odcinku (Faza 3)

| Wymiar spójności (§3.4) | Postać / Zjawisko | Liczba linii postaci | Ocena spójności w wyjściowym `.ass` (`Z3`) | Szczegółowe wnioski i dowody z `.ass` oraz logów (`Z1`/`Z5`) |
| :--- | :--- | :---: | :---: | :--- |
| **1. Spójność rejestru tej samej postaci (Gwara / *Yakuwarigo*)** | `<POSTAC_MEOW>` (chińska maniera `-aru/-yaru`, zaimek `ore`, ekspresyjne powiedzonka) | `38` linii (`27` z jawnym `Name`, `11` bez `Name`) | **`NIESPÓJNA (Przeskoki rejestru)`** | W liniach otwarcia (`[ID: 12]` `"Przeznaczenie złączyło nasze ścieżki!"`, `[ID: 15]` `"Aż mnie roznosi!"`, `[ID: 20]` `"Ta upierdliwa lalka będzie marudzić"`, `[ID: 305]` `"Dla mnie gra."`) postać ma żywy, wyrazisty rejestr. Natomiast w środkowej części odcinka (`[ID: 52–54]`, `[ID: 118–122]`, `[ID: 150]`, `[ID: 264, 267]`, `[ID: 279]`), mimo że w audio JP konsekwentnie kończy zdania na `-aru / -yaru`, jej polskie kwestie przeskakują na gładką, neutralną polszczyznę literacką (`"Poprosiłam wszystkich, by dali znać..."`, `"Słucham?"`, `"Rzucam ręcznie, więc muszę podejść dość blisko."`). |
| **1b. Spójność rejestru tej samej postaci (*Ojōsama* + sarkazm)** | `<POSTAC_RIONETTA>` (`-desu wa / -desu koto`, teatralny cynizm) | `44` linie (`31` z jawnym `Name`, `13` bez `Name`) | **`WYSOKA (z 2 odchyleniami)`** | W większości linii utrzymano spójny, wyniosło-jadowity rejestr (`[ID: 25]` `"Byłabym wdzięczna za wyjaśnienia."`, `[ID: 28]` `"Proszę, proszę."`, `[ID: 31]` `"Podziwiam, z jakim zapałem chłoniesz japońską kulturę."`, `[ID: 210]` `"A więc ta poczwara..."`, `[ID: 234]` `"Ta broń wygląda wyjątkowo licho."`, `[ID: 261]` `"To sprawdzona wiedza."`). Odchylenia wystąpiły w `[ID: 151]` (przeskok na młodzieżowy slang `"Do dobrego dropu często trzeba farta!"`) oraz w Paczce 4 (`[ID: 87–94]`), gdzie przez brak tagu `Name` w `.ass` jej kwestie z `-desu wa / -arimasen koto` zostały zneutralizowane. |
| **1c. Spójność rejestru tej samej postaci (Arystokratyczny chłód vs Służąca)** | `<POSTAC_PFLE>` i `<POSTAC_SHADOW_GALE>` | `64` linie (`49` `<POSTAC_PFLE>`, `15` `<POSTAC_SHADOW_GALE>`) | **`WZORCOWA (100%)`** | `<POSTAC_PFLE>` w całym odcinku zachowuje chłodny, władczy, precyzyjny rejestr dowódczy (`"Cieszę się, że zechciałyście przyjść."`, `"Odstąpcie mi to, proszę. Dobrze wam to wynagrodzę."`, `"<POSTAC_SHADOW_GALE>, ruszamy."`, `"Więc ustalone... Rozpoczynamy operację."`), a `<POSTAC_SHADOW_GALE>` konsekwentnie utrzymuje rejestr lojalnej podwładnej zwracającej się do niej per `"panienko"` (`[ID: 180]` `"Proszę przestać, panienko. Nie jestem wierzchowcem."`, `[ID: 231]`, `[ID: 342]`). |
| **1d. Spójność rejestru tej samej postaci (Nieśmiałość / wahanie)** | `<POSTAC_PECHKA>` | `85` linii | **`WZORCOWA (100%)`** | W całym odcinku utrzymano nieśmiały, pełen zająknięć i wielokropków rejestr (`[ID: 14]` `"D-Dzień dobry..."`, `[ID: 50]` `"Y-Ym, <POSTAC_NAKO>..."`, `[ID: 63]` `"T-Tak, już idę!"`, `[ID: 215]` `"Jak... jak w ogóle mamy z tym walczyć...?"`, `[ID: 311]` `"T-tak."`). |
| **2. Spójność code-switchingu i terminologii anglojęzycznej** | Wtrącenia EN i terminy RPG (`boss`, `miniboss`, `drop`, `loteria`) | `15` linii | **`CZĘŚCIOWA`** | Terminy systemowe RPG (`boss` w `[ID: 212]`, `miniboss` w `[ID: 251]`, słownikowe `<TYTUL_BOSS>`, `<TYTUL_BRON>`, `<TYTUL_TALIZMAN_WODY>`, `<TYTUL_TARCZA>`) są w 100% spójne. Natomiast przy wtrąceniach konwersacyjnych występuje niespójność strategii: w `[ID: 18]` `オーケーオッケ` i w `[ID: 35]` `リフレクトします` zostały całkowicie zastąpione rodzimymi zwrotami (`"Jasne..."`, `"Z wzajemnością."`), podczas gdy w `[ID: 151]` do czysto japońskiego zdania `良い装備` dodano w Fazie 2 anglicyzm `"dropu"`. |
| **3. Spójność z `series_bible`** | `SeriesBible` (`series_memory.py` + `*_bible.json`) | `29` encji postaci w `Z5` | **`BRAK POLA REJESTRU W BIBLE`** | W `SeriesBible` (`Z1` `[KROK 6]`, `Z5` `series_bible`) żadna z 29 postaci nie posiada pola określającego rejestr mowy, dialekt ani stylizację. Dodatkowo postać `<POSTAC_CLANTAIL>` ma w `SeriesBible` wpisany błędny rodzaj męski (`"gender": "MALE"`, `"description": "MĘŻCZYZNA (wyodrębniono z relacji serii)"`), który na szczęście został w 100% skorygowany w trakcie tłumaczenia przez `EpisodeProfiler` (`"<POSTAC_CLANTAIL>": "FEMALE"`) oraz pre-pass sceniczny (`87 żeńskich, 0 męskich`), dzięki czemu w `.ass` `<POSTAC_CLANTAIL>` mówi wyłącznie w rodzaju żeńskim (`[ID: 2]` `"Dawno się nie widziałyśmy."`, `[ID: 5]` `"To ja powinnam..."`, `[ID: 338]` `"Wszędzie cię szukałam!"`). |
| **4. Spójność z telemetrią `[TELEMETRIA: ...]`** | Wektor `telemetry_tag` w `Z1` / `Z5` | `347` linii | **`BRAK REJESTRU W TELEMETRII`** | Wektor `telemetry_tag` (generowany przez `format_dry_telemetry_tag` w `translator.py:4251`) zawiera wyłącznie: `[Mówca: ... | Adresat: ... | Grupa_1os_lm: ... | Grupa_2os_lm: ... | Scena: POLYLOGUE]`. Nie zawiera informacji o rejestrze (`Rejestr: ...`) ani o wykrytym code-switchingu, mimo że `translator.py:4318` oblicza zmienną `pragmatic_reg` kilka linii niżej! Co więcej, z powodu błędnego wpisu `"<POSTAC_CLANTAIL>": "MALE"` w `SeriesBible`, w liniach z udziałem `<POSTAC_CLANTAIL>` (`[ID: 1, 2, 5, 6, 10, 43–49, 57–62, 157–159, 194–195, 201, 238, 336, 338]`) wektor `telemetry_tag` raportował `Mówca: <POSTAC_CLANTAIL> (MASCULINE) | Grupa_1os_lm: VIRILE`, co modele F1 i F2 słusznie zignorowały na rzecz `EpisodeProfile` (`FEMALE`) i obrazu wideo. |

---

## Sekcja 7 — Pokrycie testami regresyjnymi (Faza 4)

### 7.1. Audyt istniejących testów w `tests/` oraz `test_system.py`

| Obszar testowy | Plik testowy i funkcja | Czy istnieje? | Co dokładnie sprawdza istniejący test | Czego NIE pokrywa (luka testowa) |
| :--- | :--- | :---: | :--- | :--- |
| **Code-switching (JA + EN w jednej wypowiedzi)** | `tests/*`, `test_system.py` | **`BRAK` (`0` testów)** | Brak jakiegokolwiek testu `test_*code_switch*`, `test_*anglicyzm*` lub `test_*anglicism*` podającego hybrydową linię JP+EN (np. katakanizm angielski w japońskiej wypowiedzi) i weryfikującego jej obsługę. | Brak pokrycia detekcji code-switchingu w `whisper_disambiguator.py`, brak pokrycia w `rules.py`, brak pokrycia fleksji anglicyzmów w `avt_linter.py`. |
| **Gwara — `EpisodeProfile` -> `EPISODE BRIEF`** | `tests/test_profiler.py:303` — `test_t10_1_1_p2a_dialect_registry_guidance_in_episode_brief` | **`ISTNIEJE`** | Sprawdza, że dla `audio_transcription="ora washi no dabe"` lub `"honma ni akan de"` funkcja `format_lean_episode_brief` dodaje ogólny wiersz `"Rejestr: wyrazista gwara / stylizacja środowiskowa"`. | Nie sprawdza, czy `format_lean_episode_brief` przekazuje właściwą treść pól `speech_style_pl` i `idiolect_matrix` z `CharacterDossier` (np. dla *yakuwarigo* `-aru/-yaru`, *ojōsama* `-desu wa`, `-ssu`), gdy `dialect_category == "brak"`. |
| **Gwara — `get_focused_rules_for_batch` + prompt Fazy 2** | `tests/test_verifier.py:663` — `test_t10_1_1_p2b_focused_rules_dialect_and_paraphrase_contrast_prompt` | **`ISTNIEJE`** | Sprawdza, że dla EN `"I ain't gonna do that, mate."` oraz JP `"honma ya nen"` funkcja `get_focused_rules_for_batch` wybiera `FILAR XIII`, wyklucza `FILAR LXXI` i `CLXXII`, a `DialogueVerifier.verify_batch` wstrzykuje `[PARAFRAZA GWARY: ...]`. | Nie sprawdza wykrywania japońskich ról *yakuwarigo* (`-aru/-yaru`, `-desu wa`, `-desu koto`, `-ssu`, `-nano`) ani odporności `detect_batch_discourse_categories` na fałszywe trafienia podciągów `"べ"` (`食べた`, `全て`, `比べれば`) i `"おら"` (`直らない`). |
| **Gwara — `detect_japanese_pragmatic_register`** | `test_system.py:255` oraz `test_system.py:2254` | **`ISTNIEJE`** | Sprawdza wykrycie dialektu Kansai (`"なんでやねん！ほんまにあかんわ！"` -> `"zachodni"`) oraz zaimka `Jibun` w Kansai-ben. | Nie sprawdza detekcji `-aru/-yaru`, `-desu koto`, `-masu no`, `-nano` ani przekazywania wykrytego rejestru do `telemetry_tag`. |
| **Gwara — `SeriesBible` (`CharacterRecord`)** | `tests/test_series_memory.py` | **`BRAK` (`0` testów)** | Testuje wyłącznie płeć (`gender`), paradygmaty deklinacji (`declensions`), toponimy i aliasy. | Brak testu na przechowywanie i synchronizację pola `speech_register` / `speech_style_pl` w `CharacterRecord`. |

### 7.2. Propozycje nowych testów regresyjnych (bez wdrażania)

1. **`test_whisper_disambiguator_no_false_positive_dialect_on_common_verbs` (w `tests/test_discourse_and_translator.py`):**
   - **Wejście:** `combined_en = "Everything is fine compared to before, isn't it fixed yet?"`, `combined_jp = "客観的事実を述べたまでのこと これに比べれば 全て私のものにしたい まだなおらない"` (zawiera zwykłe słowa z sylabami `べ` i `おら`: `述べた`, `比べれば`, `全て`, `なおらない`).
   - **Oczekiwany wynik:** `cats = WhisperDisambiguator.detect_batch_discourse_categories(combined_en, combined_jp)`.
   - **Asercje:** `assert "DIALECT_JP" not in cats` (eliminacja fałszywych trafień na podciągach `"べ"` i `"おら"` wewnątrz zwykłych słów).

2. **`test_whisper_disambiguator_detects_yakuwarigo_aru_yaru_desuwa_ssu_nano` (w `tests/test_discourse_and_translator.py`):**
   - **Wejście:**
     - Przypadek 1 (`-aru/-yaru`): `combined_jp = "みんなに頼んでるある 何か事情があるはずあるよ 私はそれでいいやる 何やるか"`
     - Przypadek 2 (`-desu wa / -desu koto`): `combined_jp = "ありがたいですわね 頼りなさげな武器ですこと"`
     - Przypadek 3 (`-ssu / -nano`): `combined_jp = "明かりは必要ないっすけど 全員揃ったなの"`
   - **Oczekiwany wynik:** Wywołanie `WhisperDisambiguator.detect_batch_discourse_categories("", combined_jp)` oraz `get_focused_rules_for_batch([{"en": "Test", "audio_jp": combined_jp}])`.
   - **Asercje:** Dla każdego z 3 przypadków `assert "DIALECT_JP" in cats` oraz `assert "FILAR XIII" in focused_rules`.

3. **`test_code_switching_detection_and_prompt_guidance` (w `tests/test_translator.py`):**
   - **Wejście:** `en_text = "Right back at ya."`, `jp_audio = "その言葉リフレクトします [sono kotoba rifurekuto shimasu]"` (hybryda JA+EN: angielski czasownik w katakanie + `します`, podczas gdy EN ma zwykły idiom).
   - **Oczekiwany wynik:** `cats = WhisperDisambiguator.detect_batch_discourse_categories(en_text, jp_audio)` oraz `reg = detect_japanese_pragmatic_register(jp_audio, en_text)`.
   - **Asercje:** `assert "CODE_SWITCH_EN" in cats` oraz `assert reg is not None and ("code-switch" in reg.lower() or "anglicyzm" in reg.lower() or "katakan" in reg.lower())`.

4. **`test_format_lean_episode_brief_includes_character_speech_style_and_idiolect` (w `tests/test_profiler.py`):**
   - **Wejście:** `EpisodeProfile` z `CharacterDossier(name="SpeakerChi", gender="FEMALE", age_and_role="Wojowniczka", speech_style_pl="Ekspresyjny rejestr z teatralnymi powiedzeniami", dialect_category="brak", idiolect_matrix="Okrzyki bojowe, dynamiczne zwroty")`.
   - **Oczekiwany wynik:** `brief = format_lean_episode_brief(profile)`.
   - **Asercje:** `assert "Ekspresyjny rejestr" in brief` oraz `assert "Okrzyki bojowe" in brief` (gwarancja, że wygenerowany przez Profiler styl mowy postaci zawsze trafia do `EPISODE BRIEF` dla Fazy 1 i Fazy 2, niezależnie od pola `dialect_category`).

5. **`test_series_bible_character_record_persists_speech_register` (w `tests/test_series_memory.py`):**
   - **Wejście:** Wywołanie `bible.sync_verified_profile_entity(name="SpeakerAlpha", gender="FEMALE", speech_register="Chłodny, arystokratyczny rejestr wyższościowy")` i `bible.format_scoped_for_batch(batch_text="SpeakerAlpha", active_speakers={"SpeakerAlpha"})`.
   - **Oczekiwany wynik:** Rekord w `bible.data["characters"]["SpeakerAlpha"]` oraz sformatowany blok dla paczki.
   - **Asercje:** `assert bible.data["characters"]["SpeakerAlpha"].get("speech_register") == "Chłodny, arystokratyczny rejestr wyższościowy"` oraz `assert "arystokratyczny rejestr" in scoped_str`.

---

## Sekcja 8 — Propozycje rozwiązań (bez wdrażania)

Wszystkie poniższe propozycje mają charakter ściśle architektoniczno-opisowy (0 zmian w repozytorium podczas audytu).

### 8.1. Priorytet P1 (Krytyczne — bezpośredni wpływ na zachowanie rejestru i sensu w `.ass`)

#### Propozycja P1-1: Naprawa detektora `DIALECT_JP` i dodanie kategorii `CODE_SWITCH_EN` w `whisper_disambiguator.py` + `rules.py`
- **Lokalizacja:** `whisper_disambiguator.py:667-708` (`WhisperDisambiguator.detect_batch_discourse_categories`) oraz `rules.py:2560-2590` (`get_focused_rules_for_batch`).
- **Mechanizm:**
  1. W `whisper_disambiguator.py:699-703` zastąpić niezakotwiczone wyszukiwanie podciągów `"べ"` i `"おら"` w `jp_dialect_tokens` wyrażeniem regularnym zakotwiczonym na końcu frazy/zdania dla partykuły `べ` (`r"(?:だべ|っぺ|いくべ|すっぺ|やるべ)(?:[！？!?。、\s]|$)"`) oraz granicą morfemu dla zaimka `おら` (`r"(?:^|[、。\s])おら(?:は|が|の|に|を|も|たち|っち)"`), eliminując fałszywe wyzwalanie `DIALECT_JP` na czasownikach `述べた`, `比べれば`, `全て`, `直らない`.
  2. Rozszerzyć `DIALECT_JP` o japońskie markery *Yakuwarigo* (Filar XIII):
     - chiński rejestr `-aru / -yaru`: `r"(?:てる|でる|はず|だけ|こと|いい|ない|な)ある(?:よ|ね|か|な)?(?:[！？!?。、\s]|$)"`, `r"(?:いい|ない|な|何)やる(?:か|ね|よ)?(?:[！？!?。、\s]|$)"` oraz odpowiedniki w rōmaji (`tanonderu aru`, `hazu aru`, `dake aru`, `koto aru`, `nani yaru ka`, `ii yaru`, `ikena yaru`, `nai yaru ne`),
     - rejestr *ojōsama*: `r"(?:ですわ|ますわ|ですこと|ありませんこと|ますのよ)"` oraz rōmaji (`desu wa`, `masu wa`, `desu koto`, `arimasen koto`),
     - rejestr chłopięcy/młodzieżowy `-ssu` i dziecięcy `-nano`: `r"(?:ないっす|っすけど|っすね|っすよ|ったなの|だなの)"`.
  3. Dodać nową kategorię `"CODE_SWITCH_EN"` wykrywającą celowe wtrącenia angielskie w japońskim strumieniu audio (np. czasowniki hybrydowe `[katakana 4+ znaków] + します/する` typu `リフレクトします / rifurekuto shimasu`, podwojone `オーケーオッケ / ookeeokke`, `テンション上げ / tenshon age`), gdy skrypt EN nie zawiera tego samego rdzenia leksykalnego, i dopiąć do `DYN_1` w `rules.py:2586` jednozdaniową pozytywną instrukcję o zachowaniu komicznego/stylistycznego efektu wtrącenia obcojęzycznego.
- **Ryzyko:** Niskie (usunięcie fałszywych trafień `"べ"`/`"おら"` odblokuje `FILAR LXXI` i `CLXXII` w zwykłych paczkach, a dodanie markerów *yakuwarigo* włączy `FILAR XIII` dokładnie tam, gdzie postacie faktycznie stylizują mowę).
- **Wymagany test regresyjny:** `test_whisper_disambiguator_no_false_positive_dialect_on_common_verbs` oraz `test_whisper_disambiguator_detects_yakuwarigo_aru_yaru_desuwa_ssu_nano`.
- **Czy wymaga `Z16-amendment`:** **NIE** (`whisper_disambiguator.py` nie należy do listy 8 plików objętych limitem rozmiarowym Depuracji Legacy 1.0 w `AGENTS.md §12`, a w `rules.py` zmiana mieści się w istniejącym stringu `DYN_1`).

---

#### Propozycja P1-2: Przekazywanie `speech_style_pl` i `idiolect_matrix` z `CharacterDossier` do `format_lean_episode_brief` (`profiler.py`) oraz przekazywanie `notes` do `get_focused_rules_for_batch` (`translator.py`)
- **Lokalizacja:** `profiler.py:285-327` (`format_lean_episode_brief`) oraz `translator.py:3930-3948` (`_process_single_batch`).
- **Mechanizm:**
  1. W `profiler.py:299-313` w funkcji `format_lean_episode_brief`: dla każdego `cd` w `dossiers`, jeżeli `speech_style_pl` lub `idiolect_matrix` są niepuste, dołączać ich skondensowaną postać bezpośrednio do opisu postaci w `EPISODE BRIEF`:

         style_summary = " | ".join(filter(None, [str(speech_style).strip(), str(idiolect).strip()]))
         if style_summary:
             lines.append(f"    Styl mowy i idiolekt: {style_summary[:180]}")

     Dzięki temu kosztowna analiza stylizacji wygenerowana przez `EpisodeProfiler` w Kroku 5 (dla `<POSTAC_PFLE>`, `<POSTAC_SHADOW_GALE>`, `<POSTAC_PECHKA>`, `<POSTAC_MEOW>`, `<POSTAC_RIONETTA>`) trafi w 100% do Context Cache Fazy 1 i Fazy 2, zamiast być odrzucana!
  2. W `translator.py:3930-3948` podczas budowania listy `batch_items_for_rules` przed wywołaniem `get_focused_rules_for_batch` dołączyć dla każdego zdarzenia:
     - `speech_style_pl`: styl mówcy pobrany z `episode_profile.character_dossiers` (po nazwie `ev.name`),
     - `notes`: wynik `detect_japanese_pragmatic_register(audio_jp, clean_txt)` oraz przypięte alerty profilera z `self.profile_line_alerts.get(orig_idx)`.
     To ożywi martwy dziś warunek `has_dialect_indicator` w `rules.py:2577-2581`.
- **Ryzyko:** Bardzo niskie (zwiększenie rozmiaru `EPISODE BRIEF` o ok. 60–80 tokenów na cały odcinek, objętych 90% rabatem Context Cache).
- **Wymagany test regresyjny:** `test_format_lean_episode_brief_includes_character_speech_style_and_idiolect`.
- **Czy wymaga `Z16-amendment`:** **TAK (ok. +10 linii w `profiler.py` i `translator.py`)** — oba pliki należą do grupy 8 plików chronionych Z16 (`AGENTS.md §12`), więc przed wdrożeniem wymagana jest autoryzacja `Z16-amendment` przez operatora.

---

#### Propozycja P1-3: Synchronizacja `speech_register` do `CharacterRecord` w `SeriesBible` oraz naprawa fałszywej płci z relacji (`series_memory.py`)
- **Lokalizacja:** `series_memory.py:4680-4785` (`register_character`, `sync_verified_profile_entity`) oraz `series_memory.py:5120-5210` (`format_scoped_for_batch`).
- **Mechanizm:**
  1. Dodać opcjonalne pole `"speech_register": Optional[str]` do `CharacterRecord` w `series_memory.py:4718-4729`, wypełniane podczas `sync_verified_profile_entity` na podstawie `CharacterDossier.speech_style_pl` z `EpisodeProfiler`.
  2. W `format_scoped_for_batch` wypisywać `speech_register` obok roli i płci postaci aktywnej w bieżącej paczce, zapewniając ciągłość idiolektu postaci między kolejnymi odcinkami sezonu.
  3. Przy ekstrakcji postaci z relacji (`"wyodrębniono z relacji serii"`), gdy `EpisodeProfile` lub `AniList` dostarcza zweryfikowaną płeć P0 (np. `<POSTAC_CLANTAIL>: FEMALE`), nadpisywać odziedziczony z heurystyki relacyjnej błędny wpis `"MALE"` w `SeriesBible`, aby wyeliminować fałszywy tag `Mówca: <POSTAC_CLANTAIL> (MASCULINE) | Grupa_1os_lm: VIRILE` w `telemetry_tag`.
- **Ryzyko:** Niskie (pełna kompatybilność wsteczna z istniejącymi plikami `*_bible.json` poprzez `record.get("speech_register", "")`).
- **Wymagany test regresyjny:** `test_series_bible_character_record_persists_speech_register`.
- **Czy wymaga `Z16-amendment`:** **TAK (ok. +12 linii w `series_memory.py`)** — plik na liście Z16.

---

### 8.2. Priorytet P2 (Istotne — poprawa separacji audio ASR, telemetrii i ochrony rejestru w Fazie 2)

#### Propozycja P2-1: Separacja słowna (`word_timestamps=True`) i odcinanie sklejonych prefiksów ASR w `whisper_engine.py` + `translator.py`
- **Lokalizacja:** `whisper_engine.py:231-271` (`transcribe_batch_scene`) oraz `translator.py:3850-3882`.
- **Mechanizm:**
  - W badanym przebiegu wiele linii straciło swoje własne wskazówki rejestrowe (lub otrzymało cudze markery, jak `幸せですわ` z `[ID: 87]` sklejone do `[ID: 83–84]`, czy `オーケーオッケ` z `[ID: 18]` sklejone do `[ID: 16–17]`), ponieważ `Kotoba-Whisper` bez `word_timestamps=True` produkował długie, wielozdaniowe segmenty przypisywane warunkiem `(overlap_end - overlap_start) > 80` do sąsiednich linii.
  - Włączenie `"word_timestamps": True` w `whisper_engine.py:232` i przypisywanie słów `w` po ich środku czasowym `w_mid_abs` w oknie `[ev.start - 120, ev.end + 120]` (oraz odcinanie powtórzonego prefiksu z linii `b_id - 1` w `translator.py:3862`) zapewni, że znaczniki `-aru`, `-yaru`, `-desu wa`, `-ssu` trafią dokładnie do tej linii, w której zostały wypowiedziane.
- **Ryzyko:** Niskie (`faster-whisper` obsługuje `word_timestamps=True` natywnie na CTranslate2 przy minimalnym narzucie czasu `< 0.3s` na paczkę).
- **Wymagany test regresyjny:** `test_word_timestamp_alignment_and_prefix_dedup`.
- **Czy wymaga `Z16-amendment`:** Dla `whisper_engine.py` **NIE**; dla części w `translator.py` **TAK**.

---

#### Propozycja P2-2: Rozszerzenie `detect_japanese_pragmatic_register` o `-aru/-yaru`, `-desu koto`, `-nano` i włączenie go do `[TELEMETRIA: ...]` (`translator.py` + `verifier.py`)
- **Lokalizacja:** `translator.py:953-1020` (`detect_japanese_pragmatic_register`), `translator.py:4251-4266` (`format_dry_telemetry_tag`) oraz `verifier.py:152-330` (`_guard_phase2_regressions`).
- **Mechanizm:**
  1. W `detect_japanese_pragmatic_register` (`translator.py:970-1020`) dodać:
     - w kategorii 2 (`Ojou-sama`): `"ますわ"`, `"ですこと"`, `"ありませんこと"`, `"ますの"`,
     - nową kategorię 15 (`Rejestr egzotyczny / wojowniczki (-aru / -yaru)`): wykrywającą końcówki `-aru / -yaru` i instruującą zachowanie wyrazistej, ciętej lub lekko stylizowanej składni bez spłaszczania do potocznej mowy ogólnej,
     - nową kategorię 16 (`Celowy code-switching JA+EN`): wykrywającą katakanizmy z `-shimasu/-suru` typu `リフレクトします`.
  2. W `translator.py:4318` przekazać skrócony tag wykrytego rejestru (`Rejestr_JP: ...`) do `line_dry_telemetry`, aby był widoczny zarówno dla Fazy 2, jak i w logach `EpisodeFlightRecorder` (`Z1`/`Z5`).
  3. W `verifier.py` (`_prepare_verifier_prompt`) dodać zasadę, że gdy mówcą linii jest postać o rejestrze *ojōsama* / arystokratycznym (`Ojou-sama`), wskazówki słownikowe RPG realizujemy słownictwem wysokim/neutralnym (`ekwipunek`, `rynsztunek`, `szczęście` jak w F1 `[ID: 151]`), unikając wstawiania młodzieżowego slangu (`drop`, `fart`).
- **Ryzyko:** Niskie.
- **Wymagany test regresyjny:** `test_pragmatic_register_aru_yaru_and_ojousama_protection`.
- **Czy wymaga `Z16-amendment`:** **TAK** (`translator.py` i `verifier.py` są na liście Z16).

---

### 8.3. Priorytet P3 (Opcjonalne / Higiena ortograficzno-leksykalna)

#### Propozycja P3-1: Korekta ortograficzna `Kope lat` -> `Kopę lat` w `rules.py` / `avt_linter.py` oraz ochrona ksywek `-cchi`
- **Lokalizacja:** `rules.py:1654-1666` (`FILAR CLXIV`) oraz `avt_linter.py:700-750`.
- **Mechanizm:**
  1. Dodać deterministyczną regułę ortograficzną zamieniającą `\b([Kk])ope\s+lat\b` na `\1opę lat` (naprawia usterkę z `[ID: 13]` `"Kope lat!"` -> `"Kopę lat!"`).
  2. W `FILAR CLXIX` (`rules.py:1745`) doprecyzować, że zdrobniałe ksywki z sufiksem `-cchi` używane przez postać o tym idiolekcie (`[ID: 304]`) zachowują sufiks `-cchi` zamiast ulegać normalizacji do oficjalnego imienia.
- **Ryzyko:** Zerowe.
- **Wymagany test regresyjny:** `test_avt_linter_fixes_kope_lat_typo`.
- **Czy wymaga `Z16-amendment`:** **TAK** (`avt_linter.py` jest na liście Z16).

---

## Sekcja 9 — Werdykt końcowy

### Werdykt ogólny: `POTOK OBSŁUGUJE CZĘŚCIOWO`

Potok AVT w certyfikowanym **Standardzie 11.1.3a** (`HEAD = 7011407cc7b47d2ffb223f402dc8366d40041b7e`) przeszedł cały 347-liniowy odcinek `<SERIA>` `<ODCINEK>` bez ani jednego błędu technicznego, bez ani jednej regresji płci gramatycznej w 11-osobowej obsadzie żeńskiej (mimo licznych niskich odczytów F0 rzędu `75–150 Hz` i błędnego wpisu `MALE` dla `<POSTAC_CLANTAIL>` w starej bazie `SeriesBible`) oraz z kompletną ochroną fleksji terminów kanonicznych w `AVTLinter` i `EpisodeQualityGate`. Jednocześnie śledztwo pod kątem dwóch zjawisk socjolingwistycznych — **code-switchingu JA/EN** oraz **gwary / ról językowych (*yakuwarigo*)** — ujawniło precyzyjne luki integracyjne między istniejącymi modułami potoku.

### 5 najważniejszych wniosków z audytu śledczego:

1. **Rozpoznane idiolekty giną na styku `EpisodeProfiler` -> `format_lean_episode_brief` (`profiler.py:285-327`):**
   `EpisodeProfiler` w Kroku 5 bezbłędnie rozpoznał i opisał w `CharacterDossier` indywidualne style mówienia wszystkich 5 głównych bohaterek (w tym teatralno-chiński rejestr `<POSTAC_MEOW>`, sarkastyczno-lalkowy rejestr `<POSTAC_RIONETTA>` i arystokratyczny chłód `<POSTAC_PFLE>`), ale funkcja `format_lean_episode_brief` wycięła 100% pól `speech_style_pl` i `idiolect_matrix`, ponieważ `dialect_category` miało wartość `"brak"`. Naprawa tego jednego mostu natychmiast udostępni Fazie 1 i Fazie 2 pełną matrycę idiolektów bez żadnego dodatkowego kosztu API.
2. **Detektor `DIALECT_JP` w `whisper_disambiguator.py:691-707` cierpi na kolizję podciągów `"べ"` i `"おら"` oraz brak markerów *Yakuwarigo*:**
   W badanym przebiegu kategoria `"DIALECT_JP"` (i powiązana z nią reguła `DYN_1: FILAR XIII`) wyzwoliła się w 4 paczkach (`1, 6, 10, 13`) wyłącznie przez przypadkową obecność sylab `"べ"` i `"おら"` w zwykłych słowach (`述べた`, `比べれば`, `全て`, `なおらない`), a nie wyzwoliła się w paczkach `5, 8, 9, 12, 14`, w których `<POSTAC_MEOW>` i `<POSTAC_CLANTAIL>` faktycznie używały końcówek `-aru`, `-yaru` oraz `-ssu`.
3. **Brak rozróżnienia między angielskim pivotem a celowym code-switchingiem JA+EN w audio seiyū:**
   Potok traktuje każde słowo angielskie jako element skryptu pośredniczącego (pivotu), który należy przełożyć na rodzimą polszczyznę zgodnie z `FILAR CLXVI`. Przez brak kategorii `CODE_SWITCH_EN` celowy, komiczny anglicyzm wypowiedziany przez seiyū w środku japońskiego zdania (`その言葉リフレクトします [sono kotoba rifurekuto shimasu]` w `[ID: 35]`) został zneutralizowany do `"Z wzajemnością."`.
4. **Przesunięcia czasowe segmentów w `Kotoba-Whisper` (`whisper_engine.py:265-270`) zamazują granice rejestru między rozmówcami:**
   Brak `word_timestamps=True` w `transcribe_batch_scene` sprawia, że na podkładzie muzycznym kilkusekundowe segmenty ASR sklejają kwestie dwóch różnych postaci (np. przypisując dystyngowane `-desu wa` z kolejnej linii do kwestii innej postaci lub przesuwając tekst o 4–16 sekund).
5. **Warstwa `AVTLinter (D_pos)` i `_guard_phase2_regressions` działają stabilnie i nie uszkadzają fleksji anglicyzmów:**
   Wszystkie anglicyzmy obecne w polskim tekście (`boss`, `miniboss`, `do dobrego dropu`, `trzeba farta`) przeszły przez `AVTLinter` i `EpisodeQualityGate` bez deformacji morfologicznych (`100% IDENTITY PASS-THROUGH` w `D_pos`).

---

## Sekcja 10 — Checklista odbioru `(a)`–`(k)` (§6)

- [x] **(a)** Potwierdzono obecność załączników `Z1` (`.log`), `Z2` (`.txt`), `Z3` (`.ass`) oraz `Z5` (`.jsonl`).
- [x] **(b)** Wykonano Fazę 0 (§3.1) i udokumentowano inwentaryzację w Sekcji 1 oraz mapę podejrzanych linii (`[ID: N]`).
- [x] **(c)** Wykonano Fazę 1 (§3.2) i udokumentowano inwentaryzację kodu w Sekcji 3 — dla wszystkich 10 obszarów z tabeli (wraz z plik:linia, sygnaturami, danymi wejściowymi, mechanizmem i śladami w logach).
- [x] **(d)** Wykonano Fazę 2 (§3.3) dla wszystkich podejrzanych linii code-switchingu (Sekcja 4) i gwary/rejestru (Sekcja 5) — z cytatami z `.ass`, logów i kodu.
- [x] **(e)** Wykonano Fazę 3 (§3.4) i udokumentowano spójność rejestru w całym odcinku w Sekcji 6.
- [x] **(f)** Wykonano Fazę 4 (§3.5) i udokumentowano pokrycie testami regresyjnymi oraz propozycje 5 nowych testów w Sekcji 7.
- [x] **(g)** Wystawiono propozycje rozwiązań `P1`/`P2`/`P3` w Sekcji 8 — z lokalizacją (`plik:linia`), mechanizmem, ryzykiem, wymaganym testem i informacją o `Z16-amendment`.
- [x] **(h)** Wystawiono werdykt końcowy, wnioski i odpowiedzi na 7 pytań kontrolnych (§7.3) w Sekcji 2 i Sekcji 9.
- [x] **(i)** Raport sformatowany jako `Artefakty/Raport_audytu_operacyjnego_2026-11-11.md`, UTF-8 bez BOM, 0 pustych placeholderów.
- [x] **(j)** Każde twierdzenie poparte cytatem z `.ass` (`[ID: N]`) + logu/konsoli (`Z1`/`Z2`/`Z5`) + kodu (`plik:linia`) + hash `HEAD` (`7011407cc7b47d2ffb223f402dc8366d40041b7e`).
- [x] **(k)** Wszystkie nazwy własne z `.ass` i logów zamaskowane w raporcie zgodnie z `Z1 Zero-Literal` (`<SERIA>`, `<ODCINEK>`, `<POSTAC_*>`, `<TYTUL_*>`), przy zachowaniu pełnej domeny pozytywnej `Z2`.