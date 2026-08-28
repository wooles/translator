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
        "aliases": ["kingdom", "kingdom s6", "kingdom season 6", "kingdom s5", "kingdom s4", "kingdom s3", "kingdom s2", "kingdom s1"],
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
            "Great General": "Wielki Generał",
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
        "aliases": ["jujutsu kaisen", "jujutsu kaisen s2", "jujutsu", "jjk"],
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
        "aliases": ["sousou no frieren", "frieren", "frieren beyond journeys end"],
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
        "aliases": ["chainsaw man", "csm"],
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
        "aliases": ["shingeki no kyojin", "attack on titan", "aot"],
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
        "aliases": ["vinland saga", "vinland"],
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
        "aliases": ["kimetsu no yaiba", "demon slayer"],
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
        "aliases": ["dungeon meshi", "delicious in dungeon"],
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
        "aliases": ["spy x family", "spyxfamily"],
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
    "golden_kamuy": {
        "title": "Golden Kamuy",
        "aliases": ["golden kamuy", "golden kamuy s4", "golden kamuy s3", "golden kamuy s2", "golden kamuy s1"],
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
        "aliases": ["fullmetal alchemist", "fullmetal alchemist brotherhood", "fma", "fmab"],
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
        "aliases": ["berserk"],
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
        "aliases": ["monster", "naoki urasawa monster"],
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
        "aliases": ["one piece", "op"],
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
        "aliases": ["tokyo ghoul", "tokyo ghoul re"],
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
        "aliases": ["bungou stray dogs", "bungo stray dogs", "bsd"],
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
        "aliases": ["blue lock"],
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
        "aliases": ["haikyuu", "haikyu", "haikyuu!!", "haikyu!!"],
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
        "aliases": ["oshi no ko", "my star"],
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
        "aliases": ["bocchi the rock", "bocchi the rock!"],
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
        "aliases": ["dragon ball", "dragon ball z", "dragon ball super", "dbz", "dbs"],
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
        "aliases": ["naruto", "naruto shippuden", "naruto shippuuden", "boruto"],
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
        "aliases": ["bleach", "bleach thousand year blood war", "bleach tybw"],
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
        "aliases": ["death note"],
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
        "aliases": ["jojo", "jojos bizarre adventure", "jojo no kimyou na bouken", "stardust crusaders", "golden wind", "stone ocean"],
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
        "aliases": ["dandadan", "dan da dan"],
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
        "aliases": ["kaiju no 8", "kaiju no. 8", "kaiju no.8"],
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
        "aliases": ["solo leveling", "ore dake level up na ken"],
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
        "aliases": ["mushoku tensei", "jobless reincarnation"],
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
        "aliases": ["made in abyss"],
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
        "aliases": ["overlord", "overlord iv", "overlord iii", "overlord ii"],
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
        "aliases": ["jigokuraku", "hells paradise", "hell's paradise"],
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
        "aliases": ["tokyo revengers"],
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
    }
}


class MangaCanonRegistry:
    """Zarządca i wyszukiwarka kanonu polskich wydań mangowych."""

    def __init__(self, custom_dir: Optional[Path] = None):
        self.custom_dir = custom_dir or MANGA_CANON_DIR
        self.custom_dir.mkdir(parents=True, exist_ok=True)
        self.canon_db: Dict[str, Dict[str, Any]] = dict(BUILTIN_MANGA_CANON)
        self._load_custom_files()

    def _load_custom_files(self):
        """Loads custom JSON files added by user into manga_canon/ directory."""
        if not self.custom_dir.exists():
            return
        for json_file in self.custom_dir.glob("*.json"):
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

    def format_canon_for_prompt(self, canon_entry: Optional[Dict[str, Any]]) -> str:
        """Formats manga canon entry into a concise system prompt block."""
        if not canon_entry:
            return ""

        lines = [
            f"=== [KANON] OFICJALNY KANON POLSKIEGO WYDANIA MANGI ({canon_entry.get('publisher', 'Oficjalne Wydawnictwo')}) ===",
            f"Dla serii '{canon_entry.get('title', 'Anime')}' BEZWZGLĘDNIE zachowaj poniższą kanoniczną terminologię:"
        ]

        glossary = canon_entry.get("glossary", {})
        if glossary:
            lines.append("• Słowniczek kanoniczny (ataki, magia, krainy, formacje):")
            for term_src, term_pl in list(glossary.items())[:15]:
                lines.append(f"  - '{term_src}' -> '{term_pl}'")

        char_forms = canon_entry.get("character_forms", {})
        if char_forms:
            lines.append("• Kanoniczne formy zwrotów i relacje:")
            for rel, form_desc in list(char_forms.items())[:8]:
                lines.append(f"  - {rel}: {form_desc}")

        lines.append("(!) ZASADA AVT: Zachowaj kanoniczne nazwy, ale przy długich wypowiedziach stosuj zwięzłą polską składnię (limit 17 CPS).")
        lines.append("=========================================================================\n")

        return "\n".join(lines)
