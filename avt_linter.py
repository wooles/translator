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
    
    # Słownik automatycznych natychmiastowych podmian kalek
    FIXED_REPLACEMENTS = [
        # Amerykanizmy i kalki leksykalne
        (r"\b[Ww]itaj z powrotem\b", "Witaj!"),
        (r"\b[Mm]am taką nadzieję\b", "Mam nadzieję"),
        (r"\b[Tt]o robi sens\b", "To ma sens"),
        (r"\b[Nn]ie robi sensu\b", "To nie ma sensu"),
        (r"\b[Jj]esteś w porządku\?", "Wszystko w porządku?"),
        (r"\b[Bb]yłem w stanie to znaleźć\b", "Udało mi się to znaleźć"),
        (r"\b[Bb]yłam w stanie to znaleźć\b", "Udało mi się to znaleźć"),
        (r"\b[Ww]ygląda jakby miało padać\b", "Chyba będzie padać"),
        (r"\b[Mm]am uczucie że\b", "Coś mi mówi, że"),
        (r"\b[Ww]ydaje się być\b", "Wydaje się"),
        (r"\b[Dd]aj mi rękę\b", "Pomóż mi"),
        (r"\b[Pp]oniosło klapę\b", "Nie wyszło"),
        (r"\b[Ww]asz [Hh]onor\b", "Wysoki Sądzie"),
        
        # Poprawność medyczna i rekcja przyczyn zgonu (zmarł z powodu wylewu / wskutek wylewu)
        (r"\b[Zz]marła na wylew\b", "zmarła z powodu wylewu"),
        (r"\b[Zz]marł na wylew\b", "zmarł z powodu wylewu"),
        (r"\b[Uu]marła na wylew\b", "zmarła z powodu wylewu"),
        (r"\b[Uu]marł na wylew\b", "zmarł z powodu wylewu"),
        (r"\b[Zz]marła na krwotok\b", "zmarła wskutek krwotoku"),
        (r"\b[Zz]marł na krwotok\b", "zmarł wskutek krwotoku"),
        (r"\b[Zz]marła na atak serca\b", "zmarła na zawał"),
        (r"\b[Zz]marł na atak serca\b", "zmarł na zawał"),
        
        # Eliminacja zbędnego "Ja " na początku zdania
        (r"^Ja myślę, że\b", "Myślę, że"),
        (r"^Ja wiem, że\b", "Wiem, że"),
        (r"^Ja uważam, że\b", "Uważam, że"),
        (r"^Ja sądzę, że\b", "Sądzę, że"),
        (r"^Ja widzę, że\b", "Widzę, że"),
        
        # Eliminacja sztucznego "Czy" na początku krótkich pytań potocznych (Zasada Szarkowskiej / Belczyka)
        (r"^[Cc]zy jesteś pewna\?", "Jesteś pewna?"),
        (r"^[Cc]zy jesteś pewien\?", "Jesteś pewien?"),
        (r"^[Cc]zy wszystko w porządku\?", "Wszystko w porządku?"),
        (r"^[Cc]zy to prawda\?", "To prawda?"),
        (r"^[Cc]zy oszalałaś\?", "Oszalałaś?"),
        (r"^[Cc]zy zgłupiałaś\?", "Zgłupiałaś?"),
        (r"^[Cc]zy pójdziesz ze mną\?", "Pójdziesz ze mną?"),
        (r"^[Cc]zy możemy już iść\?", "Możemy już iść?"),
        (r"^[Cc]zy widziałaś to\?", "Widziałaś to?"),
        (r"^[Cc]zy słyszałaś to\?", "Słyszałaś to?"),
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
        for pattern, repl in cls.FIXED_REPLACEMENTS:
            if re.search(pattern, modified):
                modified = re.sub(pattern, repl, modified)
                applied_fixes.append(f"Auto-korekta kalki: {pattern} -> {repl}")

        # 2. Korekta płci gramatycznej dla scen dziewczęcych (All-girls cast)
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
                    applied_fixes.append(f"Korekta żeńskoosobowości: {pattern} -> {repl}")

        # 3. Zabezpieczenie przed podwójnymi spacjami lub uciętymi znakami
        modified = re.sub(r"[ \t]+", " ", modified).strip()

        return modified, applied_fixes
