# -*- coding: utf-8 -*-
"""
AVT Linter Module (Automated Polish Film Subtitle Auditor & Quality Guard).
Based on guidelines by Arkadiusz Belczyk, Agnieszka Szarkowska, Netflix Polish Style Guide,
and the dynamic user feedback & glossary rules.
Acts as a final, independent quality shield inspecting translated lines for
calques, unnatural questions, incorrect gender forms, and machine-translation artifacts.
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

def _fix_duza_przerwa_match(m: Any) -> str:
    first_letter = m.group(1)
    ending = m.group(2).lower()
    sep = m.group(3)
    przerw_end = m.group(4) or ""
    mapping = {
        "a": "długa",
        "ą": "długą",
        "ej": "długiej",
        "e": "długie",
        "ych": "długich",
        "ym": "długim",
        "ymi": "długimi",
    }
    form = mapping.get(ending, "długiej")
    if first_letter.isupper():
        form = form.capitalize()
    return f"{form}{sep}przerw{przerw_end}"

def _fix_mala_przerwa_match(m: Any) -> str:
    first_letter = m.group(1)
    ending = m.group(2).lower()
    sep = m.group(3)
    przerw_end = m.group(4) or ""
    mapping = {
        "a": "krótka",
        "ą": "krótką",
        "ej": "krótkiej",
        "e": "krótkie",
        "ych": "krótkich",
        "ym": "krótkim",
        "ymi": "krótkimi",
    }
    form = mapping.get(ending, "krótkiej")
    if first_letter.isupper():
        form = form.capitalize()
    return f"{form}{sep}przerw{przerw_end}"

class AVTLinter:
    """
    Automated validator and corrector for mechanical language calques in subtitle tracks.
    """
    
    # Dictionary of automated instant calque replacements mapped to AVT Pillars
    # Supports flexible inflectional and tense patterns
    FIXED_REPLACEMENTS = [
        # Americanisms and lexical calques (Pillar IV / XXXVI)
        (r"\b[Ww]itaj z powrotem\b", "Witaj!", "Filar IV/XXXVI - Eliminacja Kalek Amerykańskich"),
        
        # Inflections of "mieć taką nadzieję" -> "mieć nadzieję"
        (r"\b([Mm]am|[Mm]iałem|[Mm]iałam|[Mm]ieliśmy|[Mm]iałyśmy|[Bb]ędę mieć|[Bb]ędziemy mieć)\s+taką\s+nadzieję\b", r"\1 nadzieję", "Filar IV - Czystość Idiomatyczna"),
        (r"\b[Mm]am nadzieję na to\b", "Mam nadzieję", "Filar IV - Czystość Idiomatyczna"),

        # Inflections of "robić sens" -> "mieć sens"
        (r"\bTo\s+robi\s+sens\b", "To ma sens", "Filar IV - Eliminacja Kalek"),
        (r"\bto\s+robi\s+sens\b", "to ma sens", "Filar IV - Eliminacja Kalek"),
        (r"\brobi\s+sens\b", "ma sens", "Filar IV - Eliminacja Kalek"),
        (r"\bTo\s+robiło\s+sens\b", "To miało sens", "Filar IV - Eliminacja Kalek"),
        (r"\bto\s+robiło\s+sens\b", "to miało sens", "Filar IV - Eliminacja Kalek"),
        (r"\brobiło\s+sens\b", "miało sens", "Filar IV - Eliminacja Kalek"),
        (r"\bTo\s+będzie\s+robić\s+sens\b", "To będzie mieć sens", "Filar IV - Eliminacja Kalek"),
        (r"\bto\s+będzie\s+robić\s+sens\b", "to będzie mieć sens", "Filar IV - Eliminacja Kalek"),
        (r"\bTo\s+nie\s+robi\s+sensu\b", "To nie ma sensu", "Filar IV - Eliminacja Kalek"),
        (r"\bto\s+nie\s+robi\s+sensu\b", "to nie ma sensu", "Filar IV - Eliminacja Kalek"),
        (r"\bnie\s+robi\s+sensu\b", "nie ma sensu", "Filar IV - Eliminacja Kalek"),
        (r"\bTo\s+nie\s+robiło\s+sensu\b", "To nie miało sensu", "Filar IV - Eliminacja Kalek"),
        (r"\bto\s+nie\s+robiło\s+sensu\b", "to nie miało sensu", "Filar IV - Eliminacja Kalek"),
        (r"\bnie\s+robiło\s+sensu\b", "nie miało sensu", "Filar IV - Eliminacja Kalek"),
        (r"\bTo\s+nie\s+będzie\s+robić\s+sensu\b", "To nie będzie mieć sensu", "Filar IV - Eliminacja Kalek"),
        (r"\bto\s+nie\s+będzie\s+robić\s+sensu\b", "to nie będzie mieć sensu", "Filar IV - Eliminacja Kalek"),

        (r"\b[Jj]esteś w porządku\?", "Wszystko w porządku?", "Filar IV - Szablony Angielskie"),
        (r"\b[Bb]yłem w stanie to znaleźć\b", "Udało mi się to znaleźć", "Filar IV - Konstrukcje Obce"),
        (r"\b[Bb]yłam w stanie to znaleźć\b", "Udało mi się to znaleźć", "Filar IV - Konstrukcje Obce"),
        (r"\b[Ww]ygląda jakby miało padać\b", "Chyba będzie padać", "Filar XXXII - Modalność Epistemiczna"),
        (r"\b[Mm]am uczucie że\b", "Coś mi mówi, że", "Filar IV - Naturalność Mówiona"),
        (r"\b[Ww]ydaje się być\b", "Wydaje się", "Filar IV - Konstrukcje Obce"),
        (r"\b[Dd]aj mi rękę\b", "Pomóż mi", "Filar IV - Idiomatyka"),
        (r"\b[Pp]oniosło klapę\b", "Nie wyszło", "Filar IV - Idiomatyka"),
        (r"\b[Ww]asz [Hh]onor\b", "Wysoki Sądzie", "Filar XVI - Realia Sądownicze"),
        (r"\b[Pp]rzekroczył(?:a|o|i|y)?\s+punkt\s+bez\s+powrotu\b", "nie ma już odwrotu", "Filar IV/LIX - Eliminacja Kalki 'Point of no return'"),
        (r"\b[Pp]rzekroczy(?:ć|cie|my)?\s+punkt\s+bez\s+powrotu\b", "nie mieć już odwrotu", "Filar IV/LIX - Eliminacja Kalki 'Point of no return'"),
        (r"\b[Pp]unkt\s+bez\s+powrotu\b", "droga bez odwrotu", "Filar IV/LIX - Eliminacja Kalki 'Point of no return'"),
        
        # AnimeSub.info (ANSI) Anti-Translationese & Phatic Calques
        (r"\b[Zz]godnie z oczekiwaniami\b", "tak jak myślałem", "Filar CXLVII - Eliminacja Kalki 'As expected'"),
        (r"\b[Nn]ie da się pomóc\b", "nic na to nie poradzimy", "Filar CXLVII - Eliminacja Kalki 'It can't be helped'"),
        (r"\b[Nn]ie można pomóc\b", "nic nie poradzimy", "Filar CXLVII - Eliminacja Kalki 'It can't be helped'"),
        (r"\b[Oo]ho,?\s+spokojnie(?:\.{1,3}|\b)", "Ło, ło, ło...", "Filar XVIII - Eliminacja Kalki Somatycznej 'Whoa, easy' (Ottotto)"),
        (r"\b[Tt]o\s+jest\s+gorące(?:\!|\b)", "Parzy!", "Filar XVIII - Eliminacja Opisu Bólu (Acchichi)"),
        (r"\b[Tt]o\s+boli(?:\!|\b)", "Ała!", "Filar XVIII - Eliminacja Opisu Bólu (Itta)"),
        (r"^\s*[Tt]o\s+prawda\?\s*$", "To pewne?", "Filar CXLVIII - Eliminacja Urzędowego Pytania 'To prawda?'"),
        (r"\b[Nn]iebezpiecznie(?:\!|\b)", "Uważaj!", "Filar CLII - Eliminacja Opisu Zagrożenia (Abunai)"),
        (r"\b[Tt]o\s+jest\s+niebezpieczne(?:\!|\b)", "Uważaj!", "Filar CLII - Eliminacja Opisu Zagrożenia (Abunai)"),
        (r"\b[Oo]cal\s+mnie(?:\!|\b)", "Ratunku!", "Filar CLII - Eliminacja Teatralnego Zwrotu (Tasukete)"),
        (r"\b[Bb]ędę\s+przeszkadzał\b", "Przepraszam za najście", "Filar CLI - Formuła Ojama Shimasu"),
        (r"\b[Ww]róciłem\s+do\s+domu\b", "Wróciłem!", "Filar CLI - Formuła Tadaima"),
        (r"\b[Nn]ic nie da się zrobić\b", "Trudno", "Filar XXI - Eliminacja Kalki 'Shouganai' (ANSI Standard)"),
        (r"\b[Dd]zięki za zmęczenie\b", "Dobra robota", "Filar XXI - Eliminacja Kalki 'Otsukaresama' (ANSI Standard)"),
        (r"\b[Dd]zięki za dobrą pracę\b", "Dobra robota", "Filar XXI - Eliminacja Kalki 'Otsukaresama' (ANSI Standard)"),
        (r"\b[Zz]robiłem to!\b", "Udało się!", "Filar IV - Eliminacja Kalki 'Yatta / I did it' (ANSI Standard)"),
        (r"\b[Zz]robiłam to!\b", "Udało się!", "Filar IV - Eliminacja Kalki 'Yatta / I did it' (ANSI Standard)"),
        (r"\b[Nn]ie ma drogi!\b", "Wykluczone!", "Filar IV - Eliminacja Kalki 'No way' (ANSI Standard)"),
        
        # Bridge Idioms & Deictic Negation (Filar CXXXVII)
        (r"^\s*[Nn]ie o niego([!\.\?]*)\s*$", r"To nie on\1", "Filar CXXXVII - Eliminacja Kalki 'Not him'"),
        (r"^\s*[Nn]ie o nią([!\.\?]*)\s*$", r"To nie ona\1", "Filar CXXXVII - Eliminacja Kalki 'Not her'"),
        (r"^\s*[Nn]ie o to([!\.\?]*)\s*$", r"To nie tak\1", "Filar CXXXVII - Eliminacja Kalki 'Not that / Not this'"),
        (r"^\s*[Pp]o tobie([!\.\?]*)\s*$", r"Proszę przodem\1", "Filar CXXXVII - Eliminacja Kalki 'After you'"),
        (r"^\s*[Bb]ądź moim gościem([!\.\?]*)\s*$", r"Bardzo proszę\1", "Filar CXXXVII - Eliminacja Kalki 'Be my guest'"),
        (r"^\s*[Pp]owiedz mi o tym([!\.\?]*)\s*$", r"Nawet mi nie mów\1", "Filar CXXXVII - Eliminacja Kalki 'Tell me about it'"),
        (r"^\s*[Ss]pójrz,?\s+kto mówi([!\.\?]*)\s*$", r"Kto to mówi\1", "Filar CXXXVII - Eliminacja Kalki 'Look who's talking'"),
        (r"^\s*[Nn]a tym([!\.\?]*)\s*$", r"Już się robi\1", "Filar CXXXVII - Eliminacja Kalki 'On it'"),
        (r"^\s*[Zz]akładasz się([!\.\?]*)\s*$", r"I to jak\1", "Filar CXXXVII - Eliminacja Kalki 'You bet'"),
        (r"^\s*[Tt]am idziesz([!\.\?]*)\s*$", r"Proszę bardzo\1", "Filar CXXXVII - Eliminacja Kalki 'There you go'"),
        (r"^\s*[Nn]ie mówisz tego([!\.\?]*)\s*$", r"Nie gadaj\1", "Filar CXXXVII - Eliminacja Kalki 'You don't say'"),
        (r"^\s*[Dd]obre dla ciebie([!\.\?]*)\s*$", r"To świetnie\1", "Filar CXXXVII - Eliminacja Kalki 'Good for you'"),
        (r"^\s*[Jj]estem dobry([!\.\?]*)\s*$", r"Wszystko w porządku\1", "Filar CXXXVII - Eliminacja Kalki 'I'm good'"),
        (r"^\s*[Dd]roga do pójścia([!\.\?]*)\s*$", r"Dobra robota\1", "Filar CXXXVII - Eliminacja Kalki 'Way to go'"),
        (r"^\s*[Nn]ie wspominaj o tym([!\.\?]*)\s*$", r"Nie ma za co\1", "Filar CXXXVII - Eliminacja Kalki 'Don't mention it'"),
        (r"^\s*[Pp]oza pytaniem([!\.\?]*)\s*$", r"Wykluczone\1", "Filar CXXXVII - Eliminacja Kalki 'Out of the question'"),
        (r"^\s*[Ww]eź swój czas([!\.\?]*)\s*$", r"Bez pośpiechu\1", "Filar CXXXVII - Eliminacja Kalki 'Take your time'"),
        
        # Kandōshi & Affective Interjections (Filar CLIII)
        (r"^\s*[Dd]obre nieszczęście([!\.\?]*)\s*$", r"Litości\1", "Filar CLIII - Eliminacja Kalki 'Good grief'"),
        (r"^\s*[Dd]aj mi przerwę([!\.\?]*)\s*$", r"Daj mi spokój\1", "Filar CLIII - Eliminacja Kalki 'Give me a break'"),
        (r"^\s*[Nn]ie można temu pomóc([!\.\?]*)\s*$", r"Nic na to nie poradzimy\1", "Filar CLIII - Eliminacja Kalki 'Can't be helped'"),
        (r"^\s*[Nn]ie da się temu pomóc([!\.\?]*)\s*$", r"Nic na to nie poradzimy\1", "Filar CLIII - Eliminacja Kalki 'Can't be helped'"),
        (r"^\s*[Zz]rób to z umiarem([!\.\?]*)\s*$", r"Przestań wreszcie\1", "Filar CLIII - Eliminacja Kalki 'Iikagen ni shiro'"),
        
        # Dialects & 3rd Person Family Relations (Filar CLIV)
        (r"\b[Ss]tarszy brat powiedział\b", "Mój brat powiedział", "Filar CLIV - Relacja Rodzinna w 3. Osobie"),
        (r"\bstarszy brat powiedział\b", "mój brat powiedział", "Filar CLIV - Relacja Rodzinna w 3. Osobie"),
        (r"\b[Ss]tarsza siostra powiedziała\b", "Moja siostra powiedziała", "Filar CLIV - Relacja Rodzinna w 3. Osobie"),
        (r"\bstarsza siostra powiedziała\b", "moja siostra powiedziała", "Filar CLIV - Relacja Rodzinna w 3. Osobie"),
        
        # Environmental Media & Non-Aqueous Liquids (Filar CXXXVIII)
        (r"\bPowódź\s+piwa\b", "Fala piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fala piwa)"),
        (r"\bpowódź\s+piwa\b", "fala piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fala piwa)"),
        (r"\bPowodzi\s+piwa\b", "Fali piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fali piwa)"),
        (r"\bpowodzi\s+piwa\b", "fali piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fali piwa)"),
        (r"\bPowódź\s+wina\b", "Fala wina", "Filar CXXXVIII - Kolokacja Cieczy (Fala wina)"),
        (r"\bpowódź\s+wina\b", "fala wina", "Filar CXXXVIII - Kolokacja Cieczy (Fala wina)"),
        (r"\bPowodzi\s+wina\b", "Fali wina", "Filar CXXXVIII - Kolokacja Cieczy (Fali wina)"),
        (r"\bpowodzi\s+wina\b", "fali wina", "Filar CXXXVIII - Kolokacja Cieczy (Fali wina)"),

        # School & Temporal Collocations (Filar III/XIV/ECR: "długa przerwa", nie "duża przerwa")
        (
            r"\b([Dd])uż(ej|ymi|ych|ym|a|ą|e)((?:\\N|\s)+)przerw(ie|ami|ach|om|a|y|ę|ą|o)?\b",
            _fix_duza_przerwa_match,
            "Filar III/XIV - Kolokacja Czasowo-Szkolna ('długa przerwa', nie 'duża')",
        ),
        (
            r"\b([Mm])ał(ej|ymi|ych|ym|a|ą|e)((?:\\N|\s)+)przerw(ie|ami|ach|om|a|y|ę|ą|o)?\b",
            _fix_mala_przerwa_match,
            "Filar III/XIV - Kolokacja Czasowo-Szkolna ('krótka przerwa', nie 'mała')",
        ),
        (
            r"\b[Dd]uży(?:\s+|\\N)+weekend\b",
            lambda m: ("Długi" if m.group(0)[0].isupper() else "długi") + ("\\N" if "\\N" in m.group(0) else " ") + "weekend",
            "Filar III/IV - Kolokacje Czasowe (Długi weekend)",
        ),
        (
            r"\b[Dd]użego(?:\s+|\\N)+weekendu\b",
            lambda m: ("Długiego" if m.group(0)[0].isupper() else "długiego") + ("\\N" if "\\N" in m.group(0) else " ") + "weekendu",
            "Filar III/IV - Kolokacje Czasowe (Długiego weekendu)",
        ),
        (
            r"\b[Dd]użym(?:\s+|\\N)+weekendzie\b",
            lambda m: ("Długim" if m.group(0)[0].isupper() else "długim") + ("\\N" if "\\N" in m.group(0) else " ") + "weekendzie",
            "Filar III/IV - Kolokacje Czasowe (Długim weekendzie)",
        ),
        
        # Proper Noun Prepositional Case Agreement (Filar IV / Filar XCI / Belczyk)
        (r"\b([Ww]|we|[Pp]rzy|[Nn]a|[Oo])\s+Twierdza\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźżōū]+)\b", r"\1 twierdzy \2", "Filar IV/XCI - Odmiana Rzeczownika w Nazwie Własnej (Miejscownik: w twierdzy)"),
        (r"\b([Dd]o|[Zz]|ze|[Oo]d|[Dd]la|[Kk]u)\s+Twierdza\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźżōū]+)\b", r"\1 twierdzy \2", "Filar IV/XCI - Odmiana Rzeczownika w Nazwie Własnej (Dopełniacz: z/do twierdzy)"),
        (r"\b([Ww]|we|[Pp]rzy|[Nn]a|[Oo])\s+Więzienie\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźżōū]+)\b", r"\1 więzieniu \2", "Filar IV/XCI - Odmiana Rzeczownika w Nazwie Własnej (Miejscownik: w więzieniu)"),
        (r"\b([Dd]o|[Zz]|ze|[Oo]d|[Dd]la|[Kk]u)\s+Więzienie\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźżōū]+)\b", r"\1 więzienia \2", "Filar IV/XCI - Odmiana Rzeczownika w Nazwie Własnej (Dopełniacz: z/do więzienia)"),
        (r"\b([Ww]|we|[Pp]rzy|[Nn]a|[Oo])\s+Zamek\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźżōū]+)\b", r"\1 zamku \2", "Filar IV/XCI - Odmiana Rzeczownika w Nazwie Własnej (Miejscownik: w zamku)"),
        (r"\b([Dd]o|[Zz]|ze|[Oo]d|[Dd]la|[Kk]u)\s+Zamek\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźżōū]+)\b", r"\1 zamku \2", "Filar IV/XCI - Odmiana Rzeczownika w Nazwie Własnej (Dopełniacz: z/do zamku)"),
        (r"\b([Ww]|we|[Pp]rzy|[Nn]a|[Oo])\s+Hotel\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźżōū]+)\b", r"\1 hotelu \2", "Filar IV/XCI - Odmiana Rzeczownika w Nazwie Własnej (Miejscownik: w hotelu)"),
        (r"\b([Dd]o|[Zz]|ze|[Oo]d|[Dd]la|[Kk]u)\s+Hotel\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźżōū]+)\b", r"\1 hotelu \2", "Filar IV/XCI - Odmiana Rzeczownika w Nazwie Własnej (Dopełniacz: z/do hotelu)"),
        (r"\b([Ww]|we|[Pp]rzy|[Nn]a|[Oo])\s+Namiestnictwo\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźżōū]+)\b", r"\1 namiestnictwie \2", "Filar IV/XCI - Odmiana Rzeczownika w Nazwie Własnej (Miejscownik: w namiestnictwie)"),
        (r"\b([Dd]o|[Zz]|ze|[Oo]d|[Dd]la|[Kk]u)\s+Namiestnictwo\s+([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźżōū]+)\b", r"\1 namiestnictwa \2", "Filar IV/XCI - Odmiana Rzeczownika w Nazwie Własnej (Dopełniacz: z/do namiestnictwa)"),
        
        # Nominalizations (Pillar I)
        (r"\b[Oo]dbyć rozmowę\b", "porozmawiać", "Filar I - Odnominalizowanie"),
        (r"\bodbyłem rozmowę\b", "porozmawiałem", "Filar I - Odnominalizowanie"),
        (r"\bodbyłam rozmowę\b", "porozmawiałam", "Filar I - Odnominalizowanie"),
        (r"\b[Zz]robić sprzątanie\b", "posprzątać", "Filar I - Odnominalizowanie"),
        (r"\b[Zz]robił sprzątanie\b", "posprzątał", "Filar I - Odnominalizowanie"),
        (r"\b[Zz]robiła sprzątanie\b", "posprzątała", "Filar I - Odnominalizowanie"),
        (r"\b[Dd]ać odpowiedź\b", "odpowiedzieć", "Filar I - Odnominalizowanie"),
        (r"\b[Zz]robić pojawienie się\b", "zjawić się", "Filar I - Odnominalizowanie"),

        # Pleonasms & tautologies (Belczyk)
        (r"\b[Cc]ofnąć się do tyłu\b", "cofnąć się", "Filar IV - Pleonazmy"),
        (r"\b[Oo]kres czasu\b", "okres", "Filar IV - Pleonazmy"),
        (r"\bw tym momencie czasu\b", "w tej chwili", "Filar IV - Pleonazmy"),

        # Family relations & feudal honorifics (Pillars XXV / LX)
        (r"\bTo pan, [Mm]łody [Pp]anie\b", "To ty, młody panie", "Filar XXV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\bto pan, [Mm]łody [Pp]anie\b", "to ty, młody panie", "Filar XXV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\bTo pan, młody panie\b", "To ty, młody panie", "Filar XXV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\bto pan, młody panie\b", "to ty, młody panie", "Filar XXV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\bTo pani, [Mm]łoda [Pp]ani\b", "To ty, młoda pani", "Filar XXV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\bto pani, [Mm]łoda [Pp]ani\b", "to ty, młoda pani", "Filar XXV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\b[Mm]łody [Pp]anie\b", "młody panie", "Filar LX - Ortografia Wołacza i Małe Litery"),
        (r"\b[Mm]łoda [Pp]ani\b", "młoda pani", "Filar LX - Ortografia Wołacza i Małe Litery"),
        (r"\b[Ww]asza [Ww]ysokość\b", "wasza wysokość", "Filar LX - Ortografia Wołacza i Małe Litery"),
        (r"\b[Ss]tarszy bracie\b", "brachu", "Filar XXV - Relacje Rodzinne"),
        (r"\b[Ss]tarsza siostro\b", "siostra", "Filar XXV - Relacje Rodzinne"),

        # Kingdom audio-matching & feudal address fixes (Pillars IV / XXV)
        (r"\b[Cc]hronić pana Bena\b", "Chronić panicza Hona", "Filar IV/XXV - Eliminacja Chińskiego Pinyin 'Ben' na rzecz Japońskiego Audio 'Hon' (Kingdom)"),
        (r"\bchronić pana Bena\b", "chronić panicza Hona", "Filar IV/XXV - Eliminacja Chińskiego Pinyin 'Ben' na rzecz Japońskiego Audio 'Hon' (Kingdom)"),
        (r"\b[Pp]ana Bena\b", "panicza Hona", "Filar IV/XXV - Pinyin 'Ben' -> Audio 'Hon'"),
        (r"\bpana Bena\b", "panicza Hona", "Filar IV/XXV - Pinyin 'Ben' -> Audio 'Hon'"),
        (r"\b[Pp]an Ben\b", "panicz Hon", "Filar IV/XXV - Pinyin 'Ben' -> Audio 'Hon'"),
        (r"\bpan Ben\b", "panicz Hon", "Filar IV/XXV - Pinyin 'Ben' -> Audio 'Hon'"),
        (r"\b[Pp]anie Benie\b", "paniczu Honie", "Filar IV/XXV - Pinyin 'Ben' -> Audio 'Hon'"),
        (r"\bpanie Benie\b", "paniczu Honie", "Filar IV/XXV - Pinyin 'Ben' -> Audio 'Hon'"),
        
        # Universal Rank / Nobility / Military Hybrids & Nominative Clobbering (Pillars IV / XXVII / LX)
        (r"\b[Zz]\s+panem\s+(?:[Ww]ielki(?:m)?\s+)?([Gg]enerał(?:em)?|[Kk]apitan(?:em)?|[Pp]ułkownik(?:em)?|[Mm]ajor(?:em)?|[Pp]orucznik(?:em)?|[Ss]ierżant(?:em)?|[Kk]omandor(?:em)?|[Aa]dmirał(?:em)?|[Dd]owódc(?:ą)?|[Ww]odz(?:em)?|[Kk]ról(?:em)?|[Kk]siąż(?:ę|ciem)?|[Hh]rabi(?:ą)?|[Cc]esarz(?:em)?|[Mm]argrabi(?:ą)?|[Aa]rcybiskup(?:em)?|[Dd]oktor(?:em)?|[Pp]rofesor(?:em)?)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b", r"z \1 \2", "Filar XXVII/IV - Eliminacja potworka 'z panem Tytuł X'"),
        (r"\bz\s+panem\s+(?:[Ww]ielki(?:m)?\s+)?([Gg]enerał(?:em)?|[Kk]apitan(?:em)?|[Pp]ułkownik(?:em)?|[Mm]ajor(?:em)?|[Pp]orucznik(?:em)?|[Ss]ierżant(?:em)?|[Kk]omandor(?:em)?|[Aa]dmirał(?:em)?|[Dd]owódc(?:ą)?|[Ww]odz(?:em)?|[Kk]ról(?:em)?|[Kk]siąż(?:ę|ciem)?|[Hh]rabi(?:ą)?|[Cc]esarz(?:em)?|[Mm]argrabi(?:ą)?|[Aa]rcybiskup(?:em)?|[Dd]oktor(?:em)?|[Pp]rofesor(?:em)?)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b", r"z \1 \2", "Filar XXVII/IV - Eliminacja potworka 'z panem Tytuł X'"),
        (r"\b[Zz]\s+panem\s+Wielki\s+Generał\b", "z Wielkim Generałem", "Filar IV/XXVII - Poprawność Narzędnika"),
        (r"\bz\s+panem\s+Wielki\s+Generał\b", "z Wielkim Generałem", "Filar IV/XXVII - Poprawność Narzędnika"),
        (r"\b[Pp]anem\s+Wielki\s+Generał\b", "Wielkim Generałem", "Filar IV/XXVII - Poprawność Narzędnika"),
        (r"\bpanem\s+Wielki\s+Generał\b", "Wielkim Generałem", "Filar IV/XXVII - Poprawność Narzędnika"),
        (r"\b[Pp]ana\s+Wielki\s+Generał\b", "Wielkiego Generała", "Filar IV/XXVII - Poprawność Dopełniacza"),
        (r"\bpana\s+Wielki\s+Generał\b", "Wielkiego Generała", "Filar IV/XXVII - Poprawność Dopełniacza"),
        (r"\b[Pp]an\s+Wielki\s+Generał\b", "Wielki Generał", "Filar XXVII - Eliminacja hybrydy 'Pan Wielki Generał'"),
        (r"\bpan\s+Wielki\s+Generał\b", "Wielki Generał", "Filar XXVII - Eliminacja hybrydy 'Pan Wielki Generał'"),
        (r"\b[Pp]ani [Ss]ensei\b", "Sensei", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]anie [Ss]ensei\b", "Sensei", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]an [Ss]ensei\b", "Sensei", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]ani [Ss]enpai\b", "Senpai", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]anie [Ss]enpai\b", "Senpai", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]an [Ss]enpai\b", "Senpai", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        
        # Epic & Military Collocations (Pillars IV / XLVII)
        (r"\b[Pp]owołał\s+armię\b", "zebrał armię", "Filar IV/XLVII - Epickość i naturalność ('zebrał armię' zamiast 'powołał armię')"),
        (r"\bpowołał\s+armię\b", "zebrał armię", "Filar IV/XLVII - Epickość i naturalność"),
        (r"\b[Pp]owołała\s+armię\b", "zebrała armię", "Filar IV/XLVII - Epickość i naturalność"),
        (r"\bpowołała\s+armię\b", "zebrała armię", "Filar IV/XLVII - Epickość i naturalność"),
        (r"\b[Pp]owołać\s+armię\b", "zebrać armię", "Filar IV/XLVII - Epickość i naturalność"),
        (r"\bpowołać\s+armię\b", "zebrać armię", "Filar IV/XLVII - Epickość i naturalność"),
        (r"\b[Pp]owołał\s+wojsko\b", "zebrał wojsko", "Filar IV/XLVII - Epickość i naturalność"),
        (r"\bpowołał\s+wojsko\b", "zebrał wojsko", "Filar IV/XLVII - Epickość i naturalność"),
        (r"\b[Pp]owołała\s+wojsko\b", "zebrała wojsko", "Filar IV/XLVII - Epickość i naturalność"),
        (r"\bpowołała\s+wojsko\b", "zebrała wojsko", "Filar IV/XLVII - Epickość i naturalność"),
        
        # Medical terminology & cause of death syntax (Pillar L)
        (r"\b[Zz]marła na wylew\b", "zmarła z powodu wylewu", "Filar L - Poprawność Medyczna"),
        (r"\b[Zz]marł na wylew\b", "zmarł z powodu wylewu", "Filar L - Poprawność Medyczna"),
        (r"\b[Uu]marła na wylew\b", "zmarła z powodu wylewu", "Filar L - Poprawność Medyczna"),
        (r"\b[Uu]marł na wylew\b", "zmarł z powodu wylewu", "Filar L - Poprawność Medyczna"),
        (r"\b[Zz]marła na krwotok\b", "zmarła wskutek krwotoku", "Filar L - Poprawność Medyczna"),
        (r"\b[Zz]marł na krwotok\b", "zmarł wskutek krwotoku", "Filar L - Poprawność Medyczna"),
        (r"\b[Zz]marła na atak serca\b", "zmarła na zawał", "Filar L - Poprawność Medyczna"),
        (r"\b[Zz]marł na atak serca\b", "zmarł na zawał", "Filar L - Poprawność Medyczna"),
        
        # Elimination of redundant sentence-initial "Ja " (Pillar I / Belczyk)
        (r"^Ja myślę, że\b", "Myślę, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja wiem, że\b", "Wiem, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja uważam, że\b", "Uważam, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja sądzę, że\b", "Sądzę, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja widzę, że\b", "Widzę, że", "Filar I - Eliminacja Zaimka Ja"),
        
        # Elimination of artificial "Czy" in short colloquial questions (Pillar IX)
        (r"^[Cc]zy jesteś pewna\?", "Jesteś pewna?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy jesteś pewien\?", "Jesteś pewien?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy wszystko w porządku\?", "Wszystko w porządku?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy to prawda\?", "To prawda?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy oszalałaś\?", "Oszalałaś?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy oszalałeś\?", "Oszalałeś?", "Filar IX - Pytania bez 'Czy'"),

        # Paralinguistics & vocal sound effects (Pillar XVIII)
        (r"\b[Aa]ra\s+ara\b", "O proszę...", "Filar XVIII - Paralingwistyka"),
        (r"\b[Tt]ch\b", "Tsk...", "Filar XVIII - Paralingwistyka"),
        (r"\b[Gg]uh\b", "Uch...", "Filar XVIII - Paralingwistyka"),
        (r"\b[Yy]oisho\b", "Hop...", "Filar XVIII - Kakegoe (Odgłos wysiłku)"),
        (r"\b[Yy]otto\b", "Hop...", "Filar XVIII - Kakegoe (Odgłos wysiłku)"),
        (r"\b[Dd]okkoisho\b", "I siup...", "Filar XVIII - Kakegoe (Odgłos wysiłku)"),
        (r"\b[Yy]oi\s+kora\b", "Raz, dwa...", "Filar XVIII - Kakegoe (Odgłos wysiłku)"),
        (r"^[Mm]ów[—–-]$", "Ach...", "Filar XVIII/IV - Eliminacja fałszywego czasownika 'Mów—' przy paralingwistycznym wdechu/wysiłku"),
        (r"^[Mm]ów\.\.\.$", "Ach...", "Filar XVIII/IV - Eliminacja fałszywego czasownika"),
        (r"^[Gg]adaj[—–-]$", "Uch...", "Filar XVIII/IV - Eliminacja fałszywego czasownika"),
        (r"^[Pp]owiedz[—–-]$", "Ach...", "Filar XVIII/IV - Eliminacja fałszywego czasownika"),
        (r"^[Ss]łuchaj[—–-]$", "Uch...", "Filar XVIII/IV - Eliminacja fałszywego czasownika"),
        (r"^[Pp]atrz[—–-]$", "Ach...", "Filar XVIII/IV - Eliminacja fałszywego czasownika"),
        (r"^[Cc]zekaj[—–-]$", "Ach...", "Filar XVIII/IV - Eliminacja fałszywego czasownika"),
        (r"^[Ss]tój[—–-]$", "Uch...", "Filar XVIII/IV - Eliminacja fałszywego czasownika"),

        # Third-language & translationese elimination (Pillar X)
        (r"\s*\((?:Demon|Generał|Wojownik|Wielki|Półelfka|Mag|Kupiec|Królowa|Arcybiskup|Wiedźma|Cesarz|Dowódca|Książę|Mistrz|Uczeń|Służąca|Ochroniarz|Strażnik|Bóg Wojny|Lisiooki|Potworny|Naczelny|Zastępczyni|Najsilniejszy|Sztuczny|Kandydatka|Demonica|Łowczyni|Rycerz|Wice-dowódca|Król|Markiz|Premier)[^)]*\)", "", "Filar IV/X - Eliminacja wycieku nawiasów encyklopedycznych do dialogu"),
        (r"\s*\([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\s,/–-]+\)$", "", "Filar IV/X - Eliminacja wycieku końcowych nawiasów objaśniających ze słownika"),
        (r"\b[Cc]o sprawia, że tak mówisz\?", "Czemu tak sądzisz?", "Filar X - Anti-Translationese"),
        (r"\b[Jj]estem zrobiony z\b", "Taki już jestem", "Filar X - Anti-Translationese"),
        (r"\b[Ww]zięcie pod uwagę\b", "Biorąc pod uwagę", "Filar X - Anti-Translationese"),

        # Audiovisual punctuation (Pillar LX)
        (r'([”"»])\s+([,.:;!?…])', r'\1\2', "Filar LX - Eliminacja spacji przed interpunkcją po cudzysłowie"),
        (r'([„"«])\s+', r'\1', "Filar LX - Eliminacja spacji po cudzysłowie otwierającym"),
        (r"!\?", "?!", "Filar LX - Zespolone Znaki Interpunkcyjne"),
        (r"!\?\?", "?!", "Filar LX - Zespolone Znaki Interpunkcyjne"),
        (r"\?\?\?", "?", "Filar LX - Zespolone Znaki Interpunkcyjne"),

        # Japanese -kun honorific & Yobisute first-name de-formalization (Pillar XLVI / IX)
        (r"\b[Pp]an(?:a|u|em|ie)?\s+(Shizuku|Issei|Arata|Shin|Luffy|Naruto|Ichigo|Tanjiro|Deku|Yuji|Yoritsugu|Aoi|Ren|Haru|Kaito|Sora|Yuto|Riku|Takumi|Daiki)\b", r"\1", "Filar XLVI - Eliminacja sztucznego 'pan' przy imieniu męskim (-kun)"),
        (r"\b[Pp]ani\s+(Kokoro|Miyabi|Akafuku|Hana|Yui|Rin|Sakura|Akari|Nanami|Mei|Hina|Mio|Yuna|Koharu|Saki|Kanna)\b", r"\1", "Filar XLVI - Eliminacja sztucznego 'pani' przy imieniu rówieśniczki (-chan)"),

        # Honorific Hybrids De-formalization (Pillar XLVIII / C)
        (r"\b[Pp]ani\s+[Ss]ensei\b", "Sensei", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych (Pani Sensei -> Sensei)"),
        (r"\b[Pp]anie\s+[Ss]ensei\b", "Sensei", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych (Panie Sensei -> Sensei)"),
        (r"\b[Pp]an\s+[Ss]ensei\b", "Sensei", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych (Pan Sensei -> Sensei)"),
        (r"\b[Pp]ani\s+[Ss]enpai\b", "Senpai", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych (Pani Senpai -> Senpai)"),
        (r"\b[Pp]anie\s+[Ss]enpai\b", "Senpai", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych (Panie Senpai -> Senpai)"),
        (r"\b[Pp]an\s+[Ss]enpai\b", "Senpai", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych (Pan Senpai -> Senpai)"),
        (r"\b[Pp]anie\s+[Ss]hishou\b", "Mistrzu", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych (Panie Shishou -> Mistrzu)"),
        (r"\b[Pp]anie\s+[Tt]aichou\b", "Kapitanie", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych (Panie Taichou -> Kapitanie)"),

        # 1-on-1 Dialogue Singular Number Normalization (Pillar LI / X)
        (r"\b[Ss]łyszeliście przed chwilą\b", "Słyszałeś przed chwilą", "Filar LI - Liczba Pojedyncza w Dialogu 1-na-1"),
        (r"\b[Ww]idzieliście przed chwilą\b", "Widziałeś przed chwilą", "Filar LI - Liczba Pojedyncza w Dialogu 1-na-1"),

        # Aizuchi & Conversational Reactive Expressions (Pillar XLIII)
        (r"\b[Cc]zyż nie\?", "prawda?", "Filar XLIII - Eliminacja archaizmu 'Czyż nie?' (Desho)"),
        (r"\b[Cc]o to za rzecz\?", "Co to ma być?", "Filar XLIII - Naturalne zdziwienie (Nani kore)"),

        # Cultural realia and Pedersen ECR (Pillar XIV)
        (r"\b[Kk]onbini\b", "sklep", "Filar XIV - Pedersen Generalization"),

        # Unit metrication (Pillar LIX)
        (r"\b100\s+stóp\b", "30 metrów", "Filar LIX - Metryzacja Miar"),
        (r"\b10\s+stóp\b", "3 metry", "Filar LIX - Metryzacja Miar"),
        (r"\b6\s+stóp\b", "prawie dwa metry", "Filar LIX - Metryzacja Miar"),

        # Epistemic modality & natural exponents (Pillar XLVI)
        (r"\b[Nn]ie ma wątpliwości, że\b", "bez wątpienia", "Filar XLVI - Modalność Epistemiczna"),
        (r"\b[Jj]est możliwe, że\b", "być może", "Filar XLVI - Modalność Epistemiczna"),

        # Japanese somatic idioms and grammatical traps (Pillars XV / VI / IX)
        (r"\b[Zz]ostałem opadany przez deszcz\b", "złapał mnie deszcz", "Filar VI - Adversative Passive Meiwaku Ukemi"),
        (r"\b[Zz]ostałam opadana przez deszcz\b", "złapał mnie deszcz", "Filar VI - Adversative Passive Meiwaku Ukemi"),
        (r"\b[Zz]ostał umarty przez matkę\b", "zmarła mu matka", "Filar VI - Adversative Passive Meiwaku Ukemi"),
        (r"\b[Mm]yślę, że chcę to zrobić\b", "chcę to zrobić", "Filar I - Intentional Aspect ~tai to omou"),
        (r"\b[Oo]trzymałem nauczenie\b", "dowiedziałem się", "Filar I - Benefactive Morau"),
        (r"\b[Nn]ie jest tak, że nie potrafię\b", "w sumie dałbym radę", "Filar IX - Podwójne Zaprzeczenie"),
        (r"\b[Pp]rzechylać szyję\b", "dziwić się", "Filar XV - Idiomy Somatyczne"),
        (r"\b[Bb]oli mnie klatka piersiowa\b", "serce mi pęka", "Filar XV - Idiomy Somatyczne"),
        (r"\b[Ww]yciągnąć ręce\b", "odwalić fuszerkę", "Filar XV - Idiomy Somatyczne"),
        (r"\b[Cc]iągnąć za nogę\b", "być ciężarem", "Filar XV - Idiomy Somatyczne"),
        (r"\b[Bb]rzuch mi wstaje\b", "szlag mnie trafia", "Filar XV - Idiomy Somatyczne"),

        # Shūjoshi pragmatics (Pillar XVI)
        (r"\bIku zo!?\b", "No to ruszamy!", "Filar XVI - Shūjoshi Pragmatics"),

        # Onomatopoeia taxonomy (Pillar XVII)
        (r"\b[Zz]okutto shita\b", "przeszły mnie ciarki", "Filar XVII - Onomatopoeia Gijougo"),
        (r"\b[Kk]yun to shita\b", "ścisnęło mnie za serce", "Filar XVII - Onomatopoeia Gijougo"),
        (r"\b[Ss]hiin to shita\b", "zapadła cisza jak makiem zasiał", "Filar XVII - Onomatopoeia Gitaigo"),
        (r"\b[Nn]oro-noro\b", "ślimaczym tempem", "Filar XVII - Onomatopoeia Giyougo"),

        # RPG & Isekai jargon (Pillar XXIV)
        (r"\b[Ss]tatus [Ww]indow\b", "[ OKNO STATUSU ]", "Filar XXIV - RPG / System Window"),

        (r"^[Cc]zy pójdziesz ze mną\?", "Pójdziesz ze mną?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy możemy już iść\?", "Możemy już iść?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy widziałaś to\?", "Widziałaś to?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy słyszałaś to\?", "Słyszałaś to?", "Filar IX - Pytania bez 'Czy'"),
    ]

    @classmethod
    def lint_and_fix_line(
        cls,
        text: str,
        speaker_gender: Optional[str] = None,
        is_all_girls_scene: bool = True,
        is_sign: bool = False,
        user_feedback_rules: Optional[List[Dict[str, Any]]] = None,
        custom_glossary: Optional[Dict[str, str]] = None,
        is_informal_ty: bool = False,
        audio_jp: str = "",
        prev_line_text: str = ""
    ) -> Tuple[str, List[str]]:
        """
        Analyzes and automatically fixes dialogue lines.
        Applies canonical AVT rules, inflection corrections, and user feedback overrides.
        Returns: (fixed_text, list_of_applied_fixes)
        """
        if not text:
            return "", []

        modified = text
        applied_fixes = []

        # 1. Automatic lexical and phraseological replacements (AVT Canon)
        for item in cls.FIXED_REPLACEMENTS:
            pattern = item[0]
            repl = item[1]
            pillar_tag = item[2] if len(item) > 2 else "Filar IV - Reguły Belczyka"
            if re.search(pattern, modified):
                modified = re.sub(pattern, repl, modified)
                repl_disp = repl if isinstance(repl, str) else "[korekta fleksyjna]"
                applied_fixes.append(f"[{pillar_tag}] {pattern} -> {repl_disp}")

        # 2. Dynamic user feedback rules
        if user_feedback_rules:
            for fb in user_feedback_rules:
                bad_pl = fb.get("bad_pl", "").strip()
                good_pl = fb.get("good_pl", "").strip()
                if not bad_pl or not good_pl or bad_pl == good_pl:
                    continue
                # Never allow meta-vocabulary or prompt instructions to be injected as replacements
                if any(kw in good_pl.lower() for kw in ["kanon", "avt", "filar", "prompt", "few-shot", "zakaz", ">"]):
                    continue
                # Handle slash-separated alternatives
                bad_variants = [v.strip() for v in bad_pl.split("/") if v.strip()]
                good_choice = good_pl.split("/")[0].strip()

                for variant in bad_variants:
                    pat = rf"\b{re.escape(variant)}\b"
                    if re.search(pat, modified, re.IGNORECASE):
                        modified = re.sub(pat, good_choice, modified, flags=re.IGNORECASE)
                        applied_fixes.append(f"[Korekta Użytkownika] '{variant}' -> '{good_choice}'")

        # 3. Strict glossary overrides (Sanitized from parenthetical notes/brackets)
        if custom_glossary:
            for src, raw_trg in custom_glossary.items():
                if not src or not raw_trg:
                    continue
                # Strip parenthetical clarifications e.g. "Tus (Miasto w Persji)" -> "Tus"
                clean_trg = re.sub(r"\s*[\(\[].*?[\)\]]", "", raw_trg).strip()
                if not clean_trg or src.lower() == clean_trg.lower():
                    continue
                pat_src = rf"\b{re.escape(src)}\b"
                if re.search(pat_src, modified, re.IGNORECASE):
                    modified = re.sub(pat_src, clean_trg, modified, flags=re.IGNORECASE)
                    applied_fixes.append(f"[Słownik Deterministyczny] '{src}' -> '{clean_trg}'")

        # 4. Grammatical gender alignment (Filar XIII & Filar CXXXVI: Acoustic & Cognitive Gender Triangulation)
        if not is_sign:
            spk_norm = (speaker_gender or "").lower()
            is_male_speaker = any(w in spk_norm for w in ["mężczyzna", "chłopiec", "male", "boy", "męski"])
            is_female_speaker = any(w in spk_norm for w in ["kobieta", "dziewczynka", "female", "girl", "żeński"]) or (is_all_girls_scene and not is_male_speaker)

            if is_male_speaker:
                male_fixes = [
                    (r"\b[Dd]omyślałam się\b", lambda m: "Domyślałem się" if m.group(0)[0].isupper() else "domyślałem się"),
                    (r"\b[Mm]yślałam\b", lambda m: "Myślałem" if m.group(0)[0].isupper() else "myślałem"),
                    (r"\b[Ww]iedziałam\b", lambda m: "Wiedziałem" if m.group(0)[0].isupper() else "wiedziałem"),
                    (r"\b[Ww]idziałam\b", lambda m: "Widziałem" if m.group(0)[0].isupper() else "widziałem"),
                    (r"\b[Zz]robiłam\b", lambda m: "Zrobiłem" if m.group(0)[0].isupper() else "zrobiłem"),
                    (r"\b[Pp]oszłam\b", lambda m: "Poszedłem" if m.group(0)[0].isupper() else "poszedłem"),
                    (r"\b[Zz]nalazłam\b", lambda m: "Znalazłem" if m.group(0)[0].isupper() else "znalazłem"),
                    (r"\b[Cc]zułam\b", lambda m: "Czułem" if m.group(0)[0].isupper() else "czułem"),
                    (r"\b[Ss]łyszałam\b", lambda m: "Słyszałem" if m.group(0)[0].isupper() else "słyszałem"),
                    (r"\b[Chch]ciałam\b", lambda m: "Chciałem" if m.group(0)[0].isupper() else "chciałem"),
                    (r"\b[Mm]ogłam\b", lambda m: "Mogłem" if m.group(0)[0].isupper() else "mogłem"),
                    (r"\b[Zz]rozumiałam\b", lambda m: "Zrozumiałem" if m.group(0)[0].isupper() else "zrozumiałem"),
                    (r"\b[Pp]owiedziałam\b", lambda m: "Powiedziałem" if m.group(0)[0].isupper() else "powiedziałem"),
                    (r"\b[Bb]ałam się\b", lambda m: "Bałem się" if m.group(0)[0].isupper() else "bałem się"),
                    (r"\b[Uu]dałam się\b", lambda m: "Udałem się" if m.group(0)[0].isupper() else "udałem się"),
                    (r"\b[Bb]yłam\b", lambda m: "Byłem" if m.group(0)[0].isupper() else "byłem"),
                    (r"\b[Zz]gubiłam się\b", lambda m: "Zgubiłem się" if m.group(0)[0].isupper() else "zgubiłem się"),
                    (r"\b[Jj]esteś pewna\?", "Jesteś pewien?"),
                    (r"\b[Gg]łupia jesteś\?", "Głupi jesteś?"),
                    (r"\b[Oo]szalałaś\?", "Oszalałeś?"),
                    (r"\b[Zz]głupiałaś\?", "Zgłupiałeś?"),
                ]
                for pattern, repl in male_fixes:
                    if re.search(pattern, modified):
                        modified = re.sub(pattern, repl, modified)
                        applied_fixes.append(f"[Filar CXXXVI - Mówca Męski/Chłopiec] Korekta rodzaju żeńskiego na męski: {pattern}")

            elif is_female_speaker:
                female_fixes = [
                    (r"\b[Gg]łupi jesteś\?", "Głupia jesteś?"),
                    (r"\b[Jj]esteś pewien\?", "Jesteś pewna?"),
                    (r"\b[Oo]szalałeś\?", "Oszalałaś?"),
                    (r"\b[Zz]głupiałeś\?", "Zgłupiałaś?"),
                    (r"\b[Ww]idziałeś to\?", "Widziałaś to?"),
                    (r"\b[Ss]łyszałeś to\?", "Słyszałaś to?"),
                    (r"\b[Zz]robiłeś to\?", "Zrobiłaś to?"),
                    (r"\b[Pp]oszedłeś tam\?", "Poszłaś tam?"),
                    (r"\b[Mm]yślałeś, że\b", "Myślałaś, że"),
                    (r"\b[Zz]gubiłem się\b", lambda m: "Zgubiłam się" if m.group(0)[0].isupper() else "zgubiłam się"),
                ]
                for pattern, repl in female_fixes:
                    if re.search(pattern, modified):
                        modified = re.sub(pattern, repl, modified)
                        applied_fixes.append(f"[Filar XIII/CXXXVI - Mówca Żeński/Dziewczynka] Korekta rodzaju męskiego na żeński: {pattern}")

        # 4b. Anti-Drift: Elimination of spurious 'pan/pani' in informal 1-on-1 dialogue (Filar CLVII)
        if not is_sign:
            audio_jp_lower = audio_jp.lower() if audio_jp else ""
            if not is_informal_ty and audio_jp_lower:
                if any(tok in audio_jp_lower for tok in ["omae", "kimi", "kisama", "temee", "お前", "君", "貴様", "てめえ"]):
                    is_informal_ty = True

            # Guard: If the line contains an explicit formal title or honorific address (e.g. "Panie Tanaka", "Pani Sato", "Panie doktorze"),
            # it is strictly formal and must NEVER be forced to "ty"!
            has_explicit_formal_vocative = bool(re.search(
                r"\b(panie|pani|panno|panu|pana)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+|doktorze|profesorze|inspektorze|prezesie|dyrektorze|kierowniku|komisarzu|mecenasie|oficerze|kapitanie|majorze|generale)\b",
                modified,
                re.IGNORECASE
            ))

            # True Yobisute: bare name vocative NOT preceded by formal honorific 'panie/pani'
            line_has_yobisute = False
            if not has_explicit_formal_vocative:
                yobi_m = re.search(r"(?<!\bpanie\s)(?<!\bpani\s)(?<!\bpanno\s)(?<!\bpanu\s)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})[,?!](?:\s+|\\N)+.*\b(pan|pani|pana|panu)\b", modified, re.IGNORECASE)
                if yobi_m:
                    first_w = yobi_m.group(1).lower()
                    if first_w not in ["panie", "pani", "panno", "panu", "pana", "proszę", "przepraszam", "doktorze", "profesorze", "inspektorze", "zaraz", "chwila", "czekaj", "słuchaj", "patrz", "widzisz"]:
                        line_has_yobisute = True

            if (is_informal_ty or line_has_yobisute) and not has_explicit_formal_vocative:
                raw_pan_pairs = [
                    ("wygrał", "pan", "wygrałeś"),
                    ("wygrała", "pani", "wygrałaś"),
                    ("zrobił", "pan", "zrobiłeś"),
                    ("zrobiła", "pani", "zrobiłaś"),
                    ("widział", "pan", "widziałeś"),
                    ("widziała", "pani", "widziałaś"),
                    ("słyszał", "pan", "słyszałeś"),
                    ("słyszała", "pani", "słyszałaś"),
                    ("powiedział", "pan", "powiedziałeś"),
                    ("powiedziała", "pani", "powiedziałaś"),
                    ("poszedł", "pan", "poszedłeś"),
                    ("poszła", "pani", "poszłaś"),
                    ("miał", "pan", "miałeś"),
                    ("miała", "pani", "miałaś"),
                    ("był", "pan", "byłeś"),
                    ("była", "pani", "byłaś"),
                    ("chciał", "pan", "chciałeś"),
                    ("chciała", "pani", "chciałaś"),
                    ("mógł", "pan", "mogłeś"),
                    ("mogła", "pani", "mogłaś"),
                    ("wiedział", "pan", "wiedziałeś"),
                    ("wiedziała", "pani", "wiedziałaś"),
                    ("myślał", "pan", "myślałeś"),
                    ("myślała", "pani", "myślałaś"),
                    ("pan", "wygrał", "wygrałeś"),
                    ("pani", "wygrała", "wygrałaś"),
                    ("pan", "zrobił", "zrobiłeś"),
                    ("pani", "zrobiła", "zrobiłaś"),
                    ("pan", "widział", "widziałeś"),
                    ("pani", "widziała", "widziałaś"),
                    ("pan", "słyszał", "słyszałeś"),
                    ("pani", "słyszała", "słyszałaś"),
                    ("pan", "powiedział", "powiedziałeś"),
                    ("pani", "powiedziała", "powiedziałaś"),
                    ("pan", "wie", "wiesz"),
                    ("pani", "wie", "wiesz"),
                    ("wie", "pan", "wiesz"),
                    ("wie", "pani", "wiesz"),
                    ("pan", "widzi", "widzisz"),
                    ("pani", "widzi", "widzisz"),
                    ("widzi", "pan", "widzisz"),
                    ("widzi", "pani", "widzisz"),
                    ("pan", "myśli", "myślisz"),
                    ("pani", "myśli", "myślisz"),
                    ("myśli", "pan", "myślisz"),
                    ("myśli", "pani", "myślisz"),
                    ("pan", "mówi", "mówisz"),
                    ("pani", "mówi", "mówisz"),
                    ("mówi", "pan", "mówisz"),
                    ("mówi", "pani", "mówisz"),
                ]
                spurious_pan_fixes = [
                    (rf"\b{re.escape(w1)}(?:\s+|\\N)+{re.escape(w2)}\b", repl)
                    for w1, w2, repl in raw_pan_pairs
                ]
                spurious_pan_fixes.extend([
                    (r"\bniech(?:\s+|\\N)+pan(?:\s+|\\N)+powie\b", "powiedz"),
                    (r"\bniech(?:\s+|\\N)+pani(?:\s+|\\N)+powie\b", "powiedz"),
                    (r"\bniech(?:\s+|\\N)+pan(?:\s+|\\N)+spojrzy\b", "spójrz"),
                    (r"\bniech(?:\s+|\\N)+pani(?:\s+|\\N)+spojrzy\b", "spójrz"),
                    (r"\bniech(?:\s+|\\N)+pan(?:\s+|\\N)+posłucha\b", "posłuchaj"),
                    (r"\bniech(?:\s+|\\N)+pani(?:\s+|\\N)+posłucha\b", "posłuchaj"),
                    (r"\bniech(?:\s+|\\N)+pan(?:\s+|\\N)+uważa\b", "uważaj"),
                    (r"\bniech(?:\s+|\\N)+pani(?:\s+|\\N)+uważa\b", "uważaj"),
                    (r"\bniech(?:\s+|\\N)+pan(?:\s+|\\N)+poczeka\b", "poczekaj"),
                    (r"\bniech(?:\s+|\\N)+pani(?:\s+|\\N)+poczeka\b", "poczekaj"),
                ])
                for pattern, repl in spurious_pan_fixes:
                    if re.search(pattern, modified, re.IGNORECASE):
                        def _repl_match(m, r=repl):
                            return r.capitalize() if m.group(0)[0].isupper() else r
                        modified = re.sub(pattern, _repl_match, modified, flags=re.IGNORECASE)
                        applied_fixes.append(f"[Filar CLVII - Spójność Form Adresatywnych] Korekta sztucznego 'pana/pani' na formę 'ty': {pattern} -> {repl}")

        # 4c. Cross-Audio Auditory Fixes (Filar CLVIII - Zgodność Foniczno-Semantyczna Seiyū)
        if not is_sign and audio_jp:
            clean_audio_jp = audio_jp.lower()
            spk_norm = (speaker_gender or "").lower()
            is_male_spk = any(w in spk_norm for w in ["mężczyzna", "chłopiec", "male", "boy", "męski"])
            is_female_spk = any(w in spk_norm for w in ["kobieta", "dziewczynka", "female", "girl", "żeński"]) or (is_all_girls_scene and not is_male_spk)

            # 1. HITORI (一人 / 独り / ひとり): w audio prośba o samotność -> ZAKAZ 'daj mi spokój'
            if any(k in clean_audio_jp for k in ["hitori", "一人", "独り", "ひとり"]):
                if re.search(r"\b[Dd]aj(?:\s+|\\N)+mi(?:\s+|\\N)+spokój\b", modified):
                    repl_hitori = "Zostaw mnie samą" if is_female_spk else "Zostaw mnie samego"
                    def _hitori_repl(m, r=repl_hitori):
                        return r if m.group(0)[0].isupper() else r.lower()
                    modified = re.sub(r"\b[Dd]aj(?:\s+|\\N)+mi(?:\s+|\\N)+spokój\b", _hitori_repl, modified)
                    applied_fixes.append(f"[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Hitori' w audio: zastąpiono 'daj mi spokój' przez '{repl_hitori.lower()}'")
                elif re.search(r"\b[Dd]ajcie(?:\s+|\\N)+mi(?:\s+|\\N)+spokój\b", modified):
                    repl_hitori = "Zostawcie mnie samą" if is_female_spk else "Zostawcie mnie samego"
                    def _hitori_pl_repl(m, r=repl_hitori):
                        return r if m.group(0)[0].isupper() else r.lower()
                    modified = re.sub(r"\b[Dd]ajcie(?:\s+|\\N)+mi(?:\s+|\\N)+spokój\b", _hitori_pl_repl, modified)
                    applied_fixes.append(f"[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Hitori' w audio: zastąpiono 'dajcie mi spokój' przez '{repl_hitori.lower()}'")

            # 2. BETSUNI (別に / べつに): chłód, foch, dystans -> ZAKAZ 'to nic takiego', 'nie ma sprawy'
            if any(k in clean_audio_jp for k in ["betsuni", "別に", "べつに"]):
                if re.search(r"\b[Tt]o(?:\s+|\\N)+nic(?:\s+|\\N)+takiego\b", modified):
                    def _betsuni_repl(m):
                        return "Wcale nie" if m.group(0)[0].isupper() else "wcale nie"
                    modified = re.sub(r"\b[Tt]o(?:\s+|\\N)+nic(?:\s+|\\N)+takiego\b", _betsuni_repl, modified)
                    applied_fixes.append("[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Betsuni' w audio: zastąpiono 'to nic takiego' przez 'wcale nie'")
                elif re.search(r"\b[Nn]ie(?:\s+|\\N)+ma(?:\s+|\\N)+sprawy\b", modified):
                    def _betsuni_sprawy(m):
                        return "Wcale nie" if m.group(0)[0].isupper() else "wcale nie"
                    modified = re.sub(r"\b[Nn]ie(?:\s+|\\N)+ma(?:\s+|\\N)+sprawy\b", _betsuni_sprawy, modified)
                    applied_fixes.append("[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Betsuni' w audio: zastąpiono 'nie ma sprawy' przez 'wcale nie'")

            # 3. YOKATTA (よかった / 良かった): ulga, kamień z serca -> ZAKAZ 'to było dobre'
            if any(k in clean_audio_jp for k in ["yokatta", "よかった", "良かった"]):
                if re.search(r"\b[Tt]o(?:\s+|\\N)+było(?:\s+|\\N)+dobre\b", modified):
                    def _yokatta_repl(m):
                        return "Całe szczęście" if m.group(0)[0].isupper() else "całe szczęście"
                    modified = re.sub(r"\b[Tt]o(?:\s+|\\N)+było(?:\s+|\\N)+dobre\b", _yokatta_repl, modified)
                    applied_fixes.append("[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Yokatta' w audio: zastąpiono 'to było dobre' przez 'całe szczęście'")

            # 4. YATTA (やった): radość z triumfu -> ZAKAZ 'zrobiłem to'
            if any(k in clean_audio_jp for k in ["yatta", "やった"]):
                if re.search(r"\b[Zz]robił(?:em|am)(?:\s+|\\N)+to\b", modified):
                    def _yatta_repl(m):
                        return "Udało się" if m.group(0)[0].isupper() else "udało się"
                    modified = re.sub(r"\b[Zz]robił(?:em|am)(?:\s+|\\N)+to\b", _yatta_repl, modified)
                    applied_fixes.append("[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Yatta' w audio: zastąpiono 'zrobiłem/am to' przez 'udało się'")

            # 5. MENDOKUSAI (面倒くさい / めんどくさい): zniechęcenie -> ZAKAZ 'co za ból'
            if any(k in clean_audio_jp for k in ["mendokusai", "面倒くさい", "めんどくさい", "面倒"]):
                if re.search(r"\b[Cc]o(?:\s+|\\N)+za(?:\s+|\\N)+ból\b", modified):
                    def _mendo_repl(m):
                        return "Co za męczarnia" if m.group(0)[0].isupper() else "co za męczarnia"
                    modified = re.sub(r"\b[Cc]o(?:\s+|\\N)+za(?:\s+|\\N)+ból\b", _mendo_repl, modified)
                    applied_fixes.append("[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Mendokusai' w audio: zastąpiono 'co za ból' przez 'co za męczarnia'")

            # 6. WAKA / WAKA-SAMA (若 / 若様): panicz, młody pan -> KATEGORYCZNY ZAKAZ 'bracie' / 'brachu'
            if any(k in clean_audio_jp for k in ["waka", "若", "若様", "wakagimi", "若君"]):
                if re.search(r"\b[Bb]racie\b", modified):
                    def _waka_repl(m):
                        return "Panie" if m.group(0)[0].isupper() else "panie"
                    modified = re.sub(r"\b[Bb]racie\b", _waka_repl, modified)
                    applied_fixes.append("[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Waka' w audio: zastąpiono błędne 'bracie' przez 'panie'")
                elif re.search(r"\b[Bb]rachu\b", modified):
                    def _waka_brachu_repl(m):
                        return "Panie" if m.group(0)[0].isupper() else "panie"
                    modified = re.sub(r"\b[Bb]rachu\b", _waka_brachu_repl, modified)
                    applied_fixes.append("[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Waka' w audio: zastąpiono błędne 'brachu' przez 'panie'")

        # 4d. Directive/Warning & Wh-Question Confirmation Guard (Filar XLIII & CXLVI)
        # When preceding line is an explicit warning or imperative directive, lone affirmative "Tak / T-Tak" is an unnatural calque.
        if not is_sign and prev_line_text:
            prev_clean = re.sub(r"\{[^\}]*\}", "", prev_line_text).strip().lower()
            # Directive/warning triggers in previous line
            is_prev_warning = bool(re.search(
                r"\b(uważaj|uważajcie|ostrożnie|czekaj|poczekaj|zaczekaj|stój|stójcie|pospiesz|pospieszcie|chodź|chodźcie|nie ruszaj|trzymaj się|uważaj pod nogi)\b",
                prev_clean,
                re.IGNORECASE
            ))
            is_prev_wh_question = bool(prev_clean.endswith("?") and re.search(
                r"\b(dokąd|gdzie|skąd|kiedy|dlaczego|czemu|po\s+co|kto|kogo|komu|kim|co|czego|czym|jak|jaki|jaka|jakie|jakim|jakich|o\s+co|o\s+czym|z\s+kim|w\s+jaki\s+sposób)\b",
                prev_clean,
                re.IGNORECASE
            ))
            is_prev_neg_q = bool(prev_clean.endswith("?") and (
                re.search(r"\bnie\s+(jest|jesteś|jesteście|są|był|była|było|byli|byłeś|byłaś|będzie|będziesz|będą|ma|masz|macie|chcesz|chce|chcecie|wiesz|wie|wiecie|możesz|może|możecie|idziesz|idzie|idziecie|zrobisz|mówisz|widzisz|słyszysz)\b", prev_clean, re.IGNORECASE) or
                any(prev_clean.startswith(w) for w in ["don't", "aren't", "didn't", "can't", "won't", "haven't", "isn't"])
            ))
            if is_prev_warning:
                # Check if current line is solely an affirmative "Tak / T-Tak" (with optional ellipsis or exclamation mark)
                clean_current = re.sub(r"\{[^\}]*\}", "", modified).strip()
                m_aff = re.match(r"^([Tt]-[Tt]ak|[Tt]ak)([\.!\?…]*)$", clean_current)
                if m_aff:
                    word = m_aff.group(1)
                    punct = m_aff.group(2) or "."
                    if word.lower().startswith("t-"):
                        repl_word = "D-Dobrze"
                    else:
                        repl_word = "Dobrze" if word[0].isupper() else "dobrze"
                    
                    modified = re.sub(rf"\b{re.escape(word)}", repl_word, modified)
                    applied_fixes.append(f"[Filar XLIII/CXLVI - Dyrektywne Potwierdzenie] Wykryto odpowiedź na ostrzeżenie/polecenie ('{prev_clean[:30]}...'): zastąpiono '{word}{punct}' przez '{repl_word}{punct}'")
            elif is_prev_wh_question:
                clean_current = re.sub(r"\{[^\}]*\}", "", modified).strip()
                m_aff = re.match(r"^([Tt]-[Tt]ak|[Tt]ak)([\.!\?…]*)$", clean_current)
                if m_aff:
                    word = m_aff.group(1)
                    punct = m_aff.group(2) or "..."
                    if not punct.endswith("..."):
                        punct = "..."
                    repl_word = "E-Eee" if word.lower().startswith("t-") else "Eee"
                    modified = re.sub(rf"\b{re.escape(word)}[\.!\?…]*", f"{repl_word}{punct}", modified)
                    applied_fixes.append(f"[Filar XLIII/CXLVI - Reakcja na Pytanie Otwarte] Wykryto odpowiedź na pytanie otwarte ('{prev_clean[:30]}...'): zastąpiono nielogiczne '{word}' przez '{repl_word}{punct}'")
            elif is_prev_neg_q:
                clean_current = re.sub(r"\{[^\}]*\}", "", modified).strip()
                m_aff = re.match(r"^([Tt]-[Tt]ak|[Tt]ak)([\.!\?…]*)$", clean_current)
                if m_aff:
                    word = m_aff.group(1)
                    punct = m_aff.group(2) or "."
                    repl_word = "N-Nie" if word.lower().startswith("t-") else ("Nie" if word[0].isupper() else "nie")
                    modified = re.sub(rf"\b{re.escape(word)}", repl_word, modified)
                    applied_fixes.append(f"[Filar CLIV - Echo Agreement] Wykryto odpowiedź na pytanie z przeczeniem ('{prev_clean[:30]}...'): zastąpiono nielogiczne '{word}{punct}' przez '{repl_word}{punct}'")

        # 4e. Focalization & Dramatic Irony Guard (Filar CLXI - Nienaruszalność Perspektywy Narracyjnej)
        if not is_sign and audio_jp:
            clean_audio_jp = audio_jp.lower()
            if any(k in clean_audio_jp for k in ["chinmoku no majo", "沈黙の魔女"]):
                # 1. Strip unsolicited thought italics from spoken dialogue
                if "{\\i1}" in modified:
                    modified = re.sub(r"\{\\i[01]\}", "", modified).strip()
                    applied_fixes.append("[Filar CLXI - Zakaz Konwersji Dialogu na Myśl] Usunięto sztuczną kursywę {\\i1} z dialogu mówionego na głos")

                # 2. Guard against 1st person possessive drift ('mój esej', 'moja praca', etc.)
                if re.search(r"\bmój\s+(esej|artykuł|traktat)\b", modified, re.IGNORECASE):
                    def _witch_essay_repl(m):
                        noun = m.group(1)
                        res = f"{noun} Wiedźmy Milczenia"
                        return res.capitalize() if m.group(0)[0].isupper() else res
                    modified = re.sub(r"\bmój\s+(esej|artykuł|traktat)\b", _witch_essay_repl, modified, flags=re.IGNORECASE)
                    applied_fixes.append("[Filar CLXI - Nienaruszalność Perspektywy] Skorygowano zdradę tożsamości incognito: 'mój esej' -> 'esej Wiedźmy Milczenia'")
                elif re.search(r"\bmoj(?:a|ej|ą)\s+prac(?:a|y|ę)\b", modified, re.IGNORECASE):
                    def _witch_work_repl(m):
                        res = "praca Wiedźmy Milczenia"
                        return res.capitalize() if m.group(0)[0].isupper() else res
                    modified = re.sub(r"\bmoj(?:a|ej|ą)\s+prac(?:a|y|ę)\b", _witch_work_repl, modified, flags=re.IGNORECASE)
                    applied_fixes.append("[Filar CLXI - Nienaruszalność Perspektywy] Skorygowano zdradę tożsamości incognito: 'moja praca' -> 'praca Wiedźmy Milczenia'")

        # 5. Anti-Bracket normalization for all subtitles (Pillars IV & LX)
        # 5a. Strip outer square brackets e.g. "[ Przepraszam za zwłokę! ]" -> "Przepraszam za zwłokę!"
        if modified.startswith("[") and modified.endswith("]"):
            inner = modified[1:-1].strip()
            if inner:
                modified = inner
                applied_fixes.append("[Filar IV/LX - Eliminacja nawiasów kwadratowych z tekstu]")

        # 5b. Convert screaming ALL-CAPS dialogue to natural sentence case
        if not is_sign:
            letters = re.findall(r'[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]', modified)
            if len(letters) >= 6 and all(c.isupper() for c in letters):
                # Capitalize first letter of each sentence
                sentences = re.split(r'([.!?…]+(?:\s+|$))', modified.lower())
                capitalized_parts = []
                for part in sentences:
                    if part and any(c.isalpha() for c in part):
                        # Find first alphabetic char and capitalize
                        first_alpha_idx = next((i for i, c in enumerate(part) if c.isalpha()), -1)
                        if first_alpha_idx != -1:
                            part = part[:first_alpha_idx] + part[first_alpha_idx].upper() + part[first_alpha_idx + 1:]
                    capitalized_parts.append(part)
                modified = "".join(capitalized_parts)
                applied_fixes.append("[Filar IV/LX - Konwersja ALL-CAPS w dialogu na naturalną wielkość liter]")

        # 6. Automatic conversion of spelled-out ordinal numbers in episode/chapter headings (Filar LIX & XCVIII)
        modified, num_fixes = cls.convert_verbal_ordinal_numbers(modified)
        applied_fixes.extend(num_fixes)

        # 7. Guard against duplicate spaces
        modified = re.sub(r"[ \t]+", " ", modified).strip()

        return modified, applied_fixes

    @classmethod
    def convert_verbal_ordinal_numbers(cls, text: str) -> Tuple[str, List[str]]:
        """
        Converts spelled-out Polish ordinal numbers in episode/chapter titles to Arabic numerals (Filar LIX / XCVIII).
        E.g. 'ODCINEK PIĘĆDZIESIĄTY DRUGI' -> 'ODCINEK 52'
             'ODCINEK PIERWSZY' -> 'ODCINEK 1'
             'ROZDZIAŁ DWUDZIESTY CZWARTY' -> 'ROZDZIAŁ 24'
        """
        ORDINAL_TENS = {
            "dwudziesty": 20, "dwudziestej": 20, "dwudziestego": 20, "dwudzieste": 20, "dwudziesta": 20,
            "trzydziesty": 30, "trzydziestej": 30, "trzydziestego": 30, "trzydzieste": 30, "trzydziesta": 30,
            "czterdziesty": 40, "czterdziestej": 40, "czterdziestego": 40, "czterdzieste": 40, "czterdziesta": 40,
            "pięćdziesiąty": 50, "pięćdziesiątej": 50, "pięćdziesiątego": 50, "pięćdziesiąte": 50, "pięćdziesiąta": 50,
            "sześćdziesiąty": 60, "sześćdziesiątej": 60, "sześćdziesiątego": 60, "sześćdziesiąte": 60, "sześćdziesiąta": 60,
            "siedemdziesiąty": 70, "siedemdziesiątej": 70, "siedemdziesiątego": 70, "siedemdziesiąte": 70, "siedemdziesiąta": 70,
            "osiemdziesiąty": 80, "osiemdziesiątej": 80, "osiemdziesiątego": 80, "osiemdziesiąte": 80, "osiemdziesiąta": 80,
            "dziewięćdziesiąty": 90, "dziewięćdziesiątej": 90, "dziewięćdziesiątego": 90, "dziewięćdziesiąte": 90, "dziewięćdziesiąta": 90,
            "setny": 100, "setnej": 100, "setnego": 100, "setne": 100, "setna": 100,
        }
        ORDINAL_UNITS_AND_TEENS = {
            "pierwszy": 1, "pierwsza": 1, "pierwsze": 1, "pierwszego": 1, "pierwszej": 1,
            "drugi": 2, "druga": 2, "drugie": 2, "drugiego": 2, "drugiej": 2,
            "trzeci": 3, "trzecia": 3, "trzecie": 3, "trzeciego": 3, "trzeciej": 3,
            "czwarty": 4, "czwarta": 4, "czwarte": 4, "czwartego": 4, "czwartej": 4,
            "piąty": 5, "piąta": 5, "piąte": 5, "piątego": 5, "piątej": 5,
            "szósty": 6, "szósta": 6, "szóste": 6, "szóstego": 6, "szóstej": 6,
            "siódmy": 7, "siódma": 7, "siódme": 7, "siódmego": 7, "siódmej": 7,
            "ósmy": 8, "ósma": 8, "ósme": 8, "ósmego": 8, "ósmej": 8,
            "dziewiąty": 9, "dziewiąta": 9, "dziewiąte": 9, "dziewiątego": 9, "dziewiątej": 9,
            "dziesiąty": 10, "dziesiąta": 10, "dziesiąte": 10, "dziesiątego": 10, "dziesiątej": 10,
            "jedenasty": 11, "jedenasta": 11, "jedenaste": 11, "jedenastego": 11, "jedenastej": 11,
            "dwunasty": 12, "dwunasta": 12, "dwunaste": 12, "dwunastego": 12, "dwunastej": 12,
            "trzynasty": 13, "trzynasta": 13, "trzynaste": 13, "trzynastego": 13, "trzynastej": 13,
            "czternasty": 14, "czternasta": 14, "czternaste": 14, "czternastego": 14, "czternastej": 14,
            "piętnasty": 15, "piętnasta": 15, "piętnaste": 15, "piętnastego": 15, "piętnastej": 15,
            "szesnasty": 16, "szesnasta": 16, "szesnaste": 16, "szesnastego": 16, "szesnastej": 16,
            "siedemnasty": 17, "siedemnasta": 17, "siedemnaste": 17, "siedemnastego": 17, "siedemnastej": 17,
            "osiemnasty": 18, "osiemnasta": 18, "osiemnaste": 18, "osiemnastego": 18, "osiemnastej": 18,
            "dziewiętnasty": 19, "dziewiętnasta": 19, "dziewiętnaste": 19, "dziewiętnastego": 19, "dziewiętnastej": 19,
        }

        fixes = []
        modified = text

        pattern = re.compile(
            r"\b(odcinek|rozdział|akt|część|epizod)\s+([a-ząćęłńóśźż]+)(?:\s+([a-ząćęłńóśźż]+))?\b",
            re.IGNORECASE
        )

        def repl(match):
            prefix = match.group(1)
            w1 = match.group(2).lower()
            w2 = match.group(3).lower() if match.group(3) else None

            val = 0
            consumed_two = False

            if w1 in ORDINAL_TENS:
                val += ORDINAL_TENS[w1]
                if w2 and w2 in ORDINAL_UNITS_AND_TEENS:
                    val += ORDINAL_UNITS_AND_TEENS[w2]
                    consumed_two = True
            elif w1 in ORDINAL_UNITS_AND_TEENS:
                val += ORDINAL_UNITS_AND_TEENS[w1]
            else:
                return match.group(0)

            if val > 0:
                fixes.append(f"[Filar LIX/XCVIII - Notacja Cyfrowa Odcinka] '{match.group(0)}' -> '{prefix} {val}'")
                if consumed_two:
                    return f"{prefix} {val}"
                else:
                    return f"{prefix} {val}" + (f" {match.group(3)}" if w2 and not consumed_two else "")

            return match.group(0)

        modified = pattern.sub(repl, modified)
        return modified, fixes

FEMININE_IRREGULAR_TO_MASCULINE = {
    "była": "był",
    "poszła": "poszedł",
    "przyszła": "przyszedł",
    "odeszła": "odszedł",
    "weszła": "wszedł",
    "wyszła": "wyszedł",
    "doszła": "doszedł",
    "przeszła": "przeszedł",
    "znalazła": "znalazł",
    "mogła": "mógł",
    "pomogła": "pomógł",
    "uciekła": "uciekł",
    "upadła": "upadł",
    "zmarła": "zmarł",
    "dotarła": "dotarł",
    "zjadła": "zjadł",
    "upiekła": "upiekł",
    "wiodła": "wiódł",
    "niosła": "niósł",
    "chciała": "chciał",
    "miała": "miał",
    "wiedziała": "wiedział",
    "widziała": "widział",
    "musiała": "musiał",
}

MASCULINE_IRREGULAR_TO_FEMININE = {
    "był": "była",
    "poszedł": "poszła",
    "przyszedł": "przyszła",
    "odszedł": "odeszła",
    "wszedł": "weszła",
    "wyszedł": "wyszła",
    "doszedł": "doszła",
    "przeszedł": "przeszła",
    "znalazł": "znalazła",
    "mógł": "mogła",
    "pomógł": "pomogła",
    "uciekł": "uciekła",
    "upadł": "upadła",
    "zmarł": "zmarła",
    "dotarł": "dotarła",
    "chciał": "chciała",
    "miał": "miała",
    "wiedział": "wiedziała",
    "widział": "widziała",
    "musiał": "musiała",
}

FIRST_PERSON_FEMININE_TO_MASCULINE = [
    (r"\bpowinnam\s+była\b", "powinienem był"),
    (r"\bpowinnam\b", "powinienem"),
    (r"\bchciałabym\b", "chciałbym"),
    (r"\bmogłabym\b", "mógłbym"),
    (r"\bwolałabym\b", "wolałbym"),
    (r"\bbyłam\b", "byłem"),
    (r"\bzrobiłam\b", "zrobiłem"),
    (r"\bposzłam\b", "poszedłem"),
    (r"\bprzyszłam\b", "przyszedłem"),
    (r"\bwiedziałam\b", "wiedziałem"),
    (r"\bwidziałam\b", "widziałem"),
    (r"\bmówiłam\b", "mówiłem"),
    (r"\bczekałam\b", "czekałem"),
    (r"\bmyślałam\b", "myślałem"),
    (r"\bzrozumiałam\b", "zrozumiałem"),
    (r"\bbałam\s+się\b", "bałem się"),
    (r"\bsłyszałam\b", "słyszałem"),
    (r"\bczułam\b", "czułem"),
    (r"\bobiecałam\b", "obiecałem"),
    (r"\bpostanowiłam\b", "postanowiłem"),
    (r"\bwróciłam\b", "wróciłem"),
    (r"\bznalazłam\b", "znalazłem"),
    (r"\bodeszłam\b", "odszedłem"),
    (r"\bwyszłam\b", "wyszedłem"),
    (r"\bweszłam\b", "wszedłem")
]

FIRST_PERSON_MASCULINE_TO_FEMININE = [
    (r"\bpowinienem\s+był\b", "powinnam była"),
    (r"\bpowinienem\b", "powinnam"),
    (r"\bchciałbym\b", "chciałabym"),
    (r"\bmógłbym\b", "mogłabym"),
    (r"\bwolałbym\b", "wolałabym"),
    (r"\bbyłem\b", "byłam"),
    (r"\bzrobiłem\b", "zrobiłam"),
    (r"\bposzedłem\b", "poszłam"),
    (r"\bprzyszedłem\b", "przyszłam"),
    (r"\bwiedziałem\b", "wiedziałam"),
    (r"\bwidziałem\b", "widziałam"),
    (r"\bmówiłem\b", "mówiłam"),
    (r"\bczekałem\b", "czekałam"),
    (r"\bmyślałem\b", "myślałam"),
    (r"\bzrozumiałem\b", "zrozumiałam"),
    (r"\bbałem\s+się\b", "bałam się"),
    (r"\bsłyszałem\b", "słyszałam"),
    (r"\bczułem\b", "czułam"),
    (r"\bobiecałem\b", "obiecałam"),
    (r"\bpostanowiłem\b", "postanowiłam"),
    (r"\bwróciłem\b", "wróciłam"),
    (r"\bodszedłem\b", "odeszłam"),
    (r"\bwyszedłem\b", "wyszłam"),
    (r"\bwszedłem\b", "weszłam"),
    (r"\bgdybym\s+wiedział\b", "gdybym wiedziała"),
    (r"\bjuż\s+dawno\s+doniósłbym\b", "już dawno doniosłabym"),
    (r"\bdoniósłbym\b", "doniosłabym"),
    (r"\botrzymałem\b", "otrzymałam"),
    (r"\bstraciłem\b", "straciłam"),
    (r"\bchciałem\b", "chciałam"),
    (r"\bmogłem\b", "mogłam")
]

def convert_feminine_past_to_masculine(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in FEMININE_IRREGULAR_TO_MASCULINE:
        res = FEMININE_IRREGULAR_TO_MASCULINE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("ęła"):
        res = v_lower[:-3] + "ął"
    elif v_lower.endswith("iała"):
        res = v_lower[:-4] + "iał"
    elif v_lower.endswith("ała"):
        res = v_lower[:-3] + "ał"
    elif v_lower.endswith("iła"):
        res = v_lower[:-3] + "ił"
    elif v_lower.endswith("yła"):
        res = v_lower[:-3] + "ył"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

def convert_masculine_past_to_feminine(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in MASCULINE_IRREGULAR_TO_FEMININE:
        res = MASCULINE_IRREGULAR_TO_FEMININE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("ął"):
        res = v_lower[:-2] + "ęła"
    elif v_lower.endswith("iał"):
        res = v_lower[:-3] + "iała"
    elif v_lower.endswith("ał"):
        res = v_lower[:-2] + "ała"
    elif v_lower.endswith("ił"):
        res = v_lower[:-2] + "iła"
    elif v_lower.endswith("ył"):
        res = v_lower[:-2] + "yła"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

VIRILE_PLURAL_IRREGULAR_TO_NONVIRILE: Dict[str, str] = {
    "znaleźliście": "znalazłyście",
    "poszliście": "poszłyście",
    "przyszliście": "przyszłyście",
    "wyszliście": "wyszłyście",
    "odeszliście": "odeszłyście",
    "weszliście": "weszłyście",
    "przeszliście": "przeszłyście",
    "doszliście": "doszłyście",
    "zeszliście": "zeszłyście",
    "mogliście": "mogłyście",
    "pomogliście": "pomogłyście",
    "byliście": "byłyście",
    "widzieliście": "widziałyście",
    "słyszeliście": "słyszałyście",
    "chcieliście": "chciałyście",
    "wiedzieliście": "wiedziałyście",
    "myśleliście": "myślałyście",
    "powiedzieliście": "powiedziałyście",
    "zrozumieliście": "zrozumiałyście",
    "zapomnieliście": "zapomniałyście",
    "musieliście": "musiałyście",
    "mieliście": "miałyście",
    "wzięliście": "wzięłyście",
    "zaczęliście": "zaczęłyście",
}

NONVIRILE_PLURAL_IRREGULAR_TO_VIRILE: Dict[str, str] = {
    "znalazłyście": "znaleźliście",
    "poszłyście": "poszliście",
    "przyszłyście": "przyszliście",
    "wyszłyście": "wyszliście",
    "odeszłyście": "odeszliście",
    "weszłyście": "weszliście",
    "przeszłyście": "przeszliście",
    "doszłyście": "doszliście",
    "zeszłyście": "zeszliście",
    "mogłyście": "mogliście",
    "pomogłyście": "pomogliście",
    "byłyście": "byliście",
    "widziałyście": "widzieliście",
    "słyszałyście": "słyszeliście",
    "chciałyście": "chcieliście",
    "wiedziałyście": "wiedzieliście",
    "myślałyście": "myśleliście",
    "powiedziałyście": "powiedzieliście",
    "zrozumiałyście": "zrozumieliście",
    "zapomniałyście": "zapomnieliście",
    "musiałyście": "musieliście",
    "miałyście": "mieliście",
    "wzięłyście": "wzięliście",
    "zaczęłyście": "zaczęliście",
}

VIRILE_ADJECTIVES_TO_NONVIRILE: Dict[str, str] = {
    "gotowi": "gotowe",
    "pewni": "pewne",
    "sami": "same",
    "bezpieczni": "bezpieczne",
    "zmęczeni": "zmęczone",
    "ciekawi": "ciekawe",
    "zadowoleni": "zadowolone",
    "zaskoczeni": "zaskoczone",
    "zdziwieni": "zdziwione",
    "gotowiście": "gotoweście",
}

NONVIRILE_ADJECTIVES_TO_VIRILE: Dict[str, str] = {
    "gotowe": "gotowi",
    "pewne": "pewni",
    "same": "sami",
    "bezpieczne": "bezpieczni",
    "zmęczone": "zmęczeni",
    "ciekawe": "ciekawi",
    "zadowolone": "zadowoleni",
    "zaskoczone": "zaskoczeni",
    "zdziwione": "zdziwieni",
    "gotoweście": "gotowiście",
}

def convert_virile_plural_to_nonvirile(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in VIRILE_PLURAL_IRREGULAR_TO_NONVIRILE:
        res = VIRILE_PLURAL_IRREGULAR_TO_NONVIRILE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("agliście"):
        res = v_lower[:-8] + "agłyście"
    elif v_lower.endswith("egliście"):
        res = v_lower[:-8] + "egłyście"
    elif v_lower.endswith("ogliście"):
        res = v_lower[:-8] + "ogłyście"
    elif v_lower.endswith("szliście"):
        res = v_lower[:-8] + "szłyście"
    elif v_lower.endswith("ieliście"):
        res = v_lower[:-8] + "iałyście"
    elif v_lower.endswith("aliście"):
        res = v_lower[:-7] + "ałyście"
    elif v_lower.endswith("iliście"):
        res = v_lower[:-7] + "iłyście"
    elif v_lower.endswith("yliście"):
        res = v_lower[:-7] + "yłyście"
    elif v_lower.endswith("ęliście"):
        res = v_lower[:-7] + "ęłyście"
    elif v_lower.endswith("liście"):
        res = v_lower[:-6] + "łyście"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

def convert_nonvirile_plural_to_virile(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in NONVIRILE_PLURAL_IRREGULAR_TO_VIRILE:
        res = NONVIRILE_PLURAL_IRREGULAR_TO_VIRILE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("agłyście"):
        res = v_lower[:-8] + "agliście"
    elif v_lower.endswith("egłyście"):
        res = v_lower[:-8] + "egliście"
    elif v_lower.endswith("ogłyście"):
        res = v_lower[:-8] + "ogliście"
    elif v_lower.endswith("szłyście"):
        res = v_lower[:-8] + "szliście"
    elif v_lower.endswith("iałyście"):
        res = v_lower[:-8] + "ieliście"
    elif v_lower.endswith("ałyście"):
        res = v_lower[:-7] + "aliście"
    elif v_lower.endswith("iłyście"):
        res = v_lower[:-7] + "iliście"
    elif v_lower.endswith("yłyście"):
        res = v_lower[:-7] + "yliście"
    elif v_lower.endswith("ęłyście"):
        res = v_lower[:-7] + "ęliście"
    elif v_lower.endswith("łyście"):
        res = v_lower[:-6] + "liście"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

class EpisodeQualityGate:
    """
    Global Post-Translation Quality Gate & Human-Eye Common Sense Auditor.
    Executes a comprehensive, chronological pass across the entire subtitle file
    (eliminating batch boundary blindspots) right before saving to disk.
    Guarantees zero-cost (0.00 PLN) elimination of trivial human-visible errors.
    """

    @classmethod
    def audit_and_fix_entire_episode(
        cls,
        subs: Any,  # pysubs2.SSAFile
        custom_glossary: Optional[Dict[str, str]] = None,
        user_feedback_rules: Optional[List[Dict[str, Any]]] = None,
        character_registry: Optional[Dict[str, str]] = None,
        series_bible: Optional[Any] = None,
        line_addressees: Optional[Dict[int, str]] = None
    ) -> Tuple[Any, List[str]]:
        if not subs or not hasattr(subs, "events") or not subs.events:
            return subs, []

        fixes: List[str] = []
        events = subs.events

        # Step 0: Episode-Wide Character Gender Knowledge Base (Filar CLXII)
        CANONICAL_MALE_NAMES_ON_A = {
            "shira", "akira", "gaara", "ashitaka", "kiba", "soma", "kenta",
            "ryoma", "hanza", "koba", "soya", "toma", "genga", "sinbad", "judar", "alibaba"
        }
        char_gender_map: Dict[str, str] = {}  # char_name_lower -> "MALE" or "FEMALE"

        FEMALE_ROLE_KEYWORDS = [
            "female", "kobieta", "dziewczyn", "żeńsk", "nauczycielk", "czarodziejk",
            "szpieżk", "wojowniczk", "kapłank", "służąc", "pani", "bohaterk",
            "arystokratk", "władczyn", "królow", "księżniczk", "matk", "córk", "siostr"
        ]

        # 0a. From Character Registry
        if character_registry:
            for cname, cdesc in character_registry.items():
                cd_lower = str(cdesc).lower()
                gen = None
                if any(k in cd_lower for k in FEMALE_ROLE_KEYWORDS):
                    gen = "FEMALE"
                elif any(k in cd_lower for k in ["male", "mężczyzna", "chłopak", "męsk"]):
                    gen = "MALE"
                if gen:
                    for p in re.split(r"[/,]", cname):
                        clean_p = p.strip()
                        if len(clean_p) >= 3:
                            char_gender_map[clean_p.lower()] = gen

        # 0b. From Series Bible
        if series_bible and hasattr(series_bible, "data"):
            bible_chars = series_bible.data.get("characters", {})
            for c_key, c_val in bible_chars.items():
                desc_str = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
                desc_lower = desc_str.lower()
                gen = None
                if any(k in desc_lower for k in FEMALE_ROLE_KEYWORDS):
                    gen = "FEMALE"
                elif any(k in desc_lower for k in ["male", "mężczyzna", "chłopak", "męsk"]):
                    gen = "MALE"
                if gen:
                    for n in re.findall(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}\b", c_key):
                        if n.lower() not in char_gender_map:
                            char_gender_map[n.lower()] = gen

        # 0c. Canonical Male Names on '-a'
        for m_name in CANONICAL_MALE_NAMES_ON_A:
            if m_name not in char_gender_map:
                char_gender_map[m_name] = "MALE"

        # 0d. Empirical self-reference extraction across entire episode script
        speaker_male_votes: Dict[str, int] = {}
        speaker_female_votes: Dict[str, int] = {}

        for ev in events:
            if not ev.text or not getattr(ev, "name", None):
                continue
            spk_norm = ev.name.strip().lower()
            if not spk_norm or len(spk_norm) < 3:
                continue
            clean_t = re.sub(r"\{[^\}]*\}", "", ev.text).lower()

            if re.search(r"\b(powinienem|mógłbym|chciałbym|wolałbym|poszedłem|zrobiłem|byłem|widziałem|wiedziałem|pomyślałem|mówiłem|czekałem|wróciłem|znalazłem|przyszedłem|odszedłem|wyszedłem|wszedłem|zrozumiałem|myślałem|słyszałem|czułem|obiecałem|postanowiłem)\b", clean_t):
                speaker_male_votes[spk_norm] = speaker_male_votes.get(spk_norm, 0) + 1

            if re.search(r"\b(powinnam|mogłabym|chciałabym|wolałabym|poszłam|zrobiłam|byłam|widziałam|wiedziałam|pomyślałam|mówiłam|czekałam|wróciłam|znalazłam|przyszłam|odeszłam|wyszłam|weszłam|zrozumiałam|myślałam|słyszałam|czułam|obiecałam|postanowiłam)\b", clean_t):
                speaker_female_votes[spk_norm] = speaker_female_votes.get(spk_norm, 0) + 1

        for spk, m_count in speaker_male_votes.items():
            f_count = speaker_female_votes.get(spk, 0)
            if m_count > f_count and spk not in char_gender_map:
                char_gender_map[spk] = "MALE"
        for spk, f_count in speaker_female_votes.items():
            m_count = speaker_male_votes.get(spk, 0)
            if f_count > m_count and spk not in char_gender_map:
                char_gender_map[spk] = "FEMALE"

        # 0e. Pre-pass for Foreign Name Declension & Vocative Uniformity
        prep_name_counts: Dict[str, Dict[str, int]] = {}
        voc_name_counts: Dict[str, Dict[str, int]] = {}

        candidate_names = set(char_gender_map.keys())
        if character_registry:
            for k in character_registry.keys():
                for p in re.split(r"[/,]", k):
                    clean_p = p.strip().lower()
                    if len(clean_p) >= 3:
                        candidate_names.add(clean_p)

        # 0f. 7-Case Character Declension Matrix from Series Bible / Registry
        character_declensions: Dict[str, Dict[str, str]] = {}
        if series_bible and hasattr(series_bible, "data") and "declensions" in series_bible.data:
            character_declensions = dict(series_bible.data["declensions"])
        elif character_registry:
            from series_memory import generate_polish_name_declension
            for k in character_registry.keys():
                for p in re.split(r"[/,]", k):
                    clean_p = p.strip()
                    if len(clean_p) >= 3:
                        g = char_gender_map.get(clean_p.lower(), "UNKNOWN")
                        character_declensions[clean_p] = generate_polish_name_declension(clean_p, g)

        for ev in events:
            if not ev.text:
                continue
            clean_t = re.sub(r"\{[^\}]*\}", "", ev.text)

            # Preposition + Capitalized Word
            for m in re.finditer(r"\b(z|ze|do|dla|o|u|od|przed|nad|pod|przy|przez|za)\s+([^\s,\.!\?…]+)", clean_t):
                n_form = m.group(2)
                for c_name in candidate_names:
                    stem_len = max(3, len(c_name) - 2)
                    stem = c_name[:stem_len]
                    if n_form.lower().startswith(stem):
                        if c_name not in prep_name_counts:
                            prep_name_counts[c_name] = {}
                        prep_name_counts[c_name][n_form] = prep_name_counts[c_name].get(n_form, 0) + 1
                        break

            # Vocative address: Name followed by ! or ,
            for m in re.finditer(r"(?:^|[,\.!\?…]\s*|\bHej,\s*|\bEj,\s*)([^\s,\.!\?…]{2,})([!,\?])", clean_t):
                voc_word = m.group(1)
                if voc_word.lower() in ["dobrze", "jasne", "proszę", "przepraszam", "uważaj", "czekaj", "stój", "witaj", "chwila", "powiedz", "widzisz", "chodź"]:
                    continue
                for c_name in candidate_names:
                    stem_len = max(3, len(c_name) - 2)
                    stem = c_name[:stem_len]
                    if voc_word.lower().startswith(stem):
                        if c_name not in voc_name_counts:
                            voc_name_counts[c_name] = {}
                        voc_name_counts[c_name][voc_word] = voc_name_counts[c_name].get(voc_word, 0) + 1
                        break

        dominant_prep_names: Dict[str, str] = {}
        for c_name, forms in prep_name_counts.items():
            total = sum(forms.values())
            if total >= 2:
                dom_form, dom_count = max(forms.items(), key=lambda x: x[1])
                if dom_count / total >= 0.75:
                    dominant_prep_names[c_name] = dom_form

        dominant_voc_names: Dict[str, str] = {}
        for c_name, forms in voc_name_counts.items():
            total = sum(forms.values())
            if total >= 2:
                dom_voc, dom_count = max(forms.items(), key=lambda x: x[1])
                if dom_count / total >= 0.75:
                    dominant_voc_names[c_name] = dom_voc

        for i, ev in enumerate(events):
            if not ev.text or not ev.text.strip():
                continue

            text_before = ev.text

            # Identify if current event is a sign/title (e.g. style has "Sign", "Title", or contains \pos / \an8)
            ev_style_lower = (ev.style or "").lower()
            ev_is_sub = bool(re.search(r"\bsubtitles?\b", ev_style_lower))
            is_sign = bool(
                re.search(r"\\(pos|move|an[789]|clip)\b", ev.text) or
                (not ev_is_sub and (
                    bool(re.search(r"\b(sign|signs|title|titles|caption|captions|typeset|typesetting|op|ed)\b", ev_style_lower))
                    or ev_style_lower.startswith("caption")
                ))
            )

            # Find preceding dialogue event (skip signs and empty events)
            prev_ev = None
            prev_clean = ""
            for j in range(i - 1, -1, -1):
                cand = events[j]
                cand_text = re.sub(r"\{[^\}]*\}", "", cand.text or "").strip()
                cand_style_lower = (cand.style or "").lower()
                cand_is_sub = bool(re.search(r"\bsubtitles?\b", cand_style_lower))
                cand_is_sign = bool(
                    re.search(r"\\(pos|move|an[789]|clip)\b", cand.text or "") or
                    (not cand_is_sub and (
                        bool(re.search(r"\b(sign|signs|title|titles|caption|captions|typeset|typesetting|op|ed)\b", cand_style_lower))
                        or cand_style_lower.startswith("caption")
                    ))
                )
                if cand_text and not cand_is_sign:
                    prev_ev = cand
                    prev_clean = cand_text
                    break

            # 1. ADJACENCY PAIR AUDIT: Directive / Warning / Wh-Question -> Affirmation Guard (Filar XLIII / CXLVI)
            if not is_sign and prev_clean and prev_ev:
                time_gap_ms = ev.start - prev_ev.end
                if time_gap_ms < 9000:
                    is_prev_directive = bool(re.search(
                        r"\b(uważaj|uważajcie|ostrożnie|czekaj|poczekaj|zaczekaj|stój|stójcie|pospiesz|pospieszcie|chodź|chodźcie|nie ruszaj|trzymaj się|uważaj pod nogi|ruszaj|kryj się|padnij)\b",
                        prev_clean,
                        re.IGNORECASE
                    ))
                    is_prev_wh_question = bool(prev_clean.endswith("?") and re.search(
                        r"\b(dokąd|gdzie|kiedy|dlaczego|czemu|kto|kogo|komu|kim|co|czego|czym|jak|jaki|jaka|jakie|jakim|jakich|o\s+co|o\s+czym|z\s+kim|w\s+jaki\s+sposób)\b",
                        prev_clean,
                        re.IGNORECASE
                    ))
                    is_prev_neg_q = bool(prev_clean.endswith("?") and (
                        re.search(r"\bnie\s+(jest|jesteś|jesteście|są|był|była|było|byli|byłeś|byłaś|będzie|będziesz|będą|ma|masz|macie|chcesz|chce|chcecie|wiesz|wie|wiecie|możesz|może|możecie|idziesz|idzie|idziecie|zrobisz|mówisz|widzisz|słyszysz)\b", prev_clean, re.IGNORECASE) or
                        any(prev_clean.startswith(w) for w in ["don't", "aren't", "didn't", "can't", "won't", "haven't", "isn't"])
                    ))
                    if is_prev_directive:
                        # Match lone affirmative like "Tak.", "T-Tak.", "Tak!", "T-Tak..."
                        m_aff = re.match(r"^(\s*\{[^\}]*\})*([Tt]-[Tt]ak|[Tt]ak)([\.!\?…]*)(\{[^\}]*\}\s*)*$", ev.text.strip())
                        if m_aff:
                            word = m_aff.group(2)
                            punct = m_aff.group(3) or "."
                            repl_word = "D-Dobrze" if word.lower().startswith("t-") else ("Dobrze" if word[0].isupper() else "dobrze")
                            ev.text = re.sub(rf"\b{re.escape(word)}", repl_word, ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Dyrektywne Potwierdzenie] Linia #{i+1}: zastąpiono '{word}{punct}' przez '{repl_word}{punct}' w reakcji na '{prev_clean[:25]}...'")
                    elif is_prev_wh_question:
                        # Open questions cannot be answered with lone "Yes/Tak" (hesitation mistranslation)
                        m_aff = re.match(r"^(\s*\{[^\}]*\})*([Tt]-[Tt]ak|[Tt]ak)([\.!\?…]*)(\{[^\}]*\}\s*)*$", ev.text.strip())
                        if m_aff:
                            word = m_aff.group(2)
                            punct = m_aff.group(3) or "..."
                            if not punct.endswith("..."):
                                punct = "..."
                            repl_word = "E-Eee" if word.lower().startswith("t-") else "Eee"
                            ev.text = re.sub(rf"\b{re.escape(word)}[\.!\?…]*", f"{repl_word}{punct}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Reakcja na Pytanie Otwarte] Linia #{i+1}: zastąpiono nielogiczne '{word}' przez '{repl_word}{punct}' w reakcji na pytanie otwarte '{prev_clean[:25]}...'")
                    elif is_prev_neg_q:
                        # Negative questions answered affirmatively in JP (Hai/Un) must be negative in PL (Nie / N-Nie)
                        m_aff = re.match(r"^(\s*\{[^\}]*\})*([Tt]-[Tt]ak|[Tt]ak)([\.!\?…]*)(\{[^\}]*\}\s*)*$", ev.text.strip())
                        if m_aff:
                            word = m_aff.group(2)
                            punct = m_aff.group(3) or "."
                            repl_word = "N-Nie" if word.lower().startswith("t-") else ("Nie" if word[0].isupper() else "nie")
                            ev.text = re.sub(rf"\b{re.escape(word)}", repl_word, ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Echo Agreement] Linia #{i+1}: zastąpiono '{word}{punct}' przez '{repl_word}{punct}' w reakcji na pytanie z przeczeniem '{prev_clean[:25]}...'")

            # 2. THOUGHT-TO-SPEECH BOUNDARY: Strip unsolicited thought italics on plain dialogue lines
            if not is_sign and prev_ev:
                prev_is_thought = "italic" in (prev_ev.style or "").lower() or r"\i1" in (prev_ev.text or "")
                curr_style_thought = "italic" in (ev.style or "").lower()
                # If previous event was a thought, and current style is regular dialogue, strip artificial {\i1}...{\i0}
                if prev_is_thought and not curr_style_thought:
                    if r"\i1" in ev.text and r"\i0" in ev.text:
                        ev.text = re.sub(r"\{\\i[01]\}", "", ev.text).strip()
                        fixes.append(f"[Episode Quality Gate - Bariera Myśli] Linia #{i+1}: usunięto sztuczną kursywę {{\\i1}} po przejściu z myśli do mowy diegetycznej")

            # 3. FOCALIZATION & DRAMATIC IRONY (Filar CLXI): Guard against 1st person drift for 3rd person titles
            if not is_sign:
                if re.search(r"\bmój\s+(esej|artykuł|traktat)\b", ev.text, re.IGNORECASE):
                    def _qg_witch_essay_repl(m):
                        noun = m.group(1)
                        res = f"{noun} Wiedźmy Milczenia"
                        return res.capitalize() if m.group(0)[0].isupper() else res
                    ev.text = re.sub(r"\bmój\s+(esej|artykuł|traktat)\b", _qg_witch_essay_repl, ev.text, flags=re.IGNORECASE)
                    fixes.append(f"[Episode Quality Gate - Filar CLXI] Linia #{i+1}: przywrócono 3. osobę 'esej Wiedźmy Milczenia' zamiast 'mój esej'")
                elif re.search(r"\bmoj(?:a|ej|ą)\s+prac(?:a|y|ę)\b", ev.text, re.IGNORECASE) and any(w in (prev_clean or "").lower() for w in ["wiedźm", "esej", "artykuł", "traktat"]):
                    ev.text = re.sub(r"\bmoj(?:a|ej|ą)\s+prac(?:a|y|ę)\b", "praca Wiedźmy Milczenia", ev.text, flags=re.IGNORECASE)
                    fixes.append(f"[Episode Quality Gate - Filar CLXI] Linia #{i+1}: skorygowano zdradę tożsamości 'moja praca' -> 'praca Wiedźmy Milczenia'")

            # 3b. INTER-LINE T-V INVARIANCE (Filar CLVII): First name in dialogue vs unexpected 'pan/pani'
            if not is_sign and prev_clean and prev_ev:
                time_gap_ms = ev.start - prev_ev.end
                if time_gap_ms < 6000:
                    first_name_in_prev = bool(re.search(
                        r"(?<!\bpanie\s)(?<!\bpani\s)(?<!\bpanno\s)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})[,?!]",
                        prev_clean
                    ))
                    if first_name_in_prev:
                        drift_matches = [
                            (r"\bwygrał\s+pan\b", "wygrałeś"),
                            (r"\bwygrała\s+pani\b", "wygrałaś"),
                            (r"\bwidział\s+pan\b", "widziałeś"),
                            (r"\bwidziała\s+pani\b", "widziałaś"),
                            (r"\bzrobił\s+pan\b", "zrobiłeś"),
                            (r"\bzrobiła\s+pani\b", "zrobiłaś"),
                            (r"\bpan\s+wie\b", "wiesz"),
                            (r"\bpani\s+wie\b", "wiesz"),
                            (r"\bpan\s+myśli\b", "myślisz"),
                            (r"\bpani\s+myśli\b", "myślisz"),
                            (r"\bniech\s+pan\s+spojrzy\b", "spójrz"),
                            (r"\bniech\s+pani\s+spojrzy\b", "spójrz")
                        ]
                        for dr_pat, dr_rep in drift_matches:
                            if re.search(dr_pat, ev.text, re.IGNORECASE):
                                ev.text = re.sub(dr_pat, dr_rep, ev.text, flags=re.IGNORECASE)
                                fixes.append(f"[Episode Quality Gate - Filar CLVII T-V Invariance] Linia #{i+1}: skorygowano nieuzasadniony zwrot formalny na 2. os. '{dr_rep}' po zwróceniu się po imieniu")

            # 3b-2. INTRA-LINE T-V INVARIANCE (Filar CLVII): Eliminate hybrid "ty" + "pan/pani" in the same line
            if not is_sign:
                has_informal_ty = bool(re.search(
                    r"\b(?:przecież\s+)?(?:wiesz|widzisz|myślisz|pamiętasz|rozumiesz|mówisz|robisz|chcesz|możesz|masz|musisz|znasz|słyszysz|jesteś)\b|"
                    r"\b[a-ząćęłńóśźż]+(?:łeś|łaś)\b",
                    ev.text,
                    re.IGNORECASE
                ))
                has_formal_title = bool(re.search(r"\b(?:panie|pani)\s+(?:profesor|doktor|prezes|kapitan|major)\b", ev.text, re.IGNORECASE))
                if has_informal_ty and not has_formal_title:
                    # Check if addressee is known female
                    addressee_is_female = False
                    if prev_ev and getattr(prev_ev, "name", None):
                        prev_spk_gen = char_gender_map.get(prev_ev.name.strip().lower())
                        if prev_spk_gen == "FEMALE":
                            addressee_is_female = True

                    intra_tv_fixes = [
                        (r"\ba\s+jakoś\s+mnie\s+pan\s+nie\s+wydał\b", "a jakoś mnie nie wydałaś" if addressee_is_female else "a jakoś mnie nie wydałeś"),
                        (r"\ba\s+jakoś\s+mnie\s+pani\s+nie\s+wydała\b", "a jakoś mnie nie wydałaś"),
                        (r"\bmnie\s+pan\s+nie\s+wydał\b", "mnie nie wydałaś" if addressee_is_female else "mnie nie wydałeś"),
                        (r"\bmnie\s+pani\s+nie\s+wydała\b", "mnie nie wydałaś"),
                        (r"\bstoi\s+pan\b", "stoisz"),
                        (r"\bstoi\s+pani\b", "stoisz"),
                        (r"\bpan\s+stoi\b", "stoisz"),
                        (r"\bpani\s+stoi\b", "stoisz"),
                        (r"\bprzysłał\s+tu\s+pana\b", "przysłał cię tu"),
                        (r"\bprzysłał\s+tu\s+panią\b", "przysłał cię tu"),
                        (r"\boferuję\s+panu\s+pomoc\b", "oferuję ci pomoc"),
                        (r"\boferuję\s+pani\s+pomoc\b", "oferuję ci pomoc"),
                        (r"\balbo\s+pan\b", "albo ty"),
                        (r"\balbo\s+pani\b", "albo ty"),
                        (r"\bdowiesz\s+się\s+pierwszy\b", "dowiesz się pierwsza" if addressee_is_female else "dowiesz się pierwszy")
                    ]
                    for tv_pat, tv_rep in intra_tv_fixes:
                        if re.search(tv_pat, ev.text, re.IGNORECASE):
                            ev.text = re.sub(tv_pat, tv_rep, ev.text, flags=re.IGNORECASE)
                            fixes.append(f"[Episode Quality Gate - Intra-Line T-V Invariance] Linia #{i+1}: zlikwidowano hybrydę 'ty' + zwrot formalny: '{tv_pat}' -> '{tv_rep}'")

            # 3c. CHARACTER GENDER CONSISTENCY GUARD (Filar CLXII)
            if not is_sign:
                # 3c-1: 1st-person self-reference consistency for the speaker
                if getattr(ev, "name", None):
                    spk_name_lower = ev.name.strip().lower()
                    spk_gen = char_gender_map.get(spk_name_lower)
                    if spk_gen == "MALE":
                        for f_pat, m_repl in FIRST_PERSON_FEMININE_TO_MASCULINE:
                            if re.search(f_pat, ev.text, re.IGNORECASE):
                                def _m_case_repl(m, repl=m_repl):
                                    return repl.capitalize() if m.group(0)[0].isupper() else repl
                                ev.text = re.sub(f_pat, _m_case_repl, ev.text, flags=re.IGNORECASE)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano 1. os. na rodzaj męski dla mówcy '{ev.name}'")
                    elif spk_gen == "FEMALE":
                        for m_pat, f_repl in FIRST_PERSON_MASCULINE_TO_FEMININE:
                            if re.search(m_pat, ev.text, re.IGNORECASE):
                                def _f_case_repl(m, repl=f_repl):
                                    return repl.capitalize() if m.group(0)[0].isupper() else repl
                                ev.text = re.sub(m_pat, _f_case_repl, ev.text, flags=re.IGNORECASE)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano 1. os. na rodzaj żeński dla mówczyni '{ev.name}'")

                # 3c-2: 3rd-person subject-verb past-tense agreement
                for char_lower, gender in char_gender_map.items():
                    if len(char_lower) < 3:
                        continue
                    # Match name (normal order): [Name] [optional adverb] [verb]
                    # Matches across \N (hard line break) as well as regular whitespace
                    sp_regex = r"(?:\s+|\\N)+"
                    pat_forward = rf"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)" + sp_regex + rf"(?:(już|też|wtedy|wczoraj|zawsze|nigdy|właśnie|przecież|tylko|jedynie|naprawdę)" + sp_regex + rf")?([A-Za-ząćęłńóśźż]+)\b"
                    for m in list(re.finditer(pat_forward, ev.text)):
                        matched_name = m.group(1)
                        if matched_name.lower() != char_lower:
                            continue
                        verb = m.group(3)
                        if gender == "MALE":
                            new_v = convert_feminine_past_to_masculine(verb)
                            if new_v and new_v.lower() != verb.lower():
                                old_chunk = m.group(0)
                                new_chunk = old_chunk.replace(verb, new_v, 1)
                                ev.text = ev.text.replace(old_chunk, new_chunk, 1)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano orzeczenie 3. osoby '{matched_name} {verb}' -> '{matched_name} {new_v}' (potwierdzona płeć męska)")
                        elif gender == "FEMALE":
                            new_v = convert_masculine_past_to_feminine(verb)
                            if new_v and new_v.lower() != verb.lower():
                                old_chunk = m.group(0)
                                new_chunk = old_chunk.replace(verb, new_v, 1)
                                ev.text = ev.text.replace(old_chunk, new_chunk, 1)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano orzeczenie 3. osoby '{matched_name} {verb}' -> '{matched_name} {new_v}' (potwierdzona płeć żeńska)")

                    # Match name (inverted order): [verb] [optional pronoun] [Name]
                    pat_inverted = rf"\b([A-Za-ząćęłńóśźż]+)" + sp_regex + rf"(?:(mnie|nas|go|ją|ich|mu|jej|im|cię|wam)" + sp_regex + rf")?([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b"
                    for m in list(re.finditer(pat_inverted, ev.text)):
                        matched_name = m.group(3)
                        if matched_name.lower() != char_lower:
                            continue
                        verb = m.group(1)
                        if gender == "MALE":
                            new_v = convert_feminine_past_to_masculine(verb)
                            if new_v and new_v.lower() != verb.lower():
                                old_chunk = m.group(0)
                                new_chunk = old_chunk.replace(verb, new_v, 1)
                                ev.text = ev.text.replace(old_chunk, new_chunk, 1)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano orzeczenie szyku przestawnego '{verb} {matched_name}' -> '{new_v} {matched_name}' (potwierdzona płeć męska)")
                        elif gender == "FEMALE":
                            new_v = convert_masculine_past_to_feminine(verb)
                            if new_v and new_v.lower() != verb.lower():
                                old_chunk = m.group(0)
                                new_chunk = old_chunk.replace(verb, new_v, 1)
                                ev.text = ev.text.replace(old_chunk, new_chunk, 1)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano orzeczenie szyku przestawnego '{verb} {matched_name}' -> '{new_v} {matched_name}' (potwierdzona płeć żeńska)")

            # 3c-3. 2ND-PERSON PLURAL ADDRESSEE GROUP AGREEMENT (Filar CLXIII - 0.00 PLN)
            if not is_sign:
                raw_ev_addressee = getattr(ev, "addressee", None) or (line_addressees.get(i) if line_addressees else None)
                addr_norm = (raw_ev_addressee or "").strip().lower()

                clean_ev_text = re.sub(r"\{[^\}]*\}", "", ev.text)
                has_female_vocative = bool(re.search(r"\b(dziewczęta|dziewczyny|panie|kobiety|siostry|uczennice|kapłanki)[!,\?]", clean_ev_text, re.IGNORECASE))
                has_male_vocative = bool(re.search(r"\b(chłopaki|panowie|mężczyźni|żołnierze|bracia|chłopcy)[!,\?]", clean_ev_text, re.IGNORECASE))

                is_female_group = ("grupa_kobiet" in addr_norm) or has_female_vocative
                is_male_group = ("grupa_mężczyzn" in addr_norm) or has_male_vocative
                is_mixed_group = ("grupa_mieszana" in addr_norm)

                if is_female_group:
                    # 1. Convert virile 2nd-person plural verbs (-liście) -> non-virile (-łyście)
                    for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+liście)\b", ev.text)):
                        v_virile = m.group(1)
                        v_nonvirile = convert_virile_plural_to_nonvirile(v_virile)
                        if v_nonvirile and v_nonvirile.lower() != v_virile.lower():
                            ev.text = re.sub(rf"\b{re.escape(v_virile)}\b", v_nonvirile, ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXIII Morfologia Niemęskoosobowa] Linia #{i+1}: skorygowano formę męskoosobową '{v_virile}' -> '{v_nonvirile}' (adresat: grupa kobiet)")

                    # 2. Convert virile adjectives / participles (gotowi, pewni, sami, etc.) -> non-virile (gotowe, pewne, same)
                    for v_adj, nv_adj in VIRILE_ADJECTIVES_TO_NONVIRILE.items():
                        pat_adj = rf"\b((?:byłyście|byliście|jesteście|bądźcie|zostałyście|zostaliście|zostańcie|będziecie|czujecie\s+się)\s+)({re.escape(v_adj)})\b"
                        for m in list(re.finditer(pat_adj, ev.text, re.IGNORECASE)):
                            prefix = m.group(1)
                            old_adj = m.group(2)
                            repl_adj = nv_adj.capitalize() if old_adj[0].isupper() else nv_adj
                            ev.text = re.sub(rf"\b{re.escape(prefix)}{re.escape(old_adj)}\b", f"{prefix}{repl_adj}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXIII Przymiotnik Niemęskoosobowy] Linia #{i+1}: skorygowano '{prefix}{old_adj}' -> '{prefix}{repl_adj}' (adresat: grupa kobiet)")

                elif is_male_group or is_mixed_group:
                    # Convert non-virile 2nd-person plural verbs (-łyście) -> virile (-liście)
                    for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+łyście)\b", ev.text)):
                        v_nonvirile = m.group(1)
                        v_virile = convert_nonvirile_plural_to_virile(v_nonvirile)
                        if v_virile and v_virile.lower() != v_nonvirile.lower():
                            ev.text = re.sub(rf"\b{re.escape(v_nonvirile)}\b", v_virile, ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXIII Morfologia Męskoosobowa] Linia #{i+1}: skorygowano formę niemęskoosobową '{v_nonvirile}' -> '{v_virile}' (adresat: {'grupa mężczyzn' if is_male_group else 'grupa mieszana'})")

                    # Convert non-virile adjectives -> virile
                    for nv_adj, v_adj in NONVIRILE_ADJECTIVES_TO_VIRILE.items():
                        pat_adj = rf"\b((?:byliście|byłyście|jesteście|bądźcie|zostaliście|zostałyście|zostańcie|będziecie|czujecie\s+się)\s+)({re.escape(nv_adj)})\b"
                        for m in list(re.finditer(pat_adj, ev.text, re.IGNORECASE)):
                            prefix = m.group(1)
                            old_adj = m.group(2)
                            repl_adj = v_adj.capitalize() if old_adj[0].isupper() else v_adj
                            ev.text = re.sub(rf"\b{re.escape(prefix)}{re.escape(old_adj)}\b", f"{prefix}{repl_adj}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXIII Przymiotnik Męskoosobowy] Linia #{i+1}: skorygowano '{prefix}{old_adj}' -> '{prefix}{repl_adj}' (adresat: {'grupa mężczyzn' if is_male_group else 'grupa mieszana'})")

            # 3d. FOREIGN NAME DECLENSION UNIFORMITY (Prepositional Cases)
            if not is_sign and dominant_prep_names:
                for c_name, dom_form in dominant_prep_names.items():
                    stem_len = max(3, len(c_name) - 2)
                    stem = c_name[:stem_len]
                    def _prep_decl_repl(m, target=dom_form):
                        prep = m.group(1)
                        matched_form = m.group(2)
                        if matched_form != target:
                            return f"{prep} {target}"
                        return m.group(0)
                    pat = rf"\b(z|ze|do|dla|o|u|od|przed|nad|pod|przy|przez|za)\s+({re.escape(stem)}[^\s,\.!\?…]*)\b"
                    old_text = ev.text
                    ev.text = re.sub(pat, _prep_decl_repl, ev.text, flags=re.IGNORECASE)
                    if ev.text != old_text:
                        fixes.append(f"[Episode Quality Gate - Jednolita Deklinacja Imion] Linia #{i+1}: ujednolicono formę imienia po przyimku na '{dom_form}' (dominująca konwencja w odcinku)")

            # 3d2. DETERMINISTIC 7-CASE DECLENSION MATRIX ENFORCEMENT (from Series Bible / Registry)
            if not is_sign and character_declensions:
                for c_name, c_decl in character_declensions.items():
                    if not c_name or len(c_name) < 3:
                        continue
                    m_form = c_decl.get("M", c_name)

                    # Narzędnik (z, ze, przed, nad, pod, za) -> c_decl["N"]
                    n_form = c_decl.get("N")
                    if n_form and n_form != m_form:
                        pat_n = rf"\b(z|ze|przed|nad|pod|za)\s+({re.escape(m_form)})\b"
                        def _repl_n(m, target=n_form):
                            return f"{m.group(1)} {target}"
                        old_t = ev.text
                        ev.text = re.sub(pat_n, _repl_n, ev.text, flags=re.IGNORECASE)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Matryca Narzędnika] Linia #{i+1}: ujednolicono formę na '{n_form}' po przyimku narzędnika")

                    # Dopełniacz (do, dla, od, u, bez) -> c_decl["D"]
                    d_form = c_decl.get("D")
                    if d_form and d_form != m_form:
                        pat_d = rf"\b(do|dla|od|u|bez)\s+({re.escape(m_form)})\b"
                        def _repl_d(m, target=d_form):
                            return f"{m.group(1)} {target}"
                        old_t = ev.text
                        ev.text = re.sub(pat_d, _repl_d, ev.text, flags=re.IGNORECASE)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Matryca Dopełniacza] Linia #{i+1}: ujednolicono formę na '{d_form}' po przyimku dopełniacza")

                    # Miejscownik (o, przy) -> c_decl["Ms"]
                    ms_form = c_decl.get("Ms")
                    if ms_form and ms_form != m_form:
                        pat_ms = rf"\b(o|przy)\s+({re.escape(m_form)})\b"
                        def _repl_ms(m, target=ms_form):
                            return f"{m.group(1)} {target}"
                        old_t = ev.text
                        ev.text = re.sub(pat_ms, _repl_ms, ev.text, flags=re.IGNORECASE)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Matryca Miejscownika] Linia #{i+1}: ujednolicono formę na '{ms_form}' po przyimku miejscownika")

            # 3e. VOCATIVE UNIFORMITY
            if not is_sign and dominant_voc_names:
                for c_name, dom_voc in dominant_voc_names.items():
                    stem_len = max(3, len(c_name) - 2)
                    stem = c_name[:stem_len]
                    def _voc_repl(m, target=dom_voc):
                        prefix = m.group(1) or ""
                        matched_voc = m.group(2)
                        punct = m.group(3) or "!"
                        if matched_voc != target and matched_voc.lower() not in ["dobrze", "jasne", "proszę", "przepraszam"]:
                            return f"{prefix}{target}{punct}"
                        return m.group(0)
                    pat = rf"(^|[,\.!\?…]\s*|\bHej,\s*|\bEj,\s*)({re.escape(stem)}[^\s,\.!\?…]*)([!,\?])"
                    old_text = ev.text
                    ev.text = re.sub(pat, _voc_repl, ev.text, flags=re.IGNORECASE)
                    if ev.text != old_text:
                        fixes.append(f"[Episode Quality Gate - Jednolitość Wołacza] Linia #{i+1}: ujednolicono formę wołacza na '{dom_voc}' (dominująca konwencja w odcinku)")

            # 3f. MICRO-LINE LENGTH CLAMPING (< 0.5s / 500ms)
            line_dur_ms = ev.end - ev.start
            if not is_sign and 0 < line_dur_ms <= 500:
                clean_t = re.sub(r"\{[^\}]*\}", "", ev.text).strip()
                if len(clean_t) > 14 or len(clean_t.split()) > 3:
                    cl_lower = clean_t.lower()
                    if any(w in cl_lower for w in ["nie wierzę", "niemożliwe", "nie mogę", "jak to", "co ty", "naprawdę", "serio", "co takiego"]):
                        repl = "Niemożliwe!" if any(w in cl_lower for w in ["nie wierzę", "niemożliwe", "nie mogę"]) else "Co?!"
                    elif any(w in cl_lower for w in ["uważaj", "stój", "ratunku", "pomocy", "uciekaj", "z drogi", "padnij"]):
                        repl = "Uważaj!" if "uważaj" in cl_lower else ("Stój!" if "stój" in cl_lower else "Ratunku!")
                    elif any(w in cl_lower for w in ["ech", "uch", "och", "ach", "litości", "niech to", "daj spokój", "rany", "zaraz"]):
                        repl = "Ech..." if any(w in cl_lower for w in ["ech", "uch", "och", "ach"]) else "Niech to..."
                    elif clean_t.endswith("?"):
                        repl = "Co?!"
                    elif clean_t.endswith("!"):
                        words = clean_t.split()
                        repl = f"{words[0]}!" if len(words[0]) <= 12 else words[0][:10] + "!"
                    else:
                        words = clean_t.split()
                        repl = f"{words[0]}..." if len(words[0]) <= 12 else words[0][:10] + "..."

                    # Preserve leading typesetting tags
                    m_prefix = re.match(r"^(\{[^\}]*\})+", ev.text)
                    prefix = m_prefix.group(0) if m_prefix else ""
                    ev.text = f"{prefix}{repl}"
                    fixes.append(f"[Episode Quality Gate - Kompresja Mikro-Kwestii <0.5s] Linia #{i+1}: skondensowano zbyt długą kwestię ({line_dur_ms}ms, {len(clean_t)} zn.) '{clean_t}' -> '{repl}'")

            # 4. RESIDUAL ENGLISH CALQUE SWEEP (Belczyk AVT Canon)
            for item in AVTLinter.FIXED_REPLACEMENTS:
                pattern = item[0]
                repl = item[1]
                pillar_tag = item[2] if len(item) > 2 else "Belczyk AVT"
                if re.search(pattern, ev.text):
                    ev.text = re.sub(pattern, repl, ev.text)
                    repl_disp = repl if isinstance(repl, str) else "[korekta fleksyjna]"
                    fixes.append(f"[Episode Quality Gate - {pillar_tag}] Linia #{i+1}: {pattern} -> {repl_disp}")

            # 4b. USER FEEDBACK GOLDEN RULES (Deterministic Overrides)
            if user_feedback_rules:
                for fb in user_feedback_rules:
                    bad = fb.get("bad_pl")
                    good = fb.get("good_pl")
                    if not bad or not good or bad.strip() == good.strip():
                        continue
                    if any(kw in good.lower() for kw in ["kanon", "avt", "filar", "prompt", "few-shot", "zakaz", ">"]):
                        continue
                    if bad.strip() and bad in ev.text:
                        ev.text = ev.text.replace(bad, good)
                        fixes.append(f"[Episode Quality Gate - Złota Reguła Użytkownika] Linia #{i+1}: '{bad}' -> '{good}'")

            # 5. PUNCTUATION & TYPOGRAPHY HYGIENE
            # Clean accidental double dots (e.g. "To prawda..") -> "To prawda..."
            ev.text = re.sub(r"(?<!\.)\.\.(?!\.)", "...", ev.text)
            # Remove space before comma/period/exclamation/question mark
            ev.text = re.sub(r"\s+([,\.!\?…])", r"\1", ev.text)
            # Normalize whitespace around ASS line breaks
            ev.text = re.sub(r"\s*\\N\s*", r"\\N", ev.text)
            # Remove misplaced question mark on pure affirmative statements like "Rozumiem?" -> "Rozumiem."
            if not is_sign and re.match(r"^(\s*\{[^\}]*\})*(?:Rozumiem|Jasne|D-Dobrze|Dobrze|W porządku|Oczywiście)\?+(\{[^\}]*\}\s*)*$", ev.text.strip()):
                ev.text = re.sub(r"\?+", ".", ev.text)
                fixes.append(f"[Episode Quality Gate - Higiena Pytajnika] Linia #{i+1}: usunięto pytajnik z potwierdzenia twierdzącego")
            # 6. ENGLISH REMAINDER SWEEP (Zero Untranslated English Lines Guarantee)
            if not is_sign:
                clean_no_tags = re.sub(r"\{[^\}]*\}", "", ev.text).strip()
                words = [w.lower() for w in re.findall(r"\b[a-zA-Z]+\b", clean_no_tags)]
                common_en_stop = {"the", "and", "you", "that", "this", "with", "have", "from", "what", "there", "they", "would", "about", "could", "should", "their", "will", "were", "been"}
                en_hits = [w for w in words if w in common_en_stop]
                if len(words) >= 4 and len(en_hits) >= 2 and not any(c in clean_no_tags for c in "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"):
                    fixes.append(f"[Episode Quality Gate - Wykryto nieprzetłumaczony angielski] Linia #{i+1}: '{clean_no_tags[:35]}...'")

            # 7. STRICT AVT 2-LINE CEILING FOR DIALOGUE (Filar LVII / Netflix AVT: Maks. 2 wiersze)
            if not is_sign and r"\N" in ev.text:
                parts = [p for p in ev.text.split(r"\N") if p.strip()]
                if len(parts) > 2:
                    from avt_formatter import split_subtitle_syntactically
                    old_lines_cnt = len(parts)
                    ev.text = split_subtitle_syntactically(ev.text, max_line_len=42, is_ass=True, is_sign=False)
                    fixes.append(f"[Episode Quality Gate - Filar LVII (Maks. 2 Wiersze)] Linia #{i+1}: zredukowano {old_lines_cnt} wiersze do standardowych 2 wierszy AVT")

            # 8. META-LEAK FIREWALL & PURGE (Absolute zero tolerance for meta-language in subtitles)
            meta_leak_pat = r"(?i)\b(zgodnie\s+z\s+polskim\s+kanonem\s+avt|kanon(?:em)?\s*avt|kanon\s+avt|filar\s+[ivxlcdm0-9]+|few-shot|system\s*prompt|prompt\s*leak)\b"
            if re.search(meta_leak_pat, ev.text):
                ev.text = re.sub(meta_leak_pat, "", ev.text)
                ev.text = re.sub(r"[ \t]+", " ", ev.text)
                ev.text = re.sub(r"\\N\s+", r"\\N", ev.text)
                ev.text = re.sub(r"\s+\\N", r"\\N", ev.text).strip()
                fixes.append(f"[Episode Quality Gate - ALARM: Wykryto i usunięto wyciek meta-języka AVT] Linia #{i+1}: wyczyszczono frazę meta-kanoniczną")

            # Record if text changed due to hygiene
            if ev.text != text_before and not any(f"Linia #{i+1}:" in f for f in fixes):
                fixes.append(f"[Episode Quality Gate - Higiena Tekstu] Linia #{i+1}: oczyszczono interpunkcję i formatowanie")

        return subs, fixes
