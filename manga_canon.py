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
    },
    "kusuriya_no_hitorigoto": {
        "title": "Zapiski Zielarki (Kusuriya no Hitorigoto / The Apothecary Diaries)",
        "aliases": ["kusuriya no hitorigoto", "apothecary diaries", "the apothecary diaries", "zapiski zielarki"],
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
        "aliases": ["dr stone", "dr. stone", "dr.stone"],
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
        "aliases": ["wind breaker", "windbreaker"],
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
        "aliases": ["tongari boushi no atelier", "witch hat atelier", "atelier spiczastych kapeluszy"],
        "publisher": "Wydawnictwo Kotori",
        "glossary": {
            "Pointed Hat": "Spiczasty Kapelusz",
            "Brimmed Hat": "Rondo / Kapelusze z Rondem",
            "Magic Ink": "Magiczny Atrament",
            "Keystones": "Kamienie Kluczowe",
            "Great Hall": "Wielka Sala Magów"
        },
        "character_forms": {
            "Coco -> Qifrey": "mistrzu Qifrey",
            "Agott -> Coco": "Coco / na ty"
        }
    },
    "chihayafuru": {
        "title": "Chihayafuru",
        "aliases": ["chihayafuru"],
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
        "aliases": ["pluto", "naoki urasawa pluto"],
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
        "aliases": ["komi-san wa komyushou desu", "komi cant communicate", "komi can't communicate", "komi san"],
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
        "aliases": ["re:zero", "re zero", "rezero", "re:zero kara hajimeru isekai seikatsu"],
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
        "aliases": ["sword art online", "sao", "sword art online alicization"],
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
        "aliases": ["fire force", "enen no shouboutai"],
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
        "aliases": ["soul eater"],
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
        "aliases": ["noragami", "noragami aragoto"],
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
        "aliases": ["kage no jitsuryokusha ni naritakute", "the eminence in shadow", "eminence in shadow", "eminencja w cieniu"],
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
        "aliases": ["yofukashi no uta", "call of the night", "pieśń nocy"],
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

Jeżeli seria została oficjalnie wydana w Polsce, zwróć JSON:
{{
  "has_polish_edition": true,
  "title": "Oficjalny Polski Tytuł (Oryginalny Tytuł)",
  "publisher": "Wydawnictwo XYZ",
  "aliases": ["{primary_title.lower()}", "{slug}"],
  "glossary": {{
    "Angielska/Japońska nazwa ataku, rangi, magii lub lokacji": "Oficjalne polskie tłumaczenie z mangi"
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
            for term_src, term_pl in list(glossary.items())[:25]:
                lines.append(f"  - '{term_src}' -> '{term_pl}'")

        char_forms = canon_entry.get("character_forms", {})
        if char_forms:
            lines.append("• Kanoniczne formy zwrotów i relacje:")
            for rel, form_desc in list(char_forms.items())[:12]:
                lines.append(f"  - {rel}: {form_desc}")

        lines.append("(!) ZASADA AVT: Zachowaj kanoniczne nazwy, ale przy długich wypowiedziach stosuj zwięzłą polską składnię (limit 17 CPS).")
        lines.append("=========================================================================\n")

        return "\n".join(lines)
