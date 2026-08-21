# -*- coding: utf-8 -*-
"""
Moduł AVT Linter (Automatyczny Strażnik i Audytor Polszczyzny Filmowej).
Oparty na wytycznych Arkadiusza Belczyka, Agnieszki Szarkowskiej i Netflix Polish Style Guide.
Działa jako ostatnia, niezależna tarcza jakościowa sprawdzająca przetłumaczone kwestie pod kątem
rażących kalek, sztucznych pytań, niewłaściwych form gramatycznych i pozostałości mechanicznego przekładu.
"""

import re
from typing import Dict, List, Tuple, Optional

class AVTLinter:
    """
    Automatyczny walidator i korektor mechanicznych kalek językowych w napisach filmowych.
    """
    
    # Słownik automatycznych natychmiastowych podmian kalek z przypisaniem do Filarów AVT
    FIXED_REPLACEMENTS = [
        # Amerykanizmy i kalki leksykalne (Filar IV / XXXVI)
        (r"\b[Ww]itaj z powrotem\b", "Witaj!", "Filar IV/XXXVI - Eliminacja Kalek Amerykańskich"),
        (r"\b[Mm]am taką nadzieję\b", "Mam nadzieję", "Filar IV - Czystość Idiomatyczna"),
        (r"\b[Tt]o robi sens\b", "To ma sens", "Filar IV - Eliminacja Kalek"),
        (r"\b[Nn]ie robi sensu\b", "To nie ma sensu", "Filar IV - Eliminacja Kalek"),
        (r"\b[Jj]esteś w porządku\?", "Wszystko w porządku?", "Filar IV - Szablony Angielskie"),
        (r"\b[Bb]yłem w stanie to znaleźć\b", "Udało mi się to znaleźć", "Filar IV - Konstrukcje Obce"),
        (r"\b[Bb]yłam w stanie to znaleźć\b", "Udało mi się to znaleźć", "Filar IV - Konstrukcje Obce"),
        (r"\b[Ww]ygląda jakby miało padać\b", "Chyba będzie padać", "Filar XXXII - Modalność Epistemiczna"),
        (r"\b[Mm]am uczucie że\b", "Coś mi mówi, że", "Filar IV - Naturalność Mówiona"),
        (r"\b[Ww]ydaje się być\b", "Wydaje się", "Filar IV - Konstrukcje Obce"),
        (r"\b[Dd]aj mi rękę\b", "Pomóż mi", "Filar IV - Idiomatyka"),
        (r"\b[Pp]oniosło klapę\b", "Nie wyszło", "Filar IV - Idiomatyka"),
        (r"\b[Ww]asz [Hh]onor\b", "Wysoki Sądzie", "Filar XVI - Realia Sądownicze"),
        
        # Relacje rodzinne i tytulatura feudalna (Filar II / XXXIV / XLI)
        (r"\bTo pan, [Mm]łody [Pp]anie\b", "To ty, młody panie", "Filar II/XXXIV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\bto pan, [Mm]łody [Pp]anie\b", "to ty, młody panie", "Filar II/XXXIV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\bTo pan, młody panie\b", "To ty, młody panie", "Filar II/XXXIV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\bto pan, młody panie\b", "to ty, młody panie", "Filar II/XXXIV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\bTo pani, [Mm]łoda [Pp]ani\b", "To ty, młoda pani", "Filar II/XXXIV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\bto pani, [Mm]łoda [Pp]ani\b", "to ty, młoda pani", "Filar II/XXXIV - Eliminacja Tautologii Honoryfikatywnej"),
        (r"\b[Mm]łody [Pp]anie\b", "młody panie", "Filar XLI - Ortografia Wołacza i Małe Litery"),
        (r"\b[Mm]łoda [Pp]ani\b", "młoda pani", "Filar XLI - Ortografia Wołacza i Małe Litery"),
        (r"\b[Ww]asza [Ww]ysokość\b", "wasza wysokość", "Filar XLI - Ortografia Wołacza i Małe Litery"),
        (r"\b[Ss]tarszy bracie\b", "brachu", "Filar XXXIV - Relacje Rodzinne"),
        (r"\b[Ss]tarsza siostro\b", "siostra", "Filar XXXIV - Relacje Rodzinne"),
        (r"\b[Pp]ani [Ss]ensei\b", "Sensei", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]anie [Ss]ensei\b", "Sensei", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]an [Ss]ensei\b", "Sensei", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]ani [Ss]enpai\b", "Senpai", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]anie [Ss]enpai\b", "Senpai", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]an [Ss]enpai\b", "Senpai", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych"),
        
        # Poprawność medyczna i rekcja przyczyn zgonu (Filar XIV)
        (r"\b[Zz]marła na wylew\b", "zmarła z powodu wylewu", "Filar XIV - Poprawność Medyczna"),
        (r"\b[Zz]marł na wylew\b", "zmarł z powodu wylewu", "Filar XIV - Poprawność Medyczna"),
        (r"\b[Uu]marła na wylew\b", "zmarła z powodu wylewu", "Filar XIV - Poprawność Medyczna"),
        (r"\b[Uu]marł na wylew\b", "zmarł z powodu wylewu", "Filar XIV - Poprawność Medyczna"),
        (r"\b[Zz]marła na krwotok\b", "zmarła wskutek krwotoku", "Filar XIV - Poprawność Medyczna"),
        (r"\b[Zz]marł na krwotok\b", "zmarł wskutek krwotoku", "Filar XIV - Poprawność Medyczna"),
        (r"\b[Zz]marła na atak serca\b", "zmarła na zawał", "Filar XIV - Poprawność Medyczna"),
        (r"\b[Zz]marł na atak serca\b", "zmarł na zawał", "Filar XIV - Poprawność Medyczna"),
        
        # Eliminacja zbędnego "Ja " na początku zdania (Filar I / Belczyk)
        (r"^Ja myślę, że\b", "Myślę, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja wiem, że\b", "Wiem, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja uważam, że\b", "Uważam, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja sądzę, że\b", "Sądzę, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja widzę, że\b", "Widzę, że", "Filar I - Eliminacja Zaimka Ja"),
        
        # Eliminacja sztucznego "Czy" na początku krótkich pytań potocznych (Filar X)
        (r"^[Cc]zy jesteś pewna\?", "Jesteś pewna?", "Filar X - Pytania bez 'Czy'"),
        (r"^[Cc]zy jesteś pewien\?", "Jesteś pewien?", "Filar X - Pytania bez 'Czy'"),
        (r"^[Cc]zy wszystko w porządku\?", "Wszystko w porządku?", "Filar X - Pytania bez 'Czy'"),
        (r"^[Cc]zy to prawda\?", "To prawda?", "Filar X - Pytania bez 'Czy'"),
        (r"^[Cc]zy oszalałaś\?", "Oszalałaś?", "Filar X - Pytania bez 'Czy'"),
        (r"^[Cc]zy zgłupiałaś\?", "Zgłupiałaś?", "Filar X - Pytania bez 'Czy'"),
        (r"^[Cc]zy pójdziesz ze mną\?", "Pójdziesz ze mną?", "Filar X - Pytania bez 'Czy'"),
        (r"^[Cc]zy możemy już iść\?", "Możemy już iść?", "Filar X - Pytania bez 'Czy'"),
        (r"^[Cc]zy widziałaś to\?", "Widziałaś to?", "Filar X - Pytania bez 'Czy'"),
        (r"^[Cc]zy słyszałaś to\?", "Słyszałaś to?", "Filar X - Pytania bez 'Czy'"),
    ]

    @classmethod
    def lint_and_fix_line(
        cls,
        text: str,
        speaker_gender: Optional[str] = None,
        is_all_girls_scene: bool = True,
        is_sign: bool = False
    ) -> Tuple[str, List[str]]:
        """
        Analizuje i automatycznie poprawia kwestię dialogową.
        Zwraca: (poprawiony_tekst, lista_zastosowanych_korekt)
        """
        if not text:
            return "", []

        modified = text
        applied_fixes = []

        # 1. Automatyczne podmiany leksykalne i frazeologiczne
        for item in cls.FIXED_REPLACEMENTS:
            pattern = item[0]
            repl = item[1]
            pillar_tag = item[2] if len(item) > 2 else "Filar IV - Reguły Belczyka"
            if re.search(pattern, modified):
                modified = re.sub(pattern, repl, modified)
                applied_fixes.append(f"[{pillar_tag}] {pattern} -> {repl}")

        # 2. Korekta płci gramatycznej dla scen dziewczęcych (Filar XIII)
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

        # 3. Zabezpieczenie przed podwójnymi spacjami lub uciętymi znakami
        modified = re.sub(r"[ \t]+", " ", modified).strip()

        return modified, applied_fixes
