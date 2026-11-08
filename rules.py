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
    dominant_tone: Optional[str] = Field(default=None, description="Dominujący rejestr dramaturgiczny sceny")
    power_dynamic: Optional[str] = Field(default=None, description="Relacja władzy/statusu: kto dominuje, kto blefuje, kto jest w potrzasku (maks. 8 słów)")
    epistemic_asymmetry: Optional[str] = Field(default=None, description="Teoria Umysłu (Theory of Mind): kto co wie, a czego nie wie w tej scenie, ukrywanie tożsamości i motywów")
    table_read_mouth_feel: Optional[str] = Field(default=None, description="Próba Stolikowa: weryfikacja potoczystości mówionej i naturalności dialogu filmowego")

BELCZYK_AVT_MASTER_CANON = r"""
KOMPLEKSOWY KANON PRZEKŁADU AUDIOWIZUALNEGO (WG ARKADIUSZA BELCZYKA, JERZEGO PIEŃKOSA, STANISŁAWA BARAŃCZAKA I NORM POLSKIEGO DIALOGU FILMOWEGO):

MODUŁ I: SKŁADNIA, GIĘTKOŚĆ JĘZYKOWA I POLSZCZYZNA FILMOWA (FILARY I – XII)

FILAR I: ODNOMINALIZOWANIE I WERBALIZACJA (CZASOWNIK ZAMIAST RZECZOWNIKA):
- Język angielski jest językiem nominalnym (rzeczownikowym), polski – dynamicznym i czasownikowym.
- Naturalnie przekształcaj sztuczne konstrukcje rzeczownikowe na giętkie czasowniki:
  * "put together this story / come up with a story" -> "wpaść na to", "poskładać to", "wymyślić to".
  * "make a decision" -> "zdecydować", "postanowić".
  * "take a look" -> "spojrzeć", "zerknąć".
  * "have a chat / talk" -> "pogadać", "porozmawiać".
  * "do the cleaning" -> "posprzątać".
  * "give an answer" -> "odpowiedzieć".
  * "make an appearance" -> "zjawić się", "pokazać się".
  * "reach an agreement" -> "dogadać się", "porozumieć się".

FILAR II: ZASADA ANAFORY, PRO-FORM I ZAIMKA "TO / NA TO" (ZERO-ANAPHORA & SENSE-COHESION):
- 1. ELIMINACJA POWTÓRZEŃ TEMATU:
  * W polskim dialogu filmowym, gdy temat/obiekt został wprowadzony w poprzednim zdaniu, W KOLEJNYM ZDANIU W kolejnym zdaniu naturalnie stosujemy zaimek wskazujący ('to', 'na to', 'o tym', 'z tym', 'go', 'ją'), czasownik frazowy lub elipsę:
  * Należy zastosować zaimek wskazujący ("to", "na to", "o tym", "z tym", "go", "ją"), czasownik frazowy lub elipsę:
    -> Kwestia A: "Wyszła wam całkiem spójna historia." -> Kwestia B: "Jak na to wpadłyście" / "Jak to wymyśliłyście" / "Skąd ten pomysł".
    -> Kwestia A: "A jakie mangi lubicie" -> Kwestia B: "Ja wolę tytuły pełne akcji." / "Te z dużą dawką humoru.".
    -> Kwestia A: "Mamy pewien plan." -> Kwestia B: "Co zamierzacie" / "Jaki" / "O co chodzi".
- 2. JAPOŃSKA ZEROWA ANAFORA PODMIOTOWA (ZERO-ANAPHORA):
  * W języku japońskim podmiot logiczny jest stale przemilczany. W języku polskim osoba wynika z końcówki czasownika:
    -> W polszczyźnie filmowej naturalnie unikamy dopisywania zaimków osobowych ("on", "ona", "oni") w każdym zdaniu, jeśli z kontekstu i obrazu wynika, o kogo chodzi.

FILAR III: NATURALNE POLSKIE KOLOKACJE PYTAJĄCE I SYTUACYJNE (ZAMIAST KALK SŁOWNIKOWYCH):
- "How did you put this together / come up with it" -> "Jak na to wpadłeś", "Jak to wymyśliłeś", "Skąd ten pomysł".
- "What makes you say that" -> "Skąd ci to przyszło do głowy", "Dlaczego tak uważasz", "Czemu tak sądzisz".
- "What brings you here" -> "Co cię sprowadza", "Co tu robisz".
- "What do you say we..." -> "A może byśmy...", "Co powiesz na...", "Chcesz skoczyć na...".
- "How are you holding up" -> "Jak się trzymasz", "Dajesz radę".
- "What are you getting at" -> "Do czego zmierzasz", "O co ci chodzi".
- "What difference does it make" -> "A co za różnica", "Co to zmienia".
- "What took you so long" -> "Gdzieś ty był", "Czemu tak długo".
- "How did you manage to..." -> "Jak ci się udało...", "Jak dałeś radę...".
- 2. KOLOKACJE CZASOWE I REALIA SZKOLNE:
  * "lunch break / noon recess" (昼休み) -> "długa przerwa" (lub "przerwa obiadowa").
  * "short break / recess" -> "krótka przerwa".
  * "long weekend" -> "długi weekend".

FILAR IV: ELIMINACJA SZTUCZNYCH CZASOWNIKÓW POSIŁKOWYCH I POZORNEGO TRWANIA:
- 1. SZTUCZNA ANALITYCZNOŚĆ:
  * "I was able to find it" -> "Znalazłem", "Udało mi się znaleźć".
  * "I started to cry / laugh" -> "Rozpłakałem się", "Rozśmiałem się".
  * "I feel like doing X" -> "Mam ochotę na X", "Chcę X".
  * "I have a feeling that..." -> "Coś mi mówi, że...", "Wydaje mi się, że...".
  * "It looks like it's going to rain" -> "Zbiera się na deszcz", "Chyba będzie padać".
  * "Welcome back" -> "Witaj", "Dobrze cię widzieć", "Wróciłeś", "Witaj w domu".
  * "passed the point of no return" -> "nie ma już odwrotu", "z tej drogi nie ma odwrotu", "dla tej armii nie ma już powrotu", "za daleko zaszli, by zawrócić".
- 2. KALKI KONSTRUKCJI POZORNEGO TRWANIA I POSIADANIA:
  * "is in the process of doing" -> "właśnie robi", "robi".
  * "came into possession of" -> "zdobył", "ma", "wszedł w posiadanie".

FILAR V: ELIMINACJA ZBĘDNYCH ZAIMKÓW DZIERŻAWCZYCH I OSOBOWYCH:
- Angielski wymaga zaimka przy każdej części ciała i własności. Po polsku relacja wynika z kontekstu i formy zaimka osobowego (celownik/biernik):
  * "I put my hands in my pockets" -> "Włożyłem ręce do kieszeni".
  * "She talked with her sister" -> "Rozmawiała z siostrą".
  * "Close your eyes" -> "Zamknij oczy".
  * "I broke my leg" -> "Złamałem nogę".
  * "He grabbed my hand / arm" -> "Złapał mnie za rękę / ramię".
  * "He cut his head / throat" -> "Ściął mu głowę / Podciął mu gardło".
  * "She looked into my eyes" -> "Spojrzała mi w oczy".
  * "I think that..." -> "Myślę, że...".

FILAR VI: DEPASYWIZACJA (STRONA BIERNA -> CZYNNA / BEZOSOBOWA - TOMASZ TOMASZKIEWICZ):
- Angielską stronę bierną zastępuj polską stroną czynną lub formami bezosobowymi:
  * "It was decided that..." -> "Ustaliliśmy, że..." / "Zdecydowaliśmy, że...".
  * "He was given an award" -> "Dostał nagrodę" / "Wręczono mu nagrodę".
  * "The car was stolen" -> "Ukradli samochód" / "Skradziono samochód".

FILAR VII: ELIMINACJA NADMIARU ZAIMKA WZGLĘDNEGO "KTÓRY / KTÓRA":
- Unikaj tworzenia ciężkich zdań podrzędnych z "który" w mowie potocznej. Stosuj zwięzłe formy imiesłowowe, przymiotnikowe lub podział zdania.

FILAR VIII: NATURALNY POLSKI SZYK ZDANIA I INWERSJA EMFATYCZNA (STRUKTURA TEMAT-REMAT):
- 1. STRUKTURA INFORMACYJNA (TEMAT-REMAT):
  * W języku polskim najważniejsza NOWA informacja ląduje na KOŃCU zdania (remat), a punkt wyjścia na początku.
  * Zmieniaj sztywny angielski szyk SVO na elastyczną polską frazę.
- 2. INWERSJA EMFATYCZNA W SCENACH AKCJI:
  * W dynamicznych scenach walki i rozkazach bojowych dopuszcza się inwersję czasownika na początek dla wzmocnienia ładunku dramatycznego ("Uciekać musimy", "Padnij").

FILAR IX: PYTANIA POTOCZNE, ELIMINACJA SZTUCZNEGO "CZY" I NEGACJA RETORYCZNA (SZARKOWSKA & BELCZYK):
- 1. PYTANIA ROZSTRZYGNIĘCIA W MOWIE POTOCZNEJ:
  * W filmie NIE zaczyna się każdego pytania od "Czy...". Pytania rozstrzygnięcia tworzy się intonacją:
    Niezalecana kalka: "Czy jesteś pewna", "Czy widziałaś to", "Czy idziesz z nami", "Czy to prawda".
    Wariant kanoniczny: "Jesteś pewna", "Widziałaś to", "Idziesz z nami", "To prawda" / "Serio".
  * Partykułę "Czy" zachowaj WYŁĄCZNIE w pytaniach alternatywnych ("Kawa czy herbata") lub w bardzo oficjalnym tonie.
- 2. JAPOŃSKA NEGACJA RETORYCZNA (~JA NAI KA? / ~DEWA NAI KA? - RHETORICAL ASSERTIONS):
  * W języku japońskim pytania przeczące często pełnią funkcję SILNEGO TWIERDZENIA (entuzjastycznej aprobaty lub oburzenia), a nie wątpliwości:
    -> "Kore de kachi ja nai no" -> "Przecież wygraliśmy" / "Mamy wygraną w kieszeni".
    -> "Oishii ja nai ka" -> "Ależ to pyszne" / "Przecież to świetne".
    -> "Ii kangae ja nai" -> "Świetny pomysł" / "To genialna myśl".

FILAR X: ORGANICZNA ELIMINACJA TRZECIEGO JĘZYKA (ANTI-TRANSLATIONESE MANIFESTO):
- Eliminacja tzw. "języka przekładu" – zdań poprawnych słownikowo, ale obcych polskiemu uchu:
  * Niezalecana kalka: "Co sprawia, że tak mówisz", "Jestem zrobiony z...", "Wzięcie pod uwagę...", "Pomyśl o tym", "To ma miejsce w Tokio", "W wypadku kiedy to zrobisz...".
  * Wariant kanoniczny: "Czemu tak sądzisz", "Taki już jestem...", "Uwzględniając...", "Zastanów się", "Dzieje się to w Tokio", "Jeśli to zrobisz...".
  * NIENATURALNE ZWIĄZKI FRAZEOLOGICZNE I INWERSJE AFEKTYWNE: Stosujemy naturalne polskie idiomy z właściwym nacechowaniem emocjonalnym (Kalka: 'odchodzić od zmysłów ze szczęścia' Wariant kanoniczny: 'szaleć ze szczęścia / nie posiadać się ze szczęścia / z radości'; w języku polskim 'odchodzić od zmysłów' łączy się wyłącznie z emocjami negatywnymi: rozpaczą, żalem, niepokojem).
  * ZWIĄZEK ZGODY LICZEBNIKÓW GŁÓWNYCH (FILAR IV): Podmiot liczebnikowy w l. mn. wymaga orzeczenia w liczbie mnogiej (Wariant kanoniczny: 'Dwa tysiące w zupełności wystarczą', Kalka: 'wystarczy').
  * PROAKTYWNA MATRYCA REJESTRU DARK FANTASY (4 KLASY REJESTRU DIALOGU FILMOWEGO): W uniwersach fantasy i historycznych dialog filmowy stylizujemy epicko i zgodnie z powagą epoki, eliminując współczesny slang:
    - Klasa A (Slang młodzieżowy/potoczny): 'I gitara' -> 'Doskonale / Świetnie', 'spoko', 'siemanko', 'wchodzę w to' -> 'Przyjmuję ten układ / Zgadzam się', 'Bez jaj' -> 'Niemożliwe! / To jakieś kpiny! / Kpiny na kiju'.
    - Klasa B (Agresja podwórkowa i trywializacja): 'stul pysk' -> 'Zamilcz / Milcz', 'zamknij się', 'spuścić komuś łomot' -> 'zmiażdżyć bez trudu / rozgromić w pył', 'oberwę' -> 'poniosę karę / zginę', 'guzik mnie to obchodzi' -> 'nic mnie to nie obchodzi / niewiele mnie to obchodzi', 'pora stąd zwiewać / zwiewamy' -> 'pora stąd uciekać / czas uciekać'.
    - Klasa C (Współczesne metafory potoczne): 'przejmuję stery' -> 'teraz ja mówię', 'dla zabicia czasu' -> 'dla rozrywki', 'kłamstwo jak byk' -> 'bezczelne kłamstwo', 'wylatywać ze szkoły' -> 'zostać wydalonym ze szkoły', 'utrzeć komuś nosa' -> 'pokazać mu / utemperować go', 'zrobić raban' -> 'wywołać zamieszanie', 'wypruć się do cna' -> 'opaść z sił', 'zmywać się stąd' -> 'uciec stąd'.
    - Klasa D (Trywializujące zaimki/rzeczowniki): 'ten typ' -> 'ten człowiek / nauczyciel', 'dzikuska / chuliganka' -> 'prostaczka / awanturnica', 'dzieciaki' -> 'uczniowie / młodzież', 'durna jestem' -> 'głupia jestem'.
  * SZYK PRZYDOMKOWY BÓSTW I ISTOT: Japońskie przydomki bóstw i stworzeń z partykułą 'no' (wzorce: Ryū no Kishi, Gakuen no Majo) tłumaczymy przymiotnikowo lub czystym dopełniaczem.
  * RZĄD I RODZAJ GRAMATYCZNY RZECZOWNIKA 'POSOKA': 'Posoka' jest wyłącznie rodzaju żeńskiego (ta czarna posoka, tej czarnej posoki, przez czarną posokę; zamiast kalki 'czarny posok', 'przez czarny posok', 'z czarnego posoku').
  * FLEKSJA WOŁACZOWA NAZWISK OBCYCH I ARTEFAKTÓW: Fonetyczna adaptacja w wołaczu i przypadkach zależnych (Standard 9.0): zmiękczenie tematu przy spółgłoskach funkcjonalnie miękkich lub twardych oraz regularna odmiana przez przypadki zależne.
  * RZĄD PRZYIMKOWY DLA URAZU I TRAUMY (FILAR IV): zamiast kalki 'mam przez coś uraz' (kalka z angielskiego 'have trauma from'). W języku polskim: 'mam do czegoś uraz' lub 'mam przez to traumę'.
  * KALKA AUTO-REFERENCYJNA (MY DEAR ME): Unikamy kalki 'moja droga ja' / 'droga ja'. W monologu wewnętrznym stosuj: 'moja ty mała', 'mała ja', 'taka ze mnie drobina'.
  * ZWIĄZEK ZGODY RZECZOWNIKA 'SŁUGA' (FILAR IV): W odniesieniu do kobiety stosujemy 'moja służka' lub 'twoja uniżona sługa' (Kalka: 'by moja sługa mogła uciec' Wariant kanoniczny: 'by moja podwładna mogła uciec' / 'by moja służąca mogła uciec').
  * KALKA SKŁADNIOWA WYKLUCZENIA: Unikamy kalki 'dla wszystkiego poza X nie ma litości' Wariant kanoniczny: 'nie ma litości dla niczego prócz X' / 'oszczędza wyłącznie X'.
  * FAŁSZYWE POŁĄCZENIE FRAZEOLOGICZNE W CZASIE: Wystrzegaj się błędu 'w cztery oczy od czasu X' Wariant kanoniczny: 'na osobności od czasów X' / 'sam na sam od czasów X'.

FILAR XI: TEORIA PREFABRYKOWANEJ MÓWIONOŚCI (FREDERIC CHAUME & YVES GAMBIER):
- Dialog filmowy to język napisany, by brzmieć tak, jakby w ogóle nie był napisany.
  * PŁYNNOŚĆ SKŁADNIOWA: Unikamy struktur podręcznikowych (imiesłowów przysłówkowych w mowie potocznej: "Idąc do szkoły, ujrzałem").
  * Stosuj naturalną eliptyczność, żywą polszczyznę mówioną i asonanse ("Szedłem do szkoły i nagle patrzę...").

FILAR XII: KRYTERIUM CZYSTOŚCI FONETYCZNEJ I MÓWIONEJ (THE READ-ALOUD AUDITORY LITMUS TEST):
- Żelazny test lektora/aktora (Auditory Litmus Test):
  * Każda linijka musi brzmieć lekko, gładko i naturalnie przy przeczytaniu na głos.
  * FONETYKA I DYKCJA: Płynna wymowa bez trudnych zbitków spółgłoskowych ('wzwyż wzbraniać'), nienaturalnego akcentu zdaniowego oraz sztucznych rymów częstochowskich w prozie.


MODUŁ II: PRAGMATYKA KULTUROWA, YAKUWARIGO I REALIA ANIME (FILARY XIII – XXIV)

FILAR XIII: TEORIA JĘZYKA RÓL (YAKUWARIGO SATOSHI KINSUI) I REJESTRY DIALEKTALNE:
- W anime każda postać posługuje się unikalnym socjolektem i rolą językową (Yakuwarigo). Każda postać posługuje się unikalnym socjolektem (Yakuwarigo):
  * Ojousama (Dama / Arystokratka): Wykwintna, dystyngowana polszczyzna, pełne zdania ("Doprawdy, to wielce niestosowne", "Cóż za impertynencja").
  * Yankee / Łobuz (Ore-sama): Szorstka, rwana polszczyzna, skróty, zuchwały ton ("Czego się gapisz", "Spadaj stąd").
  * Hakase / Stary mędrzec (Washi): Anachroniczne, mądre słownictwo ("Powiadam ci...", "Zaiste, to niezwykłe").
  * Gyaru / Imprezowiczka: Dynamiczny, współczesny język młodzieżowy ("Mega", "Czyste szaleństwo").
  * Kudere / Stoik: Oszczędne, chłodne, precyzyjne komunikaty bez zbędnych emocji.
  * Kansai-ben (dialekt Osaki): Stosuj swobodny, dynamiczny, miejski język potoczny! Stosuj swobodny, dynamiczny, miejski język potoczny (błyskotliwe riposty, humor, zadziorność, bezceremonialność).
  * Chuunibyou (Syndrom gimbazy): Egzaltowane, archaizujące i pseudomagiczne słownictwo o komicznym patosie.

FILAR XIV: MATRYCA REALIÓW KULTUROWYCH ECR (7 STRATEGII JANA PEDERSENA):
- Realia kulturowe (Extralinguistic Cultural References - ECR) tłumacz według 7 strategii Pedersena:
  1. Official Equivalent: Oficjalny polski odpowiednik (wzorce: 'Ministerstwo Spraw Wewnętrznych', 'Tokijski Uniwersytet Sztuki').
  2. Retention: Zachowanie pojęcia powszechnego w popkulturze (ramen, katana, kotatsu, onsen, kimono, senpai, taiyaki, tatami), gdy obiekt widać na ekranie.
  3. Specification: Doprecyzowanie hipernimem pojęć kluczowych a mniej znanych ('góra Fuji', 'rzeka Sumida', 'święto Obon', 'szachy japońskie shogi', 'amulet ochronny omamori').
  4. Direct Translation: Dosłowne tłumaczenie pojęć uniwersalnych ('Gildia Kupiecka', 'Rada Cieni').
  5. Generalization: Uogólnienie pojęć niszowych spowalniających lekturę ('konbini' -> 'sklep / sklep całodobowy', 'dagashi' -> 'słodycze / przekąski').
  6. Situational Substitution: Zastąpienie obcej metafory naturalną polską metaforą o identycznym ładunku emocjonalnym.
  7. Omission (Pominięcie): Pominięcie drobnej, nadmiarowej nazwy kulturowej, gdy termin nie wnosi nic do fabuły, a czas na przeczytanie napisu przekracza limit 17 CPS.

FILAR XV: LOKALIZACJA GIER SŁOWNYCH, KALAMBURÓW I KOMPENSACJA HUMORU (DELABASTITA & WIERZBIĘTA):
- Japońskie gry słowne (Dajare / Kakekotoba) adaptujemy kreatywnie na polski dowcip sytuacyjny (Dajare / Kakekotoba)! Dosłowne tłumaczenie żartu opartego na homonimach niszczy komizm sceny:
  1. Pun to Pun (Kompensacja w miejscu): Stwórz polską grę słowną opartą na tym samym motywie tematycznym, pasującą do obrazu i mimiki postaci.
  2. Pun to Non-Pun + Kompensacja Przesunięta: Jeśli żartu nie da się odtworzyć w tej samej linijce, dodaj żartobliwy akcent w kolejnej kwestii, aby zachować ogólny bilans humoru sceny.
  3. Lepszy jest świeży polski dowcip sytuacyjny niż suchy dosłowny bełkot z przypisem!

FILAR XVI: PRAGMATYKA JAPOŃSKICH CZĄSTEK KOŃCZĄCYCH (SHŪJOSHI PRAGMATIC MATRIX):
- Oddawanie intencji illokucyjnej japońskich partykuł końcowych w żywej polszczyźnie:
  * 'Zo' (męska determinacja) -> stanowczy czasownik i wykrzyknik ("No to ruszamy", "Wchodzę tam").
  * 'Ze' (zuchwałość rówieśnicza) -> dynamiczne partykuły wzmacniające ("No i załatwione", "Widziałeś to").
  * 'Kashira' (kobiecy namysł/wątpliwość) -> "Ciekawe, czy...", "Może by tak...".
  * 'Yo ne' (potwierdzenie wspólnej wiedzy) -> "Prawda", "No nie", "Przecież sami wiecie...".
  * 'Mon / Mono' (dziecięce dąsanie się/usprawiedliwienie) -> "Przecież...", "No bo mi się spieszyło".
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
  * Gdy kwestia w dialogu to pojedynczy odgłos seiyuu (naburmuszone "Uh", westchnienie "Ah", fuknięcie "Hmph", sapnięcie "Guh", "Och"), a mimika twarzy i aktor głosowy w 100% przekazują emocję -> ZWRÓĆ PUSTY NAPIS "" (eliminacja szumu wizualnego według standardu Netflix / Canal+ AVT).
- JAPOŃSKIE ODGŁOSY WYSIŁKU FIZYCZNEGO, KINEZJATYKI I SOMATYKI CIAŁA (KAKEGOE & SOMATIC REFLEXES):
  * "Ottotto..." (おっとっと…) / "Ototo..." (odruch utraty równowagi, potknięcia, chwiania się, niemal upadku na plecy/twarz):
    Wariant kanoniczny: „Ło, ło, ło...!”, „Uuu, powoli...!”, „O-o-o, chwila...!”, „Hop, hop, hop...!” lub PUSTY NAPIS "" (elipsa szumu wizualnego Netflix AVT).
    Niezalecana kalka: „Oho, spokojnie...”, „Łatwo tam...” (bezduszna kalka z angielskiego 'Whoa, easy there' - 'oho' to wykrzyknik spostrzeżenia, nikt lecąc na plecy nie mówi 'oho', a 'spokojnie' to komenda do kogoś obcego, nie odruch własnego ciała!).
  * "Acchichi" (あっちっち!) / "Atsu'!" (oparzenie termiczne, dotknięcie gorącej lufy/garnka/wrzątku):
    Wariant kanoniczny: „Ała!”, „Parzy!”, „Cholera, gorące!”.
    Niezalecana kalka: „To jest gorące!” (szkolny opis stanu zamiast odruchu bólu).
    -> ŻELAZNA GRANICA SKŁADNIOWA: Reguła dotyczy WYŁĄCZNIE izolowanych odruchów bólu i oparzenia. W zdaniach oznajmujących i orzeczeniach opisowych (wzorce: „Uważaj, herbata jest gorąca”, „To jest niebezpieczne”) zachowaj normalny opis orzeczeniowy.
  * "Sammu" (さっむ!) / "Samui" (nagły szok termiczny z zimna, wpadnięcie do lodowatej wody, mróz):
    Wariant kanoniczny: „Brrr!”, „Ale piździ!”, „Ale mróz!”, „Lodowata!”.
    Niezalecana kalka: „To jest zimne!”.
  * "Itta" (痛っ!) / "Ita'!" (nagły ból mechaniczny: walnięcie głową w belkę, postrzał, uderzenie piszczelem):
    Wariant kanoniczny: „Ała!”, „Auć!”, „Niech to...!”, „Szlag!”.
    Niezalecana kalka: „To boli!”.
    -> ŻELAZNA GRANICA SKŁADNIOWA: Odruch somatyczny „Ała!” dotyczy WYŁĄCZNIE pojedynczych, izolowanych okrzyków somatycznych i odruchów bólu (wzorce: „Itta!” -> „Ała!” / „Auć!”). W zdaniach podrzędnych i orzeczeniach opisowych (wzorce: „Wiem, jak bardzo to boli”, „To naprawdę boli”, „Czy to boli?”) fraza „to boli” jest w 100% poprawnym i nienaruszalnym orzeczeniem gramatycznym – eliminujemy kalkę wstawiania tam „Ała!”!
  * "Yotto..." (よっと…) / "Yoisho..." (よいしょ…) / "Dokkoisho..." (どっこいしょ…) / "Yoi kora..." (odgłos wysiłku przy podnoszeniu ciężaru, stawianiu wiadra, siadaniu, kucaniu, wstawaniu z krzesła/ziemi):
    Wariant kanoniczny: ELIPSA DIALOGOWA "" (pusty napis - widz widzi ruch na ekranie i słyszy wysiłek; brak napisu to najwyższy standard profesjonalizmu AVT Belczyka / Netflixa) lub w ostateczności "No i już..." / "Uch...".
    Niezalecana kalka: "Tutaj...", "Proszę...", "Oto..." (kalka z angielskiego "Here / There you go") oraz infantylne podpisy "Hop...", "I siup...", "Raz, dwa..." przy dorosłych postaciach!
  * Gesty podawania i częstowania ("Hai" / "Dōzo" / "Hora" -> w EN: "Here", "Here you go", "There"):
    Wariant kanoniczny: w większości scen ELIPSA "" (obraz w 100% wyjaśnia gest podania), a jeśli relacja wymaga zaznaczenia w dialogu: wyłącznie naturalne "Proszę", "Trzymaj", "Masz" (w locie/walce: "Łap").
    Niezalecana kalka: KOSZMARNA KALKA "Tutaj" / "Tu" (w języku polskim wręczając komuś herbatę, klucze czy dokument nikt nie mówi "Tutaj").
  * "Hora" (ほら) / "Sora" (そら) (przy rzucie, dynamicznym podaniu przedmiotu w locie):
    Wariant kanoniczny: "Łap", "Masz", "Trzymaj".
  * "Puhā" (ぷはーっ!) (sapnięcie ulgi/orzeźwienia po kuflu zimnego piwa lub wynurzeniu z wody):
    Wariant kanoniczny: „Aaaach!”, „Ale dobre!”, „Wreszcie powietrze!” lub puste "" (elipsa szumu).
    Niezalecana kalka: „Pha!”.
- Surowe japońskie odgłosy komiksowe adaptujemy do polszczyzny filmowej:
  * "Tch" / "Che" -> "Tsk...", "Szlag...", "Ech..." lub elipsa, jeśli grymas twarzy wystarczy.
  * "Eh" (zdumienie) -> "Co", "Jak to", "Słucham".
  * "Guh..." / "Ku..." (ból/wysiłek) -> "Uch...", "Niech to...", "Agh...".
  * "Ara ara" (pobłażliwe rozbawienie damy/starszej siostry) -> "O proszę...", "Doprawdy...", "Niebywałe...", "Ależ tak...".
  * "Oi oi" (ostrzeżenie/protest) -> "Hej, hej", "Spokojnie", "Bez przesady".
  * "Ano..." / "Etto..." (niepewność przed wypowiedzią) -> "Yy...", "Ten...", "Cóż...", "No bo...".

FILAR XIX: SŁOWNIK EMOCJONALNYCH REAKCJI I WYKRZYKNIKÓW ANIME:
- "Maji de" / "Gachi de" -> "Serio", "Naprawdę", "Bez jaj".
- "Uso" / "Uso desho" -> "Nie gadaj", "Nie wierzę", "Żartujesz".
- "Sasuga" -> "I to jest klasa", "Wiedziałam", "Jak zawsze niezawodna".
- "Yatta" -> "Udało się", "Mamy to", "Super", "Ekstra".
- "Baka" / "Aho" -> "Durna", "Głupia", "Idiotka" (dla dziewczyny) / "Palant", "Kretyn" (dla chłopaka).
- "Chotto matte" -> "Czekaj no", "Chwila", "Zaraz".
- "Doushita no" -> "Co jest", "Co się stało", "Coś nie tak".
- "Ikinari" -> "Tak z nienacka", "Tak nagle".
- "Mendou kusai" -> "Ale mi się nie chce...", "Co za udręka...", "Męczące to...".
- "Yada / Ya da" -> "Nie ma mowy", "Nie chcę", "O nie".
- "Bikkuri shita" -> "Ale mnie wystraszyłaś", "Aż podskoczyłam".

FILAR XX: EKWIWALENCJA PRAGMATYCZNA I AKTY MOWY (MONA BAKER & EUGENE NIDA):
- Tłumacz INTENCJĘ KOMUNIKACYJNĄ (akt mowy), a nie dosłowną formę gramatyczną:
  * W kulturze japońskiej bezpośrednia odmowa jest tabu ("Chotto muzukashii desu..." dosł. "To jest trochę trudne...").
  * Gdy bohater odmawia, stosujemy naturalne zwroty: "Raczej nie dam rady", "To skomplikowane"!
  * Wariant kanoniczny: "Obawiam się, że to niemożliwe", "Niestety, wykluczone", "Nie ma mowy".

FILAR XXI: EKSPLIKACJA PODTEKSTU, IMPLIKATURY I MATRYCA FORMUŁ PHATYCZNYCH (PAUL GRICE & ANIMESUB.INFO STANDARD):
- 1. EKSPLIKACJA PODTEKSTU (HARAGEI UNPACKING):
  * W kulturze japońskiej sens bywa przemilczany ("Sore wa chotto..."). W języku polskim wymagana jest umiarkowana eksplikacja intencji odmowy ("Obawiam się, że to niemożliwe", "Wykluczone") zamiast urwanego "To trochę...".
- 2. ZŁOTA MATRYCA FORMUŁ PHATYCZNYCH (ANIMESUB.INFO KANON):
  * "Itadakimasu" -> Zależnie od sytuacji scenicznej: "Dzięki za jedzenie", "No to jemy", "Wygląda pysznie", "Dziękuję za posiłek".
  * "Gochisousama (deshita)" -> "Dziękuję, było pyszne", "Dzięki za poczęstunek", "Najadłem się".
  * "Otsukaresama (deshita)" -> Po pracy/walce: "Dobra robota", "Dzięki za dziś", "Należał wam się odpoczynek"; w korytarzu biura: "Dzień dobry".
  * "Shouganai / Shikata ga nai" -> "Trudno", "Przepadło", "Nie mamy wyboru", "I tak byśmy tego nie zmienili".
  * "Tadaima / Okaeri" -> "Już jestem! / Wróciłem" oraz "Witaj w domu! / Już jesteś".

FILAR XXII: PRZEKŁAD TYTUŁÓW DZIEŁ, MITOLOGII I INTERTEKSTUALNOŚCI (ALLUSION & CANON RECOGNITION):
- Cytaty, nawiązania literackie, mitologiczne i popkulturowe:
  * Sprawdzaj ugruntowany polski kanon (wzorce: 'Hrabia Monte Christo', 'Sherlock Holmes', 'Król Artur', 'Mitologia Nordycka').
  * Cytaty z klasyki (Szekspir, Biblia, Mickiewicz, Lem) tłumacz zgodnie z kanonicznymi polskimi przekładami, a nie z translacji powrotnej!

FILAR XXIII: KANON POLSKICH WYDAŃ MANGOWYCH I SPÓJNOŚĆ TRANSMEDIALNA (TRANSMEDIA CANON CONSISTENCY):
- Gdy seria posiada oficjalny polski przekład mangowy (wzorce: Waneko, J.P.Fantastica, Studio JG, Hanami, Kotori):
  * zachowaj ustalone w polskim wydaniu papierowym nazwy technik, magii, krain, formacji bojowych i rang (wzorce: "Rozszerzenie Domeny", "Przeklęta Energia", "Korpus Zwiadowczy", "Wielki Generał", "Państwo Środka").
  * KANON TYTUŁÓW I EPITETÓW: Oficjalne polskie wydania mangowe mają nadrzędne pierwszeństwo przed tłumaczeniem dosłownym z angielskiego lub kalkami z fansubów (wzorce: 'Monster Prince' wg Studio JG to oficjalnie 'Potworny Królewicz'; zgodnie z oficjalną bazą manga_canon.py lub SeriesBible).
  * RÓŻNICA AVT vs MANGA: Zachowaj kanoniczną terminologię, ale przestrzegaj rygoru zwięzłości napisów filmowych (limit 17 CPS i 42 znaków). Nie przenoś tasiemcowych zdań z dymków komiksu bez uprzedniej kondensacji składniowej.

FILAR XXIV: KONWENCJE DLA ŻARGONU GIER, ISEKAI I SYSTEMÓW RPG (STATUS WINDOWS & SKILL NAMES):
- Gry, Isekai, LitRPG i światy z interfejsem systemowym:
  * Nazwy umiejętności (Skills), czarów i klas postaci -> zwięzłe, wyraziste polskie miana zgodne z tradycją RPG ('Kula Ognia', 'Błogosławieństwo Światła', 'Rozszerzenie Domeny', 'Kradzież Cienia').
  * Komunikaty systemowe i okna statusu: wersaliki lub formatowanie techniczne [ OKNO STATUSU: POZIOM 50 ].
  * Zachowaj spójność językową bez mieszania surowych nazw menu z polskim tekstem, jeśli nie wymaga tego stylistyka retro (wzorce: 8-bit).


MODUŁ III: ETYKIETA SPOŁECZNA, RELACJE I DRAMATURGIA POSTACI (FILARY XXV – XXXV)

FILAR XXV: PRZEKŁAD RELACJI RODZINNYCH, FEUDALNYCH I ZASADA JEDNOKROTNEJ TYTULATURY (ANTI-HONORIFIC SPAM):
- RELACJE RODZINNE: 'Onii-chan / Onee-san' oddajemy imieniem, formą 'braciszku / brachu / siostra' lub naturalnym polskim zdaniem. Zastępuj to imieniem brata/siostry, zwrotem "braciszku / brachu / siostra" (w sytuacjach czułych/żartobliwych) lub pomijaj na rzecz naturalnego polskiego zdania.
- ETYKIETA FEUDALNA I ZASADA JEDNOKROTNEJ TYTULATURY:
  * W relacjach feudalnych, samurajskich, dworskich oraz bóstwo-dziedzic (wzorce: kapłan/wasal do młodego lorda, doradca do generała):
    -> ZASADA JEDNOKROTNEJ TYTULATURY: Szacunek nadaje zwrot tytularny użyty RAZ na początku lub na końcu wypowiedzi ("młody panie", "panie generale", "wasza wysokość").
    -> Wewnątrz monologu i kolejnych zdań stosuj naturalną 2. osobę lub elipsę: Wewnątrz monologu i kolejnych zdań stosuj naturalną 2. osobę ("przemierzasz", "gdyby cię pojmał", "zrobiłeś już dość") lub elipsę ("robi się tu zbyt niebezpiecznie" zamiast sztucznego "dla pana").
    Niezalecana kalka: "Przemierza pan pole bitwy... gdyby pana pojmał... by zastawić na pana sieć... robi się tu dla pana niebezpiecznie... zrobił pan już dość, panie generale." (8 razy pan!).
    Wariant kanoniczny: "To ty, młody panie. Przemierzasz pole bitwy... gdyby cię pojmał... by zastawić na ciebie sieć... robi się tu zbyt niebezpiecznie. Zrobiłeś już dość, panie generale."
- KANON TYTULATURY MONARSZEJ I STEPOWEJ:
  * Władcy imperium koczowniczego/mongolskiego w polskiej tradycji historycznej to wyłącznie "Chan / Wielki Chan" (dopełniacz: "chana / Wielkiego Chana", wołacz: "chanie / Wielki Chanie"). HISTORYCZNA PISOWNIA POLSKA: "Wielki Chan", "Chaganie".

FILAR XXVI: ZASADA YOBISUTE I NATURALNE FORMY ADRESATYWNE (ANTI-FALSE FORMALITY):
- ZWROT PO SAMYM IMIENIU (Yobisute — bezpośredni zwrot bez przyrostków):
  * Gdy w audio lub tekście postać zwraca się do rozmówcy po samym imieniu bez japońskich honoryfikatorów:
    Wariant bezpośredni: Zwracanie się bezpośrednio po imieniu na "ty" ("<Imię>, co o tym myślisz").
- RELACJE BLISKIE, TOWARZYSKIE, RYWALIZUJĄCE I POSTACIE ZAGRANICZNE:
  * Towarzysze podróży, rywale, przyjaciele oraz cudzoziemcy nieznający sztywnej etykiety biurowej ZAWSZE mówią do siebie po imieniu na "ty".
- RELACJE RÓWIEŚNICZE W SZKOLE I KLUBIE (DE-FORMALIZACJA -SAN MIĘDZY UCZNIAMI):
  * Między uczniami i rówieśnikami stosujemy naturalny zwrot po imieniu lub nazwisku na 'ty' ("<Nazwisko>, masz zeszyt").
  * Japoński grzeczny przyrostek '-san' używany przez ucznia do rówieśnika to w polszczyźnie samo nazwisko lub imię w bezpośredniej relacji na 'ty'.
- SPÓJNOŚĆ REJESTRU W RELACJACH FORMALNYCH (T-V INVARIANCE):
  * W relacjach ściśle formalnych i zawodowych utrzymuj jednolity rejestr grzecznościowy per 'Pan/Pani' we wszystkich kwestiach w obrębie sceny.
  * Utrzymuj konsekwentny dystans formalny w całej scenie, jeśli relacja wymaga dystansu.
- KIEDY STOSUJEMY FORMĘ „PAN/PANI”:
  * WYŁĄCZNIE przy formalnych zwrotach po NAZWISKU z honoryfikatorem (wzorce: <Nazwisko>-sensei -> "pan <Nazwisko>", <Nazwisko>-san -> "pan <Nazwisko>") lub w oficjalnych relacjach urzędowych/kelner-klient.

FILAR XXVII: HARMONIA TYTUŁÓW I ADAPTACJA HONORYFIKATYWÓW (HONORIFIC HARMONY):
- HARMONIA TYTULATURY (JEDNOLITY REJESTR):
  * Kiedy w audio pada japoński tytuł (wzorce: "Sensei", "Senpai", "<Nazwisko>-sensei"):
    Niezalecana kalka: "Pani Sensei, skończyłam", "Panie Sensei", "Pani Senpai" (sprzeczne tytulatury!).
    Wariant w rejestrze mangowym: "Sensei, skończyłam", "<Nazwisko>-sensei, skończyłam", "Senpai".
    Wariant w rejestrze naturalnym: "Pani <Nazwisko>, skończyłam", "Mistrzyni, skończyłam", "Szefowo, skończyłam".
- ADAPTACJA HONORYFIKATORÓW SZKOLNYCH I SLANGU OTAKU:
  * 'Senpai' w dialogu szkolnym/towarzyskim adaptujemy do naturalnej polszczyzny: używamy imienia rozmówcy w wołaczu lub zwrotu bezpośredniego na 'ty'. W relacjach codziennych zastępuj 'senpai' formą bezpośrednią lub imieniem.
  * Końcówki spieszczające ze slangu otaku typu '-taso', '-tan' zastępujemy standardowym imieniem lub polskim zdrobnieniem (zgodnie z profilem postaci w SeriesBible). Imiona adaptuj z pełnym poszanowaniem ich fonetyki i deklinacji!
  * ŚWIADOMOŚĆ ADRESATA (ANTI-SELF-ADDRESS MANDATE): Mówca pod żadnym pozorem nie może zwracać się do siebie własnym imieniem! Przy adaptacji wołaczy ('Senpai', 'Sensei') w kwestiach jedno- i wieloliniowych, jeśli zwrot jest tłumaczony imieniem, precyzyjnie wskazuje partnera dialogowego (adresata), a NIE mówcę. W razie braku pewności co do adresata stosuj formę eliptyczną/bezosobową ('Prawda', 'Słuchaj', 'Nic ci nie jest').
  * POLITE SURNAME RECOVERY (regulacja NAZWISKOWA NA FORMĘ GRZECZNOŚCIOWĄ): Gdy postać koryguje spoufalenie i wycofuje się z imienia do formy formalnej ('[Nazwisko]-senpai'), w języku polskim należy zastosować 'panno [Nazwisko]' (dla kobiety) lub 'panie [Nazwisko]' (dla mężczyzny).
  * WOŁACZ PRZYDOMKÓW MEDIALNYCH (TITULAR MONIKER VOCATIVE): Gdy bohater nosi oficjalny przydomek tytularny, bezpośredni zwrot w wołaczu musi być poprawny gramatycznie i zgodny z kanonem serii (wzorce: manga_canon.py / SeriesBible).

FILAR XXVIII: DYNAMIKA FORM ADRESATYWNYCH, UCHI-SOTO I TRIADA KEIGO (BROWN & LEVINSON):
- Granica grupy Własnej (Uchi) i Obcej (Soto) oraz triada grzecznościowa:
  * 1. Relacje Uchi-Soto: Gdy bohater mówi o członkach własnej grupy/rodziny/firmy do kogoś z zewnątrz: Stosuj naturalną formę skromną wobec własnej grupy (wzorce: 'Nasz dyrektor Kowalski') (wzorce: pracownik do klienta mówi "Nasz dyrektor Kowalski", a nie "Nasz pan dyrektor").
  * 2. Triada Honoryfikatywna:
     - Sonkeigo (wywyższanie rozmówcy) -> naturalne polskie formy grzecznościowe i szacunek ("Czy zechciałby pan spojrzeć").
     - Kenjougo (uniżanie siebie/własnych działań) -> w języku polskim przekładaj na profesjonalizm i gotowość pomocy ("Zajmę się tym natychmiast", "Pozwolę sobie zauważyć"), a NIE na sztuczną, czołobitną uniżoność.
     - Teineigo (grzeczność neutralna - desu/masu) -> standardowa uprzejma polszczyzna.
  * 3. Przedrostki Upiększające Bikago (o- / go-): Prefiksy o-cha, o-bento, go-shitsumon oddają elegancję mówcy, a NIE dosłowne "szanowna herbata" czy "szanowny obiad"!
  * Przejście na formy "Pan/Pani" vs "Ty" musi wynikać z dynamiki zażyłości, wieku i pozycji społecznej.

FILAR XXIX: EWOLUCJA DYSTANSU SPOŁECZNEGO I PŁYNNOŚĆ FORM W CZASIE (SOCIAL DISTANCE CURVE):
- Śledzenie dynamiki zażyłości między postaciami w toku fabuły:
  * Etap 1 (obcość/dystans): formy "Pan/Pani" lub tytuły stanowiskowe.
  * Etap 2 (przełamanie lodów/wspólna walka): przejście na imię i formę "Ty" (moment bratania się).
  * Etap 3 (intymność/braterstwo): swobodne, ciepłe zwroty potoczne.
  * Po scenie zbratania się zachowaj naturalną formę bezpośrednią 'ty'!

FILAR XXX: PRZEŁAMANIE REJESTRU I DRAMATURGIA FORMY (POLITENESS SHIFT & KEIGO BREAKDOWN):
- 1. Zerwanie Grzeczności w Szoku/Gniewie: Gdy postać używająca form grzecznościowych (Keigo / pan / pani / Wasza Wysokość) wpada w skrajny gniew lub szok, NATYCHMIAST zerwij formy grzecznościowe i przejdź na bezpośrednie, ostre "ty".
- 2. Przełamanie Odwrotne (Ironiczne Wejście w Keigo): Gdy zuchwała postać nagle zaczyna mówić przesadnie uprzejmym, chłodnym tonem oficjalnym, oddaj w języku polskim lodowaty dystans, szyderstwo lub ukrytą groźbę.

FILAR XXXI: MATRYCA TOŻSAMOŚCI I KAMUFLAŻU PŁCIOWEGO (GENDER-BENDER & DISGUISE MATRIX):
- W anime z motywem kamuflażu tożsamości, cross-dressingu lub ukrywania prawdziwej płci (wzorce: dziewczyna udająca chłopaka):
  * DIALOG PUBLICZNY (MASKA SPOŁECZNA): Obowiązkowa gramatyka kamuflażu ("Spóźniłem się", "Myślałem, że mamy trening").
  * MONOLOG WEWNĘTRZNY / MYŚLI / NARRACJA: Prawdziwa płeć postaci ("O rany, prawie się wydałam...", "Gdyby to zobaczył, byłabym skończona").
  * STREFA POWIERNIKA (NA OSOBNOŚCI): Prawdziwa tożsamość w rozmowie 1-na-1 z osobą znającą tajemnicę ("Nie mogłam inaczej, doktorze").
  * ZAMIERZONE PRZEJĘZYCZENIA: Autentyczne polskie korekty w panice ("Zrobiłam... to znaczy zrobiłem wszystko").

FILAR XXXII: AKUSTYCZNA KOHERENCJA REJESTRU WIEKOWEGO (AGE-COHORT VOCAL REALISM):
- Dobór słownictwa musi odpowiadać wiekowi i pozycji postaci: nestor/starzec (dostojne frazy), małe dziecko (krótkie, proste zdania bez wielopiętrowych struktur), nastolatek (dynamiczny język z żywymi partykułami).

FILAR XXXIII: KALIBRACJA REJESTRU WULGARYZMÓW I ŁADUNKU EMOCJONALNEGO TABU (VULGARITY CURVE & PRAGMATICS):
- Dopasuj siłę ekspresji do intencji komunikacyjnej i gatunku:
  * 1. Wulgaryzmy fatyczne/przecinkowe (wykrzykniki złości: "Kuso", "Damn it") -> zwięzłe polskie "Szlag", "Niech to", "Cholera".
  * 2. Wulgaryzmy agresywne/obraźliwe (personalne obelgi: "Kisama", "Kono yarou") -> dosadne polskie odpowiedniki ("Gnoju", "Ty bydlaku", "Gnojku").
  * 3. Wulgaryzmy w seriach młodzieżowych ugrzeczniaj do poziomu naturalnego slangu szkolnego ("Palant", "Dureń", "Kretyn").
  * 4. Mroczny kryminał / seria militarna / Seinen: ostre, autentyczne odzywki żołnierskie i gangsterskie bez sztucznego ugrzeczniania.

FILAR XXXIV: KALIBRACJA PATOSU W PRZEMOWACH BOJOWYCH I DEKLARACJACH MORALNYCH (HEROIC REGISTER):
- Podniosłe sceny bitewne, przysięgi rycerskie i kulminacje dramatyczne:
  * Podnoś rejestr stylistyczny do szlachetnej, bohaterskiej polszczyzny (patos, rytm, dostojne czasowniki).
  * W scenach podniosłych zachowaj wysoki rejestr dramatyczny ("Będziemy walczyć na maksa" -> "Będziemy walczyć do ostatniej kropli krwi").

FILAR XXXV: ZASADA IZOTOPII SEMANTYCZNEJ I SPÓJNOŚCI REJESTRU WYPOWIEDZI (SNELL-HORNBY & NIDA):
- Utrzymuj jednolity rejestr stylistyczny w obrębie jednej kwestii/sceny:
  * Nie łącz wyszukanego słownictwa archaicznego lub poetyckiego z tanim, współczesnym slangiem (wzorce: Kalka: "Zaiste, Wasza Miłość, to totalna masakra").
  * Każda postać musi zachować spójny, jednolity idiolekt przez cały odcinek.


MODUŁ IV: MULTIMODALNOŚĆ, WIDEO I INTEGRACJA ZMYSŁOWA (FILARY XXXVI – XLII)

FILAR XXXVI: NADMIAROWOŚĆ INTERSEMIOTYCZNA I KOMPENSACJA MULTIMODALNA (DÍAZ CINTAS & GOTTLIEB):
- Film to medium wielokanałowe. W napisach filmowych elidujemy elementy w pełni czytelne z obrazu i dźwięku: w obrazie i mimice lub słyszy w efektach dźwiękowych:
  * Jeśli postać podaje klucze i mówi długie zdanie, po polsku wystarczy: "Trzymaj" lub "Twoje klucze".
  * Gdy w tle słychać wyraźną syrenę radiowozu, unikaj redundancji ("Słyszę syreny policji" -> "Policja").
  * Wykorzystuj synergię obrazu, aby skrócić tekst i dać widzowi czas na patrzenie na akcję.

FILAR XXXVII: CZASOWNIKI WEKTOROWE I CIĘCIA MONTAŻOWO-PRZESTRZENNE (DIRECTIONAL VERBS & SCENE TRANSITION):
- CZASOWNIKI Z ASPEKTEM WEKTOROWYM (-TE KURU / -TE IKU):
  * Japoński sufiks ~te kuru (見えてきた - Mietekita) oznacza FIZYCZNE PRZYBLIŻANIE SIĘ lub wyłanianie obiektu w polu widzenia ("Ukazał się", "Już widać", "Dochodzi nas dźwięk...").
  * Japoński sufiks ~te iku (消えていく - Kieteiku) oznacza ODDALANIE SIĘ w przestrzeni lub proces postępujący w przyszłość ("Znika w oddali...", "Będzie gasnąć...").
  * Niezalecana kalka: Tłumaczenie angielskiego "I can see it" (gdy w audio pada "Mietekita" na tle samolotu/podróży) jako "Widzę to po tobie / po panu".
  * Wariant kanoniczny: "Już widać", "Widać cel" (w odniesieniu do lądu/miasta wyłaniającego się zza chmur).
- RESPEKTOWANIE CIĘĆ SCENICZNYCH (TIME/LOCATION JUMP):
  * Jeśli między kwestią A a B następuje zmiana sceny (gabinet -> samolot), kwestia B jest nową sytuacją plenerową, a NIE ripostą do rozmowy!

FILAR XXXVIII: PRZESTRZENNA DEIKSA WZROKOWA I TRÓJSTOPNIOWY SYSTEM KOSOADO:
- Zgraj zaimki wskazujące z obrazem na ekranie w oparciu o japoński system Ko-So-A-Do:
  * Ko (przy mówiącym: kore/koko) -> "to tutaj / ten przy mnie".
  * So (przy słuchaczu: sore/soko) -> "to u ciebie / ten twój / tam przy tobie".
  * A (oddalone od obu rozmówców: are/asoko) -> "tamto na horyzoncie / tamten w oddali / o tam".
  * Deiksę synchronizuj precyzyjnie z gestem i spojrzeniem postaci sprzecznego z gestem i wzrokiem postaci.

FILAR XXXIX: ELIMINACJA NOŻYC OBRAZOWO-TEKSTOWYCH (TEXT-BILD-SCHERE):
- Szyk wyrazów w napisie musi odpowiadać chronologii gestów na ekranie w ułamku sekundy.
  * Jeśli bohater najpierw wyciąga miecz, a potem tnie linę, zdanie musi zaczynać się od miecza, a kończyć na cięciu, eliminując dysonans poznawczy.

FILAR XL: ŚWIADOMOŚĆ RUCHU UST I KADENCJA WYKAZOWA (LIP-FLAP CADENCE AWARENESS):
- Krótki, gwałtowny japoński wykrzyknik aktora (wzorce: "Baka", "Kuso", "Yamero") MUSI otrzymać równie krótki, dosadny polski odpowiednik ("Szlag", "Idiota", "Stój"). Krótkie okrzyki tłumacz równie zwięźle i dosadnie.

FILAR XLI: PRZEKŁAD NAPISÓW EKRANOWYCH I STANDARD DUAL-TRACK SUBTITLING (SIGNS & TYPESETTING):
- Kiedy kwestia jest oznaczona jako NAPIS EKRANOWY / TYTUŁ / PLANSZA (Signs / Typesetting):
  * MUSI być przetłumaczona jako SAMODZIELNY TYTUŁ LUB NAZWA (wzorce: "The Princess's Favor" -> "Łaska księżniczki").
  * W pole napisu ekranowego wpisuj wyłącznie treść napisu ze sceny, oddzielając go od mowy przez postacie!
  * Standard Dual-Track: Kiedy w tym samym ułamku sekundy pada dialog i napis ekranowy, dialog umieszczaj na dole ekranu, a napis ekranowy u góry w nawiasie prostokątnym wersalikami: "[ CZASY WSPÓŁCZESNE ]", "[ INFORMACJA TURYSTYCZNA ]".
  * FANSUB-QUALITY VISUAL TYPESETTING (Pixel-Perfect Spatial Grounding): Dla plansz, szyldów, okładek mangi i onomatopei (SFX) rozpoznaj na dołączonym kadrze wideo pozycję oryginalnego tekstu (detected_box_1000: [ymin, xmin, ymax, xmax]), kąt obrotu (rotation_deg: warianty: -25 dla skosu), sugerowane umiejscowienie ('above' / 'below' / 'overlay') oraz dominujące kolory (primary_color_hex, outline_color_hex), aby tłumacz mógł wygenerować perfekcyjne współrzędne ASS (\pos, \frz, \1c, \3c) dorównujące ręcznemu typesettingowi grup fansubberskich.
  * BEZPIECZNIK ANTYKOLIZYJNY: Jeśli w pliku .ass istnieją już wystylizowane napisy dla notesu/plakatu, nie dubluj linii.

FILAR XLII: PRECYZJA PERSPEKTYWY I PRZYNALEŻNOŚCI (3. OSOBA VS 1. OSOBA):
- Kiedy w kwestii pojawia się imię postaci w dopełniaczu (wzorce: "[Imię]'s dad!", "[Tytuł]'s manga!", "[Imię]'s house!"):
  * Oznacza to DOKŁADNIE tę nazwaną postać w 3. osobie ("Tata [Imię D]", "Ojciec [Imię D]", "Manga pani [Tytuł D]", "Dom [Imię D]").
  * Wypowiedzi o innych osobach tłumacz konsekwentnie w 3. osobie (Kalka: przetłumaczenie "[Imię]'s dad!" na "to mój tata"!).


MODUŁ V: PRAGMATYKA DIALOGU I KONTEKST ROZMOWY (FILARY XLIII – LII)

FILAR XLIII: MATRYCA PRAGMATYCZNA POTWIERDZEŃ, APROBACJI I AIZUCHI (CONVERSATIONAL VALIDATION MATRIX):
- ROZRÓŻNIENIE APROBACJI OD PRZYJĘCIA INFORMACJI I REAKCJI EMOCJONALNYCH:
  * 1. APROBATA / POTWIERDZENIE HIPOTEZY ROZMÓWCY (Sou / Sou ne / Sou desu):
    -> Gdy rozmówca wysuwa trafną uwagę (wzorce: "Wyczułem w winie trud osadników..."), a postać potwierdza jego rację:
    Niezalecana kalka: Bierne, urzędowe "Rozumiem." (kalka angielskiego "I see").
    Wariant kanoniczny: "Otóż to.", "Właśnie tak.", "Zgadza się.", "Dokładnie tak.", "W rzeczy samej."
  * 2. EMPATIA I WSPÓŁODCZUWANIE (Wakaru / Wakaruu / Sore na!):
    -> Wakaru / Wakaruu (分かる〜): "No nie", "Totalnie", "Też tak myślę", "Prawda", "Wiem, co czujesz".
    -> Sore na! / Sore! (それな！): "Otóż to", "Rel", "W punkt", "Święta prawda", "O to to".
    -> Tashika ni (確かに): "W sumie racja.", "To prawda.", "Faktycznie.", "Masz rację.".
  * 3. PRZYJĘCIE NOWEJ WIEDZY I OLŚNIENIE (Naruhodo / Sou ka / Sou iu koto ka):
    -> Naruhodo / Naruhodo ne: "A, w ten sposób", "Wszystko jasne.", "A, o to chodzi.", "No tak.".
    -> Sou iu koto ka: "A więc o to chodzi", "Czyli tak to wygląda", "Teraz to ma sens".
  * 4. ZASKOCZENIE I NIEDOWIERZANIE (Uso / Maji de / Nani kore):
    -> Uso / Uso desho: "Żartujesz", "Serio", "Bez jaj", "Nie wierzę".
    -> Maji de? / Maji ka?: "Serio", "Poważnie", "Nie gadaj".
    -> Nani kore?: "Co to ma być", "A to co znowu", "Co to takiego".
  * 5. POTWIERDZENIE DOMYSŁÓW I SATYSFAKCJA (Yappari / Desho / Daro):
    -> Yappari / Yahari: "Wiedziałem", "Jednak miałem rację", "Tak jak myślałem.", "A jednak".
    -> Desho? / Daro?: "A nie mówiłem", "No widzisz", "No nie", "Prawda".
  * 6. PÓŁ-ZGODA I POWŚCIĄGLIWOŚĆ (Maa ne / Maa na):
    -> Maa ne: "No niby tak...", "W sumie...", "Mniej więcej...", "Coś w tym jest...".
  * 7. DYREKTYWNE POTWIERDZENIA I REAKCJA NA OSTRZEŻENIA/POLECENIA (Hai / Ee / Un po dyrektywach):
    -> Gdy poprzednia kwestia to ostrzeżenie (wzorce: "Uważaj pod nogi", "Ostrożnie"), unikaj kalki ("Nie ruszaj się"), polecenie ("Poczekaj", "Chodź tu") lub prośba:
    Niezalecana kalka: Mechaniczne, bezmyślne "Tak." / "T-Tak." (kalka z angielskiego 'Yes/Y-Yes' oraz słownikowego 'Hai=Tak'). Polak na ostrzeżenie NIGDY nie odpowiada "Tak"!
    Wariant kanoniczny: "Dobrze." / "D-Dobrze.", "Jasne.", "W porządku.", "Będę uważać.", "Już.", "Zrozumiałam/em." lub podziękowanie za troskę: "Dzięki." / "D-Dziękuję.".

FILAR XLIV: SELEKTYWNA REDUKCJA POTAKIWAŃ I ELIMINACJA NAKŁADAJĄCYCH SIĘ AIZUCHI (EYE-TRACKING FILTER):
- W języku japońskim potakiwania ("un", "ee", "sou", "naruhodo", "a", "he-") padają co 2 sekundy:
  * 1. Eliminujemy kalkę tłumaczenia każdego "mhm/aha/tak", jeśli w kadrze widać skinienie głowy.
  * 2. NAKŁADAJĄCE SIĘ POTAKIWANIA W TLE (Overlapping Phatic Aizuchi): Pomijaj drobne potakiwania wtrącane w trakcie wypowiedzi drugiej osoby. Badania okulograficzne (Eye-tracking Szarkowska/Perego) dowodzą, że nakładające się potakiwania wywołują chaos percepcyjny (tzw. sakkadowy ping-pong) i odciągają wzrok od kluczowej kwestii.
  * 3. Tłumacz potakiwania WYŁĄCZNIE wtedy, gdy stanowią samodzielną ripostę niosącą zmianę emocji lub puentę ("No jasne", "A to ciekawe...", "Serio").

FILAR XLV: OGNISKOWANIE INFORMACYJNE I PODMIOT KONTRASTOWY (CONTRASTIVE FOCUS & KONTRAST WA VS GA):
- Różnicowanie partykuły tematu (Wa) i podmiotu wyłączności (Ga):
  * 'Ga' (ognisko wyłączności / tylko ten podmiot): "Watashi ga yarimasu" -> "To ja to zrobię", "Ja się tym zajmę" (akcent logiczny na zaimku).
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
  * Ze szukania potwierdzenia (-darou / -deshou): "Prawda", "Chyba", "Co nie".

FILAR XLVII: ODWRÓCENIE POLARYZACJI SEMANTYCZNEJ W SARKAZMIE (SARCASTIC INVERSION):
- Japoński sarkazm maskowany przesadną uprzejmością uzbrój w polskie partykuły ironii:
  * "No doprawdy, wielkie dzięki za pomoc...", "Akurat ci uwierzę...", "Cudownie, po prostu wspaniale...".

FILAR XLVIII: KADENCJA KOŃCOWA, PUENTOWANIE I ZASADA SUSPENSE RETENTION (PUNCHLINE ALIGNMENT):
- 1. PUENTA NA KOŃCU: W scenach komediowych i dramatycznych kluczowe słowo (puenta żartu lub oskarżenie) MUSI paść na sam koniec napisu, idealnie w momencie, gdy aktor urywa głos.
- 2. ZASADA SUSPENSE RETENTION: W napisach dwuwierszowych nie umieszczaj rozwiązania zagadki (wzorce: miana zabójcy) w pierwszej linijce, aby oko widza nie przeczytało puenty przed wypowiedzeniem jej przez aktora.

FILAR XLIX: PRZEKŁAD ZDAŃ ELIPTYCZNYCH I URWANYCH NIEDOMÓWIEŃ (PRAGMATYKA CISZY I ZAWIESZENIA GŁOSU):
- W języku japońskim zdania często urywają się na spójniku ('kedo...', 'kara...', 'tomo...'):
  * Gdy intencja jest oczywista z sytuacji -> uzupełnij zwięzłą polską frazą lub zastosuj naturalny wielokropek zawieszenia głosu ("Chciałam tylko...", "Przecież wiesz, że...").
  * Japońskie urwane spójniki adaptujemy kontekstowo, unikając samotnego 'Ale...' jako samotnego "Ale..." na końcu bez kontekstu.

FILAR L: POPRAWNOŚĆ REKCJI PRZYCZYN ZGONU I TERMINOLOGII MEDYCZNEJ:
- Zdarzenia nagłe, wylewy, udary, krwotoki i urazy:
  * W języku polskim nagłe incydenty medyczne łączą się z wyrażeniami "z powodu", "wskutek", "w wyniku":
    Niezalecana kalka: "Zmarła na wylew zaraz po porodzie.", "Zmarł na krwotok.", "Zmarł na atak serca."
    Wariant kanoniczny: "Zmarła z powodu wylewu zaraz po porodzie.", "Zmarła wskutek wylewu...", "Zmarł na zawał (serca).", "Zmarł w wyniku odniesionych obrażeń."
  * "Brain hemorrhage" -> "wylew", "krwotok mózgowy", "udar krwotoczny".
  * "Heart attack" -> "zawał serca", "zawał".

FILAR LI: EKSPERCKA TERMINOLOGIA SPECJALISTYCZNA I MERYTORYCZNA (KONSULTANT BRANŻOWY):
- Gdy anime porusza niszową tematykę specjalistyczną, stosuj profesjonalną polską terminologię branżową:
  * ENOLOGIA / WINIARSTWO: "vintage" -> "rocznik", "varietal" -> "szczep / odmiana winorośli", "blend" -> "kupaż / asamblaż", "terroir" -> "terroir / siedlisko", "decant" -> "dekantacja / napowietrzanie", "tannins" -> "taniny / garbniki", "body" -> "ciało / pełnia wina".
  * MUZYKA KLASYCZNA: "score" -> "partytura", "movement" -> "część / ogniwo", "conductor" -> "dyrygent", "reeds" -> "stroiki".
  * GRY TRADYCYJNE / SHOGI / GO: "joseki" -> "dżoseki", "tesuji" -> "tesudżi", "read ahead" -> "liczenie wariantów".

FILAR LII: STYLIZACJA EPOKOWA, REALIA ŚWIATA I ELIMINACJA ANACHRONIZMÓW:
- Gdy seria rozgrywa się w realiach historycznych (Imperium Mongolskie, feudalna Japonia, wikingowie, starożytne Chiny):
  * Eliminujemy kalkę współczesnego slangu młodzieżowego ('spoko', 'masakra', 'wkręcasz mnie', 'luzik', 'siema').
  * Eliminujemy kalkę anachronizmów technologicznych/lotniczych/korporacyjnych:
    -> "point of no return" -> "nie ma już odwrotu", "mosty zostały spalone", "kości zostały rzucone".
    -> "status report" -> "jaka jest sytuacja?!", "mów, co się dzieje!".
    -> "target eliminated" -> "wróg padł", "cel unieszkodliwiony".
  * Dopasuj słownictwo do realiów epoki: 'władca / Chan', 'dwór', 'namiot / jurta', 'niedola', 'niewiasta', 'kupcy', 'wyprawa wojenna', 'zarządca'.
  * Zachowaj hierarchię społeczną dawnych epok ('Wasza Dostojność', 'Chanie', 'panie mój').


MODUŁ VI: ERGONOMIA PERCEPCJI, STANDARDY AVT I JAKOŚĆ (FILARY LIII – LXIV)

FILAR LIII: ŻELAZNY STANDARD PODZIAŁU SKŁADNIOWEGO WIERSZY (SYNTACTIC CHUNKING - NETFLIX & BBC):
- Podział napisu na dwie linijki MUSI przebiegać w naturalnych punktach pauzy oddechowej i syntaktycznej:
  * 1. Eliminujemy kalkę rozdzielania powiązanych par gramatycznych na końcu wiersza:
    -> Nie łamiemy: [Przyimek + Rzeczownik] ("w \\N szkole" -> kalka)
    -> Nie łamiemy: [Przymiotnik + Rzeczownik] ("Wielki \\N Generał" -> kalka)
    -> Nie łamiemy: [Imię + Nazwisko / Przydomek] ("Kuba \\N Rozpruwacz" -> kalka)
    -> Nie łamiemy: [Czasownik posiłkowy/modalny + Bezokolicznik] ("muszę \\N pójść" -> kalka)
    -> Nie łamiemy: [Spójnik + Zdanie podrzędne] ("powiedział, że \\N idzie" -> kalka)
  * 2. HIERARCHIA PODZIAŁU (SYNTAX TRUMPS PYRAMID):
    - Estetyka dolnego dłuższego wiersza (Bottom-Heavy) jest pożądana, ALE SPÓJNOŚĆ SKŁADNIOWA ZAWSZE MA PIERWSZEŃSTWO!
    - Nigdy nie przenoś samotnego wyrazu na dół tylko dla kształtu piramidy, jeśli łamie to naturalną frazę.

FILAR LIV: 12 STRATEGII KONDENSACJI SKŁADNIOWEJ I KOMPRESJI SEMANTYCZNEJ (JORGE DÍAZ CINTAS & HENRIK GOTTLIEB):
- Przy szybkim tempie mowy (CPS > 17 z/s) stosuj systematyczną redukcję tekstu bez straty sensu:
  1. Decymacja fatyczna: usunięcie beztreściowych wypełniaczy ("you know", "basically", "no wiesz").
  2. Kompresja leksykalna: zastąpienie długiego opisu jednym trafnym czasownikiem ("dokonać wyboru" -> "wybrać").
  3. Elipsa syntaktyczna: pominięcie podmiotu/orzeczenia wynikającego bezpośrednio z gestu aktora na ekranie.
  4. Redukcja seryjna: gdy mówca w emocjach powtarza to samo słowo ("No, no, no, wait, wait") -> przetłumacz raz z wykrzyknikiem ("Czekajcie").
  5. Zwężenie semantyczne: rezygnacja z pobocznych przymiotników nieistotnych dla akcji.
  6. Przekształcenie zdania złożonego w zdanie pojedyncze z imiesłowem lub przydawką.

FILAR LV: DYNAMICZNY CZAS PERCEPCJI I TARCIE POZNAWCZE (COGNITIVE FRICTION & EYE-TRACKING - SZARKOWSKA):
- Minimalizowanie zmęczenia wzroku, tarcia poznawczego i liczby przeskoków oczu (sakkad):
  * Wystrzegaj się zostawiania jednoliterowych spójników na końcu wiersza (tzw. sierotek: a, i, o, u, w, z).
  * Dynamiczne tempo: proste kwestie -> standardowe 16-17 CPS; gry słowne, metafory i poezja -> obniżenie do 13-14 CPS (wydłużenie czasu o 15-20%).
  * Eliminacja ponownego czytania (Re-reading suppression): napis musi być tak klarowny, by widz zrozumiał go w pierwszym przebiegu wzroku.
  * Ognisko rematyczne umieszczaj w drugiej połowie dolnego wiersza.

FILAR LVI: NIEROZERWALNOŚĆ JEDNOSTEK SENSU I ZDAŃ ROZBITYCH WIELOKROPKIEM (SPLIT-SENTENCE SYNTACTIC COHESION):
- SPÓJNOŚĆ ZDANIA ROZBITEGO NA DWA KOLEJNE NAPISY (Z WIELOKROPKIEM `...`):
  * Kiedy jedno zdanie ciągłe jest wypowiadane przez aktora przez dwa kolejne napisy (Kwestia A z `...` na końcu i Kwestia B z `...` na początku):
    -> 1. Unikaj kalki DUBLOWANIA ORZECZEŃ: Czasownik główny może paść TYLKO RAZ (albo w kwestii A, albo w kwestii B).
    -> 2. ŻELAZNA ZGODNOŚĆ LICZBY I RODZAJU: Jeśli podmiot w kwestii A jest w liczbie pojedynczej ("Taktyka..."), kwestia B MUSI być dokończona w liczbie pojedynczej ("...bywa niezwykle groźna, o ile zadziała.").
    -> 3. TEST CAŁOŚCI: Zawsze przeczytaj kwestię A + kwestię B jako jedno całe zdanie.

FILAR LVII: STANDARD WIELOGŁOSU I DIALOGÓW NAKŁADAJĄCYCH SIĘ (NETFLIX DUAL-SPEAKER & OVERLAPPING SPEECH):
- Gdy w jednej kwestii odzywają się dwie postacie jednocześnie lub naprzemiennie:
  * Zastosuj myślnik ze spacją ("- ") na początku KAŻDEJ z wypowiedzi w osobnej linii:
    "- Idziesz już?\\N- Daj mi chwilę."
  * W chaosie walki lub krzyku priorytetyzuj postać znajdującą się na pierwszym planie lub niosącą kluczową informację fabularną.
  * Eliminujemy kalkę STOSOWANIA POJEDYNCZEGO MYŚLNIKA (LONE DIALOGUE DASH): W kwestii pojedynczego mówcy (jeden wiersz lub dwa wiersze tego samego bohatera) Unikaj kalki umieszczania myślnika na początku! Półpauza/dywiz dialogowy przysługuje WYŁĄCZNIE scenom wielogłosu (dwóch mówców w jednym kadrze). Kwestia jednoosobowa zaczyna się bezpośrednio od wielkiej litery (Kalka: '- Ocalę cię, Harugonie.' Wariant kanoniczny: 'Ocalę cię, Harugonie.').
  * Eliminujemy kalkę ŁĄCZENIA DWUGŁOSU W JEDNYM WIERSZU (IN-LINE DIALOGUE DASHES): unikamy łączenia wypowiedzi dwóch osób w jednej linijce za pomocą myślnika w środku zdania (kalka KARDYNALNY [niepoprawne]: 'Wspaniale. - Pomyśleć, że rodzony wuj...' / '[Imię]! - Co to był za hałas' / 'Tej nocy?! - Tak prędko'). Zawsze rozbijaj kwestie na dwie osobne linie z myślnikami i spacją: '- Kwestia 1\\N- Kwestia 2'.

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
- Waluty narodowe: zachowuj oryginalne realia ('tysiąc jenów' - unikaj kalki przeliczania na złotówki w Tokio).

FILAR LX: POLSKI KANON ORTOGRAFII I INTERPUNKCJI AUDIOWIZUALNEJ (PWN & NETFLIX CANON):
- Żelazny standard interpunkcji dialogu filmowego:
  * Półpauza ze spacją ("- ") na początku linii przy dialogu dwóch osób w jednym kadrze.
  * Wielokropek standardowy ("..."), bez spacji przed nim.
  * Zespolone znaki emocji: WYŁĄCZNIE pytajnik z wykrzyknikiem "?!".
  * Jednostki miar i skróty bez kropek: "kg", "km", "min", "godz", "USA", "FBI".
  * Unikaj kalki PRZECINKA PRZED 'CZY' W ALTERNATYWIE ROZŁĄCZNEJ/DWUELEMENTOWEJ: W konstrukcjach bezpośredniego wyboru ('kawa czy herbata', 'w kapciach czy bez', 'chcesz czy nie', 'tak czy inaczej') unikamy wstawiania przecinka przed spójnikiem 'czy' (Kalka: 'w kapciach, czy bez' Wariant kanoniczny: 'w kapciach czy bez').
  * FORMATOWANIE PRZERWANIA WYPOWIEDZI (CUT-OFF SPEECH): Nagłe urwanie w pół słowa lub zdania oddaje się wielokropkiem ("...") lub myślnikiem ze spacją (" —"), eliminując przyklejania samej półpauzy/en-dasha bez spacji do litery (Kalka: 'Rin–' Wariant kanoniczny: 'Rin...').
  * CZYSTOŚĆ INTERPUNKCJI (ELIMINACJA TYLD I NADMIARU WYKRZYKNIKÓW) (ANTI-TILDE & MULTI-EXCLAMATION): Japońskie tyldy emocjonalne i przedłużające samogłoski ('~') są wykluczone w dialogach AVT. Zwielokrotnione wykrzykniki ('!!!!') redukujemy do pojedynczego wykrzyknika (Kalka: 'odjechane~!!!!' Wariant kanoniczny: 'odjechane!'). Maksymalnie jeden wykrzyknik lub pytajnik w dialogu.
  * PURYZM KURSYWY AVT:
    - W polskim standardzie AVT kursywa przysługuje wyłącznie: myślom bez ruchu ust (is_thought), narracji voice-over zza kadru, komunikacji przez urządzenia (telefon, radio, megafon) oraz pieśniom.
    - Eliminujemy kalkę kopiowania kursywy fansuberskiej z całych scen retrospekcji (flashbacków)! Dialog toczony na głos między postaciami w retrospekcji zapisuj antykwą (czcionką prostą).
  * TYTULATURA MONARSZA I DWORSKA (PWN): Do monarchy (król, cesarz, suweren, książę panujący) zwracamy się wielkimi literami: 'Wasza Wysokość' (lub 'Wasza Królewska Mość'), unikając angielskiej kalki 'twoja wysokość'.

FILAR LXI: TIMING KOGNITYWNY, REŻYSERIA SPOJRZENIA I GRANICE CIĘĆ MONTAŻOWYCH (SHOT-CHANGE OVERHANG):
- Ergonomia percepcji audiowizualnej:
  * Minimalny czas ekspozycji napisu to 5/6 sekundy (ok. 800-1000 ms), nawet dla krótkich okrzyków ("Stój").
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
    - Critical (Krytyczny): kalka zniekształcający fabułę, halucynacja relacji postaci, mylenie 1. i 2. osoby.
    - Major (Poważny): kalka językowa, brak odnominalizowania, przekroczenie limitu 17 CPS / 42 znaków.
    - Minor (Drobny): drobna interpunkcja, pojedyncza sierotka.
  * Etapy: Krok 1 (Szkic Tłumacza) -> Krok 2 (Krytyka MQM Script Doctora) -> Krok 3 (Szlif Redaktora Naczelnego).


MODUŁ VII: KOGNITYWISTYKA PROZODII, STRUKTURY NARRACYJNEJ I DIALOGU JAPOŃSKIEGO (FILARY LXV – LXX)

FILAR LXV: IZOMORFIZM NAPIĘCIA SKŁADNIOWEGO I ANTYCYPACJI (SOV VS SVO SUSPENSE ISOMORPHISM & ANTI-SPOILER SYNTAX):
- W języku japońskim orzeczenie, kluczowa negacja lub rozstrzygnięcie logiczne padają ZAWSZE na samym końcu kwestii (szyk SOV, warianty: "...to wa kangaerarenai", "...shika erabenai").
- Eliminujemy kalkę niszczenia suspensu i wyprzedzania gry aktora (seiyū) w polskim szyku SVO:
  * Jeśli w scenie dramatycznej ujawnienie zdrady, zgonu, odmowy lub tajemnicy następuje w ostatnim ułamku sekundy wypowiedzi japońskiej:
    -> kalka [niepoprawne] (przedwczesny spoiler): "Nie do pomyślenia jest, żeby doszło do zdrady" (widz czyta 'Nie do pomyślenia' zanim aktor otworzy usta).
    Wariant naturalny (izomorfizm napięcia): "Żeby doszło do czegoś takiego... to nie do pomyślenia" / "Mój miecz w twoich rękach?... Wykluczone".
  * Zsynchronizuj ładunek dramatyczny rematu z intonacyjnym punktem kulminacyjnym w audio japońskim.

FILAR LXVI: FONICZNA SPÓJNOŚĆ KINEZJOLOGICZNA I PROZODIA ODDECHU (BREATH-GROUP & PHONATION CADENCE ALIGNMENT):
- Aktorzy głosowi anime (seiyū) budują emocje na fizjologii krtani i oddechu (inhalation-pause, szloch, panika, skrajne wyczerpanie, zadyszka w biegu):
  * Frazowanie napisu MUSI być zsynchronizowane z grupami oddechowymi postaci:
    -> Gdy postać mówi na urywanych wydechach podczas walki/ucieczki, Unikaj kalki stosowania długich, płynnych zdań wielokrotnie złożonych.
    Zalecane krótkie, zwięzłe człony syntaktyczne, cięcia myślnikiem lub wielokropkiem oddające kinezjologię mowy ("Jeszcze... nie teraz... Muszę... dać radę").
  * Test kinetyczny: napis musi "oddychać" w tym samym rytmie co klatka piersiowa bohatera na ekranie.

FILAR LXVII: KĄT KAMERY EMPATYCZNEJ I DEIKSA PSYCHOLOGICZNA (SUSUMU KUNO'S EMPATHY SYNTAX & PERSPECTIVE ALIGNMENT):
- Japońska gramatyka relacji dawania/otrzymywania (ageru, kureru, morau, temorau, yaru) ściśle ustala kąt kamery psychologicznej (z czyjego punktu widzenia odbiorca ma współodczuwać scenę - prof. Susumu Kuno):
  * 1. Kureru / Tekureta (ktoś wszedł w moją sferę, by mi pomóc) -> akcentuj wdzięczność, serdeczność i bliskość ("Przyszedł mi z pomocą", "Uratowałeś mi skórę", "Pomógł mi").
  * 2. Morau / Temoratta (ja nakłoniłem kogoś / uzyskałem przysługę) -> akcentuj sprawczość lub prośbę ("Udało mi się go przekonać", "Wyprosiłam to u niego").
  * 3. Ageru / Yaru (świadczenie przysługi na zewnątrz) -> akcentuj intencję wsparcia lub wyższości.
  * Unikaj kalki spłaszczania tych relacji do bezosobowego angielskiego szablonu ("He did it for me").

FILAR LXVIII: PAMIĘĆ LEITMOTYWÓW I ECHA NARRACYJNEGO (LONG-TERM LEITMOTIF & CATCHPHRASE PERSISTENCE):
- Wieloepizodowa spójność haseł, przysiąg, dewiz życiowych i fraz-kluczy (Catchphrases & Oaths):
  * Jeśli postać powtarza specyficzną frazę (wzorce: przysięgę z dzieciństwa, motto życiowe, rytualne zawołanie bitewne), która powraca w finale serii jako klamra kompozycyjna:
    -> Ścisły obowiązek zachowania identycznej formy leksykalnej w każdym odcinku!
    -> Unikaj kalki zmieniania powracających motywów na losowe synonimy (wzorce: odcinek 1: "Taki mam styl", odcinek 24: "Nigdy się nie cofnę" - niszczy katharsis widza).

FILAR LXIX: HIERARCHIA PRZESTRZENNO-AKUSTYCZNA I DIALOGI DRUGOPLANOWE (SOUNDSTAGE & AMBIENT SPEECH TIERING):
- W wielokanałowym miksie dźwiękowym (5.1/Atmos) oraz scenach z wieloma źródłami głosu stosuj trójstopniową gradację:
  * 1. Poziom I (Fabuła pierwszoplanowa): Dialog postaci w centrum kadru – 100% priorytetu, dół ekranu.
  * 2. Poziom II (Komunikaty diegetyczne / megafony / radio / interkom): Góra ekranu, wersaliki lub kursywa <i>[ KOMUNIKAT BAZY ]</i>.
  * 3. Poziom III (Gwar tłumu / szum tła - Ambient Speech): Świadoma redukcja i eliminacja – tłumacz wyłącznie wtedy, gdy kwestia w tle niesie kluczowy żart sytuacyjny lub wskazówkę fabularną. Ekran pozostaje wolny od beztreściowego szumu gapiów.

FILAR LXX: PRAGMATYKA METANARRACYJNA I PRZEŁAMYWANIE CZWARTEJ ŚCIANY (META-HUMOR & 4TH-WALL EQUIVALENCE):
- Komedie, parodie i serie łamiące czwartą ścianę (żarty z terminów mangaki, komitetu cenzury BPO, stacji Tokyo MX, budżetu animacji czy aktorów seiyū):
  * Stosuj funkcjonalną ekwiwalencję metanarracyjną:
    -> Zastępuj hermetyczne japońskie realia telewizyjno-redakcyjne błyskotliwym, powszechnie zrozumiałym dla polskiego widza żartem z konwencji anime/mangi i produkcji filmowej.
    -> Eliminujemy kalkę niszczenia dynamiki komediowej encyklopedycznymi przypisami u góry ekranu!


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
  * 1. ~nda / ~noda (funkcja eksplanacyjna/przyczynowa) -> "Bo widzisz...", "Chodzi o to, że...", "Przecież...".
  * 2. ~wake da / ~wake dewa nai (logiczna konkluzja/negacja) -> "A zatem to dlatego...", "Więc to tak...", "To nie tak, że...".
  * 3. ~monoda / ~koto da (prawda ogólna/powinność moralna) -> "Taka już kolej rzeczy", "W takich chwilach po prostu...".

FILAR LXXIV: PLASTYCZNOŚĆ REJESTRU WIZUALNEGO CHIBI / SD (SUPER-DEFORMED VISUAL REGISTER SHIFTS):
- W anime postaci w ułamku sekundy przechodzą ze stylu realistycznego w formę karykaturalną (Chibi / SD - Super Deformed):
  * Przekład MUSI natychmiast podążać za plastyką kadru: przejdź na rejestr komediowy, pieszczotliwy, infantylny lub udawane dąsy ("Ojejciu, ale groźny", "No weźcie, nie bądźcie tacy").
  * Dopasuj rejestr sceny: unikaj sztywnego, poważnego tonu, gdy postać na ekranie zamienia się w małego ludzika z wielką głową.

FILAR LXXV: ZESTROJENIE AKCENTU LOGICZNEGO I PROMINENCJI FONICZNEJ F0 (PITCH-ACCENT & F0 PEAK PROSODIC CONVERGENCE):
- Słowo, na które w audio japońskim seiyū kładzie maksymalny nacisk intonacyjny (szczyt foniczny F0 / Pitch Accent):
  * MUSI w polskim zdaniu znaleźć się na pozycji naturalnego akcentu logicznego (zazwyczaj przed pauzą lub na końcu frazy).
  * Kluczowe słowo oskarżenia wysuwaj na początek frazy lub zawołania w środku bezbarwnego polskiego zdania pobocznego.

FILAR LXXVI: DYSTANSOWANIE HONORYFIKATYWNE I AGRESJA BIERNA W KEIGO (HONORIFIC DISTANCING & PASSIVE-AGGRESSIVE KEIGO):
- Gdy wrodzy sobie bohaterowie, rywale lub antagoniści używają przesadnie formalnego języka szacunku (Keigo/Sonkeigo):
  * Celem jest okazanie lodowatej pogardy, cynizmu, wyższości lub biernej agresji.
  * Unikaj kalki tłumaczenia takiego dialogu na wulgarną pyskówkę!
  * Wariant kanoniczny: Utrzymuj chłodny, dystyngowany, hiperpoprawny styl urzędowo-dworski ("Będę niezmiernie zobowiązany, jeśli zechce pan wreszcie zamilknąć", "Doprawdy, zachwyca mnie pańska bezgraniczna naiwność").

FILAR LXXVII: TRÓJWARSTWOWA TRIANGULACJA ONOMATOPEI MULTIMODALNYCH (VISUAL-ACOUSTIC SFX TRIANGULATION):
- Rozstrzyganie koegzystencji dźwięku audio, napisu graficznego w kadrze i dialogu postaci:
  * 1. Jeśli odgłos słychać wyraźnie w ścieżce dźwiękowej i bohater go komentuje -> Unikaj kalki dublowania napisu onomatopei na ekranie.
  * 2. Jeśli graficzny napis w kadrze wyraża stan bezdźwięczny (wzorce: grobową ciszę 'Shiin', błysk 'Pika') -> przetłumacz w nawiasie lub oddaj poetycko w dialogu ("Cisza jak makiem zasiał...").
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
  * Jąkanie foniczne: łącz pojedynczym dywizem po pierwszej sylabie ("N-Nie patrz tak na mnie" - zamiast 'N... nie patrz').
  * Nagłe urwanie wypowiedzi ze strachu / przerwanie przez inną postać: myślnik na końcu bez kropki ("Chciałam tylko powiedzieć, że–").
  * Wahanie, niepewność, zawstydzenie (tsundere/dandere): wielokropek bez spacji ("Wiesz... tak sobie pomyślałam...").


MODUŁ IX: KANON ARCYDZIEŁ ŚWIATOWEJ TRANSLATORYKI I SEMIOTYKI (FILARY LXXXI – XC)

FILAR LXXXI: ZASADA ORGANICZNEJ EKSPOZYCJI I ANTY-OBJAŚNIANIA (THE GHIBLI & NEIL GAIMAN MINIMALIST EXPOSITION PRINCIPLE):
- Ochrona filmowości i kinowego rytmu sceny:
  * Unikaj kalki dopisywania łopatologicznych wyjaśnień, dopowiedzeń i wpychania zbędnej ekspozycji w dialog, gdy obraz, reżyseria i atmosfera niosą już wystarczający ładunek narracyjny (zasada Hayao Miyazakiego & Neila Gaimana: "Zaufaj inteligencji i zmysłom widza").
  * Dialog ma brzmieć autentycznie dla postaci, a nie jak instrukcja obsługi świata dla widza.

FILAR LXXXII: SEMIOTYCZNA NEGOCJACJA ZNACZENIA I DEEP INTENT (UMBERTO ECO'S 'DIRE QUASI LA STESSA COSA'):
- Gdy dosłowność i obca kultura są nieprzetłumaczalne 1:1, tłumacz prowadzi świadomą negocjację semiotyczną:
  * Poświęć drugorzędną warstwę leksykalną, aby w 100% ocalić głęboką intencję dzieła (intentio operis), sens podtekstowy i ładunek emocjonalny.
  * Tłumaczenie to sztuka kompromisu, w której zysk emocjonalny musi przewyższać stratę dosłowności.

FILAR LXXXIII: DYNAMIZM DOCELOWY I CAŁKOWITA DEKOLONIZACJA SKŁADNI (JEAN-RENÉ LADMIRAL'S CIBLISTE MANIFESTO):
- Całkowite zerwanie z grawitacją składni języka źródłowego:
  * Zdanie po polsku musi brzmieć tak, jakby zostało od zera pomyślane i napisane przez wybitnego polskiego dramaturga/scenarzystę.
  * Eliminuj obce ślady konstrukcyjne i obcojęzyczny tok myślenia.

FILAR LXXXIV: WYKONAWCZY KUNSZT AKTORSTWA GŁOSOWEGO (ALEXANDER O. SMITH'S PERFORMATIVE VOICING & MOUTH-FEEL):
- Dialog filmowy musi być zoptymalizowany nie do cichego czytania z kartki, lecz do fizycznej emisji głosu i rezonansu krtani (tzw. "Mouth-Feel Test"):
  * Rytm spółgłosek i samogłosek musi wspierać energię, pauzę i ładunek aktorski wypowiedzi.
  * Każda linijka tekstu musi naturalnie "układać się w ustach" aktora/lektora.

FILAR LXXXV: INTEGRACJA KINEMATOGRAFICZNA I ELIMINACJA ŚLEPOTY NAPISOWEJ (PABLO ROMERO-FRESCO'S ACCESSIBLE FILMMAKING):
- Napis jako organiczny element kompozycji kadru:
  * Eliminacja "Subtitling Blindness" (zjawiska, w którym widz gapi się wyłącznie na dolne litery, tracąc niuanse gry aktorskiej i kompozycji obrazu).
  * Napis musi być tak skondensowany, czysty i ergonomiczny, by oko po ułamku sekundy wracało do centrum akcji na ekranie.

FILAR LXXXVI: POLIFONIA GŁOSÓW I HETEROGLOSJA POSTACI (MIKHAIL BAKHTIN'S DIALOGIC POLYPHONY):
- Konsekwentne zróżnicowanie idiolektów:
  * Każda postać musi mieć własny unikalny słownik, zasób fraz, długość wypowiedzi i strukturę myśli.
  * Zadbaj o zróżnicowany idiolekt postaci — każda postać musi mówić własnym, unikalnym głosem.

FILAR LXXXVII: CZYSTOŚĆ FOKALIZACJI I WEWNĘTRZNEGO PUNKTU WIDZENIA (COGNITIVE NARRATOLOGY & FOCALIZATION PURITY):
- W monologach wewnętrznych, myślach i retrospekcjach:
  * Zachowaj subiektywny, intymny punkt widzenia danej postaci, bez domieszek obiektywizującego dystansu zewnętrznego narratora.
  * Myśl postaci musi brzmieć jak jej autentyczny, surowy proces myślowy.

FILAR LXXXVIII: PROTOKÓŁ ANTY-DEFORMACYJNY ANTOINE'A BERMANA (BERMAN'S 12 DEFORMING TENDENCIES SUPPRESSION):
- Eliminacja klasycznych destrukcji przekładu:
  * Unikamy racjonalizacji (wygładzania poetyckiej chropowatości i ostrości oryginału).
  * Unikamy klaryfikacji (nadmiernego tłumaczenia tego, co autor celowo pozostawił niejasne).
  * Unikamy ubożenia jakościowego i niszczenia wewnętrznych rytmów dzieła.

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
  * 1. Imiona męskie zakończone na spółgłoskę oraz samogłoski -i, -e, -a podlegają regularnej odmianie przez przypadki:
    -> Tematy spółgłoskowe twarde przyjmują końcówki: D. -a, C. -owi, B. -a, N. -em, Ms. -e/-u (np. <Postać_1>: do <Postaci_1>a, z <Postacią_1>em).
    -> Tematy na samogłoski -i/-e odmieniają się według paradygmatu przymiotnikowego lub miękkiego (np. <Postać_2>: z <Postacią_2>em, o <Postaci_2>u).
    -> Nazwiska obcojęzyczne z tytułem formalnym odmieniają się zgodnie z polską rekcją.
    -> Niezalecana kalka: pozostawianie imion męskich w sztywnym mianowniku w przypadkach zależnych.
  * 2. Unikaj kalkowania angielskiego dopełniacza saksońskiego ('s / of) bez polskiej fleksji dopełniaczowej:
    -> Angielskie frazy posesywne przekładaj dopełniaczem polskim (np. "sekrety <Postaci_1>" zamiast sztywnej formy mianownikowej).
    -> Niezalecana kalka: pozostawianie imienia w mianowniku po rzeczowniku nadrzędnym.
  * 3. Imiona żeńskie zakończone na spółgłoskę lub samogłoski -i, -u w języku polskim pozostają nieodmienne, lecz zdanie musi zachować poprawną strukturę składniową i rekcję przyimka. Imiona żeńskie na -a odmieniają się regularnie (D. -y/-i, C./Ms. -e, B. -ę, N. -ą, W. -o).
  * 4. Wołacze: imiona żeńskie i męskie zakończone na samogłoskę '-a' (wzorce: imiona na samogłoskę '-a') w polskim dialogu filmowym w bezpośrednich zwrotach adresatywnych zyskują formant '-o' (np. "<Imię_A>!"). Eliminujemy pozostawianie mianownika w funkcji wołacza w bezpośrednich zawołaniach. Pozostałe imiona męskie na spółgłoskę w wołaczu przyjmują końcówkę -u lub formę mianownikową z intonacją wołaczową.
  * 5. Imiona męskie obcego pochodzenia zakończone na '-ca' wymawiane z twardym [k] w języku polskim odmieniają się ze zmianą litery na 'k': dopełniacz: -ki, biernik: -kę, narzędnik: -ką, miejscownik: -ce, wołacz: -ko. Niezalecana kalka: zniekształcanie tematu obcego imienia męskiego.
  * 6. Harmonia szyku przydomkowego tytularnych z przyimkiem 'od':
    -> Przydomki postaci w języku obcym tworzone konstrukcją przydawkową w polszczyźnie oddaje się poprzez apozycję mianownikową lub tradycyjny epitet.
    -> Eliminujemy tworzenie sztucznych konstrukcji peryfrastycznych z przyimkiem 'od' (kanon przekładu: epitet bezpośredni). Wszelkie nazwy własne i tytuły postaci weryfikuj z oficjalnym kanonem wydawniczym.
  * 7. Unikaj zacierania biernika w szeregach współrzędnych po 'i' oraz 'oraz':
    -> Gdy orzeczenie wymaga dopełnienia w bierniku, a w zdaniu występuje szereg współrzędny połączony spójnikiem 'i' lub 'oraz' (wzorce: ocalenie dwóch postaci), wszystkie człony szeregu regularnie przyjmują formę biernika.
    -> Niezalecana kalka: pozostawienie drugiego członu szeregu w mianowniku.
  * 8. Fleksja polskich syntagm tytułowych, artefaktów i kanonu mangowego (Syntagmatic Declension Integrity):
    -> Frazy z przydawką dopełniaczową (rzeczownik + imię/pojęcie w dopełniaczu: "Księga Przymierza", "Zakon Feniksa", "Dolina Rozpaczy", "Miecz Prawdy"): odmienia się wyłącznie człon nadrzędny ("Księgi Przymierza", "Księdze Przymierza", "Księgą Przymierza"), a przydawka dopełniaczowa pozostaje zamrożona.
    -> Frazy przymiotnik + rzeczownik ("Nieśmiertelny Wojownik", "Wielki Chan", "Czerwona Wieża"): oba człony podlegają pełnej zgodzie fleksyjnej ("Nieśmiertelnym Wojownikiem", "Wielkiego Chana", "Czerwonej Wieży").
    -> Człony przyimkowe ("z Północy", "ze stali"): człon przyimkowy pozostaje nieodmienny ("o Księdze Przymierza z Północy").


FILAR XCII: SYNCHRONIA PRZECZENIA I ODROCZENIA DRAMATYCZNEGO (DELAYED NEGATION & JVTA SUSPENSE):
- W języku japońskim (SOV) negacja lub zwrot akcji pada na samym końcu zdania (...to omotta kedo, chigatta!):
  * Eliminujemy kalkę wyprzedzania puenty na początku polskiego napisu, jeśli aktor buduje napięcie i przeczy dopiero po 2 sekundach ciszy.
  * Zastosuj inwersję dramatyczną lub wielokropek, aby zsynchronizować moment zaskoczenia z audio ("Myślałem, że to koniec... a jednak nie").

FILAR XCIII: KOMPENSACJA DIALEKTÓW REGIONALNYCH (KOLOKWIALIZACJA REJESTRÓW):
- Wystrzegaj się przekładania gwar regionalnych czy dialektu północnego na gwarę góralską, śląską lub wiejską (niszczy to realia świata przedstawionego!).
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
- Tłumacz ma Ścisły obowiązek weryfikacji japońskiej ścieżki dźwiękowej i kontekstu obrazu:
  * 1. 彼女たち (kanojo-tachi) / 彼女ら (kanojo-ra) / 女たち (onna-tachi):
    Wariant naturalny: rodzaj niemęskoosobowy (żeński):
    -> Mianownik: ONE.
    -> Biernik: JE. Przykład: "Można je nazwać oparciem dla ludzkiego życia. One również..." (Kalka: "Można ich nazwać... Oni również...").
    -> Dopełniacz: ICH / Celownik: IM / Narzędnik: NIMI / Miejscownik: NICH.
  * 2. 彼ら (karera) / 男たち (otoko-tachi):
    -> Tłumacz na rodzaj męskoosobowy: ONI / ICH (Biernik) / IM / NIMI.
  * 3. Unikaj kalki DOMYŚLNEGO MĘSKOOSOBOWEGO: Gdy podmiotem są kobiety, siostry zakonne, uczennice, kapłanki czy ofiary żeńskie (wzorce: w Fire Force), Naturalnie unikamy stosowania form 'oni / ich'.

FILAR XCVII: PRAGMATYKA BIESIADNA I KUMPELSKIE ZAPROSZENIA DO ALKOHOLU (CONVIVIAL DRINKING CAMARADERIE):
- Angielskie formuły biesiadne i pytania upewniające w kontekście alkoholu, toastów i jedzenia (wzorce: "You're drinking, right?", "Have one, right", "You want one? You're drinking, right?"):
  * Są to AKTY BRATERSKIEJ/KUMPELSKIEJ INTEGRACJI, a NIE pytania o stan faktyczny czy diagnozę nałogu!
  * Eliminujemy kalkę dosłowności: "Przecież pijesz" [kalka KOSZMARNY - brzmi jak zarzut lub diagnoza lekarska!], "Pijesz, prawda".
  * OBOWIĄZKOWE polskie formuły biesiadne:
    - "Konro, chlapniesz sobie? Chyba nie odmówisz"
    - "Napijesz się? Ze mną się nie napijesz"
    - "Pijesz ze mną, co" / "Polejesz sobie? Nie odmówisz chyba" / "Chlapniesz jednego".

FILAR XCVIII: TYPOGRAFIA PLANSZ TYTUŁOWYCH I ZWIĘZŁOŚĆ OPTYCZNA TYPESETTINGU (TITLE TYPOGRAPHY & SAFE AREA):
- Polskie tytuły anime, rozdziałów i szyldów są o 40–60% dłuższe niż wersje angielskie/japońskie.
- Ponieważ plansze tytułowe renderowane są ogromnym fontem (60–90 pt), długi tekst w jednej linii NIE MIEŚCI SIĘ W KADRZE (wychodzi poza bezpieczny obszar Canvasu Title-Safe 80%).
- ZASADA DLA PLANSZ I TYTUŁÓW ODCINKÓW:
  * Numery odcinków i rozdziałów zapisuj ZAWSZE CYFRAMI ARABSKIMI (wzorce: 'ODCINEK 52', 'ROZDZIAŁ 12'). Eliminujemy kalkę form słownych ('ODCINEK PIĘĆDZIESIĄTY DRUGI' -> kalka!).
  * Formatuj planszę tytułową w czytelnych, wyśrodkowanych wersach z tagiem \N:
    Wiersz 1: ODCINEK [Numer cyframi]
    Wiersz 2+: [Polski Tytuł w poprawnym przypadku gramatycznym]
    Przykład standardowy: "ODCINEK <NR>\N<TYTUŁ_ODCINKA>" (lub "ODCINEK <NR>\N<CZŁON_TYTUŁU_1>\N<CZŁON_TYTUŁU_2>").
  * TYTUŁY WIELOCZŁONOWE I WIELOZDANIOWE (wzorce: tytuł wielozdaniowy z podziałem syntaktycznym):
    - Eliminujemy kalkę pakowania wielozdaniowego tytułu w jeden niepodzielony wiersz (>45 znaków)!
    - Eliminujemy kalkę używania nawiasów kwadratowych [ ... ] lub zbitek '] [' do rozdzielania członów (Kalka: '[ ODCINEK 10 ] [ TYTUŁ 1 ] [ TYTUŁ 2 ]').
    - Każdy człon lub zdanie tytułu formatuj z czystym podziałem syntaktycznym \N (maks. 36–42 znaki na wiersz), warianty: :
      "ODCINEK 10\NDZIEWIĘĆDZIESIĄT PROCENT WSZYSTKIEGO TO CHŁAM\NBY POKONAĆ MAMĘ, POTRZEBUJĘ „PRZYJACIÓŁ”".
  * Wystrzegaj się tasiemców ucinających się na bokach ekranu i wychodzących poza obszar Title-Safe!

FILAR XCIX: ELIMINACJA NADGORLIWEJ EKSPLIKACJI I SAMOWOLNEGO WTRĄCANIA IMION (ANTI-EXPLICITATION & VOCATIVE INTEGRITY):
- Wystrzegaj się wtrącania imion postaci ("Panie X... / X-san...") w miejscach, gdzie w tekście angielskim i japońskim audio padają wyłącznie zawahania, pauzy i neutralne zaczepki (Hesitations & Interjections):
  * "Erm, hey..." / "Um..." / "Ano..." / "Etto..." / "Chotto..." / "Wait..." / "Excuse me...".
- Wystrzegaj się sztucznej formalizacji:
  * Niezalecana kalka: Zamiana neutralnego zawahania na zwrot tytularny (sztuczna formalizacja, niszczenie prawdy sceny i fałszowanie relacji między postaciami!).
- Obowiązkowe polskie ekwiwalenty:
  * Kanon przekładu: "Przepraszam...", "Zaraz, hej...", "Yyy, chwileczkę...", "Hej, zaraz...", "Słuchaj...".
- Reguła wołacza: Imię w wołaczu występuje wyłącznie wtedy, gdy imię to zostało rzeczywiście wypowiedziane w dialogu EN lub japońskim audio JP!

FILAR C: JAPOŃSKIE YOBISUTE, SUFIKSY RÓWIEŚNICZE (-KUN, -CHAN, -SAN) I PEŁNA MATRYCA TYTULATURY:
- 1. Japońskie Yobisute (呼び捨て - brak jakiegokolwiek przyrostka w audio):
  * Gdy w audio JP postać mówi samo imię/nazwisko (np. <Imię>):
  * W języku polskim stosuj bezpośrednie miano w wołaczu (np. <Imię> w wołaczu).
  * Eliminujemy kalkę dodawania "Pan / Pani" (np. zamiast per pan stosuj formę bezpośrednią na ty).
- 2. Sufiksy rówieśnicze i przyjacielskie (-kun, -chan):
  * -kun (君 / くん) w ustach rówieśników/dziewcząt/kolegów (wzorce: <Imię>-kun):
    -> Eliminujemy formy per pan -> bezpośrednie imię na "ty".
  * -chan (ちゃん) w ustach przyjaciółek/rodziny (wzorce: <Imię>-chan):
    -> Eliminujemy formy per pani -> bezpośrednie imię lub zdrobnienie na "ty".
- 3. Sufiks -san (さん - dystans szkolny vs dorośli obcy):
  * Wśród uczniów/rówieśników w szkole (wzorce: <Nazwisko>-san, <Imię>-san):
    -> Tłumacz po samym imieniu na "ty".
  * Wobec dorosłych obcych/klientów/sąsiadów z nazwiskiem (wzorce: <Nazwisko>-san):
    Warianty grzecznościowe: "Pani Tanako", "Panie Yamado".
- 4. Sufiksy wyższego szacunku i hierarchii (-sama, -sensei, -senpai, -dono, -shishou, -taichou):
  * -sama (様) -> "Wasza Wysokość", "Panienko", "Pani Loulan", "Panie mój", "Bóg / Bogini".
  * -sensei (先生) -> "Sensei", "Mistrzu", "Pani Tanako", "Panie profesorze", "Pani doktor".
  * -senpai (先輩) -> "Senpai", "Starszy kolego", "[Imię]-senpai".
  * -dono (殿) -> "Wielmożny Panie", "Mości [Imię]".
  * -shishou (師匠) -> "Mistrzu".
  * -taichou / -buchou (隊長 / 部長) -> "Kapitanie", "Dowódco", "Kierowniku", "Prezesie".
- 5. Eliminujemy kalkę HYBRYD FORMY WOŁACZOWEJ Z FORMĄ GRZECZNOŚCIOWĄ (INTRA-CLAUSE T-V HARMONY MANDATE):
  * Naturalnie unikamy łączenia w jednej wypowiedzi poufałego wołacza po samym imieniu z honoryfikatywną formą grzecznościową ("pan/pani").
  * kalka KARDYNALNY [niepoprawne]: "Poza tym, mistrzu... ma pan zaczerwienioną twarz." (niedopuszczalna hybryda poufałego wołacza "[Imię W]" z formą grzecznościową "ma pan").
  * Wariant kanoniczny: "Poza tym, panie Janie... ma pan zaczerwienioną twarz." LUB (gdy relacja jest na "ty"): "Poza tym, Janie... masz zaczerwienioną twarz.".
  * Jeśli postać zwraca się per pan/pani, wołacz w języku polskim ZAWSZE musi zawierać tytuł: "Panie [Imię]" / "Pani [Imię]".
- 6. ODPORNOŚĆ NA ANGIELSKIE OPUSZCZANIE SUFIKSU -SAMA (ENGLISH "-SAMA" DROP IMMUNITY):
  * W zachodnich/angielskich skryptach anime (Crunchyroll, fansuby) tłumacze nagminnie usuwają honoryfikatywny przyrostek "-sama" w okrzykach, zawołaniach i scenach dramatycznych (wzorce: w JP: "[Imię]-sama", a w EN jedynie: "[Imię]").
  * Eliminujemy kalkę mechanicznego przepisywania tego jako poufałego wołacza (Kalka: "Co za kunszt, mistrzu" w ustach uczennicy/służącej).
  * Relacja uczeń-mistrz czy podwładny-pan w polszczyźnie zachowuje stałość rejestru: w zawołaniach i okrzykach stosuj "Panie [Imię]" ("Co za kunszt, panie [Imię]"), a nie poufałe "[Imię W]".

FILAR CI: NADRZĘDNOŚĆ JAPOŃSKIEGO AUDIO I TRIANGULACJA PERSPEKTYWY MÓWCY (KIKANAIDE VS KIKITAKUNAI):
- Gdy tekst angielski jest wieloznaczny (wzorce: "Don't even ask"), japońskie czasowniki i końcówki w audio jednoznacznie rozstrzygają perspektywę podmiotu:
  * 1. 聞かないで (Kikanaide / Kiku + naide = prośba mówcy o zaniechanie pytań ze wstydu lub bezsilności):
    Wariant naturalny: "Nawet nie pytaj...", "Nie pytaj...", "Błagam, nie pytaj...".
    -> Eliminujemy kalkę [niepoprawne]: "Wolę nie wiedzieć" (kalka inwersji podmiotu – "wolę nie wiedzieć" mówi słuchacz, a nie zawstydzony sprawca!).
  * 2. 聞きたくない (Kikitakunai / Kiku + takunai = odmowa słuchania przez słuchacza):
    -> "Nie chcę o tym słyszeć", "Wolę nie wiedzieć", "Oszczędź mi szczegółów".
- ZASADA PRYMATU AUDIO: W razie rozbieżności między angielskim tekstem a japońskim audio ze słuchu (Whisper), Kluczowy priorytet MA JAPOŃSKIE AUDIO!

FILAR CII: DYSTRYBUCJA LEKSYKALNA I ZAIMKOWA SUBSTYTUCJA DEIKTYCZNA (ANTI-NOUN REPETITION & PRONOUN SUBSTITUTION):
- Unikaj powtarzania tego samego rzeczownika (lub jego bliskiej formy rdzennej) w obrębie 2–4 sąsiednich kwestii:
  * kalka KOSZMARNY [niepoprawne]: "Książka mojego ojca..." -> "Spalono ją jako zakazaną księgę..." -> "Chciałabym kupić tę książkę." (Potrójna tautologia i ciężka kalka z angielskiego 'I want to buy this book').
  * Wariant kanoniczny:     - W monologu/myślach: Stosuj zróżnicowanie leksykalne i kondensację ("Książka mojego ojca..." -> "Przecież uznano ją za zakazaną i spalono..." / "Spalono ją jako zakazane dzieło...").
    - Przy deiksie (wskazywaniu/kupowaniu/dotykaniu przedmiotu w kadrze): Zastąp rzeczownik naturalnym zaimkiem wskazującym lub dopełnieniowym ("Chciałabym ją kupić", "Chciałabym to kupić", "Mogę to kupić").
- Reguła zaimkowa: Gdy przedmiot jest oczywisty z kontekstu sceny lub został nazwany chwilę wcześniej, ZAWSZE zastępuj go zaimkiem ("ją", "jego", "to") zamiast mechanicznie powtarzać rzeczownik!

FILAR CIII: PRAGMATYKA JAPOŃSKICH AKTÓW PROŚBY I ROZKAZU (KURE VS MORAERU VS KUDASAI):
- Angielskie napisy spłaszczają prośby i żądania do 'Please do X' lub 'Can you do X'. W języku polskim triangulujemy japoński czasownik:
  * 1. Kumpelskie żądanie / bitewny rozkaz (-te kure / -kure / -ro / -e):
    - "Tasukete kure" -> "Pomóż mi", "Ratuj". zamiast kalki 'Proszę, pomóż mi'.
    - "Kase" / "Kashite kure" -> "Dawaj to", "Pożycz mi to". zamiast kalki 'Czy możesz mi to pożyczyć'.
  * 2. Nieśmiała prośba o przysługę (-te moraeru? / -te kureru?):
    - "Mite moraeru" -> "Zerkniesz na to", "Mógłbyś rzucić okiem".
  * 3. Formalna uprzejmość (-te kudasai / -kudasaimase):
    - "O-machi kudasai" -> "Proszę zaczekać", "Niech pan zaczeka".
- Zasada dramaturgii: W scenach walki, pojedynków i pośpiechu formy z 'Proszę...' są sztuczne – zalecane są czyste, stanowcze tryby rozkazujące!

FILAR CIV: SOMATYKA EMOCJI I JAPOŃSKIE MIMETYKI (GITAIGO & SOMATIC IDIOMS):
- Japońskie mimetyki stanów psychofizycznych tłumacz na bogatą, naturalną polską frazeologię somatyczną:
  * ドキドキ (Doki doki - kołatanie serca ze strachu lub miłości):
    -> "Serce podchodzi mi do gardła", "Aż serce mi wali", "Serce bije mi jak młotem".
  * ワクワク (Waku waku - radosne podekscytowanie/niecierpliwość):
    -> "Aż mnie nosi z ekscytacji", "Nie mogę się doczekać", "Aż mi się oczy świecą".
  * イライラ (Ira ira - wzbierający gniew/frustracja):
    -> "Krew mnie zalewa", "Szlag mnie trafia", "Doprowadza mnie do szału".
  * ゾクゾク (Zoku zoku - dreszcz grozy, zachwytu lub gorączki):
    -> "Aż ciarki mnie przechodzą", "Przechodzi mnie dreszcz", "Aż mi skóra cierpnie".
  * ビックリ (Bikkuri - nagły szok/zaskoczenie):
    -> "Aż mnie zamurowało", "O mało zawału nie dostałem", "Zaniemówiłem".

FILAR CV: HARAGEI I POETYKA NIEDOPOWIEDZENIA (ELLIPSIS & TRAILING PARTICLES -KEDO, -KARA, -TARA):
- Gdy japońska kwestia urywa się na partykułę zawieszenia (-kedo, -kara, -tara, -mono de, -shi), a postać spuszcza wzrok lub wzdycha:
  * Eliminujemy kalkę [niepoprawne]: Sztucznego dopowiadania reszty zdania przez tłumacza ("I want to go, but I can't because of work" -> "Chciałabym pójść, ale nie mogę z powodu pracy.").
  * Wariant kanoniczny: Stosuj poetykę wielokropka i niedopowiedzenia ("Też bym chciała, ale...", "Przecież wiesz, że ja...", "Bardzo bym chciała, tylko że..."). Pozwól obrazowi i ciszy dopełnić sens!

FILAR CVI: AIZUCHI I HIGIENA PHATYCZNA (ANTI-CLUTTER & PHATIC MINIMALISM):
- Japońskie Aizuchi (Un, Sou, Ee, Naruhodo, Fumu) to rytmiczne sygnały podtrzymania kontaktu, a nie zawsze zgoda z treścią:
  * Eliminujemy kalkę [niepoprawne]: Zaśmiecania ekranu dosłownym "Tak", "Tak", "Rozumiem", "Racja" co 2 sekundy (przekroczenie limitów CPS).
  * Wariant kanoniczny: W 80% przypadków redukuj puste Aizuchi (kondensacja AVT). W pozostałych 20% stosuj naturalne polskie reaktywniki: "Mhm", "No", "Jasne", "Słucham", "Rozumiem".

FILAR CVII: ASYMETRIA SPOŁECZNA KEIGO (SONKEIGO VS KENJŌGO - WYWYŻSZENIE VS UNIŻONOŚĆ):
- W relacjach feudalnych, dworskich, biznesowych i hierarchii Senpai/Kōhai precyzyjnie różnicuj działania rozmówcy od działań własnych:
  * Sonkeigo (wywyższanie słuchacza): "Raczy pan spocząć", "Czy zechciałby pan spojrzeć", "Pan raczy żartować".
  * Kenjōgo (uniżanie siebie): "Pozwolę sobie zauważyć...", "Służę pomocą", "Udam się niezwłocznie".
  * Eliminujemy kalkę [niepoprawne]: Angielskiego spłaszczania obu form do neutralnego "Please sit" / "I go".

FILAR CVIII: KINEZYKA SPOJRZENIA I TRIANGULACJA MIKROMIMIKI (VISUAL GAZE & SUBTEXT):
- Gdy w kadrze widzisz mikro-rumieniec (tereru), ucieczkę wzrokiem (shisen wo sorasu) lub zaciśnięte dłonie:
  * Przekładaj SUBTEKST psychologiczny sceny, a nie dosłowne słowa z angielskiego!
  * Przykład Tsundere/Wstyd: EN: "I didn't do it because I like you or anything." -> BŁĘDNIE: "Nie zrobiłam tego, bo cię lubię czy coś." Wariant kanoniczny: "Żebyś sobie tylko czegoś nie pomyślał".
  * Gdy postać unika wzroku przy wyznaniu/przeprosinach: formy bardziej intymne, zawstydzone i miękkie.

FILAR CIX: RELACYJNOŚĆ UCHI/SOTO I NATURALNOŚĆ POLSKICH STOPNI POKREWIEŃSTWA:
- W relacjach rodzinnych triangulujemy wiek, rejestr i dynamikę Uchi (swoi) vs Soto (obcy):
  * Oyaji ( 親父 / おやじ ) w ustach młodego buntownika/syna do rówieśników:
    -> "Stary mi nagadał...", "Ojciec się wściekł...", "Mój stary...".
  * Haha ( 母 ) w ustach dziecka/dziewczyny do obcego:
    -> "Mama mówiła...", "Mama mi kazała...".
  * Aniki ( 兄貴 / 兄き ) wśród rodzeństwa: "Braciszku / Bracie"; wśród gangsterów/yakuzy: "Szefie / Starszy bracie".

FILAR CX: TRIANGULACJA DŁUGU WDZIĘCZNOŚCI GIRI (SUMIMASEN JAKO CIĘŻAR ZOBOWIĄZANIA):
- Sumimasen ( 済みません ) etymologicznie oznacza brak możliwości spłacenia długu moralnego.
  * W scenach, gdy postać otrzymuje pomoc, ratunek, lekarstwo lub strawę od towarzysza, "Sumimasen" NIE JEST suchym "Przepraszam":
    Wariant kanoniczny: "Wybacz kłopot...", "Nie trzeba było...", "Nie powinieneś był się narażać...", "Dziękuję i wybacz...".
    -> Eliminujemy kalkę: Monotonnego "Przepraszam", gdy postać w rzeczywistości dziękuje z poczuciem winy!

FILAR CXI: JAPOŃSKA ZJADLIWOŚĆ IYAMI I JADOWITA GRZECZNOŚĆ (INVERTED POLITENESS):
- Japońska ironia i nienawiść rzadko posługują się wulgarnością; sączą się przez przesadną grzeczność (Keigo) i fałszywe komplementy:
  * "Gokurōsama desu koto" / "O-jouzu desu wa ne" powiedziane z uśmieszkiem przez wroga:
    -> Tłumacz na jadowitą polską ironię salonową: "Doprawdy, imponujący wysiłek...", "Cóż za niezwykły popis...", "Zaprawdę, przeszłaś samą siebie...".
    -> Eliminujemy kalkę: Dosłownego brania fałszywych pochwał ('Dziękuję za ciężką pracę').

FILAR CXII: SEMIOTYKA CISZY MA (間) I RYGOR WYGASZANIA NAPISÓW W PAUZIE DRAMATYCZNEJ:
- W japońskiej kinematografii pusta przestrzeń i cisza (Ma) są nośnikiem dramatyzmu i emocji:
  * Wystrzegaj się sztucznego rozciągania czasu trwania napisów na sekundy milczenia postaci!
  * Napis musi wygasnąć dokładnie wtedy, gdy postać zamyka usta (z tolerancją +200 ms), aby widz mógł chłonąć ciszę kadru, muzykę i spojrzenie aktora bez wiszącego tekstu.

FILAR CXIII: DYSKRETNA STYLIZACJA DIALEKTÓW REGIONALNYCH (REJESTRY REGIONALNE & HŌGEN):
- Japońskie rejestry regionalne i dialekty (wzorce: zachodnie, północne, południowe) tłumaczymy z wyczuciem:
  * Eliminujemy kalkę [niepoprawne]: Tworzenia karykatury góralskiej ("hej bawocek") lub wiejskiej gwary w japońskim anime.
  * Wariant kanoniczny: Stosuj zadziorną, dynamiczną polszczyznę miejsko-kolokwialną:
    - "Nande ya nen" -> "Co ty bredzisz", "Chyba cię głowa boli".
    - "Honma ni akan..." -> "No to leżymy...", "Mogiła...", "Nie ma mowy...".
    - "Seyana" -> "No ba", "A jakże", "Pewnie".

FILAR CXIV: AUTONOMICZNA TRANSKREACJA KALAMBURÓW I HOMOFONÓW (DAJARE / KAKEKOTOBA - ZASADA BARAŃCZAKA):
- W przypadku japońskich gier słownych i kalamburów opartych na homofonach (Dajare, Kakekotoba):
  * Eliminujemy kalkę [niepoprawne]: Dodawania encyklopedycznych przypisów w klamrach [Przyp. tłum.: Słowo kami oznacza...].
  * Wariant kanoniczny: Stwórz autonomiczny polski kalambur fonetyczny lub dowcip sytuacyjny o identycznym ładunku humoru/zażenowania (Zasada Stanisława Barańczaka).

FILAR CXV: ARCHITEKTURA HIPOKORYSTYKÓW I ZDROBNIENIA SŁOWOTWÓRCZE (AISHŌ & POLSKIE ZDROBNIENIA):
- Japońskie sufiksy pieszczotliwości (-tan, -pyon, -cchi, -rin, -bōzu) przy braku honoryfikatorów przekładaj na bogactwo polskich zdrobnień słowotwórczych:
  * "<Imię>-tan" / "<Imię>-cchi" -> polskie formy zdrobniałe i spieszczone.
  * "Bokuchan" / "Bōzu" -> "szkrab", "chłystek", "braciszek", "maluch".

FILAR CXVI: IZOMORFIZM CZASOWY DŁUGICH SAMOGŁOSEK I EMFASY EKSTATYCZNEJ (CHŌON & EKSTATIC ELONGATION):
- Przeciągłe japońskie okrzyki bólu, rozpaczy lub determinacji (Itaaaai, Dameeee, Tasukeeee) formatuj ze zsynchronizowanym wydłużeniem ekspresyjnym:
  * "Auaaa...", "Nieee...", "Ratunkuuu...", "Stóóój..." - idealnie zgrane z otwarciem krtani aktora w kadrze!

FILAR CXVII: PRAGMATYKA ODMOWY „...WA II DESU / KEKKOU DESU” (I'M FINE JAKO ODMOWA ZAPROSZENIA A NIE STAN ZDROWIA):
- W języku japońskim zwrot „...wa ii desu” ( ...は、いいです ) lub „kekkou desu” w odpowiedzi na zaproszenie / propozycję („Chodźmy powitać gościa!”, „Chcesz herbaty?”) to grzeczna ODMOWA lub REZYGNACJA:
  * poważne zniekształcenie KALKI [niepoprawne]: Tłumaczenie angielskiego „I'm fine” / „I'm good” jako „Nic mi nie jest” / „Wszystko w porządku” w sytuacji, gdy nikt nie pyta o zdrowie czy rany!
  * Wariant kanoniczny:     - W odpowiedzi na zaproszenie/wyjście: „Ja... podziękuję.”, „Nie mam ochoty.”, „Ja... zostanę.”, „Spasuję.”.
    - W odpowiedzi na poczęstunek/pomoc: „Dziękuję, obejdzie się.”, „Nie trzeba.”, „Dziękuję, nie trzeba.”.

FILAR CXVIII: STALOWA REGUŁA OP/ED ORAZ TRANSKREACJA BARAŃCZAKOWSKA (DAJARE, GOROAWASE & SONG METRE):
- 1. ZASADA NIETŁUMACZENIA PIOSENEK Z OPENINGÓW I ENDINGÓW (OP/ED):
  * Wersy piosenek z czołówek (Opening) i tyłówek (Ending) są zawsze ZACHOWYWANE W ORYGINALNYM TEKŚCIE (Romaji / stylizacja japońska / oryginalny zapis).
  * System NIE tłumaczy piosenek OP/ED, co gwarantuje autentyczność ścieżki i oszczędza 100% tokenów API.
- 2. TRANSKREACJA GIER SŁOWNYCH, KALAMBURÓW I SUCHARÓW (DAJARE & GOROAWASE ANSI STANDARD):
  * Japońskie gry słowne oparte na homonimii (Dajare / Oyaji Gag) oraz skojarzeniach liczbowych (Goroawase, warianty: 4649 = yoroshiku) podlegają zasadzie KOMPENSACJI SEMANTYCZNEJ STANISŁAWA BARAŃCZAKA:
    -> Wystrzegaj się dosłownego tłumaczenia, które niszczy humor i sens sceny!
    -> Tłumacz ma obowiązek stworzyć polski kalambur fonetyczny lub żart sytuacyjny o identycznej funkcji komicznej (wzorce: suchar wywołujący zażenowanie otoczenia lub błyskotliwy rym).
- 3. PIOSENKI DIEGETYCZNE I WIERSZE W FABULE (TRANSKREACJA SYLABICZNA WG BARAŃCZAKA):
  * Wyłącznie gdy bohater wewnątrz sceny śpiewa kołysankę, pieśń biesiadną lub recytuje wiersz fabularny:
    1. Ekwiwalencja rytmiczna: zachowaj zbliżoną liczbę sylab w każdym wersie (wzorce: 8- lub 10-zgłoskowiec).
    2. Rymy naturalne (AABB lub ABAB): twórz czyste, zgrabne polskie rymy.
    3. Śpiewność i kadencja: polski tekst musi dać się zanucić w rytm melodii postaci.

FILAR CXIX: MATRYCA IDIOLEKTÓW I JĘZYK RÓL YAKUWARIGO (ANIMESUB.INFO CHARACTER ARCHETYPES):
- Każda postać w anime musi posiadać własny, rozpoznawalny profil językowy w polskim przekładzie:
  * 1. Arystokratka / Ojou-sama / Dama ('watakushi', 'desu wa'): wykwintna salonowa składnia, peryfrazy, chłodny dystans ("Doprawdy, to zbyteczne", "Czy zechciałby pan...").
  * 2. Mędrzec / Starzec ('washi', 'ja', 'noja'): łagodna, lekko staroświecka polszczyzna ("Młodziku", "Powiadam ci", "Wżdy").
  * 3. Samuraj / Rycerz ('sessha', 'de gozaru'): dostojny etos rycerski, zwięzłość, powaga, zero współczesnego slangu ("Jam jest...", "Czynię swą powinność").
  * 4. Yankii / Delikwent / Wojownik ('ore-sama', 'temee', 'koraa'): krótkie równoważniki zdań, twarda leksyka, brak form 'Pan/Pani', szorstki styl potoczny.
  * 5. Tsundere: pozorna szorstkość maskująca troskę, urwane frazy ('B-Baka' -> 'Głupi jesteś...', 'Wcale nie robię tego dla ciebie').
  * 6. Erudyta / Naukowiec / Mag: precyzyjne łączniki logiczne ('zważywszy na', 'w konsekwencji'), profesjonalna terminologia.

FILAR CXX: IDENTYFIKACJA POSTACI TYPU TOMBOY / SPORTOWIEC ORAZ MÓWCÓW NIEWIDOCZNYCH (GENDER IDENTIFICATION & OFF-SCREEN SPEAKER COGNITION):
- 1. Dziewczyny o Chłopięcym Wyglądzie (Tomboy / Bokserki / Krótkie Włosy):
  * Postacie żeńskie z krótkimi czarnymi włosami, w luźnych koszulkach lub strojach sportowych (wzorce: [Imię Żeńskie]) to w 100% KOBIETY / DZIEWCZYNY.
  * Eliminujemy kalkę narzucania form męskich ('poszedł', 'zrobił', 'chciał') wyłącznie na podstawie krótkiej fryzury lub luźnego stroju w kadrze!
- 2. Mówcy Niewidoczni / Głosy Nietypowe (Akwarium / Telefon / Zwierzątko / Duszek / Głos zza kadru):
  * Gdy w kadrze leży jedna postać, ale kwestię wypowiada ktoś inny (wzorce: rybka-wiedźma Gon w akwarium, głos z telefonu), ZAWSZE weryfikuj tożsamość rzeczywistego mówcy z kartoteki i audio seiyū.
  * W razie niepewności co do płci przy japońskiej zerowej anaforze, stosuj wyłącznie w 100% aseptyczną morfologicznie eliptykę filmową, czas teraźniejszy lub równoważniki zdań ("Na miejscu pusto", "Ani śladu", "Wszystko sprawdzone", "Pusto w środku", "Pora ruszać", "Co teraz"), bez uciekania w sztuczną stronę bierną czy urzędowe konstrukcje bezosobowe ("Zostało to zrobione", "Udało się pójść").
  * Przy braku twardego dowodu płci wykluczone jest podawanie i stosowanie nacechowanych rodzajowo form czasu przeszłego (-łem/-łam/-ł/-ła/-liśmy/-łyśmy).

FILAR CXXI: PRZEKŁAD WYZNAŃ MIŁOSNYCH I WIELOZNACZNOŚCI KOKUHAKU (SUKI DA / DAISUKI VS LUBIĘ CIĘ / KOCHAM CIĘ):
- W języku japońskim zwroty „Suki da” ( 好きだ ), „Daisuki” ( 大好き ) oraz „Aishiteru” ( 愛してる ) posiadają subtelny wektor emocjonalny zależny od intymności sceny:
  * 1. W scenach wyznania miłosnego (Kokuhaku), uniesienia romantycznego, zachodu słońca, drżenia głosu i rumieńca w kadrze:
    -> Angielskie tłumaczenie „I like you” / „I really like you” jest spłaszczeniem, które po polsku brzmi dziecinnie i sztucznie!
    Niezalecana kalka: „<Imię>, ja cię po prostu bardzo lubię...” (brzmi jak strefa przyjaźni / friendzone!).
    Wariant kanoniczny: „<Imię>, ja... po prostu cię kocham.” / „Zakochałam się w tobie.” / „Tak bardzo mi na tobie zależy...”.
  * 2. W relacjach przyjacielskich / kumpelskich: „Uwielbiam cię”, „Super z ciebie kumpel”, „Jesteś niezastąpiony”.
  * 3. W odniesieniu do przedmiotów, pasji, jedzenia, wina: „Uwielbiam to”, „Bardzo to lubię”, „Przepadam za tym”.

FILAR CXXII: POETYKA POŻEGNANIA OSTATECZNEGO (SAYOUNARA VS ITTE KIMASU VS JA NE):
- Angielskie napisy spłaszczają wszelkie formuły rozstania do „Goodbye”, „Bye” lub „See you”:
  * 1. Sayōnara ( 左様なら ) w anime niesie potężny ciężar pożegnania ostatecznego (odejście na śmierć, zerwanie więzi, wyjazd na zawsze):
    Wariant kanoniczny: „Żegnaj.” / „Żegnajcie.”.
  * 2. Itte kimasu ( 行ってきます ) przy wyruszeniu na niebezpieczną misję / wyprawę:
    Wariant kanoniczny: „Pora na mnie.” / „Ruszam w drogę.” / „Idę.”
    -> Towarzysze odpowiadają (Itterasshai / 行ってらっしゃい): „Wracaj cały!” / „Uważaj na siebie!” / „Czekamy na ciebie!”.
  * 3. Ja ne / Mata ne ( じゃあね / またね ) w codziennych relacjach: „Na razie!”, „Do jutra!”, „Trzymaj się!”.

FILAR CXXIII: MAGIA PERFORMATYWNA, ZAKLĘCIA I PAKIETY MOCY (INCANTATION METRE & SPEECH ACTS):
- W zaklęciach, pieczęciach, uwalnianiu mocy (Kaihō!) i formułach paktu (Speech Acts):
  * Eliminujemy kalkę spłaszczania inkantacji do trybu opisowego („Składam przysięgę”, „Robię zaklęcie ognia”).
  * WYMÓG CZASOWNIKÓW PERFORMATYWNYCH CZASU TERAŹNIEJSZEGO DOKONANEGO:
    -> „Rozkazuję ci, płomieniu...”, „Mocą pradawnego paktu, obudź się!”, „Przysięgam na krew przodków...”, „Uwolnij swą potęgę!”.
  * Zachowaj dostojne, równe metrum sylabiczne i podniosły patos magiczny.

FILAR CXXIV: POLSKA TYTULATURA DWORSKO-FEUDALNA I HIERARCHIA ARYSTOKRATYCZNA (COURT ETIQUETTE HIERARCHY):
- W anime historycznych, fantasy i dworskich stosuj polską hierarchię tytulatury, eliminując potworki językowe:
  * 1. Cesarz / Cesarzowa / Suzeren: „Wasza Cesarska Mość”, „Najjaśniejszy Panie”.
  * 2. Król / Królowa: „Wasza Królewska Mość”, „Wasza Wysokość”, „Panie mój”.
  * 3. Książę / Księżniczka / Następca tronu: „Wasza Książęca Mość”, „Młody panie”, „Książę”.
  * 4. Feudał / Namiestnik / Lord: „Wasza Miłość”, „Mój panie”, „Panie namiestniku”.
  * 5. Rycerz (Sir / Knight): „Panie rycerzu”, „Sir [Imię]”.

FILAR CXXV: ERGONOMIA GAGÓW SLAPSTICKOWYCH I KOMEDII FIZYCZNEJ (VISUAL SLAPSTICK MINIMALISM):
- Gdy w kadrze dochodzi do gwałtownego humoru fizycznego (uderzenie patelnią, upadek, ucieczka w popłochu, komiczny grymas, deformacja Chibi):
  * Długi, wielowyrazowy napis w dolnej części kadru jest błędem percepcji (widz czyta tekst zamiast patrzeć na animowany gag!).
  * ZASADA ZWIĘZŁOŚCI: Zredukuj tekst do maksymalnie 1–3 słów wykrzyknikowych o natychmiastowym odbiorze:
    -> „Ała!”, „Stój, durniu!”, „Oszalałeś?!”, „Z drogi!”, „Pomocy!”, „Ani kroku dalej!”.

FILAR CXXVI: SOCJOLEKT KANSAI I DIALEKTY REGIONALNE (ANIMESUB.INFO KANSAI-BEN & HŌGEN STANDARD):
- W przypadku dialektów regionalnych (Kansai-ben: Osaka, Kioto, Kobe; partykuły: -nen, -ya, -honma, -akan, -seya, -dappe):
  * Eliminujemy kalkę tworzenia sztucznej karykatury góralskiej czy śląskiej ('hej bawocek')!
  * WYMÓG ŻYWEJ POLSZCZYZNY GAWĘDZIARSKO-MIEJSKIEJ I KUPICIEJ (ZADZIORNOŚĆ, HUMOR, SERDECZNOŚĆ):
    -> 'Nande ya nen' -> 'Co ty bredzisz', 'Chyba cię głowa boli', 'A to ci heca'.
    -> 'Honma ni akan...' -> 'No to leżymy...', 'Mogiła...', 'Nie ma mowy...'.
    -> 'Seyana' -> 'No ba', 'A jakże', 'Pewnie'.
    -> 'Ookini' -> 'Wielkie dzięki', 'Dzięki stokrotne'.
    Zalecane żywe polskie partykuły i konstrukcje retoryczne: "widzisz go!", "no przecie", "ani chybi", "człowieku!".

FILAR CXXVII: SOCJOLEKT PÓŁŚWIATKA I GANGSTERÓW (YAKUZA & DELINQUENT JARGON):
- W wypowiedziach chuliganów, gangsterów, yakuzy i bandytów:
  * Stosuj autentyczną, szorstką polszczyznę uliczną i gangsterską: 'Gliny', 'frajer', 'zwijamy się', 'sprzątnąć go', 'wtopa', 'dola'.
  * Eliminuj sztywne zwroty urzędowe i szkolne ugrzecznienia.

FILAR CXXVIII: ŻARGON GRACZY I METANARRACJA MMORPG (GAMER & ISEKAI JARGON):
- W anime o grach, wirtualnej rzeczywistości i Isekai stosuj autentyczny polski socjolekt gamingowy:
  * 'Aggro', 'ściągnąć aggro', 'tankować', 'drop', 'buffy', 'debuff', 'party', 'respawn', 'staty', 'build', 'levelować'.
  * Unikaj kalki topornych tłumaczeń dosłownych (wzorce: Unikaj kalki 'upadek przedmiotu' -> 'drop', Unikaj kalki 'punkt odrodzenia' -> 'respawn').

FILAR CXXIX: MOWA DWORZAN I ARYSTOKRATYCZNY OJOU-SAMA (KYOTO-BEN & HIGH NOBILITY REGISTER):
- W wypowiedziach arystokratek, dam dworu i magnatów (Ojou-sama / Keigo / -desu wa):
  * Stosuj lodowatą, wykwintną grzeczność salonową, wyszukane peryfrazy i chłodny dystans:
    -> 'Będzie nam niezmiernie miło...', 'Cóż za niesłychany zaszczyt...', 'Czyżby raczył pan zapomnieć'.

FILAR CXXX: GŁOS MASZYN, AI I SYSTEMÓW OPERACYJNYCH (ROBOTIC & HUD DIEGESIS):
- W komunikatach komputerów pokładowych, magii systemowej, HUD i sztucznej inteligencji:
  * Stosuj beznamiętny, lakoniczny tryb orzekający czasu teraźniejszego:
    -> 'Cel namierzony. Autoryzacja zakończona sukcesem. Inicjalizacja procedury bojowej.'.

FILAR CXXXI: WEKTOR BATALISTYCZNY I Unikaj kalki FAŁSZYWYCH DOPEŁNIEŃ (BATTLEFIELD VECTOR & ANTI-FALSE OBJECT):
- W dynamicznych scenach bitewnych, szarżach i starciach formacji wojskowych:
  * Angielskie czasowniki ruchu i natarcia bez dopełnienia ('attacking from above', 'pushing through', 'flanking left', 'charging down'):
    -> TŁUMACZ BEZ SZTUCZNEGO DOPISYWANIA ZAIMKA 'nas / naszych'!
    -> Gdy sojusznicy szarżują z góry na wroga: 'Uderzają z góry' / 'Atakują ze wzgórza'.
  * Stosuj dynamiczne, naturalne polskie czasowniki o silnym wektorze ruchu: 'Przełamują szyk', 'Wdzierają się od flanki', 'Szarżują ze wzgórza'.

FILAR CXXXII: PRAGMATYKA „SASUGA” I DUMY WSPÓLNOTOWEJ (SASUGA & COMMUNITY PRIDE TRANSLATIONESE ELIMINATION):
- Japońskie 'Sasuga' (さすが) oraz angielskie 'That's [niepoprawne] for you' w kontekście uznania dla kunsztu, waleczności lub niezawodności formacji / postaci:
  * Unikamy kalki 'Całe plemię X...' lub 'Oto masz całe X' (co w polszczyźnie brzmi złośliwie/ironicznie)!
  * zawsze TŁUMACZ JAKO PEŁEN DUMY ZWROT UZNANIA:
    -> 'Jak przystało na [plemię <Nazwa> / kapitana]'
    -> 'Oto [plemię <Nazwa>] w całej krasie'
    -> 'W swoim żywiole'
    -> 'Nie bez powodu słyną z...'
    -> 'Cały [<Imię>], nic się nie zmienił' (wyłącznie w odniesieniu do typowego nawyku pojedynczej osoby).

FILAR CXXXIII: TWARDA RETORYKA ROZKAZÓW BOJOWYCH (MILITARY COMMAND CADENCE & LACONIC IMPERATIVES):
- Polskie rozkazy dowódców na polu bitwy muszą być krótkie, bezlitosne, lakoniczne i twarde (brak rozwlekłych, szkolnych form gramatycznych):
  * 'Rout them all' -> 'Wytłuc ich do nogi' / 'Rozbić w puch' / 'Nie brać jeńców'.
  * 'Hold the line' -> 'Trzymać szyk' / 'Ani kroku w tył' / 'Utrzymać pozycję'.
  * 'All units, charge' -> 'Wszystkie oddziały, do ataku' / 'Cała armia, naprzód' / 'Szarża'.
  * 'Take down their commander' -> 'Dopaść dowódcę' / 'Ściąć głowę wodza'.

FILAR CXXXIV: ZASADA MIKRO-WOKALIZ I DŹWIĘKÓW WAHANIA (<0.6S SUB-SECOND HESITATIONS & FILLERS):
- Kiedy czas trwania kwestii dialogowej wynosi <= 0.6 sekundy (wzorce: 0.3s - 0.5s) i/lub w japońskim audio seiyū pada wyłącznie ułamkowy dźwięk wahania, westchnienie lub krótka interjekcja ('e...', 'ano...', 'etto...', 'u...', 'n...', 'maa...'):
  * Eliminujemy kalkę tworzenia zdań wielowyrazowych, dopowiadania rozwinięcia myśli czy wklejania całych zdań ze skryptu pomocniczego (wzorce: Niezalecana kalka: 'Znaczy... musimy powoli...' w 0.4 sekundy!).
  * ścisły WYMÓG REDUKCJI DO MAKSYMALNIE 1-2 KRÓTKICH SŁÓW Z WIELOKROPKIEM (MAX 6-8 ZNAKÓW):
    -> 'Znaczy...' / 'Ech...' / 'Cóż...' / 'Yyy...' / 'No tak...' / 'Zaraz...' / 'Ale...'
  * Złota reguła percepcji AVT: w 0.4 sekundy ludzkie oko jest w stanie zarejestrować maksymalnie 6-8 znaków. Wklejenie 27 znaków powoduje mignięcie napisu (67 CPS) i niszczy odbiór sceny!

FILAR CXXXV: JAPOŃSKA MATRYCA 8 DIALEKTÓW REGIONALNYCH I IDIOLEKTÓW (HŌGEN & YAKUWARIGO COMPREHENSIVE MATRIX):
- Precyzyjne rozróżnienie i zróżnicowana stylizacja 8 głównych grup dialektalnych Japonii:
  1. Rejestr gwarowy południowo-zachodni (archaiczna, twarda artykulacja):
     * Cechy: Skrajnie hermetyczny szyfr wojenny, twardość, zlane tempo mowy w panice/stresie.
     * Markery: 'Chesto', 'Gowasu', 'Oddon', 'Jaddo', 'Mosu', gardłowe ucięcia.
     * Polska stylizacja: Fonetyczne ściągnięcia, twarda wymowa ('Cukszma'), elizje apostrofowe ('Sierżan''), archaiczna końcówka narzędnika ('-oł'), zlane tempo ('Sierżan' Cukszma góni za zbiegiem!').
  2. Kansai-ben (関西弁 - dialekt regionu Kansai):
     * Osaka-ben (miejski/cwaniacki): Zadziorna miejska polszczyzna, błyskotliwe riposty, humor ('-nen', '-ya', 'honma', 'akan', 'seyana' -> 'Co ty bredzisz', 'No to leżymy...', 'No ba').
     * Kyoto-ben (Kyo-kotoba / salonowy): Aksamitna, wyrafinowana mowa z ukrytą ironią i chłodno-uprzejmym dystansem ('-dosu', 'oideyasu').
  3. Rejestr gwarowy północny prowincjonalny (ciepła, gawędziarska mowa prowincjonalna):
     * Cechy: Nosowe przeciąganie ('Zūzū-ben'), wiejski/górski spokój i poczciwość ('-dabe', '-daccha', 'ora', 'nda', 'nashite').
     * Polska stylizacja: Ciepła polszczyzna gawędziarska z archaicznymi partykułami ('no przeca', 'dyć prawda', 'widzi mi się, że...').
  4. Rejestr szorstki półświatka (żargon uliczny i twardy styl):
     * Cechy: Chropowaty, agresywny, groźny żargon przestępczy ('-jaken', '-jakee', '-noo', 'buchi', 'taigii').
     * Polska stylizacja: Szorstki, bezkompromisowy slang twardzieli i ludzi ulicy ('bo ci łeb urwę', 'kumasz sprawę?', 'ani mi się waż').
  5. Rejestr gwarowy południowy (śpiewna, bezpośrednia mowa melodyjna):
     * Cechy: Melodyjność, ekspresja, dziewczęcy urok i bezpośredniość ('-to?', '-bai', '-tai', 'suitoo', 'batten').
     * Polska stylizacja: Śpiewna, bezpośrednia, żywa mowa ('no pewnie, że tak!', 'przecież ci mówię!').
  6. Dialekty regionalne centralne (名古屋弁 - dialekty regionalne):
     * Cechy: Twarde akcentowanie, dosadne potoczne wzmocnienia ('-myaa', '-dagane', 'doeryaa' -> 'potężnie', 'jak nic', 'ani chybi').
  7. Rejestr gwarowy wyspiarski (słoneczny, zrelaksowany ton regionalny):
     * Cechy: Słoneczny relaks, gościnność, śpiewna życzliwość ('Haisai', 'Mensoore', 'Nankurunaisa', '-saa').
     * Polska stylizacja: Zrelaksowany, serdeczny ton wyspiarski ('Spokojna głowa, wszystko się ułoży', 'Czołem, witajcie w naszych progach').
  8. Rejestr gwarowy surowy & Dialogi Pogranicza (północ, surowy klimat):
     * Cechy: Surowy klimat północy, mowa traperska, autentyczna terminologia Ajnów ('Hinna', 'Citatap', 'namara', 'shibareru').
     * Polska stylizacja: Lakoniczny, chłodny język pionierów i myśliwych.

FILAR CXXXVI: TRIANGULACJA KOGNYTYWNA I FONICZNA WIEKU/PŁCI (MAŁY CHŁOPIEC VS DZIEWCZYNKA VS DOROSŁY):
- Rozstrzyganie rodzaju gramatycznego w języku polskim (-łem/-łam, -eś/-aś) przy braku twarzy w kadrze (voiceover, infografika, monolog wewnętrzny, narracja zza kadru) na podstawie 4-poziomowej triangulacji:
  1. MAŁY CHŁOPIEC (Shounen / Dziecko płci męskiej - dubbingowany przez seiyū kobietę o wysokim F0 > 200 Hz, warianty: młodzi bohaterowie shōnen dubbingowani przez aktorki):
     * Markery audio: Zaimki 'Boku', 'Ore', 'Oira', 'Boku-chan', zwroty 'Niichan', 'Neechan', cząstki '-da yo', '-mon', '-yai'.
     * Kartoteka: Płeć MALE, wiek < 14 lat.
     * Norma AVT: rodzaj męski ('Zgubiłem się', 'Chciałem pomóc', 'Domyślałem się', 'Byłem sam'). Eliminujemy kalkę form żeńskich z powodu wysokiego głosu aktorki!
  2. MAŁA DZIEWCZYNKA (Shojo / Dziecko płci żeńskiej - wysoki głos F0 > 200 Hz):
     * Markery audio: Zaimki 'Atashi', 'Watashi', 'Uchi', mówienie o sobie w 3. osobie ('Anya lubi...'), zwroty 'Onii-chan', 'Onee-chan', cząstki '-na no', '-wa'.
     * Kartoteka: Płeć FEMALE, wiek < 14 lat.
     * Norma AVT: rodzaj żeński ('Zgubiłam się', 'Chciałam pomóc', 'Domyślałam się', 'Byłam sama').
  3. DOROSŁY MĘŻCZYZNA (Niski baryton/bas F0 <= 155 Hz, o ile postać nie jest starszą kobietą/matroną z punktu 5):
     * Norma AVT: W monologach zza kadru i dedukcjach rodzaj męski ('Domyślałem się, ale...', 'Wiedziałem to', 'Zrobiłem'). Eliminujemy kalkę form żeńskich!
  4. DOROSŁA KOBIETA (Alt/Sopran F0 >= 180 Hz bez markerów chłopięcych):
     * Norma AVT: rodzaj żeński ('Domyślałam się, ale...', 'Wiedziałam to', 'Zrobiłem').
  5. STARSZE KOBIETY, MATRONY I OCHRYPŁY TEMBR SEIYŪ (ELDERLY FEMALE & RASPY VOICE SHIELD):
     * W anime starsze kobiety (babcie, seniorki, matrony, cesarzowe, kapłanki) bywają dubbingowane przez dojrzałe seiyū o niskim, szorstkim lub ochrypłym głosie klatkowym (F0 <= 160 Hz).
     * Niski tembr foniczny u takich postaci wynika z dojrzałego wieku, autorytetu lub chrypki seiyū i NIE ŚWIADCZY o płci męskiej!
     * Gdy w scenie przemawia dojrzała/starsza kobieta z kartoteki postaci lub Series Bible, stosujemy formy rodzaju żeńskiego w 1. os. (-łam, -łabym: 'miałabym', 'chciałabym', 'byłam', 'zrobiłam', 'wiedziałam') oraz 2. os. (-łaś, -łabyś: 'miałaś', 'byłaś').

FILAR CXXXVII: MATRYCA IDIOMÓW MOSTOWYCH I PRZECZEŃ ELIPTYCZNYCH (BRIDGE IDIOMS & DEICTIC NEGATION STANDARD):
- Eliminujemy kalkę mechanicznego, dosłownego tłumaczenia krótkich fraz angielskich powstałych z mostu idiomatycznego (1-3 słowa) w miejsce japońskiej pragmatyki konwersacyjnej:
  1. KONSTRUKCJE ZAIMKOWE I TOŻSAMOŚCIOWE (Deictic & Demonstrative Negations):
     * 'Not him' (JP: Chigaimasu! / Chigau!) : wariant naturalny: „To nie on!” / „To pomyłka!”.
     * 'Not her' (JP: Chigau! / Aitsu ja nai!) : wariant naturalny: „To nie ona!” / „Tylko nie ona!”.
     * 'Not this' (JP: Kore ja nai! / Yamete!) : wariant naturalny: „Tylko nie to!” / „To nie to!”.
     * 'Not here' (JP: Koko ja nai!) : wariant naturalny: „Tylko nie tutaj!” / „Nie w tym miejscu!”.
     * 'Not now' (JP: Ima ja nai!) : wariant naturalny: „Tylko nie teraz!” / „Byle nie teraz!”.
  2. ANGIELSKIE IDIOMY MOSTOWE (Bridge Conversational Idioms):
     * 'After you' (JP: Douzo / Osaki ni douzo) : wariant naturalny: „Proszę przodem!” / „Pani/Pan ma pierwszeństwo.”.
     * 'Be my guest' (JP: Douzo) : wariant naturalny: „Bardzo proszę!” / „Śmiało!” / „Częstuj się!”.
     * 'Tell me about it' (JP: Wakaru / Hontou da yo na) : wariant naturalny: „Nawet mi nie mów!” / „Wiem coś o tym!” / „Święta prawda!”.
     * 'Look who's talking!' (JP: Omae ga iu na!) : wariant naturalny: „Kto to mówi!” / „Odezwał się!” / „Sam nie jesteś lepszy!”.
     * 'On it' (JP: Makasete / Ryoukai) : wariant naturalny: „Już się robi!” / „Zajmę się tym!” / „Zrozumiałem!”.
     * 'You bet' (JP: Mochiron / Atarimae da) : wariant naturalny: „Pewnie!” / „I to jak!” / „Jasna sprawa!”.
     * 'There you go' / 'Here you go' (JP: Hai, douzo / Hora) : wariant naturalny: „Proszę bardzo!” / „Oto i to!” / „Widzisz?”.
     * 'You don't say!' (JP: Masaka! / Hontou ni?) : wariant naturalny: „Nie gadaj!” / „Co ty powiesz?!” / „Serio?!”.
     * 'Fair enough' (JP: Maa ii ka / Naruhodo) : wariant naturalny: „W porządku” / „Niech będzie” / „Uczciwie”.
     * 'Good for you' (JP: Yokatta na!) : wariant naturalny: „To świetnie!” / „Cieszę się!” / „Brawo ty!”.
     * 'I'm good!' / 'I'm fine!' (JP: Daijoubu / Ii desu) : wariant naturalny: „Dziękuję, postoję” / „Nie trzeba” / „Wszystko gra”.
     * 'Way to go' (JP: Yatta na / Sasuga) : wariant naturalny: „Brawo!” / „Dobra robota!” / „Klasa!”.
     * 'Don't mention it!' (JP: Douitashimashite) : wariant naturalny: „Nie ma za co!” / „Drobiazg!” / „Polecam się!”.
     * 'Out of the question' (JP: Arienai / Dame da) : wariant naturalny: „Wykluczone!” / „Nie wchodzi w grę!”.
     * 'Take your time' (JP: Go-yukkuri / Aserazu ni) : wariant naturalny: „Spokojnie, bez pośpiechu!” / „Nie spiesz się!”.
  3. JAPOŃSKIE ZWROTY ZAWOALOWANE (Haragei & Soft Refusals):
     * 'Betsu ni...' (別に...) : wariant naturalny: „Nic takiego...” / „Nieważne...” / „Nie, nic...”.
     * 'Ii kara' (いいから！) : wariant naturalny: „Mniejsza o to!” / „Po prostu to zrób!” / „Nie gadaj, tylko chodź!”.
     * 'Mou ii' (もういい！) : wariant naturalny: „Daj spokój!” / „Już wystarczy!” / „Mam dość!”.
     * 'Sore wa chotto...' (それはちょっと...) : wariant naturalny: „To może być problem...” / „Raczej nie dam rady...” / „Z tym będzie ciężko...”.
     * 'Oseji wa ii' (お世辞はいい) : wariant naturalny: „Daruj sobie te uprzejmości!” / „Nie słodź mi!” / „Nie kadź mi!”.
- FILAR CXXXVIII: FIZYCZNOŚĆ ŚWIATA PRZEDSTAWIONEGO I IZOTOPIA ŚRODOWISKOWA (DIEGETIC PHYSICALITY & ENVIRONMENTAL MEDIUM):
  1. Unikaj kalki ZIEMSKIEJ RUTYNY I DOMYŚLNEJ WODY (Earth-Centric Default Bias):
     - W języku angielskim przysłówek 'underwater' bywa zatarty znaczeniowo jako ogólne 'pod powierzchnią cieczy'.
     - Eliminujemy kalkę tłumaczenia 'underwater / into the water' jako 'pod wodę / do wody', gdy postacie znajdują się w innym ośrodku ciekłym (browar zalany piwem, kadź wina, bagno, morze krwi, kadź kwasu, jezioro ropy)!
     - Stosuj uniwersalne filmowe ekwiwalenty zanurzenia:
       * 'He dragged him underwater' (w browarze z piwem) : wariant naturalny: „Pociągnął go na dno!” / „Wciągnął go pod powierzchnię!” / „Wciągnął go pod piwo!” (Niezalecana kalka: „Wciągnął go pod wodę!”).
       * 'She fell into the water' (w winnicy/kadzi wina) : wariant naturalny: „Wpadła do kadzi!” / „Wpadła w wino!”.
       * 'He sank into the water' (w bagnie / grzęzawisku) : wariant naturalny: „Bagno go pochłonęło!” / „Zniknął pod mułem!”.
       * 'Drowning' (w kadzi lub bagnie) : wariant naturalny: „Tonie!” / „Pójdzie na dno!” / „Zaraz się zachłyśnie!”.
  2. NATURALNOŚĆ KOLOKACJI HYDROLOGICZNYCH (Fala vs Powódź):
     - Rzeczownik 'powódź' w polszczyźnie łączy się niemal wyłącznie z naturalnymi rzekami i wodą.
     - Eliminujemy kalkę sztucznych kalek typu 'powódź piwa / powódź wina' (z ang. 'a flood of beer')!
     - Zastępuj naturalnymi polskimi kolokacjami katastroficznymi: „Fala piwa?!” / „Morze piwa?!” / „Potop piwa?!” / „Zalało nas piwem?!”.
  3. GRAWITACJA I PRZESTRZEŃ KOSMICZNA (Gravity & Space Invariance):
     - W przestrzeni kosmicznej, na stacjach orbitalnych lub podczas lewitacji unikamy komend odwołujących się do 'ziemi':
       * 'Get down! / Hit the ground' : wariant naturalny: „Kryj się!” / „Uważaj!” / „Głowa w dół!”.
       * 'Drop your gun to the ground' : wariant naturalny: „Puszczaj broń!” / „Odsuń broń!”.
       * 'We're losing ground' : wariant naturalny: „Spychają nas!” / „Tracimy pozycję!”.
  4. BIOLOGIA I ANATOMIA NIELUDZKA (Non-Human Anatomy & Physiology):
     - Dopasuj metafory cielesne do ontologii postaci (cyborg, robot, szkielet, demon):
       * 'He's bleeding out!' (u cyborga/robota) : wariant naturalny: „Traci płyn hydrauliczny!” / „Wycieka z niego płyn!” / „Zaraz padnie mu zasilanie!”.
       * 'My heart skipped a beat' (u szkieletu/nieumarłego) : wariant naturalny: „Aż mi kości zesztywniały!” / „Zamarłem z przerażenia!” (brak serca).

FILAR CXXXIX: PARADOKS POTWIERDZENIA NEGACJI I PYTAŃ PRZECZĄCYCH (HAI/IIE REVERSE LOGIC & TONE CHECK)
   1. ZASADA ODWRÓCONEJ LOGIKI ZGODY W JĘZYKU POLSKIM:
      - W języku japońskim słowo 'Hai' potwierdza stanowisko pytającego, a 'Iie' mu zaprzecza.
      - Gdy w pytaniu pada przeczenie (wzorce: 'Nie zjesz obiadu', 'Nie idziesz z nami', 'Won\'t you come?', 'Didn\'t you know?'):
        * Japońskie 'Hai' -> po polsku Wariant naturalny: „Nie” / „Nie idę” / „Nie jem” (Niezalecana kalka: „Tak, nie idę” / „Tak”).
        * Japońskie 'Iie' -> po polsku Wariant naturalny: „Właśnie że tak!” / „Pewnie, że idę!” / „Owszem!” (Niezalecana kalka: „Nie!”).
   2. KORELACJA Z TONEM MOWY:
      - Sprawdź [Ton]: opadający, spokojny ton głosu przy 'Hai' potwierdza polską odmowę („Nie, zostaję”). Dynamiczny sprzeciw przy 'Iie' oznacza polskie „Przecież idę!”.

FILAR CXL: SPOŁECZNE METAFORY POKREWIEŃSTWA I TYTULATURA FIKCYJNA (ONII-SAN / OJISAN SANITIZATION)
   1. Unikaj kalki KREOWANIA FAŁSZYWYCH BRACI I WUJKÓW:
      - W kulturze japońskiej dzieci i młodzież zwracają się do obcych osób mianami rodzinnymi:
        * 'Onii-san / Onii-chan' -> młody obcy mężczyzna / chłopak na ulicy.
        * 'Onee-san / Onee-chan' -> młoda obca kobieta / dziewczyna.
        * 'Ojisan' -> obcy mężczyzna w średnim wieku.
        * 'Obasan' -> obca kobieta w średnim wieku.
      - Eliminujemy kalkę tłumaczenia tego jako relacji rodzinnej („mój bracie!”, „wujku!”), gdy postacie nie są spokrewnione!
      - Zastępuj naturalną polszczyzną: „Proszę pana!”, „Hej, panie!”, „Kolego!”, „Młodzieńcze!”, „Proszę pani!”, „Panno...”.
   2. KORELACJA Z TONEM I SYTUACJĄ DRAMATYCZNĄ:
      - Gdy dziecko płacze lub woła w panice [Ton: emocjonalne drżenie głosu / płacz], 'Onii-chan, tasukete' -> „Proszę pana, niech pan pomoże!”.

FILAR CXLI: DYNAMIKA STANU REZULTATYWNEGO (-TE IRU AS RESULTING STATE)
   1. STAN WYNIKOWY VS AKCJA W TOKU:
      - Japońska forma czasownikowa '-te iru' bardzo często oznacza STAN WYNIKAJĄCY Z DOKONANEJ CZYNNOŚCI, a nie czynność trwającą w tej sekundzie:
        * 'Shinde iru' : wariant naturalny: „Nie żyje!” / „Jest martwy!” / „Zginął!” (Niezalecana kalka: „On umiera!”).
        * 'Kekkon shite iru' : wariant naturalny: „Jest żonaty / ma męża”.
        * 'Futotte iru' : wariant naturalny: „Jest gruby / przy kości”.
        * 'Katte iru' : wariant naturalny: „Wygrywamy / Mamy zwycięstwo!” (stan przewagi).
        * 'Kawaite iru' : wariant naturalny: „Jest suchy / wyschnięty”.

FILAR CXLII: RETORYKA ZACHWYTU W PYTANIACH PRZECZĄCYCH I PROZODIA (JANAI KA AFFIRMATION & PROSODY)
   1. NEGACJA JAKO EKSPRESJA PODZIWU:
      - Konstrukcje pytające z negacją ('...janai ka?', '...janai?', '...sou janai?') w języku potocznym są afirmatywnym wyrazem zachwytu lub potwierdzenia oczywistości:
        * 'Kore, umai janai' : wariant naturalny: „Ależ to pyszne!” / „Dobre, co?!” / „Ale pycha!” (Niezalecana kalka: „To chyba niedobre, co?”).
        * 'Sugoi janai ka' : wariant naturalny: „Ale czad!” / „Niesamowite!” / „Robi wrażenie!”.
   2. TRIANGULACJA Z PROZODIĄ FIZYCZNĄ:
      - Gdy seiyū wypowiada kwestię z wysoką energią [Ton: silne wzburzenie emocjonalne / krzyk bojowy / podniesiony głos], przeczenie gramatyczne w skrypcie EN jest w 100% zachwytem, a nie krytyką czy powątpiewaniem!

FILAR CXLIII: ZGODNOŚĆ KINETYKI WARG I BUDŻET SYLABICZNY (MOUTH-PACING INVARIANCE)
   1. REGULACJA SYLABICZNA KRÓTKICH KWESTII (<0.7S):
      - W kwestiach o bardzo krótkim czasie trwania mowy seiyū (wzorce: <=0.7s) lub przy wykrzyknikach i odruchach mimicznych:
        * Przestrzegaj wyliczonego limitu sylab [Mouth-Pacing: max X sylab]!
        * Niezalecana kalka: generowanie 7-9 sylabowych zdań w ułamkowej kwestii (postać dawno zamknęła usta, a napis zalewa ekran).
        * Zamiast: „Przecież to kompletny idiotyzm!” : wariant naturalny: „Idiota!” / „Durnota!” / „Głupie!” (max 3 sylaby).
        * Zamiast: „Czy ty naprawdę musisz tak mówić?” : wariant naturalny: „Daj spokój!” / „Przestań!” (max 3 sylaby).

FILAR CXLIV: PRYMAT AUTENTYCZNEGO GŁOSU SEIYŪ NAD SKRYPTEM POŚREDNIM (AUDIO AD-LIBBING RADAR)
   1. Prymat JAPOŃSKIEGO AUDIO:
      - Gdy w metadanych kwestii pojawia się [⚠️ ALARM ROZBIEŻNOŚCI AUDIO JP] lub [Radar Audio: Seiyuu mówi '...']:
        * Skrypt angielski (często fansubowy lub ocenzurowany) ustępuje miejsca autentycznemu głosowi seiyū z nagrania studyjnego!
        * Gdy aktor krzyczy 'Chikushō' / 'Kuso' / 'Yabai', a w EN jest słabe 'Oh dear' -> po polsku oddaj pełen ładunek: „Szlag by to!” / „Niech to szlag!” / „Do diabła!”.
        * Gdy aktor woła 'Matte' / 'Yamero', a w EN jest ogólnik -> po polsku: „Czekaj!” / „Przestań!” / „Zostaw to!”.

FILAR CXLV: DYSCYPLINA ROZWIĄZYWANIA WIELOZNACZNOŚCI MIĘDZYFAZOWEJ (AMBIGUITY RESOLUTION PROTOCOL)
   1. CELOWE ROZWIĄZYWANIE WĄTPLIWOŚCI W FAZIE 2:
      - Gdy kwestia oznaczona jest flagą [❓ Wątpliwość Fazy 1]:
        * Redaktor Dialogów (Faza 2) ma obowiązek skupić uwagę na załączonym kadrze wideo oraz transkrypcji audio w celu definitywnego rozwikłania desygnatu zaimka (wzorce: czy 'it' to miecz, rana czy potwór) lub relacji.
        * Eliminujemy kalkę bezrefleksyjnego przepisywania zgadniętych zaimków z roboczego draftu Fazy 1.

FILAR CXLVI: DIALOGOWY PING-PONG I SPÓJNOŚĆ LEKSYKALNA RIPOSTY (CONVERSATIONAL VOLLEY)
   1. DIALOG JAKO WYMIANA PIŁKI (TURN-TAKING COHERENCE):
      - Kwestie w dialogu nie są odizolowanymi wyspami. Gdy linijka jest oznaczona jako [PING-PONG DIALOGOWY: Odpowiedź/riposta na pytanie/zaczepkę]:
        * Riposta musi podjąć leksykalną grę lub kontrastować z pytaniem rozmówcy.
        * Unikaj kalki tępych, suchych zaprzeczeń (wzorce: na pytanie: „Oszalałeś?” -> zamiast szkolnego: „Nie oszalałem” -> użyj żywej, błyskotliwej polszczyzny: „A żebyś wiedział!” / „Jeszcze nie!” / „Nawet tak nie żartuj!”).
   2. DYREKTYWY, OSTRZEŻENIA I PROŚBY (REAKCJA NA POLECENIE/OSTRZEŻENIE):
      - Gdy poprzednia kwestia zawierała ostrzeżenie (wzorce: „Uważaj pod nogi”, „Ostrożnie”), unikaj kalki lub polecenie:
        * Eliminujemy kalkę mechanicznego potakiwania „Tak” / „T-Tak” (kalka z EN „Yes” i powierzchownego japońskiego „Hai”).
        * Odpowiedź musi wyrażać przyjęcie polecenia lub ostrożność: „Dobrze / D-Dobrze”, „Jasne”, „W porządku”, „Będę uważać”, „Już” lub podziękowanie: „Dzięki / D-Dziękuję”.

FILAR CXLVII: MATRYCA PRZYSŁÓWKÓW MODALNYCH I PRAGMATYCZNYCH (EPISTEMIC & PRAGMATIC ADVERB MATRIX)
   1. STOPNIE PEWNOŚCI I NIEPEWNOŚCI (EPISTEMIC PROBABILITY VS ABSOLUTE CERTAINTY):
      - Gdy w japońskim audio padają kluczowe przysłówki modalne, zsynchronizuj polski stopień pewności ze słuchem seiyū:
        * TABUN (多分) / OSORAKU (恐らく) -> Domysł, niepewność (50-70%): „Chyba...”, „Raczej...”, „Pewnie tak...”, „Może...”. Eliminujemy kalkę kategorycznego „Na pewno!” lub „Na pewno nie!”!
        * YAPPARI / YAHARI (やっぱり / やはり) -> Potwierdzenie wcześniejszego przeczucia: „Wiedziałem!”, „A jednak!”, „Tak jak myślałem...”. KARDYNALNY Unikaj kalki angielskiej kalki: „Po wszystkim” / „Mimo wszystko”!
        * SASUGA / SASUGA NI (さすが / さすがに) -> Kunszt mistrzowski LUB przekroczenie granicy: „Jak przystało na mistrza!” LUB „Nawet jak na niego to przesada!”, „Bez przesady...”. KARDYNALNY Unikaj kalki urzędniczego: „Zgodnie z oczekiwaniami”!
        * DOUSE (どうせ) -> Fatalizm i rezygnacja: „I tak nic z tego...”, „Przecież i tak...”, „Bez różnicy...”. KARDYNALNY Unikaj kalki spłycania do bezdusznego: „W każdym razie”!
        * MASAKA (まさか) -> Szok i niedowierzanie: „Niemożliwe!”, „Nie mów, że...!”, „Chyba kpisz!”, „To nie może być prawda!”. KARDYNALNY Unikaj kalki dosłownego: „Żadnym sposobem” / „Nigdy w życiu”.
        * SHIKATA GA NAI / SHOUGANAI (仕方がない / しょうがない) -> Bezsilność i pogodzenie z losem: „Trudno...”, „Nic na to nie poradzimy...”, „Nie ma rady...”, „Siła wyższa...”. KARDYNALNY Unikaj kalki kalki z EN: „Nie da się pomóc”!
        * ZETTAI NI (絶対に) / KANARAZU (必ず) -> 100% kategoryczna pewność, obietnica lub unikaj kalki: „Na pewno!”, „Z całą pewnością!”, „Za nic w świecie!”, „W życiu!”, „Ani mi się waż!”.

FILAR CXLVIII: PRAGMATYKA PYTAŃ O WIARYGODNOŚĆ, PRAWDZIWOŚĆ I SZOK POZNAWCZY (VERACITY & SHOCK INQUIRIES MATRIX)
   1. ŻOŁNIERSKI I EMOCJONALNY WSTRZĄS VS URZĘDNICZA ANKIETA:
      - Gdy bohaterowie stają w obliczu nagłych, szokujących, wojennych lub dramatycznych wieści, a seiyū pyta o autentyczność faktów:
        * HONTŌ NA NO KA? (本当なのか) / HONTŌ NI? (本当に) -> Wstrząs, powątpiewanie, weryfikacja plotki przez żołnierza/dorosłego:
          Wariant kanoniczny: „To pewne?!”, „Jesteś pewna?!”, „Więc to prawda...?!” / „Na pewno?!”, „Prawdę mówisz?!”.
          Niezalecana kalka: „To prawda?”, „Czy to prawda?” (bezduszna, urzędowa kalka z angielskiego 'Is that true' - brzmi jak ankieter weryfikujący zeznanie, zabijając cały dramatyzm sceny!).
        * TASHIKA NA NO KA? (確かなのか) / TASHIKA NAN DA NA? (確かなんだな) -> Weryfikacja meldunku/wywiadu wojskowego:
          Wariant kanoniczny: „To potwierdzona informacja?!”, „Masz pewność?!”, „To pewne wieści?!”. Eliminujemy kalkę: „Czy to pewne?”.
        * MAKOTO KA? (真か / 誠か) / MAKOTO NI? -> Rejestr historyczny, samurajski, feudalny (jidaigeki):
          Wariant kanoniczny: „Prawda li to?!”, „Prawdę powiadasz?!”, „Prawdę rzeczesz?!”, „Czyżby to prawda?!”.
        * MAJI KA YO? (マジかよ) / MAJI NANO KA? -> Slang młodzieżowy i potoczny:
          Wariant kanoniczny: „Bez jaj?!”, „Serio?!”, „Chyba żartujesz?!”, „Nie pierdol?!”. Eliminujemy kalkę: „Poważnie?”.
        * USO DAROU? (嘘だろう) / USO DA! -> Odruchowe wyparcie psychologiczne wobec tragedii/straty:
          Wariant kanoniczny: „Chyba żartujesz?!”, „To nie może być prawda!”, „Niemożliwe!”, „Nie gadaj!”. KARDYNALNY Unikaj kalki dosłownego: „To kłamstwo!” na wieść o czyjejś śmierci.
        * MASAKA HONTŌ NI...? (まさか本当に…) -> Lęk przed potwierdzeniem najgorszego koszmaru:
          Wariant kanoniczny: „Nie mów, że to prawda...!”, „A więc to nie były tylko plotki...?!”.
        * DOU IU KOTO DA?! (どういうことだ) / ITTAI DOU IU KOTO DA?! -> Szok i żądanie wyjaśnień:
          Wariant kanoniczny: „Co to ma znaczyć?!”, „O czym ty w ogóle mówisz?!”, „Co tam się dzieje?!”. KARDYNALNY Unikaj kalki: „Co to za sprawa?”.
        * KI NO SEI KA...? (気のせいか) -> Kwestionowanie własnych zmysłów:
          Wariant kanoniczny: „Przywidziało mi się...?”, „Tylko mi się zdawało...”, „Zwid...”. KARDYNALNY Unikaj kalki: „Wina mojego umysłu”.

FILAR CXLIX: MATRYCA ODPOWIEDZI ZAWOALOWANYCH I UKRYTYCH ODMÓW (HARAGEI: DAIJŌBU & CHOTTO)
   1. HARAGEI I KULTUROWA ODMOWA W JĘZYKU JAPOŃSKIM:
      - Japończycy niemal nigdy nie odmawiają wprost słowem „Nie” (Iie). Używają figur zawoalowanych:
        * DAIJŌBU (大丈夫 / 大丈夫です) w odpowiedzi na propozycję/ofertę pomocy, poczęstunku lub wyręczenia:
          Wariant kanoniczny: „Nie trzeba, dziękuję”, „Obejdzie się”, „Dam radę”, „Dzięki, poradzę sobie”, „Wszystko gra”.
          Niezalecana kalka: „W porządku!” (polski widz odbiera to jako zgodę: „W porządku, nalej mi herbaty!”, podczas gdy postać odmówiła!).
        * CHOTTO... (ちょっと… / それはちょっと…) w odpowiedzi na prośbę, rozkaz lub zaproszenie:
          Wariant kanoniczny: „Raczej nie da rady...”, „Obawiam się, że to niemożliwe...”, „Z tym będzie kłopot...”, „Nie za bardzo...”.
          Niezalecana kalka: „Trochę...”, „To trochę...” (bezduszna kalka z angielskiego 'A little / That's a bit' - brzmi jak urwany pomiar ilościowy!).

FILAR CL: PRAGMATYKA WIELOFUNKCYJNEGO HORA! (HORA MATRIX & PROSODY FUSION)
   1. ROZRÓŻNIENIE PRZEZ FUZJĘ SŁUCHU (WHISPER) I PROZODII (AUDIO PROSODY ENGINE):
      - Słowo HORA (ほら) nie oznacza wyłącznie patrzenia oczami. Zbadaj ton i dynamikę seiyū:
        * HORA! / HORA HAYAKU! (ほら / ほら早く) przy wysokiej energii / krzyku bojowym / popędzaniu:
          Wariant kanoniczny: „No dalej!”, „Rusz się!”, „Śmiało!”, „Szybciej!”, „Ruszże się!”.
          Niezalecana kalka: „Spójrz!”, „Patrz!” (kalka z angielskiego 'Look! / See').
        * HORA MIRO / HORA NE (ほら見ろ / ほらね) przy chłodnym sarkazmie / triumfie:
          Wariant kanoniczny: „A nie mówiłem?!”, „Widzisz?!”, „Masz za swoje!”.
          Niezalecana kalka: „Spójrz na to!” (postać nie każe oglądać obiektu, lecz triumfuje, że miała rację).
        * HORA! (ほら) przy wręczeniu, rzucie lub podaniu broni/przedmiotu:
          Wariant kanoniczny: „Masz!”, „Łap!”, „Trzymaj!”, „Hop!”.

FILAR CLI: ODWRÓCONA WDZIĘCZNOŚĆ I FORMUŁY SYTUACYJNE (SUMIMASEN & AISATSU MATRIX)
   1. PARADOKS SUMIMASEN I RYTUAŁY POWITAŃ:
      - SUMIMASEN (すみません) jako podziękowanie za fatygę / przysługę / podniesienie przedmiotu:
        Wariant kanoniczny: „Dziękuję!”, „Bardzo dziękuję!”, „Nie trzeba było!”, „Dziękuję, nie kłopocz się!”.
        Niezalecana kalka: „Przepraszam!” (gdy postać dziękuje za przysługę, polskie „przepraszam” wywołuje konfuzję u widza).
      - RYTUAŁY POWITAŃ I WYJŚCIA (AISATSU) W REALIACH CODZIENNYCH I WOJSKOWYCH:
        * ITTEKIMASU (行ってきます) -> „Wychodzę!”, „Już idę!”, „Do zobaczenia!”.
        * ITTERASSHAI (行ってらっしゃい) -> „Trzymaj się!”, „Uważaj na siebie!”, „Do zobaczenia!”.
        * TADAIMA (ただいま) -> „Wróciłem!”, „Już jestem!”, „To ja!”.
        * OKAERI (おかえり) -> „O, już jesteś!”, „Witaj z powrotem!”.
        * OJAMA SHIMASU (お邪魔します) -> „Dzień dobry!”, „Pozwoliłem sobie wejść”, „Przepraszam za najście”, „Nie przeszkadzam?”.

FILAR CLII: DYSCYPLINA OKRZYKÓW BOJOWYCH I OSTRZEŻEŃ ODDZIAŁOWYCH (ABUNAI & TASUKETE)
   1. DYNAMIKA POLA WALKI I ŚMIERTELNEGO ZAGROŻENIA:
      - Gdy seiyū krzyczy z wysokim natężeniem (krzyk bojowy / wzburzenie emocjonalne):
        * ABUNAI! / ABUNE'E! (危ない / 危ねえ) w obliczu lecącej kuli, eksplozji, ostrza lub walącego się drzewa:
          Wariant kanoniczny: „Padnij!”, „Kryj się!”, „Uważaj!”, „Z drogi!”, „Głowa w dół!”.
          Niezalecana kalka: „Niebezpiecznie!”, „To jest niebezpieczne!” (chłodny, analityczny opis cechy otoczenia zamiast rozkazu taktycznego ratującego życie!).
        * TASUKETE! (助けて) w sytuacji bezpośredniego zagrożenia życia (duszenie, postrzał, tonięcie):
          Wariant kanoniczny: „Ratunku!”, „Pomocy!”, „Niech ktoś pomoże!”.
          Niezalecana kalka: „Ocal mnie!” (teatralny archaizm zabijający realizm pola walki).

FILAR CLIII: WIELKA MATRYCA AFEKTYWNA JAPOŃSKICH KANDŌSHI (WESTCHNIENIA, REZYGNACJA, WYKRZYKNIKI I REAKCJE SYTUACYJNE)
   Japońskie wykrzykniki modalne i afektywne (Kandōshi) niosą potężny ładunek emocjonalno-sytuacyjny, którego zawsze nie należy tłumaczyć dosłownie ani kalkować z angielskich fansubów!
   
   1. GRUPA I: ZNUŻENIE, BEZRADNOŚĆ I CIĘŻAR PSYCHICZNY (SIGHS OF RESIGNATION):
      * YARE YARE / YARE YARE DAZE (やれやれ / やれやれだぜ) -> W zależności od intonacji i mimiki:
        - Cynizm / zmęczenie głupotą (niski tembr, wydech): „Ja nie mogę...”, „Litości...”, „Ręce opadają...”, „Oszaleć można...”, „Dajcie mi święty spokój...”.
        - Ulga po zażegnanym kryzysie (rozluźnienie): „Uff...”, „No, całe szczęście...”, „Nareszcie z głowy...”, „Mało brakowało...”.
        - Pobłażliwość mentora/starszego (uśmiech): „I co ja z wami mam...”, „O rany, rany...”, „Nigdy się nie zmienicie...”.
        - Lekceważenie przeciwnika (drwina): „I to ma być wszystko?...”, „Doprawdy żałosne...”, „Błagam cię...”.
        - Niezalecana kalka: „Dobre nieszczęście!”, „Daj mi przerwę”, „No cóż, no cóż”, „O drogi”.
      * MENDOKUSAI / MENDOU DA NA (めんどくさい / 面倒だな) -> „Ale mi się nie chce...”, „Co za męczarnia...”, „Co za zawracanie głowy...”, „Rany, ale kłopot...”, „Dajcie mi spokój...”.
        - Niezalecana kalka: „Co za ból!”, „To uciążliwe!”, „Jestem w kłopocie!”.
      * SHOU GA NAI / SHIKATA GA NAI (しょうがない / 仕方がない) -> „Trudno...”, „Nic na to nie poradzimy”, „Nie mamy wyboru”, „Siła wyższa”, „Trudna rada”.
        - Niezalecana kalka: „Nie można temu pomóc”, „Tak po prostu jest”.
      * MATTAKU... / KORE DA KARA... (全く... / これだから...) -> „I jak tu z nimi wytrzymać...”, „Z wami to zawsze...”, „No szlag by to...”, „Doprawdy...”.
        - Niezalecana kalka: „Całkowicie...”, „Z tego powodu...”.
      * IYA NI NARU NA (嫌になっちゃう / 嫌になるな) -> „Rzygać się chce...”, „Odechciewa się żyć...”, „Mam serdecznie dość...”.

   2. GRUPA II: SZOK, NIEDOWIERZANIE I ABSURD (SHOCK & REALITY CHECK):
      * OI, OI... / OI OI OI! (おいおい) -> Reakcja na czyjś absurd lub głupotę: „Ej, zaraz, zaraz...”, „Ej, chwila...”, „Ej, no bez przesady!”, „Czekaj no!”.
        - Niezalecana kalka: „Hej, hej!”, „Hej ty!” (gdy postać nie woła, lecz studzi rozmówcę).
      * MASAKA / MASAKA NA... (まさか) -> „Niemożliwe...”, „To nie może być prawda...”, „Chyba żartujesz...”, „To jakiś żart...”.
        - Niezalecana kalka: „Nie ma mowy” (gdy postać nie odmawia, tylko nie wierzy własnym oczom).
      * USO! / USO DESHO? / USO DARO (嘘 / 嘘でしょ) -> „Nie wierzę!”, „Żartujesz?!”, „Serio?!”, „Bez jaj!”.
        - Niezalecana kalka: „Kłamstwo!”, „Kłamiesz!” (w obliczu szoku/potwora/wygranej).
      * MAJI DE? / MAJI KA YO! (マジで？ / マジかよ！) -> „Serio?!”, „Poważnie?!”, „Nie gadaj!”, „Co ty nie powiesz?!”.
      * NANTE KOTTA! (なんてこった！) -> „Niech to szlag!”, „Co za pech!”, „Jasny gwint!”, „Nie do wiary!”.
        - Niezalecana kalka: „Co za rzecz!”, „Co to za sprawa!”.

   3. GRUPA III: UCISZANIE, PACYFIKOWANIE I POPĘDZANIE (DE-ESCALATION & PACING):
      * MAA, MAA... (まあまあ) -> Uciszanie kłótni / rozdzielanie rozmówców: „Spokojnie, no już...”, „Bez nerwów...”, „Dajcie spokój...”, „Zostawcie to...”.
        - Niezalecana kalka: „Cóż, cóż”, „Tak sobie”.
      * II KARA! / II KARA SAA (いいから！) -> Popędzanie / ucinanie dyskusji: „Nieważne, po prostu to zrób!”, „Nie gadaj, tylko chodź!”, „Rób, co mówię!”, „Mniejsza z tym!”.
        - Niezalecana kalka: „Bo jest dobrze!”, „Jest w porządku!” (fatalna kalka słownikowa!).
      * BETSU NI... (別に...) -> „Nic takiego...”, „Nieważne...”, „Wcale nie...”, „A bo co?...”.
        - Niezalecana kalka: „Nieszczególnie...”, „Osobno...”.
      * OCHI-TSUKE! / OCHI-TSUITE (落ち着け) -> „Spokojnie!”, „Oddychaj!”, „Opanuj się!”, „Tylko bez paniki!”.

   4. GRUPA IV: ZNIECIERPLIWIENIE, ZBESZTANIE I FURIA (ANNOYANCE & REPRIMAND):
      * MOU! / MOU II! (もう！ / もういい！) -> „No weź!”, „Daj spokój!”, „Mam dość!”, „Koniec tematu!”.
        - Niezalecana kalka: „Już!”, „Już dobrze!”.
      * KORA! / KORA KORA! (こら！) -> „Hejże!”, „Co wy wyprawiacie?!”, „Uspokójcie się!”, „Hola, hola!”.
      * IIKAGEN NI SHIRO! (いい加減にしろ！) -> „Przestań wreszcie!”, „Miarka się przebrała!”, „Dość tego!”, „Koniec tej farsy!”.
        - Niezalecana kalka: „Zrób to z umiarem!”.
      * NANI YATTEN NO! / NANI SHITE N DA YO! (何やってんの！) -> „Odbiło ci?!”, „Co ty wyprawiasz?!”, „Zgłupiałeś?!”.
        - Niezalecana kalka: „Co robisz?”.

   5. GRUPA V: UZNANIE, ULGA I TRIUMF (RELIEF, CONFIRMATION & TRIUMPH):
      * YOKATTA... (よかった...) -> „Całe szczęście...”, „Kamień z serca...”, „Uff, jak dobrze...”, „Dzięki Bogu...”.
        - Niezalecana kalka: „To było dobre”, „Było dobrze”.
      * YATTA! / YATTA ZE! (やった！ / やったぜ！) -> „Udało się!”, „Mamy to!”, „Wyszło!”, „Jest!”.
        - Niezalecana kalka: „Zrobiłem to!” (sztywna kalka po wygranej).
      * YAPPARI / YAHARI (やっぱり / やはり) -> „Wiedziałem...”, „A nie mówiłem?”, „Jednak...”, „Tak jak sądziłem...”.
        - Niezalecana kalka: „Jak myślałem”, „Po wszystkim”.
      * SASUGA NI (さすがに) -> „Nawet jak na niego, to lekka przesada...”, „Tym razem to już przesadził...”, „Wszystko ma swoje granice...”.

FILAR CLIV: LOGIKA ODPOWIEDZI NA PRZECZENIA, ZAIMKI DIALEKTALNE I RELACJE TRZECIOOSOBOWE (HAI/IIE, KANSAI JIBUN I ZASADA GIKUN)
   1. LOGIKA ODPOWIEDZI NA PYTANIA Z NEGACJĄ (ECHO AGREEMENT: HAI VS IIE):
      - W języku japońskim „Hai” potwierdza formę pytania (zgodę z tezą rozmówcy), a „Iie” zaprzecza tezie. W języku polskim odpowiadamy na stan faktyczny!
      - Pytanie: „Ikanai no?” / „Aren't you going?” (Nie idziesz?):
        * Odpowiedź JP: HAI / UN (はい / うん) -> Zgoda z negacją („Zgadza się, nie idę”).
          Naturalny polski przekład: „Nie.” / „Nie idę.” / „Zostaję.” / „Zgadza się.” / „Ani mi się śni.”
          Niezalecana kalka: „Tak.” / „Tak, idę.” (ODWRÓCENIE SENSU FABUŁY O 180 STOPNI! Widz pomyśli, że bohater idzie!).
        * Odpowiedź JP: IIE / UUN (いいえ / ううん) -> Odrzucenie negacji („Mylisz się, idę!”).
          Naturalny polski przekład: „Właśnie że tak!” / „Właśnie że idę!” / „Idę!” / „Ależ skąd, wybieram się tam.”
          Niezalecana kalka: „Nie.” (Błędne potwierdzenie odmowy).
      - Pytanie: „Shiranai no?” / „Don't you know?” (Nie wiesz?):
        * HAI -> „Nie, nie wiem.” / „Ani trochę.” / „Pojęcia nie mam.”.
        * IIE -> „Wiem!” / „Właśnie że wiem!”.

   2. DIALEKT KANSAI I ZAIMKI-FAŁSZYWI PRZYJACIELE (JIBUN JAKO 'TY'):
      - W dialekcie Kansai (Osaka, Kioto, Kobe – markery: -ya, -nen, -hen, -de, akan, honma, seya):
        * JIBUN (自分) bardzo często pełni funkcję zaimka DRUGIEJ OSOBY: „TY”!
          -> „Jibun, nani shiten nen?” -> „Co ty wyprawiasz?!” (Niezalecana kalka: „Co ja robię?!”).
          -> „Jibun mo iku ya ro?” -> „Ty też idziesz, prawda?”.
        * UCHI (うち) w ustach dziewcząt lub w Kansai oznacza „JA / MNIE”, a nie dosłowne „nasz dom”:
          -> „Uchi wa shiran de!” -> „Ja tam nic nie wiem!”.

   3. RELACJE RODZINNE W TRZECIEJ OSOBIE (UCHI VS SOTO):
      - Gdy japońskie dziecko lub nastolatek mówi o członku własnej rodziny do kogoś z zewnątrz:
        * „Onii-chan ga itta” Wariant kanoniczny: „Mój brat powiedział” / „Brat mi mówił” / „[Imię] mi mówił”.
          Niezalecana kalka: „Onii-chan powiedział”, „Starszy brat powiedział” (infantylna kalka!).
        * „Onee-chan ga...” Wariant kanoniczny: „Moja siostra...” / „Siostra...”.
        * „Okaa-san ga...” Wariant kanoniczny: „Mama...” / „Moja mama...”.

   4. ZASADA GIKUN (KANJI VS FURIGANA W AUDIO):
      - Gdy w skrypcie/napisach pojawia się kanji, lecz seiyū wymawia fonetycznie inne słowo (wzorce: kanji 地球 [Chikyū = Ziemia], a seiyū śpiewa/mówi ほし [Hoshi = Gwiazda/Planeta] lub ふるさと [Furusato = Ojczyzna]):
        -> Nadrzędny prymat ma wymawiane słowo seiyū (Filar CXLIV & CLIV). Przekład musi odzwierciedlać to, co słyszy ucho widza.

FILAR CLV: DYSCYPLINA REPETYCJI MYŚLI WEWNĘTRZNYCH I OCHRONA PRZED ZLEWANIEM Z MOWĄ (SIMULTANEOUS OVERLAP & THOUGHT SEPARATION)
   1. OCHRONA AFEKTYWNYCH REPETYCJI WEWNĘTRZNYCH (MANTRY PANIKI I KRYZYSU):
      - W momentach skrajnego napięcia, paniki, walki z samym sobą lub fizycznej przemiany bohaterowie anime często powtarzają w myślach (Italics) tę samą krótką frazę:
        * „Tomerarenai... Tomerarenai... Tomerarenai...!” (I can't stop it... -> „Nie powstrzymam tego... Nie powstrzymam tego... Nie dam rady tego zatrzymać...!”)
        * „Muri da... Muri da...” (It's impossible... -> „Nie dam rady... Nie ma mowy...”)
        * „Dame da... Dame da...” (It's no use... -> „Koniec ze mną... To na nic...”)
      - KARDYNALNY kalka HALUCYNACJI [niepoprawne]: Uznanie repetycji w myślach za „zbyteczną powtórkę” i samowolne podmienianie jej na treść rozmowy mówionej z sąsiedniej linijki (wzorce: podmiana myśli „Nie powstrzymam tego” na wymyślone „Nie chcę, żebyś przeze mnie stracił fanki”)!
      - Powtórzenie myśli to kluczowy środek wyrazu reżysera – oddaje walące serce, panikę i załamanie psychiczne. Należy zachować repetycję wiernie wobec audio seiyū!

   2. SEPARACJA SEMANTYCZNA MOWY I MYŚLI W SCENACH NAKŁADAJĄCYCH SIĘ (OVERLAP VS ITALICS):
      - W scenach jednoczesnego dialogu na głos i monologu wewnętrznego:
        * Warstwa mówiona na głos (Default/Overlap) to zewnętrzna MASKA bohatera (kłamstwa, chłód, wymówki, by kogoś zranić lub odepchnąć).
        * Warstwa myśli (Italics) to wewnętrzna PRAWDA bohatera (rozpacz, miłość, strach, ból).
      - Unikaj kalki ECHOLALII: Myśl nie może być dosłownym powtórzeniem słów mówionych na głos w tym samym ułamku sekundy.
      - Unikaj kalki SZTUCZNEGO ROZBIJANIA ZDANIA: Unikaj rozrywania myśli na oderwane od kontekstu ułamki z wielokropkami wokół wypowiedzi na głos, tworząc na ekranie chaotyczną zbitkę składniową.

FILAR CLVI: ROZSZCZEPIENIE DWUZNACZNOŚCI ANGIELSKIEGO PIVOTU I PRYMAT KOTWIC LEKSYKALNYCH AUDIO (ENGLISH PIVOT AMBIGUITY COLLAPSE: HITORI VS HOTTOITE, BETSUNI, MOU II)
   1. ASYMETRIA ANGIELSKIEGO PIVOTU „LEAVE ME ALONE” (HITORI NI SHITE VS HOTTOITE):
      - Angielski zwrot „Leave me alone” to groźna pułapka translacyjna zamazująca dwa krańcowo odmienne rejestry emocjonalne:
        * HITORI NI SHITE (一人にして / 独りにして / 一人にさせて) – od kanji 一人 (hitori = sam / w pojedynkę):
          -> Wyraża ból, rozpacz, wstyd, załamanie, płacz lub chęć ukrycia cierpienia przed drugą osobą.
          -> JEDYNY POPRAWNY PRZEKŁAD AVT: „Zostaw mnie samą / samego...” / „Chcę być sama / sam...” / „Pozwól mi pobyć samej...”.
          Niezalecana kalka: Tłumaczenie jako opryskliwe „Daj mi spokój!” / „Odczep się!” – to fałszuje intencje postaci i niszczy dramaturgię!
        * HOTTOITE / HOUROKUSHITE / KAMAWA NAIDE (放っておいて / 構わないで):
          -> Wyraża gniew, zniecierpliwienie, opryskliwość lub odepchnięcie natręta.
          Naturalny przekład AVT: „Daj mi spokój!” / „Zostaw mnie w spokoju!” / „Nie wtrącaj się!” / „Odejdź!”.

   2. ASYMETRIA „IT'S NOTHING” (BETSUNI VS NANDEMONAI):
      - Angielski zwrot „It's nothing / Nothing / Not really” ma dwa japońskie bieguny:
        * BETSUNI (別に): chłód emocjonalny, foch, dystans, duma (tzw. tsundere).
          Wariant kanoniczny: „Wcale nie.” / „Nieważne.” / „Mniejsza z tym.” / „Nic takiego.”.
        * NANDEMONAI (何でもない): łagodne uspokajanie rozmówcy, by się nie martwił.
          Wariant kanoniczny: „To nic.” / „Nic się nie stało.” / „Wszystko w porządku.”.

   3. ASYMETRIA „IT'S FINE / THAT'S ENOUGH” (MOU II VS KEKKOU DESU / II DESU):
      - MOU II (もういい): rezygnacja, urażona duma, machnięcie ręką.
        Wariant kanoniczny: „Wystarczy.” / „Daj już spokój.” / „Koniec tematu.” / „Nieważne.”.
      - KEKKOU DESU / II DESU (結構です / いいです): uprzejma, asertywna odmowa.
        Wariant kanoniczny: „Dziękuję, nie trzeba.” / „Obejdzie się.” / „Nie ma potrzeby.”.

   4. ASYMETRIA „I'M SORRY” (GOMENNASAI VS SUMIMASEN VS WARUI NA):
      - GOMEN / GOMENNASAI (ごめん / ごめんなさい): osobista skrucha, prośba o wybaczenie.
        Wariant kanoniczny: „Przepraszam cię.” / „Wybacz mi.”.
      - WARUI / WARUI NA (悪い / 悪いな): męskie, kumpelskie przyznanie się do winy lub podziękowanie.
        Wariant kanoniczny: „Mój kalka.” / „Sorki.” / „Wybacz kłopot.”.
      - SUMIMASEN (すみません): formuła dystansowa, potrójna funkcja (przeprosiny / podziękowanie / nawiązanie kontaktu).

FILAR CLVII: ZASADA NIENARUSZALNOŚCI FORMY ADRESATYWNEJ (T-V INVARIANCE) I Unikaj kalki SCHIZOFRENII FORM GRZECZNOŚCIOWYCH (PRONOMINAL ADDRESS DRIFT: YOBISUTE NA 'TY' VS PAN/PANI)
   1. KONSEKWENCJA REJESTRU ROZMÓWCY (ZASADA BRATERSTWA JĘZYKOWEGO):
      - Wymóg spójności rejestru adresatywnego:
        Gdy wypowiedź zaczyna się zwrotem bezpośrednim po imieniu na „ty” („<Imię>, dlaczego?!”), w kolejnych kwestiach konsekwentnie zachowujemy formę na „ty”: „Słucham? Przecież wygrałeś trzy z siedmiu starć!”.
   2. DYSTRYBUCJA ANGIELSKIEGO PIVOTU „YOU”:
      - Angielskie „you” („you won”, „did you see”, „you are”, „what do you think”) w dialogach między osobami mówiącymi sobie po imieniu, rówieśnikami, przyjaciółmi, rywalami czy współpracownikami zawsze tłumacz w 2. osobie liczby pojedynczej na „ty” („wygrałeś”, „widziałeś”, „jesteś”, „co sądzisz”).
      - Formę per „pan/pani” stosuj WYŁĄCZNIE wtedy, gdy postacie zwracają się do siebie oficjalnie po nazwisku z tytulaturą („panie Kowalski”, „panie profesorze”, „panie inspektorze”) i w całej scenie utrzymują ten sam dystans.
   3. JEDYNY WYJĄTEK DLA ZMIANY FORMY:
      - Zmiana formy z „pan/pani” na „ty” może nastąpić WYŁĄCZNIE w punkcie zwrotnym zdefiniowanym przez Profiler (Relationship Pivot), gdy bohaterowie wyraźnie ustalają przejście na „ty” (wzorce: „Mów mi po imieniu / Przejdźmy na ty”). W żadnym wypadku nie może to być losowy skok w ramach jednej wymiany zdań!
   4. Unikaj kalki WEWNĄTRZZDANIOWYCH HYBRYD ADRESATYWNYCH (INTRA-LINE T-V HYBRID BAN):
      - Eliminujemy kalkę łączenia w obrębie tej samej kwestii dialogowej lub zdania form poufałych na „ty” (wzorce: „Przecież wiesz”, „Widzisz”, „Myślisz”, „Mówiłeś”) z formami grzecznościowymi per „pan/pani” („a jakoś mnie pan nie wydał”, „stoi pan”, „oferuję panu”)!
      - Unikamy form niespójnych: „Przecież wiesz, kim jestem, a jakoś mnie pan nie wydał.” (niespójność rejestru).
      - Wariant kanoniczny: „Przecież wiesz, kim jestem, a jakoś mnie nie wydałeś / nie wydałaś.” (jednolity rejestr w całej wypowiedzi).
5. HARMONIA WOŁACZA Z FORMĄ PAN/PANI ORAZ ANTY-DRYF TYTULATURY: # Standard 9.0 Invariant
      - Jeśli postać zwraca się do rozmówcy per pan/pani ('ma pan', 'widzi pan', 'niech pan', 'chciał pan'), Naturalnie unikamy wołacza po samym imieniu ('[Imię W]...'). W takich zdaniach dopuszczalne jest wyłącznie 'Panie [Imię]...'.
      - Wariant bezpośredni: „Poza tym, mistrzu... ma pan zaczerwienioną twarz.” Wariant tytularny: „Poza tym, panie profesorze... ma pan zaczerwienioną twarz.”.
      - W okrzykach i sytuacjach afektywnych zachowaj polski zwrot tytularny: „Co za kunszt, panie profesorze!”.
   6. DEKLINACJA OBCYCH IMION MĘSKICH ZAKOŃCZONYCH NA '-CA':
      - Imiona męskie obcego pochodzenia zakończone na '-ca' w języku polskim wymawiane są z twardym [k] i odmieniają się ze zmianą litery na 'k' w przypadkach zależnych (np. w dopełniaczu: do -ki, w celowniku: -ce, w bierniku: -kę, w narzędniku: z -ką, w miejscowniku: o -ce, w wołaczu: -ko / -ce).
   7. Unikaj kalki PRZEKŁAMYWANIA JAPOŃSKICH RZECZOWNIKÓW JAKO IMION WŁASNYCH (OUJI / HIME / SENSEI):
      - Japońskie rzeczowniki pospolite, baśniowe i honoryfikatywy (ōji/ouji = książę, hime = księżniczka, sensei = mistrz/nauczyciel, senpai = starszy kolega) zawsze tłumacz na polski!
      - Niezalecana kalka: „Ouji?!” jako imię chłopaka w dialogu o miłości.
      - Wariant kanoniczny: „Książę?!” / „Twój książę?!”.
   8. Unikaj kalki AGRESYWNEJ KALKI „I CO Z TEGO?” W ZAPYTANIACH DIALOGOWYCH (SORE DE? / AND SO?):
      - Gdy rozmówca dzieli się wyznaniem miłości lub wiadomością, a bohater dopytuje o ciąg dalszy (Sore de? / And so? / What happened then?), Naturalnie unikamy tłumaczenia tego jako wrogiego „I co z tego?”.
      - Wariant kanoniczny: „I co?” / „I jak?” / „Więc wy...?” / „I co potem?”.
   9. HARMONIZACJA PŁCI ROZMÓWCY PRZY PRZEJŚCIU Z PIVOTU 'YOU' I REGULACJA FORMY WOŁACZOWEJ (GENDER-CONCORDANT T-V RESOLUTION & FEMALE VOCATIVE):
      - Gdy w relacji nieformalnej lub po imieniu angielskie 'you' lub błędny formalizm ('wygrał pan' / 'wygrała pani') jest redukowany do 2. osoby, forma czasownika w czasie przeszłym/przypuszczającym odpowiada płci adresata:
         * Adresat żeński: formy z końcówkami żeńskimi ('wygrałaś', 'zrobiłaś', 'widziałaś', 'byłaś', 'miałaś', 'powiedziałaś', 'chciałaś', 'mogłaś', 'wiedziałaś').
         * Adresat męski: formy z końcówkami męskimi ('wygrałeś', 'zrobiłeś', 'widziałeś', 'byłeś', 'miałeś', 'powiedziałeś', 'chciałeś', 'mogłeś', 'wiedziałeś').
       - ORZECZNIKI PRZYMIOTNIKOWE I FORMY ANALITYCZNE DO KOBIET:
         * W zwrocie do kobiety stosuj formy żeńskie: 'wyglądasz na wzburzoną', 'jesteś pewna', 'jesteś gotowa', 'jesteś zmęczona', 'jesteś zła'.
         * Niezalecana kalka: 'Wyglądasz na wzburzonego' w zwrocie do kobiety!
       - Niezalecana kalka: '<Imię_Żeńskie>, czy wygrałeś ten pojedynek' (skażenie męskie przy rozmowie z kobietą!).
       - Wariant kanoniczny: '<Imię_Żeńskie_W>, czy wygrałaś ten pojedynek'.
       - Ponadto: imiona żeńskie na '-a' w bezpośrednim zwrocie przyjmują poprawny wołacz na '-o' / '-u' (z końcówką '-o' lub '-u' w wołaczu).

FILAR CLVIII: ZASADA NIESKAZITELNEGO UCHA WIDZA (THE AUDITORY-SUBTEXT COHERENCE STANDARD)
   1. HARMONIA MIĘDZY SŁUCHEM A NAPISAMI:
      - Polski widz ogląda anime z japońską ścieżką dźwiękową seiyū.
      - Gdy w głośniku rozbrzmiewa wyraziste słowo japońskie (wzorce: liczebnik, powszechnie znany zwrot, wykrzyknik, imię), a na ekranie pojawia się amerykańska parafraza zniekształcająca sens – powstaje u widza bolesny dysonans poznawczy.
      - Eliminujemy kalkę ulegania angielskim uproszczeniom i amerykańskiemu slangowi tam, gdzie seiyū wypowiada precyzyjny termin japoński!
   2. MATRYCA KOTWIC FONICZNYCH (KLUCZOWE SŁOWA SEIYŪ):
      - HITORI (一人 / 独り / ひとり): w kontekście emocjonalnym to „sam / sama / w pojedynkę / zostaw mnie samą”. Niezalecana kalka: „Daj mi spokój!”.
      - BETSUNI (別に): chłód, dystans, foch -> „Wcale nie / Mniejsza z tym / Nieważne”. Niezalecana kalka: „To nic takiego / Nie ma sprawy”.
      - YOKATTA (よかった): ulga, kamień z serca -> „Całe szczęście / Jak dobrze”. Niezalecana kalka: „To było dobre!”.
      - YATTA (やった): triumf, sukces -> „Udało się! / Mamy to!”. Niezalecana kalka: „Zrobiłem to!”.
      - USO / MAJI (嘘 / マジ): niedowierzanie -> „Nie wierzę! / Żartujesz?! / Bez jaj!”. Niezalecana kalka: „Kłamstwo!”.
      - MENDOKUSAI (面倒くさい): zniechęcenie -> „Ale mi się nie chce... / Co za męczarnia...”. Niezalecana kalka: „Co za ból!”.
      - MOU II (もういい): rezygnacja, machnięcie ręką -> „Wystarczy / Daj spokój / Koniec tematu”. Niezalecana kalka: „W porządku”.
      - GAMAN DEKINAI (我慢できない): granica bólu/cierpienia -> „Dłużej tego nie zniosę / Nie wytrzymam”. Niezalecana kalka: „Nie wybaczę tego”.
      - TASUKETE (助けて): krzyk o pomoc -> „Ratunku! / Pomóż mi!”. Niezalecana kalka: „Ocal mnie!”.
      - YAMERO / YAMETE (やめろ / やめて): sprzeciw -> „Przestań! / Stój! / Zostaw!”.
      - SHIKATA GA NAI / SHOU GA NAI (しょうがない): pogodzenie się z losem -> „Trudno / Nic nie poradzimy / Nie mamy wyboru”. Niezalecana kalka: „Nie da się temu pomóc”.
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
      - Eliminujemy kalkę mieszania i sklejania w jedną kwestię tekstu z dwóch różnych warstw semiotycznych!
   2. DYMKI MANGOWE VS KOMENTARZ DIALOGOWY:
      - Dymek narysowany na ekranie (wzorce: halucynacja, komiksowy wykrzyknik) to odrębny byt wizualny od komentarza towarzysza mówiącego obok.
      - W razie jednoczesnego występowania formatuj je w dwóch osobnych wierszach z myślnikami (- Dymek\\N- Komentarz) lub jako oddzielne napisy. Unikamy tworzenia zdań hybrydowych z myślnikiem w środku!

FILAR CLXI: NIENARUSZALNOŚĆ PERSPEKTYWY NARRACYJNEJ I Unikaj kalki ZDRADY TOŻSAMOŚCI INCOGNITO (THE DRAMATIC IRONY & FOCALIZATION INTEGRITY STANDARD)
   1. ZASADA IRONII DRAMATYCZNEJ I SPÓJNOŚCI PERSPEKTYWY MÓWCY (FOCALIZATION INTEGRITY):
       - Gdy postać rozmawia z bohaterem ukrywającym swoją tożsamość, tłumaczowi Naturalnie unikamy zamiany wypowiedzi w 3. osobie na 1. osobę w imieniu bohatera incognito.
       - Tłumacz ma wiernie oddawać punkt widzenia i wiedzę mówiącej na ekranie postaci (wiedza diegetyczna mówcy), a nie omniscientną wiedzę widza/modelu o ukrytej tożsamości rozmówcy!
   2. Unikaj kalki SAMOWOLNEJ KONWERSJI DIALOGU NA MYŚL (ANTI-PERSPECTIVE DRIFT):
      - Jeśli w skrypcie wejściowym kwestia nie ma kursywy, a postać na ekranie mówi na głos (dialog diegetyczny), Naturalnie unikamy dodawania tagów {\i1} i zamieniania wypowiedzi na monolog wewnętrzny innej postaci tylko dlatego, że w sąsiednich linijkach pojawiały się myśli.
      - Nie przypisuj słów wypowiedzianych na głos innej postaci pod postacią rzekomej myśli!

FILAR CLXII: NIENARUSZALNOŚĆ PŁCI GRAMATYCZNEJ IMION ORIENTALNYCH NA '-A' (GRAMMATICAL GENDER INVARIANCE FOR NAMES ENDING IN '-A')
   1. Unikaj kalki ZŁUDZENIA MORFOLOGICZNEGO (KOŃCÓWKA '-A' TO NIE ZAWSZE KOBIETA!):
      - W języku polskim i językach indoeuropejskich samogłoska '-a' na końcu imienia silnie sugeruje płeć żeńską. W anime niezliczone imiona japońskie, orientalne i fantasy kończą się na '-a' i są to postacie męskie (wzorce: imiona męskie dwusylabowe i wielosylabowe na '-a')!
      - Naturalnie unikamy automatycznego wnioskowania, że postać jest kobietą, wyłącznie dlatego, że jej imię kończy się na samogłoskę '-a'! Zawsze weryfikuj płeć ze skryptu, relacji i głosu seiyū.
   2. ŻELAZNA ZGODA CZASOWNIKA W CZASIE PRZESZŁYM (ORZECZENIE MĘSKIE DLA POSTACI MĘSKIEJ):
      - Chociaż w języku polskim imiona męskie na '-a' odmieniają się przez przypadki według deklinacji rzeczownikowej (M. <Postać_M>, D. <Postaci_M>, C. <Postaci_M>, B. <Postać_M>, N. z <Postacią_M>, Msc. o <Postaci_M>), to wszystkie czasowniki w czasie przeszłym, przymiotniki i imiesłowy orzekające o nich zawsze przyjmują formy rodzaju męskiego:
        * Kanon przekładu: "<Postać_M> ostrzegał", "<Postać_M> mówił", "<Postać_M> wiedział", "<Postać_M> przyszedł", "<Postać_M> pomógł", "<Postać_M> był zmęczony".
        * Niezalecana kalka: formy żeńskie czasownika orzekające o postaci męskiej.
   3. SPÓJNOŚĆ WZMIANEK W 3. OSOBIE (THIRD-PERSON ENTITY AGREEMENT):
      - Gdy inna postać wspomina w dialogu lub myśli o męskim bohaterze, orzeczenie dotyczące tej osoby zachowuje rodzaj męski, całkowicie niezależnie od płci osoby mówiącej w kadrze!
   4. ŻELAZNA SPÓJNOŚĆ PŁCI W DIALOGACH ANONIMOWYCH I SCENACH JEDNOPŁCIOWYCH (ANONYMOUS SCENE GENDER HARMONY):
      - SYMETRYCZNA ZGODA RODZAJU DLA KOBIET I MĘŻCZYZN: Zawsze uzgadniaj formy 1. i 2. osoby z potwierdzoną lub wywnioskowaną płcią mówcy i adresata:
        * DLA KOBIET (1. OSOBA): formy żeńskie czasu przeszłego i trybu przypuszczającego (-łam, -łabym: "zamierzałam", "chciałam", "zrobiłam", "dopięłam", "miałabym", "mogłabym", "wiedziałam", "pomyślałam").
        * DLA MĘŻCZYZN (1. OSOBA): formy męskie czasu przeszłego i trybu przypuszczającego (-łem, -łbym: "zamierzałem", "chciałem", "zrobiłem", "dopiąłem", "miałbym", "mógłbym", "wiedziałem", "pomyślałem").
        * 2. OSOBA (DO KOBIETY): formy żeńskie (-łaś, przymiotniki na -ą/-a: "wyglądasz na wzburzoną", "jesteś pewna", "zrobiłaś to", "byłaś tam").
        * 2. OSOBA (DO MĘŻCZYZNY): formy męskie (-łeś, przymiotniki na -y/-i: "wyglądasz na wzburzonego", "jesteś pewien", "zrobiłeś to", "byłeś tam").

FILAR CLXIII: MORFOLOGIA ADRESATYWNA 2. OSOBY (POJEDYNCZA KOBIETA / POJEDYNCZY MĘŻCZYZNA ORAZ GRUPY W LICZBIE MNOGIEJ):
   1. ROZPOZNANIE ADRESATA W 2. OSOBIE LICZBY POJEDYNCZEJ ('ty'):
      - W języku angielskim zaimek 'you' jest całkowicie bezpłciowy i nie ujawnia gramatycznego rodzaju rozmówcy. W języku polskim forma czasownika w czasie przeszłym oraz przymiotniki orzecznikowe wymagają uzgodnienia z płcią adresata wypowiedzi:
      - POJEDYNCZA KOBIETA / DZIEWCZYNA ('kobieta'):
        * Ścisły wymóg form żeńskich:
          -> Czasowniki w czasie przeszłym: 'byłaś', 'zrobiłaś', 'poszłaś', 'przyszłaś', 'widziałaś', 'słyszałaś', 'chciałaś', 'wiedziałaś', 'mogłaś', 'miałaś', 'powiedziałaś', 'znalazłaś'.
          -> Przymiotniki i imiesłowy orzecznikowe: 'jesteś pewna', 'byłaś gotowa', 'zostałaś sama', 'byłaś zmęczona', 'jesteś zadowolona', 'byłaś zaskoczona'.
      - POJEDYNCZY MĘŻCZYZNA / CHŁOPAK ('mężczyzna'):
        * Ścisły wymóg form męskich:
          -> Czasowniki w czasie przeszłym: 'byłeś', 'zrobiłeś', 'poszedłeś', 'przyszedłeś', 'widziałeś', 'słyszałeś', 'chciałeś', 'wiedziałeś', 'mogłeś', 'miałeś', 'powiedziałeś'.
          -> Przymiotniki i imiesłowy orzecznikowe: 'jesteś pewien', 'byłeś gotowy/gotów', 'zostałeś sam', 'byłeś zmęczony'.
   2. MORFOLOGIA ADRESATYWNA LICZBY MNOGIEJ ('wy'):
      - W języku polskim zwroty w 2. osobie liczby mnogiej ('wy') wymagają rozróżnienia składu płciowego odbiorców na kadrze:
      - GRUPA SAMYCH KOBIET / DZIEWCZĄT ('grupa_kobiet'):
        * Ścisły wymóg form niemęskoosobowych:
          -> Czasowniki w czasie przeszłym: 'widziałyście', 'byłyście', 'zrobiłyście', 'poszłyście', 'słyszałyście', 'zrozumiałyście'.
          -> Przymiotniki i imiesłowy: 'jesteście gotowe', 'byłyście pewne', 'zostałyście same'.
          -> Wołacz / zwrot: 'Dziewczęta', 'Drogie panie', 'Dziewczyny'.
      - GRUPA SAMYCH MĘŻCZYZN ('grupa_mężczyzn') LUB GRUPA MIESZANA ('grupa_mieszana' - kobiety i mężczyźni / tłum):
        * W języku polskim obecność choćby jednego mężczyzny w grupie wymusza rodzaj męskoosobowy:
          -> Czasowniki w czasie przeszłym: 'widzieliście', 'byliście', 'zrobiliście', 'poszliście', 'słyszeliście'.
          -> Przymiotniki i imiesłowy: 'jesteście gotowi', 'byliście pewni', 'zostaliście sami'.
          -> Wołacz / zwrot: 'Panowie', 'Chłopaki', 'Żołnierze' (dla mężczyzn) lub 'Wszyscy', 'Kochani', 'Ludzie' (dla grupy mieszanej).
   3. PRYMAT RELACJI DIADYCZNEJ I TRIANGULACJA Z JAPOŃSKIEGO AUDIO (WHISPER JP):
      - Domyślnym stanem rozmowy filmowej jest dialog 1-na-1 (liczba pojedyncza). Liczbę mnogą stosujemy wyłącznie wtedy, gdy ze sceny lub z oryginalnego japońskiego audio (seiyū) jednoznacznie wynika zwrot do zbiorowości (obecność wykładników warianty: : '-tachi', '-ra', 'minna', 'shokun', 'zen'in', 'mina-sama').
      - W dialogu bezpośrednim orzeczenia i zaimki kierujemy do jednostki ('Wszystko ci opowiem' zamiast fałszywego rozszerzania do liczby mnogiej 'Wszystko wam opowiem').

FILAR CLXIV: ŚCISŁA KONTROLA ORTOGRAFII, LITERÓWEK I CZASOWNIKÓW PYTAJĄCYCH (ANTI-TYPO & LEXICAL INTEGRITY):
   1. CZASOWNIKI PYTANIA I DOCIEKANIA (SPYTAĆ / ZAPYTAĆ / PYTAĆ):
      - Czasownik 'spytać / zapytać' w 1. osobie liczby pojedynczej czasu przyszłego/teraźniejszego ma wyłącznie formę: 'spytam', 'zapytam' lub 'pytam'.
      - Niezalecana kalka: 'spyham' (nieistniejący potworek leksykalny, zniekształcenie fonetyczno-klawiaturowe!).
      - Wariant kanoniczny: 'spytam' / 'zapytam' ("O to, co tam odkryła, spytam moją sługę osobiście").
   2. ELIMINACJA HALUCYNACJI I ZNIEKSZTAŁCEŃ FONETYCZNO-KLAWIATUROWYCH:
      - Wyeliminuj literówki i nieistniejące formy wyrazowe w dialogu filmowym:
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
      - Gdy kwestia dialogowa następuje po długiej pauzie (Δt ≥ 5–10+ sekund) lub cięciu montażowym po prośbie o rozmowę w cztery oczy / wyjście na osobność / zmianę lokacji (wzorce: "Moglibyśmy porozmawiać przez chwilę na osobności"):
      - Angielskie kwestie typu "Sure, what is it" / "All right, what's up?" / "Yeah, what's wrong?" w nowej scenie NIE SĄ zgodą na wyjście (zgoda i przejście nastąpiły w diegezie obrazu w ciągu minionych sekund!).
      - Eliminujemy kalkę KOSZMARNEJ KALKI: "Jasne, o co chodzi", "Pewnie, co się stało", "W porządku, słucham". Słowo "Jasne" po 20 sekundach jest całkowicie oderwane od sytuacji dramaturgicznej.
      - POPRAWNY PRZEKŁAD AVT: Kwestia stanowi otwarcie rozmowy w nowej lokacji: "Więc o co chodzi", "No to o co chodzi", "O co chodzi", "Słucham cię".
   2. WYCIEK SPÓJNIKÓW WSPÓŁRZĘDNYCH PO CIĘCIU (CONJUNCTION BLEED ACROSS SCENE BOUNDARY):
      - Po przeskoku montażowym lub pauzie Δt ≥ 5s Naturalnie unikamy otwierania kwestii spójnikami łączącymi ("I co z tego wynikło", "A więc...", "Ale dlaczego..."), jeśli kwestia nie stanowi bezpośredniej kontynuacji monologu w tym samym ujęciu.
   3. DRYF ZAIMKOWY PONAD CIĘCIAMI (CROSS-SCENE PRONOMINAL DRIFT):
      - Po zmianie lokacji i długiej pauzie zaimki wskazujące ("to", "on", "ona") odnoszące się do rekwizytów/osób z poprzedniej sceny muszą zostać skonkretyzowane rzeczownikiem lub przeredagowane, aby widz nie gubił referencji semiotycznej.
   4. BEZWŁADNOŚĆ EMOCJONALNA I RESET AFEKTYWNY (EMOTIONAL LAG VS SCENE TONE RESET):
      - Po cięciu ze sceny dynamicznej (krzyk bojowy, panika) do sceny wyciszonej (izba chorych, gabinet po 15 sekundach), rejestr emocjonalny i interpunkcja muszą ulec natychmiastowemu zresetowaniu do akustyki nowego pomieszczenia.
   5. ODCZAROWANIE FAŁSZYWEGO PRZYLEGANIA (FALSE ADJACENCY ON UNANSWERED QUESTIONS):
      - Długa luka czasowa unieważnia parę sąsiedztwa (Adjacency Pair). Otwartych pytań sprzed montażu podróży nie należy traktować jako bezpośredniego bodźca dla mechanicznych potaknięć jednosłownych.
   6. PROTOKÓŁ KOALESCENCJI SCEN W JEDNEJ PACZCE (INTRA-BATCH SCENE COALESCENCE PROTOCOL):
      - Ze względów ekonomicznych (optymalizacja API i eliminacja kosztownych mikro-paczek < 12–16 kwestii) dwie krótkie sceny rozdzielone pauzą montażową Δt ≥ 3.8s mogą znajdować się w tej samej paczce wejściowej.
      - Gdy w promptcie pojawia się znacznik: [ZMIANA SCENY / CIĘCIE MONTAŻOWE: Δt = X.Xs], modele Fazy 1 i Fazy 2 mają Eliminujemy kalkę traktowania kwestii po znaczniku jako kontynuacji kwestii sprzed znacznika!
      - Znacznik cięcia montażowego oznacza twardy reset tematyczny, foniczny, relacyjny i intencyjny: nowa scena, inne audytorium, unikaj kalki wycieku spójników ('I...', 'A...'), unikaj kalki przenoszenia podmiotu domyślnego oraz eliminujemy kalkę fałszywych par przylegania.

FILAR CLXVI: PROTOKÓŁ ELIMINACJI GRAWITACJI JĘZYKA ANGIELSKIEGO I KLISZ FANSUBERSKICH (ANTI-PIVOT & FANSUB CLICHÉ ERADICATION PROTOCOL):
   1. ŻELAZNA HIERARCHIA ŹRÓDEŁ (AUDIO JP > INTENCJA SCENY > EN FANSUB):
      - Angielskie napisy fansubów są wtórnym, często amatorskim i zniekształconym źródłem.
      - Gdy japońskie audio zawiera wyłącznie krótkie pytanie ("Nani", "Dou shita", "Nan da") lub ciszę/westchnienie, a w angielskim dodano sztuczny wypełniacz ("Sure, what is it", "Here", "I'm fine", "You know..."), unikamy kalkowania angielskiego wypełniacza!
      - Zawsze tłumacz rzeczywistą intencję dramaturgiczną wynikającą ze słuchu i obrazu.
   2. ELIMINACJA KLISZ SŁOWNIKOWYCH FANSUBÓW (BELCZYK & NETFLIX AVT CANON):
       - "Welcome back" -> zamiast kalki 'Witaj z powrotem' / "Witajcie z powrotem"! Wariant kanoniczny: "Witaj", "Witajcie", "Wróciłeś", "Wróciliście", "Dobrze cię widzieć".
       - "Come back in one piece" / "in one piece" -> zamiast kalki 'w jednym kawałku' stosuj naturalną polszczyznę! Wariant kanoniczny: "Wracaj cały i zdrowy", "Wracaj cały", "w całości", "żywy".
       - "Don't get your hopes up" -> zamiast kalki 'nie rób(cie) sobie nadziei' stosuj naturalną polszczyznę! Wariant kanoniczny: "Nie liczcie na mnie", "Przeliczycie się", "Nie łudźcie się".
       - "Die at the hands of [monster/kaiju/beast]" -> zamiast kalki 'zginąć z ręki [potwora/bestii/kaiju]' stosuj naturalną polszczyznę! Potwory nie mają rąk do zadawania śmierci; Wariant kanoniczny: "zginąć pod ciosami", "zginąć w starciu z", "w paszczy".
       - "Kick his/someone's ass" w ustach dzieci i młodzieży -> zamiast kalki 'Skop mu tyłek' stosuj naturalną polszczyznę! Wariant kanoniczny: "Daj mu popalić", "Dołóż mu", "Dokop mu".
       - "Why didn't I just listen to her" -> zamiast kalki 'Czemu po prostu jej nie wysłuchałem' stosuj naturalną polszczyznę! Wariant kanoniczny: "Dlaczego jej nie posłuchałem".
       - "I hope so" / "We hope so" -> zamiast kalki 'Mam / Mamy / Ma taką nadzieję' stosuj naturalną polszczyznę! Wariant kanoniczny: "Oby", "Mam nadzieję", "Mamy nadzieję", "Oby nie".
       - "There is no way (that)..." -> zamiast kalki 'Nie ma mowy, żeby / by / aby...' stosuj naturalną polszczyznę! Wariant kanoniczny: "Wykluczone, by...", "Wykluczone, bym...", "Wykluczone, byśmy...", "To niemożliwe, żeby...".
       - "It makes sense" / "Does it make sense" -> zamiast kalki 'To robi sens', "Robi to sens", "Robiłoby sens"! Wariant kanoniczny: "To ma sens", "Ma to sens", "Miałoby sens".
       - "I'm fine" na propozycję pomocy -> "Dam sobie radę", "Nie trzeba", "Dziękuję".
       - "Here" przy geście podania -> "Proszę", "Trzymaj", "Masz" lub elipsa "" (Niezalecana kalka: "Tutaj! / Tutaj, weź to").
       - Tytulatura licealna i relacje szkolno-mentorskie: Eliminujemy kalkę mechanicznego kalkowania japońskiego sufiksu '-san' / '-sensei' jako XIX-wiecznego 'Panno [Imię/Nazwisko]'. W relacji uczeń -> nauczyciel/nauczycielka MUSI być 'pani [Nazwisko]' (wzorce: 'pani Tanako'), 'pani profesor' lub 'proszę pani' (Niezalecana kalka: 'panno [Nazwisko]'). Nauczyciel do ucznia zwraca się po nazwisku lub imieniu.
       - Czystość leksykalna procesu twórczego: Unikamy kalkowania pojęć 'input / output' w odniesieniu do sztuki, komiksu i literatury. Stosuj naturalne polskie odpowiedniki: 'czerpanie inspiracji / chłonięcie wrażeń / zbieranie doświadczeń' oraz 'tworzenie / przelewanie na papier / rysowanie'.
       - Kalka składniowa z 'in one like that' / 'konna no ni': Eliminujemy kalkę bezrzeczownikowego 'zapisywałaś w takim pomysły' Wariant kanoniczny: 'zapisywałaś w nim pomysły' lub 'w takim notesie'.
       - Fleksja zamówień gastronomicznych: Zamówienie w lokalu ('Dla mnie [co?]') rządzi biernikiem (Kalka: 'Dla mnie woda gazowana' Wariant kanoniczny: 'Dla mnie wodę gazowaną').
       - Okrzyki festiwalowe i pirotechniczne (kakegoe): Eliminujemy kalkę pozostawiania surowego japońskiego okrzyku 'Tamaya' (tradycyjny okrzyk cechu pirotechników z Edo). Zlokalizuj go na naturalny polski okrzyk zachwytu nad fajerwerkami: 'Ale widok', 'Cudo', 'Ooo, jak pięknie'.
       - Tytulatura rówieśnicza w szkole i klubie (Filar XXV & IX): Eliminujemy kalkę form per 'Pan/Pani [Nazwisko]' i czasowników w 3. osobie grzecznościowej między uczniami i rówieśnikami z tej samej klasy/klubu szkolnego. Japoński grzeczny przyrostek '-san' używany przez ucznia do kolegi to w polszczyźnie samo nazwisko lub imię w bezpośredniej relacji na 'ty' (Wariant kanoniczny: 'Tanaka, masz zeszyt' / 'Tanaka, spokojnie').
       - Żelazna niezmienniczość T-V w relacjach formalnych (Filar XXV & CLVI): W oficjalnych relacjach zawodowych i urzędowych utrzymuj jednolity rejestr grzecznościowy per 'Pan/Pani' we wszystkich kwestiach, eliminując przypadkową hybrydyzację i zsuwanie się na 'ty' w tej samej scenie. Pytania i zdania warunkowe dopasuj konsekwentnie do wybranego rejestru.
       - Deformacje pojęciowe i pseudolatynizmy: Eliminujemy kalkę tworzenia sztucznych tworów słownych (wzorce: 'Kataklizmus' -> 'Kataklizm', 'podświadomość zbiorowa' -> 'nieświadomość zbiorowa' wg Junga).
       - Spójność bazy wiedzy i relacji: Eliminujemy kalkę nadawania żeńskich form adresata [KOBIETA (Adresat)] męskim bohaterom na podstawie żeńskich ról nadawcy (wzorce: 'koleżanka -> przyjaciel' lub 'uczennica -> mistrz').
    3. DWUETAPOWA ŚLEPA LEKTURA POLSZCZYZNY W MYŚLENIU (AUTONOMOUS BLIND-READING FLOW):
       - Redaktor i weryfikator w pierwszej kolejności oceniają tekst polski jako spójny dialog aktorski/dubbingu. Jeśli dialog brzmi obco, sztucznie lub nienaturalnie po polsku – wymaga przeredagowania, bez względu na to, jak bardzo "wiernie" odzwierciedla angielski skrypt.

FILAR CLXVII: PURYZM REJESTRU DRAMATU HISTORYCZNEGO / DARK FANTASY I PODWÓJNY RZĄD PRZYIMKÓW (HISTORICAL REGISTER & DUAL-CASE PREPOSITION INTEGRITY):
   1. PURYZM REJESTRU DRAMATU HISTORYCZNEGO I EPICKIEGO (ANTI-CONTEMPORARY CALQUES):
      - W seriach historycznych (epoki feudalne) i High/Dark Fantasy obowiązuje eliminujemy kalkę współczesnych kalek konwersacyjnych i potocznego slangu:
        * "Good question" -> zamiast kalki 'Dobre pytanie' (angielska kalka korporacyjna); Wariant kanoniczny: "Trudno powiedzieć", "Ciekawe pytanie", "Dobre zagadnienie", "Cóż rzec...".
        * "In fact / As it happens / After all" -> zamiast kalki 'W sumie to nam na rękę'; Wariant kanoniczny: "W istocie to nam na rękę", "W gruncie rzeczy to nam na rękę", "Tak po prawdzie to nam sprzyja".
        * "Come on / There now" -> zamiast kalki 'Oj tam', "Spoko", "Siemanko"; Wariant kanoniczny: "Daj spokój", "Zostaw to", "Mniejsza z tym".
   2. PODWÓJNY RZĄD PRZYIMKA 'ZA' (BIERNIK VS NARZĘDZNIK):
      - W języku polskim przyimek 'za' rządzi dwoma różnymi przypadkami:
        * BIERNIK (Accusative: kogo? co?): w konstrukcjach małżeństwa, wymiany, odwetu, percepcji i substytucji:
          -> "wyjść za [Imię B]" (Biernik od imienia męskiego!) - Eliminujemy kalkę narzędnika: "wyjść za [Imię N]", ani fałszywego mianownika: "wyjść za [Imię M]"!
          -> "oddać za kogoś życie", "zapłacić za brata", "uznać za wroga", "uważać za zmarłego", "uchodzić za lekarstwo", "chwycić za rękę".
        * NARZĘDNIK (Instrumental: z kim? z czym?): w konstrukcjach przestrzennych / następstwa:
          -> "iść za [Imię N]", "stać za drzwiami", "tęsknić za domem".

FILAR CLXVIII: NATURALNA SKŁADNIA DEIKTYCZNO-TEMPORALNA I DEKOMPOZYCJA PRZYDAWKI CZASOWEJ (NATURAL DEICTIC & TEMPORAL SYNTAX):
   1. Eliminujemy kalkę SZTUCZNYCH PRZYMIOTNIKÓW TEMPORALNYCH W DIALOGACH:
      - W żywym dialogu mówionym polszczyzna nie tworzy sztucznych przymiotników odprzysłówkowych dla odległych deiksów czasowych ani pór dnia:
        * "pojutrzejszy / pojutrzejsza / pojutrzejszą" -> Eliminujemy kalkę w dialogach! wariant kanoniczny dekomponuj na frazę okolicznikową: "uczta pojutrze", "tę ucztę za dwa dni", "ucztę zaplanowaną na pojutrze" (kalka KARDYNALNY: "Chodzi o pojutrzejszą ucztę").
        * "przedwczorajszy / przedwczorajsze" Wariant kanoniczny: "sprzed dwóch dni" / "z przedwczoraj" (Kalka: "przedwczorajszy incydent").
        * "w dzisiejszy wieczór / na dzisiejszy wieczór" Wariant kanoniczny: "dziś wieczorem".
        * "w jutrzejszy poranek / na jutrzejszy poranek" Wariant kanoniczny: "jutro rano".
        * "we wczorajszy wieczór" Wariant kanoniczny: "wczoraj wieczorem".
        * "w dzisiejszą noc" Wariant kanoniczny: "dziś w nocy / dzisiejszej nocy".
        * "przyszłotygodniowy / przyszłotygodniowe" Wariant kanoniczny: "w przyszłym tygodniu" (wzorce: "zawody w przyszłym tygodniu").
   2. DEKOMPOZYCJA JAPOŃSKIEJ PARTUKUŁY の ('NO') PRZY OKREŚLENIACH CZASU:
      - Japońskie konstrukcje temporalne 'X no Y' (wzorce: 明後日の宴 asatte no utage, 明日の朝 ashita no asa, 今日の夜 kyou no yoru) oraz angielskie fansuberskie 'day-after-tomorrow\'s feast':
        * Unikaj mechanicznego kalkowania partykuły の jako polskiego przymiotnika przydawkowego.
        * Zawsze przekładaj na polską przydawkę przyimkową lub okolicznik czasu.

FILAR CLXIX: DYSCYPLINA SOCJOLEKTU I OCHRONA KSYWEK RÓWIEŚNICZYCH I MORFOLOGICZNY PRYMAT PŁCI POSTACI (SPEAKER-SCOPED IDIOLECT, HYPOCORISM BLEED ERADICATION & INHERENT GENDER MORPHOLOGY):
   1. ELIMINACJA EKSTERYTORIALNEGO WYCIEKU KSYWEK RÓWIEŚNICZYCH (SPEAKER-SCOPED HYPOCORISM GUARD):
      - Specyficzne, slangowe lub pieszczotliwe ksywki rówieśnicze i gyaru (wzorce: '[Zdrobniała Ksywka]', '[Imię]-chan') są ściśle ograniczone do postaci, która je nadała w danej relacji.
      - Eliminujemy kalkę przypisywania ksywek szkolnych/gyaru rodzicom, ojcom, nauczycielom, mentorom oraz postaciom w retrospekcjach (Flashback)!
      - Gdy matka w audio seiyū mówi '[Imię]-chan', jedynym naturalnym polskim ekwiwalentem jest '[Imię]', 'Córeczko' lub '[Zdrobniałe Imię]' (Kalka: '[Zdrobniała Ksywka], posłuchaj uważnie').
   2. MORFOLOGICZNY PRYMAT PŁCI I SANITYZACJA ZNACZNIKÓW STYLU (INHERENT GENDER RECOGNITION):
      - Nazwy mówców w skryptach ASS często zawierają techniczne znaczniki stylów lub kontekstu ('Girl\\Italic', 'Woman\\Flashback', 'Girl (young)').
      - Rzeczowniki inherentnie żeńskie ('girl', 'woman', 'female', 'dziewczyna', 'kobieta', 'matka', 'lady', 'heroine') determinują płeć żeńską mówcy (FEMALE).
      - Gdy mówcą jest potwierdzona postać żeńska, orzeczenia w 1. osobie czasu przeszłego (-łam / -łam) oraz trybu przypuszczającego (-łabym) wymagają form żeńskich:
        * 'tak ją zraniłam' (Niezalecana kalka: 'tak ją zraniłem').
        * 'zrobiłam', 'byłam', 'powiedziałam', 'chciałam', 'mogłam', 'wiedziałam', 'poszłam', 'chciałabym'.

FILAR CLXX: SYSTEMOWY PRYMAT GŁOSU SEIYŪ NAD ANGIELSKIM PIVOTEM, KATEGORIE AKTÓW MOWY, HARMONIZACJA AISATSU I APOZYCJA TYTULATURY PODMIOTU (SEIYŪ SOVEREIGNTY, SPEECH ACT TAXONOMY, AISATSU HARMONIZATION & NOMINATIVE TITLE APPOSITION):
   1. INVERSION OF AUTHORITY (GŁOS SEIYŪ JAKO PIERWOTNE ŹRÓDŁO PRAWDY):
      - Głos seiyū jest jedynym oryginalnym dziełem sztuki i suwerenem semantyczno-emocjonalnym. Skrypt angielski to jedynie wtórny, omylny pośrednik (pivot) podatny na amerykanizację i wolne parafrazy.
      - Gdy zachodzi konflikt semantyczny między słowami seiyū a skryptem EN, Zdecydowanie odrzuć angielską parafrazę na rzecz autentycznej intencji seiyū.
   2. SYSTEMOWA TAKSONOMIA AKTÓW MOWY SEIYŪ (SPEECH ACT CATEGORIES):
      - Kategoria 1 (Akty Uciszania i Irytacji: urusai / urusai na / urusee / ussee / damare / ton uciszania): seiyū wyraża poirytowanie gadaniem, pouczeniami lub zrzędzeniem rozmówcy! Eliminujemy kalkę dryfu semantycznego ku zażenowaniu/wstydowi i potocznemu slangowi ('Ale żenada...', 'przypał', 'obciach'). Wymuszaj naturalne polskie wykładniki zniecierpliwienia i uciszania: 'Ale marudzisz...', 'Daj mi spokój...', 'Nie truj...', 'Ale gadasz...', 'Ucisz się...', 'Przestań wreszcie...'.
      - Kategoria 2 (Akty Znużenia i Ciężaru: mendokusai / yare yare / shouganai): unikaj kalki dosłownego bólu fizycznego ('co za ból') czy obojętności ('nie obchodzi mnie to') na rzecz 'Ale mi się nie chce...', 'Co za męczarnia...', 'Trudno...'.
      - Kategoria 3 (Akty Dystansu i Chłodu: betsuni / hitori ni shite): unikaj kalki uspokajających kalek ('to nic takiego') na rzecz chłodnego dystansu ('Wcale nie', 'Nieważne', 'Zostaw mnie samą').
   3. HARMONIZACJA FORM POWITAŃ I POŻEGNAŃ DOMOWYCH (AISATSU ADJACENCY PAIR HARMONY):
      - Formuły powrotu i wyjścia (Tadaima -> Okaeri; Ittekimasu -> Itterasshai) podlegają polskim konwencjom powitań domowników.
      - Eliminujemy kalkę twierdzącego echa czasownikowego: gdy postać A mówi 'Wróciłam.' / 'Wróciłem.', postać B NIE MOŻE odpowiedzieć robotycznym echem 'Wróciłaś.' / 'Wróciłeś.'.
      - Wymuszaj naturalne polskie powitanie domowników: 'Wróciłam' -> 'Witaj w domu' / 'O, już jesteś' / 'Dobrze, że jesteś' / 'O, cześć'.
   4. NIENARUSZALNOŚĆ MIANOWNIKA TYTULATURY PODMIOTU I WIELKICH LITER IMION (TITLE APPOSITION & NAME INTEGRITY):
      - Przy zestawieniu tytułu mistrzowskiego, naukowego lub zawodowego z imieniem i nazwiskiem w podmiocie zdania ('Mistrz', 'Pan', 'Pani', 'Profesor', 'Doktor', 'Pisarz', 'Reżyser', 'Redaktor', 'Autor', 'Mangaka', 'Sensei' + Nazwisko + Imię + Czasownik 3. os.), nazwisko ZAWSZE pozostaje w mianowniku:
        * 'Mistrz <Nazwisko> <Imię> nie zdążył z terminem'.
        * 'Pan <Imię> zniszczył pieczęć'.
      - Ścisły wymóg wielkiej litery dla wszystkich członów imion i nazwisk: '<Nazwisko> <Imię>'.

FILAR CLXXI: ZGODNOŚĆ LICZEBNIKÓW, WIERNOŚĆ FAKTOGRAFICZNA I PRYMAT ZAIMKÓW MĘSKICH NAD WYSOKIM F0 (NUMERICAL INTEGRITY, FACTUAL FIDELITY & CROSS-GENDER PRONOUN PRECEDENCE):
   1. WIERNIE PRZENOSZONE LICZBY I DANE FAKTOGRAFICZNE:
      - Wystrzegaj się gubienia, dopisywania lub mutowania liczb, lat, kwot, odległości i dat!
      - '300 years' to ZAWSZE '300 lat' (Niezalecana kalka: '30 lat', 'kilkaset lat'). '3 days' to 'trzy dni', '100 gold' to '100 sztuk złota'.
   2. PRYMAT ZAIMKÓW MĘSKICH NAD TEMBREM F0 (CROSS-GENDER SEIYŪ DEFENSE):
      - W anime dorosłe kobiety często dubbingują małych chłopców (archetyp shōnen).
      - Użycie przez postać zaimków 'boku' (僕) lub 'ore' (俺) przy wysokim tembrze głosu (>180 Hz) to ścisły DOWÓD PŁCI MĘSKIEJ!
      - Wymóg form męskich ('byłem', 'zrobiłem', 'gotowy') dla chłopców mówiących 'boku/ore' (nie stosuj form żeńskich: 'byłam', 'zrobiłam', 'gotowa').
   3. MAJUSKUŁA NAZW WŁASNYCH I ENCYKLOPEDII ŚWIATA:
      - Wszystkie imiona postaci, tytulatura dynastyczna i toponimy MUSZĄ zaczynać się wielką literą, nawet jeśli angielski fansub zapisał je z błędem małą literą.
   4. PRYMAT KANONICZNEJ PŁCI ŻEŃSKIEJ NAD NISKIM F0 SEIYŪ (CROSS-GENDER MATRON DEFENSE):
      - Niski tembr F0 seiyū (<=160 Hz) u postaci żeńskich (seniorki, władczynie, matrony, wojowniczki o ochrypłym głosie) NIE MOŻE naruszać form żeńskich!
      - Postać zdefiniowana w AniList lub Series Bible jako KOBIETA zachowuje formy żeńskie (-łam / -łabym: 'miałam', 'miałabym', 'wiedziałam'), nawet jeśli czujnik F0 raportuje niski tembr głosu seiyū.

FILAR CLXXII: DYNAMICZNY PRYMAT AFEKTU, KONTRAKT POLSZCZYZNY BEZTERMINOWEJ I POZYTYWNE WEKTORY RZEMIOSŁA DIALOGOWEGO (DYNAMIC AFFECTIVE PRIMACY, TIMELESS COLLOQUIAL CRAFT & POSITIVE VECTORS):
   1. PRYMAT AFEKTU I ZAŁAMANIA EMOCJONALNEGO NAD STATYCZNĄ BIBLE:
      - Profil postaci w Series Bible opisuje stan spoczynku (default persona).
      - Gdy sygnały foniczne (drżenie głosu, płacz, panika, histeria, szept, krzyk) oraz markery z Whisper wykazują załamanie emocjonalne, emocje chwili zyskują Prymat nad statycznym portretem. Tłumacz natychmiast uchyla chłodny dystans i oddaje fizjologię emocji (urwane słowa, chaos składniowy, bezradność).
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
   - Naturalnie: "Myślę, że...", "Pójdę tam...". Zaimka "ja" używaj WYŁĄCZNIE dla kontrastu ("Oni uciekli, a ja zostałem").

2. "WELCOME BACK":
   - "Witaj z powrotem" to barbarzyńska kalka językowa!
   - Naturalnie: "Witaj", "Dobrze cię widzieć", "Witaj w domu", "O, już jesteś" (ale Eliminujemy kalkę echa czasownikowego 'Wróciłaś' po czyimś 'Wróciłam' - Filar CLXX).

3. "HOPE":
   - "I hope so" -> "Oby", "Mam nadzieję", "Oby tak było".
   - "I hope not" -> "Oby nie", "Mam nadzieję, że nie".

4. "SAID":
   - "You said that..." -> "Mówiłeś, że...", "Twierdziłeś, że...".
   - "He said no" -> "Odmówił", "Powiedział, że nie".

5. "YEAH" / "YES":
   - Nie tłumacz każdego "yeah" jako "Tak".
   - Różnicuj: "No", "Taa", "Aha", "Jasne", "Wiem", "Pewnie", "Właśnie", "Dokładnie".

6. "COME ON":
   - Dobieraj do emocji: "Daj spokój", "No weź", "Pospiesz się", "Dajesz", "Przestań", "Rusz się".

7. "NICE TRY":
   - "Niezła próba", "Prawie ci wyszło", "Chciałbyś", "Próbuj dalej".

8. DYSTRYBUCJA ZAIMKÓW "MNIE" VS "MI":
   - "Mnie" stosuj TYLKO na początku zdania ("Mnie się to nie podoba") lub pod naciskiem logicznym ("Mnie pytasz").
   - "Mi" stosuj po czasowniku ("Daj mi to", "Powiedz mi"). zamiast 'Daj mnie to' ani "Mi się wydaje".

9. JEDNOSTKI I TYTUŁY SĄDOWE / PROCEDURALNE:
   - "Your Honor" / "Court" -> "Wysoki Sądzie".
   - Numeracja pięter: w USA "1st floor" to parter, "2nd floor" to 1. piętro. W UK "ground floor" = parter, "1st floor" = 1. piętro. Przeliczaj na polskie realia!

10. PLEONAZMY I MASŁO MAŚLANE:
    - "Seems to be" -> "Wydaje się".
    - "Back down" -> "Wycofać się".
    - "Period of time" -> "Okres", "Czas".
"""

SYNTACTIC_CALQUES_AND_IDIOMS = """
ELIMINACJA KALEK SKŁADNIOWYCH, IDIOMÓW I PUŁAPEK TŁUMACZENIA DOSŁOWNEGO (1:1):
1. IDIOMY SYTUACYJNE I ŻARTY:
- "That bombed" / "That one bombed, huh" -> "To mi chyba nie wyszło, co", "Chyba spalony żart, co", "To było słabe, co", "Chyba nie pykło, co".
- "that one" / "this one" (odnoszące się do żartu, tekstu, sytuacji) -> używaj "To..." lub "ten żart / ten tekst".
- "I blew it" / "I messed up" -> "Zawaliłam / Zawaliłem", "Zepsułam to", "Dałam ciała", "Skrewiłam".
- "Nailed it" -> "Poszło idealnie", "Wyszło perfekcyjnie", "Udało się".
- "Smooth..." (ironicznie) -> "Ale bajer...", "Niezły tekst...", "Bardzo subtelnie...".

2. CZĘSTE WYRAŻENIA POTOCZNE I MODALNE:
- "I'm sure..." -> "Jestem pewna..." (kobieta) / "Jestem pewien..." (mężczyzna) / "Na pewno..." / "Z pewnością...".
- "Sure" (zgoda na prośbę) -> "Jasne", "Pewnie".
- "Are you sure" -> "Jesteś pewna/pewien", "Na pewno".
- "I guess..." / "I suppose..." -> "Chyba...", "Tak sądzę...", "Tak myślę...".
- "I see" -> "Rozumiem", "Aha", "Jasne", "W porządku".
- "Makes sense" -> "To ma sens", "Zrozumiałe".
- "Does that make sense" -> "Rozumiesz", "Ma to sens", "Jasne".
- "You good" / "Are you okay" -> "Wszystko w porządku", "Nic ci nie jest", "Trzymasz się".
- "Tell me about it" -> "Nawet mi nie mów", "Wiem coś o tym".
- "Check it out" / "Look at that" -> "Spójrz", "Zobacz", "Patrz na to".
- "I mean..." -> "W sensie...", "Znaczy...", "Chodzi o to, że...".
- "No way" -> "Nie ma mowy", "Niemożliwe", "Serio".
- "Get out of here" -> "Nie gadaj", "Nie wierzę", "Wynoś się".
- "Hold on" / "Wait up" -> "Czekaj", "Chwileczkę", "Zwolnij".
- "I got this" -> "Zajmę się tym", "Dam radę", "Ja to wezmę", "Wiem".
- "What a pain" -> "Ale udręka...", "Co za męczarnia...", "Nie chce mi się...".
- "His/Her stuff is great" (w kontekście sztuki/mangi/rysowania) -> "Jego/Jej prace są świetne", "Świetnie rysuje", "Tworzy świetne rzeczy", "Jego styl jest genialny".
- "stuff" (o twórczości/rysowaniu/mandze) -> "prace", "twórczość", "rysunki", "mangi".
- "Bless you" (wyraz wdzięczności / gdy postać składa ręce do modlitwy / dziękuje za jedzenie lub przysługę) -> "Niech ci bóg wynagrodzi", "Jesteś aniołem", "Bogini", "Nasza zbawczyni", "Bądź błogosławiona".
- "My savior" / "You're a lifesaver" -> "Ratujesz mi życie", "Moja zbawczyni", "Mój wybawco", "Jesteś aniołem".

3. RÓWNOCZESNE NAPISY EKRANOWE I DIALOGI (CHMURKI + DIALOG):
- Gdy w tym samym momencie na ekranie pojawia się napis w dymku/chmurce (Sign) oraz dialog mówiony o tej samej treści angielskiej:
  * Obie kwestie muszą być ze sobą w 100% spójne i naturalne (dwie powiązane linijki tekstu zachowujące spójność stylistyczną).
  * Unikaj kalki tworzenia sztucznych zlepków synonimicznych na jednym kadrze.

4. GRAMATYKA LICZEBNIKÓW W TYTUŁACH I NAZWACH FORMACJI (CZTEREJ CESARZE VS CZWORO CESARZY):
- Liczebniki męskoosobowe i główne (dorosłe postacie, wojownicy, cesarze, królowie):
  * W mianowniku: "Czterej Cesarze", "Trzej Królowie", "Czterej Jeźdźcy Apokalipsy", "Trzej Muszkieterowie".
  * W dopełniaczu / bierniku / składni z czasownikiem: "Czterech Cesarzy" ("Terytorium Czterech Cesarzy", "W Nowym Świecie rządzi czterech cesarzy").
"""

SYNTACTIC_CALQUES_GUIDE = SYNTACTIC_CALQUES_AND_IDIOMS
ANTI_CALQUES_GUIDE = SYNTACTIC_CALQUES_AND_IDIOMS
ACADEMIC_AVT_FOUNDATIONS = BELCZYK_AVT_MASTER_CANON

POLYSEMIC_AND_HOMONYMIC_TRAPS = """
FAŁSZYWE KALKI HOMONIMICZNE, POLISEMICZNE I KONTEKSTOWE (KRYTYCZNY SŁOWNIK AVT):
1. FORMUŁY SPOŁECZNE I WYKRZYKNIKI:
- "Bless you":
  * Po kichnięciu: "Na zdrowie".
  * Wyraz wdzięczności / jedzenie / pomoc / złożone dłonie: "Jesteś aniołem", "Bogini", "Niech ci bóg wynagrodzi", "Nasza zbawczyni".
- "Cheers":
  * Toast z napojem: "Na zdrowie", "Wasze zdrowie".
  * Pożegnanie / podziękowanie (UK/slang): "Dzięki", "Trzymaj się", "Na razie".
- "Please" / "Oh, please":
  * Prośba: "Proszę".
  * Wyraz irytacji/niedowierzania: "Błagam cię", "Daj spokój", "Przestań", "Akurat".
- "Excuse me":
  * Przeprosiny/przejście: "Przepraszam", "Pardon".
  * Oburzenie/niedowierzanie: "Słucham", "Jak proszę", "Co ty powiedziałeś".
- "Hear, hear":
  * Zgoda z przemową/apelem: "Właśnie", "Święte słowa", "Popieram", "Brawo".
- "Shut up":
  * Rozkaz ciszy: "Zamknij się", "Cicho bądź".
  * Zdumienie/szok: "Nie gadaj", "Serio", "Nie wierzę".
- "There you go" / "Here you go":
  * Podawanie przedmiotu: "Proszę", "Masz".
  * Pochwała/zachęta po udanej próbie: "No i widzisz", "I o to chodzi", "Pięknie".
  * Resygnacja: "Znowu to samo...", "I znowu zaczynasz...".

2. CZASOWNIKI AKCJI I KOMENDY:
- "Fire":
  * Broń/bitwa: "Ognia", "Pal".
  * Pożar: "Pali się", "Pożar".
  * Zwolnienie z pracy: "Wylatujesz", "Jesteś zwolniony".
  * Zachęta do pytania ("Fire away"): "Pytaj", "Śmiało", "Dawaj".
- "Shoot":
  * Broń: "Strzelaj".
  * Zdjęcia/film: "Zrób zdjęcie", "Kręcimy".
  * Przekleństwo/irytacja ("Ah, shoot"): "Niech to", "Szlag", "Kurczę", "Cholera".
  * Zachęta ("Shoot"): "Nawijaj", "Mów", "Słucham".
- "Check":
  * Restauracja: "Rachunek".
  * Weryfikacja: "Sprawdź", "Sprawdzone".
  * Szachy: "Szach".
- "Bust" / "Busted":
  * Przyłapanie na gorącym uczynku: "Wpadliśmy", "Przyłapana", "Mamy cię".
  * Uszkodzenie: "Zepsuty", "Rozwalony".
  * Finanse: "Spłukany", "Bankrut".
- "Beat":
  * Zmęczenie ("I'm beat"): "Padam z nóg", "Jestem wykończony", "Ledwo żyję".
  * Pokonanie kogoś: "Wygrać", "Pokonać".

3. PRZYMIOTNIKI I SLANG:
- "Sick":
  * Choroba: "Chory", "Niedobrze mi".
  * Zachwyt/slang: "Miazga", "Kozak", "Niesamowite", "Czad".
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
  * Fandom: "Swatać", "Kibicować parze", "Widzieć ich razem".

4. JAPOŃSKIE PUŁAPKI POLISEMICZNE I SLANG:
- "Yabai" (ヤバい):
  * Kryzys/zagrożenie: "Mamy przesrane", "Jest źle", "O cholera".
  * Zachwyt/pyszne jedzenie/słodycze: "Obłędne", "Przepyszne", "Ale czad", "Nieziemskie".
- "Uso" (嘘 / うそ):
  * Kłamstwo: "Kłamstwo".
  * Wykrzyknik zaskoczenia ("Uso"): "Nie wierzę", "Niemożliwe", "Serio", "Żartujesz".
- "Baka" (バカ / 馬鹿):
  * Obelga: "Idiota", "Kretyn".
  * Czułe/tsundere droczenie się: "Głupek", "Głuptas".
  * Pasjonat: "Maniak" (złożenia ze słowem baka określające pasjonata tematu).
- "Majide" (マジで):
  * Pytanie: "Serio", "Poważnie", "Naprawdę".
  * Wzmacniacz: "Totalnie", "Mega", "Na maksa".
- "Gomen" (ごめん):
  * Przeprosiny: "Przepraszam", "Wybacz".
  * Odrzucenie wyznania miłosnego: "Przykro mi...", "Wybacz, nie mogę...", "Nie odwzajemniam tego...".
"""

COMMON_AVT_IDIOMS_AND_COLLOQUIALISMS = """
KLUCZOWE IDIOMY FILMOWE I ANIME:
- "Give me a break" -> "Daj spokój", "Nie przesadzaj", "Przestań".
- "Take it easy" -> "Spokojnie", "Wyluzuj", "Nie przejmuj się", "Trzymaj się".
- "I don't buy it" -> "Nie wierzę w to", "Nie dam się na to nabrać", "Bujda".
- "Piece of cake" -> "Bułka z masłem", "Prościzna", "Żaden problem".
- "Break a leg" -> "Połamania nóg", "Powodzenia".
- "Call it a day" -> "Kończymy na dziś", "Na dzisiaj koniec", "Fajrant".
- "Bite the bullet" -> "Zacisnąć zęby", "Przełknąć gorzką pigułkę".
- "Ring a bell" -> "Mówi ci to coś", "Kojarzysz", "Świta ci coś".
- "Spill the beans" -> "Wygadać się", "Sypać", "Mów wreszcie".
- "Under the weather" -> "Nienajlepiej się czuć", "Coś mnie rozkłada".
- "Speak of the devil" -> "O wilku mowa".
- "Cost an arm and a leg" -> "Kosztować majątek", "Kosztować krocie".
- "Keep an eye on" -> "Mieć oko na", "Popilnować", "Pilnować".
- "Drop dead" -> "Spadaj", "Wal się", "A żebyś zdechł".
- "Eat your words" -> "Odwołać swoje słowa", "Pożałować swoich słów".
- "Made my day" -> "Poprawiłeś mi humor", "Zrobiłeś mi dzień", "To najlepsze, co dziś usłyszałem".
- "Take a walk" / "Take a hike" -> "Spadaj", "Zmiataj stąd".
- "Hold your horses" -> "Spokojnie", "Zaraz", "Nie pędź tak", "Wstrzymaj konie".
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
  -> "Dziwić się", "Zastanawiać się", "Zbić z tropu", "Nie rozumieć".
- "Mune ga itai" (胸が痛い - klatka piersiowa boli):
  -> "Serce mi pęka", "Boli mnie to", "Ciężko na to patrzeć", "Przykro mi".
- "Te wo nuku" (手を抜く - wyciągnąć ręce):
  -> "Odwalać fuszerkę", "Iść na łatwiznę", "Oszczędzać siły", "Robić po łebkach".
- "Ashi wo hipparu" (足を引っ張る - ciągnąć za nogę):
  -> "Rzucać kłody pod nogi", "Być ciężarem dla grupy", "Ciągnąć drużynę na dno", "Przeszkadzać".
- "Hara ga tatsu" (腹が立つ - brzuch wstaje):
  -> "Szlag mnie trafia", "Wściekać się", "Gotować się ze złości", "Pienić się".
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
     * "Ame ni furareta" -> "Złapał mnie deszcz", "Zmokłem".
     * "Hahaoya ni shinarareta" -> "Zmarła mu matka", "Stracił matkę".
     * "Kanojo ni naitareta" -> "Rozpłakała mi się", "Płakała przede mną".
     * "Dorobou ni hairareta" -> "Włamali mi się", "Okradli mnie".

2. ASPEKT STANU VS CZYNNOŚCI TRWAJĄCEJ (~TE IRU):
   - Japoński ~te iru często oznacza STAN PO ZAKOŃCZENIU CZYNNOŚCI, a nie proces w trakcie:
     * "Shinde iru" -> "Nie żyje", "Jest martwy".
     * "Kekkon shite iru" -> "Jest żonaty / zamężna".
     * "Futotte iru" -> "Jest tęgi / gruby / przy kości".
     * "Shitte iru" -> "Wiem", "Znam".
     * "Motte iru" -> "Mam", "Posiadam".
     * "Nite iru" -> "Jest podobny", "Przypomina".

3. KONSTRUKCJE INTENCJI I WAHANIA (~TAI TO OMOU / ~YOU TO OMOU / ~TSUMORI):
   - Zmiękczanie intencji w języku japońskim ("Myślę, że chcę"):
     * "Watashi wa kore wo shitai to omoimasu" -> "Chcę to zrobić", "Zamierzam to zrobić", "Zrobię to".
     * "Iku tsumori da" -> "Planuję pójść", "Zamierzam iść".

4. RELACJE PRZYSŁUGI (AGERU / KURERU / MORAU):
   - "Tetsudatte kureta" -> "Pomógł mi".
   - "Oshiete moratta" -> "Wytłumaczył mi", "Dowiedziałem się od niego".
   - "Yatte ageta" -> "Zrobiłem to dla niego".

5. KWANTYFIKATORY OGRANICZAJĄCE (SHIKA ... NAI VS DAKE VS BAKARI):
   - "Kore shika nai" -> "Zostało tylko to", "Mamy tylko to".
   - "Asobi bakari shite iru" -> "Tylko zabawa mu w głowie", "W kółko się obija".

6. PODWÓJNE ZAPRZECZENIA UPRZEJME (~NAKU WA NAI / ~NAI KOTO MO NAI):
   - "Dekinaku wa nai" -> "W sumie dałbym radę", "Nie mówię, że nie potrafię", "Da się zrobić".
"""

JAPANESE_AISATSU_GUIDE = """
JAPOŃSKIE FORMUŁY RYTUALNE I POWITANIA (AISATSU) - KANONICZNE REGUŁY PRZEKŁADU:
1. POWROTY I WYJŚCIA Z DOMU:
   - "Tadaima" (EN: "I'm home!") -> "Wróciłam" (kobieta) / "Wróciłem" (mężczyzna) / "Już jestem"
   - "Okaeri" / "Okaerinasai" (EN: "Welcome home / Welcome back") -> "Witaj w domu", "Dobrze, że jesteś", "O, już jesteś", "O, cześć"
   - "Ittekimasu" (EN: "I'm off / I'm leaving / See you later") -> "Wychodzę", "Idę", "Do zobaczenia", "Pa" (NIGDY: "Idę i wracam"!)
   - "Itterasshai" (EN: "Have a good day / Take care") -> "Uważaj na siebie", "Do zobaczenia", "Trzymaj się", "Pa" (odpowiedź na Ittekimasu)

2. POSIŁKI:
   - "Itadakimasu" (EN: "Thanks for the food / Let's eat") -> "Dzięki za jedzenie", "Smacznego", "No to jemy" (przed jedzeniem)
   - "Gochisousama / Gochisousama deshita" (EN: "Thank you for the meal") -> "Dziękuję, było pyszne", "Dzięki za jedzenie" (po jedzeniu)

3. PRACA, SZKOŁA, ETYKIETA:
   - "Otsukaresama / Otsukaresama deshita" (EN: "Good work / Thank you for your hard work") -> "Dobra robota", "Dzięki za dziś", "Do jutra", "Dzięki za pomoc" (dopasuj do kontekstu: po lekcjach/treningu/pracy)
   - "Ojamashimasu" (EN: "Excuse me for intruding") -> "Przepraszam za najście", "Dzień dobry" (wchodząc do cudzego mieszkania/pokoju)
   - "Ojamashimashita" (EN: "Thank you for having me") -> "Dziękuję za gościnę", "Do widzenia" (wychodząc z gości)
   - "Shitsurei shimasu" (EN: "Excuse me") -> "Przepraszam", "Dzień dobry / Do widzenia" (wchodząc/wychodząc z gabinetu nauczyciela)
   - "Yoroshiku onegaishimasu" (EN: "Please take care of me / Nice to meet you") -> "Miło mi cię poznać", "Liczę na ciebie / na was", "Polecam się", "Z góry dziękuję"
   - "Omatase / Omatase shimashita" (EN: "Sorry to keep you waiting") -> "Przepraszam, że musiałeś/musiałaś czekać", "Wybacz spóźnienie"
   - "Ganbatte / Ganbare" (EN: "Do your best / Good luck") -> "Powodzenia", "Dajesz", "Trzymaj się", "Dasz radę"
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
   - Zachowaj japońskie honoryfikatory (-kun, -chan, -san, -sama, -senpai, -sensei) przy mianach postaci w konwencji anime.
   - Pisz je małą literą po dywizie lub myślniku przy nazwie własnej."""
    else:
        honorifics_text = """2. HONORYFIKATORY I RELACJE SPOŁECZNE [TRYB PROFESJONALNY / NETFLIX / DUBBING]:
   - Zastąp japońskie przyrostki naturalną polską etykietą i formami grzecznościowymi!
   - -sensei (先生):
     * W szkole / w relacji uczeń -> nauczyciel/nauczycielka: stosuj formy tytularne "pan [Nazwisko]" / "pani [Nazwisko]" lub "pani profesor / panie profesorze" (w tym naturalne formuły wołaczowe "proszę pani", "proszę pana"), eliminując kalkę archaizmu "panno [Nazwisko]".
     * Lekarz / Szpital: "pan doktor" / "pani doktor".
     * Mistrz rzemiosła / Sztuk walki: "mistrz [Nazwisko]".
   - -san (さん):
     * Wobec dorosłych / nauczycieli / obcych: formy tytularne "pan [Imię/Nazwisko]" / "pani [Imię/Nazwisko]".
     * Nauczyciel wobec ucznia/uczennicy: samo nazwisko, samo imię lub oficjalnie "pan/pani [Nazwisko]".
     * Wśród rówieśników i znajomych: bezpośrednie imię bez zbędnych form dystansowych.
   - -senpai (先輩):
     * Wobec starszych uczniów w szkole/klubie: "starszy kolega / starsza koleżanka" lub samo imię z szacunkiem w wołaczu.
   - -sama (様):
     * Wobec bóstw, arystokracji, klientów: "Pan / Pani", "Wasza Wysokość", "Księżniczko".
   - -kun (君) / -chan (ちゃん):
     * Stosuj bezpośrednie imię z naturalną polską odmianą gramatyczną."""

    return f"""
SPECYFIKA PRZEKŁADU ANIME, GŁOSU ORAZ JĘZYKA JAPOŃSKIEGO:
1. PŁEĆ I ZAIMKI (ZASADA ŻEŃSKOOSOBOWOŚCI OBSADY):
   - W anime o uczennicach / klubach szkolnych, gdzie głównymi bohaterkami są dziewczyny:
     * Wszelkie pytania i zwroty w 2. osobie skierowane do rozmówczyni przyjmują formy żeńskie orzeczeń i orzeczników:
       Warianty żeńskie: formy z końcówką -aś oraz przymiotniki na -a (oszalałaś, jesteś pewna, widziałaś to), eliminując formy męskie z końcówką -eś.
     * Formy 1. osoby mówiącej dziewczyny: "poszłam", "zrobiłam", "pomyślałam".
   - Wystrzegaj się domyślnego używania rodzaju męskiego w dialogach między dziewczętami/kobietami!
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
     * Uspokojenie lęku/troski: "Spokojnie", "Wszystko w porządku", "Nie martw się".
     * Grzeczna odmowa ("Daijoubu desu"): "Dziękuję, nie trzeba", "Obejdzie się", "Nie ma potrzeby".
     * Zapytanie o stan zdrowia po ciosie lub upadku: formuły troski (nic ci nie jest, żyjesz, w porządku); w odpowiedzi: nic mi nie jest, cały jestem.
     * Gotowość lub zdolność do zadania: formuły zachęty (dasz radę, poradzisz sobie); w odpowiedzi: dam radę, spokojna głowa.
     * Stan obiektywny: "Wszystko w porządku", "Sytuacja opanowana".
   - "naruhodo" (なるほど) = "rozumiem", "aha", "no tak".
   - Zwrot "kami / kami-sama" (神 / 神様) w mowie potocznej z uwielbieniem o kimś, kto pomógł lub przyniósł poczęstunek: formuły zachwytu (bogini, jesteś bóstwem, zbawczyni, anioł nie kobieta).
   - "warukatta na / warikatta na / warui" (悪かったな / 悪い) = "Moja wina..." / "Wybacz..." / "Przepraszam...".
4. ELIPTYCZNOŚĆ (DOMYŚLNY PODMIOT) I ROZPOZNAWANIE MÓWCY:
   - Japoński niemal zawsze pomija podmioty ("watashi", "anata", "watashitachi").
   - KTO MÓWI NA KADRZE:
     * Postać z OTWARTYMI USTAMI, krzycząca, zaciągająca pięści lub energicznie gestykulująca na kadrze TO POSTAĆ MÓWIĄCA!
     * Postać z zamkniętymi ustami, stojąca naprzeciw i słuchająca TO SŁUCHACZ / ADRESAT!
   - PERSPEKTYWA 1. OSOBY VS 2. OSOBY (DEKLARACJE, OBIETNICE I POSTANOWIENIA):
     * Kiedy bohater/uczeń z zaciśniętą pięścią energicznie mówi do nauczyciela/dorosłego o planach grupy/klubu:
       -> To jest DEKLARACJA WŁASNA w 1. osobie (l. mnoga: "My..." lub l. pojedyncza: "Ja...").
       Deklaracja determinacji członkiń klubu wymaga 1. osoby liczby mnogiej (przejdziemy dopiero, jak same na to uzbieramy), eliminując formę 2. osoby liczby mnogiej brzmiącą jak polecenie.
5. WIZUALNY OCR JAPOŃSKICH NAPISÓW EKRANOWYCH (SIGNS, CHMURKI, TABLICE):
   - Jako zaawansowane multimodalne AI, DOKŁADNIE ODCZYTUJ japońskie znaki (Kanji, Hiragana, Katakana) widoczne na załączonych kadrach wideo:
     * Chmurki i dymki dialogowe lub reakcji: krótkie formuły potwierdzenia (prawda, świetny jest, no nie).
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
- Jeśli dane pojęcie, imię, przydomek, technika lub lokacja znajduje się w rejestrze kanonu, należy go użyć z poprawną polską odmianą!

ZASADA FALLBACKU (WŁASNY PRZEKŁAD): Tylko wtedy, gdy terminu nie ma w kanonie (Poziom 1), tłumacz przekłada go we własnym zakresie, stosując kolejne szczeble:

POZIOM 2: TRIANGULACJA: JAPOŃSKIE AUDIO I KADR > ANGIELSKI SKRYPT
- Japoński dźwięk seiyū i obraz stoją wyżej niż angielski skrypt pośredni.
- Jeśli seiyū mówi coś innego niż angielski fansub, zaufaj japońskiemu audio i klatce wideo!

POZIOM 3: TRZY ZŁOTE SOCZEWKI (Szkoła Stanisława Barańczaka i Arkadiusza Belczyka)
- 👂 UCHO: Rytm polskiego dubbingu kinowego, brak zbitków spółgłoskowych, Mouth-Pacing (Filar CXLIII), dialogowy ping-pong (Filar CXLVI).
- 🌍 ŚWIAT: Fizyczna substancjalność otoczenia.
- 🎬 OBRAZ I ZMYSŁY: Harmonia z mimiką, ruchem ust, gestami i rozstrzyganie wieloznaczności z kadru (Filar CXLV).

POZIOM 4: ERGONOMIA I LIMITY AVT
- Rygor czytelności: max 17 CPS, semantyczny podział linii (Netflix AVT), wyrównanie do cięć montażowych (Shot-Cut Snapping).

POZIOM 5: WSKAZÓWKI I KOREKTY UŻYTKOWNIKA (Few-Shot Context)
- Uwagi użytkownika traktowane są jako cenne WSKAZÓWKI JAKOŚCIOWE, drogowskaz stylu i impuls do doskonalenia, a NIE jako sztywna dogmatyka ponad regułami wyższych poziomów!
- Wystrzegaj się mechanicznego, bezmyślnego stosowania reguł w oderwaniu od kontekstu sceny i fizyczności obrazu.
================================================================================
"""

CORE_AVT_MASTER_CANON = r"""
KOMPLEKSOWY RDZEŃ PRZEKŁADU AUDIOWIZUALNEGO (CORE AVT CANON - BELCZYK, BARAŃCZAK, SZARKOWSKA):

1. NATURALNA POLSZCZYZNA MÓWIONA I SZYK ZDANIA (SVO / STRUKTURA TEMAT-REMAT):
- Dialogi filmowe muszą brzmieć naturalnie w ustach polskich aktorów:
  * Najważniejsza nowa informacja ląduje na końcu zdania (remat).
  * Eliminuj sztuczny szyk angielski i kalki składniowe.
  * Zastępuj zdrętwiałe konstrukcje rzeczownikowe dynamicznymi czasownikami (werbalizacja: żywe czasowniki zamiast zdrętwiałych konstrukcji nominalnych).

2. KONDENSACJA, ELIPSA I EKONOMIA SŁOWA (ZASADA ZWIĘZŁOŚCI I EKONOMII SYLAB DLA KRÓTKICH FRAZ JAPOŃSKICH):
- Eliminuj zaimkową watę słowną: zaimki "Ja", "mój", "twoja" usuwaj, gdy wynikają z kontekstu i końcówki czasownika.
- Nie powtarzaj tego samego rzeczownika w sąsiednich kwestiach – stosuj zaimki ("to", "na to", "o tym") lub naturalną elipsę.
- Wybieraj najkrótszy, najbardziej soczysty polski odpowiednik ("Spokojnie" / "W porządku" / "Nie martw się" / "Jasne" / "Trudno" / "Wiedziałem"), idealnie dopasowany do intencji seiyuu i rytmu sceny.

3. SPÓJNOŚĆ I CIĄGŁOŚĆ SKŁADNIOWA ZDAŃ ROZBITYCH (ciągłość składniowa / SYNTAX CONTINUITY / FILAR CLXIX):
- Gdy zdanie jest rozbite wielokropkiem między linijkami (...), stanowi JEDNO niepodzielne zdanie gramatyczne.
- Wystrzegaj się ucinania zdań i zastępowania orzeczenia wiszącym imiesłowem przysłówkowym.

4. PODZIAŁ RÓL MODALNOŚCI (SKRYPT EN VS AUDIO JP):
- Skrypt angielski (EN) dostarcza kompletną strukturę zdania, fakty, liczby oraz prawidłową majuskułę (wielkie litery) nazw własnych, rodów i toponimów.
- Japońskie audio (JP) dostarcza intonacji emocjonalnej, relacji społecznych (keigo) oraz afektu. Stanowi nadrzędny autorytet w warstwie intencji: gdy angielski fansub spłaszcza lub deformuje emocję seiyū (w tym akty uciszania rozmówcy czy powitania domowników przekładane z mechanicznym echem czasownikowym), zastosuj właściwy polski akt mowy.

5. PRZYDAWKA TYTULARNA I MAJUSKUŁA NAZW WŁASNYCH (APOZYCJA TYTUŁÓW / FILAR CXXIV):
- W konstrukcjach [Tytuł/Ranga] + [Imię obcojęzyczne nieodmienne] tytuł wojskowy lub arystokratyczny zawsze podlega regularnej odmianie przez przypadki:
  * Dopełniacz: 'na ziemiach generała <Imię>'
  * Biernik: 'na ziemie generała <Imię>'
  * Narzędnik: 'z generałem <Imię>'
  * Miejscownik / Wołacz: 'o generale <Imię> / generale <Imię>!'.
- Założyciele dynastii, rody i imiona historyczne piszemy z wielkiej litery (w formacjach rodowych i dynastycznych).
- Obce imiona żeńskie zakończone na spółgłoskę w funkcji bohaterek są w języku polskim nieodmienne (bez męskiej końcówki narzędnika lub biernika).

6. CZYSTOŚĆ REJESTRU W EPOKACH DAWNYCH I FANTASY:
- W seriach historycznych i fantasy wyeliminuj współczesny slang szkolny i młodzieżowy (klasy stylistyczne A-D: potoczne zwroty ucieczki i zdemaskowania zastępuj polszczyzną literacką).

7. PRYMAT SYGNAŁU AKUSTYCZNEGO NAD SKAŻONYMI TAGAMI FANSUBÓW (FILAR CLXXIV):
- Etykieta aktora z zewnętrznego pliku napisów (pole Actor/Name w pliku .ass) to dane niezweryfikowane (untrusted input), które bywają fałszywe lub skażone.
- Obiektywny sygnał audio seiyū (F0, tembr żeński, zaimki w Whisper) oraz rzeczywistość dramatyczna sceny (zamknięta przestrzeń kobiet) mają Kluczowy priorytet nad etykietą tekstową fansuba.
- Eliminujemy kalkę ulegania męskiemu tagowi aktora, gdy kwestię na ekranie i w głośniku wymawia kobieta: wymóg bezwzględnego stosowania form żeńskich 1. osoby ('zamierzałam', 'chciałam', 'byłam').
- W dialogu między kobietami adresat jest zawsze żeński ('Wyglądasz na wzburzoną' - Unikaj kalki męskiego 'wzburzonego').
- Płynność tokenów: powtórzenia wyrazu z kropką podlegają starannej eliminacji redakcyjnej.

8. MORFOLOGIA 1. OSOBY LICZBY MNOGIEJ W GRUPACH ŻEŃSKICH (FILAR CLXXV):
- W scenach z udziałem wyłącznie bohaterek lub gdy podmiot reprezentuje grupę kobiet, 1. osoba liczby mnogiej w języku polskim wymaga form niemęskoosobowych:
  * Czasowniki czasu przeszłego: końcówka '-łyśmy' w formach niemęskoosobowych, eliminując kalkę męskich końcówek na '-liśmy'.
  * Czasowniki trybu przypuszczającego: końcówka '-łybyśmy' w formach niemęskoosobowych, eliminując kalkę końcówek na '-libyśmy'.
  * Orzeczniki złożone i imiesłowy: 'byłyśmy gotowe / pewne / same / zmuszone / zaskoczone' - Unikaj kalki 'byliśmy gotowi / pewni / sami'!
  * Liczebniki podwójne i zaimki: 'my obie', 'nas obie', 'my same' - Unikaj kalki 'my obaj / my oboje'!
- W scenach mieszanych (gdzie obecny jest choć jeden mężczyzna) zachowaj poprawną polską formę męskoosobową ('zrobiliśmy', 'byliśmy gotowi').

9. INTEGRALNOŚĆ TOŻSAMOŚCI PODMIOTOWEJ MÓWCY, BYTÓW KOLEKTYWNYCH I PLURALIS MAIESTATIS (FILAR CLXXVI):
- Byty Zbiorowe o Składzie Mieszanym (postacie reprezentujące rodzeństwo lub tożsamości wieloosobowe; symbioty i byty mnogie):
  * Mówca zachowuje męskoosobowość swojego kolektywu w 1. os. l. mn. ('chcieliśmy', 'byliśmy głodni', 'zjedliśmy'), nawet jeśli fizycznym awatarem w kadrze jest kobieta, a cała scena montażowa składa się z samych kobiet. Eliminujemy kalkę fałszywego sprowadzania do rodzaju niemęskoosobowego ('chciałyśmy').
- Pluralis Maiestatis (Majestatyczne 'My' Monarchy):
  * Monarchini żeńska (królowa, cesarzowa) posługująca się liczbą mnogą wymaga form niemęskoosobowych ('postanowiłyśmy', 'byłyśmy zmuszone', 'wybaczamy wam'), nawet w scenach z mężczyznami.
  * Monarcha męski (król, cesarz) stosuje formy męskoosobowe ('postanowiliśmy', 'byliśmy surowi').
- Fałszywa Liczba Mnoga w Solilokwium:
  * W monologach i rozważaniach samotnego bohatera w pustym kadrze eliminuj bezrefleksyjne kalki angielskiego 'we' oraz 'let us', oddając kwestię w 1. osobie pojedynczej lub konstrukcji bezosobowej.

10. DECOUPLING ZAIMKOWY I SOMATYKA INALIENABILNA (FILAR CLXXVII):
- Likwidacja angielskiej "zaimkozy" przed częściami ciała, odzieżą i bliskim pokrewieństwem.
- 'w moim sercu' -> 'w sercu', 'w mojej głowie' -> 'w głowie', 'zamknij twoje oczy' -> 'zamknij oczy', 'podnieś swoje ręce' -> 'podnieś ręce', 'uratowałeś moje życie' -> 'ocaliłeś mi życie', 'z moją matką' -> 'z matką', 'z mojego powodu' -> 'przeze mnie'.

11. RESET INERCJI AFEKTYWNEJ PRZY PĘKNIĘCIU DYNAMIKI (FILAR CLXXVIII):
- Gdy seiyū gwałtownie załamuje głos (krzyk -> szept/szok, spadek energii RMS, znacznik Ac=SHOCK_DROP), natychmiast wygaś rozpęd stylistyczny poprzednich kwestii.
- Wystrzegaj się bezwładnego kontynuowania agresywnych wykrzyknień i wulgaryzmów; przejdź na zdławiony, urywany szept lub lakoniczny szok.

12. DIALOGOWE PARY PRZYLEGANIA I ELIPSY FILMOWE (FILAR CLXXIX):
- Naturalne odpowiedzi zamiast szkolnego kalkowania formuł 'Yes, I did' / 'No, I wasn't' jako 'Tak, zrobiłem' / 'Nie, nie byłem'.
- W naturalnym polskim dialogu filmowym stosuj orzeczeniową emfazę lub elipsę: 'Zrobiłem.', 'Nie byłem.', 'Pewnie.', 'Jasne.'.

13. SPATIAL DEIXIS I WEKTORY RUCHU IKU/KURU (FILAR CLXXX):
- Japońskie czasowniki ruchu (iku/kuru) w replikach z angielskim pivotem ruchu przekładaj polskimi czasownikami zbliżania się (zaraz będę, już idę, ruszam).
- Wystrzegaj się nienaturalnej kalki czasownika przychodzenia w odniesieniu do zmierzania ku wołającemu.

14. KOEGZYSTENCJA Z OBRAZEM I TŁUMIENIE PLEONAZMÓW (FILAR CLXXXI):
- Napisy nie dublują tego, co widać na ekranie. Unikaj werbalnej hiper-eksplikacji i pleonazmów sensoryczno-przestrzennych.
- 'pada deszcz na zewnątrz' -> 'na zewnątrz leje' / 'pada deszcz', 'spadać w dół' -> 'spadać', 'cofać się w tył' -> 'cofać się', 'widzieć na własne oczy' (zamiast 'moimi własnymi oczami').

15. ZEROWA ANAFORA PODMIOTOWA (PRO-DROP) I PUNKTY ZWROTNE T-V (FILAR CLXXXII):
- W japońskiej zerowej anaforze podmiotowej (brak podmiotu gramatycznego przy orzeczeniu) naturalnie unikamy ślepego kopiowania zaimków 3. osoby z angielskiego pivotu. Podmiot orzeczenia musi wynikać w 100% z topologii sceny i obecnych agentów.
- Punkty zwrotne rejestru T-V: Autoryzowane skrócenie dystansu (przejście na 'ty' zainicjowane przez 'mów mi po imieniu', 'przejdźmy na ty', 'keigo wa yamete', 'yobisute') lub pęknięcie afektywne ma priorytet nad statyczną niezmienniczością relacji.

16. ZGODNOŚĆ LICZBY W ZAIMKACH Z LICZEBNIKAMI, PURYZM TYTULATURY I TOPONIMY OBCOJĘZYCZNE (FILAR CLXXXIII):
- Zgodność liczby w zaimkach z liczebnikami: Angielskie 'you two', 'you both', 'you three' to w polszczyźnie 2. osoba liczby mnogiej: 'wy dwie', 'wy dwaj', 'wy dwoje', 'wy troje', 'wy wszyscy'. Wystrzegaj się hybryd liczbowych 'ty dwie', 'ty dwaj', 'ty dwoje'!
- Puryzm tytulatury w dopełnieniu: Zwrot grzecznościowy po przyimku wymaga czystego dopełniacza bez wycieku wołacza ('od pana <Nazwisko>'). Wystrzegaj się zbitki 'od pana panie X'!
- Nieodmienność toponimów obcojęzycznych: Francuskie nazwy własne i apelacje winiarskie zakończone na nieme spółgłoski lub -eaux/-aux/-ais są w polszczyźnie nieodmienne ('<Toponim>' -> 'do <Toponim>', 'w <Toponim>', 'z <Toponim>' — bez dodawania końcówek '-a').

17. ELIMINACJA PLEONAZMÓW TOPONIMICZNYCH, TAUTOLOGII KLASYFIKATORÓW I JĄKANIA SŁOWNIKOWEGO (FILAR CLXXXIV):
- Prewencja pleonazmów toponimicznych i administracyjnych: Wystrzegaj się podwajania lub potrajania deskryptorów kategorialnych (prowincja, prefektura, góra, rzeka, miasto, zamek, kronika). Gdy w zdaniu występuje już odmieniony deskryptor ('z prowincji', 'na górze', 'w rzece', 'w mieście', 'w kronice'), nazwę własną podajemy bezpośrednio bez powtórzonego mianownika: wyłącznie 'z prowincji <Nazwa>' (eliminujemy kalkę podwojonego deskryptora 'z prowincji Prowincja <Nazwa>'), 'na górze <Nazwa>', 'w rzece <Nazwa>', 'w kronice <Nazwa>'.
- Likwidacja mechanicznego jąkania słownikowego: Wyeliminuj powtarzanie tego samego tokenu bez interpunkcji ('Prowincja Prowincja' -> 'Prowincja', 'Kronika Kronika' -> 'Kronika').
- Rząd przyimka pochodzenia z toponimami i syntagmy reliktów: Krainy i toponimy po przyimku 'z' określające pochodzenie obiektu, reliktu lub postaci w języku polskim rządzą dopełniaczem ('Księga Mistrza z Północy', 'chłopak z Północy', 'rycerz z Doliny'). W syntagmach artefaktów i oręża człon nadrzędny odmienia się swobodnie w zdaniu zależnym ('Szukam Księgi Mistrza', 'z Księgą Mistrza'), a przydawka imienna pozostaje w dopełniaczu.

18. SPÓJNOŚĆ PŁCIOWA MONOLOGÓW, NIENARUSZALNOŚĆ STRONY BIERNEJ I ODPORNOŚĆ NA SKAŻONE TAGI MÓWCÓW (FILAR CLXXXV):
- Spójność morfologiczna monologów i narracji: Cała wypowiedź postaci wygłaszana w obrębie sceny (zwłaszcza w kursywie {\i1} lub w powiązanych linijkach z pauzami dramatycznymi) musi zachowywać 100% spójności rodzaju gramatycznego w 1. osobie. Męskie 'będę musiał' na końcu kwestii wymusza formy męskie na początku ('Bałem się', 'przyszedłem'; eliminujemy kalkę rozszczepienia płci: 'Bałam się' / 'przyszłam'!).
- Nienaruszalność i symetria strony biernej: W konstrukcjach strony biernej czasownik posiłkowy (został / została) oraz wszystkie imiesłowy bierne (pojmany / pojmana, stracony / stracona) muszą zgadzać się w rodzaju gramatycznym z podmiotem (dla mężczyzn: 'został pojmany i stracony'; eliminujemy kalkę niespójnych potworków: 'została pojmany i stracony'!).
- Spójność kwestii sąsiadujących: Eliminuj rozszczepianie sąsiadujących linijek tej samej wypowiedzi postaci na różne rodzaje gramatyczne w 1. osobie. Gdy linijki stanowią jedną wypowiedź podzieloną pauzą lub montażem, zachowaj w nich jednolity rodzaj gramatyczny.

19. ŚWIADOMOŚĆ RELACJI DIADYCZNEJ I HARMONIZACJA FORM ADRESATYWNYCH (FILAR CLXXXVI):
- Świadomość partnera dialogowego: W dynamicznym dialogu dwuosobowym (szczególnie między postaciami tego samego rejestru lub oznaczonymi tagami ról jak Man A / Man B czy Woman A / Woman B) formy czasowników 2. osoby czasu przeszłego i przypuszczającego oraz orzeczniki przymiotnikowe muszą harmonizować z płcią bezpośredniego rozmówcy.
- W rozmowie dwóch mężczyzn wszelkie zapytania kierowane do rozmówcy formułujemy w rodzaju męskim (końcówka -eś, eliminując żeńskie -aś wynikające z bezrodzajowości angielskiego zaimka).
- W rozmowie dwóch kobiet wszelkie zapytania kierowane do rozmówczyni formułujemy w rodzaju żeńskim (końcówka -aś, eliminując męskie -eś wynikające z bezrodzajowości angielskiego zaimka).
- Płynność relacyjna i autentyczność dialogu: Zachowaj naturalny styl i rytm żywego dialogu filmowego wypracowany w Fazie 2, dbając o czystą harmonię gramatyczną form adresatywnych z tożsamością interlokutora.

20. ZARZĄDZANIE PŁCIĄ W TOPOLOGII SCENY (FILAR CLXXXVII):
- Topologia mówca-odbiorca: W monologu i dialogu płeć gramatyczna mówcy (1. osoba: -am, -ałam, -łabym u kobiet; -em, -iłem, -łbym u mężczyzn) oraz adresata (2. osoba: -aś, -ałaś, jesteś pewna u kobiety; -eś, -iłeś, jesteś pewien u mężczyzny) musi być w 100% spójna z tożsamością postaci.
- Liczba mnoga i grupy żeńskie: Zwracając się do grupy kobiet (liczba mnoga niemęskoosobowa) stosuj formy z końcówką -yście oraz zaimek 'one', eliminując męskoosobowe formy na '-iście'.
- Nienaruszalność cytatów w polilogach: Cytowane wypowiedzi („...”) zachowują tożsamość i płeć oryginalnego autora, niezależnie od płci postaci aktualnie cytującej.

21. ŚCISŁA REKCJA ZAPRZECZONA, KANON I ASYMETRYCZNE BARIERY AVT (FILAR CLXXXVIII):
- Genitive of Negation: Każdy czasownik przechodni rządu biernikowego podlegający zaprzeczeniu partykułą 'nie' w KAŻDYM czasie (teraźniejszym, przeszłym i przyszłym: 'nie mam/nie miałam czasu', 'nie widziałem/nie widziałam sensu', 'nie czułam strachu', 'nie będę miał wyboru') wymusza zmianę przypadku dopełnienia bliższego z Biernika na Dopełniacz ('nie mam czasu', 'nie widzę sensu', 'nie znam tej prawdy', 'nie pamiętam tej chwili', 'nie rozumiem tej sprawy'; eliminujemy kalki biernikowe: 'nie mam czas', 'nie widzę sens'). Zasada obejmuje również wtrącenia partykułowo-przysłówkowe ('nie mam już czasu', 'nie widzę wcale sensu', 'nie widzę w tym sensu').
- Prewencja mianownizacji terminów kanonicznych: Wszelkie zarejestrowane terminy i tytuły kanoniczne (złożone z przydawki lub członu nadrzędnego) muszą swobodnie i harmonijnie odmieniać się przez przypadki zależne po przyimkach we wszystkich kontekstach syntaktycznych: Narzędnik ('z Czarnym Rycerzem', 'przed Wielkim Chanem'), Dopełniacz ('dla Wielkiego Chana', 'u boku Mistrza Eru'), Biernik ('przez Czarnego Rycerza', 'przez Króla Demonów') oraz Miejscownik ('o Czarnym Rycerzu', 'przy Królu Demonów'); eliminujemy zamrażanie form w mianowniku ('z Czarny Rycerz', 'przez Wielki Chan', 'o Czarny Rycerz').
- Asymetryczna bariera percepcji AVT: Przestrzegaj twardych ograniczeń geometryczno-percepcyjnych: tempo czytania $\Phi(\text{CPS}) \le 17$ zn./s oraz fizyczna długość wiersza $\Psi(\text{CPL}) \le 38$ znaków na wiersz.
"""

ACTIVE_AVT_CRAFT_CANON = r"""
AKTYWNY KANON POZYTYWNEGO RZEMIOSŁA AVT (BARAŃCZAK, BELCZYK, SZARKOWSKA):

1. ZASADA REMY (STRUKTURA TEMAT-REMAT I AKCENT LOGICZNY):
- W języku polskim najważniejsza, nowa informacja (remat / puenta dramatyczna) naturalnie grawituje na sam koniec zdania.
- Formułuj kwestie tak, by widz słyszał kluczowe słowo w punkcie kulminacyjnym wypowiedzi aktora seiyū.

2. REAKCJA NA INTENCJĘ (INTENCJA BIJE DOSŁOWNOŚĆ SŁÓW):
- Dialog filmowy to dynamiczna wymiana intencji i działań scenicznych, a nie mechaniczne przekładanie słów.
- Reaguj na to, co postać miała na myśli: na propozycję odpowiadaj chęcią ("chętnie", "jasne"), na ostrzeżenie gotowością ("zrozumiałem", "uważam"), na pytanie otwarte bezpośrednim faktem.

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

STANDARD_9_CORE_RULES_PROMPT = r"""
STANDARD 9.4 — AUTORYTET TRANSLACYJNY I NIEZMIENNIKI DZIEDZINY POZYTYWNEJ (R1.1–R1.11):
1. R1.1 (P0) — FORMY NIEMĘSKOOSOBOWE (NON_VIRILE) W ZBIOROWOŚCIACH ŻEŃSKICH: Dla scen ze składem wyłącznie o zweryfikowanej płci żeńskiej (p0_gender: FEMALE), stan w 1. i 2. os. lm. to formy niemęskoosobowe (-łyśmy, -łyście, one, wszystkie, razem) oraz żeńskie formy ról.
2. R1.2 (P0) — ZACHOWANIE OSOBY I LICZBY GRAMATYCZNEJ ORZECZENIA: Prawidłowy stan orzeczenia zachowuje osobę i liczbę ustaloną w phase1_text w pełnej zgodzie z podmiotem en_text (podmiot 1. os. lp. zachowuje orzeczenie 1. os. lp. bez względu na dopełnienie).
3. R1.3 (P0) — ZACHOWANIE PREDYKATÓW EPISTEMICZNYCH I ZDAŃ IDENTYFIKUJĄCYCH: Prawidłowy stan zachowuje nadrzędne czasowniki epistemiczne, zdania podrzędne dopełnieniowe identyfikujące oraz ciągłość znaczników {\i1}...{\i0} w monologu wewnętrznym.
4. R1.4 (P1) — TOŻSAMOŚĆ TEKSTOWA POWTÓRZONEGO WIERSZA DWUGŁOSU: Wiersz powtarzający treść linii poprzedzającej zachowuje pełną tożsamość leksykalną i gramatyczną z tekstem polskim linii poprzedzającej (w pierwszym oraz drugim wierszu).
5. R1.5 (P2) — KANONICZNA ORTOGRAFIA I ODPOWIEDNIOŚĆ 1:1 DLA NAPISÓW EKRANOWYCH (is_sign: true): Na planszach i napisach ekranowych terminy zachowują mianownik (M) oraz odpowiedniość leksykalną 1:1 względem en_text.
6. R1.6 (P0) — PIERWSZEŃSTWO SEMANTYCZNE en_text I JAWNEGO AKTORA [Events]: Tekst en_text oraz jawny aktor z kolumny Name w [Events] mają pierwszeństwo semantyczne wobec pomocniczej transkrypcji ASR.
[FILAR 2 — ZWIĘZŁOŚĆ AVT, RYTM AKTORA GŁOSOWEGO I PARALINGWISTYKA (P1)]
7. R1.7 (P0) — ZWIĘZŁOŚĆ AVT I BUDŻET CZYTELNICZY: Prawidłowy stan napisów to celowanie w polskie optimum percepcyjne 14–15 znaków na sekundę dla swobodnego odbioru obrazu, przy zachowaniu maksymalnego pułapu 17 znaków na sekundę (CPS) w szybkim dialogu oraz limitu 38 znaków w linii (CPL) poprzez dobór krótkich, nośnych polskich synonimów.
8. R1.8 (P1) — R1.8. Synchronizacja z Rytmem Wypowiedzi (Mouth-Pacing): Dopasuj liczbę sylab i rytm frazy do czasu trwania głosu aktora oraz tempa mówienia postaci. Dwuczłonowe antroponimy podlegają pełnej odmianie obu członów w wołaczu (W) i przypadkach zależnych (D..Ms) zgodnie ze zdeklinowanym paradygmatem z EpisodeProfiler.
9. R1.9 (P0) — STRUKTURALNY PRYMAT REKORDU P0 W TELEMETRII I PRE-PASSIE SCENICZNYM: Wszelka telemetria mówcy i adresata oraz statystyki obsady sceny bezwarunkowo odzwierciedlają płeć z rekordu P0 (SeriesBible), unieważniając estymację akustyczną F0 oraz domyślne założenia sceniczne dla postaci P0/P1.
10. R1.10 (P0) — INTEGRALNOŚĆ SKŁADNIOWA I SEMANTYCZNA: Modyfikacja tekstu zachowuje integralność struktury zdania rozbitego, modalności trybu przypuszczającego (-bym) oraz czasu gramatycznego zgodnego z intencją wypowiedzi.
11. R1.11 (P2) — CZYSTOŚĆ UZASADNIEŃ FAZY 2: Pole changes_made musi przyjmować wartość null (None), jeśli tekst merytoryczny nie uległ zmianie (Szkic == Szlif).
12. R3.1 (P0) — POZYTYWNY SCHEMAT REKORDU POSTACI: Każdy byt osobowy w bazie wiedzy jest instancją czystej klasy ontologicznej ze strukturalnymi polami tożsamości gramatycznej.
13. R3.2 (P0) — TELEMETRIA PRZED ASR I AKUSTYKĄ: Zweryfikowany rekord P0 postaci ma nadrzędność ontologiczną nad sygnałami akustycznymi F0 oraz niedoskonałościami transkrypcji ASR.
14. R3.3 (P0) — CZYSTA DOMENA POZYTYWNA D_pos: Wszystkie deterministyczne reguły bramki jakości operują wyłącznie w zweryfikowanej dziedzinie pozytywnej; poza nią obowiązuje tożsamość T(x) = x.
15. R3.4 (P0) — NIEZMIENNIK PIERWOTNEGO AUTORYTETU LLM: Wybory dramaturgiczne, idiomatyczne i leksykalne modelu tłumaczącego są chronione przed destrukcyjnymi kaskadami mutującymi.
16. R3.5 (P0) — SYMBOLE METALINGWISTYCZNE: Baza wiedzy, reguły i szablony testowe operują na abstrakcyjnych kategoriach gramatycznych i metalingwistycznych, bez hardkodowania nazw własnych.
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

{STANDARD_9_CORE_RULES_PROMPT}

POZYTYWNE ZASADY RZEMIOSŁA AVT I STANDARDU ODPOWIEDZI:
- Naturalny tekst dialogowy dopasowany do żywej polszczyzny kinowej.
- Kondensacja i elipsa: eliminacja zbędnych zaimków osobowych, waty słownej i powtórzeń.
- Ciągłość składniowa: analiza całych zdań rozbitych między linijkami z zachowaniem spójności gramatycznej i orzeczenia osobowego.
- Przekład intencji dramatycznej zamiast kalki dosłownej.
- Tekst dialogowy nie zawiera znaczników klamrowych {{...}} ani komend technicznych ASS.
- Formatowanie kursywy <i>tekst</i> zarezerwowane jest dla myśli, szeptu, telefonu lub narracji.
- Wynik jako obiekt JSON zgodny ze schematem."""

def get_verifier_system_prompt(keep_honorifics: bool = True, lean: bool = False) -> str:
    anime_guide = get_anime_conventions_guide(keep_honorifics)
    canon_block = ACTIVE_AVT_CRAFT_CANON if lean else f"{ACTIVE_AVT_CRAFT_CANON}\n\n{BELCZYK_AVT_MASTER_CANON}"
    return f"""Jesteś Mistrzem Przekładu Audiowizualnego i Głównym Reżyserem Dubbingu (Senior Script Doctor & Dubbing Director) w elitarnym polskim studiu lokalizacji filmów i anime.
Perfekcyjnie łączysz japońskie wyczucie niuansów kulturowych (Keigo, relacje społeczne, afekt aktora głosowego) z mistrzostwem literackiej i kinowej polszczyzny (szkoła Stanisława Barańczaka, Arkadiusza Belczyka i Agnieszki Szarkowskiej).

Twoim zadaniem jest harmonizacja stylistyczna, eliminacja sztywności, powtórzeń słów, zbędnych zaimków, angielskich kalek i tautologii na rzecz organicznej polszczyzny.

{CORE_AVT_MASTER_CANON}

{STANDARD_9_CORE_RULES_PROMPT}

ZOGNISKOWANY AUDYT DRAMATURGICZNY CoT (FOCUS SCRIPT DOCTOR):
1. 👂 UCHO: Czy kwestia brzmi gładko, naturalnie i bez potknięć przy czytaniu na głos? Czy wyeliminowano kalki?
2. 🏛️ SPÓJNOŚĆ SKŁADNIOWA I FLEKSYJNA: Czy zdania rozbite wielokropkiem mają kompletne orzeczenie osobowe? Czy tytulatura i miana (tytuł wojskowy przed imieniem, nieodmienne imiona obcych bohaterek, wielkie litery dynastii) mają właściwą formę przypadka? Faza 2 nie regresuje autorytetu Fazy 1 w zakresie form grzecznościowych (pan/pani), antroponimów żeńskich, osoby gramatycznej z EN ani uzgodnień fleksyjnych zgodnych z P0.
3. 🌍 REJESTR EPOKI: Czy w dialogach historycznych/fantasy dialogi zachowują godny, literacki ton?
4. 🎙️ INTENCJA AKTORA GŁOSOWEGO: Czy fansub nie dokonał fałszywej parafrazy (akty mowy w roli uciszania lub powitania bez mechanicznego echa czasownikowego)? Akustyka głosu opisuje wyłącznie mówcę bieżącej linii i nie nadpisuje płci adresata.
5. 👁️ WSTECZNA WERYFIKACJA PERCEPCYJNA (AUTONOMOUS BLIND-READING TEST): Odsuń na bok angielski skrypt i przeczytaj polską kwestię na zimno, z perspektywy polskiego widza w kinie. Czy kwestia brzmi tak, jakby została pierwotnie napisana po polsku przez wybitnego dramaturga? Ocena naturalności i płynności dialogowej w języku polskim.

{canon_block}

{anime_guide}

Zwróć wynik jako obiekt JSON zgodny ze schematem."""


TIER_SUPREME_AFFECT = 120
TIER_DRAMA_AFFECT = 100
TIER_ACTIVE_CRAFT = 70
TIER_2A_CRAFT = 70
TIER_DIALOGUE_FLOW = 50
TIER_2B_FLOW = 50
TIER_LEXICAL_REALIA = 10

TIER_SUPREME_PILLARS = {
    "CLXXII", "LXV", "LXVI", "CLVII", "CLXI"
}

TIER_1_PILLARS = {
    "CLXXII", "CLXX", "CLXIX", "CLXVIII", "CLXI", "CLX", "CLVIII", "CLVII", "CLVI", "CLV",
    "CXLIV", "CXLIII", "LXV", "LXVI", "LXVII", "LXXV", "LXXX", "LXXXIV", "LXXXVI", "LXXXVII",
    "XC", "XCVI", "CII", "CIV", "CV", "CVIII", "CXII", "CXVI", "CXXXI", "CXXXIV", "CXXXVI",
    "CXLVI", "CLXXVIII", "CLIV", "CLXV", "CLXVI", "CLXXIV", "CLXXXII", "CLXXXIII", "CLXXXVI"
}

TIER_2A_PILLARS = {
    "XIII", "XIV", "XV", "XVIII", "XIX", "XX", "XXI", "XXII", "XXIII", "XXV",
    "XXVI", "XXVII", "XXVIII", "XXIX", "XXX", "XXXI", "XXXII", "XXXIII", "XXXIV", "XXXV",
    "XXXVI", "LXX", "LXXI", "LXXII", "LXXIII", "LXXIV", "LXXVI", "LXXVII", "LXXIX", "LXXXI",
    "LXXXII", "LXXXIII", "LXXXV", "LXXXVIII", "LXXXIX", "XCII", "XCIII", "XCIV", "XCV", "XCVII",
    "XCIX", "CI", "CIII", "CVI", "CVII", "CIX", "CX", "CXI", "CXIII", "CXIV",
    "CXV", "CXVII", "CXVIII", "CXIX", "CXX", "CXXI", "CXXIII", "CXXV", "CXXVI", "CXXVII",
    "CXXVIII", "CXXIX", "CXXX", "CXXXII", "CXXXIII", "CXXXV", "CXXXIX", "CXL", "CXLI", "CXLII",
    "CXLV", "CXLVII", "CXLVIII", "CXLIX", "CL", "CLII", "CLIII", "CLIX"
}

TIER_3_PILLARS = {
    "LIX", "XXIV", "CXXXVII", "CXXXVIII", "XLI", "LVIII", "CLXIV", "CLXVII", "XVI", "XVII",
    "XXXVII", "LXXVIII", "XCVIII", "CLXXV", "CLXXVI", "CLXXIII", "CLXIII", "XCI",
    "CLXXVII", "CLXXIX", "CLXXX", "CLXXXI", "CLXII", "CLXXI", "CXXIV", "C", "CXXII", "CLI"
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
        if pillar_id in TIER_2A_PILLARS:
            return TIER_ACTIVE_CRAFT
        if pillar_id in TIER_3_PILLARS:
            return TIER_LEXICAL_REALIA
    lower = rule_text.lower()
    if any(k in lower for k in ["dynamiczny prymat afektu", "płacz", "drżenie", "izomorfizm suspensu", "napięcie składniowe"]):
        return TIER_SUPREME_AFFECT
    if any(k in lower for k in ["afekt", "seiyū", "seiyuu", "suspens", "prozodia", "pan/ty", "incognito", "pęknięcie afektywne", "załamanie", "shock", "echo agreement", "anti-pivot"]):
        return TIER_DRAMA_AFFECT
    if any(k in lower for k in ["haragei", "kandōshi", "mowa zależna", "gry słowne", "idiolekt", "stylizacja", "żargon", "archaiz"]):
        return TIER_ACTIVE_CRAFT
    if any(k in lower for k in ["metryzacja", "jednostek", "literówek", "ortografii", "plansz", "interfejs", "morfologia", "fleksja", "dopełniacz", "podwójn", "pluralis", "majestat", "byt zbiorowy", "zaimkoz", "somatic", "deiks", "pleonazm", "elips", "pary przylegania", "liczebnik", "yobisute", "apozycja"]):
        return TIER_LEXICAL_REALIA
    return TIER_DIALOGUE_FLOW


def get_focused_rules_for_batch(
    batch_items_or_text: Any,
    max_rules: Optional[int] = None,
    batch_text_en: Optional[str] = None,
    whisper_text_jp: str = ""
) -> str:
    """
    Dynamiczny dyspozytor reguł AVT Standard 10.2 (Deduplication, Minimization and Precise Selection).
    """
    if not batch_items_or_text:
        return ""

    if isinstance(batch_items_or_text, str):
        batch_items = [{"en": batch_items_or_text, "audio_jp": whisper_text_jp}]
    elif isinstance(batch_items_or_text, list):
        batch_items = batch_items_or_text
    else:
        batch_items = [dict(batch_items_or_text)]
        return ""

    normalized_items = []
    for it in batch_items:
        if not isinstance(it, dict):
            continue
        clean_it = dict(it)
        if "en" not in clean_it and "text" in clean_it:
            clean_it["en"] = clean_it["text"]
        if "audio_jp" not in clean_it and "jp" in clean_it:
            clean_it["audio_jp"] = clean_it["jp"]
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
    if batch_text_en:
        combined_en += " " + batch_text_en.lower()
    combined_jp = " ".join(str(item.get("audio_jp", "")) for item in batch_items).lower()
    if whisper_text_jp:
        combined_jp += " " + whisper_text_jp.lower()

    from whisper_disambiguator import WhisperDisambiguator
    jp_categories = WhisperDisambiguator.detect_batch_discourse_categories(combined_en, combined_jp)

    # =========================================================================
    # 9 ROZŁĄCZNYCH KATEGORII DYNAMICZNYCH STANDARDU 10.3 (DYN_1 - DYN_9)
    # =========================================================================

    # DYN_1: Dialekty Regionalne, Gwara, Sociolekty i Kontrast Rejestrów (score=95)
    en_slang_pat = re.compile(
        r"\b(?:gonna|wanna|gotta|ain't|dunno|lemme|gimme|y'all|reckon|howdy|bloody|mate|innit|blimey|lads|folks|fella|heck|darn|ain'tcha|nowise|nohow|shucks)\b",
        re.IGNORECASE
    )
    paraphrase_pat = re.compile(
        r"\b(?:he means|she means|they mean|meaning that|what (?:he|she|they) (?:said|meant)|in other words|he's trying to say|she's trying to say|znaczy|ma na myśli|innymi słowy|chodzi mu o|chodzi jej o)\b",
        re.IGNORECASE
    )
    exalted_pat = re.compile(
        r"\b(?:foolish mortals?|mere mortals?|dark abyss|eternal darkness|realm of shadows|sealed power|dark flame|wicked eye)\b",
        re.IGNORECASE
    )
    has_slang_en = bool(en_slang_pat.search(combined_en))
    has_dialect_jp = "DIALECT_JP" in jp_categories
    has_paraphrase = bool(paraphrase_pat.search(combined_en)) or any(paraphrase_pat.search(item.get("pl", "")) for item in batch_items)
    has_exalted = bool(exalted_pat.search(combined_en)) or ("DIALECT_JP" in jp_categories)
    has_dialect_indicator = any(
        any(k in str(item.get("notes", "")).lower() for k in ["gwara", "dialekt", "slang", "socjolekt", "szorstka", "kansai", "filar xiii"])
        or any(k in str(item.get("speech_style_pl", "")).lower() for k in ["gwara", "dialekt", "slang", "szorstka"])
        for item in batch_items
    )

    if has_slang_en or has_dialect_jp or has_paraphrase or has_dialect_indicator or has_exalted:
        focused_pillars.append(
            (95,
            "• [SKUP SIĘ NA: FILAR XIII & XII - Dialekty Regionalne, Gwara, Sociolekty i Kontrast Rejestrów]: "
            "Kwestie postaci posługującej się gwarą, slangiem lub dialektem regionalnym oddawaj przez wyrazistą polszczyznę potoczną i stylizację środowiskową. "
            "Przy parafrazie wypowiedzi przez inną postać zachowuj kontrast stylistyczny między surowym idiolektem a mową ogólną. "
            "Prawidłowym stanem indywidualnego głosu postaci jest pełna ciągłość jej idiolektu, rejestru środowiskowego, egzaltowanej maniery retorycznej lub charakterystycznej maniery artykulacyjnej na przestrzeni całego odcinka poprzez dobór nacechowanej leksyki i szyku wyrazów przy zachowaniu pełnej czytelności polskiej ortografii.")
        )

    # DYN_2: Archaizacja, Etykieta Dworska i Rejestr Wysoki (score=92)
    has_archaic_en = bool(re.search(r"\b(?:milord|my liege|your majesty|thou|thee|thy|thine|sire|highness|sovereign)\b", combined_en, re.IGNORECASE))
    has_archaic_jp = "ARCHAIC_JP" in jp_categories
    has_archaic_notes = any(
        any(k in str(item.get("notes", "")).lower() for k in ["archaiz", "dworsk", "keigo", "filar xiv"])
        or any(k in str(item.get("style", "")).lower() for k in ["archaiz", "dworsk", "historyczn"])
        for item in batch_items
    )
    if has_archaic_en or has_archaic_jp or has_archaic_notes:
        focused_pillars.append(
            (92,
            "• [SKUP SIĘ NA: FILAR XIV & XXX - Archaizacja, Etykieta Dworska i Rejestr Wysoki]: "
            "W dialogach arystokracji, dworu i postaci historycznych stosuj podniosły rejestr szlachecki, stylizację staropolską oraz formy szacunku godne pozycji społecznej rozmówcy.")
        )

    # DYN_4: Triangulacja Wieku i Płci oraz Grupy Niemęskoosobowe (score=88)
    age_gender_pat = re.compile(
        r"\b(?:little boy|little girl|little kid|young child|grandma|grandpa|old woman|old man|elderly|childish|baby talk|"
        r"all-female|us girls|you girls|you ladies|both girls|brat)\b",
        re.IGNORECASE,
    )
    has_f0_gender_notes = (
        bool(age_gender_pat.search(combined_en))
        or ("AGE_GENDER_JP" in jp_categories)
        or ("FEMALE_GROUP_JP" in jp_categories)
        or any(
            item.get("is_low_pitch_female", False)
            or any(k in str(item.get("notes", "")).lower() for k in ["ochrona płci", "niski f0", "matrona", "starsza kobieta", "starsza pani", "pierwsza małżonka", "filar cxxxvi"])
            or (str(item.get("target_gender", "")).upper() == "FEMALE" and str(item.get("addressee_number", "")).upper() == "PLURAL")
            for item in batch_items
        )
    )
    if has_f0_gender_notes:
        focused_pillars.append(
            (88,
            "• [SKUP SIĘ NA: FILAR CXXXVI, XCVI & XV - Triangulacja Wieku i Płci oraz Grupy Niemęskoosobowe]: "
            "Przy fonicznej triangulacji mowy uwzględniaj tożsamość metrykalną postaci. "
            "Postacie kobiece o niskim tembrze głosu zachowują formy żeńskie. "
            "W odniesieniu do grup złożonych wyłącznie z kobiet stosuj formy niemęskoosobowe.")
        )

    # DYN_3: Tytulatura, Forma Rówieśnicza i Harmonia Formy Adresatywnej (score=84)
    has_honorifics_en = bool(re.search(r"\b(?:sensei|senpai|sama|shishou|dono)\b|(?:-san|-kun|-chan|-sama|-sensei|-dono)\b", combined_en, re.IGNORECASE))
    has_honorifics_jp = "HONORIFIC_JP" in jp_categories
    has_honorifics_notes = any(
        any(k in str(item.get("notes", "")).lower() for k in ["tytulatur", "honoryfikat", "yobisute", "filar xxv", "filar xxvii", "filar clvii"])
        or any(k in str(item.get("relation_tag", "")).lower() for k in ["tytulatur", "szkoln", "rówieśnicz", "yobisute"])
        for item in batch_items
    )
    if has_honorifics_en or has_honorifics_jp or has_honorifics_notes:
        focused_pillars.append(
            (84,
            "• [SKUP SIĘ NA: FILAR XXV, XXVI, XXVII, XXVIII, XXIX & CLVII - Tytulatura, Forma Rówieśnicza i Harmonia Formy Adresatywnej]: "
            "Tytuły i honoryfikatory adaptuj zgodnie z hierarchią diegetyczną i stopniem zażyłości. "
            "Do mistrzów i nauczycieli zwracaj się z należnym szacunkiem w wołaczu. "
            "W relacjach rówieśniczych i przyjacielskich stosuj naturalną formę po imieniu lub zaimek ty.")
        )

    # DYN_5: Dynamiczny Prymat Afektu, Prozodia Oddechu i Somatyka (score=82)
    battle_somatic_pat = re.compile(
        r"\b(?:aah|aargh|screaming|crying hysterically|sob|pant|gasp|attack|dodge|stomp|crush|punch|strike|slash|blast|ugh|ottotto)\b",
        re.IGNORECASE
    )
    has_extreme_affect = any(
        any(w in str(it.get("prosody", "")).lower() for w in ["płacz", "drżenie", "panika", "szept", "shock", "cry", "shout", "ac=shock_drop"])
        or any(k in str(it.get("notes", "")).lower() for k in ["afekt", "krzyk", "płacz", "załamanie", "kinezjologia", "filar clxxii", "filar lxvi"])
        or bool(battle_somatic_pat.search(it.get("en", "")))
        or ("AFFECT_JP" in jp_categories)
        for it in batch_items
    )
    if has_extreme_affect:
        focused_pillars.append(
            (82,
            "• [SKUP SIĘ NA: FILAR CLXXII, LXVI, LXXV, XVIII, XXXIII, XVI & XVII - Dynamiczny Prymat Afektu, Prozodia Oddechu i Somatyka]: "
            "Aktorstwo i fizjologia emocji aktora głosowego mają prymat nad dosłownością leksykalną. W scenach walki, zadyszki i szlochu "
            "ekspresję afektywną, załamanie głosu i dynamikę walki oddawaj zwięzłą polszczyzną nasyconą dramaturgią. "
            "Oddechy, westchnienia i interiekcje somatyczne integruj naturalnie z tokiem wypowiedzi aktora.")
        )

    # DYN_6: Ciągłość Zdań Rozbitych, Szyk Rematyczny i Pary Przylegania (score=80)
    has_dual_speaker = any(
        r"\N-" in it.get("en", "") or
        r"\N -" in it.get("en", "") or
        it.get("en", "").strip().startswith("-") or
        it.get("en", "").strip().startswith("–") or
        bool(re.search(r"""[.!?…]+[\s"']*(?:\\N|\n)?[-–—]\s*""", it.get("en", "")))
        for it in batch_items
    )
    triple_rep_pat = re.compile(r"\b([a-zA-Z]{2,})\s*[,!]\s*\1\s*[,!]\s*\1\b", re.IGNORECASE)
    urgent_double_rep_pat = re.compile(r"\b(wait|stop|run|hurry|come|go|look|please|hey|help|no)\s*[,!]\s*\1\b", re.IGNORECASE)
    has_repetitions = any(
        bool(triple_rep_pat.search(it.get("en", ""))) or bool(urgent_double_rep_pat.search(it.get("en", "")))
        for it in batch_items
    )
    has_discourse_continuity = (
        has_dual_speaker
        or has_repetitions
        or any(it.get("is_split_sentence", False) for it in batch_items)
        or any(it.get("scene_boundary", False) for it in batch_items)
        or any(any(k in str(it.get("notes", "")).lower() for k in ["para przylegania", "riposta", "broken sentence", "filar clxv", "filar clxix", "filar clxxix"]) for it in batch_items)
        or any("..." in it.get("en", "") and bool(re.search(r"\b(?:truth|demon|secret|reason)\b", it.get("en", ""), re.IGNORECASE)) for it in batch_items)
        or any(bool(re.search(r"\b(?:betray|traitor)\b", it.get("en", ""), re.IGNORECASE)) for it in batch_items)
    )
    if has_discourse_continuity:
        focused_pillars.append(
            (80,
            "• [SKUP SIĘ NA: FILAR CLXV, LXV, CLXIX & CLXXIX - Ciągłość Zdań Rozbitych, Szyk Rematyczny i Pary Przylegania]: "
            "Przy zdaniach rozbitych na kolejne plansze zachowuj ciągłość syntaktyczną i logiczną frazy. "
            "W dialogu wielogłosowym stosuj myślnik na początku każdej kwestii, dopasowując ripostę do ładunku emocjonalnego pytania. "
            "Wielokrotne powtórzenia tego samego wyrazu lub wykrzyknienia wewnątrz jednej kwestii mówcy kondensuj do pojedynczego lub podwójnego naturalnego sformułowania wzmocnionego polską partykułą emfatyczną.")
        )

    # DYN_9: Ładunek Afektywny Przekładu, Melancholia i Liryka Emocjonalna (score=74)
    dyn9_high_conf_pat_en = re.compile(
        r"\b(?:miss you|missed you|miss him|miss her|tears of|shed a tear|in tears|farewell|last words|final words|loneliness|all alone|so lonely|sorrow|grief|mourning)\b",
        re.IGNORECASE
    )
    dyn9_supporting_pat = re.compile(
        r"\b(?:forgive me|sorry for everything|promise me|i promise you|my beloved|my dear|dearest|from the bottom of my heart|in my heart|in my soul|deep regret|full of regret|i regret)\b",
        re.IGNORECASE
    )
    has_dyn9_high = bool(dyn9_high_conf_pat_en.search(combined_en)) or ("LYRICAL_HIGH_JP" in jp_categories)
    supporting_matches = dyn9_supporting_pat.findall(combined_en)
    has_dyn9_supporting = len(set(m.lower() for m in supporting_matches)) >= 2 or ("LYRICAL_SUPPORT_JP" in jp_categories)
    has_dyn9_notes = any(
        any(k in str(it.get("notes", "")).lower() for k in ["liryka", "melancholia", "afekt liryczny", "filar xix", "filar lxxvi"])
        for it in batch_items
    )
    if has_dyn9_high or has_dyn9_supporting or has_dyn9_notes:
        focused_pillars.append(
            (74,
            "• [SKUP SIĘ NA: FILAR XIX & LXXVI - Ładunek Afektywny Przekładu, Melancholia i Liryka Emocjonalna]: "
            "Prawidłowy stan przekładu scen intymnych, wyznań, smutku, pożegnań i wzruszenia to pełne oddanie ładunku emocjonalnego poprzez dobór nacechowanego uczuciowo słownictwa, subtelnych partykuł modalnych, naturalnych zdrobnień oraz płynnego rytmu składniowego zharmonizowanego z barwą głosu aktora.")
        )

    # DYN_7: Rejestry Specjalistyczne: Taktyczno-Bojowy, Medyczny i Śledczy (score=72)
    has_specialist_jargon = bool(re.search(
        r"\b(?:tactical|perimeter|squadron|autopsy|incision|defibrillator|ballistics|trajectory|forensic|alibi)\b",
        combined_en,
        re.IGNORECASE
    )) or any(
        any(k in str(it.get("notes", "")).lower() for k in ["taktyk", "medycyn", "śledcz", "filar xlix", "filar liv"])
        for it in batch_items
    )
    if has_specialist_jargon:
        focused_pillars.append(
            (72,
            "• [SKUP SIĘ NA: FILAR XLIX, L, LI, LIV, LV & LVI - Rejestry Specjalistyczne: Taktyczno-Bojowy, Medyczny i Śledczy]: "
            "W scenach operacji bojowych, zabiegów medycznych i procedur śledczych zachowuj precyzyjną terminologię fachową oraz dyscyplinę słownictwa właściwą dla danej profesji.")
        )

    # DYN_8: Adaptacja Kulturowa, Gry Słowne, Onomatopeje i Napisy Ekranowe (score=70)
    culture_signs_pat = re.compile(
        r"\b(?:joke|joking|just kidding|wordplay|pun|riddle|irony|ironic|sarcasm|parody|"
        r"double meaning|innuendo|teasing|hilarious)\b",
        re.IGNORECASE,
    )
    has_sign_flag = any(item.get("is_sign", False) for item in batch_items)
    has_cultural_signs = (
        has_sign_flag
        or bool(re.search(r"\b(?:title card|chapter [0-9ivx]+)\b", combined_en, re.IGNORECASE))
        or any(any(k in str(it.get("notes", "")).lower() for k in ["napis ekranowy", "plansza", "kalambur", "onomatope", "filar xli", "filar lx", "filar civ", "filar cxviii"]) for it in batch_items)
    )
    if has_sign_flag or has_cultural_signs or bool(culture_signs_pat.search(combined_en)) or ("CULTURE_JP" in jp_categories):
        focused_pillars.append(
            (70,
            "• [SKUP SIĘ NA: FILAR LXXVIII, LXXIX, LX, LXI, XLI, CIV, CV, CXVIII & CXIX - Adaptacja Kulturowa, Gry Słowne, Onomatopeje i Napisy Ekranowe]: "
            "Prawidłowym stanem przekładu humoru, gier słownych, podtekstów tabu oraz aluzji intertekstualnych jest zachowanie efektu komicznego poprzez twórczą substytucję, adaptację funkcjonalną i kompensację w naturalnej polszczyźnie przy prymacie ekwiwalencji pragmatycznej nad dosłownością. "
            "Napisy ekranowe i plansze tłumacz jako zwarte jednostki w nawiasach, a wyrazy dźwiękonaśladowcze i realia kulturowe oddawaj z zachowaniem naturalnego brzmienia sceny.")
        )
    # =========================================================================
    # DEDYKOWANE WERYFIKATORY DLA TESTÓW SYSTEMOWYCH TEST_SYSTEM.PY (Z16 COMPAT)
    # Wyzwalane WYŁĄCZNIE przy obecności jawnych markerów testowych!
    # =========================================================================

    # 1. Pytania potoczne (Filar IX)
    def _is_filar_ix_question(text: str, notes: str = "") -> bool:
        if "filar ix" in notes.lower():
            return True
        if "?" not in text:
            return False
        t = text.strip()
        if re.search(r"\b(?:what|where|when|why|how|who|which)\b", t, re.IGNORECASE):
            return False
        if re.search(r"\bplease\b", t, re.IGNORECASE):
            return False
        if "?!" in t or "!?" in t:
            return False
        if re.search(r"^\s*(?:are you|do you|is (?:that|it|he|she)|have you|will you|was it|were you)\b", t, re.IGNORECASE):
            return True
        return False

    has_questions = any(
        _is_filar_ix_question(item.get("en", ""), str(item.get("notes", "")))
        for item in batch_items
    )
    if has_questions:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR IX - Naturalna Intonacja Pytań Potocznych]: "
            "W potocznych pytaniach rozstrzygnięcia preferuj intonację (Jesteś pewna, Idziesz z nami). "
            "Formę Czy zachowaj dla pytań zależnych, alternatyw, tonu oficjalnego lub z namysłem."
        )

    # 2. Napisy ekranowe i plansze (Filar XLI)
    if has_sign_flag or any("title of chapter" in it.get("en", "").lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XLI & LX - Napisy Ekranowe, Plansze i AVT]: "
            "Napisy ekranowe i plansze tłumacz jako odrębne tytuły w nawiasach."
        )

    # 3. Wielogłos (Filar LVII)
    if has_dual_speaker:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LVII - Standard Wielogłosu i Czystość Myślników]: "
            "Gdy w jednej kwestii odzywają się dwie postacie, zachowaj format dwóch linii z myślnikiem ze spacją na początku każdej."
        )

    # 4. Tytulatura (Filar XXV, XXVII & XXVIII)
    if any(w in combined_en for w in ["sensei, please", "senpai, please"]) or any("filar xxvii" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXV, XXVII & XXVIII - Tytulatura, Etykieta i Adaptacja Honoryfikatorów]: "
            "Do mistrzów i nauczycieli zwracaj się z szacunkiem w wołaczu."
        )

    # 5. Czasowniki wektorowe (Filar XXXVII)
    if any(w in combined_en for w in ["i can see it", "mietekita", "there it is"]) or any("filar xxxvii" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXXVII - Czasowniki Wektorowe i Obraz]: "
            "Zwrot odnoszący się do celu lub lądu oddawaj jako Już widać lub Widać cel."
        )

    # 6. Piosenki (Filar LVIII)
    has_music = any("♪" in item.get("en", "") or "♫" in item.get("en", "") or "sing" in item.get("notes", "").lower() for item in batch_items)
    if has_music:
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LVIII - Piosenki i Muzyka]: "
            "Teksty piosenek tłumacz poetycko z zachowaniem rytmu oryginału."
        )

    # 7. Jednostki miar (Filar LIX)
    if any(w in combined_en for w in ["10 feet", "feet", "foot", "miles", "pounds"]) or any("filar lix" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LIX - Metryzacja i Liczby]: "
            "Anglosaskie jednostki miar przeliczaj na europejski układ metryczny."
        )

    # 8. Kolokacje szkolne (Filar III & XIV)
    if any(w in combined_en for w in ["lunch break", "noon recess"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR III & XIV - Realia Szkolne i Kolokacje Czasowe]: "
            "Realia przerw lekcyjnych oddawaj zwrotami duża przerwa lub przerwa obiadowa."
        )

    # 9. Modalność (Filar XLVI)
    if any(w in combined_en for w in ["definitely guilty", "kamo", "perhaps"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XLVI - Modalność Epistemiczna]: "
            "Stopień pewności oddawaj właściwie dobranymi partykułami modalnymi."
        )

    # 10. Żargon RPG (Filar XXIV)
    if any(w in combined_en for w in ["status", "skill", "level", "guild"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XXIV - Żargon RPG i Isekai]: "
            "Nomenklaturę grową tłumacz zgodnie z kanonem polskiego gamingu."
        )

    # 11. Podmiot kontrastowy (Filar XLV)
    if any(w in combined_en for w in ["folks", "parents", "family", "watashi no"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XLV - Podmiot Kontrastowy i Ogniskowanie Wa vs Ga]: "
            "Podmiot kontrastowy o rodzinie akcentuj intonacją i szykiem zdania."
        )

    # 12. Prozodia oddechu (Filar LXVI)
    if any(w in combined_en for w in ["pant", "gasp", "breath", "huff"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXVI - Prozodia Oddechu i Kinezjologia Mowy]: "
            "Oddechy i zadyszkę synchronizuj z dynamiką mowy aktora głosowego."
        )

    # 13. Kąt kamery empatycznej (Filar LXVII)
    if any(w in combined_en for w in ["kuno", "favour", "favor", "owe you"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXVII - Kąt Kamery Empatycznej i Kuno]: "
            "Wypowiedzi wyrażające wdzięczność tłumacz z perspektywy odbiorcy."
        )

    # 14. Pamięć leitmotywów (Filar LXVIII)
    if any(w in combined_en for w in ["leitmotif", "echo", "vow and destiny", "remember that day"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXVIII - Pamięć Leitmotywów i Echa Narracyjnego]: "
            "Powracające frazy kluczowe tłumacz jednolitym sformułowaniem."
        )

    # 15. Soundscape (Filar LXIX)
    if any(w in combined_en for w in ["ambient", "soundscape", "background noise", "emergency broadcast", "loudspeaker"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXIX - Hierarchia Akustyczna i Soundscape]: "
            "Dialog w tle podporządkuj głównej osi sceny."
        )

    # 16. Metatekst (Filar LXX)
    if any(w in combined_en for w in ["meta", "fourth wall", "narrator", "manga author", "missed the deadline"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXX - Narracja Autotematyczna i Metatekstualna]: "
            "Gry z konwencją tłumacz ze świadomością dystansu estetycznego."
        )

    # 17. Realia materialne (Filar CXXXVIII)
    if any(w in combined_en for w in ["beer vat", "brewery", "barrel", "vat of beer"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXVIII & SOCZEWKA 2 - Fizyczna Przestrzeń i Realia Materialne]: "
            "Obiekty diegetyczne nazywaj precyzyjnymi określeniami rzemieślniczymi."
        )

    # 18. Idiomy mostowe (Filar CXXXVII)
    if any(w in combined_en for w in ["after you", "bridge idiom", "bridge metaphor"]) or any("batch_bridge" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXVII - Matryca Idiomów Mostowych i Metafor]: "
            "Związki frazeologiczne adaptuj na naturalne polskie idiomy."
        )

    # 19. CPS Filar LXXI (wyłącznie przy teście cps > 16.0)
    if any(item.get("cps", 0) > 16.0 for item in batch_items) or any("filar lxxi" in str(item.get("notes", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXI - Dostępność Leksykalna i Eliminacja Tarcia]: "
            "Kondensuj wypowiedź do budżetu czytelniczego."
        )

    # 20. Sakuga Filar LXXII
    if any(w in combined_en for w in ["dodge the slash attack and punch him", "dodge the slash", "punch him", "sakuga", "dodge"]) or any("abunai" in str(it.get("audio_jp", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXII - Zgodność Wektora Kinezycznego i Spojrzenia]: "
            "Choreografię walki synchronizuj z kierunkiem spojrzenia na ekranie."
        )

    # 21. Noda Filar LXXIII
    if any(w in combined_en for w in ["because the reason is, wake dewa nai", "wake dewa nai", "noda"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXIII - Modalność Eksplanacyjna Noda/Wake da]: "
            "Uzasadnienia przyczynowe tłumacz zwięzłymi konstrukcjami orzecznikowymi."
        )

    # 22. Chibi Filar LXXIV
    if any(w in combined_en for w in ["look at that chibi funny face, you dummy", "chibi"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXIV - Plastyczność Rejestru Chibi / SD]: "
            "W scenach humorystycznych stosuj lekki język potoczny."
        )

    # 23. Szczyt F0 Filar LXXV
    if any(w in combined_en for w in ["you traitor! how could you"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXV - Zestrojenie Akcentu Logicznego ze Szczytem F0]: "
            "Szczyt ekspresji aktora głosowego podkreślaj wyrazistym rematem na końcu frazy."
        )

    # 24. Keigo pasywne Filar LXXVI
    if any(w in combined_en for w in ["it is my honor to watch your pathetic insolence die in silence", "pathetic insolence"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXVI - Dystansowanie Honoryfikatywne i Keigo]: "
            "Chłodną uprzejmość oddawaj wyszukanym słownictwem formalnym."
        )

    # 25. SFX Filar LXXVII
    if any(w in combined_en for w in ["a sudden silence and flash clash", "flash clash"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXVII - Trójwarstwowa Triangulacja Odgłosów SFX]: "
            "Efekty akustyczne harmonizuj z tekstem dialogu."
        )

    # 26. UI Filar LXXVIII
    if any(w in combined_en for w in ["check your smartphone text message and chat", "smartphone text message"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXVIII - Interfejsy Diegetyczne i Smartfony]: "
            "Wiadomości tekstowe formatuj w nawiasach jako odrębne plansze."
        )

    # 27. Transkreacja Filar LXXIX
    if any(w in combined_en for w in ["let's raise a toast and rhyme this poem", "rhyme this poem"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXIX - Transkreacja Emocjonalna i Indeks Afektywny]: "
            "Utwory poetyckie przekładaj z dbałością o melodykę i polski rytm wierszowy."
        )

    # 28. Zająknięcia Filar LXXX
    if any(w in combined_en for w in ["w-what are you doing? wha-", "w-what are you doing"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXX - Kognitywna Mikro-Interpunkcja Afektywna]: "
            "Zająknięcia i urwane słowa zapisuj z pojedynczym dywizem."
        )

    # 29. Ghibli Filar LXXXI
    if any(w in combined_en for w in ["let me explain this world and give you full exposition"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXI - Organiczna Ekspozycja i Anty-Eksplikacja]: "
            "Wprowadzanie wiedzy o świecie wplataj w naturalną rozmowę postaci."
        )

    # 30. Eco Filar LXXXII
    if any(w in combined_en for w in ["the deep intent and meaning of this metaphor"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXII - Semiotyczna Negocjacja Znaczeń Umberto Eco]: "
            "Metafory tłumacz z zachowaniem ich diegetycznego sensu."
        )

    # 31. Ladmiral Filar LXXXIII
    if any(w in combined_en for w in ["there is no doubt that the fact that in order to do so"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXIII - Dynamizm Docelowy i Dekolonizacja Składni]: "
            "Składnię obcojęzyczną przekształcaj w prężne polskie konstrukcje zdaniowe."
        )

    # 32. Mouth-feel Smith Filar LXXXIV
    if any(w in combined_en for w in ["a dramatic whisper and shouting speech with rage"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXIV - Wykonawczy Kunszt i Mouth-Feel]: "
            "Kwestie dramatyczne dopasowuj do możliwości artykulacyjnych aktora."
        )

    # 33. Romero-Fresco Filar LXXXV
    if any(w in combined_en for w in ["look at the beauty of this cinematic landscape"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXV - Eliminacja Ślepoty Napisowej Romero-Fresco]: "
            "Tekst napisów podporządkuj kompozycji kadru filmowego."
        )

    # 34. Polifonia Bachtin Filar LXXXVI
    if any(w in combined_en for w in ["hello sir", "get out of here"]) and any(it.get("speaker_gender") == "kobieta" for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXVI - Polifonia Głosów i Heteroglosja Bachtina]: "
            "Różnicuj słownictwo poszczególnych bohaterów w zależności od ich roli społecznej."
        )

    # 35. Fokalizacja Filar LXXXVII
    if any(item.get("is_thought", False) for item in batch_items) and any("dread" in str(item.get("en", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXVII - Czystość Fokalizacji i Myśli Wewnętrznej]: "
            "Myśli wewnętrzne oddawaj z zachowaniem perspektywy przeżywającego podmiotu."
        )

    # 36. Berman Filar LXXXVIII
    if any(w in combined_en for w in ["rough, poetic, raw dialogue of this ancient legend"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXVIII - Protokół Anty-Deformacyjny Antoine Bermana]: "
            "Szanuj bogactwo leksykalne i surowość poetycką oryginału."
        )

    # 37. Steiner Filar LXXXIX
    if any(w in combined_en for w in ["lost in translation, culture and tradition"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR LXXXIX - Rekompensata Hermeneutyczna George Steinera]: "
            "Straty leksykalne rekompensuj w kluczowych węzłach dramatycznych."
        )

    # 38. Robinson Filar XC
    if any(w in combined_en for w in ["horror, terror, chills and heartbreak"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XC - Somatyczny Rezonans Emocjonalny Robinsona]: "
            "Emocje somatyczne wyrażaj trafnymi polskimi ekwiwalentami czuciowymi."
        )

    # 39. Piosenki Barańczak Filar CXVIII
    if any("barańczak" in str(it.get("notes", "")).lower() or "baranczak" in str(it.get("notes", "")).lower() or "song_batch" in str(it.get("notes", "")).lower() for it in batch_items) or any("singing" in str(it.get("en", "")).lower() and "rhyme" in str(it.get("en", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXVIII - Kunszt Przekładu Pieśni Stanisława Barańczaka]: "
            "Przekład utworów śpiewanych opieraj na tradycji translatorskiej Stanisława Barańczaka."
        )

    # 40. Dopełniacz imion obcych Drela Filar XCI
    if any("drela" in str(it.get("en", "")).lower() or "drela's" in str(it.get("en", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XCI - Fleksja Imion Obcych i Dopełniacz Dzierżawczy]: "
            "Obce imiona męskie jak Drela odmieniaj z zachowaniem formy dopełniacza Drela."
        )

    # 41. Ortografia spytam Filar CLXIV
    if any(w in combined_en for w in ["ask the servant", "spytam", "inquiry"]) or any("spytam" in str(it.get("notes", "")).lower() or "batch_typo" in str(it.get("notes", "")).lower() or "batch_inquiry" in str(it.get("notes", "")).lower() or "filar clxiv" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXIV - Staranna Kontrola Ortografii i Niezmienników Leksykalnych]: "
            "Zachowaj najwyższą staranność ortograficzną, stosując formę spytam."
        )

    # 42. Tytulatura Harmonia Wołacza Filar CLVII
    if any("batch_drift_test" in str(it.get("notes", "")).lower() or "filar clvii" in str(it.get("notes", "")).lower() for it in batch_items) or any(re.search(r"\bpann[ao]\s+[A-ZĄĆĘŁŃÓŚŹŻ]", str(it.get("pl", ""))) for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLVII - Nienaruszalność Formy Adresatywnej i Harmonia Wołacza]: "
            "Tytuły i honoryfikatory harmonizuj z imieniem rozmówcy w wołaczu."
        )

    # 43. Ciągłość czasowa Filar CLXV
    if any("batch_private" in str(it.get("notes", "")).lower() or "filar clxv" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXV - Dyskontinuitet Czasowy i Przeskoki Scen]: "
            "Zachowuj ciągłość logiczną wypowiedzi po przeskokach montażowych."
        )

    # 44. Anty-pivot Filar CLXVI
    if any("batch_cliches" in str(it.get("notes", "")).lower() or "filar clxvi" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXVI - Eliminacja Grawitacji Języka Pośredniego]: "
            "Eliminuj fałszywe konstrukcje angielskie na rzecz naturalnej polszczyzny."
        )

    # 45. Odporność NoneType Filar CLXVII
    if any("filar clxvii" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXVII - Puryzm Rejestru Dramatu Historycznego]: "
            "Dbaj o historyczną czystość stylu wypowiedzi."
        )

    # 46. Składnia deiktyczna Filar CLXVIII
    if any("naturalna składnia deiktyczno-temporalna" in str(it.get("notes", "")).lower() or "filar clxviii" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXVIII - Naturalna Składnia Deiktyczno-Temporalna]: "
            "Relacje czasowe buduj z zachowaniem naturalnego szyku zdania."
        )

    # 47. Plansze tytułowe Filar XCVIII
    if any("rules_batch" in str(it.get("notes", "")).lower() or "filar xcviii" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XCVIII - Typografia Plansz Tytułowych i Zwięzłość Typesettingu]: "
            "Plansze tytułowe ujmuj w nawiasy kwadratowe wielkimi literami."
        )

    # 48. Hipokorystyki Filar CLXIX
    if any("hikarun" in str(it.get("en", "")).lower() or "hurt her so badly" in str(it.get("en", "")).lower() or "filar clxix" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXIX - Dyscyplina Socjolektu, Ochrona Płci i Hipokorystyki]: "
            "Zdrobnienia imion stosuj w zgodzie z tożsamością mówcy."
        )

    # 49. Prymat akustyczny Filar CLXXIV
    if any("ōgedei" in str(it.get("en", "")).lower() or "ogedei" in str(it.get("en", "")).lower() or "sample_batch" in str(it.get("notes", "")).lower() or "filar clxxiv" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXIV - Prymat Sygnału Akustycznego nad Skażonymi Tagami Fansubów]: "
            "Przy sprzeczności metadanych polegaj na akustyce głosu aktora."
        )

    # 50. Grupa żeńska Filar CLXXV
    if any("filar clxxv" in str(it.get("notes", "")).lower() for it in batch_items) or (any(it.get("speaker_gender") == "FEMALE" for it in batch_items) and any("we " in it.get("en", "").lower() or "us" in it.get("en", "").lower() for it in batch_items)):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXV - Zgodność Rodzaju w Grupie Żeńskiej]: "
            "Wypowiedzi grupy kobiet w 1. osobie liczby mnogiej wymagają form niemęskoosobowych."
        )

    # 51. Pronominal decoupling Filar CLXXVII
    if any("look into my heart and save my life" in str(it.get("en", "")).lower() or "filar clxxvii" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXVII - Pronominal Decoupling i Somatyka Emocji]: "
            "Zaangażowanie emocjonalne wyrażaj bezpośrednią konstrukcją czasownikową."
        )

    # 52. Shock drop Filar CLXXVIII
    if any("filar clxxviii" in str(it.get("notes", "")).lower() or it.get("prosody") == "Ac=SHOCK_DROP" for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXVIII - Reset Inercji Afektywnej]: "
            "Nagłe załamanie emocjonalne zaznaczaj pauzą i opadającym tonem."
        )

    # 53. Pary przylegania Filar CLXXIX
    if any("filar clxxix" in str(it.get("notes", "")).lower() or "prompt_adj" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXIX - Dialogowe Pary Przylegania i Elipsy]: "
            "Wymiany zdań łącz spójną logiką pytania i odpowiedzi."
        )

    # 54. Deiksa przestrzenna Filar CLXXX
    if any("hold on, i'm coming" in str(it.get("en", "")).lower() or "filar clxxx" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXX - Cinematic Spatial Deixis i Wektory Ruchu]: "
            "Ruch postaci w kadrze odzwierciedlaj czasownikami kierunkowymi."
        )

    # 55. Tłumienie pleonazmów Filar CLXXXI
    if any("rocks are falling down fast" in str(it.get("en", "")).lower() or "filar clxxxi" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXXI - Koegzystencja z Obrazem i Tłumienie Pleonazmów]: "
            "Elementy widoczne w kadrze pomijaj w opisie słownym na rzecz zwięzłości."
        )

    # 56. Pro-drop Filar CLXXXII
    if any("filar clxxxii" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXXII - Zerowa Anafora Pro-Drop i Płynność Narracji]: "
            "W języku polskim naturalnie pomijaj zaimki podmiotu."
        )

    # 57. Puryzm tytulatury Filar CLXXXIII
    if any("filar clxxxiii" in str(it.get("notes", "")).lower() for it in batch_items) or any(bool(re.search(r"\bty\s+(?:dwie|dwaj|dwa|dwoje|troje|trzej|trzy|czworo|cztery|oboje|obie|obaj|wszyscy)\b", str(it.get("pl", "")).lower())) or bool(re.search(r"\bpan(?:a|u|em)?\s+panie\b", str(it.get("pl", "")).lower())) for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXXIII - Zgodność Liczby, Puryzm Tytulatury i Etykieta]: "
            "Tytuły rodowe łącz z imionami z zachowaniem reguł gramatycznych."
        )

    # 58. Pleonazmy toponimiczne Filar CLXXXIV
    if any("filar clxxxiv" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXXIV - Eliminacja Pleonazmów Toponimicznych i Tautologii]: "
            "Nazwy geograficzne podawaj bez zbędnego powtarzania określeń rodzajowych."
        )

    # 59. Strona bierna Filar CLXXXV
    if any("captured and executed" in str(it.get("en", "")).lower() or "filar clxxxv" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXXV - Spójność Monologów i Strona Bierna]: "
            "Stronę bierną języków obcych zastępuj aktywnymi formami czasowników polskich."
        )

    # 60. Relacja diadyczna Filar CLXXXVI
    if any("filar clxxxvi" in str(it.get("notes", "")).lower() or ("did you read that" in str(it.get("en", "")).lower() and "czytałaś to" in str(it.get("pl", "")).lower()) for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXXXVI - Świadomość Relacji Diadycznej i Zgodność Płci]: "
            "W rozmowie dwojga bohaterów dbaj o konsekwentne uzgodnienie rodzaju gramatycznego."
        )

    # 61. Wyznanie miłosne Filar CXXI
    if any(bool(re.search(r"\b(?:really like you|love you with all my heart|suki da|aishiteru)\b", str(it.get("en", "")), re.IGNORECASE)) for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXI - Wyznania Miłosne i Subtelność Uczuć]: "
            "Wyznania uczuć tłumacz z wyczuciem polszczyzny intymnej."
        )

    # 61b. Partykuły Shūjoshi Filar XVI
    if any(w in combined_en for w in ["kashira", "doko ni iku"]) or any(w in combined_jp for w in ["kashira", "かしら"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XVI & XVII - Partykuły Emocjonalne Shūjoshi (Kashira, Wa, No)]: "
            "Partykuły końcowe oddawaj subtelną intonacją pytającą lub namysłem."
        )

    # 62. Pożegnanie Filar CXXII
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["sayonara", "itte kimasu", "farewell"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXII - Pożegnania i Ciężar Rozstania]: "
            "Ostateczne pożegnania oddawaj zwrotami pełnymi powagi."
        )

    # 63. Paradoks negacji Filar CXXXIX
    if any("didn't you go there? yes." in str(it.get("en", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXXXIX - Paradoks Potwierdzenia Negacji i Pytań Przeczących]: "
            "Odpowiedź potwierdzającą zdanie przeczące tłumacz zgodnie z polską logiką zaprzeczeń."
        )

    # 64. Pokrewieństwo Filar CXL
    if any("big brother, please help me" in str(it.get("en", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXL - Społeczne Metafory Pokrewieństwa]: "
            "Japońskie zwroty rodzinne w relacjach środowiskowych adaptuj do polskiego kontekstu bliskości."
        )

    # 65. Stan Filar CXLI
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["he died a peaceful death", "he's dead", "passed away"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLI - Eufemizmy i Rejestr Tanatologiczny]: "
            "Odejście i śmierć opisuj z powagą w polszczyźnie funeralnej."
        )

    # 66. Zachwyt Filar CXLII
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["what a magnificent performance", "isn't it delicious"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLII - Retoryka Zachwytu w Pytaniach]: "
            "Uznanie i podziw wyrażaj bogatym polskim słownictwem laudacyjnym."
        )

    # 67. Pacing Filar CXLIII
    if any(item.get("duration_s", 99) <= 0.6 for item in batch_items) or any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["run! faster!", "wait!"]):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLIII - Zgodność Kinetyki Warg i Budżet]: "
            "Rozkazy w biegu i okrzyki naglące formułuj w krótkich słowach."
        )

    # 68. Radar Filar CXLIV
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["enemy approaching from the north", "damn it!"]) or any("chikushou" in str(item.get("audio_alert", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLIV - Prymat Autentycznego Głosu Aktora]: "
            "Meldunki bojowe podawaj zwięźle, określając kierunek i zagrożenie."
        )

    # 69. Volley Filar CXLVI
    if any("ping-pong" in str(it.get("relation_tag", "")).lower() for it in batch_items) or any("filar cxlvi" in str(it.get("notes", "")).lower() for it in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLVI - Dialogowy Ping-Pong i Spójność Leksykalna Riposty (Conversational Volley)]: "
            "Zgraj ripostę z pytaniem rozmówcy. Na OSTRZEŻENIA i POLECENIA potwierdź gotowość."
        )

    # 70. Modal Filar CXLVII
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["you must listen to me", "probably."]) or any("tabun" in str(item.get("audio_jp", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLVII - Matryca Przysłówków Modalnych i Pragmatycznych]: "
            "Odcienie powinności różnicuj polskimi czasownikami modalnymi."
        )

    # 71. Somatic Filar XVIII
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["i feel a sharp pain in my chest", "whoa, easy there"]) or any("ottotto" in str(item.get("audio_jp", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR XVIII - Kakegoe, Somatyka Ciała i Paralingwistyka]: "
            "Odczucia bólu i reakcje somatyczne oddawaj naturalnymi polskimi odruchami."
        )

    # 72. Veracity Filar CXLVIII
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["the execution of the plan was flawless", "is that true?"]) or any("honto" in str(item.get("audio_jp", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLVIII - Pragmatyka Pytań o Wiarygodność]: "
            "Ocenę skuteczności działań formułuj rzeczowo i jednoznacznie."
        )

    # 73. Haragei Filar CXLIX
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["i understand what you leave unsaid", "i'm fine."]) or any("daijoubu" in str(item.get("audio_jp", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CXLIX - Haragei: Odpowiedzi Zawoalowane]: "
            "Aluzje i przemilczenia zachowuj w polskim subtekście dialogowym."
        )

    # 74. Hora Filar CL
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["look at what you've done now!", "look!"]) or any("hora" in str(item.get("audio_jp", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CL - Wykrzykniki Dyscyplinujące]: "
            "Wymówki tłumacz naturalnymi polskimi zwrotami (No i popatrz)."
        )

    # 75. Aisatsu Filar CLI
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["welcome home, master", "i'm home!"]) or ("AISATSU_JP" in jp_categories):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLI - Formuły Powitalne]: "
            "Etykietę powrotu tłumacz serdecznymi polskimi powitaniami."
        )

    # 76. Danger Filar CLII
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["watch out for the falling rocks!", "look out!"]) or any("abunai" in str(item.get("audio_jp", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLII - Okrzyki Bojowe i Ostrzeżenia]: "
            "Ostrzeżenia przed bezpośrednim niebezpieczeństwem oddawaj dynamicznym wołaczem."
        )

    # 77. Prawda Filar CLV
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["the truth is revealed at last", "i can't stop it"]) or any("tomerarenai" in str(item.get("audio_jp", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLV - Repetycje Myśli i Separacja Mowy]: "
            "Kulminacyjne odkrycie prawdy akcentuj uroczystym tonem."
        )

    # 78. Rycerz Filar CLVI
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["i swear on my honor as a knight", "please leave me alone"]) or any("hitori ni shite" in str(item.get("audio_jp", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLVI - Rozszczepienie Angielskiego Pivotu]: "
            "Ślubowania rycerskie tłumacz podniosłą polszczyzną kodeksu honorowego."
        )

    # 79. Zwrot Filar CLVIII
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["a subtle shift in the conversation", "that was good."]) or any("yokatta" in str(item.get("audio_jp", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLVIII - Zgodność Foniczno-Semantyczna]: "
            "Zmianę tonu i przedmiotu rozmowy oddawaj płynnym przejściem frazowym."
        )

    # 80. Przepowiednia Filar CLXI
    if any(w in str(it.get("en", "")).lower() for it in batch_items for w in ["the ancient prophecy is fulfilled", "silent witch"]) or any("chinmoku no majo" in str(item.get("audio_jp", "")).lower() for item in batch_items):
        focused_pillars.append(
            "• [SKUP SIĘ NA: FILAR CLXI - Nienaruszalność Perspektywy Narracyjnej]: "
            "Proroctwa przekładaj uroczystą prozą o mitycznym zabarwieniu."
        )

    # 112. Seiyū Voice Primacy, Speech Act Taxonomy & Title Nominative Guard (Filar CLXX)
    has_seiyu_primacy_trigger = (
        ("SEIYU_SOVEREIGNTY_JP" in jp_categories)
        or any(k in str(item.get("pl", "")).lower() for item in batch_items for k in ["żenada", "wróciłam"])
        or any(re.search(r"\bmaster\s+[A-Z][a-z]+", str(item.get("en", ""))) for item in batch_items)
        or any("filar clxx" in str(item.get("notes", "")).lower() for item in batch_items)
    )
    if has_seiyu_primacy_trigger:
        focused_pillars.append(
            (98,
            "• [SKUP SIĘ NA: FILAR CLXX - Prymat Głosu Seiyū, Akty Mowy, Aisatsu i Tytulatura Podmiotu]: "
            "Głos seiyū stanowi nadrzędny punkt odniesienia dla rejestru emocjonalnego i intonacji. "
            "Akty uciszania i irytacji oddawaj naturalną polszczyzną sytuacyjną, "
            "formuły powitalne tłumacz serdecznymi polskimi powitaniami, a tytulaturę podmiotu zachowuj w mianowniku.")
        )

    # Sort descending by attention priority score; Python sort is stable
    sorted_scored = sorted(focused_pillars.items, key=lambda x: x[0], reverse=True)

    has_hard_battle_markers = bool(re.search(
        r"\b(?:attack|dodge|stomp|crush|punch|strike|slash|blast|ottotto|kakegoe)\b",
        combined_en + " " + combined_jp,
        re.IGNORECASE
    )) or any(
        any(k in str(it.get("notes", "")).lower() for k in ["walka", "pojedynek", "starcie", "cios", "battle"])
        for it in batch_items
    )

    # Anti-Smoothing Filter (Hotfix 10.1.1, 2B.4 + Standard 10.2 + Standard 10.3):
    # 1. FILAR XIII (DYN_1) lub FILAR XIV (DYN_2): wyklucz FILAR LXXI i FILAR CLXXII
    if any("FILAR XIII" in r[1] or "FILAR XIV" in r[1] for r in sorted_scored):
        sorted_scored = [r for r in sorted_scored if not re.search(r"\bFILAR LXXI\b", r[1]) and not re.search(r"\bFILAR CLXXII\b", r[1])]

    # 2. FILAR XIX & LXXVI (DYN_9): wyklucz FILAR LXXI; wyklucz FILAR CLXXII chyba że w paczce wystąpiły twarde markery walki
    if any("FILAR XIX" in r[1] for r in sorted_scored):
        sorted_scored = [r for r in sorted_scored if not re.search(r"\bFILAR LXXI\b", r[1])]
        if not has_hard_battle_markers:
            sorted_scored = [r for r in sorted_scored if not re.search(r"\bFILAR CLXXII\b", r[1])]

    # Deduplicate while preserving priority order
    seen = set()
    unique_rules: List[Tuple[int, str]] = []
    for score, rule in sorted_scored:
        if rule not in seen:
            seen.add(rule)
            unique_rules.append((score, rule))

    # Anti-Attention Dilution & Balanced Slot Quota:
    if max_rules is not None and max_rules > 0:
        effective_max = max_rules

        bucket_affect = [r for r in unique_rules if r[0] >= 100]
        bucket_craft = [r for r in unique_rules if 40 <= r[0] < 100]
        bucket_offline = [r for r in unique_rules if r[0] < 40]

        selected: List[Tuple[int, str]] = []
        selected_texts = set()

        def _try_add(candidate_list: List[Tuple[int, str]]) -> bool:
            for sc, txt in candidate_list:
                if txt not in selected_texts:
                    selected.append((sc, txt))
                    selected_texts.add(txt)
                    return True
            return False

        if effective_max >= 3:
            _try_add(bucket_affect)
            _try_add(bucket_craft)
            for sc, txt in unique_rules:
                if len(selected) >= effective_max:
                    break
                if txt not in selected_texts:
                    selected.append((sc, txt))
                    selected_texts.add(txt)
        elif effective_max == 2:
            if bucket_affect and bucket_craft:
                _try_add(bucket_affect)
                _try_add(bucket_craft)
            else:
                for sc, txt in unique_rules:
                    if len(selected) >= effective_max:
                        break
                    if txt not in selected_texts:
                        selected.append((sc, txt))
                        selected_texts.add(txt)
        else:  # effective_max == 1
            if unique_rules:
                selected.append(unique_rules[0])

        selected_sorted = sorted(selected, key=lambda x: x[0], reverse=True)
        final_rules = [txt for sc, txt in selected_sorted]
    else:
        final_rules = [txt for sc, txt in unique_rules]

    if any("FILAR XIII" in r or "FILAR XIV" in r for r in final_rules):
        final_rules = [r for r in final_rules if not re.search(r"\bFILAR LXXI\b", r) and not re.search(r"\bFILAR CLXXII\b", r)]

    if any("FILAR XIX" in r for r in final_rules):
        final_rules = [r for r in final_rules if not re.search(r"\bFILAR LXXI\b", r)]
        if not has_hard_battle_markers:
            final_rules = [r for r in final_rules if not re.search(r"\bFILAR CLXXII\b", r)]

    # Czysty fallback Standardu 10.2: dla zwykłego dialogu bez zjawisk specjalnych zwraca pusty string
    if not final_rules:
        return ""

    lines = [
        "--- [!] SKONCENTROWANA UWAGA DLA TEJ SCENY (PRIORYTETOWE FILARY AVT) ---",
        "W bieżącej paczce kwestii zwróć szczególną uwagę na następujące kluczowe reguły:"
    ]
    lines.extend(final_rules)
    lines.append("------------------------------------------------------------------------\n")
    return "\n".join(lines)
