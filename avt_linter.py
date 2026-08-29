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
        (r"!\?", "?!", "Filar LX - Zespolone Znaki Interpunkcyjne"),
        (r"!\?\?", "?!", "Filar LX - Zespolone Znaki Interpunkcyjne"),
        (r"\?\?\?", "?", "Filar LX - Zespolone Znaki Interpunkcyjne"),

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

        # 3. Strict glossary overrides
        if custom_glossary:
            for src, trg in custom_glossary.items():
                if not src or not trg or src.lower() == trg.lower():
                    continue
                pat_src = rf"\b{re.escape(src)}\b"
                if re.search(pat_src, modified, re.IGNORECASE):
                    modified = re.sub(pat_src, trg, modified, flags=re.IGNORECASE)
                    applied_fixes.append(f"[Słownik Deterministyczny] '{src}' -> '{trg}'")

        # 4. Grammatical gender alignment for all-female scenes (Pillar XIII)
        if is_all_girls_scene and not is_sign:
            gender_fixes = [
                (r"\b[Gg]łupi jesteś\?", "Głupia jesteś?"),
                (r"\b[Jj]esteś pewien\?", "Jesteś pewna?"),
                (r"\b[Oo]szalałeś\?", "Oszalałaś?"),
                (r"\b[Zz]głupiałeś\?", "Zgłupiałaś?"),
                (r"\b[Ww]idziałeś to\?", "Widziałaś to?"),
                (r"\b[Ss]łyszałeś to\?", "Słyszałaś to?"),
                (r"\b[Zz]robiłeś to\?", "Zrobiłaś to?"),
                (r"\b[Pp]oszedłeś tam\?", "Poszłaś tam?"),
                (r"\b[Mm]yślałeś, że\b", "Myślałaś, że"),
            ]
            for pattern, repl in gender_fixes:
                if re.search(pattern, modified):
                    modified = re.sub(pattern, repl, modified)
                    applied_fixes.append(f"[Filar XIII - Płeć Żeńska w Obsadzie] {pattern} -> {repl}")

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

        # 6. Guard against duplicate spaces
        modified = re.sub(r"[ \t]+", " ", modified).strip()

        return modified, applied_fixes
