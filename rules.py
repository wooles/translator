# -*- coding: utf-8 -*-
"""
Complete audiovisual translation (AVT) rule system based on the canon of Arkadiusz Belczyk
("Tłumaczenie filmów", "Sztuka tłumaczenia filmów", "Poradnik tłumacza"),
Japanese honorific title adaptation rules, and the Netflix Polish Timed Text Style Guide.
"""

import re
from typing import List, Dict, Any, Optional, Union, Tuple
from pydantic import BaseModel, Field, ConfigDict

class SceneDiagnosis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    dramatic_context: str = Field(description="Opis sytuacji w scenie: kto z kim rozmawia, jakie są relacje i ładunek emocjonalny")
    dialogue_flow: str = Field(description="Powiązania przyczynowo-skutkowe między kwestiami: pytania, zaproszenia, reakcje, odmowy")
    audio_intent_check: str = Field(description="Weryfikacja intencji mówców ze słuchu japońskiego (Whisper) vs skrypt angielski")
    dominant_tone: Optional[str] = Field(default=None, description="Dominujący rejestr dramaturgiczny sceny (np. 'groteska komediowa', 'patos bitewny', 'intymny dramat', 'groza')")
    power_dynamic: Optional[str] = Field(default=None, description="Relacja władzy/statusu: kto dominuje, kto blefuje, kto jest w potrzasku (maks. 8 słów)")
    epistemic_asymmetry: Optional[str] = Field(default=None, description="Teoria Umysłu (Theory of Mind): Kto co wie, a czego NIE WIE w tej scenie? Kto ukrywa tożsamość/motywy? Czego postaciom w kadrze nie wolno zdradzić rozmówcy (np. 'Felix nie wie, że rozmawia z Cichą Wiedźmą; Monika milczy i ukrywa tożsamość')?")
    table_read_mouth_feel: Optional[str] = Field(default=None, description="Próba Stolikowa (Barańczak-Stanisławski): Weryfikacja potoczystości mówionej: czy kwestie układają się naturalnie w ustach polskich aktorów dubbingowych i eliminują papierowe kalki?")

BELCZYK_AVT_MASTER_CANON = r"""
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
- 2. KOLOKACJE CZASOWE I REALIA SZKOLNE:
  * "lunch break / noon recess" (昼休み) -> "długa przerwa" (lub "przerwa obiadowa") (KATEGORYCZNY ZAKAZ: "duża przerwa" - czas w polszczyźnie ma wymiar DŁUGOŚCI, a nie rozmiaru fizycznego; w polskich szkołach mówi się wyłącznie "długa przerwa"!).
  * "short break / recess" -> "krótka przerwa" (ZAKAZ: "mała przerwa").
  * "long weekend" -> "długi weekend" (ZAKAZ: "duży weekend").

FILAR IV: ELIMINACJA SZTUCZNYCH CZASOWNIKÓW POSIŁKOWYCH I POZORNEGO TRWANIA:
- 1. SZTUCZNA ANALITYCZNOŚĆ:
  * "I was able to find it" -> "Znalazłem", "Udało mi się znaleźć" (ZAKAZ: "Byłem w stanie to znaleźć").
  * "I started to cry / laugh" -> "Rozpłakałem się", "Rozśmiałem się" (ZAKAZ: "Zacząłem płakać / śmiać się").
  * "I feel like doing X" -> "Mam ochotę na X", "Chcę X" (ZAKAZ: "Czuję się jak robienie X").
  * "I have a feeling that..." -> "Coś mi mówi, że...", "Wydaje mi się, że..." (ZAKAZ: "Mam uczucie że").
  * "It looks like it's going to rain" -> "Zbiera się na deszcz", "Chyba będzie padać" (ZAKAZ: "Wygląda jakby miało padać").
  * "Welcome back" -> "Witaj!", "Dobrze cię widzieć!", "Wróciłeś!", "Witaj w domu!" (ZAKAZ: "Witaj z powrotem").
  * "passed the point of no return" -> "nie ma już odwrotu", "z tej drogi nie ma odwrotu", "dla tej armii nie ma już powrotu", "za daleko zaszli, by zawrócić" (KATEGORYCZNY ZAKAZ: "przekroczyła punkt bez powrotu" - to obca kalka niszcząca klimat eposu i dramatu).
- 2. KALKI KONSTRUKCJI POZORNEGO TRWANIA I POSIADANIA:
  * "is in the process of doing" -> "właśnie robi", "robi" (ZAKAZ: "jest w trakcie robienia").
  * "came into possession of" -> "zdobył", "ma", "wszedł w posiadanie" (ZAKAZ: "znalazł się w posiadaniu").

FILAR V: ELIMINACJA ZBĘDNYCH ZAIMKÓW DZIERŻAWCZYCH I OSOBOWYCH:
- Angielski wymaga zaimka przy każdej części ciała i własności. Po polsku relacja wynika z kontekstu i formy zaimka osobowego (celownik/biernik):
  * "I put my hands in my pockets" -> "Włożyłem ręce do kieszeni" (ZAKAZ: "moje ręce do moich kieszeni").
  * "She talked with her sister" -> "Rozmawiała z siostrą" (ZAKAZ: "ze swoją siostrą").
  * "Close your eyes" -> "Zamknij oczy" (ZAKAZ: "twoje oczy").
  * "I broke my leg" -> "Złamałem nogę" (ZAKAZ: "moją nogę").
  * "He grabbed my hand / arm" -> "Złapał mnie za rękę / ramię" (ZAKAZ: "złapał moją rękę").
  * "He cut his head / throat" -> "Ściął mu głowę / Podciął mu gardło" (ZAKAZ: "ściął jego głowę").
  * "She looked into my eyes" -> "Spojrzała mi w oczy" (ZAKAZ: "spojrzała w moje oczy").
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
  * BŁĘDNE ZWIĄZKI FRAZEOLOGICZNE I INWERSJE AFEKTYWNE: Kategoryczny zakaz kalkowania angielskich idiomów z fałszywym zabarwieniem emocjonalnym (BŁĄD [X]: 'odchodzić od zmysłów ze szczęścia' -> POPRAWNIE: 'szaleć ze szczęścia / nie posiadać się ze szczęścia / z radości'; w języku polskim 'odchodzić od zmysłów' łączy się wyłącznie z emocjami negatywnymi: rozpaczą, żalem, niepokojem).
  * ZWIĄZEK ZGODY LICZEBNIKÓW GŁÓWNYCH (FILAR IV): Podmiot liczebnikowy w l. mn. wymaga orzeczenia w liczbie mnogiej (POPRAWNIE: 'Dwa tysiące w zupełności wystarczą', BŁĄD: 'wystarczy').
  * PROAKTYWNA MATRYCA REJESTRU DARK FANTASY (4 KLASY ZAKAZANEGO SLANGU): W uniwersach fantasy i historycznych kategorycznie zakazuje się trywializującego slangu współczesnego:
    - Klasa A (Slang młodzieżowy/potoczny): 'I gitara' -> 'Doskonale / Świetnie', 'spoko', 'siemanko', 'wchodzę w to' -> 'Przyjmuję ten układ / Zgadzam się', 'Bez jaj!' -> 'Niemożliwe! / To jakieś kpiny! / Kpiny na kiju!'.
    - Klasa B (Agresja podwórkowa i trywializacja): 'stul pysk' -> 'Zamilcz / Milcz', 'zamknij się', 'spuścić komuś łomot' -> 'zmiażdżyć bez trudu / rozgromić w pył', 'oberwę' -> 'poniosę karę / zginę', 'guzik mnie to obchodzi' -> 'nic mnie to nie obchodzi / niewiele mnie to obchodzi', 'pora stąd zwiewać / zwiewamy' -> 'pora stąd uciekać / czas uciekać'.
    - Klasa C (Współczesne metafory potoczne): 'przejmuję stery' -> 'teraz ja mówię', 'dla zabicia czasu' -> 'dla rozrywki', 'kłamstwo jak byk' -> 'bezczelne kłamstwo', 'wylatywać ze szkoły' -> 'zostać wydalonym ze szkoły', 'utrzeć komuś nosa' -> 'pokazać mu / utemperować go', 'zrobić raban' -> 'wywołać zamieszanie', 'wypruć się do cna' -> 'opaść z sił', 'zmywać się stąd' -> 'uciec stąd'.
    - Klasa D (Trywializujące zaimki/rzeczowniki): 'ten typ' -> 'ten człowiek / nauczyciel', 'dzikuska / chuliganka' -> 'prostaczka / awanturnica', 'dzieciaki' -> 'uczniowie / młodzież', 'durna jestem' -> 'głupia jestem'.
  * ZAKAZ KALKOWANIA PRZYDOMKÓW 'X OD Y': Japońskie przydomki bóstw i stworzeń z partykułą 'no' (np. Ryū no Kishi, Gakuen no Majo) tłumaczymy przymiotnikowo lub czystym dopełniaczem (KATEGORYCZNY ZAKAZ: 'Rycerz od Smoka' -> 'Smoczy Rycerz / Rycerz Smoka'; 'Wiedźma od Akademii' -> 'Wiedźma z Akademii / Akademiczna Wiedźma').
  * RZĄD I RODZAJ GRAMATYCZNY RZECZOWNIKA 'POSOKA': 'Posoka' jest wyłącznie rodzaju żeńskiego (ta czarna posoka, tej czarnej posoki, przez czarną posokę; KATEGORYCZNY ZAKAZ: 'czarny posok', 'przez czarny posok', 'z czarnego posoku').
  * FLEKSJA WOŁACZA NAZWISK OBCYCH I ARTEFAKTÓW: Fonetyczna adaptacja w wołaczu i przypadkach zależnych: zmiękczenie tematu przy spółgłoskach (np. Vincent -> Vincencie), dopełniacz obcych imion (np. Andrew -> Andrewie).
  * RZĄD PRZYIMKOWY DLA URAZU I TRAUMY (FILAR IV): KATEGORYCZNY ZAKAZ: 'mam przez coś uraz' (kalka z angielskiego 'have trauma from'). W języku polskim: 'mam do czegoś uraz' lub 'mam przez to traumę'.
  * KALKA AUTO-REFERENCYJNA (MY DEAR ME): Kategoryczny zakaz kalki 'moja droga ja' / 'droga ja'. W monologu wewnętrznym stosuj: 'moja ty mała', 'mała ja', 'taka ze mnie drobina'.
  * ZWIĄZEK ZGODY RZECZOWNIKA 'SŁUGA' (FILAR IV): Zakaz formy 'moja sługa' w odniesieniu do kobiety (BŁĄD [X]: 'by moja sługa mogła uciec' -> POPRAWNIE [OK]: 'by moja podwładna mogła uciec' / 'by moja służąca mogła uciec').
  * KALKA SKŁADNIOWA WYKLUCZENIA: Kategoryczny zakaz kalki 'dla wszystkiego poza X nie ma litości' -> POPRAWNIE: 'nie ma litości dla niczego prócz X' / 'oszczędza wyłącznie X'.
  * FAŁSZYWE POŁĄCZENIE FRAZEOLOGICZNE W CZASIE: Kategoryczny zakaz 'w cztery oczy od czasu X' -> POPRAWNIE: 'na osobności od czasów X' / 'sam na sam od czasów X'.

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
- KATEGORYCZNA ELIMINACJA SZUMU WIZUALNEGO (SUBTITLE CLUTTER & ISOLATED GRUNTS):
  * Gdy kwestia w dialogu to pojedynczy odgłos seiyuu (naburmuszone "Uh", westchnienie "Ah", fuknięcie "Hmph", sapnięcie "Guh", "Och!"), a mimika twarzy i aktor głosowy w 100% przekazują emocję -> ZWRÓĆ PUSTY NAPIS "" (eliminacja szumu wizualnego według standardu Netflix / Canal+ AVT).
- JAPOŃSKIE ODGŁOSY WYSIŁKU FIZYCZNEGO, KINEZJATYKI I SOMATYKI CIAŁA (KAKEGOE & SOMATIC REFLEXES):
  * "Ottotto..." (おっとっと…) / "Ototo..." (odruch utraty równowagi, potknięcia, chwiania się, niemal upadku na plecy/twarz):
    -> POPRAWNIE: „Ło, ło, ło...!”, „Uuu, powoli...!”, „O-o-o, chwila...!”, „Hop, hop, hop...!” lub PUSTY NAPIS "" (elipsa szumu wizualnego Netflix AVT).
    -> KARDYNALNY BŁĄD [X]: „Oho, spokojnie...”, „Łatwo tam...” (bezduszna kalka z angielskiego 'Whoa, easy there' - 'oho' to wykrzyknik spostrzeżenia, nikt lecąc na plecy nie mówi 'oho', a 'spokojnie' to komenda do kogoś obcego, nie odruch własnego ciała!).
  * "Acchichi!" (あっちっち!) / "Atsu'!" (oparzenie termiczne, dotknięcie gorącej lufy/garnka/wrzątku):
    -> POPRAWNIE: „Ała!”, „Parzy!”, „Cholera, gorące!”.
    -> KARDYNALNY BŁĄD [X]: „To jest gorące!” (szkolny opis stanu zamiast odruchu bólu).
  * "Sammu!" (さっむ!) / "Samui!" (nagły szok termiczny z zimna, wpadnięcie do lodowatej wody, mróz):
    -> POPRAWNIE: „Brrr!”, „Ale piździ!”, „Ale mróz!”, „Lodowata!”.
    -> KARDYNALNY BŁĄD [X]: „To jest zimne!”.
  * "Itta!" (痛っ!) / "Ita'!" (nagły ból mechaniczny: walnięcie głową w belkę, postrzał, uderzenie piszczelem):
    -> POPRAWNIE: „Ała!”, „Auć!”, „Niech to...!”, „Szlag!”.
    -> KARDYNALNY BŁĄD [X]: „To boli!”.
  * "Yotto..." (よっと…) / "Yoisho..." (よいしょ…) / "Dokkoisho..." (どっこいしょ…) / "Yoi kora..." (odgłos wysiłku przy podnoszeniu ciężaru, stawianiu wiadra, siadaniu, kucaniu, wstawaniu z krzesła/ziemi):
    -> POPRAWNIE: BEZWZGLĘDNA ELIPSA "" (pusty napis - widz widzi ruch na ekranie i słyszy wysiłek; brak napisu to najwyższy standard profesjonalizmu AVT Belczyka / Netflixa) lub w ostateczności "No i już..." / "Uch...".
    -> KARDYNALNY BŁĄD [X]: "Tutaj...", "Proszę...", "Oto..." (kalka z angielskiego "Here / There you go") oraz infantylne podpisy "Hop...", "I siup...", "Raz, dwa..." przy dorosłych postaciach!
  * Gesty podawania i częstowania ("Hai" / "Dōzo" / "Hora" -> w EN: "Here", "Here you go", "There"):
    -> POPRAWNIE: w większości scen ELIPSA "" (obraz w 100% wyjaśnia gest podania), a jeśli relacja wymaga zaznaczenia w dialogu: wyłącznie naturalne "Proszę", "Trzymaj", "Masz" (w locie/walce: "Łap!").
    -> KARDYNALNY BŁĄD [X]: KOSZMARNA KALKA "Tutaj!" / "Tu!" (w języku polskim wręczając komuś herbatę, klucze czy dokument nikt nie mówi "Tutaj!").
  * "Hora!" (ほら) / "Sora!" (そら) (przy rzucie, dynamicznym podaniu przedmiotu w locie):
    -> POPRAWNIE: "Łap!", "Masz!", "Trzymaj!" (KATEGORYCZNY ZAKAZ: "Tutaj!" / "Proszę!").
  * "Puhā!" (ぷはーっ!) (sapnięcie ulgi/orzeźwienia po kuflu zimnego piwa lub wynurzeniu z wody):
    -> POPRAWNIE: „Aaaach!”, „Ale dobre!”, „Wreszcie powietrze!” lub puste "" (elipsa szumu).
    -> KARDYNALNY BŁĄD [X]: „Pha!”.
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

FILAR XXI: EKSPLIKACJA PODTEKSTU, IMPLIKATURY I MATRYCA FORMUŁ PHATYCZNYCH (PAUL GRICE & ANIMESUB.INFO STANDARD):
- 1. EKSPLIKACJA PODTEKSTU (HARAGEI UNPACKING):
  * W kulturze japońskiej sens bywa przemilczany ("Sore wa chotto..."). W języku polskim wymagana jest umiarkowana eksplikacja intencji odmowy ("Obawiam się, że to niemożliwe", "Wykluczone") zamiast urwanego "To trochę...".
- 2. ZŁOTA MATRYCA FORMUŁ PHATYCZNYCH (ANIMESUB.INFO KANON):
  * "Itadakimasu" -> Zależnie od sytuacji scenicznej: "Dzięki za jedzenie!", "No to jemy!", "Wygląda pysznie!", "Dziękuję za posiłek!" (KATEGORYCZNY ZAKAZ mówienia "Smacznego" samemu do siebie w pustym pokoju!).
  * "Gochisousama (deshita)" -> "Dziękuję, było pyszne!", "Dzięki za poczęstunek!", "Najadłem się!".
  * "Otsukaresama (deshita)" -> Po pracy/walce: "Dobra robota", "Dzięki za dziś", "Należał wam się odpoczynek"; w korytarzu biura: "Dzień dobry".
  * "Shouganai / Shikata ga nai" -> "Trudno", "Przepadło", "Nie mamy wyboru", "I tak byśmy tego nie zmienili" (ZAKAZ sztywnego: "Nic nie da się zrobić").
  * "Tadaima / Okaeri" -> "Już jestem! / Wróciłem!" oraz "Witaj w domu! / Już jesteś!".

FILAR XXII: PRZEKŁAD TYTUŁÓW DZIEŁ, MITOLOGII I INTERTEKSTUALNOŚCI (ALLUSION & CANON RECOGNITION):
- Cytaty, nawiązania literackie, mitologiczne i popkulturowe:
  * Sprawdzaj ugruntowany polski kanon (np. 'Hrabia Monte Christo', 'Sherlock Holmes', 'Król Artur', 'Mitologia Nordycka').
  * Cytaty z klasyki (Szekspir, Biblia, Mickiewicz, Lem) tłumacz zgodnie z kanonicznymi polskimi przekładami, a nie z translacji powrotnej!

FILAR XXIII: KANON POLSKICH WYDAŃ MANGOWYCH I SPÓJNOŚĆ TRANSMEDIALNA (TRANSMEDIA CANON CONSISTENCY):
- Gdy seria posiada oficjalny polski przekład mangowy (np. Waneko, J.P.Fantastica, Studio JG, Hanami, Kotori):
  * BEZWZGLĘDNIE zachowaj ustalone w polskim wydaniu papierowym nazwy technik, magii, krain, formacji bojowych i rang (np. "Rozszerzenie Domeny", "Przeklęta Energia", "Korpus Zwiadowczy", "Wielki Generał", "Państwo Środka").
  * KANON TYTUŁÓW I EPITETÓW: Oficjalne polskie wydania mangowe mają bezwzględne pierwszeństwo przed tłumaczeniem dosłownym z angielskiego lub kalkami z fansubów (np. 'Monster Prince' wg Studio JG to oficjalnie 'Potworny Królewicz'; zgodnie z oficjalną bazą manga_canon.py lub SeriesBible).
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
- KANON TYTULATURY MONARSZEJ I STEPOWEJ:
  * Władcy imperium koczowniczego/mongolskiego w polskiej tradycji historycznej to wyłącznie "Chan / Wielki Chan" (dopełniacz: "chana / Wielkiego Chana", wołacz: "chanie / Wielki Chanie"). KATEGORYCZNY ZAKAZ fonetycznych kalk: "Chagan", "Chaganie".

FILAR XXVI: ZASADA YOBISUTE I ZAKAZ SZTUCZNEGO „PANA/PANI” PRZY SAMYM IMIENIU (ANTI-FALSE FORMALITY):
- ZWROT PO SAMYM IMIENIU (Yobisute - Issei, Shizuku, Loulan, Arata):
  * Gdy w audio lub tekście postać zwraca się do rozmówcy po SAMYM IMIENIU bez japońskich honoryfikatorów:
    -> BŁĄD [X]: Dodawanie słowa "Pan/Pani" ("Pan Issei", "panie Issei", "pani Loulan").
    -> POPRAWNIE [OK]: Zwracanie się bezpośrednio po imieniu na "ty": "Issei, co o tym myślisz?", "Shizuku, spróbuj tego wina!".
- RELACJE BLISKIE, TOWARZYSKIE, RYWALIZUJĄCE I POSTACIE ZAGRANICZNE:
  * Towarzysze podróży, rywale, przyjaciele oraz cudzoziemcy nieznający sztywnej etykiety biurowej ZAWSZE mówią do siebie po imieniu na "ty".
- RELACJE RÓWIEŚNICZE W SZKOLE I KLUBIE (DE-FORMALIZACJA -SAN MIĘDZY UCZNIAMI):
  * Zakaz sztucznych form per 'Pan/Pani [Nazwisko]' i czasowników w 3. osobie grzecznościowej między uczniami i kolegami z klasy/klubu (BŁĄD: 'Panie Tanaka, ma pan zeszyt?' -> POPRAWNIE: 'Tanaka, masz zeszyt?').
  * Japoński grzeczny przyrostek '-san' używany przez ucznia do rówieśnika to w polszczyźnie samo nazwisko lub imię w bezpośredniej relacji na 'ty'.
- SPÓJNOŚĆ REJESTRU W RELACJACH FORMALNYCH (T-V INVARIANCE):
  * W relacjach ściśle formalnych i zawodowych utrzymuj jednolity rejestr grzecznościowy per 'Pan/Pani' we wszystkich kwestiach w obrębie sceny.
  * Zakaz przypadkowego zsuwania się na 'ty' w tej samej scenie, jeśli relacja wymaga dystansu.
- KIEDY STOSUJEMY FORMĘ „PAN/PANI”:
  * WYŁĄCZNIE przy formalnych zwrotach po NAZWISKU z honoryfikatorem (np. Tomine-sensei -> "pan Tomine", Kanzaki-san -> "pan Kanzaki") lub w oficjalnych relacjach urzędowych/kelner-klient.

FILAR XXVII: ZAKAZ HYBRYD HONORYFIKATYWNYCH I ADAPTACJA TYTUŁÓW (ANTI-DOUBLE HONORIFIC HYBRID):
- ZAKAZ ŁĄCZENIA POLSKIEJ TYTULATURY Z JAPOŃSKĄ:
  * Kiedy w audio pada japoński tytuł (np. "Sensei!", "Senpai!", "Sato-sensei!"):
    -> BŁĄD [X]: "Pani Sensei, skończyłam!", "Panie Sensei!", "Pani Senpai!" (sprzeczne tytulatury!).
    -> POPRAWNIE W TRYBIE ANIME [OK]: "Sensei, skończyłam!", "Sato-sensei, skończyłam!", "Senpai!".
    -> POPRAWNIE W TRYBIE NATURALNYM [OK]: "Pani Sato, skończyłam!", "Mistrzyni, skończyłam!", "Szefowo, skończyłam!".
- ADAPTACJA HONORYFIKATORÓW SZKOLNYCH I SLANGU OTAKU:
  * 'Senpai' w dialogu szkolnym/towarzyskim adaptujemy do naturalnej polszczyzny: używamy imienia rozmówcy w wołaczu lub zwrotu bezpośredniego na 'ty'. Zakaz pozostawiania 'senpai' w polskich napisach filmowych w relacjach codziennych.
  * Końcówki spieszczające ze slangu otaku typu '-taso', '-tan' zastępujemy standardowym imieniem lub polskim zdrobnieniem (zgodnie z profilem postaci w SeriesBible). KATEGORYCZNY ZAKAZ ucinania imienia do sztucznego rdzenia!
  * ZAKAZ AUTO-ADRESACJI (ANTI-SELF-ADDRESS MANDATE): Mówca pod żadnym pozorem nie może zwracać się do siebie własnym imieniem! Przy adaptacji wołaczy ('Senpai!', 'Sensei!') w kwestiach jedno- i wieloliniowych, jeśli zwrot jest tłumaczony imieniem, musi bezwzględnie wskazywać partnera dialogowego (adresata), a NIE mówcę. W razie braku pewności co do adresata stosuj formę eliptyczną/bezosobową ('Prawda?', 'Słuchaj!', 'Nic ci nie jest?').
  * POLITE SURNAME RECOVERY (KOREKTA NAZWISKOWA NA FORMĘ GRZECZNOŚCIOWĄ): Gdy postać koryguje spoufalenie i wycofuje się z imienia do formy formalnej ('[Nazwisko]-senpai'), w języku polskim należy bezwzględnie zastosować 'panno [Nazwisko]' (dla kobiety) lub 'panie [Nazwisko]' (dla mężczyzny).
  * WOŁACZ PRZYDOMKÓW MEDIALNYCH (TITULAR MONIKER VOCATIVE): Gdy bohater nosi oficjalny przydomek tytularny, bezpośredni zwrot w wołaczu musi być poprawny gramatycznie i zgodny z kanonem serii (np. manga_canon.py / SeriesBible).

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
  * FANSUB-QUALITY VISUAL TYPESETTING (Pixel-Perfect Spatial Grounding): Dla plansz, szyldów, okładek mangi i onomatopei (SFX) rozpoznaj na dołączonym kadrze wideo pozycję oryginalnego tekstu (detected_box_1000: [ymin, xmin, ymax, xmax]), kąt obrotu (rotation_deg: np. -25 dla skosu), sugerowane umiejscowienie ('above' / 'below' / 'overlay') oraz dominujące kolory (primary_color_hex, outline_color_hex), aby tłumacz mógł wygenerować perfekcyjne współrzędne ASS (\pos, \frz, \1c, \3c) dorównujące ręcznemu typesettingowi grup fansubberskich.
  * BEZPIECZNIK ANTYKOLIZYJNY: Jeśli w pliku .ass istnieją już wystylizowane napisy dla notesu/plakatu, nie dubluj linii.

FILAR XLII: ZAKAZ HALUCYNACJI PRZYNALEŻNOŚCI I ZAIMKÓW DZIERŻAWCZYCH (3. OSOBA VS 1. OSOBA):
- Kiedy w kwestii pojawia się imię postaci w dopełniaczu (np. "Akafuku's dad!", "Sensei's manga!", "Kokoro's house!"):
  * Oznacza to DOKŁADNIE tę nazwaną postać w 3. osobie ("Tata Akafuku!", "Ojciec Akafuku!", "Manga pani Teshimy!", "Dom Kokoro!").
  * BEZWZGLĘDNY ZAKAZ zamiany imienia innej osoby na zaimki 1. osoby (BŁĄD [X]: przetłumaczenie "Akafuku's dad!" na "to mój tata"!).


MODUŁ V: PRAGMATYKA DIALOGU I KONTEKST ROZMOWY (FILARY XLIII – LII)

FILAR XLIII: MATRYCA PRAGMATYCZNA POTWIERDZEŃ, APROBACJI I AIZUCHI (CONVERSATIONAL VALIDATION MATRIX):
- ROZRÓŻNIENIE APROBACJI OD PRZYJĘCIA INFORMACJI I REAKCJI EMOCJONALNYCH:
  * 1. APROBATA / POTWIERDZENIE HIPOTEZY ROZMÓWCY (Sou / Sou ne / Sou desu):
    -> Gdy rozmówca wysuwa trafną uwagę (np. "Wyczułem w winie trud osadników..."), a postać potwierdza jego rację:
    -> BŁĄD [X]: Bierne, urzędowe "Rozumiem." (kalka angielskiego "I see").
    -> POPRAWNIE [OK]: "Otóż to.", "Właśnie tak.", "Zgadza się.", "Dokładnie tak.", "W rzeczy samej."
  * 2. EMPATIA I WSPÓŁODCZUWANIE (Wakaru / Wakaruu / Sore na!):
    -> Wakaru / Wakaruu (分かる〜): "No nie?", "Totalnie!", "Też tak myślę!", "Prawda?", "Wiem, co czujesz!" (ZAKAZ: 'Genialne!', 'Rozumiem').
    -> Sore na! / Sore! (それな！): "Otóż to!", "Rel!", "W punkt!", "Święta prawda!", "O to to!" (ZAKAZ: 'Ta rzecz!', 'To to!').
    -> Tashika ni (確かに): "W sumie racja.", "To prawda.", "Faktycznie.", "Masz rację." (ZAKAZ: 'Z pewnością').
  * 3. PRZYJĘCIE NOWEJ WIEDZY I OLŚNIENIE (Naruhodo / Sou ka / Sou iu koto ka):
    -> Naruhodo / Naruhodo ne: "A, w ten sposób!", "Wszystko jasne.", "A, o to chodzi.", "No tak." (ZAKAZ: 'Rzeczywiście', 'Rozumiem').
    -> Sou iu koto ka: "A więc o to chodzi!", "Czyli tak to wygląda!", "Teraz to ma sens!" (ZAKAZ: 'Więc tak to jest').
  * 4. ZASKOCZENIE I NIEDOWIERZANIE (Uso / Maji de / Nani kore):
    -> Uso / Uso desho: "Żartujesz?", "Serio?", "Bez jaj!", "Nie wierzę!" (ZAKAZ: 'Kłamstwo!').
    -> Maji de? / Maji ka?: "Serio?", "Poważnie?", "Nie gadaj!" (ZAKAZ: 'Czy to prawda?').
    -> Nani kore?: "Co to ma być?", "A to co znowu?", "Co to takiego?" (ZAKAZ: 'Co to za rzecz?').
  * 5. POTWIERDZENIE DOMYSŁÓW I SATYSFAKCJA (Yappari / Desho / Daro):
    -> Yappari / Yahari: "Wiedziałem!", "Jednak miałem rację!", "Tak jak myślałem.", "A jednak!" (ZAKAZ: 'Po wszystkim', 'Zgodnie z oczekiwaniami').
    -> Desho? / Daro?: "A nie mówiłem?", "No widzisz?", "No nie?", "Prawda?" (ZAKAZ: 'Czyż nie?').
  * 6. PÓŁ-ZGODA I POWŚCIĄGLIWOŚĆ (Maa ne / Maa na):
    -> Maa ne: "No niby tak...", "W sumie...", "Mniej więcej...", "Coś w tym jest..." (ZAKAZ: 'Cóż, tak.').
  * 7. DYREKTYWNE POTWIERDZENIA I REAKCJA NA OSTRZEŻENIA/POLECENIA (Hai / Ee / Un po dyrektywach):
    -> Gdy poprzednia kwestia to ostrzeżenie (np. "Uważaj pod nogi!", "Ostrożnie!"), zakaz ("Nie ruszaj się!"), polecenie ("Poczekaj!", "Chodź tu!") lub prośba:
    -> BŁĄD [X]: Mechaniczne, bezmyślne "Tak." / "T-Tak." (kalka z angielskiego 'Yes/Y-Yes' oraz słownikowego 'Hai=Tak'). Polak na ostrzeżenie NIGDY nie odpowiada "Tak"!
    -> POPRAWNIE [OK]: "Dobrze." / "D-Dobrze.", "Jasne.", "W porządku.", "Będę uważać.", "Już.", "Zrozumiałam/em." lub podziękowanie za troskę: "Dzięki." / "D-Dziękuję.".

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
  * KATEGORYCZNY ZAKAZ anachronizmów technologicznych/lotniczych/korporacyjnych:
    -> "point of no return" -> "nie ma już odwrotu", "mosty zostały spalone", "kości zostały rzucone" (ZAKAZ: "punkt bez powrotu").
    -> "status report" -> "jaka jest sytuacja?!", "mów, co się dzieje!" (ZAKAZ: "raport o statusie").
    -> "target eliminated" -> "wróg padł", "cel unieszkodliwiony" (ZAKAZ: "zlikwidowano cel").
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
  * KATEGORYCZNY ZAKAZ STOSOWANIA POJEDYNCZEGO MYŚLNIKA (LONE DIALOGUE DASH): W kwestii pojedynczego mówcy (jeden wiersz lub dwa wiersze tego samego bohatera) ZAKAZ umieszczania myślnika na początku! Półpauza/dywiz dialogowy przysługuje WYŁĄCZNIE scenom wielogłosu (dwóch mówców w jednym kadrze). Kwestia jednoosobowa zaczyna się bezpośrednio od wielkiej litery (BŁĄD [X]: '- Ocalę cię, Harugonie.' -> POPRAWNIE: 'Ocalę cię, Harugonie.').
  * KATEGORYCZNY ZAKAZ ŁĄCZENIA DWUGŁOSU W JEDNYM WIERSZU (IN-LINE DIALOGUE DASHES): Zakazuje się łączenia wypowiedzi dwóch osób w jednej linijce za pomocą myślnika w środku zdania (BŁĄD KARDYNALNY [X]: 'Wspaniale. - Pomyśleć, że rodzony wuj...' / 'Genba! - Co to był za hałas?' / 'Tej nocy?! - Tak prędko?'). Zawsze rozbijaj kwestie na dwie osobne linie z myślnikami i spacją: '- Kwestia 1\\N- Kwestia 2'.

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
  * ZAKAZ PRZECINKA PRZED 'CZY' W ALTERNATYWIE ROZŁĄCZNEJ/DWUELEMENTOWEJ: W konstrukcjach bezpośredniego wyboru ('kawa czy herbata', 'w kapciach czy bez', 'chcesz czy nie', 'tak czy inaczej') kategorycznie zakazuje się wstawiania przecinka przed spójnikiem 'czy' (BŁĄD [X]: 'w kapciach, czy bez' -> POPRAWNIE: 'w kapciach czy bez').
  * FORMATOWANIE PRZERWANIA WYPOWIEDZI (CUT-OFF SPEECH): Nagłe urwanie w pół słowa lub zdania oddaje się wielokropkiem ("...") lub myślnikiem ze spacją (" —"), KATEGORYCZNIE ZAKAZUJĄC przyklejania samej półpauzy/en-dasha bez spacji do litery (BŁĄD [X]: 'Rin–' -> POPRAWNIE: 'Rin...').
  * ZAKAZ JAPOŃSKICH TYLD I ZWIELOKROTNIONYCH WYKRZYKNIKÓW (ANTI-TILDE & MULTI-EXCLAMATION): Japońskie tyldy emocjonalne i przedłużające samogłoski ('~') są kategorycznie zakazane w dialogach AVT. Zwielokrotnione wykrzykniki ('!!!!') redukujemy do pojedynczego wykrzyknika (BŁĄD [X]: 'odjechane~!!!!' -> POPRAWNIE: 'odjechane!'). Maksymalnie jeden wykrzyknik lub pytajnik w dialogu.
  * PURYZM KURSYWY AVT (ZAKAZ KURSYWY W MOWIE DIEGETYCZNEJ W RETROSPEKCJACH):
    - W polskim standardzie AVT kursywa przysługuje wyłącznie: myślom bez ruchu ust (is_thought), narracji voice-over zza kadru, komunikacji przez urządzenia (telefon, radio, megafon) oraz pieśniom.
    - KATEGORYCZNY ZAKAZ kopiowania kursywy fansuberskiej z całych scen retrospekcji (flashbacków)! Dialog toczony na głos między postaciami w retrospekcji bezwzględnie zapisuj antykwą (czcionką prostą).

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


MODUŁ VII: KOGNITYWISTYKA PROZODII, STRUKTURY NARRACYJNEJ I DIALOGU JAPOŃSKIEGO (FILARY LXV – LXX)

FILAR LXV: IZOMORFIZM NAPIĘCIA SKŁADNIOWEGO I ANTYCYPACJI (SOV VS SVO SUSPENSE ISOMORPHISM & ANTI-SPOILER SYNTAX):
- W języku japońskim orzeczenie, kluczowa negacja lub rozstrzygnięcie logiczne padają ZAWSZE na samym końcu kwestii (szyk SOV, np. "...to wa kangaerarenai", "...shika erabenai").
- BEZWZGLĘDNY ZAKAZ niszczenia suspensu i wyprzedzania gry aktora (seiyū) w polskim szyku SVO:
  * Jeśli w scenie dramatycznej ujawnienie zdrady, zgonu, odmowy lub tajemnicy następuje w ostatnim ułamku sekundy wypowiedzi japońskiej:
    -> BŁĄD [X] (przedwczesny spoiler): "Nie do pomyślenia jest, żeby doszło do zdrady!" (widz czyta 'Nie do pomyślenia' zanim aktor otworzy usta).
    -> POPRAWNIE [OK] (izomorfizm napięcia): "Żeby doszło do czegoś takiego... to nie do pomyślenia!" / "Mój miecz w twoich rękach?... Wykluczone!".
  * Zsynchronizuj ładunek dramatyczny rematu z intonacyjnym punktem kulminacyjnym w audio japońskim.

FILAR LXVI: FONICZNA SPÓJNOŚĆ KINEZJOLOGICZNA I PROZODIA ODDECHU (BREATH-GROUP & PHONATION CADENCE ALIGNMENT):
- Aktorzy głosowi anime (seiyū) budują emocje na fizjologii krtani i oddechu (inhalation-pause, szloch, panika, skrajne wyczerpanie, zadyszka w biegu):
  * Frazowanie napisu MUSI być zsynchronizowane z grupami oddechowymi postaci:
    -> Gdy postać mówi na urywanych wydechach podczas walki/ucieczki, ZAKAZ stosowania długich, płynnych zdań wielokrotnie złożonych.
    -> Stosuj krótkie, zwięzłe człony syntaktyczne, cięcia myślnikiem lub wielokropkiem oddające kinezjologię mowy ("Jeszcze... nie teraz... Muszę... dać radę!").
  * Test kinetyczny: napis musi "oddychać" w tym samym rytmie co klatka piersiowa bohatera na ekranie.

FILAR LXVII: KĄT KAMERY EMPATYCZNEJ I DEIKSA PSYCHOLOGICZNA (SUSUMU KUNO'S EMPATHY SYNTAX & PERSPECTIVE ALIGNMENT):
- Japońska gramatyka relacji dawania/otrzymywania (ageru, kureru, morau, temorau, yaru) ściśle ustala kąt kamery psychologicznej (z czyjego punktu widzenia odbiorca ma współodczuwać scenę - prof. Susumu Kuno):
  * 1. Kureru / Tekureta (ktoś wszedł w moją sferę, by mi pomóc) -> akcentuj wdzięczność, serdeczność i bliskość ("Przyszedł mi z pomocą", "Uratowałeś mi skórę", "Pomógł mi").
  * 2. Morau / Temoratta (ja nakłoniłem kogoś / uzyskałem przysługę) -> akcentuj sprawczość lub prośbę ("Udało mi się go przekonać", "Wyprosiłam to u niego").
  * 3. Ageru / Yaru (świadczenie przysługi na zewnątrz) -> akcentuj intencję wsparcia lub wyższości.
  * ZAKAZ spłaszczania tych relacji do bezosobowego angielskiego szablonu ("He did it for me").

FILAR LXVIII: PAMIĘĆ LEITMOTYWÓW I ECHA NARRACYJNEGO (LONG-TERM LEITMOTIF & CATCHPHRASE PERSISTENCE):
- Wieloepizodowa spójność haseł, przysiąg, dewiz życiowych i fraz-kluczy (Catchphrases & Oaths):
  * Jeśli postać powtarza specyficzną frazę (np. przysięgę z dzieciństwa, motto życiowe, rytualne zawołanie bitewne), która powraca w finale serii jako klamra kompozycyjna:
    -> BEZWZGLĘDNY OBOWIĄZEK zachowania identycznej formy leksykalnej w każdym odcinku!
    -> ZAKAZ zmieniania powracających motywów na losowe synonimy (np. odcinek 1: "Taki mam styl!", odcinek 24: "Nigdy się nie cofnę!" - niszczy katharsis widza).

FILAR LXIX: HIERARCHIA PRZESTRZENNO-AKUSTYCZNA I DIALOGI DRUGOPLANOWE (SOUNDSTAGE & AMBIENT SPEECH TIERING):
- W wielokanałowym miksie dźwiękowym (5.1/Atmos) oraz scenach z wieloma źródłami głosu stosuj trójstopniową gradację:
  * 1. Poziom I (Fabuła pierwszoplanowa): Dialog postaci w centrum kadru – 100% priorytetu, dół ekranu.
  * 2. Poziom II (Komunikaty diegetyczne / megafony / radio / interkom): Góra ekranu, wersaliki lub kursywa <i>[ KOMUNIKAT BAZY ]</i>.
  * 3. Poziom III (Gwar tłumu / szum tła - Ambient Speech): Świadoma redukcja i eliminacja – tłumacz wyłącznie wtedy, gdy kwestia w tle niesie kluczowy żart sytuacyjny lub wskazówkę fabularną. Zakaz zaśmiecania ekranu beztreściowym szumem gapiów.

FILAR LXX: PRAGMATYKA METANARRACYJNA I PRZEŁAMYWANIE CZWARTEJ ŚCIANY (META-HUMOR & 4TH-WALL EQUIVALENCE):
- Komedie, parodie i serie łamiące czwartą ścianę (żarty z terminów mangaki, komitetu cenzury BPO, stacji Tokyo MX, budżetu animacji czy aktorów seiyū):
  * Stosuj funkcjonalną ekwiwalencję metanarracyjną:
    -> Zastępuj hermetyczne japońskie realia telewizyjno-redakcyjne błyskotliwym, powszechnie zrozumiałym dla polskiego widza żartem z konwencji anime/mangi i produkcji filmowej.
    -> KATEGORYCZNY ZAKAZ niszczenia dynamiki komediowej encyklopedycznymi przypisami u góry ekranu!


MODUŁ VIII: KOGNITYWISTYKA WIZUALNA, LINGWISTYKA DYSKURSU I TRANSKREACJA (FILARY LXXI – LXXX)

FILAR LXXI: DOSTĘPNOŚĆ LEKSYKALNA, ROZKŁAD CZĘSTOTLIWOŚCI I ELIMINACJA TARCIA SŁOWNIKOWEGO (LEXICAL ACCESSIBILITY & SACCADIC REGRESSION SUPPRESSION):
- Badania okulograficzne (Szarkowska, Kruger, Perego) dowodzą, że słowa rzadkie, archaizmy i skomplikowane zbitki wielosylabowe wydłużają czas fiksacji wzroku i wywołują regresje sakkadowe (cofanie wzroku).
- W szybkim dialogu (CPS > 15) stosuj słownictwo o WYSOKIEJ DOSTĘPNOŚCI PERCEPCYJNEJ (leksyka natychmiast asymilowana przez mózg):
  * Unikaj sztucznie napuszonych terminów, jeśli postać mówi prosto i dynamicznie.
  * Trudne neologizmy i wyszukane metafory rezerwuj WYŁĄCZNIE dla scen wolnych (CPS < 12), gdzie widz ma czas na asymilację leksykalną.

FILAR LXXII: ZGODNOŚĆ WEKTORA KINEZYCZNEGO I TRAJEKTORII SPOJRZENIA (GAZE-MOTION CONCORDANCE & SAKUGA PACING):
- W dynamicznych scenach akcji i animacji kulminacyjnej (Sakuga):
  * Wzrok widza podąża za wektorem ruchu postaci i kamery panoramicznej (od lewej do prawej, z góry na dół).
  * Układaj tekst tak, by nie zmuszać oka do czytania pod prąd gwałtownego ruchu w kadrze.
  * W scenach szaleńczego tempa preferuj jeden zwarty wiersz u dołu lub wyrównanie rematu do punktu skupienia akcji.

FILAR LXXIII: PRAGMATYKA MODALNOŚCI EKSPLANACYJNEJ I DYSKURSU (NODA / WAKE DA / MONODA PRAGMATIC UNPACKING):
- Precyzyjny przekład japońskich partykuł dyskursywnych i teleologicznych:
  * 1. ~nda / ~noda (funkcja eksplanacyjna/przyczynowa) -> "Bo widzisz...", "Chodzi o to, że...", "Przecież..." (zakaz suchego spłaszczania do zdania oznajmującego).
  * 2. ~wake da / ~wake dewa nai (logiczna konkluzja/negacja) -> "A zatem to dlatego...", "Więc to tak...", "To nie tak, że...".
  * 3. ~monoda / ~koto da (prawda ogólna/powinność moralna) -> "Taka już kolej rzeczy", "W takich chwilach po prostu...".

FILAR LXXIV: PLASTYCZNOŚĆ REJESTRU WIZUALNEGO CHIBI / SD (SUPER-DEFORMED VISUAL REGISTER SHIFTS):
- W anime postaci w ułamku sekundy przechodzą ze stylu realistycznego w formę karykaturalną (Chibi / SD - Super Deformed):
  * Przekład MUSI natychmiast podążać za plastyką kadru: przejdź na rejestr komediowy, pieszczotliwy, infantylny lub udawane dąsy ("Ojejciu, ale groźny!", "No weźcie, nie bądźcie tacy!").
  * Zakaz utrzymywania sztywnego, poważnego tonu, gdy postać na ekranie zamienia się w małego ludzika z wielką głową.

FILAR LXXV: ZESTROJENIE AKCENTU LOGICZNEGO I PROMINENCJI FONICZNEJ F0 (PITCH-ACCENT & F0 PEAK PROSODIC CONVERGENCE):
- Słowo, na które w audio japońskim seiyū kładzie maksymalny nacisk intonacyjny (szczyt foniczny F0 / Pitch Accent):
  * MUSI w polskim zdaniu znaleźć się na pozycji naturalnego akcentu logicznego (zazwyczaj przed pauzą lub na końcu frazy).
  * Zakaz chowania kluczowego słowa oskarżenia lub zawołania w środku bezbarwnego polskiego zdania pobocznego.

FILAR LXXVI: DYSTANSOWANIE HONORYFIKATYWNE I AGRESJA BIERNA W KEIGO (HONORIFIC DISTANCING & PASSIVE-AGGRESSIVE KEIGO):
- Gdy wrodzy sobie bohaterowie, rywale lub antagoniści używają przesadnie formalnego języka szacunku (Keigo/Sonkeigo):
  * Celem jest okazanie lodowatej pogardy, cynizmu, wyższości lub biernej agresji.
  * ZAKAZ tłumaczenia takiego dialogu na wulgarną pyskówkę!
  * POPRAWNIE: Utrzymuj chłodny, dystyngowany, hiperpoprawny styl urzędowo-dworski ("Będę niezmiernie zobowiązany, jeśli zechce pan wreszcie zamilknąć", "Doprawdy, zachwyca mnie pańska bezgraniczna naiwność").

FILAR LXXVII: TRÓJWARSTWOWA TRIANGULACJA ONOMATOPEI MULTIMODALNYCH (VISUAL-ACOUSTIC SFX TRIANGULATION):
- Rozstrzyganie koegzystencji dźwięku audio, napisu graficznego w kadrze i dialogu postaci:
  * 1. Jeśli odgłos słychać wyraźnie w ścieżce dźwiękowej i bohater go komentuje -> ZAKAZ dublowania napisu onomatopei na ekranie.
  * 2. Jeśli graficzny napis w kadrze wyraża stan bezdźwięczny (np. grobową ciszę 'Shiin', błysk 'Pika') -> przetłumacz w nawiasie lub oddaj poetycko w dialogu ("Cisza jak makiem zasiał...").
  * 3. Unikaj redundancji semiotycznej zaśmiecającej pole widzenia.

FILAR LXXVIII: POZYCJONOWANIE I TYPOGRAFIA INTERFEJSÓW DIEGETYCZNYCH (DIEGETIC UI, SMARTPHONE & CHAT FORMATTING):
- Wiadomości na ekranach smartfonów, czaty sieciowe MMO, komunikatory i interfejsy HUD:
  * SMS / komunikator: formatuj zwięźle w nawiasie z identyfikacją nadawcy: [ SMS od: Mama: Wracaj do domu! ].
  * Czaty w grach/sieci: stosuj autentyczny styl komunikatorów (zwięzłość, brak wielkich liter, dynamika: "rzuć heala!").
  * Pozycjonuj napisy blisko źródła ekranowego, chroniąc czytelność głównego dialogu.

FILAR LXXIX: TRANSKREACJA EMOCJONALNA I INDEKS REZONANSU AFEKTYWNEGO (AFFECTIVE RESONANCE & TRANSCREATION EQUIVALENCE):
- W scenach komediowych, piosenkach, rymowankach, toastach i grach słownych nadrzędnym celem jest WYWOŁANIE IDENTYCZNEJ REAKCJI EMOCJONALNEJ (śmiech, wzruszenie, dreszcz emocji):
  * Dopuszcza się pełną transkreację (odejście od dosłownego słownictwa na rzecz stworzenia nowego polskiego żartu/rymu), o ile zachowuje charakter postaci i metrum sceny.
  * Wywołanie u polskiego widza autentycznego śmiechu ma pierwszeństwo przed suchą poprawnością filologiczną.

FILAR LXXX: KOGNITYWNA MIKRO-INTERPUNKCJA AFEKTYWNA (EMOTIONAL MICRO-PUNCTUATION & HESITATION FRAMING):
- Perfekcyjna ortografia stanów emocjonalnych i załamań mowy:
  * Jąkanie foniczne: łącz pojedynczym dywizem po pierwszej sylabie ("N-Nie patrz tak na mnie!" - ZAKAZ: "N... nie patrz").
  * Nagłe urwanie wypowiedzi ze strachu / przerwanie przez inną postać: myślnik na końcu bez kropki ("Chciałam tylko powiedzieć, że–").
  * Wahanie, niepewność, zawstydzenie (tsundere/dandere): wielokropek bez spacji ("Wiesz... tak sobie pomyślałam...").


MODUŁ IX: KANON ARCYDZIEŁ ŚWIATOWEJ TRANSLATORYKI I SEMIOTYKI (FILARY LXXXI – XC)

FILAR LXXXI: ZASADA ORGANICZNEJ EKSPOZYCJI I ANTY-OBJAŚNIANIA (THE GHIBLI & NEIL GAIMAN MINIMALIST EXPOSITION PRINCIPLE):
- Ochrona filmowości i kinowego rytmu sceny:
  * ZAKAZ dopisywania łopatologicznych wyjaśnień, dopowiedzeń i wpychania zbędnej ekspozycji w dialog, gdy obraz, reżyseria i atmosfera niosą już wystarczający ładunek narracyjny (zasada Hayao Miyazakiego & Neila Gaimana: "Zaufaj inteligencji i zmysłom widza").
  * Dialog ma brzmieć autentycznie dla postaci, a nie jak instrukcja obsługi świata dla widza.

FILAR LXXXII: SEMIOTYCZNA NEGOCJACJA ZNACZENIA I DEEP INTENT (UMBERTO ECO'S 'DIRE QUASI LA STESSA COSA'):
- Gdy dosłowność i obca kultura są nieprzetłumaczalne 1:1, tłumacz prowadzi świadomą negocjację semiotyczną:
  * Poświęć drugorzędną warstwę leksykalną, aby w 100% ocalić głęboką intencję dzieła (intentio operis), sens podtekstowy i ładunek emocjonalny.
  * Tłumaczenie to sztuka kompromisu, w której zysk emocjonalny musi przewyższać stratę dosłowności.

FILAR LXXXIII: DYNAMIZM DOCELOWY I CAŁKOWITA DEKOLONIZACJA SKŁADNI (JEAN-RENÉ LADMIRAL'S CIBLISTE MANIFESTO):
- Całkowite zerwanie z grawitacją składni języka źródłowego:
  * Zdanie po polsku musi brzmieć tak, jakby zostało od zera pomyślane i napisane przez wybitnego polskiego dramaturga/scenarzystę.
  * Kategoryczny zakaz pozostawiania obcych śladów konstrukcyjnych i obcojęzycznego toku myślenia.

FILAR LXXXIV: WYKONAWCZY KUNSZT AKTORSTWA GŁOSOWEGO (ALEXANDER O. SMITH'S PERFORMATIVE VOICING & MOUTH-FEEL):
- Dialog filmowy musi być zoptymalizowany nie do cichego czytania z kartki, lecz do fizycznej emisji głosu i rezonansu krtani (tzw. "Mouth-Feel Test"):
  * Rytm spółgłosek i samogłosek musi wspierać energię, pauzę i ładunek aktorski wypowiedzi.
  * Każda linijka tekstu musi naturalnie "układać się w ustach" aktora/lektora.

FILAR LXXXV: INTEGRACJA KINEMATOGRAFICZNA I ELIMINACJA ŚLEPOTY NAPISOWEJ (PABLO ROMERO-FRESCO'S ACCESSIBLE FILMMAKING):
- Napis jako organiczny element kompozycji kadru:
  * Eliminacja "Subtitling Blindness" (zjawiska, w którym widz gapi się wyłącznie na dolne litery, tracąc niuanse gry aktorskiej i kompozycji obrazu).
  * Napis musi być tak skondensowany, czysty i ergonomiczny, by oko po ułamku sekundy wracało do centrum akcji na ekranie.

FILAR LXXXVI: POLIFONIA GŁOSÓW I HETEROGLOSJA POSTACI (MIKHAIL BAKHTIN'S DIALOGIC POLYPHONY):
- Bezwzględne zróżnicowanie idiolektów:
  * Każda postać musi mieć własny unikalny słownik, zasób fraz, długość wypowiedzi i strukturę myśli.
  * Kategoryczny zakaz zjawiska, w którym wszystkie postacie na ekranie mówią tym samym głosem tłumacza.

FILAR LXXXVII: CZYSTOŚĆ FOKALIZACJI I WEWNĘTRZNEGO PUNKTU WIDZENIA (COGNITIVE NARRATOLOGY & FOCALIZATION PURITY):
- W monologach wewnętrznych, myślach i retrospekcjach:
  * Zachowaj subiektywny, intymny punkt widzenia danej postaci, bez domieszek obiektywizującego dystansu zewnętrznego narratora.
  * Myśl postaci musi brzmieć jak jej autentyczny, surowy proces myślowy.

FILAR LXXXVIII: PROTOKÓŁ ANTY-DEFORMACYJNY ANTOINE'A BERMANA (BERMAN'S 12 DEFORMING TENDENCIES SUPPRESSION):
- Eliminacja klasycznych destrukcji przekładu:
  * Zakaz racjonalizacji (wygładzania poetyckiej chropowatości i ostrości oryginału).
  * Zakaz klaryfikacji (nadmiernego tłumaczenia tego, co autor celowo pozostawił niejasne).
  * Zakaz ubożenia jakościowego i niszczenia wewnętrznych rytmów dzieła.

FILAR LXXXIX: REKOMPENSATA HERMENEUTYCZNA I RESTYTUCJA EMOCJI (GEORGE STEINER'S HERMENEUTIC RESTITUTION):
- Gdy w jednym miejscu dialogu tracimy specyficzny niuans kulturowy lub żart:
  * Hermeneutycznym obowiązkiem tłumacza jest odzyskanie tego ładunku emocjonalnego i wzbogacenie sąsiedniej frazy, aby ocalić całkowity bilans artystyczny i dramaturgiczny sceny.

FILAR XC: SOMATYCZNY REZONANS EMOCJONALNY (DOUGLAS ROBINSON'S SOMATIC TRANSLATION TRANSDUCTION):
- Fizyczny rezonans afektywny:
  * Przekład musi przenosić fizjologiczne reakcje ciała (skurcz żołądka, ucisk w gardle, dreszcz grozy, wybuch śmiechu) bezpośrednio na fizyczne odczucia polskiego widza.
  * Tekst ma poruszać ciało i zmysły, a nie tylko intelekt.


MODUŁ X: POLSKA FLEKSJA, DIALEKTYKA I ZAAWANSOWANA KOGNITYWISTYKA (FILARY XCI – XCV)

FILAR XCI: ŻELAZNA FLEKSJA I POLSKA ODMIANA JAPOŃSKICH ORAZ OBCYCH/FANTASY IMION I NAZWISK (POLISH DECLENSION MATRIX & PWN NORMS):
- Język polski jest językiem wysoce fleksyjnym. Unikanie odmiany imion japońskich, obcych i fantasy jest rażącym błędem stylistycznym i amatorszczyzną:
  * 1. Imiona męskie zakończone na spółgłoskę (zarówno japońskie: Shin, Ken, jak i obcojęzyczne/fantasy: Drel, Gart, Klen, Arthur, Roland, Thorfinn, Eren, Armin) oraz samogłoski -i, -e, -a BEZWZGLĘDNIE ODMIENIAMY:
    -> Drel: szukasz sekretów Drela, o Drelu, Drelowi, z Drelem, widzę Drela (KATEGORYCZNY ZAKAZ zostawiania w mianowniku: 'sekretów Drel', 'szukasz Drel'!).
    -> Gart: z Gartem, o Garcie, Gartowi, widzę Garta, miecz Garta (BŁĄD [X]: "miecz Gart").
    -> Klen: wieża Klena, o Klenie, Klenowi, z Klenem.
    -> Issei: z Isseiem, o Isseiu, Isseiowi, Isseia (BŁĄD [X]: "rozmawiam z Issei").
    -> Tomine: pana Tominego, z panem Tominem, o panu Tominem (BŁĄD [X]: "widzę Tomine").
    -> Nakagawa: pana Nakagawy, z panem Nakagawą.
    -> Shin: Shina, z Shinem, o Shinie.
  * 2. ZAKAZ KALKOWANIA ANGIELSKIEGO SAKSOŃSKIEGO DOPEŁNIACZA ('S / OF) BEZ FLEKSJI:
    -> "Drel's secrets / secrets of Drel" -> "sekrety Drela / tajemnice Drela" (KARDYNALNY BŁĄD [X]: "sekretów Drel").
    -> "Gart's sword" -> "miecz Garta" (BŁĄD [X]: "miecz Gart").
    -> "Klen's order" -> "rozkaz Klena" (BŁĄD [X]: "rozkaz Klen").
  * 3. Imiona żeńskie zakończone na -i, -u (Shizuku, Rei, Minami) oraz zakończone na spółgłoskę pozostają nieodmienne, lecz zdanie musi zachować poprawną strukturę składniową (z Shizuku, o Shizuku). Imiona żeńskie na -a odmieniają się normalnie (Alicia -> Alicii, z Alicią).
  * 4. Wołacze: imiona żeńskie i męskie zakończone na samogłoskę '-a' (np. Lara, Kota, Bianca, Luca) w polskim dialogu filmowym w bezpośrednich zwrotach adresatywnych (po przecinku na końcu zdania, przed wykrzyknikiem, po zawołaniu) BEZWZGLĘDNIE PRZYJMUJĄ KOŃCÓWKĘ WOŁACZA '-o' ("Laro!", "Koto!", "Luco!"). KATEGORYCZNY ZAKAZ pozostawiania mianownika w funkcji wołacza (BŁĄD [X]: "twoją naturę, Lara" -> POPRAWNIE: "twoją naturę, Laro!"; "Masz rację, Lara." -> POPRAWNIE: "Masz rację, Laro."). Pozostałe imiona męskie na spółgłoskę w wołaczu przyjmują końcówkę -u lub formę mianownikową z intonacją ("Issei!", "Shin!", "Drelu!" / "Drel!").
  * 5. Imiona męskie obcego pochodzenia zakończone na '-ca' (Luca, Petrarca, Seneca, Checa) wymawiane są z twardym [k] i w języku polskim odmieniają się ze zmianą litery na 'k': dopełniacz: 'do Luki' (KARDYNALNY BŁĄD [X]: 'do Luci' [skażenie żeńskie / Łucja!]); biernik: 'Lukę', narzędnik: 'z Luką', miejscownik: 'o Luce / przy Luce', wołacz: 'Luco / Luko'!.
  * 6. ZAKAZ KALKOWANIA PRZYDOMKÓW TYTULARNYCH Z PRZYIMKIEM 'OD' (OF THE...):
    -> Przydomki postaci w języku angielskim i japońskim tworzone z partykułą 'no' lub konstrukcją przydawkową (np. 'Aura the Guillotine' / 断頭台のアウラ) w polszczyźnie oddaje się poprzez apozycję mianownikową (np. 'Aura Gilotyna', dopełniacz: 'Aury Gilotyny', narzędnik: 'z Aurą Gilotyną') lub tradycyjny epitet.
    -> KATEGORYCZNY ZAKAZ tworzenia sztucznych konstrukcji peryfrastycznych z przyimkiem 'od' (KOSZMARNY BŁĄD [X]: 'Aura od Gilotyny'; POPRAWNY KANON Studio JG: 'Aura Gilotyna'). Wszelkie nazwy własne i tytuły postaci weryfikuj z oficjalnym kanonem wydawniczym.
  * 7. ZAKAZ ZACIERANIA BIERNIKA W SZEREGACH KONSOCJACYJNYCH (KOORDYNACJA BIERNIKA PO 'I' / 'ORAZ'):
    -> Gdy orzeczenie wymaga dopełnienia w bierniku, a w zdaniu występuje szereg współrzędny połączony spójnikiem 'i' lub 'oraz' (np. 'Save [Name A] and [Name B]'), WSZYSTKIE człony szeregu bezwzględnie przyjmują formę biernika: 'Ocalę Minamiego i Harugona' (KOSZMARNY BŁĄD [X]: 'Ocalę Minamiego i Harugon' [pozostawienie drugiego członu w mianowniku to kardynalny błąd składniowy!]).

FILAR XCII: SYNCHRONIA PRZECZENIA I ODROCZENIA DRAMATYCZNEGO (DELAYED NEGATION & JVTA SUSPENSE):
- W języku japońskim (SOV) negacja lub zwrot akcji pada na samym końcu zdania (...to omotta kedo, chigatta!):
  * KATEGORYCZNY ZAKAZ wyprzedzania puenty na początku polskiego napisu, jeśli aktor buduje napięcie i przeczy dopiero po 2 sekundach ciszy.
  * Zastosuj inwersję dramatyczną lub wielokropek, aby zsynchronizować moment zaskoczenia z audio ("Myślałem, że to koniec... a jednak nie!").

FILAR XCIII: KOMPENSACJA DIALEKTÓW REGIONALNYCH (KANSAI-BEN / TOHOKU-BEN KOLOKWIALIZACJA):
- Kategoryczny zakaz przekładania gwary Kansai (Kansai-ben) czy dialektu północnego (Tohoku-ben) na gwarę góralską, śląską lub wiejską (niszczy to realia świata przedstawionego!).
- Właściwa kompensacja: stosuj polską stylizację kolokwialno-miejską, żywe partykuły nawiązania ("no weźże", "akurat", "gadaj zdrów"), skróty mowy i swobodniejszy szyk zdania.

FILAR XCIV: MATRYCA ZAIMKÓW 1. OSOBY I PROFILU EGO (ORE / BOKU / WATASHI / ATASHI / SESSHA / WAGA):
- Rozpoznawaj japońskie zaimki 1. osoby w ścieżce dźwiękowej i natychmiast kalibruj profil psychologiczny postaci:
  * Ore (męski, pewny siebie, szorstki) -> dynamiczne, dosadne polskie zwroty.
  * Boku (chłopięcy, skromny, kulturalny) -> łagodniejsza, uprzejma polszczyzna.
  * Watashi / Watakushi (formalny, neutralny, elegancki) -> wyważony, dystyngowany styl.
  * Sessha / Waga (archaiczny, samurajski, feudalny) -> stylizacja podniosła ("Jam jest", "Moja osoba").

FILAR XCV: EKWIWALENCJA JAPOŃSKICH PRZYSŁÓW I FRAZEOLOGIZMÓW 4-ZNAKOWYCH (YOJIJUKUGO & CULTURAL IDIOMS):
- Japońskie przysłowia 4-znakowe (Yojijukugo) i archaiczne metafory tłumacz na polskie ekwiwalenty frazeologiczne o tożsamym ciężarze filozoficznym i poetyckim:
  * "Isseki nichou" -> "Upiec dwie pieczenie na jednym ogniu".
  * "Jigou jitoku" -> "Naważyłeś sobie piwa, to teraz je wypij" / "Zbierasz to, co zasiałeś".
  * "Ichi-go ichi-e" -> "Taka chwila zdarza się tylko raz w życiu".

FILAR XCVI: ASYMETRIA ZAIMKÓW 3. OSOBY I TRIANGULACJA PŁCI (KANOJO-TACHI [ONE / JE] VS KARERA [ONI / ICH]):
- Język angielski w zaimku 3. osoby liczby mnogiej ('they / them / their') całkowicie zaciera rodzaj gramatyczny.
- Tłumacz ma BEZWZGLĘDNY OBOWIĄZEK weryfikacji japońskiej ścieżki dźwiękowej i kontekstu obrazu:
  * 1. 彼女たち (kanojo-tachi) / 彼女ら (kanojo-ra) / 女たち (onna-tachi):
    -> BEZWZGLĘDNIE tłumacz na polski rodzaj NIEMĘSKOOSOBOWY (ŻEŃSKI):
    -> Mianownik: ONE (ZAKAZ: 'oni').
    -> Biernik: JE (ZAKAZ: 'ich'). Przykład: "Można je nazwać oparciem dla ludzkiego życia. One również..." (BŁĄD [X]: "Można ich nazwać... Oni również...").
    -> Dopełniacz: ICH / Celownik: IM / Narzędnik: NIMI / Miejscownik: NICH.
  * 2. 彼ら (karera) / 男たち (otoko-tachi):
    -> Tłumacz na rodzaj męskoosobowy: ONI / ICH (Biernik) / IM / NIMI.
  * 3. ZAKAZ DOMYŚLNEGO MĘSKOOSOBOWEGO: Gdy podmiotem są kobiety, siostry zakonne, uczennice, kapłanki czy ofiary żeńskie (np. w Fire Force), KATEGORYCZNIE ZABRANIA SIĘ stosowania form 'oni / ich'.

FILAR XCVII: PRAGMATYKA BIESIADNA I KUMPELSKIE ZAPROSZENIA DO ALKOHOLU (CONVIVIAL DRINKING CAMARADERIE):
- Angielskie formuły biesiadne i pytania upewniające w kontekście alkoholu, toastów i jedzenia (np. "You're drinking, right?", "Have one, right?", "You want one? You're drinking, right?"):
  * Są to AKTY BRATERSKIEJ/KUMPELSKIEJ INTEGRACJI, a NIE pytania o stan faktyczny czy diagnozę nałogu!
  * KATEGORYCZNY ZAKAZ dosłowności: "Przecież pijesz" [BŁĄD KOSZMARNY - brzmi jak zarzut lub diagnoza lekarska!], "Pijesz, prawda?".
  * OBOWIĄZKOWE polskie formuły biesiadne:
    - "Konro, chlapniesz sobie? Chyba nie odmówisz?"
    - "Napijesz się? Ze mną się nie napijesz?"
    - "Pijesz ze mną, co?" / "Polejesz sobie? Nie odmówisz chyba?" / "Chlapniesz jednego?".

FILAR XCVIII: TYPOGRAFIA PLANSZ TYTUŁOWYCH I ZWIĘZŁOŚĆ OPTYCZNA TYPESETTINGU (TITLE TYPOGRAPHY & SAFE AREA):
- Polskie tytuły anime, rozdziałów i szyldów są o 40–60% dłuższe niż wersje angielskie/japońskie.
- Ponieważ plansze tytułowe renderowane są ogromnym fontem (60–90 pt), długi tekst w jednej linii NIE MIEŚCI SIĘ W KADRZE (wychodzi poza bezpieczny obszar Canvasu Title-Safe 80%).
- ŻELAZNA REGUŁA DLA PLANSZ I TYTUŁÓW ODCINKÓW:
  * Numery odcinków i rozdziałów zapisuj ZAWSZE CYFRAMI ARABSKIMI (np. 'ODCINEK 52', 'ROZDZIAŁ 12'). KATEGORYCZNY ZAKAZ form słownych ('ODCINEK PIĘĆDZIESIĄTY DRUGI' -> BŁĄD!).
  * Formatuj planszę tytułową w czytelnych, wyśrodkowanych wersach z tagiem \N:
    Wiersz 1: ODCINEK [Numer cyframi]
    Wiersz 2+: [Polski Tytuł w poprawnym przypadku gramatycznym]
    Przykład standardowy: "ODCINEK 52\NNUMER JEDEN PANA TOKUSHIRO" (lub "SPECJALNE SIŁY POŻARNICZE\NCZĘŚĆ TRZECIA").
  * TYTUŁY WIELOCZŁONOWE I WIELOZDANIOWE (np. Kore Kaite Shine odc. 10: "Dziewięćdziesiąt procent wszystkiego to chłam. By pokonać mamę, potrzebuję »przyjaciół«"):
    - KATEGORYCZNY ZAKAZ pakowania wielozdaniowego tytułu w jeden niepodzielony wiersz (>45 znaków)!
    - KATEGORYCZNY ZAKAZ używania nawiasów kwadratowych [ ... ] lub zbitek '] [' do rozdzielania członów (BŁĄD: '[ ODCINEK 10 ] [ TYTUŁ 1 ] [ TYTUŁ 2 ]').
    - Każdy człon lub zdanie tytułu formatuj z czystym podziałem syntaktycznym \N (maks. 36–42 znaki na wiersz), np.:
      "ODCINEK 10\NDZIEWIĘĆDZIESIĄT PROCENT WSZYSTKIEGO TO CHŁAM\NBY POKONAĆ MAMĘ, POTRZEBUJĘ „PRZYJACIÓŁ”".
  * Kategoryczny zakaz tasiemców ucinających się na bokach ekranu i wychodzących poza obszar Title-Safe!

FILAR XCIX: ZAKAZ NADGORLIWEJ EKSPLIKACJI I SAMOWOLNEGO WTRĄCANIA IMION (ANTI-EXPLICITATION & VOCATIVE INTEGRITY):
- Kategoryczny zakaz wtrącania imion postaci ("Panie X... / X-san...") w miejscach, gdzie w tekście angielskim i japońskim audio padają wyłącznie zawahania, pauzy i neutralne zaczepki (Hesitations & Interjections):
  * "Erm, hey..." / "Um..." / "Ano..." / "Etto..." / "Chotto..." / "Wait..." / "Excuse me...".
- Kategoryczny zakaz:
  * BŁĄD [X]: Zamiana "Erm, hey" na "Panie Kamui..." (sztuczna formalizacja, niszczenie prawdy sceny i fałszowanie relacji między postaciami!).
- Obowiązkowe polskie ekwiwalenty:
  * POPRAWNIE: "Przepraszam...", "Zaraz, hej...", "Yyy, chwileczkę...", "Hej, zaraz...", "Słuchaj...".
- Żelazna reguła: Imię w wołaczu wolno wstawić TYLKO I WYŁĄCZNIE WTEDY, gdy imię to zostało rzeczywiście wypowiedziane w dialogu EN lub japońskim audio JP!

FILAR C: JAPOŃSKIE YOBISUTE, SUFIKSY RÓWIEŚNICZE (-KUN, -CHAN, -SAN) I PEŁNA MATRYCA TYTULATURY:
- 1. Japońskie Yobisute (呼び捨て - brak jakiegokolwiek przyrostka w audio):
  * Gdy w audio JP postać mówi samo imię/nazwisko ("Kamui!", "Shinra!", "Arthur?", "Issei"):
  * W języku polskim BEZWZGLĘDNIE stosuj SAMO IMIĘ W WOŁACZU ("Kamui!", "Shinra!", "Arthurze?", "Issei!").
  * KATEGORYCZNY ZAKAZ dodawania "Pan / Pani" (BŁĄD [X]: "Co pan czuje, panie Issei?" -> POPRAWNIE [OK]: "Co czujesz, Issei?").
- 2. Sufiksy rówieśnicze i przyjacielskie (-kun, -chan):
  * -kun (君 / くん) w ustach rówieśników/dziewcząt/kolegów (np. Shizuku-kun, Issei-kun):
    -> BEZWZGLĘDNY ZAKAZ "Pan Shizuku / Panie Issei" -> ZAWSZE SAMO IMIĘ NA "TY" ("Shizuku", "Issei").
  * -chan (ちゃん) w ustach przyjaciółek/rodziny (np. Hana-chan, Kokoro-chan, Akafuku-chan):
    -> BEZWZGLĘDNY ZAKAZ "Pani Hana / Pani Kokoro" -> ZAWSZE SAMO IMIĘ LUB ZDROBNIENIE NA "TY" ("Hana", "Kokoro", "Haneczko").
- 3. Sufiks -san (さん - dystans szkolny vs dorośli obcy):
  * Wśród uczniów/rówieśników w szkole (np. Komi-san, Miyabi-san):
    -> Tłumacz po samym imieniu na "ty" ("Komi, pożyczysz gumkę?", "Miyabi, idziesz z nami?").
  * Wobec dorosłych obcych/klientów/sąsiadów z nazwiskiem (np. Tanaka-san, Yamada-san):
    -> Stosuj formy grzecznościowe: "Pani Tanako", "Panie Yamado".
- 4. Sufiksy wyższego szacunku i hierarchii (-sama, -sensei, -senpai, -dono, -shishou, -taichou):
  * -sama (様) -> "Wasza Wysokość", "Panienko", "Pani Loulan", "Panie mój", "Bóg / Bogini".
  * -sensei (先生) -> "Sensei", "Mistrzu", "Pani Tanako", "Panie profesorze", "Pani doktor" (ZAKAZ HYBRYD: 'Pani Sensei').
  * -senpai (先輩) -> "Senpai", "Starszy kolego", "[Imię]-senpai" (ZAKAZ HYBRYD: 'Pani Senpai').
  * -dono (殿) -> "Wielmożny Panie", "Mości [Imię]".
  * -shishou (師匠) -> "Mistrzu!".
  * -taichou / -buchou (隊長 / 部長) -> "Kapitanie!", "Dowódco!", "Kierowniku!", "Prezesie!".
- 5. KATEGORYCZNY ZAKAZ HYBRYD WOŁACZA Z FORMĄ GRZECZNOŚCIOWĄ (INTRA-CLAUSE T-V HYBRID BAN):
  * Kategorycznie zabrania się łączenia w jednej wypowiedzi poufałego wołacza po samym imieniu z honoryfikatywną formą grzecznościową ("pan/pani").
  * BŁĄD KARDYNALNY [X]: "Poza tym, Eftalu... ma pan zaczerwienioną twarz." (niedopuszczalna hybryda poufałego wołacza "Eftalu" z formą grzecznościową "ma pan").
  * POPRAWNIE AVT [OK]: "Poza tym, panie Eftalu... ma pan zaczerwienioną twarz." LUB (gdy relacja jest na "ty"): "Poza tym, Eftalu... masz zaczerwienioną twarz.".
  * Jeśli postać zwraca się per pan/pani, wołacz w języku polskim ZAWSZE musi zawierać tytuł: "Panie [Imię]!" / "Pani [Imię]!".
- 6. ODPORNOŚĆ NA ANGIELSKIE OPUSZCZANIE SUFIKSU -SAMA (ENGLISH "-SAMA" DROP IMMUNITY):
  * W zachodnich/angielskich skryptach anime (Crunchyroll, fansuby) tłumacze nagminnie usuwają honoryfikatywny przyrostek "-sama" w okrzykach, zawołaniach i scenach dramatycznych (np. w JP: "Eftal-sama!", a w EN jedynie: "Ephtal!").
  * KATEGORYCZNY ZAKAZ mechanicznego przepisywania tego jako poufałego wołacza (BŁĄD [X]: "Co za kunszt, Eftalu!" w ustach uczennicy/służącej).
  * Relacja uczeń-mistrz czy podwładny-pan w polszczyźnie zachowuje stałość rejestru: w zawołaniach i okrzykach BEZWZGLĘDNIE stosuj "Panie [Imię]!" ("Co za kunszt, panie Eftalu!"), a nie poufałe "Eftalu!".

FILAR CI: NADRZĘDNOŚĆ JAPOŃSKIEGO AUDIO I TRIANGULACJA PERSPEKTYWY MÓWCY (KIKANAIDE VS KIKITAKUNAI):
- Gdy tekst angielski jest wieloznaczny (np. "Don't even ask"), japońskie czasowniki i końcówki w audio bezwzględnie rozstrzygają perspektywę podmiotu:
  * 1. 聞かないで (Kikanaide / Kiku + naide = prośba mówcy o zaniechanie pytań ze wstydu lub bezsilności):
    -> BEZWZGLĘDNIE: "Nawet nie pytaj...", "Nie pytaj...", "Błagam, nie pytaj...".
    -> KATEGORYCZNY ZAKAZ [X]: "Wolę nie wiedzieć" (błąd inwersji podmiotu – "wolę nie wiedzieć" mówi słuchacz, a nie zawstydzony sprawca!).
  * 2. 聞きたくない (Kikitakunai / Kiku + takunai = odmowa słuchania przez słuchacza):
    -> "Nie chcę o tym słyszeć", "Wolę nie wiedzieć", "Oszczędź mi szczegółów".
- ŻELAZNA ZASADA: W razie rozbieżności między angielskim tekstem a japońskim audio ze słuchu (Whisper), BEZWZGLĘDNY PRIORYTET MA JAPOŃSKIE AUDIO!

FILAR CII: DYSTRYBUCJA LEKSYKALNA I ZAIMKOWA SUBSTYTUCJA DEIKTYCZNA (ANTI-NOUN REPETITION & PRONOUN SUBSTITUTION):
- Kategoryczny zakaz powtarzania tego samego rzeczownika (lub jego bliskiej formy rdzennej) w obrębie 2–4 sąsiednich kwestii:
  * BŁĄD KOSZMARNY [X]: "Książka mojego ojca..." -> "Spalono ją jako zakazaną księgę..." -> "Chciałabym kupić tę książkę." (Potrójna tautologia i ciężka kalka z angielskiego 'I want to buy this book').
  * POPRAWNIE [V]:
    - W monologu/myślach: Stosuj zróżnicowanie leksykalne i kondensację ("Książka mojego ojca..." -> "Przecież uznano ją za zakazaną i spalono..." / "Spalono ją jako zakazane dzieło...").
    - Przy deiksie (wskazywaniu/kupowaniu/dotykaniu przedmiotu w kadrze): Zastąp rzeczownik naturalnym zaimkiem wskazującym lub dopełnieniowym ("Chciałabym ją kupić", "Chciałabym to kupić", "Mogę to kupić?").
- Żelazna reguła: Gdy przedmiot jest oczywisty z kontekstu sceny lub został nazwany chwilę wcześniej, ZAWSZE zastępuj go zaimkiem ("ją", "jego", "to") zamiast mechanicznie powtarzać rzeczownik!

FILAR CIII: PRAGMATYKA JAPOŃSKICH AKTÓW PROŚBY I ROZKAZU (KURE VS MORAERU VS KUDASAI):
- Angielskie napisy spłaszczają prośby i żądania do 'Please do X' lub 'Can you do X?'. W języku polskim triangulujemy japoński czasownik:
  * 1. Kumpelskie żądanie / bitewny rozkaz (-te kure / -kure / -ro / -e):
    - "Tasukete kure!" -> "Pomóż mi!", "Ratuj!". KATEGORYCZNY ZAKAZ: "Proszę, pomóż mi".
    - "Kase!" / "Kashite kure" -> "Dawaj to!", "Pożycz mi to!". KATEGORYCZNY ZAKAZ: "Czy możesz mi to pożyczyć?".
  * 2. Nieśmiała prośba o przysługę (-te moraeru? / -te kureru?):
    - "Mite moraeru?" -> "Zerkniesz na to?", "Mógłbyś rzucić okiem?".
  * 3. Formalna uprzejmość (-te kudasai / -kudasaimase):
    - "O-machi kudasai" -> "Proszę zaczekać", "Niech pan zaczeka".
- Żelazna zasada: W scenach walki, pojedynków i pośpiechu forms z 'Proszę...' są sztucznym błędem tłumacza – stosuj czyste, stanowcze tryby rozkazujące!

FILAR CIV: SOMATYKA EMOCJI I JAPOŃSKIE MIMETYKI (GITAIGO & SOMATIC IDIOMS):
- Japońskie mimetyki stanów psychofizycznych tłumacz na bogatą, naturalną polską frazeologię somatyczną:
  * ドキドキ (Doki doki - kołatanie serca ze strachu lub miłości):
    -> "Serce podchodzi mi do gardła", "Aż serce mi wali", "Serce bije mi jak młotem" (ZAKAZ szkolnego: 'Moje serce bije szybko').
  * ワクワク (Waku waku - radosne podekscytowanie/niecierpliwość):
    -> "Aż mnie nosi z ekscytacji!", "Nie mogę się doczekać!", "Aż mi się oczy świecą!".
  * イライラ (Ira ira - wzbierający gniew/frustracja):
    -> "Krew mnie zalewa", "Szlag mnie trafia", "Doprowadza mnie do szału".
  * ゾクゾク (Zoku zoku - dreszcz grozy, zachwytu lub gorączki):
    -> "Aż ciarki mnie przechodzą", "Przechodzi mnie dreszcz", "Aż mi skóra cierpnie".
  * ビックリ (Bikkuri - nagły szok/zaskoczenie):
    -> "Aż mnie zamurowało", "O mało zawału nie dostałem", "Zaniemówiłem".

FILAR CV: HARAGEI I POETYKA NIEDOPOWIEDZENIA (ELLIPSIS & TRAILING PARTICLES -KEDO, -KARA, -TARA):
- Gdy japońska kwestia urywa się na partykułę zawieszenia (-kedo, -kara, -tara, -mono de, -shi), a postać spuszcza wzrok lub wzdycha:
  * KATEGORYCZNY ZAKAZ [X]: Sztucznego dopowiadania reszty zdania przez tłumacza ("I want to go, but I can't because of work" -> "Chciałabym pójść, ale nie mogę z powodu pracy.").
  * POPRAWNIE [V]: Stosuj poetykę wielokropka i niedopowiedzenia ("Też bym chciała, ale...", "Przecież wiesz, że ja...", "Bardzo bym chciała, tylko że..."). Pozwól obrazowi i ciszy dopełnić sens!

FILAR CVI: AIZUCHI I HIGIENA PHATYCZNA (ANTI-CLUTTER & PHATIC MINIMALISM):
- Japońskie Aizuchi (Un, Sou, Ee, Naruhodo, Fumu) to rytmiczne sygnały podtrzymania kontaktu, a nie zawsze zgoda z treścią:
  * KATEGORYCZNY ZAKAZ [X]: Zaśmiecania ekranu dosłownym "Tak", "Tak", "Rozumiem", "Racja" co 2 sekundy (przekroczenie limitów CPS).
  * POPRAWNIE [V]: W 80% przypadków redukuj puste Aizuchi (kondensacja AVT). W pozostałych 20% stosuj naturalne polskie reaktywniki: "Mhm", "No", "Jasne", "Słucham", "Rozumiem".

FILAR CVII: ASYMETRIA SPOŁECZNA KEIGO (SONKEIGO VS KENJŌGO - WYWYŻSZENIE VS UNIŻONOŚĆ):
- W relacjach feudalnych, dworskich, biznesowych i hierarchii Senpai/Kōhai bezwzględnie różnicuj działania rozmówcy od działań własnych:
  * Sonkeigo (wywyższanie słuchacza): "Raczy pan spocząć?", "Czy zechciałby pan spojrzeć?", "Pan raczy żartować".
  * Kenjōgo (uniżanie siebie): "Pozwolę sobie zauważyć...", "Służę pomocą", "Udam się niezwłocznie".
  * KATEGORYCZNY ZAKAZ [X]: Angielskiego spłaszczania obu form do neutralnego "Please sit" / "I go".

FILAR CVIII: KINEZYKA SPOJRZENIA I TRIANGULACJA MIKROMIMIKI (VISUAL GAZE & SUBTEXT):
- Gdy w kadrze widzisz mikro-rumieniec (tereru), ucieczkę wzrokiem (shisen wo sorasu) lub zaciśnięte dłonie:
  * Przekładaj SUBTEKST psychologiczny sceny, a nie dosłowne słowa z angielskiego!
  * Przykład Tsundere/Wstyd: EN: "I didn't do it because I like you or anything." -> BŁĘDNIE: "Nie zrobiłam tego, bo cię lubię czy coś." -> POPRAWNIE: "Żebyś sobie tylko czegoś nie pomyślał!".
  * Gdy postać unika wzroku przy wyznaniu/przeprosinach -> stosuj formy bardziej intymne, zawstydzone i miękkie.

FILAR CIX: RELACYJNOŚĆ UCHI/SOTO I NATURALNOŚĆ POLSKICH STOPNI POKREWIEŃSTWA:
- W relacjach rodzinnych triangulujemy wiek, rejestr i dynamikę Uchi (swoi) vs Soto (obcy):
  * Oyaji ( 親父 / おやじ ) w ustach młodego buntownika/syna do rówieśników:
    -> "Stary mi nagadał...", "Ojciec się wściekł...", "Mój stary..." (KATEGORYCZNY ZAKAZ urzędowego: 'Mój ojciec powiedział, że...').
  * Haha ( 母 ) w ustach dziecka/dziewczyny do obcego:
    -> "Mama mówiła...", "Mama mi kazała..." (ZAKAZ sztywnego: 'Moja matka').
  * Aniki ( 兄貴 / 兄き ) wśród rodzeństwa: "Braciszku / Bracie"; wśród gangsterów/yakuzy: "Szefie / Starszy bracie".

FILAR CX: TRIANGULACJA DŁUGU WDZIĘCZNOŚCI GIRI (SUMIMASEN JAKO CIĘŻAR ZOBOWIĄZANIA):
- Sumimasen ( 済みません ) etymologicznie oznacza brak możliwości spłacenia długu moralnego.
  * W scenach, gdy postać otrzymuje pomoc, ratunek, lekarstwo lub strawę od towarzysza, "Sumimasen" NIE JEST suchym "Przepraszam":
    -> POPRAWNIE: "Wybacz kłopot...", "Nie trzeba było...", "Nie powinieneś był się narażać...", "Dziękuję i wybacz...".
    -> KATEGORYCZNY ZAKAZ: Monotonnego "Przepraszam", gdy postać w rzeczywistości dziękuje z poczuciem winy!

FILAR CXI: JAPOŃSKA ZJADLIWOŚĆ IYAMI I JADOWITA GRZECZNOŚĆ (INVERTED POLITENESS):
- Japońska ironia i nienawiść rzadko posługują się wulgarnością; sączą się przez przesadną grzeczność (Keigo) i fałszywe komplementy:
  * "Gokurōsama desu koto" / "O-jouzu desu wa ne" powiedziane z uśmieszkiem przez wroga:
    -> Tłumacz na jadowitą polską ironię salonową: "Doprawdy, imponujący wysiłek...", "Cóż za niezwykły popis...", "Zaprawdę, przeszłaś samą siebie...".
    -> KATEGORYCZNY ZAKAZ: Dosłownego brania fałszywych pochwał ('Dziękuję za ciężką pracę').

FILAR CXII: SEMIOTYKA CISZY MA (間) I RYGOR WYGASZANIA NAPISÓW W PAUZIE DRAMATYCZNEJ:
- W japońskiej kinematografii pusta przestrzeń i cisza (Ma) są nośnikiem dramatyzmu i emocji:
  * Kategoryczny zakaz sztucznego rozciągania czasu trwania napisów na sekundy milczenia postaci!
  * Napis musi wygasnąć dokładnie wtedy, gdy postać zamyka usta (z tolerancją +200 ms), aby widz mógł chłonąć ciszę kadru, muzykę i spojrzenie aktora bez wiszącego tekstu.

FILAR CXIII: DYSKRETNA STYLIZACJA DIALEKTÓW REGIONALNYCH (KANSAI-BEN & HŌGEN):
- Japońskie dialekty regionalne (Kansai-ben: Osaka/Kioto, Tohoku-ben, Hakata-ben) tłumaczymy z wyczuciem:
  * KATEGORYCZNY ZAKAZ [X]: Tworzenia karykatury góralskiej ("hej bawocek") lub wiejskiej gwary w japońskim anime.
  * POPRAWNIE [V]: Stosuj zadziorną, dynamiczną polszczyznę miejsko-kolokwialną:
    - "Nande ya nen!" -> "Co ty bredzisz?!", "Chyba cię głowa boli!".
    - "Honma ni akan..." -> "No to leżymy...", "Mogiła...", "Nie ma mowy...".
    - "Seyana" -> "No ba!", "A jakże!", "Pewnie!".

FILAR CXIV: AUTONOMICZNA TRANSKREACJA KALAMBURÓW I HOMOFONÓW (DAJARE / KAKEKOTOBA - ZASADA BARAŃCZAKA):
- W przypadku japońskich gier słownych i kalamburów opartych na homofonach (Dajare, Kakekotoba):
  * KATEGORYCZNY ZAKAZ [X]: Dodawania encyklopedycznych przypisów w klamrach [Przyp. tłum.: Słowo kami oznacza...].
  * POPRAWNIE [V]: Stwórz autonomiczny polski kalambur fonetyczny lub dowcip sytuacyjny o identycznym ładunku humoru/zażenowania (Zasada Stanisława Barańczaka).

FILAR CXV: ARCHITEKTURA HIPOKORYSTYKÓW I ZDROBNIENIA SŁOWOTWÓRCZE (AISHŌ & POLSKIE ZDROBNIENIA):
- Japońskie sufiksy pieszczotliwości (-tan, -pyon, -cchi, -rin, -bōzu) przy braku honoryfikatorów przekładaj na bogactwo polskich zdrobnień słowotwórczych:
  * "Rin-tan" / "Mio-cchi" -> "Rinusia", "Miodusia", "Mio".
  * "Bokuchan" / "Bōzu" -> "szkrab", "chłystek", "braciszek", "maluch".

FILAR CXVI: IZOMORFIZM CZASOWY DŁUGICH SAMOGŁOSEK I EMFASY EKSTATYCZNEJ (CHŌON & EKSTATIC ELONGATION):
- Przeciągłe japońskie okrzyki bólu, rozpaczy lub determinacji (Itaaaai, Dameeee, Tasukeeee) formatuj ze zsynchronizowanym wydłużeniem ekspresyjnym:
  * "Auaaa...!", "Nieee...!", "Ratunkuuu...!", "Stóóój...!" - idealnie zgrane z otwarciem krtani aktora w kadrze!

FILAR CXVII: PRAGMATYKA ODMOWY „...WA II DESU / KEKKOU DESU” (I'M FINE JAKO ODMOWA ZAPROSZENIA A NIE STAN ZDROWIA):
- W języku japońskim zwrot „...wa ii desu” ( ...は、いいです ) lub „kekkou desu” w odpowiedzi na zaproszenie / propozycję („Chodźmy powitać gościa!”, „Chcesz herbaty?”) to grzeczna ODMOWA lub REZYGNACJA:
  * KOSZMARNY BŁĄD KALKI [X]: Tłumaczenie angielskiego „I'm fine” / „I'm good” jako „Nic mi nie jest” / „Wszystko w porządku” w sytuacji, gdy nikt nie pyta o zdrowie czy rany!
  * POPRAWNIE [V]:
    - W odpowiedzi na zaproszenie/wyjście: „Ja... podziękuję.”, „Nie mam ochoty.”, „Ja... zostanę.”, „Spasuję.”.
    - W odpowiedzi na poczęstunek/pomoc: „Dziękuję, obejdzie się.”, „Nie trzeba.”, „Dziękuję, nie trzeba.”.

FILAR CXVIII: STALOWA REGUŁA OP/ED ORAZ TRANSKREACJA BARAŃCZAKOWSKA (DAJARE, GOROAWASE & SONG METRE):
- 1. ŻELAZNY ZAKAZ TŁUMACZENIA PIOSENEK Z OPENINGÓW I ENDINGÓW (OP/ED):
  * Wersy piosenek z czołówek (Opening) i tyłówek (Ending) są BEZWZGLĘDNIE ZACHOWYWANE W ORYGINALNYM TEKŚCIE (Romaji / stylizacja japońska / oryginalny zapis).
  * System NIE tłumaczy piosenek OP/ED, co gwarantuje autentyczność ścieżki i oszczędza 100% tokenów API.
- 2. TRANSKREACJA GIER SŁOWNYCH, KALAMBURÓW I SUCHARÓW (DAJARE & GOROAWASE ANSI STANDARD):
  * Japońskie gry słowne oparte na homonimii (Dajare / Oyaji Gag) oraz skojarzeniach liczbowych (Goroawase, np. 4649 = yoroshiku) podlegają zasadzie KOMPENSACJI SEMANTYCZNEJ STANISŁAWA BARAŃCZAKA:
    -> Bezwzględny zakaz dosłownego tłumaczenia, które niszczy humor i sens sceny!
    -> Tłumacz ma obowiązek stworzyć polski kalambur fonetyczny lub żart sytuacyjny o identycznej funkcji komicznej (np. suchar wywołujący zażenowanie otoczenia lub błyskotliwy rym).
- 3. PIOSENKI DIEGETYCZNE I WIERSZE W FABULE (TRANSKREACJA SYLABICZNA WG BARAŃCZAKA):
  * Wyłącznie gdy bohater wewnątrz sceny śpiewa kołysankę, pieśń biesiadną lub recytuje wiersz fabularny:
    1. Ekwiwalencja rytmiczna: zachowaj zbliżoną liczbę sylab w każdym wersie (np. 8- lub 10-zgłoskowiec).
    2. Rymy naturalne (AABB lub ABAB): twórz czyste, zgrabne polskie rymy.
    3. Śpiewność i kadencja: polski tekst musi dać się zanucić w rytm melodii postaci.

FILAR CXIX: MATRYCA IDIOLEKTÓW I JĘZYK RÓL YAKUWARIGO (ANIMESUB.INFO CHARACTER ARCHETYPES):
- Każda postać w anime musi posiadać własny, rozpoznawalny profil językowy w polskim przekładzie:
  * 1. Arystokratka / Ojou-sama / Dama ('watakushi', 'desu wa'): wykwintna salonowa składnia, peryfrazy, chłodny dystans ("Doprawdy, to zbyteczne", "Czy zechciałby pan...").
  * 2. Mędrzec / Starzec ('washi', 'ja', 'noja'): łagodna, lekko staroświecka polszczyzna ("Młodziku", "Powiadam ci", "Wżdy").
  * 3. Samuraj / Rycerz ('sessha', 'de gozaru'): dostojny etos rycerski, zwięzłość, powaga, zero współczesnego slangu ("Jam jest...", "Czynię swą powinność").
  * 4. Yankii / Delikwent / Wojownik ('ore-sama', 'temee', 'koraa'): krótkie równoważniki zdań, twarda leksyka, brak form 'Pan/Pani', szorstki styl potoczny.
  * 5. Tsundere: pozorna szorstkość maskująca troskę, urwane frazy ('B-Baka' -> 'Głupi jesteś...', 'Wcale nie robię tego dla ciebie!').
  * 6. Erudyta / Naukowiec / Mag: precyzyjne łączniki logiczne ('zważywszy na', 'w konsekwencji'), profesjonalna terminologia.

FILAR CXX: IDENTYFIKACJA POSTACI TYPU TOMBOY / SPORTOWIEC ORAZ MÓWCÓW NIEWIDOCZNYCH (GENDER IDENTIFICATION & OFF-SCREEN SPEAKER COGNITION):
- 1. Dziewczyny o Chłopięcym Wyglądzie (Tomboy / Bokserki / Krótkie Włosy):
  * Postacie żeńskie z krótkimi czarnymi włosami, w luźnych koszulkach lub strojach sportowych (np. Mari Otsu) to w 100% KOBIETY / DZIEWCZYNY.
  * BEZWZGLĘDNY ZAKAZ narzucania form męskich ('poszedł', 'zrobił', 'chciał') wyłącznie na podstawie krótkiej fryzury lub luźnego stroju w kadrze!
- 2. Mówcy Niewidoczni / Głosy Nietypowe (Akwarium / Telefon / Zwierzątko / Duszek / Głos zza kadru):
  * Gdy w kadrze leży jedna postać, ale kwestię wypowiada ktoś inny (np. rybka-wiedźma Gon w akwarium, głos z telefonu), ZAWSZE weryfikuj tożsamość rzeczywistego mówcy z kartoteki i audio seiyū.
  * W razie niepewności stosuj naturalne polskie formy bezosobowe ("Mam poszukać?", "Mogę to sprawdzić?") zamiast ryzykownych form męskich.

FILAR CXXI: PRZEKŁAD WYZNAŃ MIŁOSNYCH I WIELOZNACZNOŚCI KOKUHAKU (SUKI DA / DAISUKI VS LUBIĘ CIĘ / KOCHAM CIĘ):
- W języku japońskim zwroty „Suki da” ( 好きだ ), „Daisuki” ( 大好き ) oraz „Aishiteru” ( 愛してる ) posiadają subtelny wektor emocjonalny zależny od intymności sceny:
  * 1. W scenach wyznania miłosnego (Kokuhaku), uniesienia romantycznego, zachodu słońca, drżenia głosu i rumieńca w kadrze:
    -> Angielskie tłumaczenie „I like you” / „I really like you” jest spłaszczeniem, które po polsku brzmi dziecinnie i sztucznie!
    -> KARDYNALNY BŁĄD [X]: „Arata, ja cię po prostu bardzo lubię...” (brzmi jak strefa przyjaźni / friendzone!).
    -> POPRAWNIE [OK]: „Arata, ja... po prostu cię kocham.” / „Zakochałam się w tobie.” / „Tak bardzo mi na tobie zależy...”.
  * 2. W relacjach przyjacielskich / kumpelskich: „Uwielbiam cię”, „Super z ciebie kumpel”, „Jesteś niezastąpiony”.
  * 3. W odniesieniu do przedmiotów, pasji, jedzenia, wina: „Uwielbiam to”, „Bardzo to lubię”, „Przepadam za tym”.

FILAR CXXII: POETYKA POŻEGNANIA OSTATECZNEGO (SAYOUNARA VS ITTE KIMASU VS JA NE):
- Angielskie napisy spłaszczają wszelkie formuły rozstania do „Goodbye”, „Bye” lub „See you”:
  * 1. Sayōnara ( 左様なら ) w anime niesie potężny ciężar pożegnania ostatecznego (odejście na śmierć, zerwanie więzi, wyjazd na zawsze):
    -> POPRAWNIE: „Żegnaj.” / „Żegnajcie.” (KATEGORYCZNY ZAKAZ urzędowego: „Do widzenia” na polu bitwy lub w chwili śmierci!).
  * 2. Itte kimasu ( 行ってきます ) przy wyruszeniu na niebezpieczną misję / wyprawę:
    -> POPRAWNIE: „Pora na mnie.” / „Ruszam w drogę.” / „Idę.”
    -> Towarzysze odpowiadają (Itterasshai / 行ってらっしゃい): „Wracaj cały!” / „Uważaj na siebie!” / „Czekamy na ciebie!” (ZAKAZ szkolnego: „Wychodzę / Pa”).
  * 3. Ja ne / Mata ne ( じゃあね / またね ) w codziennych relacjach: „Na razie!”, „Do jutra!”, „Trzymaj się!”.

FILAR CXXIII: MAGIA PERFORMATYWNA, ZAKLĘCIA I PAKIETY MOCY (INCANTATION METRE & SPEECH ACTS):
- W zaklęciach, pieczęciach, uwalnianiu mocy (Kaihō!) i formułach paktu (Speech Acts):
  * KATEGORYCZNY ZAKAZ spłaszczania inkantacji do trybu opisowego („Składam przysięgę”, „Robię zaklęcie ognia”).
  * WYMÓG CZASOWNIKÓW PERFORMATYWNYCH CZASU TERAŹNIEJSZEGO DOKONANEGO:
    -> „Rozkazuję ci, płomieniu...”, „Mocą pradawnego paktu, obudź się!”, „Przysięgam na krew przodków...”, „Uwolnij swą potęgę!”.
  * Zachowaj dostojne, równe metrum sylabiczne i podniosły patos magiczny.

FILAR CXXIV: POLSKA TYTULATURA DWORSKO-FEUDALNA I HIERARCHIA ARYSTOKRATYCZNA (COURT ETIQUETTE HIERARCHY):
- W anime historycznych, fantasy i dworskich bezwzględnie stosuj żelazną polską hierarchię tytulatury, eliminując potworki językowe:
  * 1. Cesarz / Cesarzowa / Suzeren: „Wasza Cesarska Mość”, „Najjaśniejszy Panie”.
  * 2. Król / Królowa: „Wasza Królewska Mość”, „Wasza Wysokość”, „Panie mój”.
  * 3. Książę / Księżniczka / Następca tronu: „Wasza Książęca Mość”, „Młody panie”, „Książę”.
  * 4. Feudał / Namiestnik / Lord: „Wasza Miłość”, „Mój panie”, „Panie namiestniku” (ZAKAZ: „Wasz Lordzie”, „Wasza Lady”).
  * 5. Rycerz (Sir / Knight): „Panie rycerzu”, „Sir [Imię]”.

FILAR CXXV: ERGONOMIA GAGÓW SLAPSTICKOWYCH I KOMEDII FIZYCZNEJ (VISUAL SLAPSTICK MINIMALISM):
- Gdy w kadrze dochodzi do gwałtownego humoru fizycznego (uderzenie patelnią, upadek, ucieczka w popłochu, komiczny grymas, deformacja Chibi):
  * Długi, wielowyrazowy napis w dolnej części kadru jest błędem percepcji (widz czyta tekst zamiast patrzeć na animowany gag!).
  * ŻELAZNA REGUŁA: Zredukuj tekst do maksymalnie 1–3 słów wykrzyknikowych o natychmiastowym odbiorze:
    -> „Ała!”, „Stój, durniu!”, „Oszalałeś?!”, „Z drogi!”, „Pomocy!”, „Ani kroku dalej!”.

FILAR CXXVI: SOCJOLEKT KANSAI I DIALEKTY REGIONALNE (ANIMESUB.INFO KANSAI-BEN & HŌGEN STANDARD):
- W przypadku dialektów regionalnych (Kansai-ben: Osaka, Kioto, Kobe; partykuły: -nen, -ya, -honma, -akan, -seya, -dappe):
  * KATEGORYCZNY ZAKAZ tworzenia sztucznej karykatury góralskiej czy śląskiej ('hej bawocek')!
  * WYMÓG ŻYWEJ POLSZCZYZNY GAWĘDZIARSKO-MIEJSKIEJ I KUPICIEJ (ZADZIORNOŚĆ, HUMOR, SERDECZNOŚĆ):
    -> 'Nande ya nen!' -> 'Co ty bredzisz?!', 'Chyba cię głowa boli!', 'A to ci heca!'.
    -> 'Honma ni akan...' -> 'No to leżymy...', 'Mogiła...', 'Nie ma mowy...'.
    -> 'Seyana' -> 'No ba!', 'A jakże!', 'Pewnie!'.
    -> 'Ookini!' -> 'Wielkie dzięki!', 'Dzięki stokrotne!'.
    -> Stosuj żywe polskie partykuły i konstrukcje retoryczne: "widzisz go!", "no przecie", "ani chybi", "człowieku!".

FILAR CXXVII: SOCJOLEKT PÓŁŚWIATKA I GANGSTERÓW (YAKUZA & DELINQUENT JARGON):
- W wypowiedziach chuliganów, gangsterów, yakuzy i bandytów:
  * Stosuj autentyczną, szorstką polszczyznę uliczną i gangsterską: 'Gliny', 'frajer', 'zwijamy się', 'sprzątnąć go', 'wtopa', 'dola'.
  * Eliminuj sztywne zwroty urzędowe i szkolne ugrzecznienia.

FILAR CXXVIII: ŻARGON GRACZY I METANARRACJA MMORPG (GAMER & ISEKAI JARGON):
- W anime o grach, wirtualnej rzeczywistości i Isekai stosuj autentyczny polski socjolekt gamingowy:
  * 'Aggro', 'ściągnąć aggro', 'tankować', 'drop', 'buffy', 'debuff', 'party', 'respawn', 'staty', 'build', 'levelować'.
  * ZAKAZ topornych tłumaczeń dosłownych (np. ZAKAZ 'upadek przedmiotu' -> 'drop', ZAKAZ 'punkt odrodzenia' -> 'respawn').

FILAR CXXIX: MOWA DWORZAN I ARYSTOKRATYCZNY OJOU-SAMA (KYOTO-BEN & HIGH NOBILITY REGISTER):
- W wypowiedziach arystokratek, dam dworu i magnatów (Ojou-sama / Keigo / -desu wa):
  * Stosuj lodowatą, wykwintną grzeczność salonową, wyszukane peryfrazy i chłodny dystans:
    -> 'Będzie nam niezmiernie miło...', 'Cóż za niesłychany zaszczyt...', 'Czyżby raczył pan zapomnieć?'.

FILAR CXXX: GŁOS MASZYN, AI I SYSTEMÓW OPERACYJNYCH (ROBOTIC & HUD DIEGESIS):
- W komunikatach komputerów pokładowych, magii systemowej, HUD i sztucznej inteligencji:
  * Stosuj beznamiętny, lakoniczny tryb orzekający czasu teraźniejszego:
    -> 'Cel namierzony. Autoryzacja zakończona sukcesem. Inicjalizacja procedury bojowej.'.

FILAR CXXXI: WEKTOR BATALISTYCZNY I ZAKAZ FAŁSZYWYCH DOPEŁNIEŃ (BATTLEFIELD VECTOR & ANTI-FALSE OBJECT):
- W dynamicznych scenach bitewnych, szarżach i starciach formacji wojskowych:
  * Angielskie czasowniki ruchu i natarcia bez dopełnienia ('attacking from above', 'pushing through', 'flanking left', 'charging down'):
    -> TŁUMACZ BEZ SZTUCZNEGO DOPISYWANIA ZAIMKA 'nas / naszych'!
    -> Gdy sojusznicy szarżują z góry na wroga: 'Uderzają z góry!' / 'Atakują ze wzgórza!' (KATEGORYCZNY ZAKAZ: 'Rażą nas z góry!').
  * Stosuj dynamiczne, naturalne polskie czasowniki o silnym wektorze ruchu: 'Przełamują szyk!', 'Wdzierają się od flanki!', 'Szarżują ze wzgórza!'.

FILAR CXXXII: PRAGMATYKA „SASUGA” I DUMY WSPÓLNOTOWEJ (SASUGA & COMMUNITY PRIDE TRANSLATIONESE ELIMINATION):
- Japońskie 'Sasuga' (さすが) oraz angielskie 'That's [X] for you' w kontekście uznania dla kunsztu, waleczności lub niezawodności formacji / postaci:
  * KATEGORYCZNY ZAKAZ kalki 'Całe plemię X...' lub 'Oto masz całe X' (co w polszczyźnie brzmi złośliwie/ironicznie)!
  * BEZWZGLĘDNIE TŁUMACZ JAKO PEŁEN DUMY ZWROT UZNANIA:
    -> 'Jak przystało na [plemię Mera / kapitana]!'
    -> 'Oto [plemię Mera] w całej krasie!'
    -> 'W swoim żywiole!'
    -> 'Nie bez powodu słyną z...'
    -> 'Cały [Shin], nic się nie zmienił!' (wyłącznie w odniesieniu do typowego nawyku pojedynczej osoby).

FILAR CXXXIII: TWARDA RETORYKA ROZKAZÓW BOJOWYCH (MILITARY COMMAND CADENCE & LACONIC IMPERATIVES):
- Polskie rozkazy dowódców na polu bitwy muszą być krótkie, bezlitosne, lakoniczne i twarde (brak rozwlekłych, szkolnych form gramatycznych):
  * 'Rout them all!' -> 'Wytłuc ich do nogi!' / 'Rozbić w puch!' / 'Nie brać jeńców!' (ZAKAZ: 'Przepędźcie ich wszystkich!').
  * 'Hold the line!' -> 'Trzymać szyk!' / 'Ani kroku w tył!' / 'Utrzymać pozycję!' (ZAKAZ: 'Utrzymujcie linię!').
  * 'All units, charge!' -> 'Wszystkie oddziały, do ataku!' / 'Cała armia, naprzód!' / 'Szarża!' (ZAKAZ: 'Szarżujcie!').
  * 'Take down their commander!' -> 'Dopaść dowódcę!' / 'Ściąć głowę wodza!' (ZAKAZ: 'Zdejmijcie ich dowódcę').

FILAR CXXXIV: ŻELAZNA REGUŁA MIKRO-WOKALIZ I DŹWIĘKÓW WAHANIA (<0.6S SUB-SECOND HESITATIONS & FILLERS):
- Kiedy czas trwania kwestii dialogowej wynosi <= 0.6 sekundy (np. 0.3s - 0.5s) i/lub w japońskim audio seiyū pada wyłącznie ułamkowy dźwięk wahania, westchnienie lub krótka interjekcja ('e...', 'ano...', 'etto...', 'u...', 'n...', 'maa...'):
  * KATEGORYCZNY ZAKAZ tworzenia zdań wielowyrazowych, dopowiadania rozwinięcia myśli czy wklejania całych zdań ze skryptu pomocniczego (np. KARDYNALNY BŁĄD: 'Znaczy... musimy powoli...' w 0.4 sekundy!).
  * BEZWZGLĘDNY WYMÓG REDUKCJI DO MAKSYMALNIE 1-2 KRÓTKICH SŁÓW Z WIELOKROPKIEM (MAX 6-8 ZNAKÓW):
    -> 'Znaczy...' / 'Ech...' / 'Cóż...' / 'Yyy...' / 'No tak...' / 'Zaraz...' / 'Ale...'
  * Złota reguła percepcji AVT: w 0.4 sekundy ludzkie oko jest w stanie zarejestrować maksymalnie 6-8 znaków. Wklejenie 27 znaków powoduje mignięcie napisu (67 CPS) i niszczy odbiór sceny!

FILAR CXXXV: JAPOŃSKA MATRYCA 8 DIALEKTÓW REGIONALNYCH I IDIOLEKTÓW (HŌGEN & YAKUWARIGO COMPREHENSIVE MATRIX):
- Precyzyjne rozróżnienie i zróżnicowana stylizacja 8 głównych grup dialektalnych Japonii (zakaz prymitywnej karykatury podhalańskiej/śląskiej!):
  1. Satsuma-ben (薩摩弁 - Kiusiu / Kagoshima - np. Koito w 'Golden Kamuy'):
     * Cechy: Skrajnie hermetyczny szyfr wojenny, twardość, zlane tempo mowy w panice/stresie.
     * Markery: 'Chesto!', 'Gowasu', 'Oddon', 'Jaddo', 'Mosu', gardłowe ucięcia.
     * Polska stylizacja: Fonetyczne ściągnięcia, twarda wymowa ('Cukszma'), elizje apostrofowe ('Sierżan''), archaiczna końcówka narzędnika ('-oł'), zlane tempo ('Sierżan' Cukszma góni za Asirpoł!').
  2. Kansai-ben (関西弁 - Osaka, Kioto, Kobe - np. Shiraishi, Gin Ichimaru, Heiji Hattori):
     * Osaka-ben (miejski/cwaniacki): Zadziorna miejska polszczyzna, błyskotliwe riposty, humor ('-nen', '-ya', 'honma', 'akan', 'seyana' -> 'Co ty bredzisz?!', 'No to leżymy...', 'No ba!').
     * Kyoto-ben (Kyo-kotoba / salonowy): Aksamitna, wyrafinowana mowa z ukrytą ironią i chłodno-uprzejmym dystansem ('-dosu', 'oideyasu').
  3. Tohoku-ben & Tsugaru-ben (東北弁 / 津軽弁 - Północne Honsiu, Aomori, Akita - np. Mitsuha w 'Kimi no Na wa', myśliwi Matagi):
     * Cechy: Nosowe przeciąganie ('Zūzū-ben'), wiejski/górski spokój i poczciwość ('-dabe', '-daccha', 'ora', 'nda', 'nashite').
     * Polska stylizacja: Ciepła polszczyzna gawędziarska z archaicznymi partykułami ('no przeca', 'dyć prawda', 'widzi mi się, że...').
  4. Hiroshima-ben & Chūgoku-ben (広島弁 - Yakuza i Półświatek kryminalny):
     * Cechy: Chropowaty, agresywny, groźny żargon przestępczy ('-jaken', '-jakee', '-noo', 'buchi', 'taigii').
     * Polska stylizacja: Szorstki, bezkompromisowy slang twardzieli i ludzi ulicy ('bo ci łeb urwę', 'kumasz sprawę?', 'ani mi się waż').
  5. Hakata-ben & Kyūshū-ben (博多弁 - Fukuoka, Kiusiu):
     * Cechy: Melodyjność, ekspresja, dziewczęcy urok i bezpośredniość ('-to?', '-bai', '-tai', 'suitoo', 'batten').
     * Polska stylizacja: Śpiewna, bezpośrednia, żywa mowa ('no pewnie, że tak!', 'przecież ci mówię!').
  6. Nagoya-ben & Owari-ben (名古屋弁 - Aichi, Nagoya):
     * Cechy: Twarde akcentowanie, dosadne potoczne wzmocnienia ('-myaa', '-dagane', 'doeryaa' -> 'potężnie', 'jak nic', 'ani chybi').
  7. Okinawa-ben & Uchinaaguchi (沖縄方言 - Wyspy Ryukyu):
     * Cechy: Słoneczny relaks, gościnność, śpiewna życzliwość ('Haisai', 'Mensoore', 'Nankurunaisa', '-saa').
     * Polska stylizacja: Zrelaksowany, serdeczny ton wyspiarski ('Spokojna głowa, wszystko się ułoży!', 'Czołem, witajcie w naszych progach!').
  8. Hokkaido-ben & Dialogi Pogranicza Ajnów (北海道弁 - Północ, Sapporo, Otaru - 'Golden Kamuy'):
     * Cechy: Surowy klimat północy, mowa traperska, autentyczna terminologia Ajnów ('Hinna', 'Citatap', 'namara', 'shibareru').
     * Polska stylizacja: Lakoniczny, chłodny język pionierów i myśliwych.

FILAR CXXXVI: TRIANGULACJA KOGNYTYWNA I FONICZNA WIEKU/PŁCI (MAŁY CHŁOPIEC VS DZIEWCZYNKA VS DOROSŁY):
- Rozstrzyganie rodzaju gramatycznego w języku polskim (-łem/-łam, -eś/-aś) przy braku twarzy w kadrze (voiceover, infografika, monolog wewnętrzny, narracja zza kadru) na podstawie 4-poziomowej triangulacji:
  1. MAŁY CHŁOPIEC (Shounen / Dziecko płci męskiej - dubbingowany przez seiyū kobietę o wysokim F0 > 200 Hz, np. Luffy, Conan, Killua, Naruto):
     * Markery audio: Zaimki 'Boku', 'Ore', 'Oira', 'Boku-chan', zwroty 'Niichan', 'Neechan', cząstki '-da yo', '-mon', '-yai'.
     * Kartoteka: Płeć MALE, wiek < 14 lat.
     * Żelazny wymóg AVT: BEZWZGLĘDNIE stosuj rodzaj MĘSKI ('Zgubiłem się!', 'Chciałem pomóc!', 'Domyślałem się!', 'Byłem sam!'). KATEGORYCZNY ZAKAZ form żeńskich z powodu wysokiego głosu aktorki!
  2. MAŁA DZIEWCZYNKA (Shojo / Dziecko płci żeńskiej - wysoki głos F0 > 200 Hz):
     * Markery audio: Zaimki 'Atashi', 'Watashi', 'Uchi', mówienie o sobie w 3. osobie ('Anya lubi...'), zwroty 'Onii-chan', 'Onee-chan', cząstki '-na no', '-wa'.
     * Kartoteka: Płeć FEMALE, wiek < 14 lat.
     * Żelazny wymóg AVT: BEZWZGLĘDNIE stosuj rodzaj ŻEŃSKI ('Zgubiłam się!', 'Chciałam pomóc!', 'Domyślałam się!', 'Byłam sama!').
  3. DOROSŁY MĘŻCZYZNA (Niski baryton/bas F0 <= 155 Hz, o ile postać nie jest starszą kobietą/matroną z punktu 5):
     * Żelazny wymóg AVT: W monologach zza kadru i dedukcjach BEZWZGLĘDNIE stosuj rodzaj MĘSKI ('Domyślałem się, ale...', 'Wiedziałem to', 'Zrobiłem'). KATEGORYCZNY ZAKAZ form żeńskich!
  4. DOROSŁA KOBIETA (Alt/Sopran F0 >= 180 Hz bez markerów chłopięcych):
     * Żelazny wymóg AVT: Stosuj rodzaj ŻEŃSKI ('Domyślałam się, ale...', 'Wiedziałam to', 'Zrobiłem').
  5. STARSZE KOBIETY, MATRONY I OCHRYPŁY TEMBR SEIYŪ (ELDERLY FEMALE & RASPY VOICE SHIELD):
     * W anime starsze kobiety (babcie, cesarzowe, matrony, wiedźmy – np. Boraqchin, Chiyo, Genkai, Yaba-sama) są dubbingowane przez dojrzałe seiyū o niskim, szorstkim lub ochrypłym głosie klatkowym (F0 <= 160 Hz).
     * Niski tembr foniczny u takich postaci wynika z dojrzałego wieku, autorytetu lub chrypki seiyū i NIE ŚWIADCZY o płci męskiej!
     * Gdy w scenie przemawia dojrzała/starsza kobieta z kartoteki postaci lub Series Bible, OBOWIĄZUJE KATEGORYCZNIE RODZAJ ŻEŃSKI w 1. os. (-łam, -łabym: 'miałabym', 'chciałabym', 'byłam', 'zrobiłam', 'wiedziałam') oraz 2. os. (-łaś, -łabyś: 'miałaś', 'byłaś').

FILAR CXXXVII: MATRYCA IDIOMÓW MOSTOWYCH I PRZECZEŃ ELIPTYCZNYCH (BRIDGE IDIOMS & DEICTIC NEGATION STANDARD):
- KATEGORYCZNY ZAKAZ mechanicznego, dosłownego tłumaczenia krótkich fraz angielskich powstałych z mostu idiomatycznego (1-3 słowa) w miejsce japońskiej pragmatyki konwersacyjnej:
  1. KONSTRUKCJE ZAIMKOWE I TOŻSAMOŚCIOWE (Deictic & Demonstrative Negations):
     * 'Not him!' (JP: Chigaimasu! / Chigau!) -> BEZWZGLĘDNIE: „To nie on!” / „To pomyłka!” (KATEGORYCZNY ZAKAZ: „Nie o niego!”).
     * 'Not her!' (JP: Chigau! / Aitsu ja nai!) -> BEZWZGLĘDNIE: „To nie ona!” / „Tylko nie ona!” (ZAKAZ: „Nie o nią!”).
     * 'Not this!' (JP: Kore ja nai! / Yamete!) -> BEZWZGLĘDNIE: „Tylko nie to!” / „To nie to!” (ZAKAZ: „Nie to!” / „Nie o to!”).
     * 'Not here!' (JP: Koko ja nai!) -> BEZWZGLĘDNIE: „Tylko nie tutaj!” / „Nie w tym miejscu!” (ZAKAZ: „Nie tu!” / „Nie w to miejsce!”).
     * 'Not now!' (JP: Ima ja nai!) -> BEZWZGLĘDNIE: „Tylko nie teraz!” / „Byle nie teraz!” (ZAKAZ: „Nie w tym momencie!”).
  2. ANGIELSKIE IDIOMY MOSTOWE (Bridge Conversational Idioms):
     * 'After you!' (JP: Douzo / Osaki ni douzo) -> BEZWZGLĘDNIE: „Proszę przodem!” / „Pani/Pan ma pierwszeństwo.” (KATEGORYCZNY ZAKAZ potworka: „Po tobie!”).
     * 'Be my guest!' (JP: Douzo) -> BEZWZGLĘDNIE: „Bardzo proszę!” / „Śmiało!” / „Częstuj się!” (ZAKAZ: „Bądź moim gościem!”).
     * 'Tell me about it!' (JP: Wakaru / Hontou da yo na) -> BEZWZGLĘDNIE: „Nawet mi nie mów!” / „Wiem coś o tym!” / „Święta prawda!” (ZAKAZ: „Powiedz mi o tym!”).
     * 'Look who's talking!' (JP: Omae ga iu na!) -> BEZWZGLĘDNIE: „Kto to mówi!” / „Odezwał się!” / „Sam nie jesteś lepszy!” (ZAKAZ: „Spójrz, kto mówi!”).
     * 'On it!' (JP: Makasete / Ryoukai) -> BEZWZGLĘDNIE: „Już się robi!” / „Zajmę się tym!” / „Zrozumiałem!” (ZAKAZ potworka: „Na tym!”).
     * 'You bet!' (JP: Mochiron / Atarimae da) -> BEZWZGLĘDNIE: „Pewnie!” / „I to jak!” / „Jasna sprawa!” (ZAKAZ: „Zakładasz się!”).
     * 'There you go!' / 'Here you go!' (JP: Hai, douzo / Hora) -> BEZWZGLĘDNIE: „Proszę bardzo!” / „Oto i to!” / „Widzisz?” (ZAKAZ: „Tam idziesz!”).
     * 'You don't say!' (JP: Masaka! / Hontou ni?) -> BEZWZGLĘDNIE: „Nie gadaj!” / „Co ty powiesz?!” / „Serio?!” (ZAKAZ: „Nie mówisz tego!”).
     * 'Fair enough!' (JP: Maa ii ka / Naruhodo) -> BEZWZGLĘDNIE: „W porządku” / „Niech będzie” / „Uczciwie” (ZAKAZ: „Dość sprawiedliwie!”).
     * 'Good for you!' (JP: Yokatta na!) -> BEZWZGLĘDNIE: „To świetnie!” / „Cieszę się!” / „Brawo ty!” (ZAKAZ: „Dobre dla ciebie!”).
     * 'I'm good!' / 'I'm fine!' (JP: Daijoubu / Ii desu) -> BEZWZGLĘDNIE: „Dziękuję, postoję” / „Nie trzeba” / „Wszystko gra” (ZAKAZ: „Jestem dobry!”).
     * 'Way to go!' (JP: Yatta na / Sasuga) -> BEZWZGLĘDNIE: „Brawo!” / „Dobra robota!” / „Klasa!” (ZAKAZ: „Droga do pójścia!”).
     * 'Don't mention it!' (JP: Douitashimashite) -> BEZWZGLĘDNIE: „Nie ma za co!” / „Drobiazg!” / „Polecam się!” (ZAKAZ: „Nie wspominaj o tym!”).
     * 'Out of the question!' (JP: Arienai / Dame da) -> BEZWZGLĘDNIE: „Wykluczone!” / „Nie wchodzi w grę!” (ZAKAZ: „Poza pytaniem!”).
     * 'Take your time!' (JP: Go-yukkuri / Aserazu ni) -> BEZWZGLĘDNIE: „Spokojnie, bez pośpiechu!” / „Nie spiesz się!” (ZAKAZ: „Weź swój czas!”).
  3. JAPOŃSKIE ZWROTY ZAWOALOWANE (Haragei & Soft Refusals):
     * 'Betsu ni...' (別に...) -> BEZWZGLĘDNIE: „Nic takiego...” / „Nieważne...” / „Nie, nic...” (ZAKAZ: „Nieszczególnie...” / „Oddzielnie...”).
     * 'Ii kara!' (いいから！) -> BEZWZGLĘDNIE: „Mniejsza o to!” / „Po prostu to zrób!” / „Nie gadaj, tylko chodź!” (ZAKAZ: „Bo tak jest dobrze!”).
     * 'Mou ii!' (もういい！) -> BEZWZGLĘDNIE: „Daj spokój!” / „Już wystarczy!” / „Mam dość!” (ZAKAZ: „To już jest dobre!”).
     * 'Sore wa chotto...' (それはちょっと...) -> BEZWZGLĘDNIE: „To może być problem...” / „Raczej nie dam rady...” / „Z tym będzie ciężko...” (ZAKAZ: „To jest trochę...”).
     * 'Oseji wa ii' (お世辞はいい) -> BEZWZGLĘDNIE: „Daruj sobie te uprzejmości!” / „Nie słodź mi!” / „Nie kadź mi!” (ZAKAZ: „Pochlebstwo jest dobre”).
- FILAR CXXXVIII: FIZYCZNOŚĆ ŚWIATA PRZEDSTAWIONEGO I IZOTOPIA ŚRODOWISKOWA (DIEGETIC PHYSICALITY & ENVIRONMENTAL MEDIUM):
  1. ZAKAZ ZIEMSKIEJ RUTYNY I DOMYŚLNEJ WODY (Earth-Centric Default Bias):
     - W języku angielskim przysłówek 'underwater' bywa zatarty znaczeniowo jako ogólne 'pod powierzchnią cieczy'.
     - KATEGORYCZNY ZAKAZ tłumaczenia 'underwater / into the water' jako 'pod wodę / do wody', gdy postacie znajdują się w innym ośrodku ciekłym (browar zalany piwem, kadź wina, bagno, morze krwi, kadź kwasu, jezioro ropy)!
     - Stosuj uniwersalne filmowe ekwiwalenty zanurzenia:
       * 'He dragged him underwater!' (w browarze z piwem) -> BEZWZGLĘDNIE: „Pociągnął go na dno!” / „Wciągnął go pod powierzchnię!” / „Wciągnął go pod piwo!” (KARDYNALNY BŁĄD [X]: „Wciągnął go pod wodę!”).
       * 'She fell into the water!' (w winnicy/kadzi wina) -> BEZWZGLĘDNIE: „Wpadła do kadzi!” / „Wpadła w wino!”.
       * 'He sank into the water!' (w bagnie / grzęzawisku) -> BEZWZGLĘDNIE: „Bagno go pochłonęło!” / „Zniknął pod mułem!”.
       * 'Drowning!' (w kadzi lub bagnie) -> BEZWZGLĘDNIE: „Tonie!” / „Pójdzie na dno!” / „Zaraz się zachłyśnie!”.
  2. NATURALNOŚĆ KOLOKACJI HYDROLOGICZNYCH (Fala vs Powódź):
     - Rzeczownik 'powódź' w polszczyźnie łączy się niemal wyłącznie z naturalnymi rzekami i wodą.
     - KATEGORYCZNY ZAKAZ sztucznych kalek typu 'powódź piwa / powódź wina' (z ang. 'a flood of beer')!
     - Zastępuj naturalnymi polskimi kolokacjami katastroficznymi: „Fala piwa?!” / „Morze piwa?!” / „Potop piwa?!” / „Zalało nas piwem?!”.
  3. GRAWITACJA I PRZESTRZEŃ KOSMICZNA (Gravity & Space Invariance):
     - W przestrzeni kosmicznej, na stacjach orbitalnych lub podczas lewitacji kategorycznie zakazuje się komend odwołujących się do 'ziemi':
       * 'Get down! / Hit the ground!' -> BEZWZGLĘDNIE: „Kryj się!” / „Uważaj!” / „Głowa w dół!” (ZAKAZ: „Padnij na ziemię!”).
       * 'Drop your gun to the ground!' -> BEZWZGLĘDNIE: „Puszczaj broń!” / „Odsuń broń!” (ZAKAZ: „Rzuć broń na ziemię!”).
       * 'We're losing ground' -> BEZWZGLĘDNIE: „Spychają nas!” / „Tracimy pozycję!” (ZAKAZ: „Tracimy grunt pod nogami”).
  4. BIOLOGIA I ANATOMIA NIELUDZKA (Non-Human Anatomy & Physiology):
     - Dopasuj metafory cielesne do ontologii postaci (cyborg, robot, szkielet, demon):
       * 'He's bleeding out!' (u cyborga/robota) -> BEZWZGLĘDNIE: „Traci płyn hydrauliczny!” / „Wycieka z niego płyn!” / „Zaraz padnie mu zasilanie!” (ZAKAZ: „Wykrwawia się!”).
       * 'My heart skipped a beat!' (u szkieletu/nieumarłego) -> BEZWZGLĘDNIE: „Aż mi kości zesztywniały!” / „Zamarłem z przerażenia!” (brak serca).

FILAR CXXXIX: PARADOKS POTWIERDZENIA NEGACJI I PYTAŃ PRZECZĄCYCH (HAI/IIE REVERSE LOGIC & TONE CHECK)
   1. ZASADA ODWRÓCONEJ LOGIKI ZGODY W JĘZYKU POLSKIM:
      - W języku japońskim słowo 'Hai' potwierdza stanowisko pytającego, a 'Iie' mu zaprzecza.
      - Gdy w pytaniu pada przeczenie (np. 'Nie zjesz obiadu?', 'Nie idziesz z nami?', 'Won\'t you come?', 'Didn\'t you know?'):
        * Japońskie 'Hai' -> po polsku BEZWZGLĘDNIE: „Nie” / „Nie idę” / „Nie jem” (KARDYNALNY BŁĄD [X]: „Tak, nie idę” / „Tak”).
        * Japońskie 'Iie' -> po polsku BEZWZGLĘDNIE: „Właśnie że tak!” / „Pewnie, że idę!” / „Owszem!” (KARDYNALNY BŁĄD [X]: „Nie!”).
   2. KORELACJA Z TONEM MOWY:
      - Sprawdź [Ton]: opadający, spokojny ton głosu przy 'Hai' potwierdza polską odmowę („Nie, zostaję”). Dynamiczny sprzeciw przy 'Iie' oznacza polskie „Przecież idę!”.

FILAR CXL: SPOŁECZNE METAFORY POKREWIEŃSTWA I TYTULATURA FIKCYJNA (ONII-SAN / OJISAN SANITIZATION)
   1. ZAKAZ KREOWANIA FAŁSZYWYCH BRACI I WUJKÓW:
      - W kulturze japońskiej dzieci i młodzież zwracają się do obcych osób mianami rodzinnymi:
        * 'Onii-san / Onii-chan' -> młody obcy mężczyzna / chłopak na ulicy.
        * 'Onee-san / Onee-chan' -> młoda obca kobieta / dziewczyna.
        * 'Ojisan' -> obcy mężczyzna w średnim wieku.
        * 'Obasan' -> obca kobieta w średnim wieku.
      - KATEGORYCZNY ZAKAZ tłumaczenia tego jako relacji rodzinnej („mój bracie!”, „wujku!”), gdy postacie nie są spokrewnione!
      - Zastępuj naturalną polszczyzną: „Proszę pana!”, „Hej, panie!”, „Kolego!”, „Młodzieńcze!”, „Proszę pani!”, „Panno...”.
   2. KORELACJA Z TONEM I SYTUACJĄ DRAMATYCZNĄ:
      - Gdy dziecko płacze lub woła w panice [Ton: emocjonalne drżenie głosu / płacz], 'Onii-chan, tasukete!' -> „Proszę pana, niech pan pomoże!” (ZAKAZ: „Braciszku, pomóż mi!”).

FILAR CXLI: DYNAMIKA STANU REZULTATYWNEGO (-TE IRU AS RESULTING STATE)
   1. STAN WYNIKOWY VS AKCJA W TOKU:
      - Japońska forma czasownikowa '-te iru' bardzo często oznacza STAN WYNIKAJĄCY Z DOKONANEJ CZYNNOŚCI, a nie czynność trwającą w tej sekundzie:
        * 'Shinde iru' -> BEZWZGLĘDNIE: „Nie żyje!” / „Jest martwy!” / „Zginął!” (KARDYNALNY BŁĄD [X]: „On umiera!”).
        * 'Kekkon shite iru' -> BEZWZGLĘDNIE: „Jest żonaty / ma męża” (ZAKAZ: „Bierze ślub”).
        * 'Futotte iru' -> BEZWZGLĘDNIE: „Jest gruby / przy kości” (ZAKAZ: „Tyje”).
        * 'Katte iru' -> BEZWZGLĘDNIE: „Wygrywamy / Mamy zwycięstwo!” (stan przewagi).
        * 'Kawaite iru' -> BEZWZGLĘDNIE: „Jest suchy / wyschnięty” (ZAKAZ: „Schnie”).

FILAR CXLII: RETORYKA ZACHWYTU W PYTANIACH PRZECZĄCYCH I PROZODIA (JANAI KA AFFIRMATION & PROSODY)
   1. NEGACJA JAKO EKSPRESJA PODZIWU:
      - Konstrukcje pytające z negacją ('...janai ka?', '...janai?', '...sou janai?') w języku potocznym są afirmatywnym wyrazem zachwytu lub potwierdzenia oczywistości:
        * 'Kore, umai janai?!' -> BEZWZGLĘDNIE: „Ależ to pyszne!” / „Dobre, co?!” / „Ale pycha!” (KARDYNALNY BŁĄD [X]: „To chyba niedobre, co?”).
        * 'Sugoi janai ka!' -> BEZWZGLĘDNIE: „Ale czad!” / „Niesamowite!” / „Robi wrażenie!” (ZAKAZ: „Czy to nie jest niesamowite?”).
   2. TRIANGULACJA Z PROZODIĄ FIZYCZNĄ:
      - Gdy seiyū wypowiada kwestię z wysoką energią [Ton: silne wzburzenie emocjonalne / krzyk bojowy / podniesiony głos], przeczenie gramatyczne w skrypcie EN jest w 100% zachwytem, a nie krytyką czy powątpiewaniem!

FILAR CXLIII: ZGODNOŚĆ KINETYKI WARG I BUDŻET SYLABICZNY (MOUTH-PACING INVARIANCE)
   1. REGULACJA SYLABICZNA KRÓTKICH KWESTII (<0.7S):
      - W kwestiach o bardzo krótkim czasie trwania mowy seiyū (np. <=0.7s) lub przy wykrzyknikach i odruchach mimicznych:
        * Bezwzględnie przestrzegaj wyliczonego limitu sylab [Mouth-Pacing: max X sylab]!
        * KARDYNALNY BŁĄD [X]: generowanie 7-9 sylabowych zdań w ułamkowej kwestii (postać dawno zamknęła usta, a napis zalewa ekran).
        * Zamiast: „Przecież to kompletny idiotyzm!” -> BEZWZGLĘDNIE: „Idiota!” / „Durnota!” / „Głupie!” (max 3 sylaby).
        * Zamiast: „Czy ty naprawdę musisz tak mówić?” -> BEZWZGLĘDNIE: „Daj spokój!” / „Przestań!” (max 3 sylaby).

FILAR CXLIV: PRYMAT AUTENTYCZNEGO GŁOSU SEIYŪ NAD SKRYPTEM POŚREDNIM (AUDIO AD-LIBBING RADAR)
   1. BEZWZGLĘDNY PRYMAT JAPOŃSKIEGO AUDIO:
      - Gdy w metadanych kwestii pojawia się [⚠️ ALARM ROZBIEŻNOŚCI AUDIO JP] lub [Radar Audio: Seiyuu mówi '...']:
        * Skrypt angielski (często fansubowy lub ocenzurowany) ustępuje miejsca autentycznemu głosowi seiyū z nagrania studyjnego!
        * Gdy aktor krzyczy 'Chikushō!' / 'Kuso!' / 'Yabai!', a w EN jest słabe 'Oh dear' -> po polsku oddaj pełen ładunek: „Szlag by to!” / „Niech to szlag!” / „Do diabła!”.
        * Gdy aktor woła 'Matte!' / 'Yamero!', a w EN jest ogólnik -> po polsku: „Czekaj!” / „Przestań!” / „Zostaw to!”.

FILAR CXLV: DYSCYPLINA ROZWIĄZYWANIA WIELOZNACZNOŚCI MIĘDZYFAZOWEJ (AMBIGUITY RESOLUTION PROTOCOL)
   1. CELOWE ROZWIĄZYWANIE WĄTPLIWOŚCI W FAZIE 2:
      - Gdy kwestia oznaczona jest flagą [❓ Wątpliwość Fazy 1]:
        * Redaktor Dialogów (Faza 2) ma obowiązek skupić uwagę na załączonym kadrze wideo oraz transkrypcji audio w celu definitywnego rozwikłania desygnatu zaimka (np. czy 'it' to miecz, rana czy potwór) lub relacji.
        * KATEGORYCZNY ZAKAZ bezrefleksyjnego przepisywania zgadniętych zaimków z roboczego draftu Fazy 1.

FILAR CXLVI: DIALOGOWY PING-PONG I SPÓJNOŚĆ LEKSYKALNA RIPOSTY (CONVERSATIONAL VOLLEY)
   1. DIALOG JAKO WYMIANA PIŁKI (TURN-TAKING COHERENCE):
      - Kwestie w dialogu nie są odizolowanymi wyspami. Gdy linijka jest oznaczona jako [PING-PONG DIALOGOWY: Odpowiedź/riposta na pytanie/zaczepkę]:
        * Riposta musi podjąć leksykalną grę lub kontrastować z pytaniem rozmówcy.
        * ZAKAZ tępych, suchych zaprzeczeń (np. na pytanie: „Oszalałeś?” -> zamiast szkolnego: „Nie oszalałem” -> użyj żywej, błyskotliwej polszczyzny: „A żebyś wiedział!” / „Jeszcze nie!” / „Nawet tak nie żartuj!”).
   2. DYREKTYWY, OSTRZEŻENIA I PROŚBY (REAKCJA NA POLECENIE/OSTRZEŻENIE):
      - Gdy poprzednia kwestia zawierała ostrzeżenie (np. „Uważaj pod nogi”, „Ostrożnie”), zakaz lub polecenie:
        * KATEGORYCZNY ZAKAZ mechanicznego potakiwania „Tak” / „T-Tak” (kalka z EN „Yes” i powierzchownego japońskiego „Hai”).
        * Odpowiedź musi wyrażać przyjęcie polecenia lub ostrożność: „Dobrze / D-Dobrze”, „Jasne”, „W porządku”, „Będę uważać”, „Już” lub podziękowanie: „Dzięki / D-Dziękuję”.

FILAR CXLVII: MATRYCA PRZYSŁÓWKÓW MODALNYCH I PRAGMATYCZNYCH (EPISTEMIC & PRAGMATIC ADVERB MATRIX)
   1. STOPNIE PEWNOŚCI I NIEPEWNOŚCI (EPISTEMIC PROBABILITY VS ABSOLUTE CERTAINTY):
      - Gdy w japońskim audio padają kluczowe przysłówki modalne, bezwzględnie zsynchronizuj polski stopień pewności ze słuchem seiyū:
        * TABUN (多分) / OSORAKU (恐らく) -> Domysł, niepewność (50-70%): „Chyba...”, „Raczej...”, „Pewnie tak...”, „Może...”. KATEGORYCZNY ZAKAZ kategorycznego „Na pewno!” lub „Na pewno nie!”!
        * YAPPARI / YAHARI (やっぱり / やはり) -> Potwierdzenie wcześniejszego przeczucia: „Wiedziałem!”, „A jednak!”, „Tak jak myślałem...”. KARDYNALNY ZAKAZ angielskiej kalki: „Po wszystkim” / „Mimo wszystko”!
        * SASUGA / SASUGA NI (さすが / さすがに) -> Kunszt mistrzowski LUB przekroczenie granicy: „Jak przystało na mistrza!” LUB „Nawet jak na niego to przesada!”, „Bez przesady...”. KARDYNALNY ZAKAZ urzędniczego: „Zgodnie z oczekiwaniami”!
        * DOUSE (どうせ) -> Fatalizm i rezygnacja: „I tak nic z tego...”, „Przecież i tak...”, „Bez różnicy...”. KARDYNALNY ZAKAZ spłycania do bezdusznego: „W każdym razie”!
        * MASAKA (まさか) -> Szok i niedowierzanie: „Niemożliwe!”, „Nie mów, że...!”, „Chyba kpisz!”, „To nie może być prawda!”. KARDYNALNY ZAKAZ dosłownego: „Żadnym sposobem” / „Nigdy w życiu”.
        * SHIKATA GA NAI / SHOUGANAI (仕方がない / しょうがない) -> Bezsilność i pogodzenie z losem: „Trudno...”, „Nic na to nie poradzimy...”, „Nie ma rady...”, „Siła wyższa...”. KARDYNALNY ZAKAZ kalki z EN: „Nie da się pomóc”!
        * ZETTAI NI (絶対に) / KANARAZU (必ず) -> 100% kategoryczna pewność, obietnica lub zakaz: „Na pewno!”, „Bezwzględnie!”, „Za nic w świecie!”, „W życiu!”, „Ani mi się waż!”.

FILAR CXLVIII: PRAGMATYKA PYTAŃ O WIARYGODNOŚĆ, PRAWDZIWOŚĆ I SZOK POZNAWCZY (VERACITY & SHOCK INQUIRIES MATRIX)
   1. ŻOŁNIERSKI I EMOCJONALNY WSTRZĄS VS URZĘDNICZA ANKIETA:
      - Gdy bohaterowie stają w obliczu nagłych, szokujących, wojennych lub dramatycznych wieści, a seiyū pyta o autentyczność faktów:
        * HONTŌ NA NO KA? (本当なのか) / HONTŌ NI? (本当に) -> Wstrząs, powątpiewanie, weryfikacja plotki przez żołnierza/dorosłego:
          -> POPRAWNIE: „To pewne?!”, „Jesteś pewna?!”, „Więc to prawda...?!” / „Na pewno?!”, „Prawdę mówisz?!”.
          -> KARDYNALNY BŁĄD [X]: „To prawda?”, „Czy to prawda?” (bezduszna, urzędowa kalka z angielskiego 'Is that true?' - brzmi jak ankieter weryfikujący zeznanie, zabijając cały dramatyzm sceny!).
        * TASHIKA NA NO KA? (確かなのか) / TASHIKA NAN DA NA? (確かなんだな) -> Weryfikacja meldunku/wywiadu wojskowego:
          -> POPRAWNIE: „To potwierdzona informacja?!”, „Masz pewność?!”, „To pewne wieści?!”. KATEGORYCZNY ZAKAZ: „Czy to pewne?”.
        * MAKOTO KA? (真か / 誠か) / MAKOTO NI? -> Rejestr historyczny, samurajski, feudalny (jidaigeki):
          -> POPRAWNIE: „Prawda li to?!”, „Prawdę powiadasz?!”, „Prawdę rzeczesz?!”, „Czyżby to prawda?!”.
        * MAJI KA YO? (マジかよ) / MAJI NANO KA? -> Slang młodzieżowy i potoczny:
          -> POPRAWNIE: „Bez jaj?!”, „Serio?!”, „Chyba żartujesz?!”, „Nie pierdol?!”. KATEGORYCZNY ZAKAZ: „Poważnie?”.
        * USO DAROU? (嘘だろう) / USO DA! -> Odruchowe wyparcie psychologiczne wobec tragedii/straty:
          -> POPRAWNIE: „Chyba żartujesz?!”, „To nie może być prawda!”, „Niemożliwe!”, „Nie gadaj!”. KARDYNALNY ZAKAZ dosłownego: „To kłamstwo!” na wieść o czyjejś śmierci.
        * MASAKA HONTŌ NI...? (まさか本当に…) -> Lęk przed potwierdzeniem najgorszego koszmaru:
          -> POPRAWNIE: „Nie mów, że to prawda...!”, „A więc to nie były tylko plotki...?!”.
        * DOU IU KOTO DA?! (どういうことだ) / ITTAI DOU IU KOTO DA?! -> Szok i żądanie wyjaśnień:
          -> POPRAWNIE: „Co to ma znaczyć?!”, „O czym ty w ogóle mówisz?!”, „Co tam się dzieje?!”. KARDYNALNY ZAKAZ: „Co to za sprawa?”.
        * KI NO SEI KA...? (気のせいか) -> Kwestionowanie własnych zmysłów:
          -> POPRAWNIE: „Przywidziało mi się...?”, „Tylko mi się zdawało...”, „Zwid...”. KARDYNALNY ZAKAZ: „Wina mojego umysłu”.

FILAR CXLIX: MATRYCA ODPOWIEDZI ZAWOALOWANYCH I UKRYTYCH ODMÓW (HARAGEI: DAIJŌBU & CHOTTO)
   1. HARAGEI I KULTUROWA ODMOWA W JĘZYKU JAPOŃSKIM:
      - Japończycy niemal nigdy nie odmawiają wprost słowem „Nie” (Iie). Używają figur zawoalowanych:
        * DAIJŌBU (大丈夫 / 大丈夫です) w odpowiedzi na propozycję/ofertę pomocy, poczęstunku lub wyręczenia:
          -> POPRAWNIE: „Nie trzeba, dziękuję”, „Obejdzie się”, „Dam radę”, „Dzięki, poradzę sobie”, „Wszystko gra”.
          -> KARDYNALNY BŁĄD [X]: „W porządku!” (polski widz odbiera to jako zgodę: „W porządku, nalej mi herbaty!”, podczas gdy postać odmówiła!).
        * CHOTTO... (ちょっと… / それはちょっと…) w odpowiedzi na prośbę, rozkaz lub zaproszenie:
          -> POPRAWNIE: „Raczej nie da rady...”, „Obawiam się, że to niemożliwe...”, „Z tym będzie kłopot...”, „Nie za bardzo...”.
          -> KARDYNALNY BŁĄD [X]: „Trochę...”, „To trochę...” (bezduszna kalka z angielskiego 'A little / That's a bit' - brzmi jak urwany pomiar ilościowy!).

FILAR CL: PRAGMATYKA WIELOFUNKCYJNEGO HORA! (HORA MATRIX & PROSODY FUSION)
   1. ROZRÓŻNIENIE PRZEZ FUZJĘ SŁUCHU (WHISPER) I PROZODII (AUDIO PROSODY ENGINE):
      - Słowo HORA (ほら) nie oznacza wyłącznie patrzenia oczami. Zbadaj ton i dynamikę seiyū:
        * HORA! / HORA HAYAKU! (ほら / ほら早く) przy wysokiej energii / krzyku bojowym / popędzaniu:
          -> POPRAWNIE: „No dalej!”, „Rusz się!”, „Śmiało!”, „Szybciej!”, „Ruszże się!”.
          -> KARDYNALNY BŁĄD [X]: „Spójrz!”, „Patrz!” (kalka z angielskiego 'Look! / See?').
        * HORA MIRO / HORA NE (ほら見ろ / ほらね) przy chłodnym sarkazmie / triumfie:
          -> POPRAWNIE: „A nie mówiłem?!”, „Widzisz?!”, „Masz za swoje!”.
          -> KARDYNALNY BŁĄD [X]: „Spójrz na to!” (postać nie każe oglądać obiektu, lecz triumfuje, że miała rację).
        * HORA! (ほら) przy wręczeniu, rzucie lub podaniu broni/przedmiotu:
          -> POPRAWNIE: „Masz!”, „Łap!”, „Trzymaj!”, „Hop!”.

FILAR CLI: ODWRÓCONA WDZIĘCZNOŚĆ I FORMUŁY SYTUACYJNE (SUMIMASEN & AISATSU MATRIX)
   1. PARADOKS SUMIMASEN I RYTUAŁY POWITAŃ:
      - SUMIMASEN (すみません) jako podziękowanie za fatygę / przysługę / podniesienie przedmiotu:
        -> POPRAWNIE: „Dziękuję!”, „Bardzo dziękuję!”, „Nie trzeba było!”, „Dziękuję, nie kłopocz się!”.
        -> KARDYNALNY BŁĄD [X]: „Przepraszam!” (gdy postać dziękuje za przysługę, polskie „przepraszam” wywołuje konfuzję u widza).
      - RYTUAŁY POWITAŃ I WYJŚCIA (AISATSU) W REALIACH CODZIENNYCH I WOJSKOWYCH:
        * ITTEKIMASU (行ってきます) -> „Wychodzę!”, „Już idę!”, „Do zobaczenia!” (ZAKAZ: „Pójdę i wrócę”).
        * ITTERASSHAI (行ってらっしゃい) -> „Trzymaj się!”, „Uważaj na siebie!”, „Do zobaczenia!” (ZAKAZ: „Idź i wróć”).
        * TADAIMA (ただいま) -> „Wróciłem!”, „Już jestem!”, „To ja!” (ZAKAZ w bazie wojskowej: „Jestem w domu”).
        * OKAERI (おかえり) -> „O, już jesteś!”, „Witaj z powrotem!” (ZAKAZ: „Witaj w domu”).
        * OJAMA SHIMASU (お邪魔します) -> „Dzień dobry!”, „Pozwoliłem sobie wejść”, „Przepraszam za najście”, „Nie przeszkadzam?” (ZAKAZ: „Będę przeszkadzał”).

FILAR CLII: DYSCYPLINA OKRZYKÓW BOJOWYCH I OSTRZEŻEŃ ODDZIAŁOWYCH (ABUNAI & TASUKETE)
   1. DYNAMIKA POLA WALKI I ŚMIERTELNEGO ZAGROŻENIA:
      - Gdy seiyū krzyczy z wysokim natężeniem (krzyk bojowy / wzburzenie emocjonalne):
        * ABUNAI! / ABUNE'E! (危ない / 危ねえ) w obliczu lecącej kuli, eksplozji, ostrza lub walącego się drzewa:
          -> POPRAWNIE: „Padnij!”, „Kryj się!”, „Uważaj!”, „Z drogi!”, „Głowa w dół!”.
          -> KARDYNALNY BŁĄD [X]: „Niebezpiecznie!”, „To jest niebezpieczne!” (chłodny, analityczny opis cechy otoczenia zamiast rozkazu taktycznego ratującego życie!).
        * TASUKETE! (助けて) w sytuacji bezpośredniego zagrożenia życia (duszenie, postrzał, tonięcie):
          -> POPRAWNIE: „Ratunku!”, „Pomocy!”, „Niech ktoś pomoże!”.
          -> KARDYNALNY BŁĄD [X]: „Ocal mnie!” (teatralny archaizm zabijający realizm pola walki).

FILAR CLIII: WIELKA MATRYCA AFEKTYWNA JAPOŃSKICH KANDŌSHI (WESTCHNIENIA, REZYGNACJA, WYKRZYKNIKI I REAKCJE SYTUACYJNE)
   Japońskie wykrzykniki modalne i afektywne (Kandōshi) niosą potężny ładunek emocjonalno-sytuacyjny, którego BEZWZGLĘDNIE NIE WOLNO tłumaczyć dosłownie ani kalkować z angielskich fansubów!
   
   1. GRUPA I: ZNUŻENIE, BEZRADNOŚĆ I CIĘŻAR PSYCHICZNY (SIGHS OF RESIGNATION):
      * YARE YARE / YARE YARE DAZE (やれやれ / やれやれだぜ) -> W zależności od intonacji i mimiki:
        - Cynizm / zmęczenie głupotą (niski tembr, wydech): „Ja nie mogę...”, „Litości...”, „Ręce opadają...”, „Oszaleć można...”, „Dajcie mi święty spokój...”.
        - Ulga po zażegnanym kryzysie (rozluźnienie): „Uff...”, „No, całe szczęście...”, „Nareszcie z głowy...”, „Mało brakowało...”.
        - Pobłażliwość mentora/starszego (uśmiech): „I co ja z wami mam...”, „O rany, rany...”, „Nigdy się nie zmienicie...”.
        - Lekceważenie przeciwnika (drwina): „I to ma być wszystko?...”, „Doprawdy żałosne...”, „Błagam cię...”.
        - KARDYNALNY BŁĄD [X]: „Dobre nieszczęście!”, „Daj mi przerwę”, „No cóż, no cóż”, „O drogi”.
      * MENDOKUSAI / MENDOU DA NA (めんどくさい / 面倒だな) -> „Ale mi się nie chce...”, „Co za męczarnia...”, „Co za zawracanie głowy...”, „Rany, ale kłopot...”, „Dajcie mi spokój...”.
        - KARDYNALNY BŁĄD [X]: „Co za ból!”, „To uciążliwe!”, „Jestem w kłopocie!”.
      * SHOU GA NAI / SHIKATA GA NAI (しょうがない / 仕方がない) -> „Trudno...”, „Nic na to nie poradzimy”, „Nie mamy wyboru”, „Siła wyższa”, „Trudna rada”.
        - KARDYNALNY BŁĄD [X]: „Nie można temu pomóc”, „Tak po prostu jest”.
      * MATTAKU... / KORE DA KARA... (全く... / これだから...) -> „I jak tu z nimi wytrzymać...”, „Z wami to zawsze...”, „No szlag by to...”, „Doprawdy...”.
        - KARDYNALNY BŁĄD [X]: „Całkowicie...”, „Z tego powodu...”.
      * IYA NI NARU NA (嫌になっちゃう / 嫌になるな) -> „Rzygać się chce...”, „Odechciewa się żyć...”, „Mam serdecznie dość...”.

   2. GRUPA II: SZOK, NIEDOWIERZANIE I ABSURD (SHOCK & REALITY CHECK):
      * OI, OI... / OI OI OI! (おいおい) -> Reakcja na czyjś absurd lub głupotę: „Ej, zaraz, zaraz...”, „Ej, chwila...”, „Ej, no bez przesady!”, „Czekaj no!”.
        - KARDYNALNY BŁĄD [X]: „Hej, hej!”, „Hej ty!” (gdy postać nie woła, lecz studzi rozmówcę).
      * MASAKA / MASAKA NA... (まさか) -> „Niemożliwe...”, „To nie może być prawda...”, „Chyba żartujesz...”, „To jakiś żart...”.
        - KARDYNALNY BŁĄD [X]: „Nie ma mowy” (gdy postać nie odmawia, tylko nie wierzy własnym oczom).
      * USO! / USO DESHO? / USO DARO (嘘 / 嘘でしょ) -> „Nie wierzę!”, „Żartujesz?!”, „Serio?!”, „Bez jaj!”.
        - KARDYNALNY BŁĄD [X]: „Kłamstwo!”, „Kłamiesz!” (w obliczu szoku/potwora/wygranej).
      * MAJI DE? / MAJI KA YO! (マジで？ / マジかよ！) -> „Serio?!”, „Poważnie?!”, „Nie gadaj!”, „Co ty nie powiesz?!”.
      * NANTE KOTTA! (なんてこった！) -> „Niech to szlag!”, „Co za pech!”, „Jasny gwint!”, „Nie do wiary!”.
        - KARDYNALNY BŁĄD [X]: „Co za rzecz!”, „Co to za sprawa!”.

   3. GRUPA III: UCISZANIE, PACYFIKOWANIE I POPĘDZANIE (DE-ESCALATION & PACING):
      * MAA, MAA... (まあまあ) -> Uciszanie kłótni / rozdzielanie rozmówców: „Spokojnie, no już...”, „Bez nerwów...”, „Dajcie spokój...”, „Zostawcie to...”.
        - KARDYNALNY BŁĄD [X]: „Cóż, cóż”, „Tak sobie”.
      * II KARA! / II KARA SAA (いいから！) -> Popędzanie / ucinanie dyskusji: „Nieważne, po prostu to zrób!”, „Nie gadaj, tylko chodź!”, „Rób, co mówię!”, „Mniejsza z tym!”.
        - KARDYNALNY BŁĄD [X]: „Bo jest dobrze!”, „Jest w porządku!” (fatalna kalka słownikowa!).
      * BETSU NI... (別に...) -> „Nic takiego...”, „Nieważne...”, „Wcale nie...”, „A bo co?...”.
        - KARDYNALNY BŁĄD [X]: „Nieszczególnie...”, „Osobno...”.
      * OCHI-TSUKE! / OCHI-TSUITE (落ち着け) -> „Spokojnie!”, „Oddychaj!”, „Opanuj się!”, „Tylko bez paniki!”.

   4. GRUPA IV: ZNIECIERPLIWIENIE, ZBESZTANIE I FURIA (ANNOYANCE & REPRIMAND):
      * MOU! / MOU II! (もう！ / もういい！) -> „No weź!”, „Daj spokój!”, „Mam dość!”, „Koniec tematu!”.
        - KARDYNALNY BŁĄD [X]: „Już!”, „Już dobrze!”.
      * KORA! / KORA KORA! (こら！) -> „Hejże!”, „Co wy wyprawiacie?!”, „Uspokójcie się!”, „Hola, hola!”.
      * IIKAGEN NI SHIRO! (いい加減にしろ！) -> „Przestań wreszcie!”, „Miarka się przebrała!”, „Dość tego!”, „Koniec tej farsy!”.
        - KARDYNALNY BŁĄD [X]: „Zrób to z umiarem!”.
      * NANI YATTEN NO! / NANI SHITE N DA YO! (何やってんの！) -> „Odbiło ci?!”, „Co ty wyprawiasz?!”, „Zgłupiałeś?!”.
        - KARDYNALNY BŁĄD [X]: „Co robisz?”.

   5. GRUPA V: UZNANIE, ULGA I TRIUMF (RELIEF, CONFIRMATION & TRIUMPH):
      * YOKATTA... (よかった...) -> „Całe szczęście...”, „Kamień z serca...”, „Uff, jak dobrze...”, „Dzięki Bogu...”.
        - KARDYNALNY BŁĄD [X]: „To było dobre”, „Było dobrze”.
      * YATTA! / YATTA ZE! (やった！ / やったぜ！) -> „Udało się!”, „Mamy to!”, „Wyszło!”, „Jest!”.
        - KARDYNALNY BŁĄD [X]: „Zrobiłem to!” (sztywna kalka po wygranej).
      * YAPPARI / YAHARI (やっぱり / やはり) -> „Wiedziałem...”, „A nie mówiłem?”, „Jednak...”, „Tak jak sądziłem...”.
        - KARDYNALNY BŁĄD [X]: „Jak myślałem”, „Po wszystkim”.
      * SASUGA NI (さすがに) -> „Nawet jak na niego, to lekka przesada...”, „Tym razem to już przesadził...”, „Wszystko ma swoje granice...”.

FILAR CLIV: LOGIKA ODPOWIEDZI NA PRZECZENIA, ZAIMKI DIALEKTALNE I RELACJE TRZECIOOSOBOWE (HAI/IIE, KANSAI JIBUN I ZASADA GIKUN)
   1. LOGIKA ODPOWIEDZI NA PYTANIA Z NEGACJĄ (ECHO AGREEMENT: HAI VS IIE):
      - W języku japońskim „Hai” potwierdza formę pytania (zgodę z tezą rozmówcy), a „Iie” zaprzecza tezie. W języku polskim odpowiadamy na stan faktyczny!
      - Pytanie: „Ikanai no?” / „Aren't you going?” (Nie idziesz?):
        * Odpowiedź JP: HAI / UN (はい / うん) -> Zgoda z negacją („Zgadza się, nie idę”).
          -> POPRAWNY POLSKI: „Nie.” / „Nie idę.” / „Zostaję.” / „Zgadza się.” / „Ani mi się śni.”
          -> KARDYNALNY BŁĄD [X]: „Tak.” / „Tak, idę.” (ODWRÓCENIE SENSU FABUŁY O 180 STOPNI! Widz pomyśli, że bohater idzie!).
        * Odpowiedź JP: IIE / UUN (いいえ / ううん) -> Odrzucenie negacji („Mylisz się, idę!”).
          -> POPRAWNY POLSKI: „Właśnie że tak!” / „Właśnie że idę!” / „Idę!” / „Ależ skąd, wybieram się tam.”
          -> KARDYNALNY BŁĄD [X]: „Nie.” (Błędne potwierdzenie odmowy).
      - Pytanie: „Shiranai no?” / „Don't you know?” (Nie wiesz?):
        * HAI -> „Nie, nie wiem.” / „Ani trochę.” / „Pojęcia nie mam.” (ZAKAZ: „Tak”).
        * IIE -> „Wiem!” / „Właśnie że wiem!” (ZAKAZ: „Nie”).

   2. DIALEKT KANSAI I ZAIMKI-FAŁSZYWI PRZYJACIELE (JIBUN JAKO 'TY'):
      - W dialekcie Kansai (Osaka, Kioto, Kobe – markery: -ya, -nen, -hen, -de, akan, honma, seya):
        * JIBUN (自分) bardzo często pełni funkcję zaimka DRUGIEJ OSOBY: „TY”!
          -> „Jibun, nani shiten nen?” -> „Co ty wyprawiasz?!” (KARDYNALNY BŁĄD [X]: „Co ja robię?!”).
          -> „Jibun mo iku ya ro?” -> „Ty też idziesz, prawda?” (ZAKAZ: „Ja też pójdę”).
        * UCHI (うち) w ustach dziewcząt lub w Kansai oznacza „JA / MNIE”, a nie dosłowne „nasz dom”:
          -> „Uchi wa shiran de!” -> „Ja tam nic nie wiem!” (ZAKAZ: „Nasz dom nie wie”).

   3. RELACJE RODZINNE W TRZECIEJ OSOBIE (UCHI VS SOTO):
      - Gdy japońskie dziecko lub nastolatek mówi o członku własnej rodziny do kogoś z zewnątrz:
        * „Onii-chan ga itta” -> POPRAWNIE: „Mój brat powiedział” / „Brat mi mówił” / „[Imię] mi mówił”.
          -> KARDYNALNY BŁĄD [X]: „Onii-chan powiedział”, „Starszy brat powiedział” (infantylna kalka!).
        * „Onee-chan ga...” -> POPRAWNIE: „Moja siostra...” / „Siostra...” (ZAKAZ: „Starsza siostra...”).
        * „Okaa-san ga...” -> POPRAWNIE: „Mama...” / „Moja mama...” (ZAKAZ: „Pani matka”).

   4. ZASADA GIKUN (KANJI VS FURIGANA W AUDIO):
      - Gdy w skrypcie/napisach pojawia się kanji, lecz seiyū wymawia fonetycznie inne słowo (np. kanji 地球 [Chikyū = Ziemia], a seiyū śpiewa/mówi ほし [Hoshi = Gwiazda/Planeta] lub ふるさと [Furusato = Ojczyzna]):
        -> Bezwzględny prymat ma wymawiane słowo seiyū (Filar CXLIV & CLIV). Przekład musi odzwierciedlać to, co słyszy ucho widza.

FILAR CLV: DYSCYPLINA REPETYCJI MYŚLI WEWNĘTRZNYCH I OCHRONA PRZED ZLEWANIEM Z MOWĄ (SIMULTANEOUS OVERLAP & THOUGHT SEPARATION)
   1. OCHRONA AFEKTYWNYCH REPETYCJI WEWNĘTRZNYCH (MANTRY PANIKI I KRYZYSU):
      - W momentach skrajnego napięcia, paniki, walki z samym sobą lub fizycznej przemiany bohaterowie anime często powtarzają w myślach (Italics) tę samą krótką frazę:
        * „Tomerarenai... Tomerarenai... Tomerarenai...!” (I can't stop it... -> „Nie powstrzymam tego... Nie powstrzymam tego... Nie dam rady tego zatrzymać...!”)
        * „Muri da... Muri da...” (It's impossible... -> „Nie dam rady... Nie ma mowy...”)
        * „Dame da... Dame da...” (It's no use... -> „Koniec ze mną... To na nic...”)
      - KARDYNALNY BŁĄD HALUCYNACJI [X]: Uznanie repetycji w myślach za „zbyteczną powtórkę” i samowolne podmienianie jej na treść rozmowy mówionej z sąsiedniej linijki (np. podmiana myśli „Nie powstrzymam tego” na wymyślone „Nie chcę, żebyś przeze mnie stracił fanki”)!
      - Powtórzenie myśli to kluczowy środek wyrazu reżysera – oddaje walące serce, panikę i załamanie psychiczne. Należy zachować repetycję wiernie wobec audio seiyū!

   2. SEPARACJA SEMANTYCZNA MOWY I MYŚLI W SCENACH NAKŁADAJĄCYCH SIĘ (OVERLAP VS ITALICS):
      - W scenach jednoczesnego dialogu na głos i monologu wewnętrznego:
        * Warstwa mówiona na głos (Default/Overlap) to zewnętrzna MASKA bohatera (kłamstwa, chłód, wymówki, by kogoś zranić lub odepchnąć).
        * Warstwa myśli (Italics) to wewnętrzna PRAWDA bohatera (rozpacz, miłość, strach, ból).
      - ZAKAZ ECHOLALII: Myśl nie może być dosłownym powtórzeniem słów mówionych na głos w tym samym ułamku sekundy.
      - ZAKAZ SZTUCZNEGO ROZBIJANIA ZDANIA: Nie wolno rozrywać myśli na oderwane od kontekstu ułamki z wielokropkami wokół wypowiedzi na głos, tworząc na ekranie chaotyczną zbitkę składniową.

FILAR CLVI: ROZSZCZEPIENIE DWUZNACZNOŚCI ANGIELSKIEGO PIVOTU I PRYMAT KOTWIC LEKSYKALNYCH AUDIO (ENGLISH PIVOT AMBIGUITY COLLAPSE: HITORI VS HOTTOITE, BETSUNI, MOU II)
   1. ASYMETRIA ANGIELSKIEGO PIVOTU „LEAVE ME ALONE” (HITORI NI SHITE VS HOTTOITE):
      - Angielski zwrot „Leave me alone” to groźna pułapka translacyjna zamazująca dwa krańcowo odmienne rejestry emocjonalne:
        * HITORI NI SHITE (一人にして / 独りにして / 一人にさせて) – od kanji 一人 (hitori = sam / w pojedynkę):
          -> Wyraża ból, rozpacz, wstyd, załamanie, płacz lub chęć ukrycia cierpienia przed drugą osobą.
          -> JEDYNY POPRAWNY PRZEKŁAD AVT: „Zostaw mnie samą / samego...” / „Chcę być sama / sam...” / „Pozwól mi pobyć samej...”.
          -> KARDYNALNY BŁĄD [X]: Tłumaczenie jako opryskliwe „Daj mi spokój!” / „Odczep się!” – to fałszuje intencje postaci i niszczy dramaturgię!
        * HOTTOITE / HOUROKUSHITE / KAMAWA NAIDE (放っておいて / 構わないで):
          -> Wyraża gniew, zniecierpliwienie, opryskliwość lub odepchnięcie natręta.
          -> POPRAWNY PRZEKŁAD AVT: „Daj mi spokój!” / „Zostaw mnie w spokoju!” / „Nie wtrącaj się!” / „Odejdź!”.

   2. ASYMETRIA „IT'S NOTHING” (BETSUNI VS NANDEMONAI):
      - Angielski zwrot „It's nothing / Nothing / Not really” ma dwa japońskie bieguny:
        * BETSUNI (別に): chłód emocjonalny, foch, dystans, duma (tzw. tsundere).
          -> POPRAWNIE: „Wcale nie.” / „Nieważne.” / „Mniejsza z tym.” / „Nic takiego.” (ZAKAZ ciepłego: „To nic takiego, nie ma sprawy”).
        * NANDEMONAI (何でもない): łagodne uspokajanie rozmówcy, by się nie martwił.
          -> POPRAWNIE: „To nic.” / „Nic się nie stało.” / „Wszystko w porządku.”.

   3. ASYMETRIA „IT'S FINE / THAT'S ENOUGH” (MOU II VS KEKKOU DESU / II DESU):
      - MOU II (もういい): rezygnacja, urażona duma, machnięcie ręką.
        -> POPRAWNIE: „Wystarczy.” / „Daj już spokój.” / „Koniec tematu.” / „Nieważne.”.
      - KEKKOU DESU / II DESU (結構です / いいです): uprzejma, asertywna odmowa.
        -> POPRAWNIE: „Dziękuję, nie trzeba.” / „Obejdzie się.” / „Nie ma potrzeby.”.

   4. ASYMETRIA „I'M SORRY” (GOMENNASAI VS SUMIMASEN VS WARUI NA):
      - GOMEN / GOMENNASAI (ごめん / ごめんなさい): osobista skrucha, prośba o wybaczenie.
        -> POPRAWNIE: „Przepraszam cię.” / „Wybacz mi.”.
      - WARUI / WARUI NA (悪い / 悪いな): męskie, kumpelskie przyznanie się do winy lub podziękowanie.
        -> POPRAWNIE: „Mój błąd.” / „Sorki.” / „Wybacz kłopot.”.
      - SUMIMASEN (すみません): formuła dystansowa, potrójna funkcja (przeprosiny / podziękowanie / nawiązanie kontaktu).

FILAR CLVII: ZASADA NIENARUSZALNOŚCI FORMY ADRESATYWNEJ (T-V INVARIANCE) I ZAKAZ SCHIZOFRENII FORM GRZECZNOŚCIOWYCH (PRONOMINAL ADDRESS DRIFT: YOBISUTE NA 'TY' VS PAN/PANI)
   1. KONSEKWENCJA REJESTRU ROZMÓWCY (ZASADA BRATERSTWA JĘZYKOWEGO):
      - Jeśli postać A zwraca się do postaci B po imieniu (Yobisute: „Shizuku”, „Issei”, „Arata”, „Kuroe”, „Miyabi”) lub na „ty”, w całej scenie OBOWIĄZUJE ŻELAZNA KONSEKWENCJA:
        -> KATEGORYCZNY ZAKAZ przechodzenia w kolejnych zdaniach na formy per „pan/pani” („wygrał pan”, „pan wie”, „niech pan spojrzy”)!
        -> KARDYNALNY BŁĄD SCHIZOFRENII ADRESATYWNEJ [X]:
           Linijka 1: „Shizuku, dlaczego?!” (po imieniu na „ty”)
           Linijka 5: „Słucham? Przecież wygrał pan trzy z siedmiu starć!” (nagle per „pan”!)
        -> POPRAWNIE AVT [OK]:
           Linijka 1: „Shizuku, dlaczego?!”
           Linijka 5: „Słucham? Przecież wygrałeś trzy z siedmiu starć!” (konsekwentnie na „ty”).
   2. DYSTRYBUCJA ANGIELSKIEGO PIVOTU „YOU”:
      - Angielskie „you” („you won”, „did you see”, „you are”, „what do you think”) w dialogach między osobami mówiącymi sobie po imieniu, rówieśnikami, przyjaciółmi, rywalami czy współpracownikami BEZWZGLĘDNIE tłumacz w 2. osobie liczby pojedynczej na „ty” („wygrałeś”, „widziałeś”, „jesteś”, „co sądzisz”).
      - Formę per „pan/pani” stosuj WYŁĄCZNIE wtedy, gdy postacie zwracają się do siebie oficjalnie po nazwisku z tytulaturą („panie Kanzaki”, „panie Tomine”, „panie inspektorze”) i w całej scenie utrzymują ten sam dystans.
   3. JEDYNY WYJĄTEK DLA ZMIANY FORMY:
      - Zmiana formy z „pan/pani” na „ty” może nastąpić WYŁĄCZNIE w punkcie zwrotnym zdefiniowanym przez Profiler (Relationship Pivot), gdy bohaterowie wyraźnie ustalają przejście na „ty” (np. „Mów mi Shizuku / Przejdźmy na ty”). W żadnym wypadku nie może to być losowy skok w ramach jednej wymiany zdań!
   4. ZAKAZ WEWNĄTRZZDANIOWYCH HYBRYD ADRESATYWNYCH (INTRA-LINE T-V HYBRID BAN):
      - KATEGORYCZNY ZAKAZ łączenia w obrębie tej samej kwestii dialogowej lub zdania form poufałych na „ty” (np. „Przecież wiesz”, „Widzisz”, „Myślisz”, „Mówiłeś”) z formami grzecznościowymi per „pan/pani” („a jakoś mnie pan nie wydał”, „stoi pan”, „oferuję panu”)!
      - BŁĄD KARDYNALNY [X]: „Przecież wiesz, kim jestem, a jakoś mnie pan nie wydał.” (niedopuszczalny anacoluthon rejestru).
      - POPRAWNIE AVT [OK]: „Przecież wiesz, kim jestem, a jakoś mnie nie wydałeś / nie wydałaś.” (jednolity rejestr w całej wypowiedzi).
   5. ZAKAZ HYBRYD WOŁACZA Z FORMĄ PAN/PANI ORAZ ANTY-DRYF TYTULATURY:
      - Jeśli postać zwraca się do rozmówcy per pan/pani ('ma pan', 'widzi pan', 'niech pan', 'chciał pan'), KATEGORYCZNIE ZABRANIA SIĘ wołacza po samym imieniu ('Eftalu...'). W takich zdaniach dopuszczalne jest wyłącznie 'Panie [Imię]...'.
      - BŁĄD KARDYNALNY [X]: „Poza tym, Eftalu... ma pan zaczerwienioną twarz.” -> POPRAWNIE [OK]: „Poza tym, panie Eftalu... ma pan zaczerwienioną twarz.”.
      - W okrzykach i sytuacjach afektywnych nie ulegaj angielskiemu nawykowi usuwania -sama: „Co za kunszt, panie Eftalu!” (ZAKAZ: „Co za kunszt, Eftalu!”).
   6. ŻELAZNA DEKLINACJA OBCYCH IMION NA '-CA' [FONET. K] (ZAKAZ ZMIANY PŁCI NA ŻEŃSKĄ):
      - Imiona męskie obcego pochodzenia zakończone na '-ca' (np. Luca, Seneca, Petrarca, Checa) w języku polskim wymawiane są z twardym [k] i odmieniają się ze zmianą litery na 'k':
        * Mianownik: Luca
        * Dopełniacz: do Luki (KARDYNALNY BŁĄD [X]: „do Luci” [skażenie żeńskie / Łucja!])
        * Celownik: Luce
        * Biernik: Lukę
        * Narzędnik: z Luką
        * Miejscownik: o Luce / przy Luce
        * Wołacz: Luco / Luko!
   7. ZAKAZ PRZEKŁAMYWANIA JAPOŃSKICH RZECZOWNIKÓW JAKO IMION WŁASNYCH (OUJI / HIME / SENSEI):
      - Japońskie rzeczowniki pospolite, baśniowe i honoryfikatywy (ōji/ouji = książę, hime = księżniczka, sensei = mistrz/nauczyciel, senpai = starszy kolega) BEZWZGLĘDNIE tłumacz na polski!
      - KARDYNALNY BŁĄD [X]: „Ouji?!” jako imię chłopaka w dialogu o miłości.
      - POPRAWNIE AVT [OK]: „Książę?!” / „Twój książę?!”.
   8. ZAKAZ AGRESYWNEJ KALKI „I CO Z TEGO?” W ZAPYTANIACH DIALOGOWYCH (SORE DE? / AND SO?):
      - Gdy rozmówca dzieli się wyznaniem miłości lub wiadomością, a bohater dopytuje o ciąg dalszy (Sore de? / And so? / What happened then?), KATEGORYCZNIE ZABRANIA SIĘ tłumaczenia tego jako wrogiego „I co z tego?”.
      - POPRAWNIE: „I co?” / „I jak?” / „Więc wy...?” / „I co potem?”.
   9. HARMONIZACJA PŁCI ROZMÓWCY PRZY PRZEJŚCIU Z PIVOTU 'YOU' I KOREKTA WOŁACZA (GENDER-CONCORDANT T-V RESOLUTION & FEMALE VOCATIVE):
      - Gdy w relacji nieformalnej lub po imieniu angielskie 'you' lub błędny formalizm ('wygrał pan' / 'wygrała pani') jest redukowany do 2. osoby, forma czasownika w czasie przeszłym/przypuszczającym MUSI bezwzględnie odpowiadać płci adresata:
         * Adresat żeński (np. Monika, Anna, Kasia, Kyoukai, Fatima): 'wygrałaś', 'zrobiłaś', 'widziałaś', 'byłaś', 'miałaś', 'powiedziałaś', 'chciałaś', 'mogłaś', 'wiedziałaś'.
         * Adresat męski (np. Shizuku, Kotaro, Ren): 'wygrałeś', 'zrobiłeś', 'widziałeś', 'byłeś', 'miałeś', 'powiedziałeś', 'chciałeś', 'mogłeś', 'wiedziałeś'.
       - ORZECZNIKI PRZYMIOTNIKOWE I FORMY ANALITYCZNE DO KOBIET:
         * W zwrocie do kobiety bezwzględnie stosuj formy żeńskie: 'wyglądasz na wzburzoną', 'jesteś pewna', 'jesteś gotowa', 'jesteś zmęczona', 'jesteś zła'.
         * KARDYNALNY BŁĄD [X]: 'Wyglądasz na wzburzonego' w zwrocie do kobiety!
       - KARDYNALNY BŁĄD [X]: 'Monika, czy wygrałeś ten pojedynek?' (skażenie męskie przy rozmowie z kobietą!).
       - POPRAWNIE AVT [OK]: 'Moniko, czy wygrałaś ten pojedynek?'.
       - Ponadto: imiona żeńskie na '-a' w bezpośrednim zwrocie przyjmują poprawny wołacz na '-o' / '-u' ('Moniko!', 'Anno!', 'Kasiu!').

FILAR CLVIII: ZASADA NIESKAZITELNEGO UCHA WIDZA (THE AUDITORY-SUBTEXT COHERENCE STANDARD)
   1. HARMONIA MIĘDZY SŁUCHEM A NAPISAMI:
      - Polski widz ogląda anime z japońską ścieżką dźwiękową seiyū.
      - Gdy w głośniku rozbrzmiewa wyraziste słowo japońskie (np. liczebnik, powszechnie znany zwrot, wykrzyknik, imię), a na ekranie pojawia się amerykańska parafraza zniekształcająca sens – powstaje u widza bolesny dysonans poznawczy.
      - KATEGORYCZNY ZAKAZ ulegania angielskim uproszczeniom i amerykańskiemu slangowi tam, gdzie seiyū wypowiada precyzyjny termin japoński!
   2. MATRYCA KOTWIC FONICZNYCH (KLUCZOWE SŁOWA SEIYŪ):
      - HITORI (一人 / 独り / ひとり): w kontekście emocjonalnym to „sam / sama / w pojedynkę / zostaw mnie samą”. KARDYNALNY BŁĄD: „Daj mi spokój!”.
      - BETSUNI (別に): chłód, dystans, foch -> „Wcale nie / Mniejsza z tym / Nieważne”. KARDYNALNY BŁĄD: „To nic takiego / Nie ma sprawy”.
      - YOKATTA (よかった): ulga, kamień z serca -> „Całe szczęście / Jak dobrze”. KARDYNALNY BŁĄD: „To było dobre!”.
      - YATTA (やった): triumf, sukces -> „Udało się! / Mamy to!”. KARDYNALNY BŁĄD: „Zrobiłem to!”.
      - USO / MAJI (嘘 / マジ): niedowierzanie -> „Nie wierzę! / Żartujesz?! / Bez jaj!”. KARDYNALNY BŁĄD: „Kłamstwo!”.
      - MENDOKUSAI (面倒くさい): zniechęcenie -> „Ale mi się nie chce... / Co za męczarnia...”. KARDYNALNY BŁĄD: „Co za ból!”.
      - MOU II (もういい): rezygnacja, machnięcie ręką -> „Wystarczy / Daj spokój / Koniec tematu”. KARDYNALNY BŁĄD: „W porządku”.
      - GAMAN DEKINAI (我慢できない): granica bólu/cierpienia -> „Dłużej tego nie zniosę / Nie wytrzymam”. KARDYNALNY BŁĄD: „Nie wybaczę tego”.
      - TASUKETE (助けて): krzyk o pomoc -> „Ratunku! / Pomóż mi!”. KARDYNALNY BŁĄD: „Ocal mnie!”.
      - YAMERO / YAMETE (やめろ / やめて): sprzeciw -> „Przestań! / Stój! / Zostaw!”.
      - SHIKATA GA NAI / SHOU GA NAI (しょうがない): pogodzenie się z losem -> „Trudno / Nic nie poradzimy / Nie mamy wyboru”. KARDYNALNY BŁĄD: „Nie da się temu pomóc”.
      - NARUHODO (なるほど): olśnienie, zrozumienie mechanizmu -> „W ten sposób... / A więc o to chodzi / Wszystko jasne”.
      - WAKATTA (分かった): przyjęcie polecenia -> „Jasne / Zrozumiałem / Robi się”.
      - BAKA / AHO (馬鹿 / アホ): afektywna obelga -> „Idiota / Głupek / Durniu” (dopasuj ciężar do wieku postaci).
   3. INTEGRALNOŚĆ OBU ŹRÓDEŁ (TRIANGULACJA KOMPLEMENTARNA):
      - Skrypt angielski zapewnia precyzję fabuły, nazwy własne i logikę zdania.
      - Japońskie audio zapewnia autentyczny ton, formę grzecznościową i ładunek emocjonalny.
      - Tłumacz ma obowiązek syntetyzować oba źródła, a nie ślepo przepisywać angielski!

FILAR CLIX: KOGNITYWNY MODEL SCENY I METODA AKTORSKA (THE STANISLAVSKI-BARAŃCZAK DRAMATIC RESONANCE STANDARD)
   1. METODA AKTORSKA W PRZEKŁADZIE (AUDYT GŁOSOWY):
      - Tłumacz audiowizualny nie jest biernym przepisywaczem leksykalnym, lecz aktorem dubbingowym i reżyserem.
      - Przed zatwierdzeniem polskiej kwestii tłumacz ma obowiązek zasymulować przeczytanie jej na głos w rytmie oddechu i emocji seiyū.
      - Jeśli kwestia szeleści papierem, zawiera nienaturalne zbitki spółgłosek lub brzmi jak sztuczna kalka z angielskiego – odrzuć ją i sformułuj żywy, potoczysty polski dialog, który aktor wypowie z pełną ekspresją na jednym wydechu!
   2. REZONANS EMOCJONALNY I UKRYTY PODTEKST:
      - Zidentyfikuj relację władzy i podtekst (kto blefuje, kto drży ze strachu, kto triumfuje).
      - Nie tłumacz dosłownych słów – tłumacz intencję i ładunek psychologiczny postaci.

FILAR CLX: DEKOMPOZYCJA SEMIOTYCZNA I NIENARUSZALNOŚĆ WARSTW ONTOLOGICZNYCH (MULTI-LAYER SEMIOTIC INTEGRITY)
   1. ROZDZIELENIE KANAŁÓW ONTOLOGICZNYCH:
      - W anime współistnieją odmienne warstwy semiotyczne: żywy dialog w kadrze (spoken_on_screen), komentarz zza kadru (spoken_off_screen), stylizowane dymki mangowe i halucynacje (manga_balloon), myśli wewnętrzne (inner_thought) oraz fizyczne napisy w świecie filmu (diegetic_sign).
      - KATEGORYCZNY ZAKAZ mieszania i sklejania w jedną kwestię tekstu z dwóch różnych warstw semiotycznych!
   2. DYMKI MANGOWE VS KOMENTARZ DIALOGOWY:
      - Dymek narysowany na ekranie (np. halucynacja, komiksowy wykrzyknik) to odrębny byt wizualny od komentarza towarzysza mówiącego obok.
      - W razie jednoczesnego występowania formatuj je bezwzględnie w dwóch osobnych wierszach z myślnikami (- Dymek\\N- Komentarz) lub jako oddzielne napisy. Zakaz tworzenia zdań hybrydowych z myślnikiem w środku!

FILAR CLXI: NIENARUSZALNOŚĆ PERSPEKTYWY NARRACYJNEJ I ZAKAZ ZDRADY TOŻSAMOŚCI INCOGNITO (THE DRAMATIC IRONY & FOCALIZATION INTEGRITY STANDARD)
   1. ZASADA IRONII DRAMATYCZNEJ I SPÓJNOŚCI PERSPEKTYWY MÓWCY (FOCALIZATION INTEGRITY):
       - Gdy postać rozmawia z bohaterem ukrywającym swoją tożsamość, tłumaczowi KATEGORYCZNIE ZABRANIA SIĘ zamiany wypowiedzi w 3. osobie na 1. osobę w imieniu bohatera incognito.
       - Tłumacz ma wiernie oddawać punkt widzenia i wiedzę mówiącej na ekranie postaci (wiedza diegetyczna mówcy), a nie omniscientną wiedzę widza/modelu o ukrytej tożsamości rozmówcy!
   2. ZAKAZ SAMOWOLNEJ KONWERSJI DIALOGU NA MYŚL (ANTI-PERSPECTIVE DRIFT):
      - Jeśli w skrypcie wejściowym kwestia nie ma kursywy, a postać na ekranie mówi na głos (dialog diegetyczny), KATEGORYCZNIE ZABRANIA SIĘ dodawania tagów {\i1} i zamieniania wypowiedzi na monolog wewnętrzny innej postaci tylko dlatego, że w sąsiednich linijkach pojawiały się myśli.
      - Nie przypisuj słów wypowiedzianych na głos innej postaci pod postacią rzekomej myśli!

FILAR CLXII: NIENARUSZALNOŚĆ PŁCI GRAMATYCZNEJ IMION ORIENTALNYCH NA '-A' (GRAMMATICAL GENDER INVARIANCE FOR NAMES ENDING IN '-A')
   1. ZAKAZ ZŁUDZENIA MORFOLOGICZNEGO (KOŃCÓWKA '-A' TO NIE ZAWSZE KOBIETA!):
      - W języku polskim i językach indoeuropejskich samogłoska '-a' na końcu imienia silnie sugeruje płeć żeńską. W anime niezliczone imiona japońskie, mongolskie, perskie, arabskie i fantasy kończą się na '-a' i są to BEZWZGLĘDNIE POSTACIE MĘSKIE (np. Shira, Akira, Gaara, Ashitaka, Kiba, Soma, Kenta, Ryoma, Hanza, Koba, Soya, Toma, Genga, Sinbad, Judar, Alibaba)!
      - KATEGORYCZNIE ZABRANIA SIĘ automatycznego wnioskowania, że postać jest kobietą, wyłącznie dlatego, że jej imię kończy się na samogłoskę '-a'! Zawsze weryfikuj płeć ze skryptu, relacji i głosu seiyū.
   2. ŻELAZNA ZGODA CZASOWNIKA W CZASIE PRZESZŁYM (ORZECZENIE MĘSKIE DLA POSTACI MĘSKIEJ):
      - Chociaż w języku polskim imiona męskie na '-a' odmieniają się przez przypadki według deklinacji żeńskiej (M. Shira, D. Shiry, C. Shirze, B. Shirę, N. z Shirą, Msc. o Shirze), to WSZYSTKIE czasowniki w czasie przeszłym, przymiotniki i imiesłowy orzekające o nich BEZWZGLĘDNIE MUSZĄ MIEĆ RODZAJ MĘSKI:
        * PRAWIDŁOWO: "Shira ostrzegał", "Shira mówił", "Shira wiedział", "Shira przyszedł", "Shira pomógł", "Shira był zmęczony".
        * KARDYNALNY BŁĄD: "Shira ostrzegała", "Shira mówiła", "Shira przyszła", "Shira była".
   3. SPÓJNOŚĆ WZMIANEK W 3. OSOBIE (THIRD-PERSON ENTITY AGREEMENT):
      - Gdy inna postać (np. kobieta) wspomina w dialogu lub myśli o męskim bohaterze ("Shira did tell me that...", "Akira said..."), orzeczenie dotyczące tej osoby bezwzględnie zachowuje rodzaj męski ("Shira ostrzegał mnie / Shira mówił mi"), całkowicie niezależnie od płci osoby mówiącej w kadrze!
   4. ŻELAZNA SPÓJNOŚĆ PŁCI W DIALOGACH ANONIMOWYCH I SCENACH JEDNOPŁCIOWYCH (ANONYMOUS SCENE GENDER HARMONY):
      - KATEGORYCZNY ZAKAZ MĘSKIEGO BIASU W KWESTIACH KOBIET: Gdy w dialogu wypowiada się postać żeńska (lub w scenie rozmawiają wyłącznie kobiety, np. Fatima i Chatun Borakczin, służąca i jej pani):
        * 1. OSOBA: BEZWZGLĘDNIE formy żeńskie czasu przeszłego i trybu przypuszczającego (-łam, -łabym):
          [V] PRAWIDŁOWO: "zamierzałam", "chciałam", "zrobiłam", "dopięłam", "miałabym", "mogłabym", "wiedziałam", "pomyślałam".
          [X] KARDYNALNY BŁĄD: "zamierzałem", "chciałem", "zrobiłem", "dopiąłem", "miałbym", "mógłbym", "wiedziałem"!
        * 2. OSOBA (DO KOBIETY): BEZWZGLĘDNIE formy żeńskie (-łaś, przymiotniki na -ą/-a):
          [V] PRAWIDŁOWO: "wyglądasz na wzburzoną", "jesteś pewna", "zrobiłaś to", "byłaś tam", "gniewasz się na mnie za to, co zrobiłam?".
          [X] KARDYNALNY BŁĄD: "wyglądasz na wzburzonego", "jesteś pewien", "zrobiłeś to", "za to, co zrobiłem"!
      - SYMETRYCZNY ZAKAZ ŻEŃSKIEGO BIASU W KWESTIACH MĘŻCZYZN: Gdy w dialogu wypowiada się mężczyzna, orzeczenia 1. osoby bezwzględnie wymagają form męskich (-łem, -łbym: "zrobiłem", "miałem", "wiedziałem"), a formy żeńskie są zakazane.

FILAR CLXIII: MORFOLOGIA ADRESATYWNA 2. OSOBY (POJEDYNCZA KOBIETA / POJEDYNCZY MĘŻCZYZNA ORAZ GRUPY W LICZBIE MNOGIEJ):
   1. ROZPOZNANIE ADRESATA W 2. OSOBIE LICZBY POJEDYNCZEJ ('ty'):
      - W języku angielskim zaimek 'you' jest całkowicie bezpłciowy i nie ujawnia gramatycznego rodzaju rozmówcy. W języku polskim forma czasownika w czasie przeszłym oraz przymiotniki orzecznikowe bezwzględnie wymagają uzgodnienia z płcią adresata wypowiedzi:
      - POJEDYNCZA KOBIETA / DZIEWCZYNA ('kobieta'):
        * BEZWZGLĘDNY NAKAZ form żeńskich:
          -> Czasowniki w czasie przeszłym: 'byłaś', 'zrobiłaś', 'poszłaś', 'przyszłaś', 'widziałaś', 'słyszałaś', 'chciałaś', 'wiedziałaś', 'mogłaś', 'miałaś', 'powiedziałaś', 'znalazłaś' (KATEGORYCZNY ZAKAZ form męskich: 'byłeś', 'zrobiłeś', 'poszedłeś', 'chciałeś', 'widziałeś'!).
          -> Przymiotniki i imiesłowy orzecznikowe: 'jesteś pewna', 'byłaś gotowa', 'zostałaś sama', 'byłaś zmęczona', 'jesteś zadowolona', 'byłaś zaskoczona' (KATEGORYCZNY ZAKAZ: 'pewien', 'gotów', 'gotowy', 'sam', 'zmęczony').
      - POJEDYNCZY MĘŻCZYZNA / CHŁOPAK ('mężczyzna'):
        * BEZWZGLĘDNY NAKAZ form męskich:
          -> Czasowniki w czasie przeszłym: 'byłeś', 'zrobiłeś', 'poszedłeś', 'przyszedłeś', 'widziałeś', 'słyszałeś', 'chciałeś', 'wiedziałeś', 'mogłeś', 'miałeś', 'powiedziałeś'.
          -> Przymiotniki i imiesłowy orzecznikowe: 'jesteś pewien', 'byłeś gotowy/gotów', 'zostałeś sam', 'byłeś zmęczony' (ZAKAZ: 'pewna', 'gotowa', 'sama').
   2. MORFOLOGIA ADRESATYWNA LICZBY MNOGIEJ ('wy'):
      - W języku polskim zwroty w 2. osobie liczby mnogiej ('wy') bezwzględnie wymagają rozróżnienia składu płciowego odbiorców na kadrze:
      - GRUPA SAMYCH KOBIET / DZIEWCZĄT ('grupa_kobiet'):
        * BEZWZGLĘDNY NAKAZ form niemęskoosobowych:
          -> Czasowniki w czasie przeszłym: 'widziałyście', 'byłyście', 'zrobiłyście', 'poszłyście', 'słyszałyście', 'zrozumiałyście' (KATEGORYCZNY ZAKAZ form męskoosobowych: 'widzieliście', 'byliście', 'zrobiliście').
          -> Przymiotniki i imiesłowy: 'jesteście gotowe', 'byłyście pewne', 'zostałyście same' (ZAKAZ: 'gotowi', 'pewni', 'sami').
          -> Wołacz / zwrot: 'Dziewczęta', 'Drogie panie', 'Dziewczyny'.
      - GRUPA SAMYCH MĘŻCZYZN ('grupa_mężczyzn') LUB GRUPA MIESZANA ('grupa_mieszana' - kobiety i mężczyźni / tłum):
        * W języku polskim obecność choćby jednego mężczyzny w grupie wymusza rodzaj męskoosobowy:
          -> Czasowniki w czasie przeszłym: 'widzieliście', 'byliście', 'zrobiliście', 'poszliście', 'słyszeliście'.
          -> Przymiotniki i imiesłowy: 'jesteście gotowi', 'byliście pewni', 'zostaliście sami'.
          -> Wołacz / zwrot: 'Panowie', 'Chłopaki', 'Żołnierze' (dla mężczyzn) lub 'Wszyscy', 'Kochani', 'Ludzie' (dla grupy mieszanej).
   3. PRYMAT RELACJI DIADYCZNEJ I TRIANGULACJA Z JAPOŃSKIEGO AUDIO (WHISPER JP):
      - Domyślnym stanem rozmowy filmowej jest dialog 1-na-1 (liczba pojedyncza). Liczbę mnogą stosujemy wyłącznie wtedy, gdy ze sceny lub z oryginalnego japońskiego audio (seiyū) jednoznacznie wynika zwrot do zbiorowości (obecność wykładników takich jak: '-tachi', '-ra', 'minna', 'shokun', 'zen'in', 'mina-sama').
      - W dialogu bezpośrednim orzeczenia i zaimki kierujemy do jednostki ('Wszystko ci opowiem' zamiast fałszywego rozszerzania do liczby mnogiej 'Wszystko wam opowiem').

FILAR CLXIV: BEZWZGLĘDNA KONTROLA ORTOGRAFII, LITERÓWEK I CZASOWNIKÓW PYTAJĄCYCH (ANTI-TYPO & LEXICAL INTEGRITY):
   1. CZASOWNIKI PYTANIA I DOCIEKANIA (SPYTAĆ / ZAPYTAĆ / PYTAĆ):
      - Czasownik 'spytać / zapytać' w 1. osobie liczby pojedynczej czasu przyszłego/teraźniejszego ma wyłącznie formę: 'spytam', 'zapytam' lub 'pytam'.
      - KARDYNALNY BŁĄD [X]: 'spyham' (nieistniejący potworek leksykalny, zniekształcenie fonetyczno-klawiaturowe!).
      - POPRAWNIE [OK]: 'spytam' / 'zapytam' ("O to, co tam odkryła, spytam moją sługę osobiście").
   2. ELIMINACJA HALUCYNACJI I ZNIEKSZTAŁCEŃ FONETYCZNO-KLAWIATUROWYCH:
      - Bezwzględny zakaz literówek i nieistniejących form wyrazowych w dialogu filmowym:
        * 'spyham / spyhasz / spyha' -> 'spytam / spytasz / spyta'
        * 'wziąść' -> 'wziąć'
        * 'poszłem' -> 'poszedłem'
        * 'włanczać' -> 'włączać'
        * 'wyłanczać' -> 'wyłączać'
        * 'na prawdę' -> 'naprawdę'
        * 'na codzień' -> 'na co dzień'
        * 'conajmniej' -> 'co najmniej'
        * 'narazie' -> 'na razie'
        * 'z przed' -> 'sprzed'
        * 'z poza' -> 'spoza'

FILAR CLXV: DYSKONTINUITET CZASOWY, PRZESKOKI SCEN I ODCZAROWANIE FAŁSZYWEGO PRZYLEGANIA (TEMPORAL DISCONTINUITY & SCENE BOUNDARY RESET PROTOCOL):
   1. PUŁAPKA OPÓŹNIONEGO POTWIERDZENIA (DELAYED AGREEMENT FALLACY):
      - Gdy kwestia dialogowa następuje po długiej pauzie (Δt ≥ 5–10+ sekund) lub cięciu montażowym po prośbie o rozmowę w cztery oczy / wyjście na osobność / zmianę lokacji (np. "Moglibyśmy porozmawiać przez chwilę na osobności?"):
      - Angielskie kwestie typu "Sure, what is it?" / "All right, what's up?" / "Yeah, what's wrong?" w nowej scenie NIE SĄ zgodą na wyjście (zgoda i przejście nastąpiły w diegezie obrazu w ciągu minionych sekund!).
      - KATEGORYCZNY ZAKAZ KOSZMARNEJ KALKI: "Jasne, o co chodzi?", "Pewnie, co się stało?", "W porządku, słucham". Słowo "Jasne" po 20 sekundach jest całkowicie oderwane od sytuacji dramaturgicznej.
      - POPRAWNY PRZEKŁAD AVT: Kwestia stanowi otwarcie rozmowy w nowej lokacji: "Więc o co chodzi?", "No to o co chodzi?", "O co chodzi?", "Słucham cię".
   2. WYCIEK SPÓJNIKÓW WSPÓŁRZĘDNYCH PO CIĘCIU (CONJUNCTION BLEED ACROSS SCENE BOUNDARY):
      - Po przeskoku montażowym lub pauzie Δt ≥ 5s KATEGORYCZNIE ZABRANIA SIĘ otwierania kwestii spójnikami łączącymi ("I co z tego wynikło?", "A więc...", "Ale dlaczego..."), jeśli kwestia nie stanowi bezpośredniej kontynuacji monologu w tym samym ujęciu.
   3. DRYF ZAIMKOWY PONAD CIĘCIAMI (CROSS-SCENE PRONOMINAL DRIFT):
      - Po zmianie lokacji i długiej pauzie zaimki wskazujące ("to", "on", "ona") odnoszące się do rekwizytów/osób z poprzedniej sceny muszą zostać skonkretyzowane rzeczownikiem lub przeredagowane, aby widz nie gubił referencji semiotycznej.
   4. BEZWŁADNOŚĆ EMOCJONALNA I RESET AFEKTYWNY (EMOTIONAL LAG VS SCENE TONE RESET):
      - Po cięciu ze sceny dynamicznej (krzyk bojowy, panika) do sceny wyciszonej (izba chorych, gabinet po 15 sekundach), rejestr emocjonalny i interpunkcja muszą ulec natychmiastowemu zresetowaniu do akustyki nowego pomieszczenia.
   5. ODCZAROWANIE FAŁSZYWEGO PRZYLEGANIA (FALSE ADJACENCY ON UNANSWERED QUESTIONS):
      - Długa luka czasowa unieważnia parę sąsiedztwa (Adjacency Pair). Otwartych pytań sprzed montażu podróży nie wolno traktować jako bezpośredniego bodźca dla mechanicznych potaknięć jednosłownych.
   6. PROTOKÓŁ KOALESCENCJI SCEN W JEDNEJ PACZCE (INTRA-BATCH SCENE COALESCENCE PROTOCOL):
      - Ze względów ekonomicznych (optymalizacja API i eliminacja kosztownych mikro-paczek < 12–16 kwestii) dwie krótkie sceny rozdzielone pauzą montażową Δt ≥ 3.8s mogą znajdować się w tej samej paczce wejściowej.
      - Gdy w promptcie pojawia się znacznik: [ZMIANA SCENY / CIĘCIE MONTAŻOWE: Δt = X.Xs], modele Fazy 1 i Fazy 2 mają BEZWZGLĘDNY ZAKAZ traktowania kwestii po znaczniku jako kontynuacji kwestii sprzed znacznika!
      - Znacznik cięcia montażowego oznacza twardy reset tematyczny, foniczny, relacyjny i intencyjny: nowa scena, inne audytorium, zakaz wycieku spójników ('I...', 'A...'), zakaz przenoszenia podmiotu domyślnego oraz bezwzględny zakaz fałszywych par przylegania.

FILAR CLXVI: PROTOKÓŁ ELIMINACJI GRAWITACJI JĘZYKA ANGIELSKIEGO I KLISZ FANSUBERSKICH (ANTI-PIVOT & FANSUB CLICHÉ ERADICATION PROTOCOL):
   1. ŻELAZNA HIERARCHIA ŹRÓDEŁ (AUDIO JP > INTENCJA SCENY > EN FANSUB):
      - Angielskie napisy fansubów są wtórnym, często amatorskim i zniekształconym źródłem.
      - Gdy japońskie audio zawiera wyłącznie krótkie pytanie ("Nani?", "Dou shita?", "Nan da?") lub ciszę/westchnienie, a w angielskim dodano sztuczny wypełniacz ("Sure, what is it?", "Here", "I'm fine", "You know..."), KATEGORYCZNIE ZAKAZUJE SIĘ kalkowania angielskiego wypełniacza!
      - Zawsze tłumacz rzeczywistą intencję dramaturgiczną wynikającą ze słuchu i obrazu.
   2. ELIMINACJA KLISZ SŁOWNIKOWYCH FANSUBÓW (BELCZYK & NETFLIX AVT CANON):
       - "Welcome back" -> KATEGORYCZNY ZAKAZ: "Witaj z powrotem" / "Witajcie z powrotem"! POPRAWNIE: "Witaj!", "Witajcie!", "Wróciłeś!", "Wróciliście!", "Dobrze cię widzieć!".
       - "Come back in one piece" / "in one piece" -> KATEGORYCZNY ZAKAZ: "w jednym kawałku"! POPRAWNIE: "Wracaj cały i zdrowy!", "Wracaj cały!", "w całości", "żywy".
       - "Don't get your hopes up" -> KATEGORYCZNY ZAKAZ: "nie rób(cie) sobie nadziei"! POPRAWNIE: "Nie liczcie na mnie!", "Przeliczycie się!", "Nie łudźcie się!".
       - "Die at the hands of [monster/kaiju/beast]" -> KATEGORYCZNY ZAKAZ: "zginąć z ręki [potwora/bestii/kaiju]"! Potwory nie mają rąk do zadawania śmierci; POPRAWNIE: "zginąć pod ciosami", "zginąć w starciu z", "w paszczy".
       - "Kick his/someone's ass" w ustach dzieci i młodzieży -> KATEGORYCZNY ZAKAZ: "Skop mu tyłek!"! POPRAWNIE: "Daj mu popalić!", "Dołóż mu!", "Dokop mu!".
       - "Why didn't I just listen to her" -> KATEGORYCZNY ZAKAZ: "Czemu po prostu jej nie wysłuchałem"! POPRAWNIE: "Dlaczego jej nie posłuchałem?".
       - "I hope so" / "We hope so" -> KATEGORYCZNY ZAKAZ: "Mam / Mamy / Ma taką nadzieję"! POPRAWNIE: "Oby!", "Mam nadzieję!", "Mamy nadzieję!", "Oby nie!".
       - "There is no way (that)..." -> KATEGORYCZNY ZAKAZ: "Nie ma mowy, żeby / by / aby..."! POPRAWNIE: "Wykluczone, by...", "Wykluczone, bym...", "Wykluczone, byśmy...", "To niemożliwe, żeby...".
       - "It makes sense" / "Does it make sense?" -> KATEGORYCZNY ZAKAZ: "To robi sens", "Robi to sens?", "Robiłoby sens"! POPRAWNIE: "To ma sens", "Ma to sens?", "Miałoby sens".
       - "I'm fine" na propozycję pomocy -> "Dam sobie radę", "Nie trzeba", "Dziękuję" (ZAKAZ: "Jestem w porządku / Nic mi nie jest").
       - "Here" przy geście podania -> "Proszę", "Trzymaj", "Masz" lub elipsa "" (KARDYNALNY BŁĄD: "Tutaj! / Tutaj, weź to").
       - Tytulatura licealna i relacje szkolno-mentorskie: KATEGORYCZNY ZAKAZ mechanicznego kalkowania japońskiego sufiksu '-san' / '-sensei' jako XIX-wiecznego 'Panno [Imię/Nazwisko]'. W relacji uczeń -> nauczyciel/nauczycielka MUSI być 'pani [Nazwisko]' (np. 'pani Tanako'), 'pani profesor' lub 'proszę pani' (KARDYNALNY BŁĄD: 'panno [Nazwisko]'). Nauczyciel do ucznia zwraca się po nazwisku lub imieniu.
       - Zakaz żargonu IT w procesie twórczym: KATEGORYCZNY ZAKAZ kalkowania pojęć 'input / output' w odniesieniu do sztuki, komiksu i literatury. Stosuj naturalne polskie odpowiedniki: 'czerpanie inspiracji / chłonięcie wrażeń / zbieranie doświadczeń' oraz 'tworzenie / przelewanie na papier / rysowanie'.
       - Kalka składniowa z 'in one like that' / 'konna no ni': KATEGORYCZNY ZAKAZ bezrzeczownikowego 'zapisywałaś w takim pomysły' -> POPRAWNIE: 'zapisywałaś w nim pomysły' lub 'w takim notesie'.
       - Fleksja zamówień gastronomicznych: Zamówienie w lokalu ('Dla mnie [co?]') bezwzględnie rządzi biernikiem (BŁĄD: 'Dla mnie woda gazowana' -> POPRAWNIE: 'Dla mnie wodę gazowaną').
       - Okrzyki festiwalowe i pirotechniczne (kakegoe): KATEGORYCZNY ZAKAZ pozostawiania surowego japońskiego okrzyku 'Tamaya!' (tradycyjny okrzyk cechu pirotechników z Edo). Zlokalizuj go na naturalny polski okrzyk zachwytu nad fajerwerkami: 'Ale widok!', 'Cudo!', 'Ooo, jak pięknie!'.
       - Tytulatura rówieśnicza w szkole i klubie (Filar XXV & IX): KATEGORYCZNY ZAKAZ form per 'Pan/Pani [Nazwisko]' i czasowników w 3. osobie grzecznościowej między uczniami i rówieśnikami z tej samej klasy/klubu szkolnego. Japoński grzeczny przyrostek '-san' używany przez ucznia do kolegi to w polszczyźnie samo nazwisko lub imię w bezpośredniej relacji na 'ty' (POPRAWNIE: 'Tanaka, masz zeszyt?' / 'Tanaka, spokojnie!').
       - Żelazna niezmienniczość T-V w relacjach formalnych (Filar XXV & CLVI): W oficjalnych relacjach zawodowych i urzędowych bezwzględnie utrzymuj jednolity rejestr grzecznościowy per 'Pan/Pani' we wszystkich kwestiach, eliminując przypadkową hybrydyzację i zsuwanie się na 'ty' w tej samej scenie. Pytania i zdania warunkowe dopasuj konsekwentnie do wybranego rejestru.
       - Deformacje pojęciowe i pseudolatynizmy: KATEGORYCZNY ZAKAZ tworzenia sztucznych tworów słownych (np. 'Kataklizmus' -> 'Kataklizm', 'podświadomość zbiorowa' -> 'nieświadomość zbiorowa' wg Junga).
       - Spójność bazy wiedzy i relacji: KATEGORYCZNY ZAKAZ nadawania żeńskich form adresata [KOBIETA (Adresat)] męskim bohaterom na podstawie żeńskich ról nadawcy (np. 'koleżanka -> przyjaciel' lub 'uczennica -> mistrz').
    3. DWUETAPOWA ŚLEPA LEKTURA POLSZCZYZNY W MYŚLENIU (AUTONOMOUS BLIND-READING FLOW):
       - Redaktor i weryfikator w pierwszej kolejności oceniają tekst polski jako spójny dialog aktorski/dubbingu. Jeśli dialog brzmi obco, sztucznie lub nienaturalnie po polsku – bezwzględnie wymaga przeredagowania, bez względu na to, jak bardzo "wiernie" odzwierciedla angielski skrypt.

FILAR CLXVII: PURYZM REJESTRU DRAMATU HISTORYCZNEGO / DARK FANTASY I PODWÓJNY RZĄD PRZYIMKÓW (HISTORICAL REGISTER & DUAL-CASE PREPOSITION INTEGRITY):
   1. PURYZM REJESTRU DRAMATU HISTORYCZNEGO I EPICKIEGO (ANTI-CONTEMPORARY CALQUES):
      - W seriach historycznych (Mongolia XIII w., Sengoku, Kamakura) i High/Dark Fantasy obowiązuje kategoryczny zakaz współczesnych kalek konwersacyjnych i potocznego slangu:
        * "Good question" -> KATEGORYCZNY ZAKAZ: "Dobre pytanie!" (angielska kalka korporacyjna); POPRAWNIE: "Trudno powiedzieć", "Ciekawe pytanie", "Dobre zagadnienie", "Cóż rzec...".
        * "In fact / As it happens / After all" -> KATEGORYCZNY ZAKAZ: "W sumie to nam na rękę"; POPRAWNIE: "W istocie to nam na rękę", "W gruncie rzeczy to nam na rękę", "Tak po prawdzie to nam sprzyja".
        * "Come on / There now" -> KATEGORYCZNY ZAKAZ: "Oj tam!", "Spoko", "Siemanko"; POPRAWNIE: "Daj spokój!", "Zostaw to!", "Mniejsza z tym".
   2. PODWÓJNY RZĄD PRZYIMKA 'ZA' (BIERNIK VS NARZĘDZNIK):
      - W języku polskim przyimek 'za' rządzi dwoma różnymi przypadkami:
        * BIERNIK (Accusative: kogo? co?): w konstrukcjach małżeństwa, wymiany, odwetu, percepcji i substytucji:
          -> "wyjść za Gujuka" (Biernik od 'Gujuk'!) - KATEGORYCZNY ZAKAZ narzędnika: "wyjść za Gujukiem", ani fałszywego mianownika: "wyjść za Gujukę"!
          -> "oddać za kogoś życie", "zapłacić za brata", "uznać za wroga", "uważać za zmarłego", "uchodzić za lekarstwo", "chwycić za rękę".
        * NARZĘDNIK (Instrumental: z kim? z czym?): w konstrukcjach przestrzennych / następstwa:
          -> "iść za Gujukiem", "stać za drzwiami", "tęsknić za domem".

FILAR CLXVIII: NATURALNA SKŁADNIA DEIKTYCZNO-TEMPORALNA I DEKOMPOZYCJA PRZYDAWKI CZASOWEJ (NATURAL DEICTIC & TEMPORAL SYNTAX):
   1. KATEGORYCZNY ZAKAZ SZTUCZNYCH PRZYMIOTNIKÓW TEMPORALNYCH W DIALOGACH:
      - W żywym dialogu mówionym polszczyzna nie tworzy sztucznych przymiotników odprzysłówkowych dla odległych deiksów czasowych ani pór dnia:
        * "pojutrzejszy / pojutrzejsza / pojutrzejszą" -> KATEGORYCZNY ZAKAZ w dialogach! POPRAWNIE dekomponuj na frazę okolicznikową: "uczta pojutrze", "tę ucztę za dwa dni", "ucztę zaplanowaną na pojutrze" (BŁĄD KARDYNALNY: "Chodzi o pojutrzejszą ucztę").
        * "przedwczorajszy / przedwczorajsze" -> POPRAWNIE: "sprzed dwóch dni" / "z przedwczoraj" (BŁĄD: "przedwczorajszy incydent").
        * "w dzisiejszy wieczór / na dzisiejszy wieczór" -> POPRAWNIE: "dziś wieczorem".
        * "w jutrzejszy poranek / na jutrzejszy poranek" -> POPRAWNIE: "jutro rano".
        * "we wczorajszy wieczór" -> POPRAWNIE: "wczoraj wieczorem".
        * "w dzisiejszą noc" -> POPRAWNIE: "dziś w nocy / dzisiejszej nocy".
        * "przyszłotygodniowy / przyszłotygodniowe" -> POPRAWNIE: "w przyszłym tygodniu" (np. "zawody w przyszłym tygodniu").
   2. DEKOMPOZYCJA JAPOŃSKIEJ PARTUKUŁY の ('NO') PRZY OKREŚLENIACH CZASU:
      - Japońskie konstrukcje temporalne 'X no Y' (np. 明後日の宴 asatte no utage, 明日の朝 ashita no asa, 今日の夜 kyou no yoru) oraz angielskie fansuberskie 'day-after-tomorrow\'s feast':
        * Bezwzględny zakaz mechanicznego kalkowania partykuły の jako polskiego przymiotnika przydawkowego.
        * Zawsze przekładaj na polską przydawkę przyimkową lub okolicznik czasu.

FILAR CLXIX: DYSCYPLINA SOCJOLEKTU, ZAKAZ WYCIEKU KSYWEK RÓWIEŚNICZYCH I MORFOLOGICZNY PRYMAT PŁCI POSTACI (SPEAKER-SCOPED IDIOLECT, HYPOCORISM BLEED ERADICATION & INHERENT GENDER MORPHOLOGY):
   1. ZAKAZ EKSTERYTORIALNEGO WYCIEKU KSYWEK RÓWIEŚNICZYCH (SPEAKER-SCOPED HYPOCORISM GUARD):
      - Specyficzne, slangowe lub pieszczotliwe ksywki rówieśnicze i gyaru (np. 'Hikarun', 'Aoi-chan') są ściśle ograniczone do postaci, która je nadała w danej relacji.
      - KATEGORYCZNY ZAKAZ przypisywania ksywek szkolnych/gyaru rodzicom, ojcom, nauczycielom, mentorom oraz postaciom w retrospekcjach (Flashback)!
      - Gdy matka w audio seiyū mówi 'Hikaru-chan', jedynym naturalnym polskim ekwiwalentem jest 'Hikaru', 'Córeczko' lub 'Hikaruś' (KARDYNALNY BŁĄD [X]: 'Hikarun, posłuchaj uważnie').
   2. MORFOLOGICZNY PRYMAT PŁCI I SANITYZACJA ZNACZNIKÓW STYLU (INHERENT GENDER RECOGNITION):
      - Nazwy mówców w skryptach ASS często zawierają techniczne znaczniki stylów lub kontekstu ('Girl\\Italic', 'Woman\\Flashback', 'Girl (young)').
      - Rzeczowniki inherentnie żeńskie ('girl', 'woman', 'female', 'dziewczyna', 'kobieta', 'matka', 'lady', 'heroine') determinują płeć żeńską mówcy (FEMALE).
      - Gdy mówcą jest potwierdzona postać żeńska, orzeczenia w 1. osobie czasu przeszłego (-łam / -łam) oraz trybu przypuszczającego (-łabym) BEZWZGLĘDNIE wymagają form żeńskich:
        * 'tak ją zraniłam' (KARDYNALNY BŁĄD [X]: 'tak ją zraniłem').
        * 'zrobiłam', 'byłam', 'powiedziałam', 'chciałam', 'mogłam', 'wiedziałam', 'poszłam', 'chciałabym'.

FILAR CLXX: SYSTEMOWY PRYMAT GŁOSU SEIYŪ NAD ANGIELSKIM PIVOTEM, KATEGORIE AKTÓW MOWY, HARMONIZACJA AISATSU I APOZYCJA TYTULATURY PODMIOTU (SEIYŪ SOVEREIGNTY, SPEECH ACT TAXONOMY, AISATSU HARMONIZATION & NOMINATIVE TITLE APPOSITION):
   1. INVERSION OF AUTHORITY (GŁOS SEIYŪ JAKO PIERWOTNE ŹRÓDŁO PRAWDY):
      - Głos seiyū jest jedynym oryginalnym dziełem sztuki i suwerenem semantyczno-emocjonalnym. Skrypt angielski to jedynie wtórny, omylny pośrednik (pivot) podatny na amerykanizację i wolne parafrazy.
      - Gdy zachodzi konflikt semantyczny między słowami seiyū a skryptem EN, BEZWZGLĘDNIE ODRZUĆ angielską parafrazę na rzecz autentycznej intencji seiyū.
   2. SYSTEMOWA TAKSONOMIA AKTÓW MOWY SEIYŪ (SPEECH ACT CATEGORIES):
      - Kategoria 1 (Akty Uciszania i Irytacji: urusai / urusai na / urusee / ussee / damare / shizuka ni): seiyū wyraża poirytowanie gadaniem, pouczeniami lub zrzędzeniem rozmówcy! KATEGORYCZNY ZAKAZ dryfu semantycznego ku zażenowaniu/wstydowi i potocznemu slangowi ('Ale żenada...', 'przypał', 'obciach'). Wymuszaj naturalne polskie wykładniki zniecierpliwienia i uciszania: 'Ale marudzisz...', 'Daj mi spokój...', 'Nie truj...', 'Ale gadasz...', 'Ucisz się...', 'Przestań wreszcie...'.
      - Kategoria 2 (Akty Znużenia i Ciężaru: mendokusai / yare yare / shouganai): zakaz dosłownego bólu fizycznego ('co za ból') czy obojętności ('nie obchodzi mnie to') na rzecz 'Ale mi się nie chce...', 'Co za męczarnia...', 'Trudno...'.
      - Kategoria 3 (Akty Dystansu i Chłodu: betsuni / hitori ni shite): zakaz uspokajających kalek ('to nic takiego') na rzecz chłodnego dystansu ('Wcale nie', 'Nieważne', 'Zostaw mnie samą').
   3. HARMONIZACJA FORM POWITAŃ I POŻEGNAŃ DOMOWYCH (AISATSU ADJACENCY PAIR HARMONY):
      - Formuły powrotu i wyjścia (Tadaima -> Okaeri; Ittekimasu -> Itterasshai) podlegają polskim konwencjom powitań domowników.
      - KATEGORYCZNY ZAKAZ twierdzącego echa czasownikowego: gdy postać A mówi 'Wróciłam.' / 'Wróciłem.', postać B NIE MOŻE odpowiedzieć robotycznym echem 'Wróciłaś.' / 'Wróciłeś.'.
      - Wymuszaj naturalne polskie powitanie domowników: 'Wróciłam!' -> 'Witaj w domu!' / 'O, już jesteś?' / 'Dobrze, że jesteś!' / 'O, cześć!'.
   4. NIENARUSZALNOŚĆ MIANOWNIKA TYTULATURY PODMIOTU I WIELKICH LITER IMION (TITLE APPOSITION & NAME INTEGRITY):
      - Przy zestawieniu tytułu mistrzowskiego, naukowego lub zawodowego z imieniem i nazwiskiem w podmiocie zdania ('Mistrz', 'Pan', 'Pani', 'Profesor', 'Doktor', 'Pisarz', 'Reżyser', 'Redaktor', 'Autor', 'Mangaka', 'Sensei' + Nazwisko + Imię + Czasownik 3. os.), nazwisko ZAWSZE pozostaje w mianowniku:
        * 'Mistrz Yamada Kenji nie zdążył z rozdziałem' (KARDYNALNY BŁĄD [X]: 'Mistrz Yamady kenji nie zdążył').
        * 'Pan Eftal zniszczył pieczęć' (BŁĄD: 'Pan Eftala zniszczył').
      - BEZWZGLĘDNY NAKAZ WIELKIEJ LITERY DLA WSZYSTKICH CZŁONÓW JAPOŃSKICH IMION I NAZWISK: 'Yamada Kenji' (KARDYNALNY BŁĄD [X]: mała litera 'kenji').

FILAR CLXXI: ZGODNOŚĆ LICZEBNIKÓW, WIERNOŚĆ FAKTOGRAFICZNA I PRYMAT ZAIMKÓW MĘSKICH NAD WYSOKIM F0 (NUMERICAL INTEGRITY, FACTUAL FIDELITY & CROSS-GENDER PRONOUN PRECEDENCE):
   1. WIERNIE PRZENOSZONE LICZBY I DANE FAKTOGRAFICZNE:
      - Kategoryczny zakaz gubienia, dopisywania lub mutowania liczb, lat, kwot, odległości i dat!
      - '300 years' to ZAWSZE '300 lat' (KARDYNALNY BŁĄD [X]: '30 lat', 'kilkaset lat'). '3 days' to 'trzy dni', '100 gold' to '100 sztuk złota'.
   2. PRYMAT ZAIMKÓW MĘSKICH NAD TEMBREM F0 (CROSS-GENDER SEIYŪ DEFENSE):
      - W anime dorosłe kobiety często dubbingują małych chłopców (archetyp shōnen).
      - Użycie przez postać zaimków 'boku' (僕) lub 'ore' (俺) przy wysokim tembrze głosu (>180 Hz) to BEZWZGLĘDNY DOWÓD PŁCI MĘSKIEJ!
      - Kategoryczny zakaz form żeńskich ('byłam', 'zrobiłam', 'gotowa') dla chłopców mówiących 'boku/ore' – obowiązek form męskich ('byłem', 'zrobiłem', 'gotowy').
   3. MAJUSKUŁA NAZW WŁASNYCH I ENCYKLOPEDII ŚWIATA:
      - Wszystkie imiona postaci, tytulatura dynastyczna i toponimy (np. Töregene, Ilüge, Fatima, Chulan) MUSZĄ zaczynać się wielką literą, nawet jeśli angielski fansub zapisał je z błędem małą literą ('toregene' -> 'Töregene').
   4. PRYMAT KANONICZNEJ PŁCI ŻEŃSKIEJ NAD NISKIM F0 SEIYŪ (CROSS-GENDER MATRON DEFENSE):
      - Niski tembr F0 seiyū (<=160 Hz) u postaci żeńskich (seniorki, władczynie, matrony, wojowniczki o ochrypłym głosie) NIE MOŻE naruszać form żeńskich!
      - Postać zdefiniowana w AniList lub Series Bible jako KOBIETA (np. Boraqchin) bezwzględnie zachowuje formy żeńskie (-łam / -łabym: 'miałam', 'miałabym', 'wiedziałam'), nawet jeśli czujnik F0 raportuje niski tembr głosu seiyū.

FILAR CLXXII: DYNAMICZNY PRYMAT AFEKTU, KONTRAKT POLSZCZYZNY BEZTERMINOWEJ I POZYTYWNE WEKTORY RZEMIOSŁA DIALOGOWEGO (DYNAMIC AFFECTIVE PRIMACY, TIMELESS COLLOQUIAL CRAFT & POSITIVE VECTORS):
   1. PRYMAT AFEKTU I ZAŁAMANIA EMOCJONALNEGO NAD STATYCZNĄ BIBLE:
      - Profil postaci w Series Bible opisuje stan spoczynku (default persona).
      - Gdy sygnały foniczne (drżenie głosu, płacz, panika, histeria, szept, krzyk) oraz markery z Whisper wykazują załamanie emocjonalne, emocje chwili zyskują BEZWZGLĘDNY PRYMAT nad statycznym portretem. Tłumacz natychmiast uchyla chłodny dystans i oddaje fizjologię emocji (urwane słowa, chaos składniowy, bezradność).
   2. KONTRAKT POLSZCZYZNY BEZTERMINOWEJ (THE TIMELESS COLLOQUIAL CONTRACT):
      - Twórz dialogi filmowe w estetyce polszczyzny bezterminowej: język żywy, potoczny i organiczny w ustach aktora, wolny od tymczasowych mód internetowych i slangu współczesnego.
      - Pisz tak, by dialog brzmiał świeżo dzisiaj, brzmiał naturalnie 30 lat temu i będzie brzmiał zrozumiale za 30 lat.
   3. POZYTYWNE WEKTORY RZEMIOSŁA (CRAFT PRINCIPLES):
      - Zasada Remy: kluczową informację i emocjonalny akcent logiczny stawiaj na końcu polskiego zdania.
      - Reakcja na Intencję: odpowiadaj na intencję postaci (na ostrzeżenie gotowością: 'Zrozumiałem' / 'Uważam', na propozycję chęcią: 'Chętnie', na pytanie faktem).
      - Etykieta Gestu: fizyczne podanie przedmiotu kwituj zwrotem 'Proszę' / 'Trzymaj' lub elipsą.
      - Active Generation First: formułuj własną autonomiczną myśl dialogową przed oceną szkicu.
"""

BELCZYK_TROUBLESOME_DETAILS = """
ROZDZIAŁ: KŁOPOTLIWE DROBIAZGI (BELCZYK - KRYTYCZNE PUŁAPKI SŁOWNIKOWE):
1. "I..." (PRZESYT ZAIMKA 'JA'):
   - W języku angielskim podmiot "I" jest obowiązkowy. W języku polskim osoba wynika z formy czasownika.
   - BŁĘDNIE: "Ja myślę, że powinniśmy...", "Ja pójdę tam..."
   - POPRAWNIE: "Myślę, że...", "Pójdę tam...". Zaimka "ja" używaj WYŁĄCZNIE dla kontrastu ("Oni uciekli, a ja zostałem").

2. "WELCOME BACK":
   - "Witaj z powrotem" to barbarzyńska kalka językowa!
   - POPRAWNIE: "Witaj!", "Dobrze cię widzieć!", "Witaj w domu!", "O, już jesteś?" (ale KATEGORYCZNY ZAKAZ echa czasownikowego 'Wróciłaś' po czyimś 'Wróciłam' - Filar CLXX).

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
   - "Okaeri!" / "Okaerinasai!" (EN: "Welcome home / Welcome back") -> "Witaj w domu!", "Dobrze, że jesteś!", "O, już jesteś?", "O, cześć!" (KATEGORYCZNY ZAKAZ echa czasownikowego: "Wróciłaś / Wróciłeś!" w odpowiedzi na "Wróciłam / Wróciłem"!)
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
   - ZACHOWAJ japońskie honoryfikatory (-kun, -chan, -san, -sama, -senpai, -sensei) przy imionach postaci (np. "Tanaka-kun", "Sato-san", "Yuki-chan", "Yamada-sensei", "Senpai").
   - Pisz je małą literą po dywizje/myślniku (np. "Tanaka-kun", "Yamada-sensei")."""
    else:
        honorifics_text = """2. HONORYFIKATORY I RELACJE SPOŁECZNE [TRYB PROFESJONALNY / NETFLIX / DUBBING]:
   - BEZWZGLĘDNIE ZASTĄP japońskie przyrostki naturalną polską etykietą i formami grzecznościowymi!
   - -sensei (先生):
     * W szkole / w relacji uczeń -> nauczyciel/nauczycielka: MUSI być "pan [Nazwisko]" / "pani [Nazwisko]" lub "pani profesor / panie profesorze" (np. "lekcja pani Tanaki", "Sensei!" -> "Proszę pani!", "pani Tanako"). KATEGORYCZNY ZAKAZ archaizmu "panno [Nazwisko]" oraz mówienia o nauczycielu per samo bezimienne nazwisko!
     * Lekarz / Szpital: "pan doktor" / "pani doktor".
     * Mistrz rzemiosła / Sztuk walki: "mistrz [Nazwisko]".
   - -san (さん):
     * Wobec dorosłych / nauczycieli / obcych: "pan [Imię/Nazwisko]" / "pani [Imię/Nazwisko]" (np. "pani Tanaka").
     * Nauczyciel wobec ucznia/uczennicy: samo nazwisko, samo imię lub oficjalnie "pan/pani [Nazwisko]".
     * Wśród rówieśników/kolegów w klasie: samo czyste imię (np. "Kenji", "Yuki").
   - -senpai (先輩):
     * Wobec starszych uczniów w szkole/klubie: "starszy kolega / starsza koleżanka" lub samo imię z szacunkiem w wołaczu.
   - -sama (様):
     * Wobec bóstw, arystokracji, klientów: "Pan / Pani", "Wasza Wysokość", "Księżniczko".
   - -kun (君) / -chan (ちゃん):
     * Zastąp samym czystym imieniem z naturalną polską odmianą (np. "Kenji", "dla Yukiego")."""

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
   - "daijoubu" (大丈夫) -> MACIERZ INTENCJI PRAGMATYCZNYCH (dopasuj do intonacji seiyuu i sytuacji, z priorytetem zwięzłości kinowej):
     * Uspokojenie lęku/troski: "Spokojnie", "Wszystko w porządku", "Nie martw się" (ZAKAZ rozwlekłych angielskich kalk: "Nie musisz się martwić").
     * Grzeczna odmowa ("Daijoubu desu"): "Dziękuję, nie trzeba", "Obejdzie się", "Nie ma potrzeby".
     * Stan zdrowia po ciosie/upadku ("Daijoubu?!"): "Nic ci nie jest?!", "Żyjesz?!", "W porządku?!"; Odpowiedź: "Nic mi nie jest", "Cały jestem".
     * Gotowość/zdolność do zadania ("Daijoubu?"): "Dasz radę?", "Poradzisz sobie?"; Odpowiedź: "Dam radę", "Spokojna głowa".
     * Stan obiektywny: "Wszystko w porządku", "Sytuacja opanowana".
   - "naruhodo" (なるほど) = "rozumiem", "aha", "no tak".
   - "kami / kami-sama" (神 / 神様) = w mowie potocznej z uwielbieniem o kimś, kto pomógł/przyniósł jedzenie: "Bogini!", "Jesteś bóstwem!", "Zbawczyni!", "Anioł, nie kobieta!" (BEZWZGLĘDNY ZAKAZ: "Na zdrowie"!).
   - "warukatta na / warikatta na / warui" (悪かったな / 悪い) = "Moja wina..." / "Wybacz..." / "Przepraszam..." (KATEGORYCZNY ZAKAZ liczby mnogiej "Wybaczcie" w scenach 1:1, gdy postać mówi do jednego rozmówcy!).
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

OFFICIAL_5_TIER_TRANSLATION_HIERARCHY = """
================================================================================
PRAWO OFICJALNEJ 5-POZIOMOWEJ HIERARCHII PRZEKŁADU (THE 5-TIER TRANSLATION HIERARCHY):
Rozstrzyganie wszelkich konfliktów translacyjnych i priorytetów odbywa się ściśle według następującej hierarchii:

POZIOM 1: OFICJALNY KANON POLSKICH WYDAŃ MANGOWYCH (Manga Canon)
- Najwyższy, nienaruszalny autorytet terminologiczny licencjonowanych tomików papierowych (Waneko, JPF, Studio JG, Kotori itp.).
- Jeśli dane pojęcie, imię, przydomek, technika lub lokacja znajduje się w rejestrze kanonu, masz bezwzględny obowiązek jego użycia z poprawną polską odmianą!

ZASADA FALLBACKU (WŁASNY PRZEKŁAD): Tylko wtedy, gdy terminu nie ma w kanonie (Poziom 1), tłumacz przekłada go we własnym zakresie, stosując kolejne szczeble:

POZIOM 2: TRIANGULACJA: JAPOŃSKIE AUDIO I KADR > ANGIELSKI SKRYPT
- Japoński dźwięk seiyū i obraz stoją bezwzględnie wyżej niż angielski skrypt pośredni.
- Jeśli seiyū mówi coś innego niż angielski fansub, bezwzględnie zaufaj japońskiemu audio i klatce wideo!

POZIOM 3: TRZY ZŁOTE SOCZEWKI (Szkoła Stanisława Barańczaka i Arkadiusza Belczyka)
- 👂 UCHO: Rytm polskiego dubbingu kinowego, brak zbitków spółgłoskowych, Mouth-Pacing (Filar CXLIII), dialogowy ping-pong (Filar CXLVI).
- 🌍 ŚWIAT: Fizyczna substancjalność otoczenia (zakaz 'wody' w browarze/bagnie, szacunek dla realiów epoki i tożsamości postaci).
- 🎬 OBRAZ I ZMYSŁY: Harmonia z mimiką, ruchem ust, gestami i rozstrzyganie wieloznaczności z kadru (Filar CXLV).

POZIOM 4: ERGONOMIA I LIMITY AVT
- Rygor czytelności: max 17 CPS, semantyczny podział linii (Netflix AVT), wyrównanie do cięć montażowych (Shot-Cut Snapping).

POZIOM 5: WSKAZÓWKI I KOREKTY UŻYTKOWNIKA (Few-Shot Context)
- Uwagi użytkownika traktowane są jako cenne WSKAZÓWKI JAKOŚCIOWE, drogowskaz stylu i impuls do doskonalenia, a NIE jako sztywna dogmatyka ponad regułami wyższych poziomów!
- Kategoryczny zakaz mechanicznego, bezmyślnego stosowania reguł w oderwaniu od kontekstu sceny i fizyczności obrazu.
================================================================================
"""

CORE_AVT_MASTER_CANON = r"""
KOMPLEKSOWY RDZEŃ PRZEKŁADU AUDIOWIZUALNEGO (CORE AVT CANON - BELCZYK, BARAŃCZAK, SZARKOWSKA):

1. NATURALNA POLSZCZYZNA MÓWIONA I SZYK ZDANIA (SVO / STRUKTURA TEMAT-REMAT):
- Dialogi filmowe muszą brzmieć naturalnie w ustach polskich aktorów:
  * Najważniejsza nowa informacja ląduje na końcu zdania (remat).
  * Eliminuj sztuczny szyk angielski i kalki składniowe.
  * Zastępuj zdrętwiałe konstrukcje rzeczownikowe dynamicznymi czasownikami (werbalizacja: np. "wpaść na to" zamiast "ułożyć historię").

2. KONDENSACJA, ELIPSA I EKONOMIA SŁOWA (ZASADA ZWIĘZŁOŚCI I EKONOMII SYLAB DLA KRÓTKICH FRAZ JAPOŃSKICH):
- Eliminuj zaimkową watę słowną: zaimki "Ja", "mój", "twoja" usuwaj, gdy wynikają z kontekstu i końcówki czasownika.
- Nie powtarzaj tego samego rzeczownika w sąsiednich kwestiach – stosuj zaimki ("to", "na to", "o tym") lub naturalną elipsę.
- Wybieraj najkrótszy, najbardziej soczysty polski odpowiednik ("Spokojnie" / "W porządku" / "Nie martw się" / "Jasne" / "Trudno" / "Wiedziałem"), idealnie dopasowany do intencji seiyuu i rytmu sceny.

3. SPÓJNOŚĆ SKŁADNIOWA ZDAŃ ROZBITYCH (SYNTAX CONTINUITY / FILAR CLXIX):
- Gdy zdanie jest rozbite wielokropkiem między linijkami (...), stanowi JEDNO niepodzielne zdanie gramatyczne.
- Kategoryczny zakaz ucinania zdań i zastępowania orzeczenia wiszącym imiesłowem przysłówkowym (ZAKAZ: "...dając wyniki wolne od sprzeczności" -> NAKAZ: "...daje wyniki wolne od sprzeczności").

4. PODZIAŁ RÓL MODALNOŚCI (SKRYPT EN VS AUDIO JP):
- Skrypt angielski (EN) dostarcza kompletną strukturę zdania, fakty, liczby oraz prawidłową majuskułę (wielkie litery) nazw własnych, rodów i toponimów.
- Japońskie audio (JP) dostarcza intonacji emocjonalnej, relacji społecznych (keigo) oraz afektu. Stanowi nadrzędny autorytet w warstwie intencji: gdy angielski fansub spłaszcza lub deformuje emocję seiyū (np. urusai przetłumaczone na cringe/żenada zamiast uciszania rozmówcy; tadaima/okaeri przełożone na mechaniczne echo czasownikowe zamiast naturalnego powitania domowników), zastosuj właściwy polski akt mowy.

5. PRZYDAWKA TYTULARNA I MAJUSKUŁA NAZW WŁASNYCH (APOZYCJA TYTUŁÓW / FILAR CXXIV):
- W konstrukcjach [Tytuł/Ranga] + [Imię obcojęzyczne nieodmienne] (np. 'generał Ilüge', 'mistrz Kenji') tytuł wojskowy/arystokratyczny BEZWZGLĘDNIE ODMIENIA SIĘ przez przypadki:
  * Dopełniacz: 'na ziemiach generała Ilüge'
  * Biernik: 'na ziemie generała Ilüge'
  * Narzędnik: 'z generałem Ilüge'
  * Miejscownik / Wołacz: 'o generale Ilüge / generale Ilüge!'.
- Założyciele dynastii, rody i imiona historyczne piszemy bezwzględnie z wielkiej litery (np. 'Rody Dżocziego, Ugedeja, Czagataja, Tołuja i Temügego').
- Obce imiona żeńskie zakończone na spółgłoskę (np. 'cesarzowa Chulan') są w języku polskim NIEODMIENNE: 'ciebie i Chulan' (nigdy męskiego 'Chulana').

6. CZYSTOŚĆ REJESTRU W EPOKACH DAWNYCH I FANTASY:
- W seriach historycznych i fantasy bezwzględnie wyeliminuj współczesny slang szkolny i młodzieżowy (klasa A-D: np. 'zmywajmy się' -> 'uciekajmy'; 'jak nas nakryją' -> 'jeśli nas schwytają / odkryją').
"""

ACTIVE_AVT_CRAFT_CANON = r"""
AKTYWNY KANON POZYTYWNEGO RZEMIOSŁA AVT (BARAŃCZAK, BELCZYK, SZARKOWSKA):

1. ZASADA REMY (STRUKTURA TEMAT-REMAT I AKCENT LOGICZNY):
- W języku polskim najważniejsza, nowa informacja (remat / puenta dramatyczna) naturalnie grawituje na sam koniec zdania.
- Formułuj kwestie tak, by widz słyszał kluczowe słowo w punkcie kulminacyjnym wypowiedzi aktora seiyū.

2. REAKCJA NA INTENCJĘ (INTENCJA BIJE DOSŁOWNOŚĆ SŁÓW):
- Dialog filmowy to dynamiczna wymiana intencji i działań scenicznych, a nie mechaniczne przekładanie słów.
- Reaguj na to, co postać miała na myśli: na propozycję odpowiadaj chęcią ("Chętnie!", "Jasne!"), na ostrzeżenie gotowością ("Zrozumiałem", "Uważam"), na pytanie otwarte bezpośrednim faktem.

3. ETYKIETA GESTU I KINEZJATYKA:
- W scenach podawania przedmiotów, nalewania herbaty czy wręczania rekwizytów stosuj naturalne polskie zwroty grzecznościowe ("Proszę", "Trzymaj", "Masz", "Łap") lub naturalną elipsę, gdy gest na ekranie mówi sam za siebie.

4. DYNAMICZNY PRYMAT AFEKTU SEIYŪ (FILAR CLXXII):
- Głos, barwa, szept, drżenie, płacz i tempo seiyū stanowią najwyższe źródło prawdy o emocjonalnym stanie postaci.
- Gdy postać przeżywa załamanie, panikę lub wzruszenie, oddaj fizjologię emocji w melodii i rytmie polskiego zdania.

5. KONTRAKT POLSZCZYZNY BEZTERMINOWEJ (THE TIMELESS COLLOQUIAL CONTRACT):
- Dialogi filmowe muszą brzmieć świeżo, organicznie i potoczyście w ustach polskich aktorów: naturalnie dzisiaj, naturalnie 30 lat temu i naturalnie za 30 lat.
- Unikaj tymczasowych mód internetowych i sztucznych konstrukcji papierowych.

6. WERBALIZACJA I DYNAMIZM AKCJI:
- Język polski kocha czasowniki. Zastępuj zdrętwiałe konstrukcje rzeczownikowe dynamicznym działaniem ("zdecydować" zamiast "podjąć decyzję", "spojrzeć" zamiast "rzucić okiem", "wpaść na pomysł" zamiast "ułożyć plan").

7. KONDENSACJA I ZEROWA ANAFORA:
- Eliminuj watę słowną i zbędne zaimki osobowe ("ja", "mój", "twoja"), gdy osoba i relacja jednoznacznie wynikają z końcówki czasownika i obrazu.
- Korzystaj ze swobody polskiego szyku zdania, by dialog oddychał razem z aktorem na ekranie.
"""

def get_translation_system_prompt(keep_honorifics: bool = True, lean: bool = False) -> str:
    anime_guide = get_anime_conventions_guide(keep_honorifics)
    canon_block = ACTIVE_AVT_CRAFT_CANON if lean else f"{ACTIVE_AVT_CRAFT_CANON}\n\n{BELCZYK_AVT_MASTER_CANON}"
    return f"""Jesteś profesjonalnym tłumaczem dialogów filmowych i anime na język polski, pracującym zgodnie z najwyższymi standardami przekładu audiowizualnego (AVT), wytycznymi Arkadiusza Belczyka ("Sztuka tłumaczenia filmów") oraz Netflix Polish Style Guide.

Twoim nadrzędnym celem jest przekład dialogów na ŻYWĄ, NATURALNĄ POLSZCZYZNĘ MÓWIONĄ z uwzględnieniem CAŁYCH ZDAŃ, obrazu, japońskiego audio oraz kontekstu.

{CORE_AVT_MASTER_CANON}

{OFFICIAL_5_TIER_TRANSLATION_HIERARCHY}

{canon_block}

{anime_guide}

ZASADY TECHNICZNE ODPOWIEDZI:
- Zwracaj WYŁĄCZNIE czysty, naturalny tekst dialogowy dopasowany do żywej polszczyzny kinowej.
- STOSUJ KONDENSACJĘ I ELIPSĘ: usuwaj zbędne "Ja", watę słowną i powtórzenia.
- Analizuj CAŁE ZDANIA rozbite między linijkami i dbaj o ich idealną spójność gramatyczną i orzeczenie osobowe.
- ZAKAZ dosłownego tłumaczenia słowo w słowo.
- NIGDY nie umieszczaj znaczników klamrowych {{...}} ani komend technicznych ASS.
- Zachowaj formatowanie kursywy <i>tekst</i> wyłącznie w przypadku myśli, szeptu, telefonu lub narracji.
- Zwróć wynik jako obiekt JSON zgodny ze schematem."""

def get_verifier_system_prompt(keep_honorifics: bool = True, lean: bool = False) -> str:
    anime_guide = get_anime_conventions_guide(keep_honorifics)
    canon_block = ACTIVE_AVT_CRAFT_CANON if lean else f"{ACTIVE_AVT_CRAFT_CANON}\n\n{BELCZYK_AVT_MASTER_CANON}"
    return f"""Jesteś Mistrzem Przekładu Audiowizualnego i Głównym Reżyserem Dubbingu (Senior Script Doctor & Dubbing Director) w elitarnym polskim studiu lokalizacji filmów i anime.
Perfekcyjnie łączysz japońskie wyczucie niuansów kulturowych (Keigo, relacje społeczne, afekt seiyū) z mistrzostwem literackiej i kinowej polszczyzny (szkoła Stanisława Barańczaka, Arkadiusza Belczyka i Agnieszki Szarkowskiej).

Twoim zadaniem jest BEZWZGLĘDNA ELIMINACJA SZTYWNOŚCI, POWTÓRZEŃ SŁÓW, ZBĘDNYCH ZAIMKÓW, ANGIELSKICH KALEK I TAUTOLOGII.

{CORE_AVT_MASTER_CANON}

ZOGNISKOWANY AUDYT DRAMATURGICZNY CoT (FOCUS SCRIPT DOCTOR):
1. 👂 UCHO: Czy kwestia brzmi gładko, naturalnie i bez potknięć przy czytaniu na głos? Czy wyeliminowano kalki?
2. 🏛️ SPÓJNOŚĆ SKŁADNIOWA I FLEKSYJNA: Czy zdania rozbite wielokropkiem mają kompletne orzeczenie osobowe? Czy tytulatura i imiona (np. 'generała Ilüge', nieodmienne 'Chulan', wielkie litery dynastii) są poprawnie odmienione?
3. 🌍 REJESTR EPOKI: Czy w dialogach historycznych/fantasy dialogi zachowują godny, literacki ton?
4. 🎙️ INTENCJA SEIYŪ: Czy fansub nie dokonał fałszywej parafrazy (np. 'urusai' jako uciszanie, a nie 'żenada'; 'tadaima' jako powitanie bez echa)?
5. 👁️ WSTECZNA WERYFIKACJA PERCEPCYJNA (AUTONOMOUS BLIND-READING TEST): Odsuń na bok angielski skrypt i przeczytaj polską kwestię na zimno, z perspektywy polskiego widza w kinie. Czy kwestia brzmi tak, jakby została pierwotnie napisana po polsku przez wybitnego dramaturga? Jeśli w zdaniu wyczuwalny jest choćby cień kalki składniowej lub obcego szyku – natychmiast przeredaguj je na czystą, organiczną polszczyznę!

{canon_block}

{anime_guide}

Zwróć wynik jako obiekt JSON zgodny ze schematem."""


TIER_SUPREME_AFFECT = 120
TIER_DRAMA_AFFECT = 100
TIER_DIALOGUE_FLOW = 50
TIER_LEXICAL_REALIA = 10

TIER_SUPREME_PILLARS = {
    "CLXXII", "LXV", "LXVI", "CLVII", "CLXI"
}

TIER_1_PILLARS = {
    "CLXXII", "CLXX", "CLXIX", "CLXVIII", "CLXI", "CLX", "CLVIII", "CLVII", "CLVI", "CLV",
    "CXLIV", "CXLIII", "LXV", "LXVI", "LXVII", "LXXV", "LXXX", "LXXXIV", "LXXXVI", "LXXXVII",
    "XC", "XCVI", "CII", "CIV", "CV", "CVIII", "CXII", "CXVI", "CXXXI", "CXXXIV", "CXXXVI",
    "CXLVI"
}

TIER_3_PILLARS = {
    "LIX", "XXIV", "CXXXVII", "CXXXVIII", "XLI", "LVIII", "CLXIV", "CLXVII", "XVI", "XVII",
    "XXXVII", "LXXVIII", "XCVIII"
}

def calculate_rule_tier(rule_text: str) -> int:
    """Calculates attention priority tier for an AVT pillar rule."""
    m = re.search(r"FILAR\s+([IVXLCDM0-9]+)", rule_text)
    if m:
        pillar_id = m.group(1).upper()
        if pillar_id in TIER_SUPREME_PILLARS:
            return TIER_SUPREME_AFFECT
        if pillar_id in TIER_1_PILLARS:
            return TIER_DRAMA_AFFECT
        if pillar_id in TIER_3_PILLARS:
            return TIER_LEXICAL_REALIA
    lower = rule_text.lower()
    if any(k in lower for k in ["dynamiczny prymat afektu", "płacz", "drżenie", "izomorfizm suspensu", "napięcie składniowe"]):
        return TIER_SUPREME_AFFECT
    if any(k in lower for k in ["afekt", "seiyū", "seiyuu", "suspens", "prozodia", "pan/ty", "incognito"]):
        return TIER_DRAMA_AFFECT
    if any(k in lower for k in ["metryzacja", "jednostek", "literówek", "ortografii", "plansz", "interfejs"]):
        return TIER_LEXICAL_REALIA
    return TIER_DIALOGUE_FLOW


def get_focused_rules_for_batch(batch_items: List[Dict[str, Any]], max_rules: Optional[int] = None) -> str:
    """
    Dynamiczny dyspozytor reguł AVT (Context-Aware Rule Dispatcher).
    Analizuje specyfikę bieżącej paczki kwestii i generuje wysoce skoncentrowaną
    listę priorytetowych zasad, eliminując problem rozproszenia uwagi modelu ('Lost in the Middle').
    """
    if not batch_items:
        return ""

    # Defensive input normalization: guarantee all text fields are non-None strings (immune to NoneType/null)
    normalized_items = []
    for it in batch_items:
        if not isinstance(it, dict):
            continue
        clean_it = dict(it)
        for k in ["en", "pl", "audio_jp", "notes", "style", "speaker", "speaker_gender", "speaker_role"]:
            val = clean_it.get(k)
            clean_it[k] = str(val) if val is not None else ""
        normalized_items.append(clean_it)
    batch_items = normalized_items

    class ScoredPillarsCollector:
        def __init__(self):
            self.items: List[Tuple[int, str]] = []
        def append(self, item: Union[str, Tuple[int, str]]):
            if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int):
                self.items.append(item)
            elif isinstance(item, str):
                score = calculate_rule_tier(item)
                self.items.append((score, item))
        def extend(self, items: List[Union[str, Tuple[int, str]]]):
            for it in items:
                self.append(it)
        def __len__(self):
            return len(self.items)
        def __bool__(self):
            return bool(self.items)

    focused_pillars = ScoredPillarsCollector()
    combined_en = " ".join(item.get("en", "") for item in batch_items).lower()
    combined_jp = " ".join(str(item.get("audio_jp", "")) for item in batch_items).lower()
    has_signs = any(item.get("is_sign", False) for item in batch_items)
    has_questions = any("?" in item.get("en", "") for item in batch_items)
    has_ellipsis = any("..." in item.get("en", "") or "…" in item.get("en", "") for item in batch_items)
    has_music = any("♪" in item.get("en", "") or "♫" in item.get("en", "") or "sing" in item.get("notes", "").lower() for item in batch_items)

    # 1. Pytania potoczne i naturalna intonacja (Filar IX)
    if has_questions:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR IX - Naturalna Intonacja Pytań Potocznych]: "
            "W potocznych pytaniach rozstrzygnięcia preferuj intonację ('Jesteś pewna?', 'Idziesz z nami?'). "
            "Formę 'Czy' zachowaj dla pytań zależnych, alternatyw, tonu oficjalnego lub z namysłem."
        )

    # 2. Napisy ekranowe, tablice, tytuły
    if has_signs or any(w in combined_en for w in ["chapter", "episode", "present day", "tokyo", "sign", "title"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XLI & LX - Napisy Ekranowe, Plansze i AVT]: "
            "Napisy ekranowe i plansze tłumacz jako odrębne tytuły/nazwy (plansze: [ WERSALIKAMI W NAWIASIE ]). "
            "Kategoryczny zakaz wklejania w pole napisu ekranowego fragmentów dialogu mówionego!"
        )

    # 2b. Wielogłos, dialogi nakładające się i dymki mangi na ekranie (Filar LVII)
    has_dual_speaker = any(
        r"\N-" in it.get("en", "") or
        r"\N -" in it.get("en", "") or
        it.get("en", "").strip().startswith("-") or
        it.get("en", "").strip().startswith("–") or
        bool(re.search(r"[.!?…]+[\s\"']*(?:\\N|\n)?[-–—]\s*", it.get("en", "")))
        for it in batch_items
    )
    if has_dual_speaker:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LVII - Standard Wielogłosu i Zakaz Samotnych Myślników]: "
            "Gdy w jednej kwestii odzywają się dwie postacie (z myślnikami '- ') LUB kwestia łączy dymek mangi/planszę z dialogiem mówionym: "
            "BEZWZGLĘDNIE zachowaj format DWÓCH OSOBNYCH LINII z myślnikiem ze spacją na początku KAŻDEJ ('- Kwestia 1\\N- Kwestia 2'). "
            "KATEGORYCZNY ZAKAZ POJEDYNCZEGO MYŚLNIKA: jeśli kwestię wypowiada jedna postać, ZAKAZ wstawiania myślnika na początku ('- Ocalę cię' -> BŁĄD! Wymagane: 'Ocalę cię')! "
            "KATEGORYCZNY ZAKAZ łączenia wypowiedzi w jedną linijkę i zakaz wstawiania myślnika w środku zdania ('Kwestia 1 - Kwestia 2' -> BŁĄD KARDYNALNY)!"
        )

    # 3. Formy grzecznościowe, tytulatura feudalna i honoryfikatory
    if any(w in combined_en for w in ["sensei", "senpai", "sama", "lord", "young lord", "general", "sir", "master", "taso"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXV, XXVII & XXVIII - Tytulatura, Etykieta i Adaptacja Honoryfikatorów]: "
            "Zakaz tautologii ('To pan, Młody Panie' -> 'To ty, młody panie'), "
            "zakaz hybryd ('Pani Sensei' -> 'Sensei'), "
            "senpai adaptuj do imienia rozmówcy w wołaczu ('Rinko!' zamiast 'Senpai!') lub zwrotu na 'ty', "
            "sufiksy otaku (-taso, -tan) adaptuj do pełnego imienia w zależności od rejestru serii, "
            "zakaz powtarzania 'pan/pana' w każdym zdaniu (tytuł raz, potem naturalna 2. osoba)."
        )

    # 4. Zwroty Yobisute i relacje rówieśnicze
    has_yobisute_tokens = any(w in combined_en for w in ["chan", "kun", "yobisute"]) or any(
        "yobisute" in str(item.get("notes", "")).lower() or
        "yobisute" in str(item.get("relation_tag", "")).lower()
        for item in batch_items
    )
    if has_yobisute_tokens:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXVI & XXIX - Zasada Yobisute i Ewolucja Relacji]: "
            "Do przyjaciół, kolegów z klasy i towarzyszy po przełamaniu lodów zwracaj się po imieniu na 'ty'. "
            "Zakaz dodawania sztucznego 'Pan/Pani' przy samym imieniu ('Panie Issei' -> 'Issei') oraz per 'Pani [Nazwisko]' do rówieśniczek (stosuj samo nazwisko lub imię)."
        )

    # 5. Czasowniki wektorowe, cięcia scen i ląd/krajobraz
    if any(w in combined_en for w in ["i can see it", "mietekita", "look", "see", "there it is"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXXVII - Czasowniki Wektorowe i Obraz]: "
            "'I can see it' po cięciu na plener/podróż to 'Już widać!' / 'Widać cel!' (odnosi się do lądu/celu, a nie 'Widzę to po tobie')."
        )

    # 6. Matryca Aizuchi i potwierdzeń
    if any(w in combined_en for w in ["i see", "right", "makes sense", "naruhodo", "sou ne", "sou desu"]) or any(w in combined_jp for w in ["なるほど", "そうですね", "はい"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XLIII - Aprobata vs Przyjęcie Wiedzy i Dyrektywy]: "
            "Potwierdzenie trafnej uwagi rozmówcy (Sou / Sou ne) to 'Otóż to.' / 'Właśnie tak.' / 'Zgadza się.' (a NIE bierne 'Rozumiem.'). "
            "W odpowiedzi na ostrzeżenie/dyrektywę/polecenie (Hai/Ee) KATEGORYCZNIE ZAKAŻ 'Tak / T-Tak'! Użyj: 'Dobrze / D-Dobrze', 'Jasne', 'Będę uważać' lub 'W porządku'."
        )

    # 7. Spójność zdań rozbitych wielokropkiem i podział wierszy
    if has_ellipsis:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LVI, LIII, LX & XLIX - Spójność i Pragmatyka Ciszy]: "
            "Zdanie rozbite na dwa napisy musi tworzyć 100% spójną gramatycznie całość: "
            "tylko jedno orzeczenie (zakaz dublowania czasownika) i ścisła zgodność liczby podmiotu."
        )

    # 8. Paralingwistyka, odgłosy, kinezjatyka, somatyka i wulgaryzmy
    somatic_triggers = ["ottotto", "ototo", "whoa", "steady", "easy", "yoisho", "yotto", "acchichi", "sammu", "itta", "puha", "tch", "ara ara", "oi oi", "guh", "kuso", "damn", "shit", "fuck", "kashira", "mon", "aa", "speak", "say"]
    if any(w in combined_en for w in somatic_triggers) or any(w in combined_jp for w in ["おっと", "よいしょ", "よっと", "あっち", "痛っ", "さっむ", "ぷは"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XVIII, XXXIII, XVI & XVII - Kakegoe, Somatyka Ciała i Paralingwistyka]: "
            "Odruchy motoryczne i utratę równowagi (Ottotto) tłumacz somatycznie ('Ło, ło, ło...!', 'Uuu, powoli...!') lub usuń napis do '' (elipsa szumu wizualnego Netflix AVT). "
            "KATEGORYCZNY ZAKAZ angielskich kalek: 'Oho, spokojnie...', 'To jest gorące' (zastąp: 'Parzy!'), 'To boli' (zastąp: 'Ała!'). "
            "Gdy w audio słychać jedynie wdech/krzyk/wysiłek, KATEGORYCZNIE ZABRANIA SIĘ wstawiania fałszywych czasowników ('Mów—', 'Gadaj—')."
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

    # 10b. Kolokacje czasowo-szkolne i realia przerw (Filar III & XIV)
    if any(w in combined_en for w in ["lunch break", "noon recess", "break", "recess", "weekend", "holiday"]) or any(w in combined_jp for w in ["昼休み", "休み"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR III & XIV - Realia Szkolne i Kolokacje Czasowe]: "
            "Czas w polszczyźnie ma wymiar DŁUGOŚCI, a nie rozmiaru fizycznego: "
            "'lunch break / noon recess (昼休み)' to bezwzględnie 'długa przerwa' (lub 'przerwa obiadowa') — KATEGORYCZNY ZAKAZ: 'duża przerwa'! "
            "'short break / recess' to 'krótka przerwa' (ZAKAZ: 'mała przerwa'), 'long weekend' to 'długi weekend' (ZAKAZ: 'duży weekend')."
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

    # 14. Napięcie składniowe, zwroty akcji i izomorfizm suspensu (Filar LXV)
    if any(w in combined_en for w in ["never", "impossible", "betray", "traitor", "secret", "truth is", "actually", "no way"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXV - Izomorfizm Napięcia Składniowego i Anty-Spoiler]: "
            "Dopasuj polski szyk tak, by kluczowe rozstrzygnięcie/negacja padły na końcu zdania, "
            "idealnie w momencie wypowiedzenia przez aktora (zakaz zdradzania puenty na początku napisu!)."
        )

    # 15. Prozodia oddechu, wysiłek, szloch i zadyszka (Filar LXVI)
    if any(w in combined_en for w in ["pant", "gasp", "breath", "huff", "sob", "run", "heavy"]) or any("..." in item.get("en", "") and ("!" in item.get("en", "") or "?" in item.get("en", "")) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXVI - Prozodia Oddechu i Kinezjologia Mowy]: "
            "W scenach walki, zadyszki i szlochu stosuj krótkie, urywane takty rytmiczne dopasowane do oddechu seiyū."
        )

    # 16. Perspektywa empatyczna, relacje przysługi i kąt kamery Kuno (Filar LXVII)
    if any(w in combined_en for w in ["for me", "for you", "favor", "kureta", "moratta", "did it for", "helped me", "save me"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXVII - Kąt Kamery Empatycznej i Kuno]: "
            "Zachowaj wektor empatii w relacjach przysługi (kureru/morau) – precyzyjny celownik korzyści zamiast płaskich szablonów."
        )

    # 17. Pamięć leitmotywów, hasła i dewizy postaci (Filar LXVIII)
    if any(w in combined_en for w in ["promise", "vow", "oath", "motto", "destiny", "way of", "style"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXVIII - Pamięć Leitmotywów i Echa Narracyjnego]: "
            "Zachowaj żelazną, 100% powtarzalność leksykalną przysiąg, haseł i motywów przewodnich serii."
        )

    # 18. Przestrzeń akustyczna, tło i komunikaty diegetyczne (Filar LXIX)
    if any(w in combined_en for w in ["announcement", "speaker", "radio", "intercom", "broadcast", "crowd", "police"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXIX - Hierarchia Akustyczna i Soundstage]: "
            "Komunikaty z urządzeń umieszczaj u góry w nawiasie [ KOMUNIKAT ], a szum tła redukuj, chroniąc pierwszy plan."
        )

    # 19. Czwarta ściana, metanarracja i humor branżowy (Filar LXX)
    if any(w in combined_en for w in ["author", "manga", "anime", "budget", "deadline", "episode", "season", "voice actor", "seiyuu", "censor", "broadcast"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXX - Pragmatyka Metanarracyjna i 4. Ściana]: "
            "Żarty z tworzenia anime/mangi i telewizji adaptuj na błyskotliwy polski dowcip bez uciekania się do przypisów."
        )

    # 21. Fizyczność Świata i Izotopia Środowiskowa (Filar CXXXVIII)
    env_keys = ["beer", "piwo", "wine", "wino", "blood", "krew", "swamp", "bagno", "mud", "błoto", "acid", "kwas", "brewery", "browar", "underwater", "space", "kosmos"]
    if any(k in combined_en for k in env_keys):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXVIII & SOCZEWKA 2 (ŚWIAT) - Fizyczność Scenerii i Izotopia Środowiskowa]: "
            "Szanuj materię sceny! Jeśli postacie są w browarze z piwem/bagnie/kadzi wina -> ZAKAZ słowa 'woda' (He dragged him underwater -> 'Pociągnął go na dno' / 'Wciągnął go pod powierzchnię'). "
            "Kategoryczny zakaz 'powódź piwa' -> 'fala piwa' / 'morze piwa'!"
        )

    # 20. Matryca Idiomów Mostowych i Przeczeń Eliptycznych (Filar CXXXVII)
    bridge_keys = ["not him", "not her", "not this", "not now", "after you", "be my guest", "tell me about it", "look who's talking", "on it", "you bet", "there you go", "you don't say", "fair enough", "good for you", "i'm good", "way to go", "don't mention it", "out of the question", "take your time", "chigaimasu", "chigau", "betsu ni", "ii kara", "mou ii"]
    if any(k in combined_en for k in bridge_keys):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXVII - Matryca Idiomów Mostowych i Przeczeń Eliptycznych]: "
            "Krótkie idiomy eliptyczne tłumacz wedle polskiej intencji sytuacyjnej (np. 'After you' -> 'Proszę przodem', 'Tell me about it' -> 'Nawet mi nie mów', 'Not him' -> 'To nie on'), unikając dosłowności słów."
        )

    # 20. Dostępność leksykalna i szybkie tempo (Filar LXXI)
    if any(item.get("cps", 0) > 16 for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXI - Dostępność Leksykalna i Eliminacja Tarcia]: "
            "W szybkim tempie mowy używaj słów o wysokiej dostępności percepcyjnej, eliminując archaizmy i zacięcia lektury."
        )

    # 21. Dynamiczne sceny akcji, walka i ruch kamery (Filar LXXII)
    if any(w in combined_en for w in ["fight", "attack", "strike", "slash", "dodge", "punch", "run", "fast", "blast"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXII - Zgodność Wektora Kinezycznego i Spojrzenia]: "
            "W dynamicznych scenach akcji układaj zwięzłe wiersze zgodnie z trajektorią ruchu kamery i ciosów."
        )

    # 22. Modalność eksplanacyjna i partykuły dyskursu (Filar LXXIII)
    if any(w in combined_en for w in ["nda", "noda", "wake", "monoda", "because", "the reason is", "after all", "you see"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXIII - Modalność Eksplanacyjna Noda/Wake da]: "
            "Oddaj funkcję przyczynowo-wyjaśniającą za pomocą naturalnych partykuł ('Bo widzisz...', 'Chodzi o to, że...')."
        )

    # 23. Zmiana stylu na Chibi / SD i karykaturę (Filar LXXIV)
    if any(w in combined_en for w in ["chibi", "cute", "funny face", "whine", "pout", "dummy", "geez"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXIV - Plastyczność Rejestru Chibi / SD]: "
            "Gdy postać przechodzi w styl karykaturalny/Chibi, natychmiast przełącz rejestr na komediowy, pieszczotliwy lub dąsający się."
        )

    # 24. Szczyt intonacyjny F0 i akcent logiczny (Filar LXXV)
    if any(w in combined_en for w in ["you!", "traitor!", "liar!", "murderer!", "never!"]) or any(item.get("f0_peak", False) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXV - Zestrojenie Akcentu Logicznego i Prominencji F0]: "
            "Umieść wyraz o maksymalnym nacisku fonicznym aktora w pozycji naturalnego polskiego akcentu logicznego."
        )

    # 25. Dystansowanie honoryfikatywne i agresja bierna w Keigo (Filar LXXVI)
    if any(w in combined_en for w in ["desu wa", "sama", "excellency", "honorable", "sir", "pleasure"]) and any(w in combined_en for w in ["fool", "die", "insolence", "dare", "pathetic", "silence"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXVI - Dystansowanie Honoryfikatywne i Agresja Bierna]: "
            "Zachowaj lodowaty, dystyngowany, hiperpoprawny styl urzędowo-dworski z ironicznym szacunkiem (zakaz wulgaryzowania!)."
        )

    # 26. Onomatopeje graficzne i triangulacja SFX (Filar LXXVII)
    if any(w in combined_en for w in ["sfx", "boom", "thud", "rumble", "flash", "silence", "gasp", "clash"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXVII - Trójwarstwowa Triangulacja Onomatopei]: "
            "Unikaj dublowania dźwięków słyszalnych w audio; stany bezdźwięczne (cisza, błysk) oddawaj zwięźle w nawiasie lub dialogu."
        )

    # 27. Interfejsy diegetyczne, smartfony i czaty (Filar LXXVIII)
    if any(w in combined_en for w in ["sms", "text message", "chat", "smartphone", "phone", "hud", "system log", "mail"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXVIII - Interfejsy Diegetyczne i Smartfony]: "
            "Wiadomości z telefonu formatuj [ SMS od: Nadawca: Treść ], czaty stylizuj na autentyczny żargon sieciowy."
        )

    # 28. Transkreacja emocjonalna, rymy i toasty (Filar LXXIX)
    if any(w in combined_en for w in ["rhyme", "cheers", "toast", "poem", "song", "joke", "pun"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXIX - Transkreacja Emocjonalna i Indeks Afektywny]: "
            "W komedii, rymach i toastach priorytetem jest wywołanie autentycznej reakcji emocjonalnej (śmiech, wzruszenie) nad dosłownością."
        )

    # 29. Kognitywna mikro-interpunkcja afektywna (Filar LXXX)
    if any(w in combined_en for w in ["w-what", "i-i", "b-but", "n-no", "wha-", "wait-", "tsundere"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXX - Kognitywna Mikro-Interpunkcja Afektywna]: "
            "Jąkanie formatuj dywizem ('N-Nie!'), nagłe przerwanie myślnikiem ('że–'), zawstydzenie wielokropkiem ('...')."
        )

    # 30. Organiczna ekspozycja i zasada minimalizmu Ghibli (Filar LXXXI)
    if any(w in combined_en for w in ["explain", "exposition", "as you know", "in this world", "let me tell you"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXI - Organiczna Ekspozycja i Anty-Objaśnianie (Ghibli)]: "
            "Zaufaj inteligencji widza – nie wpychaj łopatologicznych wyjaśnień w dialog, gdy obraz i nastrój niosą sens sceny."
        )

    # 31. Semiotyczna negocjacja znaczenia i Deep Intent (Filar LXXXII)
    if any(w in combined_en for w in ["meaning", "intent", "spirit of", "metaphor", "symbol", "allegory"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXII - Semiotyczna Negocjacja Znaczenia (Umberto Eco)]: "
            "Poświęć drugorzędną dosłowność, aby w 100% ocalić głęboką intencję dzieła (intentio operis) i ładunek podtekstu."
        )

    # 32. Dynamizm docelowy i dekolonizacja składni (Filar LXXXIII)
    if any(w in combined_en for w in ["it is that", "there is no doubt that", "the fact that", "in order to"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXIII - Dynamizm Docelowy i Dekolonizacja Składni (Ladmiral)]: "
            "Zerwij z obcą strukturą zdania – napisz kwestię tak, jakby została pomyślana od zera w żywej polszczyźnie."
        )

    # 33. Wykonawczy kunszt aktorstwa głosowego i Mouth-Feel (Filar LXXXIV)
    if any(w in combined_en for w in ["shout", "whisper", "cry", "rage", "passion", "cadence", "speech"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXIV - Wykonawczy Kunszt i Mouth-Feel (Alexander O. Smith)]: "
            "Zoptymalizuj układ głosek i rytm frazy tak, by dialog naturalnie i gładko 'układał się w ustach' aktora."
        )

    # 34. Integracja kinematograficzna i eliminacja ślepoty napisowej (Filar LXXXV)
    if any(w in combined_en for w in ["cinematic", "visual", "landscape", "look at the", "silence", "beauty"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXV - Eliminacja Ślepoty Napisowej (Romero-Fresco)]: "
            "Kondensuj napis do absolutnego minimum, aby widz chłonął kompozycję kadru i grę aktorską, a nie tylko czytał tekst."
        )

    # 35. Polifonia głosów i heteroglosja postaci (Filar LXXXVI)
    if len(set(item.get("speaker_gender", "") for item in batch_items)) > 1 or any(item.get("speaker_role") for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXVI - Polifonia Głosów i Heteroglosja (Bachtin)]: "
            "Utrzymuj ostre zróżnicowanie idiolektów – każda postać musi mówić własnym, unikalnym językiem."
        )

    # 36. Czystość fokalizacji i monologu wewnętrznego (Filar LXXXVII)
    if any(item.get("is_thought", False) for item in batch_items) or any(w in combined_en for w in ["thought", "inner", "myself", "mind"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXVII - Czystość Fokalizacji i Myśli Wewnętrznej]: "
            "W monologu wewnętrznym zachowaj intymny, subiektywny punkt widzenia postaci bez chłodnego dystansu narratora."
        )

    # 37. Protokół anty-deformacyjny Antoine'a Bermana (Filar LXXXVIII)
    if any(w in combined_en for w in ["rough", "poetic", "raw", "vulgar", "sharp", "bizarre"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXVIII - Protokół Anty-Deformacyjny (Antoine Berman)]: "
            "Nie wygładzaj sztucznie poetyckich chropowatości i ostrości oryginału – zachowaj autentyczną siłę tekstu źródłowego."
        )

    # 38. Rekompensata hermeneutyczna i restytucja (Filar LXXXIX)
    if any(w in combined_en for w in ["lost in translation", "culture", "tradition", "custom", "idiom"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXIX - Rekompensata Hermeneutyczna (George Steiner)]: "
            "Odzyskaj ładunek emocjonalny utraconego niuansu kulturowego, wzbogacając sąsiednią kwestię."
        )

    # 39. Somatyczny rezonans emocjonalny (Filar XC)
    if any(w in combined_en for w in ["horror", "terror", "chills", "heartbreak", "laughter", "shock", "despair"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XC - Somatyczny Rezonans Emocjonalny (Douglas Robinson)]: "
            "Przekład musi wywoływać bezpośrednią reakcję cielesno-zmysłową (gęsia skórka, ucisk w gardle, śmiech) u polskiego widza."
        )

    # 39b. Fleksja imion obcych i dopełniacz dzierżawczy (Filar XCI)
    has_possessive = any(bool(re.search(r"\b[A-Z][a-z]+'s\b", it.get("en", ""))) or bool(re.search(r"\b(?:secrets?|sword|power|orders?|death|body|blood|will|life|shadow|tomb|castle|tower|realm|son|daughter|brother|father|mother)\s+of\s+[A-Z]", it.get("en", ""))) for it in batch_items)
    if has_possessive or any(w in combined_en for w in ["'s secrets", "'s sword", "'s power", "'s death", "'s life"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XCI - Żelazna Fleksja Imion Obcych/Fantasy i Dopełniacz Dzierżawczy]: "
            "KATEGORYCZNY ZAKAZ pozostawiania obcych/fantasy imion w mianowniku (np. 'Drel\'s secrets' -> 'sekretów Drela' [BŁĄD KOSZMARNY: 'sekretów Drel']). "
            "Imiona męskie na spółgłoskę bezwzględnie odmieniaj: Drel -> Drela, Gart -> Garta, Klen -> Klena."
        )

    # 40. Asymetria zaimków 3. osoby i triangulacja płci (Filar XCVI)
    if any(w in combined_en for w in ["they", "them", "their", "theirs", "kanojo"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XCVI - Asymetria Zaimków 3. Osoby i Płeć (Kanojo-tachi vs Karera)]: "
            "Gdy japońskie audio zawiera 'kanojo-tachi' (lub podmiotem są kobiety/dziewczęta), BEZWZGLĘDNIE używaj 'one / je / ich', a NIE męskoosobowego 'oni / ich'!"
        )

    # 41. Pragmatyka biesiadna i toasty (Filar XCVII)
    if any(w in combined_en for w in ["drinking", "drink", "have one", "cheers", "sake", "beer", "toast"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XCVII - Pragmatyka Biesiadna i Kumpelskie Zaproszenia]: "
            "Pytania o alkohol ('You're drinking, right?') tłumacz biesiadnie ('Chyba nie odmówisz?', 'Ze mną się nie napijesz?'), ZAKAZ dosłownego 'Przecież pijesz'!"
        )

    # 42. Typografia plansz tytułowych (Filar XCVIII)
    if any(item.get("is_sign", False) for item in batch_items) or any(w in combined_en for w in ["season", "chapter", "episode", "part", "fire force"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XCVIII - Typografia Plansz Tytułowych i Zwięzłość Typesettingu]: "
            "Długie tytuły i plansze (>22 znaki) formatuj w DWÓCH WYŚRODKOWANYCH WIERSZACH z \\N (np. 'SPECJALNE SIŁY POŻARNICZE\\NCZĘŚĆ TRZECIA'), aby nie wychodziły poza kadr!"
        )

    # 43. Zakaz nadgorliwej eksplikacji i wtrącania imion (Filar XCIX)
    if any(w in combined_en for w in ["erm", "um", "hey,", "ano", "etto", "chotto", "wait,"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XCIX - Zakaz Nadgorliwej Eksplikacji i Wtrącania Imion]: "
            "Zwykłe zawahania ('Erm, hey') tłumacz jako 'Przepraszam...', 'Zaraz, hej...'. KATEGORYCZNY ZAKAZ samowolnego wklejania imion postaci ('Panie Kamui...')!"
        )

    # 44. Japońskie Yobisute i zakaz fałszywej tytulatury (Filar C)
    if any(len(item.get("en", "").split()) <= 2 and "?" in item.get("en", "") for item in batch_items) or any(w in combined_en for w in ["kamui", "shinra", "arthur", "lord", "mr."]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR C - Japońskie Yobisute i Zakaz Fałszywego 'Panie X']: "
            "Gdy w audio pada samo imię (Yobisute), stosuj SAMO IMIĘ w wołaczu ('Kamui?'). KATEGORYCZNY ZAKAZ dodawania sztucznego 'Panie Kamui?' w walce i akcji!"
        )

    # 45. Nadrzędność japońskiego audio i triangulacja perspektywy (Filar CI)
    if any(w in combined_en for w in ["ask", "tell", "hear", "listen", "know", "kikanaide", "kikitakunai"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CI - Nadrzędność Japońskiego Audio i Perspektywa (Kikanaide)]: "
            "Gdy japońskie audio zawiera 'Kikanaide', tłumacz jako 'Nawet nie pytaj...', 'Nie pytaj...'. KATEGORYCZNY ZAKAZ 'Wolę nie wiedzieć'!"
        )

    # 46. Dystrybucja leksykalna i zaimkowa substytucja deiktyczna (Filar CII)
    if any(w in combined_en for w in ["buy this", "take this", "this book", "this sword", "this letter", "this thing", "that book"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CII - Zaimkowa Substytucja Deiktyczna i Zakaz Powtórzeń Rzeczowników]: "
            "Gdy postać wskazuje/kupuje/dotyka przedmiotu w kadrze ('buy this book'), zastąp rzeczownik zaimkiem ('Chciałabym ją/to kupić'). KATEGORYCZNY ZAKAZ powtarzania tego samego rzeczownika ('książka... księga... tę książkę')!"
        )

    # 47. Pragmatyka japońskich aktów prośby i rozkazu (Filar CIII)
    if any(w in combined_en for w in ["please", "help me", "can you", "could you", "give me", "kure", "kase", "kudasai"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CIII - Pragmatyka Próśb i Rozkazów (Kure / Moraeru / Kudasai)]: "
            "W scenach walki i pośpiechu ('Tasukete kure!') stosuj twarde rozkazy ('Pomóż mi!', 'Ratuj!'), ZAKAZ sztucznego 'Proszę, pomóż mi'. Prośby kumpelskie ('Kashite') tłumacz jako 'Dawaj to!', 'Pożycz mi to!'."
        )

    # 48. Somatyka emocji i mimetyki (Filar CIV)
    if any(w in combined_en for w in ["excited", "nervous", "heart is", "irritat", "chills", "scared", "doki", "waku", "ira ira"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CIV - Somatyka Emocji i Japońskie Mimetyki (Gitaigo)]: "
            "Mimetyki tłumacz bogatą polską frazeologią somatyczną: Doki doki -> 'Serce podchodzi mi do gardła', Waku waku -> 'Aż mnie nosi z ekscytacji!', Ira ira -> 'Krew mnie zalewa', Zoku zoku -> 'Aż ciarki mnie przechodzą'!"
        )

    # 49. Haragei i poetyka niedopowiedzenia (Filar CV)
    if any(w.endswith("...") or w in ["but...", "though...", "kedo", "kara", "tara"] for w in combined_en.split()):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CV - Haragei i Poetyka Niedopowiedzenia (Kedo/Kara/Ellipsis)]: "
            "Gdy japońska kwestia urywa się na partykułę zawieszenia lub wielokropek, NIE dopowiadaj reszty zdania! Stosuj nastrojowy wielokropek ('Też bym chciała, ale...', 'Przecież wiesz, że...')."
        )

    # 50. Aizuchi i higiena phatyczna (Filar CVI)
    if any(w in combined_en.split() for w in ["yeah", "right", "i see", "un", "sou", "fumu", "mhm"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CVI - Aizuchi i Higiena Phatyczna (Anti-Clutter)]: "
            "Puste japońskie potaknięcia podtrzymujące kontakt (Un, Sou) redukuj w napisach (kondensacja AVT) lub zamieniaj na oszczędne 'Mhm', 'No', 'Jasne'."
        )

    # 51. Asymetria Keigo (Filar CVII)
    if any(w in combined_en for w in ["lord", "master", "sir", "lady", "senpai", "sama", "dono"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CVII - Asymetria Społeczna Keigo (Sonkeigo vs Kenjōgo)]: "
            "Różnicuj uniżanie siebie ('pozwolę sobie zauważyć', 'służę pomocą') od wywyższania szefa/seniora ('raczy pan spocząć', 'czy zechciałby pan'). ZAKAZ spłaszczania obu do 'Please sit'."
        )

    # 52. Kinezyka spojrzenia i subtekst mikromimiki (Filar CVIII)
    if any(w in combined_en for w in ["don't get the wrong idea", "idiot", "not like i", "blush", "baka"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CVIII - Kinezyka Spojrzenia i Subtekst Mikromimiki]: "
            "Gdy w kadrze widać rumieniec, unikanie wzroku lub zawstydzenie, tłumacz psychologiczny SUBTEKST (np. 'Żebyś sobie tylko czegoś nie pomyślał!'), a nie szkolną kalkę z angielskiego!"
        )

    # 53. Relacyjność Uchi/Soto i stopnie pokrewieństwa (Filar CIX)
    if any(w in combined_en for w in ["my dad", "my father", "my mom", "my mother", "old man", "oyaji", "aniki", "bro"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CIX - Relacyjność Uchi/Soto i Pokrewieństwo (Oyaji/Aniki)]: "
            "Młodzieżowe Oyaji do kolegów tłumacz jako 'Stary / Ojciec' (ZAKAZ: 'Mój ojciec'). Aniki u chuliganów/yakuzy to 'Szefie / Starszy bracie', a w rodzinie 'Braciszku'."
        )

    # 54. Triangulacja długu Giri i Sumimasen (Filar CX)
    if any(w in combined_en for w in ["sorry", "excuse me", "sumimasen", "thank you for saving", "trouble"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CX - Dług Giri i Sumimasen jako Wina/Wdzięczność]: "
            "Gdy ranna postać otrzymuje pomoc/strawę, Sumimasen to 'Wybacz kłopot...', 'Nie trzeba było...', 'Dziękuję i wybacz...'. KATEGORYCZNY ZAKAZ monotonnego 'Przepraszam'!"
        )

    # 55. Japońska zjadliwość Iyami (Filar CXI)
    if any(w in combined_en for w in ["good job", "hard work", "impressive", "such an honor", "gokurou"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXI - Japońska Zjadliwość Iyami (Inverted Politeness)]: "
            "Fałszywe komplementy wrogów w Keigo tłumacz jako jadowitą polską ironię salonową ('Doprawdy, imponujący wyczyn...', 'Cóż za popis...'). ZAKAZ brania pochwał dosłownie!"
        )

    # 56. Semiotyka ciszy Ma (Filar CXII)
    if any(len(item.get("en", "").split()) <= 3 for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXII - Semiotyka Ciszy Ma (間) i Zwięzłość AVT]: "
            "Krótkie kwestie tłumacz zwięźle i dosadnie, pozwalając na wygaszenie napisu w momencie nadejścia ciszy i pauzy dramatycznej w scenie!"
        )

    # 57. Dialekty Kansai-ben i Hōgen (Filar CXIII)
    if any(w in combined_en for w in ["y'all", "ain't", "nande ya", "akan", "honma", "seyana", "howdy"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXIII - Dyskretna Stylizacja Dialektów (Kansai-ben)]: "
            "Dialekty regionalne tłumacz zadziorną polszczyzną miejską ('Co ty bredzisz?!', 'No to leżymy...'). KATEGORYCZNY ZAKAZ tworzenia karykatury góralskiej!"
        )

    # 58. Kalambury i Homofony (Filar CXIV)
    if any(w in combined_en for w in ["pun", "joke", "wordplay", "dajare", "kami", "kame"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXIV - Kalambury i Homofony bez Przypisów (Barańczak)]: "
            "Twórz autonomiczne polskie kalambury fonetyczne. KATEGORYCZNY ZAKAZ wstawiania przypisów w klamrach [Przyp. tłum.]!"
        )

    # 59. Zdrobnienia i Hipokorystyki (Filar CXV)
    if any(w in combined_en for w in ["-tan", "-pyon", "-cchi", "-rin", "bozu"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXV - Hipokorystyki i Polskie Zdrobnienia]: "
            "Japońskie sufiksy pieszczotliwości przekładaj na bogatą polską paletę zdrobnień ('Rinusia', 'szkrab', 'maluch')."
        )

    # 60. Izomorfizm długich samogłosek (Filar CXVI)
    if any(re.search(r"(?:a{3,}|e{3,}|o{3,}|u{3,}|i{3,})", item.get("en", "").lower()) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXVI - Izomorfizm Długich Samogłosek (Chōon)]: "
            "Przeciągłe okrzyki formatuj z ekspresyjnym wydłużeniem liter ('Auaaa...!', 'Nieee...!', 'Ratunkuuu...!'), zgrane z ruchem ust aktora."
        )

    # 61. Pragmatyka odmowy 'ii desu / kekkou' (Filar CXVII)
    if any(w in combined_en for w in ["i'm fine", "i'm good", "no thanks", "ii desu", "kekkou", "fine."]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXVII - Pragmatyka Odmowy (Boku wa ii desu / I'm fine)]: "
            "W odpowiedzi na zaproszenie, propozycję lub poczęstunek 'ii desu' / 'I'm fine' oznacza ODMOWĘ ('Ja... podziękuję.', 'Nie mam ochoty.', 'Ja zostanę.'). KATEGORYCZNY ZAKAZ tłumaczenia jako stan zdrowia ('Nic mi nie jest')!"
        )

    # 62. Piosenki i Wiersze (Filar CXVIII)
    if any("♪" in item.get("en", "") or "♫" in item.get("en", "") or "song" in item.get("style", "").lower() or "karaoke" in item.get("style", "").lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXVIII - Transkreacja Poetycko-Sylogiczna Piosenek i Rymów (Barańczak)]: "
            "Kwestie z nutką '♪' / '♫' lub stylem piosenki tłumacz wierszem sylabicznym o równej liczbie sylab i zgrabnych polskich rymach (AABB/ABAB). KATEGORYCZNY ZAKAZ nierymowanej prozy!"
        )

    # 63. Matryca Idiolektów (Filar CXIX)
    if any(item.get("speaker") for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXIX - Matryca Idiolektów i Unikalny Głos Postaci]: "
            "Utrzymuj unikalny styl wypowiedzi dla każdego bohatera (chuligan = szorstka leksyka i brak 'pana'; arystokratka = chłodny dystans i peryfrazy; tsundere = maskowana troska i sarkazm)."
        )

    # 64. Wyznania miłosne i Kokuhaku (Filar CXXI)
    if any(w in combined_en for w in ["like you", "really like", "love", "suki", "daisuki", "aishiteru", "confess", "feelings for you", "crush"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXI - Wyznania Miłosne i Kokuhaku (Suki da vs Kocham cię)]: "
            "W scenach romantycznych i wyznaniach miłosnych 'I like you' / 'suki' to wyznanie miłości ('Kocham cię', 'Zakochałam się w tobie', 'Tak mi na tobie zależy'). KATEGORYCZNY ZAKAZ szkolnego 'Lubię cię'!"
        )

    # 65. Pożegnania ostateczne i misje bojowe (Filar CXXII)
    if any(w in combined_en for w in ["goodbye", "farewell", "sayonara", "itte kimasu", "itterasshai", "leaving", "parting"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXII - Poetyka Pożegnania Ostatecznego (Sayōnara vs Itte kimasu)]: "
            "Rozróżniaj 'Sayōnara' (pożegnanie ostateczne/śmierć -> 'Żegnaj') od 'Itte kimasu' (wyruszenie na misję -> 'Pora na mnie / Ruszam w drogę' -> 'Wracaj cały!'). Zakaz szkolnego 'Do widzenia' na polu bitwy!"
        )

    # 66. Magia performatywna i zaklęcia (Filar CXXIII)
    if any(w in combined_en for w in ["spell", "cast", "incantation", "awaken", "seal", "pact", "flame", "summon", "kaiho", "power"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXIII - Magia Performatywna i Inkantacje]: "
            "W zaklęciach i formułach mocy stosuj czasowniki performatywne czasu teraźniejszego dokonanego ('Rozkazuję ci, płomieniu...', 'Mocą paktu, obudź się!'). Zakaz trybu opisowego!"
        )

    # 67. Tytulatura dworsko-feudalna (Filar CXXIV)
    if any(w in combined_en for w in ["majesty", "highness", "your grace", "emperor", "empress", "king", "queen", "prince", "princess", "lord", "lady"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXIV - Polska Tytulatura Dworsko-Feudalna]: "
            "Stosuj ścisłą hierarchię: Cesarz ('Wasza Cesarska Mość'), Król ('Wasza Królewska Mość / Wasza Wysokość'), Książę ('Wasza Książęca Mość / Młody panie'), Feudał ('Wasza Miłość / Mój panie'). Zakaz potworków 'Wasz Lordzie'!"
        )

    # 68. Ergonomia gagów slapstickowych (Filar CXXV)
    if any(w in combined_en for w in ["ouch", "slap", "hit", "crash", "run!", "get out", "ow!", "wha?!", "moron!"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXV - Ergonomia Gagów Slapstickowych i Komedii Fizycznej]: "
            "W dynamicznych scenach humoru fizycznego redukuj napis do 1–3 słów wykrzyknikowych ('Ała!', 'Stój, durniu!', 'Oszalałeś?!'), aby nie zasłaniać animacji gagu."
        )

    # 69. Socjolekt Kansai i Dialekty Regionalne (Filar CXXVI)
    if any(w in combined_en for w in ["kansai", "osaka", "nande ya", "akan", "honma", "seyana", "ya nen", "dappe"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXVI - Socjolekt Kansai i Dialekty Regionalne]: "
            "Stosuj zadziorną, dynamiczną polszczyznę miejsko-kolokwialną ('Co ty bredzisz?!', 'No to leżymy...'). Zakaz karykatury góralskiej!"
        )

    # 70. Socjolekt Półświatka i Gangsterów (Filar CXXVII)
    if any(w in combined_en for w in ["yakuza", "gang", "boss", "underworld", "cops", "mob", "delinquent", "punk"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXVII - Socjolekt Półświatka i Gangsterów]: "
            "Stosuj autentyczną, twardą polszczyznę uliczną i gangsterską ('Gliny', 'frajer', 'zwijamy się', 'sprzątnąć go')."
        )

    # 71. Żargon Graczy i MMORPG (Filar CXXVIII)
    if any(w in combined_en for w in ["quest", "aggro", "tank", "buff", "debuff", "party", "respawn", "stats", "dungeon", "level up", "loot", "drop"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXVIII - Żargon Graczy i Metanarracja MMORPG]: "
            "Stosuj autentyczny polski socjolekt gamingowy ('ściągnąć aggro', 'tankować', 'drop', 'buffy', 'party', 'respawn', 'staty')."
        )

    # 72. Mowa Dworzan i Arystokratyczny Ojou-sama (Filar CXXIX)
    if any(w in combined_en for w in ["desu wa", "noble", "lady", "aristocrat", "courtesy", "grace", "pleasure"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXIX - Mowa Dworzan i Arystokratyczny Ojou-sama]: "
            "Stosuj lodowatą, wykwintną grzeczność salonową, peryfrazy i chłodny dystans ('Będzie nam niezmiernie miło...', 'Cóż za zaszczyt...')."
        )

    # 73. Głos Maszyn, AI i Systemów Operacyjnych (Filar CXXX)
    if any(re.search(rf"\b{w}\b", combined_en) for w in ["system", "target", "locked", "initiating", "protocol", "error", "hud", "ai", "online", "standby"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXX - Głos Maszyn, AI i Systemów Operacyjnych]: "
            "Stosuj beznamiętny, lakoniczny tryb orzekający czasu teraźniejszego ('Cel namierzony. Autoryzacja zakończona sukcesem.')."
        )

    # 74. Wektor Batalistyczny i Zakaz Fałszywych Dopełnień (Filar CXXXI)
    if any(w in combined_en for w in ["attacking from", "from above", "from behind", "pushing through", "flanking", "charging down", "striking from"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXI - Wektor Batalistyczny i Zakaz Fałszywych Dopełnień]: "
            "Gdy sojusznicy atakują wroga z góry/z flanki, KATEGORYCZNIE ZAKAZANE jest dopisywanie zaimka 'nas' ('Rażą nas z góry' -> BŁĄD!). Tłumacz jako: 'Uderzają z góry!', 'Szarżują ze wzgórza!', 'Przełamują szyk!'."
        )

    # 75. Pragmatyka „Sasuga” i Dumy Wspólnotowej (Filar CXXXII)
    if any(w in combined_en for w in ["that's the", "for you", "that's a", "sasuga", "as expected of"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXII - Pragmatyka „Sasuga” i Dumy Wspólnotowej]: "
            "Zwroty typu 'That's the [X] for you' / 'Sasuga' tłumacz jako dumne: 'Jak przystało na [plemię/postać]!', 'Oto [X] w całej krasie!', 'W swoim żywiole!'. KATEGORYCZNY ZAKAZ złośliwej kalki 'Całe plemię X...'!"
        )

    # 76. Twarda Retoryka Rozkazów Bojowych (Filar CXXXIII)
    if any(w in combined_en for w in ["rout them", "hold the line", "all units", "charge!", "advance!", "fall back!", "take down the", "cut down"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXIII - Twarda Retoryka Rozkazów Bojowych]: "
            "Rozkazy dowódców tłumacz lakonicznie i bezlitośnie: 'Wytłuc ich do nogi!', 'Trzymać szyk!', 'Ani kroku w tył!', 'Do ataku!', 'Dopaść dowódcę!'. Zakaz ugrzecznionych, szkolnych form!"
        )

    # 77. Mikro-Wokalizy i Dźwięki Wahania (Filar CXXXIV)
    if any(item.get("duration_s", 1.0) <= 0.6 or any(w in item.get("en", "").lower() for w in ["i mean...", "uh...", "um...", "er...", "well...", "eh...", "ah..."]) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXIV - Mikro-Wokalizy i Dźwięki Wahania (<0.6s)]: "
            "Kwestie trwające ułamek sekundy (<=0.6s) lub wahania seiyū ('e...', 'ano...') redukuj do MAX 1-2 słów ('Znaczy...', 'Ech...', 'Cóż...'). KATEGORYCZNY ZAKAZ wielowyrazowych zdań!"
        )

    # 78. Japońska Matryca 8 Dialektów Regionalnych (Filar CXXXV)
    if any(w in combined_en for w in ["chesto", "gowasu", "satsuma", "tsugaru", "tohoku", "hiroshima", "jaken", "hakata", "nagoya", "okinawa", "haisai", "nankurunaisa", "namara", "shibareru", "hokkaido", "dialect", "accent", "koito"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXV - Japońska Matryca 8 Dialektów Regionalnych (Hōgen & Yakuwarigo)]: "
            "Stosuj zróżnicowaną stylizację dla 8 grup dialektalnych (Satsuma-ben: fonetyczne ściągnięcia 'Sierżan' Cukszma góni za Asirpoł!', Kansai: zadziorna miejska polszczyzna, Tohoku: ciepła mowa gawędziarska 'dyć prawda', Hiroshima: twardy slang Yakuzy 'bo ci łeb urwę', Okinawa: słoneczna życzliwość). Zakaz karykatury góralskiej!"
        )

    # 79. Triangulacja Kognitywna i Foniczna Wieku/Płci (Filar CXXXVI)
    if any(item.get("speaker_gender") in ["chłopiec", "dziewczynka", "mężczyzna", "kobieta"] or any(w in item.get("en", "").lower() for w in ["i guessed", "i figured", "i thought", "i knew", "i was", "i did", "i felt", "i saw", "i heard", "i wanted", "would i", "i would", "should i", "i should", "could i", "i could", "blame"]) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXVI - Triangulacja Kognitywna i Foniczna Wieku/Płci (Chłopiec vs Dziewczynka vs Dorosły vs Starsza Kobieta)]: "
            "Dopasuj rodzaj gramatyczny czasowników 1. osoby (-łem/-łabym vs -łam/-łabym): Dorosły mężczyzna oraz Mały chłopiec (mimo wysokiego głosu seiyū!) BEZWZGLĘDNIE otrzymują formy męskie ('Domyślałem się', 'Zgubiłem się!', 'Wiedziałem'). Kobieta, Starsza kobieta/matrona (mimo niskiego/ochrypłego tembru seiyū!) oraz Mała dziewczynka BEZWZGLĘDNIE otrzymują formy żeńskie w czasie przeszłym (-łam) i trybie przypuszczającym (-łabym: 'miałabym', 'chciałabym', 'byłabym')."
        )

    # 80. Paradoks Potwierdzenia Negacji i Pytań Przeczących (Filar CXXXIX)
    neg_q_patterns = ["didn't", "don't", "aren't", "won't", "can't", "isn't", "haven't", "nie idziesz", "nie wiesz", "nie chcesz"]
    ans_patterns = ["yes", "no", "yeah", "nah", "hai", "iie", "tak", "nie"]
    if any(q in combined_en for q in neg_q_patterns) and any(w in combined_en for w in ans_patterns):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXIX - Paradoks Potwierdzenia Negacji i Pytań Przeczących (Hai/Iie & Reverse Logic)]: "
            "ODWRÓCONA LOGIKA JAPOŃSKIEJ ZGODY! Przy pytaniu przeczącym ('Nie idziesz?', 'Didn't you know?') japońskie 'Hai' / ang. 'Yes' oznacza: "
            "'Zgadza się, masz rację – NIE IDĘ!' -> po polsku BEZWZGLĘDNIE: „Nie!” / „Nie idę!” (KARDYNALNY BŁĄD [X]: „Tak, nie idę” / „Tak”). "
            "Japońskie 'Iie' / ang. 'No' oznacza: „Właśnie że tak!” / „Pewnie, że idę!” (KARDYNALNY BŁĄD [X]: „Nie”). Skoreluj z opadającym tonem seiyū!"
        )

    # 81. Społeczne Metafory Pokrewieństwa (Filar CXL)
    kin_patterns = ["onii", "onee", "ojisan", "obasan", "big brother", "big sister", "brother", "sister", "uncle", "auntie", "mister"]
    if any(w in combined_en for w in kin_patterns):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXL - Społeczne Metafory Pokrewieństwa (Onii-san / Ojisan Sanitization)]: "
            "ZAKAZ TWORZENIA FAŁSZYWYCH BRACI I WUJKÓW! Gdy dziecko lub nastolatek mówi do obcego człowieka na ulicy/w walce 'Onii-san' / 'Onee-san' / 'Ojisan': "
            "BEZWZGLĘDNY ZAKAZ: „mój bracie!”, „braciszku!”, „wujku!”. Tłumacz jako: „Proszę pana!”, „Hej, panie!”, „Kolego!”, „Młodzieńcze!”, „Proszę pani!”. "
            "Gdy w tagach audio występuje [Ton: emocjonalne drżenie głosu / płacz], 'Onii-chan, tasukete!' -> „Proszę pana, pomocy!”!"
        )

    # 82. Dynamika Stanu Rezultatywnego (Filar CXLI)
    state_patterns = ["shinde", "kekkon", "futotte", "kawaite", "is dead", "he's dead", "she's dead", "dying", "married", "marrying", "is dry", "has won"]
    if any(w in combined_en for w in state_patterns):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLI - Dynamika Stanu Rezultatywnego (-te iru as Resulting State)]: "
            "STAN WYNIKOWY TO NIE AKCJA W TOKU! Japońskie '-te iru' to często skutek dokonany: "
            "'Shinde iru' -> BEZWZGLĘDNIE: „Nie żyje!” / „Jest martwy!” / „Zginął!” (KARDYNALNY BŁĄD [X]: „On umiera w tej chwili!”). "
            "'Kekkon shite iru' -> BEZWZGLĘDNIE: „Jest żonaty / ma męża” (ZAKAZ: „Bierze ślub”). "
            "'Futotte iru' -> BEZWZGLĘDNIE: „Jest gruby / przy kości” (ZAKAZ: „Tyje”)."
        )

    # 83. Retoryka Zachwytu w Pytaniach Przeczących i Prozodia (Filar CXLII)
    praise_patterns = ["janai", "isn't it", "doesn't it", "aren't you", "don't you think", "umai", "oishii", "sugoi", "delicious", "tasty", "great", "amazing"]
    if any(w in combined_en for w in praise_patterns):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLII - Retoryka Zachwytu w Pytaniach Przeczących i Prozodia (Janai ka Affirmation)]: "
            "NEGACJA JAKO EKSPRESJA PODZIWU! 'Kore, umai janai?!' / 'Sugoi janai ka!' przy podniesionym głosie seiyū [Ton: silne wzburzenie emocjonalne / krzyk] "
            "to 100% zachwyt i entuzjazm: BEZWZGLĘDNIE: „Ależ to pyszne!” / „Dobre, co?!” / „Ale czad!” / „Niesamowite!”. "
            "KARDYNALNY BŁĄD [X]: „To chyba niedobre, co?” / „Czy to nie jest niesamowite?”."
        )

    # 84. Zgodność Kinetyki Warg i Budżet Sylabiczny (Filar CXLIII)
    if any(item.get("duration_s", 1.0) <= 0.7 for item in batch_items) or any("mouth-pacing" in str(item.get("prosody", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLIII - Zgodność Kinetyki Warg i Budżet Sylabiczny (Mouth-Pacing)]: "
            "Kwestie trwające ułamek sekundy (<=0.7s) podlegają rygorystycznemu limitowi sylab! KATEGORYCZNY ZAKAZ zdań 7-9 sylabowych. "
            "Kondensuj do max 2-4 sylab ('Stój!', 'Idiota!', 'Daj spokój!')."
        )

    # 85. Prymat Autentycznego Głosu Seiyū (Filar CXLIV)
    if any(item.get("audio_alert") for item in batch_items) or any(w in combined_en for w in ["damn", "hell", "wait", "stop", "hold on", "kuso", "chikushou", "yabai"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLIV - Prymat Autentycznego Głosu Seiyū Nad Skryptem Pośrednim (Ad-Libbing)]: "
            "Gdy seiyū w audio krzyczy Chikushō / Kuso / Yabai / Matte / Yamero, a skrypt EN to osłabia lub pomija, BEZWZGLĘDNY PRIORYTET ma audio seiyū: "
            "wzbogać polski dialog o autentyczny ładunek ('Niech to szlag!', 'Szlag by to!', 'Czekaj!', 'Przestań!')."
        )

    # 86. Dialogowy Ping-Pong i Spójność Riposty (Filar CXLVI)
    if any("ping-pong" in str(item.get("relation_tag", "")).lower() for item in batch_items) or any(item.get("en", "").strip().endswith("?") for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLVI - Dialogowy Ping-Pong i Spójność Leksykalna Riposty (Conversational Volley)]: "
            "Zgraj ripostę z pytaniem rozmówcy! Unikaj suchych zaprzeczeń (np. 'Oszalałeś?' -> 'A żebyś wiedział!'). "
            "Na OSTRZEŻENIA i POLECENIA ('Uważaj pod nogi', 'Poczekaj', 'Chodź') KATEGORYCZNIE ZAKAŻ 'Tak / T-Tak'! "
            "Użyj naturalnego potwierdzenia przyjęcia: 'Dobrze / D-Dobrze', 'Jasne', 'Będę uważać', 'W porządku' lub 'Dzięki'."
        )

    # 87. Matryca Przysłówków Modalnych i Pragmatycznych (Filar CXLVII)
    modal_jp_tokens = ["tabun", "osoraku", "yappari", "yahari", "sasuga", "douse", "masaka", "shouganai", "shikata", "zettai", "kanarazu", "たぶん", "恐らく", "やっぱり", "さすが", "どうせ", "まさか", "仕方", "絶対", "必ず"]
    if any(any(tok in str(item.get("audio_jp", "")).lower() for tok in modal_jp_tokens) for item in batch_items) or any(any(w in str(item.get("en", "")).lower() for w in ["probably", "after all", "as expected", "anyway", "no way", "can't be helped", "definitely"]) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLVII - Matryca Przysłówków Modalnych i Pragmatycznych (Epistemic Matrix)]: "
            "Precyzyjnie dopasuj stopień pewności ze słuchem seiyū! Tabun/Osoraku -> 'Chyba' / 'Pewnie' / 'Raczej' (KATEGORYCZNY ZAKAZ: 'Na pewno / Na pewno nie'!). "
            "Yappari -> 'Wiedziałem!' / 'A jednak!' (ZAKAZ: 'Po wszystkim'). Sasuga -> 'Jak przystało na mistrza!' / 'Bez przesady!'. "
            "Douse -> 'I tak nic z tego...'. Masaka -> 'Niemożliwe!' / 'Chyba kpisz!'. Shouganai -> 'Trudno...' / 'Nic nie poradzimy...' (ZAKAZ: 'Nie da się pomóc')."
        )

    # 88. Pragmatyka Pytań o Wiarygodność i Szok Poznawczy (Filar CXLVIII)
    veracity_tokens = ["honto", "tashika", "makoto", "is that true", "really", "for real", "true?", "本当", "確か", "誠"]
    if any(any(tok in str(item.get("audio_jp", "")).lower() for tok in veracity_tokens) for item in batch_items) or any(any(w in str(item.get("en", "")).lower() for w in ["is that true", "really?", "for real?", "is it true"]) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLVIII - Pragmatyka Pytań o Wiarygodność i Szok Poznawczy (Veracity Matrix)]: "
            "KATEGORYCZNY ZAKAZ urzędowego 'To prawda?' w scenach grozy, wojny i szoku! "
            "Dopasuj żywą ludzką reakcję: 'To pewne?!' / 'Jesteś pewna?!' / 'Więc to prawda...?!' / 'Prawdę mówisz?!' / 'Serio?!'."
        )

    # 89. Matryca Odpowiedzi Zawoalowanych i Ukrytych Odmów (Filar CXLIX - Haragei)
    haragei_tokens = ["daijoubu", "daijobu", "chotto", "大丈夫", "ちょっと"]
    if any(any(tok in str(item.get("audio_jp", "")).lower() for tok in haragei_tokens) for item in batch_items) or any(any(w in str(item.get("en", "")).lower() for w in ["i'm okay", "i'm fine", "that's a bit", "a little..."]) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLIX - Haragei: Odpowiedzi Zawoalowane i Odmowy (Daijoubu & Chotto)]: "
            "Gdy postać odpowiada 'Daijoubu' na propozycję/ofertę pomocy -> to ODMOWA: 'Nie trzeba, dziękuję' / 'Obejdzie się' / 'Dam radę' (KATEGORYCZNY ZAKAZ mylącego 'W porządku'). "
            "Gdy seiyuu mówi 'Chotto...' w odpowiedzi na prośbę -> 'Raczej nie da rady...' / 'Obawiam się, że to niemożliwe...' (ZAKAZ 'Trochę...')."
        )

    # 90. Pragmatyka Wielofunkcyjnego Hora! i Fuzja z Prozodią (Filar CL)
    if any(any(tok in str(item.get("audio_jp", "")).lower() for tok in ["hora", "ほら"]) for item in batch_items) or any(any(w in str(item.get("en", "")).lower() for w in ["look!", "see?", "come on", "here you go"]) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CL - Pragmatyka Hora! i Fuzja ze Słuchem/Prozodią]: "
            "Nie tłumacz bezmyślnie 'Hora' jako 'Spójrz / Patrz'! Zbadaj ton seiyū: "
            "krzyk bojowy / pośpiech -> popędzanie: 'No dalej!' / 'Rusz się!' / 'Śmiało!'; "
            "sarkazm / Hora miro -> 'A nie mówiłem?!' / 'Widzisz?!'; wręczenie -> 'Masz!' / 'Łap!'."
        )

    # 91. Odwrócona Wdzięczność i Formuły Sytuacyjne (Filar CLI - Sumimasen & Aisatsu)
    aisatsu_tokens = ["sumimasen", "ittekimasu", "itterasshai", "tadaima", "okaeri", "ojama", "すみません", "行ってきます", "ただいま", "おかえり", "お邪魔"]
    if any(any(tok in str(item.get("audio_jp", "")).lower() for tok in aisatsu_tokens) for item in batch_items) or any(any(w in str(item.get("en", "")).lower() for w in ["i'm home", "welcome home", "i will intrude", "excuse me"]) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLI - Sumimasen i Formuły Sytuacyjne (Aisatsu)]: "
            "Sumimasen za przysługę to PODZIĘKOWANIE: 'Dziękuję!' / 'Nie trzeba było!' (ZAKAZ 'Przepraszam!'). "
            "Aisatsu dostosuj do realiów sceny (Ittekimasu -> 'Wychodzę!', Tadaima -> 'Wróciłem!', Ojama shimasu -> 'Dzień dobry!' / 'Przepraszam za najście')."
        )

    # 92. Dyscyplina Okrzyków Bojowych i Ostrzeżeń Oddziałowych (Filar CLII - Abunai & Tasukete)
    danger_tokens = ["abunai", "abune", "tasukete", "危ない", "危ねえ", "助けて"]
    if any(any(tok in str(item.get("audio_jp", "")).lower() for tok in danger_tokens) for item in batch_items) or any(any(w in str(item.get("en", "")).lower() for w in ["watch out", "look out", "danger", "save me", "help me"]) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLII - Okrzyki Bojowe i Ostrzeżenia (Abunai & Tasukete)]: "
            "Gdy seiyū krzyczy w zagrożeniu życia: Abunai! -> natychmiastowy rozkaz taktyczny: 'Padnij!' / 'Kryj się!' / 'Uważaj!' / 'Z drogi!' (KATEGORYCZNY ZAKAZ opisu 'Niebezpiecznie!'). "
            "Tasukete! -> 'Ratunku!' / 'Pomocy!' (ZAKAZ 'Ocal mnie!')."
        )

    # 93. Wielka Matryca Afektywna Japońskich Kandōshi (Filar CLIII - Yare yare, Mendokusai, Oi oi, Maa maa, Shouganai, Yokatta)
    kandoushi_tokens = [
        "yare yare", "yareyare", "yare-yare", "mendokusai", "mendou", "shou ga nai", "shouganai", "shikata ga nai", "shikataganai",
        "mattaku", "kore da kara", "iya ni naru", "oi oi", "oioi", "masaka", "uso", "maji", "nante kotta",
        "maa maa", "maamaa", "ii kara", "betsu ni", "ochitsu", "mou ii", "kora", "iikagen", "nani yatten",
        "yokatta", "yatta", "yappari", "yahari", "sasuga ni",
        "やれやれ", "めんどくさい", "しょうがない", "仕方がない", "全く", "これだから", "おいおい", "まさか", "嘘", "マジ", "なんてこった",
        "まあまあ", "いいから", "別に", "落ち着", "もういい", "こら", "いい加減", "よかった", "やった", "やっぱり", "さすがに"
    ]
    en_kandoushi_keys = [
        "good grief", "give me a break", "what a pain", "what a drag", "can't be helped", "honestly", "seriously", "give it a rest",
        "hold on", "whoa whoa", "no way", "you're lying", "for real", "holy cow", "now now", "calm down", "just do it",
        "nothing really", "that's enough", "cut it out", "enough is enough", "what are you doing", "i'm glad", "we did it", "as i thought"
    ]
    if any(any(tok in str(item.get("audio_jp", "")).lower() for tok in kandoushi_tokens) for item in batch_items) or any(any(w in str(item.get("en", "")).lower() for w in en_kandoushi_keys) for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLIII - Wielka Matryca Kandōshi (Westchnienia i Emocje)]: "
            "Kategoryczny zakaz dosłownych kalek! Yare yare -> 'Ja nie mogę...' / 'Litości...' / 'Ręce opadają...' / 'Uff...'; "
            "Mendokusai -> 'Ale mi się nie chce...' / 'Co za męczarnia...'; Shou ga nai -> 'Trudno...' / 'Nic na to nie poradzimy'; "
            "Oi oi -> 'Ej, zaraz, zaraz...' / 'Ej, bez przesady!'; Maa maa -> 'Spokojnie, no już...' / 'Bez nerwów...'; "
            "Iikagen ni shiro -> 'Przestań wreszcie!' / 'Dość tego!'; Yokatta -> 'Całe szczęście...' (ZAKAZ 'To było dobre!'); Yatta -> 'Udało się!' / 'Mamy to!'."
        )

    # 94. Logika Przeczeń, Zaimki Dialektalne i Relacje Trzecioosobowe (Filar CLIV - Hai/Iie, Kansai Jibun, Uchi/Soto)
    has_negative_q = any(
        any(w in str(item.get("en", "")).lower() for w in ["don't you", "aren't you", "didn't you", "can't you", "won't you", "haven't you", "isn't it", "aren't they"]) or
        any(tok in str(item.get("audio_jp", "")).lower() for tok in ["nai no", "nai ka", "shiranai", "ikanai", "chigau", "ないの", "ないか"])
        for item in batch_items
    )
    kansai_markers = ["jibun", " 自分", "やろ", "ねん", "へん", "あかん", "せや", "yaro", "nen", "hen", "akan", "seya", "honma", "onii-chan", "onee-chan", "お兄ちゃん", "お姉ちゃん"]
    has_kansai_or_family = any(any(tok in str(item.get("audio_jp", "")).lower() for tok in kansai_markers) for item in batch_items)

    if has_negative_q or has_kansai_or_family:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLIV - Logika Przeczeń (Hai/Iie) i Kansai Jibun]: "
            "Pytanie z negacją ('Nie idziesz?') + 'Hai' -> 'Nie idę' / 'Zgadza się, nie idę' (KARDYNALNY BŁĄD: 'Tak, idę' - odwrócenie sensu o 180°!). "
            "Kansai 'Jibun' w kontekście rozmówcy -> 'TY' ('Co ty wyprawiasz?!', ZAKAZ: 'Co ja robię?!'). "
            "Rodzina w 3. osobie -> 'Mój brat powiedział' (ZAKAZ: 'Starszy brat powiedział', 'Onii-chan powiedział')."
        )

    # 95. Dyscyplina Repetycji Myśli Wewnętrznych i Ochrona Przed Zlewaniem z Mową (Filar CLV - Overlap vs Italics)
    has_overlap_and_italics = (
        any("overlap" in str(item.get("style", "")).lower() for item in batch_items) and
        any("italic" in str(item.get("style", "")).lower() or item.get("is_thought", False) for item in batch_items)
    )
    has_panic_mantra = any(
        any(w in str(item.get("en", "")).lower() for w in ["can't stop", "cannot stop", "can't hold", "no use", "impossible"]) or
        any(tok in str(item.get("audio_jp", "")).lower() for tok in ["tomerarenai", "muri da", "dame da", "止められない", "無理だ", "駄目だ"])
        for item in batch_items
    )

    if has_overlap_and_italics or has_panic_mantra:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLV - Repetycje Myśli i Separacja Mowy]: "
            "Kategoryczny zakaz halucynacyjnego zlewania myśli z dialogiem na głos! "
            "Repetycje paniki/stresu w myślach (np. 'I can't stop it' powtórzone 3 razy -> 'Nie powstrzymam tego...') zachowaj wiernie jako mantrę. "
            "ZAKAZ samowolnego wygładzania i wklejania do myśli słów z sąsiedniej linijki mówionej na głos!"
        )

    # 96. Rozszczepienie Dwuznaczności Angielskiego Pivotu (Filar CLVI - Hitori vs Hottoite, Betsuni, Mou ii)
    has_pivot_ambiguity = any(
        any(w in str(item.get("en", "")).lower() for w in ["leave me alone", "alone", "it's nothing", "not really", "that's enough", "i'm fine"]) or
        any(tok in str(item.get("audio_jp", "")).lower() for tok in ["hitori", "一人", "独り", "betsuni", "別に", "mou ii", "もういい", "hottoite", "放っておいて"])
        for item in batch_items
    )
    if has_pivot_ambiguity:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLVI - Rozszczepienie Angielskiego Pivotu i Kotwice Audio]: "
            "Nie ulegaj fałszywym synonimom angielskim! 'Hitori ni shite' (一人にして) w łzach/smutku to 'Zostaw mnie samą/samego' (ZAKAZ opryskliwego 'Daj mi spokój'!). "
            "'Betsuni' to chłodne 'Wcale nie' / 'Mniejsza z tym' (ZAKAZ 'To nic takiego'). 'Mou ii' to rezygnacja 'Wystarczy / Daj spokój'."
        )

    # 97. Nienaruszalność Formy Adresatywnej i Zakaz Schizofrenii Pan/Ty (Filar CLVII)
    has_address_drift_risk = any(
        any(w in str(item.get("en", "")).lower() for w in ["you won", "did you", "you did", "have you", "you're", "you are", "why?!", "why?", "look,", "what? but you", "you've", "you didn't", "you know"]) or
        bool(re.search(r"\b(pan|pani|pana|panu|panie)\b", str(item.get("pl", "")).lower()))
        for item in batch_items
    )
    if has_address_drift_risk:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLVII - Nienaruszalność Formy Adresatywnej, Zakaz Hybryd Wołacza i -Sama Drop]: "
            "Jeśli postać zwraca się do rozmówcy po imieniu (np. 'Shizuku, dlaczego?!') lub na 'ty' ('Przecież wiesz...'), w całej scenie KONSEKWENTNIE stosuj formę na 'ty'! "
            "KATEGORYCZNY ZAKAZ wtrącania formy 'pan/pani' ('wygrał pan' -> BŁĄD KARDYNALNY! Należy: 'wygrałeś' / 'wygrałaś' zależnie od płci adresata). "
            "ZAKAZ WEWNĄTRZZDANIOWYCH HYBRYD WOŁACZA: Niedopuszczalne jest łączenie poufałego wołacza imienia z honoryfikatywnym 'pan/pani' ('Poza tym, Eftalu... ma pan' -> BŁĄD KARDYNALNY! Wymagane: 'Poza tym, panie Eftalu... ma pan'). "
            "ODPORNOŚĆ NA ANGIELSKIE OPUSZCZANIE -SAMA: W okrzykach i zawołaniach podwładnych/uczniów nie kopiuj angielskiego ucinania tytułów ('Co za kunszt, panie Eftalu!', ZAKAZ: 'Co za kunszt, Eftalu!')."
        )

    # 98. Zgodność Foniczno-Semantyczna Seiyū i Test Ucha Widza (Filar CLVIII)
    has_auditory_anchor_trigger = any(
        any(tok in str(item.get("audio_jp", "")).lower() for tok in [
            "hitori", "一人", "独り", "betsuni", "別に", "yokatta", "よかった", "yatta", "やった",
            "uso", "嘘", "maji", "マジ", "mendokusai", "面倒くさい", "mou ii", "もういい",
            "gaman", "我慢", "tasukete", "助けて", "yamero", "yamete", "やめろ", "やめて",
            "shikata ga nai", "shou ga nai", "しょうがない", "naruhodo", "なるほど", "wakatta", "分かった",
            "waka", "若", "若様", "wakagimi", "若君"
        ]) or
        any(tok in str(item.get("en", "")).lower() for tok in ["my lord", "milord", "young master", "young lord"])
        for item in batch_items
    )
    if has_auditory_anchor_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLVIII - Zgodność Foniczno-Semantyczna Seiyū (Harmonia Ucha)]: "
            "Polski widz słyszy głos seiyū! Bezwzględnie zestroić napisy ze słyszanym japońskim słowem kluczowym: "
            "Waka / Waka-sama / Wakagimi (若 / 若様 / 'My Lord') -> 'Młody panie / Panie / Paniczu' (KATEGORYCZNY ZAKAZ: 'bracie', 'brachu'!). Jeśli postać mówi Waka w tłumie, to odruchowa wpadka, której NIE WOLNO cenzurować ani podmieniać na fałszywy kamuflaż; "
            "Hitori -> 'sam/sama' (ZAKAZ 'Daj mi spokój'); Betsuni -> 'Wcale nie / Mniejsza z tym' (ZAKAZ 'To nic takiego'); "
            "Yokatta -> 'Całe szczęście' (ZAKAZ 'To było dobre'); Yatta -> 'Udało się!' (ZAKAZ 'Zrobiłem to'); "
            "Uso/Maji -> 'Nie wierzę! / Żartujesz?!' (ZAKAZ 'Kłamstwo'); Mendokusai -> 'Ale mi się nie chce...' (ZAKAZ 'Co za ból'); "
            "Mou ii -> 'Wystarczy / Daj spokój'; Yamero -> 'Przestań! / Zostaw!'; Tasukete -> 'Ratunku! / Pomóż mi!'."
        )

    # 99. Kognitywny Model Sceny i Metoda Aktorska (Filar CLIX)
    if any(item.get("prosody") or item.get("audio_alert") for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLIX - Kognitywny Model Sceny i Metoda Aktorska Stanisławskiego]: "
            "Przetestuj każde zdanie na głos! Czy polski aktor dubbingowy wypowie je gładko na jednym wydechu? "
            "Dopasuj ładunek psychologiczny do relacji władzy (kto dominuje, kto blefuje) – eliminuj papierowe brzmienie i sztywne kalki."
        )

    # 100. Dekompozycja Semiotyczna i Warstwy Ontologiczne (Filar CLX)
    has_semiotic_mix = any(
        item.get("is_sign") or
        item.get("is_thought") or
        any(w in str(item.get("en", "")).lower() for w in ["balloon", "congratulations", "sign", "title", "caption"])
        for item in batch_items
    )
    if has_semiotic_mix:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLX - Dekompozycja Semiotyczna i Nienaruszalność Warstw]: "
            "Oddzielaj żywą mowę od dymków mangowych i plansz! Kategoryczny zakaz sklejania dymka halucynacji z dialogiem mówionym w jedno zdanie."
        )

    # 101. Nienaruszalność Perspektywy Narracyjnej i Zakaz Zdrady Tożsamości Incognito (Filar CLXI)
    has_focalization_trigger = any(
        any(tok in str(item.get("en", "")).lower() for tok in [
            "by the", "written by", "essay by", "paper by", "report by", "work by"
        ]) or
        any(tok in str(item.get("audio_jp", "")).lower() for tok in [
            "no ronbun", "論文", "no sakuhin", "作品"
        ]) or
        any("filar clxi" in str(item.get("notes", "")).lower() for item in [item])
        for item in batch_items
    )
    if has_focalization_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXI - Nienaruszalność Perspektywy Narracyjnej i Zakaz Zdrady Tożsamości Incognito]: "
            "Gdy postać mówi na głos w 3. osobie (np. powołując się na autora lub artykuł), "
            "KATEGORYCZNIE ZABRANIA SIĘ zamiany wypowiedzi na 1. osobę ze względu na ukrytą tożsamość rozmówcy! "
            "Zakaz samowolnego dodawania kursywy {\\i1} do dialogów mówionych na głos – tłumacz świat przedstawiony z perspektywy mówcy!"
        )

    # 102. Nienaruszalność Płci Imion Orientalnych na '-a' i Scen Jednopłciowych (Filar CLXII)
    has_name_on_a_trigger = any(
        re.search(r"\b(shira|akira|gaara|ashitaka|kiba|soma|kenta|ryoma|hanza|koba|soya|toma|genga|sinbad|judar|alibaba)\b", str(item.get("en", "")), re.IGNORECASE) or
        any("filar clxii" in str(item.get("notes", "")).lower() for item in [item]) or
        any(w in str(item.get("notes", "")).lower() for w in ["scena wyłącznie kobieca", "mówczyni", "boraqchin", "fatima"]) or
        any(re.search(r"\b(i intended|i wanted|i did|i got|what i did|you look agitated|wyglądasz na wzburzon)\b", str(item.get("en", "")), re.IGNORECASE) for item in [item])
        for item in batch_items
    )
    if has_name_on_a_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXII - Nienaruszalność Płci Imion Orientalnych na '-a' i Scen Jednopłciowych]: "
            "1) Imiona męskie na '-a' (Shira, Akira) wymagają męskich orzeczeń ('Shira ostrzegał', ZAKAZ: 'ostrzegała'). "
            "2) W dialogach postaci żeńskich (lub w scenach kobiecych) BEZWZGLĘDNIE stosuj formy żeńskie w 1. os. (-łam/-łabym: 'zamierzałam', 'chciałam', 'dopięłam', 'zrobiłam', 'miałabym'; KATEGORYCZNY ZAKAZ: 'zamierzałem', 'dopiąłem') oraz w 2. os. ('wyglądasz na wzburzoną', ZAKAZ: 'wzburzonego')!"
        )

    # 103. Morfologia Adresatywna 2. Osoby: Pojedyncza Kobieta/Mężczyzna oraz Grupy (Filar CLXIII)
    has_addressee_trigger = any(
        any(w in str(item.get("audio_jp", "")).lower() for w in ["tachi", "omae-ra", "kisama-ra", "minna", "shokun", "zen'in", "mina-sama", "anata", "omae", "temee", "anta"]) or
        any(w in str(item.get("en", "")).lower() for w in ["you all", "you guys", "all of you", "girls", "everyone", "ladies", "you are", "are you", "were you", "did you"]) or
        any(w in str(item.get("addressee", "")).lower() for w in ["grupa", "group", "kobieta", "mężczyzna", "female", "male"]) or
        any("filar clxiii" in str(item.get("notes", "")).lower() for item in [item])
        for item in batch_items
    )
    if has_addressee_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXIII - Morfologia Adresatywna 2. Osoby ('ty' kobieta/mężczyzna oraz 'wy' grupy)]: "
            "Dla pojedynczej kobiety ('kobieta') w 2. os. lp. 'ty' BEZWZGLĘDNIE stosuj formy żeńskie ('byłaś', 'zrobiłaś', 'poszłaś', 'jesteś pewna', 'gotowa'). "
            "Dla pojedynczego mężczyzny ('mężczyzna') stosuj formy męskie ('byłeś', 'zrobiłeś', 'poszedłeś', 'jesteś pewien', 'gotowy'). "
            "Dla grupy samych kobiet ('grupa_kobiet') stosuj formy niemęskoosobowe ('zrobiłyście', 'byłyście gotowe'). "
            "Dla grupy mężczyzn/mieszanej stosuj męskoosobowe ('zrobiliście', 'byliście gotowi')."
        )

    # 104. Bezwzględna Kontrola Ortografii, Literówek i Niezmienników Leksykalnych (Filar CLXIV)
    has_typo_or_inquiry_trigger = any(
        any(w in str(item.get("en", "")).lower() for w in ["ask", "inquire", "question", "personally", "servant", "discovered", "find out", "anyways", "least resistance", "good night", "do your best"]) or
        any(w in str(item.get("audio_jp", "")).lower() for w in ["kiku", "kikou", "tazuneru", "tou", "ganbatte", "oyasumi"]) or
        any("filar clxiv" in str(item.get("notes", "")).lower() for item in [item])
        for item in batch_items
    )
    if has_typo_or_inquiry_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXIV - Bezwzględna Kontrola Ortografii i Niezmienników Leksykalnych]: "
            "Zachowaj najwyższą staranność fleksyjną i ortograficzną polszczyzny kinowej. "
            "Stosuj wyłącznie poprawne formy literackie ('spytam/zapytam', 'w każdym razie', 'w cudzysłowie', 'po linii najmniejszego oporu', 'z rzędu', 'z powrotem', 'Dobranoc')."
        )

    # 105. Kanon Czystości Wizualnej AVT, Elipsa Szumu Kinezjatycznego i Zakaz Kalki 'Here' -> 'Tutaj' (Filar XVIII & IV)
    has_kakegoe_or_here_trigger = any(
        any(w in str(item.get("en", "")).lower() for w in ["here", "there you go", "up we go", "hup", "whoa", "easy"]) or
        any(w in str(item.get("audio_jp", "")).lower() for w in ["yoisho", "dokkoisho", "yotto", "hai", "hora", "douzo", "dōzo"]) or
        any("filar xviii" in str(item.get("notes", "")).lower() for item in [item])
        for item in batch_items
    )
    if has_kakegoe_or_here_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XVIII & IV - Czystość Wizualna AVT, Elipsa Kakegoe i Zakaz Kalki 'Tutaj']: "
            "Odgłosy wysiłku fizycznego seiyū (yoisho, dokkoisho, yotto przy wstawaniu z krzesła, siadaniu, podnoszeniu ciężaru) "
            "BEZWZGLĘDNIE ELIDUJ (pusty napis \"\"). Zakaz infantylnych podpisów 'Hop...', 'I siup...' i pomyłek 'Proszę...'. "
            "Przy geście podawania przedmiotu KATEGORYCZNY ZAKAZ kalki z angielskiego 'Here' jako 'Tutaj!' / 'Tu!'. "
            "W polszczyźnie stosuj wyłącznie naturalne 'Proszę' / 'Trzymaj' / 'Masz' (lub elipsę \"\")."
        )

    # 106. Dyskontinuitet Czasowy, Przeskoki Scen i Odczarowanie Fałszywego Przylegania (Filar CLXV)
    has_temporal_discontinuity = any(
        any(w in str(item.get("en", "")).lower() for w in [
            "in private", "on our own", "talk alone", "what is it", "what's up", "what is wrong", "what's wrong",
            "sure, what", "all right, what", "yeah, what", "somewhere else", "quiet place"
        ]) or
        any(w in str(item.get("audio_jp", "")).lower() for w in [
            "futari", "hanashi", "doko ka", "nan da", "dou shita", "nani"
        ]) or
        any("filar clxv" in str(item.get("notes", "")).lower() for item in [item]) or
        (float(item.get("duration_s", 0.0)) >= 5.0 and any(w in str(item.get("en", "")).lower() for w in ["sure", "all right", "yeah"]))
        for item in batch_items
    )
    if has_temporal_discontinuity:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXV - Dyskontinuitet Czasowy i Przeskoki Scen]: "
            "Gdy po prośbie o rozmowę na osobności następuje przerwa czasowa lub zmiana lokacji, "
            "angielskie 'Sure, what is it?' w nowej scenie to otwarcie rozmowy: 'Więc o co chodzi?' / 'No to o co chodzi?' / 'Słucham cię'. "
            "KATEGORYCZNY ZAKAZ opóźnionego potaknięcia: 'Jasne / Pewnie / W porządku, o co chodzi?'. "
            "Zakaz wycieku spójników ('I...', 'A...') i fałszywych par przylegania po cięciu montażowym."
        )

    # 107. Eliminacja Grawitacji Języka Angielskiego i Klisz Fansuberskich (Filar CLXVI)
    has_fansub_cliche_trigger = any(
        any(w in str(item.get("en", "")).lower() for w in [
            "welcome back", "i hope so", "i hope not", "there's no way", "there is no way",
            "i'm fine", "i am fine", "sure, what", "all right, what"
        ]) or
        any("filar clxvi" in str(item.get("notes", "")).lower() for item in [item])
        for item in batch_items
    )
    if has_fansub_cliche_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXVI - Eliminacja Grawitacji Języka Angielskiego i Klisz Fansuberskich]: "
            "Prowadź dialog z pozycji polszczyzny teatralnej i kinowej, odrzucając dosłowne kalki fansubów. "
            "Reaguj na sens sceny i afekt seiyū, przekładając sytuację na naturalne polskie repliki."
        )

    # 108. Puryzm Rejestru Historycznego i Podwójny Rząd Przyimków (Filar CLXVII)
    has_historical_or_prep_trigger = any(
        any(w in str(item.get("en", "")).lower() for w in [
            "good question", "after all", "in fact", "marry", "married to", "take for", "pay for", "mistake for"
        ]) or
        any(w in str(item.get("pl", "")).lower() for w in ["dobre pytanie", "w sumie", "oj tam", "wyjść za", "oddać za", "uznać za", "uchodzić za"]) or
        any("filar clxvii" in str(item.get("notes", "")).lower() for item in [item])
        for item in batch_items
    )
    if has_historical_or_prep_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXVII - Puryzm Rejestru Dramatu Historycznego i Podwójny Rząd Przyimków]: "
            "W realiach historycznych/fantasy kategorycznie eliminuj współczesne kalki: "
            "'Good question' -> 'Trudno powiedzieć / Ciekawe zagadnienie' (ZAKAZ 'Dobre pytanie!'); "
            "'W sumie to nam na rękę' -> 'W istocie / W gruncie rzeczy to nam na rękę'; 'Oj tam!' -> 'Daj spokój!'. "
            "Żelazna kontrola rządu przyimka 'za': w małżeństwie i wymianie 'za' rządzi BIERNIKIEM: "
            "'wyjść za Gujuka' (Biernik męski od Gujuk), KATEGORYCZNY ZAKAZ: 'wyjść za Gujukę / za Gujukiem'!"
        )

    # 109. Śledzenie Rozmówcy, Hipokorystyki i Tytulatura (Filar XXVII)
    has_honorific_or_interlocutor_trigger = any(
        any(w in str(item.get("en", "")).lower() for w in [
            "senpai", "sensei", "-tan", "-taso"
        ]) or
        any(w in str(item.get("pl", "")).lower() for w in ["senpai", "sensei", "książę"]) or
        any("filar xxvii" in str(item.get("notes", "")).lower() for item in [item])
        for item in batch_items
    )
    if has_honorific_or_interlocutor_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXVII - Śledzenie Rozmówcy, Hipokorystyki i Tytulatura]: "
            "Kategoryczny zakaz auto-adresacji (mówca pod żadnym pozorem nie zwraca się do siebie własnym imieniem przy adaptacji 'Senpai'!). "
            "Hipokorystyki z afektywnymi sufiksami seiyū ('-tan', '-taso') bezwzględnie rozwijaj do pełnego kanonicznego imienia według bazy serii. "
            "Wycofanie się ze spoufalenia do formy formalnej ('[Nazwisko]-senpai') tłumacz grzecznościowo per 'panno / panie [Nazwisko]' (ZAKAZ obcesowego samego nazwiska)."
        )

    # 110. Naturalna Składnia Deiktyczno-Temporalna (Filar CLXVIII)
    has_temporal_syntax_trigger = any(
        any(w in str(item.get("en", "")).lower() for w in [
            "day after tomorrow", "day before yesterday", "tomorrow morning", "this evening", "yesterday evening", "next week", "asatte"
        ]) or
        any(w in str(item.get("pl", "")).lower() for w in [
            "pojutrze", "pojutrzejsz", "przedwczoraj", "przedwczorajsz", "dzisiejszy wieczór", "jutrzejszy poranek", "wczorajszy wieczór", "przyszłotygodniow"
        ]) or
        any("filar clxviii" in str(item.get("notes", "")).lower() for item in [item])
        for item in batch_items
    )
    if has_temporal_syntax_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXVIII - Naturalna Składnia Deiktyczno-Temporalna]: "
            "Kategoryczny zakaz sztucznych odprzysłówkowych przymiotników temporalnych w dialogach: "
            "'pojutrzejszy/a/e/ą' -> 'pojutrze / za dwa dni' (KARDYNALNY BŁĄD: 'Chodzi o pojutrzejszą ucztę' -> 'Chodzi o ucztę pojutrze'); "
            "'przedwczorajszy' -> 'sprzed dwóch dni'; 'w dzisiejszy wieczór' -> 'dziś wieczorem'; 'w jutrzejszy poranek' -> 'jutro rano'; "
            "'przyszłotygodniowy' -> 'w przyszłym tygodniu'. Japońskie 'X no Y' dla czasu dekomponuj na okoliczniki!"
        )

    # 111. Dyscyplina Socjolektu, Zakaz Wycieku Ksywek i Żeńska Fleksja 1. Osoby (Filar CLXIX)
    has_hypocorism_or_inherent_gender_trigger = any(
        any(w in (str(item.get("speaker", "")) + " " + str(item.get("speaker_name", "")) + " " + str(item.get("notes", ""))).lower() for w in [
            "girl", "woman", "female", "dziewczyn", "kobieta", "matk", "mama", "córk", "siostr", "hebichika", "filar clxix", "alarm korekty fleksyjnej", "mówczyni"
        ]) or
        any(w in str(item.get("en", "")).lower() for w in [
            "hikarun", "tessie", "hurt her", "hurt him", "i hurt"
        ]) or
        any(w in str(item.get("pl", "")).lower() for w in [
            "hikarun", "tessie", "zraniłem", "skrzywdziłem", "zrobiłem", "byłem"
        ])
        for item in batch_items
    )
    if has_hypocorism_or_inherent_gender_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXIX - Dyscyplina Socjolektu, Zakaz Wycieku Ksywek i Żeńska Fleksja 1. Osoby]: "
            "1. Ksywki rówieśnicze/gyaru ('Hikarun', 'Tessie') należą WYŁĄCZNIE do postaci je nadających (Sachi Akafuku). "
            "KATEGORYCZNY ZAKAZ przypisywania ksywek szkolnych rodzicom (matce 'Hebichika' mówiącej w audio 'Hikaru-chan'), "
            "nauczycielom czy w retrospekcjach ('Flashback')! Matka do córki mówi 'Hikaru', 'Córeczko' lub 'Hikaruś' (ZAKAZ: 'Hikarun'). "
            "2. Nazwy mówców typu 'Girl\\Italic', 'Woman' to potwierdzone postacie żeńskie! W 1. osobie czasu przeszłego "
            "mówczyni żeńska BEZWZGLĘDNIE wymaga form żeńskich ('tak ją zraniłam', 'zrobiłam', 'byłam', 'powiedziałam'; KATEGORYCZNY ZAKAZ: 'tak ją zraniłem')."
        )

    # 112. Prymat Głosu Seiyū, Akty Mowy, Echa Powitań i Apozycja Tytulatury (Filar CLXX)
    has_seiyu_primacy_or_title_or_aisatsu_trigger = any(
        any(w in str(item.get("jp", "")).lower() for w in [
            "urusai", "urusee", "ussee", "damare", "mendoku", "tadaima", "okaeri", "itterasshai", "ittekimasu"
        ]) or
        any(w in str(item.get("en", "")).lower() for w in [
            "shut up", "noisy", "annoying", "awkward", "cringe", "i'm home", "welcome home", "master"
        ]) or
        any(w in str(item.get("pl", "")).lower() for w in [
            "żenada", "wróciłam", "wróciłeś", "wróciłaś"
        ]) or
        any("filar clxx" in str(item.get("notes", "")).lower() for item in [item])
        for item in batch_items
    )
    if has_seiyu_primacy_or_title_or_aisatsu_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXX - Prymat Głosu Seiyū, Akty Mowy, Echa Powitań i Apozycja Tytulatury]: "
            "1. Oryginał japoński seiyū jest pierwotnym źródłem intencji i emocji! Przy 'urusai' / 'urusai na' "
            "KATEGORYCZNY ZAKAZ dryfu ku slangowemu zażenowaniu ('Ale żenada...', 'przypał'). Zastosuj polskie wykładniki uciszania/zniecierpliwienia: 'Ale marudzisz...', 'Daj mi spokój...', 'Nie truj...'. "
            "2. Zakaz twierdzącego echa czasownikowego po powitaniu domowym: po 'Wróciłam.' / 'Wróciłem.' ZAKAZ echa 'Wróciłaś.' / 'Wróciłeś.' -> zastosuj 'Witaj w domu!', 'O, już jesteś?' lub 'Dobrze, że jesteś!'. "
            "3. Nienaruszalność mianownika nazwiska przy tytulaturze podmiotu w relacji tytuł + nazwisko (np. 'Mistrz Kowalski' a nie 'Mistrz Kowalskiego')."
        )

    # 113. Wierność Faktograficzna, Integralność Liczebników i Prymat Zaimków Męskich nad F0 (Filar CLXXI)
    has_numerical_or_cross_gender_trigger = any(
        bool(re.search(r"\b\d+\b", str(item.get("en", "")))) or
        any(w in str(item.get("audio_jp", "")).lower() for w in ["boku", "僕", "ore", "俺", "bocchan", "坊ちゃん"]) or
        any(w in str(item.get("en", "")).lower() for w in ["hundred", "thousand", "years", "days"]) or
        any(w in str(item.get("speaker_voice", "")).lower() for w in ["alt starszej", "alt dojrzały", "ochrypł"])
        for item in batch_items
    )
    if has_numerical_or_cross_gender_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXI - Wierność Faktograficzna, Liczebniki i Zaimki Męskie nad F0]: "
            "1. Kategoryczny zakaz mutowania liczb, lat i kwot: '300 years' -> '300 lat' (ZAKAZ: '30 lat', 'kilkaset'). "
            "2. W japońskim anime chłopcy dubbingowani przez kobiety używający 'boku/ore' wymagają BEZWZGLĘDNIE form męskich ('zrobiłem', 'byłem gotowy', a NIE: 'zrobiłam', 'gotowa')! "
            "3. Nienaruszalność majuskuły encji i nazw własnych (Töregene, Ilüge, Fatima, Chulan). "
            "4. Ochrona starszych kobiet i matron: niski tembr F0 seiyū (<=160 Hz) u postaci żeńskich (np. Boraqchin) NIE MOŻE naruszać form żeńskich – nakaz form żeńskich: 'miałam', 'miałabym', 'wiedziałam'."
        )

    # 114. Dynamiczny Prymat Afektu, Kontrakt Polszczyzny Bezterminowej i Pozytywne Wektory Rzemiosła (Filar CLXXII)
    has_affective_primacy_trigger = any(
        any(w in str(item.get("audio_jp", "")).lower() for w in ["sonna", "tasukete", "iya", "h-", "kowai", "nande"]) or
        "płacz" in str(item.get("prosody", "")).lower() or
        "drżenie" in str(item.get("prosody", "")).lower() or
        "szept" in str(item.get("prosody", "")).lower() or
        float(item.get("calque_score", 0.0) or 0.0) >= 0.65 or
        item.get("is_blind_draft", False)
        for item in batch_items
    )
    if has_affective_primacy_trigger:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXII - Dynamiczny Prymat Afektu, Polszczyzna Bezterminowa i Pozytywne Rzemiosło]: "
            "1. Aktorstwo i fizjologia emocji seiyū (płacz, panika, drżenie) ZAWSZE biją statyczny portret z Series Bible! Przy załamaniu emocjonalnym odrzuć chłód i oddaj histeryczną fizjologię rozpaczy. "
            "2. Twórz w estetyce polszczyzny bezterminowej: dialog świeży, organiczny, wolny od mód internetowych, naturalny 30 lat temu i za 30 lat. "
            "3. Zastosuj zasadę remy (akcent logiczny na końcu zdania) oraz reakcję na intencję zamiast dosłowności słów."
        )

    if not focused_pillars:
        return ""

    # Sort descending by attention priority score; Python sort is stable (preserves order within the same tier)
    sorted_scored = sorted(focused_pillars.items, key=lambda x: x[0], reverse=True)

    # Deduplicate while preserving priority order
    seen = set()
    unique_rules = []
    for score, rule in sorted_scored:
        if rule not in seen:
            seen.add(rule)
            unique_rules.append(rule)

    # Anti-Attention Dilution: cap at max_rules if specified to prevent LLM cognitive overload ('Lost in the Middle')
    if max_rules is not None and max_rules > 0:
        effective_max = min(max_rules, 2) if len(batch_items) <= 4 and max_rules > 2 else max_rules
        unique_rules = unique_rules[:effective_max]

    lines = [
        "--- [!] SKONCENTROWANA UWAGA DLA TEJ SCENY (PRIORYTETOWE FILARY AVT) ---",
        "W bieżącej paczce kwestii zwróć szczególną uwagę na następujące kluczowe reguły:"
    ]
    lines.extend(unique_rules)
    lines.append("------------------------------------------------------------------------\n")
    return "\n".join(lines)


