# -*- coding: utf-8 -*-
"""
Series Bible & Cross-Episode Continuity Module.
Automatically accumulates knowledge, character profiles, honorific forms, and terminology
across consecutive episodes of the same anime, ensuring 100% consistency across the entire season.
"""

import os
import re
import json
import threading
import copy
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Union

import unicodedata

SERIES_MEMORY_DIR = Path(__file__).parent / "series_memory"

def clean_anime_slug(title: str) -> str:
    """Creates a filesystem-safe identifier slug from anime title, normalizing diacritics."""
    if not title:
        return "default_series"
    # Normalize unicode diacritics (e.g. Caraméliser -> Carameliser)
    nfkd = unicodedata.normalize('NFKD', title)
    title_ascii = "".join([c for c in nfkd if not unicodedata.combining(c)])
    slug = re.sub(r"[^\w\s-]", "", title_ascii, flags=re.UNICODE).strip()
    slug = re.sub(r"[-\s]+", "_", slug)
    return slug[:50] or "default_series"


INHERENT_FEMALE_NOUNS = {
    # Basic / Family / Age
    "girl", "woman", "female", "lady", "miss", "mrs", "ms", "heroine", "witch",
    "dziewczyna", "dziewczynka", "kobieta", "matka", "mama", "mamusia", "mateczka", "mamunia", "macocha",
    "córka", "córeczka", "córunia", "siostra", "siostrzyczka", "siostrunia",
    "babcia", "babunia", "babka", "prababka", "staruszka", "starowinka", "starowina", "starucha", "seniorka", "matrona",
    "wnuczka", "prawnuczka", "ciotka", "ciocia", "ciotunia", "stryjenka", "wujenka", "wujna",
    "siostrzenica", "bratanica", "teściowa", "świekra", "synowa", "szwagierka", "bratowa", "jątrew",
    "kuzynka", "krewna", "pociotka", "sierota", "wdowa", "panna", "panienka", "panna młoda", "młodka", "niewiasta", "białogłowa",
    "pani", "pani domu", "oblubienica", "narzeczona", "wybranka", "ukochana", "małżonka", "żona", "żonka", "żonusia",
    # Nobility / Administration / Royalty
    "królowa", "królewna", "królowa-matka", "księżniczka", "księżna", "caryca", "cesarzowa", "cesarzówna", "carówna",
    "władczyni", "monarchini", "kniagini", "arcyksiężna", "arystokratka", "szlachcianka", "magnatka",
    "hrabina", "hrabianka", "margrabina", "baronowa", "baronówna", "wicehrabina", "markiza", "wielmożna", "suwerenka",
    "kasztelanka", "kasztelanowa", "wojewodzina", "wojewodzianka", "starościna", "starościanka", "podkomorzyna",
    "stolnikowa", "cześnikowa", "miecznikowa", "dziedziczka", "posesorka", "feudałka", "seniorka", "suzerenka",
    "protektorka", "patronka", "kuratorka", "sędzina", "sędzia", "jurorka", "notariuszka", "mecenaska", "rejentowa",
    "adwokatka", "prokuratorka", "trybunka", "prefektka", "rajczyni", "burmistrzyni", "prezydentka", "sołtyska", "wójtowa",
    "kanclerzowa", "kanclerka", "namiestniczka", "urzędniczka", "zarządczyni", "konsulka", "senatorka", "posłanka",
    "deputowana", "ambasadorka", "dyplomatka", "heroldzica",
    # Military / Guard / Combat
    "strażniczka", "wojowniczka", "żołnierka", "rycerka", "komendantka", "kapitanka", "generałowa",
    "łuczniczka", "szermierka", "zwiadowczyni", "najemniczka", "bohaterka", "oficerka", "rekrutka", "gladiatorka",
    "kuszniczka", "kanonierka", "partyzantka", "majorka", "pułkownikowa", "admirałowa", "hetmanka", "hetmanowa",
    "berserkerka", "amazonka", "tarczowniczka", "włóczniczka", "grenadierka", "sapera", "weteranka", "dezerterka", "cichociemna",
    # Religion / Magic / Science
    "czarownica", "czarodziejka", "kapłanka", "arcykapłanka", "miko", "westalka", "mniszka", "zakonnica", "opatka", "ksieni",
    "przeorysza", "siostrzyczka", "nowicjuszka", "postulantka", "misjonarka", "katechetka", "teolożka", "kaznodziejka",
    "prorokini", "wieszczka", "jasnowidzka", "wyrocznia", "wróżka", "wróżbiarka", "chiromantka", "zielarka", "guślarka",
    "szamanka", "druidka", "maga", "magini", "arcymaga", "czarnoksiężnica", "zaklinaczka", "nekromantka", "iluzjonistka",
    "alchemiczka", "astrologini", "mędrczyni", "uczona", "badaczka", "profesorka", "doktorka", "filozofka", "myślicielka",
    "astronomka", "matematyczka", "algebrzystka", "archeolożka", "historyczka", "kronikarka", "skrybka", "bibliotekarka", "archiwistka", "wiedźma", "wiedunka", "wiedunki",
    "demonica", "bogini", "wampirzyca", "wilkołaczka", "nimfa", "rusałka", "driada", "syrena", "harpia", "banshee", "sukuba", "sukub",
    "elfka", "krasnoludka", "orkini", "trollka", "diablica", "szatanka", "aniołica", "aniolica", "widmo", "zjawa",
    # Domestic / Service
    "służąca", "pokojówka", "gosposia", "kucharka", "kuchareczka", "szefowa kuchni", "ochmistrzyni", "panna służąca",
    "pomocnica", "posługaczka", "pomywaczka", "praczka", "garderobiana", "czesaczka", "fryzjerka", "kosmetyczka",
    "niańka", "piastunka", "mamka", "guwernantka", "bona", "opiekunka", "pensjonarka", "rezydentka", "odźwierna", "klucznica",
    "szafarka", "sprzątaczka", "dziewka",
    # Commoners / Trades / Crafts
    "wieśniaczka", "chłopka", "rolniczka", "kmiotka", "osadniczka", "kmieciowa", "zagrodniczka", "chałupniczka", "komornica",
    "pasterka", "owczarka", "dojarza", "gospodyni", "młynarka", "piekarzowa", "piekarka", "cukierniczka", "rzeźniczka", "masarka",
    "krawcowa", "szwaczka", "hafciarka", "prządka", "tkaczka", "bieliźniarka", "modystka", "kuśnierka", "garbarniczka",
    "szewcowa", "szewczyni", "kowalka", "kowalowa", "ślusarka", "stolarka", "garncarka", "bednarka", "cieślina", "murarka",
    "dekarzowa", "szklarzowa", "drukara", "zecerka", "introligatorka", "mydlarka", "świecarka", "bartniczka", "pszczelarka",
    "rybaczka", "marynarka", "flisaczka", "przewoźniczka", "woźniczka", "kupcowa", "handlarka", "kramarka", "straganiarka",
    "przekupka", "karczmarka", "szynkarka", "oberżystka", "szynkareczka", "barmanka", "kelnerka", "garkuchnica", "górniczka",
    # Underworld / Outsiders
    "bandytka", "rozbójniczka", "zbójniczka", "łotrzyca", "złodziejka", "złodziejaszka", "kasiarka", "kieszonkowniczka",
    "włamywaczka", "paserka", "szpieżka", "agentka", "wywiadowczyni", "skrytobójczyni", "zabójczyni", "morderczyni", "trucicielka",
    "piratka", "korsarka", "przemytniczka", "szmuglerka", "oszustka", "szulerka", "szantażystka", "kłusowniczka", "żebraczka",
    "nędzarka", "banitka", "wygnanka", "uchodźczyni", "tułaczka", "wędrowniczka", "uciekinierka", "zbieg", "renegatka",
    "apostatka", "heretyczka", "buntowniczka", "powstańczyni", "dywersantka", "partyzantka", "niewolnica", "branka",
    "więźniarka", "skazana", "potępiona",
    # School / Youth / Medicine
    "uczennica", "studentka", "słuchaczka", "wychowanka", "pensjonarka", "abiturientka", "absolwentka", "stażystka",
    "praktykantka", "asystentka", "nauczycielka", "bakałarzowa", "pedagożka", "lektorka", "korepetytorka", "instruktorka",
    "mentorka", "mistrzyni", "przewodniczka", "lekarka", "medyczka", "felczerka", "chirurżka", "internistka", "okulistka",
    "pediatrka", "psychiatra", "psycholożka", "terapeutka", "aptekarka", "farmaceutka", "uzdrowicielka", "znachorka",
    "sanitariuszka", "pielęgniarka", "siostra miłosierdzia", "salowa", "ratowniczka", "pacjentka", "chora", "ranna", "ozdrowieńcza"
}

INHERENT_MALE_NOUNS = {
    # Basic / Family / Age
    "boy", "man", "male", "lord", "mr", "hero", "wizard",
    "chłopak", "chłopiec", "mężczyzna", "ojciec", "tata", "tatuś", "ojczym", "syn", "synek", "synuś", "pasierb",
    "brat", "braciszek", "dziadek", "dziadziuś", "starzec", "staruszek", "senior", "nestor", "starowina",
    "pradziadek", "wnuk", "wnuczek", "prawnuk", "wuj", "wujek", "stryj", "stryjek", "siostrzeniec", "bratanek",
    "teść", "świekier", "zięć", "szwagier", "bratankowy", "kuzyn", "krewny", "pociotek", "sierota", "wdowiec",
    "kawaler", "młodzieniec", "młodzik", "podrostek", "gołowąs", "młodzian", "pan", "panicz", "bocchan",
    "oblubieniec", "pan młody", "mąż", "małżonek",
    # Nobility / Administration / Royalty
    "król", "królewicz", "król-ojciec", "książę", "książątko", "car", "carewicz", "cesarz", "cesarzewicz", "władca",
    "monarcha", "kniź", "diuk", "arcyksiążę", "arystokrata", "szlachcic", "magnat", "hrabia", "hrabicz", "margrabia",
    "markiz", "baron", "baronet", "wicehrabia", "wielmoża", "suweren", "kasztelan", "wojewoda", "starosta",
    "podkomorzy", "stolnik", "cześnik", "miecznik", "dziedzic", "posesor", "feudał", "senior", "suzeren", "wasal",
    "protektor", "patron", "kurator", "sędzia", "ławnik", "juror", "notariusz", "mecenas", "rejent", "adwokat",
    "prokurator", "trybun", "konsul", "senator", "poseł", "deputowany", "ambasador", "dyplomata", "legat", "herold",
    "woźny", "burmistrz", "prezydent", "rajca", "wójt", "sołtys", "kanclerz", "wicekanclerz", "namiestnik", "urzędnik",
    "poborca", "zarządca", "intendent", "dostojnik", "kuge", "buke",
    # Military / Guard / Combat
    "strażnik", "wartownik", "obrońca", "żołnierz", "rycerz", "generał", "dowódca", "kapitan", "komendant",
    "sierżant", "porucznik", "podporucznik", "pułkownik", "podpułkownik", "major", "rotmistrz", "kapral", "szeregowiec",
    "kadet", "rekrut", "brygadier", "feldmarszałek", "marszałek", "admirał", "komandor", "sternik", "nawigator",
    "marynarz", "majtek", "bosman", "fechmistrz", "giermek", "łucznik", "kusznik", "szermierz", "piechur",
    "zwiadowca", "kanonier", "artylerzysta", "saper", "szpica", "forpoczta", "wojownik", "najemnik", "kondotier",
    "hetman", "oficer", "samuraj", "bohater", "czempion", "berserker", "gladiator", "tarczownik", "włócznik",
    "halabardnik", "pikinier", "muszkieter", "dragon", "ułan", "husarz", "kirasjer", "lansjer", "kawalerzysta",
    "grenadier", "weteran", "inwalida", "dezerter", "partyzant", "powstaniec", "dywersant", "komandos", "snajper",
    # Religion / Magic / Science
    "czarodziej", "czarnoksiężnik", "mag", "arcymag", "wiedun", "wieduni", "wiedunowie", "kapłan", "arcykapłan", "mnich", "zakonnik", "brat zakonny",
    "nowicjusz", "kleryk", "seminarzysta", "opat", "przeor", "biskup", "arcybiskup", "patriarcha", "kardynał", "papież",
    "prałat", "kanonik", "proboszcz", "wikary", "wikariusz", "misjonarz", "kaznodzieja", "teolog", "katecheta",
    "prorok", "wieszcz", "jasnowidz", "wyrocznia", "wróżbita", "astrolog", "chiromanta", "guślarz", "szaman", "druid",
    "zielarz", "znachor", "czarownik", "zaklinacz", "nekromanta", "iluzjonista", "alchemik", "mędrzec", "uczony",
    "filozof", "myśliciel", "badacz", "profesor", "doktor", "astronom", "matematyk", "archeolog", "historyk",
    "kronikarz", "skryba", "kopista", "bibliotekarz", "archiwista",
    "demon", "bóg", "wampir", "wilkołak", "tryton", "centaur", "satyr", "inkub",
    "elf", "krasnolud", "ork", "troll", "anioł", "archanioł", "diabeł", "szatan", "czort",
    # Domestic / Service
    "służący", "lokaj", "kamerdyner", "majordomus", "ochmistrz", "stangret", "woźnica", "parobek", "parobczak",
    "pachołek", "stajenny", "masztalerz", "fornal", "ogrodnik", "stróż", "odźwierny", "cerber", "klucznik",
    "szafarz", "kucharz", "kuchcik", "szef kuchni", "piwniczny", "podczaszy", "kredencerz", "guwerner", "pedagog",
    "opiekun", "rezydent", "posłaniec", "goniec",
    # Commoners / Trades / Crafts
    "wieśniak", "chłop", "kmiotek", "rolnik", "oracz", "siewca", "żniwiarz", "kosiarz", "rataj", "włościanin", "osadnik",
    "kmieć", "zagrodnik", "chałupnik", "komornik", "pasterz", "owczarz", "pastuszek", "juhas", "gospodarz", "młynarz",
    "piekarz", "cukiernik", "masarz", "rzeźnik", "krawiec", "szewc", "garbarz", "kuśnierz", "kowal", "ślusarz",
    "stolarz", "cieśla", "bednarz", "kołodziej", "rymarz", "siodlarz", "garncarz", "zdun", "murarz", "dekarz",
    "szklarz", "malarz", "kamieniarz", "rzeźbiarz", "drukarz", "zecer", "introligator", "tkacz", "powroźnik",
    "mydlarz", "świecarz", "zielarz", "bartnik", "pszczelarz", "leśnik", "gajowy", "drwal", "smolarz", "węglarz",
    "rybak", "flisak", "marynarz", "żeglarz", "przewoźnik", "dorożkarz", "furman", "tragarz", "kurier", "listonosz",
    "kupiec", "handlarz", "kramarz", "straganiarz", "przekupień", "faktor", "lichwiarz", "bankier", "wekslarz",
    "karczmarz", "szynkarz", "oberżysta", "barman", "kelner", "garkuchnik", "górnik",
    # Underworld / Outsiders
    "bandyta", "zbój", "zbójnik", "rozbójnik", "łotr", "łotrzyk", "rzezimieszek", "złodziej", "złodziejaszek",
    "kasiarz", "doliniarz", "kieszonkowiec", "włamywacz", "paser", "szpieg", "agent", "wywiadowca", "donosiciel",
    "kapuś", "skrytobójca", "zabójca", "morderca", "truciciel", "pirat", "korsarz", "kaper", "przemytnik",
    "szmugler", "oszust", "szuler", "szantażysta", "kłusownik", "żebrak", "nędzarz", "dziad", "łachmaniarz",
    "banita", "wygnaniec", "uchodźca", "tułacz", "wędrowiec", "pielgrzym", "uciekinier", "zbieg", "renegat",
    "apostata", "heretyk", "buntownik", "powstaniec", "dywersant", "niewolnik", "jeniec", "więzień", "skazaniec", "potępieniec",
    # School / Youth / Medicine
    "uczeń", "student", "żak", "słuchacz", "wychowanek", "pensjonarz", "abiturient", "absolwent", "stażysta",
    "praktykant", "asystent", "nauczyciel", "profesor", "bakałarz", "pedagog", "lektor", "wychowawca", "korepetytor",
    "instruktor", "mentor", "mistrz", "przewodnik", "doktor", "lekarz", "medyk", "felczer", "chirurg", "internista",
    "okulista", "pediatra", "psychiatra", "psycholog", "terapeuta", "aptekarz", "farmaceuta", "uzdrowiciel", "znachor",
    "sanitariusz", "pielęgniarz", "ratownik", "pacjent", "chory", "ranny", "ozdrowieniec"
}

INHERENT_PLURAL_NOUNS = {
    # Polish
    "strażnicy", "wartownicy", "obrońcy", "żołnierze", "wojownicy", "rycerze", "szermierze", "łucznicy", "kusznicy",
    "kanonierzy", "saperzy", "zwiadowcy", "piechurzy", "gladiatorzy", "grenadierzy", "kadeci", "rekruci", "kaprale",
    "sierżanci", "oficerowie", "kapitanowie", "majorowie", "pułkownicy", "generałowie", "marszałkowie", "admirałowie",
    "marynarze", "weterani", "dezerterzy", "partyzanci", "powstańcy", "komandosi", "snajperzy", "najemnicy", "dowódcy",
    "berserkerzy", "amazonki", "wojowniczki", "strażniczki", "łuczniczki", "zwiadowczynie",
    "wieśniacy", "chłopi", "rolnicy", "osadnicy", "pasterze", "młynarze", "piekarze", "rzeźnicy", "krawcy", "szewcy",
    "kowale", "ślusarze", "stolarze", "cieśle", "murarze", "drukarze", "tkacze", "drwale", "rybacy", "flisacy",
    "marynarze", "żeglarze", "przewoźnicy", "woźnice", "tragarze", "kurierzy", "gońcy", "posłańcy", "handlarze",
    "kupcy", "kramarze", "szynkarze", "karczmarze", "barmanki", "kelnerzy", "kelnerki", "wieśniaczki", "chłopki",
    "krawcowe", "szwaczki", "mieszkańcy", "mieszczanie", "obywatele", "tubylcy", "tutejsi",
    "arystokraci", "szlachcice", "szlachta", "magnaci", "lordowie", "baronowie", "hrabiowie", "suwereni", "władcy",
    "władczynie", "królowie", "królowe", "cesarze", "cesarzowe", "książęta", "księżniczki", "sędziowie", "notariusze",
    "adwokaci", "senatorowie", "posłowie", "dyplomaci", "ambasadorzy",
    "kapłani", "kapłanki", "mnisi", "zakonnicy", "zakonnice", "mniszki", "biskupi", "druidzi", "szamani", "prorocy",
    "wieszcze", "czarodzieje", "magowie", "czarnoksiężnicy", "nekromanci", "alchemicy", "mędrcy", "uczeni",
    "profesorowie", "skrybowie",
    "słudzy", "służący", "służące", "lokaje", "kamerdynerzy", "pachołkowie", "parobkowie", "stajenni", "ogrodnicy",
    "stróże", "kucharze", "kucharki", "pokojówki", "niańki", "piastunki", "mamki", "opiekunki",
    "ludzie", "mężczyźni", "kobiety", "panowie", "panie", "młodzieńcy", "panny", "panny młode", "chłopcy",
    "dziewczęta", "dziewczyny", "dziewczynki", "dzieci", "maluchy", "berbecie", "dzieciaki", "rodzice", "ojcowie",
    "matki", "synowie", "córki", "bracia", "siostry", "dziadkowie", "babcie", "wnuki", "wujowie", "stryjowie", "ciotki",
    "krewni", "pociotkowie", "małżonkowie", "pary", "narzeczeni", "wdowy", "wdowcy", "starcy", "staruszkowie",
    "staruszki", "seniorzy", "przodkowie",
    "bandyci", "rozbójnicy", "zbóje", "zbójnicy", "rozbójnicy", "łotry", "rzezimieszki", "złodzieje", "włamywacze",
    "szpiedzy", "agenci", "skrytobójcy", "zabójcy", "mordercy", "piraci", "korsarze", "przemytnicy", "szulerzy",
    "żebracy", "nędzarze", "banici", "wygnańcy", "uchodźcy", "uchodźczynie", "tułacze", "uciekinierzy", "renegaci",
    "buntownicy", "powstańcy", "niewolnicy", "niewolnice", "jeńcy", "więźniowie", "skazańcy",
    "uczniowie", "uczennice", "studentki", "studenci", "słuchacze", "wychowankowie", "absolwenci", "nauczyciele",
    "nauczycielki", "lektorzy", "mentorzy", "lekarze", "lekarki", "medycy", "chirurdzy", "aptekarze", "uzdrowiciele",
    "pielęgniarki", "pielęgniarze", "sanitariusze", "ratownicy", "pacjenci", "pacjentki", "ranni", "chorzy",
    "tłum", "tłumy", "pospólstwo", "gawiedź", "czeladź", "rzesza", "rzesze", "starszyzna", "plemię", "klan", "ród",
    "załoga", "armia", "wojsko", "wojska", "oddział", "oddziały", "kompania", "kompanie", "warta", "straż", "patrol",
    "patrole", "pułk", "pułki", "batalion", "bataliony", "dywizja", "dywizje", "legia", "legie", "horda", "hordy",
    "wataha", "watahy", "zgraja", "banda", "bandy", "świta", "orszak", "zgromadzenie", "zebrani", "zebranie",
    "goście", "widzowie", "publiczność", "widownia", "obecni", "uczestnicy", "pasażerowie", "przechodnie", "gapie",
    "posłańcy", "gońcy",
    # English
    "guards", "soldiers", "warriors", "knights", "generals", "commanders", "officers", "mercenaries", "archers",
    "swordsmen", "spearmen", "scouts", "snipers", "captains", "marshals", "admirals", "sailors", "veterans", "rebels",
    "partisans", "commandos",
    "villagers", "peasants", "farmers", "citizens", "townspeople", "merchants", "traders", "people", "settlers",
    "shepherds", "bakers", "butchers", "smiths", "blacksmiths", "carpenters", "fishermen", "drivers", "couriers",
    "innkeepers", "bartenders", "waiters", "waitresses",
    "nobles", "aristocrats", "lords", "ladies", "barons", "dukes", "princes", "princesses", "kings", "queens",
    "judges", "senators", "diplomats",
    "priests", "priestesses", "monks", "nuns", "bishops", "shamans", "druids", "wizards", "mages", "sorcerers",
    "necromancers", "alchemists", "scholars", "scribes",
    "servants", "maids", "butlers",
    "men", "women", "boys", "girls", "children", "kids", "toddlers", "parents", "fathers", "mothers", "sons", "daughters",
    "brothers", "sisters", "grandparents", "ancestors",
    "bandits", "robbers", "thieves", "burglars", "rogues", "outlaws", "spies", "assassins", "killers", "murderers",
    "pirates", "smugglers", "beggars", "slaves", "captives", "prisoners", "convicts", "refugees", "exiles", "runaways",
    "students", "pupils", "teachers", "professors", "mentors", "doctors", "medics", "surgeons", "nurses", "patients",
    "crowd", "crowds", "mob", "mobs", "crew", "crews", "army", "armies", "patrol", "patrols", "squad", "squads",
    "company", "unit", "units", "troop", "troops", "bystanders", "guests", "spectators", "audience", "passengers"
}

CANONICAL_MALE_NAMES = {
    "shira", "akira", "gaara", "ashitaka", "kiba", "soma", "kenta",
    "ryoma", "hanza", "koba", "soya", "toma", "genga", "sinbad", "judar", "alibaba",
    "masashige", "kusunoki", "saionji", "kinmune", "ashikaga", "takauji", "mochizuki",
    "ou hon", "ouhon", "robert", "tokiyuki", "genba", "kazama genba", "genba kazama"
}


FEMALE_ROLE_KEYWORDS = [
    # General / Base
    "female", "kobieta", "dziewczyn", "żeńsk", "pani ", "panią", "paniom", "panieńskie",
    # Rodzina (18)
    "matk", "mamk", "córk", "siostr", "babk", "babci", "prababk", "prababci",
    "wnuczk", "prawnuczk", "ciotk", "wujenk", "stryjenk", "bratanic", "siostrzenic",
    "teściowa", "teściowej", "teściową", "świekr", "synowa", "synowej", "synową", "szwagierk", "kuzynk", "pasierbic", "macoch",
    # Monarchia & Władza (22)
    "królowa", "królowej", "królową", "królowo", "królewn", "księżniczk", "księżn", "cesarzowa", "cesarzowej", "cesarzową", "cesarzewn", "caryc", "carewn",
    "władczyn", "suwerenk", "monarchin", "arcyksiężn", "wielmożna", "wielmożnej", "wielmożną", "diuszes", "markiz", "margrabin",
    "hrabin", "hrabiank", "wicehrabin", "baronowa", "baronowej", "baronową", "baronówn", "szlachciank", "magnatk", "arystokratk",
    # Dwór & Służba (20)
    "panienk", "pann[ayęe]", "służąca", "służącej", "służącą", "pokojówk", "garderobiana", "garderobianej", "garderobianą", "ochmistrzyn", "woźniczk",
    "fornaliczk", "stajenna", "stajennej", "stajenną", "posługaczk", "ogrodniczk", "kuchark", "pomywaczk", "szafark",
    "klucznic", "zarządczyn", "dama dworu", "dwórk", "niańk",
    # Wojsko & Straż (35)
    "żołnierk", "wojowniczk", "rycerk", "strażniczk", "wartowniczk", "dowódczyn", "generałowa", "generałowej", "generałową", "generałk",
    "komendantk", "kapitank", "oficerk", "poruczniczk", "podporuczniczk", "pułkowniczk", "podpułkowniczk",
    "majork", "sierżantk", "kapralk", "szeregowa", "szeregowej", "szeregową", "kadetk", "rekrutk", "hetmanowa", "hetmanowej", "hetmanową",
    "fechmistrzyn", "szermierk", "łuczniczk", "kuszniczk", "włóczniczk", "tarczowniczk", "pikinierk",
    "zwiadowczyn", "kanonierk", "saperk", "piechurk", "najemniczk", "obrończyn", "przywódczyn",
    # Religia & Magia (25)
    "kapłank", "arcykapłank", "mniszk", "zakonnic", "opatk", "przeorysz", "biskupk", "czarodziejk",
    "czarownic", "magini", "arcymagini", "czarnoksiężnic", "nekromantk", "alchemiczk", "szamank",
    "druidk", "guślark", "wiedźm", "wróżk", "wieszczk", "prorokin", "zielark", "znachork",
    "zaklinaczk", "iluzjonistk", "egzorcystk",
    # Rzemiosło & Handel (30)
    "kowalk", "karczmark", "szynkark", "oberżystk", "kupcowa", "kupcowej", "kupcową", "kupczyn", "handlark", "kramark",
    "piekark", "cukierniczk", "rzeźniczk", "krawcowa", "krawcowej", "krawcową", "szewcowa", "szewcowej", "szewcową", "stolark", "cieślin", "garncark",
    "tkaczk", "garbark", "kuśnierk", "młynark", "rolniczk", "wieśniaczk", "chłopk", "pasterk",
    "drwalk", "leśniczk", "gajowa", "gajowej", "gajową", "rybaczk", "żeglark", "sterniczk",
    # Edukacja & Medycyna (15)
    "nauczycielk", "profesork", "uczennic", "studentk", "wychowawczyn", "lekark", "medyczk",
    "pielęgniark", "uzdrowicielk", "aptekark", "sędzin", "urzędniczk", "namiestniczk", "kanclerzowa", "kanclerzowej", "kanclerzową", "skrybk",
    # Dodatkowe
    "bohaterk", "chatun", "szpieżk", "girl", "woman", "lady"
]

MALE_ROLE_KEYWORDS = [
    # General / Base
    "male", "mężczyzna", "chłopak", "chłopiec", "boy", "młodzieniec", "męsk", "bocchan", "panie", "pan ", "man",
    # Rodzina (18)
    "ojciec", "syn", "brat", "dziadek", "pradziadek", "wnuk", "prawnuk", "wuj", "stryj",
    "bratanek", "siostrzeniec", "teść", "świekier", "zięć", "szwagier", "kuzyn", "pasierb", "ojczym",
    # Monarchia & Władza (22)
    "król", "królewicz", "książę", "cesarz", "cesarzewicz", "car ", "carewicz", "władca", "suweren",
    "monarcha", "arcyksiążę", "wielmoża", "wielmożny", "diuk", "markiz", "margrabia", "hrabi", "hrabicz",
    "wicehrabia", "baron", "szlachcic", "magnat", "arystokrata",
    # Dwór & Służba (20)
    "panicz", "służący", "lokaj", "kamerdyner", "majordomus", "ochmistrz", "stangret", "fornal",
    "stajenny", "pachołek", "parobek", "ogrodnik", "kucharz", "kuchcik", "szafarz", "klucznik",
    "zarządca", "giermek", "paź ", "samuraj",
    # Wojsko & Straż (35)
    "żołnierz", "wojownik", "rycerz", "strażnik", "wartownik", "dowódc", "generał", "komendant",
    "kapitan", "oficer", "porucznik", "podporucznik", "pułkownik", "podpułkownik", "major", "sierżant",
    "kapral", "szeregowiec", "szeregowy", "kadet", "rekrut", "hetman", "fechmistrz", "szermierz", "łucznik",
    "kusznik", "włócznik", "tarczownik", "pikinier", "zwiadowca", "kanonier", "saper", "piechur",
    "najemnik", "obrońca", "wódz ", "kat ",
    # Religia & Magia (25)
    "kapłan", "arcykapłan", "mnich", "zakonnik", "opat ", "przeor", "biskup", "czarodziej",
    "czarownik", "mag ", "arcymag", "czarnoksiężnik", "nekromanta", "alchemik", "szaman",
    "druid", "guślarz", "wróżbita", "wieszcz", "prorok", "zielarz", "znachor", "zaklinacz",
    "iluzjonista", "egzorcysta",
    # Rzemiosło & Handel (30)
    "kowal", "karczmarz", "szynkarz", "oberżysta", "kupiec", "handlarz", "kramarz", "piekarz",
    "cukiernik", "rzeźnik", "krawiec", "szewc", "stolarz", "cieśla", "garncarz", "tkacz",
    "garbarz", "kuśnierz", "młynarz", "rolnik", "wieśniak", "chłop ", "pasterz", "drwal",
    "leśnik", "gajowy", "rybak", "marynarz", "żeglarz", "sternik",
    # Edukacja & Medycyna (15)
    "nauczyciel", "profesor", "uczeń", "student", "wychowawca", "lekarz", "medyk", "pielęgniarz",
    "uzdrowiciel", "aptekarz", "sędzia", "urzędnik", "namiestnik", "kanclerz", "skryba",
    # Dodatkowe
    "lord", "kuge", "buke", "wasal"
]

POLISH_COMMON_NOUN_HOMONYMS: Set[str] = {
    # 1. Żywioły, astronomia, pory roku i czas (65 słów)
    "ogień", "woda", "ziemia", "wiatr", "powietrze", "płomień", "żar", "popiół", "iskra", "dym",
    "lód", "mróz", "śnieg", "szron", "grad", "deszcz", "ulewa", "burza", "grom", "piorun",
    "błyskawica", "chmura", "mgła", "rosa", "szadź", "fala", "przypływ", "odpływ", "wir", "prąd",
    "blask", "światło", "cień", "mrok", "ciemność", "zorza", "łuna", "tęcza", "promień", "słońce",
    "księżyc", "gwiazda", "kometa", "meteoryt", "świt", "brzask", "poranek", "dzień", "południe", "zmierzch",
    "zmrok", "wieczór", "noc", "północ", "czas", "chwila", "moment", "wieczność", "era", "wiek",
    "zima", "wiosna", "lato", "jesień",

    # 2. Minerały, metale i barwy (47 słów)
    "kamień", "skała", "głaz", "żwir", "piasek", "pył", "proch", "glina", "błoto", "kreda",
    "węgiel", "ruda", "kruszec", "żelazo", "stal", "miedź", "brąz", "mosiądz", "spiż", "złoto",
    "srebro", "ołów", "cyna", "rtęć", "kryształ", "diament", "rubin", "szafir", "szmaragd", "bursztyn",
    "perła", "koral", "agat", "jaspis", "ametyst", "onyks", "opal", "nefryt", "topaz", "biel",
    "czerń", "czerwień", "błękit", "zieleń", "żółć", "purpura", "szkarłat",

    # 3. Zwierzęta, ptaki, owady i bestie fantastyczne (104 słowa)
    "wilk", "wilczyca", "lis", "lisica", "niedźwiedź", "lew", "lwica", "tygrys", "pantera", "lampart",
    "ryś", "żbik", "kuna", "borsuk", "wydra", "soból", "gronostaj", "łasica", "jeleń", "sarna",
    "łoś", "daniel", "dzik", "żubr", "tur", "koń", "ogier", "klacz", "byk", "wół",
    "krowa", "baran", "owca", "kozioł", "koza", "pies", "wilczur", "ogar", "kot", "mysz",
    "szczur", "zając", "królik", "jeż", "kret", "bóbr", "wiewiórka", "nietoperz", "orzeł", "sokół",
    "jastrząb", "krogulec", "bielik", "myszołów", "sęp", "kruk", "wrona", "gawron", "kawka", "sroka",
    "sójka", "sowa", "puchacz", "puszczyk", "bocian", "żuraw", "czapla", "łabędź", "gęś", "kaczka",
    "kormoran", "mewa", "jaskółka", "gołąb", "słowik", "skowronek", "drozd", "kos", "dzięcioł", "dudek",
    "kogut", "kura", "kaczor", "bażant", "kuropatwa", "wąż", "żmija", "zaskroniec", "jaszczurka", "żółw",
    "krokodyl", "żaba", "ropucha", "salamandra", "smok", "żmij", "gryf", "bazyliszek", "wiwerna", "hydra",
    "feniks", "chimera", "jednorożec", "pegaz", "lewiatan", "kraken", "pająk", "skorpion", "osa", "pszczoła",
    "szerszeń", "mrówka", "ważka", "modliszka", "mucha", "komar", "motyl", "ćma", "żuk", "chrząszcz",

    # 4. Flora, drzewa i roślinność (55 słów)
    "drzewo", "las", "bór", "puszcza", "gaj", "dąb", "sosna", "świerk", "jodła", "modrzew",
    "brzoza", "buk", "grab", "jesion", "wiąz", "klon", "jawor", "lipa", "olcha", "topola",
    "wierzba", "cis", "jarząb", "głóg", "tarnina", "róża", "lilia", "mak", "fiołek", "wrzos",
    "mech", "paproć", "trawa", "trzcina", "sitowie", "bluszcz", "jemioła", "konwalia", "pokrzywa", "piołun",
    "liść", "gałąź", "konar", "pień", "kora", "korzeń", "pąk", "kwiat", "owoc", "jagoda",
    "nasiono", "ziarno", "szyszka", "cierń", "kolec",

    # 5. Topografia, krajobraz i architektura (98 słów)
    "góra", "szczyt", "grań", "turnia", "wierch", "przełęcz", "stok", "zbocze", "wzgórze", "pagórek",
    "kotlina", "dolina", "parów", "jar", "wąwóz", "rów", "przepaść", "urwisko", "otchłań", "jaskinia",
    "grota", "pieczara", "piekiełko", "wulkan", "krater", "pustynia", "step", "preria", "sawanna", "łąka",
    "pole", "równina", "polana", "bagno", "moczary", "bagnisko", "trzęsawisko", "rzeka", "potok", "strumień",
    "ruczaj", "źródło", "koryto", "brzeg", "mielizna", "wodospad", "kaskada", "jezioro", "staw", "sadzawka",
    "morze", "ocean", "zatoka", "zalew", "cieśnina", "fiord", "laguna", "wyspa", "wysepka", "archipelag",
    "półwysep", "przylądek", "rafa", "mierzeja", "droga", "trakt", "szlak", "ścieżka", "gościniec", "rozdroże",
    "skrzyżowanie", "most", "kładka", "grobla", "tama", "brama", "wrota", "furta", "baszta", "wieża",
    "mur", "mury", "zamek", "gród", "twierdza", "forteca", "szaniec", "bastion", "pałac", "dwór",
    "chata", "dom", "domostwo", "osada", "wieś", "miasto", "rynek", "plac", "uliczka", "zaułek",
    "świątynia", "klasztor", "kaplica", "ołtarz", "grobowiec", "grób", "mogiła", "kurhan", "cmentarz", "czeluść",
    "loch", "piwnica", "katakumby", "labirynt",

    # 6. Broń, rynsztunek i insygnia (73 słowa)
    "miecz", "szpada", "szabla", "rapier", "sztylet", "kord", "nóż", "puginał", "kindżał", "kosa",
    "sierp", "włócznia", "pika", "lanca", "dzida", "oszczep", "harpun", "halabarda", "berdysz", "glewia",
    "topór", "siekiera", "czekan", "nadziak", "obuch", "młot", "młotek", "buława", "buzdygan", "korbacz",
    "kiścień", "wekiera", "pałka", "maczuga", "kij", "kostur", "laska", "proca", "łuk", "kusza",
    "strzała", "bełt", "grot", "kołczan", "tarcza", "puklerz", "pawęż", "hełm", "przyłbica", "szyszak",
    "kolczuga", "pancerz", "zbroja", "kirys", "napierśnik", "naramiennik", "karwasz", "rękawica", "nagolennik", "nakolannik",
    "pas", "pochwa", "temblak", "korona", "diadem", "tiara", "tron", "berło", "jabłko", "pieczęć",
    "herb", "sztandar", "chorągiew", "flaga", "proporzec", "godło", "znak", "łańcuch", "powróz", "lina",
    "kajdany", "dyby", "klatka", "hak", "kotwica",

    # 7. Pojęcia abstrakcyjne, cnoty, afekt i magia (96 słów)
    "wola", "los", "dola", "niedola", "fatum", "przeznaczenie", "przypadek", "zbieg", "kres", "początek",
    "koniec", "życie", "śmierć", "duma", "honor", "chwała", "sława", "hańba", "wstyd", "męstwo",
    "odwaga", "śmiałość", "strach", "lęk", "trwoga", "groza", "zgroza", "panika", "ból", "cierpienie",
    "męka", "katusze", "rozpacz", "żal", "smutek", "tęsknota", "gniew", "złość", "szał", "wściekłość",
    "furia", "spokój", "pokój", "cisza", "milczenie", "prawda", "fałsz", "kłamstwo", "obłuda", "zdrada",
    "wierność", "wiara", "nadzieja", "miłość", "nienawiść", "łaska", "litość", "miłosierdzie", "zemsta", "odwet",
    "kara", "nagroda", "prawo", "bezprawie", "sprawiedliwość", "wolność", "swoboda", "niewola", "pęta", "więzy",
    "potęga", "siła", "moc", "niemoc", "słabość", "władza", "rządy", "panowanie", "ład", "porządek",
    "chaos", "bezład", "cud", "omen", "wróżba", "klątwa", "przekleństwo", "urok", "czar", "czary",
    "zaklęcie", "magia", "wiedza", "mądrość", "rozum", "spryt", "zmysł", "pamięć", "zapomnienie", "sen",
    "jawa", "mara", "widziadło", "zmora", "iluzja", "złudzenie", "tajemnica", "sekret", "zagadka", "krzyż",

    # 8. Części ciała, somatyka i percepcja (66 słów)
    "oko", "oczy", "ucho", "uszy", "nos", "usta", "wargi", "ząb", "zęby", "kły",
    "język", "broda", "wąsy", "włosy", "głowa", "czoło", "skroń", "szyja", "kark", "gardło",
    "ramię", "ramiona", "bark", "barki", "pierś", "piersi", "serce", "płuca", "brzuch", "bok",
    "boki", "plecy", "kręgosłup", "kość", "kości", "żebro", "żebra", "ręka", "ręce", "dłoń",
    "dłonie", "palec", "palce", "pięść", "pięści", "szpon", "szpony", "pazur", "pazury", "noga",
    "nogi", "udo", "uda", "kolano", "kolana", "łydka", "stopa", "stopy", "pięta", "krew",
    "posoka", "łza", "łzy", "pot", "ślina", "oddech", "tchnienie", "głos", "krzyk", "wrzask",
    "pisk", "szept", "uśmiech", "spojrzenie", "wzrok", "słuch", "węch", "dotyk", "smak", "ślad", "trop",

    # 9. Postacie pospolite, pokrewieństwo i status (48 słów)
    "człowiek", "lud", "naród", "tłum", "rzesza", "gromada", "zgraja", "wataha", "horda", "klan",
    "plemię", "ród", "rodzina", "ojciec", "matka", "brat", "siostra", "syn", "córka", "dziadek",
    "babka", "dziecko", "niemowlę", "starzec", "staruszka", "młodzieniec", "panna", "dziewczę", "chłopiec", "chłopak",
    "mąż", "żona", "pan", "pani", "król", "książę", "wódz", "wojownik", "rycerz", "strażnik",
    "wróg", "nieprzyjaciel", "druh", "przyjaciel", "towarzysz", "gość", "obcy", "cudzoziemiec", "tułacz", "wędrowiec",
    "pielgrzym", "jeniec", "niewolnik", "sługa", "panicz", "bękart", "podrzutek",

    # 10. Jednostki monetarne, miary i wagi historyczne (20 słów)
    "grosz", "dukat", "talar", "floren", "denar", "szeląg", "tynf", "złoty", "rubel", "marka",
    "łokieć", "sążeń", "mila", "wiorsta", "staja", "korzec", "kwarta", "pud", "funt", "cetnar",

    # 11. Kalendarz, pory i cykle kosmiczne (21 słów)
    "przedpołudnie", "popołudnie", "zmierzchanie", "nów", "pełnia", "kwadra", "zaćmienie", "przesilenie", "zrównanie",
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",

    # 12. Zjawiska meteorologiczne i wiatry (20 słów)
    "zawierucha", "zamieć", "kurniawa", "nawałnica", "szkwał", "orkan", "tajfun", "cyklon", "monsun", "tornado",
    "sztorm", "halny", "bryza", "zefir", "powiew", "zadymka", "chłód", "upał", "skwar", "spiekota",

    # 13. Formacje geologiczne i hydrologiczne (22 słowa)
    "rozpadlina", "zapadlisko", "grzęda", "żleb", "piarg", "usypisko", "osuwisko", "jastrzębica", "próg", "katarakta",
    "rozlewisko", "meander", "zakole", "dopływ", "starorzecze", "oparzelisko", "topiel", "topielisko", "grzęzawisko", "wydma", "ostęp", "uroczysko",

    # 14. Architektura obronna i militarna (19 słów)
    "palisada", "częstokół", "barbakan", "donżon", "fosa", "blanki", "strzelnica", "kurtyna", "rondel", "czatownia",
    "reduta", "kordegarda", "lazaret", "cekhauz", "arsenał", "mennica", "rogatka", "zamczysko", "strażnica"
}

def is_proper_noun_homonym(word: str) -> bool:
    """
    Determines whether a token is a common noun that frequently collides with proper names/titles.
    When matched, prevents aggressive capitalization or nominative freezing in dependent contexts.
    """
    if not word:
        return False
    return word.strip().lower() in POLISH_COMMON_NOUN_HOMONYMS

RE_FEMALE_ROLE = re.compile(
    r"\b(?:"
    # General / Base
    r"kobieta|kobiet[ayęieoó]|kobietami|kobietach|żeńsk[a-ząćęłńóśźż]*|female|dziewczyn[a-ząćęłńóśźż]*|"
    r"pani(?:ą|ej)?(?!\s*e\b)|bohaterk[a-ząćęłńóśźż]*|chatun|girl|woman|lady|"
    # Rodzina (18) + Hipokorystyki i Oboczności (np. ch:sz macocha/macosze)
    r"matk[a-ząćęłńóśźż]*|mam[a-ząćęłńóśźż]*|mamusi[a-ząćęłńóśźż]*|mateńk[a-ząćęłńóśźż]*|córk[a-ząćęłńóśźż]*|córeczk[a-ząćęłńóśźż]*|córuni[a-ząćęłńóśźż]*|siostr[a-ząćęłńóśźż]*|siostrzyczk[a-ząćęłńóśźż]*|siostruni[a-ząćęłńóśźż]*|"
    r"bab(?:ka|ce|kę|ką|ki|ek|kom|kami|kach)|babci[a-ząćęłńóśźż]*|babuni[a-ząćęłńóśźż]*|prabab(?:ka|ce|kę|ką|ki|ek|kom|kami|kach)|prababci[a-ząćęłńóśźż]*|"
    r"wnuczk[a-ząćęłńóśźż]*|wnusi[a-ząćęłńóśźż]*|prawnuczk[a-ząćęłńóśźż]*|"
    r"ciot(?:ka|ce|kę|ką|ki|ek|kom|kami|kach)|wujenk[a-ząćęłńóśźż]*|stryjenk[a-ząćęłńóśźż]*|bratanic[a-ząćęłńóśźż]*|siostrzenic[a-ząćęłńóśźż]*|"
    r"teściow(?:a|ej|ą|o|e|ych|ym|ymi)\b|świekr[a-ząćęłńóśźż]*|synow(?:a|ej|ą|o|e|ych|ym|ymi)\b|szwagierk[a-ząćęłńóśźż]*|kuzynk[a-ząćęłńóśźż]*|"
    r"pasierbic[a-ząćęłńóśźż]*|macoch[a-ząćęłńóśźż]*|macosz[a-ząćęłńóśźż]*|"
    # Monarchia & Władza (22)
    r"królow(?:a|ej|ą|o|e|ych|ym|ymi)\b|królewn[a-ząćęłńóśźż]*|księżniczk[a-ząćęłńóśźż]*|księżn[a-ząćęłńóśźż]*|cesarzow(?:a|ej|ą|o|e|ych|ym|ymi)\b|"
    r"cesarzewn[a-ząćęłńóśźż]*|caryc[a-ząćęłńóśźż]*|carewn[a-ząćęłńóśźż]*|władczyn[a-ząćęłńóśźż]*|suwerenk[a-ząćęłńóśźż]*|"
    r"monarchin[a-ząćęłńóśźż]*|arcyksiężn[a-ząćęłńóśźż]*|wielmożn(?:a|ej|ą|e|ych|ym|ymi)\b|diuszes[a-ząćęłńóśźż]*|markiz[a-ząćęłńóśźż]*|"
    r"margrabin[a-ząćęłńóśźż]*|hrabin[a-ząćęłńóśźż]*|hrabiank[a-ząćęłńóśźż]*|wicehrabin[a-ząćęłńóśźż]*|baronow(?:a|ej|ą|o|e|ych|ym|ymi)\b|"
    r"baronówn[a-ząćęłńóśźż]*|szlachciank[a-ząćęłńóśźż]*|magnatk[a-ząćęłńóśźż]*|arystokratk[a-ząćęłńóśźż]*|"
    # Dwór & Służba (20)
    r"panienk[a-ząćęłńóśźż]*|pann[ayęe]|służąc(?:a|ej|ą|e|ych|ym|ymi)\b|pokojówk[a-ząćęłńóśźż]*|garderobian(?:a|ej|ą|e|ych|ym|ymi)\b|ochmistrzyn[a-ząćęłńóśźż]*|"
    r"woźniczk[a-ząćęłńóśźż]*|fornaliczk[a-ząćęłńóśźż]*|stajenn(?:a|ej|ą|e|ych|ym|ymi)\b|posługaczk[a-ząćęłńóśźż]*|ogrodniczk[a-ząćęłńóśźż]*|"
    r"kuchark[a-ząćęłńóśźż]*|pomywaczk[a-ząćęłńóśźż]*|szafark[a-ząćęłńóśźż]*|klucznic[a-ząćęłńóśźż]*|zarządczyn[a-ząćęłńóśźż]*|"
    r"dama\s+dworu|damy\s+dworu|damie\s+dworu|damą\s+dworu|dwórk[a-ząćęłńóśźż]*|niańk[a-ząćęłńóśźż]*|mamk[a-ząćęłńóśźż]*|"
    # Wojsko & Straż (35)
    r"żołnierk[a-ząćęłńóśźż]*|wojowniczk[a-ząćęłńóśźż]*|rycerk[a-ząćęłńóśźż]*|strażniczk[a-ząćęłńóśźż]*|wartowniczk[a-ząćęłńóśźż]*|"
    r"dowódczyn[a-ząćęłńóśźż]*|generałow(?:a|ej|ą|o|e|ych|ym|ymi)\b|generałk[a-ząćęłńóśźż]*|komendantk[a-ząćęłńóśźż]*|kapitank[a-ząćęłńóśźż]*|"
    r"oficerk[a-ząćęłńóśźż]*|poruczniczk[a-ząćęłńóśźż]*|podporuczniczk[a-ząćęłńóśźż]*|pułkowniczk[a-ząćęłńóśźż]*|podpułkowniczk[a-ząćęłńóśźż]*|"
    r"majork[a-ząćęłńóśźż]*|sierżantk[a-ząćęłńóśźż]*|kapralk[a-ząćęłńóśźż]*|szeregow(?:a|ej|ą|e|ych|ym|ymi)\b|kadetk[a-ząćęłńóśźż]*|rekrutk[a-ząćęłńóśźż]*|"
    r"hetmanow(?:a|ej|ą|o|e|ych|ym|ymi)\b|fechmistrzyn[a-ząćęłńóśźż]*|szermierk[a-ząćęłńóśźż]*|łuczniczk[a-ząćęłńóśźż]*|kuszniczk[a-ząćęłńóśźż]*|"
    r"włóczniczk[a-ząćęłńóśźż]*|tarczowniczk[a-ząćęłńóśźż]*|pikinierk[a-ząćęłńóśźż]*|zwiadowczyn[a-ząćęłńóśźż]*|kanonierk[a-ząćęłńóśźż]*|"
    r"saperk[a-ząćęłńóśźż]*|piechurk[a-ząćęłńóśźż]*|najemniczk[a-ząćęłńóśźż]*|obrończyn[a-ząćęłńóśźż]*|przywódczyn[a-ząćęłńóśźż]*|"
    # Religia & Magia (25)
    r"kapłank[a-ząćęłńóśźż]*|arcykapłank[a-ząćęłńóśźż]*|mniszk[a-ząćęłńóśźż]*|zakonnic[a-ząćęłńóśźż]*|opatk[a-ząćęłńóśźż]*|"
    r"przeorysz[a-ząćęłńóśźż]*|biskupk[a-ząćęłńóśźż]*|czarodziejk[a-ząćęłńóśźż]*|czarownic[a-ząćęłńóśźż]*|magini[a-ząćęłńóśźż]*|"
    r"arcymagini[a-ząćęłńóśźż]*|czarnoksiężnic[a-ząćęłńóśźż]*|nekromantk[a-ząćęłńóśźż]*|alchemiczk[a-ząćęłńóśźż]*|szamank[a-ząćęłńóśźż]*|"
    r"druidk[a-ząćęłńóśźż]*|guślark[a-ząćęłńóśźż]*|wiedźm[a-ząćęłńóśźż]*|wróżk[a-ząćęłńóśźż]*|wieszczk[a-ząćęłńóśźż]*|"
    r"prorokin[a-ząćęłńóśźż]*|zielark[a-ząćęłńóśźż]*|znachork[a-ząćęłńóśźż]*|zaklinaczk[a-ząćęłńóśźż]*|iluzjonistk[a-ząćęłńóśźż]*|egzorcystk[a-ząćęłńóśźż]*|"
    # Rzemiosło & Handel (30)
    r"kowalk[a-ząćęłńóśźż]*|karczmark[a-ząćęłńóśźż]*|szynkark[a-ząćęłńóśźż]*|oberżystk[a-ząćęłńóśźż]*|kupcow(?:a|ej|ą|o|e|ych|ym|ymi)\b|kupczyn[a-ząćęłńóśźż]*|"
    r"handlark[a-ząćęłńóśźż]*|kramark[a-ząćęłńóśźż]*|piekark[a-ząćęłńóśźż]*|cukierniczk[a-ząćęłńóśźż]*|rzeźniczk[a-ząćęłńóśźż]*|"
    r"krawcow(?:a|ej|ą|o|e|ych|ym|ymi)\b|szewcow(?:a|ej|ą|o|e|ych|ym|ymi)\b|stolark[a-ząćęłńóśźż]*|cieślin[a-ząćęłńóśźż]*|garncark[a-ząćęłńóśźż]*|"
    r"tkaczk[a-ząćęłńóśźż]*|garbark[a-ząćęłńóśźż]*|kuśnierk[a-ząćęłńóśźż]*|młynark[a-ząćęłńóśźż]*|rolniczk[a-ząćęłńóśźż]*|"
    r"wieśniaczk[a-ząćęłńóśźż]*|chłopk[a-ząćęłńóśźż]*|pasterk[a-ząćęłńóśźż]*|drwalk[a-ząćęłńóśźż]*|leśniczk[a-ząćęłńóśźż]*|"
    r"gajow(?:a|ej|ą|e|ych|ym|ymi)\b|rybaczk[a-ząćęłńóśźż]*|żeglark[a-ząćęłńóśźż]*|sterniczk[a-ząćęłńóśźż]*|"
    # Edukacja & Medycyna (15)
    r"nauczycielk[a-ząćęłńóśźż]*|profesork[a-ząćęłńóśźż]*|uczennic[a-ząćęłńóśźż]*|studentk[a-ząćęłńóśźż]*|wychowawczyn[a-ząćęłńóśźż]*|"
    r"lekark[a-ząćęłńóśźż]*|medyczk[a-ząćęłńóśźż]*|pielęgniark[a-ząćęłńóśźż]*|uzdrowicielk[a-ząćęłńóśźż]*|aptekark[a-ząćęłńóśźż]*|"
    r"sędzin[a-ząćęłńóśźż]*|urzędniczk[a-ząćęłńóśźż]*|namiestniczk[a-ząćęłńóśźż]*|kanclerzow(?:a|ej|ą|o|e|ych|ym|ymi)\b|skrybk[a-ząćęłńóśźż]*|"
    # Inne
    r"żon[a-ząćęłńóśźż]*|małżonk[a-ząćęłńóśźż]*|miko|szpieżk[a-ząćęłńóśźż]*"
    r")\b",
    re.IGNORECASE
)

RE_MALE_ROLE = re.compile(
    r"\b(?:"
    # General / Base
    r"mężczyzn[a-ząćęłńóśźż]*|męsk[a-ząćęłńóśźż]*|male|man|bocchan|"
    r"chłop(?:ak[a-ząćęłńóśźż]*|iec|ca|cem|cu|cowi|cy|ców|om|ami|ach|a|em|u|i)?|boy|"
    r"młodzieniec|młodzieńc[a-ząćęłńóśźż]*|panie\b|pan(?:em|u|a|owie|ów)?\b|"
    # Rodzina (18) + Hipokorystyki i Oboczności (np. tatko, tatusia, synuś, braciszek)
    r"ojc(?:iec|a|em|u|owi|owie|ów|om|ami|ach)|ojczulk[a-ząćęłńóśźż]*|tat[a-ząćęłńóśźż]*|tatk[a-ząćęłńóśźż]*|tatu(?:ś|si[a-ząćęłńóśźż]*)|"
    r"syn(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|synek\b|synk[a-ząćęłńóśźż]*|synu(?:ś|si[a-ząćęłńóśźż]*)|"
    r"brat(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|braci[a-ząćęłńóśźż]*|braciszk[a-ząćęłńóśźż]*|"
    r"dziad(?:ek|ka|kiem|kowi|kowie|ków|kom|kami|kach|[aeyu]|em|owi|owie|ów)?|dziadziu(?:ś|si[a-ząćęłńóśźż]*)|dziaduni[a-ząćęłńóśźż]*|"
    r"pradziad(?:ek|ka|kiem|kowi|kowie|ków|kom|kami|kach|[aeyu]|em|owi|owie|ów)?|"
    r"wnuk(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|wnuczk[a-ząćęłńóśźż]*|wnu(?:ś|si[a-ząćęłńóśźż]*)|prawnuk(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|"
    r"wuj(?:ek|ka|kiem|kowi|kowie|ków|kom|kami|kach|[aeyu]|em|owi|owie|ów)?|"
    r"stryj(?:ek|ka|kiem|kowi|kowie|ków|kom|kami|kach|[aeyu]|em|owi|owie|ów)?|bratan(?:ek|ka|kiem|kowi|kowie|ków|kom|kami|kach)|"
    r"siostrzeniec|siostrzeńc[a-ząćęłńóśźż]*|teść|teści(?:a|em|owi|owie|ów|om|ami|ach)|świekier(?:[aeyu]|em|owi|owie|ów)?|"
    r"zięć|zięci(?:a|em|owi|owie|ów|om|ami|ach)|szwagier|szwagr[a-ząćęłńóśźż]*|kuzyn(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|"
    r"pasierb(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|ojczym(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|"
    # Monarchia & Władza (22)
    r"król(?:a|em|owi|owie|ów)?(?!\s*ow[a-ząćęłńóśźż]*\b)|królewicz(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|"
    r"książ(?:ę|ęta|ąt)|księ(?:cia|ciem|ciu|ciom|ciami|ciach)|cesarz(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?|cesarzewicz(?:[aeyu]|em|owi|owie|ów)?|"
    r"car(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?(?!\s*(?:sk|yc|ew)[a-ząćęłńóśźż]*\b)|carewicz(?:[aeyu]|em|owi|owie|ów)?|władc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|suweren(?:[aeyu]|em|owi|owie|ów)?|"
    r"monarch[a-ząćęłńóśźż]*|arcyksiąż(?:ę|ęta|ąt)|arcyksię(?:cia|ciem|ciu|ciom|ciami|ciach)|wielmoż[a-ząćęłńóśźż]*|diuk(?:[aeyu]|em|owi|owie|ów)?|"
    r"markiz(?:[aeyu]|em|owi|owie|ów)?(?!\s*a\b)|margrabi[a-ząćęłńóśźż]*|hrabi[a-ząćęłńóśźż]*|hrabicz(?:[aeyu]|em|owi|owie|ów)?|"
    r"wicehrabi[a-ząćęłńóśźż]*|baron(?:[aeyu]|em|owi|owie|ów)?(?!\s*ow[a-ząćęłńóśźż]*\b)|szlachcic[a-ząćęłńóśźż]*|"
    r"magnat(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|arystokrat[a-ząćęłńóśźż]*|"
    # Dwór & Służba (20)
    r"panicz[a-ząćęłńóśźż]*|służąc(?:y|ego|emu|ym|ych)|lokaj(?:[aeyu]|em|owi|owie|ów)?|kamerdyner[a-ząćęłńóśźż]*|majordomus[a-ząćęłńóśźż]*|"
    r"ochmistrz(?:[aeyu]|em|owi|owie|ów)?(?!\s*yn[a-ząćęłńóśźż]*\b)|stangret[a-ząćęłńóśźż]*|fornal(?:[aeyu]|em|owi|owie|ów)?(?!\s*iczk[a-ząćęłńóśźż]*\b)|stajenn(?:y|ego|emu|ym|ych)|pachoł(?:ek|ka|kiem|kowi|kowie|ków)|"
    r"parob(?:ek|ka|kiem|kowi|kowie|ków)|ogrodnik[a-ząćęłńóśźż]*|kucharz[a-ząćęłńóśźż]*|kuchcik[a-ząćęłńóśźż]*|szafarz[a-ząćęłńóśźż]*|"
    r"klucznik[a-ząćęłńóśźż]*|zarządc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|giermek[a-ząćęłńóśźż]*|pa(?:ź|zia|ziem|ziowi|ziom|ziowie|ziów|ziach|ziami)|samuraj[a-ząćęłńóśźż]*|"
    # Wojsko & Straż (35)
    r"żołnierz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|wojowni(?:k(?:a|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|rycerz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|strażni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|"
    r"wartowni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|dowódc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|generał(?:[aeyu]|em|owi|owie|ów)?(?!\s*(?:k|ow)[a-ząćęłńóśźż]*\b)|komendant(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|kapitan(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"oficer(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|poruczni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|podporuczni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|pułkowni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|podpułkowni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|"
    r"major(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?(?!\s*k[a-ząćęłńóśźż]*\b)|sierżant(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|kapral(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|szeregow(?:iec|ca|cem|cowi|cy|ców)|"
    r"kadet(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|rekrut(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|hetman(?:[aeyu]|em|owi|owie|ów)?(?!\s*ow[a-ząćęłńóśźż]*\b)|fechmistrz(?:[aeyu]|em|owi|owie|ów)?(?!\s*yn[a-ząćęłńóśźż]*\b)|szermierz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"łuczni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|kuszni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|włóczni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|tarczowni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|pikinier(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"zwiadowc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|kanonier(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|saper(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|piechur(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|najemni(?:k(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|cy\b)|"
    r"obrońc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|wódz|wodz(?:a|em|owi|owie|ów|om|ami|ach)|kat(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?(?!\s*egor[a-ząćęłńóśźż]*\b)|kac(?:i|ie)|"
    # Religia & Magia (25)
    r"kapłan(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|arcykapłan(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|mnich[a-ząćęłńóśźż]*|mnisi\b|zakonnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"opat(?:[aeyu]|em|owi|owie|ów|om|ami|ach)?(?!\s*k[a-ząćęłńóśźż]*\b)|przeor(?:[aeyu]|em|owi|owie|ów)?(?!\s*ysz[a-ząćęłńóśźż]*\b)|biskup(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|czarodziej(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"czarownik(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|mag(?:[aeyu]|iem|owi|owie|ów|om|ami|ach)?(?!\s*in[a-ząćęłńóśźż]*\b)|madz(?:e|y)|arcymag(?:[aeyu]|iem|owi|owie|ów)?(?!\s*in[a-ząćęłńóśźż]*\b)|czarnoksiężnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"nekromant(?:a|y|ę|ą|o|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|alchemik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|szaman(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|druid(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|guślarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"wróżbit(?:a|y|ę|ą|o|ów|om|ami|ach)|wieszcz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|prorok(?:[aeyu]|em|owi|owie|ów)?(?!\s*in[a-ząćęłńóśźż]*\b)|zielarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|znachor(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"zaklinacz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|iluzjonist(?:a|y|ę|ą|o|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|egzorcyst(?:a|y|ę|ą|o|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|"
    # Rzemiosło & Handel (30)
    r"kowal(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|karczmarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|szynkarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|oberżyst(?:a|y|ę|ą|o|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|kupiec|kupc(?:a|em|owi|owie|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"handlarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|kramarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|piekarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|cukiernik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|rzeźnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|"
    r"krawiec|krawc(?:a|em|u|owi|owie|ów|om|ami|ach)(?!\s*ow[a-ząćęłńóśźż]*\b)|szewc(?:[aeyu]|em|owi|owie|ów)?(?!\s*ow[a-ząćęłńóśźż]*\b)|stolarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|cieśl(?:a|i|ę|ą|o|om|ami|ach)(?!\s*in[a-ząćęłńóśźż]*\b)|garncarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"tkacz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|garbarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|kuśnierz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|młynarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|rolnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|"
    r"wieśniak(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|pasterz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|drwal(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|leśnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|gajow(?:y|ego|emu|ym|ych)(?!\s*a\b)|"
    r"rybak(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|marynarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|żeglarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|sternik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|"
    # Edukacja & Medycyna (15)
    r"nauczyciel(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|profesor(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|uczeń|uczni(?:a|em|owi|owie|ów|om|ami|ach)|student(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|wychowawc(?:a|y|ę|ą|o|owie|ów|om|ami|ach)|"
    r"lekarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|medyk(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|pielęgniarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|uzdrowiciel(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|aptekarz(?:[aeyu]|em|owi|owie|ów)?(?!\s*k[a-ząćęłńóśźż]*\b)|"
    r"sędzi(?:a|ego|emu|ą|owie|ów|om|ami|ach)|urzędnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|namiestnik(?:[aeyu]|em|owi|owie|ów)?(?!\s*czk[a-ząćęłńóśźż]*\b)|kanclerz(?:[aeyu]|em|owi|owie|ów)?(?!\s*ow[a-ząćęłńóśźż]*\b)|skryb(?:a|y|ie|ę|ą|o|owie|ów|om|ami|ach)(?!\s*k[a-ząćęłńóśźż]*\b)|"
    # Inne & Posłowie, Karły, Aniołowie, Diabły
    r"lord[a-ząćęłńóśźż]*|wasal[a-ząćęłńóśźż]*|buke|kuge|dostojnik[a-ząćęłńóśźż]*|"
    r"poseł\b|posł(?:a|em|owi|owie|ów|om|ami|ach)\b|karzeł\b|karł(?:a|em|owi|owie|ów|om|ami|ach)\b|"
    r"diabeł\b|diabł(?:a|em|owi|owie|ów|om|ami|ach)\b|diabli\b|anioł(?:[aeyu]|em|owi|owie|ów)?\b|aniel(?:i|e)\b"
    r")\b",
    re.IGNORECASE
)

def is_female_role_text(text: str) -> bool:
    if not text:
        return False
    return bool(RE_FEMALE_ROLE.search(text))

def is_male_role_text(text: str) -> bool:
    if not text:
        return False
    return bool(RE_MALE_ROLE.search(text))

def is_plural_actor(name: str) -> bool:
    """
    Determines whether an actor/speaker represents a plural group or collective
    (e.g. 'Guards', 'Strażnicy', 'Villagers', 'Wieśniacy', 'Dziewczęta', 'Chłopcy').
    """
    if not name:
        return False
    clean = extract_clean_speaker_name(name).strip().lower()
    if not clean:
        return False
    tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", clean))
    if any(t in INHERENT_PLURAL_NOUNS for t in tokens):
        return True
    if clean.startswith(("grupa", "oddział", "tłum", "kompania", "patrol", "banda", "crew", "squad")):
        return True
    return False

def resolve_actor_gender(name: str, character_registry: Optional[Dict[str, Any]] = None, series_bible: Optional[Any] = None) -> str:
    """
    Determines actor gender ('MALE', 'FEMALE', 'PLURAL', or 'UNKNOWN') deterministically (0.00 PLN).
    Accurately processes named characters, generic/numbered actor tags, and plural collective actors.
    """
    if not name:
        return "UNKNOWN"
    clean = extract_clean_speaker_name(name).strip()
    if not clean:
        return "UNKNOWN"
    clean_lower = clean.lower()

    # 0. Check for plural/collective actors first
    if is_plural_actor(clean):
        return "PLURAL"

    # 1. Direct character registry lookup if provided
    if character_registry and clean in character_registry:
        c_val = character_registry[clean]
        c_desc = (c_val.get("gender", "") or c_val.get("description", "") or c_val.get("role", "")) if isinstance(c_val, dict) else str(c_val)
        c_desc_l = c_desc.lower()
        if "female" in c_desc_l or "kobieta" in c_desc_l or "żeńsk" in c_desc_l:
            return "FEMALE"
        if "male" in c_desc_l or "mężczyzna" in c_desc_l or "męsk" in c_desc_l:
            return "MALE"

    # 2. Series Bible lookup if provided
    if series_bible and hasattr(series_bible, "get_character_gender"):
        bg = series_bible.get_character_gender(clean, allow_generic_nouns=True)
        if bg in ("MALE", "FEMALE"):
            return bg

    # 3. Canonical name sets
    if clean_lower in CANONICAL_MALE_NAMES or clean_lower in MALE_EXCEPTIONS_ON_A:
        return "MALE"
    if clean_lower in POLISH_FEMALE_NAMES:
        return "FEMALE"

    # 4. Role & Lexical tokens with strict word boundaries
    tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", clean_lower))
    if any(t in INHERENT_FEMALE_NOUNS for t in tokens) or is_female_role_text(clean):
        return "FEMALE"
    if any(t in INHERENT_MALE_NOUNS for t in tokens) or is_male_role_text(clean):
        return "MALE"

    # 5. Onomastic heuristics
    if is_inherently_female_name(clean):
        return "FEMALE"

    return "UNKNOWN"


BOY_ROLE_KEYWORDS = [
    "chłopiec", "chłopak", "boy", "syn", "młodzieniec", "książę",
    "dziecko płci męskiej", "pax", "bocchan", "crossgender", "cross-gender", "seiyū żeński", "żeńskie seiyū"
]

GENERIC_CATEGORY_TAGS = {
    # Polish technical & crowd tags
    "mężczyzna", "mezczyzna", "kobieta", "grupa_kobiet", "grupa_mężczyzn", "grupa_mezczyzn",
    "grupa_mieszana", "brak", "narrator", "głos", "glos", "ktoś", "ktos", "nikt", "wszyscy",
    "tłum", "tlum", "napis", "napisy", "tytuł", "tytul", "tłumaczenie", "tlumaczenie",
    "postać", "postac", "interlokutor", "obcy", "nieznajomy", "grupa", "rozmówca", "tło", "tlo",
    # English technical & crowd tags
    "main", "default", "alt", "sign", "signs", "crowd", "voice", "voices", "unknown", "none",
    "all", "everyone", "somebody", "someone", "nobody", "narration", "caption", "captions",
    "title", "titles", "subtitle", "subtitles", "translation", "background", "mob", "people",
    "bystander", "bystanders", "audience", "spectators", "person", "character", "speaker",
    "caller", "announcer"
}

POLISH_FEMALE_NAMES = {
    "monika", "anna", "maria", "katarzyna", "małgorzata", "malgorzata", "agnieszka",
    "barbara", "ewa", "magdalena", "elżbieta", "elzbieta", "krystyna", "joanna",
    "aleksandra", "zofia", "danuta", "irena", "jadwiga", "teresa", "halina",
    "karolina", "natalia", "julia", "paulina", "beata", "dorota", "justyna",
    "iwona", "renata", "jolanta", "urszula", "alicja", "sylwia", "patrycja",
    "marta", "dominika", "aneta", "edyta", "izabela", "kinga", "wioletta",
    "kamila", "bogumiła", "bogumila", "wiesława", "wieslawa", "stanisława", "stanislawa",
    "janina", "czesława", "czeslawa", "wanda", "władysława", "wladyslawa", "grażyna", "grazyna",
    "bożena", "bozena", "marzena", "lucyna", "mariola", "henryka", "kazimiera",
    "genowefa", "bronislawa", "bronisława", "stefania", "cecylia", "emilia", "klaudia",
    "weronika", "oliwia", "wiktoria", "maja", "zuzanna", "pola", "antonina",
    "laura", "nadia", "liliana", "klara", "nina", "jagoda", "malwina",
    "kornelia", "kalina", "daria", "diana", "judyta", "fatima", "agata", "alina",
    "anita", "celina", "felicja", "gloria", "helena", "ida", "iga", "ilona",
    "karina", "lena", "lidia", "lila", "lucja", "łucja", "marika", "marlena",
    "martyna", "milena", "miranda", "nikola", "regina", "roksana", "sabina",
    "sara", "sonia", "stella", "tamara", "tola", "żaneta",
    "ada", "adriana", "anastazja", "apolonia", "aurelia", "bernadeta", "blanka",
    "dagmara", "dobrawa", "dobrochna", "eleonora", "eliza", "eugenia", "faustyna",
    "florentyna", "franciszka", "gabriela", "gaja", "gertruda", "gizela", "honorata",
    "hortensja", "inga", "irmina", "izolda", "jagienka", "klementyna", "konstancja",
    "kordelia", "krystiana", "leokadia", "lilianna", "liwia", "ludmiła", "luiza",
    "marcelina", "matylda", "melania", "michalina", "mirosława", "nadzieja", "noemi",
    "otylia", "pelagia", "petronela", "rozalia", "róża", "roza", "salomea", "seweryna",
    "sławomira", "slawomira", "sydonia", "sybilla", "tekla", "teodora", "waleria",
    "wiola", "wirginia",
    # Hypocoristics and popular variants (for vocative conversion)
    "kasia", "basia", "asia", "ania", "ola", "gosia", "madzia", "zosia",
    "marysia", "natalka", "julka", "krysia", "danka", "ala", "magda",
    "agatka", "agnisia", "agusia", "anetka", "andzia", "anitka", "anka", "anusia",
    "tosia", "tośka", "beatka", "bogusia", "celinka", "domisia", "dorotka", "edytka",
    "ela", "elka", "elunia", "emilka", "ewka", "ewunia", "halka", "halinka", "helka",
    "helenka", "iza", "izka", "jadzia", "jadźka", "joasia", "aśka", "juleczka",
    "justynka", "kamilka", "karolka", "kaśka", "kasiunia", "kingusia", "kryśka",
    "lucynka", "łucka", "lucka", "madźka", "gośka", "małgośka", "malgoska", "maryśka",
    "marychna", "martka", "martusia", "martynka", "marzenka", "monia", "moniczka",
    "natka", "oliwka", "paulinka", "renatka", "roksa", "sylwka", "terenia", "tesia",
    "ula", "ulka", "ulusia", "werka", "weronisia", "wika", "wikusia", "wiolka",
    "zośka", "zosieńka", "zuzia", "zuza", "zuźka", "zuzka"
}

MALE_EXCEPTIONS_ON_A = {
    "kuba", "barnaba", "kosma", "bonawentura", "jarema", "zawisza",
    "sasza", "mustafa", "joshua", "akira", "luka", "luca",
    "shira", "gaara", "kiba", "soma", "kenta", "ryoma", "hanza", "koba", "soya",
    "toma", "genga", "seneca", "kaligula", "sparta", "spinoza", "buddha", "budda",
    "dante", "petrarka", "torquemada", "zapata", "garcia", "elijah", "noah", "ezra",
    "micah", "hosea", "jeremiah", "jonah", "isaiah", "sasha", "misha", "ilja", "kolja",
    "wania", "alosza", "foma", "grisha", "toya", "shota", "souta", "kota", "shouta",
    "yuuta", "yuta", "renga", "hakuya", "byakuya", "genya", "katsura"
}

ETHNONYMS_AND_COLLECTIVES = {
    # English plural and singular ethnonyms / collectives / polities
    "mongols", "mongol", "tatars", "tatar", "merkit", "merkits", "persians", "persian",
    "romans", "roman", "jurchen", "jurchens", "nomad", "nomads", "pastoralists", "pastoralist",
    "hunters", "hunter", "turks", "turk", "chinese", "arabs", "arab", "japanese",
    "demons", "demon", "humans", "human", "elves", "elf", "dwarves", "dwarf",
    "orcs", "orc", "beasts", "spirits", "monsters",
    # Polish plural and singular ethnonyms / collectives
    "mongołowie", "mongołów", "mongoli", "mongoł", "mongola",
    "tatarzy", "tatarów", "tatar",
    "merkici", "merkitów", "merkit",
    "persowie", "persów", "pers",
    "rzymianie", "rzymian", "rzymianin",
    "koczownicy", "koczowników", "koczownik",
    "nomadzi", "nomadów", "nomada",
    "dżurdżeni", "dżurdżeńczycy", "jurcheni",
    "turcy", "turków", "turek",
    "chińczycy", "chińczyków", "chińczyk",
    "arabowie", "arabów", "arab",
    "japończycy", "japończyków", "japończyk",
    "ludzie", "ludzi", "lud", "człowiek",
    "demony", "demonów", "elfy", "elfów", "krasnoludy", "krasnoludów",
    "orkowie", "orków", "bestie", "duchy", "potwory"
}

INDECLINABLE_FRENCH_TOPONYMS = {
    "bordeaux", "margaux", "calais", "meaux", "pau", "chamonix", "angers", "versailles", "reims", "brest", "nantes"
}

UNIVERSAL_FEMALE_NAMES_ON_A = {
    "asuka", "sakura", "elena", "fatima", "sonia", "hinata", "mikasa", "historia",
    "erza", "ayaka", "kaori", "shizuka", "ayame", "kana", "chika", "rika",
    "akane", "haruka", "nanami", "hina", "marin", "kanna", "alya", "tanya",
    "alisa", "fiona", "eliza", "clara", "rebecca", "teresa", "selena", "vanessa",
    "melissa", "natasha", "tatiana", "olga", "sveta", "katrina", "sabrina", "sarah"
}

INVARIABLE_JAPANESE_FEMALE_NAMES = {
    "karin", "marin", "rin", "ran", "ren", "shion", "karen", "sion", "suzu",
    "yoruichi", "aoi", "shinobu", "nanami", "ayame", "kaori", "tsunade", "tomoyo",
    "hitomi", "megumi", "homura", "madoka", "mami", "sayaka", "kyoko", "kohaku",
    "chiyo", "maki", "nobara", "mai", "kasumi", "miwa", "shoko", "utahime",
    "mei", "kanna", "koko", "sakurako", "hanako", "fumiko", "yukiko", "yoko",
    "naoko", "mariko", "keiko", "reiko", "aiko", "riko", "miko", "ririka",
    "kikyo", "kagome", "sango", "kushina", "mikoto", "kurenai", "anko",
    "temari", "tenten", "konan", "mito", "tsuchigumo", "suzumebachi", "nemu",
    "unohana", "isane", "kiyone", "soi-fon", "soifon", "mashiro", "hiyori",
    "himeko", "seele", "bronya", "raiden", "yae"
}

FOREIGN_FEMALE_CONSONANT_NAMES = {
    "chulan", "frieren", "fern", "carmen", "miriam", "ines", "rachel", "astrid", "judith",
    "gwen", "karin", "marin", "rin", "shion", "sion", "helen", "ellen", "karen", "vivian",
    "lyn", "lynn", "ann", "anne", "jean", "joan", "jill", "kim", "dawn", "megan", "beth"
}

def is_inherently_female_name(name: str, series_bible: Any = None) -> bool:
    """
    Returns True if the name is an inherently female first name (Polish or universal female name
    in the curated onomastic database or its vocative form on -o/-u).
    Excludes male exceptions on -a (Kuba, Barnaba, Kosma, etc.), interjections ('ała'),
    generic grammatical categories ('kobieta', 'mężczyzna'), and canonical male names.
    If series_bible is provided, epistemic precedence checks whether the character is registered as MALE.
    """
    if not name:
        return False
    clean = extract_clean_speaker_name(name).strip().lower()
    if is_generic_actor_or_category(clean):
        return False
    if clean in MALE_EXCEPTIONS_ON_A or clean in CANONICAL_MALE_NAMES:
        return False
    if series_bible and hasattr(series_bible, "get_character_gender"):
        try:
            bible_gen = series_bible.get_character_gender(clean, allow_generic_nouns=False)
            if bible_gen == "MALE":
                return False
            if bible_gen == "FEMALE":
                return True
        except Exception:
            pass

    if clean in POLISH_FEMALE_NAMES or clean in UNIVERSAL_FEMALE_NAMES_ON_A or clean in INVARIABLE_JAPANESE_FEMALE_NAMES or clean in FOREIGN_FEMALE_CONSONANT_NAMES:
        return True

    # Vocative of known Polish female name ending with -o or -u
    if clean.endswith("o") and len(clean) >= 4:
        stem = clean[:-1] + "a"
        if stem in POLISH_FEMALE_NAMES:
            return True
    if clean.endswith("u") and len(clean) >= 4:
        stem = clean[:-1] + "a"
        if stem in POLISH_FEMALE_NAMES:
            return True

    return False

def to_polish_female_vocative(name: str) -> str:
    """
    Converts a nominative Polish female name ending in -a into its correct vocative (wołacz) form:
    - Diminutives/hypocoristics on -sia, -cia, -nia, -la -> -u (Kasia -> Kasiu, Basia -> Basiu, Ania -> Aniu, Ola -> Olu, Zosia -> Zosiu)
    - Standard female names on -a -> -o (Monika -> Moniko, Anna -> Anno, Maria -> Mario, Katarzyna -> Katarzyno, Zofia -> Zofio)
    Only transforms recognized Polish female names from POLISH_FEMALE_NAMES.
    Non-names, interjections ('Ała!'), and foreign names without Polish vocative tradition remain unchanged.
    Preserves capitalization.
    """
    if not name:
        return name
    clean = name.strip()
    c_lower = clean.lower()
    if c_lower not in POLISH_FEMALE_NAMES:
        return clean
    if not c_lower.endswith("a") or c_lower in MALE_EXCEPTIONS_ON_A:
        return clean

    if any(c_lower.endswith(e) for e in ("kasia", "basia", "asia", "ania", "zosia", "marysia", "gosia", "madzia", "ola")):
        voc = clean[:-1] + ("u" if c_lower.endswith(("sia", "cia", "nia", "ola")) else "o")
        return voc

    # Default female name vocative on -a -> -o
    return clean[:-1] + ("O" if clean[-1].isupper() else "o")

def is_generic_actor_or_category(name: str) -> bool:
    """
    Returns True if the string is a generic grammatical category, placeholder,
    or descriptive label (e.g. 'mężczyzna', 'kobieta', 'grupa_kobiet', 'brak', 'narrator')
    rather than a real named character.
    """
    if not name:
        return True
    clean = extract_clean_speaker_name(name).strip().lower()
    return clean in GENERIC_CATEGORY_TAGS

def extract_clean_speaker_name(name: str) -> str:
    """
    Sanitizes ASS speaker names by stripping style overrides, parenthetical notes,
    and trailing context indicators (e.g. 'Girl\\Italic' -> 'Girl', 'Hebichika (Flashback)' -> 'Hebichika').
    """
    if not name:
        return ""
    # Strip ASS style suffix (e.g. \Italic, /Italic, \Default, \Narration)
    clean = re.split(r"[\\\/]", str(name))[0].strip()
    # Strip parenthetical or bracketed additions (e.g. (Flashback), [Off-screen], (young))
    clean = re.sub(r"[\(\[].*?[\)\]]", "", clean).strip()
    return clean


def is_polish_adjective(word: str) -> bool:
    w = word.lower().strip()
    if len(w) < 4:
        return False

    # Explicit exclusion of common Japanese names ending in -ki, -gi, -na
    # (e.g. Suzuki, Sasaki, Kawasaki, Miyazaki, Todoroki, Tanuki, Shizuku, Shina, etc.)
    if any(w.endswith(jp_end) for jp_end in ("saki", "zuki", "zaki", "roki", "nuki", "buki", "muki", "tuki", "yuki", "yaki", "seki", "deki", "heki", "kiki", "giki")):
        return False

    # Polish feminine nouns ending in -yna, -ina, -anka, -arka, -anna (e.g. gilotyna, dziewczyna, maszyna, cytryna)
    if w.endswith(("yna", "ina", "anka", "arka", "anna", "otta", "etta")):
        return False

    # Exclusion of common nouns ending in -na, -ta, -ka, -ga
    if w in {"kobieta", "dziewczyna", "pani", "chata", "brama", "tarcza", "lanca", "rana", "scena", "wojna", "korona", "strona", "ochrona", "obrona", "wrona", "rzeka", "książka", "ręka", "nauka", "matka", "córka", "dróżka", "papuga", "waga", "droga", "flaga", "saga", "manga", "planeta", "rakieta", "flota", "armata", "herbata", "gazeta"}:
        return False

    # Polish base adjectives
    BASE_ADJECTIVES = {
        "czerwony", "czerwona", "czerwone", "biały", "biała", "białe", "czarny", "czarna", "czarne",
        "złoty", "złota", "złote", "srebrny", "srebrna", "srebrne", "zielony", "zielona", "zielone",
        "święty", "święta", "święte", "cichy", "cicha", "ciche", "krwawy", "krwawa", "krwawe",
        "mroczny", "mroczna", "mroczne", "jasny", "jasna", "jasne", "ciemny", "ciemna", "ciemne",
        "młody", "młoda", "młode", "stary", "stara", "stare", "nowy", "nowa", "nowe",
        "dobry", "dobra", "dobre", "zły", "zła", "złe", "szalony", "szalona", "szalone",
        "dziki", "dzika", "dzike", "wolny", "wolna", "wolne", "żywy", "żywa", "żywe",
        "martwy", "martwa", "martwe", "zimny", "zimna", "zimne", "gorący", "gorąca", "gorące",
        "prosty", "prosta", "proste", "gęsty", "gęsta", "gęste", "pusty", "pusta", "puste",
        "czysty", "czysta", "czyste", "nieśmiertelny", "nieśmiertelna", "nieśmiertelne"
    }
    if w in BASE_ADJECTIVES:
        return True

    # Polish adjective and adjectival participle endings
    ADJ_ENDINGS = (
        "ski", "ska", "skie", "cki", "cka", "ckie", "dzki", "dzka", "dzkie",
        "owy", "owa", "owe", "asty", "asta", "aste", "isty", "ista", "iste",
        "liwy", "liwa", "liwe", "szy", "sza", "sze", "czy", "cza", "cze",
        "alny", "alna", "alne", "elny", "elna", "elne", "olny", "olna", "olne",
        "arny", "arna", "arne", "erny", "erna", "erne", "yczny", "yczna", "yczne",
        "iczny", "iczna", "iczne", "owny", "owna", "owne", "tywny", "tywna", "tywne",
        "ienny", "ienna", "ienne", "enny", "enna", "enne",
        # Active adjectival participles (e.g. płonący, śpiący, latający, milczący)
        "ący", "ąca", "ące",
        # Qualitative, diminutive, and expressive adjective suffixes
        "aty", "ata", "ate", "ity", "ita", "ite",
        "utki", "utka", "utkie", "eńki", "eńka", "eńkie",
        "owaty", "owata", "owate", "iasty", "iasta", "iaste"
    )
    if any(w.endswith(end) for end in ADJ_ENDINGS):
        return True

    # Root adjectives ending in -ki, -gi
    ADJ_ROOTS_ON_KI_GI = {"wielk", "dzik", "krótk", "szyb", "lekk", "ciężk", "miękk", "gładk", "wąsk", "szerok", "wysok", "nisk", "dalek", "blisk", "głębok", "płytk", "gorzk", "słodk", "cienk", "drog", "ubog", "sroga", "tęga", "błoga"}
    if any(w.startswith(root) for root in ADJ_ROOTS_ON_KI_GI) and w.endswith(("i", "y", "a", "e")):
        return True

    return False



def generate_polish_adjective_declension(adj: str, gender: Optional[str] = None, is_animate: bool = True) -> Dict[str, str]:
    w = adj.strip()
    if not w:
        return {}
    w_l = w.lower()
    g_upper = (gender or "").strip().upper()

    # 1. Feminine adjective on -a
    if w_l.endswith("a") or g_upper in ("FEMALE", "KOBIETA", "ŻEŃSKI", "ŻEŃSKA"):
        stem = w[:-1] if w_l.endswith("a") else w
        suffix_d = "iej" if stem.lower().endswith(("k", "g")) and not stem.lower().endswith("i") else "ej"
        return {
            "M": w,
            "D": stem + suffix_d,
            "C": stem + suffix_d,
            "B": stem + "ą",
            "N": stem + "ą",
            "Ms": stem + suffix_d,
            "W": w
        }

    # 2. Neuter adjective on -e
    if w_l.endswith("e") or g_upper in ("NEUTER", "NIJAKI"):
        stem = w[:-1] if w_l.endswith("e") else w
        n_ms = stem + "im" if stem.lower().endswith(("k", "g")) else (stem[:-1] + "im" if stem.lower().endswith("i") else stem + "ym")
        return {
            "M": w,
            "D": stem + "ego",
            "C": stem + "emu",
            "B": w,
            "N": n_ms,
            "Ms": n_ms,
            "W": w
        }

    # 3. Masculine adjective on -y / -i
    if w_l.endswith(("y", "i")) or g_upper in ("MALE", "MĘŻCZYZNA", "MĘSKI", "MĘSKA"):
        stem = w[:-1]
        last_c = stem[-1].lower() if stem else ""
        if w_l.endswith("i"):
            d_case = stem + "ego" if stem.lower().endswith("i") else stem + "iego"
            c_case = stem + "emu" if stem.lower().endswith("i") else stem + "iemu"
            n_ms = stem + "m" if stem.lower().endswith("i") else stem + "im"
        else:
            d_case = stem + "ego"
            c_case = stem + "emu"
            n_ms = stem + "im" if last_c in ("k", "g") else stem + "ym"
        b_case = d_case if is_animate else w
        return {
            "M": w,
            "D": d_case,
            "C": c_case,
            "B": b_case,
            "N": n_ms,
            "Ms": n_ms,
            "W": w
        }

    return {"M": w, "D": w, "C": w, "B": w, "N": w, "Ms": w, "W": w}


KNOWN_HEAD_NOUN_DECLENSIONS = {
    "zakon": {"M": "Zakon", "D": "Zakonu", "C": "Zakonowi", "B": "Zakon", "N": "Zakonem", "Ms": "Zakonie", "W": "Zakonie"},
    "miecz": {"M": "Miecz", "D": "Miecza", "C": "Mieczowi", "B": "Miecz", "N": "Mieczem", "Ms": "Mieczu", "W": "Mieczu"},
    "księga": {"M": "Księga", "D": "Księgi", "C": "Księdze", "B": "Księgę", "N": "Księgą", "Ms": "Księdze", "W": "Księgo"},
    "dolina": {"M": "Dolina", "D": "Doliny", "C": "Dolinie", "B": "Dolinę", "N": "Doliną", "Ms": "Dolinie", "W": "Dolino"},
    "zamek": {"M": "Zamek", "D": "Zamku", "C": "Zamkowi", "B": "Zamek", "N": "Zamkiem", "Ms": "Zamku", "W": "Zamku"},
    "lanca": {"M": "Lanca", "D": "Lancy", "C": "Lancy", "B": "Lancę", "N": "Lancą", "Ms": "Lancy", "W": "Lanco"},
    "tarcza": {"M": "Tarcza", "D": "Tarczy", "C": "Tarczy", "B": "Tarczę", "N": "Tarczą", "Ms": "Tarczy", "W": "Tarczo"},
    "pakt": {"M": "Pakt", "D": "Paktu", "C": "Paktowi", "B": "Pakt", "N": "Paktem", "Ms": "Pakcie", "W": "Pakcie"},
    "przymierze": {"M": "Przymierze", "D": "Przymierza", "C": "Przymierzu", "B": "Przymierze", "N": "Przymierzem", "Ms": "Przymierzu", "W": "Przymierze"},
    "amulet": {"M": "Amulet", "D": "Amuletu", "C": "Amuletowi", "B": "Amulet", "N": "Amuletem", "Ms": "Amuletu", "W": "Amuletu"},
    "zwój": {"M": "Zwój", "D": "Zwoju", "C": "Zwojowi", "B": "Zwój", "N": "Zwojem", "Ms": "Zwoju", "W": "Zwoju"},
    "kamień": {"M": "Kamień", "D": "Kamienia", "C": "Kamieniowi", "B": "Kamień", "N": "Kamieniem", "Ms": "Kamieniu", "W": "Kamieniu"},
    "drzewo": {"M": "Drzewo", "D": "Drzewa", "C": "Drzewu", "B": "Drzewo", "N": "Drzewem", "Ms": "Drzewie", "W": "Drzewo"},
    "wieża": {"M": "Wieża", "D": "Wieży", "C": "Wieży", "B": "Wieżę", "N": "Wieżą", "Ms": "Wieży", "W": "Wieżo"},
    "brama": {"M": "Brama", "D": "Bramy", "C": "Bramie", "B": "Bramę", "N": "Bramą", "Ms": "Bramie", "W": "Bramo"},
    "tron": {"M": "Tron", "D": "Tronu", "C": "Tronowi", "B": "Tron", "N": "Tronem", "Ms": "Tronie", "W": "Tronie"},
    "sztylet": {"M": "Sztylet", "D": "Sztyletu", "C": "Sztyletowi", "B": "Sztylet", "N": "Sztyletem", "Ms": "Sztylecie", "W": "Sztylecie"},
    "młot": {"M": "Młot", "D": "Młota", "C": "Młotowi", "B": "Młot", "N": "Młotem", "Ms": "Młocie", "W": "Młocie"},
    "kosa": {"M": "Kosa", "D": "Kosy", "C": "Kosie", "B": "Kosę", "N": "Kosą", "Ms": "Kosie", "W": "Koso"},
    "hełm": {"M": "Hełm", "D": "Hełmu", "C": "Hełmowi", "B": "Hełm", "N": "Hełmem", "Ms": "Hełmie", "W": "Hełmie"},
    "zbroja": {"M": "Zbroja", "D": "Zbroi", "C": "Zbroi", "B": "Zbroję", "N": "Zbroją", "Ms": "Zbroi", "W": "Zbrojo"},
    "gniew": {"M": "Gniew", "D": "Gniewu", "C": "Gniewowi", "B": "Gniew", "N": "Gniewem", "Ms": "Gniewie", "W": "Gniewie"},
    # Epithets, Titles & Anime Classes (Manga Canon Supreme)
    "władca": {"M": "Władca", "D": "Władcy", "C": "Władcy", "B": "Władcę", "N": "Władcą", "Ms": "Władcy", "W": "Władco"},
    "władczyni": {"M": "Władczyni", "D": "Władczyni", "C": "Władczyni", "B": "Władczynię", "N": "Władczynią", "Ms": "Władczyni", "W": "Władczyni"},
    "demon": {"M": "Demon", "D": "Demona", "C": "Demonowi", "B": "Demona", "N": "Demonem", "Ms": "Demonie", "W": "Demonie"},
    "demonica": {"M": "Demonica", "D": "Demonicy", "C": "Demonicy", "B": "Demonicę", "N": "Demonicą", "Ms": "Demonicy", "W": "Demonico"},
    "mistrz": {"M": "Mistrz", "D": "Mistrza", "C": "Mistrzowi", "B": "Mistrza", "N": "Mistrzem", "Ms": "Mistrzu", "W": "Mistrzu"},
    "mistrzyni": {"M": "Mistrzyni", "D": "Mistrzyni", "C": "Mistrzyni", "B": "Mistrzynię", "N": "Mistrzynią", "Ms": "Mistrzyni", "W": "Mistrzyni"},
    "pani": {"M": "Pani", "D": "Pani", "C": "Pani", "B": "Panią", "N": "Panią", "Ms": "Pani", "W": "Pani"},
    "pan": {"M": "Pan", "D": "Pana", "C": "Panu", "B": "Pana", "N": "Panem", "Ms": "Panu", "W": "Panie"},
    "lord": {"M": "Lord", "D": "Lorda", "C": "Lordowi", "B": "Lorda", "N": "Lordem", "Ms": "Lordzie", "W": "Lordzie"},
    "bóg": {"M": "Bóg", "D": "Boga", "C": "Bogu", "B": "Boga", "N": "Bogiem", "Ms": "Bogu", "W": "Boże"},
    "bogini": {"M": "Bogini", "D": "Bogini", "C": "Bogini", "B": "Boginię", "N": "Boginią", "Ms": "Bogini", "W": "Bogini"},
    "rycerz": {"M": "Rycerz", "D": "Rycerza", "C": "Rycerzowi", "B": "Rycerza", "N": "Rycerzem", "Ms": "Rycerzu", "W": "Rycerzu"},
    "generał": {"M": "Generał", "D": "Generała", "C": "Generałowi", "B": "Generała", "N": "Generałem", "Ms": "Generale", "W": "Generale"},
    "dowódca": {"M": "Dowódca", "D": "Dowódcy", "C": "Dowódcy", "B": "Dowódcę", "N": "Dowódcą", "Ms": "Dowódcy", "W": "Dowódco"},
    "zabójca": {"M": "Zabójca", "D": "Zabójcy", "C": "Zabójcy", "B": "Zabójcę", "N": "Zabójcą", "Ms": "Zabójcy", "W": "Zabójco"},
    "obrońca": {"M": "Obrońca", "D": "Obrońcy", "C": "Obrońcy", "B": "Obrońcę", "N": "Obrońcą", "Ms": "Obrońcy", "W": "Obrońco"},
    "łowca": {"M": "Łowca", "D": "Łowcy", "C": "Łowcy", "B": "Łowcę", "N": "Łowcą", "Ms": "Łowcy", "W": "Łowco"},
    "strażnik": {"M": "Strażnik", "D": "Strażnika", "C": "Strażnikowi", "B": "Strażnika", "N": "Strażnikiem", "Ms": "Strażniku", "W": "Strażniku"},
    "król": {"M": "Król", "D": "Króla", "C": "Królowi", "B": "Króla", "N": "Królem", "Ms": "Królu", "W": "Królu"},
    "królowa": {"M": "Królowa", "D": "Królowej", "C": "Królowej", "B": "Królową", "N": "Królową", "Ms": "Królowej", "W": "Królowo"},
    "książę": {"M": "Książę", "D": "Księcia", "C": "Księciu", "B": "Księcia", "N": "Księciem", "Ms": "Księciu", "W": "Książę"},
    "księżniczka": {"M": "Księżniczka", "D": "Księżniczki", "C": "Księżniczce", "B": "Księżniczkę", "N": "Księżniczką", "Ms": "Księżniczce", "W": "Księżniczko"},
    "cesarz": {"M": "Cesarz", "D": "Cesarza", "C": "Cesarzowi", "B": "Cesarza", "N": "Cesarzem", "Ms": "Cesarzu", "W": "Cesarzu"},
    "cesarzowa": {"M": "Cesarzowa", "D": "Cesarzowej", "C": "Cesarzowej", "B": "Cesarzową", "N": "Cesarzową", "Ms": "Cesarzowej", "W": "Cesarzowo"},
    "mag": {"M": "Mag", "D": "Maga", "C": "Magowi", "B": "Maga", "N": "Magiem", "Ms": "Magu", "W": "Magu"},
    "czarnoksiężnik": {"M": "Czarnoksiężnik", "D": "Czarnoksiężnika", "C": "Czarnoksiężnikowi", "B": "Czarnoksiężnika", "N": "Czarnoksiężnikiem", "Ms": "Czarnoksiężniku", "W": "Czarnoksiężniku"},
    "kapłan": {"M": "Kapłan", "D": "Kapłana", "C": "Kapłanowi", "B": "Kapłana", "N": "Kapłanem", "Ms": "Kapłanie", "W": "Kapłanie"},
    "kapłanka": {"M": "Kapłanka", "D": "Kapłanki", "C": "Kapłance", "B": "Kapłankę", "N": "Kapłanką", "Ms": "Kapłance", "W": "Kapłanko"},
    "wojownik": {"M": "Wojownik", "D": "Wojownika", "C": "Wojownikowi", "B": "Wojownika", "N": "Wojownikiem", "Ms": "Wojowniku", "W": "Wojowniku"},
    "wojowniczka": {"M": "Wojowniczka", "D": "Wojowniczki", "C": "Wojowniczce", "B": "Wojowniczkę", "N": "Wojowniczką", "Ms": "Wojowniczce", "W": "Wojowniczko"},
    "bohater": {"M": "Bohater", "D": "Bohatera", "C": "Bohaterowi", "B": "Bohatera", "N": "Bohaterem", "Ms": "Bohaterze", "W": "Bohaterze"},
    "bohaterka": {"M": "Bohaterka", "D": "Bohaterki", "C": "Bohaterce", "B": "Bohaterkę", "N": "Bohaterką", "Ms": "Bohaterce", "W": "Bohaterko"},
    "cień": {"M": "Cień", "D": "Cienia", "C": "Cieniowi", "B": "Cień", "N": "Cieniem", "Ms": "Cieniu", "W": "Cieniu"},
    "płomień": {"M": "Płomień", "D": "Płomienia", "C": "Płomieniowi", "B": "Płomień", "N": "Płomieniem", "Ms": "Płomieniu", "W": "Płomieniu"},
    "krew": {"M": "Krew", "D": "Krwi", "C": "Krwi", "B": "Krew", "N": "Krwią", "Ms": "Krwi", "W": "Krwi"},
    "serce": {"M": "Serce", "D": "Serca", "C": "Sercu", "B": "Serce", "N": "Sercem", "Ms": "Sercu", "W": "Serce"},
    "oko": {"M": "Oko", "D": "Oka", "C": "Oku", "B": "Oko", "N": "Okiem", "Ms": "Oku", "W": "Oko"},
    "ręka": {"M": "Ręka", "D": "Ręki", "C": "Ręce", "B": "Rękę", "N": "Ręką", "Ms": "Ręce", "W": "Ręko"},
    "pierścień": {"M": "Pierścień", "D": "Pierścienia", "C": "Pierścieniowi", "B": "Pierścień", "N": "Pierścieniem", "Ms": "Pierścieniu", "W": "Pierścieniu"},
    "korona": {"M": "Korona", "D": "Korony", "C": "Koronie", "B": "Koronę", "N": "Koroną", "Ms": "Koronie", "W": "Korono"},
    "pieczęć": {"M": "Pieczęć", "D": "Pieczęci", "C": "Pieczęci", "B": "Pieczęć", "N": "Pieczęcią", "Ms": "Pieczęci", "W": "Pieczęci"},
    "zwierciadło": {"M": "Zwierciadło", "D": "Zwierciadła", "C": "Zwierciadłu", "B": "Zwierciadło", "N": "Zwierciadłem", "Ms": "Zwierciadle", "W": "Zwierciadło"},
    "kielich": {"M": "Kielich", "D": "Kielicha", "C": "Kielichowi", "B": "Kielich", "N": "Kielichem", "Ms": "Kielichu", "W": "Kielichu"},
    "światło": {"M": "Światło", "D": "Światła", "C": "Światłu", "B": "Światło", "N": "Światłem", "Ms": "Świetle", "W": "Światło"},
    "wrota": {"M": "Wrota", "D": "Wrót", "C": "Wrotom", "B": "Wrota", "N": "Wrotami", "Ms": "Wrotach", "W": "Wrota"},
    "twierdza": {"M": "Twierdza", "D": "Twierdzy", "C": "Twierdzy", "B": "Twierdzę", "N": "Twierdzą", "Ms": "Twierdzy", "W": "Twierdzo"},
    "świątynia": {"M": "Świątynia", "D": "Świątyni", "C": "Świątyni", "B": "Świątynię", "N": "Świątynią", "Ms": "Świątyni", "W": "Świątynio"},
    "duch": {"M": "Duch", "D": "Ducha", "C": "Duchowi", "B": "Ducha", "N": "Duchem", "Ms": "Duchu", "W": "Duchu"},
    "ród": {"M": "Ród", "D": "Rodu", "C": "Rodowi", "B": "Ród", "N": "Rodem", "Ms": "Rodzie", "W": "Rodzie"},
    "znak": {"M": "Znak", "D": "Znaku", "C": "Znakowi", "B": "Znak", "N": "Znakiem", "Ms": "Znaku", "W": "Znaku"},
    "łuk": {"M": "Łuk", "D": "Łuku", "C": "Łukowi", "B": "Łuk", "N": "Łukiem", "Ms": "Łuku", "W": "Łuku"},
    "strzała": {"M": "Strzała", "D": "Strzały", "C": "Strzale", "B": "Strzałę", "N": "Strzałą", "Ms": "Strzale", "W": "Strzało"},
    "różdżka": {"M": "Różdżka", "D": "Różdżki", "C": "Różdżce", "B": "Różdżkę", "N": "Różdżką", "Ms": "Różdżce", "W": "Różdżko"},
    "kodeks": {"M": "Kodeks", "D": "Kodeksu", "C": "Kodeksowi", "B": "Kodeks", "N": "Kodeksem", "Ms": "Kodeksie", "W": "Kodeksie"},
    "opowieść": {"M": "Opowieść", "D": "Opowieści", "C": "Opowieści", "B": "Opowieść", "N": "Opowieścią", "Ms": "Opowieści", "W": "Opowieści"},
    "legenda": {"M": "Legenda", "D": "Legendy", "C": "Legendzie", "B": "Legendę", "N": "Legendą", "Ms": "Legendzie", "W": "Legendo"},
    "pieśń": {"M": "Pieśń", "D": "Pieśni", "C": "Pieśni", "B": "Pieśń", "N": "Pieśnią", "Ms": "Pieśni", "W": "Pieśni"},
    "hymn": {"M": "Hymn", "D": "Hymnu", "C": "Hymnowi", "B": "Hymn", "N": "Hymnem", "Ms": "Hymnie", "W": "Hymnie"},
    "kronika": {"M": "Kronika", "D": "Kroniki", "C": "Kronice", "B": "Kronikę", "N": "Kroniką", "Ms": "Kronice", "W": "Kroniko"},
    "droga": {"M": "Droga", "D": "Drogi", "C": "Drodze", "B": "Drogę", "N": "Drogą", "Ms": "Drodze", "W": "Drogo"},
    "szlak": {"M": "Szlak", "D": "Szlaku", "C": "Szlakowi", "B": "Szlak", "N": "Szlakiem", "Ms": "Szlaku", "W": "Szlaku"},
    "most": {"M": "Most", "D": "Mostu", "C": "Mostowi", "B": "Most", "N": "Mostem", "Ms": "Moście", "W": "Moście"},
    "rzeka": {"M": "Rzeka", "D": "Rzeki", "C": "Rzece", "B": "Rzekę", "N": "Rzeką", "Ms": "Rzece", "W": "Rzeko"},
    "jezioro": {"M": "Jezioro", "D": "Jeziora", "C": "Jezioru", "B": "Jezioro", "N": "Jeziorem", "Ms": "Jeziorze", "W": "Jezioro"},
    "morze": {"M": "Morze", "D": "Morza", "C": "Morzu", "B": "Morze", "N": "Morzem", "Ms": "Morzu", "W": "Morze"},
    "góra": {"M": "Góra", "D": "Góry", "C": "Górze", "B": "Górę", "N": "Górą", "Ms": "Górze", "W": "Góro"},
    "pustynia": {"M": "Pustynia", "D": "Pustyni", "C": "Pustyni", "B": "Pustynię", "N": "Pustynią", "Ms": "Pustyni", "W": "Pustynio"},
    "zemsta": {"M": "Zemsta", "D": "Zemsty", "C": "Zemście", "B": "Zemstę", "N": "Zemstą", "Ms": "Zemście", "W": "Zemsto"},
    "klątwa": {"M": "Klątwa", "D": "Klątwy", "C": "Klątwie", "B": "Klątwę", "N": "Klątwą", "Ms": "Klątwie", "W": "Klątwo"},
    "bunt": {"M": "Bunt", "D": "Buntu", "C": "Buntowi", "B": "Bunt", "N": "Buntem", "Ms": "Buncie", "W": "Buncie"},
    "upadek": {"M": "Upadek", "D": "Upadku", "C": "Upadkowi", "B": "Upadek", "N": "Upadkiem", "Ms": "Upadku", "W": "Upadku"},
    "powrót": {"M": "Powrót", "D": "Powrotu", "C": "Powrotowi", "B": "Powrót", "N": "Powrotem", "Ms": "Powrocie", "W": "Powrocie"},
    "narodziny": {"M": "Narodziny", "D": "Narodzin", "C": "Narodzinom", "B": "Narodziny", "N": "Narodzinami", "Ms": "Narodzinach", "W": "Narodziny"},
    "koniec": {"M": "Koniec", "D": "Końca", "C": "Końcowi", "B": "Koniec", "N": "Końcem", "Ms": "Końcu", "W": "Końcu"},
    "początek": {"M": "Początek", "D": "Początku", "C": "Początkowi", "B": "Początek", "N": "Początkiem", "Ms": "Początku", "W": "Początku"},
    "córka": {"M": "Córka", "D": "Córki", "C": "Córce", "B": "Córkę", "N": "Córką", "Ms": "Córce", "W": "Córko"},
    "syn": {"M": "Syn", "D": "Syna", "C": "Synowi", "B": "Syna", "N": "Synem", "Ms": "Synu", "W": "Synu"},
    "matka": {"M": "Matka", "D": "Matki", "C": "Matce", "B": "Matkę", "N": "Matką", "Ms": "Matce", "W": "Matko"},
    "ojciec": {"M": "Ojciec", "D": "Ojca", "C": "Ojcu", "B": "Ojca", "N": "Ojcem", "Ms": "Ojcu", "W": "Ojcze"},
    "brat": {"M": "Brat", "D": "Brata", "C": "Bratu", "B": "Brata", "N": "Bratem", "Ms": "Bracie", "W": "Bracie"},
    "siostra": {"M": "Siostra", "D": "Siostry", "C": "Siostrze", "B": "Siostrę", "N": "Siostrą", "Ms": "Siostrze", "W": "Siostro"},
    "arcykapłan": {"M": "Arcykapłan", "D": "Arcykapłana", "C": "Arcykapłanowi", "B": "Arcykapłana", "N": "Arcykapłanem", "Ms": "Arcykapłanie", "W": "Arcykapłanie"},
    "arcymag": {"M": "Arcymag", "D": "Arcymaga", "C": "Arcymagowi", "B": "Arcymaga", "N": "Arcymagiem", "Ms": "Arcymagu", "W": "Arcymagu"},
    "szaman": {"M": "Szaman", "D": "Szamana", "C": "Szamanowi", "B": "Szamana", "N": "Szamanem", "Ms": "Szamanie", "W": "Szamanie"},
    "czarownik": {"M": "Czarownik", "D": "Czarownika", "C": "Czarownikowi", "B": "Czarownika", "N": "Czarownikiem", "Ms": "Czarowniku", "W": "Czarowniku"},
    "czarownica": {"M": "Czarownica", "D": "Czarownicy", "C": "Czarownicy", "B": "Czarownicę", "N": "Czarownicą", "Ms": "Czarownicy", "W": "Czarownico"},
    "bestia": {"M": "Bestia", "D": "Bestii", "C": "Bestii", "B": "Bestię", "N": "Bestią", "Ms": "Bestii", "W": "Bestio"},
    "potwór": {"M": "Potwór", "D": "Potwora", "C": "Potworowi", "B": "Potwora", "N": "Potworem", "Ms": "Potworze", "W": "Potworze"},
    "smok": {"M": "Smok", "D": "Smoka", "C": "Smokowi", "B": "Smoka", "N": "Smokiem", "Ms": "Smoku", "W": "Smoku"},
    "bóstwo": {"M": "Bóstwo", "D": "Bóstwa", "C": "Bóstwu", "B": "Bóstwo", "N": "Bóstwem", "Ms": "Bóstwie", "W": "Bóstwo"},
    "anioł": {"M": "Anioł", "D": "Anioła", "C": "Aniołowi", "B": "Anioła", "N": "Aniołem", "Ms": "Aniele", "W": "Aniele"},
    "wampir": {"M": "Wampir", "D": "Wampira", "C": "Wampirowi", "B": "Wampira", "N": "Wampirem", "Ms": "Wampirze", "W": "Wampirze"},
    "widmo": {"M": "Widmo", "D": "Widma", "C": "Widmu", "B": "Widmo", "N": "Widmem", "Ms": "Widmie", "W": "Widmo"},
    "zjawa": {"M": "Zjawa", "D": "Zjawy", "C": "Zjawie", "B": "Zjawę", "N": "Zjawą", "Ms": "Zjawie", "W": "Zjawo"},
    "kapitan": {'M': 'Kapitan', 'D': 'Kapitana', 'C': 'Kapitanowi', 'B': 'Kapitana', 'N': 'Kapitanem', 'Ms': 'Kapitanie', 'W': 'Kapitanie'},
    "major": {'M': 'Major', 'D': 'Majora', 'C': 'Majorowi', 'B': 'Majora', 'N': 'Majorem', 'Ms': 'Majorze', 'W': 'Majorze'},
    "pułkownik": {'M': 'Pułkownik', 'D': 'Pułkownika', 'C': 'Pułkownikowi', 'B': 'Pułkownika', 'N': 'Pułkownikiem', 'Ms': 'Pułkowniku', 'W': 'Pułkowniku'},
    "porucznik": {'M': 'Porucznik', 'D': 'Porucznika', 'C': 'Porucznikowi', 'B': 'Porucznika', 'N': 'Porucznikiem', 'Ms': 'Poruczniku', 'W': 'Poruczniku'},
    "sierżant": {'M': 'Sierżant', 'D': 'Sierżanta', 'C': 'Sierżantowi', 'B': 'Sierżanta', 'N': 'Sierżantem', 'Ms': 'Sierżancie', 'W': 'Sierżancie'},
    "kapral": {'M': 'Kapral', 'D': 'Kaprala', 'C': 'Kapralowi', 'B': 'Kaprala', 'N': 'Kapralem', 'Ms': 'Kapralu', 'W': 'Kapralu'},
    "admirał": {'M': 'Admirał', 'D': 'Admirała', 'C': 'Admirałowi', 'B': 'Admirała', 'N': 'Admirałem', 'Ms': 'Admirale', 'W': 'Admirale'},
    "hetman": {'M': 'Hetman', 'D': 'Hetmana', 'C': 'Hetmanowi', 'B': 'Hetmana', 'N': 'Hetmanem', 'Ms': 'Hetmanie', 'W': 'Hetmanie'},
    "przywódca": {'M': 'Przywódca', 'D': 'Przywódcy', 'C': 'Przywódcy', 'B': 'Przywódcę', 'N': 'Przywódcą', 'Ms': 'Przywódcy', 'W': 'Przywódco'},
    "przywódczyni": {'M': 'Przywódczyni', 'D': 'Przywódczyni', 'C': 'Przywódczyni', 'B': 'Przywódczynię', 'N': 'Przywódczynią', 'Ms': 'Przywódczyni', 'W': 'Przywódczyni'},
    "wódz": {'M': 'Wódz', 'D': 'Wodza', 'C': 'Wodzowi', 'B': 'Wodza', 'N': 'Wodzem', 'Ms': 'Wodzu', 'W': 'Wodzu'},
    "watażka": {'M': 'Watażka', 'D': 'Watażki', 'C': 'Watażce', 'B': 'Watażkę', 'N': 'Watażką', 'Ms': 'Watażce', 'W': 'Watażko'},
    "czempion": {'M': 'Czempion', 'D': 'Czempiona', 'C': 'Czempionowi', 'B': 'Czempiona', 'N': 'Czempionem', 'Ms': 'Czempionie', 'W': 'Czempionie'},
    "czempionka": {'M': 'Czempionka', 'D': 'Czempionki', 'C': 'Czempionce', 'B': 'Czempionkę', 'N': 'Czempionką', 'Ms': 'Czempionce', 'W': 'Czempionko'},
    "oficer": {'M': 'Oficer', 'D': 'Oficera', 'C': 'Oficerowi', 'B': 'Oficera', 'N': 'Oficerem', 'Ms': 'Oficerze', 'W': 'Oficerze'},
    "żołnierz": {'M': 'Żołnierz', 'D': 'Żołnierza', 'C': 'Żołnierzowi', 'B': 'Żołnierza', 'N': 'Żołnierzem', 'Ms': 'Żołnierzu', 'W': 'Żołnierzu'},
    "woj": {'M': 'Woj', 'D': 'Woja', 'C': 'Wojowi', 'B': 'Woja', 'N': 'Wojem', 'Ms': 'Woju', 'W': 'Woju'},
    "najemnik": {'M': 'Najemnik', 'D': 'Najemnika', 'C': 'Najemnikowi', 'B': 'Najemnika', 'N': 'Najemnikiem', 'Ms': 'Najemniku', 'W': 'Najemniku'},
    "paladyn": {'M': 'Paladyn', 'D': 'Paladyna', 'C': 'Paladynowi', 'B': 'Paladyna', 'N': 'Paladynem', 'Ms': 'Paladynie', 'W': 'Paladynie'},
    "krzyżowiec": {'M': 'Krzyżowiec', 'D': 'Krzyżowca', 'C': 'Krzyżowcowi', 'B': 'Krzyżowca', 'N': 'Krzyżowcem', 'Ms': 'Krzyżowcu', 'W': 'Krzyżowcu'},
    "straż": {'M': 'Straż', 'D': 'Straży', 'C': 'Straży', 'B': 'Straż', 'N': 'Strażą', 'Ms': 'Straży', 'W': 'Straży'},
    "strażniczka": {'M': 'Strażniczka', 'D': 'Strażniczki', 'C': 'Strażniczce', 'B': 'Strażniczkę', 'N': 'Strażniczką', 'Ms': 'Strażniczce', 'W': 'Strażniczko'},
    "obrończyni": {'M': 'Obrończyni', 'D': 'Obrończyni', 'C': 'Obrończyni', 'B': 'Obrończynię', 'N': 'Obrończynią', 'Ms': 'Obrończyni', 'W': 'Obrończyni'},
    "łowczyni": {'M': 'Łowczyni', 'D': 'Łowczyni', 'C': 'Łowczyni', 'B': 'Łowczynię', 'N': 'Łowczynią', 'Ms': 'Łowczyni', 'W': 'Łowczyni'},
    "zabójczyni": {'M': 'Zabójczyni', 'D': 'Zabójczyni', 'C': 'Zabójczyni', 'B': 'Zabójczynię', 'N': 'Zabójczynią', 'Ms': 'Zabójczyni', 'W': 'Zabójczyni'},
    "zwiadowca": {'M': 'Zwiadowca', 'D': 'Zwiadowcy', 'C': 'Zwiadowcy', 'B': 'Zwiadowcę', 'N': 'Zwiadowcą', 'Ms': 'Zwiadowcy', 'W': 'Zwiadowco'},
    "tropiciel": {'M': 'Tropiciel', 'D': 'Tropiciela', 'C': 'Tropicielowi', 'B': 'Tropiciela', 'N': 'Tropicielem', 'Ms': 'Tropicielu', 'W': 'Tropicielu'},
    "barbarzyńca": {'M': 'Barbarzyńca', 'D': 'Barbarzyńcy', 'C': 'Barbarzyńcy', 'B': 'Barbarzyńcę', 'N': 'Barbarzyńcą', 'Ms': 'Barbarzyńcy', 'W': 'Barbarzyńco'},
    "namiestnik": {'M': 'Namiestnik', 'D': 'Namiestnika', 'C': 'Namiestnikowi', 'B': 'Namiestnika', 'N': 'Namiestnikiem', 'Ms': 'Namiestniku', 'W': 'Namiestniku'},
    "gubernator": {'M': 'Gubernator', 'D': 'Gubernatora', 'C': 'Gubernatorowi', 'B': 'Gubernatora', 'N': 'Gubernatorem', 'Ms': 'Gubernatorze', 'W': 'Gubernatorze'},
    "kanclerz": {'M': 'Kanclerz', 'D': 'Kanclerza', 'C': 'Kanclerzowi', 'B': 'Kanclerza', 'N': 'Kanclerzem', 'Ms': 'Kanclerzu', 'W': 'Kanclerzu'},
    "hrabia": {'M': 'Hrabia', 'D': 'Hrabiego', 'C': 'Hrabiemu', 'B': 'Hrabiego', 'N': 'Hrabią', 'Ms': 'Hrabim', 'W': 'Hrabio'},
    "hrabina": {'M': 'Hrabina', 'D': 'Hrabiny', 'C': 'Hrabinie', 'B': 'Hrabinę', 'N': 'Hrabiną', 'Ms': 'Hrabinie', 'W': 'Hrabino'},
    "margrabia": {'M': 'Margrabia', 'D': 'Margrabiego', 'C': 'Margrabiemu', 'B': 'Margrabiego', 'N': 'Margrabią', 'Ms': 'Margrabim', 'W': 'Margrabio'},
    "baron": {'M': 'Baron', 'D': 'Barona', 'C': 'Baronowi', 'B': 'Barona', 'N': 'Baronem', 'Ms': 'Baronie', 'W': 'Baronie'},
    "baronowa": {'M': 'Baronowa', 'D': 'Baronowej', 'C': 'Baronowej', 'B': 'Baronową', 'N': 'Baronową', 'Ms': 'Baronowej', 'W': 'Baronowo'},
    "suweren": {'M': 'Suweren', 'D': 'Suwerena', 'C': 'Suwerenowi', 'B': 'Suwerena', 'N': 'Suwerenem', 'Ms': 'Suwerenie', 'W': 'Suwerenie'},
    "wasal": {'M': 'Wasal', 'D': 'Wasala', 'C': 'Wasalowi', 'B': 'Wasala', 'N': 'Wasalem', 'Ms': 'Wasalu', 'W': 'Wasalu'},
    "dziedzic": {'M': 'Dziedzic', 'D': 'Dziedzica', 'C': 'Dziedzicowi', 'B': 'Dziedzica', 'N': 'Dziedzicem', 'Ms': 'Dziedzicu', 'W': 'Dziedzicu'},
    "dziedziczka": {'M': 'Dziedziczka', 'D': 'Dziedziczki', 'C': 'Dziedziczce', 'B': 'Dziedziczkę', 'N': 'Dziedziczką', 'Ms': 'Dziedziczce', 'W': 'Dziedziczko'},
    "czarodziej": {'M': 'Czarodziej', 'D': 'Czarodzieja', 'C': 'Czarodziejowi', 'B': 'Czarodzieja', 'N': 'Czarodziejem', 'Ms': 'Czarodzieju', 'W': 'Czarodzieju'},
    "czarodziejka": {'M': 'Czarodziejka', 'D': 'Czarodziejki', 'C': 'Czarodziejce', 'B': 'Czarodziejkę', 'N': 'Czarodziejką', 'Ms': 'Czarodziejce', 'W': 'Czarodziejko'},
    "czarnoksiężnica": {'M': 'Czarnoksiężnica', 'D': 'Czarnoksiężnicy', 'C': 'Czarnoksiężnicy', 'B': 'Czarnoksiężnicę', 'N': 'Czarnoksiężnicą', 'Ms': 'Czarnoksiężnicy', 'W': 'Czarnoksiężnico'},
    "uzdrowiciel": {'M': 'Uzdrowiciel', 'D': 'Uzdrowiciela', 'C': 'Uzdrowicielowi', 'B': 'Uzdrowiciela', 'N': 'Uzdrowicielem', 'Ms': 'Uzdrowicielu', 'W': 'Uzdrowicielu'},
    "uzdrowicielka": {'M': 'Uzdrowicielka', 'D': 'Uzdrowicielki', 'C': 'Uzdrowicielce', 'B': 'Uzdrowicielkę', 'N': 'Uzdrowicielką', 'Ms': 'Uzdrowicielce', 'W': 'Uzdrowicielko'},
    "alchemik": {'M': 'Alchemik', 'D': 'Alchemika', 'C': 'Alchemikowi', 'B': 'Alchemika', 'N': 'Alchemikiem', 'Ms': 'Alchemiku', 'W': 'Alchemiku'},
    "aptekarz": {'M': 'Aptekarz', 'D': 'Aptekarza', 'C': 'Aptekarzowi', 'B': 'Aptekarza', 'N': 'Aptekarzem', 'Ms': 'Aptekarzu', 'W': 'Aptekarzu'},
    "zielarz": {'M': 'Zielarz', 'D': 'Zielarza', 'C': 'Zielarzowi', 'B': 'Zielarza', 'N': 'Zielarzem', 'Ms': 'Zielarzu', 'W': 'Zielarzu'},
    "zielarka": {'M': 'Zielarka', 'D': 'Zielarki', 'C': 'Zielarce', 'B': 'Zielarkę', 'N': 'Zielarką', 'Ms': 'Zielarce', 'W': 'Zielarko'},
    "kowal": {'M': 'Kowal', 'D': 'Kowala', 'C': 'Kowalowi', 'B': 'Kowala', 'N': 'Kowalem', 'Ms': 'Kowalu', 'W': 'Kowalu'},
    "płatnerz": {'M': 'Płatnerz', 'D': 'Płatnerza', 'C': 'Płatnerzowi', 'B': 'Płatnerza', 'N': 'Płatnerzem', 'Ms': 'Płatnerzu', 'W': 'Płatnerzu'},
    "kupiec": {'M': 'Kupiec', 'D': 'Kupca', 'C': 'Kupcowi', 'B': 'Kupca', 'N': 'Kupcem', 'Ms': 'Kupcu', 'W': 'Kupcu'},
    "złodziej": {'M': 'Złodziej', 'D': 'Złodzieja', 'C': 'Złodziejowi', 'B': 'Złodzieja', 'N': 'Złodziejem', 'Ms': 'Złodzieju', 'W': 'Złodzieju'},
    "złodziejka": {'M': 'Złodziejka', 'D': 'Złodziejki', 'C': 'Złodziejce', 'B': 'Złodziejkę', 'N': 'Złodziejką', 'Ms': 'Złodziejce', 'W': 'Złodziejko'},
    "szpieg": {'M': 'Szpieg', 'D': 'Szpiega', 'C': 'Szpiegowi', 'B': 'Szpiega', 'N': 'Szpiegiem', 'Ms': 'Szpiegu', 'W': 'Szpiegu'},
    "uczeń": {'M': 'Uczeń', 'D': 'Ucznia', 'C': 'Uczniowi', 'B': 'Ucznia', 'N': 'Uczniem', 'Ms': 'Uczniu', 'W': 'Uczniu'},
    "uczennica": {'M': 'Uczennica', 'D': 'Uczennicy', 'C': 'Uczennicy', 'B': 'Uczennicę', 'N': 'Uczennicą', 'Ms': 'Uczennicy', 'W': 'Uczennico'},
    "nauczyciel": {'M': 'Nauczyciel', 'D': 'Nauczyciela', 'C': 'Nauczycielowi', 'B': 'Nauczyciela', 'N': 'Nauczycielem', 'Ms': 'Nauczycielu', 'W': 'Nauczycielu'},
    "nauczycielka": {'M': 'Nauczycielka', 'D': 'Nauczycielki', 'C': 'Nauczycielce', 'B': 'Nauczycielkę', 'N': 'Nauczycielką', 'Ms': 'Nauczycielce', 'W': 'Nauczycielko'},
    "sługa": {'M': 'Sługa', 'D': 'Sługi', 'C': 'Słudze', 'B': 'Sługę', 'N': 'Sługą', 'Ms': 'Słudze', 'W': 'Sługo'},
    "służąca": {'M': 'Służąca', 'D': 'Służącej', 'C': 'Służącej', 'B': 'Służącą', 'N': 'Służącą', 'Ms': 'Służącej', 'W': 'Służąca'},
    "kamerdyner": {'M': 'Kamerdyner', 'D': 'Kamerdynera', 'C': 'Kamerdynerowi', 'B': 'Kamerdynera', 'N': 'Kamerdynerem', 'Ms': 'Kamerdynerze', 'W': 'Kamerdynerze'},
    "opiekun": {'M': 'Opiekun', 'D': 'Opiekuna', 'C': 'Opiekunowi', 'B': 'Opiekuna', 'N': 'Opiekunem', 'Ms': 'Opiekunie', 'W': 'Opiekunie'},
    "opiekunka": {'M': 'Opiekunka', 'D': 'Opiekunki', 'C': 'Opiekunce', 'B': 'Opiekunkę', 'N': 'Opiekunką', 'Ms': 'Opiekunce', 'W': 'Opiekunko'},
    "prorok": {'M': 'Prorok', 'D': 'Proroka', 'C': 'Prorokowi', 'B': 'Proroka', 'N': 'Prorokiem', 'Ms': 'Proroku', 'W': 'Proroku'},
    "prorokini": {'M': 'Prorokini', 'D': 'Prorokini', 'C': 'Prorokini', 'B': 'Prorokinię', 'N': 'Prorokinią', 'Ms': 'Prorokini', 'W': 'Prorokini'},
    "wyrocznia": {'M': 'Wyrocznia', 'D': 'Wyroczni', 'C': 'Wyroczni', 'B': 'Wyrocznię', 'N': 'Wyrocznią', 'Ms': 'Wyroczni', 'W': 'Wyrocznio'},
    "mnich": {'M': 'Mnich', 'D': 'Mnicha', 'C': 'Mnichowi', 'B': 'Mnicha', 'N': 'Mnichem', 'Ms': 'Mnichu', 'W': 'Mnichu'},
    "mniszka": {'M': 'Mniszka', 'D': 'Mniszki', 'C': 'Mniszce', 'B': 'Mniszkę', 'N': 'Mniszką', 'Ms': 'Mniszce', 'W': 'Mniszko'},
    "biskup": {'M': 'Biskup', 'D': 'Biskupa', 'C': 'Biskupowi', 'B': 'Biskupa', 'N': 'Biskupem', 'Ms': 'Biskupie', 'W': 'Biskupie'},
    "towarzysz": {'M': 'Towarzysz', 'D': 'Towarzysza', 'C': 'Towarzyszowi', 'B': 'Towarzysza', 'N': 'Towarzyszem', 'Ms': 'Towarzyszu', 'W': 'Towarzyszu'},
    "towarzyszka": {'M': 'Towarzyszka', 'D': 'Towarzyszki', 'C': 'Towarzyszce', 'B': 'Towarzyszkę', 'N': 'Towarzyszką', 'Ms': 'Towarzyszce', 'W': 'Towarzyszko'},
    "rywal": {'M': 'Rywal', 'D': 'Rywala', 'C': 'Rywalowi', 'B': 'Rywala', 'N': 'Rywalem', 'Ms': 'Rywalu', 'W': 'Rywalu'},
    "rywalka": {'M': 'Rywalka', 'D': 'Rywalki', 'C': 'Rywalce', 'B': 'Rywalkę', 'N': 'Rywalką', 'Ms': 'Rywalce', 'W': 'Rywalko'},
    "zdrajca": {'M': 'Zdrajca', 'D': 'Zdrajcy', 'C': 'Zdrajcy', 'B': 'Zdrajcę', 'N': 'Zdrajcą', 'Ms': 'Zdrajcy', 'W': 'Zdrajco'},
    "zdrajczyni": {'M': 'Zdrajczyni', 'D': 'Zdrajczyni', 'C': 'Zdrajczyni', 'B': 'Zdrajczynię', 'N': 'Zdrajczynią', 'Ms': 'Zdrajczyni', 'W': 'Zdrajczyni'},
    "wędrowiec": {'M': 'Wędrowiec', 'D': 'Wędrowca', 'C': 'Wędrowcowi', 'B': 'Wędrowca', 'N': 'Wędrowcem', 'Ms': 'Wędrowcu', 'W': 'Wędrowcu'},
    "przewodnik": {'M': 'Przewodnik', 'D': 'Przewodnika', 'C': 'Przewodnikowi', 'B': 'Przewodnika', 'N': 'Przewodnikiem', 'Ms': 'Przewodniku', 'W': 'Przewodniku'},
    "przewodniczka": {'M': 'Przewodniczka', 'D': 'Przewodniczki', 'C': 'Przewodniczce', 'B': 'Przewodniczkę', 'N': 'Przewodniczką', 'Ms': 'Przewodniczce', 'W': 'Przewodniczko'},
    "walkiria": {'M': 'Walkiria', 'D': 'Walkirii', 'C': 'Walkirii', 'B': 'Walkirię', 'N': 'Walkirią', 'Ms': 'Walkirii', 'W': 'Walkirio'},
    "nimfa": {'M': 'Nimfa', 'D': 'Nimfy', 'C': 'Nimfie', 'B': 'Nimfę', 'N': 'Nimfą', 'Ms': 'Nimfie', 'W': 'Nimfo'},
    "syrena": {'M': 'Syrena', 'D': 'Syreny', 'C': 'Syrenie', 'B': 'Syrenę', 'N': 'Syreną', 'Ms': 'Syrenie', 'W': 'Syreno'},
    "sukkub": {'M': 'Sukkub', 'D': 'Sukkuba', 'C': 'Sukkubowi', 'B': 'Sukkuba', 'N': 'Sukkubem', 'Ms': 'Sukkubie', 'W': 'Sukkubie'},
    "elf": {'M': 'Elf', 'D': 'Elfa', 'C': 'Elfowi', 'B': 'Elfa', 'N': 'Elfem', 'Ms': 'Elfie', 'W': 'Elfie'},
    "elfka": {'M': 'Elfka', 'D': 'Elfki', 'C': 'Elfce', 'B': 'Elfkę', 'N': 'Elfką', 'Ms': 'Elfce', 'W': 'Elfko'},
    "krasnolud": {'M': 'Krasnolud', 'D': 'Krasnoluda', 'C': 'Krasnoludowi', 'B': 'Krasnoluda', 'N': 'Krasnoludem', 'Ms': 'Krasnoludzie', 'W': 'Krasnoludzie'},
    "krasnoludka": {'M': 'Krasnoludka', 'D': 'Krasnoludki', 'C': 'Krasnoludce', 'B': 'Krasnoludkę', 'N': 'Krasnoludką', 'Ms': 'Krasnoludce', 'W': 'Krasnoludko'},
    "ork": {'M': 'Ork', 'D': 'Orka', 'C': 'Orkowi', 'B': 'Orka', 'N': 'Orkiem', 'Ms': 'Orku', 'W': 'Orku'},
    "goblin": {'M': 'Goblin', 'D': 'Goblina', 'C': 'Goblinowi', 'B': 'Goblina', 'N': 'Goblinem', 'Ms': 'Goblinie', 'W': 'Goblinie'},
    "olbrzym": {'M': 'Olbrzym', 'D': 'Olbrzyma', 'C': 'Olbrzymowi', 'B': 'Olbrzyma', 'N': 'Olbrzymem', 'Ms': 'Olbrzymie', 'W': 'Olbrzymie'},
    "tytan": {'M': 'Tytan', 'D': 'Tytana', 'C': 'Tytanowi', 'B': 'Tytana', 'N': 'Tytanem', 'Ms': 'Tytanie', 'W': 'Tytanie'},
    "golem": {'M': 'Golem', 'D': 'Golema', 'C': 'Golemowi', 'B': 'Golema', 'N': 'Golemem', 'Ms': 'Golemie', 'W': 'Golemie'},
    "upiór": {'M': 'Upiór', 'D': 'Upiora', 'C': 'Upiorowi', 'B': 'Upiora', 'N': 'Upiorem', 'Ms': 'Upiorze', 'W': 'Upiorze'},
    "wilkołak": {'M': 'Wilkołak', 'D': 'Wilkołaka', 'C': 'Wilkołakowi', 'B': 'Wilkołaka', 'N': 'Wilkołakiem', 'Ms': 'Wilkołaku', 'W': 'Wilkołaku'},
    "wiedźma": {'M': 'Wiedźma', 'D': 'Wiedźmy', 'C': 'Wiedźmie', 'B': 'Wiedźmę', 'N': 'Wiedźmą', 'Ms': 'Wiedźmie', 'W': 'Wiedźmo'},
    "gildia": {'M': 'Gildia', 'D': 'Gildii', 'C': 'Gildii', 'B': 'Gildię', 'N': 'Gildią', 'Ms': 'Gildii', 'W': 'Gildio'},
    "bractwo": {'M': 'Bractwo', 'D': 'Bractwa', 'C': 'Bractwu', 'B': 'Bractwo', 'N': 'Bractwem', 'Ms': 'Bractwie', 'W': 'Bractwo'},
    "sojusz": {'M': 'Sojusz', 'D': 'Sojuszu', 'C': 'Sojuszowi', 'B': 'Sojusz', 'N': 'Sojuszem', 'Ms': 'Sojuszu', 'W': 'Sojuszu'},
    "koalicja": {'M': 'Koalicja', 'D': 'Koalicji', 'C': 'Koalicji', 'B': 'Koalicję', 'N': 'Koalicją', 'Ms': 'Koalicji', 'W': 'Koalicjo'},
    "akademia": {'M': 'Akademia', 'D': 'Akademii', 'C': 'Akademii', 'B': 'Akademię', 'N': 'Akademią', 'Ms': 'Akademii', 'W': 'Akademio'},
    "senat": {'M': 'Senat', 'D': 'Senatu', 'C': 'Senatowi', 'B': 'Senat', 'N': 'Senatem', 'Ms': 'Senacie', 'W': 'Senacie'},
    "republika": {'M': 'Republika', 'D': 'Republiki', 'C': 'Republice', 'B': 'Republikę', 'N': 'Republiką', 'Ms': 'Republice', 'W': 'Republiko'},
    "imperium": {'M': 'Imperium', 'D': 'Imperium', 'C': 'Imperium', 'B': 'Imperium', 'N': 'Imperium', 'Ms': 'Imperium', 'W': 'Imperium'},
    "cesarstwo": {'M': 'Cesarstwo', 'D': 'Cesarstwa', 'C': 'Cesarstwu', 'B': 'Cesarstwo', 'N': 'Cesarstwem', 'Ms': 'Cesarstwie', 'W': 'Cesarstwo'},
    "królestwo": {'M': 'Królestwo', 'D': 'Królestwa', 'C': 'Królestwu', 'B': 'Królestwo', 'N': 'Królestwem', 'Ms': 'Królestwie', 'W': 'Królestwo'},
    "księstwo": {'M': 'Księstwo', 'D': 'Księstwa', 'C': 'Księstwu', 'B': 'Księstwo', 'N': 'Księstwem', 'Ms': 'Księstwie', 'W': 'Księstwo'},
    "domena": {'M': 'Domena', 'D': 'Domeny', 'C': 'Domenie', 'B': 'Domenę', 'N': 'Domeną', 'Ms': 'Domenie', 'W': 'Domeno'},
    "kraina": {'M': 'Kraina', 'D': 'Krainy', 'C': 'Krainie', 'B': 'Krainę', 'N': 'Krainą', 'Ms': 'Krainie', 'W': 'Kraino'},
    "armia": {'M': 'Armia', 'D': 'Armii', 'C': 'Armii', 'B': 'Armię', 'N': 'Armią', 'Ms': 'Armii', 'W': 'Armio'},
    "oddział": {'M': 'Oddział', 'D': 'Oddziału', 'C': 'Oddziałowi', 'B': 'Oddział', 'N': 'Oddziałem', 'Ms': 'Oddziale', 'W': 'Oddziale'},
    "legion": {'M': 'Legion', 'D': 'Legionu', 'C': 'Legionowi', 'B': 'Legion', 'N': 'Legionem', 'Ms': 'Legionie', 'W': 'Legionie'},
    "flota": {'M': 'Flota', 'D': 'Floty', 'C': 'Flocie', 'B': 'Flotę', 'N': 'Flotą', 'Ms': 'Flocie', 'W': 'Floto'},
    "cytadela": {'M': 'Cytadela', 'D': 'Cytadeli', 'C': 'Cytadeli', 'B': 'Cytadelę', 'N': 'Cytadelą', 'Ms': 'Cytadeli', 'W': 'Cytadelo'},
    "bastion": {'M': 'Bastion', 'D': 'Bastionu', 'C': 'Bastionowi', 'B': 'Bastion', 'N': 'Bastionem', 'Ms': 'Bastionie', 'W': 'Bastionie'},
    "forteca": {'M': 'Forteca', 'D': 'Fortecy', 'C': 'Fortecy', 'B': 'Fortecę', 'N': 'Fortecą', 'Ms': 'Fortecy', 'W': 'Forteco'},
    "pałac": {'M': 'Pałac', 'D': 'Pałacu', 'C': 'Pałacowi', 'B': 'Pałac', 'N': 'Pałacem', 'Ms': 'Pałacu', 'W': 'Pałacu'},
    "katedra": {'M': 'Katedra', 'D': 'Katedry', 'C': 'Katedrze', 'B': 'Katedrę', 'N': 'Katedrą', 'Ms': 'Katedrze', 'W': 'Katedro'},
    "sanktuarium": {'M': 'Sanktuarium', 'D': 'Sanktuarium', 'C': 'Sanktuarium', 'B': 'Sanktuarium', 'N': 'Sanktuarium', 'Ms': 'Sanktuarium', 'W': 'Sanktuarium'},
    "kaplica": {'M': 'Kaplica', 'D': 'Kaplicy', 'C': 'Kaplicy', 'B': 'Kaplicę', 'N': 'Kaplicą', 'Ms': 'Kaplicy', 'W': 'Kaplico'},
    "klasztor": {'M': 'Klasztor', 'D': 'Klasztoru', 'C': 'Klasztorowi', 'B': 'Klasztor', 'N': 'Klasztorem', 'Ms': 'Klasztorze', 'W': 'Klasztorze'},
    "krypta": {'M': 'Krypta', 'D': 'Krypty', 'C': 'Krypcie', 'B': 'Kryptę', 'N': 'Kryptą', 'Ms': 'Krypcie', 'W': 'Krypto'},
    "grobowiec": {'M': 'Grobowiec', 'D': 'Grobowca', 'C': 'Grobowcowi', 'B': 'Grobowiec', 'N': 'Grobowcem', 'Ms': 'Grobowcu', 'W': 'Grobowcu'},
    "katakumby": {'M': 'Katakumby', 'D': 'Katakumb', 'C': 'Katakumbom', 'B': 'Katakumby', 'N': 'Katakumbami', 'Ms': 'Katakumbach', 'W': 'Katakumby'},
    "labirynt": {'M': 'Labirynt', 'D': 'Labiryntu', 'C': 'Labiryntowi', 'B': 'Labirynt', 'N': 'Labiryntem', 'Ms': 'Labiryncie', 'W': 'Labiryncie'},
    "loch": {'M': 'Loch', 'D': 'Lochu', 'C': 'Lochowi', 'B': 'Loch', 'N': 'Lochem', 'Ms': 'Lochu', 'W': 'Lochu'},
    "miasto": {'M': 'Miasto', 'D': 'Miasta', 'C': 'Miastu', 'B': 'Miasto', 'N': 'Miastem', 'Ms': 'Mieście', 'W': 'Miasto'},
    "wioska": {'M': 'Wioska', 'D': 'Wioski', 'C': 'Wiosce', 'B': 'Wioskę', 'N': 'Wioską', 'Ms': 'Wiosce', 'W': 'Wiosko'},
    "wieś": {'M': 'Wieś', 'D': 'Wsi', 'C': 'Wsi', 'B': 'Wieś', 'N': 'Wsią', 'Ms': 'Wsi', 'W': 'Wsi'},
    "port": {'M': 'Port', 'D': 'Portu', 'C': 'Portowi', 'B': 'Port', 'N': 'Portem', 'Ms': 'Porcie', 'W': 'Porcie'},
    "przystań": {'M': 'Przystań', 'D': 'Przystani', 'C': 'Przystani', 'B': 'Przystań', 'N': 'Przystanią', 'Ms': 'Przystani', 'W': 'Przystani'},
    "plac": {'M': 'Plac', 'D': 'Placu', 'C': 'Placowi', 'B': 'Plac', 'N': 'Placem', 'Ms': 'Placu', 'W': 'Placu'},
    "ulica": {'M': 'Ulica', 'D': 'Ulicy', 'C': 'Ulicy', 'B': 'Ulicę', 'N': 'Ulicą', 'Ms': 'Ulicy', 'W': 'Ulico'},
    "zaułek": {'M': 'Zaułek', 'D': 'Zaułka', 'C': 'Zaułkowi', 'B': 'Zaułek', 'N': 'Zaułkiem', 'Ms': 'Zaułku', 'W': 'Zaułku'},
    "las": {'M': 'Las', 'D': 'Lasu', 'C': 'Lasowi', 'B': 'Las', 'N': 'Lasem', 'Ms': 'Lesie', 'W': 'Lesie'},
    "puszcza": {'M': 'Puszcza', 'D': 'Puszczy', 'C': 'Puszczy', 'B': 'Puszczę', 'N': 'Puszczą', 'Ms': 'Puszczy', 'W': 'Puszczo'},
    "bór": {'M': 'Bór', 'D': 'Boru', 'C': 'Borowi', 'B': 'Bór', 'N': 'Borem', 'Ms': 'Borze', 'W': 'Borze'},
    "gaj": {'M': 'Gaj', 'D': 'Gaju', 'C': 'Gajowi', 'B': 'Gaj', 'N': 'Gajem', 'Ms': 'Gaju', 'W': 'Gaju'},
    "szczyt": {'M': 'Szczyt', 'D': 'Szczytu', 'C': 'Szczytowi', 'B': 'Szczyt', 'N': 'Szczytem', 'Ms': 'Szczycie', 'W': 'Szczycie'},
    "wąwóz": {'M': 'Wąwóz', 'D': 'Wąwozu', 'C': 'Wąwozowi', 'B': 'Wąwóz', 'N': 'Wąwozem', 'Ms': 'Wąwozie', 'W': 'Wąwozie'},
    "polana": {'M': 'Polana', 'D': 'Polany', 'C': 'Polanie', 'B': 'Polanę', 'N': 'Polaną', 'Ms': 'Polanie', 'W': 'Polano'},
    "bagno": {'M': 'Bagno', 'D': 'Bagna', 'C': 'Bagnu', 'B': 'Bagno', 'N': 'Bagnem', 'Ms': 'Bagnie', 'W': 'Bagno'},
    "oaza": {'M': 'Oaza', 'D': 'Oazy', 'C': 'Oazie', 'B': 'Oazę', 'N': 'Oazą', 'Ms': 'Oazie', 'W': 'Oazo'},
    "ocean": {'M': 'Ocean', 'D': 'Oceanu', 'C': 'Oceanowi', 'B': 'Ocean', 'N': 'Oceanem', 'Ms': 'Oceanie', 'W': 'Oceanie'},
    "wyspa": {'M': 'Wyspa', 'D': 'Wyspy', 'C': 'Wyspie', 'B': 'Wyspę', 'N': 'Wyspą', 'Ms': 'Wyspie', 'W': 'Wyspo'},
    "archipelag": {'M': 'Archipelag', 'D': 'Archipelagu', 'C': 'Archipelagowi', 'B': 'Archipelag', 'N': 'Archipelagiem', 'Ms': 'Archipelagu', 'W': 'Archipelagu'},
    "półwysep": {'M': 'Półwysep', 'D': 'Półwyspu', 'C': 'Półwyspowi', 'B': 'Półwysep', 'N': 'Półwyspem', 'Ms': 'Półwyspie', 'W': 'Półwyspie'},
    "wybrzeże": {'M': 'Wybrzeże', 'D': 'Wybrzeża', 'C': 'Wybrzeżu', 'B': 'Wybrzeże', 'N': 'Wybrzeżem', 'Ms': 'Wybrzeżu', 'W': 'Wybrzeże'},
    "przepaść": {'M': 'Przepaść', 'D': 'Przepaści', 'C': 'Przepaści', 'B': 'Przepaść', 'N': 'Przepaścią', 'Ms': 'Przepaści', 'W': 'Przepaści'},
    "otchłań": {'M': 'Otchłań', 'D': 'Otchłani', 'C': 'Otchłani', 'B': 'Otchłań', 'N': 'Otchłanią', 'Ms': 'Otchłani', 'W': 'Otchłani'},
    "pustka": {'M': 'Pustka', 'D': 'Pustki', 'C': 'Pustce', 'B': 'Pustkę', 'N': 'Pustką', 'Ms': 'Pustce', 'W': 'Pustko'},
    "kryształ": {'M': 'Kryształ', 'D': 'Kryształu', 'C': 'Kryształowi', 'B': 'Kryształ', 'N': 'Kryształem', 'Ms': 'Krysztale', 'W': 'Krysztale'},
    "klejnot": {'M': 'Klejnot', 'D': 'Klejnotu', 'C': 'Klejnotowi', 'B': 'Klejnot', 'N': 'Klejnotem', 'Ms': 'Klejnocie', 'W': 'Klejnocie'},
    "diament": {'M': 'Diament', 'D': 'Diamentu', 'C': 'Diamentowi', 'B': 'Diament', 'N': 'Diamentem', 'Ms': 'Diamencie', 'W': 'Diamencie'},
    "perła": {'M': 'Perła', 'D': 'Perły', 'C': 'Perle', 'B': 'Perłę', 'N': 'Perłą', 'Ms': 'Perle', 'W': 'Perło'},
    "rubin": {'M': 'Rubin', 'D': 'Rubinu', 'C': 'Rubinowi', 'B': 'Rubin', 'N': 'Rubinem', 'Ms': 'Rubinie', 'W': 'Rubinie'},
    "szmaragd": {'M': 'Szmaragd', 'D': 'Szmaragdu', 'C': 'Szmaragdowi', 'B': 'Szmaragd', 'N': 'Szmaragdem', 'Ms': 'Szmaragdzie', 'W': 'Szmaragdzie'},
    "runa": {'M': 'Runa', 'D': 'Runy', 'C': 'Runie', 'B': 'Runę', 'N': 'Runą', 'Ms': 'Runie', 'W': 'Runo'},
    "talizman": {'M': 'Talizman', 'D': 'Talizmanu', 'C': 'Talizmanowi', 'B': 'Talizman', 'N': 'Talizmanem', 'Ms': 'Talizmanie', 'W': 'Talizmanie'},
    "relikwia": {'M': 'Relikwia', 'D': 'Relikwii', 'C': 'Relikwii', 'B': 'Relikwię', 'N': 'Relikwią', 'Ms': 'Relikwii', 'W': 'Relikwio'},
    "artefakt": {'M': 'Artefakt', 'D': 'Artefaktu', 'C': 'Artefaktowi', 'B': 'Artefakt', 'N': 'Artefaktem', 'Ms': 'Artefakcie', 'W': 'Artefakcie'},
    "laska": {'M': 'Laska', 'D': 'Laski', 'C': 'Lasce', 'B': 'Laskę', 'N': 'Laską', 'Ms': 'Lasce', 'W': 'Lasko'},
    "kostur": {'M': 'Kostur', 'D': 'Kostura', 'C': 'Kosturowi', 'B': 'Kostur', 'N': 'Kosturem', 'Ms': 'Kosturze', 'W': 'Kosturze'},
    "topór": {'M': 'Topór', 'D': 'Topora', 'C': 'Toporowi', 'B': 'Topór', 'N': 'Toporem', 'Ms': 'Toporze', 'W': 'Toporze'},
    "włócznia": {'M': 'Włócznia', 'D': 'Włóczni', 'C': 'Włóczni', 'B': 'Włócznię', 'N': 'Włócznią', 'Ms': 'Włóczni', 'W': 'Włócznio'},
    "pika": {'M': 'Pika', 'D': 'Piki', 'C': 'Pice', 'B': 'Pikę', 'N': 'Piką', 'Ms': 'Pice', 'W': 'Piko'},
    "halabarda": {'M': 'Halabarda', 'D': 'Halabardy', 'C': 'Halabardzie', 'B': 'Halabardę', 'N': 'Halabardą', 'Ms': 'Halabardzie', 'W': 'Halabardo'},
    "kusza": {'M': 'Kusza', 'D': 'Kuszy', 'C': 'Kuszy', 'B': 'Kuszę', 'N': 'Kuszą', 'Ms': 'Kuszy', 'W': 'Kuszo'},
    "szpada": {'M': 'Szpada', 'D': 'Szpady', 'C': 'Szpadzie', 'B': 'Szpadę', 'N': 'Szpadą', 'Ms': 'Szpadzie', 'W': 'Szpado'},
    "rapier": {'M': 'Rapier', 'D': 'Rapiera', 'C': 'Rapierowi', 'B': 'Rapier', 'N': 'Rapierem', 'Ms': 'Rapierze', 'W': 'Rapierze'},
    "szabla": {'M': 'Szabla', 'D': 'Szabli', 'C': 'Szabli', 'B': 'Szablę', 'N': 'Szablą', 'Ms': 'Szabli', 'W': 'Szablo'},
    "pancerz": {'M': 'Pancerz', 'D': 'Pancerza', 'C': 'Pancerzowi', 'B': 'Pancerz', 'N': 'Pancerzem', 'Ms': 'Pancerzu', 'W': 'Pancerzu'},
    "rękawica": {'M': 'Rękawica', 'D': 'Rękawicy', 'C': 'Rękawicy', 'B': 'Rękawicę', 'N': 'Rękawicą', 'Ms': 'Rękawicy', 'W': 'Rękawico'},
    "płaszcz": {'M': 'Płaszcz', 'D': 'Płaszcza', 'C': 'Płaszczowi', 'B': 'Płaszcz', 'N': 'Płaszczem', 'Ms': 'Płaszczu', 'W': 'Płaszczu'},
    "szata": {'M': 'Szata', 'D': 'Szaty', 'C': 'Szacie', 'B': 'Szatę', 'N': 'Szatą', 'Ms': 'Szacie', 'W': 'Szato'},
    "maska": {'M': 'Maska', 'D': 'Maski', 'C': 'Masce', 'B': 'Maskę', 'N': 'Maską', 'Ms': 'Masce', 'W': 'Masko'},
    "zegar": {'M': 'Zegar', 'D': 'Zegara', 'C': 'Zegarowi', 'B': 'Zegar', 'N': 'Zegarem', 'Ms': 'Zegarze', 'W': 'Zegarze'},
    "klepsydra": {'M': 'Klepsydra', 'D': 'Klepsydry', 'C': 'Klepsydrze', 'B': 'Klepsydrę', 'N': 'Klepsydrą', 'Ms': 'Klepsydrze', 'W': 'Klepsydro'},
    "książka": {'M': 'Książka', 'D': 'Książki', 'C': 'Książce', 'B': 'Książkę', 'N': 'Książką', 'Ms': 'Książce', 'W': 'Książko'},
    "sekret": {'M': 'Sekret', 'D': 'Sekretu', 'C': 'Sekretowi', 'B': 'Sekret', 'N': 'Sekretem', 'Ms': 'Sekrecie', 'W': 'Sekrecie'},
    "tajemnica": {'M': 'Tajemnica', 'D': 'Tajemnicy', 'C': 'Tajemnicy', 'B': 'Tajemnicę', 'N': 'Tajemnicą', 'Ms': 'Tajemnicy', 'W': 'Tajemnico'},
}

KNOWN_HEAD_NOUNS = {
    "księga", "księgi", "miecz", "miecze", "lanca", "tarcza", "zakon", "dolina", "pieczęć",
    "oko", "ręka", "pierścień", "amulet", "zwierciadło", "kielich", "zwój", "zwoje",
    "królowa", "król", "władca", "władczyni", "cesarz", "cesarzowa", "książę", "księżniczka",
    "mistrz", "mistrzyni", "demon", "demonica", "pani", "pan", "lord", "bóg", "bogini",
    "kamień", "drzewo", "kraj", "wyspa", "wieża", "zamek", "twierdza", "świątynia", "krew", "duch",
    "serce", "płomień", "brama", "wrota", "światło", "cień", "korona", "tron",
    "ród", "znak", "kosa", "młot", "sztylet", "łuk", "strzała", "zbroja", "hełm",
    "różdżka", "książka", "kodeks", "tajemnica", "tajemnice", "sekret", "sekrety",
    "opowieść", "legenda", "pieśń", "hymn", "kronika", "kroniki", "droga", "szlak",
    "most", "rzeka", "jezioro", "morze", "góra", "góry", "pustynia", "pakt",
    "przymierze", "zemsta", "klątwa", "gniew", "bunt", "upadek", "powrót",
    "narodziny", "koniec", "początek", "córka", "syn", "matka", "ojciec",
    "brat", "siostra", "bohater", "wojownik", "rycerz", "mag", "czarnoksiężnik", "kapłan",
    "dowódca", "zabójca", "obrońca", "łowca", "strażnik", "generał",
    "arcykapłan", "arcymag", "szaman", "czarownik", "czarownica", "bestia", "potwór",
    "smok", "bóstwo", "anioł", "wampir", "widmo", "zjawa", "wojowniczka", "bohaterka",
    "kapłanka"
}

TOPONYMIC_INSTITUTION_HEAD_NOUNS = {
    "miasto", "wieża", "gildia", "akademia", "cytadela", "las", "zamek", "twierdza",
    "dolina", "rzeka", "jezioro", "morze", "góra", "pałac", "katedra", "sanktuarium",
    "kaplica", "klasztor", "krypta", "grobowiec", "katakumby", "labirynt", "loch",
    "wioska", "wieś", "port", "przystań", "plac", "ulica", "zaułek", "puszcza",
    "bór", "gaj", "szczyt", "wąwóz", "polana", "bagno", "oaza", "ocean", "wyspa",
    "archipelag", "półwysep", "wybrzeże", "przepaść", "otchłań", "pustka", "bractwo",
    "zakon", "sojusz", "koalicja", "senat", "republika", "imperium", "cesarstwo",
    "królestwo", "księstwo", "domena", "kraina", "armia", "oddział", "legion", "flota",
    "bastion", "forteca", "brama", "wrota", "kościół"
}

_PREPS_GEN = {"do", "od", "z", "ze", "dla", "bez", "u", "koło", "obok", "blisko", "wokół", "dookoła", "pośród", "wśród", "spod", "zza", "znad", "wzdłuż", "podczas", "mimo", "według", "wskutek", "wobec", "naprzeciw"}
_PREPS_LOC = {"w", "we", "na", "po", "o", "przy"}
_PREPS_INST = {"za", "pod", "pode", "nad", "nade", "przed", "przede", "między", "pomiędzy", "poza"}
_PREPS_DAT = {"dzięki", "przeciw", "przeciwko", "ku", "wbrew"}
_ALL_TOPONYM_PREPS = _PREPS_GEN | _PREPS_LOC | _PREPS_INST | _PREPS_DAT
_PREP_PAT = "|".join(sorted(_ALL_TOPONYM_PREPS, key=len, reverse=True))
_HEAD_PAT = "|".join([k.capitalize() for k in TOPONYMIC_INSTITUTION_HEAD_NOUNS])
_RE_TOPONYMIC_PREP_GOV = re.compile(rf"\b({_PREP_PAT})\s+({_HEAD_PAT})\b(\s+[A-ZĄĆĘŁŃÓŚŹŻ0-9][a-ząćęłńóśźż0-9]*)", re.IGNORECASE)

def sanitize_toponymic_preposition_governance(text: str) -> str:
    """
    Sanitizes nominative freezing of toponym and institution head nouns governed by Polish prepositions
    (Filar CLXXXIV / Zasada 15 AGENTS.md / 0.00 PLN).
    Ensures that generic category head nouns (miasto, wieża, gildia, akademia, cytadela, las, etc.)
    inflect to the proper grammatical case governed by the preceding preposition (Dopełniacz, Miejscownik,
    Narzędnik, Celownik), while preserving proper names/genitive modifiers and lowercase orthography.
    """
    if not text:
        return ""

    def _repl_toponym_prep(m):
        prep = m.group(1)
        head = m.group(2)
        rest = m.group(3)
        prep_l = prep.lower()
        head_l = head.lower()
        d = KNOWN_HEAD_NOUN_DECLENSIONS.get(head_l)
        if not d:
            return m.group(0)
        if prep_l in _PREPS_GEN:
            case = "D"
        elif prep_l in _PREPS_LOC:
            case = "Ms"
        elif prep_l in _PREPS_INST:
            case = "N"
        elif prep_l in _PREPS_DAT:
            case = "C"
        else:
            case = "D"
        decl_head = d.get(case, head).lower()
        return f"{prep} {decl_head}{rest}"

    return _RE_TOPONYMIC_PREP_GOV.sub(_repl_toponym_prep, text)


def generate_polish_name_declension(name: str, gender: str = "UNKNOWN") -> Dict[str, str]:
    """
    Generates 7 grammatical cases for Japanese / foreign anime character names
    following standard Polish literary AVT phonological rules.
    """
    n = name.strip()
    g = gender.upper()
    if not n:
        return {}
    if len(n) <= 1 or not any(c.isalpha() for c in n):
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    words = n.split()
    if len(words) > 1:
        # A. Check for prepositional complement: "X z Y", "X ze stali", "X do Y"
        # e.g. "Księga Toaha z Hiden", "Miecz z Boelate"
        for prep_idx, w_p in enumerate(words):
            if prep_idx > 0 and w_p.lower() in ("z", "ze", "od", "do", "w", "we", "o", "pod") and prep_idx < len(words) - 1:
                head_part = " ".join(words[:prep_idx])
                prep_part = " ".join(words[prep_idx:])
                head_decl = generate_polish_name_declension(head_part, gender)
                if head_decl and head_decl.get("M"):
                    return {
                        case: f"{head_decl.get(case, head_part)} {prep_part}"
                        for case in ["M", "D", "C", "B", "N", "Ms", "W"]
                    }

        # B. Check for Noun + Genitive Attribute (Przydawka dopełniaczowa)
        # e.g. "Księga Toaha", "Zakon Feniksa", "Dolina Rozpaczy", "Miecz Prawdy", "Władca Złudzeń", "Demon Krwi"
        first_lower = words[0].lower()
        if (first_lower in KNOWN_HEAD_NOUNS or first_lower in KNOWN_HEAD_NOUN_DECLENSIONS) and len(words) >= 2:
            if first_lower in KNOWN_HEAD_NOUN_DECLENSIONS:
                is_cap = words[0][0].isupper()
                head_decl = {
                    c: (v.capitalize() if is_cap else v.lower())
                    for c, v in KNOWN_HEAD_NOUN_DECLENSIONS[first_lower].items()
                }
            else:
                head_gender = "FEMALE" if (first_lower.endswith("a") or first_lower in ("pieczęć", "krew", "opowieść", "pieśń")) else (
                    "NEUTER" if first_lower.endswith(("o", "e")) else (
                        "MALE" if first_lower in ("syn", "ojciec", "brat", "bohater", "wojownik", "rycerz", "mag", "czarnoksiężnik", "kapłan", "król", "władca", "cesarz", "książę", "mistrz", "arcykapłan", "arcymag", "szaman", "czarownik", "anioł", "wampir", "smok", "potwór") else "MALE_INANIMATE"
                    )
                )
                head_decl = generate_polish_name_declension(words[0], "FEMALE" if head_gender == "FEMALE" else ("MALE" if head_gender == "MALE" else "UNKNOWN"))
            attr_phrase = " ".join(words[1:])
            return {
                case: f"{head_decl.get(case, words[0])} {attr_phrase}"
                for case in ["M", "D", "C", "B", "N", "Ms", "W"]
            }

        # C. Check for Adjective + Noun (or Noun + Adjective)
        if len(words) == 2:
            w1, w2 = words[0], words[1]
            if is_polish_adjective(w1) and not is_polish_adjective(w2):
                adj_g = "FEMALE" if w1.lower().endswith("a") else ("NEUTER" if w1.lower().endswith("e") else (gender if gender != "UNKNOWN" else ("FEMALE" if w2.lower().endswith("a") else "MALE")))
                adj_decl = generate_polish_adjective_declension(w1, adj_g, is_animate=True)
                noun_decl = generate_polish_name_declension(w2, adj_g)
                return {
                    case: f"{adj_decl.get(case, w1)} {noun_decl.get(case, w2)}"
                    for case in ["M", "D", "C", "B", "N", "Ms", "W"]
                }
            elif is_polish_adjective(w2) and not is_polish_adjective(w1):
                adj_g = "FEMALE" if w2.lower().endswith("a") else ("NEUTER" if w2.lower().endswith("e") else (gender if gender != "UNKNOWN" else ("FEMALE" if w1.lower().endswith("a") else "MALE")))
                noun_decl = generate_polish_name_declension(w1, adj_g)
                adj_decl = generate_polish_adjective_declension(w2, adj_g, is_animate=True)
                return {
                    case: f"{noun_decl.get(case, w1)} {adj_decl.get(case, w2)}"
                    for case in ["M", "D", "C", "B", "N", "Ms", "W"]
                }

        # D. Default multi-word: decline each word (e.g. Aura Gilotyna, Brandon Heat)
        sub_decls = [generate_polish_name_declension(w, gender) for w in words]
        if all(sub_decls):
            return {
                case: " ".join(d.get(case, w) for d, w in zip(sub_decls, words))
                for case in ["M", "D", "C", "B", "N", "Ms", "W"]
            }

    # Already inflected tokens or non-nominative plural/case endings
    if n.lower().endswith(("ą", "ę", "ej", "ach", "ami", "om")):
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    is_male = (g == "MALE" or "MĘSK" in g or "MALE" in g)
    is_female = (g == "FEMALE" or "KOBIETA" in g or "ŻEŃSK" in g)
    if not is_female and not is_male and (n.lower() in INVARIABLE_JAPANESE_FEMALE_NAMES or n.lower() in FOREIGN_FEMALE_CONSONANT_NAMES or is_inherently_female_name(n)):
        is_female = True

    # 0a. Adjectives / adjectival names and titles (e.g. Wielka, Wielki, Czarna, Czarny, Nieśmiertelny, Sobieski)
    if is_polish_adjective(n):
        return generate_polish_adjective_declension(n, gender=g if g != "UNKNOWN" else None, is_animate=True)

    # 0. Neuter nouns ending in -um (e.g. Imperium, Muzeum, Liceum, Akwarium, Koloseum, Seminarium):
    # In Polish singular, these borrowings from Latin are strictly indeclinable across all 7 cases (M=D=C=B=N=Ms=W).
    if n.lower().endswith("um"):
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    # 1. Names ending in -a (both female and male like Akira, Soma, Luca, Seneca, Alicia, Maria)
    if n.endswith("a"):
        stem = n[:-1]
        if not stem:
            return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

        # Phonological alternations in Polish:
        # -ia (Maria, Alicia, Julia, Silvia) -> D./C./Ms. -ii; B. -ię; N. -ią; W. -io
        if stem.endswith("i"):
            return {
                "M": n,
                "D": stem + "i",
                "C": stem + "i",
                "B": stem + "ę",
                "N": stem + "ą",
                "Ms": stem + "i",
                "W": stem + "o"
            }
        # -ya (Freya, Maya, Anya, Kaya) -> D./C./Ms. -i; B. -ę; N. -ą; W. -o
        elif stem.endswith("y"):
            return {
                "M": n,
                "D": stem + "i",
                "C": stem + "i",
                "B": stem + "ę",
                "N": stem + "ą",
                "Ms": stem + "i",
                "W": stem + "o"
            }
        # -ca foreign names (Luca, Seneca, Petrarca, Mica) -> hard k stem in D/B/N
        # vs Polish agent nouns in -ca (władca, dowódca, obrońca, zabójca, zdrajca, łowca, stwórca):
        elif stem.endswith("c"):
            if stem.lower() in ("władc", "dowódc", "dowodc", "obrońc", "obronc", "zabójc", "zabojc", "zdrajc", "łowc", "lowc", "stwórc", "stworc", "twórc", "tworc", "znawc", "morderc", "wykonawc") or len(stem) > 4:
                return {
                    "M": n,
                    "D": stem + "y",
                    "C": stem + "y",
                    "B": stem + "ę",
                    "N": stem + "ą",
                    "Ms": stem + "y",
                    "W": stem + "o"
                }
            return {
                "M": n,
                "D": stem[:-1] + "ki",
                "C": stem + "e",
                "B": stem[:-1] + "kę",
                "N": stem[:-1] + "ką",
                "Ms": stem + "e",
                "W": stem + "o"
            }

        # Consonant stems before -a
        if stem.endswith("k"):
            c_ms = stem[:-1] + "ce"
            d_case = stem + "i"
        elif stem.endswith("g"):
            c_ms = stem[:-1] + "dze"
            d_case = stem + "i"
        elif stem.endswith("r"):
            c_ms = stem[:-1] + "rze"
            d_case = stem + "y"
        elif stem.endswith("t"):
            c_ms = stem[:-1] + "cie"
            d_case = stem + "y"
        elif stem.endswith("d"):
            c_ms = stem[:-1] + "dzie"
            d_case = stem + "y"
        elif stem.endswith("s"):
            c_ms = stem[:-1] + "sie"
            d_case = stem + "y"
        elif stem.endswith("z"):
            c_ms = stem[:-1] + "zie"
            d_case = stem + "y"
        elif stem.endswith("n"):
            c_ms = stem[:-1] + "nie"
            d_case = stem + "y"
        elif stem.endswith("m"):
            c_ms = stem[:-1] + "mie"
            d_case = stem + "y"
        elif stem.endswith("b"):
            c_ms = stem[:-1] + "bie"
            d_case = stem + "y"
        elif stem.endswith("p"):
            c_ms = stem[:-1] + "pie"
            d_case = stem + "y"
        elif stem.endswith("w"):
            c_ms = stem[:-1] + "wie"
            d_case = stem + "y"
        elif stem.endswith("ł"):
            c_ms = stem[:-1] + "le"
            d_case = stem + "y"
        elif stem.endswith("l"):
            c_ms = stem + "i"
            d_case = stem + "i"
        elif stem.endswith(("cz", "sz", "rz", "ż")):
            c_ms = stem + "y"
            d_case = stem + "y"
        else:
            c_ms = stem + "e"
            d_case = stem + "y"

        return {
            "M": n,
            "D": d_case,
            "C": c_ms,
            "B": stem + "ę",
            "N": stem + "ą",
            "Ms": c_ms,
            "W": stem + "o"
        }

    # Female names ending in consonant or vowel other than -a: strictly undeclined in Polish (PWN norm)
    if is_female:
        return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}

    # 2. Male names ending in consonant
    if n[-1].lower() not in "aeiouyąęó":
        stem = n
        last_c = n[-1].lower()
        last_2c = n[-2:].lower() if len(n) >= 2 else ""

        # Mobile 'e' in Polish names ending in -ek (Marek -> Mark-, Jacek -> Jack-, Tomek -> Tomk-, etc.)
        if len(n) >= 4 and last_2c == "ek" and n.lower() in ("marek", "jacek", "tomek", "janek", "franek", "bartek", "wojtek", "maciek", "leszek", "radek", "przemek", "władek", "staszek", "wiesiek"):
            stem = n[:-2] + "k"

        # Narzędnik po k, g: -iem (Gujukiem, Güyükiem, Olegiem, Magiem)
        n_case = stem + "iem" if last_c in ("k", "g") else stem + "em"

        # Miejscownik i Wołacz
        if last_c in ("l", "k", "g", "j", "c") or last_2c in ("ch", "cz", "sz", "rz", "th"):
            c_ms = stem + "u"
            c_w = stem + "u"
        elif last_c == "r":
            c_ms = stem[:-1] + "rze"
            c_w = stem[:-1] + "rze"
        elif last_c == "t":
            c_ms = stem[:-1] + "cie"
            c_w = stem[:-1] + "cie"
        elif last_c == "d":
            c_ms = stem[:-1] + "dzie"
            c_w = stem[:-1] + "dzie"
        elif last_c == "w":
            c_ms = stem + "ie"
            c_w = stem + "ie"
        else:
            c_ms = stem + "ie"
            c_w = stem + "ie"

        return {
            "M": n,
            "D": stem + "a",
            "C": stem + "owi",
            "B": stem + "a",
            "N": n_case,
            "Ms": c_ms,
            "W": c_w
        }

    # 2b. Adjectives / adjectival names and titles ending in -y / -i (e.g. Nieśmiertelny, Wielki, Sobieski, Czarny)
    if is_polish_adjective(n):
        return generate_polish_adjective_declension(n, gender=g if g != "UNKNOWN" else None, is_animate=True)

    # 3. Male names ending in vowels other than -a (-o, -e, -i, -u, -y)
    # In Japanese AVT, vowel-ending names are kept uninflected to preserve phonetic integrity (Belczyk/PWN).
    return {"M": n, "D": n, "C": n, "B": n, "N": n, "Ms": n, "W": n}


def _fix_ubrac_clothes_match(m) -> str:
    lead = m.group(1)
    suffix = m.group(2) or ""
    sep = m.group(3)
    garment = m.group(4)
    is_cap = lead.isupper()
    if not suffix:
        verb = "Założył" if is_cap else "założył"
    elif suffix == "a":
        verb = "Założyła" if is_cap else "założyła"
    elif suffix == "o":
        verb = "Założyło" if is_cap else "założyło"
    elif suffix == "i":
        verb = "Założyli" if is_cap else "założyli"
    elif suffix == "y":
        verb = "Założyły" if is_cap else "założyły"
    elif suffix == "em":
        verb = "Założyłem" if is_cap else "założyłem"
    elif suffix == "am":
        verb = "Założyłam" if is_cap else "założyłam"
    elif suffix == "eś":
        verb = "Założyłeś" if is_cap else "założyłeś"
    elif suffix == "aś":
        verb = "Założyłaś" if is_cap else "założyłaś"
    else:
        verb = ("Założył" if is_cap else "założył") + suffix
    return f"{verb}{sep}{garment}"


def _fix_rozebrac_clothes_match(m) -> str:
    lead = m.group(1)
    suffix = m.group(2) or ""
    sep = m.group(3)
    garment = m.group(4)
    is_cap = lead.isupper()
    if not suffix:
        verb = "Zdjął" if is_cap else "zdjął"
    elif suffix == "a":
        verb = "Zdjęła" if is_cap else "zdjęła"
    elif suffix == "o":
        verb = "Zdjęło" if is_cap else "zdjęło"
    elif suffix == "i":
        verb = "Zdjęli" if is_cap else "zdjęli"
    elif suffix == "y":
        verb = "Zdjęły" if is_cap else "zdjęły"
    elif suffix == "em":
        verb = "Zdjąłem" if is_cap else "zdjąłem"
    elif suffix == "am":
        verb = "Zdjąłam" if is_cap else "zdjąłam"
    elif suffix == "eś":
        verb = "Zdjąłeś" if is_cap else "zdjąłeś"
    elif suffix == "aś":
        verb = "Zdjąłaś" if is_cap else "zdjąłaś"
    else:
        verb = ("Zdjął" if is_cap else "zdjął") + suffix
    return f"{verb}{sep}{garment}"


def _fix_odegrac_znaczenie(m) -> str:
    lead = m.group(1)
    is_cap = lead[0].isupper()
    if lead.endswith("li"):
        verb = "Mieli" if is_cap else "mieli"
    elif lead.endswith("ły"):
        verb = "Miały" if is_cap else "miały"
    elif lead.endswith("ło"):
        verb = "Miało" if is_cap else "miało"
    elif lead.endswith("ła"):
        verb = "Miała" if is_cap else "miała"
    elif lead.endswith("ł"):
        verb = "Miał" if is_cap else "miał"
    elif "wa" in lead:
        verb = "Ma" if is_cap else "ma"
    else:
        verb = "Mieć" if is_cap else "mieć"
    return f"{verb} znaczenie"


def _fix_kupic_czas(m) -> str:
    lead = m.group(1)
    is_cap = lead[0].isupper()
    if lead.endswith("ła"):
        verb = "Zyskała" if is_cap else "zyskała"
    elif lead.endswith("ło"):
        verb = "Zyskało" if is_cap else "zyskało"
    elif lead.endswith("li"):
        verb = "Zyskali" if is_cap else "zyskali"
    elif lead.endswith("ły"):
        verb = "Zyskały" if is_cap else "zyskały"
    elif lead.endswith("ł"):
        verb = "Zyskał" if is_cap else "zyskał"
    elif lead.endswith("my"):
        verb = "Zyskamy" if is_cap else "zyskamy"
    elif lead.endswith("sz"):
        verb = "Zyskasz" if is_cap else "zyskasz"
    elif "kupuj" in lead.lower():
        verb = "Zyskujemy" if lead.endswith("emy") else ("Zyskują" if lead.endswith("ą") else ("Zyskuje" if lead.endswith("e") else "zyskuje"))
        if not is_cap:
            verb = verb.lower()
    else:
        verb = "Zyskać" if is_cap else "zyskać"
    return f"{verb} na czasie"



CLOTHES_PATTERN = (
    r"(?:buty|butów|butami|butach|trampki|trampkami|kalosze|kaloszami|"
    r"kurtk(?:a|ę|i|ce|ą|ach|ami)|płaszcz(?:a|em|u|e|ach|ami)?|spodni(?:e|ami|ach)?|spodni|"
    r"bluz(?:a|ę|y|ce|ą|ki|kach|kami)|czapk(?:a|ę|i|ce|ą|ach|ami)|szalik(?:a|u|iem|i|ach|ami)?|"
    r"rękawiczk(?:i|ami|ach|ek)|rękawic(?:e|ami|ach|ą|y)|skarpet(?:ki|ek|kami|kach)|"
    r"sukienk(?:a|ę|i|ce|ą|ach|ami))"
)

TYPO_NORMALIZATIONS = [
    # Clothing collocations (Norma Wzorcowa PWN: 'zakładać/wkładać buty', a nie 'ubierać')
    (rf"\b([Uu])bierz(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Załóż" if m.group(1).isupper() else "załóż") + m.group(2) + m.group(3)),
    (rf"\b([Uu])bierzcie(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Załóżcie" if m.group(1).isupper() else "załóżcie") + m.group(2) + m.group(3)),
    (rf"\b([Uu])bierać(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Zakładać" if m.group(1).isupper() else "zakładać") + m.group(2) + m.group(3)),
    (rf"\b([Uu])brać(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Założyć" if m.group(1).isupper() else "założyć") + m.group(2) + m.group(3)),
    (rf"\b([Uu])brał(em|am|aś|eś|a|o|i|y)?(\s+)({CLOTHES_PATTERN})\b",
     _fix_ubrac_clothes_match),
    (rf"\b([Rr])ozbierz(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Zdejmij" if m.group(1).isupper() else "zdejmij") + m.group(2) + m.group(3)),
    (rf"\b([Rr])ozebrać(\s+)({CLOTHES_PATTERN})\b",
     lambda m: ("Zdjąć" if m.group(1).isupper() else "zdjąć") + m.group(2) + m.group(3)),
    (rf"\b([Rr])ozebrał(em|am|aś|eś|a|o|i|y)?(\s+)({CLOTHES_PATTERN})\b",
     _fix_rozebrac_clothes_match),
    (r"(^|[^\w]|\\[Nnh])([Ss])pyh(am|asz|a|amy|acie|ają|ać|ał|ała|ało|ali|ały|ano)\b", r"\g<1>\g<2>pyt\g<3>"),
    (r"(^|[^\w]|\\[Nnh])([Ww])ziąść\b", r"\g<1>\g<2>ziąć"),
    (r"(^|[^\w]|\\[Nnh])([Pp])oszłem\b", r"\g<1>\g<2>oszedłem"),
    (r"(^|[^\w]|\\[Nnh])([Ww])łancza(ć|m|sz|my|cie|ją|ł|ła|ło|li|ły|no|nie|nia|niem)?\b", r"\g<1>\g<2>łącza\g<3>"),
    (r"(^|[^\w]|\\[Nnh])([Ww])yłancza(ć|m|sz|my|cie|ją|ł|ła|ło|li|ły|no|nie|nia|niem)?\b", r"\g<1>\g<2>yłącza\g<3>"),
    (r"(^|[^\w]|\\[Nnh])([Nn])a\s+codzień\b", r"\g<1>\g<2>a co dzień"),
    (r"(^|[^\w]|\\[Nnh])([Cc])onajmniej\b", r"\g<1>\g<2>o najmniej"),
    (r"(^|[^\w]|\\[Nnh])([Nn])arazie\b", r"\g<1>\g<2>a razie"),
    (r"(^|[^\w]|\\[Nnh])([Zz])\s+przed\b", r"\g<1>sprzed"),
    (r"(^|[^\w]|\\[Nnh])([Zz])\s+poza\b", r"\g<1>spoza"),
    # Chained bracket sanitization (Filar IV / LX / XCVIII)
    (r"\s*\]\s*\[\s*", r"\\N"),
    # Anti-calque titular normalizations: 'Aura od Gilotyny' -> 'Aura Gilotyna' (Filar XCVIII/CLXV)
    (r"(^|[^\w]|\\[Nnh])([Aa])ura\s+od\s+[Gg]ilotyny\b", r"\g<1>\g<2>ura Gilotyna"),
    (r"(^|[^\w]|\\[Nnh])([Aa])ury\s+od\s+[Gg]ilotyny\b", r"\g<1>\g<2>ury Gilotyny"),
    (r"(^|[^\w]|\\[Nnh])([Aa])urze\s+od\s+[Gg]ilotyny\b", r"\g<1>\g<2>urze Gilotynie"),
    (r"(^|[^\w]|\\[Nnh])([Aa])urę\s+od\s+[Gg]ilotyny\b", r"\g<1>\g<2>urę Gilotynę"),
    (r"(^|[^\w]|\\[Nnh])([Aa])urą\s+od\s+[Gg]ilotyn(?:ą|y)\b", r"\g<1>\g<2>urą Gilotyną"),
    # Deformed adjective comparatives / superlatives (e.g. 'najdobrejsze' -> 'najlepsze')
    (r"(^|[^\w]|\\[Nnh])([Nn])ajdobrejsz(y|ego|emu|ym|a|ej|ą|e|ych|ymi)?\b", r"\g<1>\g<2>ajlepsz\g<3>"),
    (r"(^|[^\w]|\\[Nnh])dobrejsz(y|ego|emu|ym|a|ej|ą|e|ych|ymi)?\b", r"\g<1>lepsz\g<2>"),
    (r"(^|[^\w]|\\[Nnh])Dobrejsz(y|ego|emu|ym|a|ej|ą|e|ych|ymi)?\b", r"\g<1>Lepsz\g<2>"),
    # Absolute linguistic & orthographic invariants (Filar CLXIV)
    (r"(^|[^\w]|\\[Nnh])([Ww])\s*każdym\s+bądź\s+razie\b", r"\g<1>\g<2> każdym razie"),
    (r"(^|[^\w]|\\[Nnh])([Ww])\s+cudzysłowiu\b", r"\g<1>\g<2> cudzysłowie"),
    (r"(^|[^\w]|\\[Nnh])([Pp])o\s+najmniejszej\s+linii\s+oporu\b", r"\g<1>\g<2>o linii najmniejszego oporu"),
    (r"(^|[^\w]|\\[Nnh])spowrotem\b", r"\g<1>z powrotem"),
    (r"(^|[^\w]|\\[Nnh])Spowrotem\b", r"\g<1>Z powrotem"),
    (r"(^|[^\w]|\\[Nnh])([Dd])latego\s+bo\b", r"\g<1>\g<2>latego że"),
    (r"(^|[^\w]|\\[Nnh])([Oo])d\s+nienacka\b", r"\g<1>znienacka"),
    (r"\b((?:[A-Za-ząćęłńóśźż0-9]+\s+)?(?:raz|razy|kroć|dni|lat|godzin|minut|sekund|miesięcy|tygodni|kolejek|prób|zwycięstw|porażek))\s+pod\s+rząd\b", r"\1 z rzędu"),
    (r"\b([Dd]wa|[Tt]rzy|[Cc]ztery|[Pp]ięć|[Ss]ześć|[Ss]iedem|[Oo]siem|[Dd]ziewięć|[Dd]ziesiąt|[Kk]ilka|[Pp]arę|[Ww]iele|[Kk]olejn[a-ząćęłńóśźż]*)\s+([a-ząćęłńóśźż]+)\s+pod\s+rząd\b", r"\1 \2 z rzędu"),
    # Absolute pleonasms (Filar IV / Belczyk / PWN)
    (r"\b([Ss]pada(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+w\s+dół\b", r"\1"),
    (r"\b([Ss]pada(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+na\s+dół\b", r"\1"),
    (r"\b([Ww]znosi(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+się\s+w\s+górę\b", r"\1 się"),
    (r"\b([Ww]znosi(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+się\s+do\s+góry\b", r"\1 się"),
    (r"\b([Cc]ofn(?:ąć|ął|ęła|ęło|ęli|ęły|ij|ijcie|ę|iesz|ie|iemy|iecie|ą)|[Cc]ofa(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+się\s+do\s+tyłu\b", r"\1 się"),
    (r"\b([Cc]ofn(?:ąć|ął|ęła|ęło|ęli|ęły|ij|ijcie|ę|iesz|ie|iemy|iecie|ą)|[Cc]ofa(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+się\s+wstecz\b", r"\1 się"),
    (r"\b[Pp]ełn(?:y|ego|emu|ym|a|ą|ej|e|ych|ymi)\s+(komplet(?:y|ów|om|ami|ach)?)\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Gg]łówn(?:y|ego|emu|ym|a|ą|ej|e|ych|ymi)\s+(priorytet(?:y|ów|om|ami|ach)?)\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b((?:[A-Za-ząćęłńóśźż0-9]+\s+)?(?:godzin[aeyęi]?|miesiąc[ae]?|miesięcy|dni[aey]?|tydzień|tygodni[ae]?|rok[u]?|lat(?:a)?))\s+czasu\b", r"\1"),
    (r"\b([Pp]rzedzia[łl][a-ząćęłńóśźż]*)\s+czasu\b", r"\1"),
    (r"\b([Oo]kres[a-ząćęłńóśźż]*)\s+czasu\b", r"\1"),
    (r"\b[Ww]\s+dniu\s+dzisiejszym\b", "dzisiaj"),
    (r"\b[Dd]zień\s+dzisiejszy\b", "dzisiejszy dzień"),
    (r"\b[Nn]a\s+dzień\s+dzisiejszy\b", lambda m: "Na dziś" if m.group(0)[0].isupper() else "na dziś"),
    (r"\b[Pp]otencjaln(?:e|ych|ym|ymi)\s+(możliwoś(?:ć|ci|cią|ciom|ciami|ciach))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Ww]zajemn(?:a|ej|ą|e|ych|ym|ymi)\s+(współprac(?:a|y|ę|ą|ie|om|ami))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Ww]zajemn(?:a|ej|ą|e|ych|ym|ymi)\s+(relacj(?:a|e|i|om|ami|ach|ę|ą))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Ww]zajemn(?:y|ego|emu|ym)\s+(szacunk(?:u|iem)?|szacunek)\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Ww]zajemn(?:a|ej|ą)\s+(sympati(?:a|i|ę|ą))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Mm]artw(?:e|ych|ym|ymi)\s+(zwłok(?:i|ach|ami|om))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Ii]nn(?:a|ej|ą|e|ych|ym|ymi)\s+(alternatyw(?:a|y|om|ami|ach|ę))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b[Rr]óżn(?:e|ych|ym|ymi|a|ej|ą)\s+(wariant(?:y|ów|om|ami|ach)?)\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1)),
    (r"\b([Ff]akt(?:y|ów|om|ami|ach)?)\s+autentyczn(?:e|ych|ym|ymi)\b", r"\1"),
    (r"\b([Aa]kwen(?:y|ów|om|ami|ach)?)\s+wodn(?:y|e|ych|ym|ymi)\b", r"\1"),
    (r"\b([Kk]ontynuowa(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+dalej\b", r"\1"),
    (r"\b([Pp]owtórzy(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+(?:znowu|ponownie)\b", r"\1"),
    (r"\b([Pp]onownie)\s+powtórzy(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?\b", lambda m: "Powtórzyć" if m.group(0)[0].isupper() else "powtórzyć"),
    (r"\b[Mm]iesiąc\s+(styczeń|luty|marzec|kwiecień|maj|czerwiec|lipiec|sierpień|wrzesień|październik|listopad|grudzień)\b", r"\1"),
    (r"\b[Ww]\s+miesiącu\s+(styczniu|lutym|marcu|kwietniu|maju|czerwcu|lipcu|sierpniu|wrześniu|październiku|listopadzie|grudniu)\b", r"w \1"),
    (r"\b[Cc]iężki\s+orzech\s+do\s+zgryzienia\b", "twardy orzech do zgryzienia"),
    (r"\b[Cc]iężkim\s+orzechem\s+do\s+zgryzienia\b", "twardym orzechem do zgryzienia"),
    (r"\b([Oo]dnie(?:ść|sie|siemy|siecie|są)|[Oo]dni[óo]sł|[Oo]dniosł[aoy]|[Oo]dnieśli|[Oo]dniosły|[Oo]dniosłem|[Oo]dniosłam|[Oo]dniosłeś|[Oo]dniosłaś)\s+porażk[ęi]\b",
     lambda m: m.group(0).replace("odnie", "ponie").replace("Odnie", "Ponie").replace("odnió", "ponió").replace("Odnió", "Ponió").replace("odnios", "ponios").replace("Odnios", "Ponios")),
    (r"\b([Oo]dgr(?:ywa|ywał|ywała|ywali|ywają|ywać)|[Oo]degr(?:ać|ał|ała|ało|ali|ały))\s+znaczenie\b", _fix_odegrac_znaczenie),
    (r"\b[Pp]odda(?:ć|ł|ła|ło|li|ły|je|ją)\s+pod\s+wątpliwość\b", lambda m: m.group(0).replace("odda", "oda").replace("Odda", "Oda").replace("pod wątpliwość", "w wątpliwość")),
    (r"\b([Pp])rzeznaczy(ć|ł|ła|ło|li|ły|łem|łam|łeś|łaś)\s+na\s+straty\b", lambda m: ("Spisa" if m.group(1) == "P" else "spisa") + m.group(2) + " na straty"),
    (r"\b([Pp])rzeznacz(ę|ysz|y|ymy|ycie|ą)\s+na\s+straty\b", lambda m: ("Spisz" if m.group(1) == "P" else "spisz") + m.group(2) + " na straty"),
    (r"\b([Kk]upi(?:ć|ł|ła|ło|li|ły|my|sz)?|[Kk]upuj(?:e|emy|ą|esz)?)\s+(?:trochę\s+)?czasu\b", _fix_kupic_czas),
    # Somatic possessive pronoun pleonasm: 'boli mnie moja głowa' -> 'boli mnie głowa'
    (r"\b([Bb]oli\s+(?:mnie|cię|go|ją|nas|was|ich))\s+(?:moja|twój|twoja|twoje|jego|jej|nasza|nasz|wasz|wasza|ich|swoja|swój|swoje)\s+(głow[aęy]|serce|brzuch|nog[aęyie]|ręk[aęyie]|plecy|ramię|ramiona|ucho|uszy|gardło|ząb|zęby)\b", r"\1 \2"),
    (r"\b([Zz]łama[ł|łem|łam|łeś|łaś|li|ły])\s+(?:swoją|moją|twoją|jego|jej|naszą|waszą|ich)\s+(nogę|rękę|palec|kość|żebro)\b", r"\1 \2"),
    (r"\b([Oo]tw[óo]rz(?:ył|yła|yli|yłam|yłem|yłeś|yłaś|cie)?|[Zz]amkn(?:ij|ijcie|ął|ęła|ęli|ęłam|ęłem|ęłaś|ełeś))\s+(?:swoje|twoje|moje|jego|jej|nasze|wasze|ich)\s+(oczy|powieki|usta)\b", r"\1 \2"),
    # Absolute grammatical government and gender (Filar IV / X)
    (r"\b([Cc]zarn[a-ząćęłńóśźż]*)\s+posok(?:u|iem|owi|a)\b", lambda m: ("Czarna posoka" if m.group(0)[0].isupper() else "czarna posoka")),
    (r"\b[Zz]\s+czarnego\s+posoku\b", "z czarnej posoki"),
    (r"\b[Pp]rzez\s+czarny\s+posok\b", "przez czarną posokę"),
    (r"\b[Mm]am\s+przez\s+(?:to|coś)\s+uraz\b", lambda m: "Mam do tego uraz" if m.group(0)[0].isupper() else "mam do tego uraz"),
    (r"\b[Dd]wa\s+tysiące\s+wystarczy\b", lambda m: "Dwa tysiące wystarczą" if m.group(0)[0].isupper() else "dwa tysiące wystarczą"),
    (r"\b[Pp]ółtorej\s+roku\b", lambda m: "Półtora roku" if m.group(0)[0].isupper() else "półtora roku"),
    # Kakegoe physical/festive interjections (Filar XVIII / CLXIV)
    (r"\bTamaya[!]*", "Ale widok!"),
    (r"\b[Oo]ttotto[\.!\?…]*", "Ło, ło, ło...!"),
    # Absolute dialogic calques (Filar IV / CLIII / CLXVI)
    (r"\b[Zz]rób\s+swoje\s+najlepsze\b", lambda m: "Daj z siebie wszystko" if m.group(0)[0].isupper() else "daj z siebie wszystko"),
    (r"\b[Zz]róbcie\s+swoje\s+najlepsze\b", lambda m: "Dajcie z siebie wszystko" if m.group(0)[0].isupper() else "dajcie z siebie wszystko"),
    (r"\b[Dd]obrej\s+nocy\b", lambda m: "Dobranoc" if m.group(0)[0].isupper() else "dobranoc"),
    # Anti-pivot fansub cliché eradication (Filar CLXVI)
    (r"\b([Ww])ita(j|jcie|m|my)\s+z\s+powrotem(!|\.|\.\.\.|,)?(?=\s|$|[,\.!\?])", lambda m: ("Witajcie!" if m.group(2) == "jcie" else ("Witamy!" if m.group(2) == "my" else ("Witam!" if m.group(2) == "m" else "Witaj!")))),
    (r"\b([Nn])ie\s+ma\s+mowy,?\s+(?:że|a)?by(śmy|ście|m|ś)?\b", lambda m: ("Wykluczone, by" if m.group(1).isupper() else "wykluczone, by") + (m.group(2) or "")),
    (r"\b([Mm](?:am|asz|a|amy|acie|ają|iałem|iałam|iał|iała|iało|ieliśmy|iałyśmy|ieli|iały|iałby|iałaby|iałoby|ieliby|iałyby)|[Bb]ęd(?:ę|ziesz|zie|ziemy|ziecie|dą)\s+mieć)\s+taką\s+nadzieję\b", r"\1 nadzieję"),
    (r"\b([Mm](?:am|asz|a|amy|acie|ają|iałem|iałam|iał|iała|iało|ieliśmy|iałyśmy|ieli|iały|iałby|iałaby|iałoby|ieliby|iałyby)|[Bb]ęd(?:ę|ziesz|zie|ziemy|ziecie|dą)\s+mieć)\s+nadzieję\s+na\s+to\b", r"\1 nadzieję"),
    # Japanese false proper noun & honorific titular repair (Filar II / Kanon)
    (r"(^|[^\w]|\\[Nnh])Ouji([!\?…]+)", r"\g<1>Książę\g<2>"),
    (r"(^|[^\w]|\\[Nnh])ouji([!\?…]+)", r"\g<1>książę\g<2>"),
    # Conversational continuation calque (Filar IV / CLVI)
    (r"(^|[^\w]|\\[Nnh])([Ii]|[Aa])\s+co\s+z\s+tego\?(\s*\\N\s*|\s+)(?=[Tt]o\s+wy\b|[Cc]hodzicie\b|[Jj]esteście\b|[Cc]o\s+było\b|[Cc]o\s+dalej\b|[Jj]ak\s+to\b)", r"\g<1>\g<2> co?\g<3>"),
    # Manga canon titular enforcement: 'Książę Kaiju' -> 'Potworny Królewicz' (Filar II / Kanon)
    (r"(^|[^\w]|\\[Nnh])([Kk])siążę\s+[Kk]aiju\b", lambda m: ("Potworny Królewicz" if m.group(2) == "K" else "potworny królewicz")),
    (r"(^|[^\w]|\\[Nnh])([Kk])sięcia\s+[Kk]aiju\b", lambda m: ("Potwornego Królewicza" if m.group(2) == "K" else "potwornego królewicza")),
    (r"(^|[^\w]|\\[Nnh])([Kk])sięciu\s+[Kk]aiju\b", lambda m: ("Potwornemu Królewiczowi" if m.group(2) == "K" else "potwornemu królewiczowi")),
    (r"(^|[^\w]|\\[Nnh])([Kk])sięciem\s+[Kk]aiju\b", lambda m: ("Potwornym Królewiczem" if m.group(2) == "K" else "potwornym królewiczem")),
    # Otaku slang adaptation: 'Kuro-taso' -> 'Kuroe' (Filar II / Kanon)
    (r"(^|[^\w]|\\[Nnh])Kuro-?taso\b", r"\g<1>Kuroe"),
    (r"(^|[^\w]|\\[Nnh])kuro-?taso\b", r"\g<1>kuroe"),
    # Binary alternative comma eradication: 'w kapciach, czy bez' -> 'w kapciach czy bez' (Filar XCI)
    (r"\b([A-Za-ząćęłńóśźż0-9]+),\s+czy\s+(bez|nie|tak)\b", r"\1 czy \2"),
    # Trailing cut-off speech attached dash: 'Rin–' -> 'Rin...' (Filar XCI)
    (r"([A-Za-ząćęłńóśźż])–(?=\s*\\N|\s*$|[!\?…])", r"\1..."),
    # Deictic temporal syntax normalizations (Filar CLXVIII)
    (r"\b([Pp])ojutrzejsz(?:y|ą|a|e|ego|ej|emu|ym|ych|ymi)?\s+([a-ząćęłńóśźż]+)\b",
     lambda m: (f"{m.group(2)} pojutrze" if m.group(1) == "p" else f"{m.group(2).capitalize()} pojutrze")),
    (r"\b([Pp])rzedwczorajsz(?:y|ą|a|e|ego|ej|emu|ym|ych|ymi)?\s+([a-ząćęłńóśźż]+)\b",
     lambda m: (f"{m.group(2)} sprzed dwóch dni" if m.group(1) == "p" else f"{m.group(2).capitalize()} sprzed dwóch dni")),
    (r"\b([Ww])\s+dzisiejszy\s+wieczór\b", lambda m: "Dziś wieczorem" if m.group(1) == "W" else "dziś wieczorem"),
    (r"\b([Ww])\s+jutrzejszy\s+poranek\b", lambda m: "Jutro rano" if m.group(1) == "W" else "jutro rano"),
    (r"\b([Ww])e\s+wczorajszy\s+wieczór\b", lambda m: "Wczoraj wieczorem" if m.group(1) == "W" else "wczoraj wieczorem"),
    (r"\b([Ww])\s+dzisiejszą\s+noc\b", lambda m: "Dziś w nocy" if m.group(1) == "W" else "dziś w nocy"),
    (r"\b([Pp])rzyszłotygodniow(?:y|ą|a|e|ego|ej|emu|ym|ych|ymi)?\s+([a-ząćęłńóśźż]+)\b",
     lambda m: (f"{m.group(2)} w przyszłym tygodniu" if m.group(1) == "p" else f"{m.group(2).capitalize()} w przyszłym tygodniu")),
    # Eradication of youth slang 'żenada' in dialogue (Filar CLXX)
    (r"\b([Aa]le|[Cc]o\s+za)\s+żenada[!\?…\.]*", lambda m: ("Ale marudzisz..." if m.group(1)[0].isupper() else "ale marudzisz...")),
    (r"^\s*([Żż]enada)[!\?…\.]*\s*$", lambda m: ("Ale marudzisz..." if m.group(1)[0].isupper() else "ale marudzisz...")),
    (r"(?<!\bbas\s)(?<!\bperkusja\s)(?<!\bi\s)\b[Ii]\s+gitara[!]+", lambda m: "Doskonale!" if m.group(0)[0].isupper() else "doskonale!"),
    (r"\b[Ss]tul\s+pysk\b", lambda m: "Zamilcz" if m.group(0)[0].isupper() else "zamilcz"),
    (r"\b[Zz]mywajmy\s+się\s+stąd\b", lambda m: "Uciekajmy stąd" if m.group(0)[0].isupper() else "uciekajmy stąd"),
    (r"\b[Zz]mywamy\s+się\s+stąd\b", lambda m: "Uciekamy stąd" if m.group(0)[0].isupper() else "uciekamy stąd"),
    (r"\b[Zz]mywaj\s+się\s+stąd\b", lambda m: "Uciekaj stąd" if m.group(0)[0].isupper() else "uciekaj stąd"),
    (r"\b[Kk]łamstwo\s+jak\s+byk\b", lambda m: "Bezczelne kłamstwo" if m.group(0)[0].isupper() else "bezczelne kłamstwo"),
    (r"\b[Pp]rzejmuję\s+stery\b", lambda m: "Teraz ja mówię" if m.group(0)[0].isupper() else "teraz ja mówię"),
    (r"\b[Dd]la\s+zabicia\s+czasu\b", lambda m: "Dla rozrywki" if m.group(0)[0].isupper() else "dla rozrywki"),
    (r"\b[Ww]ylec(?:ieć|iał|iała|ieli)\s+ze\s+szkoły\b", "zostać wydalonym ze szkoły"),
    # Closed invariant PWN preposition-pronoun phonetic forms and idioms (0.00 PLN)
    (r"\b([Dd]la)\s+mię\b", lambda m: "Dla mnie" if m.group(1)[0].isupper() else "dla mnie"),
    (r"\b([Oo]de)\s+mie\b", lambda m: "Ode mnie" if m.group(1)[0].isupper() else "ode mnie"),
    (r"\b([Oo]d)\s+mnie\b", lambda m: "Ode mnie" if m.group(1)[0].isupper() else "ode mnie"),
    (r"\b([Zz])\s+mną\b", lambda m: "Ze mną" if m.group(1)[0].isupper() else "ze mną"),
    (r"\b([Pp]rzed)\s+mną\b", lambda m: "Przede mną" if m.group(1)[0].isupper() else "przede mną"),
    (r"\b([Ww])\s+każdym\s+bądź\s+razie\b", lambda m: "W każdym razie" if m.group(1)[0].isupper() else "w każdym razie"),
    (r"\b([Bb])ez\s+jaj[!]+", lambda m: "To jakieś kpiny!" if m.group(1)[0].isupper() else "to jakieś kpiny!"),
    (r"\b([Gg])uzik\s+mnie\s+to\s+obchodzi\b", lambda m: "Nic mnie to nie obchodzi" if m.group(1)[0].isupper() else "nic mnie to nie obchodzi"),
    (r"\b([Pp])omiędzy\s+tobą\s+i\s+mną\b", lambda m: "Między nami" if m.group(1)[0].isupper() else "między nami"),
    (r"\b([Pp])omiędzy\s+nami\b", lambda m: "Między nami" if m.group(1)[0].isupper() else "między nami"),
    (r"\b([Ww])\s+mrugnięciu\s+oka\b", lambda m: "W mgnieniu oka" if m.group(1)[0].isupper() else "w mgnieniu oka"),
]


def replace_with_case_preservation(pattern: str, replacement: str, text: str) -> str:
    """Replaces matches of pattern with replacement, preserving initial capitalization of matched token."""
    def _sub_cb(m):
        orig = m.group(0)
        if orig and orig[0].isupper():
            return replacement[0].upper() + replacement[1:]
        return replacement.lower()
    return re.sub(pattern, _sub_cb, text, flags=re.IGNORECASE)


VERB_PAT_MIEĆ = r"nie\s+(?:mam|masz|ma|mamy|macie|mają|miał(?:em|am|eś|aś|a|o)?|miel(?:i|iśmy|iście)|miały(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:mieć|miał(?:a)?))"
VERB_PAT_WIDZIEĆ = r"nie\s+(?:widz(?:ę|isz|i|imy|icie|ą)|widział(?:em|am|eś|aś|a|o)?|widziel(?:i|iśmy|iście)|widziały(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:widzieć|widział(?:a)?))"
VERB_PAT_CZUĆ = r"nie\s+(?:czuj(?:ę|esz|e|emy|ecie|ą)|czuł(?:em|am|eś|aś|a|o)?|czul(?:i|iśmy|iście)|czuły(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:czuć|czuł(?:a)?))"
VERB_PAT_ZNAĆ = r"nie\s+(?:zna(?:m|sz|my|cie|ją)?|znał(?:em|am|eś|aś|a|o)?|znal(?:i|iśmy|iście)|znały(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:znać|znał(?:a)?))"
VERB_PAT_PAMIĘTAĆ = r"nie\s+(?:pamięta(?:m|sz|my|cie|ją)?|pamiętał(?:em|am|eś|aś|a|o)?|pamiętal(?:i|iśmy|iście)|pamiętały(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:pamiętać|pamiętał(?:a)?))"
VERB_PAT_SŁYSZEĆ = r"nie\s+(?:słysz(?:ę|ysz|y|ymy|ycie|ą)|słyszał(?:em|am|eś|aś|a|o)?|słyszel(?:i|iśmy|iście)|słyszały(?:śmy|ście)?|będ(?:ę|ziesz|zie|ziemy|ziecie|ą)\s+(?:słyszeć|słyszał(?:a)?))"
VERB_PAT_SPRAWIAĆ = r"nie\s+(?:sprawia(?:m|sz|my|cie|ją)?|sprawiał(?:em|am|eś|aś|a|o)?|sprawi(?:ł|ła|ło|li|ły|ć)?)"

TRANSITIVE_NEGATION_BASE_COLLOCATIONS = [
    # (verb_pattern, direct_object_pattern, genitive_replacement)
    # mieć + B. -> D.
    (VERB_PAT_MIEĆ, r"czas", "czasu"),
    (VERB_PAT_MIEĆ, r"wybór", "wyboru"),
    (VERB_PAT_MIEĆ, r"ochotę", "ochoty"),
    (VERB_PAT_MIEĆ, r"nadzieję", "nadziei"),
    (VERB_PAT_MIEĆ, r"siłę", "siły"),
    (VERB_PAT_MIEĆ, r"pojęcie", "pojęcia"),
    (VERB_PAT_MIEĆ, r"powód", "powodu"),
    (VERB_PAT_MIEĆ, r"problem", "problemu"),
    (VERB_PAT_MIEĆ, r"wątpliwość", "wątpliwości"),
    # znać + B. -> D.
    (VERB_PAT_ZNAĆ, r"tę\s+prawdę", "tej prawdy"),
    (VERB_PAT_ZNAĆ, r"odpowiedź", "odpowiedzi"),
    (VERB_PAT_ZNAĆ, r"litość", "litości"),
    (VERB_PAT_ZNAĆ, r"granice", "granic"),
    # widzieć + B. -> D.
    (VERB_PAT_WIDZIEĆ, r"żaden\s+sens", "żadnego sensu"),
    (VERB_PAT_WIDZIEĆ, r"inny\s+sposób", "innego sposobu"),
    (VERB_PAT_WIDZIEĆ, r"sens", "sensu"),
    (VERB_PAT_WIDZIEĆ, r"przeszkody", "przeszkód"),
    (VERB_PAT_WIDZIEĆ, r"powód", "powodu"),
    (VERB_PAT_WIDZIEĆ, r"problem", "problemu"),
    # czuć + B. -> D.
    (VERB_PAT_CZUĆ, r"strach", "strachu"),
    (VERB_PAT_CZUĆ, r"ból", "bólu"),
    (VERB_PAT_CZUĆ, r"litość", "litości"),
    # pamiętać + B. -> D.
    (VERB_PAT_PAMIĘTAĆ, r"ten\s+dzień", "tego dnia"),
    (VERB_PAT_PAMIĘTAĆ, r"tę\s+chwilę", "tej chwili"),
    # słyszeć + B. -> D.
    (VERB_PAT_SŁYSZEĆ, r"żaden\s+głos", "żadnego głosu"),
    (VERB_PAT_SŁYSZEĆ, r"głos", "głosu"),
    # sprawiać + B. -> D.
    (VERB_PAT_SPRAWIAĆ, r"problem", "problemu"),
    (VERB_PAT_SPRAWIAĆ, r"ból", "bólu"),
]

# Safe conversational adverbs/particles (<= 2 words, strictly no commas)
NEGATION_ADVERBIAL_SPAN = r"(?:\s+(?:już|teraz|wcale|ani\s+trochę|tutaj|tu|tam|wciąż|nadal|przecież|nawet|zresztą|zbytnio|w\s+tym|chyba|naprawdę))?"

TRANSITIVE_NEGATION_REPLACEMENTS = [
    (r"\bnie\s+mam\s+czas\b", "nie mam czasu"),
    (r"\bnie\s+mam\s+wybór\b", "nie mam wyboru"),
    (r"\bnie\s+mam\s+ochotę\b", "nie mam ochoty"),
    (r"\bnie\s+mam\s+nadzieję\b", "nie mam nadziei"),
    (r"\bnie\s+mam\s+siłę\b", "nie mam siły"),
    (r"\bnie\s+znam\s+tę\s+prawdę\b", "nie znam tej prawdy"),
    (r"\bnie\s+znam\s+odpowiedź\b", "nie znam odpowiedzi"),
    (r"\bnie\s+zna\s+litość\b", "nie zna litości"),
    (r"\bnie\s+zna\s+granice\b", "nie zna granic"),
    (r"\bnie\s+widzę\s+żaden\s+sens\b", "nie widzę żadnego sensu"),
    (r"\bnie\s+widzę\s+inny\s+sposób\b", "nie widzę innego sposobu"),
    (r"\bnie\s+widzi\s+przeszkody\b", "nie widzi przeszkód"),
    (r"\bnie\s+pamiętam\s+ten\s+dzień\b", "nie pamiętam tego dnia"),
    (r"\bnie\s+czuję\s+strach\b", "nie czuję strachu"),
]


def sanitize_genitive_of_negation(text: str) -> str:
    """
    Enforces Genitive of Negation on closed high-certainty transitive verb collocations
    including optional conversational adverbial/particle insertions (<= 2 words, no commas) (Filar CLXXXVIII / 0.00 PLN).
    Preserves case capitalization.
    """
    if not text:
        return ""
    res = text
    for verb_pat, obj_pat, gen_target in TRANSITIVE_NEGATION_BASE_COLLOCATIONS:
        pat = rf"\b({verb_pat})({NEGATION_ADVERBIAL_SPAN})\s+({obj_pat})\b"
        def _sub_neg(m, tgt=gen_target):
            v_matched = m.group(1)
            adv_matched = m.group(2) or ""
            obj_matched = m.group(3)
            repl_tgt = tgt[0].upper() + tgt[1:] if obj_matched[0].isupper() else tgt
            return f"{v_matched}{adv_matched} {repl_tgt}"
        res = re.sub(pat, _sub_neg, res, flags=re.IGNORECASE)
    return res


CANON_OBLIQUE_CORRECTIONS = [
    # Narzędnik po z/ze/przed/nad/pod/za/między
    (r"\b([Zz]e?|[Pp]rzed|[Nn]ad|[Pp]od|[Zz]a|[Mm]iędzy)\s+(?:Aura\s+Gilotyna|Aurą\s+Gilotyna|Aura\s+Gilotyną)\b", r"\1 Aurą Gilotyną"),
    (r"\b([Zz]e?|[Pp]rzed|[Nn]ad|[Pp]od|[Zz]a|[Mm]iędzy)\s+(?:Wielki\s+Chan|Wielkim\s+Chan|Wielki\s+Chanem)\b", r"\1 Wielkim Chanem"),
    (r"\b([Zz]e?|[Pp]rzed|[Nn]ad|[Pp]od|[Zz]a|[Mm]iędzy)\s+(?:Król|Królem)\s+Demonów\b", r"\1 Królem Demonów"),
    (r"\b([Zz]e?|[Pp]rzed|[Nn]ad|[Pp]od|[Zz]a|[Mm]iędzy)\s+(?:Czarny\s+Rycerz|Czarnym\s+Rycerz|Czarny\s+Rycerzem)\b", r"\1 Czarnym Rycerzem"),

    # Dopełniacz po u/do/od/dla/bez/zza
    (r"\b([Dd]la|[Uu]|[Oo]d|[Dd]o|[Bb]ez|[Zz]za)\s+(?:Aura\s+Gilotyna|Aury\s+Gilotyna|Aura\s+Gilotyny)\b", r"\1 Aury Gilotyny"),
    (r"\b([Dd]la|[Uu]|[Oo]d|[Dd]o|[Bb]ez|[Zz]za)\s+(?:Wielki\s+Chan|Wielkiego\s+Chan|Wielki\s+Chana)\b", r"\1 Wielkiego Chana"),
    (r"\b([Dd]la|[Uu]|[Oo]d|[Dd]o|[Bb]ez|[Zz]za)\s+(?:Król|Króla)\s+Demonów\b", r"\1 Króla Demonów"),
    (r"\b([Dd]la|[Uu]|[Oo]d|[Dd]o|[Bb]ez|[Zz]za)\s+(?:Czarny\s+Rycerz|Czarnego\s+Rycerz|Czarny\s+Rycerza)\b", r"\1 Czarnego Rycerza"),

    # Celownik po przeciwko/ku/dzięki
    (r"\b([Pp]rzeciwko|[Kk]u|[Dd]zięki)\s+(?:Aura\s+Gilotyna|Aurze\s+Gilotyna|Aura\s+Gilotynie)\b", r"\1 Aurze Gilotynie"),
    (r"\b([Pp]rzeciwko|[Kk]u|[Dd]zięki)\s+(?:Wielki\s+Chan|Wielkiemu\s+Chan|Wielki\s+Chanowi)\b", r"\1 Wielkiemu Chanowi"),
    (r"\b([Pp]rzeciwko|[Kk]u|[Dd]zięki)\s+(?:Król|Królowi)\s+Demonów\b", r"\1 Królowi Demonów"),
    (r"\b([Pp]rzeciwko|[Kk]u|[Dd]zięki)\s+(?:Czarny\s+Rycerz|Czarnemu\s+Rycerz|Czarny\s+Rycerzowi)\b", r"\1 Czarnemu Rycerzowi"),

    # Biernik po przez
    (r"\b([Pp]rzez)\s+(?:Aura\s+Gilotyna|Aurę\s+Gilotyna|Aura\s+Gilotynę)\b", r"\1 Aurę Gilotynę"),
    (r"\b([Pp]rzez)\s+(?:Wielki\s+Chan|Wielkiego\s+Chan|Wielki\s+Chana)\b", r"\1 Wielkiego Chana"),
    (r"\b([Pp]rzez)\s+(?:Król|Króla)\s+Demonów\b", r"\1 Króla Demonów"),
    (r"\b([Pp]rzez)\s+(?:Czarny\s+Rycerz|Czarnego\s+Rycerz|Czarny\s+Rycerza)\b", r"\1 Czarnego Rycerza"),

    # Miejscownik po o/przy
    (r"\b([Oo]|[Pp]rzy)\s+(?:Aura\s+Gilotyna|Aurze\s+Gilotyna|Aura\s+Gilotynie)\b", r"\1 Aurze Gilotynie"),
    (r"\b([Oo]|[Pp]rzy)\s+(?:Wielki\s+Chan|Wielkim\s+Chan|Wielki\s+Chanie)\b", r"\1 Wielkim Chanie"),
    (r"\b([Oo]|[Pp]rzy)\s+(?:Król|Królu)\s+Demonów\b", r"\1 Królu Demonów"),
    (r"\b([Oo]|[Pp]rzy)\s+(?:Czarny\s+Rycerz|Czarnym\s+Rycerz|Czarny\s+Rycerzu)\b", r"\1 Czarnym Rycerzu"),
]


def sanitize_canon_compound_oblique_cases(text: str) -> str:
    """
    Corrects frozen nominative compound canon syntagmas governed by prepositions (Filar CLXXXVIII / 0.00 PLN).
    'z Aura Gilotyna' -> 'z Aurą Gilotyną', 'dla Wielki Chan' -> 'dla Wielkiego Chana'.
    """
    if not text:
        return ""
    res = text
    for pat, repl in CANON_OBLIQUE_CORRECTIONS:
        res = re.sub(pat, repl, res)
    return res


def sanitize_lexical_text(text: str) -> str:
    """Sanitizes text against known LLM/OCR typos and deformed Polish words (Filar CLXIV/CLXX)."""
    if not text:
        return ""
    res = text
    for pat, repl in TYPO_NORMALIZATIONS:
        res = re.sub(pat, repl, res)

    # Subject nominative title repair: 'pan Eftala zniszczył' -> 'pan Eftal zniszczył', 'Mistrz Tondena minoru nie zdążył' -> 'Mistrz Tonden Minoru nie zdążył'
    TITLES_SUBJECT_PAT = r"[Pp]an|[Pp]ani|[Mm]istrz|[Pp]rofesor|[Dd]oktor|[Pp]isarz|[Rr]eżyser|[Rr]edaktor|[Aa]utor|[Mm]angaka|[Ss]ensei"
    CANONICAL_A_NAMES = {
        "akira", "shira", "soma", "gaara", "ashitaka", "kiba", "kenta",
        "ryoma", "hanza", "koba", "soya", "toma", "genga", "teshima",
        "yamada", "maeda", "takeda", "matsuda", "kuroda", "sanada",
        "shimada", "okada", "ishida", "kawada", "ueda", "baba", "honda", "oda", "aida"
    }
    POLISH_ADVERBS = {
        "faktycznie", "naprawdę", "bardzo", "właśnie", "wczoraj", "dzisiaj", "jutro",
        "wtedy", "teraz", "zaraz", "nagle", "znowu", "ponownie", "dobrze", "źle",
        "szybko", "wolno", "także", "również", "jednak", "przecież", "wcale", "zawsze", "nigdy", "osobiście"
    }

    # Case 1: Title + Surname + Given Name + Verb (e.g. 'Mistrz Tondena minoru\Nnie zdążył' -> 'Mistrz Tonden Minoru\Nnie zdążył')
    def _fix_nominative_two_part_title_subject(m):
        prefix = m.group(1)
        title = m.group(2)
        sep1 = m.group(3)
        surname_stem = m.group(4)
        sep2 = m.group(5)
        given_name = m.group(6)
        sep3 = m.group(7)
        verb = m.group(8)
        if title.lower() == "pani" or given_name.lower() in POLISH_ADVERBS:
            return m.group(0)
        full_surname = (surname_stem + "a").lower()
        if full_surname in CANONICAL_A_NAMES or full_surname.endswith(("da", "ta", "ka", "ma", "ba")):
            clean_surname = surname_stem + "a"
        else:
            clean_surname = surname_stem
        clean_given = given_name.capitalize()
        return f"{prefix}{title}{sep1}{clean_surname}{sep2}{clean_given}{sep3}{verb}"

    res = re.sub(
        rf"(^|[^\w]|\\[Nnh])({TITLES_SUBJECT_PAT})(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]*[bcdfghjklmnprstvwxz])a(\s+|\\[Nnh]+)([A-Za-ząćęłńóśźż]+)(\s+|\\[Nnh]+)((?:nie\s+)?[a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
        _fix_nominative_two_part_title_subject,
        res
    )

    # Case 2: Title + Single Name + Verb (e.g. 'pan Eftala zniszczył' -> 'pan Eftal zniszczył')
    def _fix_nominative_title_subject(m):
        prefix = m.group(1)
        title = m.group(2)
        sep1 = m.group(3)
        name_stem = m.group(4)
        sep2 = m.group(5)
        verb = m.group(6)
        if title.lower() == "pani":
            return m.group(0)
        full_name = (name_stem + "a").lower()
        if full_name in CANONICAL_A_NAMES or full_name.endswith(("da", "ta", "ka", "ma", "ba")):
            return m.group(0)
        return f"{prefix}{title}{sep1}{name_stem}{sep2}{verb}"

    res = re.sub(
        rf"(^|[^\w]|\\[Nnh])({TITLES_SUBJECT_PAT})(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]*[bcdfghjklmnprstvwxz])a(\s+|\\[Nnh]+)((?:nie\s+)?[a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
        _fix_nominative_title_subject,
        res
    )
    res = sanitize_pronominal_somatic_possession(res)
    res = sanitize_deictic_motion_vector(res)
    res = sanitize_sensory_pleonasm(res)
    res = sanitize_closed_idioms_and_prepositions(res)
    return res


def sanitize_pronominal_somatic_possession(text: str) -> str:
    """
    Eliminates English possessive pronoun calques before body parts,
    personal belongings, and close relatives (Filar CLXXVII / Pronominal Decoupling).
    Deterministic offline 0.00 PLN enforcement.
    """
    if not text:
        return ""
    res = text

    # Prepositional somatic phrases: w moim sercu -> w sercu, w mojej głowie -> w głowie
    SOMATIC_PREPOSITIONS = [
        (r"\b([Ww])\s+(?:moim|twoim|swoim|jego|jej|naszym|waszym)\s+sercu\b", r"\1 sercu"),
        (r"\b([Ww])\s+(?:mojej|twojej|swojej|jego|jej|naszej|waszej)\s+głowie\b", r"\1 głowie"),
        (r"\b([Ww])\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+myślach\b", r"\1 myślach"),
        (r"\b([Ww])\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+oczach\b", r"\1 oczach"),
        (r"\b([Ww])\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+żyłach\b", r"\1 żyłach"),
        (r"\b([Ww])\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+ramionach\b", r"\1 ramionach"),
        (r"\b([Nn]a)\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+plecach\b", r"\1 plecach"),
        (r"\b([Nn]a)\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+ramionach\b", r"\1 ramionach"),
        (r"\b([Zz])\s+(?:moich|twoich|swoich|jego|jej|naszych|waszych)\s+ust\b", r"\1 ust"),
    ]
    for pat, repl in SOMATIC_PREPOSITIONS:
        res = re.sub(pat, repl, res)

    # Imperatives and somatic verbs:
    VERBAL_SOMATIC = [
        (r"\b(zamknij|zamknijcie|otwórz|otwórzcie|przymknij|przymknijcie)\s+(?:twoje|swoje|twoich|swoich)\s+(oczy)\b", r"\1 \2"),
        (r"\b(podnieś|podnieście|wznieś|wznieście|załóż|załóżcie|rozłóż|rozłóżcie|opuść|opuśćcie|umyj|umyjcie)\s+(?:twoje|swoje|twoich|swoich)\s+(ręce|dłonie|ramiona)\b", r"\1 \2"),
        (r"\b(zdejmij|zdejmijcie|włóż|włóżcie|załóż|załóżcie|ubierz|ubierzcie)\s+(?:twoje|swoje|twój|twą|twoją)\s+(buty|kurtkę|płaszcz|ubranie|czapkę)\b", r"\1 \2"),
    ]
    for pat, repl in VERBAL_SOMATIC:
        res = re.sub(pat, repl, res, flags=re.IGNORECASE)

    # Life saving: uratowałeś moje życie -> ocaliłeś mi życie / uratowałeś mi życie
    res = re.sub(r"\b(uratował|uratowała|uratowałeś|uratowałaś|ocalił|ocaliła|ocaliłeś|ocaliłaś|ratując|ocalając)\s+moje\s+życie\b", r"\1 mi życie", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(uratował|uratowała|uratowałeś|uratowałaś|ocalił|ocaliła|ocaliłeś|ocaliłaś)\s+twoje\s+życie\b", r"\1 ci życie", res, flags=re.IGNORECASE)

    # Relational possession (family):
    RELATIONAL_PATTERNS = [
        (r"\b([Zz]|ze|dla|do|u|od)\s+moją\s+(matką|siostrą|córką|babcią)\b", r"\1 \2"),
        (r"\b([Zz]|ze|dla|do|u|od)\s+moim\s+(ojcem|bratem|synem|dziadkiem)\b", r"\1 \2"),
        (r"\b([Zz]|ze|dla|do|u|od)\s+moimi\s+(rodzicami|braćmi|siostrami)\b", r"\1 \2"),
        (r"\b([Zz]|ze|dla|do|u|od)\s+twoją\s+(matką|siostrą|córką|babcią)\b", r"\1 \2"),
        (r"\b([Zz]|ze|dla|do|u|od)\s+twoim\s+(ojcem|bratem|synem|dziadkiem)\b", r"\1 \2"),
        (r"\b([Zz]|ze|dla|do|u|od)\s+twoimi\s+(rodzicami|braćmi|siostrami)\b", r"\1 \2"),
    ]
    for pat, repl in RELATIONAL_PATTERNS:
        res = re.sub(r"(?<!a nie\s)(?<!niż\s)(?<!zamiast\s)" + pat, repl, res, flags=re.IGNORECASE)

    # Causal calque: z mojego powodu -> przeze mnie, z twojego powodu -> przez ciebie
    res = re.sub(
        r"\b([Zz])\s+mojego\s+powodu\b",
        lambda m: "Przeze mnie" if m.group(1) == "Z" else "przeze mnie",
        res
    )
    res = re.sub(
        r"\b([Zz])\s+twojego\s+powodu\b",
        lambda m: "Przez ciebie" if m.group(1) == "Z" else "przez ciebie",
        res
    )

    return res


def naturalize_adjacency_rejoinder(prior_q: str, resp: str) -> str:
    """
    Eliminates stiff 'Yes, I did' / 'No, I didn't' calques in adjacent conversational pairs (Filar CLXXIX).
    Transforms 'Tak, poszedłem' -> 'Poszedłem', 'Nie, nie widziałem' -> 'Nie widziałem'.
    """
    if not resp:
        return ""
    if not prior_q or not prior_q.strip().endswith("?"):
        return resp

    res = resp.strip()

    m_aff = re.match(r"^Tak,\s+([a-ząćęłńóśźż]+(?:łem|łam|liśmy|łyśmy|em|am|eś|aś|liście|łyście|ł|ła|ło|li|ły|bym|byś|by|byśmy|byście|ę|emy|imy|ymy))\b", res, re.IGNORECASE)
    if m_aff:
        verb = m_aff.group(1)
        rest = res[m_aff.end():]
        return f"{verb.capitalize()}{rest}"

    m_neg = re.match(r"^Nie,\s+nie\s+([a-ząćęłńóśźż]+)\b", res, re.IGNORECASE)
    if m_neg:
        verb = m_neg.group(1)
        rest = res[m_neg.end():]
        return f"Nie {verb}{rest}"

    return res


def sanitize_deictic_motion_vector(text: str) -> str:
    """
    Sanitizes false spatial deixis motion verbs (Filar CLXXX / Cinematic Deixis).
    Eliminates English/Japanese motion mismatch:
    'Już przychodzę!' -> 'Już idę!'
    'Oto przychodzę!' / 'Oto nadchodzę!' -> 'Już idę!' / 'Zaraz będę!'
    """
    if not text:
        return ""
    res = text
    DEICTIC_REPLACEMENTS = [
        (r"\bJuż\s+przychodzę\b", "Już idę"),
        (r"\bjuż\s+przychodzę\b", "już idę"),
        (r"\bZaraz\s+przychodzę\b", "Zaraz będę"),
        (r"\bzaraz\s+przychodzę\b", "zaraz będę"),
        (r"\bOto\s+przychodzę\b", "Już idę"),
        (r"\boto\s+przychodzę\b", "już idę"),
        (r"\bOto\s+nadchodzę\b", "Już idę"),
        (r"\boto\s+nadchodzę\b", "już idę"),
        (r"\bZaraz\s+tam\s+przyjdę\b", "Zaraz tam pójdę"),
        (r"\bzaraz\s+tam\s+przyjdę\b", "zaraz tam pójdę"),
    ]
    for pat, repl in DEICTIC_REPLACEMENTS:
        res = re.sub(pat, repl, res)
    return res


def sanitize_sensory_pleonasm(text: str) -> str:
    """
    Eliminates visual-auditory pleonasms and sensory tautologies (Filar CLXXXI).
    'pada deszcz na zewnątrz' -> 'pada deszcz' / 'na zewnątrz leje'
    'spada w dół' -> 'spada'
    'cofa się w tył' -> 'cofa się'
    'wspina się do góry' -> 'wspina się'
    'patrzeć moimi własnymi oczami' -> 'patrzeć na własne oczy'
    """
    if not text:
        return ""
    res = text
    PLEONASMS = [
        (r"\b(pada|padał|padający|leje|lał)\s+deszcz\s+na\s+zewnątrz\b", r"\1 deszcz"),
        (r"\bna\s+zewnątrz\s+pada\s+deszcz\b", "na zewnątrz leje"),
        (r"\b(spadać|spada|spadają|spadł|spadła|spadło|spadli|spadły|spadłem|spadłam|spadłeś|spadłaś)\s+w\s+dół\b", r"\1"),
        (r"\b(cofać|cofa|cofają|cofnął|cofnęła|cofnęło|cofnęli|cofnęły|cofam|cofasz|cofamy|cofacie)\s+się\s+w\s+tył\b", r"\1 się"),
        (r"\b(wspinać|wspina|wspinają|wspiął|wspięła|wspięło|wspinam|wspinasz|wspinamy)\s+się\s+do\s+góry\b", r"\1 się"),
        (r"\b(patrzeć|widzieć|zobaczyć)\s+(?:na\s+to\s+)?moimi\s+(?:własnymi\s+)?oczami\b", r"\1 na własne oczy"),
        (r"\b(widziałem|widziałam|widzieliśmy|widziałyśmy)\s+to\s+moimi\s+(?:własnymi\s+)?oczami\b", r"\1 to na własne oczy"),
    ]
    for pat, repl in PLEONASMS:
        res = re.sub(pat, repl, res, flags=re.IGNORECASE)
    return res


def sanitize_toponymic_pleonasms_and_stuttering(text: str) -> str:
    """
    Sanitizes toponymic, administrative, geographical, and chronicle pleonasms
    and identical token stuttering without destroying legitimate stylistic punctuation.
    (Filar CLXXXIV / 0.00 PLN)
    """
    if not text:
        return ""
    res = text

    # 1. Identical capitalized word stuttering without punctuation (e.g. 'Prowincja Prowincja' -> 'Prowincja')
    # Requires identical capitalized tokens of length >= 3 separated by whitespace or \N
    res = re.sub(
        r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})(?:\s+|\\[Nnh]+)\1\b",
        r"\1",
        res
    )

    # 2. Repeated or multiple inflected/base category descriptors preceding a proper name
    # Accounts for Polish consonant alternations (k:c, k:cz, g:dz, r:rz, etc.):
    # - 'z prowincji Prowincja Prowincja Shimotsuke' -> 'z prowincji Shimotsuke'
    # - 'z prowincji Prowincja Shimotsuke' -> 'z prowincji Shimotsuke'
    # - 'w kronice Kronika Taiheiki' -> 'w kronice Taiheiki'
    # - 'na górze Góra Hiei' -> 'na górze Hiei'
    # - 'w rzece Rzeka Kamogawa' -> 'w rzece Kamogawa'
    # - 'w mieście Miasto Kioto' -> 'w mieście Kioto'
    # - 'w prefekturze Prefektura Nagano' -> 'w prefekturze Nagano'
    CATEGORY_STEM_GROUPS = [
        r"prowincj",
        r"prefektur",
        r"gór|górz",
        r"rzek|rzec",
        r"jezior",
        r"morz",
        r"dolin",
        r"wysp",
        r"zatok|zatoc",
        r"przełęcz",
        r"zamk|zame",
        r"twierdz",
        r"świątyn",
        r"chram",
        r"bram",
        r"miast|mieśc",
        r"dystrykt|dystrykc",
        r"ziem",
        r"księstw",
        r"królestw",
        r"cesarstw",
        r"państw",
        r"kraj",
        r"kronik|kronic",
        r"księg|księdz",
        r"traktat|traktac",
    ]

    for grp in CATEGORY_STEM_GROUPS:
        pat = re.compile(
            rf"\b([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]*(?:{grp})[a-ząćęłńóśźż]*)"
            rf"(?:(?:\s+|\\[Nnh]+)+[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]*(?:{grp})[a-ząćęłńóśźż]*)+"
            rf"((?:\s+|\\[Nnh]+)+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b",
            re.IGNORECASE
        )
        res = pat.sub(r"\1\2", res)

    return res


def sanitize_toponymic_origin_and_companionship(text: str, custom_glossary: Optional[Dict[str, str]] = None) -> str:
    """
    Sanitizes toponymic origin vs animate companionship errors (Filar CLXXXIV / 0.00 PLN).
    When a toponym (realm, city, location) qualifies an artifact, object, or person of origin
    ('from Hiden', 'Haiden's Book of Toah', 'knight from Boelate'), Polish preposition 'z'
    strictly governs Genitive (Dopełniacz pochodzenia: 'z Hiden', 'z Boelate', 'z Eslinn', 'z Kanyou', 'z Ridill'),
    NEVER Instrumental (Narzędnik towarzyszenia: '*z Hidenem', '*z Haidenem', '*z Kanyouem').
    Also handles compound artifact title syntagmas ('Księga Toaha z Hiden'), prevents modifier hyper-inflection
    ('*z Księgą Toahem' -> 'z Księgą Toaha'), resolves nominative freezing ('z Księga Toaha' -> 'z Księgą Toaha'),
    and normalizes phonetic/fansub transliteration variants (Haiden -> Hiden) in toponymic contexts,
    strictly adhering to the Single-Word Invariance Principle (W_i -> W'_i).
    """
    if not text:
        return ""
    res = text

    # 1. False Instrumental of origin for realms/toponyms ending in consonants across all series
    # Clevatess realms
    res = re.sub(r"\b([Zz]\s+)(?:Haidenem|Hidenem)\b", r"\g<1>Hiden", res)
    res = re.sub(r"\b([Zz]\s+)(?:Boiratem|Boelatem)\b", r"\g<1>Boelate", res)
    res = re.sub(r"\b([Zz]\s+)(?:Esrinem|Eslinnem)\b", r"\g<1>Eslinn", res)
    res = re.sub(r"\b([Zz]\s+)(?:Solseinem|Solceynem)\b", r"\g<1>Solsein", res)
    res = re.sub(r"\b([Zz]\s+)(?:Haideratem|Heideratem)\b", r"\g<1>Hyderatu", res)
    # Kingdom realms/cities
    res = re.sub(r"\b([Zz]\s+)(?:Kanyouem|Kanyōem)\b", r"\g<1>Kanyou", res)
    res = re.sub(r"\b([Zz]\s+)Kantanem\b", r"\g<1>Kantan", res)
    # Silent Witch realms/cities
    res = re.sub(r"\b([Zz]\s+)Ridillem\b", r"\g<1>Ridill", res)

    # 1b. False Instrumental of origin for feminine-like toponyms ending in -a in origin/displacement contexts
    res = re.sub(r"\b(pochodzi[a-ząćęłńóśźż]*|zbieg[a-ząćęłńóśźż]*|wieści|wieść|posłaniec|ucieczka|uciekł[a-ząćęłńóśźż]*|rycerz[a-ząćęłńóśźż]*|chłopak[a-ząćęłńóśźż]*|dziewczyn[a-ząćęłńóśźż]*)\s+([Zz]\s+)Kamakurą\b", r"\g<1> \g<2>Kamakury", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(pochodzi[a-ząćęłńóśźż]*|zbieg[a-ząćęłńóśźż]*|wieści|wieść|posłaniec|ucieczka|uciekł[a-ząćęłńóśźż]*|rycerz[a-ząćęłńóśźż]*|chłopak[a-ząćęłńóśźż]*|dziewczyn[a-ząćęłńóśźż]*)\s+([Zz]\s+)Suwą\b", r"\g<1> \g<2>Suwy", res, flags=re.IGNORECASE)
    res = re.sub(r"\b(pochodzi[a-ząćęłńóśźż]*|uczeń|uczennica|uczniowie|akademia)\s+([Zz]\s+)Minervą\b", r"\g<1> \g<2>Minervy", res, flags=re.IGNORECASE)

    # 2. Canonical toponym transliteration normalization after prepositions (z, do, w, o) or in realm names
    res = re.sub(r"\b([ZzWwOo]|do|dla|ku|przez|od)\s+Haiden\b", r"\g<1> Hiden", res)
    res = re.sub(r"\b([ZzWwOo]|do|dla|ku|przez|od)\s+Boirate\b", r"\g<1> Boelate", res)
    res = re.sub(r"\b([ZzWwOo]|do|dla|ku|przez|od)\s+Esrin\b", r"\g<1> Eslinn", res)
    res = re.sub(r"\b([ZzWwOo]|do|dla|ku|przez|od)\s+Haiderat\b", r"\g<1> Hyderat", res)
    res = re.sub(r"\b([ZzWwOo]|do|dla|ku|przez|od)\s+Solceyn\b", r"\g<1> Solsein", res)

    # 3. Specific compound realm constructions (Królestwo Haiden -> Królestwo Hiden)
    res = re.sub(r"\b([Kk]rólestw[a-ząćęłńóśźż]*|[Cc]esarstw[a-ząćęłńóśźż]*|[Kk]rain[a-ząćęłńóśźż]*)\s+Haiden\b", r"\g<1> Hiden", res)
    res = re.sub(r"\b([Kk]rólestw[a-ząćęłńóśźż]*|[Cc]esarstw[a-ząćęłńóśźż]*|[Kk]rain[a-ząćęłńóśźż]*)\s+Boirate\b", r"\g<1> Boelate", res)
    res = re.sub(r"\b([Kk]rólestw[a-ząćęłńóśźż]*|[Cc]esarstw[a-ząćęłńóśźż]*|[Kk]rain[a-ząćęłńóśźż]*)\s+Esrin\b", r"\g<1> Eslinn", res)

    # 4. Canonical qualification of relics/titles and modifier hyper-inflection protection:
    # 'Księga Toaha z Haiden' / 'Księga Toaha z Haidenem' / 'Księga Toaha z Hidenem' -> 'Księga Toaha z Hiden'
    res = re.sub(r"\bKsięga\s+Toaha\s+z\s+(?:Haidenem|Hidenem|Haiden)\b", "Księga Toaha z Hiden", res)
    # Protection against modifier hyper-inflection: 'z Księgą Toahem' -> 'z Księgą Toaha'
    res = re.sub(r"\b([Zz]\s+Księgą)\s+Toahem\b", r"\g<1> Toaha", res)
    # Protection against double-preposition hyper-inflection: 'z Księgą Toahem z Haidenem' -> 'z Księgą Toaha z Hiden'
    res = re.sub(r"\b([Zz]\s+Księgą)\s+Toahem\s+([Zz]\s+)(?:Haidenem|Hidenem|Haiden)\b", r"\g<1> Toaha \g<2>Hiden", res)
    # Protection against nominative freezing after preposition: 'z Księga Toaha' -> 'z Księgą Toaha'
    res = re.sub(r"\b([Zz]\s+)Księga\s+Toaha\b", r"\g<1>Księgą Toaha", res)
    # Nominative freezing after genitive verbs: 'szuka/szukam/szukać Księga Toaha' -> 'szukać Księgi Toaha'
    res = re.sub(r"\b(szuka[a-ząćęłńóśźż]*|pilnuje|pilnowa[a-ząćęłńóśźż]*|używa[a-ząćęłńóśźż]*|strzeż[a-ząćęłńóśźż]*)\s+Księga\s+Toaha\b", r"\g<1> Księgi Toaha", res)

    return res


def sanitize_closed_idioms_and_prepositions(text: str) -> str:
    """
    Sanitizes closed, invariant register idioms and PWN prepositional-pronominal forms.
    Guaranteed 100% syntactically closed — zero inflectional risk, zero nominative freezing.
    """
    if not text:
        return ""
    res = text
    INVARIANT_RULES = [
        # PWN Preposition-Pronoun phonetic government
        (r"\b([Dd]la)\s+mię\b", lambda m: "Dla mnie" if m.group(1)[0].isupper() else "dla mnie"),
        (r"\b([Oo]de)\s+mie\b", lambda m: "Ode mnie" if m.group(1)[0].isupper() else "ode mnie"),
        (r"\b([Oo]d)\s+mnie\b", lambda m: "Ode mnie" if m.group(1)[0].isupper() else "ode mnie"),
        (r"\b([Zz])\s+mną\b", lambda m: "Ze mną" if m.group(1)[0].isupper() else "ze mną"),
        (r"\b([Pp]rzed)\s+mną\b", lambda m: "Przede mną" if m.group(1)[0].isupper() else "przede mną"),
        # PWN Preposition phonetic alternations: 'ze' before s/z/sz/ż/ś/ź + consonant, 'we' before w/f + consonant
        (r"\b([Zz])\s+(stali|złota|żelaza|szkła|srebra|strachu|szmaragdu|złości|zazdrości|związku|Szwecji|Szwajcarii)\b",
         lambda m: ("Ze " if m.group(1).isupper() else "ze ") + m.group(2)),
        (r"\b([Zz])e\s+(Hiden|Boelate|Eslinn|Solsein|Kanyou|Kantan|Ridill|Paryża|Londynu)\b",
         lambda m: ("Z " if m.group(1).isupper() else "z ") + m.group(2)),
        (r"\b([Ww])\s+(Francji|Florencji|Flandrii|Włoszech|wrześniu|wtorku|wpół)\b",
         lambda m: ("We " if m.group(1).isupper() else "we ") + m.group(2)),
        # Closed invariant register idioms
        (r"\b([Ww])\s+każdym\s+bądź\s+razie\b", lambda m: "W każdym razie" if m.group(1)[0].isupper() else "w każdym razie"),
        (r"\b([Bb])ez\s+jaj[!]+", lambda m: "To jakieś kpiny!" if m.group(1)[0].isupper() else "to jakieś kpiny!"),
        (r"\b([Gg])uzik\s+mnie\s+to\s+obchodzi\b", lambda m: "Nic mnie to nie obchodzi" if m.group(1)[0].isupper() else "nic mnie to nie obchodzi"),
        (r"\b([Pp])omiędzy\s+tobą\s+i\s+mną\b", lambda m: "Między nami" if m.group(1)[0].isupper() else "między nami"),
        (r"\b([Pp])omiędzy\s+nami\b", lambda m: "Między nami" if m.group(1)[0].isupper() else "między nami"),
        (r"\b([Ww])\s+mrugnięciu\s+oka\b", lambda m: "W mgnieniu oka" if m.group(1)[0].isupper() else "w mgnieniu oka"),
    ]
    for pat, repl in INVARIANT_RULES:
        res = re.sub(pat, repl, res)
    return res


# -------------------------------------------------------------------------
# Definite Article Nominative vs False Vocative Mapping (Filar CLXXIII / §0 & §3)
# Maps English noun/title to Polish vocative forms and target nominative form.
# When English has "the <title>", the definite article marks 3rd-person reference (Nominativus Exclamativus).
# English direct address (vocative) NEVER takes a definite article ("*The king, listen!").
# -------------------------------------------------------------------------
DEFINITE_TITLE_MAPPING: Dict[str, Dict[str, Any]] = {
    "king": {"vocatives": ["królu"], "nominative": "król"},
    "queen": {"vocatives": ["królowo"], "nominative": "królowa"},
    "emperor": {"vocatives": ["cesarzu"], "nominative": "cesarz"},
    "empress": {"vocatives": ["cesarzowo"], "nominative": "cesarzowa"},
    "prince": {"vocatives": ["królewiczu"], "nominative": "królewicz"},
    "princess": {"vocatives": ["księżniczko"], "nominative": "księżniczka"},
    "duke": {"vocatives": ["książę"], "nominative": "książę"},
    "count": {"vocatives": ["hrabio"], "nominative": "hrabia"},
    "baron": {"vocatives": ["baronie"], "nominative": "baron"},
    "lord": {"vocatives": ["lordzie"], "nominative": "lord"},
    "commander": {"vocatives": ["dowódco", "komendancie"], "nominative": "dowódca"},
    "captain": {"vocatives": ["kapitanie"], "nominative": "kapitan"},
    "general": {"vocatives": ["generale"], "nominative": "generał"},
    "chief": {"vocatives": ["wodzu", "szefie"], "nominative": "wódz"},
    "boss": {"vocatives": ["szefie"], "nominative": "szef"},
    "leader": {"vocatives": ["przywódco"], "nominative": "przywódca"},
    "knight": {"vocatives": ["rycerzu"], "nominative": "rycerz"},
    "soldier": {"vocatives": ["żołnierzu"], "nominative": "żołnierz"},
    "guard": {"vocatives": ["strażniku"], "nominative": "strażnik"},
    "master": {"vocatives": ["mistrzu"], "nominative": "mistrz"},
    "doctor": {"vocatives": ["doktorze", "lekarzu"], "nominative": "doktor"},
    "physician": {"vocatives": ["lekarzu", "doktorze"], "nominative": "lekarz"},
    "teacher": {"vocatives": ["nauczycielu"], "nominative": "nauczyciel"},
    "professor": {"vocatives": ["profesorze"], "nominative": "profesor"},
    "president": {"vocatives": ["prezydencie"], "nominative": "prezydent"},
    "priest": {"vocatives": ["kapłanie"], "nominative": "kapłan"},
    "pope": {"vocatives": ["papieżu"], "nominative": "papież"},
    "hero": {"vocatives": ["bohaterze"], "nominative": "bohater"},
    "enemy": {"vocatives": ["wrogu", "nieprzyjacielu"], "nominative": "wróg"},
    "beast": {"vocatives": ["bestio"], "nominative": "bestia"},
    "monster": {"vocatives": ["potworze"], "nominative": "potwór"},
    "demon": {"vocatives": ["demonie"], "nominative": "demon"},
    "dragon": {"vocatives": ["smoku"], "nominative": "smok"},
    "traitor": {"vocatives": ["zdrajco"], "nominative": "zdrajca"},
    "killer": {"vocatives": ["zabójco", "morderco"], "nominative": "zabójca"},
    "assassin": {"vocatives": ["zabójco", "morderco"], "nominative": "zabójca"},
    "culprit": {"vocatives": ["sprawco"], "nominative": "sprawca"},
    "father": {"vocatives": ["ojcze"], "nominative": "ojciec"},
    "mother": {"vocatives": ["matko"], "nominative": "matka"},
    "son": {"vocatives": ["synu"], "nominative": "syn"},
    "daughter": {"vocatives": ["córko"], "nominative": "córka"},
    "brother": {"vocatives": ["bracie"], "nominative": "brat"},
    "sister": {"vocatives": ["siostro"], "nominative": "siostra"},
    "god": {"vocatives": ["boże"], "nominative": "bóg"},
    "wizard": {"vocatives": ["czarodzieju"], "nominative": "czarodziej"},
    "sorcerer": {"vocatives": ["czarodzieju"], "nominative": "czarodziej"},
    "mage": {"vocatives": ["magu"], "nominative": "mag"},
    "witch": {"vocatives": ["wiedźmo"], "nominative": "wiedźma"},
    "warrior": {"vocatives": ["wojowniku"], "nominative": "wojownik"},
    "hunter": {"vocatives": ["łowco"], "nominative": "łowca"},
    "boy": {"vocatives": ["chłopcze"], "nominative": "chłopiec"},
    "girl": {"vocatives": ["dziewczyno"], "nominative": "dziewczyna"}
}


def resolve_definite_article_nominative(en_text: str, pl_text: str) -> Tuple[str, bool]:
    """
    Guards against False Vocative Drift (Filar CLXXIII / §0 & §3 Offline-First).
    When English uses 'The [Title/Role]' (e.g. 'The king...!', 'The captain!'),
    the definite article 'The' strictly marks 3rd-person reference (Nominativus Exclamativus).
    English direct address (vocative) NEVER takes a definite article.
    If Polish mistakenly outputs a vocative form (e.g. 'Królu...!', 'Kapitanie!'),
    this function deterministically restores the correct nominative form ('Król...!', 'Kapitan!').
    Returns (fixed_pl_text, was_changed).
    """
    if not en_text or not pl_text:
        return pl_text, False

    clean_en = str(en_text).lower()
    modified = pl_text
    changed = False

    GOVERNING_PREP_PAT = re.compile(r"\b(?:o|przy|ku|przeciw|przeciwko|dzięki|wobec|u|do|od)\s*$", re.IGNORECASE)

    for en_title, data in DEFINITE_TITLE_MAPPING.items():
        if not re.search(rf"\bthe\s+{re.escape(en_title)}\b", clean_en):
            continue

        nom = data["nominative"]
        for voc in data["vocatives"]:
            voc_pat = rf"\b({re.escape(voc)})\b"

            def _repl(m, target_nom=nom):
                preceding = modified[:m.start()]
                if GOVERNING_PREP_PAT.search(preceding):
                    return m.group(0)
                matched = m.group(1)
                if matched.isupper():
                    return target_nom.upper()
                elif matched[0].isupper():
                    return target_nom.capitalize()
                return target_nom

            new_pl = re.sub(voc_pat, _repl, modified, flags=re.IGNORECASE)
            if new_pl != modified:
                modified = new_pl
                changed = True

    return modified, changed


class SeriesBible:
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        inst = super().__new__(cls)
        inst._lock = threading.RLock()
        return inst

    def __init__(self, anime_title: str, storage_dir: Optional[Path] = None):
        self._lock = threading.RLock()
        self.anime_title = anime_title.strip() if anime_title else "Nieznana Seria"
        self.slug = clean_anime_slug(self.anime_title)
        self.storage_dir = storage_dir or SERIES_MEMORY_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.storage_dir / f"{self.slug}_bible.json"
        
        self.data: Dict[str, Any] = {
            "anime_title": self.anime_title,
            "characters": {},          # { "Arata": {"gender": "męska", "role": "uczeń", "forms": "Arata"} }
            "glossary": {},            # { "Choushi": "czara na sake", "Dragon Slayer": "Pogromca Smoków" }
            "relationships": {},      # { "Kokoro->Arata": "po imieniu / na ty", "Uczniowie->Teshima": "pani Teshima" }
            "declensions": {},        # { "Shira": {"M": "Shira", "D": "Shiry", "C": "Shirze", ...} }
            "hypocorisms": {},        # { "Kuro": "Kuroe", "Kuro-tan": "Kuroe", "Rin": "Rinko" }
            "plot_anchors": {},        # { "kamień jada": "rytualny artefakt wywołujący deszcz", "zbieg z Samarkandy": "Shira" }
            "episodes_translated": [], # ["odcinek 1", "odcinek 2"]
            "batch_stats": {}          # { "odcinek 1": {"batches": 17, "dialogues": 374, "avg_batch_size": 22.0} }
        }
        self.load()

    def get_characters_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.data.get("characters", {}))

    def get_declensions_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.data.get("declensions", {}))

    def get_relationships_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.data.get("relationships", {}))

    def get_glossary_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.data.get("glossary", {}))

    def load(self):
        """Loads existing Series Bible from disk (Thread-Safe)."""
        with self._lock:
            if self.file_path.exists():
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        saved_data = json.load(f)
                        if isinstance(saved_data, dict):
                            for k, v in saved_data.items():
                                if k in self.data and isinstance(v, dict):
                                    self.data[k].update(v)
                                elif k in self.data and isinstance(v, list):
                                    for item in v:
                                        if item not in self.data[k]:
                                            self.data[k].append(item)
                    self._sanitize_bible_integrity()
                except Exception:
                    pass

            # Auto-integrate verified Fansub Canon Lexicon from fansub_miner (0.00 PLN)
            try:
                from fansub_miner import load_fansub_lexicon
                fansub_lex = load_fansub_lexicon(self.anime_title)
                if fansub_lex and "terms" in fansub_lex:
                    if "fansub_canon" not in self.data:
                        self.data["fansub_canon"] = {}
                    self.data["fansub_canon"].update(fansub_lex["terms"])
                    if "glossary" not in self.data:
                        self.data["glossary"] = {}
                    for t_key, t_val in fansub_lex["terms"].items():
                        if isinstance(t_val, dict) and "canonical_pl" in t_val:
                            en_keys = t_val.get("en", [t_key])
                            for ek in en_keys:
                                if ek not in self.data["glossary"]:
                                    self.data["glossary"][ek] = t_val["canonical_pl"]
            except Exception:
                pass

    def _sanitize_bible_integrity(self):
        """
        Self-healing relational and biological gender consistency audit.
        Guards against poisoned entries where female characters (empresses, daughters, wives)
        were accidentally marked as male or inflected with masculine endings.
        """
        if not hasattr(self, "data") or "characters" not in self.data:
            return

        FEMALE_TITLES = {"cesarzowa", "chatun", "małżonka", "żona", "córka", "matka", "księżniczka", "królowa", "lady"}

        # 1. Collect female names from relationships or explicit notes
        confirmed_females = set()
        for rel_name, rel_desc in list(self.data.get("relationships", {}).items()):
            r_lower = str(rel_desc).lower()
            if "->" in rel_name:
                parts = [p.strip() for p in rel_name.split("->")]
                spk = parts[0]
                rec = parts[1] if len(parts) > 1 else ""
                if any(w in r_lower for w in ["córka ->", "żona ->", "pasierbica ->", "cesarzowa ->"]):
                    confirmed_females.add(spk)
                if any(w in r_lower for w in ["-> córka", "-> żona", "-> matka", "-> macocha", "-> cesarzowa"]):
                    confirmed_females.add(rec)

        # 2. Check characters table
        for char_name, c_val in list(self.data.get("characters", {}).items()):
            if "->" in char_name:
                continue
            desc = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
            d_lower = desc.lower()

            is_confirmed_female = (char_name in confirmed_females) or any(t in d_lower for t in FEMALE_TITLES)
            if is_confirmed_female:
                # If marked as male, auto-repair to female
                if any(m in d_lower for m in ["mężczyzna", "chłopak", "male"]):
                    clean_desc = re.sub(r"\bmężczyzna\b", "KOBIETA", desc, flags=re.IGNORECASE)
                    clean_desc = re.sub(r"\[MĘŻCZYZNA \(Adresat\)[^\]]*\]", "[KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]", clean_desc)
                    if isinstance(c_val, dict):
                        c_val["description"] = clean_desc
                    else:
                        self.data["characters"][char_name] = {"description": clean_desc}

                # Regenerate declensions for foreign female names
                if "declensions" in self.data:
                    if char_name in self.data["declensions"]:
                        self.data["declensions"][char_name] = generate_polish_name_declension(char_name, "FEMALE")
                        self.data["declensions"][char_name]["gender"] = "FEMALE"

                # Auto-register and synchronize transliterated aliases found in female character descriptions
                for alias in re.findall(r"\b(?:cesarzowa|pani|księżniczka|postać|imię)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)", desc):
                    if alias != char_name:
                        if alias not in self.data["characters"]:
                            self.data["characters"][alias] = dict(c_val) if isinstance(c_val, dict) else {"description": str(c_val)}
                        if "declensions" in self.data:
                            self.data["declensions"][alias] = generate_polish_name_declension(alias, "FEMALE")
                            self.data["declensions"][alias]["gender"] = "FEMALE"

        # 2b. Check characters table for poisoned male characters (e.g. historical samurai, kuge, generals, lords)
        MALE_TITLES = {"samuraj", "generał", "buke", "kuge", "wasal", "lord", "pan ", "wojownik", "rycerz", "król", "książę", "cesarz", "wielki radca"}
        confirmed_males = set()
        for rel_name, rel_desc in list(self.data.get("relationships", {}).items()):
            r_str = str(rel_desc)
            r_lower = r_str.lower()
            if "->" in rel_name:
                parts = [p.strip() for p in rel_name.split("->")]
                spk = parts[0]
                rec = parts[1] if len(parts) > 1 else ""
                if re.search(r"\bpanie\s+[A-ZĄĆĘŁŃÓŚŹŻ]", r_str) or any(w in r_lower for w in ["ojciec", "syn", "brat", "generał", "dowódca", "lord", "panicz", "bocchan"]):
                    confirmed_males.add(rec)
                if any(w in r_lower for w in ["syn ->", "ojciec ->", "brat ->", "pan ->"]):
                    confirmed_males.add(spk)
                # Auto-repair poisoned [KOBIETA (Adresat)] in relationships if recipient is confirmed male or addressed with 'panie'
                rec_tokens = extract_clean_speaker_name(rec).lower().split()
                if re.search(r"\bpanie\s+[A-ZĄĆĘŁŃÓŚŹŻ]", r_str) or (rec.lower() in CANONICAL_MALE_NAMES) or any(t in CANONICAL_MALE_NAMES for t in rec_tokens):
                    if "[KOBIETA (Adresat)" in r_str:
                        fixed_rel = re.sub(r"\[KOBIETA \(Adresat\)[^\]]*\]", "[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]", r_str)
                        self.data["relationships"][rel_name] = fixed_rel
                        if rel_name in self.data.get("characters", {}):
                            self.data["characters"][rel_name]["description"] = fixed_rel

        for char_name, c_val in list(self.data.get("characters", {}).items()):
            if "->" in char_name:
                continue
            desc = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
            d_lower = desc.lower()
            c_tokens = extract_clean_speaker_name(char_name).lower().split()

            is_female_cand = (char_name in confirmed_females) or any(t in d_lower for t in FEMALE_TITLES)
            is_confirmed_male = (
                (char_name in confirmed_males)
                or any(t in d_lower for t in MALE_TITLES)
                or (char_name.lower() in CANONICAL_MALE_NAMES)
                or any(t in CANONICAL_MALE_NAMES for t in c_tokens)
            ) and not is_female_cand

            if is_confirmed_male:
                # If marked as female due to past "pani" substring collision in "panie", auto-repair to male
                if any(f in d_lower for f in ["kobieta", "żeńsk", "female", "kobieta (adresat)"]) and not any(f in d_lower for f in ["córka", "żona", "matka", "księżniczka"]):
                    clean_desc = re.sub(r"\bkobieta\b", "MĘŻCZYZNA", desc, flags=re.IGNORECASE)
                    clean_desc = re.sub(r"\[KOBIETA \(Adresat\)[^\]]*\]", "[MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]", clean_desc)
                    if isinstance(c_val, dict):
                        c_val["description"] = clean_desc
                    else:
                        self.data["characters"][char_name] = {"description": clean_desc}
                elif "postać" in d_lower and not any(m in d_lower for m in ["mężczyzna", "male", "chłopak"]):
                    clean_desc = f"{desc} [MĘŻCZYZNA]"
                    if isinstance(c_val, dict):
                        c_val["description"] = clean_desc
                    else:
                        self.data["characters"][char_name] = {"description": clean_desc}

                if isinstance(c_val, dict):
                    c_val["gender"] = "MALE"

                # Regenerate declensions for male character
                if "declensions" in self.data:
                    if char_name in self.data["declensions"]:
                        self.data["declensions"][char_name] = generate_polish_name_declension(char_name, "MALE")
                        self.data["declensions"][char_name]["gender"] = "MALE"

        # Ensure any declension with a female or male character has gender aligned
        if "declensions" in self.data:
            for d_name, d_val in list(self.data["declensions"].items()):
                if isinstance(d_val, dict):
                    c_info = self.data.get("characters", {}).get(d_name)
                    if c_info:
                        c_desc = c_info.get("description", "") if isinstance(c_info, dict) else str(c_info)
                        cd_lower = c_desc.lower()
                        d_tokens = extract_clean_speaker_name(d_name).lower().split()
                        if any(t in cd_lower for t in FEMALE_TITLES) or "kobieta" in cd_lower or "female" in cd_lower:
                            d_val["gender"] = "FEMALE"
                        elif any(t in cd_lower for t in ["mężczyzna", "male", "chłopak"]) or (d_name.lower() in CANONICAL_MALE_NAMES) or any(t in CANONICAL_MALE_NAMES for t in d_tokens):
                            d_val["gender"] = "MALE"


        # 3. Systemic Ethnonym & Collective Purge from Characters & Declensions
        for bad_key in list(self.data.get("characters", {}).keys()):
            if "->" not in bad_key:
                clean_k = extract_clean_speaker_name(bad_key).strip().lower()
                if clean_k in ETHNONYMS_AND_COLLECTIVES or self.is_non_character_entity(bad_key):
                    del self.data["characters"][bad_key]

        if "declensions" in self.data:
            for bad_key in list(self.data.get("declensions", {}).keys()):
                clean_k = extract_clean_speaker_name(bad_key).strip().lower()
                if clean_k in ETHNONYMS_AND_COLLECTIVES or self.is_non_character_entity(bad_key):
                    del self.data["declensions"][bad_key]

        # 4. Systemic Historical Titling Sanity Audit (Khagan/Chagan -> Wielki Chan/Chan)
        if "glossary" in self.data and isinstance(self.data["glossary"], dict):
            new_gloss = {}
            for gk, gv in list(self.data["glossary"].items()):
                gk_str = str(gk)
                gv_str = str(gv)
                # Normalize key if it's Great Kha'an or Khagan
                if gk_str.lower() in ["great kha'an", "great khagan", "great chagan"]:
                    gk_clean = "Great Kha'an"
                    gv_clean = "Wielki Chan"
                elif gk_str.lower() in ["khagan", "chagan"]:
                    gk_clean = "Khagan"
                    gv_clean = "Chan / Wielki Chan"
                else:
                    gk_clean = gk_str
                    gv_clean = gv_str
                    gv_clean = re.sub(r"\bWielki Chaganie\b", "Wielki Chanie", gv_clean)
                    gv_clean = re.sub(r"\bWielkiego Chagana\b", "Wielkiego Chana", gv_clean)
                    gv_clean = re.sub(r"\bWielki Chagan\b", "Wielki Chan", gv_clean)
                    gv_clean = re.sub(r"\bChaganie\b", "Chanie", gv_clean)
                    gv_clean = re.sub(r"\bChagana\b", "Chana", gv_clean)
                    gv_clean = re.sub(r"\bChagan\b", "Chan", gv_clean)
                new_gloss[gk_clean] = gv_clean
            self.data["glossary"] = new_gloss

        if "relationships" in self.data and isinstance(self.data["relationships"], dict):
            for rk, rv in list(self.data["relationships"].items()):
                rv_str = str(rv)
                rv_clean = re.sub(r"\bWielki Chaganie\b", "Wielki Chanie", rv_str)
                rv_clean = re.sub(r"\bWielkiego Chagana\b", "Wielkiego Chana", rv_clean)
                rv_clean = re.sub(r"\bWielkiemu Chaganowi\b", "Wielkiemu Chanowi", rv_clean)
                rv_clean = re.sub(r"\bWielkim Chaganem\b", "Wielkim Chanem", rv_clean)
                rv_clean = re.sub(r"\bWielki Chagan\b", "Wielki Chan", rv_clean)
                rv_clean = re.sub(r"\bChaganie\b", "Chanie", rv_clean)
                rv_clean = re.sub(r"\bChagana\b", "Chana", rv_clean)
                rv_clean = re.sub(r"\bChaganem\b", "Chanem", rv_clean)
                rv_clean = re.sub(r"\bChagan\b", "Chan", rv_clean)
                rv_clean = re.sub(r"\bchagan\b", "chan", rv_clean, flags=re.IGNORECASE)

                # Auto-detect female-only relationships and enforce dual forms
                if "->" in rk:
                    parts = [p.strip() for p in rk.split("->")]
                    spk_name = parts[0]
                    rec_name = parts[1] if len(parts) > 1 else ""
                    if self.is_female_pair(spk_name, rec_name) or (spk_name in confirmed_females and rec_name in confirmed_females):
                        if "PARA DWÓCH KOBIET" not in rv_clean:
                            rv_clean += " [PARA DWÓCH KOBIET: w odniesieniu do obu kobiet stosuj wyłącznie formy żeńskie 'obie / dla was obu / was obie', KATEGORYCZNY ZAKAZ 'oboje' (Filar CLXXIII)]"

                self.data["relationships"][rk] = rv_clean

        # 5. Sanitize character descriptions and relation keys in characters table
        for c_k, c_v in list(self.data.get("characters", {}).items()):
            if isinstance(c_v, dict) and "description" in c_v:
                d_s = c_v["description"]
                d_s = re.sub(r"\bWielki Chaganie\b", "Wielki Chanie", d_s)
                d_s = re.sub(r"\bWielkiego Chagana\b", "Wielkiego Chana", d_s)
                d_s = re.sub(r"\bWielkiemu Chaganowi\b", "Wielkiemu Chanowi", d_s)
                d_s = re.sub(r"\bWielkim Chaganem\b", "Wielkim Chanem", d_s)
                d_s = re.sub(r"\bWielki Chagan\b", "Wielki Chan", d_s)
                d_s = re.sub(r"\bChaganie\b", "Chanie", d_s)
                d_s = re.sub(r"\bChagana\b", "Chana", d_s)
                d_s = re.sub(r"\bChaganem\b", "Chanem", d_s)
                d_s = re.sub(r"\bChagan\b", "Chan", d_s)
                d_s = re.sub(r"\bchagan\b", "chan", d_s, flags=re.IGNORECASE)
                c_v["description"] = d_s
            elif isinstance(c_v, str):
                d_s = re.sub(r"\bWielki Chaganie\b", "Wielki Chanie", c_v)
                d_s = re.sub(r"\bWielkiego Chagana\b", "Wielkiego Chana", d_s)
                d_s = re.sub(r"\bWielki Chagan\b", "Wielki Chan", d_s)
                d_s = re.sub(r"\bChaganie\b", "Chanie", d_s)
                d_s = re.sub(r"\bChagana\b", "Chana", d_s)
                d_s = re.sub(r"\bChagan\b", "Chan", d_s)
                d_s = re.sub(r"\bchagan\b", "chan", d_s, flags=re.IGNORECASE)
                self.data["characters"][c_k] = d_s

    def save(self):
        """Saves current Series Bible state to disk (Thread-Safe)."""
        with self._lock:
            try:
                dump_data = copy.deepcopy(self.data)
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(dump_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def register_episode_execution(
        self,
        episode_name: str,
        batch_count: int,
        dialogue_count: int,
        cost_pln: Optional[float] = None
    ):
        """
        Records execution density and batch stats in Series Bible to monitor and prevent financial/fragmentation drift.
        """
        with self._lock:
            if not hasattr(self, "data") or "episodes_translated" not in self.data:
                return
            entry = episode_name.strip()
            if entry and entry not in self.data["episodes_translated"]:
                self.data["episodes_translated"].append(entry)

            if "batch_stats" not in self.data:
                self.data["batch_stats"] = {}
            self.data["batch_stats"][entry] = {
                "dialogues": dialogue_count,
                "batches": batch_count,
                "avg_batch_size": round(dialogue_count / max(1, batch_count), 1),
                "cost_pln": cost_pln
            }
            self.save()

    def resolve_canonical_name(self, name_or_stem: str) -> str:
        """
        Resolves hypocorisms, pet names, and truncated stems (e.g. 'Kuro-tan', 'Kuro')
        to the full canonical character name ('Kuroe') registered in the Series Bible.
        """
        if not name_or_stem:
            return ""
        s = name_or_stem.strip()
        s_lower = s.lower()
        # 1. Direct lookup in registered hypocorisms
        with self._lock:
            hypo = dict(self.data.get("hypocorisms", {}))
            chars_keys = list(self.data.get("characters", {}).keys())
        if s in hypo:
            return hypo[s]
        for k, v in hypo.items():
            if k.lower() == s_lower:
                return v
        # 2. Check if stem matches prefix of a confirmed character name
        for c in chars_keys:
            if "->" not in c:
                c_first = c.split()[0]
                if c_first.lower() == s_lower:
                    return c_first
                if c_first.lower().startswith(s_lower) and len(s_lower) >= 3:
                    return c_first
        return s

    def is_named_character(self, name: str) -> bool:
        """
        Returns True if name belongs to an actual named character in the series
        (from AniList/Bible registry) and is NOT a generic category noun.
        """
        if not name or is_generic_actor_or_category(name):
            return False
        clean = extract_clean_speaker_name(name).strip().lower()
        with self._lock:
            chars_keys = list(self.data.get("characters", {}).keys())
        for k in chars_keys:
            if "->" not in k:
                if k.lower() == clean or extract_clean_speaker_name(k).strip().lower() == clean:
                    return True
        return False

    def get_character_gender(self, name: str, allow_generic_nouns: bool = True) -> str:
        """
        Returns 'MALE', 'FEMALE', or 'UNKNOWN' based on Series Bible records and inherent lexical gender.
        When allow_generic_nouns=False, generic category nouns ('mężczyzna', 'kobieta') return 'UNKNOWN',
        ensuring they cannot impersonate named characters.
        """
        if not name:
            return "UNKNOWN"
        clean = extract_clean_speaker_name(name)
        n_l = (clean or name).strip().lower()

        if not allow_generic_nouns and is_generic_actor_or_category(n_l):
            return "UNKNOWN"

        if self.is_non_character_entity(name) or n_l in ETHNONYMS_AND_COLLECTIVES:
            return "UNKNOWN"

        # Inherent lexical gender check
        tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", n_l))
        if allow_generic_nouns:
            if n_l in INHERENT_FEMALE_NOUNS or any(t in INHERENT_FEMALE_NOUNS for t in tokens):
                return "FEMALE"
            if n_l in INHERENT_MALE_NOUNS or any(t in INHERENT_MALE_NOUNS for t in tokens):
                return "MALE"

        with self._lock:
            chars_items = list(self.data.get("characters", {}).items())
            rels_keys_str = " ".join(list(self.data.get("relationships", {}).keys())).lower()

        def _extract_gender_from_val(v) -> Optional[str]:
            if isinstance(v, dict):
                raw_g = str(v.get("gender") or "").strip().upper()
                if raw_g in ("FEMALE", "KOBIETA", "FEMALE_GROUP"):
                    return "FEMALE"
                if raw_g in ("MALE", "MĘŻCZYZNA", "MALE_GROUP"):
                    return "MALE"

            desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
            # Strip negative prohibition clauses (e.g. 'zakaz form żeńskich', 'zakaz form męskich')
            desc_clean = re.sub(r"\b(?:zakaz|nie|brak)\s+[^.!?\n]*?(?:żeńsk\w*|męsk\w*|kobiet\w*|mężczyzn\w*)", "", desc_v)

            raw_desc = str(v.get("description", "") if isinstance(v, dict) else v)
            # Check structured canonical tag first: [KOBIETA (Adresat)...] or [MĘŻCZYZNA (Adresat)...]
            m_tag = re.search(r"\[(KOBIETA|MĘŻCZYZNA)\s+\(Adresat\)", raw_desc, re.IGNORECASE)
            if m_tag:
                return "FEMALE" if m_tag.group(1).upper() == "KOBIETA" else "MALE"

            # 1. Primary lead gender tag at start of description or in [TAG]
            m_lead = re.match(r"^\s*\[?(kobieta|mężczyzna|female|male)\b", desc_clean)
            if m_lead:
                lead_g = m_lead.group(1).lower()
                if lead_g in ("kobieta", "female"):
                    return "FEMALE"
                if lead_g in ("mężczyzna", "male"):
                    return "MALE"

            if re.search(r"\b\[kobieta\b", desc_clean) or re.search(r"\(kobieta\)", desc_clean):
                return "FEMALE"
            if re.search(r"\b\[mężczyzna\b", desc_clean) or re.search(r"\(mężczyzna\)", desc_clean):
                return "MALE"

            # 2. General keywords in cleaned description
            has_f = is_female_role_text(desc_clean) or any(w in desc_clean for w in FEMALE_ROLE_KEYWORDS)
            has_m = is_male_role_text(desc_clean) or any(w in desc_clean for w in MALE_ROLE_KEYWORDS)
            if has_f and not has_m:
                return "FEMALE"
            if has_m and not has_f:
                return "MALE"
            if has_f and has_m:
                f_pos = None
                m_pos = None
                m_f = RE_FEMALE_ROLE.search(desc_clean)
                if m_f:
                    f_pos = (m_f.start(), m_f.end() - m_f.start())
                else:
                    f_matches = [(desc_clean.find(w), len(w)) for w in FEMALE_ROLE_KEYWORDS if w in desc_clean]
                    if f_matches:
                        f_pos = min(f_matches, key=lambda x: (x[0], -x[1]))

                m_m = RE_MALE_ROLE.search(desc_clean)
                if m_m:
                    m_pos = (m_m.start(), m_m.end() - m_m.start())
                else:
                    m_matches = [(desc_clean.find(w), len(w)) for w in MALE_ROLE_KEYWORDS if w in desc_clean]
                    if m_matches:
                        m_pos = min(m_matches, key=lambda x: (x[0], -x[1]))

                if f_pos and not m_pos:
                    return "FEMALE"
                if m_pos and not f_pos:
                    return "MALE"
                if f_pos and m_pos:
                    if f_pos[0] < m_pos[0]:
                        return "FEMALE"
                    elif m_pos[0] < f_pos[0]:
                        return "MALE"
                    else:
                        return "FEMALE" if f_pos[1] >= m_pos[1] else "MALE"
            return None

        # Pass 1: Exact character names only (e.g. 'Tomine', 'Shizuku', 'Issei Tomine')
        for k, v in chars_items:
            if "->" not in k:
                k_l = k.lower()
                clean_k = extract_clean_speaker_name(k_l)
                if k_l == n_l or clean_k == n_l:
                    g = _extract_gender_from_val(v)
                    if g:
                        return g

        # Pass 2: Token / surname matches with collision detection (e.g. 'Tomine' matching 'Issei Tomine' and 'Honoka Tomine')
        token_matches = []
        for k, v in chars_items:
            if "->" not in k:
                k_l = k.lower()
                if n_l in k_l.split():
                    g = _extract_gender_from_val(v)
                    if g:
                        token_matches.append((k, g))

        if token_matches:
            genders_found = set(g for _, g in token_matches)
            if len(genders_found) == 1:
                return next(iter(genders_found))
            # Collision: multiple characters share surname with different genders
            # Check relationships: prioritize candidate active as primary interpersonal entity
            for cand_k, cand_g in token_matches:
                if cand_k.lower() in rels_keys_str:
                    return cand_g
            return "UNKNOWN"

        # Onomastic female / male name check (for named characters when series records don't specify)
        if not is_generic_actor_or_category(n_l):
            if (
                n_l in CANONICAL_MALE_NAMES
                or any(t in CANONICAL_MALE_NAMES for t in tokens)
                or n_l in MALE_EXCEPTIONS_ON_A
                or any(t in MALE_EXCEPTIONS_ON_A for t in tokens)
            ):
                return "MALE"
            if is_inherently_female_name(n_l) or any(is_inherently_female_name(t) for t in tokens):
                return "FEMALE"

        return "UNKNOWN"

    def get_character_age_class(self, name: str) -> str:
        """
        Returns 'CHILD', 'ADULT', 'ELDERLY', or 'UNKNOWN' based on Series Bible records and lexical patterns.
        """
        if not name:
            return "UNKNOWN"
        clean = extract_clean_speaker_name(name)
        n_l = (clean or name).strip().lower()
        if any(w in n_l for w in ["dziewczynka", "chłopiec", "dziecko", "mała", "mały", "girl", "boy", "kid", "child", "bocchan", "bozu", "kozo"]):
            return "CHILD"
        if any(w in n_l for w in ["staruszek", "staruszka", "dziadek", "babcia", "elderly", "old man", "old woman"]):
            return "ELDERLY"
        chars = self.get_characters_snapshot() if hasattr(self, "get_characters_snapshot") else (self.data.get("characters", {}) if hasattr(self, "data") else {})
        for k, v in list(chars.items()):
            if "->" not in k:
                k_l = k.lower()
                clean_k = extract_clean_speaker_name(k_l)
                if k_l == n_l or clean_k == n_l or n_l in k_l.split():
                    desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    if any(w in desc_v for w in ["dziecko", "dziewczynka", "chłopiec", "child", "young girl", "little girl", "young boy", "little boy"]):
                        return "CHILD"
                    if any(w in desc_v for w in ["staruszek", "staruszka", "dziadek", "babcia", "elderly", "old man", "old woman", "senior"]):
                        return "ELDERLY"
                    if any(w in desc_v for w in ["dorosły", "kobieta", "mężczyzna", "adult"]):
                        return "ADULT"
        return "UNKNOWN"

    def is_all_female_cast(self, cast: Any, min_size: int = 2) -> bool:
        """
        Returns True if all characters in the given cast are confirmed FEMALE and cast has at least min_size members.
        Excludes generic background/actor nouns from false positive validation.
        """
        named = [str(c).strip() for c in cast if c and not is_generic_actor_or_category(str(c).strip())]
        if len(named) < min_size:
            return False
        return all(self.get_character_gender(c, allow_generic_nouns=False) == "FEMALE" for c in named)

    def is_all_male_cast(self, cast: Any, min_size: int = 2) -> bool:
        """
        Returns True if all characters in the given cast are confirmed MALE and cast has at least min_size members.
        Excludes generic background/actor nouns from false positive validation.
        """
        named = [str(c).strip() for c in cast if c and not is_generic_actor_or_category(str(c).strip())]
        if len(named) < min_size:
            return False
        return all(self.get_character_gender(c, allow_generic_nouns=False) == "MALE" for c in named)

    def get_dual_pair_gender_type(self, names: Any) -> str:
        """
        Returns 'DUAL_FEMALE', 'DUAL_MALE', 'DUAL_MIXED', or 'UNKNOWN' for a pair of characters.
        """
        if not names:
            return "UNKNOWN"
        named = [str(c).strip() for c in names if c and not is_generic_actor_or_category(str(c).strip())]
        clean_names = [extract_clean_speaker_name(n).strip() for n in named]
        # Deduplicate while preserving unique named characters
        unique_names = []
        for n in clean_names:
            if n and n.lower() not in [u.lower() for u in unique_names]:
                unique_names.append(n)
        if len(unique_names) != 2:
            return "UNKNOWN"
        g1 = self.get_character_gender(unique_names[0], allow_generic_nouns=False)
        g2 = self.get_character_gender(unique_names[1], allow_generic_nouns=False)
        if g1 == "FEMALE" and g2 == "FEMALE":
            return "DUAL_FEMALE"
        elif g1 == "MALE" and g2 == "MALE":
            return "DUAL_MALE"
        elif (g1 == "FEMALE" and g2 == "MALE") or (g1 == "MALE" and g2 == "FEMALE"):
            return "DUAL_MIXED"
        return "UNKNOWN"

    @staticmethod
    def sanitize_pronominal_somatic_possession(text: str) -> str:
        return sanitize_pronominal_somatic_possession(text)

    @staticmethod
    def naturalize_adjacency_rejoinder(prior_q: str, resp: str) -> str:
        return naturalize_adjacency_rejoinder(prior_q, resp)

    @staticmethod
    def sanitize_deictic_motion_vector(text: str) -> str:
        return sanitize_deictic_motion_vector(text)

    @staticmethod
    def sanitize_sensory_pleonasm(text: str) -> str:
        return sanitize_sensory_pleonasm(text)

    @staticmethod
    def sanitize_closed_idioms_and_prepositions(text: str) -> str:
        return sanitize_closed_idioms_and_prepositions(text)

    def is_female_group_speaker(self, speaker_name: str) -> bool:
        """
        Returns True if the speaker label or category represents a confirmed female group
        (e.g. 'grupa_kobiet', 'zakonnice', 'dziewczęta', 'uczennice', 'służące', 'kobiety', 'matki').
        """
        if not speaker_name:
            return False
        spk_clean = extract_clean_speaker_name(speaker_name).strip().lower()
        if any(w in spk_clean for w in [
            "grupa_kobiet", "grupa kobiet", "dziewczęta", "dziewczyny", "kobiety",
            "uczennice", "kapłanki", "zakonnice", "służące", "siostry", "matki", "damy dworu"
        ]):
            return True
        return False

    def register_speaker_entity_type(self, name: str, entity_type: str) -> None:
        """
        Registers speaker grammatical identity type in SeriesBible (Filar CLXXVI - 0.00 PLN).
        entity_type: 'COLLECTIVE_VIRILE' | 'COLLECTIVE_NONVIRILE' | 'MAJESTIC_FEMALE' | 'MAJESTIC_MALE' | 'INDIVIDUAL'
        """
        if not name:
            return
        if "speaker_entity_types" not in self.data:
            self.data["speaker_entity_types"] = {}
        cl_name = extract_clean_speaker_name(name).strip().lower()
        self.data["speaker_entity_types"][cl_name] = entity_type

    def get_speaker_entity_type(self, speaker_name: str) -> str:
        """
        Retrieves speaker grammatical identity type (Filar CLXXVI - 0.00 PLN).
        Recognizes canonical known entities (e.g. Louis Arneb -> COLLECTIVE_VIRILE).
        """
        if not speaker_name:
            return "INDIVIDUAL"
        cl_name = extract_clean_speaker_name(speaker_name).strip().lower()
        with self._lock:
            types_items = list(self.data.get("speaker_entity_types", {}).items())
            chars_items = list(self.data.get("characters", {}).items())
        for k, v in types_items:
            if k == cl_name or k in cl_name or cl_name in k:
                return v

        # Canonical known patterns across major anime / literature
        if any(w in cl_name for w in ["louis arneb", "rui arunebu", "rui arnebu", "arneb", "arunebu", "żarłoczność", "zarlocznosc"]):
            return "COLLECTIVE_VIRILE"
        char_desc = ""
        for k, v in chars_items:
            if "->" not in k:
                k_l = k.lower()
                clean_k = extract_clean_speaker_name(k_l)
                if k_l == cl_name or clean_k == cl_name or cl_name in k_l:
                    char_desc = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    break

        if any(w in cl_name for w in ["królowa", "krolowa", "cesarzowa", "queen", "empress"]) or "monarchini" in char_desc:
            if "pluralis" in char_desc or "majestat" in char_desc or "my" in char_desc or any(w in cl_name for w in ["królowa", "krolowa", "cesarzowa"]):
                return "MAJESTIC_FEMALE"
        if any(w in cl_name for w in ["cesarz", "król", "krol", "emperor", "king"]) or "monarcha" in char_desc:
            if "pluralis" in char_desc or "majestat" in char_desc or "my" in char_desc or any(w in cl_name for w in ["cesarz", "król", "krol"]):
                return "MAJESTIC_MALE"

        return "INDIVIDUAL"

    def is_collective_virile_speaker(self, speaker_name: str) -> bool:
        """
        Returns True if the speaker represents a mixed/virile collective entity
        (e.g. Louis Arneb in Re:Zero, speaking for Ley, Roy and herself).
        Requires 1st-person plural virile agreement (-liśmy, byliśmy), immune to female scene overrides!
        """
        return self.get_speaker_entity_type(speaker_name) == "COLLECTIVE_VIRILE"

    def is_collective_nonvirile_speaker(self, speaker_name: str) -> bool:
        """
        Returns True if the speaker represents an exclusively female collective entity.
        """
        return self.get_speaker_entity_type(speaker_name) == "COLLECTIVE_NONVIRILE"

    def is_majestic_female_speaker(self, speaker_name: str) -> bool:
        """
        Returns True if the speaker is a female monarch using Pluralis Maiestatis.
        Requires 1st-person plural non-virile agreement (-łyśmy, byłyśmy), even in mixed/neutral scenes!
        """
        return self.get_speaker_entity_type(speaker_name) == "MAJESTIC_FEMALE"

    def is_majestic_male_speaker(self, speaker_name: str) -> bool:
        """
        Returns True if the speaker is a male monarch using Pluralis Maiestatis.
        """
        return self.get_speaker_entity_type(speaker_name) == "MAJESTIC_MALE"

    def infer_scene_cast_from_text(self, scene_texts: List[str], whisper_texts: Optional[List[str]] = None) -> Tuple[Set[str], Optional[str]]:
        """
        Scans dialogue lines within an anonymous scene (where ev.name is blank) for character mentions,
        vocatives, and distinctive plot anchors to determine the scene cast and gender exclusivity (0.00 PLN).
        Universal across all 16 series via dynamic scanning of characters and relationships.
        Returns: (detected_cast_set, 'FEMALE' | 'MALE' | None)
        """
        if isinstance(scene_texts, str):
            scene_texts = [scene_texts]
        if not scene_texts and not whisper_texts:
            return set(), None

        combined_text = " ".join(scene_texts or [])
        combined_lower = combined_text.lower()
        detected_cast: Set[str] = set()

        with self._lock:
            chars_keys = list(self.data.get("characters", {}).keys())
        for k in chars_keys:
            if "->" in k:
                continue
            parts = [p.strip() for p in k.split("/") if len(p.strip()) >= 3]
            for p in parts:
                if is_generic_actor_or_category(p) or self.is_non_character_entity(p):
                    continue
                # Generate transliteration and phonetic variants (e.g. Ögedei <-> Ogedei <-> Ugedej)
                variants = {p}
                p_l = p.lower()
                if "ö" in p_l:
                    variants.add(p.replace("Ö", "O").replace("ö", "o"))
                if "ü" in p_l:
                    variants.add(p.replace("Ü", "U").replace("ü", "u"))
                if "sorghaghtani" in p_l:
                    variants.add("Sorkaktani")
                if "ögedei" in p_l or "ogedei" in p_l:
                    variants.update({"Ugedej", "Ugedeja", "Ugedejowi", "Ugedejem"})
                if "tolui" in p_l:
                    variants.update({"Tołuj", "Tołuja", "Tołujowi", "Tołujem"})
                if "chagatai" in p_l:
                    variants.update({"Czagataj", "Czagataja", "Czagatajowi"})
                if "temüge" in p_l or "temuge" in p_l:
                    variants.update({"Temügego", "Temugego", "Temuge"})
                if "jochi" in p_l:
                    variants.update({"Dżoczi", "Dżocziego"})

                matched_any = False
                for v in variants:
                    v_esc = re.escape(v)
                    # Exclude 3rd-person genealogy, deceased houses or historical reference (e.g. Tolui's lineage / rodu Tołuja)
                    is_genealogy = bool(re.search(
                        rf"\b(?:houses?|lineages?|lineage|house|tomb|tombs|memory|death|grave|graves|ród|rodu|rody|rodów|grobu|grobów|pamięć|pamięci|wola|woli)\s+(?:of\s+|z\s+|wielkiego\s+chana\s+|grand\s+khan'?s?\s+)?[^.!?\n]*?\b{v_esc}\b|\b{v_esc}'s\s+(?:lineage|lineages|house|houses|memory|tomb|tombs|grave|graves|death|will)\b",
                        combined_text,
                        re.IGNORECASE
                    ))
                    if is_genealogy:
                        continue
                    if re.search(rf"\b{v_esc}\b", combined_text, re.IGNORECASE):
                        matched_any = True
                        break

                if matched_any:
                    detected_cast.add(p)

        # Dynamic relationship scanning across all series (e.g. A -> B where both are female/male)
        with self._lock:
            rels_keys = list(self.data.get("relationships", {}).keys()) if hasattr(self, "data") else []
        for rel_k in rels_keys:
            if "->" in rel_k:
                p_from, p_to = [p.strip() for p in rel_k.split("->", 1)]
                p_from_clean = extract_clean_speaker_name(p_from)
                p_to_clean = extract_clean_speaker_name(p_to)
                if len(p_from_clean) >= 3 and len(p_to_clean) >= 3:
                    has_from = bool(re.search(rf"\b{re.escape(p_from_clean)}\b", combined_text, re.IGNORECASE))
                    has_to = bool(re.search(rf"\b{re.escape(p_to_clean)}\b", combined_text, re.IGNORECASE))
                    if has_from and re.search(rf"\b(?:houses?|lineages?|lineage|house|ród|rodu|rody|rodów)\s+(?:of\s+|z\s+)?[^.!?\n]*?\b{re.escape(p_from_clean)}\b|\b{re.escape(p_from_clean)}'s\s+(?:lineage|house)\b", combined_text, re.IGNORECASE):
                        has_from = False
                    if has_to and re.search(rf"\b(?:houses?|lineages?|lineage|house|ród|rodu|rody|rodów)\s+(?:of\s+|z\s+)?[^.!?\n]*?\b{re.escape(p_to_clean)}\b|\b{re.escape(p_to_clean)}'s\s+(?:lineage|house)\b", combined_text, re.IGNORECASE):
                        has_to = False
                    if has_from or has_to:
                        g_from = self.get_character_gender(p_from_clean, allow_generic_nouns=False)
                        g_to = self.get_character_gender(p_to_clean, allow_generic_nouns=False)
                        if g_from in ("FEMALE", "MALE") and g_to in ("FEMALE", "MALE") and g_from == g_to:
                            detected_cast.add(p_from_clean)
                            detected_cast.add(p_to_clean)


        # Series-scoped plot anchors and context for anonymous historical scenes (0.00 PLN)
        if getattr(self, "anime_title", None) and "tenmaku" in str(self.anime_title).lower():
            if any(kw in combined_lower for kw in [
                "sorkaktani", "sorghaghtani", "cztery tysiące jurt", "four thousand tents",
                "töregene jest dla mnie", "don't bring töregene", "leave töregene out"
            ]):
                detected_cast.add("Boraqchin")
                detected_cast.add("Möge")
                for m_male in ["Ögedei", "Ogedei", "Tolui", "Chagatai", "Jochi", "Temüge", "Temuge"]:
                    detected_cast.discard(m_male)

        # Audio Whisper Ground Truth integration (if available)
        combined_whisper = " ".join(whisper_texts or []).lower() if whisper_texts else ""
        has_female_audio = any(m in combined_whisper for m in ["warawa", "妾", "atashi", "あたし", "atai", "あたい", "wa yo", "わよ", "no yo", "のよ", "kashira", "かしら"])
        has_male_audio = any(m in combined_whisper for m in ["ore", "俺", "boku", "僕", "washi", "わし", "sessha", "拙者", "da zo", "だぞ", "da ze", "だぜ"])

        gender_exclusive = None
        if len(detected_cast) >= 2:
            if self.is_all_female_cast(detected_cast, min_size=2):
                gender_exclusive = "FEMALE"
            elif self.is_all_male_cast(detected_cast, min_size=2):
                gender_exclusive = "MALE"

        return detected_cast, gender_exclusive

    def audit_speaker_metadata_against_audio(
        self,
        actor_name: str,
        audio_gender: Optional[str] = None,
        f0_hz: Optional[float] = None,
        whisper_gender: Optional[str] = None,
        scene_gender: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Audits untrusted actor tag from external fansub (.ass) against physical audio ground truth (0.00 PLN).
        Returns: (resolved_gender, is_contaminated)
        - If tag indicates MALE (e.g. 'Ögedei'), but audio F0 (>=185Hz / alt żeński), Whisper markers ('FEMALE'),
          or pre-pass scene exclusivity ('FEMALE') confirm female speaker, tag is demoted to 'UNTRUSTED_CONTRADICTION'
          and resolved_gender becomes 'FEMALE'.
        """
        if not actor_name or is_generic_actor_or_category(actor_name):
            return (audio_gender or whisper_gender or scene_gender or "UNKNOWN"), False

        actor_clean = extract_clean_speaker_name(actor_name).strip()
        canon_gender = self.get_character_gender(actor_clean, allow_generic_nouns=False)

        # Contamination condition: Canonical tag contradicted by objective physical acoustic evidence
        has_female_audio = (audio_gender == "FEMALE") or (f0_hz is not None and f0_hz >= 185.0) or (whisper_gender == "FEMALE")
        has_male_audio = (audio_gender == "MALE") or (f0_hz is not None and f0_hz <= 140.0) or (whisper_gender == "MALE")

        # Check if character is marked as a young boy or cross-gender role (voiced by female seiyū)
        char_desc_lower = ""
        if hasattr(self, "data") and "characters" in self.data:
            b_val = self.data["characters"].get(actor_clean, {})
            char_desc_lower = (b_val.get("description", "") if isinstance(b_val, dict) else str(b_val)).lower()
        is_boy_or_crossgender = any(k in char_desc_lower for k in [
            "chłopiec", "chłopak", "boy", "syn", "młodzieniec", "książę",
            "dziecko płci męskiej", "pax", "bocchan", "crossgender", "cross-gender", "seiyū żeński", "żeńskie seiyū",
            "uczeń", "schoolboy", "lad", "kid", "shōnen", "shonen", "brat", "brother", "wnuk", "grandson",
            "conan", "naruto", "luffy", "edward", "shinji", "killua"
        ]) or any(k in actor_clean.lower() for k in ["chłopiec", "chłopak", "boy", "bocchan", "lad", "kid"])

        if canon_gender == "MALE" and is_boy_or_crossgender:
            # Young boy voiced by female seiyū: high acoustic F0 is normal for age/actor, canonical gender is MALE
            return "MALE", False

        # Low-pitch female protection (matron, elderly, or raspy female seiyū)
        is_low_pitch_fem = (hasattr(self, "is_low_pitch_female") and self.is_low_pitch_female(actor_clean)) or any(k in char_desc_lower for k in [
            "starsza", "dojrzała", "babcia", "matrona", "cesarzowa", "chatun", "wiedźma", "ochrypły alt", "alt starszej"
        ])
        if canon_gender == "FEMALE" and is_low_pitch_fem:
            # Mature / raspy female voice: low acoustic F0 is natural, canonical gender is FEMALE
            return "FEMALE", False

        is_female_space = (scene_gender == "FEMALE")
        is_male_space = (scene_gender == "MALE")

        if canon_gender == "MALE" and (has_female_audio or is_female_space):
            return "FEMALE", True
        elif canon_gender == "FEMALE" and (has_male_audio or is_male_space):
            return "MALE", True

        return (canon_gender if canon_gender != "UNKNOWN" else (audio_gender or whisper_gender or scene_gender or "UNKNOWN")), False

    def register_tv_transition(self, char_a: str, char_b: str, new_tv_state: str, ep_idx: int = 0) -> None:
        """
        Registers an authorized narrative T-V transition between two characters (e.g. from FORMAL to INFORMAL).
        Prevents linter and memory from treating emotional intimate agreements as accidental drift errors.
        """
        if not char_a or not char_b:
            return
        if not hasattr(self, "data") or self.data is None:
            self.data = {}
        if "tv_transitions" not in self.data:
            self.data["tv_transitions"] = {}
        pair_key = " <-> ".join(sorted([char_a.strip().lower(), char_b.strip().lower()]))
        self.data["tv_transitions"][pair_key] = {
            "state": new_tv_state.upper(),
            "ep_idx": ep_idx
        }

    def get_authorized_tv_state(self, char_a: str, char_b: str) -> Optional[str]:
        """
        Returns authorized T-V state if an intentional narrative transition was registered.
        """
        if not char_a or not char_b or not hasattr(self, "data") or not self.data:
            return None
        pair_key = " <-> ".join(sorted([char_a.strip().lower(), char_b.strip().lower()]))
        return self.data.get("tv_transitions", {}).get(pair_key, {}).get("state")

    def update_character_gender_from_audio(self, name: str, gender: str) -> bool:
        """
        Updates an unconfirmed character's gender in Series Bible using definitive Japanese
        first-person audio markers (ore/boku -> MALE, atashi/atai -> FEMALE).
        Protected by symmetrical locks: cannot downgrade or overwrite confirmed MALE with FEMALE or vice versa.
        Thread-safe under concurrent batch processing.
        """
        if not name or gender not in ("MALE", "FEMALE"):
            return False
        with self._lock:
            clean_name = name.strip()
            existing_entry = self.data.get("characters", {}).get(clean_name)
            desc_v = ""
            if isinstance(existing_entry, dict):
                desc_v = str(existing_entry.get("description", ""))
            elif existing_entry:
                desc_v = str(existing_entry)

            # Symmetrical lock: already confirmed definitively by audio, quality gate, or explicit gender field
            has_confirmed_audio = "zweryfikowano z audio" in desc_v
            has_confirmed_qg = "zweryfikowano przez EpisodeQualityGate" in desc_v
            has_canonical_tag = bool(re.search(r"\[(KOBIETA|MĘŻCZYZNA)\s+\(Adresat\)", desc_v, re.IGNORECASE))
            has_explicit_gender = isinstance(existing_entry, dict) and existing_entry.get("gender") in ("MALE", "FEMALE")

            if has_confirmed_audio or has_confirmed_qg or has_canonical_tag or has_explicit_gender:
                return False

            existing_gender = self.get_character_gender(clean_name, allow_generic_nouns=False)
            if existing_gender in ("MALE", "FEMALE") and existing_gender != gender:
                # Symmetrical lock: cannot overwrite inferred gender with opposite audio gender
                return False

            desc = f"{'MĘŻCZYZNA' if gender == 'MALE' else 'KOBIETA'} (zweryfikowano z audio seiyū Whisper)"
            if clean_name not in self.data["characters"]:
                self.data["characters"][clean_name] = {"description": desc}
            else:
                entry = self.data["characters"][clean_name]
                if isinstance(entry, dict):
                    cur_desc = entry.get("description", "")
                    entry["description"] = f"{cur_desc}; {desc}".strip("; ")
                else:
                    self.data["characters"][clean_name] = {"description": f"{entry}; {desc}".strip("; ")}

            self.data["declensions"][clean_name] = generate_polish_name_declension(clean_name, gender)
            return True

    def is_low_pitch_female(self, name: str) -> bool:
        """
        Returns True if character is a confirmed female with an elderly, mature, raspy, or deep vocal profile,
        immunizing her against false male overrides from low F0 audio detectors.
        """
        if not name:
            return False
        clean = extract_clean_speaker_name(name)
        n_l = (clean or name).strip().lower()

        MATRON_ROLE_KEYWORDS = [
            "starsza", "dojrzała", "babcia", "babci", "matrona", "matron", "cesarzow", "chatun",
            "pierwsza małżonka", "wiedźma", "seniorka", "staruszka", "ochrypł", "niski głos"
        ]

        chars = self.get_characters_snapshot() if hasattr(self, "get_characters_snapshot") else (self.data.get("characters", {}) if hasattr(self, "data") else {})
        for k, v in list(chars.items()):
            if "->" not in k:
                k_l = k.lower()
                clean_k = extract_clean_speaker_name(k_l)
                if k_l == n_l or clean_k == n_l or n_l in k_l.split() or k_l in n_l:
                    desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    is_female = any(w in desc_v for w in ["female", "kobieta", "dziewczyn", "żeńsk"])
                    if is_female and any(w in desc_v for w in MATRON_ROLE_KEYWORDS):
                        return True
        return False

    def is_female_pair(self, name1: str, name2: str) -> bool:
        """
        Returns True if both named entities are confirmed female characters,
        mandating the use of non-virile dual numerals/pronouns ('obie / dla was obu')
        instead of virile/collective forms ('oboje / obaj').
        """
        if not name1 or not name2:
            return False
        g1 = self.get_character_gender(name1)
        g2 = self.get_character_gender(name2)
        return (g1 == "FEMALE" and g2 == "FEMALE")

    def get_dual_pair_gender_type(self, names_or_name1: Union[List[str], Set[str], Tuple[str, ...], str], name2: Optional[str] = None) -> str:
        """
        Determines the gender type of a two-person group (dual pair):
        - 'DUAL_FEMALE': both members are confirmed female (requires 'obie / was obu / z wami obiema')
        - 'DUAL_MALE': both members are confirmed male (requires 'obaj / was obu / z wami oboma')
        - 'DUAL_MIXED': 1 female + 1 male (requires collective 'oboje / was obojga / wam obojgu / z wami obojgiem')
        - 'UNKNOWN': fewer than 2 valid characters or unknown genders
        """
        if name2 is not None:
            names = [str(names_or_name1), str(name2)]
        elif isinstance(names_or_name1, (list, set, tuple)):
            names = list(names_or_name1)
        else:
            names = [str(names_or_name1)]

        clean_names = [n.strip() for n in names if n and str(n).strip()]
        if len(clean_names) < 2:
            return "UNKNOWN"

        distinct = []
        for cn in clean_names:
            if cn not in distinct:
                distinct.append(cn)
            if len(distinct) == 2:
                break
        if len(distinct) < 2:
            return "UNKNOWN"

        g1 = self.get_character_gender(distinct[0])
        g2 = self.get_character_gender(distinct[1])

        if g1 == "FEMALE" and g2 == "FEMALE":
            return "DUAL_FEMALE"
        if g1 == "MALE" and g2 == "MALE":
            return "DUAL_MALE"
        if (g1 == "FEMALE" and g2 == "MALE") or (g1 == "MALE" and g2 == "FEMALE"):
            return "DUAL_MIXED"
        return "UNKNOWN"

    def is_non_character_entity(self, name: str) -> bool:
        """
        Determines whether a name refers to an organization, realm, institution, faction, location,
        ethnonym, or collective group, preventing it from ever being treated as a masculine/feminine character in name declension engines.
        """
        if not name:
            return False
        n_l = name.strip().lower()
        if n_l in INDECLINABLE_FRENCH_TOPONYMS:
            return True
        if n_l.endswith("um"):
            return True
        if n_l in ETHNONYMS_AND_COLLECTIVES or any(n_l.startswith(eth) for eth in ["mongol", "tatar", "merkit", "persian", "roman", "nomad", "pastoralist"]):
            return True
        REALM_INSTITUTION_NOUNS = {
            "imperium", "królestwo", "cesarstwo", "senat", "republika", "zakon", "gildia", "rada",
            "armia", "muzeum", "liceum", "koloseum", "akwarium", "centrum", "forum", "archiwum",
            "kościół", "rząd", "dwór", "trybunał", "pałac", "państwo", "akademia", "uniwersytet"
        }
        if n_l in REALM_INSTITUTION_NOUNS:
            return True
        KNOWN_FANTASY_TOPONYMS = {
            "hiden", "haiden", "boelate", "boelat", "boelatu", "boirate", "eslinn", "esrin", "solsein", "solcein",
            "elbe", "erbe", "hyderat", "haiderat", "heiderat", "esleburg", "esreburg", "edsea", "edthea",
            "kanyou", "kantan", "xianyang", "handan", "chouhei", "sanyou", "tonryuu", "sai", "zui",
            "kamakura", "suwa", "kyoto", "shinano", "musashi", "hiei", "hieizan", "shimotsuke",
            "ridill", "minerva", "felm", "carnelian",
            "samarkand", "karakorum", "bukhara", "nishapur", "baghdad", "tabriz", "herat",
            "yamato", "owari", "mikawa", "echigo", "kai",
            "otaru", "sapporo", "asahikawa", "abashiri", "karafuto", "nemuro", "yubari",
            "melini"
        }
        if n_l in KNOWN_FANTASY_TOPONYMS:
            return True
        for section in ["organizations", "factions", "realms", "locations", "places", "cities", "countries", "historical_context", "relics", "artifacts", "weapons"]:
            with self._lock:
                sec_dict = dict(self.data.get(section, {})) if isinstance(self.data.get(section, {}), dict) else {}
            if sec_dict:
                for k, v in list(sec_dict.items()):
                    if k.lower() == n_l:
                        return True
                    if isinstance(v, dict):
                        if v.get("canonical_name", "").lower() == n_l or v.get("short_name", "").lower() == n_l or v.get("name", "").lower() == n_l:
                            return True
        # Check glossary entries for realm/toponym/location designations
        with self._lock:
            glossary_dict = dict(self.data.get("glossary", {})) if isinstance(self.data.get("glossary", {}), dict) else {}
        if glossary_dict:
            TOPONYM_KWS = {"kraina", "królestwo", "cesarstwo", "toponim", "lokacja", "kopalnia", "stolica", "zamek", "twierdza", "akademia", "instytucja", "miasto", "prowincja", "prefektura", "rzeka", "góra", "relikt", "artefakt", "święty oręż"}
            for k, v in list(glossary_dict.items()):
                k_l = str(k).lower()
                v_str = str(v).lower()
                if any(kw in v_str for kw in TOPONYM_KWS):
                    if k_l == n_l or n_l in k_l.split():
                        return True
                    v_tokens = [w.lower() for w in re.findall(r"\b[A-Za-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]{3,}\b", v_str)]
                    if n_l in v_tokens:
                        return True
        return False

    def get_ethnonym_canonical(self, ethnonym: str) -> Optional[Dict[str, str]]:
        """
        Returns canonical Polish plural declension for an ethnonym/demonym (e.g. 'Mongołowie'),
        enforcing the rule that nation/ethnic references require plural, not English singularis pro plurali.
        """
        if not ethnonym:
            return None
        eth_norm = ethnonym.strip().lower()
        ETHNONYMS_CANONICAL = {
            "mongol": {
                "M": "Mongołowie", "D": "Mongołów", "C": "Mongołom", "B": "Mongołów",
                "N": "Mongołami", "Ms": "Mongołach", "W": "Mongołowie"
            },
            "mongoł": {
                "M": "Mongołowie", "D": "Mongołów", "C": "Mongołom", "B": "Mongołów",
                "N": "Mongołami", "Ms": "Mongołach", "W": "Mongołowie"
            },
            "tatar": {
                "M": "Tatarzy", "D": "Tatarów", "C": "Tatarom", "B": "Tatarów",
                "N": "Tatarami", "Ms": "Tatarach", "W": "Tatarzy"
            },
            "merkit": {
                "M": "Merkici", "D": "Merkitów", "C": "Merkitom", "B": "Merkitów",
                "N": "Merkitami", "Ms": "Merkitach", "W": "Merkici"
            },
            "merkid": {
                "M": "Merkidzi", "D": "Merkidów", "C": "Merkidom", "B": "Merkidów",
                "N": "Merkidami", "Ms": "Merkidach", "W": "Merkidzi"
            }
        }
        res = ETHNONYMS_CANONICAL.get(eth_norm)
        if res:
            return res
        with self._lock:
            factions = dict(self.data.get("factions", {})) if isinstance(self.data.get("factions", {}), dict) else {}
        if factions:
            for f_key, f_val in list(factions.items()):
                if f_key.lower() == eth_norm and isinstance(f_val, dict) and "cases_pl" in f_val:
                    return f_val["cases_pl"]
                if isinstance(f_val, dict) and f_val.get("name", "").lower() == eth_norm and "cases_pl" in f_val:
                    return f_val["cases_pl"]
        return None

    def get_scoped_characters_for_scene(
        self,
        speakers: Optional[Set[str]] = None,
        dialogue_text: str = "",
        max_chars: int = 4
    ) -> Dict[str, str]:
        """
        Extracts only characters active in the current scene (speakers or mentioned by name)
        from the Series Bible characters table, preventing LLM cognitive saturation.
        """
        if not hasattr(self, "data") or "characters" not in self.data:
            return {}

        active_chars: Dict[str, str] = {}
        speakers_clean = {extract_clean_speaker_name(s).strip().lower() for s in (speakers or set()) if s}
        corpus_lower = (dialogue_text or "").lower()

        with self._lock:
            bible_chars = list(self.data.get("characters", {}).items())
        for name, info in bible_chars:
            if "->" in name:
                continue
            desc = info.get("description", "") if isinstance(info, dict) else str(info)
            name_clean = extract_clean_speaker_name(name).strip()
            name_lower = name_clean.lower()
            name_stem = name_lower[:max(3, len(name_lower) - 2)]

            is_active_speaker = name_lower in speakers_clean or any(s in name_lower or name_lower in s for s in speakers_clean if len(s) >= 3)
            is_mentioned = name_stem in corpus_lower if len(name_stem) >= 3 else False

            if is_active_speaker or is_mentioned:
                active_chars[name] = desc

        # Fallback if no characters matched: return top characters capped at max_chars
        if not active_chars and bible_chars:
            for name, info in bible_chars[:max_chars]:
                if "->" not in name:
                    desc = info.get("description", "") if isinstance(info, dict) else str(info)
                    active_chars[name] = desc

        return active_chars

    def _sanitize_character_entry(self, name: str, details: str) -> str:
        """
        Guards Series Bible against gender poisoning and ambiguous descriptions (Layer 5).
        - Filters out collective feminine nouns (e.g. 'służące w obozie', 'koleżanki')
          when applied to male or mixed characters.
        - Ensures explicit gender clarity for canonical oriental names on '-a'.
        """
        if not details:
            return ""

        CANONICAL_MALE_NAMES = {
            "shira", "akira", "gaara", "ashitaka", "kiba", "soma", "kenta",
            "ryoma", "hanza", "koba", "soya", "toma", "genga", "sinbad", "judar", "alibaba"
        }

        clean_desc = sanitize_lexical_text(details.strip())
        name_lower = name.lower()

        # Distinguish standalone characters from relationships (Speaker -> Listener)
        is_rel = "->" in name
        speaker = ""
        listener = ""
        if is_rel:
            parts = [p.strip() for p in name.split("->", 1)]
            speaker = parts[0]
            listener = parts[1] if len(parts) > 1 else ""

        target_name = listener.lower() if is_rel else name_lower
        target_is_male = any(m == target_name or f" {m} " in f" {target_name} " for m in CANONICAL_MALE_NAMES)
        target_is_female = False

        # Look up confirmed target character gender in Series Bible
        if hasattr(self, "data") and "characters" in self.data:
            with self._lock:
                chars_items = list(self.data["characters"].items())
            for k, v in chars_items:
                if "->" not in k:
                    k_l = k.lower()
                    if k_l == target_name or (len(k_l) >= 3 and k_l in target_name) or (len(target_name) >= 3 and target_name in k_l):
                        desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                        if any(w in desc_v for w in MALE_ROLE_KEYWORDS):
                            target_is_male = True
                        if is_male_role_text(desc_v):
                            target_is_male = True
                        if is_female_role_text(desc_v):
                            target_is_female = True

        # In relationships, extract recipient description part (after '->' in brackets e.g. '(koleżanka -> przyjaciel)')
        rel_target_desc = clean_desc.split("->")[-1].lower() if ("->" in clean_desc and is_rel) else clean_desc.lower()
        if is_male_role_text(rel_target_desc) or re.search(r"\bpanie\s+[A-ZĄĆĘŁŃÓŚŹŻ]", clean_desc):
            target_is_male = True
        if is_female_role_text(rel_target_desc) and not re.search(r"\bpanie\s+[A-ZĄĆĘŁŃÓŚŹŻ]", clean_desc):
            target_is_female = True

        # Resolve conflict: target cannot be both male and female
        if target_is_male and target_is_female:
            if is_male_role_text(rel_target_desc) or re.search(r"\bpanie\s+[A-ZĄĆĘŁŃÓŚŹŻ]", clean_desc):
                target_is_female = False
            elif is_female_role_text(rel_target_desc):
                target_is_male = False


        # Clean existing poisoned tags if they contradict target gender
        if target_is_male:
            clean_desc = re.sub(r"\s*\[KOBIETA \(Adresat\)[^\]]*\]", "", clean_desc).strip()
        if target_is_female:
            clean_desc = re.sub(r"\s*\[MĘŻCZYZNA \(Adresat\)[^\]]*\]", "", clean_desc).strip()

        # Check if the relationship or character involves a confirmed male character
        involves_male = target_is_male or any(m in name_lower for m in CANONICAL_MALE_NAMES)
        if not involves_male and hasattr(self, "data") and "characters" in self.data:
            with self._lock:
                chars_items_male = list(self.data["characters"].items())
            for k, v in chars_items_male:
                if k.lower() in name_lower:
                    desc_v = str(v.get("description", "") if isinstance(v, dict) else v).lower()
                    if any(w in desc_v for w in MALE_ROLE_KEYWORDS):
                        involves_male = True
                        break

        # If a relationship or entry involves a male character, forbid collective feminine nouns
        if involves_male:
            # Replace ambiguous "służące" with "służba / podwładni"
            clean_desc = re.sub(r"\bsłużące\b", "służba", clean_desc, flags=re.IGNORECASE)
            clean_desc = re.sub(r"\bkoleżanki\b", "znajomi", clean_desc, flags=re.IGNORECASE)
            clean_desc = re.sub(r"\bprzyjaciółki\b", "przyjaciele", clean_desc, flags=re.IGNORECASE)

        # For standalone male names ending in '-a', enforce explicit gender and directive
        is_standalone_male_a = any(name_lower == m for m in CANONICAL_MALE_NAMES)
        if is_standalone_male_a:
            if "mężczyzna" not in clean_desc.lower() and "male" not in clean_desc.lower():
                clean_desc = f"MĘŻCZYZNA (postać) - {clean_desc}".strip()
            if "kategoryczny nakaz form męskich" not in clean_desc.lower() and "ostrzegał" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [KATEGORYCZNY NAKAZ form męskich w czasie przeszłym: mówił / ostrzegał / pomógł]".strip()

        # Safeguard plural groups morphology in Series Bible (Filar CLXIII)
        is_female_group = any(w in name_lower or w in clean_desc.lower() for w in ["grupa kobiet", "grupa dziewcząt", "uczennice", "kapłanki", "dziewczęta", "wojowniczki"])
        if is_female_group and not involves_male:
            if "niemęskoosobow" not in clean_desc.lower() and "-łyście" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [GRUPA KOBIET - Wymóg form niemęskoosobowych: -łyście / byłyście gotowe]".strip()

        is_male_group = any(w in name_lower or w in clean_desc.lower() for w in ["grupa mężczyzn", "grupa chłopaków", "żołnierze", "panowie", "wojownicy"])
        if is_male_group:
            if "męskoosobow" not in clean_desc.lower() and "-liście" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [GRUPA MĘŻCZYZN - Wymóg rodzaju męskoosobowego: -liście / byliście gotowi]".strip()

        # Safeguard singular addressee morphology in Series Bible (Filar CLXIII)
        is_single_female = (target_is_female or bool(re.search(r"\b(?:kobieta|female|dziewczyna|nauczycielka|uczennica|kapłanka)\b", rel_target_desc, re.IGNORECASE))) and not is_female_group and not target_is_male
        if is_single_female:
            if "2. os. lp." not in clean_desc.lower() and "-łaś" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [KOBIETA (Adresat) - W 2. os. lp. 'ty' wymóg form żeńskich: byłaś / zrobiłaś / jesteś pewna]".strip()

        is_single_male = (target_is_male or bool(re.search(r"\b(?:mężczyzna|male|chłopak|żołnierz|pan|uczeń)\b", rel_target_desc, re.IGNORECASE))) and not is_male_group and not target_is_female
        if is_single_male:
            if "2. os. lp." not in clean_desc.lower() and "-łeś" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [MĘŻCZYZNA (Adresat) - W 2. os. lp. 'ty' wymóg form męskich: byłeś / zrobiłeś / jesteś pewien]".strip()

        # Safeguard hierarchical honorific relationships and anti-hybrid vocatives (Filar C & CLVII)
        is_subordinate_or_disciple = any(w in clean_desc.lower() for w in ["uczeń", "uczennica", "służąca", "niewolnica", "adept", "podwładn"])
        is_master_or_superior = any(w in clean_desc.lower() for w in ["mistrz", "arcymag", "pan ", "mentor", "zwierzchnik", "lord"])
        if is_subordinate_or_disciple or is_master_or_superior:
            if "t-v invariance" not in clean_desc.lower() and "panie" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [RELACJA HIERARCHICZNA (T-V Invariance): stały zwrot formalny 'Pan / Panie [Imię]', zakaz hybryd 'Imię... ma pan' oraz odporność na opuszczanie -sama]".strip()

        # Safeguard temporal continuity & scene boundary protection (Filar CLXV)
        is_private_relationship = any(w in clean_desc.lower() for w in ["na osobności", "w cztery oczy", "prywatn", "zaufan", "sekret"])
        if is_private_relationship:
            if "filar clxv" not in clean_desc.lower() and "dyskontinuitet" not in clean_desc.lower():
                clean_desc = f"{clean_desc} [OCHRONA PRZESKOKÓW SCEN (Filar CLXV): w rozmowach na osobności po przejściu zakaz opóźnionego 'Jasne, o co chodzi?' -> otwarcie dialogu: 'Więc o co chodzi?']".strip()

        return clean_desc

    def update_from_episode_profile(
        self,
        episode_name: str = "",
        characters: Optional[Dict[str, str]] = None,
        glossary: Optional[Dict[str, str]] = None,
        plot_anchors: Optional[Dict[str, str]] = None,
        relationships: Optional[Dict[str, str]] = None,
    ):
        """Updates glossary, character registry, relationships, and plot anchors based on Profiler output of a new episode (Thread-Safe)."""
        with self._lock:
            if episode_name and episode_name not in self.data["episodes_translated"]:
                self.data["episodes_translated"].append(episode_name)

            if characters:
                FEMALE_KEYWORDS = [
                    "kobieta", "żeńsk", "female", "dziewczyn", "nauczycielk", "czarodziejk",
                    "szpieżk", "wojowniczk", "kapłank", "służąc", "pani ", "panią", "bohaterk",
                    "arystokratk", "władczyn", "królow", "księżniczk", "matk", "córk", "siostr"
                ]
                if "declensions" not in self.data:
                    self.data["declensions"] = {}
                if "relationships" not in self.data:
                    self.data["relationships"] = {}

                for name, details in list(characters.items()):
                    if not name or not details:
                        continue
                    clean_details = self._sanitize_character_entry(name, details)
                    if "->" in name:
                        self.data["relationships"][name] = clean_details
                        self.data["characters"][name] = {"description": clean_details}
                        parts = [p.strip() for p in name.split("->")]
                        for idx, p in enumerate(parts):
                            clean_p = re.sub(r"-(?:sensei|kun|chan|san|sama|senpai)\b", "", p, flags=re.IGNORECASE).strip()
                            clean_p = re.sub(r"^(?:Pani|Pan|Kapitan|Dziekan|Kardynał|Generał|Doktor|Profesor)\s+", "", clean_p).strip()
                            if clean_p and len(clean_p) >= 2 and not any(ch in clean_p for ch in "{}[]():;"):
                                if clean_p not in self.data["characters"]:
                                    p_details = clean_details
                                    if "->" in clean_details and len(parts) == 2:
                                        detail_halves = clean_details.split("->", 1)
                                        p_details = detail_halves[idx].strip()

                                    p_g = "UNKNOWN"
                                    if is_female_role_text(p_details) and not is_male_role_text(p_details):
                                        p_g = "FEMALE"
                                    elif is_male_role_text(p_details) and not is_female_role_text(p_details):
                                        p_g = "MALE"
                                    elif is_male_role_text(clean_details) and ("panie " in clean_details.lower() or "pan " in clean_details.lower()) and idx == 1:
                                        p_g = "MALE"
                                    else:
                                        p_lower = clean_p.lower()
                                        p_tokens = p_lower.split()
                                        if p_lower in CANONICAL_MALE_NAMES or any(t in CANONICAL_MALE_NAMES for t in p_tokens):
                                            p_g = "MALE"
                                        elif p_lower.endswith("a") and (p_lower not in CANONICAL_MALE_NAMES and not any(t in CANONICAL_MALE_NAMES for t in p_tokens)):
                                            p_g = "FEMALE"
                                        else:
                                            p_g = "MALE"

                                    g_str = "KOBIETA" if p_g == "FEMALE" else "MĘŻCZYZNA"
                                    self.data["characters"][clean_p] = {"description": f"{g_str} (wyodrębniono z relacji serii)"}
                                    self.data["declensions"][clean_p] = generate_polish_name_declension(clean_p, p_g)
                        continue

                    if name not in self.data["characters"]:
                        self.data["characters"][name] = {"description": clean_details}
                    else:
                        existing_entry = self.data["characters"][name]
                        existing_desc = existing_entry.get("description", "") if isinstance(existing_entry, dict) else str(existing_entry)
                        existing_lower = existing_desc.lower()

                        # Protect confirmed gender against downgrading or overwriting (both male and female)
                        is_definite_female = any(w in clean_details.lower() for w in ["córka", "cesarzowa", "chatun", "żona", "małżonka", "matka", "księżniczka", "królowa"])
                        has_confirmed_male = any(w in existing_lower for w in ["mężczyzna", "męsk", "male", "kategoryczny nakaz form męskich"]) and not is_definite_female
                        is_incoming_female = any(w in clean_details.lower() for w in ["kobieta", "żeńsk", "female", "służąca", "nauczycielka", "dziewczyna", "cesarzowa", "chatun", "córka", "żona"])
                        if has_confirmed_male and is_incoming_female:
                            continue

                        has_confirmed_female = any(w in existing_lower for w in ["kobieta", "żeńsk", "female", "dziewczyna", "kategoryczny nakaz form żeńskich", "nauczycielka"])
                        is_incoming_male = any(w in clean_details.lower() for w in ["mężczyzna", "męsk", "male", "chłopak"])
                        if has_confirmed_female and is_incoming_male:
                            continue

                        # If existing entry has rich directives/seiyū, do not overwrite with bare string
                        has_rich_directives = any(w in existing_lower for w in ["kategoryczny", "nakaz", "seiyū", "bezwzględnie formy"])
                        if has_rich_directives and not any(w in clean_details.lower() for w in ["kategoryczny", "nakaz"]):
                            continue

                        self.data["characters"][name] = {"description": clean_details}

                    # Generate and store 7-case Polish declension matrix
                    clean_details_sanitized = re.sub(r"zakaz\s+form\s+(?:żeńsk|męsk)[a-ząćęłńóśźż]*", "", clean_details.lower())
                    if is_male_role_text(clean_details_sanitized) and not is_female_role_text(clean_details_sanitized):
                        c_gender = "MALE"
                    elif is_female_role_text(clean_details_sanitized) and not is_male_role_text(clean_details_sanitized):
                        c_gender = "FEMALE"
                    elif any(w in clean_details_sanitized for w in ["mężczyzna", "męsk", "male", "chłopak"]):
                        c_gender = "MALE"
                    elif any(w in clean_details_sanitized for w in FEMALE_KEYWORDS):
                        c_gender = "FEMALE"
                    else:
                        c_gender = "UNKNOWN"

                    if "/" in name:
                        names_to_decline = [p.strip() for p in name.split("/")]
                    else:
                        names_to_decline = [name]

                    for single_n in names_to_decline:
                        if single_n and len(single_n) >= 3 and not any(ch in single_n for ch in "->/"):
                            self.data["declensions"][single_n] = generate_polish_name_declension(single_n, c_gender)

            if glossary:
                for k, v in list(glossary.items()):
                    # Store non-trivial terms only and sanitize parenthetical descriptions
                    if k and v and len(k) > 1 and len(v) > 1:
                        clean_k = str(k).strip()
                        clean_v = sanitize_lexical_text(re.sub(r"\s*[\(\[].*?[\)\]]", "", v).strip())
                        if clean_k and clean_v:
                            # Case-insensitive update to prevent duplicate collisions
                            norm_k = clean_k.lower()
                            for old_k in list(self.data["glossary"].keys()):
                                if old_k.lower() == norm_k and old_k != clean_k:
                                    del self.data["glossary"][old_k]
                            self.data["glossary"][clean_k] = clean_v
                            # Auto-generate 7-case declension for proper terms/entities/titles in glossary
                            if len(clean_v) >= 3 and not any(ch in clean_v for ch in "{}[]():;"):
                                if "declensions" not in self.data:
                                    self.data["declensions"] = {}
                                if clean_v not in self.data["declensions"] and clean_v[0].isupper():
                                    self.data["declensions"][clean_v] = generate_polish_name_declension(clean_v, "UNKNOWN")

            if plot_anchors:
                if "plot_anchors" not in self.data:
                    self.data["plot_anchors"] = {}
                for k, v in list(plot_anchors.items()):
                    if k and v:
                        clean_k = str(k).strip()
                        clean_v = sanitize_lexical_text(str(v).strip())
                        if clean_k and clean_v:
                            self.data["plot_anchors"][clean_k] = clean_v

            if relationships:
                if "relationships" not in self.data:
                    self.data["relationships"] = {}
                for rel_k, rel_v in list(relationships.items()):
                    if rel_k and rel_v:
                        self.data["relationships"][rel_k] = sanitize_lexical_text(str(rel_v).strip())
                        # Also extract names from relationships to decline them
                        for part in re.split(r"->|/|,", rel_k):
                            part_clean = part.strip()
                            if len(part_clean) >= 3 and not any(ch in part_clean for ch in "{}[]():;"):
                                if part_clean not in self.data["declensions"]:
                                    self.data["declensions"][part_clean] = generate_polish_name_declension(part_clean, "UNKNOWN")

            self.save()

    def assimilate_quality_gate_invariants(self, quality_gate_fixes: List[Any]):
        """
        Closed-loop learning engine (Layer 2).
        Ingests 100% confirmed invariants from EpisodeQualityGate post-pass
        (character gender, 7-case foreign name declensions, T-V address forms)
        and commits them permanently to the Series Bible.
        """
        if not quality_gate_fixes:
            return

        with self._lock:
            has_updates = False
            if "characters" not in self.data:
                self.data["characters"] = {}
            if "declensions" not in self.data:
                self.data["declensions"] = {}

            for fix_item in quality_gate_fixes:
                # 1. Structured fix dictionary
                if isinstance(fix_item, dict):
                    f_type = fix_item.get("type", "")
                    c_name = fix_item.get("character") or fix_item.get("name")
                    if c_name and f_type == "gender":
                        gen = fix_item.get("gender", "").upper()
                        if gen in ["MALE", "FEMALE"]:
                            desc = f"{'MĘŻCZYZNA' if gen == 'MALE' else 'KOBIETA'} (zweryfikowano przez EpisodeQualityGate)"
                            self.data["characters"][c_name] = {"description": desc, "source": "quality_gate"}
                            self.data["declensions"][c_name] = generate_polish_name_declension(c_name, gen)
                            has_updates = True
                    elif c_name and f_type == "declension":
                        decl_map = fix_item.get("declension")
                        if isinstance(decl_map, dict):
                            self.data["declensions"][c_name] = decl_map
                            has_updates = True

                # 2. String parsing from EpisodeQualityGate log lines
                elif isinstance(fix_item, str):
                    # Gender confirmation: e.g. "potwierdzona płeć męska" or "potwierdzona płeć żeńska"
                    m_gen = re.search(r"'(?:([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\.\.\.[^']*|[^']*\.\.\.\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+))'.*?potwierdzona płeć (męska|żeńska)", fix_item)
                    if m_gen:
                        char_name = m_gen.group(1) or m_gen.group(2)
                        gender_str = "MALE" if m_gen.group(3) == "męska" else "FEMALE"
                        is_generic_actor = is_generic_actor_or_category(char_name) or bool(re.match(r"^(?:man|male|boy|guy|woman|female|girl|lady|mężczyzna|kobieta|chłopak|dziewczyna|facet|pan|pani)\s+[a-z0-9]+$", char_name, re.IGNORECASE))
                        if char_name and len(char_name) >= 3 and not is_generic_actor:
                            desc = f"{'MĘŻCZYZNA' if gender_str == 'MALE' else 'KOBIETA'} (zweryfikowano przez EpisodeQualityGate)"
                            self.data["characters"][char_name] = {"description": desc, "source": "quality_gate"}
                            self.data["declensions"][char_name] = generate_polish_name_declension(char_name, gender_str)
                            has_updates = True

                    # 1st-person speaker gender confirmation:
                    m_spk = re.search(r"skorygowano 1\. os\. na rodzaj (męski|żeński) dla mówc(?:y|zyni) '([^']+)'", fix_item)
                    if m_spk:
                        gender_str = "MALE" if m_spk.group(1) == "męski" else "FEMALE"
                        char_name = m_spk.group(2).strip()
                        is_generic_actor = is_generic_actor_or_category(char_name) or bool(re.match(r"^(?:man|male|boy|guy|woman|female|girl|lady|mężczyzna|kobieta|chłopak|dziewczyna|facet|pan|pani)\s+[a-z0-9]+$", char_name, re.IGNORECASE))
                        if char_name and len(char_name) >= 3 and not is_generic_actor:
                            desc = f"{'MĘŻCZYZNA' if gender_str == 'MALE' else 'KOBIETA'} (zweryfikowano przez EpisodeQualityGate)"
                            self.data["characters"][char_name] = {"description": desc, "source": "quality_gate"}
                            self.data["declensions"][char_name] = generate_polish_name_declension(char_name, gender_str)
                            has_updates = True

                    # Prepositional Foreign Name Declension: e.g. "ujednolicono formę imienia po przyimku na 'Drela'"
                    m_prep = re.search(r"ujednolicono formę (?:imienia po przyimku|na) '([^']+)'", fix_item)
                    if m_prep:
                        decl_form = m_prep.group(1)
                        for existing_name in list(self.data["characters"].keys()) + list(self.data["declensions"].keys()):
                            if len(existing_name) >= 3 and decl_form.lower().startswith(existing_name[:max(3, len(existing_name)-2)].lower()):
                                if existing_name in self.data["declensions"]:
                                    self.data["declensions"][existing_name]["D"] = decl_form
                                    has_updates = True

                    # Vocative confirmation: e.g. "ujednolicono wołacz na 'Andrewie'"
                    m_voc = re.search(r"ujednolicono wołacz na '([^']+)'", fix_item)
                    if m_voc:
                        voc_form = m_voc.group(1)
                        for existing_name in list(self.data["characters"].keys()) + list(self.data["declensions"].keys()):
                            if len(existing_name) >= 3 and voc_form.lower().startswith(existing_name[:max(3, len(existing_name)-2)].lower()):
                                if existing_name in self.data["declensions"]:
                                    self.data["declensions"][existing_name]["W"] = voc_form
                                    has_updates = True

                    # Locative confirmation: e.g. "ujednolicono formę na 'Nathanie' po przyimku miejscownika"
                    m_loc = re.search(r"ujednolicono formę na '([^']+)' po przyimku miejscownika", fix_item)
                    if m_loc:
                        loc_form = m_loc.group(1)
                        for existing_name in list(self.data["characters"].keys()) + list(self.data["declensions"].keys()):
                            if len(existing_name) >= 3 and loc_form.lower().startswith(existing_name[:max(3, len(existing_name)-2)].lower()):
                                if existing_name in self.data["declensions"]:
                                    self.data["declensions"][existing_name]["Ms"] = loc_form
                                    has_updates = True

            if has_updates:
                self.save()

    def format_for_prompt(self) -> str:
        """Formats Series Bible into a compact section for LLM prompt injection (Thread-Safe)."""
        lines = []
        has_content = False

        with self._lock:
            chars_items = list(self.data.get("characters", {}).items())[:8]
            rels_items = list(self.data.get("relationships", {}).items())[:8]
            decls_items = list(self.data.get("declensions", {}).items())[:6]
            gloss_items = list(self.data.get("glossary", {}).items())[:12]
            canon_items = list(self.data.get("fansub_canon", {}).items())[:8]
            anchors_items = list(self.data.get("plot_anchors", {}).items())[:8]
            ep_count = len(self.data.get("episodes_translated", []))

        if chars_items or gloss_items or anchors_items or decls_items or canon_items:
            lines.append("--- BIBLIA SERIALU (PAMIĘĆ MIĘDZYODCINKOWA SEZONU) ---")
            lines.append(f"Seria: '{self.anime_title}' (Przetłumaczono odcinków: {ep_count})")
            
            if chars_items:
                lines.append("• Kluczowe postacie z poprzednich odcinków:")
                for name, info in chars_items:
                    desc = info.get("description", "") if isinstance(info, dict) else str(info)
                    lines.append(f"  - {name}: {desc}")
                has_content = True

            if rels_items:
                lines.append("• Kluczowe relacje i formy zwrotu (T-V / Honoryfikatywność):")
                for rel_k, rel_v in rels_items:
                    lines.append(f"  - {rel_k}: {rel_v}")
                has_content = True

            if decls_items:
                decl_items_out = []
                for c_name, c_decl in decls_items:
                    if c_decl and isinstance(c_decl, dict) and c_decl.get("M") != c_decl.get("D"):
                        decl_items_out.append(f"    * {c_name}: D. {c_decl.get('D')}, C/Ms. {c_decl.get('C')}, B/N. {c_decl.get('B')}/z {c_decl.get('N')}, W. {c_decl.get('W')}!")
                if decl_items_out:
                    lines.append("• Wzorzec odmiany imion (Matryca 7 Przypadków fleksyjnych):")
                    lines.extend(decl_items_out)
                    has_content = True

            if gloss_items:
                lines.append("• Ustalone nazwy i terminologia z poprzednich odcinków (ZACHOWAJ SPÓJNOŚĆ!):")
                for src, trg in gloss_items:
                    lines.append(f"  - '{src}' -> '{trg}'")
                has_content = True

            if canon_items:
                lines.append("• Sprawdzony kanon fansuberski dla tej serii (ZACHOWAJ 100% SPÓJNOŚCI!):")
                for f_term, f_info in canon_items:
                    if isinstance(f_info, dict) and "instruction" in f_info:
                        lines.append(f"  - {f_info['instruction']}")
                    elif isinstance(f_info, dict) and "canonical_pl" in f_info:
                        lines.append(f"  - '{f_term}' -> '{f_info['canonical_pl']}'")
                has_content = True

            if anchors_items:
                lines.append("• Kluczowe rekwizyty i kotwice fabularne (PLOT ANCHORS - ZACHOWAJ CIĄGŁOŚĆ!):")
                for item_key, directive in anchors_items:
                    lines.append(f"  - [{item_key}]: {directive}")
                has_content = True

            lines.append("-------------------------------------------------------\n")

        return "\n".join(lines) if has_content else ""

    def format_scoped_for_batch(
        self,
        batch_text: str = "",
        active_speakers: Optional[Set[str]] = None,
        lookback_text: str = "",
        lookahead_text: str = ""
    ) -> str:
        """
        Formats a strictly scoped Series Bible snippet for a specific batch (Context Minimalism).
        Only includes characters, relationships, declensions, glossary terms, and plot anchors
        that are actually referenced in the current batch or its immediate context.
        Thread-safe under concurrent batch processing.
        """
        corpus = f"{batch_text} {lookback_text} {lookahead_text}".lower()
        active_spk_lower = {s.lower().strip() for s in (active_speakers or set()) if s and s.strip()}

        with self._lock:
            chars_items = list(self.data.get("characters", {}).items())
            rels_items = list(self.data.get("relationships", {}).items())
            decls_items = list(self.data.get("declensions", {}).items())
            gloss_items = list(self.data.get("glossary", {}).items())
            anchors_items = list(self.data.get("plot_anchors", {}).items())
            canon_items = list(self.data.get("fansub_canon", {}).items())

        # 1. Filter characters
        scoped_chars = {}
        for name, info in chars_items:
            name_lower = name.lower()
            # Match if speaker or mentioned in corpus
            if name_lower in active_spk_lower or any(s in name_lower or name_lower in s for s in active_spk_lower if len(s) >= 3):
                scoped_chars[name] = info
            elif re.search(rf"\b{re.escape(name_lower)}\b", corpus):
                scoped_chars[name] = info

        # 2. Filter relationships
        scoped_rels = {}
        for rel_k, rel_v in rels_items:
            rel_k_lower = rel_k.lower()
            if any(name.lower() in rel_k_lower for name in scoped_chars) or any(s in rel_k_lower for s in active_spk_lower if len(s) >= 3):
                scoped_rels[rel_k] = rel_v

        # 3. Filter declensions
        scoped_decls = {}
        for c_name, c_decl in decls_items:
            if c_name in scoped_chars or c_name.lower() in active_spk_lower or re.search(rf"\b{re.escape(c_name.lower())}\b", corpus):
                scoped_decls[c_name] = c_decl

        # 4. Filter glossary
        scoped_gloss = {}
        for src, trg in gloss_items:
            if len(src) >= 3 and re.search(rf"\b{re.escape(src.lower())}\b", corpus):
                scoped_gloss[src] = trg

        # 5. Filter plot anchors
        scoped_anchors = {}
        for item_key, directive in anchors_items:
            if len(item_key) >= 3 and item_key.lower() in corpus:
                scoped_anchors[item_key] = directive

        # 6. Filter fansub canon
        scoped_canon = {}
        for f_term, f_info in canon_items:
            en_words = [f_term]
            if isinstance(f_info, dict) and "en" in f_info:
                en_words.extend(f_info["en"])
            if any(len(w) >= 3 and re.search(rf"\b{re.escape(w.lower())}\b", corpus) for w in en_words):
                scoped_canon[f_term] = f_info
            elif "clevatess" in self.slug:
                scoped_canon[f_term] = f_info

        lines = []
        has_content = False

        if scoped_chars or scoped_gloss or scoped_anchors or scoped_decls or scoped_rels or scoped_canon:
            lines.append("--- BIBLIA SERIALU (KONTEKST BIEŻĄCEJ SCENY) ---")
            if scoped_chars:
                lines.append("• Postacie obecne w scenie:")
                for name, info in scoped_chars.items():
                    desc = info.get("description", "") if isinstance(info, dict) else str(info)
                    lines.append(f"  - {name}: {desc}")
                has_content = True

            if scoped_rels:
                lines.append("• Relacje w scenie (T-V / Honoryfikatywność):")
                for rel_k, rel_v in scoped_rels.items():
                    lines.append(f"  - {rel_k}: {rel_v}")
                has_content = True

            if scoped_decls:
                decl_items = []
                for c_name, c_decl in scoped_decls.items():
                    if c_decl and isinstance(c_decl, dict) and c_decl.get("M") != c_decl.get("D"):
                        decl_items.append(f"    * {c_name}: D. {c_decl.get('D')}, C/Ms. {c_decl.get('C')}, B/N. {c_decl.get('B')}/z {c_decl.get('N')}, W. {c_decl.get('W')}!")
                if decl_items:
                    lines.append("• Wzorzec odmiany imion w scenie (Matryca 7 Przypadków fleksyjnych):")
                    lines.extend(decl_items)
                    has_content = True

            if scoped_canon:
                lines.append("• Sprawdzony kanon fansuberski dla tej serii:")
                for f_term, f_info in scoped_canon.items():
                    if isinstance(f_info, dict) and "instruction" in f_info:
                        lines.append(f"  - {f_info['instruction']}")
                    elif isinstance(f_info, dict) and "canonical_pl" in f_info:
                        lines.append(f"  - '{f_term}' -> '{f_info['canonical_pl']}'")
                has_content = True

            if scoped_gloss:
                lines.append("• Ustalone nazwy i pojęcia obecne w scenie:")
                for src, trg in scoped_gloss.items():
                    lines.append(f"  - '{src}' -> '{trg}'")
                has_content = True

            if scoped_anchors:
                lines.append("• Kluczowe rekwizyty i kotwice fabularne w scenie:")
                for item_key, directive in scoped_anchors.items():
                    lines.append(f"  - [{item_key}]: {directive}")
                has_content = True

            lines.append("--------------------------------------------------\n")
        elif not scoped_chars and not active_spk_lower.intersection({n.lower() for n in self.data.get("characters", {})}):
            # If the series has characters defined but NONE of them are in this scene (e.g. background character, mob, new scene)
            if self.data.get("characters"):
                lines.append("--- KONTEKST SCENY: Postacie epizodyczne / tło ---")
                lines.append("• W tej scenie nie występują główne postacie z bazy serii.")
                lines.append("• Dedukuj płeć, relacje i emocje bezpośrednio z dialogu, intonacji seiyū oraz kontekstu sytuacyjnego.")
                lines.append("--------------------------------------------------\n")
                has_content = True

        return "\n".join(lines) if has_content else ""

    def generate_html_report(self) -> str:
        """Generates a responsive modern dark-mode HTML continuity report of the Series Bible (Thread-Safe)."""
        with self._lock:
            chars_items = list(self.data.get("characters", {}).items())
            gloss_items = list(self.data.get("glossary", {}).items())
            rel_items = list(self.data.get("relationships", {}).items())
            anchor_items = list(self.data.get("plot_anchors", {}).items())
            episodes_list = ", ".join(self.data.get("episodes_translated", [])) or "Brak przetłumaczonych odcinków"

        chars_rows = ""
        for name, info in chars_items:
            desc = info.get("description", "") if isinstance(info, dict) else str(info)
            chars_rows += f"<tr><td><strong>{name}</strong></td><td>{desc}</td></tr>"

        gloss_rows = ""
        for src, trg in gloss_items:
            gloss_rows += f"<tr><td><code>{src}</code></td><td><strong>{trg}</strong></td></tr>"

        rel_rows = ""
        for pair, rel in rel_items:
            rel_rows += f"<tr><td><strong>{pair}</strong></td><td>{rel}</td></tr>"

        anchor_rows = ""
        for p_item, p_dir in anchor_items:
            anchor_rows += f"<tr><td><strong>{p_item}</strong></td><td>{p_dir}</td></tr>"

        html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<title>Biblia Serialu: {self.anime_title}</title>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 30px; }}
  .container {{ max-width: 900px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
  h1 {{ color: #38bdf8; border-bottom: 2px solid #334155; padding-bottom: 12px; }}
  h2 {{ color: #a855f7; margin-top: 30px; }}
  .badge {{ background: #0284c7; color: white; padding: 4px 10px; border-radius: 6px; font-size: 13px; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 10px; background: #0f172a; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #334155; }}
  th {{ background: #1e293b; color: #94a3b8; text-transform: uppercase; font-size: 12px; }}
  tr:hover {{ background: #1e293b; }}
  code {{ background: #334155; padding: 2px 6px; border-radius: 4px; color: #f472b6; }}
  .meta {{ color: #94a3b8; font-size: 14px; margin-bottom: 20px; }}
</style>
</head>
<body>
<div class="container">
  <h1>📖 Biblia Serialu: {self.anime_title}</h1>
  <div class="meta">
    <p>📺 <strong>Przetłumaczone odcinki:</strong> {episodes_list}</p>
    <p>🛡️ <strong>Liczba wpisów w pamięci ciągłości:</strong> {len(self.data.get('characters', {}))} postaci | {len(self.data.get('glossary', {}))} terminów | {len(self.data.get('plot_anchors', {}))} kotwic fabularnych</p>
  </div>

  <h2>👥 Rejestr Postaci i Idiolekty</h2>
  <table>
    <thead><tr><th>Postać</th><th>Opis / Idiolekt / Forma zwracania się</th></tr></thead>
    <tbody>{chars_rows or '<tr><td colspan="2">Brak zarejestrowanych postaci</td></tr>'}</tbody>
  </table>

  <h2>🤝 Matryca Relacji i Honoryfikatorów</h2>
  <table>
    <thead><tr><th>Relacja</th><th>Zasada zwracania się</th></tr></thead>
    <tbody>{rel_rows or '<tr><td colspan="2">Brak zarejestrowanych relacji</td></tr>'}</tbody>
  </table>

  <h2>📚 Słownik Nazw Własnych i Pojęć</h2>
  <table>
    <thead><tr><th>Termin Źródłowy</th><th>Ustalony Przekład Polski</th></tr></thead>
    <tbody>{gloss_rows or '<tr><td colspan="2">Brak ustalonych terminów</td></tr>'}</tbody>
  </table>

  <h2>⚓ Rekwizyty i Kotwice Fabularne (Plot Anchors)</h2>
  <table>
    <thead><tr><th>Rekwizyt / Zdarzenie</th><th>Wymóg Ciągłości i Kontekst</th></tr></thead>
    <tbody>{anchor_rows or '<tr><td colspan="2">Brak zarejestrowanych kotwic fabularnych</td></tr>'}</tbody>
  </table>
</div>
</body>
</html>"""
        return html


def sanitize_all_series_bibles(storage_dir: Optional[Path] = None) -> int:
    """
    Scans and sanitizes all Series Bible JSON files in storage_dir (default: series_memory/),
    applying self-healing integrity audits across all series systemically.
    Returns the count of sanitized bibles.
    """
    target_dir = storage_dir or SERIES_MEMORY_DIR
    if not target_dir.exists():
        return 0
    count = 0
    for p in target_dir.glob("*_bible.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            title = d.get("anime_title") or p.stem.replace("_bible", "").replace("_", " ")
            bible = SeriesBible(title, storage_dir=target_dir)
            bible.save()
            count += 1
        except Exception:
            pass
    return count
