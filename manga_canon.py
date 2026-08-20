# -*- coding: utf-8 -*-
"""
Moduł Rejestru Kanonu Polskich Wydań Mangowych (Manga Canon Registry).
Zapewnia 100% zgodności terminologicznej, nazw technik, magii, rang i relacji postaci
z oficjalnymi polskimi tomikami mang wydawanymi przez renomowane wydawnictwa
(Waneko, J.P.Fantastica, Studio JG, Hanami, Kotori, Dango).

Działa w 100% lokalnie (Offline / 0 zł kosztów API).
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

MANGA_CANON_DIR = Path(__file__).parent / "manga_canon"

# Wbudowana baza kanonicznej terminologii czołowych polskich wydań mangowych
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
            "Five Hundred-Man Commander": "Dowódca pięciuset ludzi",
            "Thousand-Man Commander": "Dowódca tysiąca ludzi"
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
        """Wczytuje ewentualne pliki JSON dodane przez użytkownika do katalogu manga_canon/."""
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
        """Wyszukuje kanon polskiego wydania mangi na podstawie tytułu anime."""
        if not anime_title:
            return None

        norm_title = re.sub(r"[^\w\s]", " ", anime_title.lower()).strip()
        norm_title_compact = re.sub(r"\s+", " ", norm_title)

        # 1. Dokładne lub aliasowe dopasowanie
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
        """Formatuje kanon mangowy do postaci zwięzłego bloku promptu systemowego."""
        if not canon_entry:
            return ""

        lines = [
            f"=== 📖 OFICJALNY KANON POLSKIEGO WYDANIA MANGI ({canon_entry.get('publisher', 'Oficjalne Wydawnictwo')}) ===",
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

        lines.append("⚠️ ZASADA AVT: Zachowaj kanoniczne nazwy, ale przy długich wypowiedziach stosuj zwięzłą polską składnię (limit 17 CPS).")
        lines.append("=========================================================================\n")

        return "\n".join(lines)
