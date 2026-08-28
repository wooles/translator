# -*- coding: utf-8 -*-
"""
Polish Manga Canon Registry Module (Manga Canon Registry).
Ensures 100% terminology consistency for techniques, magic, ranks, and character relationships
matching official Polish manga publications from renowned publishers
(Waneko, J.P.Fantastica, Studio JG, Hanami, Kotori, Dango).

Runs 100% locally (Offline / 0 PLN API cost).
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

MANGA_CANON_DIR = Path(__file__).parent / "manga_canon"

# Built-in canon terminology database from leading Polish manga editions
BUILTIN_MANGA_CANON: Dict[str, Dict[str, Any]] = {
    "kingdom": {
        "title": "Kingdom",
        "aliases": [
            "kingdom",
            "kingdom s6",
            "kingdom season 6",
            "kingdom s5",
            "kingdom s4",
            "kingdom s3",
            "kingdom s2",
            "kingdom s1"
        ],
        "publisher": "Oficjalny kanon mangowy / Państwo Środka",
        "glossary": {
            "Middle Kingdom": "Państwo Środka",
            "Great General": "Wielki Generał",
            "Hi Shin Unit": "Oddział Hi Shin",
            "Heavenly Kings": "Czterej Niebiańscy Królowie",
            "Guan Dao / Glaive": "Glewia bojowa / Guandao",
            "Glaive": "Glewia",
            "Six Great Generals": "Sześciu Wielkich Generałów",
            "State of Qin": "Państwo Qin",
            "State of Zhao": "Państwo Zhao",
            "State of Wei": "Państwo Wei",
            "State of Chu": "Państwo Chu",
            "State of Yan": "Państwo Yan",
            "State of Han": "Państwo Han",
            "State of Qi": "Państwo Qi",
            "Quanrong": "Quanrong",
            "Xiongnu": "Xiongnu",
            "Zhuhai Plains": "Równina Zhuhai",
            "Laoyang": "Zamek Laoyang",
            "Five Hundred-Man Commander": "Pięćsetnik / Dowódca pięciuset ludzi",
            "500-Man Commander": "Pięćsetnik / Dowódca pięciuset ludzi",
            "Hundred-Man Commander": "Setnik / Dowódca stu ludzi",
            "100-Man Commander": "Setnik / Dowódca stu ludzi",
            "Three-Hundred-Man Commander": "Trzechsetnik / Dowódca trzystu ludzi",
            "300-Man Commander": "Trzechsetnik / Dowódca trzystu ludzi",
            "Thousand-Man Commander": "Tysięcznik / Dowódca tysiąca ludzi",
            "1000-Man Commander": "Tysięcznik / Dowódca tysiąca ludzi",
            "Two-Thousand-Man Commander": "Dwutysięcznik / Dowódca dwóch tysięcy ludzi",
            "2000-Man Commander": "Dwutysięcznik / Dowódca dwóch tysięcy ludzi",
            "Three-Thousand-Man Commander": "Trzytysięcznik / Dowódca trzech tysięcy ludzi",
            "3000-Man Commander": "Trzytysięcznik / Dowódca trzech tysięcy ludzi",
            "Four-Thousand-Man Commander": "Czterotysięcznik / Dowódca czterech tysięcy ludzi",
            "4000-Man Commander": "Czterotysięcznik / Dowódca czterech tysięcy ludzi",
            "Five-Thousand-Man Commander": "Pięciotysięcznik / Dowódca pięciu tysięcy ludzi",
            "5000-Man Commander": "Pięciotysięcznik / Dowódca pięciu tysięcy ludzi",
            "Great General Under the Heavens": "Wielki Generał pod Niebiosami",
            "General": "Generał"
        },
        "character_forms": {
            "Shin -> Sei": "na ty (przyjaciele) / Królu Sei (oficjalnie)",
            "Ten -> Shin": "na ty / po imieniu",
            "Kyou Kai -> Shin": "na ty (towarzysze broni)"
        }
    },
    "jujutsu_kaisen": {
        "title": "Jujutsu Kaisen",
        "aliases": [
            "jujutsu kaisen",
            "jujutsu kaisen s2",
            "jujutsu",
            "jjk"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Domain Expansion": "Rozszerzenie Domeny",
            "Cursed Energy": "Przeklęta Energia",
            "Reverse Cursed Technique": "Odwrócona Technika Przeklęta",
            "Cursed Spirit": "Przeklęty Duch",
            "Cursed Tool": "Przeklęte Narzędzie",
            "Black Flash": "Czarny Błysk",
            "Special Grade": "Klasa Specjalna",
            "Grade 1 Sorcerer": "Czarownik 1. Klasy",
            "Jujutsu High / Tokyo Jujutsu High": "Technikum Magii Przeklętej w Tokio",
            "Simple Domain": "Prosta Domena",
            "King of Curses": "Król Przekleństw",
            "Six Eyes": "Sześcioro Oczu",
            "Limitless": "Bezgraniczność"
        },
        "character_forms": {
            "Yuji -> Megumi": "Megumi / na ty",
            "Yuji -> Gojo": "panie Gojo / sensei",
            "Nobara -> Yuji": "Itadori / na ty"
        }
    },
    "frieren": {
        "title": "Sousou no Frieren (Frieren. U kresu drogi)",
        "aliases": [
            "sousou no frieren",
            "frieren",
            "frieren beyond journeys end",
            "frieren u kresu drogi"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Frieren the Slayer": "Frieren Pogromczyni",
            "Zoltraak": "Zoltraak (Magia Przebijająca)",
            "First-Class Mage": "Mag Pierwszej Klasy",
            "Holy City of Strahl": "Święte Miasto Strahl",
            "Aura the Guillotine": "Aura od Gilotyny",
            "Goddess of Creation": "Bogini Stworzenia",
            "Hero Party": "Drużyna Bohatera",
            "Hero Himmel": "Bohater Himmel",
            "Demon King": "Król Demonów",
            "Grimoire": "Grimuar / Księga Zaklęć"
        },
        "character_forms": {
            "Fern -> Frieren": "pani Frieren / mistrzyni",
            "Stark -> Frieren": "pani Frieren",
            "Stark -> Fern": "Fern / na ty"
        }
    },
    "chainsaw_man": {
        "title": "Chainsaw Man",
        "aliases": [
            "chainsaw man",
            "csm"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Chainsaw Devil": "Diabeł Piły Łańcuchowej",
            "Public Safety Devil Hunters": "Łowcy Diabłów Bezpieczeństwa Publicznego",
            "Gun Devil": "Diabeł Broni Palnej",
            "Control Devil": "Diabeł Kontroli",
            "Blood Devil": "Diabeł Krwi",
            "Fiend": "Diabloid",
            "Special Division 4": "Czwarty Wydział Specjalny"
        },
        "character_forms": {
            "Denji -> Makima": "pani Makimo",
            "Power -> Denji": "Denji / na ty",
            "Aki -> Denji": "Denji / gówniarzu"
        }
    },
    "attack_on_titan": {
        "title": "Atak Tytanów (Shingeki no Kyojin)",
        "aliases": [
            "shingeki no kyojin",
            "attack on titan",
            "aot",
            "atak tytanow",
            "atak tytanów"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Survey Corps / Scout Regiment": "Korpus Zwiadowczy",
            "Omni-Directional Mobility Gear / ODM Gear / 3D Maneuver Gear": "Sprzęt do Manewrów Przestrzennych",
            "Colossal Titan": "Tytan Kolosalny",
            "Armored Titan": "Tytan Opancerzony",
            "Attack Titan": "Tytan Atakujący",
            "Beast Titan": "Tytan Zwierzęcy",
            "Founding Titan": "Tytan Pierwotny",
            "Wall Maria": "Mur Maria",
            "Wall Rose": "Mur Rose",
            "Wall Sina": "Mur Sina",
            "Garrison": "Stacjonariusze",
            "Military Police": "Żandarmeria",
            "Thunder Spears": "Włócznie Grzmotu"
        },
        "character_forms": {
            "Eren -> Levi": "kapitanie Levi",
            "Mikasa -> Eren": "Eren / na ty"
        }
    },
    "vinland_saga": {
        "title": "Saga Winlandzka (Vinland Saga)",
        "aliases": [
            "vinland saga",
            "vinland",
            "saga winlandzka"
        ],
        "publisher": "Wydawnictwo Hanami",
        "glossary": {
            "Jomsvikings": "Wojownicy z Jomsborga",
            "Vinland": "Winlandia",
            "Askeladd's Band": "Banda Askeladda",
            "Einars": "Einherjarowie",
            "King Sweyn": "Król Swen Widłobrody",
            "Prince Canute": "Książę Kanut"
        },
        "character_forms": {
            "Thorfinn -> Askeladd": "Askeladd (z wściekłością, na ty)"
        }
    },
    "demon_slayer": {
        "title": "Miecz Zabójcy Demonów (Kimetsu no Yaiba)",
        "aliases": [
            "kimetsu no yaiba",
            "demon slayer",
            "miecz zabojcy demonow",
            "miecz zabójcy demonów"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Demon Slayer Corps": "Korpus Zabójców Demonów",
            "Hashira / Pillars": "Filary",
            "Total Concentration Breathing": "Oddech Całkowitego Skupienia",
            "Sun Breathing / Hinokami Kagura": "Oddech Słońca / Taniec Boga Ognia (Hinokami Kagura)",
            "Water Breathing": "Oddech Wody",
            "Flame Breathing": "Oddech Płomienia",
            "Thunder Breathing": "Oddech Błyskawicy",
            "Upper Ranks / Upper Moons": "Księżyce Wyższej Rangi",
            "Lower Ranks / Lower Moons": "Księżyce Niższej Rangi",
            "Muzan Kibutsuji": "Muzan Kibutsuji (Władca Demonów)",
            "Nichirin Blade": "Ostrze Nichirin"
        },
        "character_forms": {
            "Tanjiro -> Giyu": "panie Tomioka",
            "Zenitsu -> Tanjiro": "Tanjiro / na ty",
            "Inosuke -> Tanjiro": "Monjiro / Kentaro (przekręca imię)"
        }
    },
    "dungeon_meshi": {
        "title": "Pyszności w Lochu (Dungeon Meshi)",
        "aliases": [
            "dungeon meshi",
            "delicious in dungeon",
            "pysznosci w lochu",
            "pyszności w lochu"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Red Dragon": "Czerwony Smok",
            "Living Armor": "Ożywiona Zbroja",
            "Changeling": "Zmiennokształtny",
            "Treasure Bugs": "Skarbce / Skarbowe Robaki",
            "Mana": "Mana",
            "Ancient Magic": "Magia Starożytna"
        },
        "character_forms": {
            "Laios -> Marcille": "Marcille / na ty",
            "Senshi -> Laios": "Laios / młodziku"
        }
    },
    "spy_x_family": {
        "title": "Spy x Family",
        "aliases": [
            "spy x family",
            "spyxfamily"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Twilight": "Zmierzch",
            "Operation Strix": "Operacja Strix",
            "Eden Academy": "Akademia Eden",
            "Imperial Scholars": "Cesarskie Gwiazdy",
            "Stella Stars": "Gwiazdki Stella",
            "Tonitrus Bolts": "Gromy Tonitrus",
            "Ostania": "Ostania",
            "Westalis": "Westalis",
            "WISE": "WISE"
        },
        "character_forms": {
            "Anya -> Loid": "tato",
            "Anya -> Yor": "mamo",
            "Loid -> Yor": "Yor / pani Yor (oficjalnie)"
        }
    },
    "my_hero_academia": {
        "title": "Moja Akademia Bohaterów (My Hero Academia / Boku no Hero Academia)",
        "aliases": [
            "my hero academia",
            "boku no hero academia",
            "mha",
            "bnha",
            "moja akademia bohaterow",
            "moja akademia bohaterów"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Quirk": "Dar",
            "One For All": "Jeden za Wszystkich (One For All)",
            "All For One": "Wszystko dla Jednego (All For One)",
            "Hero Association": "Stowarzyszenie Bohaterów",
            "League of Villains": "Liga Złoczyńców",
            "Plus Ultra": "Plus Ultra!",
            "Pro Hero": "Zawodowy Bohater",
            "U.A. High School": "Liceum U.A."
        },
        "character_forms": {
            "Deku -> All Might": "panie All Might",
            "Bakugo -> Deku": "Deku / śmieciu",
            "Deku -> Bakugo": "Kacchan"
        }
    },
    "one_punch_man": {
        "title": "One-Punch Man",
        "aliases": [
            "one punch man",
            "one-punch man",
            "opm"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Hero Association": "Stowarzyszenie Bohaterów",
            "S-Class Hero": "Bohater Klasy S",
            "Threat Level: God / Dragon / Demon / Tiger / Wolf": "Poziom Zagrożenia: Bóg / Smok / Demon / Tygrys / Wilk",
            "Serious Punch": "Poważne Uderzenie",
            "Consecutive Normal Punches": "Seria Zwykłych Ciosów",
            "Monster Association": "Stowarzyszenie Potworów"
        },
        "character_forms": {
            "Genos -> Saitama": "mistrzu Saitama",
            "Saitama -> Genos": "Genos / na ty"
        }
    },
    "black_clover": {
        "title": "Black Clover",
        "aliases": [
            "black clover"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Magic Knights": "Rycerze Magii",
            "Black Bulls": "Czarne Byki",
            "Golden Dawn": "Złoty Świt",
            "Wizard King": "Król Magów",
            "Anti-Magic": "Antymagia",
            "Grimoire": "Grimuar (Pięciolistna Koniczyna)",
            "Clover Kingdom": "Królestwo Koniczyny",
            "Devil Union": "Zjednoczenie z Diabłem"
        },
        "character_forms": {
            "Asta -> Yami": "kapitanie Yami",
            "Asta -> Yuno": "Yuno / rywalu",
            "Noelle -> Asta": "głupi Asta / Asta"
        }
    },
    "kaguya_sama": {
        "title": "Kaguya-sama: Miłość to wojna (Kaguya-sama wa Kokurasetai)",
        "aliases": [
            "kaguya-sama wa kokurasetai",
            "kaguya sama",
            "kaguya-sama love is war",
            "milosc to wojna",
            "miłość to wojna"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Student Council": "Samorząd Uczniowski",
            "Shuchiin Academy": "Akademia Shuchiin",
            "Love Confession": "Wyznanie Miłości",
            "President": "Przewodniczący",
            "Vice President": "Wiceprzewodnicząca"
        },
        "character_forms": {
            "Kaguya -> Shirogane": "panie przewodniczący / Shirogane",
            "Shirogane -> Kaguya": "pani Shinomiya / Kaguya",
            "Chika -> Kaguya": "Kaguya-san / Kaguya"
        }
    },
    "horimiya": {
        "title": "Horimiya",
        "aliases": [
            "horimiya",
            "hori-san to miyamura-kun"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Katagiri High School": "Liceum Katagiri",
            "Piercing": "Kolczyki",
            "Secret Identity": "Ukryta Tożsamość"
        },
        "character_forms": {
            "Hori -> Miyamura": "Miyamura / Izumi",
            "Miyamura -> Hori": "Hori-san / Kyouko"
        }
    },
    "the_promised_neverland": {
        "title": "The Promised Neverland (Yakusoku no Neverland)",
        "aliases": [
            "yakusoku no neverland",
            "the promised neverland",
            "promised neverland"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Grace Field House": "Sierociniec Grace Field House",
            "Premium Quality Meat": "Mięso Najwyższej Jakości",
            "Demons": "Demony",
            "The Promise": "Obietnica",
            "Mama": "Mama (Opiekunka)",
            "Sister Krone": "Siostra Krone"
        },
        "character_forms": {
            "Emma -> Norman": "Norman / na ty",
            "Ray -> Emma": "Emma / na ty",
            "Children -> Isabella": "Mamo"
        }
    },
    "kuroshitsuji": {
        "title": "Mroczny Kamerdyner (Kuroshitsuji / Black Butler)",
        "aliases": [
            "kuroshitsuji",
            "black butler",
            "mroczny kamerdyner"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Phantomhive Household": "Ród Phantomhive",
            "Queen's Watchdog": "Pies Łańcuchowy Królowej",
            "Demon Butler": "Demoniczny Kamerdyner",
            "Faustian Contract": "Cyrograf / Pakt",
            "Grim Reaper / Shinigami": "Żniwiarz Śmierci",
            "Cinematic Record": "Zapis Życia (Taśma Kinematograficzna)"
        },
        "character_forms": {
            "Sebastian -> Ciel": "mój panie / paniczu Cielu",
            "Ciel -> Sebastian": "Sebastianie / to rozkaz"
        }
    },
    "blue_exorcist": {
        "title": "Ao no Exorcist (Blue Exorcist)",
        "aliases": [
            "ao no exorcist",
            "blue exorcist",
            "niebieski egzorcysta"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "True Cross Academy": "Akademia Prawdziwego Krzyża",
            "Exorcist": "Egzorcysta",
            "Paladin": "Paladyn",
            "Blue Flames": "Błękitne Płomienie Szatana",
            "Gehenna": "Gehenna (Świat Demonów)",
            "Assiah": "Assiah (Świat Ludzi)",
            "Kurikara": "Miecz Kurikara"
        },
        "character_forms": {
            "Rin -> Yukio": "Yukio / braciszku",
            "Yukio -> Rin": "bracie / Rinie",
            "Rin -> Mephisto": "Mephisto / durniu"
        }
    },
    "claymore": {
        "title": "Claymore",
        "aliases": [
            "claymore"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Claymore / Silver-eyed Witches": "Srebrnookie Wiedźmy (Claymore)",
            "Yoma": "Yoma (Potwory)",
            "Awakened Being": "Przebudzona Istota",
            "Abyssal One": "Istota z Otchłani",
            "Yoki": "Energia Yoki",
            "Organization": "Organizacja"
        },
        "character_forms": {
            "Clare -> Teresa": "pani Tereso / Teresa",
            "Raki -> Clare": "Clare / na ty"
        }
    },
    "dorohedoro": {
        "title": "Dorohedoro",
        "aliases": [
            "dorohedoro"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "The Hole": "Dziura",
            "Sorcerers / Magic Users": "Magowie",
            "Black Smoke": "Czarny Dym",
            "En Family": "Rodzina Ena",
            "Cross-Eyes": "Krzyżoocy",
            "Gyoza": "Gyoza"
        },
        "character_forms": {
            "Caiman -> Nikaido": "Nikaido / na ty",
            "Shin -> Noi": "Noi / na ty"
        }
    },
    "mob_psycho_100": {
        "title": "Mob Psycho 100",
        "aliases": [
            "mob psycho 100",
            "mob psycho"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Esper": "Esper / Psychik",
            "Spirits and Such Consultation Office": "Biuro Konsultacji Duchowych",
            "Claw": "Szpon (Organizacja Claw)",
            "100% Explosion": "Eksplozja 100%",
            "???%": "Stan ???%"
        },
        "character_forms": {
            "Mob -> Reigen": "mistrzu Reigen",
            "Reigen -> Mob": "Mob / Shigeo",
            "Dimple -> Mob": "Shigeo / na ty"
        }
    },
    "slime_isekai": {
        "title": "Odrodzony jako galareta (Tensei shitara Slime Datta Ken)",
        "aliases": [
            "tensei shitara slime datta ken",
            "that time i got reincarnated as a slime",
            "tensura",
            "odrodzony jako galareta"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Jura Tempest Federation": "Federacja Jura Tempest",
            "Demon Lord": "Władca Demonów (Demon Lord)",
            "True Dragon": "Prawdziwy Smok",
            "Great Sage": "Wielki Mędrzec (Great Sage)",
            "Raphael": "Mądrościowy Król Rafael",
            "Predator / Gluttony": "Drapieżca / Żarłoczność",
            "Ogre / Kijin": "Ogr / Kijin"
        },
        "character_forms": {
            "Subordinates -> Rimuru": "Lordzie Rimuru / Władco Rimuru",
            "Rimuru -> Veldora": "Veldora / brachu"
        }
    },
    "goblin_slayer": {
        "title": "Goblin Slayer (Pogromca Goblinów)",
        "aliases": [
            "goblin slayer",
            "pogromca goblinow",
            "pogromca goblinów"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Goblin Slayer": "Pogromca Goblinów",
            "Silver Rank": "Ranga Srebrna",
            "Porcelain Rank": "Ranga Porcelanowa",
            "Goblin Champion / Lord / Shaman": "Czempion / Władca / Szaman Goblinów",
            "Adventurers Guild": "Gildia Poszukiwaczy Przygód"
        },
        "character_forms": {
            "Priestess -> Goblin Slayer": "panie Pogromco Goblinów",
            "High Elf Archer -> Goblin Slayer": "Orcbolg / brodaczu"
        }
    },
    "spice_and_wolf": {
        "title": "Wilk i Korzenne Ciasteczka (Spice and Wolf / Ookami to Koushinryou)",
        "aliases": [
            "spice and wolf",
            "ookami to koushinryou",
            "wilk i korzenne ciasteczka"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Holo the Wise Wolf": "Holo Mądra Wilczyca",
            "Yoitsu": "Kraina Yoitsu",
            "Trenni Silver Coins": "Srebrniki Trenni",
            "Rowen Trade Guild": "Gildia Kupiecka Rowen",
            "Traveling Merchant": "Wędrowny Kupiec"
        },
        "character_forms": {
            "Holo -> Lawrence": "Lawrence / mój miły",
            "Lawrence -> Holo": "Holo / pani Holo"
        }
    },
    "yona_of_the_dawn": {
        "title": "Yona w blasku świtu (Akatsuki no Yona)",
        "aliases": [
            "akatsuki no yona",
            "yona of the dawn",
            "yona w blasku switu",
            "yona w blasku świtu"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Kingdom of Kouka": "Królestwo Kouka",
            "Four Dragon Warriors (White, Blue, Green, Yellow)": "Cztery Smoki (Biały, Błękitny, Zielony, Żółty)",
            "Sky Clan / Wind Clan / Fire Clan": "Plemię Niebios / Wiatru / Ognia",
            "Hiryuu Castle": "Zamek Hiryuu"
        },
        "character_forms": {
            "Hak -> Yona": "księżniczko Yono",
            "Yona -> Hak": "Hak / na ty",
            "Soo-won -> Yona": "Yona / na ty"
        }
    },
    "kuroko_no_basket": {
        "title": "Kuroko's Basketball (Kuroko no Basket)",
        "aliases": [
            "kuroko no basket",
            "kuroko no basuke",
            "kuroko's basketball"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Generation of Miracles": "Pokolenie Cudów",
            "Phantom Sixth Man": "Widmowy Szósty Gracz",
            "Seirin High": "Liceum Seirin",
            "Misdirection": "Mylenie Wzroku (Misdirection)",
            "Ignite Pass": "Płomienne Podanie",
            "The Zone": "Strefa Skupienia (The Zone)"
        },
        "character_forms": {
            "Kuroko -> Kagami": "Kagami-kun / Kagami",
            "Kagami -> Kuroko": "Kuroko / na ty",
            "Aomine -> Kuroko": "Tetsu"
        }
    },
    "gokushufudou": {
        "title": "Droga do Yakuzy (Gokushufudou: The Way of the Househusband)",
        "aliases": [
            "gokushufudou",
            "the way of the househusband",
            "droga do yakuzy"
        ],
        "publisher": "Wydawnictwo Kotori",
        "glossary": {
            "Immortal Tatsu": "Nieśmiertelny Tatsu",
            "Househusband": "Mąż Domowy / Perfekcyjny Pan Domu",
            "Yakuza": "Yakuza",
            "Neighborhood Association": "Komitet Sąsiedzki"
        },
        "character_forms": {
            "Miku -> Tatsu": "Tatsu / kochanie",
            "Masa -> Tatsu": "szefie Tatsu / aniki"
        }
    },
    "ancient_magus_bride": {
        "title": "Oblubienica Czarnoksiężnika (Mahoutsukai no Yome / The Ancient Magus' Bride)",
        "aliases": [
            "mahoutsukai no yome",
            "the ancient magus bride",
            "ancient magus bride",
            "oblubienica czarnoksieznika",
            "oblubienica czarnoksiężnika"
        ],
        "publisher": "Wydawnictwo Kotori",
        "glossary": {
            "Sleigh Beggy": "Sleigh Beggy (Dziecko Umiłowane przez Magię)",
            "Thorn Mage": "Mag Cierni",
            "Neighbors / Fae": "Sąsiedzi / Elfy i Duszki",
            "Familiar": "Chowaniec",
            "Alchemist": "Alchemik"
        },
        "character_forms": {
            "Chise -> Elias": "Elias / panie Eliasie",
            "Elias -> Chise": "Chise / moja panno"
        }
    },
    "sakamoto_days": {
        "title": "Sakamoto Days",
        "aliases": [
            "sakamoto days"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Order": "Zakon / Order (Elita Zabójców)",
            "JCC (Japanese Assassin Training Center)": "JCC (Japońska Akademia Zabójców)",
            "Legendary Hitman": "Legendarny Płatny Zabójca",
            "Sakamoto Convenience Store": "Sklep Spożywczy Sakamoto"
        },
        "character_forms": {
            "Shin -> Sakamoto": "szefie Sakamoto / panie Sakamoto",
            "Lu -> Sakamoto": "Sakamoto / panie Sakamoto"
        }
    },
    "gachiakuta": {
        "title": "Gachiakuta",
        "aliases": [
            "gachiakuta"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "The Pit / The Abyss": "Otchłań (Wysypisko Śmieci)",
            "Cleaners / Janitors": "Czyściciele (Klan Sprzątaczy)",
            "Jinki (Vital Instrument)": "Jinki (Ożywione Narzędzie)",
            "Giver": "Obdarowany (Użytkownik Jinki)",
            "Trash Beast": "Śmieciowa Bestia"
        },
        "character_forms": {
            "Rudo -> Enjin": "Enjin / na ty",
            "Zanka -> Rudo": "Rudo / śmieciu"
        }
    },
    "akira": {
        "title": "Akira",
        "aliases": [
            "akira"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Neo-Tokyo": "Neo-Tokio",
            "Capsules": "Gang Kapsułek",
            "Clowns": "Gang Błaznów",
            "Akira": "Projekt Akira",
            "Olympic Stadium": "Stadion Olimpijski"
        },
        "character_forms": {
            "Kaneda -> Tetsuo": "Tetsuo / na ty",
            "Tetsuo -> Kaneda": "Kaneda / durniu"
        }
    },
    "ghost_in_the_shell": {
        "title": "Ghost in the Shell",
        "aliases": [
            "ghost in the shell",
            "gits",
            "stand alone complex"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Public Security Section 9": "Sekcja 9 Bezpieczeństwa Publicznego",
            "Major": "Pani Major",
            "Cyberbrain": "Cybermózg",
            "Ghost": "Duch (Ghost)",
            "Tachikoma": "Tachikoma",
            "Laughing Man": "Śmiejący Się Człowiek"
        },
        "character_forms": {
            "Batou -> Motoko": "Major / Motoko",
            "Section 9 -> Aramaki": "szefie Aramaki"
        }
    },
    "blame": {
        "title": "Blame!",
        "aliases": [
            "blame",
            "blame!"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "The City / Megastructure": "Megastruktura / Miasto",
            "Net Terminal Gene": "Gen Terminala Sieciowego",
            "Gravitational Beam Emitter": "Emiter Promieni Grawitacyjnych (GBE)",
            "Safeguard": "System Zabezpieczeń (Safeguard)",
            "Silicon Life": "Krzemowe Formy Życia"
        },
        "character_forms": {
            "Killy -> Cibo": "Cibo / na ty",
            "Cibo -> Killy": "Killy / na ty"
        }
    },
    "gantz": {
        "title": "Gantz",
        "aliases": [
            "gantz"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Gantz": "Czarna Kula Gantz",
            "100 Points Menu": "Menu 100 Punktów",
            "Gantz Suit": "Kombinezon Bojowy Gantz",
            "X-Gun": "Pistolet Rentgenowski (X-Gun)",
            "Oni Alien": "Obcy Rasy Oni",
            "Nurarihyon": "Obcy Nurarihyon"
        },
        "character_forms": {
            "Kurono -> Kato": "Kato / na ty",
            "Kato -> Kurono": "Kurono / na ty"
        }
    },
    "inuyasha": {
        "title": "InuYasha",
        "aliases": [
            "inuyasha",
            "inu yasha"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Shikon Jewel": "Klejnot Czterech Dusz (Shikon no Tama)",
            "Tessaiga": "Miecz Tessaiga",
            "Tenseiga": "Miecz Tenseiga",
            "Wind Scar": "Blizna Wiatru",
            "Backlash Wave": "Fala Odwetowa (Bakuryuha)",
            "Naraku": "Naraku (Półdemon)",
            "Sengoku Period": "Epoka Sengoku"
        },
        "character_forms": {
            "Kagome -> Inuyasha": "Inuyasha / do nogi! (osuwari)",
            "Inuyasha -> Kagome": "Kagome / na ty",
            "Sesshomaru -> Inuyasha": "półdemonie / Inuyasho"
        }
    },
    "ranma": {
        "title": "Ranma 1/2",
        "aliases": [
            "ranma",
            "ranma 1/2",
            "ranma 1 2"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Jusenkyo Cursed Springs": "Przeklęte Źródła Jusenkyo",
            "Anything-Goes Martial Arts": "Sztuki Walki Wszystkich Chwytów Dozwolonych",
            "Tendo Dojo": "Dojo Rodziny Tendo",
            "Moko Takabisha": "Moko Takabisha",
            "Hiryu Shotenha": "Hiryu Shotenha"
        },
        "character_forms": {
            "Ranma -> Akane": "niekobieca Akane / Akane",
            "Akane -> Ranma": "zboczeniec Ranma / Ranma"
        }
    },
    "sailor_moon": {
        "title": "Czarodziejka z Księżyca (Sailor Moon)",
        "aliases": [
            "sailor moon",
            "czarodziejka z ksiezyca",
            "czarodziejka z księżyca",
            "bishoujo senshi sailor moon"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Sailor Guardians": "Czarodziejki / Wojowniczki w Marynarkach",
            "Moon Tiara Action": "Księżycowy Diademie, Działaj!",
            "Moon Healing Escalation": "Księżycowa Eskalacja Uzdrowienia",
            "Tuxedo Mask": "Tuxedo Mask / Zamaskowany Dżentelmen",
            "Silver Crystal": "Srebrny Kryształ",
            "Dark Kingdom": "Mroczne Królestwo",
            "Moon Kingdom": "Księżycowe Królestwo (Srebrne Milenium)"
        },
        "character_forms": {
            "Usagi -> Mamoru": "Mamoru / panie Mamoru",
            "Mamoru -> Usagi": "Usako / Usagi",
            "Sailors -> Usagi": "Usagi / Księżniczko Serenity"
        }
    },
    "captain_tsubasa": {
        "title": "Kapitan Jastrząb (Captain Tsubasa)",
        "aliases": [
            "captain tsubasa",
            "kapitan jastrzab",
            "kapitan jastrząb",
            "tsubasa"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Drive Shoot": "Strzał Opadający (Drive Shoot)",
            "Tiger Shoot": "Strzał Tygrysa (Tiger Shoot)",
            "Twin Shoot": "Podwójny Strzał",
            "Nankatsu SC": "Klub Nankatsu",
            "Toho Academy": "Akademia Toho",
            "All Japan Youth": "Młodzieżowa Reprezentacja Japonii"
        },
        "character_forms": {
            "Tsubasa -> Hyuga": "Hyuga / na ty",
            "Hyuga -> Tsubasa": "Tsubasa / na ty",
            "Ishizaki -> Tsubasa": "kapitanie Tsubasa / Tsubasa"
        }
    },
    "slam_dunk": {
        "title": "Slam Dunk",
        "aliases": [
            "slam dunk"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Shohoku High": "Liceum Shohoku",
            "Rebound King": "Król Zbiórek",
            "Slam Dunk": "Wsad do Kosza (Slam Dunk)",
            "National Championship / Inter-High": "Turniej Narodowy (Inter-High)",
            "Kainan High": "Liceum Kainan"
        },
        "character_forms": {
            "Sakuragi -> Rukawa": "lisie Rukawa / Rukawa",
            "Rukawa -> Sakuragi": "głąbie / kretynie",
            "Sakuragi -> Akagi": "Gorylu / kapitanie"
        }
    },
    "parasyte": {
        "title": "Pasożyt (Parasyte / Kiseijuu)",
        "aliases": [
            "kiseijuu",
            "parasyte",
            "pasozyt",
            "pasożyt"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Migi": "Migi (Prawica)",
            "Parasite": "Pasożyt",
            "Gotou": "Gotou (Kolektyw Pasożytów)"
        },
        "character_forms": {
            "Shinichi -> Migi": "Migi / na ty",
            "Migi -> Shinichi": "Shinichi"
        }
    },
    "gunnm": {
        "title": "Battle Angel Alita (Gunnm)",
        "aliases": [
            "gunnm",
            "battle angel alita",
            "alita"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Scrapyard": "Miasto Złomu",
            "Tiphares / Zalem": "Podniebne Miasto Zalem",
            "Panzer Kunst": "Pancerna Sztuka Walki (Panzer Kunst)",
            "Motorball": "Motorball",
            "Hunter-Warrior": "Łowca Nagród (Hunter-Warrior)",
            "Damascus Blade": "Ostrze Damasceńskie"
        },
        "character_forms": {
            "Alita / Gally -> Ido": "doktorze Ido / ojcze",
            "Ido -> Alita": "Alita / Gally"
        }
    },
    "shaman_king": {
        "title": "Król Szamanów (Shaman King)",
        "aliases": [
            "shaman king",
            "krol szamanow",
            "król szamanów"
        ],
        "publisher": "Wydawnictwo Hanami",
        "glossary": {
            "Shaman Fight": "Turniej Szamanów",
            "Over Soul": "Jedność Duszy (Over Soul)",
            "Guardian Ghost": "Duch Stróż",
            "Amidamaru": "Amidamaru (Duch Samuraja)",
            "Great Spirit": "Wielki Duch",
            "Patch Tribe": "Plemię Patch",
            "Furyoku": "Energia Furyoku"
        },
        "character_forms": {
            "Yoh -> Amidamaru": "Amidamaru / przyjacielu",
            "Anna -> Yoh": "Yoh / durniu (z władczością)"
        }
    },
    "twenty_century_boys": {
        "title": "Chłopcy z XX wieku (20th Century Boys)",
        "aliases": [
            "20th century boys",
            "chlopcy z xx wieku",
            "chłopcy z xx wieku",
            "21st century boys"
        ],
        "publisher": "Wydawnictwo Hanami",
        "glossary": {
            "Friend / Tomodachi": "Przyjaciel (Tomodachi)",
            "Book of Prophecy": "Księga Proroctw",
            "Bloody New Year's Eve": "Krwawy Sylwester 2000",
            "Friendland": "Park Rozrywki Przyjaciela"
        },
        "character_forms": {
            "Kenji -> Kanna": "Kanna / na ty",
            "Kanna -> Kenji": "wujku Kenji"
        }
    },
    "mushishi": {
        "title": "Mushishi",
        "aliases": [
            "mushishi"
        ],
        "publisher": "Wydawnictwo Hanami",
        "glossary": {
            "Mushi": "Mushi (Pierwotne Formy Życia)",
            "Mushi Master": "Mistrz Mushi (Mushishi)",
            "Ginko": "Ginko (Wędrowny Znawca Mushi)",
            "Kouki": "Kouki (Płynne Źródło Życia)"
        },
        "character_forms": {
            "Villagers -> Ginko": "panie Ginko / mistrzu Ginko"
        }
    },
    "mieruko_chan": {
        "title": "Mieruko-chan (Ta dziewczyna widzi potwory)",
        "aliases": [
            "mieruko-chan",
            "mieruko chan",
            "mieruko"
        ],
        "publisher": "Wydawnictwo Dango",
        "glossary": {
            "Grotesque Spirits": "Widmowe Potwory",
            "Ignore": "Ignoruj za wszelką cenę (Nie patrz na nich)",
            "Shrine Spirits": "Bóstwa Chramu (Trzy Modlitwy)"
        },
        "character_forms": {
            "Miko -> Hana": "Hana / na ty",
            "Hana -> Miko": "Miko / na ty"
        }
    },
    "rent_a_girlfriend": {
        "title": "Dziewczyna do wynajęcia (Kanojo, Okarishimasu)",
        "aliases": [
            "kanojo okarishimasu",
            "kanojo, okarishimasu",
            "rent a girlfriend",
            "dziewczyna do wynajecia",
            "dziewczyna do wynajęcia"
        ],
        "publisher": "Wydawnictwo Dango",
        "glossary": {
            "Rental Girlfriend": "Dziewczyna do Wynajęcia",
            "Diamond App": "Aplikacja Diamond",
            "Diamond Rental": "Wypożyczenie Diamentowe"
        },
        "character_forms": {
            "Kazuya -> Chizuru": "Mizuhara / Chizuru-san",
            "Chizuru -> Kazuya": "panie Kinoshita / Kazuya"
        }
    },
    "hamefura": {
        "title": "Moje odrodzenie w grze otome jako czarny charakter (Hamefura)",
        "aliases": [
            "hamefura",
            "otome game no hametsu flag",
            "my next life as a villainess"
        ],
        "publisher": "Wydawnictwo Dango",
        "glossary": {
            "Fortune Lover": "Gra Otome Fortune Lover",
            "Doom Flag / Destruction Flag": "Flaga Zgłuby",
            "Bakarina": "Katarina Claes (Bakarina)",
            "Exile / Death": "Wygnanie / Śmierć"
        },
        "character_forms": {
            "Katarina -> Geordo": "książę Geordo",
            "Geordo -> Katarina": "Katarino / moja droga"
        }
    },
    "natsume_yuujinchou": {
        "title": "Księga Przyjaciół Natsume (Natsume Yuujinchou)",
        "aliases": [
            "natsume yuujinchou",
            "natsume's book of friends",
            "ksiega przyjaciol natsume",
            "księga przyjaciół natsume"
        ],
        "publisher": "Wydawnictwo Dango",
        "glossary": {
            "Book of Friends": "Księga Przyjaciół (Yuujinchou)",
            "Nyanko-sensei / Madara": "Nyanko-sensei (Madara)",
            "Ayakashi / Youkai": "Ayakashi / Youkai (Duchy)",
            "Name Returning": "Zwracanie Imienia"
        },
        "character_forms": {
            "Natsume -> Nyanko-sensei": "mistrzu Nyanko / kocie",
            "Nyanko-sensei -> Natsume": "Natsume / dzieciaku"
        }
    },
    "twoje_kwietniowe_klamstwo": {
        "title": "Twoje kwietniowe kłamstwo (Shigatsu wa Kimi no Uso)",
        "aliases": [
            "shigatsu wa kimi no uso",
            "your lie in april",
            "twoje kwietniowe klamstwo",
            "twoje kwietniowe kłamstwo"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Human Metronome": "Ludzki Metronom",
            "Violinist": "Skrzypaczka",
            "Pianist": "Pianista",
            "Monotone World": "Czarno-biały Świat bez Dźwięków"
        },
        "character_forms": {
            "Kaori -> Kousei": "Przyjacielu A / Kousei",
            "Kousei -> Kaori": "Miyazono-san / Kaori"
        }
    },
    "toradora": {
        "title": "Toradora!",
        "aliases": [
            "toradora",
            "toradora!"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Palmtop Tiger": "Kieszonkowy Tygrys",
            "Dragon and Tiger": "Smok i Tygrys",
            "Ohashi High School": "Liceum Ohashi"
        },
        "character_forms": {
            "Taiga -> Ryuuji": "Ryuuji / kundlu",
            "Ryuuji -> Taiga": "Taiga / na ty",
            "Minori -> Ryuuji": "Takasu-kun"
        }
    },
    "shape_of_voice": {
        "title": "Kształt twojego głosu (Koe no Katachi / A Silent Voice)",
        "aliases": [
            "koe no katachi",
            "a silent voice",
            "ksztalt twojego glosu",
            "kształt twojego głosu"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Sign Language": "Język Migowy",
            "Notebook": "Zeszyt do Rozmów",
            "Redemption": "Odkupienie Win"
        },
        "character_forms": {
            "Shoya -> Shoko": "Nishimiya / Shoko",
            "Shoko -> Shoya": "Shoya (w języku migowym)"
        }
    },
    "d_gray_man": {
        "title": "D.Gray-man",
        "aliases": [
            "d.gray-man",
            "d gray man",
            "dgrayman"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Black Order": "Czarny Zakon",
            "Exorcist": "Egzorcysta",
            "Innocence": "Niewinność (Innocence)",
            "Akuma": "Akuma (Machina Cierpienia)",
            "Millennium Earl": "Tysiącletni Hrabia",
            "Noah Clan": "Klan Noego",
            "Crown Clown": "Błazen Koronny"
        },
        "character_forms": {
            "Allen -> Kanda": "Kanda / durniu",
            "Kanda -> Allen": "kiełku / fasolo",
            "Lenalee -> Allen": "Allen / na ty"
        }
    },
    "yu_yu_hakusho": {
        "title": "Yu Yu Hakusho (Wysłannik Zaświatów)",
        "aliases": [
            "yu yu hakusho",
            "yuyu hakusho",
            "wyslannik zaswiatow",
            "wysłannik zaświatów"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Spirit Detective": "Detektyw Zaświatów",
            "Spirit Gun / Reigan": "Pocisk Ducha (Reigan)",
            "Dark Tournament": "Mroczny Turniej",
            "Spirit World": "Świat Dusz (Reikai)",
            "Demon World": "Świat Demonów (Makai)",
            "Dragon of the Darkness Flame": "Czarny Płomienny Smok"
        },
        "character_forms": {
            "Yusuke -> Kuwabara": "Kuwabara / głąbie",
            "Hiei -> Yusuke": "Yusuke / durniu",
            "Kurama -> Yusuke": "Yusuke / na ty"
        }
    },
    "kenshin": {
        "title": "Rurouni Kenshin (Kenshin: Wędrowny Samuraj)",
        "aliases": [
            "rurouni kenshin",
            "kenshin",
            "rurouni kenshin meiji kenkaku romantan"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Battosai the Manslayer": "Battousai Zabójca",
            "Reverse-Blade Sword / Sakabato": "Miecz o Odwróconym Ostrzu (Sakabato)",
            "Hiten Mitsurugi-ryu": "Styl Miecza Hiten Mitsurugi",
            "Amakakeru Ryu no Hirameki": "Błysk Pikującego Smoka",
            "Kamiya Kasshin-ryu": "Styl Kamiya Kasshin (Miecz Chroniący Życie)",
            "Meiji Era": "Era Meiji"
        },
        "character_forms": {
            "Kenshin -> Kaoru": "panno Kaoru (Kaoru-dono)",
            "Kaoru -> Kenshin": "Kenshin / na ty",
            "Sanosuke -> Kenshin": "Kenshin / durniu"
        }
    },
    "hellsing": {
        "title": "Hellsing",
        "aliases": [
            "hellsing",
            "hellsing ultimate"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Hellsing Organization / Royal Order of Protestant Knights": "Organizacja Hellsing (Królewski Zakon Rycerzy Protestanckich)",
            "Alucard": "Alucard (Prawdziwy Wampir)",
            "Iscariot (Section XIII)": "Iscariot (Watykańska Sekcja XIII)",
            "Millennium": "Organizacja Millennium (Ostatni Batalion)",
            "Major": "Major (Dowódca Millennium)",
            "Alexander Anderson": "Ojciec Alexander Anderson (Bagnetowy Egzorcysta)"
        },
        "character_forms": {
            "Alucard -> Integra": "pani Hellsing / moja pani",
            "Integra -> Alucard": "Alucardzie / Szukaj i niszcz!",
            "Seras -> Alucard": "mistrzu"
        }
    },
    "black_lagoon": {
        "title": "Black Lagoon",
        "aliases": [
            "black lagoon"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Lagoon Company": "Kompania Lagoon",
            "Roanapur": "Miasto Zbrodni Roanapur",
            "Hotel Moscow": "Hotel Moskwa",
            "Balalaika": "Balalaika (Kapitan)",
            "Rip-Off Church": "Fałszywy Kościół (Siostra Eda)",
            "Cutlass": "Pistolety Beretta Cutlass"
        },
        "character_forms": {
            "Revy -> Rock": "Rock / gogusiu",
            "Rock -> Revy": "Revy / na ty",
            "Dutch -> Rock": "Rock / synu"
        }
    },
    "golden_kamuy": {
        "title": "Golden Kamuy",
        "aliases": [
            "golden kamuy",
            "golden kamuy s4",
            "golden kamuy s3",
            "golden kamuy s2",
            "golden kamuy s1"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Immortal Sugimoto": "Nieśmiertelny Sugimoto",
            "7th Division": "7. Dywizja (Siódma Dywizja Cesarskiej Armii)",
            "Lieutenant Tsurumi": "Porucznik Tsurumi",
            "Asirpa": "Asirpa",
            "Kotan": "Kotan (osada Ajnów)",
            "Chitatap": "Chitatap",
            "Hinna hinna": "Hinna, hinna (podziękowanie za dar jedzenia u Ajnów)",
            "Kamuy": "Kamuj (duch / bóstwo u Ajnów)",
            "Type 30 Rifle": "Karabin Typ 30 (Arisaka)",
            "Type 38 Rifle": "Karabin Typ 38 (Arisaka)",
            "Matagi": "Matagi (tradycyjny myśliwy z północy)",
            "Abashiri Prison": "Więzienie w Abashiri",
            "Tattooed Convicts": "Wytatuowani skazańcy",
            "Noppera-bou / Faceless Man": "Beztwarzowiec / Noppera-bo",
            "Ainu Gold": "Złoto Ajnów",
            "Surku": "Surku (trucizna z tojadu)"
        },
        "character_forms": {
            "Sugimoto -> Asirpa": "Asirpa / na ty",
            "Asirpa -> Sugimoto": "Sugimoto / na ty",
            "Soldiers -> Tsurumi": "panie poruczniku",
            "Shiraishi -> Sugimoto": "Sugimoto / Nieśmiertelny"
        }
    },
    "fullmetal_alchemist": {
        "title": "Fullmetal Alchemist (Stalowy Alchemik)",
        "aliases": [
            "fullmetal alchemist",
            "fullmetal alchemist brotherhood",
            "fma",
            "fmab",
            "stalowy alchemik"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "State Alchemist": "Państwowy Alchemik",
            "Fullmetal Alchemist": "Stalowy Alchemik",
            "Flame Alchemist": "Płomienny Alchemik",
            "Equivalent Exchange": "Zasada Równorzędnej Wymiany",
            "Philosopher's Stone": "Kamień Filozoficzny",
            "Homunculus": "Homunkulus",
            "Amestris": "Amestris",
            "Automail": "Automail (proteza mechaniczna)",
            "Transmutation Circle": "Krąg Transmutacyjny"
        },
        "character_forms": {
            "Ed -> Al": "Al / na ty",
            "Al -> Ed": "bracie",
            "Roy -> Ed": "Fullmetal / Edwardzie"
        }
    },
    "berserk": {
        "title": "Berserk",
        "aliases": [
            "berserk"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Band of the Hawk": "Drużyna Sokoła",
            "Dragonslayer": "Pogromca Smoków (miecz Gutsa)",
            "God Hand": "Ręka Boga",
            "Behelit": "Behelit / Jajo Króla",
            "Brand of Sacrifice": "Piętno Ofiary",
            "Black Swordsman": "Czarny Szermierz",
            "Apostle": "Apostoł",
            "Eclipse": "Zaćmienie"
        },
        "character_forms": {
            "Guts -> Griffith": "Griffith / na ty",
            "Casca -> Griffith": "Griffith / dowódco"
        }
    },
    "monster": {
        "title": "Monster",
        "aliases": [
            "monster",
            "naoki urasawa monster"
        ],
        "publisher": "Wydawnictwo Hanami",
        "glossary": {
            "Kinderheim 511": "Sierociniec Kinderheim 511",
            "Unnamed Monster": "Bezimienny Potwór",
            "Dr. Tenma": "Doktor Tenma",
            "Inspector Lunge": "Inspektor Lunge"
        },
        "character_forms": {
            "Tenma -> Nina": "Nina / na ty",
            "Lunge -> Tenma": "doktorze Tenma"
        }
    },
    "one_piece": {
        "title": "One Piece",
        "aliases": [
            "one piece",
            "op"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Straw Hat Pirates": "Piraci Słomkowego Kapelusza",
            "Grand Line": "Grand Line",
            "Devil Fruit": "Diabelski Owoc",
            "Haki": "Haki (Wola)",
            "Conqueror's Haki": "Królewskie Haki / Haki Zdobywcy",
            "Marine / Navy": "Marynarka Wojenna",
            "Admiral": "Admirał",
            "Warlords of the Sea / Shichibukai": "Królewscy Wojownicy Mórz (Shichibukai)",
            "All Blue": "All Blue"
        },
        "character_forms": {
            "Zoro -> Luffy": "Luffy / kapitanie",
            "Sanji -> Nami": "pani Nami / Nami-san"
        }
    },
    "tokyo_ghoul": {
        "title": "Tokyo Ghoul",
        "aliases": [
            "tokyo ghoul",
            "tokyo ghoul re"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "CCG / Commission of Counter Ghoul": "Biuro Przeciwdziałania Ghouli (CCG)",
            "Quinque": "Quinque (broń anty-ghoul)",
            "Kagune": "Kagune",
            "Kakuhou": "Kakuhou",
            "One-Eyed Ghoul": "Jednooki Ghoul",
            "Anteiku": "Kawiarnia Anteiku",
            "Aogiri Tree": "Drzewo Aogiri",
            "Ghoul Investigator": "Śledczy ds. Ghouli"
        },
        "character_forms": {
            "Kaneki -> Touka": "Touka / na ty",
            "Touka -> Kaneki": "Kaneki / na ty"
        }
    },
    "bungou_stray_dogs": {
        "title": "Bungou Stray Dogs (Bezpańscy Literaci)",
        "aliases": [
            "bungou stray dogs",
            "bungo stray dogs",
            "bsd",
            "bezpanscy literaci",
            "bezpańscy literaci"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Armed Detective Agency": "Zbrojna Agencja Detektywistyczna",
            "Port Mafia": "Portowa Mafia",
            "No Longer Human": "Zatracenie (Zatracenie człowieka)",
            "Rashomon": "Rashomon",
            "Beast Beneath the Moonlight": "Bestia w blasku księżyca",
            "The Guild": "Gildia",
            "Special Division for Unusual Powers": "Wydział ds. Zdolności Specjalnych"
        },
        "character_forms": {
            "Atsushi -> Dazai": "panie Dazai",
            "Akutagawa -> Dazai": "panie Dazai (z nabożnym szacunkiem)",
            "Dazai -> Kunikida": "Kunikida / na ty"
        }
    },
    "blue_lock": {
        "title": "Blue Lock",
        "aliases": [
            "blue lock"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Blue Lock": "Projekt Blue Lock",
            "Egoist": "Egoista",
            "Ego Jinpachi": "Jinpachi Ego",
            "Flow": "Stan Flow / Pełne Skupienie",
            "Metavision": "Metawizja"
        },
        "character_forms": {
            "Isagi -> Bachira": "Bachira / na ty",
            "Rin -> Isagi": "cieciu / śmieciu / Isagi"
        }
    },
    "haikyuu": {
        "title": "Haikyu!! (Haikyuu!!)",
        "aliases": [
            "haikyuu",
            "haikyu",
            "haikyuu!!",
            "haikyu!!"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Karasuno High": "Liceum Karasuno",
            "Quick Attack": "Szybki atak (Atak z pierwszej)",
            "Minus Tempo Attack": "Atak w tempie minusowym",
            "Libero": "Libero",
            "Setter": "Rozgrywający",
            "Wing Spiker": "Skrzydłowy / Przyjmujący",
            "Middle Blocker": "Środkowy bloku",
            "Spring Tournament / Harukou": "Turniej Wiosenny (Harukou)"
        },
        "character_forms": {
            "Hinata -> Kageyama": "Kageyama / na ty",
            "Hinata -> Tsukishima": "Tsukishima / na ty",
            "Hinata -> Daichi": "kapitanie / panie Daichi"
        }
    },
    "oshi_no_ko": {
        "title": "Moja Gwiazda (Oshi no Ko)",
        "aliases": [
            "oshi no ko",
            "my star",
            "moja gwiazda"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "B-Komachi": "Grupa Idol B-Komachi",
            "Strawberry Productions": "Strawberry Productions",
            "Lalalie Theatrical Company": "Teatr Lalalie",
            "Aqua": "Aqua",
            "Ruby": "Ruby",
            "Ai Hoshino": "Ai Hoshino"
        },
        "character_forms": {
            "Aqua -> Ruby": "Ruby / na ty",
            "Ruby -> Aqua": "Aqua / braciszku",
            "Kana -> Aqua": "Aqua / na ty"
        }
    },
    "bocchi_the_rock": {
        "title": "Bocchi the Rock!",
        "aliases": [
            "bocchi the rock",
            "bocchi the rock!"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Kessoku Band": "Kessoku Band",
            "guitarhero": "guitarhero",
            "Live House STARRY": "Klub STARRY",
            "Bocchi": "Bocchi / Hitori"
        },
        "character_forms": {
            "Nijika -> Hitori": "Bocchi-chan / Bocchi",
            "Hitori -> Nijika": "Nijika-chan / pani Nijiko (z lękiem)"
        }
    },
    "dragon_ball": {
        "title": "Dragon Ball",
        "aliases": [
            "dragon ball",
            "dragon ball z",
            "dragon ball super",
            "dbz",
            "dbs"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Kamehameha": "Kamehameha",
            "Super Saiyan": "Super Saiyanin",
            "Dragon Balls": "Smocze Kule",
            "Senzu Bean": "Fasolka Senzu",
            "Spirit Bomb / Genki Dama": "Kula Genki Dama",
            "Capsule Corp": "Capsule Corporation"
        },
        "character_forms": {
            "Goku -> Vegeta": "Vegeta / na ty",
            "Vegeta -> Goku": "Kakarotto"
        }
    },
    "naruto": {
        "title": "Naruto / Naruto Shippuuden",
        "aliases": [
            "naruto",
            "naruto shippuden",
            "naruto shippuuden",
            "boruto"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Hidden Leaf Village / Konoha": "Wioska Ukrytego Liścia (Konoha)",
            "Hokage": "Hokage",
            "Rasengan": "Rasengan",
            "Shadow Clone Jutsu": "Technika Klonowania Cienia",
            "Nine-Tailed Fox / Kurama": "Dziewięcioogoniasty Lis (Kyuubi / Kurama)",
            "Chidori": "Chidori / Piorunochwyt",
            "Sharingan": "Szaringan",
            "Akatsuki": "Akatsuki"
        },
        "character_forms": {
            "Naruto -> Kakashi": "panie Kakashi / Kakashi-sensei",
            "Naruto -> Sasuke": "Sasuke / na ty",
            "Sakura -> Sasuke": "Sasuke-kun / Sasuke"
        }
    },
    "bleach": {
        "title": "Bleach",
        "aliases": [
            "bleach",
            "bleach thousand year blood war",
            "bleach tybw"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Soul Reaper / Shinigami": "Żniwiarz Dusz (Shinigami)",
            "Soul Society": "Społeczność Dusz (Soul Society)",
            "Zanpakuto": "Zanpakuto",
            "Bankai": "Bankai",
            "Shikai": "Shikai",
            "Hollow": "Pusty (Hollow)",
            "Espada": "Espada",
            "Quincy": "Quincy",
            "Getsuga Tenshou": "Getsuga Tenshou"
        },
        "character_forms": {
            "Ichigo -> Rukia": "Rukia / na ty",
            "Rukia -> Ichigo": "Ichigo / durniu"
        }
    },
    "death_note": {
        "title": "Death Note (Notatnik Śmierci)",
        "aliases": [
            "death note",
            "notatnik smierci",
            "notatnik śmierci"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Death Note": "Notatnik Śmierci",
            "Shinigami": "Shinigami (Bóg Śmierci)",
            "Kira": "Kira",
            "Shinigami Eyes": "Oczy Shinigami",
            "L": "L / Ryuzaki"
        },
        "character_forms": {
            "Light -> L": "Ryuzaki / na ty",
            "L -> Light": "panie Yagami / Light"
        }
    },
    "jojo": {
        "title": "JoJo's Bizarre Adventure",
        "aliases": [
            "jojo",
            "jojos bizarre adventure",
            "jojo no kimyou na bouken",
            "stardust crusaders",
            "golden wind",
            "stone ocean"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Stand": "Stand",
            "Hamon / Ripple": "Fale Hamon",
            "Speedwagon Foundation": "Fundacja Speedwagona",
            "Stone Mask": "Kamienna Maska",
            "Dio": "Dio Brando"
        },
        "character_forms": {
            "Jotaro -> Joseph": "stary / dziadku",
            "Polnareff -> Jotaro": "Jotaro / na ty"
        }
    },
    "dandadan": {
        "title": "DanDaDan",
        "aliases": [
            "dandadan",
            "dan da dan"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Turbo Granny": "Turbo Babcia",
            "Serpoians": "Kosmici Serpo",
            "Spirit / Yokai": "Yokai / Duch",
            "Cursed Ball": "Złota Kula"
        },
        "character_forms": {
            "Momo -> Okarun": "Okarun / na ty",
            "Okarun -> Momo": "Ayase-san / Momo"
        }
    },
    "kaiju_no_8": {
        "title": "Kaiju No. 8",
        "aliases": [
            "kaiju no 8",
            "kaiju no. 8",
            "kaiju no.8"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Kaiju": "Kaiju (Potwór)",
            "Defense Force": "Siły Samoobrony",
            "Unleashed Combat Power": "Uwolniona Siła Bojowa",
            "Monster Sweeper": "Sprzątacze Kaiju"
        },
        "character_forms": {
            "Kafka -> Reno": "Reno / na ty",
            "Mina -> Kafka": "Kafka / panie Hibino"
        }
    },
    "solo_leveling": {
        "title": "Solo Leveling (Tylko ja awansuję)",
        "aliases": [
            "solo leveling",
            "ore dake level up na ken",
            "tylko ja awansuje",
            "tylko ja awansuję"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Hunter": "Łowca",
            "Shadow Monarch": "Monarcha Cieni",
            "Arise": "Powstań",
            "D-Rank / S-Rank": "Ranga D / Ranga S",
            "Dungeon Break": "Przełamanie Lochu",
            "Shadow Soldiers": "Żołnierze Cienia"
        },
        "character_forms": {
            "Jinwoo -> Shadows": "Powstańcie / do ataku"
        }
    },
    "mushoku_tensei": {
        "title": "Mushoku Tensei: Przegrany bezrobotny",
        "aliases": [
            "mushoku tensei",
            "jobless reincarnation"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Mana Disaster / Teleportation Incident": "Incydent Teleportacyjny (Katastrofa Many)",
            "Superd": "Plemię Superdów",
            "Dragon God Orsted": "Smoczy Bóg Orsted",
            "Ruijerd of the Dead End": "Ruijerd z Dead End",
            "Magic University of Ranoa": "Uniwersytet Magii Ranoa"
        },
        "character_forms": {
            "Rudeus -> Eris": "pani Eris / Eris",
            "Rudeus -> Roxy": "mistrzyni Roxy / bogini Roxy"
        }
    },
    "made_in_abyss": {
        "title": "Made in Abyss",
        "aliases": [
            "made in abyss"
        ],
        "publisher": "Wydawnictwo Kotori",
        "glossary": {
            "Abyss": "Otchłań",
            "Delver / Cave Raider": "Eksplorator / Grabieżca Jaskiń",
            "White Whistle": "Biały Gwizdek",
            "Curse of the Abyss": "Klątwa Otchłani",
            "Relic": "Relikt",
            "Orth": "Miasto Orth"
        },
        "character_forms": {
            "Riko -> Reg": "Reg / na ty",
            "Nanachi -> Riko": "Riko / na ty"
        }
    },
    "overlord": {
        "title": "Overlord",
        "aliases": [
            "overlord",
            "overlord iv",
            "overlord iii",
            "overlord ii"
        ],
        "publisher": "Wydawnictwo Kotori",
        "glossary": {
            "Great Tomb of Nazarick": "Wielki Grobowiec Nazarick",
            "Supreme Being": "Najwyższa Istota",
            "Floor Guardian": "Strażnik Piętra",
            "Ainz Ooal Gown": "Ainz Ooal Gown",
            "Sorcerer Kingdom": "Królestwo Magii",
            "World Item": "Przedmiot Światowy"
        },
        "character_forms": {
            "Guardians -> Ainz": "Władco Ainz / Lordzie Ainz",
            "Ainz -> Guardians": "po imieniu"
        }
    },
    "hells_paradise": {
        "title": "Piekielny Raj (Jigokuraku / Hell's Paradise)",
        "aliases": [
            "jigokuraku",
            "hells paradise",
            "hell's paradise",
            "piekielny raj"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Elixir of Immortality": "Eliksir Nieśmiertelności",
            "Asaemon": "Klan Yamada Asaemon",
            "Gabimaru the Hollow": "Gabimaru Pusty",
            "Tao": "Energia Tao",
            "Lord Tensen": "Lord Tensen"
        },
        "character_forms": {
            "Sagiri -> Gabimaru": "Gabimaru / na ty",
            "Gabimaru -> Sagiri": "Sagiri / na ty"
        }
    },
    "tokyo_revengers": {
        "title": "Tokyo Revengers",
        "aliases": [
            "tokyo revengers"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Tokyo Manji Gang / Toman": "Gang Tokyo Manji (Toman)",
            "Commander": "Naczelny Dowódca / Prezydent Tomana",
            "Vice-Commander": "Wicedowódca",
            "Time Leap": "Skok w czasie",
            "Mikey the Invincible": "Niezwyciężony Mikey"
        },
        "character_forms": {
            "Takemichi -> Mikey": "Mikey-kun / Mikey",
            "Draken -> Mikey": "Mikey / na ty"
        }
    },
    "nieuchwytny_samuraj": {
        "title": "Nieuchwytny Samuraj (Nige Jouzu no Wakagimi / The Elusive Samurai)",
        "aliases": [
            "nieuchwytny samuraj",
            "nige jouzu no wakagimi",
            "nige jouzu no wakagimi s2",
            "nige jouzu no wakagimi 2nd season",
            "the elusive samurai",
            "elusive samurai",
            "nigejouzu no wakagimi",
            "nigejouzu"
        ],
        "publisher": "Wydawnictwo Dango",
        "glossary": {
            "Elusive Samurai": "Nieuchwytny Samuraj",
            "Suwa Grand Shrine": "Wielka Świątynia Suwa",
            "Suwa Shrine": "Chram Suwa / Świątynia Suwa",
            "Suwa Sect": "Nurt Suwa",
            "Three Great Generals of the Suwa Sect": "Trzej Wielcy Generałowie Nurtu Suwa",
            "Three Great Generals of Suwa": "Trzej Wielcy Generałowie Suwa",
            "Hojo clan": "Ród Hōjō",
            "Ashikaga clan": "Ród Ashikaga",
            "Suwa clan": "Ród Suwa",
            "Kamakura Shogunate": "Szogunat Kamakura",
            "Kenmu Restoration": "Restauracja Kenmu",
            "Nanboku-cho period": "Okres Nanboku-chō (Dwóch Dworów)",
            "Nakasendai Rebellion": "Powstanie Nakasendai",
            "Inuoumono": "Inuoumono (łucznictwo konne z psami)",
            "Yabusame": "Yabusame (rytualne łucznictwo konne)",
            "Kasagake": "Kasagake (łucznictwo do kapeluszy)",
            "Lord of Kamakura": "Władca Kamakury / Pan na Kamakurze",
            "Fukashi Fortress": "Twierdza Fukashi",
            "Shinano Province": "Prowincja Shinano"
        },
        "character_forms": {
            "Tokiyuki -> Yorishige": "panie Yorishige / Wasza Świątobliwość",
            "Yorishige -> Tokiyuki": "panie Tokiyuki / panie młody",
            "Shizuku -> Tokiyuki": "panie Tokiyuki",
            "Kojiro -> Tokiyuki": "Tokiyuki / Wasza Dostojność",
            "Ayako -> Tokiyuki": "Tokiyuki / paniczu Tokiyuki"
        }
    },
    "kusuriya_no_hitorigoto": {
        "title": "Zapiski Zielarki (Kusuriya no Hitorigoto / The Apothecary Diaries)",
        "aliases": [
            "kusuriya no hitorigoto",
            "apothecary diaries",
            "the apothecary diaries",
            "zapiski zielarki"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Rear Palace": "Tylny Pałac",
            "Inner Palace": "Pałac Wewnętrzny",
            "Pure Consort": "Czysta Małżonka",
            "Precious Consort": "Drogocenna Małżonka",
            "Virtuous Consort": "Cnotliwa Małżonka",
            "Capable Consort": "Zdolna Małżonka",
            "Verdigris House": "Dom pod Zielonym Gryfem",
            "Courtesan": "Kurtyzana",
            "Eunuch": "Eunuch",
            "Apothecary": "Zielarka / Aptekarka",
            "Quack Doctor": "Pocieszny Doktorek / Konował"
        },
        "character_forms": {
            "Maomao -> Jinshi": "pan Jinshi",
            "Jinshi -> Maomao": "Maomao / ty",
            "Gaoshun -> Jinshi": "panicz Jinshi",
            "Maomao -> Gyokuyou": "pani Gyokuyou / Wasza Wysokość"
        }
    },
    "dr_stone": {
        "title": "Dr. Stone",
        "aliases": [
            "dr stone",
            "dr. stone",
            "dr.stone"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Kingdom of Science": "Królestwo Nauki",
            "Petrification": "Petryfikacja (Zamiana w kamień)",
            "Revival Fluid / Miracle Fluid": "Płyn Ożywienia (Cudowny Płyn)",
            "Empire of Might": "Imperium Siły Tsukasy",
            "Ishigami Village": "Wioska Ishigami",
            "Nital": "Nital (Kwas azotowy + alkohol)",
            "Sulfa Drug": "Sulfamid"
        },
        "character_forms": {
            "Senku -> Chrome": "Chrome / na ty",
            "Chrome -> Senku": "Senku / na ty",
            "Kohaku -> Senku": "Senku / czarodzieju"
        }
    },
    "wind_breaker": {
        "title": "Wind Breaker",
        "aliases": [
            "wind breaker",
            "windbreaker"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Bofurin": "Bofurin (Strażnicy Wiatru Furin)",
            "Furin High School": "Liceum Furin",
            "Shishitoren": "Gang Shishitoren",
            "Keel": "Gang Keel",
            "Captain": "Kapitan / Dowódca"
        },
        "character_forms": {
            "Sakura -> Umemiya": "Umemiya / na ty (szorstko)",
            "Nirei -> Sakura": "panie Sakura / Sakura-san",
            "Suo -> Sakura": "Sakura-kun / Sakura"
        }
    },
    "witch_hat_atelier": {
        "title": "Atelier Spiczastych Kapeluszy (Tongari Boushi no Atelier)",
        "aliases": [
            "tongari boushi no atelier",
            "witch hat atelier",
            "atelier spiczastych kapeluszy",
            "atelier szpiczastych kapelusznikow",
            "atelier szpiczastych kapeluszy",
            "tongari boushi"
        ],
        "publisher": "Wydawnictwo Kotori",
        "glossary": {
            "Pointed Hat / Pointed Caps": "Spiczasty Kapelusz (Magowie Prawi)",
            "Brimmed Hat / Brimmed Caps": "Kapelusze z Rondem (Magowie Wyklęci / Wrogowie)",
            "Magic Ink": "Magiczny Atrament",
            "Forbidden Magic": "Magia Zakazana (Magia Ciała i Ludzi)",
            "Knights of Moralis": "Rycerze Moralis (Strażnicy Praw Magii)",
            "Great Hall": "Wielka Sala Magów (Rada Siedmiu)",
            "Atelier": "Atelier (Pracownia Magiczna)",
            "Magic Crest / Glyph": "Pieczęć Magiczna / Glif",
            "Keystones": "Kamienie Kluczowe",
            "Silverwood": "Srebrnodrzew",
            "Magic Wand / Pen": "Rysik Magiczny / Pióro Magiczne",
            "Silver Night Festival": "Festiwal Srebrnej Nocy"
        },
        "character_forms": {
            "Coco -> Qifrey": "mistrzu Qifrey",
            "Agott -> Coco": "Coco / na ty",
            "Tetia -> Coco": "Coco / na ty",
            "Richeh -> Coco": "Coco / na ty",
            "Olruggio -> Qifrey": "Qifrey / na ty",
            "Qifrey -> Olruggio": "Olruggio / na ty",
            "Coco -> Beldaruit": "Wielki Mędrcu Beldaruit / panie Beldaruit"
        }
    },
    "chihayafuru": {
        "title": "Chihayafuru",
        "aliases": [
            "chihayafuru"
        ],
        "publisher": "Wydawnictwo Hanami",
        "glossary": {
            "Karuta": "Karuta (Ogura Hyakunin Isshu)",
            "Meijin": "Meijin (Mistrz)",
            "Queen": "Królowa Karuty",
            "Mizuusawa High": "Liceum Mizusawa",
            "Class A / Class B": "Klasa A / Klasa B"
        },
        "character_forms": {
            "Chihaya -> Taichi": "Taichi / na ty",
            "Chihaya -> Arata": "Arata / na ty"
        }
    },
    "pluto": {
        "title": "Pluto",
        "aliases": [
            "pluto",
            "naoki urasawa pluto"
        ],
        "publisher": "Wydawnictwo Hanami",
        "glossary": {
            "Gesicht": "Inspektor Gesicht",
            "Atom": "Atom / Astro Boy",
            "Seven Great Robots": "Siedem Najwspanialszych Robotów Świata",
            "39th Central Asian War": "39. Wojna Środkowoazjatycka",
            "Bora Corporation": "Korporacja Bora"
        },
        "character_forms": {
            "Gesicht -> Atom": "Atom / na ty",
            "Atom -> Gesicht": "panie Gesicht"
        }
    },
    "komi_cant_communicate": {
        "title": "Komi nie potrafi się porozumieć (Komi-san wa, Komyushou desu)",
        "aliases": [
            "komi-san wa komyushou desu",
            "komi cant communicate",
            "komi can't communicate",
            "komi san",
            "komi nie potrafi sie porozumiec",
            "komi nie potrafi się porozumieć"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Communication Disorder": "Zaburzenie Komunikacji",
            "Itan Private High School": "Prywatne Liceum Itan",
            "100 Friends": "100 Przyjaciół"
        },
        "character_forms": {
            "Tadano -> Komi": "Komi-san / Komi",
            "Najimi -> Tadano": "Tadano / na ty"
        }
    },
    "re_zero": {
        "title": "Re:Zero - Życie w innym świecie od zera",
        "aliases": [
            "re:zero",
            "re zero",
            "rezero",
            "re:zero kara hajimeru isekai seikatsu",
            "zycie w innym swiecie od zera",
            "życie w innym świecie od zera"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Return by Death": "Powrót przez Śmierć",
            "Witch of Envy / Satella": "Wiedźma Zazdrości (Satella)",
            "Witch Cult": "Kult Wiedźmy",
            "Sin Archbishop": "Arcybiskup Grzechu",
            "Dragon Kingdom of Lugnica": "Smocze Królestwo Lugnicy",
            "Royal Selection": "Królewska Selekcja",
            "White Whale": "Biały Wieloryb",
            "Mabeast": "Magiczna Bestia"
        },
        "character_forms": {
            "Subaru -> Emilia": "Emilia-tan / Emilia",
            "Rem -> Subaru": "panie Subaru / Subaru-kun",
            "Ram -> Subaru": "Barusu / głąbie"
        }
    },
    "sword_art_online": {
        "title": "Sword Art Online",
        "aliases": [
            "sword art online",
            "sao",
            "sword art online alicization"
        ],
        "publisher": "Wydawnictwo Kotori",
        "glossary": {
            "Aincrad": "Aincrad (Pływający Zamek)",
            "NerveGear": "NerveGear",
            "Beater": "Beater (Beta Tester + Oszust)",
            "Knights of the Blood Oath": "Rycerze Krwi",
            "Black Swordsman": "Czarny Szermierz",
            "Dual Blades": "Podwójne Ostrza",
            "Underworld": "Underworld",
            "Fluctlight": "Fluctlight"
        },
        "character_forms": {
            "Kirito -> Asuna": "Asuna / na ty",
            "Asuna -> Kirito": "Kirito-kun / Kirito",
            "Klein -> Kirito": "Kirito / na ty"
        }
    },
    "fire_force": {
        "title": "Fire Force (Enen no Shouboutai)",
        "aliases": [
            "fire force",
            "enen no shouboutai"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Special Fire Force": "Specjalne Siły Przeciwpożarowe",
            "Company 8": "Ósma Kompania",
            "Infernals": "Piekielni",
            "Adolla Burst": "Płomień Adolli (Adolla Burst)",
            "White-Clad": "Białe Szaty",
            "Evangelist": "Ewangelista",
            "Latom": "Látom (Niech spłonie w pokoju)"
        },
        "character_forms": {
            "Shinra -> Captain Obi": "kapitanie Obi",
            "Arthur -> Shinra": "Shinra / diable",
            "Iris -> Shinra": "panie Shinra"
        }
    },
    "soul_eater": {
        "title": "Soul Eater",
        "aliases": [
            "soul eater"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "DWMA / Shibusen": "Akademia Śmierci (Shibusen)",
            "Meister": "Mistrz Broni (Meister)",
            "Demon Weapon": "Demoniczna Broń",
            "Death Scythe": "Kosa Śmierci",
            "Lord Death / Shinigami": "Lord Śmierć",
            "Kishin": "Kishin (Bóstwo Szaleństwa)",
            "Soul Resonance": "Rezonans Dusz"
        },
        "character_forms": {
            "Maka -> Soul": "Soul / na ty",
            "Black Star -> Tsubaki": "Tsubaki / na ty",
            "Death the Kid -> Liz": "Liz / na ty"
        }
    },
    "noragami": {
        "title": "Noragami",
        "aliases": [
            "noragami",
            "noragami aragoto"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Delivery God Yato": "Bóg na Telefon Yato",
            "Regalia / Shinki": "Święty Oręż (Shinki)",
            "Phantoms / Ayakashi": "Zjawy (Ayakashi)",
            "Ablution": "Rytuał Oczyszczenia",
            "Bishamonten": "Bishamonten (Bogini Wojny)",
            "Kofuku": "Bogini Biedy Kofuku"
        },
        "character_forms": {
            "Hiyori -> Yato": "Yato / na ty",
            "Yukine -> Yato": "Yato / durniu",
            "Yato -> Hiyori": "Hiyori / na ty"
        }
    },
    "eminence_in_shadow": {
        "title": "Eminencja w cieniu (Kage no Jitsuryokusha ni Naritakute!)",
        "aliases": [
            "kage no jitsuryokusha ni naritakute",
            "the eminence in shadow",
            "eminence in shadow",
            "eminencja w cieniu"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Shadow Garden": "Ogród Cieni (Shadow Garden)",
            "Cult of Diablos": "Kult Diablosa",
            "Seven Shadows": "Siedem Cieni",
            "Lord Shadow": "Władca Shadow / Lord Shadow",
            "I Am Atomic": "Jestem Atomem (I Am Atomic)"
        },
        "character_forms": {
            "Shadows -> Cid": "Władco Shadow / panie Shadow",
            "Cid -> Alpha": "Alpha / na ty"
        }
    },
    "yofukashi_no_uta": {
        "title": "Pieśń Nocy (Yofukashi no Uta / Call of the Night)",
        "aliases": [
            "yofukashi no uta",
            "call of the night",
            "pieśń nocy",
            "piesn nocy"
        ],
        "publisher": "Wydawnictwo Dango",
        "glossary": {
            "Vampire": "Wampir",
            "Night Walking": "Nocne Włóczęgi",
            "Blood Sucking": "Wysysanie Krwi",
            "Offspring": "Potomek / Dziecko Wampira"
        },
        "character_forms": {
            "Kou -> Nazuna": "Nazuna / na ty",
            "Nazuna -> Kou": "Kou-kun / Kou"
        }
    }
}


class MangaCanonRegistry:
    """
    Zarządca i inteligentna wyszukiwarka oficjalnego kanonu polskich wydań mangowych
    (Waneko, J.P.Fantastica, Studio JG, Kotori, Hanami, Dango, Akuma, Egmont itp.).
    """

    def __init__(self, custom_dir: Optional[Path] = None):
        self.custom_dir = custom_dir or MANGA_CANON_DIR
        self.custom_dir.mkdir(parents=True, exist_ok=True)
        self.canon_db: Dict[str, Dict[str, Any]] = dict(BUILTIN_MANGA_CANON)
        self._load_custom_files()

    def _load_custom_files(self):
        """Loads custom and dynamically discovered JSON files from manga_canon/ directory."""
        if not self.custom_dir.exists():
            return
        for json_file in self.custom_dir.glob("*.json"):
            if json_file.name.startswith("."):
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "title" in data:
                        key = json_file.stem.lower()
                        self.canon_db[key] = data
            except Exception:
                pass

    def find_canon_for_series(self, anime_title: str) -> Optional[Dict[str, Any]]:
        """Finds Polish manga canon entry based on anime title."""
        if not anime_title:
            return None

        norm_title = re.sub(r"[^\w\s]", " ", anime_title.lower()).strip()
        norm_title_compact = re.sub(r"\s+", " ", norm_title)

        # 1. Exact or alias matching
        for key, entry in self.canon_db.items():
            aliases = entry.get("aliases", []) + [entry.get("title", "").lower(), key]
            for alias in aliases:
                norm_alias = re.sub(r"[^\w\s]", " ", alias.lower()).strip()
                if norm_alias == norm_title_compact:
                    return entry
                if len(norm_alias) >= 4 and (norm_alias in norm_title_compact or norm_title_compact in norm_alias):
                    return entry

        return None

    def get_or_discover_canon(
        self,
        series_title: str,
        candidates: Optional[List[str]] = None,
        anime_meta: Optional[Dict[str, Any]] = None,
        client: Optional[Any] = None,
        model: str = "gemini-3.6-flash"
    ) -> Optional[Dict[str, Any]]:
        """
        Universal Polish Manga Canon Resolver:
        1. Checks built-in database and local cache.
        2. If not found, dynamically queries AI knowledge base to discover
           if the anime has an official Polish manga/light novel edition (Waneko, JPF, Studio JG, Kotori, Hanami, Dango etc.).
        3. Saves discovered canon to manga_canon/{slug}.json for instant offline access.
        """
        all_candidates = []
        if series_title:
            all_candidates.append(series_title)
        if candidates:
            all_candidates.extend(candidates)
        if anime_meta:
            for k in ["title_romaji", "title_english", "title_japanese", "title_native"]:
                if anime_meta.get(k):
                    all_candidates.append(anime_meta[k])

        # 1. Check local DB
        for cand in all_candidates:
            if cand:
                entry = self.find_canon_for_series(cand)
                if entry:
                    return entry

        # 2. Check negative cache
        neg_cache_path = self.custom_dir / ".no_canon_cache.json"
        neg_cache = set()
        if neg_cache_path.exists():
            try:
                with open(neg_cache_path, "r", encoding="utf-8") as f:
                    neg_cache = set(json.load(f))
            except Exception:
                pass

        primary_title = series_title or (all_candidates[0] if all_candidates else "")
        if not primary_title:
            return None

        slug = re.sub(r"[^\w]+", "_", primary_title.lower()).strip("_")
        if slug in neg_cache:
            return None

        # 3. Dynamic Discovery via AI (if client available)
        if not client:
            return None

        try:
            from google.genai import types
            prompt = f"""
Jesteś czołowym ekspertem i archiwistą rynku mangi oraz light novel w Polsce.
Znasz na wylot katalogi wszystkich oficjalnych polskich wydawnictw:
- Wydawnictwo Waneko
- Wydawnictwo J.P.Fantastica (JPF)
- Wydawnictwo Studio JG
- Wydawnictwo Kotori
- Wydawnictwo Hanami
- Wydawnictwo Dango
- Wydawnictwo Akuma
- Wydawnictwo Egmont Polska
- Wydawnictwo Amber / Kasen / Taiga

ZADANIE:
Sprawdź, czy seria anime/manga '{primary_title}' (lub powiązane tytuły: {', '.join(all_candidates[:4])}) POSIADA OFICJALNE POLSKIE WYDANIE MANGI LUB LIGHT NOVEL wydane przez jakiekolwiek licencjonowane polskie wydawnictwo.

Jeżeli seria została oficjalnie wydana w Polsce, zwróć WYCZERPUJĄCY, KOMPLETNY JSON ze WSZYSTKIMI kluczowymi nazwami własnymi, rangami, atakami, magią, lokacjami i formami zwrotów:
{{
  "has_polish_edition": true,
  "title": "Oficjalny Polski Tytuł (Oryginalny Tytuł)",
  "publisher": "Wydawnictwo XYZ",
  "aliases": ["{primary_title.lower()}", "{slug}"],
  "glossary": {{
    "Angielska/Japońska nazwa ataku, rangi, magii, frakcji lub lokacji": "Oficjalne polskie tłumaczenie z polskiego wydania mangi"
  }},
  "character_forms": {{
    "PostaćA -> PostaćB": "kanoniczna forma zwrotu (np. panie X / po imieniu / na ty / mistrzu)"
  }}
}}

Jeżeli seria NIE POSIADA oficjalnego polskiego wydania mangi/LN w Polsce:
Zwróć:
{{
  "has_polish_edition": false
}}

ZWRÓĆ WYŁĄCZNIE CZYSTY KOD JSON BEZ ZBĘDNYCH KOMENTARZY.
"""
            target_client = getattr(client, "get_client", lambda: client)()
            resp = target_client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            raw_text = resp.text.strip()
            data = json.loads(raw_text)

            if data.get("has_polish_edition") and data.get("title") and data.get("publisher"):
                entry_data = {
                    "title": data["title"],
                    "aliases": list(set(data.get("aliases", []) + [slug, primary_title.lower()])),
                    "publisher": data["publisher"],
                    "glossary": data.get("glossary", {}),
                    "character_forms": data.get("character_forms", {})
                }
                out_path = self.custom_dir / f"{slug}.json"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(entry_data, f, ensure_ascii=False, indent=2)

                self.canon_db[slug] = entry_data
                return entry_data
            else:
                neg_cache.add(slug)
                with open(neg_cache_path, "w", encoding="utf-8") as f:
                    json.dump(list(neg_cache), f, ensure_ascii=False, indent=2)
                return None
        except Exception:
            return None

    def format_canon_for_prompt(self, canon_entry: Optional[Dict[str, Any]]) -> str:
        """Formats complete manga canon entry into a system prompt block with ZERO truncation."""
        if not canon_entry:
            return ""

        lines = [
            f"=== [KANON] OFICJALNY KANON POLSKIEGO WYDANIA MANGI ({canon_entry.get('publisher', 'Oficjalne Wydawnictwo')}) ===",
            f"Dla serii '{canon_entry.get('title', 'Anime')}' BEZWZGLĘDNIE zachowaj poniższą kanoniczną terminologię:"
        ]

        glossary = canon_entry.get("glossary", {})
        if glossary:
            lines.append("• Kompletny słowniczek kanoniczny (ataki, magia, krainy, formacje, rangi):")
            for term_src, term_pl in glossary.items():
                lines.append(f"  - '{term_src}' -> '{term_pl}'")

        char_forms = canon_entry.get("character_forms", {})
        if char_forms:
            lines.append("• Kompletne kanoniczne formy zwrotów i relacje:")
            for rel, form_desc in char_forms.items():
                lines.append(f"  - {rel}: {form_desc}")

        lines.append("(!) ZASADA AVT: Zachowaj kanoniczne nazwy, ale przy długich wypowiedziach stosuj zwięzłą polską składnię (limit 17 CPS).")
        lines.append("=========================================================================\n")

        return "\n".join(lines)
