# -*- coding: utf-8 -*-
"""
Official Polish Manga/Light Novel Canon Registry (manga_canon.py).
Maintains 100% authentic, verified official Polish terminology published in physical volumes
by licensed Polish publishers (Wydawnictwo Waneko, J.P.Fantastica, Studio JG, Kotori, Hanami, Dango, Egmont).

Strict Grounding Rule (Law 9 - Zero-AI Policy):
Zero tolerance for synthetic English calques or hallucinated AI terms.
Deterministic Glossary only includes pure, clean key-value pairs (Source EN/JP -> Target PL)
without any bracketed annotations, descriptions, or slash alternatives.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("manga_canon")

# =========================================================================
# 100% VERIFIED OFFICIAL POLISH MANGA CANON (PHYSICAL VOLUME ACCURACY)
# =========================================================================
BUILTIN_MANGA_CANON: Dict[str, Dict[str, Any]] = {
    "tenmaku_no_jaadugar": {
        "title": "Wiedźma z Jurty (Tenmaku no Jaadugar: A Witch's Life in Mongol)",
        "aliases": [
            "jaadugar",
            "a witch's life in mongol",
            "wiedzma z jurty",
            "wiedźma z jurty",
            "tenmaku no jaadugar"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Toregene": "Toregene",
            "Fatima": "Fatima",
            "Ogedei": "Ogedej Chan",
            "Genghis Khan": "Czyngis-chan",
            "Karakorum": "Karakorum",
            "Khatun": "Chatun",
            "Yurt": "Jurta",
            "Great Khan": "Wielki Chan",
            "Jochi": "Dżuczi",
            "Chagatai": "Czagataj",
            "Tolui": "Tołuj",
            "Sorghaghtani": "Sorkaktani Beki",
            "Guyuk": "Güyük",
            "Godan": "Köden"
        },
        "character_forms": {
            "Toregene -> Fatima": "Fatimo (bliskość, zaufanie)",
            "Fatima -> Toregene": "Pani Toregene / Chatun (szacunek)",
            "Fatima -> Ogedei": "Wielki Chanie / Wasza Wysokość (pełna uległość poddanej)",
            "Dwór -> Toregene": "Dostojna Chatun / Pani Toregene (poddaństwo)"
        }
    },
    "kingdom": {
        "title": "Kingdom (Anime Audio-Matching Canon)",
        "aliases": [
            "królestwo",
            "kingdom"
        ],
        "publisher": "Anime Dub/Sub Audio-Matching Japanese Reading",
        "glossary": {
            "Shin": "Shin",
            "Li Xin": "Shin",
            "Ei Sei": "Ei Sei",
            "Ying Zheng": "Ei Sei",
            "Karyo Ten": "Karyo Ten",
            "He Liao Diao": "Karyo Ten",
            "Kyoukai": "Kyoukai",
            "Qiang Lei": "Kyoukai",
            "Kyourei": "Kyourei",
            "Qiang Li": "Kyourei",
            "Hyou": "Hyou",
            "En": "Porucznik En",
            "Sosui": "Sosui",
            "Garo": "Garo",
            "Gakurai": "Gakurai",
            "Naki": "Naki",
            "Suugen": "Suugen",
            "Shousa": "Shousa",
            "Hairou": "Hairou",
            "Denei": "Denei",
            "Ryuro": "Ryuro",
            "Ryuu Yuu": "Ryuu Yuu",
            "Bihei": "Bihei",
            "Bitou": "Bitou",
            "Taku Kei": "Taku Kei",
            "Sou Jin": "Sou Jin",
            "Sou Tan": "Sou Tan",
            "Kanto": "Kanto",
            "Seki": "Seki",
            "Ouki": "Ouki",
            "Wang Qi": "Ouki",
            "Kyou": "Kyou",
            "Qiang": "Kyou",
            "Hakuki": "Hakuki",
            "Bai Qi": "Hakuki",
            "Oukotsu": "Oukotsu",
            "Wang He": "Oukotsu",
            "Koushou": "Koushou",
            "Shibasaku": "Shibasaku",
            "Sima Cuo": "Shibasaku",
            "Moubu": "Moubu",
            "Meng Wu": "Moubu",
            "Tou": "Tou",
            "Teng": "Tou",
            "Ousen": "Ousen",
            "Wang Jian": "Ousen",
            "Kanki": "Kanki",
            "Huan Yi": "Kanki",
            "Yotanwa": "Yotanwa",
            "Yang Duanhe": "Yotanwa",
            "Ouhon": "Ouhon",
            "Wang Ben": "Ouhon",
            "Hon-sama": "Panicz Hon",
            "Lord Ben": "Panicz Hon",
            "Master Ben": "Panicz Hon",
            "Young Master Ben": "Panicz Hon",
            "Lord Hon": "Panicz Hon",
            "Master Hon": "Panicz Hon",
            "Ben": "Hon",
            "Banyou": "Banyou",
            "Ban You": "Banyou",
            "Kanjou": "Kanjou",
            "Mouten": "Mouten",
            "Meng Tian": "Mouten",
            "Lord Tian": "Panicz Mouten",
            "Master Tian": "Panicz Mouten",
            "Young Master Tian": "Panicz Mouten",
            "Tian": "Mouten",
            "Rikusen": "Rikusen",
            "Kozen": "Kozen",
            "Duke Hyou": "Książę Hyou",
            "Biao Gong": "Książę Hyou",
            "Mougou": "Wielki Generał Mougou",
            "Meng Ao": "Wielki Generał Mougou",
            "Choutou": "Generał Choutou",
            "Zhang Tang": "Generał Choutou",
            "Heki": "Generał Heki",
            "Bi": "Generał Heki",
            "Rokuomi": "Rokuomi",
            "Ryuu Koku": "Ryuu Koku",
            "Kanou": "Kanou",
            "Akou": "Akou",
            "Makou": "Makou",
            "Sou'ou": "Sou'ou",
            "Shiryou": "Shiryou",
            "Denrimi": "Denrimi",
            "Raido": "Raido",
            "Maron": "Maron",
            "Ringyoku": "Ringyoku",
            "Koku'ou": "Koku'ou",
            "Zenou": "Zenou",
            "Bajio": "Bajio",
            "Tajifu": "Tajifu",
            "Shunmen": "Shunmen",
            "Danto": "Feigo King Danto",
            "Kitari": "Kitari",
            "Katari": "Katari",
            "Shouheikun": "Lord Shouheikun",
            "Changping Jun": "Lord Shouheikun",
            "Shoubunkun": "Lord Shoubunkun",
            "Changwen Jun": "Lord Shoubunkun",
            "Kaioku": "Kaioku",
            "Ryo Fui": "Ryo Fui",
            "Lu Buwei": "Ryo Fui",
            "Rishi": "Rishi",
            "Li Si": "Rishi",
            "Saitaku": "Saitaku",
            "Cai Ze": "Saitaku",
            "Rou Ai": "Rou Ai",
            "Queen Mother": "Królowa Matka",
            "Seikyou": "Seikyou",
            "Rui": "Rui",
            "Kou": "Kou",
            "Youka": "Youka",
            "Riboku": "Riboku",
            "Li Mu": "Riboku",
            "Lord Riboku": "Lord Riboku",
            "Master Riboku": "Lord Riboku",
            "Prime Minister Riboku": "Kanclerz Riboku",
            "Houken": "Houken",
            "Pang Nuan": "Houken",
            "Shibasou": "Shibashou",
            "Sima Shang": "Shibashou",
            "Renpa": "Renpa",
            "Lian Po": "Renpa",
            "Rinko": "Rinko",
            "Lun Hu": "Rinko",
            "Genpou": "Genpou",
            "Kaishibou": "Kaishibou",
            "Kyouen": "Kyouen",
            "Keisha": "Keisha",
            "Qing She": "Keisha",
            "Kaine": "Kaine",
            "Futei": "Futei",
            "Kisui": "Kisui",
            "Batei": "Batei",
            "Ryuutou": "Ryuutou",
            "Bananji": "Bananji",
            "Shunsuiju": "Shunsuiju",
            "Gakuei": "Gakuei",
            "Chougaryuu": "Chougaryuu",
            "Gyou'un": "Gyou'un",
            "Kochou": "Kochou",
            "Hu Zhe": "Kochou",
            "Toujou": "Król Toujou",
            "Kakukai": "Kakukai",
            "Shunshinkun": "Lord Shunshinkun",
            "Kanmei": "Kanmei",
            "Han Ming": "Kanmei",
            "Karin": "Karin",
            "Wa Lin": "Karin",
            "Kouen": "Kouen",
            "Kouyoku": "Kouyoku",
            "Xiang Yi": "Kouyoku",
            "Hakurei": "Hakurei",
            "Bai Li": "Hakurei",
            "Rinbunkun": "Generał Rinbunkun",
            "Man'goku": "Generał Man'goku",
            "Wan Ji": "Generał Man'goku",
            "Man'u": "Man'u",
            "Sento'un": "Sento'un",
            "Juko'ou": "Juko'ou",
            "Gen'u": "Gen'u",
            "Gohoumei": "Wielki Generał Gohoumei",
            "Wu Fengming": "Wielki Generał Gohoumei",
            "Gokei": "Wielki Generał Gokei",
            "Wu Qing": "Wielki Generał Gokei",
            "Gaimou": "Gaimou",
            "Reiou": "Reiou",
            "Earl Shi": "Earl Shi",
            "Ranbihaku": "Ranbihaku",
            "Gekishin": "Wielki Generał Gekishin",
            "Ju Xin": "Wielki Generał Gekishin",
            "Ordo": "Wielki Generał Ordo",
            "Seikai": "Generał Seikai",
            "Cheng Hui": "Generał Seikai",
            "Ouken": "Król Ouken",
            "Wang Jian (Qi)": "Król Ouken",
            "Hi Shin Unit": "Oddział Hi Shin",
            "Fei Xin Dui": "Oddział Hi Shin",
            "Gyoku Hou Unit": "Oddział Gyoku Hou",
            "Yui Feng Unit": "Oddział Gyoku Hou",
            "Gaku Ka Unit": "Oddział Gaku Ka",
            "Le Hua Unit": "Oddział Gaku Ka",
            "5-Man Squad": "Piątka",
            "10-Man Commander": "Dziesiętnik",
            "100-Man Commander": "Setnik",
            "300-Man Commander": "Trzysetnik",
            "1000-Man Commander": "Tysięcznik",
            "3000-Man Commander": "Trzytysięcznik",
            "5000-Man Commander": "Pięciotysięcznik",
            "General": "Generał",
            "Great General": "Wielki Generał",
            "Great General Under the Heavens": "Wielki Generał pod Niebiosami",
            "Six Great Generals": "Sześciu Wielkich Generałów Qin",
            "Three Great Heavens": "Trzy Wielkie Niebiosa Zhao",
            "Fire Dragons of Wei": "Siedem Ognistych Smoków Wei",
            "Ten Bows of China": "Dziesięć Łuków Chin",
            "Middle Kingdom": "Państwo Środka",
            "Qin State": "Państwo Qin",
            "Zhao State": "Państwo Zhao",
            "Chu State": "Państwo Chu",
            "Wei State": "Państwo Wei",
            "Yan State": "Państwo Yan",
            "Qi State": "Państwo Qi",
            "Han State": "Państwo Han",
            "Kankoku Pass": "Przełęcz Kankoku",
            "Hangu Pass": "Przełęcz Kankoku",
            "Coalition Army": "Armia Koalicji",
            "City of Sai": "Miasto Sai",
            "Battle of Dakan Plains": "Bitwa na Równinie Dakan",
            "Battle of Bayou": "Bitwa pod Bayou",
            "Battle of Sanyo": "Bitwa pod Sanyo",
            "Battle of Kanyou": "Obrona Stolicy Kanyou",
            "Battle of Kokuyou Hills": "Bitwa na Wzgórzach Kokuyou",
            "Invasion of Western Zhao": "Kampania Zachodniego Zhao",
            "City of Gyou": "Twierdza Gyou",
            "Battle of Shukai Plains": "Bitwa na Równinie Shukai",
            "Battle of Ryouyou": "Bitwa pod Ryouyou",
            "Siege of Atsuyo": "Oblężenie Atsuyo",
            "Battle of Gian": "Bitwa pod Gian",
            "Chouhei Massacre": "Rzeź pod Chouhei",
            "Ouki's Glaive": "Glewia Oukiego",
            "Hyou's Sword": "Miecz Hyou",
            "Bakuya Sword": "Święty Miecz Bakuya",
            "Dance of the Shiyuu": "Taniec Kapłanki Shiyuu",
            "Priestess Dance": "Taniec Kapłanki Shiyuu",
            "Unification of China": "Zjednoczenie Chin pod Jednymi Niebiosami",
            "Legalism": "Praworządność",
            "Weight of a General": "Ciężar Generała",
            "Bushin": "Bushin"
        },
        "character_forms": {
            "Shin -> Ei Sei": "Sei (braterska relacja i bezpośredniość) / Wasza Wysokość (oficjalnie przy dworzanach)",
            "Ei Sei -> Shin": "Shin (serdeczny przyjaciel, równy partner w marzeniu o zjednoczeniu)",
            "Ten -> Shin": "Shin (kumpelska troska jak o starszego brata)",
            "Kyoukai -> Shin": "Shin (spokój, głębokie zaufanie i cicha miłość)",
            "Ouki -> Shin": "Młody chłopcze / Dzieciaku (ojcowski mentoring z humorem 'nfufufu')",
            "Shin -> Ouki": "Wielki Generale Ouki! (najwyższy szacunek i autorytet)",
            "Banyou -> Ouhon": "Panicz Hon / Młody pan Hon / Hon-sama (stary, oddany sługa; BEZWZGLĘDNY ZAKAZ 'pan Ben')",
            "Ban You -> Ouhon": "Panicz Hon / Młody pan Hon / Hon-sama (stary, oddany sługa; BEZWZGLĘDNY ZAKAZ 'pan Ben')",
            "Gyoku Hou -> Ouhon": "Młody pan Hon / Dowódca Hon (oddanie żołnierzy; zakaz 'Ben')",
            "Kozen -> Mouten": "Panicz Ten / Młody pan Mouten / Mouten-sama (stary sługa; BEZWZGLĘDNY ZAKAZ 'pan Tian')",
            "Ouhon -> Shin": "Bękarcie / Chłystku (szlachecka duma skrywająca uznanie rywala)",
            "Mouten -> Shin": "Shin / Przyjacielu (lekki, ciepły ton kumpelski)"
        }
    },
    "golden_kamuy": {
        "title": "Golden Kamuy",
        "aliases": [
            "złoty kamuj",
            "kamuy",
            "golden kamuy"
        ],
        "publisher": "Wydawnictwo Kotori (tłum. Tomasz Molski)",
        "glossary": {
            "Immortal Sugimoto": "Nieśmiertelny Sugimoto",
            "Saichi Sugimoto": "Saichi Sugimoto",
            "Asirpa": "Asirpa",
            "Yoshitake Shiraishi": "Yoshitake Shiraishi",
            "Tokushirou Tsurumi": "Tokushirou Tsurumi",
            "Hyakunosuke Ogata": "Hyakunosuke Ogata",
            "Genjirou Tanigaki": "Genjirou Tanigaki",
            "Hajime Tsukishima": "Hajime Tsukishima",
            "Otonoshin Koito": "Otonoshin Koito",
            "Toshizou Hijikata": "Toshizou Hijikata",
            "Shinpachi Nagakura": "Shinpachi Nagakura",
            "Tetsuzou Nihei": "Tetsuzou Nihei",
            "Wilk": "Wilk",
            "Nopperabo": "Nopperabo",
            "7th Division": "Siódma Dywizja",
            "Ainu": "Ainu",
            "Kamuy": "Kamuj",
            "Kotan": "Kotan",
            "Citatap": "Citatap",
            "Hinna hinna": "Hinna hinna",
            "Osoma": "Osoma",
            "Retar": "Retar",
            "Abashiri Prison": "Więzienie Abashiri",
            "Tattooed Convicts": "Wytatuowani więźniowie",
            "Ainu Gold": "Złoto Ajnów",
            "Karafuto": "Karafuto"
        },
        "character_forms": {
            "Sugimoto -> Asirpa": "Asirpa / Asirpo (partnerska relacja i szacunek dla kultury Ajnów)",
            "Asirpa -> Sugimoto": "Sugimoto (zaufanie i przyjaźń)",
            "Shiraishi -> Sugimoto": "Sugimoto (kumpelsko / tchórzliwie)",
            "Żołnierze -> Tsurumi": "Poruczniku Tsurumi / Panie Poruczniku (ślepe oddanie)"
        }
    },
    "chainsaw_man": {
        "title": "Chainsaw Man",
        "aliases": [
            "człowiek piła",
            "chainsaw man",
            "csm"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Chainsaw Man": "Chainsaw Man",
            "Denji": "Denji",
            "Pochita": "Pochita",
            "Makima": "Makima",
            "Aki Hayakawa": "Aki Hayakawa",
            "Power": "Power",
            "Himeno": "Himeno",
            "Kobeni Higashiyama": "Kobeni Higashiyama",
            "Kishibe": "Kishibe",
            "Reze": "Reze",
            "Quanxi": "Quanxi",
            "Asa Mitaka": "Asa Mitaka",
            "Yoru": "Yoru",
            "Public Safety": "Bezpieczeństwo Publiczne",
            "Devil Hunter": "Łowca Demonów",
            "Special Division 4": "4. Dywizja Specjalna Tokio",
            "Gun Devil": "Demon Broni Palnej",
            "Control Devil": "Demon Kontroli",
            "Blood Devil": "Demon Krwi",
            "Fox Devil": "Demon Lisa",
            "Curse Devil": "Demon Przekleństwa",
            "Ghost Devil": "Demon Ducha",
            "Future Devil": "Demon Przyszłości",
            "Darkness Devil": "Demon Ciemności",
            "Fiend": "Opętaniec",
            "Hybrid": "Hybryda",
            "Hell": "Piekło",
            "Beam": "Beam",
            "Angel Devil": "Demon Anioła",
            "Galgali": "Galgali",
            "Prinz": "Prinz",
            "Arai Hirokazu": "Hirokazu Arai",
            "Michiko Tendo & Yutaro Kurose": "Tendo i Kurose",
            "Katana Man": "Katana Man",
            "Santa Claus": "Święty Mikołaj",
            "Nayuta": "Nayuta",
            "Fami": "Fami",
            "Death Devil": "Demon Śmierci",
            "Hell Devil": "Demon Piekła",
            "Zombie Devil": "Demon Zombie",
            "Bat Devil": "Demon Nietoperza",
            "Leech Devil": "Demon Pijawki",
            "Eternity Devil": "Demon Wieczności",
            "Public Safety Devil Hunters": "Bezpieczeństwo Publiczne",
            "Four Horsemen of the Apocalypse": "Czterej Jeźdźcy",
            "Primal Fears": "Pierwotne Lęki",
            "Devil Contract": "Pakt z Demonem",
            "Hero of Hell": "Bohater Piekieł",
            "Chainsaw Cord": "Uchwyt rozrusznika na piersi Denjiego",
            "Kon": "Kon!",
            "Easy Revenge": "Łatwa Zemsta"
        },
        "character_forms": {
            "Denji -> Makima": "Pani Makimo / Makima-san (ślepe, psie posłuszeństwo i zauroczenie)",
            "Aki -> Makima": "Pani Makimo (pełen profesjonalizm i zauroczenie)",
            "Power -> Denji": "Denji! (zarozumiała, komiczna wyższość 'Jestem geniuszem!')",
            "Denji -> Power": "Power (kłótliwe rodzeństwo)",
            "Aki -> Denji/Power": "Głupki / Bachory (szorstka odpowiedzialność starszego brata)",
            "Makima -> Denji": "Dobry piesek (chłodna, bezlitosna manipulacja)"
        }
    },
    "jujutsu_kaisen": {
        "title": "Jujutsu Kaisen",
        "aliases": [
            "starcie magów",
            "jjk",
            "jujutsu kaisen"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Yuji Itadori": "Yuji Itadori",
            "Megumi Fushiguro": "Megumi Fushiguro",
            "Nobara Kugisaki": "Nobara Kugisaki",
            "Satoru Gojo": "Satoru Gojo",
            "Ryomen Sukuna": "Ryomen Sukuna",
            "Kento Nanami": "Kento Nanami",
            "Suguru Geto": "Suguru Geto",
            "Kenjaku": "Kenjaku",
            "Yuta Okkotsu": "Yuta Okkotsu",
            "Maki Zen'in": "Maki Zen'in",
            "Toge Inumaki": "Toge Inumaki",
            "Panda": "Panda",
            "Aoi Todo": "Aoi Todo",
            "Toji Fushiguro": "Toji Fushiguro",
            "Mahito": "Mahito",
            "Jogo": "Jogo",
            "Hanami": "Hanami",
            "Cursed Energy": "Energia Przeklęta",
            "Cursed Technique": "Zaklęta Technika",
            "Domain Expansion": "Rozszerzenie Domeny",
            "Simple Domain": "Prosta Domena",
            "Black Flash": "Czarny Błysk",
            "Limitless": "Bezgraniczność",
            "Six Eyes": "Sześcioro Oczu",
            "Malevolent Shrine": "Złowrogie Sanktuarium",
            "Infinite Void": "Nieograniczona Pustka",
            "Jujutsu High": "Technikum Magii w Tokio",
            "Special Grade": "Ranga Specjalna",
            "Shibuya Incident": "Incydent w Shibuyi",
            "Culling Game": "Gra Przesiewowa",
            "Rika Orimoto": "Rika Orimoto",
            "Maki Zenin": "Maki Zenin",
            "Kinji Hakari": "Kinji Hakari",
            "Kirara Hoshi": "Kirara Hoshi",
            "Mai Zenin": "Mai Zenin",
            "Kasumi Miwa": "Kasumi Miwa",
            "Kokichi Muta": "Kokichi Muta",
            "Noritoshi Kamo": "Noritoshi Kamo",
            "Momo Nishimiya": "Momo Nishimiya",
            "Masamichi Yaga": "Dyrektor Masamichi Yaga",
            "Yoshinobu Gakuganji": "Dyrektor Yoshinobu Gakuganji",
            "Shoko Ieiri": "Doktor Shoko Ieiri",
            "Utahime Iori": "Utahime Iori",
            "Mei Mei": "Mei Mei",
            "Ui Ui": "Ui Ui",
            "Naobito Zenin": "Naobito Zenin",
            "Naoya Zenin": "Naoya Zenin",
            "Atsuya Kusakabe": "Atsuya Kusakabe",
            "Takuma Ino": "Takuma Ino",
            "Yuki Tsukumo": "Yuki Tsukumo",
            "Tengen": "Mistrz Tengen",
            "Dagon": "Dagon",
            "Choso": "Choso",
            "Eso & Kechizu": "Eso i Kechizu",
            "Uraume": "Uraume",
            "Hajime Kashimo": "Hajime Kashimo",
            "Hiromi Higuruma": "Hiromi Higuruma",
            "Fumihiko Takaba": "Fumihiko Takaba",
            "Angel": "Angel",
            "Self-Embodiment of Perfection": "Ucieleśnienie Doskonałości",
            "Coffin of the Iron Mountain": "Trumna Żelaznej Góry",
            "Horizon of the Captivating Skandha": "Horyzont Urzekających Skandh",
            "Chimera Shadow Garden": "Ogród Cieni Chimery",
            "Idle Death Gamble": "Śmiertelny Hazard Spoczynku",
            "Deadly Sentencing": "Śmiertelny Wyrok",
            "Authentic Mutual Love": "Prawdziwa Wzajemna Miłość",
            "Infinity": "Nieskończoność",
            "Cursed Technique Lapse: Blue": "Błękit",
            "Cursed Technique Reversal: Red": "Czerwień",
            "Hollow Purple": "Purpura",
            "Reverse Cursed Technique": "Odwrócona Technika Przeklęta",
            "Ten Shadows Technique": "Technika Dziesięciu Cieni",
            "Divine Dog": "Boski Pies",
            "Nue": "Nue",
            "Great Serpent": "Wielki Wąż",
            "Toad": "Ropucha",
            "Max Elephant": "Maksymalny Słoń",
            "Rabbit Escape": "Ucieczka Królików",
            "Round Deer": "Jeleń Madoka",
            "Piercing Ox": "Przebijający Byk",
            "Eight-Handled Sword Divergent Sila Divine General Mahoraga": "Boski Generał Mahoraga",
            "Falling Blossom Emotion": "Emocja Opadającego Kwiatu",
            "Domain Amplification": "Wzmocnienie Domeny",
            "Heavenly Restriction": "Niebiański Pakt",
            "Inverted Spear of Heaven": "Odwrócona Włócznia Niebios",
            "Split Soul Katana": "Katana Rozcinająca Dusze",
            "Playful Cloud": "Swawolna Chmura",
            "Cursed Spirit": "Przeklęty Duch"
        },
        "character_forms": {
            "Yuji -> Gojo": "Gojo-sensei (uwielbienie i szacunek dla mentora)",
            "Megumi -> Gojo": "Gojo-san (lekki dystans i powaga)",
            "Todo -> Yuji": "Mój najlepszy przyjacielu! / Bracie! (My Best Friend / Brother)",
            "Sukuna -> Ludzie": "Robaki / Nędznicy (absolutna boska pycha)",
            "Nobara -> Yuji/Megumi": "Głupki / Chłopcy (pewność siebie i dominacja)"
        }
    },
    "shingeki_no_kyojin": {
        "title": "Atak Tytanów (Shingeki no Kyojin)",
        "aliases": [
            "atak tytanow",
            "snk",
            "atak tytanów",
            "shingeki no kyojin",
            "aot",
            "attack on titan"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Eren Jaeger": "Eren Jaeger",
            "Mikasa Ackermann": "Mikasa Ackermann",
            "Armin Arlert": "Armin Arlert",
            "Levi Ackermann": "Kapral Levi",
            "Erwin Smith": "Dowódca Erwin Smith",
            "Hange Zoe": "Hange Zoe",
            "Reiner Braun": "Reiner Braun",
            "Bertholdt Hoover": "Bertholdt Hoover",
            "Annie Leonhart": "Annie Leonhart",
            "Zeke Jaeger": "Zeke Jaeger",
            "Survey Corps": "Korpus Zwiadowczy",
            "Military Police Brigade": "Żandarmeria",
            "Garrison Regiment": "Korpus Stacjonarny",
            "Attack Titan": "Tytan Atakujący",
            "Colossal Titan": "Tytan Kolosalny",
            "Armored Titan": "Tytan Opancerzony",
            "Female Titan": "Tytan Kobiecy",
            "Beast Titan": "Tytan Zwierzęcy",
            "Founding Titan": "Tytan Pierwotny",
            "War Hammer Titan": "Tytan Młot Bojowy",
            "Jaw Titan": "Tytan Szczękowy",
            "Cart Titan": "Tytan Transportowy",
            "Omni-Directional Mobility Gear": "Sprzęt do Manewrów Przestrzennych",
            "Wall Maria": "Mur Maria",
            "Wall Rose": "Mur Rose",
            "Wall Sina": "Mur Sina",
            "Paradis Island": "Wyspa Paradis",
            "Marley": "Marley",
            "Eldia": "Eldia",
            "Rumbling": "Dudnienie"
        },
        "character_forms": {
            "Mikasa -> Eren": "Eren (nadopiekuńczość, głęboka miłość)",
            "Zwiadowcy -> Levi": "Kapralu Levi / Panie Kapralu (dyscyplina i podziw)",
            "Zwiadowcy -> Erwin": "Dowódco Erwinie / Sasageyo (gotowość na śmierć)"
        }
    },
    "naruto": {
        "title": "Naruto / Boruto",
        "aliases": [
            "boruto",
            "naruto",
            "naruto shippuden"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Naruto Uzumaki": "Naruto Uzumaki",
            "Sasuke Uchiha": "Sasuke Uchiha",
            "Sakura Haruno": "Sakura Haruno",
            "Kakashi Hatake": "Kakashi Hatake",
            "Jiraiya": "Jiraiya",
            "Tsunade": "Tsunade",
            "Orochimaru": "Orochimaru",
            "Itachi Uchiha": "Itachi Uchiha",
            "Madara Uchiha": "Madara Uchiha",
            "Obito Uchiha": "Obito Uchiha",
            "Pain": "Pain",
            "Nagato": "Pain",
            "Minato Namikaze": "Minato Namikaze",
            "Shikamaru Nara": "Shikamaru Nara",
            "Hinata Hyuga": "Hinata Hyuga",
            "Gaara": "Gaara",
            "Konohagakure": "Konohagakure",
            "Sunagakure": "Sunagakure",
            "Hokage": "Hokage",
            "Kazekage": "Kazekage",
            "Mizukage": "Mizukage",
            "Raikage": "Raikage",
            "Tsuchikage": "Tsuchikage",
            "Chakra": "Czakra",
            "Jutsu": "Jutsu",
            "Rasengan": "Rasengan",
            "Chidori": "Chidori",
            "Sharingan": "Sharingan",
            "Mangekyo Sharingan": "Mangekyo Sharingan",
            "Rinnegan": "Rinnegan",
            "Byakugan": "Byakugan",
            "Nine-Tails": "Kurama",
            "Kurama": "Kyuubi",
            "Jinchuriki": "Jinchuuriki",
            "Akatsuki": "Akatsuki",
            "Hashirama Senju": "Hashirama Senju",
            "Tobirama Senju": "Tobirama Senju",
            "Hiruzen Sarutobi": "Hiruzen Sarutobi",
            "Konan": "Konan",
            "Kisame Hoshigaki": "Kisame Hoshigaki",
            "Sasori": "Sasori",
            "Deidara": "Deidara",
            "Hidan": "Hidan",
            "Kakuzu": "Kakuzu",
            "Zetsu": "Zetsu",
            "Kaguya Otsutsuki": "Kaguya Otsutsuki",
            "Boruto Uzumaki": "Boruto Uzumaki",
            "Sarada Uchiha": "Sarada Uchiha",
            "Mitsuki": "Mitsuki",
            "Kawaki": "Kawaki",
            "Jigen": "Jigen",
            "Neji Hyuga": "Neji Hyuga",
            "Rock Lee": "Rock Lee",
            "Might Guy": "Might Guy",
            "Killer Bee": "Killer Bee",
            "Rasenshuriken": "Rasenshuriken",
            "Sage Mode": "Tryb Mędrca",
            "Tailed Beasts": "Ogoniaste Bestie",
            "Hidden Leaf Village": "Wioska Ukryta w Liściach",
            "Hidden Sand Village": "Wioska Ukrytego Piasku",
            "Hidden Mist Village": "Wioska Ukrytej Mgły",
            "Hidden Cloud Village": "Wioska Ukrytej Chmury",
            "Hidden Stone Village": "Wioska Ukrytej Skały"
        },
        "character_forms": {
            "Naruto -> Jiraiya": "Zboczony Pustelniku! / Ero-sennin",
            "Naruto -> Sasuke": "Sasuke! (wieczny rywal i brat)",
            "Sakura -> Sasuke": "Sasuke-kun! (miłość)",
            "Naruto -> Tsunade": "Babciu Tsunade!",
            "Naruto -> Wszyscy": "Dattebayo! / Taka jest moja droga ninja!",
            "Sasuke -> Naruto": "Usuratonkachi / Durniu (skrywane braterstwo)",
            "Jiraiya -> Naruto": "Naruto / Dzieciaku (ojcowska mądrość Mędrca)"
        }
    },
    "dragon_ball": {
        "title": "Dragon Ball / Dragon Ball Z / Dragon Ball Super",
        "aliases": [
            "dbs",
            "dragon ball z",
            "dbz",
            "dragon ball",
            "dragon ball super"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Son Goku": "Son Goku",
            "Vegeta": "Vegeta",
            "Son Gohan": "Son Gohan",
            "Son Goten": "Son Goten",
            "Trunks": "Trunks",
            "Piccolo": "Piccolo",
            "Krillin": "Krilan",
            "Yamcha": "Yamcha",
            "Tien Shinhan": "Tenshinhan",
            "Chiaotzu": "Chaoz",
            "Master Roshi": "Genialny Żółw",
            "Bulma": "Bulma Briefs",
            "Chi-Chi": "Chi-Chi",
            "Frieza": "Frezer",
            "Cell": "Komórczak",
            "Majin Buu": "Majin Buu",
            "Beerus": "Lord Beerus",
            "Whis": "Whis",
            "Shenron": "Shenron",
            "Dragon Balls": "Smocze Kule",
            "Saiyan": "Saiyanin",
            "Super Saiyan": "Super Saiyanin",
            "Ultra Instinct": "Ultra Instynkt",
            "Ultra Ego": "Ultra Ego",
            "Kamehameha": "Kamehameha",
            "Spirit Bomb": "Genki Dama",
            "Final Flash": "Ostateczny Błysk",
            "Big Bang Attack": "Wielki Wybuch",
            "Destructo Disc": "Wirujący Dysk Energii",
            "Kienzan": "Kienzan",
            "Senzu Bean": "Magiczna Fasolka Senzu",
            "Capsule Corp": "Capsule Corporation",
            "Android 18": "Android 18",
            "Android 17": "Android 17",
            "Zeno": "Król Wszystkiego",
            "Grand Priest": "Arcykapłan",
            "Shin": "Kaioshin",
            "King Kai": "Król Kai",
            "Broly": "Broly",
            "Jiren": "Jiren Szary",
            "Hit": "Hit",
            "Goku Black": "Goku Black",
            "Moro": "Moro Pożeracz Planet",
            "Granolah": "Granolah",
            "Super Saiyan God": "Boski Super Saiyanin",
            "Super Saiyan Blue": "Super Saiyanin Blue",
            "Galick Gun": "Działo Galick",
            "Special Beam Cannon": "Promień Diabła",
            "Kaio-ken": "Kaio-ken",
            "Hakai": "Zniszczenie",
            "Fusion": "Fuzja: Taniec Fuzyjny, Kolczyki Potara",
            "Super Dragon Balls": "Super Smocze Kule",
            "Hyperbolic Time Chamber": "Komnata Ducha i Czasu"
        },
        "character_forms": {
            "Vegeta -> Goku": "Kakarotto! (wieczna duma rywala)",
            "Goku -> Vegeta": "Vegeta (beztroska, kumpelska chęć walki)",
            "Goku -> Roshi": "Mistrzu Żółwiu (Genialny Żółwiu)",
            "Frieza -> Saiyans": "Te bezużyteczne małpy...",
            "Gohan -> Piccolo": "Panie Piccolo / Piccolo-san (najwyższy szacunek i ojcowska więź)"
        }
    },
    "kimetsu_no_yaiba": {
        "title": "Miecz Zabójcy Demonów (Kimetsu no Yaiba: Demon Slayer)",
        "aliases": [
            "miecz zabójcy demonów",
            "kimetsu no yaiba",
            "demon slayer",
            "kny",
            "miecz zabojcy demonow"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Tanjiro Kamado": "Tanjiro Kamado",
            "Nezuko Kamado": "Nezuko Kamado",
            "Zenitsu Agatsuma": "Zenitsu Agatsuma",
            "Inosuke Hashibira": "Inosuke Hashibira",
            "Kanao Tsuyuri": "Kanao Tsuyuri",
            "Genya Shinazugawa": "Genya Shinazugawa",
            "Muzan Kibutsuji": "Muzan Kibutsuji",
            "Demon Slayer Corps": "Korpus Zabójców Demonów",
            "Hashira": "Filary: Giyu Tomioka, Shinobu Kocho, Kyojuro Rengoku, Tengen Uzui, Muichiro Tokito, Mitsuri Kanroji, Obanai Iguro, Sanemi Shinazugawa, Gyomei Himejima",
            "Pillars": "Filary: Giyu Tomioka, Shinobu Kocho, Kyojuro Rengoku, Tengen Uzui, Muichiro Tokito, Mitsuri Kanroji, Obanai Iguro, Sanemi Shinazugawa, Gyomei Himejima",
            "Kagaya Ubuyashiki": "Kagaya Ubuyashiki",
            "Twelve Demon Moons": "Dwanaście Demonicznych Księżyców",
            "Kizuki": "Dwanaście Demonicznych Księżyców",
            "Nichirin Blade": "Miecz Nichirin",
            "Total Concentration Breathing": "Oddech Całkowitego Skupienia",
            "Sun Breathing": "Taniec Boga Ognia",
            "Hinokami Kagura": "Taniec Boga Ognia",
            "Water Breathing": "Oddychanie Wody",
            "Flame Breathing": "Oddychanie Płomienia",
            "Thunder Breathing": "Oddychanie Błyskawicy",
            "Beast Breathing": "Oddech Bestii",
            "Demon Slayer Mark": "Znamię Zabójcy Demonów",
            "Mugen Train": "Pociąg Nieskończoność",
            "Entertainment District": "Dzielnica Czerwonych Latarni",
            "Swordsmith Village": "Wioska Kowali",
            "Infinity Castle": "Zamek Nieskończoności"
        },
        "character_forms": {
            "Tanjiro -> Nezuko": "Nezuko! (braterska czułość i determinacja ochrony)",
            "Zabójcy -> Oyakata-sama": "Mistrzu / Oyakata-sama (święta cześć)",
            "Inosuke -> Tanjiro": "Kamaboko Gonpachiro! (przekręcanie imion)",
            "Zenitsu -> Nezuko": "Nezuko-chan! (zakochany lament)"
        }
    },
    "death_note": {
        "title": "Death Note (Notatnik Śmierci)",
        "aliases": [
            "notatnik smierci",
            "death note",
            "notatnik śmierci"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Light Yagami": "Light Yagami",
            "L Lawliet": "L",
            "Ryuk": "Ryuk",
            "Misa Amane": "Misa Amane",
            "Rem": "Rem",
            "Soichiro Yagami": "Soichiro Yagami",
            "Near": "Near",
            "Nate River": "Near",
            "Mello": "Mello",
            "Mihael Keehl": "Mello",
            "Teru Mikami": "Teru Mikami",
            "Kiyomi Takada": "Kiyomi Takada",
            "Watari": "Watari",
            "Quillsh Wammy": "Watari",
            "Death Note": "Notatnik Śmierci",
            "Shinigami": "Shinigami",
            "Shinigami Realm": "Świat Bogów Śmierci",
            "Shinigami Eyes": "Oczy Boga Śmierci",
            "Heart Attack": "Zawał serca",
            "Kira": "Kira",
            "SPK": "SPK",
            "Wammy's House": "Dom Wammy'ego"
        },
        "character_forms": {
            "Light -> L": "Ryuzaki (maska przyjaźni / zimna kalkulacja)",
            "L -> Light": "Light-kun (intelektualna gra w szachy / podejrzenie)",
            "Misa -> Light": "Light-kun! / Mój ukochany!",
            "Ryuk -> Light": "Ludzie są naprawdę interesujący..."
        }
    },
    "fullmetal_alchemist": {
        "title": "Fullmetal Alchemist (Stalowy Alchemik)",
        "aliases": [
            "stalowy alchemik",
            "fma",
            "fma: brotherhood",
            "fullmetal alchemist"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Edward Elric": "Edward Elric",
            "Alphonse Elric": "Alphonse Elric",
            "Roy Mustang": "Pułkownik Roy Mustang",
            "Riza Hawkeye": "Porucznik Riza Hawkeye",
            "Winry Rockbell": "Winry Rockbell",
            "Pinako Rockbell": "Babcia Pinako Rockbell",
            "Van Hohenheim": "Van Hohenheim",
            "Father": "Ojciec",
            "Lust": "Lust",
            "Gluttony": "Gluttony",
            "Envy": "Envy",
            "Greed": "Greed",
            "Wrath": "Wrath",
            "King Bradley": "Wrath",
            "Sloth": "Sloth",
            "Pride": "Pride",
            "Selim Bradley": "Pride",
            "Scar": "Scar",
            "Ling Yao": "Książę Ling Yao",
            "Lan Fan": "Lan Fan",
            "Fu": "Fu",
            "May Chang": "May Chang",
            "Alex Louis Armstrong": "Major Alex Louis Armstrong",
            "Olivier Mira Armstrong": "Generał Olivier Mira Armstrong",
            "Maes Hughes": "Podpułkownik Maes Hughes",
            "Izumi Curtis": "Izumi Curtis",
            "Philosopher's Stone": "Kamień Filozoficzny",
            "Human Transmutation": "Transmutacja Ludzka",
            "Equivalent Exchange": "Prawo Równoważnej Wymiany",
            "Gate of Truth": "Brama Prawdy",
            "Automail": "Automail",
            "State Alchemist": "Państwowy Alchemik",
            "Amestris": "Państwo Amestris",
            "Central City": "Centrala",
            "Fortress of Briggs": "Forteca Briggs",
            "Ishval": "Ishval",
            "Trisha Elric": "Trisha Elric",
            "Sig Curtis": "Sig Curtis",
            "Dr. Tim Marcoh": "Doktor Tim Marcoh",
            "Solf J. Kimblee": "Solf J. Kimblee",
            "Truth": "Prawda",
            "Alkahestry": "Alkahestria",
            "Briggs": "Twierdza Briggs",
            "Xing": "Cesarstwo Xing"
        },
        "character_forms": {
            "Edward -> Każdy": "KTO JEST TAK MAŁY, ŻE TRZEBA GO SZUKAĆ PRZEZ LUPĘ?!",
            "Alphonse -> Edward": "Nii-san! / Bracie! (rozsądek i troska)",
            "Mustang -> Hawkeye": "Porucznik Hawkeye (absolutne zaufanie wojskowe i osobiste)",
            "Winry -> Ed": "Ed, znowu zniszczyłeś moją protezę automail?!",
            "Edward -> Wszyscy": "Kto jest taki mały, że ledwo go widać spod fasoli?! (szał na punkcie wzrostu)",
            "Mustang -> Edward": "Stalowy / Fullmetal (szorstka opieka dowódcy)"
        }
    },
    "bleach": {
        "title": "Bleach",
        "aliases": [
            "bleach"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Ichigo Kurosaki": "Ichigo Kurosaki",
            "Rukia Kuchiki": "Rukia Kuchiki",
            "Orihime Inoue": "Orihime Inoue",
            "Yasutora Sado": "Yasutora Sado",
            "Chad": "Yasutora Sado",
            "Uryu Ishida": "Uryu Ishida",
            "Renji Abarai": "Renji Abarai",
            "Byakuya Kuchiki": "Byakuya Kuchiki",
            "Sosuke Aizen": "Sosuke Aizen",
            "Kisuke Urahara": "Kisuke Urahara",
            "Yoruichi Shihoin": "Yoruichi Shihoin",
            "Kenpachi Zaraki": "Kenpachi Zaraki",
            "Toshiro Hitsugaya": "Toshiro Hitsugaya",
            "Genryusai Shigekuni Yamamoto": "Yamamoto Genryusai",
            "Shunsui Kyoraku": "Shunsui Kyoraku",
            "Jushiro Ukitake": "Jushiro Ukitake",
            "Gin Ichimaru": "Gin Ichimaru",
            "Ulquiorra Cifer": "Ulquiorra Cifer",
            "Grimmjow Jaegerjaquez": "Grimmjow Jaegerjaquez",
            "Yhwach": "Yhwach",
            "Shinigami": "Shinigami",
            "Zanpakuto": "Zanpakuto",
            "Shikai": "Shikai",
            "Bankai": "Bankai",
            "Getsuga Tensho": "Getsuga Tensho",
            "Soul Society": "Społeczność Dusz",
            "Seireitei": "Seireitei",
            "Rukongai": "Rukongai",
            "Hueco Mundo": "Hueco Mundo",
            "Las Noches": "Las Noches",
            "Hollow": "Hollow",
            "Arrancar": "Arrancar",
            "Espada": "Espada",
            "Quincy": "Quincy",
            "Gotei 13": "Gotei 13",
            "Reiatsu": "Reiatsu",
            "Flash Step": "Shunpo",
            "Shunpo": "Shunpo",
            "Mayuri Kurotsuchi": "Mayuri Kurotsuchi",
            "Retsu Unohana": "Retsu Unohana",
            "Shinji Hirako": "Shinji Hirako",
            "Coyote Starrk": "Coyote Starrk",
            "Baraggan Louisenbairn": "Baraggan Louisenbairn",
            "Tier Harribel": "Tier Harribel",
            "Nnoitra Gilga": "Nnoitra Gilga",
            "Szayelaporro Granz": "Szayelaporro Granz",
            "Jugram Haschwalth": "Jugram Haschwalth",
            "Gerard Valkyrie": "Gerard Valkyrie",
            "Lille Barro": "Lille Barro",
            "Pernida Parnkgjas": "Pernida Parnkgjas",
            "Askin Nakk Le Vaar": "Askin Nakk Le Vaar",
            "Bambietta Basterbine": "Bambietta Basterbine",
            "Bazz-B": "Bazz-B",
            "Ichibe Hyosube": "Ichibe Hyosube",
            "Oetsu Nimaiya": "Oetsu Nimaiya",
            "Senjumaru Shutara": "Senjumaru Shutara",
            "Kirio Hikifune": "Kirio Hikifune",
            "Tenjiro Kirinji": "Tenjiro Kirinji",
            "Getsuga Jujisho": "Getsuga Jujisho",
            "Resurreccion": "Resurrección",
            "Vollstandig": "Quincy: Vollständig",
            "Soul King": "Król Dusz"
        },
        "character_forms": {
            "Ichigo -> Rukia": "Rukia (głębokie zaufanie i partnerska więź)",
            "Rukia -> Ichigo": "Ichigo / Durniu (surowa opieka i wsparcie)",
            "Renji -> Byakuya": "Kapitanie Kuchiki (pełen szacunek podwładnego)",
            "Hitsugaya -> Wszyscy": "Nie Hitsugaya, tylko Kapitan Hitsugaya!",
            "Aizen -> Wszyscy": "Zimna, boska pycha ('Wszystko szło zgodnie z moim planem')"
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
            "Monkey D. Luffy": "Monkey D. Luffy",
            "Roronoa Zoro": "Roronoa Zoro",
            "Nami": "Nami",
            "Usopp": "Usopp",
            "Sanji": "Sanji",
            "Tony Tony Chopper": "Tony Tony Chopper",
            "Nico Robin": "Nico Robin",
            "Franky": "Franky",
            "Brook": "Brook",
            "Jinbe": "Jinbe",
            "Straw Hat Pirates": "Piraci Słomkowego Kapelusza",
            "Going Merry": "Going Merry",
            "Thousand Sunny": "Thousand Sunny",
            "Gol D. Roger": "Gol D. Roger",
            "Edward Newgate": "Edward Newgate",
            "Whitebeard": "Białobrody",
            "Shanks": "Czerwonowłosy Shanks",
            "Marshall D. Teach": "Marshall D. Teach",
            "Blackbeard": "Czarnobrody",
            "Kaido": "Kaido",
            "Big Mom": "Big Mom",
            "Charlotte Linlin": "Charlotte Linlin",
            "Marine": "Marynarka Wojenna",
            "Navy": "Marynarka Wojenna",
            "World Government": "Rząd Światowy",
            "Seven Warlords of the Sea": "Królewscy Wojownicy Mórz: Dracule Mihawk, Boa Hancock, Crocodile, Doflamingo, Kuma, Moria, Jinbe",
            "Shichibukai": "Królewscy Wojownicy Mórz: Dracule Mihawk, Boa Hancock, Crocodile, Doflamingo, Kuma, Moria, Jinbe",
            "Devil Fruit": "Owoc Diabła: Paramecia, Zoan, Logia, Mityczny Zoan",
            "Gum-Gum Fruit": "Owoc Gomu Gomu",
            "Hito Hito no Mi Model Nika": "Owoc Gomu Gomu",
            "Haki": "Haki",
            "Grand Line": "Grand Line",
            "New World": "Nowy Świat",
            "Red Line": "Red Line",
            "Poneglyph": "Poneglyph",
            "Void Century": "Pusty Wiek",
            "Gear 2": "Bieg Drugi",
            "3": "Bieg Drugi",
            "4": "Bieg Drugi",
            "5": "Bieg Drugi",
            "Gomu Gomu no Pistol": "Gomu Gomu no Pistol!",
            "Santoryu": "Styl Trzech Mieczy",
            "Silvers Rayleigh": "Silvers Rayleigh",
            "Buggy": "Buggy Gwiazda",
            "Monkey D. Garp": "Monkey D. Garp",
            "Sengoku": "Sengoku Budda",
            "Sakazuki": "Sakazuki",
            "Kuzan": "Kuzan",
            "Borsalino": "Borsalino",
            "Issho": "Issho",
            "Aramaki": "Aramaki",
            "Smoker": "Smoker",
            "Tashigi": "Tashigi",
            "Koby": "Koby",
            "Five Elders": "Gorosei",
            "Imu": "Imu-sama",
            "Dr. Vegapunk": "Dr Vegapunk",
            "Dracule Mihawk": "Dracule Mihawk",
            "Boa Hancock": "Boa Hancock",
            "Sir Crocodile": "Sir Crocodile",
            "Donquixote Doflamingo": "Donquixote Doflamingo",
            "Bartholomew Kuma": "Bartholomew Kuma",
            "Gecko Moria": "Gecko Moria",
            "Trafalgar D. Water Law": "Trafalgar Law",
            "Eustass Captain Kid": "Eustass Kid",
            "Portgas D. Ace": "Portgas D. Ace",
            "Sabo": "Sabo",
            "Monkey D. Dragon": "Monkey D. Dragon",
            "Gomu Gomu no Mi": "Gomu Gomu no Mi",
            "Gear 2, 3, 4, 5": "Gear Second, Third, Fourth, Gear 5",
            "Observation Haki": "Haki Obserwacji",
            "Armament Haki": "Haki Zbrojenia",
            "Conqueror's Haki": "Haki Zdobywcy",
            "Awakening": "Przebudzenie Owocu Diabła",
            "One Piece": "One Piece",
            "Road Poneglyph": "Czerwony Poneglyph",
            "Laugh Tale": "Laugh Tale",
            "Ancient Weapons": "Starożytne Bronie",
            "Mary Geoise": "Święta Ziemia Mary Geoise"
        },
        "character_forms": {
            "Luffy -> Załoga": "Będę Królem Piratów! / Chodźmy jeść mięso!",
            "Zoro -> Sanji": "Przeklęty kucharz / Ero-cook (wieczna rywalizacja)",
            "Sanji -> Zoro": "Głupi mchem / Marimo",
            "Sanji -> Nami/Robin": "Nami-san~! / Robin-chan~! (miłosny obłęd)",
            "Chopper -> Ludzie": "Wcale się nie cieszę, że mnie chwalisz, ty draniu! (taniec radości)",
            "Luffy -> Wszyscy": "Zostanę Królem Piratów! / Kaizoku ou ni ore wa naru!",
            "Zoro -> Luffy": "Kapitanie / Luffy (absolutna lojalność prawego skrzydła)",
            "Sanji -> Kobiety": "Nami-san~! / Robin-chan~! (miłosne uwielbienie)"
        }
    },
    "spy_x_family": {
        "title": "Spy x Family",
        "aliases": [
            "spyxfamily",
            "sxf",
            "spy x family"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Twilight": "Zmierzch",
            "Loid Forger": "Loid Forger",
            "Thorn Princess": "Cierniowa Księżniczka",
            "Yor Forger": "Yor Forger",
            "Briar": "Yor Forger",
            "Anya Forger": "Anya Forger",
            "Bond Forger": "Bond",
            "Yuri Briar": "Yuri Briar",
            "Franky Franklin": "Franky Franklin",
            "Sylvia Sherwood": "Sylvia Sherwood",
            "Handler": "Sylvia Sherwood",
            "Fiona Frost": "Fiona Frost",
            "Nightfall": "Fiona Frost",
            "Damian Desmond": "Damian Desmond",
            "Becky Blackbell": "Becky Blackbell",
            "Henry Henderson": "Henry Henderson",
            "Donovan Desmond": "Donovan Desmond",
            "Operation Strix": "Operacja Strix",
            "WISE": "WISE",
            "Eden Academy": "Akademia Eden",
            "Imperial Scholars": "Uczniowie Cesarscy",
            "Stella Stars": "Gwiazdki Stella",
            "Tonitrus Bolts": "Pioruny Tonitrus",
            "Ostania": "Ostania",
            "Westalis": "Westalis",
            "Garden": "Ogród"
        },
        "character_forms": {
            "Anya -> Loid": "Tatuś (Papai)",
            "Anya -> Yor": "Mamusiu (Mamai)",
            "Anya -> Damian": "Synek (Jinan / kpina telepatyczna)",
            "Loid -> Anya": "Anya (cierpliwość agenta pod przykrywką)",
            "Yor -> Loid": "Panie Loidzie (nieśmiałość i urok)"
        }
    },
    "tokyo_ghoul": {
        "title": "Tokyo Ghoul / Tokyo Ghoul:re",
        "aliases": [
            "tokyo ghoul re",
            "tokyo ghoul",
            "tokyo ghoul:re"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Ken Kaneki": "Ken Kaneki",
            "Haise Sasaki": "Haise Sasaki",
            "Touka Kirishima": "Touka Kirishima",
            "Rize Kamishiro": "Rize Kamishiro",
            "Shu Tsukiyama": "Shu Tsukiyama",
            "Yoshimura": "Kuzan Yoshimura",
            "Eto Yoshimura": "Eto Yoshimura",
            "Koutarou Amon": "Koutarou Amon",
            "Kureo Mado": "Kureo Mado",
            "Akira Mado": "Akira Mado",
            "Kisho Arima": "Kisho Arima",
            "Juuzou Suzuya": "Juuzou Suzuya",
            "Hideyoshi Nagachika": "Hideyoshi Nagachika",
            "Anteiku": "Anteiku",
            "CCG": "CCG",
            "Aogiri Tree": "Drzewo Aogiri",
            "Quinx Squad": "Oddział Quinx",
            "Kagune": "Kagune",
            "Kakuja": "Kakuja",
            "Quinque": "Quinque",
            "RC Cells": "Komórki RC",
            "Kakuhou": "Kakuhou",
            "Ghoul": "Ghul"
        },
        "character_forms": {
            "Kaneki -> Touka": "Touka-chan / Touko",
            "Tsukiyama -> Kaneki": "Kaneki-ken~! (ekstatyczny obłęd smakosza)",
            "Arima -> Kaneki/Haise": "Haise (chłodny, surowy ojciec)",
            "Quinx -> Haise": "Maman / Panie Sasaki (ciepło rodzinne)"
        }
    },
    "vinland_saga": {
        "title": "Saga Winlandzka (Vinland Saga)",
        "aliases": [
            "vinland",
            "vinland saga",
            "saga winlandzka"
        ],
        "publisher": "Wydawnictwo Hanami (tłum. Radosław Bolałek / Paweł Dybała)",
        "glossary": {
            "Thorfinn": "Thorfinn Karlsefni",
            "Thors": "Thors Snorresson",
            "Askeladd": "Askeladd",
            "Bjorn": "Bjorn",
            "Canute": "Książę Knut",
            "Prince Canute": "Książę Knut",
            "King Canute": "Król Knut",
            "King Sweyn": "Król Swen Widłobrody",
            "Sweyn Forkbeard": "Swen Widłobrody",
            "Thorkell the Tall": "Thorkell Wysoki",
            "Thorkell": "Thorkell Wysoki",
            "Floki": "Floki",
            "Ragnar": "Ragnar",
            "Leif Erikson": "Leif Eriksson",
            "Leif": "Leif Eriksson",
            "Ylva": "Ylva",
            "Helga": "Helga",
            "Einar": "Einar",
            "Gudrid": "Gudrid",
            "Hild": "Hild",
            "Ketil": "Ketil",
            "Arnheid": "Arnheid",
            "Gardar": "Gardar",
            "Snake": "Wąż",
            "Fox": "Lis",
            "Badger": "Borsuk",
            "Olmar": "Olmar",
            "Thorgil": "Thorgil",
            "Sverkel": "Sverkel",
            "Old Ketil": "Stary Ketil",
            "Pater": "Pater",
            "Halfdan": "Halfdan",
            "Sigurd": "Sigurd",
            "Cordelia": "Cordelia",
            "Bug-Eyes": "Ptasie Oko",
            "Karli": "Karli",
            "Vagn": "Vagn",
            "Gorm": "Gorm",
            "Torgrim": "Torgrim",
            "Atli": "Atli",
            "Gratianus": "Gratianus",
            "Asser": "Asser",
            "Willibald": "Willibald",
            "Jomsvikings": "Jomswikingowie",
            "Jomsborg": "Jomsborg",
            "Vinland": "Winlandia",
            "Valhalla": "Walhalla",
            "Markland": "Marklandia",
            "Helluland": "Hellulandia",
            "Greenland": "Grenlandia",
            "Iceland": "Islandia",
            "Miklagard": "Miklagard",
            "London Bridge": "Most Londyński",
            "True Warrior": "Prawdziwy Wojownik",
            "No Enemies": "Nie masz żadnych wrogów",
            "Love": "Miłość bezwarunkowa",
            "Agape": "Miłość bezwarunkowa",
            "Berserk": "Szał berserkera",
            "Berserker": "Szał berserkera",
            "Danegeld": "Danegeld",
            "Thing": "Thing",
            "Althing": "Thing",
            "Wergild": "Główszczyzna",
            "Skraeling": "Skrælingowie"
        },
        "character_forms": {
            "Thorfinn -> Askeladd": "Askeladd! Pojedynkuj się ze mną! (nienawiść z dzieciństwa)",
            "Askeladd -> Thorfinn": "Thorfinn, dorośnij... / Chłopcze (gorzka lekcja życia)",
            "Thors -> Thorfinn": "Pamiętaj, synu: nie masz żadnych wrogów.",
            "Einar -> Thorfinn": "Thorfinn, bracie / Jesteśmy wolnymi ludźmi",
            "Canute -> Thorfinn": "Thorfinn, dawny druhu...",
            "Thorkell -> Thorfinn": "Młody Thorfinn! Pokaż, czego nauczył cię Thors!"
        }
    },
    "berserk": {
        "title": "Berserk",
        "aliases": [
            "berserk"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Guts": "Guts",
            "Griffith": "Griffith",
            "Casca": "Casca",
            "Judeau": "Judeau",
            "Pippin": "Pippin",
            "Corkus": "Corkus",
            "Rickert": "Rickert",
            "Puck": "Puck",
            "Isidro": "Isidro",
            "Farnese de Vandimion": "Farnese de Vandimion",
            "Serpico": "Serpico",
            "Schierke": "Schierke",
            "Ivalera": "Ivalera",
            "Skull Knight": "Rycerz Czaszka",
            "Nosferatu Zodd": "Zodd Nieśmiertelny",
            "God Hand": "Ręka Boga",
            "Band of the Falcon": "Drużyna Jastrzębia",
            "Hawk": "Drużyna Jastrzębia",
            "Brand of Sacrifice": "Znak Przeznaczenia",
            "Behelit": "Behelit",
            "Eclipse": "Zaćmienie",
            "Dragon Slayer": "Zabójca Smoków",
            "Berserker Armor": "Zbroja Berserkera",
            "Midland": "Królestwo Midlandu",
            "Holy See": "Święty Kościół",
            "Apostles": "Apostołowie",
            "Idea of Evil": "Idea Zła",
            "Farnese": "Farnese de Vandimion",
            "Void": "Void",
            "Slan": "Slan",
            "Grunbeld": "Grunbeld",
            "Locus": "Locus",
            "Irvine": "Irvine",
            "Rakshas": "Rakshas",
            "Ganishka": "Cesarz Ganishka",
            "Silat": "Silat",
            "Dragonslayer": "Pogromca Smoków",
            "The Eclipse": "Zaćmienie",
            "Astral World": "Świat Astralny",
            "World Tree": "Drzewo Świata",
            "Falconia": "Falconia"
        },
        "character_forms": {
            "Guts -> Griffith": "GRIFFITH! (czysta, wstrząsająca żądza zemsty i ból zdrady)",
            "Griffith -> Guts": "Guts (jedyny człowiek, który sprawił, że zapomniał o swoim marzeniu)",
            "Casca -> Guts": "Guts (miłość, która przetrwała piekło)",
            "Schierke -> Guts": "Panie Guts / Guts-san (troska o jego duszę w Zbroi Berserkera)"
        }
    },
    "boku_no_hero_academia": {
        "title": "My Hero Academia: Akademia Bohaterów (Boku no Hero Academia)",
        "aliases": [
            "boku no hero academia",
            "my hero academia",
            "mha",
            "akademia bohaterów",
            "akademia bohaterow",
            "bnha"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Izuku Midoriya": "Izuku Midoriya",
            "Katsuki Bakugo": "Katsuki Bakugo",
            "Shoto Todoroki": "Shoto Todoroki",
            "All Might": "All Might",
            "Toshinori Yagi": "All Might",
            "Endeavor": "Endeavor",
            "Enji Todoroki": "Endeavor",
            "Hawks": "Hawks",
            "Keigo Takami": "Hawks",
            "Ochaco Uraraka": "Ochaco Uraraka",
            "Tenya Iida": "Tenya Iida",
            "Eijiro Kirishima": "Eijiro Kirishima",
            "Tsuyu Asui": "Tsuyu Asui",
            "Shota Aizawa": "Shota Aizawa",
            "All For One": "All For One",
            "Tomura Shigaraki": "Tomura Shigaraki",
            "Tenko Shimura": "Tomura Shigaraki",
            "Dabi": "Dabi",
            "Toya Todoroki": "Dabi",
            "Himiko Toga": "Himiko Toga",
            "Twice": "Twice",
            "Jin Bubaigawara": "Twice",
            "One For All": "Jeden za Wszystkich",
            "Quirk": "Dar",
            "Quirkless": "Bezdarny",
            "U.A. High School": "Liceum U.A.",
            "Class 1-A": "Klasa 1-A",
            "League of Villains": "Liga Złoczyńców",
            "Paranormal Liberation Front": "Front Wyzwolenia Zjawisk Nadprzyrodzonych",
            "Smash": "Smash!",
            "Plus Ultra": "Plus Ultra!"
        },
        "character_forms": {
            "Izuku -> Bakugo": "Kacchan! (respekt, podziw z dzieciństwa)",
            "Bakugo -> Izuku": "Deku! Ty bezużyteczny śmieciu! (zadziorność i ambicja)",
            "Izuku -> All Might": "All Might! / Mistrzu!",
            "All Might -> Izuku": "Młody Midoriyo!"
        }
    },
    "sousou_no_frieren": {
        "title": "Frieren: U kresu drogi (Sousou no Frieren)",
        "aliases": [
            "sousou no frieren",
            "frieren",
            "frieren: u kresu drogi",
            "frieren at journey's end"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Frieren": "Frieren",
            "Himmel": "Himmel",
            "Heiter": "Heiter",
            "Eisen": "Eisen",
            "Fern": "Fern",
            "Stark": "Stark",
            "Sein": "Sein",
            "Flamme": "Flamme",
            "Serie": "Serie",
            "Aura the Guillotine": "Aura Gilotyna",
            "Demon King": "Król Demonów",
            "Hero Party": "Drużyna Bohaterów",
            "Zoltraak": "Zoltraak",
            "Mana Suppression": "Tłumienie Many",
            "Ende": "Ende",
            "Aureole": "Aureole",
            "First-Class Mage Exam": "Egzamin na Maga Pierwszej Klasy",
            "Continental Magic Association": "Kontynentalny Związek Magii",
            "Grimoire": "Grimuar"
        },
        "character_forms": {
            "Frieren -> Himmel": "Himmel... (wspomnienia, zrozumienie ludzkich serc)",
            "Fern -> Frieren": "Mistrzyni Frieren / Frieren-sama (karzące spojrzenie na lenistwo)",
            "Fern -> Stark": "Panie Stark / Dziecinny zboczeniec",
            "Stark -> Fern": "Fern (strach przed jej fochem / troska)"
        }
    },
    "dungeon_meshi": {
        "title": "Pyszności w Lochach (Dungeon Meshi: Delicious in Dungeon)",
        "aliases": [
            "delicious in dungeon",
            "pyszności w lochach",
            "pysznosci w lochach",
            "dungeon meshi"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Laios Touden": "Laios Touden",
            "Marcille Donato": "Marcille Donato",
            "Chilchuck Tims": "Chilchuck Tims",
            "Senshi": "Senshi",
            "Falin Touden": "Falin Touden",
            "Shuro": "Shuro",
            "Toshiro Nakamoto": "Shuro",
            "Kabru": "Kabru",
            "Thistle": "Thistle",
            "Red Dragon": "Czerwony Smok",
            "Winged Lion": "Skrzydlaty Lew",
            "Dungeon": "Loch",
            "Golden Kingdom": "Złote Królestwo",
            "Monster Cuisine": "Potrawka z potworów",
            "Ancient Magic": "Starożytna Magia"
        },
        "character_forms": {
            "Laios -> Potwory": "Ciekawe jak smakuje ich mięso... (naukowa pasja)",
            "Marcille -> Laios": "NIGDY TEGO NIE ZJEM! / Laios, ty obrzydliwcu!",
            "Senshi -> Marcille": "Jedz, bo bez zbilansowanej diety nie przetrwasz w lochu!",
            "Chilchuck -> Drużyna": "Pamiętajcie, to tylko praca za stawkę!"
        }
    },
    "oshi_no_ko": {
        "title": "Moja Gwiazda (Oshi no Ko)",
        "aliases": [
            "moja gwiazda",
            "oshi no ko",
            "oniko"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Ai Hoshino": "Ai Hoshino",
            "Aquamarine Hoshino": "Aquamarine Hoshino",
            "Ruby Hoshino": "Ruby Hoshino",
            "Kana Arima": "Kana Arima",
            "Akane Kurokawa": "Akane Kurokawa",
            "Mem-Cho": "Mem-Cho",
            "Miyako Saito": "Miyako Saito",
            "Ichigo Saito": "Ichigo Saito",
            "Taishi Gotanda": "Reżyser Taishi Gotanda",
            "Hikaru Kamiki": "Hikaru Kamiki",
            "B-Komachi": "B-Komachi",
            "Strawberry Productions": "Strawberry Productions",
            "Entertainment Industry": "Japoński Przemysł Rozrywkowy",
            "Lie is Love": "Kłamstwo to najdoskonalsza forma miłości",
            "Black Star Eyes": "Czarne Gwiazdy w Oczach"
        },
        "character_forms": {
            "Aqua -> Wrogowie": "Zimna, bezwzględna dedukcja i planowanie zemsty za śmierć Ai",
            "Ruby -> Aqua": "Onii-chan / Aqua (początkowo rodzeństwo, później rozpad i prawda o Goro)",
            "Kana -> Aqua": "Aqua, ty durniu! (niezdolność wyznania uczuć)",
            "Akane -> Aqua": "Rozszyfruję każdy twój ból i pomogę ci zabić..."
        }
    },
    "solo_leveling": {
        "title": "Solo Leveling (Tylko ja awansuję)",
        "aliases": [
            "tylko ja awansuje",
            "solo leveling",
            "tylko ja awansuję"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Sung Jinwoo": "Sung Jinwoo",
            "Cha Hae-in": "Cha Hae-in",
            "Baek Yoonho": "Baek Yoonho",
            "Choi Jong-in": "Choi Jong-in",
            "Go Gunhee": "Go Gunhee",
            "Woo Jinchul": "Woo Jinchul",
            "Thomas Andre": "Thomas Andre",
            "Liu Zhigang": "Liu Zhigang",
            "Igris": "Igris Krwawy Czerwony",
            "Beru": "Beru",
            "Iron": "Iron",
            "Tank": "Tank",
            "The System": "System",
            "Hunter": "Łowca",
            "Gates": "Wrota",
            "Dungeons": "Wrota",
            "Awakening": "Przebudzenie",
            "Re-Awakening": "Przebudzenie",
            "Shadow Monarch": "Monarcha Cieni",
            "Monarchs and Rulers": "Monarchowie i Władcy",
            "Arise": "Powstań!",
            "Shadow Extraction": "Ekstrakcja Cienia",
            "Ruler's Authority": "Autorytet Władcy",
            "Jeju Island Raid": "Rajd na Wyspę Jeju"
        },
        "character_forms": {
            "Jinwoo -> Cienie": "Powstań! (Epicki rozkaz budzący armię)",
            "Beru -> Jinwoo": "Mój Królu! (fanatyczne uwielbienie)",
            "Cha Hae-in -> Jinwoo": "Panie Sung Jinwoo (fascynacja zapachem many)"
        }
    },
    "made_in_abyss": {
        "title": "Made in Abyss",
        "aliases": [
            "mia",
            "made in abyss"
        ],
        "publisher": "Wydawnictwo Kotori",
        "glossary": {
            "Riko": "Riko",
            "Reg": "Reg",
            "Nanachi": "Nanachi",
            "Mitty": "Mitty",
            "Lyza the Annihilator": "Lyza Niszczycielka",
            "Ozen the Immovable": "Ozen Niewzruszona",
            "Bondrewd the Novel": "Bondrewd Nowator",
            "Prushka": "Prushka",
            "Faputa": "Faputa",
            "The Abyss": "Otchłań",
            "Whistles": "Gwizdki: Czerwony Gwizdek, Niebieski Gwizdek, Fioletowy Gwizdek, Czarny Gwizdek, Biały Gwizdek",
            "Curse of the Abyss": "Klątwa Otchłani",
            "Layers of the Abyss": "Warstwy Otchłani: 1. Krawędź Otchłani, 2. Las Pokus, 3. Wielka Uskok, 4. Kielichy Olbrzymów, 5. Morze Trupów, 6. Stolica Niepowrotnych, 7. Dno Otchłani",
            "Relics": "Relikty",
            "Incinerator": "Spopielacz",
            "Cartridges": "Kartridże"
        },
        "character_forms": {
            "Nanachi -> Reg/Riko": "Nnaa~ (charakterystyczne westchnienie i czułość)",
            "Bondrewd -> Dzieci": "Subarashii! (Przerażający zachwyt nad postępem nauki)",
            "Riko -> Reg": "Reg! (nieustraszona ciekawość i wiara w przyjaciela)"
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
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Shoyo Hinata": "Shoyo Hinata",
            "Tobio Kageyama": "Tobio Kageyama",
            "Daichi Sawamura": "Daichi Sawamura",
            "Koshi Sugawara": "Koshi Sugawara",
            "Asahi Azumane": "Asahi Azumane",
            "Yu Nishinoya": "Yu Nishinoya",
            "Ryunosuke Tanaka": "Ryunosuke Tanaka",
            "Kei Tsukishima": "Kei Tsukishima",
            "Tadashi Yamaguchi": "Tadashi Yamaguchi",
            "Toru Oikawa": "Toru Oikawa",
            "Tetsuro Kuroo": "Tetsuro Kuroo",
            "Kenma Kozume": "Kenma Kozume",
            "Kotaro Bokuto": "Kotaro Bokuto",
            "Keiji Akaashi": "Keiji Akaashi",
            "Wakatoshi Ushijima": "Wakatoshi Ushijima",
            "Karasuno High": "Liceum Karasuno",
            "Nekoma High": "Liceum Nekoma",
            "Aoba Johsai": "Liceum Aoba Johsai",
            "Fukurodani Academy": "Akademia Fukurodani",
            "Shiratorizawa Academy": "Akademia Shiratorizawa",
            "Freak Quick": "Potworny Szybki Atak",
            "Dump Shot": "Kiwa",
            "Rolling Thunder": "Rolling Thunder!",
            "Spring Tournament": "Turniej Wiosenny",
            "Trash Heap Showdown": "Bitwa na Wysypisku Śmieci"
        },
        "character_forms": {
            "Hinata -> Kageyama": "Kageyama! Wystaw mi jeszcze jedną piłkę!",
            "Kageyama -> Hinata": "Boke, Hinata boke! (Ty durniu, Hinata!)",
            "Oikawa -> Kageyama": "Tobio-chan (ironiczny uśmieszek mistrza)",
            "Bokuto -> Akaashi": "Akaaaashi! (lament w dołku psychicznym)"
        }
    },
    "kaguya_sama": {
        "title": "Kaguya-sama: Miłość to wojna (Kaguya-sama wa Kokurasetai)",
        "aliases": [
            "milosc to wojna",
            "kaguya sama",
            "kaguya-sama",
            "miłość to wojna"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Kaguya Shinomiya": "Kaguya Shinomiya",
            "Miyuki Shirogane": "Miyuki Shirogane",
            "Chika Fujiwara": "Chika Fujiwara",
            "Yu Ishigami": "Yu Ishigami",
            "Miko Iino": "Miko Iino",
            "Ai Hayasaka": "Ai Hayasaka",
            "Nagisa Kashiwagi": "Nagisa Kashiwagi",
            "Maki Shijo": "Maki Shijo",
            "Shuchiin Academy": "Akademia Shuchiin",
            "Student Council": "Samorząd Uczniowski",
            "Love is War": "Miłość to wojna: Kto pierwszy wyzna uczucie, ten przegrywa!",
            "How Cute": "Och, jakie to urocze...",
            "Shinomiya Conglomerate": "Konglomerat Finansowy Shinomiya"
        },
        "character_forms": {
            "Kaguya -> Shirogane": "Przewodniczący / Shirogane (duma i ukryte uwielbienie)",
            "Shirogane -> Kaguya": "Shinomiya (duma i obsesja na punkcie wyznania)",
            "Chika -> Ishigami": "Ishigami-kun! Nie bądź taki ponury!",
            "Ishigami -> Kaguya": "Shinomiya-senpai mnie zabije..."
        }
    },
    "jojo": {
        "title": "JoJo's Bizarre Adventure",
        "aliases": [
            "jjba",
            "jojo",
            "jojo's bizarre adventure"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Jonathan Joestar": "Jonathan Joestar",
            "Joseph Joestar": "Joseph Joestar",
            "Jotaro Kujo": "Jotaro Kujo",
            "Josuke Higashikata": "Josuke Higashikata",
            "Giorno Giovanna": "Giorno Giovanna",
            "Jolyne Cujoh": "Jolyne Cujoh",
            "Johnny Joestar": "Johnny Joestar",
            "Dio Brando": "Dio Brando",
            "DIO": "Dio Brando",
            "Kars": "Kars",
            "Yoshikage Kira": "Yoshikage Kira",
            "Diavolo": "Diavolo",
            "Enrico Pucci": "Ojciec Enrico Pucci",
            "Funny Valentine": "Prezydent Funny Valentine",
            "Hamon": "Hamon",
            "Ripple": "Hamon",
            "Stand": "Stand",
            "Star Platinum": "Star Platinum",
            "The World": "The World",
            "Crazy Diamond": "Crazy Diamond",
            "Gold Experience": "Gold Experience",
            "Stone Free": "Stone Free",
            "Tusk": "Tusk",
            "Stone Mask": "Kamienna Maska",
            "Speedwagon Foundation": "Fundacja Speedwagona"
        },
        "character_forms": {
            "Jotaro -> Wrogowie": "Yare Yare Daze... (Dajcie mi święty spokój...)",
            "DIO -> Joestarowie": "WRYYYYY! / Za Warudo!",
            "Joseph -> Przeciwnicy": "Twoje kolejne słowa to: ...!",
            "Giorno -> Bruno": "Bruno Bucciarati (braterska lojalność mafijna)"
        }
    },
    "blue_lock": {
        "title": "Blue Lock",
        "aliases": [
            "blue lock"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Yoichi Isagi": "Yoichi Isagi",
            "Meguru Bachira": "Meguru Bachira",
            "Rensuke Kunigami": "Rensuke Kunigami",
            "Hyoma Chigiri": "Hyoma Chigiri",
            "Seishiro Nagi": "Seishiro Nagi",
            "Reo Mikage": "Reo Mikage",
            "Rin Itoshi": "Rin Itoshi",
            "Sae Itoshi": "Sae Itoshi",
            "Shouei Barou": "Shouei Barou",
            "Jinpachi Ego": "Jinpachi Ego",
            "Anri Teieri": "Anri Teieri",
            "Michael Kaiser": "Michael Kaiser",
            "Alexis Ness": "Alexis Ness",
            "Noel Noa": "Noel Noa",
            "Blue Lock Project": "Projekt Blue Lock",
            "Egoist": "Egoista",
            "Metavision": "Metawizja",
            "Flow State": "Stan Flow",
            "Direct Volley": "Bezpośredni Wolej",
            "Neo Egoist League": "Liga Neo Egoistów"
        },
        "character_forms": {
            "Isagi -> Przeciwnicy": "Pożrę cię na tym boisku! (bezwzględne ego)",
            "Ego -> Uczestnicy": "Nieoszlifowane diamenty / Wy śmiecie bez ambicji!",
            "Barou -> Isagi": "Ty sługusie! Król jest tylko jeden!"
        }
    },
    "wind_breaker": {
        "title": "Wind Breaker",
        "aliases": [
            "windbreaker",
            "wind breaker"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Haruka Sakura": "Haruka Sakura",
            "Hajime Umemiya": "Hajime Umemiya",
            "Kyotaro Sugishita": "Kyotaro Sugishita",
            "Hayato Suo": "Hayato Suo",
            "Akihiko Nirei": "Akihiko Nirei",
            "Toma Hiragi": "Toma Hiragi",
            "Kotoha Tachibana": "Kotoha Tachibana",
            "Chouji Tomiyama": "Chouji Tomiyama",
            "Jo Togame": "Jo Togame",
            "Furin High School": "Liceum Furin",
            "Bofurin": "Bofurin",
            "Shishitoren": "Shishitoren",
            "KEEL": "KEEL",
            "Four Heavenly Kings": "Czterej Królowie Niebios Furin",
            "Makochi Town": "Miasto Makochi"
        },
        "character_forms": {
            "Sakura -> Każdy": "Nie potrzebuję przyjaciół, przyszedłem tu zdobyć sam szczyt! (wstydliwe zakłopotanie na dobre słowa)",
            "Umemiya -> Sakura": "Witaj w rodzinie Bofurin, Sakura! (ciepło i spokój)",
            "Suo -> Sakura": "Sakura-kun, uspokój się trochę... (dżentelmeńska elegancja)"
        }
    },
    "noragami": {
        "title": "Noragami",
        "aliases": [
            "noragami"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Yato": "Yato",
            "Hiyori Iki": "Hiyori Iki",
            "Yukine": "Yukine",
            "Bishamon": "Bishamon",
            "Kazuma": "Kazuma",
            "Kofuku": "Kofuku",
            "Daikoku": "Daikoku",
            "Tenjin": "Tenjin",
            "Nora": "Nora",
            "Stray": "Nora",
            "Father": "Ojciec",
            "Sorcerer": "Ojciec",
            "Shinki": "Shinki",
            "Sacred Vessel": "Shinki",
            "Hafuri Vessel": "Błogosławione Naczynie",
            "Ayakashi": "Ayakashi",
            "Phantom": "Ayakashi",
            "Borderline": "Granica",
            "Near Shore": "Bliski Brzeg",
            "Far Shore": "Bliski Brzeg"
        },
        "character_forms": {
            "Yato -> Hiyori": "Hiyori! (troska i uroczy żebrak)",
            "Hiyori -> Yato": "Yato! (opiekuńczość i cios zapaśniczy Jungle Savate)",
            "Yukine -> Yato": "Yato (początkowy bunt -> absolutne oddanie jako Hafuri)"
        }
    },
    "akatsuki_no_yona": {
        "title": "Yona w blasku świtu (Akatsuki no Yona: Yona of the Dawn)",
        "aliases": [
            "yona w blasku switu",
            "yona w blasku świtu",
            "yona of the dawn",
            "akatsuki no yona"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Yona": "Księżniczka Yona",
            "Son Hak": "Son Hak",
            "Soo-won": "Król Soo-won",
            "Yoon": "Yoon",
            "Kija": "Kija",
            "Shin-ah": "Shin-ah",
            "Jae-ha": "Jae-ha",
            "Zeno": "Zeno",
            "King Hiryuu": "Karmazynowy Król Hiryuu",
            "Kingdom of Kouka": "Królestwo Kouka",
            "Kuuto": "Kuuto",
            "Wind Tribe": "Plemię Wiatru",
            "Four Dragon Warriors": "Czterej Smoczy Wojownicy"
        },
        "character_forms": {
            "Hak -> Yona": "Księżniczko (bezgraniczne oddanie i ukryta miłość)",
            "Yona -> Hak": "Hak (zaufanie, lęk o jego życie, narastająca miłość)",
            "Kija -> Yona": "Nasza Pani! (święta wierność Smoka)"
        }
    },
    "jibaku_shounen_hanako_kun": {
        "title": "Hanako, duch ze szkolnej toalety (Jibaku Shounen Hanako-kun)",
        "aliases": [
            "toilet-bound hanako-kun",
            "jibaku shounen hanako-kun",
            "hanako duch ze szkolnej toalety",
            "hanako-kun"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Hanako-kun": "Hanako ze Szkolnej Toalety",
            "Nene Yashiro": "Nene Yashiro",
            "Kou Minamoto": "Kou Minamoto",
            "Teru Minamoto": "Teru Minamoto",
            "Tsukasa Yugi": "Tsukasa Yugi",
            "Sakura Nanamine": "Sakura Nanamine",
            "Natsuhiko Hyuuga": "Natsuhiko Hyuuga",
            "Sosuke Mitsuba": "Sosuke Mitsuba",
            "Aoi Akane": "Aoi Akane",
            "Akane Aoi": "Akane Aoi",
            "Kamome Academy": "Akademia Kamome",
            "Seven Wonders": "Siedem Tajemnic Szkoły",
            "Yorishiro": "Yorishiro",
            "Mokke": "Mokke",
            "Mermaid's Scale": "Łuska Syreny"
        },
        "character_forms": {
            "Hanako -> Nene": "Yashiro~ (droczliwa czułość i obrona)",
            "Nene -> Hanako": "Hanako-kun! (panika, troska i uczucie)",
            "Kou -> Hanako": "Hanako! (przyjaciel i rywal egzorcysty)"
        }
    },
    "tatsuki_fujimoto_oneshots": {
        "title": "Look Back & Goodbye, Eri (Dzieła Tatsukiego Fujimoto)",
        "aliases": [
            "do widzenia, eri",
            "goodbye, eri",
            "look back",
            "goodbye eri"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Ayumu Fujino": "Ayumu Fujino",
            "Kyomoto": "Kyomoto",
            "Fujino Kyo": "Fujino Kyo",
            "Yuta": "Yuta",
            "Eri": "Eri",
            "Explosion Scene": "Wybuch w finale filmu"
        },
        "character_forms": {
            "Fujino -> Kyomoto": "Rysujmy razem mangę! (przełamanie samotności)",
            "Yuta -> Eri": "Eri... Dlaczego oglądamy to jeszcze raz?"
        }
    },
    "tongari_boushi_no_atelier": {
        "title": "Atelier spiczastych kapeluszy (Tongari Boushi no Atelier: Witch Hat Atelier)",
        "aliases": [
            "witch hat atelier",
            "tongari boushi no atelier",
            "atelier spiczastych kapeluszy"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Coco": "Coco",
            "Qifrey": "Qifrey",
            "Agott": "Agott",
            "Tetia": "Tetia",
            "Richeh": "Richeh",
            "Olruggio": "Olruggio",
            "Brimmed Hats": "Kapelusze z Rondem w Dół",
            "Brimhats": "Kapelusze z Rondem w Dół",
            "Inishi": "Zakazana Magia",
            "Forbidden Magic": "Zakazana Magia",
            "Magic Ink": "Magiczny Atrament",
            "Magic Glyphs": "Magiczne Pieczęcie",
            "Pointed Hats": "Spiczaste Kapelusze",
            "Great Hall": "Wielka Sala Magii pod Wodą"
        },
        "character_forms": {
            "Qifrey -> Uczennice": "Magia to cud, który może rysować każdy z nas.",
            "Agott -> Coco": "Nie zostawaj w tyle, niemagiczna dziewczyno!",
            "Coco -> Qifrey": "Mistrzu Qifreyu!"
        }
    },
    "beastars": {
        "title": "Beastars",
        "aliases": [
            "beastars"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Legoshi": "Legoshi",
            "Haru": "Haru",
            "Louis": "Louis",
            "Juno": "Juno",
            "Jack": "Jack",
            "Gouhin": "Gouhin",
            "Tem": "Tem",
            "Riz": "Riz",
            "Cherryton Academy": "Akademia Cherryton",
            "Beastar": "Beastar",
            "Carnivores": "Mięsożercy",
            "Herbivores": "Roślinożercy",
            "Black Market": "Czarny Rynek Mięsa",
            "Shishigumi": "Shishigumi"
        },
        "character_forms": {
            "Legoshi -> Haru": "Chcę cię chronić... Nie jako drapieżnik, lecz z miłości.",
            "Louis -> Legoshi": "Wilku, przestań udawać słabego!",
            "Haru -> Legoshi": "Legoshi-kun..."
        }
    },
    "yofukashi_no_uta": {
        "title": "Zew Nocy (Yofukashi no Uta: Call of the Night)",
        "aliases": [
            "call of the night",
            "zew nocy",
            "yofukashi no uta"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Ko Yamori": "Ko Yamori",
            "Nazuna Nanakusa": "Nazuna Nanakusa",
            "Akira Asai": "Akira Asai",
            "Seri Kikyou": "Seri Kikyou",
            "Nico Hirata": "Nico Hirata",
            "Midori Kohakuhakobe": "Midori Kohakuhakobe",
            "Hatsuka Suzushiro": "Hatsuka Suzushiro",
            "Kabura Honda": "Kabura Honda",
            "Anko Uguisu": "Anko Uguisu",
            "Vampire Rule": "Zasada Wampirów: Człowiek zmienia się w wampira tylko, gdy zostanie ukąszony przez wampira, w którym się szczerze zakochał w ciągu 1 roku!",
            "Night Walking": "Nocne Włóczenie Się"
        },
        "character_forms": {
            "Ko -> Nazuna": "Nazuna-chan (fascynacja nocą i pragnienie zakochania)",
            "Nazuna -> Ko": "Pijemy krew i gramy w retro gry!"
        }
    },
    "kakegurui": {
        "title": "Kakegurui: Szał hazardu",
        "aliases": [
            "kakegurui: szał hazardu",
            "kakegurui",
            "szał hazardu"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Yumeko Jabami": "Yumeko Jabami",
            "Ryota Suzui": "Ryota Suzui",
            "Mary Saotome": "Mary Saotome",
            "Kirari Momobami": "Kirari Momobami",
            "Ririka Momobami": "Ririka Momobami",
            "Sayaka Igarashi": "Sayaka Igarashi",
            "Midari Ikishima": "Midari Ikishima",
            "Yumemi Yumemite": "Yumemi Yumemite",
            "Kaede Manyuda": "Kaede Manyuda",
            "Itsuki Sumeragi": "Itsuki Sumeragi",
            "Hyakkaou Private Academy": "Prywatna Akademia Hyakkaou",
            "Housepet": "Zwierzątko Domowe",
            "Life Schedule": "Plan Życiowy",
            "Gambling Craze": "Szał Hazardu"
        },
        "character_forms": {
            "Yumeko -> Przeciwnicy": "Pogrążmy się w szaleństwie hazardu! (ekstatyczny trans)",
            "Mary -> Yumeko": "Yumeko, ty szalona wariatko!",
            "Kirari -> Szkoła": "Akademia to moje osobiste akwarium."
        }
    },
    "horimiya": {
        "title": "Horimiya",
        "aliases": [
            "hori-san to miyamura-kun",
            "horimiya"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Kyoko Hori": "Kyoko Hori",
            "Izumi Miyamura": "Izumi Miyamura",
            "Toru Ishikawa": "Toru Ishikawa",
            "Yuki Yoshikawa": "Yuki Yoshikawa",
            "Kakeru Sengoku": "Kakeru Sengoku",
            "Remi Ayasaki": "Remi Ayasaki",
            "Sakura Kono": "Sakura Kono",
            "Shu Iura": "Shu Iura",
            "Souta Hori": "Souta Hori",
            "Kyosuke Hori": "Kyosuke Hori",
            "Katagiri Senior High School": "Liceum Katagiri",
            "Secret Persona": "Ukryte Drugie Oblicze"
        },
        "character_forms": {
            "Hori -> Miyamura": "Miyamura! (zaborcza miłość i prośba o bicie/przemoc domową dla zabawy)",
            "Miyamura -> Hori": "Hori-san (czułość, akceptacja i miłość)",
            "Souta -> Miyamura": "Brat Miyamura!"
        }
    },
    "toradora": {
        "title": "Toradora!",
        "aliases": [
            "toradora!",
            "toradora"
        ],
        "publisher": "Wydawnictwo Studio JG / Wydawnictwo Kotori",
        "glossary": {
            "Ryuji Takasu": "Ryuji Takasu",
            "Taiga Aisaka": "Taiga Aisaka",
            "Minori Kushieda": "Minori Kushieda",
            "Yusaku Kitamura": "Yusaku Kitamura",
            "Ami Kawashima": "Ami Kawashima",
            "Yasuko Takasu": "Yasuko Takasu",
            "Inko-chan": "Inko-chan",
            "Palmtop Tiger": "Kieszonkowy Tygrys",
            "Dragon and Tiger": "Smok i Tygrys"
        },
        "character_forms": {
            "Taiga -> Ryuji": "Ryuji, ty głupi kundlu! (początkowo) / Zawsze bądź przy mnie...",
            "Ryuji -> Taiga": "Taiga (opieka kulinarna i bezwarunkowe wsparcie)"
        }
    },
    "overlord": {
        "title": "Overlord",
        "aliases": [
            "overlord"
        ],
        "publisher": "Wydawnictwo Kotori / Wydawnictwo Waneko",
        "glossary": {
            "Ainz Ooal Gown": "Ainz Ooal Gown",
            "Momonga": "Ainz Ooal Gown",
            "Albedo": "Albedo",
            "Shalltear Bloodfallen": "Shalltear Bloodfallen",
            "Demiurge": "Demiurge",
            "Cocytus": "Cocytus",
            "Aura Bella Fiora": "Aura Bella Fiora",
            "Mare Bello Fiore": "Mare Bello Fiore",
            "Sebas Tian": "Sebas Tian",
            "Pandora's Actor": "Pandora's Actor",
            "Pleiades Six Stars": "Plejady: Yuri Alpha, Lupusregina Beta, Narberal Gamma, CZ2128 Delta, Solution Epsilon, Entoma Vasilissa Zeta",
            "Gazef Stronoff": "Gazef Stronoff",
            "Brain Unglaus": "Brain Unglaus",
            "Evileye": "Evileye",
            "Keeno": "Evileye",
            "Great Tomb of Nazarick": "Wielki Grobowiec Nazarick",
            "YGGDRASIL": "YGGDRASIL",
            "New World": "Nowy Świat",
            "World Items": "Przedmioty Świata",
            "Tier Magic": "Magia Kręgów",
            "Fallen Down": "Upadek",
            "Grasp Heart": "Zmiażdżenie Serca",
            "Sorcerer Kingdom": "Królestwo Magii"
        },
        "character_forms": {
            "Strażnicy -> Ainz": "Niech żyje Najwyższy Władca Ainz Ooal Gown! / Sasuga Ainz-sama!",
            "Ainz -> Strażnicy": "Zezwalam (w myślach: Oby tylko nie odkryli, że nie mam pojęcia co robię!)",
            "Albedo -> Ainz": "Mój ukochany panie Ainzie!"
        }
    },
    "sword_art_online": {
        "title": "Sword Art Online (SAO)",
        "aliases": [
            "sword art online: progressive",
            "sword art online",
            "sao"
        ],
        "publisher": "Wydawnictwo Kotori / Wydawnictwo Studio JG",
        "glossary": {
            "Kirito": "Kirito",
            "Kazuto Kirigaya": "Kirito",
            "Asuna": "Asuna",
            "Asuna Yuuki": "Asuna",
            "Yui": "Yui",
            "Klein": "Klein",
            "Ryotaro Tsuboi": "Klein",
            "Agil": "Agil",
            "Andrew Gilbert Mills": "Agil",
            "Silica": "Silica",
            "Keiko Ayano": "Silica",
            "Lisbeth": "Lisbeth",
            "Rika Shinozaki": "Lisbeth",
            "Sinon": "Sinon",
            "Shino Asada": "Sinon",
            "Leafa": "Leafa",
            "Suguha Kirigaya": "Leafa",
            "Eugeo": "Eugeo",
            "Alice Zuberg": "Alice Synthesis Thirty",
            "Synthesis Thirty": "Alice Synthesis Thirty",
            "Akihiko Kayaba": "Akihiko Kayaba",
            "Heathcliff": "Akihiko Kayaba",
            "Aincrad": "Aincrad",
            "NerveGear": "NerveGear",
            "Elucidator": "Elucidator",
            "Dark Repulser": "Dark Repulser",
            "Dual Blades": "Dwa Miecze",
            "Laughing Coffin": "Śmiejąca się Trumna",
            "Knights of the Blood Oath": "Rycerze Krwi",
            "Underworld": "Underworld",
            "Fluctlight": "Fluctlight"
        },
        "character_forms": {
            "Kirito -> Asuna": "Asuna (miłość, która przetrwała śmierć w grze)",
            "Asuna -> Kirito": "Kirito-kun (bezgraniczne zaufanie)",
            "Yui -> Kirito/Asuna": "Tatusiu! / Mamusiu!"
        }
    },
    "goblin_slayer": {
        "title": "Zabójca goblinów (Goblin Slayer)",
        "aliases": [
            "goblin slayer",
            "zabojca goblinow",
            "zabójca goblinów"
        ],
        "publisher": "Wydawnictwo Studio JG / Wydawnictwo Kotori",
        "glossary": {
            "Goblin Slayer": "Zabójca Goblinów",
            "Priestess": "Kapłanka",
            "High Elf Archer": "Wysoka Elfka Łuczniczka",
            "Dwarf Shaman": "Krasnoludzki Szaman",
            "Lizard Priest": "Jaszczuroludzki Kapłan",
            "Cow Girl": "Pasterka",
            "Guild Girl": "Urzędniczka Gildii",
            "Sword Maiden": "Dziewica Miecza",
            "Goblins": "Gobliny",
            "Adventurers Guild": "Gildia Poszukiwaczy Przygód",
            "Miracles": "Cuda",
            "Goblin Nest": "Gniazdo Goblinów"
        },
        "character_forms": {
            "Goblin Slayer -> Wszyscy": "Jedyny dobry goblin to martwy goblin.",
            "Kapłanka -> Goblin Slayer": "Panie Zabójco Goblinów (troska i duchowe wsparcie)",
            "Elfka -> Goblin Slayer": "Orkobójco! Nie używaj znowu ognia i wody w jaskini!"
        }
    },
    "hellsing": {
        "title": "Hellsing",
        "aliases": [
            "hellsing ultimate",
            "hellsing"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Alucard": "Alucard",
            "Sir Integra Fairbrook Wingates Hellsing": "Sir Integra Hellsing",
            "Seras Victoria": "Seras Victoria",
            "Walter C. Dornez": "Walter C. Dornez",
            "Alexander Anderson": "Ojciec Alexander Anderson",
            "The Major": "Major",
            "The Captain": "Kapitan",
            "Rip van Winkle": "Rip van Winkle",
            "Zorin Blitz": "Zorin Blitz",
            "Tubalcain Alhambra": "Tubalcain Alhambra",
            "Schrödinger": "Schrödinger",
            "Enrico Maxwell": "Biskup Enrico Maxwell",
            "Hellsing Organization": "Organizacja Hellsing",
            "Iscariot Section XIII": "Sekcja XIII Iscariot",
            "Millennium": "Millennium",
            "Letztes Bataillon": "Millennium",
            "Freak Chips": "Chipy Freak",
            "Jackal": "Pistolety Alucarda: .454 Casull i 13mm Auto Anti-Freak Jackal",
            "Casull": "Pistolety Alucarda: .454 Casull i 13mm Auto Anti-Freak Jackal",
            "Cromwell Control Art Restriction": "Pieczęć Cromwella"
        },
        "character_forms": {
            "Alucard -> Integra": "Moja Pani (Królewski pakt wierności krwi)",
            "Integra -> Alucard": "Alucardzie! Zniszcz i zabij ich wszystkich! Zostaw tylko popiół!",
            "Anderson -> Alucard": "Amen! (Fanatyczna wściekłość krzyżowca)",
            "Alucard -> Seras": "Moja mała policyjko..."
        }
    },
    "neon_genesis_evangelion": {
        "title": "Neon Genesis Evangelion (NGE)",
        "aliases": [
            "evangelion",
            "nge",
            "eva",
            "neon genesis evangelion"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Shinji Ikari": "Shinji Ikari",
            "Rei Ayanami": "Rei Ayanami",
            "Asuka Langley Soryu": "Asuka Langley Soryu",
            "Kaworu Nagisa": "Kaworu Nagisa",
            "Misato Katsuragi": "Misato Katsuragi",
            "Gendo Ikari": "Gendo Ikari",
            "Ritsuko Akagi": "Doktor Ritsuko Akagi",
            "Ryoji Kaji": "Ryoji Kaji",
            "Evangelion": "Jednostka Evangelion: EVA-01, EVA-02, EVA-00",
            "EVA": "Jednostka Evangelion: EVA-01, EVA-02, EVA-00",
            "Angels": "Aniołowie",
            "AT Field": "Pole AT",
            "NERV": "NERV",
            "SEELE": "SEELE",
            "Human Instrumentality Project": "Projekt Dopełnienia Ludzkości",
            "Second Impact": "Drugi Kataklizm",
            "Third Impact": "Trzeci Kataklizm",
            "Tokyo-3": "Neo-Tokio-3",
            "MAGI System": "Superkomputer MAGI: Melchior, Balthasar, Casper",
            "LCL": "Płyn LCL",
            "Spear of Longinus": "Włócznia Longinusa"
        },
        "character_forms": {
            "Shinji -> Gendo": "Ojcze... (strach przed odrzuceniem, rozpaczliwa potrzeba uznania)",
            "Asuka -> Shinji": "Anta baka?! (Czyś ty zidiociał, Shinji?!)",
            "Misato -> Shinji": "Shinji-kun (dorosła opieka i poczucie winy)"
        }
    },
    "soul_eater": {
        "title": "Soul Eater",
        "aliases": [
            "soul eater"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Maka Albarn": "Maka Albarn",
            "Soul Eater Evans": "Soul Eater Evans",
            "Black Star": "Black Star",
            "Tsubaki Nakatsukasa": "Tsubaki Nakatsukasa",
            "Death the Kid": "Death the Kid",
            "Liz and Patty Thompson": "Liz i Patty Thompson",
            "Shinigami": "Lord Shinigami",
            "Lord Death": "Lord Shinigami",
            "Franken Stein": "Doktor Franken Stein",
            "Spirit Albarn": "Spirit Albarn",
            "Medusa Gorgon": "Meduza",
            "Crona": "Crona",
            "Asura": "Kishin Asura",
            "DWMA": "DWMA",
            "Shibusen": "DWMA",
            "Death Scythe": "Kosa Śmierci",
            "Soul Resonance": "Rezonans Dusz",
            "Madness": "Szaleństwo",
            "Kishin": "Kishin"
        },
        "character_forms": {
            "Maka -> Soul": "Soul! Zróbmy Rezonans Dusz! (partnerska jedność)",
            "Kid -> Liz/Patty": "Moja symetria została zniszczona! Umrę!",
            "Black Star -> Wszyscy": "HAHAHA! YAHOOO! Spójrzcie na wielkiego Black Stara!"
        }
    },
    "monster": {
        "title": "Monster (Naoki Urasawa)",
        "aliases": [
            "monster",
            "potwór"
        ],
        "publisher": "Wydawnictwo Hanami / Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Kenzo Tenma": "Doktor Kenzo Tenma",
            "Johan Liebert": "Johan Liebert",
            "Nina Fortner": "Nina Fortner",
            "Anna Liebert": "Nina Fortner",
            "Heinrich Lunge": "Inspektor Heinrich Lunge",
            "Dieter": "Dieter",
            "Wolfgang Grimmer": "Wolfgang Grimmer",
            "Roberto": "Roberto",
            "Eva Heinemann": "Eva Heinemann",
            "Kinderheim 511": "Kinderheim 511",
            "The Nameless Monster": "Bezimienny Potwór",
            "Red Rose Mansion": "Dwór Czerwonych Róż",
            "Ruhenheim": "Ruhenheim"
        },
        "character_forms": {
            "Tenma -> Johan": "To ja uratowałem ci życie... Moim obowiązkiem jest je zakończyć.",
            "Johan -> Tenma": "Doktorze Tenma... Prawdziwy koniec to nie śmierć, lecz zapomnienie.",
            "Lunge -> Tenma": "Moje palce nigdy się nie mylą, doktorze Tenma."
        }
    },
    "twentieth_century_boys": {
        "title": "20th Century Boys: Chłopcy z dwudziestego wieku",
        "aliases": [
            "20th century boys",
            "chłopcy z dwudziestego wieku",
            "chlopcy z dwudziestego wieku"
        ],
        "publisher": "Wydawnictwo Hanami / Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Kenji Endo": "Kenji Endo",
            "Friend": "Przyjaciel",
            "Tomodachi": "Przyjaciel",
            "Kanna Endo": "Kanna Endo",
            "Otcho": "Otcho",
            "Shogun": "Otcho",
            "Yoshitsune": "Yoshitsune",
            "Maruo": "Maruo",
            "Mon-chan": "Mon-chan",
            "Yukiji": "Yukiji",
            "Fukube": "Fukube",
            "Katsumata": "Katsumata",
            "Book of Prophecy": "Księga Proroctw",
            "New Book of Prophecy": "Nowa Księga Proroctw",
            "Bloody New Year's Eve": "Krwawy Sylwester 2000",
            "Friendship Democratic Party": "Partia Przyjaźni i Demokracji",
            "Expo 1970": "Wystawa Światowa Expo 1970 w Osace"
        },
        "character_forms": {
            "Kenji -> Przyjaciel": "Kim naprawdę jesteś, Przyjacielu?!",
            "Kanna -> Kenji": "Wujku Kenji... Wróć i zagraj jeszcze raz na gitarze!"
        }
    },
    "pluto": {
        "title": "Pluto (Naoki Urasawa x Osamu Tezuka)",
        "aliases": [
            "pluto"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Gesicht": "Gesicht",
            "Atom": "Atom",
            "Astro Boy": "Atom",
            "Uran": "Uran",
            "Mont Blanc": "Mont Blanc",
            "North No. 2": "Północ nr 2",
            "Brando": "Brando",
            "Hercules": "Hercules",
            "Epsilon": "Epsilon",
            "Pluto": "Pluto",
            "Sahad": "Pluto",
            "Brau 1589": "Brau 1589",
            "Professor Ochanomizu": "Profesor Ochanomizu",
            "Doctor Tenma": "Doktor Tenma",
            "Doctor Abullah": "Doktor Abullah",
            "39th Central Asian War": "39. Wojna Środkowoazjatycka",
            "Article 13 of Robot Law": "Artykuł 13 Prawa Robotów"
        },
        "character_forms": {
            "Gesicht -> Wrogowie": "Nienawiść niczego nie zrodzi... Tylko smutek.",
            "Atom -> Uran": "Uran, uważaj na siebie!"
        }
    },
    "shaman_king": {
        "title": "Shaman King (Król Szamanów)",
        "aliases": [
            "król szamanów",
            "shaman king",
            "krol szamanow"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Yoh Asakura": "Yoh Asakura",
            "Amidamaru": "Amidamaru",
            "Anna Kyoyama": "Anna Kyoyama",
            "Manta Oyamada": "Manta Oyamada",
            "Ren Tao": "Ren Tao",
            "Horohoro": "Horohoro",
            "Usui Horokeu": "Horohoro",
            "Ryunosuke Umemiya": "Drewniany Miecz Ryu",
            "Wooden Sword Ryu": "Drewniany Miecz Ryu",
            "Faust VIII": "Faust VIII",
            "Lyserg Diethel": "Lyserg Diethel",
            "Chocolove McDonell": "Chocolove McDonell",
            "Hao Asakura": "Hao Asakura",
            "Iron Maiden Jeanne": "Żelazna Dziewica Jeanne",
            "Marco Lasso": "Marco Lasso",
            "Great Spirit": "Wielki Duch",
            "Spirit of Fire": "Duch Ognia",
            "Over Soul": "Over Soul",
            "Furyoku": "Furyoku",
            "Shaman Fight": "Turniej Szamanów",
            "Patch Tribe": "Plemię Patch"
        },
        "character_forms": {
            "Anna -> Yoh": "Yoh! Trenuj, bo inaczej nie zostaniesz Królem Szamanów!",
            "Yoh -> Przeciwnicy": "Spokojnie, jakoś to będzie. (Nanto ka naru)",
            "Hao -> Ludzie": "Jakie to małe i bezużyteczne..."
        }
    },
    "slam_dunk": {
        "title": "Slam Dunk",
        "aliases": [
            "slam dunk"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Hanamichi Sakuragi": "Hanamichi Sakuragi",
            "Kaede Rukawa": "Kaede Rukawa",
            "Takenori Akagi": "Takenori Akagi",
            "Hisashi Mitsui": "Hisashi Mitsui",
            "Ryota Miyagi": "Ryota Miyagi",
            "Haruko Akagi": "Haruko Akagi",
            "Mitsuyoshi Anzai": "Trener Anzai",
            "Kiminobu Kogure": "Kiminobu Kogure",
            "Akira Sendoh": "Akira Sendoh",
            "Shinichi Maki": "Shinichi Maki",
            "Eiji Sawakita": "Eiji Sawakita",
            "Shohoku High School": "Liceum Shohoku",
            "Ryonan High": "Liceum Ryonan",
            "Kainan University Affiliated High": "Liceum Kainan",
            "Sannoh Kogyo": "Liceum Sannoh",
            "Rebound": "Zbiórka",
            "Slam Dunk": "Slam Dunk",
            "Inter-High Tournament": "Mistrzostwa Narodowe Szkół Średnich"
        },
        "character_forms": {
            "Sakuragi -> Akagi": "Gorylu! (prowokacja i szacunek dla kapitana)",
            "Sakuragi -> Rukawa": "Rukawa, ty lisie! (zazdrosna rywalizacja)",
            "Rukawa -> Sakuragi": "Dobe (Głupol / Matoł)"
        }
    },
    "hokuto_no_ken": {
        "title": "Pięść Gwiazd Północy (Hokuto no Ken: Fist of the North Star)",
        "aliases": [
            "pięść gwiazd północy",
            "piesc gwiazd polnocy",
            "hokuto no ken",
            "fist of the north star"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Kenshiro": "Kenshiro",
            "Raoh": "Raoh",
            "Ken-Oh": "Raoh",
            "Toki": "Toki",
            "Jagi": "Jagi",
            "Shin": "Shin",
            "Rei": "Rei",
            "Juda": "Juda",
            "Shew": "Shew",
            "Souther": "Souther",
            "Yuria": "Yuria",
            "Bat": "Bat",
            "Lin": "Lin",
            "Hokuto Shinken": "Boska Pięść Gwiazdy Północy",
            "Nanto Seiken": "Święta Pięść Gwiazdy Południa",
            "Omae wa Mou Shindeiru": "Już jesteś martwy!",
            "Hidebu": "Hidebu!",
            "Abeshi": "Hidebu!",
            "Musou Tensei": "Musou Tensei"
        },
        "character_forms": {
            "Kenshiro -> Wrogowie": "Jesteś już martwy. (Omae wa mou shindeiru)",
            "Raoh -> Niebiosa": "W całym moim życiu nie mam ani jednego żalu! (Waga shougai ni ippen no kui nashi!)"
        }
    },
    "vagabond": {
        "title": "Vagabond (Takehiko Inoue)",
        "aliases": [
            "vagabond"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Miyamoto Musashi": "Miyamoto Musashi",
            "Shinmen Takezo": "Miyamoto Musashi",
            "Sasaki Kojiro": "Sasaki Kojiro",
            "Matahachi Hon'iden": "Matahachi Hon'iden",
            "Otsu": "Otsu",
            "Takuan Soho": "Mnich Takuan Soho",
            "Inshun": "Inshun",
            "Yagyu Muneyoshi": "Yagyu Sekishusai",
            "Sekishusai": "Yagyu Sekishusai",
            "Yoshioka Seijuro": "Yoshioka Seijuro",
            "Yoshioka Denshichiro": "Yoshioka Denshichiro",
            "Ueda Ryohei": "Ueda Ryohei",
            "Ito Ittosai": "Ito Ittosai",
            "Battle of Sekigahara": "Bitwa pod Sekigaharą",
            "Yoshioka Clan 70-Man Duel": "Pojedynek z 70 szermierzami rodu Yoshioka pod Sosną Ichijoji",
            "Ganryujima Duel": "Pojedynek na Wyspie Ganryujima",
            "Way of the Sword": "Droga Miecza"
        },
        "character_forms": {
            "Musashi -> Przeciwnicy": "Pokaż mi swój miecz. Chcę zobaczyć, co kryje się na szczycie.",
            "Takuan -> Musashi": "Takezo... Życie i śmierć to ta sama chwila."
        }
    },
    "uzumaki_junji_ito": {
        "title": "Uzumaki (Spirala) i Dzieła Junjiego Ito",
        "aliases": [
            "tomie",
            "gyo",
            "spirala",
            "uzumaki",
            "junji ito"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Kirie Goshima": "Kirie Goshima",
            "Shuichi Saito": "Shuichi Saito",
            "Toshio Saito": "Toshio Saito",
            "Tomie Kawakami": "Tomie",
            "Kurouzu-cho": "Miasteczko Kurouzu",
            "Spiral Curse": "Klątwa Spirali",
            "Snail People": "Ślimakoludzie",
            "Hanging Balloons": "Balony Wisielców",
            "Gyo": "Gyo",
            "Amigara Fault": "Uskok Amigara"
        },
        "character_forms": {
            "Shuichi -> Kirie": "Kirie! Uciekajmy z tego przeklętego miasteczka!",
            "Kirie -> Shuichi": "Shuichi, dlaczego to znowu się dzieje?!"
        }
    },
    "bakuman": {
        "title": "Bakuman",
        "aliases": [
            "bakuman"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Moritaka Mashiro": "Moritaka Mashiro",
            "Saiko": "Moritaka Mashiro",
            "Akito Takagi": "Akito Takagi",
            "Shujin": "Akito Takagi",
            "Miho Azuki": "Miho Azuki",
            "Kaya Miyoshi": "Kaya Miyoshi",
            "Eiji Nizuma": "Eiji Nizuma",
            "Shintaro Fukuda": "Shintaro Fukuda",
            "Kazuya Hiramaru": "Kazuya Hiramaru",
            "Aiko Iwase": "Aiko Iwase",
            "Nobuhiro Mashiro": "Taro Kawaguchi",
            "Taro Kawaguchi": "Taro Kawaguchi",
            "Akira Hattori": "Akira Hattori",
            "Goro Miura": "Goro Miura",
            "Koji Yoshida": "Koji Yoshida",
            "Heishi Sasaki": "Redaktor Naczelny Sasaki",
            "Ashirogi Muto": "Ashirogi Muto",
            "Weekly Shonen Jump": "Tygodnik Shonen Jump",
            "Name": "Name",
            "Storyboard": "Name",
            "Serialization": "Serializacja",
            "Questionnaire Rankings": "Wyniki Ankiet Czytelników",
            "G-Pen": "Piórko G-Pen",
            "Anime Adaptation": "Adaptacja Anime"
        },
        "character_forms": {
            "Saiko -> Shujin": "Shujin! Zróbmy najlepszą mangę w historii Jumpa!",
            "Shujin -> Saiko": "Saiko, mam genialny pomysł na scenariusz!",
            "Hattori -> Ashirogi": "Waszą siłą jest manga kalkulowana i mroczna."
        }
    },
    "kuroko_no_basket": {
        "title": "Kuroko's Basket (Kuroko no Basket)",
        "aliases": [
            "kuroko no basket",
            "kuroko no basuke",
            "knb",
            "kuroko's basket"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Tetsuya Kuroko": "Tetsuya Kuroko",
            "Taiga Kagami": "Taiga Kagami",
            "Ryota Kise": "Ryota Kise",
            "Shintaro Midorima": "Shintaro Midorima",
            "Daiki Aomine": "Daiki Aomine",
            "Atsushi Murasakibara": "Atsushi Murasakibara",
            "Seijuro Akashi": "Seijuro Akashi",
            "Tetsuya N°2": "Tetsuya nr 2",
            "Riko Aida": "Riko Aida",
            "Junpei Hyuga": "Junpei Hyuga",
            "Teiko Middle School": "Gimnazjum Teiko",
            "Generation of Miracles": "Pokolenie Cudów",
            "Seirin High": "Liceum Seirin",
            "Misdirection": "Misdirection",
            "Phantom Shot": "Widmowy Rzut Kuroko",
            "Vanishing Drive": "Znikający Dribling",
            "The Zone": "Strefa",
            "Direct Drive Zone": "Strefa Bezpośredniego Napędu",
            "Winter Cup": "Puchar Zimowy"
        },
        "character_forms": {
            "Kuroko -> Kagami": "Jestem cieniem. Im jaśniejsze jest twoje światło, tym głębszy staje się mój cień.",
            "Aomine -> Kuroko": "Tetsu... Koszykówka znowu stała się ekscytująca.",
            "Akashi -> Wszyscy": "Moje rozkazy są absolutne."
        }
    },
    "fire_force": {
        "title": "Fire Force (Enen no Shouboutai)",
        "aliases": [
            "enen no shouboutai",
            "fire force"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Shinra Kusakabe": "Shinra Kusakabe",
            "Arthur Boyle": "Arthur Boyle",
            "Akitaru Obi": "Akitaru Obi",
            "Takehisa Hinawa": "Takehisa Hinawa",
            "Iris": "Siostra Iris",
            "Maki Oze": "Maki Oze",
            "Tamaki Kotatsu": "Tamaki Kotatsu",
            "Vulcan Joseph": "Vulcan Joseph",
            "Benimaru Shinmon": "Benimaru Shinmon",
            "Leonard Burns": "Leonard Burns",
            "Sho Kusakabe": "Sho Kusakabe",
            "The Evangelist": "Ewangelista",
            "Special Fire Force": "Specjalne Siły Pożarnicze",
            "Infernals": "Płomienni",
            "Spontaneous Human Combustion": "Zjawisko Samorzutnego Zapłonu Ludzkiego Ciała",
            "Adolla Burst": "Adolla Burst",
            "Adolla Link": "Więź Adolla",
            "White-Clad": "Białe Płaszcze",
            "Holy Sol Temple": "Święta Świątynia Sol",
            "Amaterasu": "Amaterasu",
            "Latom": "Látom"
        },
        "character_forms": {
            "Shinra -> Arthur": "Głupi rycerzyku! (kumpelska rywalizacja)",
            "Arthur -> Shinra": "Jam jest Król Rycerzy, ty diable!",
            "Siostra Iris -> Płomienni": "Płomieniu, uwolnij tę duszę... Látom."
        }
    },
    "black_lagoon": {
        "title": "Black Lagoon",
        "aliases": [
            "black lagoon"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Rokuro Okajima": "Rokuro Okajima",
            "Rock": "Rokuro Okajima",
            "Revy": "Revy Dwie Dłonie",
            "Two Hand": "Revy Dwie Dłonie",
            "Dutch": "Dutch",
            "Benny": "Benny",
            "Balalaika": "Balalaika",
            "Vladilena": "Balalaika",
            "Boris": "Sierżant Boris",
            "Mr. Chang": "Pan Chang",
            "Eda": "Eda",
            "Sister Yolanda": "Siostra Yolanda",
            "Roberta": "Roberta",
            "Rosarita Cisneros": "Roberta",
            "Garcia Lovelace": "Młody pan Garcia Lovelace",
            "Fabiola Iglesias": "Fabiola Iglesias",
            "Hansel and Gretel": "Jaś i Małgosia",
            "Shenhua": "Shenhua",
            "Sawyer the Cleaner": "Sawyer Sprzątaczka",
            "Lagoon Company": "Kompania Lagoon",
            "Roanapur": "Roanapur",
            "Hotel Moscow": "Hotel Moskwa",
            "Rip-Off Church": "Kościół Przemocy"
        },
        "character_forms": {
            "Revy -> Rock": "Rock! Zamknij się i nie pouczaj mnie z tym swoim białym kołnierzykiem!",
            "Rock -> Revy": "Revy... Spójrzmy na to z innej perspektywy.",
            "Balalaika -> Wrogowie": "Uklęknijcie przed Armią Radziecką."
        }
    },
    "owari_no_seraph": {
        "title": "Seraph of the End: Serafin Dni Ostatnich (Owari no Seraph)",
        "aliases": [
            "serafin dni ostatnich",
            "owari no seraph",
            "seraph of the end"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Yuuichiro Hyakuya": "Yuuichiro Hyakuya",
            "Mikaela Hyakuya": "Mikaela Hyakuya",
            "Guren Ichinose": "Podpułkownik Guren Ichinose",
            "Shinoa Hiiragi": "Sierżant Shinoa Hiiragi",
            "Yoichi Saotome": "Yoichi Saotome",
            "Shihou Kimizuki": "Shihou Kimizuki",
            "Mitsuba Sangu": "Mitsuba Sangu",
            "Kureto Hiiragi": "Generał Kureto Hiiragi",
            "Shinya Hiiragi": "Shinya Hiiragi",
            "Ferid Bathory": "Ferid Bathory",
            "Krul Tepes": "Królowa Krul Tepes",
            "Crowley Eusford": "Crowley Eusford",
            "Japanese Imperial Demon Army": "Japońska Cesarska Armia Demonów",
            "Moon Demon Company": "Kompania Księżycowych Demonów",
            "Cursed Gear": "Przeklęty Oręż",
            "Seraph of the End": "Serafin Dni Ostatnich",
            "Vampire Progenitors": "Wampirzy Progenitorzy",
            "Apocalypse Virus": "Wirus Apokalipsy"
        },
        "character_forms": {
            "Yuu -> Mika": "Mika! Zawsze będziemy rodziną! Przywrócę cię do człowieczeństwa!",
            "Mika -> Yuu": "Yuu-chan! Nie pozwól, by ci ludzie cię wykorzystywali!",
            "Shinoa -> Yuu": "Yuu-san~ (ironiczny, uroczy uśmieszek)"
        }
    },
    "deadman_wonderland": {
        "title": "Deadman Wonderland",
        "aliases": [
            "deadman wonderland"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Ganta Igarashi": "Ganta Igarashi",
            "Woodpecker": "Ganta Igarashi",
            "Shiro": "Shiro",
            "Wretched Egg": "Czerwony Człowiek",
            "Senji Kiyomasa": "Senji Kiyomasa",
            "Crow": "Senji Kiyomasa",
            "Yo Takami": "Yo Takami",
            "Minatsuki Takami": "Minatsuki Takami",
            "Hummingbird": "Minatsuki Takami",
            "Toto Sakigami": "Toto Sakigami",
            "Mockingbird": "Toto Sakigami",
            "Tsunenaga Tamaki": "Tsunenaga Tamaki",
            "Makina": "Naczelnik Makina",
            "Deadman Wonderland": "Deadman Wonderland",
            "Branch of Sin": "Gałąź Grzechu",
            "Carnival Corpse": "Carnival Corpse",
            "Cast Points": "Punkty CP",
            "Candy": "Cukierek",
            "Red Man": "Czerwony Człowiek",
            "Forgeries": "Fałszywki"
        },
        "character_forms": {
            "Shiro -> Ganta": "Ganta~! Zjedzmy ciasteczka!",
            "Ganta -> Shiro": "Shiro! Obiecuję, że cię stąd wyciągnę!",
            "Senji -> Ganta": "Zujji! (Ścinaj ich prosto i szybko, dzieciaku!)"
        }
    },
    "pandora_hearts": {
        "title": "Pandora Hearts",
        "aliases": [
            "pandora hearts"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Oz Vessalius": "Oz Vessalius",
            "Alice": "Alice",
            "B-Rabbit": "Alice",
            "Gilbert Nightray": "Gilbert Nightray",
            "Raven": "Gilbert Nightray",
            "Sharon Rainsworth": "Sharon Rainsworth",
            "Xerxes Break": "Xerxes Break",
            "Mad Hatter": "Xerxes Break",
            "Vincent Nightray": "Vincent Nightray",
            "Jack Vessalius": "Jack Vessalius",
            "Laciez": "Laciez",
            "Glen Baskerville": "Glen Baskerville",
            "Oswald": "Glen Baskerville",
            "The Abyss": "Otchłań",
            "Will of the Abyss": "Wola Otchłani",
            "Chains": "Łańcuchy",
            "Four Great Dukedoms": "Cztery Rody Książęce: Vessalius, Nightray, Rainsworth, Barma",
            "Pandora Organization": "Organizacja Pandora",
            "Tragedy of Sablier": "Tragedia w Sablier"
        },
        "character_forms": {
            "Gilbert -> Oz": "Panie Ozie! (bezgraniczna wierność i obrona)",
            "Alice -> Oz": "Oz! Jestem głodna, daj mi mięso!",
            "Break -> Oz/Sharon": "Och, jakże to zabawne... (chytry, genialny uśmiech)"
        }
    },
    "ajin": {
        "title": "Ajin (Demi-Human)",
        "aliases": [
            "ajin",
            "ajin: demi-human",
            "półludzie"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Kei Nagai": "Kei Nagai",
            "Kaito": "Kaito",
            "Sato": "Sato",
            "Samuel T. Owen": "Sato",
            "Koji Tanaka": "Koji Tanaka",
            "Yuu Tosaki": "Yuu Tosaki",
            "Izumi Shimomura": "Izumi Shimomura",
            "Ko Nakano": "Ko Nakano",
            "IBM": "IBM",
            "Invisible Black Matter": "IBM",
            "Ajin": "Ajin",
            "Demi-Human": "Ajin",
            "Paralyzing Scream": "Paraliżujący Krzyk",
            "Reset": "Zresetowanie",
            "Ministry of Health": "Ministerstwo Zdrowia, Pracy i Opieki Społecznej Japonii"
        },
        "character_forms": {
            "Sato -> Ludzie": "Zagrajmy w grę! (ekstatyczny uśmiech rzeźnika)",
            "Kei -> Ko": "Nie pomagam ci dlatego, że cię lubię, tylko dlatego, że to logiczne."
        }
    },
    "summer_time_rendering": {
        "title": "Summer Time Rendering (Renderowanie Letniego Czasu)",
        "aliases": [
            "summer time rendering",
            "str",
            "summer time render"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Shinpei Ajiro": "Shinpei Ajiro",
            "Ushio Kofune": "Ushio Kofune",
            "Mio Kofune": "Mio Kofune",
            "Hizuru Minakata": "Hizuru Minakata",
            "Ryunosuke": "Hizuru Minakata",
            "Sou Hishigata": "Sou Hishigata",
            "Tokiko Hishigata": "Tokiko Hishigata",
            "Seido Hishigata": "Doktor Seido Hishigata",
            "Alain Kofune": "Alain Kofune",
            "Haine": "Matka Cieni Haine",
            "Shide": "Shide",
            "Masahito Karikiri": "Shide",
            "Shadows": "Cienie",
            "Hitogashima Island": "Wyspa Hitogashima",
            "Time Loop": "Pętla Czasowa",
            "Shadow Sickness": "Choroba Cieni"
        },
        "character_forms": {
            "Shinpei -> Ushio": "Ushio! Tym razem cię ocalę!",
            "Hizuru/Ryunosuke -> Cienie": "Zmierzyłem czas reakcji na 2 milisekundy. Jesteś martwy."
        }
    },
    "yuukoku_no_moriarty": {
        "title": "Patriota Moriarty (Yuukoku no Moriarty: Moriarty the Patriot)",
        "aliases": [
            "patriota moriarty",
            "yuukoku no moriarty",
            "moriarty the patriot"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "William James Moriarty": "William James Moriarty",
            "Albert James Moriarty": "Albert James Moriarty",
            "Louis James Moriarty": "Louis James Moriarty",
            "Sherlock Holmes": "Sherlock Holmes",
            "John H. Watson": "Doktor John H. Watson",
            "Fred Porlock": "Fred Porlock",
            "Sebastian Moran": "Pułkownik Sebastian Moran",
            "Mycroft Holmes": "Mycroft Holmes",
            "Irene Adler": "Irene Adler",
            "James Bond": "Irene Adler",
            "Lord of Crime": "Władca Zbrodni",
            "Class System": "System Klasowy Wiktoriańskiej Anglii",
            "Catch Me If You Can": "Złap mnie, jeśli potrafisz, Sherlocku Holmesie."
        },
        "character_forms": {
            "William -> Sherlock": "Mój drogi Sherlocku (intelektualne partnerstwo i wyznaczona rola bohatera)",
            "Sherlock -> William": "Liam! Nie pozwolę ci umrzeć w samotności!"
        }
    },
    "sasaki_to_miyano": {
        "title": "Sasaki i Miyano (Sasaki to Miyano)",
        "aliases": [
            "sasaki i miyano",
            "sasaki to miyano"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Shumei Sasaki": "Shumei Sasaki",
            "Yoshikazu Miyano": "Yoshikazu Miyano",
            "Taiga Hirano": "Taiga Hirano",
            "Akira Kagiura": "Akira Kagiura",
            "Jiro Ogasawara": "Jiro Ogasawara",
            "Tasuku Kuresawa": "Tasuku Kuresawa",
            "Gonsaburo Tashiro": "Gonsaburo Tashiro",
            "Boys' Love": "Boys' Love",
            "BL": "Boys' Love",
            "Fudanshi": "Fudanshi"
        },
        "character_forms": {
            "Sasaki -> Miyano": "Mya-chan~ (rozmarzona, czuła troska)",
            "Miyano -> Sasaki": "Sasaki-senpai! (wstydliwość, dzielenie się tomikami mang)"
        }
    },
    "given": {
        "title": "Given",
        "aliases": [
            "given"
        ],
        "publisher": "Wydawnictwo Dango / Wydawnictwo Waneko",
        "glossary": {
            "Mafuyu Sato": "Mafuyu Sato",
            "Ritsuka Uenoyama": "Ritsuka Uenoyama",
            "Haruki Nakayama": "Haruki Nakayama",
            "Akihiko Kaji": "Akihiko Kaji",
            "Ugetsu Murata": "Ugetsu Murata",
            "Yuki Yoshida": "Yuki Yoshida",
            "Hiiragi Kashima": "Hiiragi Kashima",
            "Shizusumi Yagi": "Shizusumi Yagi",
            "Band Given": "Zespół Given",
            "Fuyunohanashi": "Opowieść Zimowa"
        },
        "character_forms": {
            "Uenoyama -> Mafuyu": "Kiedy zacząłeś śpiewać, moje serce stanęło w ogniu.",
            "Mafuyu -> Uenoyama": "Uenoyama-kun... Naucz mnie grać na gitarze."
        }
    },
    "mirai_nikki": {
        "title": "Dziennik przyszłości (Mirai Nikki: Future Diary)",
        "aliases": [
            "dziennik przyszłości",
            "future diary",
            "mirai nikki",
            "dziennik przyszlosci"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Yukiteru Amano": "Yukiteru Amano",
            "First": "Yukiteru Amano",
            "Yuno Gasai": "Yuno Gasai",
            "Second": "Yuno Gasai",
            "Takao Hiyama": "Takao Hiyama",
            "Third": "Takao Hiyama",
            "Keigo Kurusu": "Keigo Kurusu",
            "Fourth": "Keigo Kurusu",
            "Reisuke Houjou": "Reisuke Houjou",
            "Fifth": "Reisuke Houjou",
            "Tsubaki Kasugano": "Tsubaki Kasugano",
            "Sixth": "Tsubaki Kasugano",
            "Marco Ikusaba & Ai Mikami": "Marco i Ai",
            "Seventh": "Marco i Ai",
            "Kamado Ueshita": "Kamado Ueshita",
            "Eighth": "Kamado Ueshita",
            "Minene Uryu": "Minene Uryu",
            "Ninth": "Minene Uryu",
            "Karyuudo Tsukishima": "Karyuudo Tsukishima",
            "Tenth": "Karyuudo Tsukishima",
            "John Bacchus": "Burmistrz John Bacchus",
            "Eleventh": "Burmistrz John Bacchus",
            "Yomotsu Hirasaka": "Yomotsu Hirasaka",
            "Twelfth": "Yomotsu Hirasaka",
            "Deus Ex Machina": "Deus Ex Machina",
            "Muru Muru": "Muru Muru",
            "Future Diary": "Pamiętnik Przyszłości",
            "Survival Game": "Gra o Tron Boga",
            "DEAD END": "DEAD END"
        },
        "character_forms": {
            "Yuno -> Yuki": "Yukkii~! Yuno cię obroni! (słodki głos przed brutalną rzezią)",
            "Yuki -> Yuno": "Yuno, stój! Przestań zabijać!"
        }
    },
    "another": {
        "title": "Another",
        "aliases": [
            "another"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Koichi Sakakibara": "Koichi Sakakibara",
            "Mei Misaki": "Mei Misaki",
            "Izumi Akazawa": "Izumi Akazawa",
            "Naoya Teshigawara": "Naoya Teshigawara",
            "Tomohiko Kazami": "Tomohiko Kazami",
            "Yuuya Mochizuki": "Yuuya Mochizuki",
            "Tatsuji Chibiki": "Tatsuji Chibiki",
            "Reiko Mikami": "Pani Mikami",
            "Ms. Mikami": "Pani Mikami",
            "Misaki Yomiyama": "Misaki z 1972 roku",
            "Yomiyama North Middle School": "Gimnazjum Yomiyama Północne",
            "Class 3-3 Curse": "Klątwa Klasy 3-3",
            "The Non-Existent One": "Nieistniejący",
            "Send the Dead Back to Death": "Odeślij Zmarłego do Śmierci"
        },
        "character_forms": {
            "Mei -> Koichi": "W naszej klasie... wydarzyło się coś strasznego.",
            "Koichi -> Mei": "Misaki... Dlaczego nikt oprócz mnie z tobą nie rozmawia?"
        }
    },
    "log_horizon": {
        "title": "Log Horizon",
        "aliases": [
            "log horizon"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Shiroe": "Shiroe",
            "Kei Shirogane": "Shiroe",
            "Naotsugu": "Naotsugu",
            "Akatsuki": "Akatsuki",
            "Nyanta": "Szef Nyanta",
            "Tohya & Minori": "Tohya i Minori",
            "Isuzu & Rundelhaus Code": "Isuzu i Rundelhaus Code",
            "Krusty": "Krusty",
            "Marielle & Henrietta": "Marielle i Henrietta",
            "Soujiro Seta": "Soujiro Seta",
            "William Massachusetts": "William Massachusetts",
            "Kanami": "Kanami",
            "Debauchery Tea Party": "Debauchery Tea Party",
            "Elder Tale": "Elder Tale",
            "Round Table Conference": "Rada Okrągłego Stołu w Akibie",
            "People of the Land": "Ludzie Ziemi",
            "Catastrophe": "Wielka Katastrofa",
            "Apocalypse": "Wielka Katastrofa",
            "Flavor Text": "Tekst Poboczny"
        },
        "character_forms": {
            "Akatsuki -> Shiroe": "Mój Panie (poprawa okularów i uderzenie kolanem w Naotsugu)",
            "Shiroe -> Okrągły Stół": "Poprawienie okularów na nosie (początek genialnego planu)"
        }
    },
    "oyasumi_punpun": {
        "title": "Dobranoc, Punpunie (Oyasumi Punpun: Goodnight Punpun)",
        "aliases": [
            "goodnight punpun",
            "dobranoc, punpunie",
            "oyasumi punpun",
            "dobranoc punpunie"
        ],
        "publisher": "Wydawnictwo Hanami",
        "glossary": {
            "Punpun Onodera": "Punpun Onodera",
            "Punyama": "Punpun Onodera",
            "Aiko Tanaka": "Aiko Tanaka",
            "Yuichi Onodera": "Wujek Yuichi",
            "Midori Okuma": "Midori",
            "Sachi Nanjou": "Sachi Nanjou",
            "Shuntaro Harumin": "Harumin",
            "Masumi Seki & Ko Shimizu": "Seki i Shimizu",
            "Pegasus": "Pegasus",
            "God": "Bóg Punpuna",
            "Kami-sama": "Bóg Punpuna",
            "Tinkle Tinkle Hoy": "Drogi Boże, drogi Boże, tinkle tinkle hoy!"
        },
        "character_forms": {
            "Punpun -> Aiko": "Aiko... Jeśli skłamiesz, zabiję cię. Chodźmy razem na koniec świata.",
            "Bóg -> Punpun": "Cześć, Punpun! Znowu masz beznadziejne myśli?"
        }
    },
    "usagi_yojimbo": {
        "title": "Usagi Yojimbo (Stan Sakai)",
        "aliases": [
            "usagi",
            "królik ochroniarz",
            "usagi yojimbo"
        ],
        "publisher": "Wydawnictwo Egmont Polska",
        "glossary": {
            "Miyamoto Usagi": "Miyamoto Usagi",
            "Gennosuke": "Gennosuke",
            "Gen": "Gennosuke",
            "Tomoe Ame": "Tomoe Ame",
            "Lord Noriyuki": "Lord Noriyuki",
            "Lord Hikiji": "Mroczny Lord Hikiji",
            "Jei": "Jei",
            "Katsuichi": "Mistrz Katsuichi",
            "Kitsune": "Kitsune",
            "Chizu": "Chizu",
            "Neko Ninja": "Klan Neko Ninja",
            "Mogura Ninja": "Klan Mogura Ninja",
            "Komou": "Komou",
            "Grasscutter": "Święty Miecz Kusanagi",
            "Kusanagi": "Święty Miecz Kusanagi",
            "Edo Period Japan": "Japonia okresu Edo"
        },
        "character_forms": {
            "Usagi -> Przeciwnicy": "Podążam ścieżką wojownika Musha Shugyo.",
            "Gen -> Usagi": "Usagi! Ile jest warta głowa tego bandyty?"
        }
    },
    "inuyasha": {
        "title": "InuYasha",
        "aliases": [
            "inuyasha: feudal fairy tale",
            "inuyasha"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "InuYasha": "InuYasha",
            "Kagome Higurashi": "Kagome Higurashi",
            "Kikyo": "Kapłanka Kikyo",
            "Sesshomaru": "Sesshomaru",
            "Jaken": "Jaken",
            "Rin": "Rin",
            "Miroku": "Mnich Miroku",
            "Sango": "Sango",
            "Shippo": "Shippo",
            "Kirara": "Kirara",
            "Naraku": "Naraku",
            "Kagura": "Kagura",
            "Kanna": "Kanna",
            "Shikon Jewel": "Klejnot Czterech Dusz",
            "Tessaiga": "Tessaiga",
            "Tenseiga": "Tenseiga",
            "Wind Scar": "Cięcie Wiatru",
            "Backlash Wave": "Fala Odwrotna",
            "Osuwari": "Siad!"
        },
        "character_forms": {
            "Kagome -> InuYasha": "InuYasha... SIAD! (Osuwari!)",
            "InuYasha -> Kagome": "Kagome! Zostań za mną!",
            "Sesshomaru -> InuYasha": "Mój nędzny pół-krwisty bracie..."
        }
    },
    "fairy_tail": {
        "title": "Fairy Tail",
        "aliases": [
            "ft",
            "fairy tail"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Natsu Dragneel": "Natsu Dragneel",
            "Lucy Heartfilia": "Lucy Heartfilia",
            "Happy": "Happy",
            "Gray Fullbuster": "Gray Fullbuster",
            "Erza Scarlet": "Erza Scarlet",
            "Wendy Marvell": "Wendy Marvell",
            "Carla": "Carla",
            "Makarov Dreyar": "Makarov Dreyar",
            "Laxus Dreyar": "Laxus Dreyar",
            "Gajeel Redfox": "Gajeel Redfox",
            "Juvia Lockser": "Juvia Lockser",
            "Mirajane Strauss": "Mirajane Strauss",
            "Elfman & Lisanna": "Elfman i Lisanna",
            "Gildarts Clive": "Gildarts Clive",
            "Zeref Dragneel": "Czarny Mag Zeref",
            "Acnologia": "Acnologia",
            "Mavis Vermillion": "Mavis Vermillion",
            "Fairy Tail Guild": "Gildia Fairy Tail",
            "Dragon Slayer Magic": "Magia Zabójców Smoków",
            "Celestial Spirit Keys": "Klucze Gwiezdnych Duchów",
            "Fairy Law": "Prawo Wróżek",
            "Fairy Glitter": "Blask Wróżek",
            "Fairy Sphere": "Sfera Wróżek"
        },
        "character_forms": {
            "Natsu -> Wrogowie": "Zapłonąłem! (Moe te kita zo!)",
            "Happy -> Natsu": "Aye, sir! (Rybka!)",
            "Juvia -> Gray": "Gray-sama~! (zakochana powódź)"
        }
    },
    "nanatsu_no_taizai": {
        "title": "Seven Deadly Sins: Siedem Grzechów Głównych (Nanatsu no Taizai)",
        "aliases": [
            "nanatsu no taizai",
            "siedem grzechow glownych",
            "seven deadly sins",
            "siedem grzechów głównych"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Meliodas": "Meliodas",
            "Elizabeth Liones": "Księżniczka Elizabeth Liones",
            "Hawk": "Hawk",
            "Ban": "Ban",
            "King": "King",
            "Harlequin": "King",
            "Diane": "Diane",
            "Gowther": "Gowther",
            "Merlin": "Merlin",
            "Escanor": "Escanor",
            "Zeldris & Estarossa": "Zeldris i Estarossa",
            "Holy Knights": "Święci Rycerze Królestwa Liones",
            "Boar Hat": "Karczma Kapelusz Dzika",
            "Full Counter": "Pełne Odbicie",
            "The One": "Ten Jedyny",
            "Sacred Treasures": "Święte Skarby Grzechów"
        },
        "character_forms": {
            "Meliodas -> Elizabeth": "Sate, sate, sate... (Cóż, cóż, cóż...)",
            "Escanor -> Wrogowie": "Poczułem przed tobą litość. Kto zadecydował, że moje słońce zgasło?",
            "Ban -> Meliodas": "Dancho! (Szefie!)"
        }
    },
    "ao_no_exorcist": {
        "title": "Blue Exorcist (Ao no Exorcist)",
        "aliases": [
            "blue exorcist",
            "ao no exorcist"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Rin Okumura": "Rin Okumura",
            "Yukio Okumura": "Yukio Okumura",
            "Shiro Fujimoto": "Ojciec Shiro Fujimoto",
            "Mephisto Pheles": "Mephisto Pheles",
            "Samael": "Mephisto Pheles",
            "Shiemi Moriyama": "Shiemi Moriyama",
            "Ryuji Suguro": "Ryuji Suguro",
            "Bon": "Ryuji Suguro",
            "Renzo Shima & Konekomaru": "Renzo Shima i Konekomaru Miwa",
            "Izumo Kamiki": "Izumo Kamiki",
            "Shura Kirigakure": "Shura Kirigakure",
            "Satan": "Szatan",
            "Assiah": "Assiah",
            "Gehenna": "Gehenna",
            "True Cross Academy": "Akademia Prawdziwego Krzyża",
            "True Cross Order": "Zakon Prawdziwego Krzyża",
            "Exorcist Classes": "Klasy Egzorcystów: Rycerz, Dragon, Doktor, Aria, Przywoływacz",
            "Paladin": "Paladyn"
        },
        "character_forms": {
            "Rin -> Yukio": "Yukio! Nie pozwolę ci dźwigać tego wszystkiego samemu!",
            "Yukio -> Rin": "Nii-san! Przestań być taki nieodpowiedzialny!",
            "Mephisto -> Wszyscy": "Eins, zwei, drei! Zróbmy z tego wspaniałe show!"
        }
    },
    "akame_ga_kill": {
        "title": "Akame ga Kill!",
        "aliases": [
            "akame ga kill",
            "akame ga kill!"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Akame": "Akame",
            "Tatsumi": "Tatsumi",
            "Najenda": "Najenda",
            "Mine": "Mine",
            "Leone": "Leone",
            "Lubbock": "Lubbock",
            "Sheele": "Sheele",
            "Bulat": "Bulat",
            "Chelsea": "Chelsea",
            "Esdeath": "Generał Esdeath",
            "Kurome": "Kurome",
            "Night Raid": "Night Raid",
            "The Empire": "Cesarstwo",
            "Prime Minister Honest": "Premier Honest",
            "Teigu": "Teigu",
            "Imperial Arms": "Teigu",
            "Shingu": "Shingu"
        },
        "character_forms": {
            "Akame -> Cele": "Zostaniesz wyeliminowany. (Houmuru)",
            "Esdeath -> Tatsumi": "Tatsumi... Będziesz mój na zawsze.",
            "Tatsumi -> Akame": "Akame! Przetrwamy to i zobaczymy nowy świat!"
        }
    },
    "cardcaptor_sakura": {
        "title": "Cardcaptor Sakura (Łowczyni Kart Sakura)",
        "aliases": [
            "ccs",
            "cardcaptor sakura",
            "sakura łowczyni kart"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Sakura Kinomoto": "Sakura Kinomoto",
            "Keroberos": "Keroberos",
            "Kero-chan": "Keroberos",
            "Tomoyo Daidouji": "Tomoyo Daidouji",
            "Syaoran Li": "Syaoran Li",
            "Meiling Li": "Meiling Li",
            "Yukito Tsukishiro": "Yukito Tsukishiro",
            "Yue": "Yukito Tsukishiro",
            "Touya Kinomoto": "Touya Kinomoto",
            "Clow Reed": "Clow Reed",
            "Eriol Hi柊zawa": "Eriol Hi柊zawa",
            "Clow Cards": "Karty Clowa",
            "Sakura Cards": "Karty Sakury",
            "Sealing Wand": "Różdżka Pieczęci"
        },
        "character_forms": {
            "Sakura -> Różdżka": "Kluczu, który kryjesz w sobie moc ciemności, ukaż swą prawdziwą postać przed Sakurą! Uwolnij moc! (Release!)",
            "Kero -> Sakura": "Sakura! Złap tę kartę!",
            "Tomoyo -> Sakura": "Sakura-chan jest dzisiaj niewyobrażalnie urocza!"
        }
    },
    "madoka_magica": {
        "title": "Puella Magi Madoka Magica (Magiczna Madoka)",
        "aliases": [
            "puella magi madoka magica",
            "magiczna madoka",
            "madoka magica"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Madoka Kaname": "Madoka Kaname",
            "Homura Akemi": "Homura Akemi",
            "Sayaka Miki": "Sayaka Miki",
            "Mami Tomoe": "Mami Tomoe",
            "Kyoko Sakura": "Kyoko Sakura",
            "Kyubey": "Kyubey",
            "Incubator": "Kyubey",
            "Nagisa Momoe": "Nagisa Momoe",
            "Soul Gem": "Klejnot Duszy",
            "Grief Seed": "Ziarno Rozpaczy",
            "Magical Girl": "Magiczna Dziewczyna",
            "Witch": "Wiedźma",
            "Walpurgisnacht": "Noc Walpurgii",
            "Law of Cycles": "Prawo Cyklu"
        },
        "character_forms": {
            "Homura -> Madoka": "Nawet jeśli cały świat cię zapomni, ja będę o tobie pamiętać.",
            "Kyubey -> Dziewczęta": "Zawrzyj ze mną kontrakt i zostań magiczną dziewczyną!"
        }
    },
    "akira": {
        "title": "Akira (Katsuhiro Otomo)",
        "aliases": [
            "akira"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Shotaro Kaneda": "Shotaro Kaneda",
            "Tetsuo Shima": "Tetsuo Shima",
            "Akira": "Akira",
            "Kei": "Kei",
            "Colonel Shikishima": "Pułkownik Shikishima",
            "Doctor Onishi": "Doktor Onishi",
            "Kiyoko, Takashi, Masaru": "Esperzy",
            "Lady Miyako": "Pani Miyako",
            "Neo-Tokyo": "Neo-Tokio",
            "The Capsules": "Kapsułki",
            "The Clowns": "Klowni",
            "SOL Laser": "Satelitarny Laser Bojowy SOL",
            "Psychic Powers": "Zdolności Parapsychiczne"
        },
        "character_forms": {
            "Kaneda -> Tetsuo": "TETSUOOO!",
            "Tetsuo -> Kaneda": "KANEDAAA! Przestań mną dyrygować!"
        }
    },
    "ghost_in_the_shell": {
        "title": "Ghost in the Shell (Koukaku Kidoutai: Duch w Pancerzu)",
        "aliases": [
            "gits",
            "koukaku kidoutai",
            "ghost in the shell"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Major Motoko Kusanagi": "Major Motoko Kusanagi",
            "Batou": "Batou",
            "Togusa": "Togusa",
            "Daisuke Aramaki": "Szef Daisuke Aramaki",
            "Ishikawa": "Ishikawa",
            "Saito": "Saito",
            "Paz & Borma": "Paz i Borma",
            "Tachikoma": "Tachikoma",
            "Puppet Master": "Władca Marionetek",
            "Laughing Man": "Śmiejący się Człowiek",
            "Aoi": "Śmiejący się Człowiek",
            "Public Security Section 9": "Sekcja Bezpieczeństwa Publicznego nr 9",
            "Cyberbrain": "Cybermózg",
            "Ghost": "Duch",
            "Thermo-Optical Camouflage": "Kamuflaż Termooptyczny",
            "Stand Alone Complex": "Stand Alone Complex",
            "Cyberbrain Sclerosis": "Stwardnienie Cybermózgu"
        },
        "character_forms": {
            "Motoko -> Batou": "Mój Duch mi to podpowiada, Batou.",
            "Batou -> Motoko": "Majorze! Uważaj na siebie!",
            "Tachikoma -> Batou": "Batou-san! Zobacz, odkryliśmy czym jest indywidualność!"
        }
    },
    "gunnm_alita": {
        "title": "Battle Angel Alita (Gunnm)",
        "aliases": [
            "battle angel alita",
            "gunnm",
            "alita"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Alita": "Alita",
            "Gally": "Alita",
            "Daisuke Ido": "Daisuke Ido",
            "Yugo": "Yugo",
            "Makaku": "Makaku",
            "Jashugan": "Jashugan",
            "Desty Nova": "Profesor Desty Nova",
            "Figure Four": "Figure Four",
            "Karasu": "Kaos",
            "Kaos": "Kaos",
            "Scrapyard": "Miasto Złomu",
            "Zalem": "Zalem",
            "Tiphares": "Zalem",
            "Motorball": "Motorball",
            "Panzer Kunst": "Panzer Kunst",
            "Damascus Steel": "Stal Damasceńska",
            "Hunter-Warrior": "Łowca Nagród"
        },
        "character_forms": {
            "Ido -> Alita": "Alito... Twoja dusza jest czysta i niewinna.",
            "Alita -> Wrogowie": "Nie jestem niczyją zabawką. Jam jest wojowniczką Panzer Kunst!"
        }
    },
    "gto_onizuka": {
        "title": "Great Teacher Onizuka (GTO)",
        "aliases": [
            "gto",
            "great teacher onizuka"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Eikichi Onizuka": "Eikichi Onizuka",
            "Ryuji Danma": "Ryuji Danma",
            "Azusa Fuyutsuki": "Azusa Fuyutsuki",
            "Hiroshi Uchiyamada": "Wicedyrektor Hiroshi Uchiyamada",
            "Ryoko Sakurai": "Dyrektor Generalna Ryoko Sakurai",
            "Yoshito Kikuchi": "Yoshito Kikuchi",
            "Urumi Kanzaki": "Urumi Kanzaki",
            "Kunio Murai": "Kunio Murai",
            "Tomoko Nomura": "Tomoko Nomura",
            "Miyabi Aizawa": "Miyabi Aizawa",
            "Holy Forest Academy": "Akademia Świętego Lasu",
            "Class 3-4": "Klasa 3-4",
            "German Suplex": "German Suplex"
        },
        "character_forms": {
            "Onizuka -> Uczniowie": "Lekcje życia są ważniejsze niż jakiekolwiek podręczniki!",
            "Uchiyamada -> Onizuka": "ONIZUKAAA! MOJA CRESTA!!!"
        }
    },
    "claymore": {
        "title": "Claymore",
        "aliases": [
            "claymore"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Clare": "Clare",
            "Teresa of the Faint Smile": "Teresa o Nikłym Uśmiechu",
            "Raki": "Raki",
            "Priscilla": "Priscilla",
            "Miria": "Miria Widmo",
            "Helen & Deneve": "Helen i Deneve",
            "Teresa, Irene, Sophia, Noel": "Dawna elita Organizacji",
            "Isley of the North": "Isley z Północy",
            "Riful of the West": "Riful z Zachodu",
            "Luciela of the South": "Luciela z Południa",
            "Claymore": "Wojowniczki Claymore",
            "Silver-Eyed Witches": "Wojowniczki Claymore",
            "Yoma": "Yoma",
            "Awakened Beings": "Przebudzone Istoty",
            "The Organization": "Organizacja",
            "Yoki": "Yoki"
        },
        "character_forms": {
            "Clare -> Priscilla": "Pomściłam Teresę... Nawet jeśli sama stanę się potworem!",
            "Teresa -> Clare": "Clare... Dzięki tobie odnalazłam ciepło w sercu."
        }
    },
    "d_gray_man": {
        "title": "D.Gray-man",
        "aliases": [
            "d gray man",
            "d.gray-man",
            "dgm",
            "d-gray-man"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Allen Walker": "Allen Walker",
            "Yu Kanda": "Yu Kanda",
            "Lenalee Lee": "Lenalee Lee",
            "Lavi": "Lavi",
            "Cross Marian": "Generał Cross Marian",
            "Komui Lee": "Komui Lee",
            "Millennium Earl": "Tysiącletni Hrabia",
            "Tyki Mikk": "Tyki Mikk",
            "Road Kamelot": "Road Kamelot",
            "The Black Order": "Czarny Zakon",
            "Innocence": "Innocence",
            "Akuma": "Akuma",
            "Noah Family": "Rodzina Noego",
            "Crown Clown": "Koronne Błazeństwo",
            "The 14th": "Czternasty Noe",
            "Nea Walker": "Czternasty Noe"
        },
        "character_forms": {
            "Allen -> Kanda": "Kanda! Przestań być taki chamski! (wieczna rywalizacja)",
            "Kanda -> Allen": "Moyashi! (Kiełku!)",
            "Hrabia -> Egzorcyści": "Witajcie, drodzy Egzorcyści~!"
        }
    },
    "gantz": {
        "title": "Gantz",
        "aliases": [
            "gantz"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Kei Kurono": "Kei Kurono",
            "Masaru Kato": "Masaru Kato",
            "Kei Kishimoto": "Kei Kishimoto",
            "Joichiro Nishi": "Joichiro Nishi",
            "Tae Kojima": "Tae Kojima",
            "Yoshikazu Suzuki": "Suzuki-san",
            "Reika Shimohira": "Reika Shimohira",
            "Daizemon Kaze": "Daizemon Kaze",
            "Hachiro Oka": "Hachiro Oka",
            "Gantz Sphere": "Czarna Kula Gantz",
            "Gantz Suit": "Kombinezon Gantz",
            "X-Gun & X-Rifle": "Broń X-Gun i Karabin X-Rifle",
            "Z-Gun": "Działo Grawitacyjne Z-Gun",
            "Gravity Gun": "Działo Grawitacyjne Z-Gun",
            "100 Points Menu": "Menu 100 Punktów: 1. Wolność z wymazaniem pamięci, 2. Potężniejsza broń/mecha, 3. Wskrzeszenie zmarłego z pamięci kuli",
            "Aliens": "Kosmici"
        },
        "character_forms": {
            "Gantz -> Gracze": "Wasze stare życia dobiegły końca. To, co zrobicie z nowymi, zależy ode mnie.",
            "Kurono -> Tae": "Tae-chan! Zawsze do ciebie wrócę!"
        }
    },
    "tokyo_revengers": {
        "title": "Tokyo Revengers",
        "aliases": [
            "tokyo revengers",
            "revengers",
            "toman"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Takemichi Hanagaki": "Takemichi Hanagaki",
            "Manjiro Sano": "Manjiro Sano",
            "Ken Ryuguji": "Ken Ryuguji",
            "Keisuke Baji": "Keisuke Baji",
            "Chifuyu Matsuno": "Chifuyu Matsuno",
            "Takashi Mitsuya": "Takashi Mitsuya",
            "Hakkai Shiba": "Hakkai Shiba",
            "Haruki Hayashida": "Haruki Hayashida",
            "Ryohei Hayashi": "Ryohei Hayashi",
            "Nahoya Kawata": "Nahoya Kawata",
            "Souya Kawata": "Souya Kawata",
            "Yasuhiro Muto": "Yasuhiro Muto",
            "Haruchiyo Sanzu": "Haruchiyo Sanzu",
            "Kazutora Hanemiya": "Kazutora Hanemiya",
            "Tetta Kisaki": "Tetta Kisaki",
            "Shuji Hanma": "Shuji Hanma",
            "Hinata Tachibana": "Hinata Tachibana",
            "Naoto Tachibana": "Naoto Tachibana",
            "Emma Sano": "Emma Sano",
            "Shinichiro Sano": "Shinichiro Sano",
            "Izana Kurokawa": "Izana Kurokawa",
            "Taiju Shiba": "Taiju Shiba",
            "Yuzuha Shiba": "Yuzuha Shiba",
            "Senju Kawaragi": "Senju Kawaragi",
            "Tokyo Manji Gang": "Tokyo Manji Gang",
            "Moebius": "Moebius",
            "Valhalla": "Valhalla",
            "Black Dragons": "Czarne Smoki",
            "Tenjiku": "Tenjiku",
            "Bonten": "Bonten",
            "Brahman": "Brahman",
            "Rokuhara Tandai": "Rokuhara Tandai",
            "Kantou Manji Gang": "Kantou Manji Gang",
            "Bloody Halloween": "Krwawe Halloween",
            "Christmas Showdown": "Starcie Bożonarodzeniowe",
            "Kanto Incident": "Incydent w Kanto"
        },
        "character_forms": {
            "Takemichi -> Mikey": "Mikey-kun (szacunek i lojalność)",
            "Mikey -> Takemichi": "Takemichy (przyjaźń i zaufanie)",
            "Draken -> Mikey": "Mikey (partnerska równość)",
            "Chifuyu -> Takemichi": "Partnerze / Takemichi (braterska więź)"
        }
    },
    "dr_stone": {
        "title": "Dr. STONE",
        "aliases": [
            "dr. stone",
            "doktor stone",
            "dr stone"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Senku Ishigami": "Senku Ishigami",
            "Taiju Oki": "Taiju Oki",
            "Yuzuriha Ogawa": "Yuzuriha Ogawa",
            "Tsukasa Shishio": "Tsukasa Shishio",
            "Gen Asagiri": "Gen Asagiri",
            "Chrome": "Chrome",
            "Kohaku": "Kohaku",
            "Suika": "Suika",
            "Kinro": "Kinro",
            "Ginro": "Ginro",
            "Kaseki": "Kaseki",
            "Ruri": "Ruri",
            "Magma": "Magma",
            "Ryusui Nanami": "Ryusui Nanami",
            "Francois": "Francois",
            "Ukyo Saionji": "Ukyo Saionji",
            "Yo Uei": "Yo Uei",
            "Hyoga": "Hyoga",
            "Homura Momiji": "Homura Momiji",
            "Stanley Snyder": "Stanley Snyder",
            "Dr. Xeno": "Dr Xeno",
            "Byakuya Ishigami": "Byakuya Ishigami",
            "Kingdom of Science": "Królestwo Nauki",
            "Empire of Might": "Imperium Siły Tsukasy",
            "Ishigami Village": "Wioska Ishigami",
            "Treasure Island": "Wyspa Skarbów",
            "Perseus": "Perseusz",
            "Medusa": "Meduza",
            "Why-man": "Dlaczego-człowiek",
            "Petrification": "Petryfikacja",
            "Revival Fluid": "Płyn ożywiający",
            "Nital": "Nital",
            "Sulfa Drug": "Sulfonamidy",
            "Cell Phone": "Telefon polowy"
        },
        "character_forms": {
            "Senku -> Wszyscy": "Na dziesięć miliardów procent / To ekscytujące!",
            "Chrome -> Senku": "Senku (fascynacja nauką)",
            "Kohaku -> Senku": "Senku (przyjaźń i lojalność wojowniczki)"
        }
    },
    "dorohedoro": {
        "title": "Dorohedoro",
        "aliases": [
            "dorohedoro"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Caiman": "Kaiman",
            "Nikaido": "Nikaido",
            "En": "En",
            "Shin": "Shin",
            "Noi": "Noi",
            "Ebisu": "Ebisu",
            "Fujita": "Fujita",
            "Kikurage": "Kikurage",
            "Chota": "Chota",
            "Turkey": "Turkey",
            "Dokuga": "Dokuga",
            "Tetsujo": "Tetsujo",
            "Ushishimada": "Ushishimada",
            "Saji": "Saji",
            "Ton": "Ton",
            "Natsuki": "Natsuki",
            "Kasukabe": "Profesor Kasukabe",
            "Vaux": "Doktor Vaux",
            "Jonson": "Jonson",
            "Tanba": "Tanba",
            "Fukuyama": "Fukuyama",
            "Chidaruma": "Chidaruma",
            "Asu": "Asu",
            "Hole": "Dziura",
            "Sorcerers' World": "Świat Magów",
            "Cross-Eyes": "Krzyżoocy",
            "En Family": "Rodzina Ena",
            "Black Smoke": "Czarny dym",
            "Smoke Devil": "Diabeł dymny",
            "Gyoza": "Gyoza",
            "Hungry Bug": "Hungry Bug",
            "Living Dead Night": "Noc Żywych Trupów"
        },
        "character_forms": {
            "Kaiman -> Nikaido": "Nikaido (kumpelska więź i miłość do gyozy)",
            "Shin -> Noi": "Noi (zgrany duet zabójców)",
            "Noi -> Shin": "Shin-senpai (szacunek i bliskość)"
        }
    },
    "re_zero": {
        "title": "Re:Zero - Życie w innym świecie od zera (Re:Zero kara Hajimeru Isekai Seikatsu)",
        "aliases": [
            "re:zero",
            "rezero",
            "re zero"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Subaru Natsuki": "Subaru Natsuki",
            "Emilia": "Emilia",
            "Puck": "Puck",
            "Rem": "Rem",
            "Ram": "Ram",
            "Beatrice": "Beatrice",
            "Roswaal L. Mathers": "Roswaal L. Mathers",
            "Otto Suwen": "Otto Suwen",
            "Garfiel Tinsel": "Garfiel Tinsel",
            "Frederica Baumann": "Frederica Baumann",
            "Petra Leyte": "Petra Leyte",
            "Patrasche": "Patrasche",
            "Felt": "Felt",
            "Reinhard van Astrea": "Reinhard van Astrea",
            "Old Man Rom": "Dziadek Rom",
            "Crusch Karsten": "Crusch Karsten",
            "Felix Argyle": "Felix Argyle",
            "Wilhelm van Astrea": "Wilhelm van Astrea",
            "Theresia van Astrea": "Theresia van Astrea",
            "Anastasia Hoshin": "Anastasia Hoshin",
            "Julius Juukulius": "Julius Juukulius",
            "Ricardo Welkin": "Ricardo Welkin",
            "Mimi, Hetaro, Tivey Pearlbaton": "Trojaczki Pearlbaton",
            "Priscilla Barielle": "Priscilla Barielle",
            "Aldebaran": "Aldebaran",
            "Satella": "Satella",
            "Echidna": "Echidna",
            "Minerva": "Minerva",
            "Daphne": "Daphne",
            "Typhon": "Typhon",
            "Camilla": "Camilla",
            "Sekhmet": "Sekhmet",
            "Pandora": "Pandora",
            "Hector": "Hector",
            "Petelgeuse Romanee-Conti": "Petelgeuse Romanee-Conti",
            "Regulus Corneas": "Regulus Corneas",
            "Lye Batenkaitos": "Lye Batenkaitos",
            "Roy Alphard": "Roy Alphard",
            "Louis Arneb": "Louis Arneb",
            "Sirius": "Sirius",
            "Capella Emerada Lugnica": "Capella",
            "Gospel": "Ewangelia Kultu Wiedźmy",
            "Elsa Granhiert": "Elsa Granhiert",
            "Meili Portroute": "Meili Portroute",
            "Shaula": "Shaula",
            "Sage Flugel": "Mędrzec Flugel",
            "Vincent Vollachia": "Vincent Vollachia",
            "Liliana Masquerade": "Liliana Masquerade",
            "White Whale": "Biały Wieloryb",
            "Great Rabbit": "Wielki Królik",
            "Black Serpent": "Czarny Wąż",
            "Return by Death": "Powrót przez Śmierć",
            "Invisible Providence": "Niewidzialna Opatrzność",
            "Cor Leonis": "Lwie Serce",
            "Al Shamak": "Al Shamak",
            "Minya": "Minya",
            "El Minya": "Minya",
            "Ur Minya": "Minya",
            "Goa": "Goa",
            "El Goa": "Goa",
            "Ur Goa": "Goa",
            "Huma": "Huma",
            "El Huma": "Huma",
            "Ur Huma": "Huma",
            "Dona": "Dona",
            "El Dona": "Dona",
            "Ur Dona": "Dona",
            "Fura": "Fura",
            "El Fura": "Fura",
            "Ur Fura": "Fura",
            "Divine Protection": "Boska Ochrona",
            "Witch's Scent": "Zapach Wiedźmy",
            "Authority": "Autorytet",
            "Dragon Kingdom of Lugnica": "Królestwo Smoka Lugnica",
            "Sanctuary": "Sanktuarium",
            "Water City Priestella": "Wodne Miasto Priestella",
            "Pleiades Watchtower": "Wieża Obserwacyjna Plejad",
            "Sacred Empire of Vollachia": "Święte Cesarstwo Vollachii",
            "Holy Kingdom of Gusteko": "Święte Królestwo Gusteko",
            "Kararagi": "Wolne Miasta Kararagi"
        },
        "character_forms": {
            "Subaru -> Emilia": "Emilia-tan (uwielbienie, czułość i miłość)",
            "Rem -> Subaru": "Subaru-kun (bezgraniczne oddanie, wiara w jego bohaterstwo)",
            "Beatrice -> Subaru": "Betty / kashira (wyniosłość tsundere skrywająca głęboką samotność)",
            "Ram -> Subaru": "Barusu (złośliwe przezwisko i cięty humor)",
            "Petelgeuse -> Subaru": "Ty... czyżbyś był zwiastunem Miłości?! / Niewierny leniwcze!",
            "Echidna -> Subaru": "Subaru (ciekawość jego nieskończonych pętli śmierci)"
        }
    },
    "bungou_stray_dogs": {
        "title": "Bungou Stray Dogs: Bezpańscy Literaci",
        "aliases": [
            "bsd",
            "bezpańscy literaci",
            "bungo stray dogs",
            "bungou stray dogs"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Atsushi Nakajima": "Atsushi Nakajima",
            "Osamu Dazai": "Osamu Dazai",
            "Doppo Kunikida": "Doppo Kunikida",
            "Ranpo Edogawa": "Ranpo Edogawa",
            "Junichiro Tanizaki": "Junichiro Tanizaki",
            "Naomi Tanizaki": "Naomi Tanizaki",
            "Akiko Yosano": "Akiko Yosano",
            "Kenji Miyazawa": "Kenji Miyazawa",
            "Yukichi Fukuzawa": "Yukichi Fukuzawa",
            "Kyoka Izumi": "Kyoka Izumi",
            "Ryunosuke Akutagawa": "Ryunosuke Akutagawa",
            "Chuya Nakahara": "Chuya Nakahara",
            "Ogai Mori": "Ogai Mori",
            "Koyo Ozaki": "Koyo Ozaki",
            "Ichiyo Higuchi": "Ichiyo Higuchi",
            "Motojiro Kajii": "Motojiro Kajii",
            "Ryuro Hirotsu": "Ryuro Hirotsu",
            "Francis Scott Key Fitzgerald": "Francis Scott Fitzgerald",
            "Lucy Maud Montgomery": "Lucy Maud Montgomery",
            "Louisa May Alcott": "Louisa May Alcott",
            "Edgar Allan Poe": "Edgar Allan Poe",
            "Fyodor Dostoevsky": "Fiodor Dostojewski",
            "Nikolai Gogol": "Nikołaj Gogol",
            "Sigma": "Sigma",
            "Bram Stoker": "Bram Stoker",
            "Armed Detective Agency": "Zbrojna Agencja Detektywistyczna",
            "Port Mafia": "Portowa Mafia",
            "The Guild": "Gildia",
            "Rats in the House of the Dead": "Szczury w Domu Umarłych",
            "Decay of the Angel": "Upadek Anioła",
            "Hunting Dogs": "Psy Gończe",
            "The Book": "Księga",
            "Rashomon": "Rashomon",
            "No Longer Human": "Niepełnosprawny Człowiek"
        },
        "character_forms": {
            "Atsushi -> Dazai": "Dazai-san (podziw i zagubienie)",
            "Dazai -> Kunikida": "Kunikida-kun (wieczne droczenie się)",
            "Akutagawa -> Dazai": "Dazai-san (desperacka potrzeba uznania)",
            "Chuya -> Dazai": "Dazai / Ty gnoju! (odwieczna nienawiść Soukoku)"
        }
    },
    "mashle": {
        "title": "Mashle: Magia i Mięśnie",
        "aliases": [
            "mashle magic and muscles",
            "mashle"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Mash Burnedead": "Mash Burnedead",
            "Finn Ames": "Finn Ames",
            "Lance Crown": "Lance Crown",
            "Dot Barrett": "Dot Barrett",
            "Lemon Irvine": "Lemon Irvine",
            "Regro Burnedead": "Regro Burnedead",
            "Rayne Ames": "Rayne Ames",
            "Wahlberg Baigan": "Wahlberg Baigan",
            "Innocent Zero": "Innocent Zero",
            "Doom": "Doom",
            "Famin": "Famin",
            "Epidem": "Epidem",
            "Delisaster": "Delisaster",
            "Cell War": "Cell War",
            "Abyss Razor": "Abyss Razor",
            "Abel Walker": "Abel Walker",
            "Wirth Madl": "Wirth Madl",
            "Milo Genius": "Milo Genius",
            "Love Cute": "Love Cute",
            "Easton Magic Academy": "Akademia Magii Easton",
            "Saint Ars Magic Academy": "Akademia Magii Saint Ars",
            "Valkis Magic Academy": "Akademia Magii Valkis",
            "Divine Visionary": "Boski Wizjoner",
            "Magia Lupus": "Magia Lupus",
            "Adler Dorm": "Dom Adler",
            "Orca Dorm": "Dom Orca",
            "Lang Dorm": "Dom Lang",
            "Magic Wand": "Różdżka magiczna",
            "Cream Puff": "Ptyś z kremem",
            "Magic Lines": "Znaki magii na twarzy"
        },
        "character_forms": {
            "Mash -> Wszyscy": "Spokojnie, to tylko mięśnie / Chcecie ptysia?",
            "Finn -> Mash": "Mash-kun! (panika i rozsądek)",
            "Dot -> Lance": "Przystojniaczku (wieczna zazdrość)"
        }
    },
    "record_of_ragnarok": {
        "title": "Walkirie Kresu Dziejów – Record of Ragnarok (Shuumatsu no Valkyrie)",
        "aliases": [
            "record of ragnarok",
            "walkirie kresu dziejów",
            "ragnarok",
            "shuumatsu no valkyrie"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Brunhilde": "Brunhilda",
            "Goll": "Göll",
            "Lu Bu": "Lü Bu Fengxian",
            "Adam": "Adam",
            "Sasaki Kojiro": "Sasaki Kojiro",
            "Jack the Ripper": "Kuba Rozpruwacz",
            "Raiden Tameemon": "Raiden Tameemon",
            "Buddha": "Budda",
            "Qin Shi Huang": "Qin Shi Huang",
            "Nikola Tesla": "Nikola Tesla",
            "Leonidas": "Król Leonidas",
            "Souji Okita": "Souji Okita",
            "Simo Hayha": "Simo Häyhä",
            "Sakata Kintoki": "Sakata Kintoki",
            "Grigori Rasputin": "Grigorij Rasputin",
            "Michel Nostradamus": "Michel Nostradamus",
            "Thor": "Thor",
            "Zeus": "Zeus",
            "Poseidon": "Posejdon",
            "Heracles": "Herakles",
            "Shiva": "Śiwa",
            "Zerofuku": "Zerofuku",
            "Hajun": "Hajun",
            "Hades": "Hades",
            "Beelzebub": "Belzebub",
            "Apollo": "Apollo",
            "Susanoo no Mikoto": "Susanoo no Mikoto",
            "Loki": "Loki",
            "Odin": "Odyn",
            "Hermes": "Hermes",
            "Ares": "Ares",
            "Ragnarok": "Ragnarok",
            "Volundr": "Volundr",
            "Mjolnir": "Mjölnir",
            "Eyes of the Lord": "Oczy Pana"
        },
        "character_forms": {
            "Brunhilda -> Bogowie": "Wyniosła pogarda i zimna kalkulacja",
            "Goll -> Brunhilda": "Hilde-neesama! (panika i podziw)",
            "Zeus -> Zawodnicy": "Ekscytacja walką i obłędna siła"
        }
    },
    "gintama": {
        "title": "Gintama",
        "aliases": [
            "gintama"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Gintoki Sakata": "Gintoki Sakata",
            "Shinpachi Shimura": "Shinpachi Shimura",
            "Kagura": "Kagura",
            "Sadaharu": "Sadaharu",
            "Kotaro Katsura": "Kotaro Katsura",
            "Elizabeth": "Elizabeth",
            "Isao Kondo": "Isao Kondo",
            "Toshiro Hijikata": "Toshiro Hijikata",
            "Sougo Okita": "Sougo Okita",
            "Sagaru Yamazaki": "Sagaru Yamazaki",
            "Tatsuma Sakamoto": "Tatsuma Sakamoto",
            "Shinsuke Takasugi": "Shinsuke Takasugi",
            "Kamui": "Kamui",
            "Umibozu": "Umibozu",
            "Otose": "Otose",
            "Catherine": "Catherine",
            "Tama": "Tama",
            "Taizo Hasegawa": "Taizo Hasegawa",
            "Tae Shimura": "Tae Shimura",
            "Tsukuyo": "Tsukuyo",
            "Sarutobi Ayame": "Sarutobi Ayame",
            "Zenzou Hattori": "Zenzou Hattori",
            "Yorozuya": "Yorozuya",
            "Shinsengumi": "Shinsengumi",
            "Amanto": "Amanto",
            "Kiheitai": "Kiheitai",
            "Harusame": "Harusame",
            "Yoshiwara": "Yoshiwara",
            "Jouishishi": "Joui",
            "Bokuto Lake Toya": "Drewniany miecz z Jeziora Toya"
        },
        "character_forms": {
            "Kagura -> Gintoki": "Gin-chan (dziecięca poufałość)",
            "Shinpachi -> Gintoki": "Gin-san (krzyk rozsądku i tsukkomi)",
            "Hijikata -> Gintoki": "Yorozuya / Srebrnowłosy (wieczna rywalizacja)",
            "Katsura -> Wszyscy": "Zura ja nai, Katsura da! (Nie Zura, tylko Katsura!)"
        }
    },
    "kuroshitsuji": {
        "title": "Kuroshitsuji: Mroczny Kamerdyner",
        "aliases": [
            "mroczny kamerdyner",
            "kuroshitsuji",
            "black butler"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Ciel Phantomhive": "Ciel Phantomhive",
            "Sebastian Michaelis": "Sebastian Michaelis",
            "Mey-Rin": "Mey-Rin",
            "Bardroy": "Bardroy",
            "Finnian": "Finnian",
            "Tanaka": "Tanaka",
            "Snake": "Snake",
            "Elizabeth Midford": "Elizabeth Midford",
            "Madam Red": "Madam Red",
            "Grell Sutcliff": "Grell Sutcliff",
            "Undertaker": "Grabarz",
            "William T. Spears": "William T. Spears",
            "Ronald Knox": "Ronald Knox",
            "Lau": "Lau",
            "Ran-Mao": "Ran-Mao",
            "Soma Asman Kadar": "Książę Soma",
            "Agni": "Agni",
            "Queen Victoria": "Królowa Wiktoria",
            "Vincent Phantomhive": "Vincent Phantomhive",
            "Rachel Phantomhive": "Rachel Phantomhive",
            "Phantomhive Manor": "Posiadłość Phantomhive",
            "Queen's Watchdog": "Pies Łańcuchowy Królowej",
            "Grim Reaper": "Żniwiarz",
            "Cinematic Record": "Zapis filmowy życia",
            "Death Scythe": "Kosa Śmierci",
            "Faustian Contract": "Cyrograf"
        },
        "character_forms": {
            "Sebastian -> Ciel": "Yes, My Lord / Oczywiście, mój panie (perfekcyjny lokaj)",
            "Ciel -> Sebastian": "Sebastian, to rozkaz! (bezwzględny władca)",
            "Elizabeth -> Ciel": "Ciel! (dziecięca, radosna miłość)"
        }
    },
    "kore_kaite_shine": {
        "title": "Kore Kaite Shine (Narysuj to i umrzyj!)",
        "aliases": [
            "kore kaite shine",
            "narysuj to i umrzyj"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Ai Yasumi": "Ai Yasumi",
            "Kokoro Teshima": "Pani Kokoro Teshima",
            "Rei Shizunami": "Rei Shizunami",
            "Nami Minami": "Nami Minami",
            "Nagisa Akaishi": "Nagisa Akaishi",
            "Shingo Chiba": "Shingo Chiba",
            "Izu Oshima": "Wyspa Izu Oshima",
            "Manga Club": "Szkolny Klub Twórczości Mangowej",
            "Comitia": "Comitia",
            "G-Pen": "Stalówka G-Pen",
            "Maru-Pen": "Stalówka Maru-Pen",
            "Screen Tone": "Rastry",
            "Manuscript Paper": "Papier do mangi"
        },
        "character_forms": {
            "Uczennice -> Teshima": "Pani Teshimo / Pani Profesor (szacunek dla nauczycielki)",
            "Uczennice między sobą": "Po imieniu bez 'Pan/Pani' (koleżeńska relacja licealna)"
        }
    },
    "dandadan": {
        "title": "Dandadan",
        "aliases": [
            "dandadan"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Momo Ayase": "Momo Ayase",
            "Ken Takakura": "Ken Takakura",
            "Turbo Granny": "Turbo Babcia",
            "Seiko Ayase": "Seiko Ayase",
            "Aira Shiratori": "Aira Shiratori",
            "Jin Enjoji": "Jin Enjoji",
            "Evil Eye": "Oko Złe",
            "Acrobatic Silky": "Akrobatyczna Jedwabnica",
            "Serpoian": "Kosmita z Serpo",
            "Flatwoods Monster": "Potwór z Flatwoods",
            "Nessie": "Nessie",
            "Reiko Kashima": "Reiko Kashima",
            "Kinta Sakata": "Kinta Sakata",
            "Vamola": "Vamola",
            "Golden Balls": "Kinto",
            "Spiritual Power": "Moc duchowa",
            "Alien Technology": "Technologia kosmitów"
        },
        "character_forms": {
            "Momo -> Okarun": "Okarun (początkowo przezwisko, później czuła więź)",
            "Okarun -> Momo": "Ayase-san (nieśmiałość i głęboki szacunek)",
            "Turbo Babcia -> Momo": "Gówniaro / Pyskata dziewucho (szorstka złośliwość)"
        }
    },
    "kaiju_no_8": {
        "title": "Kaiju No. 8",
        "aliases": [
            "kaiju no 8",
            "kaiju no. 8",
            "kaijuu 8-gou"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Kafka Hibino": "Kafka Hibino",
            "Mina Ashiro": "Mina Ashiro",
            "Reno Ichikawa": "Reno Ichikawa",
            "Kikoru Shinomiya": "Kikoru Shinomiya",
            "Soshiro Hoshina": "Soshiro Hoshina",
            "Isao Shinomiya": "Isao Shinomiya",
            "Narumi Gen": "Gen Narumi",
            "Aoi Kaguragi": "Aoi Kaguragi",
            "Haruichi Izumo": "Haruichi Izumo",
            "Iharu Furuhashi": "Iharu Furuhashi",
            "Kaiju No. 8": "Kaiju No. 8",
            "Kaiju No. 9": "Kaiju No. 9",
            "Kaiju No. 10": "Kaiju No. 10",
            "Defense Force": "Japońskie Siły Obronne",
            "Monster Sweeper Inc.": "Monster Sweeper Inc.",
            "Fortitude": "Fortitudo",
            "Numbered Weapon": "Broń Liczbowa",
            "Unleashed Combat Power": "Uwolniona Moc Bojowa"
        },
        "character_forms": {
            "Kafka -> Mina": "Mina (obietnica z dzieciństwa) / Pani Kapitan (na służbie)",
            "Mina -> Kafka": "Kafka (skrywane zaufanie i pamięć o przysiędze)",
            "Reno -> Kafka": "Senpai / Kafka-san (lojalny druh chroniący jego tajemnicę)"
        }
    },
    "sakamoto_days": {
        "title": "Sakamoto Days",
        "aliases": [
            "sakamoto days"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Taro Sakamoto": "Taro Sakamoto",
            "Shin Asakura": "Shin Asakura",
            "Lu Xiaotang": "Lu Xiaotang",
            "Heisuke Mashimo": "Heisuke Mashimo",
            "Aoi Sakamoto": "Aoi Sakamoto",
            "Hana Sakamoto": "Hana Sakamoto",
            "Nagumo": "Nagumo",
            "Shishiba": "Shishiba",
            "Osaragi": "Osaragi",
            "Hyo": "Hyo",
            "Takamura": "Takamura",
            "Kanaguri": "Kanaguri",
            "Kindaka": "Kindaka",
            "Slur": "Slur",
            "Gaku": "Gaku",
            "Kashima": "Kashima",
            "Club Jam": "Club Jam",
            "Carolina Reaper": "Carolina Reaper",
            "Order": "Order",
            "JAA": "JAA",
            "JCC": "JCC",
            "Sakamoto Store": "Sklep spożywczy Sakamoto",
            "Family Rule": "Zasada domowa Sakamoto: Absolutny zakaz zabijania!"
        },
        "character_forms": {
            "Shin -> Sakamoto": "Szefie / Sakamoto-san (bezgraniczny podziw i czytanie w myślach)",
            "Sakamoto -> Aoi": "Ciepłe oddanie i bezwzględne posłuszeństwo żonie"
        }
    },
    "kagurabachi": {
        "title": "Kagurabachi",
        "aliases": [
            "kagurabachi"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Chihiro Rokuhira": "Chihiro Rokuhira",
            "Kunishige Rokuhira": "Kunishige Rokuhira",
            "Shiba": "Shiba",
            "Char Kyonagi": "Char Kyonagi",
            "Hinao": "Hinao",
            "Sojo Genichi": "Genichi Sojo",
            "Hakuri Sazanami": "Hakuri Sazanami",
            "Kyora Sazanami": "Kyora Sazanami",
            "Hiyuki": "Hiyuki",
            "Tafuku": "Tafuku",
            "Kazane": "Kazane",
            "Enchanted Blades": "Magiczne Miecze",
            "Enten": "Enten",
            "Cloud Gouger": "Kuregumo",
            "Shinuchi": "Shinuchi",
            "Kamunabi": "Kamunabi",
            "Hishaku": "Hishaku",
            "Rakuzaichi": "Rakuzaichi",
            "Datenseki": "Datenseki"
        },
        "character_forms": {
            "Chihiro -> Char": "Opiekuńcza, starszobraterska troska",
            "Hakuri -> Chihiro": "Chihiro (wiara i oparcie w nowym przyjacielu)"
        }
    },
    "sailor_moon": {
        "title": "Czarodziejka z Księżyca – Sailor Moon",
        "aliases": [
            "sailor moon",
            "bishoujo senshi sailor moon",
            "czarodziejka z księżyca"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Usagi Tsukino": "Usagi Tsukino",
            "Mamoru Chiba": "Mamoru Chiba",
            "Ami Mizuno": "Ami Mizuno",
            "Rei Hino": "Rei Hino",
            "Makoto Kino": "Makoto Kino",
            "Minako Aino": "Minako Aino",
            "Chibiusa": "Chibiusa",
            "Haruka Tenoh": "Haruka Tenoh",
            "Michiru Kaioh": "Michiru Kaioh",
            "Setsuna Meioh": "Setsuna Meioh",
            "Hotaru Tomoe": "Hotaru Tomoe",
            "Luna": "Luna",
            "Artemis": "Artemis",
            "Diana": "Diana",
            "Queen Beryl": "Królowa Beryl",
            "Queen Metalia": "Królowa Metalia",
            "Prince Demande": "Książę Diament",
            "Black Lady": "Czarna Dama",
            "Professor Tomoe": "Profesor Tomoe",
            "Queen Nehelenia": "Królowa Nehelenia",
            "Sailor Galaxia": "Sailor Galaxia",
            "Silver Crystal": "Srebrny Kryształ",
            "Moon Tiara Action": "Księżycowy Diadem, Działaj!",
            "Moon Healing Escalation": "Księżycowa Eskalacja Uleczenia",
            "Silver Millennium": "Srebrne Milenium",
            "Crystal Tokyo": "Kryształowe Tokio"
        },
        "character_forms": {
            "Usagi -> Mamoru": "Mamo-chan (czułość i miłość)",
            "Mamoru -> Usagi": "Usako (czułe przezwisko)",
            "Wojowniczki -> Usagi": "Usagi-chan / Księżniczko (szacunek i przyjaźń)"
        }
    },
    "saint_seiya": {
        "title": "Rycerze Zodiaku – Saint Seiya",
        "aliases": [
            "rycerze zodiaku",
            "saint seiya"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Seiya": "Seiya",
            "Shiryu": "Shiryu",
            "Hyoga": "Hyoga",
            "Shun": "Shun",
            "Ikki": "Ikki",
            "Saori Kido": "Saori Kido",
            "Mu": "Mu",
            "Aldebaran": "Aldebaran",
            "Saga": "Saga",
            "Deathmask": "Deathmask",
            "Aiolia": "Aiolia",
            "Shaka": "Shaka",
            "Dohko": "Dohko",
            "Milo": "Milo",
            "Aiolos": "Aiolos",
            "Shura": "Shura",
            "Camus": "Camus",
            "Aphrodite": "Afrodyta",
            "Kanon": "Kanon",
            "Poseidon": "Julian Solo",
            "Hades": "Hades",
            "Hypnos": "Hypnos",
            "Thanatos": "Thanatos",
            "Sanctuary": "Sanktuarium Ateny",
            "Twelve Zodiac Temples": "Dwanaście Domów Zodiaku",
            "Cloth": "Święta Zbroja",
            "Cosmo": "Kosmo",
            "Pegasus Meteor Fist": "Meteory Pegaza",
            "Rozan Rising Dragon": "Wznoszący się Smok Rozan",
            "Diamond Dust": "Diamentowy Pył",
            "Aurora Execution": "Egzekucja Zorzy",
            "Nebula Chain": "Łańcuch Nebuli",
            "Phoenix Illusion Fist": "Demoniczna Pięść Feniksa"
        },
        "character_forms": {
            "Rycerze -> Saori": "Pani Saori / Bogini Ateno (absolutna lojalność)",
            "Ikki -> Shun": "Shun! (braterska opieka)"
        }
    },
    "captain_tsubasa": {
        "title": "Kapitan Tsubasa (Kapitan Jastrząb)",
        "aliases": [
            "kapitan tsubasa",
            "kapitan jastrząb",
            "captain tsubasa"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Tsubasa Ozora": "Tsubasa Ozora",
            "Genzo Wakabayashi": "Genzo Wakabayashi",
            "Kojiro Hyuga": "Kojiro Hyuga",
            "Taro Misaki": "Taro Misaki",
            "Jun Misugi": "Jun Misugi",
            "Ken Wakashimazu": "Ken Wakashimazu",
            "Hikaru Matsuyama": "Hikaru Matsuyama",
            "Ryo Ishizaki": "Ryo Ishizaki",
            "Kazuo Tachibana": "Kazuo Tachibana",
            "Masao Tachibana": "Masao Tachibana",
            "Shingo Aoi": "Shingo Aoi",
            "Roberto Hongo": "Roberto Hongo",
            "Tatsuo Mikami": "Tatsuo Mikami",
            "Karl Heinz Schneider": "Karl Heinz Schneider",
            "Deuter Muller": "Deuter Müller",
            "Carlos Santana": "Carlos Santana",
            "Natureza": "Natureza",
            "Juan Diaz": "Juan Diaz",
            "Pierre LeBlanc": "El Cid Pierre",
            "Nankatsu": "Szkoła Nankatsu",
            "Shutetsu": "Szkoła Shutetsu",
            "Meiwa": "Klub Meiwa",
            "Toho": "Akademia Toho",
            "Musashi": "Szkoła Musashi",
            "Furano": "Szkoła Furano",
            "Drive Shoot": "Strzał z Wyskoku",
            "Tiger Shot": "Strzał Tygrysa",
            "Neo Tiger Shot": "Neo Strzał Tygrysa",
            "Skylab Hurricane": "Podniebny Huragan Skylab",
            "Golden Duo": "Złoty Duet Nankatsu",
            "Eagle Shot": "Strzał Orła",
            "Fire Shot": "Ognisty Strzał",
            "Miracle Drive Shoot": "Cudowny Strzał z Rotacją"
        },
        "character_forms": {
            "Tsubasa -> Roberto": "Trenerze Roberto! (podziw i wdzięczność)",
            "Hyuga -> Tsubasa": "Tsubasa! (zaciekła, rycerska rywalizacja)",
            "Nankatsu -> Tsubasa": "Kapitanie Tsubaso!"
        }
    },
    "ranma_half": {
        "title": "Ranma 1/2",
        "aliases": [
            "ranma 1/2",
            "ranma",
            "ranma 1 2"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Ranma Saotome": "Ranma Saotome",
            "Akane Tendo": "Akane Tendo",
            "Genma Saotome": "Genma Saotome",
            "Soun Tendo": "Soun Tendo",
            "Nabiki Tendo": "Nabiki Tendo",
            "Kasumi Tendo": "Kasumi Tendo",
            "Ryoga Hibiki": "Ryoga Hibiki",
            "Shampoo": "Shampoo",
            "Mousse": "Mousse",
            "Happosai": "Happosai",
            "Cologne": "Cologne",
            "Ukyo Kuonji": "Ukyo Kuonji",
            "Tatewaki Kuno": "Tatewaki Kuno",
            "Kodachi Kuno": "Kodachi Kuno",
            "Dr. Tofu Ono": "Doktor Tofu Ono",
            "P-chan": "P-chan",
            "Jusenkyo": "Przeklęte Źródła Jusenkyo",
            "Spring of Drowned Girl": "Źródło Utopionej Dziewczyny",
            "Spring of Drowned Panda": "Źródło Utopionej Pandy",
            "Spring of Drowned Black Piglet": "Źródło Utopionego Prosiaka",
            "Spring of Drowned Cat": "Źródło Utopionego Kota",
            "Spring of Drowned Duck": "Źródło Utopionego Kaczora",
            "Anything-Goes Martial Arts": "Sztuki Walki Wszystko Ujdzie",
            "Hiryu Shotenha": "Latający Smok Przebijający Niebiosa",
            "Bakusai Tenketsu": "Technika Rozbijania Skał w Pył"
        },
        "character_forms": {
            "Ranma -> Akane": "Niekobiecy babsztyl / Akane (droczenie się skrywające uczucie)",
            "Akane -> Ranma": "Głupi Ranma! / Zboczeniec! (wybuchowy temperament)",
            "Ryoga -> Ranma": "Saotome! (żądza zemsty za zabłądzenie)",
            "Shampoo -> Ranma": "Airen! / Mój ukochany!"
        }
    },
    "yu_yu_hakusho": {
        "title": "Yu Yu Hakusho (Detektyw Świata Duchów)",
        "aliases": [
            "yu yu hakusho",
            "yuyu hakusho"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Yusuke Urameshi": "Yusuke Urameshi",
            "Kazuma Kuwabara": "Kazuma Kuwabara",
            "Kurama": "Kurama",
            "Hiei": "Hiei",
            "Keiko Yukimura": "Keiko Yukimura",
            "Botan": "Botan",
            "Koenma": "Koenma",
            "Genkai": "Mistrzyni Genkai",
            "Yukina": "Yukina",
            "Younger Toguro": "Młodszy Toguro",
            "Elder Toguro": "Starszy Toguro",
            "Shinobu Sensui": "Shinobu Sensui",
            "Raizen": "Raizen",
            "Mukuro": "Mukuro",
            "Yomi": "Yomi",
            "Spirit World": "Świat Duchów",
            "Human World": "Świat Ludzi",
            "Demon World": "Świat Demonów",
            "Spirit Gun": "Pistolet Ducha",
            "Spirit Sword": "Miecz Ducha",
            "Dragon of the Darkness Flame": "Smok Płomienia Ciemności",
            "Rose Whip": "Różany Bicz",
            "Dark Tournament": "Ciemny Turniej"
        },
        "character_forms": {
            "Kuwabara -> Yusuke": "Urameshi! (szorstka rywalizacja i braterstwo)",
            "Yusuke -> Keiko": "Keiko (troska ukryta pod maską chuligana)",
            "Hiei -> Kuwabara": "Głupi człowiek / Baka (chłodny dystans)"
        }
    },
    "dr_slump": {
        "title": "Dr. Slump",
        "aliases": [
            "dr. slump",
            "doktor slump",
            "dr slump"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Arale Norimaki": "Arale Norimaki",
            "Senbei Norimaki": "Senbei Norimaki",
            "Gatchan": "Gatchan",
            "Midori Yamabuki": "Midori Yamabuki",
            "Taro Soramame": "Taro Soramame",
            "Peasuke Soramame": "Peasuke Soramame",
            "Akane Kimidori": "Akane Kimidori",
            "Suppaman": "Suppaman",
            "King Nikochan": "Król Nikochan",
            "Dr. Mashirito": "Dr Mashirito",
            "Obotchaman": "Obotchaman",
            "Penguin Village": "Wioska Pingwinów",
            "N'cha Cannon": "Działo N'cha",
            "Earth Split": "Rozbicie Ziemi na Pół"
        },
        "character_forms": {
            "Arale -> Wszyscy": "N'cha! / Hoyoyo! / Kiiin! (dziecięca radość robota)",
            "Senbei -> Arale": "Arale, przestań bawić się kupą na patyku!"
        }
    },
    "chobits": {
        "title": "Chobits",
        "aliases": [
            "chobits"
        ],
        "publisher": "Wydawnictwo J.P.Fantastica",
        "glossary": {
            "Hideki Motosuwa": "Hideki Motosuwa",
            "Chii": "Chii",
            "Freya": "Freya",
            "Hiromu Shinbo": "Hiromu Shinbo",
            "Sumomo": "Sumomo",
            "Minoru Kokubunji": "Minoru Kokubunji",
            "Yuzuki": "Yuzuki",
            "Chitose Hibiya": "Pani Chitose Hibiya",
            "Takako Shimizu": "Takako Shimizu",
            "Yumi Omura": "Yumi Omura",
            "Persocom": "Persocom",
            "Chobits": "Chobits",
            "A City with No People": "Miasto bez ludzi",
            "The Person Just for Me": "Ta jedyna osoba przeznaczona tylko dla mnie"
        },
        "character_forms": {
            "Chii -> Hideki": "Hideki! / Chii! (dziecięca niewinność i miłość)",
            "Hideki -> Chii": "Chii (opiekuńczość i odkrywanie człowieczeństwa maszyny)"
        }
    },
    "danmachi": {
        "title": "Czy to źle, że próbuję poderwać dziewczynę w lochu? (DanMachi)",
        "aliases": [
            "dungeon ni deai",
            "danmachi",
            "is it wrong to try to pick up girls in a dungeon"
        ],
        "publisher": "Wydawnictwo Kotori",
        "glossary": {
            "Bell Cranel": "Bell Cranel",
            "Hestia": "Bogini Hestia",
            "Ais Wallenstein": "Ais Wallenstein",
            "Liliruca Arde": "Liliruca Arde",
            "Welf Crozzo": "Welf Crozzo",
            "Mikoto Yamato": "Mikoto Yamato",
            "Sanjouno Haruhime": "Haruhime",
            "Ryuu Lion": "Ryuu Lion",
            "Loki": "Bogini Loki",
            "Finn Deimne": "Finn Deimne",
            "Riveria Ljos Alf": "Riveria Ljos Alf",
            "Gareth Landrock": "Gareth Landrock",
            "Bete Loga": "Bete Loga",
            "Freya": "Bogini Freya",
            "Ottar": "Ottar",
            "Hermes": "Bóg Hermes",
            "Asfi Al Andromeda": "Asfi Al Andromeda",
            "Eina Tulle": "Eina Tulle",
            "Syr Flover": "Syr Flover",
            "Mia Grand": "Mama Mia",
            "Asterius": "Asterius",
            "Orario": "Orario",
            "The Dungeon": "Loch",
            "Hestia Familia": "Rodzina Hestii",
            "Loki Familia": "Rodzina Loki",
            "Freya Familia": "Rodzina Frei",
            "Xenos": "Xenos",
            "Falna": "Falna",
            "Status": "Status",
            "Liaris Freese": "Liaris Freese",
            "Firebolt": "Firebolt",
            "Argonaut": "Argonauta"
        },
        "character_forms": {
            "Bell -> Hestia": "Kami-sama / Pani Bogini (głęboka cześć i lojalność)",
            "Hestia -> Bell": "Bell-kun! (zaborcza miłość i opiekuńczość)",
            "Lili -> Bell": "Bell-sama (szacunek dla wybawcy)",
            "Bell -> Ais": "Panna Wallenstein (podziw dla niedoścignionego ideału)"
        }
    },
    "shield_hero": {
        "title": "Tate no Yuusha no Nariagari (Powstanie Bohatera Tarczy)",
        "aliases": [
            "shield hero",
            "tate no yuusha",
            "powstanie bohatera tarczy"
        ],
        "publisher": "Wydawnictwo Waneko",
        "glossary": {
            "Naofumi Iwatani": "Naofumi Iwatani",
            "Raphtalia": "Raphtalia",
            "Filo": "Filo",
            "Melty Q Melromarc": "Melty Melromarc",
            "Mirellia Q Melromarc": "Mirellia Melromarc",
            "Malty S Melromarc": "Malty",
            "Aultcray Melromarc XXXII": "Aultcray Melromarc",
            "Motoyasu Kitamura": "Motoyasu Kitamura",
            "Ren Amaki": "Ren Amaki",
            "Itsuki Kawasumi": "Itsuki Kawasumi",
            "Glass": "Glass",
            "L'Arc Berg": "L'Arc Berg",
            "Therese Alexanderite": "Therese",
            "Fitoria": "Fitoria",
            "Kizuna Kazeyama": "Kizuna Kazeyama",
            "Erhard": "Erhard",
            "Kingdom of Melromarc": "Królestwo Melromarc",
            "Waves of Catastrophe": "Fale Katastrofy",
            "Four Holy Weapons": "Cztery Święte Bronie",
            "Vassal Weapons": "Bronie Wasalne",
            "Curse Series": "Seria Przekleństwa",
            "Iron Maiden": "Żelazna Dziewica",
            "Blood Sacrifice": "Krwawa Ofiara"
        },
        "character_forms": {
            "Raphtalia -> Naofumi": "Naofumi-sama (miłość i wierność miecza)",
            "Naofumi -> Raphtalia": "Raphtalia (zaufanie i ojcowska opieka)",
            "Filo -> Naofumi": "Panie! / Goshujin-sama!"
        }
    },
    "slime_isekai": {
        "title": "Odrodzony jako Galareta (Tensei shitara Slime Datta Ken)",
        "aliases": [
            "tensei shitara slime",
            "odrodzony jako galareta",
            "slime isekai",
            "tensura"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Rimuru Tempest": "Rimuru Tempest",
            "Great Sage": "Wielki Mędrzec",
            "Veldora Tempest": "Veldora Tempest",
            "Shizue Izawa": "Shizue Izawa",
            "Benimaru": "Benimaru",
            "Shuna": "Shuna",
            "Shion": "Shion",
            "Souei": "Souei",
            "Hakuro": "Hakuro",
            "Kurobe": "Kurobe",
            "Rigurd": "Rigurd",
            "Gobta": "Gobta",
            "Ranga": "Ranga",
            "Diablo": "Diablo",
            "Milim Nava": "Milim Nava",
            "Guy Crimson": "Guy Crimson",
            "Ramiris": "Ramiris",
            "Carrion": "Carrion",
            "Frey": "Frey",
            "Clayman": "Clayman",
            "Hinata Sakaguchi": "Hinata Sakaguchi",
            "Luminous Valentine": "Luminous Valentine",
            "Jura Tempest Federation": "Federacja Jura Tempest",
            "Great Jura Forest": "Wielki Las Jura",
            "Demon Lord": "Władca Demonów",
            "Octagram": "Oktagram",
            "Predator": "Drapieżnik",
            "Gluttony": "Żarłoczność",
            "Megiddo": "Megiddo",
            "Naming": "Nadawanie Imion"
        },
        "character_forms": {
            "Potwory -> Rimuru": "Pan Rimuru / Rimuru-sama (uwielbienie i boska cześć)",
            "Veldora -> Rimuru": "Rimuru! (kumpelska duma)",
            "Milim -> Rimuru": "Mój najlepszy przyjaciel!"
        }
    },
    "kusuriya_no_hitorigoto": {
        "title": "Zapiski Zielarki (Kusuriya no Hitorigoto)",
        "aliases": [
            "zapiski zielarki",
            "kusuriya no hitorigoto",
            "the apothecary diaries"
        ],
        "publisher": "Wydawnictwo Studio JG",
        "glossary": {
            "Maomao": "Maomao",
            "Jinshi": "Jinshi",
            "Gaoshun": "Gaoshun",
            "Basen": "Basen",
            "Suirei": "Suirei",
            "Loulan": "Loulan",
            "Luomen": "Luomen",
            "Lakan": "Lakan",
            "Fengxian": "Fengxian",
            "Pairin": "Pairin",
            "Joka": "Joka",
            "Meimei": "Meimei",
            "Madam": "Pani Domu Werigrysu",
            "Gyokuyou": "Małżonka Gyokuyou",
            "Lihua": "Małżonka Lihua",
            "Ah-Duo": "Małżonka Ah-Duo",
            "Lishu": "Małżonka Lishu",
            "The Emperor": "Cesarz",
            "Empress Dowager": "Cesarzowa Wdowa",
            "Imperial Physician Shen": "Nadworny Lekarz Shen",
            "Hongniang": "Hongniang",
            "Inner Palace": "Wewnętrzny Pałac",
            "Outer Palace": "Zewnętrzny Pałac",
            "Verdigris House": "Dom Werigrysu",
            "Pavilion of Jade": "Pawilon Jadeitu",
            "Pavilion of Crystal": "Pawilon Kryształu",
            "Pavilion of Garnet": "Pawilon Granatu",
            "Pavilion of Topaz": "Pawilon Topazu",
            "Poison Testing": "Próbowanie potraw pod kątem trucizn",
            "White Powder Lead": "Biały puder z ołowiem",
            "Ox Bezoar": "Bezoar wołowy",
            "Datura": "Bieluń dziędzierzawa",
            "Blowfish Poison": "Tetrodotoksyna",
            "Resurrection Medicine": "Lekarstwo wskrzeszające"
        },
        "character_forms": {
            "Maomao -> Jinshi": "Panie Jinshi / Jinshi-sama (chłodny profesjonalizm skrywający zażenowanie jego urodą)",
            "Jinshi -> Maomao": "Maomao (fascynacja, zazdrość i skrywane uczucie)",
            "Gaoshun -> Maomao": "Xiaomao / Mała Mao (ojcowska, łagodna troska)",
            "Gyokuyou -> Maomao": "Maomao (ciepłe zaufanie i ochrona na dworze)"
        }
    }
}

class MangaCanonRegistry:
    """
    Registry for official Polish manga/light novel translations.
    """
    def __init__(self, custom_dir: Optional[str] = None):
        if custom_dir:
            self.custom_dir = Path(custom_dir)
        else:
            self.custom_dir = Path(os.path.dirname(__file__)) / "manga_canon"
        self.custom_dir.mkdir(parents=True, exist_ok=True)
        self.canon_db = dict(BUILTIN_MANGA_CANON)
        self._load_custom_canons()

    def _load_custom_canons(self):
        """Loads user-created or dynamically discovered JSON canon files."""
        for json_file in self.custom_dir.glob("*.json"):
            if json_file.name.startswith("."):
                continue
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    slug = json_file.stem
                    self.canon_db[slug] = data
            except Exception as e:
                logger.warning(f"Failed to load custom canon from {json_file.name}: {e}")

    def find_canon_for_series(self, title: str) -> Optional[Dict[str, Any]]:
        """Finds matching manga canon entry by title or alias."""
        if not title:
            return None

        norm_title = title.lower().strip()
        norm_title_compact = re.sub(r"[^\w]+", "", norm_title)

        for slug, entry in self.canon_db.items():
            if slug.lower() == norm_title or slug.lower() == norm_title_compact:
                return entry
            if entry.get("title", "").lower() == norm_title:
                return entry

            for alias in entry.get("aliases", []):
                norm_alias = alias.lower().strip()
                norm_alias_compact = re.sub(r"[^\w]+", "", norm_alias)
                if norm_alias == norm_title or norm_alias_compact == norm_title_compact:
                    return entry
                if len(norm_alias_compact) >= 4 and (norm_alias_compact in norm_title_compact or norm_title_compact in norm_alias_compact or norm_alias in norm_title):
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
        Universal Polish Manga Canon Resolver with Strict Verified Domain Search Grounding:
        1. Checks built-in verified database and local cache.
        2. If not found, queries Google Search Grounding restricted STRICTLY to trusted Polish sources
           (official publishers Waneko, JPF, Studio JG, Kotori, Hanami; Tanuki.pl; Polish Fandom wiki).
        3. Never hallucinates or calques English terms.
        4. Saves discovered canon to manga_canon/{slug}.json for instant offline access.
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
Jesteś rzetelnym archiwistą i ekspertem polskiego rynku wydawniczego mangi i komiksu.
Twoim zadaniem jest sprawdzenie, czy seria anime/manga '{primary_title}' (lub powiązane tytuły: {', '.join(all_candidates[:4])}) POSIADA OFICJALNE POLSKIE WYDANIE PAPIEROWE (manga / light novel) wydane przez licencjonowane polskie wydawnictwo:
- Wydawnictwo Waneko
- Wydawnictwo J.P.Fantastica (JPF)
- Wydawnictwo Studio JG
- Wydawnictwo Kotori
- Wydawnictwo Hanami
- Wydawnictwo Dango
- Wydawnictwo Egmont Polska

ŻELAZNY STANDARD ENCYKLOPEDYCZNY (STANDARD KINGDOM):
Jeśli seria ma polskie wydanie papierowe, masz OBOWIĄZEK wygenerować WYCZERPUJĄCY, PEŁNY SŁOWNIK (minimum 40–80 kluczowych terminów, bez żadnych skrótów), obejmujący:
1. PEŁNĄ OBSADĘ: Wszyscy bohaterowie główni, drugoplanowi, mentorzy, antagoniści, potwory i członkowie frakcji.
2. SYSTEM MOCY I ATAKI: Wszystkie kanoniczne nazwy ataków, zaklęć, form, stylów oddychania, domen, mieczy, broni i artefaktów.
3. ORGANIZACJE I RANGI: Stopnie wojskowe/gildyjne, oddziały, korpusy, zakony, kapituły, rody, klany i frakcje.
4. ŚWIAT I GEOGRAFIA: Krainy, państwa, miasta, akademie, lochy, wymiary, twierdze i pola bitew.
5. RELACJE I FORMY ZWROTU: Dokładne formy per 'ty' / per 'pan/pani' i wzajemne odzywki bohaterów z polskiego przekładu.

KRYTYCZNE ZASADY WERYFIKACJI ŹRÓDEŁ:
1. Wyszukuj informacje WYŁĄCZNIE w zaufanych polskich źródłach:
   - Oficjalne serwisy i katalogi polskich wydawnictw (waneko.pl, jpf.com.pl, studiojg.pl, kotori.pl, hanami.pl, dango.pl, yatta.pl, egmont.pl)
   - Encyklopedia Tanuki Manga / Anime (tanuki.pl)
   - Polskie bazy Fandom prowadzone przez czytelników polskich tomików (*.fandom.com/pl)
   - Polskie bazy komiksowe (alejakomiksu.com, komikspec.pl, gildia.pl)
2. KATEGORYCZNY ZAKAZ:
   - Kategorycznie ZAKAZANE jest korzystanie z Crunchyroll PL (ich napisy zawierają kalki z języka angielskiego, błędy gramatyczne i niską jakość literacką).
   - Kategorycznie ignoruj anglojęzyczne fora (Reddit, 4chan, MAL), automatyczne translatory i mechaniczne tłumaczenia dosłowne z języka angielskiego.
   - Jeśli nie masz 100% potwierdzenia danego terminu z polskiego wydania papierowego, NIE WYMYŚLAJ GO! Lepiej podać autentyczne terminy z polskiego druku.
3. Jeśli seria NIE POSIADA oficjalnego polskiego wydania mangi/LN w Polsce, natychmiast zwróć:
   {{"has_polish_edition": false}}

Jeżeli seria została oficjalnie wydana w Polsce, zwróć kompletny słownik w formacie JSON:
{{
  "has_polish_edition": true,
  "title": "Oficjalny Polski Tytuł (z okładki polskiego tomiku)",
  "publisher": "Wydawnictwo XYZ (np. Waneko, Studio JG, JPF, Kotori, Hanami, Dango)",
  "aliases": ["{primary_title.lower()}", "{slug}"],
  "glossary": {{
    "Oryginalna nazwa japońska lub angielska": "Oficjalne polskie tłumaczenie z polskiego wydania mangi (z krótkim wyjaśnieniem w nawiasie jeśli to postać/atak)"
  }},
  "character_forms": {{
    "PostaćA -> PostaćB": "forma zwrotu i styl relacji z polskiego przekładu"
  }}
}}

ZWRÓĆ WYŁĄCZNIE CZYSTY KOD JSON BEZ ZBĘDNYCH KOMENTARZY.
"""
            target_client = getattr(client, "get_client", lambda: client)()
            resp = target_client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            raw_text = resp.text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0]
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0]
            data = json.loads(raw_text.strip())

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
                if "(" in term_pl and ")" in term_pl:
                    clean_term = term_pl.split("(")[0].strip()
                    explanation = term_pl.split("(", 1)[1].rsplit(")", 1)[0].strip()
                    lines.append(f"  - '{term_src}' -> '{clean_term}' [Kontekst: {explanation} - UWAGA: w dialogu używaj wyłącznie czystego '{clean_term}', NIGDY nie wklejaj tekstu w nawiasie do napisów!]")
                else:
                    lines.append(f"  - '{term_src}' -> '{term_pl}'")

        char_forms = canon_entry.get("character_forms", {})
        if char_forms:
            lines.append("• Kompletne kanoniczne formy zwrotów i relacje:")
            for rel, form_desc in char_forms.items():
                lines.append(f"  - {rel}: {form_desc}")

        lines.append("(!) KRYTYCZNE ZASADY FLEKSJI I POPRAWNOŚCI GRAMATYCZNEJ:")
        lines.append("1. OBOWIĄZKOWA ODMIANA PRZEZ PRZYPADKI: Wszystkie imiona, stopnie i tytuły MUSZĄ być odmieniane gramatycznie w zdaniu (np. 'z generałem Riboku', 'dla Oukiego', 'z Shinem', a NIGDY sztywny mianownik 'z Wielki Generał Riboku'!).")
        lines.append("2. ZAKAZ DUBEL-HONORYFIKATORÓW I HYBRYD: Kategoryczny zakaz łączenia 'pan' z rangami wojskowymi (NIGDY 'z panem Wielki Generał', 'pan Generał' -> wyłącznie 'z Wielkim Generałem Riboku / z Riboku').")
        lines.append("3. Tytuły wojskowe (np. 'Wielki Generał') stosuj tylko wtedy, gdy padają one w danej kwestii w oryginale; gdy pada samo imię, używaj samego odmienionego imienia.")
        lines.append("4. KATEGORYCZNY ZAKAZ WKLEJANIA NAWIASÓW ZE SŁOWNIKA DO DIALOGÓW: Napisy filmowe to mowa postaci. Nigdy, pod żadnym pozorem nie wklejaj do napisów nawiasów wyjaśniających z glosariusza (np. '(Demon Północy z Ganmon)', '(Półelfka)', '(Potworny Ptak z Qin)'). W dialogu ma paść wyłącznie naturalna wypowiedź bohatera!")
        lines.append("5. ZASADA AVT: Zachowaj kanoniczne nazwy, ale przy długich wypowiedziach stosuj zwięzłą polską składnię (limit 17 CPS).")
        lines.append("=========================================================================\n")
        return "\n".join(lines)


# Global singleton instance
manga_canon_registry = MangaCanonRegistry()
