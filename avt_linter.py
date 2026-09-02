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
        
        # Environmental Media & Non-Aqueous Liquids (Filar CXXXVIII)
        (r"\bPowódź\s+piwa\b", "Fala piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fala piwa)"),
        (r"\bpowódź\s+piwa\b", "fala piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fala piwa)"),
        (r"\bPowodzi\s+piwa\b", "Fali piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fali piwa)"),
        (r"\bpowodzi\s+piwa\b", "fali piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fali piwa)"),
        (r"\bPowódź\s+wina\b", "Fala wina", "Filar CXXXVIII - Kolokacja Cieczy (Fala wina)"),
        (r"\bpowódź\s+wina\b", "fala wina", "Filar CXXXVIII - Kolokacja Cieczy (Fala wina)"),
        (r"\bPowodzi\s+wina\b", "Fali wina", "Filar CXXXVIII - Kolokacja Cieczy (Fali wina)"),
        (r"\bpowodzi\s+wina\b", "fali wina", "Filar CXXXVIII - Kolokacja Cieczy (Fali wina)"),
        
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
        custom_glossary: Optional[Dict[str, str]] = None
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
                applied_fixes.append(f"[{pillar_tag}] {pattern} -> {repl}")

        # 2. Dynamic user feedback rules
        if user_feedback_rules:
            for fb in user_feedback_rules:
                bad_pl = fb.get("bad_pl", "").strip()
                good_pl = fb.get("good_pl", "").strip()
                if not bad_pl or not good_pl or bad_pl == good_pl:
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
