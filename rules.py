# -*- coding: utf-8 -*-
"""
Kompletny system reguł i wytycznych przekładu audiowizualnego (AVT) oparty na kanonie dzieł
Arkadiusza Belczyka ("Tłumaczenie filmów", "Sztuka tłumaczenia filmów", "Poradnik tłumacza"),
zasadach adaptacji japońskich tytułów grzecznościowych oraz Netflix Polish Timed Text Style Guide.
"""

from typing import List, Dict, Any, Optional

BELCZYK_AVT_MASTER_CANON = """
KOMPLEKSOWY KANON PRZEKŁADU AUDIOWIZUALNEGO (WG ARKADIUSZA BELCZYKA, JERZEGO PIEŃKOSA, STANISŁAWA BARAŃCZAKA I NORM POLSKIEGO DIALOGU FILMOWEGO):

MODUŁ I: SKŁADNIA, GIĘTKOŚĆ JĘZYKOWA I POLSZCZYZNA FILMOWA (FILARY I – XII)

FILAR I: ODNOMINALIZOWANIE I WERBALIZACJA (CZASOWNIK ZAMIAST RZECZOWNIKA):
- Język angielski jest językiem nominalnym (rzeczownikowym), polski – dynamicznym i czasownikowym.
- Bezwzględnie zamieniaj sztuczne konstrukcje rzeczownikowe na naturalne, giętkie czasowniki:
  * "put together this story / come up with a story" -> "wpaść na to", "poskładać to", "wymyślić to" (ZAKAZ: "ułożyć tę historię").
  * "make a decision" -> "zdecydować", "postanowić" (ZAKAZ: "podjąć decyzję").
  * "take a look" -> "spojrzeć", "zerknąć" (ZAKAZ: "rzucić okiem / wziąć spojrzenie").
  * "have a chat / talk" -> "pogadać", "porozmawiać" (ZAKAZ: "odbyć rozmowę").
  * "do the cleaning" -> "posprzątać" (ZAKAZ: "zrobić sprzątanie").
  * "give an answer" -> "odpowiedzieć" (ZAKAZ: "dać odpowiedź").
  * "make an appearance" -> "zjawić się", "pokazać się" (ZAKAZ: "zrobić pojawienie się").
  * "reach an agreement" -> "dogadać się", "porozumieć się" (ZAKAZ: "osiągnąć porozumienie").

FILAR II: ZASADA ANAFORY, PRO-FORM I ZAIMKA "TO / NA TO" (ZERO-ANAPHORA & SENSE-COHESION):
- 1. ELIMINACJA POWTÓRZEŃ TEMATU:
  * W polskim dialogu filmowym, gdy temat/obiekt został wprowadzony w poprzednim zdaniu, W KOLEJNYM ZDANIU KATEGORYCZNIE ZABRANIA SIĘ POWTARZANIA TEGO SAMEGO RZECZOWNIKA!
  * Należy zastosować zaimek wskazujący ("to", "na to", "o tym", "z tym", "go", "ją"), czasownik frazowy lub elipsę:
    -> Kwestia A: "Wyszła wam całkiem spójna historia." -> Kwestia B: "Jak na to wpadłyście?" / "Jak to wymyśliłyście?" / "Skąd ten pomysł?" (ZAKAZ: "Jak ułożyłyście tę historię?").
    -> Kwestia A: "A jakie mangi lubicie?" -> Kwestia B: "Ja wolę tytuły pełne akcji." / "Te z dużą dawką humoru." (ZAKAZ: "lubię pełne akcji mangi").
    -> Kwestia A: "Mamy pewien plan." -> Kwestia B: "Co zamierzacie?" / "Jaki?" / "O co chodzi?" (ZAKAZ: "Jaki to jest plan?").
- 2. JAPOŃSKA ZEROWA ANAFORA PODMIOTOWA (ZERO-ANAPHORA):
  * W języku japońskim podmiot logiczny jest stale przemilczany. W języku polskim osoba wynika z końcówki czasownika:
    -> KATEGORYCZNY ZAKAZ sztucznego dopisywania zaimków osobowych ("on", "ona", "oni") w każdym zdaniu, jeśli z kontekstu i obrazu wynika, o kogo chodzi.

FILAR III: NATURALNE POLSKIE KOLOKACJE PYTAJĄCE I SYTUACYJNE (ZAMIAST KALK SŁOWNIKOWYCH):
- "How did you put this together / come up with it?" -> "Jak na to wpadłeś?", "Jak to wymyśliłeś?", "Skąd ten pomysł?".
- "What makes you say that?" -> "Skąd ci to przyszło do głowy?", "Dlaczego tak uważasz?", "Czemu tak sądzisz?" (ZAKAZ: "Co sprawia, że tak mówisz?").
- "What brings you here?" -> "Co cię sprowadza?", "Co tu robisz?" (ZAKAZ: "Co cię tu przynosi?").
- "What do you say we...?" -> "A może byśmy...", "Co powiesz na...?", "Chcesz skoczyć na...?".
- "How are you holding up?" -> "Jak się trzymasz?", "Dajesz radę?".
- "What are you getting at?" -> "Do czego zmierzasz?", "O co ci chodzi?".
- "What difference does it make?" -> "A co za różnica?", "Co to zmienia?".
- "What took you so long?" -> "Gdzieś ty był?", "Czemu tak długo?".
- "How did you manage to...?" -> "Jak ci się udało...?", "Jak dałeś radę...?".

FILAR IV: ELIMINACJA SZTUCZNYCH CZASOWNIKÓW POSIŁKOWYCH I POZORNEGO TRWANIA:
- 1. SZTUCZNA ANALITYCZNOŚĆ:
  * "I was able to find it" -> "Znalazłem", "Udało mi się znaleźć" (ZAKAZ: "Byłem w stanie to znaleźć").
  * "I started to cry / laugh" -> "Rozpłakałem się", "Rozśmiałem się" (ZAKAZ: "Zacząłem płakać / śmiać się").
  * "I feel like doing X" -> "Mam ochotę na X", "Chcę X" (ZAKAZ: "Czuję się jak robienie X").
  * "I have a feeling that..." -> "Coś mi mówi, że...", "Wydaje mi się, że..." (ZAKAZ: "Mam uczucie że").
  * "It looks like it's going to rain" -> "Zbiera się na deszcz", "Chyba będzie padać" (ZAKAZ: "Wygląda jakby miało padać").
  * "Welcome back" -> "Witaj!", "Dobrze cię widzieć!", "Wróciłeś!", "Witaj w domu!" (ZAKAZ: "Witaj z powrotem").
- 2. KALKI KONSTRUKCJI POZORNEGO TRWANIA I POSIADANIA:
  * "is in the process of doing" -> "właśnie robi", "robi" (ZAKAZ: "jest w trakcie robienia").
  * "came into possession of" -> "zdobył", "ma", "wszedł w posiadanie" (ZAKAZ: "znalazł się w posiadaniu").

FILAR V: ELIMINACJA ZBĘDNYCH ZAIMKÓW DZIERŻAWCZYCH I OSOBOWYCH:
- Angielski wymaga zaimka przy każdej części ciała i własności. Po polsku relacja wynika z kontekstu:
  * "I put my hands in my pockets" -> "Włożyłem ręce do kieszeni" (ZAKAZ: "moje ręce do moich kieszeni").
  * "She talked with her sister" -> "Rozmawiała z siostrą" (ZAKAZ: "ze swoją siostrą").
  * "Close your eyes" -> "Zamknij oczy" (ZAKAZ: "twoje oczy").
  * "I broke my leg" -> "Złamałem nogę" (ZAKAZ: "moją nogę").
  * "I think that..." -> "Myślę, że..." (ZAKAZ: "Ja myślę, że...").

FILAR VI: DEPASYWIZACJA (STRONA BIERNA -> CZYNNA / BEZOSOBOWA - TOMASZ TOMASZKIEWICZ):
- Angielską stronę bierną kategorycznie zastępuj polską stroną czynną lub formami bezosobowymi:
  * "It was decided that..." -> "Ustaliliśmy, że..." / "Zdecydowaliśmy, że..." (ZAKAZ: "Zostało zdecydowane").
  * "He was given an award" -> "Dostał nagrodę" / "Wręczono mu nagrodę" (ZAKAZ: "Została mu dana").
  * "The car was stolen" -> "Ukradli samochód" / "Skradziono samochód" (ZAKAZ: "Samochód został skradziony").

FILAR VII: ELIMINACJA NADMIARU ZAIMKA WZGLĘDNEGO "KTÓRY / KTÓRA":
- Unikaj tworzenia ciężkich zdań podrzędnych z "który" w mowie potocznej. Stosuj zwięzłe formy imiesłowowe, przymiotnikowe lub podział zdania.

FILAR VIII: NATURALNY POLSKI SZYK ZDANIA I INWERSJA EMFATYCZNA (STRUKTURA TEMAT-REMAT):
- 1. STRUKTURA INFORMACYJNA (TEMAT-REMAT):
  * W języku polskim najważniejsza NOWA informacja ląduje na KOŃCU zdania (remat), a punkt wyjścia na początku.
  * Zmieniaj sztywny angielski szyk SVO na elastyczną polską frazę.
- 2. INWERSJA EMFATYCZNA W SCENACH AKCJI:
  * W dynamicznych scenach walki i rozkazach bojowych dopuszcza się inwersję czasownika na początek dla wzmocnienia ładunku dramatycznego ("Uciekać musimy!", "Padnij!").

FILAR IX: PYTANIA POTOCZNE, ELIMINACJA SZTUCZNEGO "CZY" I NEGACJA RETORYCZNA (SZARKOWSKA & BELCZYK):
- 1. PYTANIA ROZSTRZYGNIĘCIA W MOWIE POTOCZNEJ:
  * W filmie NIE zaczyna się każdego pytania od "Czy...". Pytania rozstrzygnięcia tworzy się intonacją:
    -> BŁĄD [X]: "Czy jesteś pewna?", "Czy widziałaś to?", "Czy idziesz z nami?", "Czy to prawda?".
    -> POPRAWNIE [OK]: "Jesteś pewna?", "Widziałaś to?", "Idziesz z nami?", "To prawda?" / "Serio?".
  * Partykułę "Czy" zachowaj WYŁĄCZNIE w pytaniach alternatywnych ("Kawa czy herbata?") lub w bardzo oficjalnym tonie.
- 2. JAPOŃSKA NEGACJA RETORYCZNA (~JA NAI KA? / ~DEWA NAI KA? - RHETORICAL ASSERTIONS):
  * W języku japońskim pytania przeczące często pełnią funkcję SILNEGO TWIERDZENIA (entuzjastycznej aprobaty lub oburzenia), a nie wątpliwości:
    -> "Kore de kachi ja nai no?!" -> "Przecież wygraliśmy!" / "Mamy wygraną w kieszeni!" (ZAKAZ: "Czy to nie jest wygrana?").
    -> "Oishii ja nai ka?" -> "Ależ to pyszne!" / "Przecież to świetne!" (ZAKAZ: "Czyż to nie jest smaczne?").
    -> "Ii kangae ja nai?" -> "Świetny pomysł!" / "To genialna myśl!" (ZAKAZ: "Czy to nie jest dobry pomysł?").

FILAR X: BEZWZGLĘDNA ELIMINACJA TRZECIEGO JĘZYKA (ANTI-TRANSLATIONESE MANIFESTO):
- Eliminacja tzw. "języka przekładu" – zdań poprawnych słownikowo, ale obcych polskiemu uchu:
  * BŁĄD [X]: "Co sprawia, że tak mówisz?", "Jestem zrobiony z...", "Wzięcie pod uwagę...", "Pomyśl o tym!", "To ma miejsce w Tokio", "W wypadku kiedy to zrobisz...".
  * POPRAWNIE [OK]: "Czemu tak sądzisz?", "Taki już jestem...", "Uwzględniając...", "Zastanów się!", "Dzieje się to w Tokio", "Jeśli to zrobisz...".

FILAR XI: TEORIA PREFABRYKOWANEJ MÓWIONOŚCI (FREDERIC CHAUME & YVES GAMBIER):
- Dialog filmowy to język napisany, by brzmieć tak, jakby w ogóle nie był napisany.
  * KATEGORYCZNY ZAKAZ struktur podręcznikowych (imiesłowów przysłówkowych w mowie potocznej: "Idąc do szkoły, ujrzałem").
  * Stosuj naturalną eliptyczność, żywą polszczyznę mówioną i asonanse ("Szedłem do szkoły i nagle patrzę...").

FILAR XII: KRYTERIUM CZYSTOŚCI FONETYCZNEJ I MÓWIONEJ (THE READ-ALOUD AUDITORY LITMUS TEST):
- Żelazny test lektora/aktora (Auditory Litmus Test):
  * Każda linijka musi brzmieć lekko, gładko i naturalnie przy przeczytaniu na głos.
  * ZAKAZ trudnych do wymówienia zbitków spółgłoskowych ('wzwyż wzbraniać'), nienaturalnego akcentu zdaniowego oraz sztucznych rymów częstochowskich w prozie.


MODUŁ II: PRAGMATYKA KULTUROWA, YAKUWARIGO I REALIA ANIME (FILARY XIII – XXIV)

FILAR XIII: TEORIA JĘZYKA RÓL (YAKUWARIGO SATOSHI KINSUI) I REJESTRY DIALEKTALNE:
- W anime każda postać posługuje się unikalnym socjolektem i rolą językową (Yakuwarigo). KATEGORYCZNY ZAKAZ mówienia przez wszystkie postacie "jednym bezbarwnym głosem tłumacza":
  * Ojousama (Dama / Arystokratka): Wykwintna, dystyngowana polszczyzna, pełne zdania ("Doprawdy, to wielce niestosowne", "Cóż za impertynencja").
  * Yankee / Łobuz (Ore-sama): Szorstka, rwana polszczyzna, skróty, zuchwały ton ("Czego się gapisz?!", "Spadaj stąd!").
  * Hakase / Stary mędrzec (Washi): Anachroniczne, mądre słownictwo ("Powiadam ci...", "Zaiste, to niezwykłe").
  * Gyaru / Imprezowiczka: Dynamiczny, współczesny język młodzieżowy ("Mega!", "Czyste szaleństwo!").
  * Kudere / Stoik: Oszczędne, chłodne, precyzyjne komunikaty bez zbędnych emocji.
  * Kansai-ben (dialekt Osaki): KATEGORYCZNY ZAKAZ tłumaczenia na sztuczną gwarę śląską czy góralską! Stosuj swobodny, dynamiczny, miejski język potoczny (błyskotliwe riposty, humor, zadziorność, bezceremonialność).
  * Chuunibyou (Syndrom gimbazy): Egzaltowane, archaizujące i pseudomagiczne słownictwo o komicznym patosie.

FILAR XIV: MATRYCA REALIÓW KULTUROWYCH ECR (7 STRATEGII JANA PEDERSENA):
- Realia kulturowe (Extralinguistic Cultural References - ECR) tłumacz według 7 strategii Pedersena:
  1. Official Equivalent: Oficjalny polski odpowiednik (np. 'Ministerstwo Spraw Wewnętrznych', 'Tokijski Uniwersytet Sztuki').
  2. Retention: Zachowanie pojęcia powszechnego w popkulturze (ramen, katana, kotatsu, onsen, kimono, senpai, taiyaki, tatami), gdy obiekt widać na ekranie.
  3. Specification: Doprecyzowanie hipernimem pojęć kluczowych a mniej znanych ('góra Fuji', 'rzeka Sumida', 'święto Obon', 'szachy japońskie shogi', 'amulet ochronny omamori').
  4. Direct Translation: Dosłowne tłumaczenie pojęć uniwersalnych ('Gildia Kupiecka', 'Rada Cieni').
  5. Generalization: Uogólnienie pojęć niszowych spowalniających lekturę ('konbini' -> 'sklep / sklep całodobowy', 'dagashi' -> 'słodycze / przekąski').
  6. Situational Substitution: Zastąpienie obcej metafory naturalną polską metaforą o identycznym ładunku emocjonalnym.
  7. Omission (Pominięcie): Pominięcie drobnej, nadmiarowej nazwy kulturowej, gdy termin nie wnosi nic do fabuły, a czas na przeczytanie napisu przekracza limit 17 CPS.

FILAR XV: LOKALIZACJA GIER SŁOWNYCH, KALAMBURÓW I KOMPENSACJA HUMORU (DELABASTITA & WIERZBIĘTA):
- KATEGORYCZNY ZAKAZ dosłownego tłumaczenia japońskich gier słownych (Dajare / Kakekotoba)! Dosłowne tłumaczenie żartu opartego na homonimach niszczy komizm sceny:
  1. Pun to Pun (Kompensacja w miejscu): Stwórz polską grę słowną opartą na tym samym motywie tematycznym, pasującą do obrazu i mimiki postaci.
  2. Pun to Non-Pun + Kompensacja Przesunięta: Jeśli żartu nie da się odtworzyć w tej samej linijce, dodaj żartobliwy akcent w kolejnej kwestii, aby zachować ogólny bilans humoru sceny.
  3. Lepszy jest świeży polski dowcip sytuacyjny niż suchy dosłowny bełkot z przypisem!

FILAR XVI: PRAGMATYKA JAPOŃSKICH CZĄSTEK KOŃCZĄCYCH (SHŪJOSHI PRAGMATIC MATRIX):
- Oddawanie intencji illokucyjnej japońskich partykuł końcowych w żywej polszczyźnie:
  * 'Zo' (męska determinacja) -> stanowczy czasownik i wykrzyknik ("No to ruszamy!", "Wchodzę tam!").
  * 'Ze' (zuchwałość rówieśnicza) -> dynamiczne partykuły wzmacniające ("No i załatwione!", "Widziałeś to?").
  * 'Kashira' (kobiecy namysł/wątpliwość) -> "Ciekawe, czy...", "Może by tak...".
  * 'Yo ne' (potwierdzenie wspólnej wiedzy) -> "Prawda?", "No nie?", "Przecież sami wiecie...".
  * 'Mon / Mono' (dziecięce dąsanie się/usprawiedliwienie) -> "Przecież...", "No bo mi się spieszyło!".
  * 'Wa' (kobieca dystyngowana opinia) -> miękki ton, inwersja ("Ależ to urocze...").
  * 'Sa' (pobłażliwa oczywistość) -> "Wiadomo...", "Rzecz jasna...".
  * 'Ja' (archaiczna pewność mędrca zamiast 'da') -> dostojne polskie orzeczenie ("Oto prawda...").

FILAR XVII: PIĘCIOSTOPNIOWA TAKSONOMIA SYMBOLIZMU DŹWIĘKOWEGO ANIME (ONOMATOPOEIA 5-TIER SYSTEM):
- Precyzyjne rozróżnienie i przekład 5 klas japońskich onomatopei na soczyste polskie metafory sensoryczne i somatyczne:
  1. Giseigo (głosy istot żywych): 'wan-wan' -> 'hau-hau', 'nyaa' -> 'miau', 'kusu-kusu' -> 'chichot pod nosem'.
  2. Giongo (dźwięki fizyczne przyrody): 'za-za' -> 'ściana deszczu / ulewa', 'goro-goro' -> 'grzmot / pomruk burzy'.
  3. Gitaigo (stany statyczne i bezdźwięczne): 'shiin' -> 'cisza jak makiem zasiał', 'pika-pika' -> 'lśnić jak złoto / błysk'.
  4. Giyougo (sposób poruszania się): 'noro-noro' -> 'ślimaczym tempem', 'yoro-yoro' -> 'chwiejnym krokiem / słaniać się'.
  5. Gijougo (uczucia i stany somatyczne): 'doki-doki' -> 'serce podchodzi do gardła / wali', 'ira-ira' -> 'aż mnie nosi / szlag mnie trafia', 'waku-waku' -> 'aż mnie skręca z ciekawości', 'kyun' -> 'ścisnęło mnie za serce', 'zokutto' -> 'przeszły mnie ciarki / dreszcz'.

FILAR XVIII: ADAPTACJA PARALINGWISTYKI, DŹWIĘKÓW POZAWERBALNYCH I INTERIEKCJI FONICZNYCH:
- Kategoryczny zakaz dosłownego przepisywania surowych japońskich odgłosów komiksowych:
  * "Tch" / "Che" -> "Tsk...", "Szlag...", "Ech..." lub elipsa, jeśli grymas twarzy wystarczy.
  * "Eh?!" (zdumienie) -> "Co?!", "Jak to?!", "Słucham?!".
  * "Guh..." / "Ku..." (ból/wysiłek) -> "Uch...", "Niech to...", "Agh...".
  * "Ara ara" (pobłażliwe rozbawienie damy/starszej siostry) -> "O proszę...", "Doprawdy...", "Niebywałe...", "Ależ tak...".
  * "Oi oi" (ostrzeżenie/protest) -> "Hej, hej!", "Spokojnie!", "Bez przesady!".
  * "Ano..." / "Etto..." (niepewność przed wypowiedzią) -> "Yy...", "Ten...", "Cóż...", "No bo...".

FILAR XIX: SŁOWNIK EMOCJONALNYCH REAKCJI I WYKRZYKNIKÓW ANIME:
- "Maji de?" / "Gachi de?" -> "Serio?!", "Naprawdę?!", "Bez jaj!".
- "Uso!" / "Uso desho?!" -> "Nie gadaj!", "Nie wierzę!", "Żartujesz!".
- "Sasuga!" -> "I to jest klasa!", "Wiedziałam!", "Jak zawsze niezawodna!".
- "Yatta!" -> "Udało się!", "Mamy to!", "Super!", "Ekstra!".
- "Baka!" / "Aho!" -> "Durna!", "Głupia!", "Idiotka!" (dla dziewczyny) / "Palant!", "Kretyn!" (dla chłopaka).
- "Chotto matte!" -> "Czekaj no!", "Chwila!", "Zaraz!".
- "Doushita no?" -> "Co jest?", "Co się stało?", "Coś nie tak?".
- "Ikinari?!" -> "Tak z nienacka?!", "Tak nagle?!".
- "Mendou kusai" -> "Ale mi się nie chce...", "Co za udręka...", "Męczące to...".
- "Yada / Ya da!" -> "Nie ma mowy!", "Nie chcę!", "O nie!".
- "Bikkuri shita!" -> "Ale mnie wystraszyłaś!", "Aż podskoczyłam!".

FILAR XX: EKWIWALENCJA PRAGMATYCZNA I AKTY MOWY (MONA BAKER & EUGENE NIDA):
- Tłumacz INTENCJĘ KOMUNIKACYJNĄ (akt mowy), a nie dosłowną formę gramatyczną:
  * W kulturze japońskiej bezpośrednia odmowa jest tabu ("Chotto muzukashii desu..." dosł. "To jest trochę trudne...").
  * KATEGORYCZNY ZAKAZ dosłownego "To jest trochę trudne", gdy bohater odmawia!
  * POPRAWNIE: "Obawiam się, że to niemożliwe", "Niestety, wykluczone", "Nie ma mowy".

FILAR XXI: EKSPLIKACJA PODTEKSTU I TEORIA IMPLIKATUR (PAUL GRICE & HARAGEI UNPACKING):
- W kulturze japońskiej sens bywa przemilczany ("Sore wa chotto..."). W języku polskim wymagana jest umiarkowana eksplikacja intencji odmowy ("Obawiam się, że to niemożliwe", "Wykluczone") zamiast urwanego "To trochę...".
- Odkodowywanie presupozycji i implikatur konwersacyjnych: jeśli podtekst jest kluczowy dla zrozumienia sceny przez polskiego widza, wyartykułuj go zwięźle.

FILAR XXII: PRZEKŁAD TYTUŁÓW DZIEŁ, MITOLOGII I INTERTEKSTUALNOŚCI (ALLUSION & CANON RECOGNITION):
- Cytaty, nawiązania literackie, mitologiczne i popkulturowe:
  * Sprawdzaj ugruntowany polski kanon (np. 'Hrabia Monte Christo', 'Sherlock Holmes', 'Król Artur', 'Mitologia Nordycka').
  * Cytaty z klasyki (Szekspir, Biblia, Mickiewicz, Lem) tłumacz zgodnie z kanonicznymi polskimi przekładami, a nie z translacji powrotnej!

FILAR XXIII: KANON POLSKICH WYDAŃ MANGOWYCH I SPÓJNOŚĆ TRANSMEDIALNA (TRANSMEDIA CANON CONSISTENCY):
- Gdy seria posiada oficjalny polski przekład mangowy (np. Waneko, J.P.Fantastica, Studio JG, Hanami, Kotori):
  * BEZWZGLĘDNIE zachowaj ustalone w polskim wydaniu papierowym nazwy technik, magii, krain, formacji bojowych i rang (np. "Rozszerzenie Domeny", "Przeklęta Energia", "Korpus Zwiadowczy", "Wielki Generał", "Państwo Środka").
  * RÓŻNICA AVT vs MANGA: Zachowaj kanoniczną terminologię, ale przestrzegaj rygoru zwięzłości napisów filmowych (limit 17 CPS i 42 znaków). Nie przenoś tasiemcowych zdań z dymków komiksu bez uprzedniej kondensacji składniowej.

FILAR XXIV: KONWENCJE DLA ŻARGONU GIER, ISEKAI I SYSTEMÓW RPG (STATUS WINDOWS & SKILL NAMES):
- Gry, Isekai, LitRPG i światy z interfejsem systemowym:
  * Nazwy umiejętności (Skills), czarów i klas postaci -> zwięzłe, wyraziste polskie miana zgodne z tradycją RPG ('Kula Ognia', 'Błogosławieństwo Światła', 'Rozszerzenie Domeny', 'Kradzież Cienia').
  * Komunikaty systemowe i okna statusu: wersaliki lub formatowanie techniczne [ OKNO STATUSU: POZIOM 50 ].
  * Zakaz surowego mieszania angielskich nazw menu z polskim tekstem, jeśli nie wymaga tego stylistyka retro (np. 8-bit).


MODUŁ III: ETYKIETA SPOŁECZNA, RELACJE I DRAMATURGIA POSTACI (FILARY XXV – XXXV)

FILAR XXV: PRZEKŁAD RELACJI RODZINNYCH, FEUDALNYCH I ZASADA JEDNOKROTNEJ TYTULATURY (ANTI-HONORIFIC SPAM):
- RELACJE RODZINNE: ZAKAZ tłumaczenia japońskiego "Onii-chan / Onee-san" jako sztucznego "starszy bracie / starsza siostro"! Zastępuj to imieniem brata/siostry, zwrotem "braciszku / brachu / siostra" (w sytuacjach czułych/żartobliwych) lub pomijaj na rzecz naturalnego polskiego zdania.
- ETYKIETA FEUDALNA I ZASADA JEDNOKROTNEJ TYTULATURY (ZAKAZ PRZESYTU 'PAN / PANI'):
  * W relacjach feudalnych, samurajskich, dworskich oraz bóstwo-dziedzic (np. kapłan/wasal do młodego lorda, doradca do generała):
    -> ZASADA JEDNOKROTNEJ TYTULATURY: Szacunek nadaje zwrot tytularny użyty RAZ na początku lub na końcu wypowiedzi ("młody panie", "panie generale", "panie Tokiyuki").
    -> KATEGORYCZNY ZAKAZ POWTARZANIA 'PAN/PANA/DLA PANA' W KAŻDYM ZDANIU: Wewnątrz monologu i kolejnych zdań stosuj naturalną 2. osobę ("przemierzasz", "gdyby cię pojmał", "zrobiłeś już dość") lub elipsę ("robi się tu zbyt niebezpiecznie" zamiast sztucznego "dla pana").
    -> BŁĄD [X]: "Przemierza pan pole bitwy... gdyby pana pojmał... by zastawić na pana sieć... robi się tu dla pana niebezpiecznie... zrobił pan już dość, panie Tokiyuki." (8 razy pan!).
    -> POPRAWNIE [OK]: "To ty, młody panie. Przemierzasz pole bitwy... gdyby cię pojmał... by zastawić na ciebie sieć... robi się tu zbyt niebezpiecznie. Zrobiłeś już dość, panie Tokiyuki."

FILAR XXVI: ZASADA YOBISUTE I ZAKAZ SZTUCZNEGO „PANA/PANI” PRZY SAMYM IMIENIU (ANTI-FALSE FORMALITY):
- ZWROT PO SAMYM IMIENIU (Yobisute - Issei, Shizuku, Loulan, Arata):
  * Gdy w audio lub tekście postać zwraca się do rozmówcy po SAMYM IMIENIU bez japońskich honoryfikatorów:
    -> BŁĄD [X]: Dodawanie słowa "Pan/Pani" ("Pan Issei", "panie Issei", "pani Loulan").
    -> POPRAWNIE [OK]: Zwracanie się bezpośrednio po imieniu na "ty": "Issei, co o tym myślisz?", "Shizuku, spróbuj tego wina!".
- RELACJE BLISKIE, TOWARZYSKIE, RYWALIZUJĄCE I POSTACIE ZAGRANICZNE:
  * Towarzysze podróży, rywale, przyjaciele oraz cudzoziemcy nieznający sztywnej etykiety biurowej ZAWSZE mówią do siebie po imieniu na "ty".
- KIEDY STOSUJEMY FORMĘ „PAN/PANI”:
  * WYŁĄCZNIE przy formalnych zwrotach po NAZWISKU z honoryfikatorem (np. Tomine-sensei -> "pan Tomine", Kanzaki-san -> "pan Kanzaki") lub w oficjalnych relacjach urzędowych/kelner-klient.

FILAR XXVII: ZAKAZ HYBRYD HONORYFIKATYWNYCH (ANTI-DOUBLE HONORIFIC HYBRID):
- ZAKAZ ŁĄCZENIA POLSKIEJ TYTULATURY Z JAPOŃSKĄ:
  * Kiedy w audio pada japoński tytuł (np. "Sensei!", "Senpai!", "Teshima-sensei!"):
    -> BŁĄD [X]: "Pani Sensei, skończyłam!", "Panie Sensei!", "Pani Senpai!" (sprzeczne tytulatury!).
    -> POPRAWNIE W TRYBIE ANIME [OK]: "Sensei, skończyłam!", "Teshima-sensei, skończyłam!", "Senpai!".
    -> POPRAWNIE W TRYBIE NATURALNYM [OK]: "Pani Teshimo, skończyłam!", "Mistrzyni, skończyłam!", "Szefowo, skończyłam!".

FILAR XXVIII: DYNAMIKA FORM ADRESATYWNYCH, UCHI-SOTO I TRIADA KEIGO (BROWN & LEVINSON):
- Granica grupy Własnej (Uchi) i Obcej (Soto) oraz triada grzecznościowa:
  * 1. Relacje Uchi-Soto: Gdy bohater mówi o członkach własnej grupy/rodziny/firmy do kogoś z zewnątrz: ZAKAZ stosowania wobec nich form wywyższających w 3. osobie (np. pracownik do klienta mówi "Nasz dyrektor Kowalski", a nie "Nasz pan dyrektor").
  * 2. Triada Honoryfikatywna:
     - Sonkeigo (wywyższanie rozmówcy) -> naturalne polskie formy grzecznościowe i szacunek ("Czy zechciałby pan spojrzeć?").
     - Kenjougo (uniżanie siebie/własnych działań) -> w języku polskim przekładaj na profesjonalizm i gotowość pomocy ("Zajmę się tym natychmiast", "Pozwolę sobie zauważyć"), a NIE na sztuczną, czołobitną uniżoność.
     - Teineigo (grzeczność neutralna - desu/masu) -> standardowa uprzejma polszczyzna.
  * 3. Przedrostki Upiększające Bikago (o- / go-): Prefiksy o-cha, o-bento, go-shitsumon oddają elegancję mówcy, a NIE dosłowne "szanowna herbata" czy "szanowny obiad"!
  * Przejście na formy "Pan/Pani" vs "Ty" musi wynikać z dynamiki zażyłości, wieku i pozycji społecznej.

FILAR XXIX: EWOLUCJA DYSTANSU SPOŁECZNEGO I PŁYNNOŚĆ FORM W CZASIE (SOCIAL DISTANCE CURVE):
- Śledzenie dynamiki zażyłości między postaciami w toku fabuły:
  * Etap 1 (obcość/dystans): formy "Pan/Pani" lub tytuły stanowiskowe.
  * Etap 2 (przełamanie lodów/wspólna walka): przejście na imię i formę "Ty" (moment bratania się).
  * Etap 3 (intymność/braterstwo): swobodne, ciepłe zwroty potoczne.
  * ZAKAZ powrotu do sztucznego "Pan/Pani" po scenie zbratania się bohaterów!

FILAR XXX: PRZEŁAMANIE REJESTRU I DRAMATURGIA FORMY (POLITENESS SHIFT & KEIGO BREAKDOWN):
- 1. Zerwanie Grzeczności w Szoku/Gniewie: Gdy postać używająca form grzecznościowych (Keigo / pan / pani / Wasza Wysokość) wpada w skrajny gniew lub szok, NATYCHMIAST zerwij formy grzecznościowe i przejdź na bezpośrednie, ostre "ty".
- 2. Przełamanie Odwrotne (Ironiczne Wejście w Keigo): Gdy zuchwała postać nagle zaczyna mówić przesadnie uprzejmym, chłodnym tonem oficjalnym, oddaj w języku polskim lodowaty dystans, szyderstwo lub ukrytą groźbę.

FILAR XXXI: MATRYCA TOŻSAMOŚCI I KAMUFLAŻU PŁCIOWEGO (GENDER-BENDER & DISGUISE MATRIX):
- W anime z motywem kamuflażu tożsamości, cross-dressingu lub ukrywania prawdziwej płci (np. dziewczyna udająca chłopaka):
  * DIALOG PUBLICZNY (MASKA SPOŁECZNA): Obowiązkowa gramatyka kamuflażu ("Spóźniłem się!", "Myślałem, że mamy trening").
  * MONOLOG WEWNĘTRZNY / MYŚLI / NARRACJA: Prawdziwa płeć postaci ("O rany, prawie się wydałam...", "Gdyby to zobaczył, byłabym skończona").
  * STREFA POWIERNIKA (NA OSOBNOŚCI): Prawdziwa tożsamość w rozmowie 1-na-1 z osobą znającą tajemnicę ("Nie mogłam inaczej, doktorze").
  * ZAMIERZONE PRZEJĘZYCZENIA: Autentyczne polskie korekty w panice ("Zrobiłam... to znaczy zrobiłem wszystko!").

FILAR XXXII: AKUSTYCZNA KOHERENCJA REJESTRU WIEKOWEGO (AGE-COHORT VOCAL REALISM):
- Dobór słownictwa musi odpowiadać wiekowi i pozycji postaci: nestor/starzec (dostojne frazy), małe dziecko (krótkie, proste zdania bez wielopiętrowych struktur), nastolatek (dynamiczny język z żywymi partykułami).

FILAR XXXIII: KALIBRACJA REJESTRU WULGARYZMÓW I ŁADUNKU EMOCJONALNEGO TABU (VULGARITY CURVE & PRAGMATICS):
- Dopasuj siłę ekspresji do intencji komunikacyjnej i gatunku:
  * 1. Wulgaryzmy fatyczne/przecinkowe (wykrzykniki złości: "Kuso!", "Damn it!") -> zwięzłe polskie "Szlag!", "Niech to!", "Cholera!".
  * 2. Wulgaryzmy agresywne/obraźliwe (personalne obelgi: "Kisama!", "Kono yarou!") -> dosadne polskie odpowiedniki ("Gnoju!", "Ty bydlaku!", "Gnojku!").
  * 3. Wulgaryzmy w seriach młodzieżowych ugrzeczniaj do poziomu naturalnego slangu szkolnego ("Palant", "Dureń", "Kretyn").
  * 4. Mroczny kryminał / seria militarna / Seinen: ostre, autentyczne odzywki żołnierskie i gangsterskie bez sztucznego ugrzeczniania.

FILAR XXXIV: KALIBRACJA PATOSU W PRZEMOWACH BOJOWYCH I DEKLARACJACH MORALNYCH (HEROIC REGISTER):
- Podniosłe sceny bitewne, przysięgi rycerskie i kulminacje dramatyczne:
  * Podnoś rejestr stylistyczny do szlachetnej, bohaterskiej polszczyzny (patos, rytm, dostojne czasowniki).
  * ZAKAZ gaszenia podniosłej sceny trywialnymi, płaskimi kolokwializmami ("Będziemy walczyć na maksa" -> "Będziemy walczyć do ostatniej kropli krwi!").

FILAR XXXV: ZASADA IZOTOPII SEMANTYCZNEJ I SPÓJNOŚCI REJESTRU WYPOWIEDZI (SNELL-HORNBY & NIDA):
- Bezwzględny zakaz dysonansu rejestrów stylistycznych w obrębie jednej kwestii/sceny:
  * Nie łącz wyszukanego słownictwa archaicznego lub poetyckiego z tanim, współczesnym slangiem (np. BŁĄD [X]: "Zaiste, Wasza Miłość, to totalna masakra").
  * Każda postać musi zachować spójny, jednolity idiolekt przez cały odcinek.


MODUŁ IV: MULTIMODALNOŚĆ, WIDEO I INTEGRACJA ZMYSŁOWA (FILARY XXXVI – XLII)

FILAR XXXVI: NADMIAROWOŚĆ INTERSEMIOTYCZNA I KOMPENSACJA MULTIMODALNA (DÍAZ CINTAS & GOTTLIEB):
- Film to medium wielokanałowe. KATEGORYCZNY ZAKAZ opisywania w napisach tego, co widz widzi na własne oczy w obrazie i mimice lub słyszy w efektach dźwiękowych:
  * Jeśli postać podaje klucze i mówi długie zdanie, po polsku wystarczy: "Trzymaj" lub "Twoje klucze".
  * Gdy w tle słychać wyraźną syrenę radiowozu, unikaj redundancji ("Słyszę syreny policji!" -> "Policja!").
  * Wykorzystuj synergię obrazu, aby skrócić tekst i dać widzowi czas na patrzenie na akcję.

FILAR XXXVII: CZASOWNIKI WEKTOROWE I CIĘCIA MONTAŻOWO-PRZESTRZENNE (DIRECTIONAL VERBS & SCENE TRANSITION):
- CZASOWNIKI Z ASPEKTEM WEKTOROWYM (-TE KURU / -TE IKU):
  * Japoński sufiks ~te kuru (見えてきた - Mietekita) oznacza FIZYCZNE PRZYBLIŻANIE SIĘ lub wyłanianie obiektu w polu widzenia ("Ukazał się!", "Już widać!", "Dochodzi nas dźwięk...").
  * Japoński sufiks ~te iku (消えていく - Kieteiku) oznacza ODDALANIE SIĘ w przestrzeni lub proces postępujący w przyszłość ("Znika w oddali...", "Będzie gasnąć...").
  * BŁĄD [X]: Tłumaczenie angielskiego "I can see it!" (gdy w audio pada "Mietekita!" na tle samolotu/podróży) jako "Widzę to po tobie / po panu!".
  * POPRAWNIE [OK]: "Już widać!", "Widać cel!" (w odniesieniu do lądu/miasta wyłaniającego się zza chmur).
- RESPEKTOWANIE CIĘĆ SCENICZNYCH (TIME/LOCATION JUMP):
  * Jeśli między kwestią A a B następuje zmiana sceny (gabinet -> samolot), kwestia B jest nową sytuacją plenerową, a NIE ripostą do rozmowy!

FILAR XXXVIII: PRZESTRZENNA DEIKSA WZROKOWA I TRÓJSTOPNIOWY SYSTEM KOSOADO:
- Zgraj zaimki wskazujące z obrazem na ekranie w oparciu o japoński system Ko-So-A-Do:
  * Ko (przy mówiącym: kore/koko) -> "to tutaj / ten przy mnie".
  * So (przy słuchaczu: sore/soko) -> "to u ciebie / ten twój / tam przy tobie".
  * A (oddalone od obu rozmówców: are/asoko) -> "tamto na horyzoncie / tamten w oddali / o tam".
  * Zakaz spłaszczania deiksy do losowego "to/tamto" sprzecznego z gestem i wzrokiem postaci.

FILAR XXXIX: ELIMINACJA NOŻYC OBRAZOWO-TEKSTOWYCH (TEXT-BILD-SCHERE):
- Szyk wyrazów w napisie musi odpowiadać chronologii gestów na ekranie w ułamku sekundy.
  * Jeśli bohater najpierw wyciąga miecz, a potem tnie linę, zdanie musi zaczynać się od miecza, a kończyć na cięciu, eliminując dysonans poznawczy.

FILAR XL: ŚWIADOMOŚĆ RUCHU UST I KADENCJA WYKAZOWA (LIP-FLAP CADENCE AWARENESS):
- Krótki, gwałtowny japoński wykrzyknik aktora (np. "Baka!", "Kuso!", "Yamero!") MUSI otrzymać równie krótki, dosadny polski odpowiednik ("Szlag!", "Idiota!", "Stój!"). Zakaz rozbudowywania krótkich okrzyków w tasiemcowe zdania.

FILAR XLI: PRZEKŁAD NAPISÓW EKRANOWYCH I STANDARD DUAL-TRACK SUBTITLING (SIGNS & TYPESETTING):
- Kiedy kwestia jest oznaczona jako NAPIS EKRANOWY / TYTUŁ / PLANSZA (Signs / Typesetting):
  * MUSI być przetłumaczona jako SAMODZIELNY TYTUŁ LUB NAZWA (np. "The Princess's Favor" -> "Łaska księżniczki").
  * KATEGORYCZNY ZAKAZ wklejania w pole napisu ekranowego fragmentów wypowiedzi mówionych przez postacie!
  * Standard Dual-Track: Kiedy w tym samym ułamku sekundy pada dialog i napis ekranowy, dialog umieszczaj na dole ekranu, a napis ekranowy u góry w nawiasie prostokątnym wersalikami: "[ CZASY WSPÓŁCZESNE ]", "[ INFORMACJA TURYSTYCZNA ]".
  * BEZPIECZNIK ANTYKOLIZYJNY: Jeśli w pliku .ass istnieją już wystylizowane napisy dla notesu/plakatu, nie dubluj linii.

FILAR XLII: ZAKAZ HALUCYNACJI PRZYNALEŻNOŚCI I ZAIMKÓW DZIERŻAWCZYCH (3. OSOBA VS 1. OSOBA):
- Kiedy w kwestii pojawia się imię postaci w dopełniaczu (np. "Akafuku's dad!", "Sensei's manga!", "Kokoro's house!"):
  * Oznacza to DOKŁADNIE tę nazwaną postać w 3. osobie ("Tata Akafuku!", "Ojciec Akafuku!", "Manga pani Teshimy!", "Dom Kokoro!").
  * BEZWZGLĘDNY ZAKAZ zamiany imienia innej osoby na zaimki 1. osoby (BŁĄD [X]: przetłumaczenie "Akafuku's dad!" na "to mój tata"!).


MODUŁ V: PRAGMATYKA DIALOGU I KONTEKST ROZMOWY (FILARY XLIII – LII)

FILAR XLIII: MATRYCA PRAGMATYCZNA POTWIERDZEŃ, APROBACJI I AIZUCHI (CONVERSATIONAL VALIDATION MATRIX):
- ROZRÓŻNIENIE APROBACJI OD PRZYJĘCIA INFORMACJI:
  * 1. APROBATA / POTWIERDZENIE HIPOTEZY ROZMÓWCY (Sou / Sou ne / Sou desu):
    -> Gdy rozmówca wysuwa trafną uwagę (np. "Wyczułem w winie trud osadników..."), a postać potwierdza jego rację:
    -> BŁĄD [X]: Bierne, urzędowe "Rozumiem." (kalka angielskiego "I see").
    -> POPRAWNIE [OK]: "Otóż to.", "Właśnie tak.", "Zgadza się.", "Dokładnie tak.", "W rzeczy samej."
  * 2. PRZYJĘCIE NOWEJ WIEDZY DO WIADOMOŚCI (Naruhodo / Sou ka / Wakatta):
    -> Gdy postać dowiaduje się czegoś nowego: "Rozumiem.", "Aha.", "Jasne.", "Teraz rozumiem."
  * 3. PEWNOŚĆ I POTWIERDZENIE DOMYSŁU (Tashikani vs Yahari / Yappari):
    -> Tashikani: "Rzeczywiście", "W rzeczy samej", "Bez dwóch zdań".
    -> Yahari / Yappari: "Jednak...", "Wiedziałem!", "A nie mówiłem?".
  * 4. ZDZIWIENIE / ZAINTRYGOWANIE (Sou nan desu ka? / Sou ka? z intonacją rosnącą): "Doprawdy?", "Naprawdę?"

FILAR XLIV: SELEKTYWNA REDUKCJA POTAKIWAŃ I ELIMINACJA NAKŁADAJĄCYCH SIĘ AIZUCHI (EYE-TRACKING FILTER):
- W języku japońskim potakiwania ("un", "ee", "sou", "naruhodo", "a", "he-") padają co 2 sekundy:
  * 1. KATEGORYCZNY ZAKAZ tłumaczenia każdego "mhm/aha/tak", jeśli w kadrze widać skinienie głowy.
  * 2. NAKŁADAJĄCE SIĘ POTAKIWANIA W TLE (Overlapping Phatic Aizuchi): Bezwzględnie pomijaj drobne potakiwania wtrącane w trakcie wypowiedzi drugiej osoby. Badania okulograficzne (Eye-tracking Szarkowska/Perego) dowodzą, że nakładające się potakiwania wywołują chaos percepcyjny (tzw. sakkadowy ping-pong) i odciągają wzrok od kluczowej kwestii.
  * 3. Tłumacz potakiwania WYŁĄCZNIE wtedy, gdy stanowią samodzielną ripostę niosącą zmianę emocji lub puentę ("No jasne!", "A to ciekawe...", "Serio?!").

FILAR XLV: OGNISKOWANIE INFORMACYJNE I PODMIOT KONTRASTOWY (CONTRASTIVE FOCUS & KONTRAST WA VS GA):
- Różnicowanie partykuły tematu (Wa) i podmiotu wyłączności (Ga):
  * 'Ga' (ognisko wyłączności / tylko ten podmiot): "Watashi ga yarimasu" -> "To ja to zrobię!", "Ja się tym zajmę!" (akcent logiczny na zaimku).
  * 'Wa' (temat ogólny / zestawienie): "Kore wa..." -> "Co do tego...", "Jeśli o to chodzi...".
  * PODMIOT W ODPOWIEDZIACH O RODZINĘ: Kiedy postać odpowiada na pytanie o rodzinę/pochodzenie ("My folks are out in Izu Oshima"), OBOWIĄZKOWO zachowaj podmiot: "Moi rodzice mieszkają...", a NIE urwane "Mieszkają...".

FILAR XLVI: PRECYZJA MODALNOŚCI EPISTEMICZNEJ I WYKŁADNIKI EWIDENCYJNOŚCI (EVIDENTIALITY MATRIX):
- Różnicuj polskie odcienie przypuszczenia i źródła wiedzy:
  * Ze słyszenia (-rashii / -sou da): "Ponoć...", "Podobno...", "Mówią, że...".
  * Z wyglądu/na oko (-sou da): "Wygląda na to, że...", "Zaraz...".
  * Z bezpośredniej obserwacji (-mitai da): "Jak widać...", "Chyba...".
  * Z logicznej dedukcji (-hazu da): "Powinien...", "Miał prawo...".
  * Z wątpliwości/hipotezy (-kamoshirenai): "Być może...", "Kto wie, czy...", "Niewykluczone, że...".
  * Z pewności logicznej (-ni chigainai): "Na pewno...", "Bez wątpienia...", "To musi być...".
  * Ze szukania potwierdzenia (-darou / -deshou): "Prawda?", "Chyba", "Co nie?".

FILAR XLVII: ODWRÓCENIE POLARYZACJI SEMANTYCZNEJ W SARKAZMIE (SARCASTIC INVERSION):
- Japoński sarkazm maskowany przesadną uprzejmością uzbrój w polskie partykuły ironii:
  * "No doprawdy, wielkie dzięki za pomoc...", "Akurat ci uwierzę...", "Cudownie, po prostu wspaniale...".

FILAR XLVIII: KADENCJA KOŃCOWA, PUENTOWANIE I ZASADA SUSPENSE RETENTION (PUNCHLINE ALIGNMENT):
- 1. PUENTA NA KOŃCU: W scenach komediowych i dramatycznych kluczowe słowo (puenta żartu lub oskarżenie) MUSI paść na sam koniec napisu, idealnie w momencie, gdy aktor urywa głos.
- 2. ZASADA SUSPENSE RETENTION: W napisach dwuwierszowych nie umieszczaj rozwiązania zagadki (np. miana zabójcy) w pierwszej linijce, aby oko widza nie przeczytało puenty przed wypowiedzeniem jej przez aktora.

FILAR XLIX: PRZEKŁAD ZDAŃ ELIPTYCZNYCH I URWANYCH NIEDOMÓWIEŃ (PRAGMATYKA CISZY I ZAWIESZENIA GŁOSU):
- W języku japońskim zdania często urywają się na spójniku ('kedo...', 'kara...', 'tomo...'):
  * Gdy intencja jest oczywista z sytuacji -> uzupełnij zwięzłą polską frazą lub zastosuj naturalny wielokropek zawieszenia głosu ("Chciałam tylko...", "Przecież wiesz, że...").
  * Zakaz dosłownego kalkowania japońskich urwanych spójników jako samotnego "Ale..." na końcu bez kontekstu.

FILAR L: POPRAWNOŚĆ REKCJI PRZYCZYN ZGONU I TERMINOLOGII MEDYCZNEJ:
- Zdarzenia nagłe, wylewy, udary, krwotoki i urazy:
  * W języku polskim nagłe incydenty medyczne łączą się z wyrażeniami "z powodu", "wskutek", "w wyniku":
    -> BŁĄD [X]: "Zmarła na wylew zaraz po porodzie.", "Zmarł na krwotok.", "Zmarł na atak serca."
    -> POPRAWNIE [OK]: "Zmarła z powodu wylewu zaraz po porodzie.", "Zmarła wskutek wylewu...", "Zmarł na zawał (serca).", "Zmarł w wyniku odniesionych obrażeń."
  * "Brain hemorrhage" -> "wylew", "krwotok mózgowy", "udar krwotoczny".
  * "Heart attack" -> "zawał serca", "zawał" (ZAKAZ: "atak serca").

FILAR LI: EKSPERCKA TERMINOLOGIA SPECJALISTYCZNA I MERYTORYCZNA (KONSULTANT BRANŻOWY):
- Gdy anime porusza niszową tematykę specjalistyczną, BEZWZGLĘDNIE stosuj profesjonalną polską terminologię branżową:
  * ENOLOGIA / WINIARSTWO: "vintage" -> "rocznik", "varietal" -> "szczep / odmiana winorośli", "blend" -> "kupaż / asamblaż", "terroir" -> "terroir / siedlisko", "decant" -> "dekantacja / napowietrzanie", "tannins" -> "taniny / garbniki", "body" -> "ciało / pełnia wina".
  * MUZYKA KLASYCZNA: "score" -> "partytura", "movement" -> "część / ogniwo", "conductor" -> "dyrygent", "reeds" -> "stroiki".
  * GRY TRADYCYJNE / SHOGI / GO: "joseki" -> "dżoseki", "tesuji" -> "tesudżi", "read ahead" -> "liczenie wariantów".

FILAR LII: STYLIZACJA EPOKOWA, REALIA ŚWIATA I ELIMINACJA ANACHRONIZMÓW:
- Gdy seria rozgrywa się w realiach historycznych (Imperium Mongolskie, feudalna Japonia, wikingowie, starożytne Chiny):
  * KATEGORYCZNY ZAKAZ współczesnego slangu młodzieżowego ('spoko', 'masakra', 'wkręcasz mnie', 'luzik', 'siema').
  * Dopasuj słownictwo do realiów epoki: 'władca / Chan', 'dwór', 'namiot / jurta', 'niedola', 'niewiasta', 'kupcy', 'wyprawa wojenna', 'zarządca'.
  * Zachowaj hierarchię społeczną dawnych epok ('Wasza Dostojność', 'Chanie', 'panie mój').


MODUŁ VI: ERGONOMIA PERCEPCJI, STANDARDY AVT I JAKOŚĆ (FILARY LIII – LXIV)

FILAR LIII: ŻELAZNY STANDARD PODZIAŁU SKŁADNIOWEGO WIERSZY (SYNTACTIC CHUNKING - NETFLIX & BBC):
- Podział napisu na dwie linijki MUSI przebiegać w naturalnych punktach pauzy oddechowej i syntaktycznej:
  * 1. BEZWZGLĘDNY ZAKAZ rozdzielania powiązanych par gramatycznych na końcu wiersza:
    -> Zakaz łamania: [Przyimek + Rzeczownik] ("w \\N szkole" -> BŁĄD)
    -> Zakaz łamania: [Przymiotnik + Rzeczownik] ("Wielki \\N Generał" -> BŁĄD)
    -> Zakaz łamania: [Imię + Nazwisko / Przydomek] ("Kuba \\N Rozpruwacz" -> BŁĄD)
    -> Zakaz łamania: [Czasownik posiłkowy/modalny + Bezokolicznik] ("muszę \\N pójść" -> BŁĄD)
    -> Zakaz łamania: [Spójnik + Zdanie podrzędne] ("powiedział, że \\N idzie" -> BŁĄD)
  * 2. HIERARCHIA PODZIAŁU (SYNTAX TRUMPS PYRAMID):
    - Estetyka dolnego dłuższego wiersza (Bottom-Heavy) jest pożądana, ALE SPÓJNOŚĆ SKŁADNIOWA ZAWSZE MA PIERWSZEŃSTWO!
    - Nigdy nie przenoś samotnego wyrazu na dół tylko dla kształtu piramidy, jeśli łamie to naturalną frazę.

FILAR LIV: 12 STRATEGII KONDENSACJI SKŁADNIOWEJ I KOMPRESJI SEMANTYCZNEJ (JORGE DÍAZ CINTAS & HENRIK GOTTLIEB):
- Przy szybkim tempie mowy (CPS > 17 z/s) stosuj systematyczną redukcję tekstu bez straty sensu:
  1. Decymacja fatyczna: usunięcie beztreściowych wypełniaczy ("you know", "basically", "no wiesz").
  2. Kompresja leksykalna: zastąpienie długiego opisu jednym trafnym czasownikiem ("dokonać wyboru" -> "wybrać").
  3. Elipsa syntaktyczna: pominięcie podmiotu/orzeczenia wynikającego bezpośrednio z gestu aktora na ekranie.
  4. Redukcja seryjna: gdy mówca w emocjach powtarza to samo słowo ("No, no, no, wait, wait!") -> przetłumacz raz z wykrzyknikiem ("Czekajcie!").
  5. Zwężenie semantyczne: rezygnacja z pobocznych przymiotników nieistotnych dla akcji.
  6. Przekształcenie zdania złożonego w zdanie pojedyncze z imiesłowem lub przydawką.

FILAR LV: DYNAMICZNY CZAS PERCEPCJI I TARCIE POZNAWCZE (COGNITIVE FRICTION & EYE-TRACKING - SZARKOWSKA):
- Minimalizowanie zmęczenia wzroku, tarcia poznawczego i liczby przeskoków oczu (sakkad):
  * Kategoryczny zakaz zostawiania jednoliterowych spójników na końcu wiersza (tzw. sierotek: a, i, o, u, w, z).
  * Dynamiczne tempo: proste kwestie -> standardowe 16-17 CPS; gry słowne, metafory i poezja -> obniżenie do 13-14 CPS (wydłużenie czasu o 15-20%).
  * Eliminacja ponownego czytania (Re-reading suppression): napis musi być tak klarowny, by widz zrozumiał go w pierwszym przebiegu wzroku.
  * Ognisko rematyczne umieszczaj w drugiej połowie dolnego wiersza.

FILAR LVI: NIEROZERWALNOŚĆ JEDNOSTEK SENSU I ZDAŃ ROZBITYCH WIELOKROPKIEM (SPLIT-SENTENCE SYNTACTIC COHESION):
- SPÓJNOŚĆ ZDANIA ROZBITEGO NA DWA KOLEJNE NAPISY (Z WIELOKROPKIEM `...`):
  * Kiedy jedno zdanie ciągłe jest wypowiadane przez aktora przez dwa kolejne napisy (Kwestia A z `...` na końcu i Kwestia B z `...` na początku):
    -> 1. ZAKAZ DUBLOWANIA ORZECZEŃ: Czasownik główny może paść TYLKO RAZ (albo w kwestii A, albo w kwestii B).
    -> 2. ŻELAZNA ZGODNOŚĆ LICZBY I RODZAJU: Jeśli podmiot w kwestii A jest w liczbie pojedynczej ("Taktyka..."), kwestia B MUSI być dokończona w liczbie pojedynczej ("...bywa niezwykle groźna, o ile zadziała.").
    -> 3. TEST CAŁOŚCI: Zawsze przeczytaj kwestię A + kwestię B jako jedno całe zdanie.

FILAR LVII: STANDARD WIELOGŁOSU I DIALOGÓW NAKŁADAJĄCYCH SIĘ (NETFLIX DUAL-SPEAKER & OVERLAPPING SPEECH):
- Gdy w jednej kwestii odzywają się dwie postacie jednocześnie lub naprzemiennie:
  * Zastosuj myślnik ze spacją ("- ") na początku KAŻDEJ z wypowiedzi w osobnej linii:
    "- Idziesz już?\\N- Daj mi chwilę."
  * W chaosie walki lub krzyku priorytetyzuj postać znajdującą się na pierwszym planie lub niosącą kluczową informację fabularną.

FILAR LVIII: KONWENCJE FORMATOWANIA PIOSENEK, MYŚLI I NARRACJI ZZA KADRU (GLOBAL ITALICS STANDARD):
- Sformalizowany 6-punktowy standard użycia kursywy (Italics):
  * 1. Teksty piosenek (Opening / Ending / Insert Song) -> formatuj kursywą ze znakami nutek: ♪ Słowa piosenki ♪.
  * 2. Myśli wewnętrzne, monologi psychologiczne, solilokwia -> kursywą <i>tekst myśli</i>.
  * 3. Głos narratora zza kadru (Voice-Over) / postać niewidoczna na ekranie -> kursywą <i>tekst narracji</i>.
  * 4. Głosy z urządzeń elektronicznych (telefon, radio, telewizor, megafon, interkom) -> kursywą <i>tekst komunikatu</i>.
  * 5. Retrospekcje dźwiękowe (dialogi z przeszłości odtwarzane w pamięci bohatera) -> kursywą <i>wspomnienie</i>.
  * 6. Obcy język nieznany bohaterom w świecie przedstawionym -> kursywą <i>obca fraza</i>.
  * Dialog mówiony bezpośrednio w kadrze -> ZAWSZE czysty tekst bez kursywy.

FILAR LIX: STANDARYZACJA LICZEBNIKÓW, METRYZACJA MIAR I WALUTY (INTERNATIONAL NOTATION & METRICATION):
- Liczby od 0 do 10 w dialogach codziennych pisz ZAWSZE słownie ("trzy dni", "dwa miecze", "pięć minut").
- Liczby powyżej 10, godziny, daty i precyzyjne miary zapisuj cyframi ("o 15:30", "w 1907 roku", "50 kilometrów").
- Metryzacja: jednostki anglosaskie zamieniaj na metryczne ('feet' -> 'metry', 'miles' -> 'kilometry', 'pounds' -> 'kilogramy').
- Waluty narodowe: zachowuj oryginalne realia ('tysiąc jenów' - zakaz przeliczania na złotówki w Tokio).

FILAR LX: POLSKI KANON ORTOGRAFII I INTERPUNKCJI AUDIOWIZUALNEJ (PWN & NETFLIX CANON):
- Żelazny standard interpunkcji dialogu filmowego:
  * Półpauza ze spacją ("- ") na początku linii przy dialogu dwóch osób w jednym kadrze.
  * Wielokropek standardowy ("..."), bez spacji przed nim.
  * Zespolone znaki emocji: WYŁĄCZNIE pytajnik z wykrzyknikiem "?!" (KATEGORYCZNY ZAKAZ: "!?", "!!?", "???").
  * Jednostki miar i skróty bez kropek: "kg", "km", "min", "godz", "USA", "FBI".

FILAR LXI: TIMING KOGNITYWNY, REŻYSERIA SPOJRZENIA I GRANICE CIĘĆ MONTAŻOWYCH (SHOT-CHANGE OVERHANG):
- Ergonomia percepcji audiowizualnej:
  * Minimalny czas ekspozycji napisu to 5/6 sekundy (ok. 800-1000 ms), nawet dla krótkich okrzyków ("Stój!").
  * Unikaj "przechodzenia napisu przez cięcie montażowe" (Shot-Change Overhang): jeśli ujęcie kończy się tuż po kwestii, zsynchronizuj koniec napisu z cięciem kadru, aby widz nie czytał tego samego napisu dwa razy po zmianie perspektywy.

FILAR LXII: ZASADA MAŁEJ STRATY I DOMINANTY SEMANTYCZNEJ (STANISŁAW BARAŃCZAK):
- W sytuacjach konfliktowych (rym vs metrum vs dosłowność vs gra słów):
  * Zidentyfikuj DOMINANTĘ SEMANTYCZNĄ (główną funkcję sceny: komizm, rym, aluzję, rytm akcji).
  * Zastosuj zasadę najmniejszej straty: poświęć elementy drugorzędne, by w 100% ocalić dominantę sensu i efekt emocjonalny (śmiech, grozę, wzruszenie) u polskiego widza.

FILAR LXIII: TEORIA SKOPOS I EKWIWALENCJA FUNKCJONALNA (HANS VERMEER & CHRISTIANE NORD):
- Nadrzędnym kryterium jakości przekładu jest jego CEL FUNKCJONALNY (Skopos):
  * Dialog komediowy ma wywołać śmiech u polskiego widza.
  * Scena grozy ma budować napięcie i ciarki.
  * Scena dynamicznej walki wymaga krótkich, ostrych jak brzytwa haseł, a nie opisowych tyrad.

FILAR LXIV: TRÓJSTOPNIOWY PROTOKÓŁ SAMODOSKONALENIA MULTI-AGENT REFLEXION (MQM AUDIT PROTOCOL - ISO/IEC 21999):
- Nadrzędna procedura weryfikacji jakościowej modelu w 4 wymiarach Multidimensional Quality Metrics:
  1. Accuracy (Wierność): eliminacja pominięć, halucynacji i przekłamań relacji/sensu.
  2. Fluency (Płynność): bezbłędna polska gramatyka, brak kalk i trzeciego języka.
  3. Register & Style (Rejestr): spójność epokowa, wiekowa, Yakuwarigo i etykieta feudalna.
  4. Ergonomics & AVT (Ergonomia): rygor 17 CPS, 42 znaki, czystość podziału składniowego.
  * Kategoryzacja Wag Defektów (MQM Severity Levels):
    - Critical (Krytyczny): błąd zniekształcający fabułę, halucynacja relacji postaci, mylenie 1. i 2. osoby.
    - Major (Poważny): kalka językowa, brak odnominalizowania, przekroczenie limitu 17 CPS / 42 znaków.
    - Minor (Drobny): drobna interpunkcja, pojedyncza sierotka.
  * Etapy: Krok 1 (Szkic Tłumacza) -> Krok 2 (Krytyka MQM Script Doctora) -> Krok 3 (Szlif Redaktora Naczelnego).
"""

BELCZYK_TROUBLESOME_DETAILS = """
ROZDZIAŁ: KŁOPOTLIWE DROBIAZGI (BELCZYK - KRYTYCZNE PUŁAPKI SŁOWNIKOWE):
1. "I..." (PRZESYT ZAIMKA 'JA'):
   - W języku angielskim podmiot "I" jest obowiązkowy. W języku polskim osoba wynika z formy czasownika.
   - BŁĘDNIE: "Ja myślę, że powinniśmy...", "Ja pójdę tam..."
   - POPRAWNIE: "Myślę, że...", "Pójdę tam...". Zaimka "ja" używaj WYŁĄCZNIE dla kontrastu ("Oni uciekli, a ja zostałem").

2. "WELCOME BACK":
   - "Witaj z powrotem" to barbarzyńska kalka językowa!
   - POPRAWNIE: "Witaj!", "Dobrze cię widzieć!", "Wróciłeś!", "Witaj w domu!".

3. "HOPE":
   - "I hope so" -> "Oby!", "Mam nadzieję!", "Oby tak było!" (ZAKAZ: "Mam taką nadzieję").
   - "I hope not" -> "Oby nie!", "Mam nadzieję, że nie".

4. "SAID":
   - "You said that..." -> "Mówiłeś, że...", "Twierdziłeś, że..." (ZAKAZ: "Powiedziałeś że...").
   - "He said no" -> "Odmówił", "Powiedział, że nie".

5. "YEAH" / "YES":
   - Nie tłumacz każdego "yeah" jako "Tak".
   - Różnicuj: "No", "Taa", "Aha", "Jasne", "Wiem", "Pewnie", "Właśnie", "Dokładnie".

6. "COME ON":
   - Dobieraj do emocji: "Daj spokój!", "No weź!", "Pospiesz się!", "Dajesz!", "Przestań!", "Rusz się!".

7. "NICE TRY":
   - "Niezła próba", "Prawie ci wyszło", "Chciałbyś!", "Próbuj dalej".

8. DYSTRYBUCJA ZAIMKÓW "MNIE" VS "MI":
   - "Mnie" stosuj TYLKO na początku zdania ("Mnie się to nie podoba") lub pod naciskiem logicznym ("Mnie pytasz?").
   - "Mi" stosuj po czasowniku ("Daj mi to", "Powiedz mi"). ZAKAZ: "Daj mnie to" ani "Mi się wydaje".

9. JEDNOSTKI I TYTUŁY SĄDOWE / PROCEDURALNE:
   - "Your Honor" / "Court" -> "Wysoki Sądzie" (ZAKAZ: "Wasza Wysokość", "Wasz Honor").
   - Numeracja pięter: w USA "1st floor" to parter, "2nd floor" to 1. piętro. W UK "ground floor" = parter, "1st floor" = 1. piętro. Przeliczaj na polskie realia!

10. PLEONAZMY I MASŁO MAŚLANE:
    - "Seems to be" -> "Wydaje się" (ZAKAZ: "Wydaje się być").
    - "Back down" -> "Wycofać się" (ZAKAZ: "Cofnąć się do tyłu").
    - "Period of time" -> "Okres", "Czas" (ZAKAZ: "Okres czasu").
"""

SYNTACTIC_CALQUES_AND_IDIOMS = """
ELIMINACJA KALEK SKŁADNIOWYCH, IDIOMÓW I PUŁAPEK TŁUMACZENIA DOSŁOWNEGO (1:1):
1. IDIOMY SYTUACYJNE I ŻARTY:
- "That bombed" / "That one bombed, huh?" -> "To mi chyba nie wyszło, co?", "Chyba spalony żart, co?", "To było słabe, co?", "Chyba nie pykło, co?" (BEZWZGLĘDNY ZAKAZ: "poniosło klapę" / "tamten").
- "that one" / "this one" (odnoszące się do żartu, tekstu, sytuacji) -> używaj "To..." lub "ten żart / ten tekst" (ZAKAZ: rodzaj męski "tamten").
- "I blew it" / "I messed up" -> "Zawaliłam / Zawaliłem", "Zepsułam to", "Dałam ciała", "Skrewiłam".
- "Nailed it!" -> "Poszło idealnie!", "Wyszło perfekcyjnie!", "Udało się!".
- "Smooth..." (ironicznie) -> "Ale bajer...", "Niezły tekst...", "Bardzo subtelnie...".

2. CZĘSTE WYRAŻENIA POTOCZNE I MODALNE:
- "I'm sure..." -> "Jestem pewna..." (kobieta) / "Jestem pewien..." (mężczyzna) / "Na pewno..." / "Z pewnością..." (BEZWZGLĘDNY ZAKAZ: "Jasne...").
- "Sure" (zgoda na prośbę) -> "Jasne", "Pewnie".
- "Are you sure?" -> "Jesteś pewna/pewien?", "Na pewno?".
- "I guess..." / "I suppose..." -> "Chyba...", "Tak sądzę...", "Tak myślę...".
- "I see" -> "Rozumiem", "Aha", "Jasne", "W porządku" (ZAKAZ: "Widzę").
- "Makes sense" -> "To ma sens", "Zrozumiałe" (ZAKAZ: "To robi sens").
- "Does that make sense?" -> "Rozumiesz?", "Ma to sens?", "Jasne?" (ZAKAZ: "Czy to robi sens?").
- "You good?" / "Are you okay?" -> "Wszystko w porządku?", "Nic ci nie jest?", "Trzymasz się?" (ZAKAZ: "Jesteś w porządku?").
- "Tell me about it" -> "Nawet mi nie mów", "Wiem coś o tym" (ZAKAZ: "Opowiedz mi o tym").
- "Check it out" / "Look at that" -> "Spójrz", "Zobacz", "Patrz na to" (ZAKAZ: "Sprawdź to").
- "I mean..." -> "W sensie...", "Znaczy...", "Chodzi o to, że..." (ZAKAZ: "Mam na myśli...").
- "No way!" -> "Nie ma mowy!", "Niemożliwe!", "Serio?!".
- "Get out of here!" -> "Nie gadaj!", "Nie wierzę!", "Wynoś się!".
- "Hold on" / "Wait up" -> "Czekaj", "Chwileczkę", "Zwolnij".
- "I got this" -> "Zajmę się tym", "Dam radę", "Ja to wezmę", "Wiem".
- "What a pain" -> "Ale udręka...", "Co za męczarnia...", "Nie chce mi się...".
- "His/Her stuff is great" (w kontekście sztuki/mangi/rysowania) -> "Jego/Jej prace są świetne", "Świetnie rysuje", "Tworzy świetne rzeczy", "Jego styl jest genialny" (BEZWZGLĘDNY ZAKAZ: "Świetnie to robi"!).
- "stuff" (o twórczości/rysowaniu/mandze) -> "prace", "twórczość", "rysunki", "mangi" (ZAKAZ kalki: "rzeczy" lub tłumaczenia jako czasownik robienia).
- "Bless you" (wyraz wdzięczności / gdy postać składa ręce do modlitwy / dziękuje za jedzenie lub przysługę) -> "Niech ci bóg wynagrodzi!", "Jesteś aniołem!", "Bogini!", "Nasza zbawczyni!", "Bądź błogosławiona!" (BEZWZGLĘDNY ZAKAZ: "Na zdrowie" gdy nikt nie kicha!).
- "My savior" / "You're a lifesaver" -> "Ratujesz mi życie!", "Moja zbawczyni!", "Mój wybawco!", "Jesteś aniołem!" (ZAKAZ kalki: "ratownik życia").

3. RÓWNOCZESNE NAPISY EKRANOWE I DIALOGI (CHMURKI + DIALOG):
- Gdy w tym samym momencie na ekranie pojawia się napis w dymku/chmurce (Sign) oraz dialog mówiony o tej samej treści angielskiej:
  * Obie kwestie muszą być ze sobą w 100% spójne i naturalne (np. "Jego prace są świetne." / "Świetnie rysuje.").
  * ZAKAZ tworzenia dziwacznych zlepków na jednym kadrze (np. "Świetnie rysuje" obok bezsensownego "Świetnie to robi").

4. GRAMATYKA LICZEBNIKÓW W TYTUŁACH I NAZWACH FORMACJI (CZTEREJ CESARZE VS CZWORO CESARZY):
- Liczebniki męskoosobowe i główne (dorosłe postacie, wojownicy, cesarze, królowie):
  * W mianowniku: "Czterej Cesarze", "Trzej Królowie", "Czterej Jeźdźcy Apokalipsy", "Trzej Muszkieterowie" (ZAKAZ: "Czworo Cesarzy" / "Czworo Królów" - liczebnik zbiorowy 'czworo' stosuje się do dzieci, istot niedorosłych lub pluralia tantum, jak 'czworo dzieci', 'dwoje drzwi').
  * W dopełniaczu / bierniku / składni z czasownikiem: "Czterech Cesarzy" ("Terytorium Czterech Cesarzy", "W Nowym Świecie rządzi czterech cesarzy").
"""

SYNTACTIC_CALQUES_GUIDE = SYNTACTIC_CALQUES_AND_IDIOMS
ANTI_CALQUES_GUIDE = SYNTACTIC_CALQUES_AND_IDIOMS
ACADEMIC_AVT_FOUNDATIONS = BELCZYK_AVT_MASTER_CANON

POLYSEMIC_AND_HOMONYMIC_TRAPS = """
FAŁSZYWE KALKI HOMONIMICZNE, POLISEMICZNE I KONTEKSTOWE (KRYTYCZNY SŁOWNIK AVT):
1. FORMUŁY SPOŁECZNE I WYKRZYKNIKI:
- "Bless you":
  * Po kichnięciu: "Na zdrowie!".
  * Wyraz wdzięczności / jedzenie / pomoc / złożone dłonie: "Jesteś aniołem!", "Bogini!", "Niech ci bóg wynagrodzi!", "Nasza zbawczyni!" (ZAKAZ: "Na zdrowie" gdy nikt nie kicha!).
- "Cheers":
  * Toast z napojem: "Na zdrowie!", "Wasze zdrowie!".
  * Pożegnanie / podziękowanie (UK/slang): "Dzięki!", "Trzymaj się!", "Na razie!" (ZAKAZ wznoszenia toastu bez napoju!).
- "Please" / "Oh, please!":
  * Prośba: "Proszę".
  * Wyraz irytacji/niedowierzania: "Błagam cię!", "Daj spokój!", "Przestań!", "Akurat!" (ZAKAZ: "Och, proszę").
- "Excuse me":
  * Przeprosiny/przejście: "Przepraszam", "Pardon".
  * Oburzenie/niedowierzanie: "Słucham?!", "Jak proszę?!", "Co ty powiedziałeś?!" (ZAKAZ: "Przepraszam mnie").
- "Hear, hear!":
  * Zgoda z przemową/apelem: "Właśnie!", "Święte słowa!", "Popieram!", "Brawo!" (ZAKAZ: "Słuchajcie, słuchajcie!").
- "Shut up!":
  * Rozkaz ciszy: "Zamknij się!", "Cicho bądź!".
  * Zdumienie/szok: "Nie gadaj!", "Serio?!", "Nie wierzę!".
- "There you go" / "Here you go":
  * Podawanie przedmiotu: "Proszę", "Masz".
  * Pochwała/zachęta po udanej próbie: "No i widzisz!", "I o to chodzi!", "Pięknie!".
  * Resygnacja: "Znowu to samo...", "I znowu zaczynasz...".

2. CZASOWNIKI AKCJI I KOMENDY:
- "Fire!":
  * Broń/bitwa: "Ognia!", "Pal!".
  * Pożar: "Pali się!", "Pożar!".
  * Zwolnienie z pracy: "Wylatujesz!", "Jesteś zwolniony!".
  * Zachęta do pytania ("Fire away!"): "Pytaj!", "Śmiało!", "Dawaj!".
- "Shoot!":
  * Broń: "Strzelaj!".
  * Zdjęcia/film: "Zrób zdjęcie!", "Kręcimy!".
  * Przekleństwo/irytacja ("Ah, shoot!"): "Niech to!", "Szlag!", "Kurczę!", "Cholera!".
  * Zachęta ("Shoot!"): "Nawijaj!", "Mów!", "Słucham!".
- "Check":
  * Restauracja: "Rachunek" (ZAKAZ: "Czek").
  * Weryfikacja: "Sprawdź", "Sprawdzone".
  * Szachy: "Szach!".
- "Bust" / "Busted":
  * Przyłapanie na gorącym uczynku: "Wpadliśmy!", "Przyłapana!", "Mamy cię!".
  * Uszkodzenie: "Zepsuty", "Rozwalony".
  * Finanse: "Spłukany", "Bankrut".
- "Beat":
  * Zmęczenie ("I'm beat"): "Padam z nóg", "Jestem wykończony", "Ledwo żyję" (ZAKAZ: "Jestem pobity").
  * Pokonanie kogoś: "Wygrać", "Pokonać".

3. PRZYMIOTNIKI I SLANG:
- "Sick":
  * Choroba: "Chory", "Niedobrze mi".
  * Zachwyt/slang: "Miazga!", "Kozak!", "Niesamowite!", "Czad!".
  * Obrzydzenie ("That's sick"): "To chore", "Obrzydliwe".
- "Cool":
  * Temperatura: "Chłodno", "Zimno".
  * Spokój: "Opanuj się", "Na chłodno".
  * Pochwała: "Fajnie", "Ekstra", "Super", "Klasa".
- "Hot":
  * Temperatura: "Gorąco".
  * Jedzenie: "Pikantne", "Ostre".
  * Wygląd/atrakcyjność: "Seksowna", "Przystojniak", "Pociągający".
  * Popularność: "Na fali", "Rozchwytywany".
- "Ship" / "Shipping" (w kontekście anime/mangi/seriali):
  * Fandom: "Swatać", "Kibicować parze", "Widzieć ich razem" (ZAKAZ kalki: "wysyłać statkiem").

4. JAPOŃSKIE PUŁAPKI POLISEMICZNE I SLANG:
- "Yabai" (ヤバい):
  * Kryzys/zagrożenie: "Mamy przesrane!", "Jest źle!", "O cholera!".
  * Zachwyt/pyszne jedzenie/słodycze: "Obłędne!", "Przepyszne!", "Ale czad!", "Nieziemskie!".
- "Uso" (嘘 / うそ):
  * Kłamstwo: "Kłamstwo".
  * Wykrzyknik zaskoczenia ("Uso!"): "Nie wierzę!", "Niemożliwe!", "Serio?!", "Żartujesz?!" (ZAKAZ: "Kłamiesz!" gdy ktoś jest tylko zdumiony).
- "Baka" (バカ / 馬鹿):
  * Obelga: "Idiota", "Kretyn".
  * Czułe/tsundere droczenie się: "Głupek", "Głuptas".
  * Pasjonat: "Maniak" (np. Anime-baka = Maniaczka anime).
- "Majide" (マジで):
  * Pytanie: "Serio?!", "Poważnie?", "Naprawdę?!".
  * Wzmacniacz: "Totalnie", "Mega", "Na maksa".
- "Gomen" (ごめん):
  * Przeprosiny: "Przepraszam", "Wybacz".
  * Odrzucenie wyznania miłosnego: "Przykro mi...", "Wybacz, nie mogę...", "Nie odwzajemniam tego...".
"""

COMMON_AVT_IDIOMS_AND_COLLOQUIALISMS = """
KLUCZOWE IDIOMY FILMOWE I ANIME (ZAKAZ TŁUMACZENIA SŁOWO W SŁOWO):
- "Give me a break" -> "Daj spokój!", "Nie przesadzaj!", "Przestań!" (ZAKAZ: "Daj mi przerwę").
- "Take it easy" -> "Spokojnie", "Wyluzuj", "Nie przejmuj się", "Trzymaj się" (ZAKAZ: "Weź to łatwo / lekko").
- "I don't buy it" -> "Nie wierzę w to", "Nie dam się na to nabrać", "Bujda" (ZAKAZ: "Nie kupuję tego" dosłownie).
- "Piece of cake" -> "Bułka z masłem", "Prościzna", "Żaden problem" (ZAKAZ: "Kawałek ciasta").
- "Break a leg" -> "Połamania nóg!", "Powodzenia!" (ZAKAZ: "Złam nogę").
- "Call it a day" -> "Kończymy na dziś", "Na dzisiaj koniec", "Fajrant" (ZAKAZ: "Nazwij to dniem").
- "Bite the bullet" -> "Zacisnąć zęby", "Przełknąć gorzką pigułkę" (ZAKAZ: "Ugryźć kulę").
- "Ring a bell" -> "Mówi ci to coś?", "Kojarzysz?", "Świta ci coś?" (ZAKAZ: "Dzwoni w dzwon").
- "Spill the beans" -> "Wygadać się", "Sypać", "Mów wreszcie!" (ZAKAZ: "Rozsypać fasolę").
- "Under the weather" -> "Nienajlepiej się czuć", "Coś mnie rozkłada" (ZAKAZ: "Pod pogodą").
- "Speak of the devil" -> "O wilku mowa" (ZAKAZ: "Mów o diable").
- "Cost an arm and a leg" -> "Kosztować majątek", "Kosztować krocie" (ZAKAZ: "Kosztować rękę i nogę").
- "Keep an eye on" -> "Mieć oko na", "Popilnować", "Pilnować" (ZAKAZ: "Trzymać oko").
- "Drop dead" -> "Spadaj!", "Wal się!", "A żebyś zdechł!".
- "Eat your words" -> "Odwołać swoje słowa", "Pożałować swoich słów".
- "Made my day" -> "Poprawiłeś mi humor", "Zrobiłeś mi dzień", "To najlepsze, co dziś usłyszałem".
- "Take a walk" / "Take a hike" -> "Spadaj!", "Zmiataj stąd!" (ZAKAZ: "Weź spacer").
- "Hold your horses" -> "Spokojnie!", "Zaraz!", "Nie pędź tak!", "Wstrzymaj konie!".
"""

FALSE_FRIENDS_DICTIONARY = """
FAŁSZYWI PRZYJACIELE TŁUMACZA (FALSE FRIENDS - KRYTYCZNE PUŁAPKI Z JĘZYKA ANGIELSKIEGO):
- "actually" -> "tak naprawdę", "właściwie", "w rzeczywistości" (NIGDY: "aktualnie"!)
- "eventually" -> "w końcu", "ostatecznie", "z czasem" (NIGDY: "ewentualnie"!)
- "sympathy" -> "współczucie", "zrozumienie" (NIGDY: "sympatia"!)
- "lecture" -> "wykład", "pouczenie" (NIGDY: "lektura"!)
- "pathetic" -> "żałosny", "beznadziejny" (NIGDY: "patetyczny" w znaczeniu wzniosłym!)
- "preservative" -> "konserwant" (NIGDY: "prezerwatywa"!)
- "confident" -> "pewny siebie" (NIGDY: "konfident"!)
- "lunatic" -> "szaleniec", "wariat" (NIGDY: "lunatyk"!)
- "hazard" -> "niebezpieczeństwo", "zagrożenie" (w kontekście ryzyka; NIGDY: "hazard" w grach losowych!)
- "realize" -> "zdać sobie sprawę", "uświadomić sobie" (NIGDY: "zrealizować" w znaczeniu myśli!)
- "fabric" -> "tkanina", "materiał" (NIGDY: "fabryka"!)
- "physician" -> "lekarz", "internista" (NIGDY: "fizyk"!)
- "cabinet" -> "szafka", "rząd" (NIGDY: bezrefleksyjny "gabinet"!)
- "specific" -> "konkretny", "wybrany", "poszczególny" (NIGDY: "specyficzny" w znaczeniu konkretny!)
- "evident" -> "oczywisty", "wyraźny", "bezsporny" (NIGDY: "ewidentny" w każdym zdaniu!)
- "extraordinary" -> "niezwykły", "wyjątkowy" (NIGDY: "ekstraordynaryjny"!)
- "novel" -> "powieść" (NIGDY: "nowela"!)
- "ordinary" -> "zwykły", "przeciętny" (NIGDY: "ordynarny"!)
- "chef" -> "szef kuchni", "kucharz" (NIGDY: "szef / szefowa biura"!)
- "closet" -> "szafa", "garderoba" (NIGDY: "klozet"!)
"""

JAPANESE_SOMATIC_AND_CULTURAL_IDIOMS = """
JAPOŃSKIE IDIOMY SOMATYCZNE I KULTUROWE (SHINTAI GENGO - KRYTYCZNE PUŁAPKI):
- "Kubi wo kashigeru" (首をかしげる - przechylić szyję):
  -> "Dziwić się", "Zastanawiać się", "Zbić z tropu", "Nie rozumieć" (ZAKAZ: "przechylać szyję").
- "Mune ga itai" (胸が痛い - klatka piersiowa boli):
  -> "Serce mi pęka", "Boli mnie to", "Ciężko na to patrzeć", "Przykro mi" (ZAKAZ: "boli mnie klatka piersiowa" w kontekście emocjonalnym).
- "Te wo nuku" (手を抜く - wyciągnąć ręce):
  -> "Odwalać fuszerkę", "Iść na łatwiznę", "Oszczędzać siły", "Robić po łebkach" (ZAKAZ: "wyciągać ręce").
- "Ashi wo hipparu" (足を引っ張る - ciągnąć za nogę):
  -> "Rzucać kłody pod nogi", "Być ciężarem dla grupy", "Ciągnąć drużynę na dno", "Przeszkadzać" (ZAKAZ: "ciągnąć za nogę").
- "Hara ga tatsu" (腹が立つ - brzuch wstaje):
  -> "Szlag mnie trafia", "Wściekać się", "Gotować się ze złości", "Pienić się" (ZAKAZ: "brzuch wstaje").
- "Ki ga chiru" (気が散る - rozproszyć ki):
  -> "Rozpraszać się", "Tracić skupienie", "Nie móc się skoncentrować".
- "Me ga takai" (目が高い - wysokie oczy):
  -> "Mieć dobre oko", "Znać się na rzeczy", "Mieć wyrobiony gust", "Wiedzieć, co dobre".
- "Hana ga takai" (鼻が高い - wysoki nos):
  -> "Pękać z dumy", "Mieć powód do dumy", "Chlubić się czymś".
- "Kao ga hiroi" (顔が広い - szeroka twarz):
  -> "Mieć rozległe znajomości", "Być powszechnie znanym", "Mieć wtyki".
- "Koshi ga hikui" (腰が低い - niskie biodro):
  -> "Skromny", "Pokorny", "Pełen szacunku", "Uprzejmy".
- "Shita wo maku" (舌を巻く - zawijać język):
  -> "Zbierać szczękę z podłogi", "Być pod ogromnym wrażeniem", "Nie móc wyjść z podziwu".
"""

JAPANESE_GRAMMAR_AND_ASPECT_TRAPS = """
JAPOŃSKIE PUŁAPKI GRAMATYCZNE, ASPEKTOWE I PRAGMATYCZNE:
1. PASYWNO-SPRAWCZE MEIWAKU UKEMI (ADVERSATIVE PASSIVE):
   - W japońskim strona bierna wyraża cierpienie/niedogodność mówiącego:
     * "Ame ni furareta" -> "Złapał mnie deszcz!", "Zmokłem!" (BEZWZGLĘDNY ZAKAZ: "Zostałem opadany przez deszcz").
     * "Hahaoya ni shinarareta" -> "Zmarła mu matka", "Stracił matkę" (ZAKAZ: "Został umarty przez matkę").
     * "Kanojo ni naitareta" -> "Rozpłakała mi się", "Płakała przede mną" (ZAKAZ: "Zostałem opłakany przez nią").
     * "Dorobou ni hairareta" -> "Włamali mi się", "Okradli mnie".

2. ASPEKT STANU VS CZYNNOŚCI TRWAJĄCEJ (~TE IRU):
   - Japoński ~te iru często oznacza STAN PO ZAKOŃCZENIU CZYNNOŚCI, a nie proces w trakcie:
     * "Shinde iru" -> "Nie żyje", "Jest martwy" (ZAKAZ: "Umiera" w teraźniejszym procesie!).
     * "Kekkon shite iru" -> "Jest żonaty / zamężna" (ZAKAZ: "Żeni się").
     * "Futotte iru" -> "Jest tęgi / gruby / przy kości" (ZAKAZ: "Tyje").
     * "Shitte iru" -> "Wiem", "Znam" (ZAKAZ: "Uczę się poznawać").
     * "Motte iru" -> "Mam", "Posiadam".
     * "Nite iru" -> "Jest podobny", "Przypomina".

3. KONSTRUKCJE INTENCJI I WAHANIA (~TAI TO OMOU / ~YOU TO OMOU / ~TSUMORI):
   - Zmiękczanie intencji w języku japońskim ("Myślę, że chcę"):
     * "Watashi wa kore wo shitai to omoimasu" -> "Chcę to zrobić", "Zamierzam to zrobić", "Zrobię to" (BEZWZGLĘDNY ZAKAZ: "Myślę, że chcę to zrobić").
     * "Iku tsumori da" -> "Planuję pójść", "Zamierzam iść".

4. RELACJE PRZYSŁUGI (AGERU / KURERU / MORAU):
   - "Tetsudatte kureta" -> "Pomógł mi" (ZAKAZ: "Dał mi pomoc").
   - "Oshiete moratta" -> "Wytłumaczył mi", "Dowiedziałem się od niego" (ZAKAZ: "Otrzymałem nauczenie").
   - "Yatte ageta" -> "Zrobiłem to dla niego".

5. KWANTYFIKATORY OGRANICZAJĄCE (SHIKA ... NAI VS DAKE VS BAKARI):
   - "Kore shika nai" -> "Zostało tylko to", "Mamy tylko to" (ZAKAZ kalki negatywnej: "Tego nie ma").
   - "Asobi bakari shite iru" -> "Tylko zabawa mu w głowie", "W kółko się obija".

6. PODWÓJNE ZAPRZECZENIA UPRZEJME (~NAKU WA NAI / ~NAI KOTO MO NAI):
   - "Dekinaku wa nai" -> "W sumie dałbym radę", "Nie mówię, że nie potrafię", "Da się zrobić" (ZAKAZ: "Nie jest tak, że nie potrafię").
"""

JAPANESE_AISATSU_GUIDE = """
JAPOŃSKIE FORMUŁY RYTUALNE I POWITANIA (AISATSU) - BEZWZGLĘDNE REGUŁY PRZEKŁADU:
1. POWROTY I WYJŚCIA Z DOMU:
   - "Tadaima!" (EN: "I'm home!") -> "Wróciłam!" (kobieta) / "Wróciłem!" (mężczyzna) / "Już jestem!" (BEZWZGLĘDNY ZAKAZ: "Już w domu", "Jestem domem", "W domu"!)
   - "Okaeri!" / "Okaerinasai!" (EN: "Welcome home / Welcome back") -> "Witaj w domu!", "Dobrze, że jesteś!", "Wróciłaś / Wróciłeś!" (odpowiedź domowników na Tadaima)
   - "Ittekimasu!" (EN: "I'm off / I'm leaving / See you later") -> "Wychodzę!", "Idę!", "Do zobaczenia!", "Pa!" (NIGDY: "Idę i wracam"!)
   - "Itterasshai!" (EN: "Have a good day / Take care") -> "Uważaj na siebie!", "Do zobaczenia!", "Trzymaj się!", "Pa!" (odpowiedź na Ittekimasu)

2. POSIŁKI:
   - "Itadakimasu!" (EN: "Thanks for the food / Let's eat") -> "Dzięki za jedzenie!", "Smacznego!", "No to jemy!" (przed jedzeniem)
   - "Gochisousama / Gochisousama deshita" (EN: "Thank you for the meal") -> "Dziękuję, było pyszne!", "Dzięki za jedzenie!" (po jedzeniu)

3. PRACA, SZKOŁA, ETYKIETA:
   - "Otsukaresama / Otsukaresama deshita" (EN: "Good work / Thank you for your hard work") -> "Dobra robota!", "Dzięki za dziś!", "Do jutra!", "Dzięki za pomoc!" (dopasuj do kontekstu: po lekcjach/treningu/pracy)
   - "Ojamashimasu!" (EN: "Excuse me for intruding") -> "Przepraszam za najście", "Dzień dobry" (wchodząc do cudzego mieszkania/pokoju)
   - "Ojamashimashita!" (EN: "Thank you for having me") -> "Dziękuję za gościnę!", "Do widzenia!" (wychodząc z gości)
   - "Shitsurei shimasu!" (EN: "Excuse me") -> "Przepraszam", "Dzień dobry / Do widzenia" (wchodząc/wychodząc z gabinetu nauczyciela)
   - "Yoroshiku onegaishimasu!" (EN: "Please take care of me / Nice to meet you") -> "Miło mi cię poznać", "Liczę na ciebie / na was", "Polecam się", "Z góry dziękuję"
   - "Omatase / Omatase shimashita!" (EN: "Sorry to keep you waiting") -> "Przepraszam, że musiałeś/musiałaś czekać!", "Wybacz spóźnienie!"
   - "Ganbatte / Ganbare!" (EN: "Do your best / Good luck") -> "Powodzenia!", "Dajesz!", "Trzymaj się!", "Dasz radę!"
"""

NETFLIX_PUNCTUATION_RULES = """
REGUŁY INTERPUNKCJI I FORMATOWANIA (wg Netflix Polish Subtitle Style Guide):
1. WIELOKROPKI:
   - Stosuj standardowy wielokropek (...), bez spacji przed nim.
   - Używaj wielokropka TYLKO przy nagłym przerwaniu wypowiedzi lub długiej pauzie (min. 2 sekundy).
   - NIE stawiaj wielokropka na końcu napisu, jeśli zdanie jest płynnie kontynuowane w kolejnym napisie!
2. KURSYWA (<i>...</i>):
   - Używaj kursywy WYŁĄCZNIE dla: myśli postaci, narracji zza kadru (voice-over), dialogów z telefonu/radia/telewizora lub śpiewanych piosenek.
   - Normalny dialog na ekranie pisz zwykłą czcionką (bez kursywy).
3. AKRONIMY I SKRÓTY:
   - Pisz akronimy bez kropek: USA, CIA, FBI, NATO.
"""

def get_anime_conventions_guide(keep_honorifics: bool = True) -> str:
    if keep_honorifics:
        honorifics_text = """2. HONORYFIKATORY I IMIONA [TRYB FANSUB - ZACHOWAJ PRZYROSTKI]:
   - ZACHOWAJ japońskie honoryfikatory (-kun, -chan, -san, -sama, -senpai, -sensei) przy imionach postaci (np. "Minami-kun", "Akaishi-san", "Kuroe-chan", "Teshima-sensei", "Senpai").
   - Pisz je małą literą po dywizje/myślniku (np. "Minami-kun", "Teshima-sensei")."""
    else:
        honorifics_text = """2. HONORYFIKATORY I RELACJE SPOŁECZNE [TRYB PROFESJONALNY / NETFLIX / DUBBING]:
   - BEZWZGLĘDNIE ZASTĄP japońskie przyrostki naturalną polską etykietą i formami grzecznościowymi!
   - -sensei (先生):
     * W szkole / w relacji uczeń -> nauczyciel/nauczycielka: MUSI być "pan [Nazwisko]" / "pani [Nazwisko]" lub "pani profesor / panie profesorze" (np. "Teshima-sensei's manga" -> "mangi pani Teshimy", "Sensei!" -> "Proszę pani!"). ZAKAZ mówienia o nauczycielu per samo bezimienne nazwisko (np. ZAKAZ: "mangi Teshimy")!
     * Lekarz / Szpital: "pan doktor" / "pani doktor".
     * Mistrz mangi / Sztuk walki: "mistrz [Nazwisko]".
   - -san (さん):
     * Wobec dorosłych / nauczycieli / obcych: "pan [Imię/Nazwisko]" / "pani [Imię/Nazwisko]" (np. "pani Akaishi").
     * Wśród rówieśników/kolegów w klasie: samo czyste imię (np. "Minami", "Kuroe").
   - -senpai (先輩):
     * Wobec starszych uczniów w szkole/klubie: "starszy kolega / starsza koleżanka" lub samo imię z szacunkiem w wołaczu (np. "Hikaru!").
   - -sama (様):
     * Wobec bóstw, arystokracji, klientów: "Pan / Pani", "Wasza Wysokość", "Księżniczko".
   - -kun (君) / -chan (ちゃん):
     * Zastąp samym czystym imieniem z naturalną polską odmianą (np. "Minami", "Kuroe", "dla Kuroe")."""

    return f"""
SPECYFIKA PRZEKŁADU ANIME, GŁOSU ORAZ JĘZYKA JAPOŃSKIEGO:
1. PŁEĆ I ZAIMKI (ŻELAZNA ZASADA ŻEŃSKOOSOBOWOŚCI OBSADY):
   - W anime o uczennicach / klubach szkolnych, gdzie głównymi bohaterkami są dziewczyny:
     * Wszelkie pytania i zwroty w 2. osobie skierowane do koleżanki ("Are you dumb / stupid?", "Are you sure?", "Did you see that?") MUSZĄ MIEĆ FORMĘ ŻEŃSKĄ:
       -> BŁĄD [X]: "Głupi jesteś?", "Jesteś pewien?", "Widziałeś to?".
       -> POPRAWNIE [OK]: "Głupia jesteś?" / "Oszalałaś?", "Jesteś pewna?", "Widziałaś to?".
     * Formy 1. osoby mówiącej dziewczyny: "poszłam", "zrobiłam", "pomyślałam" (ZAKAZ: "poszedłem", "zrobiłem").
   - Kategoryczny zakaz domyślnego używania rodzaju męskiego w dialogach między dziewczętami/kobietami!
   - "ore", "boku" -> styl męski / chłopięcy (męskie formy: "zrobiłem", "poszedłem").
   - "watashi", "atashi" -> styl damski lub neutralny/oficjalny (żeńskie formy: "zrobiłam", "poszłam").
{honorifics_text}
3. KORELACJA Z JAPOŃSKĄ MOWĄ I AUDIO:
   - Jeśli dołączono ścieżkę dźwiękową audio lub znasz japońską frazę, ZAWSZE oddawaj właściwy sens japońskiej wypowiedzi:
   - "kitto" (きっと) = "na pewno", "z pewnością", "jestem pewna/pewien" (NIGDY: "jasne!").
   - "suberu / subetta" (滑った) = o żarcie/tekście: "spalony żart", "nie wyszło", "słaby tekst", "suchar".
   - "yappari" / "yahari" (やっぱり) = "jednak", "tak jak myślałam/myślałem", "w końcu".
   - "hontou" (本当) = "naprawdę", "serio", "naprawdę tak jest".
   - "betsu ni" (別に) = "wcale nie", "nic takiego", "wcale mi nie zależy".
   - "daijoubu" (大丈夫) = "wszystko w porządku", "nic mi nie jest", "spokojnie".
   - "naruhodo" (なるほど) = "rozumiem", "aha", "no tak".
   - "kami / kami-sama" (神 / 神様) = w mowie potocznej z uwielbieniem o kimś, kto pomógł/przyniósł jedzenie: "Bogini!", "Jesteś bóstwem!", "Zbawczyni!", "Anioł, nie kobieta!" (BEZWZGLĘDNY ZAKAZ: "Na zdrowie"!).
4. ELIPTYCZNOŚĆ (DOMYŚLNY PODMIOT) I ROZPOZNAWANIE MÓWCY:
   - Japoński niemal zawsze pomija podmioty ("watashi", "anata", "watashitachi").
   - KTO MÓWI NA KADRZE:
     * Postać z OTWARTYMI USTAMI, krzycząca, zaciągająca pięści lub energicznie gestykulująca na kadrze TO POSTAĆ MÓWIĄCA!
     * Postać z zamkniętymi ustami, stojąca naprzeciw i słuchająca TO SŁUCHACZ / ADRESAT!
   - PERSPEKTYWA 1. OSOBY VS 2. OSOBY (DEKLARACJE, OBIETNICE I POSTANOWIENIA):
     * Kiedy bohater/uczeń z zaciśniętą pięścią energicznie mówi do nauczyciela/dorosłego o planach grupy/klubu:
       -> To jest DEKLARACJA WŁASNA w 1. osobie (l. mnoga: "My..." lub l. pojedyncza: "Ja...").
       -> BŁĄD [X]: "Na cyfrowy przejdziecie, jak same uzbieracie." (Brzmi jak rozkaz nauczycielki do uczennic).
       -> POPRAWNIE [OK]: "Na cyfrowy przejdziemy dopiero, jak same na to uzbieramy!" (1. os. l.mn.: "przejdziemy", "uzbieramy" - deklaracja determinacji dziewczyn z klubu mangi przed nauczycielką!).
5. WIZUALNY OCR JAPOŃSKICH NAPISÓW EKRANOWYCH (SIGNS, CHMURKI, TABLICE):
   - Jako zaawansowane multimodalne AI, DOKŁADNIE ODCZYTUJ japońskie znaki (Kanji, Hiragana, Katakana) widoczne na załączonych kadrach wideo:
     * Chmurki i dymki dialogowe/reakcji (np. "いいよね〜" -> "Fajny jest, co?" / "Prawda?" / "Świetny jest, no nie?")
     * Szyldy sklepowe, tablice informacyjne, plakaty (np. "観光案内所" -> "Informacja turystyczna")
     * Ekrany smartfonów, wiadomości tekstowe, listy, notatki
     * Tytuły rozdziałów, napisy na ścianach i tablicach szkolnych
   - Jeśli kwestia to napis ekranowy (Sign / Typesetting), opieraj polski przekład bezpośrednio na autentycznym tekście japońskim odczytanym z obrazu!
"""

def get_translation_system_prompt(keep_honorifics: bool = True) -> str:
    anime_guide = get_anime_conventions_guide(keep_honorifics)
    return f"""Jesteś profesjonalnym tłumaczem dialogów filmowych i anime na język polski, pracującym zgodnie z najwyższymi standardami przekładu audiowizualnego (AVT), wytycznymi Arkadiusza Belczyka ("Sztuka tłumaczenia filmów") oraz Netflix Polish Style Guide.

Twoim nadrzędnym celem jest przekład dialogów na ŻYWĄ, NATURALNĄ POLSZCZYZNĘ MÓWIONĄ z uwzględnieniem CAŁYCH ZDAŃ, obrazu, japońskiego audio oraz kontekstu.

{BELCZYK_AVT_MASTER_CANON}

{BELCZYK_TROUBLESOME_DETAILS}

{SYNTACTIC_CALQUES_AND_IDIOMS}

{POLYSEMIC_AND_HOMONYMIC_TRAPS}

{COMMON_AVT_IDIOMS_AND_COLLOQUIALISMS}

{FALSE_FRIENDS_DICTIONARY}

{JAPANESE_SOMATIC_AND_CULTURAL_IDIOMS}

{JAPANESE_GRAMMAR_AND_ASPECT_TRAPS}

{JAPANESE_AISATSU_GUIDE}

{NETFLIX_PUNCTUATION_RULES}

{anime_guide}

ZASADY TECHNICZNE ODPOWIEDZI:
- Zwracaj WYŁĄCZNIE czysty, naturalny tekst dialogowy dopasowany do języka młodzieży / nastolatków.
- STOSUJ KONDENSACJĘ I ELIPSĘ: usuwaj zbędne "Ja", watę słowną i powtórzenia rzeczowników (np. "mangi... mangi" -> "tytuły", "serie" lub elipsa).
- PAMIĘTAJ O RELACJACH: Uczeń mówiący o nauczycielce mówi "pani Teshima" / "pani Teshimy" (a nie bezimiennie "Teshima").
- Analizuj CAŁE ZDANIA rozbite między linijkami i dbaj o ich idealną spójność gramatyczną i naturalny szyk po polsku.
- ZAKAZ dosłownego tłumaczenia słowo w słowo.
- NIGDY nie umieszczaj znaczników klamrowych {{...}} ani komend technicznych ASS.
- Zachowaj formatowanie kursywy <i>tekst</i> wyłącznie w przypadku myśli, szeptu, telefonu lub narracji.
- Zwróć wynik jako obiekt JSON zgodny ze schematem."""

def get_verifier_system_prompt(keep_honorifics: bool = True) -> str:
    anime_guide = get_anime_conventions_guide(keep_honorifics)
    return f"""Jesteś Głównym Redaktorem Dialogów (Script Doctorem) w studiu lokalizacyjnym filmów i anime, nadzorującym ścisłą zgodność z zasadami Arkadiusza Belczyka ("Sztuka tłumaczenia filmów", "Tłumaczenie filmów") oraz wytycznymi Netflix Style Guide.

Twoim zadaniem jest BEZWZGLĘDNA ELIMINACJA TŁUMACZENIA 1:1, SZTYWNOŚCI, POWTÓRZEŃ SŁÓW, ZBĘDNYCH ZAIMKÓW "JA" I KALEK.

ZASADA UCHA POLSKIEGO WIDZA I KONDENSACJI BELCZYKA:
1. Przeanalizuj CAŁE ZDANIE i relację między kolejnymi kwestiami rozmówców.
2. Zadaj sobie pytanie: "Czy żywy człowiek / nastolatek w Polsce w tej sytuacji na ekranie naprawdę tak by powiedział?".
3. Jeśli zdanie brzmi sztucznie, zawiera watę słowną, powtarza w kółko to samo słowo co rozmówca, używa zbędnego "Ja" lub kalkuje angielską składnię - MASZ BEZWZGLĘDNY OBOWIĄZEK JE PRZEPISAĆ na płynny, zwięzły, autentyczny język polski!

KRYTYCZNA LISTA KONTROLNA BELCZYKA:
1. RELACJE SPOŁECZNE I TYTUŁY (-sensei / -san):
   - Uczeń mówiący o nauczycielu/nauczycielce (-sensei) MUSI użyć formy grzecznościowej ("pani Teshima", "mangi pani Teshimy", "Proszę pani!"). ZAKAZ mówienia o nauczycielu samym nazwiskiem jak o koledze ("mangi Teshimy")!
2. ELIMINACJA POWTÓRZEŃ LEKSYKALNYCH I ANAFORA (ZAIMEK 'TO / NA TO'):
   - Jeśli w zdaniu A padł rzeczownik (np. "Wyszła wam całkiem spójna historia"), W KOLEJNYM ZDANIU B (np. "Jak ułożyłyście tę historię?") BEZWZGLĘDNIE ZABRANIA SIĘ POWTARZANIA TEGO SAMEGO SŁOWA!
   - Zastąp je zaimkiem ("Jak na to wpadłyście?", "Jak to wymyśliłyście?", "Jak to poskładałyście?"), elipsą lub synonimem ("mangi" -> "tytuły", "serie").
3. ELIMINACJA PRZESYTU ZAIMKA "JA":
   - Usuń zbędne "Ja" na początku zdań ("Ja myślę" -> "Myślę", "Ja wiem" -> "Wiem").
4. AMERYKANIZMY I DROBIAZGI:
   - "Welcome back" -> "Witaj!", "Dobrze cię widzieć!", "Wróciłeś!" (ZAKAZ: "Witaj z powrotem").
   - "I hope so" -> "Oby!", "Mam nadzieję" (ZAKAZ: "Mam taką nadzieję").
   - "You said" -> "Mówiłeś, że..." (ZAKAZ: "Powiedziałeś że").
   - "Your Honor" -> "Wysoki Sądzie" (ZAKAZ: "Wasz Honor").
5. PŁYNNOŚĆ, SZYK ZDANIA I SPÓJNOŚĆ ZDAŃ ROZBITYCH WIELOKROPKIEM (`...`):
   - Połącz rozbite linijki w logiczną całość z poprawnym polskim szykiem wyrazów i odmianą.
   - SPÓJNOŚĆ ZDAŃ ROZBITYCH MIĘDZY DWOMA NAPISAMI: Gdy zdanie ciągnie się przez dwa napisy (z `...`), sprawdź bezwzględną zgodność liczby i formy orzeczenia!
   - ZAKAZ DUBLOWANIA CZASOWNIKA (np. KARDYNALNY BŁĄD [X]: linijka A: "Taktyka... potrafi być...", linijka B: "...bywają niezwykle groźne, o ile zadziałają.").
   - POPRAWNIE [OK]: linijka A: "Taktyka łamiąca reguły wojny...", linijka B: "...bywa niezwykle groźna, o ile zadziała.".
6. FORMULARZE POWITAŃ (AISATSU):
   - "I'm home" -> MUSI być "Wróciłam!" / "Wróciłem!" / "Już jestem!" (ZAKAZ: "Już w domu").
   - "Welcome home" -> "Witaj w domu!", "Dobrze, że jesteś!".
7. IDIOMY I ŻARTY:
   - "Bless you" (przy składaniu rąk / wdzięczności / jedzeniu) -> "Niech ci niebiosa wynagrodzą!", "Jesteś aniołem!", "Bogini!", "Nasza zbawczyni!" (ZAKAZ: "Na zdrowie" gdy nikt nie kicha!).
   - "Give me a break" -> "Daj spokój!", "Nie przesadzaj!" (ZAKAZ: "Daj mi przerwę").
   - "Take it easy" -> "Spokojnie", "Wyluzuj" (ZAKAZ: "Weź to lekko").
   - "I don't buy it" -> "Nie wierzę w to", "Bujda" (ZAKAZ: "Nie kupuję tego" dosłownie).
   - "That bombed / That one bombed" -> "To mi chyba nie wyszło", "Chyba spalony żart", "To było słabe" (ZAKAZ: "poniosło klapę" / "tamten").
   - "I'm sure" -> "Jestem pewna/pewien" / "Na pewno" (ZAKAZ: "Jasne...").
   - "I blew it" -> "Zawaliłam" / "Dałam ciała".
   - "His stuff is great" -> "Jego prace są świetne", "Świetnie rysuje" (ZAKAZ: "Świetnie to robi").
8. ANGIELSKIE SZABLONY:
   - "I see" -> "Rozumiem" (ZAKAZ: "Widzę").
   - "Makes sense" -> "To ma sens" (ZAKAZ: "To robi sens").
   - "Are you okay / You good?" -> "Wszystko w porządku?" (ZAKAZ: "Jesteś w porządku?").
   - "Seems to be" -> "Wydaje się" (ZAKAZ: "Wydaje się być").
   - "Give me a hand" -> "Pomóż mi" (ZAKAZ: "Daj mi rękę").
9. HONORYFIKATORY, ETYKIETA I ZAKAZ TAUTOLOGII („PAN... PANIE”) ORAZ PRZESYTU („ANTI-HONORIFIC SPAM”):
   - {"ZACHOWAJ honoryfikatory (-kun, -chan, -san, -sensei) zgodnie z konwencją." if keep_honorifics else "ZASTĄP honoryfikatory naturalną polszczyzną (-sensei -> pani/pan [Nazwisko], -san -> pan/pani lub samo imię, -kun/-chan -> samo imię)."}
   - KATEGORYCZNY ZAKAZ mówienia per 'pan/pani [Nazwisko]' (np. 'panie Minami') między uczniami i rówieśnikami w szkole! W polskim liceum/szkole koledzy i koleżanki mówią do siebie PO IMIENIU ('Arata, zdradzasz ją?!') lub po samym nazwisku ('Minami, zdradzasz ją?!'). Formę 'Pan/Pani' rezerwujemy WYŁĄCZNIE dla nauczycieli i osób dorosłych!
   - KATEGORYCZNY ZAKAZ TAUTOLOGII HONORYFIKATYWNYCH („To pan, Młody Panie” / „To pan, panie generale”)! Zastępuj je naturalnym zaimkiem bezpośrednim: „To ty, młody panie.” / „Właśnie ty, młody panie.”, a wołacze pisz z małej litery („młody panie”, „wasza wysokość”).
   - ZASADA JEDNOKROTNEJ TYTULATURY W DIALOGACH FEUDALNYCH: Zakaz powtarzania 'pan/pana/dla pana' w każdym zdaniu wypowiedzi! Tytuł podaj raz („młody panie”), a wewnątrz monologu odmieniaj czasowniki w naturalnej 2. osobie („przemierzasz”, „gdyby cię pojmał”, „zrobiłeś już dość”).
10. PERSPEKTYWA GRAMATYCZNA I KTO MÓWI (1. OSOBA VS 2. OSOBA):
   - Upewnij się, czy kwestia nie jest deklaracją/obietnicą mówiących bohaterów (1. osoba: "My przejdziemy...", "Sami uzbieramy...").
   - BEZWZGLĘDNY ZAKAZ mylenia perspektywy: gdy uczennica z zaciśniętą pięścią krzyczy do nauczycielki o planach klubu, MUSI być 1. osoba: "Na cyfrowy przejdziemy, jak same uzbieramy!", a NIE 2. osoba: "Na cyfrowy przejdziecie...".
11. NATURALNE FRAZY PYTAJĄCE I KOLOKACJE:
   - "How did you put this story together?" / "How did you come up with it?" -> "Jak na to wpadłyście?", "Jak to wymyśliłyście?", "Skąd ten pomysł?" (ZAKAZ dosłownego: "Jak ułożyłyście tę historię?").
   - "How did you do that?" -> "Jak ci się to udało?", "Jak to zrobiłaś?".
12. ROZDZIAŁ NAPISÓW EKRANOWYCH OD MÓWIONYCH DIALOGÓW:
   - Upewnij się, że kwestie typu NAPIS EKRANOWY / TYTUŁ (Sign/Typesetting - np. tytuł mangi 'The Princess's Favor') są przetłumaczone jako samodzielny tytuł ('Łaska księżniczki'), a nie jako część zdania dialogu mówionego (np. BŁĄD: 'I w ten sposób zewnętrzne ramki...').
13. POPRAWNOŚĆ PŁCI (ŻEŃSKA DLA UCZENNIC) I ZAKAZ HALUCYNACJI DZIERŻAWCZYCH:
   - W dialogach między uczennicami/kobietami bezwzględnie stosuj formy ŻEŃSKIE ("Głupia jesteś?", "Oszalałaś?", "Zrobiłaś to?", "Jesteś pewna?"). ZAKAZ form męskich ("Głupi jesteś?")!
   - Kwestie typu "[Imię]'s dad / mom / manga" tłumacz DOKŁADNIE w 3. osobie ("Tata Akafuku!", "Manga pani Teshimy!"). BEZWZGLĘDNY ZAKAZ zamiany na 1. osobę ("to mój tata")!
14. POPRAWNOŚĆ PRZYCZYN ZGONU I MEDYCYNY:
   - "Died of a brain hemorrhage" -> "zmarła z powodu wylewu", "zmarła wskutek wylewu" (ZAKAZ: "zmarła na wylew").
   - "Heart attack" -> "zawał serca", "zawał" (ZAKAZ: "atak serca").
15. REALIA HISTORYCZNE I STYLIZACJA ŚWIATA:
   - W seriach historycznych (np. XIII w. Imperium Mongolskie, starożytność, średniowiecze) BEZWZGLĘDNIE wyeliminuj nowoczesny slang młodzieżowy ('spoko', 'masakra', 'wkręcasz'). Dopasuj słownictwo do klimatu epoki.
16. TERMINOLOGIA SPECJALISTYCZNA I KONSULTACJA BRANŻOWA:
   - W seriach o tematyce niszowej (winiarstwo, muzyka, medycyna, shogi, kulinaria) bezwzględnie stosuj oficjalną polską terminologię branżową (np. w winie: 'szczep', 'rocznik', 'apelacja', 'taniny', 'kupaż', 'ciało wina').
17. OBOWIĄZEK ATRYBUCJI FILARU W POLU 'changes_made':
   - W polu 'changes_made' dla każdej poprawionej kwestii BEZWZGLĘDNIE podawaj numer i nazwę Filaru AVT, na podstawie którego dokonałeś korekty, np.:
     * "[Filar XXXIV - Relacje Rodzinne] Usunięto 'starszy bracie' -> 'brachu'"
     * "[Filar XLIV - Czasowniki Wektorowe] 'Widzę to po panu' -> 'Już widać!' (po cięciu na samolot)"
18. CIĘCIA MONTAŻOWE, CZASOWNIKI WEKTOROWE (-TE KURU / MIETEKITA) I DESYGNATY ZAIMKÓW:
   - Kiedy po cięciu sceny (np. podróż, lecący samolot, plener) postać mówi "I can see it!" (audio: 'Mietekita!'):
     -> KARDYNALNY BŁĄD [X]: "Widzę to po tobie / po panu" (zignorowanie obrazu i cięcia sceny!).
     -> POPRAWNIE [OK]: "Już widać!", "Widać cel!", "Już je widać!" (zgodnie z obrazem i kolejnymi linijkami o krajobrazie/lądzie).
19. MATRYCA APROBACJI (SOU NE / SOU VS ROZUMIEM) I AIZUCHI:
   - Kiedy postać potwierdza trafną uwagę rozmówcy (audio: 'Sou' / 'Sou ne' / 'Sou desu') i rozwija jego myśl (np. o winie/charakterze):
     -> KARDYNALNY BŁĄD [X]: "Rozumiem." (bierna kalka "I see", brzmiąca obco i urzędowo!).
     -> POPRAWNIE [OK]: "Otóż to.", "Właśnie tak.", "Zgadza się.", "Dokładnie tak."
20. ZASADA YOBISUTE I ZAKAZ „PANA/PANI” PRZY SAMYM IMIENIU (FILAR XLVI):
   - Kiedy postać zwraca się do rozmówcy po samym imieniu (np. Loulan do Isseia, Shizuku do Isseia, przyjaciele, rywale):
     -> KARDYNALNY BŁĄD [X]: "Co pan czuje, panie Issei?" (sztuczny dystans niszczący dynamikę postaci!).
     -> POPRAWNIE [OK]: "Co czujesz, Issei?" (bezpośrednio po imieniu na "ty").
21. PODMIOT KONTRASTOWY W ODPOWIEDZIACH (MY FOLKS / WATASHI NO) (FILAR XLVII):
   - Kiedy postać odpowiada na pytanie o swoją rodzinę/pochodzenie ("My folks are out in..." / audio: "Watashi no..."):
     -> KARDYNALNY BŁĄD [X]: "Mieszkają na Izu Oshimie" (urwana forma bezosobowa gubiąca mówcę!).
     -> POPRAWNIE [OK]: "Moi rodzice mieszkają na Izu Oshimie." / "Moi mieszkają na Izu Oshimie."
22. ZAKAZ HYBRYD HONORYFIKATYWNYCH (PANI SENSEI -> SENSEI) (FILAR XLVIII):
   - Kiedy postać zwraca się do mangaki/mistrza/nauczyciela per 'Sensei' / 'Senpai':
     -> KARDYNALNY BŁĄD [X]: "Pani Sensei, skończyłam!", "Panie Sensei!", "Pani Senpai!" (potworek łączący polską i japońską tytulaturę!).
     -> POPRAWNIE [OK]: "Sensei, skończyłam!" / "Teshima-sensei, skończyłam!" (lub naturalnie: "Pani Teshimo, skończyłam!").
23. PRZEKŁAD PLANSZ TYTUŁOWYCH I POZYCJONOWANIE GÓRNE (FILAR XLIX):
   - Kiedy na ekranie widnieje plansza czasu/miejsca ('PRESENT DAY', 'TOKIO'):
     -> KARDYNALNY BŁĄD [X]: Brak tłumaczenia lub zasłanianie dołu ekranu.
     -> POPRAWNIE [OK]: "[ CZASY WSPÓŁCZESNE ]" / "[ OBECNIE ]" (wersalikami w nawiasie prostokątnym).
24. IZOTOPIA SEMANTYCZNA I JEDNOLITOŚĆ REJESTRU (FILAR L):
   - Kategoryczny zakaz mieszania skrajnych rejestrów (np. archaiczny styl dworski z młodzieżowym slangiem 'masakra').
25. KONDENSACJA I RYTM DIALOGU (FILAR LIV):
   - Przy szybkim tempie (CPS > 17) stosuj zwięzłą kompresję leksykalną, elipsę i usuwanie waty słownej.
26. ZASADA NIEŁAMALNOŚCI FRAZ I PODZIAŁU SKŁADNIOWEGO (FILAR LIII):
   - Nigdy nie rozdzielaj na końcu linijki przyimka od rzeczownika, imienia od nazwiska ani czasownika modalnego od bezokolicznika.
27. KALIBRACJA WULGARYZMÓW I INTENCJI (FILAR XXXIII):
   - Rozróżniaj przekleństwa ekspresywne/fatyczne (złość) od personalnych obelg (agresja) i dopasuj rejestr do wieku postaci.
28. ADAPTACJA DŹWIĘKÓW I PARALINGWISTYKI (FILAR XVIII):
   - Zakaz zostawiania surowych japońskich odgłosów ('Tch' -> 'Tsk/Szlag', 'Eh?!' -> 'Co?!', 'Ara ara' -> 'O proszę...', 'Guh' -> 'Uch...').
29. TIMING KOGNITYWNY I CIĘCIA MONTAŻOWE (FILAR LXI):
   - Zadbaj o minimum 5/6 sekundy ekspozycji napisu i respektuj cięcia kadrów (brak overhang).
30. STANDARD FORMATOWANIA PIOSENEK I MYŚLI (FILAR LVIII):
   - Piosenki formatuj z nutkami ♪ Tekst ♪, myśli i voice-over kursywą <i>tekst</i>, a normalny dialog czystą czcionką.
31. ETYKIETA SPOŁECZNA I RELACJE UCHI-SOTO (FILAR XXVIII):
   - Mówiąc do obcych o członkach własnej grupy, nie stosuj form wywyższających w 3. osobie.
32. TEORIA SKOPOS I CEL FUNKCJONALNY PRZEKŁADU (FILAR LXIII):
   - Nadrzędna funkcja dialogu: komedia ma śmieszyć, groza przerażać, akcja trzymać tempo.
33. ELIMINACJA TRZECIEGO JĘZYKA (FILAR X):
   - Bezwzględny zakaz sztucznych konstrukcji kalkowanych z języków obcych ('Co sprawia, że tak mówisz?').
34. POLSKI KANON INTERPUNKCJI I ORTOGRAFII AVT (FILAR LX):
   - Stosuj myślnik ze spacją ('- ') przy wielogłosie, wielokropek bez spacji ('...'), wykrzyknik zespolony '?ź' (wyłącznie '?!') oraz brak kropek w jednostkach ('kg', 'min').
35. ELEMENTY KULTUROWE I MATRYCA PEDERSENA (FILAR XIV):
   - Stosuj doprecyzowanie ('góra Fuji'), oficjalne ekwiwalenty lub uogólnienie ('sklep całodobowy').
36. SOCJOLEKTY I YAKUWARIGO BEZ SZTUCZNEGO FOLKLORU (FILAR XIII):
   - Kansai-ben tłumacz na zadziorny miejski kolokwializm (zakaz gwary góralskiej/śląskiej), Ojou-sama dystyngowanie, Yankee ostro i szorstko.
37. MAŁA STRATA I DOMINANTA SEMANTYCZNA BARAŃCZAKA (FILAR LXII):
   - W konflikcie rymu, metrum i dosłowności zachowaj nadrzędną dominantę artystyczną/komediową.
38. LOKALIZACJA KALAMBURÓW I KOMPENSACJA PRZESUNIĘTA (FILAR XV):
   - Przekładaj dowcip na błyskotliwy polski żart sytuacyjny lub kompensuj humor w sąsiedniej kwestii.
39. ERGONOMIA WZROKOWA I ELIMINACJA SIEROTEK (FILAR LV):
   - Usuwaj wiszące spójniki z końca wiersza i zachowuj stały rytm percepcyjny oka.
40. METRYZACJA MIAR I REALIA WALUTOWE (FILAR LIX):
   - Zamieniaj stopy/mile/funty na metry/kilometry/kilogramy; zachowaj jeny w Japonii; liczby 0-10 zapisuj słownie.
41. WIELOGŁOS I DIALOGI NAKŁADAJĄCE SIĘ (FILAR LVII):
   - Wprowadzaj myślniki dialogowe w dwóch wierszach i priorytetyzuj postać dominującą w kadrze.
42. PRECYZJA MODALNOŚCI EPISTEMICZNEJ (FILAR XLVI):
   - 'Kamo shirenai' -> 'być może / kto wie', 'ni chigainai' -> 'na pewno / bez wątpienia'.
43. INTERTEKSTUALNOŚĆ I ALUZJE DO KANONU (FILAR XXII):
   - Cytaty z klasyki literatury i mitologii tłumacz w oparciu o uznane polskie przekłady.
44. TEST LEKTORA / AKTORA NA GŁOS (FILAR XII):
   - Każda linijka musi brzmieć naturalnie, gładko i bez zbitków spółgłoskowych przy przeczytaniu na głos.
45. PRAGMATYKA CZĄSTEK KOŃCZĄCYCH SHŪJOSHI (FILAR XVI):
   - Przekładaj intencję cząstek (zo/ze -> determinacja/zuchwałość, kashira -> kobiecy namysł, yo ne -> potwierdzenie, mon -> dąsanie).
46. PIĘCIOSTOPNIOWY SYMBOLIZM ONOMATOPEI (FILAR XVII):
   - Rozróżniaj odgłosy fizyczne (giongo) od stanów psychicznych (gijougo: 'kyun' -> ścisnęło za serce) i ruchu (giyougo).
47. OGNISKOWANIE WYŁĄCZNOŚCI I KONTRAST WA VS GA (FILAR XLV):
   - Podmiot z 'Ga' akcentuj emfatycznie ('To ja to zrobię!'), a 'Wa' traktuj jako wprowadzenie tematu.
48. DYNAMICZNY CZAS PERCEPCJI I TARCIE POZNAWCZE (FILAR LV):
   - Przy metaforach i trudnych pojęciach obniżaj CPS (13-14), umieszczając ognisko rematu w dolnym wierszu.
49. EWOLUCJA RELACJI I ZAKAZ REGRESJI FORM (FILAR XXIX):
   - Po scenie zbratania bohaterów nie wracaj do sztywnego 'Pan/Pani' – zachowaj trwałą formę 'Ty'.
50. PRZEKŁAD MOWY WEWNĘTRZNEJ (FILAR LVIII):
   - Myśli postaci formatuj kursywą <i>tekst</i> z intymnym, szczerym rejestrem psychologicznym.
51. ŻARGON RPG, ISEKAI I OKNA STATUSU (FILAR XXIV):
   - Nazwy umiejętności tłumacz na wyraziste polskie miana; okna statusu formatuj technicznie [ OKNO STATUSU ].
52. KALIBRACJA PATOSU BOJOWEGO (FILAR XXXIV):
   - W przemowach bitewnych i przysięgach stosuj szlachetny patos (zakaz gaszenia sceny tanim slangiem).
53. PRAGMATYKA CISZY I ZDAŃ ELIPTYCZNYCH (FILAR XLIX):
   - Urwane zdania z 'kedo/kara' uzupełniaj kontekstowo lub naturalnym zawieszeniem głosu '...'.
54. PROTOKÓŁ MULTI-AGENT REFLEXION (FILAR LXIV):
   - Trzystopniowa synteza: Szkic Tłumacza -> Audyt Krytyka MQM -> Szlif Redaktora Naczelnego.
      * "[Filar XVI - Shūjoshi] 'Iku zo!' -> 'No to ruszamy!'"
      * "[Filar XVII - Onomatopeja] 'Zokutto shita' -> 'Przeszły mnie ciarki'"
      * "[Filar XXIV - RPG Canon] 'Status Window' -> '[ OKNO STATUSU ]'"
      * "[Filar XIV - Pedersen ECR] 'konbini' -> 'sklep całodobowy'"
      * "[Filar XIII - Yakuwarigo] Dostosowano ton Ojou-sama do dystyngowanej polszczyzny"
      * "[Filar LIX - Metryzacja] '10 feet' -> 'trzy metry'"
      * "[Filar XLVI - Modalność] 'ni chigainai' -> 'bez wątpienia'"
      * "[Filar XXXV - Izotopia Rejestru] Usunięto anachroniczny slang ze sceny historycznej"
      * "[Filar LIV - Kondensacja Díaz Cintas] Skrócono kwestię z 22 na 14 CPS"
      * "[Filar XVIII - Paralingwistyka] Przetłumaczono 'Ara ara' -> 'O proszę...'"
      * "[Filar X - Anti-Translationese] 'Co sprawia, że...' -> 'Czemu tak uważasz?'"
      * "[Filar LX - Interpunkcja AVT] Poprawiono '!?' -> '?!'"
      * "[Filar I - Odnominalizowanie] 'dokonał zabójstwa' -> 'zabił'"
      * "[Filar LIX - Notacja Liczebników] '3 dni' -> 'trzy dni'"
      * "[Filar XLIII - Aprobata Aizuchi] 'Rozumiem' -> 'Otóż to' (potwierdzenie intuicji Shizuku)"
      * "[Filar XXVI - Yobisute] Usunięto sztuczne 'panie Issei' -> 'Issei'"
      * "[Filar XLV - Podmiot Kontrastowy] 'Mieszkają...' -> 'Moi rodzice mieszkają...'"
      * "[Filar XXVII - Anty-Hybryda] 'Pani Sensei' -> 'Sensei'"
      * "[Filar XLI - Plansze i Lokacje] 'PRESENT DAY' -> '[ CZASY WSPÓŁCZESNE ]'"
      * "[Filar XI - Prefabrykowana Mówioność] Zastąpiono sztuczny imiesłów żywą polszczyzną"
      * "[Filar XXXIII - Rejestr i Wulgaryzmy] Ujednolicono surowy język żołnierski"

{BELCZYK_AVT_MASTER_CANON}

{anime_guide}

Zwróć ostateczną, perfekcyjnie skondensowaną, żywą wersję każdej kwestii w formacie JSON."""


def get_focused_rules_for_batch(batch_items: List[Dict[str, Any]]) -> str:
    """
    Dynamiczny dyspozytor reguł AVT (Context-Aware Rule Dispatcher).
    Analizuje specyfikę bieżącej paczki kwestii i generuje wysoce skoncentrowaną
    listę priorytetowych zasad, eliminując problem rozproszenia uwagi modelu ('Lost in the Middle').
    """
    if not batch_items:
        return ""

    focused_pillars = []
    combined_en = " ".join(item.get("en", "") for item in batch_items).lower()
    has_signs = any(item.get("is_sign", False) for item in batch_items)
    has_questions = any("?" in item.get("en", "") for item in batch_items)
    has_ellipsis = any("..." in item.get("en", "") or "…" in item.get("en", "") for item in batch_items)
    has_music = any("♪" in item.get("en", "") or "♫" in item.get("en", "") or "sing" in item.get("notes", "").lower() for item in batch_items)

    # 1. Pytania potoczne i eliminacja sztucznego "Czy"
    if has_questions:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR IX - Pytania bez sztucznego 'Czy']: "
            "Pytania rozstrzygnięcia twórz intonacją ('Jesteś pewna?', 'Idziesz z nami?'). Zakaz: 'Czy jesteś pewna?'."
        )

    # 2. Napisy ekranowe, tablice, tytuły
    if has_signs or any(w in combined_en for w in ["chapter", "episode", "present day", "tokyo", "sign", "title"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XLI & LX - Napisy Ekranowe, Plansze i AVT]: "
            "Napisy ekranowe i plansze tłumacz jako odrębne tytuły/nazwy (plansze: [ WERSALIKAMI W NAWIASIE ]). "
            "Kategoryczny zakaz wklejania w pole napisu ekranowego fragmentów dialogu mówionego!"
        )

    # 3. Formy grzecznościowe, tytulatura feudalna i honoryfikatory
    if any(w in combined_en for w in ["sensei", "senpai", "sama", "lord", "young lord", "general", "sir", "master"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXV, XXVII & XXVIII - Tytulatura i Etykieta]: "
            "Zakaz tautologii ('To pan, Młody Panie' -> 'To ty, młody panie'), "
            "zakaz hybryd ('Pani Sensei' -> 'Sensei'), "
            "zakaz powtarzania 'pan/pana' w każdym zdaniu (tytuł raz, potem naturalna 2. osoba)."
        )

    # 4. Zwroty Yobisute i relacje rówieśnicze
    if any(item.get("speaker_gender") for item in batch_items) or "chan" in combined_en or "kun" in combined_en:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXVI & XXIX - Zasada Yobisute i Ewolucja Relacji]: "
            "Do przyjaciół, kolegów z klasy i towarzyszy po przełamaniu lodów zwracaj się po imieniu na 'ty'. "
            "Zakaz dodawania sztucznego 'Pan/Pani' przy samym imieniu ('Panie Issei' -> 'Issei')."
        )

    # 5. Czasowniki wektorowe, cięcia scen i ląd/krajobraz
    if any(w in combined_en for w in ["i can see it", "mietekita", "look", "see", "there it is"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXXVII - Czasowniki Wektorowe i Obraz]: "
            "'I can see it' po cięciu na plener/podróż to 'Już widać!' / 'Widać cel!' (odnosi się do lądu/celu, a nie 'Widzę to po tobie')."
        )

    # 6. Matryca Aizuchi i potwierdzeń
    if any(w in combined_en for w in ["i see", "right", "makes sense", "naruhodo", "sou ne", "sou desu"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XLIII - Aprobata vs Przyjęcie Wiedzy]: "
            "Potwierdzenie trafnej uwagi rozmówcy (Sou / Sou ne) to 'Otóż to.' / 'Właśnie tak.' / 'Zgadza się.' (a NIE bierne 'Rozumiem.')."
        )

    # 7. Spójność zdań rozbitych wielokropkiem i podział wierszy
    if has_ellipsis:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LVI, LIII, LX & XLIX - Spójność i Pragmatyka Ciszy]: "
            "Zdanie rozbite na dwa napisy musi tworzyć 100% spójną gramatycznie całość: "
            "tylko jedno orzeczenie (zakaz dublowania czasownika) i ścisła zgodność liczby podmiotu."
        )

    # 8. Paralingwistyka, odgłosy, onomatopeje i wulgaryzmy
    if any(w in combined_en for w in ["tch", "ara ara", "oi oi", "guh", "kuso", "damn", "shit", "fuck", "kashira", "mon"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXXIII, XVIII, XVI & XVII - Shūjoshi i Onomatopeje]: "
            "Adaptuj odgłosy i cząstki ('Ara ara' -> 'O proszę...', 'Tch' -> 'Tsk/Szlag', 'Guh' -> 'Uch...', 'kashira' -> 'Ciekawe, czy...'). "
            "Wulgaryzmy kalibruj do ładunku emocjonalnego i rejestru sceny."
        )

    # 9. Piosenki i utwory muzyczne
    if has_music:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LVIII - Piosenki i Muzyka]: "
            "Formatuj słowa piosenek kursywą ze znakami nutek: ♪ Słowa piosenki ♪."
        )

    # 10. Jednostki miar, liczby i konwersja metryczna
    if any(w in combined_en for w in ["feet", "foot", "miles", "mile", "pounds", "pound", "inch", "inches", "meters", "km"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LIX - Metryzacja i Liczby]: "
            "Anglosaskie jednostki zamieniaj na metryczne ('feet' -> 'metry', 'miles' -> 'kilometry'). "
            "Małe liczby (0-10) zapisuj słownie ('trzy dni', 'pięć minut')."
        )

    # 11. Modalność i pewność wypowiedzi
    if any(w in combined_en for w in ["kamo", "maybe", "perhaps", "must be", "definitely", "surely", "no doubt", "hazu"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XLVI - Modalność Epistemiczna]: "
            "Precyzyjnie różnicuj stopnie pewności: 'być może / kto wie' (hipoteza) vs 'na pewno / bez wątpienia' (pewność logiczna)."
        )

    # 12. Żargon RPG, gier i systemów Isekai
    if any(w in combined_en for w in ["status", "skill", "level", "guild", "quest", "inventory", "magic"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXIV - Żargon RPG i Isekai]: "
            "Tłumacz umiejętności na chwytliwe polskie nazwy; okna statusu formatuj technicznie [ OKNO STATUSU ]."
        )

    # 13. Podmiot kontrastowy w odpowiedziach o rodzinę
    if any(w in combined_en for w in ["folks", "parents", "family", "watashi no"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XLV - Podmiot Kontrastowy i Ogniskowanie Wa vs Ga]: "
            "W odpowiedzi na pytanie o rodzinę/pochodzenie zachowaj podmiot ('Moi rodzice mieszkają...', a nie urwane 'Mieszkają...')."
        )

    if not focused_pillars:
        return ""

    lines = [
        "--- [!] SKONCENTROWANA UWAGA DLA TEJ SCENY (PRIORYTETOWE FILARY AVT) ---",
        "W bieżącej paczce kwestii zwróć szczególną uwagę na następujące kluczowe reguły:"
    ]
    lines.extend(focused_pillars)
    lines.append("------------------------------------------------------------------------\n")
    return "\n".join(lines)


