# -*- coding: utf-8 -*-
"""
Moduł AVT Linter (Automatyczny Strażnik i Audytor Polszczyzny Filmowej).
Oparty na wytycznych Arkadiusza Belczyka, Agnieszki Szarkowskiej, Netflix Polish Style Guide
oraz dynamicznej bazie reguł i poprawek użytkownika (User Feedback & Glossary).
Działa jako ostatnia, niezależna tarcza jakościowa sprawdzająca przetłumaczone kwestie pod kątem
rażących kalek, sztucznych pytań, niewłaściwych form gramatycznych i pozostałości mechanicznego przekładu.
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

class AVTLinter:
    """
    Automatyczny walidator i korektor mechanicznych kalek językowych w napisach filmowych.
    """
    
    # Słownik automatycznych natychmiastowych podmian kalek z przypisaniem do Filarów AVT
    # Zawiera elastyczne wzorce fleksyjne i wieloczasowe
    FIXED_REPLACEMENTS = [
        # Amerykanizmy i kalki leksykalne (Filar IV / XXXVI)
        (r"\b[Ww]itaj z powrotem\b", "Witaj!", "Filar IV/XXXVI - Eliminacja Kalek Amerykańskich"),
        
        # Odmiany "mieć taką nadzieję" -> "mieć nadzieję"
        (r"\b([Mm]am|[Mm]iałem|[Mm]iałam|[Mm]ieliśmy|[Mm]iałyśmy|[Bb]ędę mieć|[Bb]ędziemy mieć)\s+taką\s+nadzieję\b", r"\1 nadzieję", "Filar IV - Czystość Idiomatyczna"),
        (r"\b[Mm]am nadzieję na to\b", "Mam nadzieję", "Filar IV - Czystość Idiomatyczna"),

        # Odmiany "robić sens" -> "mieć sens"
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
        
        # Nominalizacje (Filar I)
        (r"\b[Oo]dbyć rozmowę\b", "porozmawiać", "Filar I - Odnominalizowanie"),
        (r"\bodbyłem rozmowę\b", "porozmawiałem", "Filar I - Odnominalizowanie"),
        (r"\bodbyłam rozmowę\b", "porozmawiałam", "Filar I - Odnominalizowanie"),
        (r"\b[Zz]robić sprzątanie\b", "posprzątać", "Filar I - Odnominalizowanie"),
        (r"\b[Zz]robił sprzątanie\b", "posprzątał", "Filar I - Odnominalizowanie"),
        (r"\b[Zz]robiła sprzątanie\b", "posprzątała", "Filar I - Odnominalizowanie"),
        (r"\b[Dd]ać odpowiedź\b", "odpowiedzieć", "Filar I - Odnominalizowanie"),
        (r"\b[Zz]robić pojawienie się\b", "zjawić się", "Filar I - Odnominalizowanie"),

        # Pleonazmy i masło maślane (Belczyk)
        (r"\b[Cc]ofnąć się do tyłu\b", "cofnąć się", "Filar IV - Pleonazmy"),
        (r"\b[Oo]kres czasu\b", "okres", "Filar IV - Pleonazmy"),
        (r"\bw tym momencie czasu\b", "w tej chwili", "Filar IV - Pleonazmy"),

        # Relacje rodzinne i tytulatura feudalna (Filar XXV / LX)
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
        
        # Hybrydy honoryfikatywne (Filar XXVII)
        (r"\b[Pp]ani [Ss]ensei\b", "Sensei", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]anie [Ss]ensei\b", "Sensei", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]an [Ss]ensei\b", "Sensei", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]ani [Ss]enpai\b", "Senpai", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]anie [Ss]enpai\b", "Senpai", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        (r"\b[Pp]an [Ss]enpai\b", "Senpai", "Filar XXVII - Zakaz Hybryd Honoryfikatywnych"),
        
        # Poprawność medyczna i rekcja przyczyn zgonu (Filar L)
        (r"\b[Zz]marła na wylew\b", "zmarła z powodu wylewu", "Filar L - Poprawność Medyczna"),
        (r"\b[Zz]marł na wylew\b", "zmarł z powodu wylewu", "Filar L - Poprawność Medyczna"),
        (r"\b[Uu]marła na wylew\b", "zmarła z powodu wylewu", "Filar L - Poprawność Medyczna"),
        (r"\b[Uu]marł na wylew\b", "zmarł z powodu wylewu", "Filar L - Poprawność Medyczna"),
        (r"\b[Zz]marła na krwotok\b", "zmarła wskutek krwotoku", "Filar L - Poprawność Medyczna"),
        (r"\b[Zz]marł na krwotok\b", "zmarł wskutek krwotoku", "Filar L - Poprawność Medyczna"),
        (r"\b[Zz]marła na atak serca\b", "zmarła na zawał", "Filar L - Poprawność Medyczna"),
        (r"\b[Zz]marł na atak serca\b", "zmarł na zawał", "Filar L - Poprawność Medyczna"),
        
        # Eliminacja zbędnego "Ja " na początku zdania (Filar I / Belczyk)
        (r"^Ja myślę, że\b", "Myślę, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja wiem, że\b", "Wiem, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja uważam, że\b", "Uważam, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja sądzę, że\b", "Sądzę, że", "Filar I - Eliminacja Zaimka Ja"),
        (r"^Ja widzę, że\b", "Widzę, że", "Filar I - Eliminacja Zaimka Ja"),
        
        # Eliminacja sztucznego "Czy" na początku krótkich pytań potocznych (Filar IX)
        (r"^[Cc]zy jesteś pewna\?", "Jesteś pewna?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy jesteś pewien\?", "Jesteś pewien?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy wszystko w porządku\?", "Wszystko w porządku?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy to prawda\?", "To prawda?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy oszalałaś\?", "Oszalałaś?", "Filar IX - Pytania bez 'Czy'"),
        (r"^[Cc]zy oszalałeś\?", "Oszalałeś?", "Filar IX - Pytania bez 'Czy'"),

        # Paralingwistyka i odgłosy foniczne (Filar XVIII)
        (r"\b[Aa]ra\s+ara\b", "O proszę...", "Filar XVIII - Paralingwistyka"),
        (r"\b[Tt]ch\b", "Tsk...", "Filar XVIII - Paralingwistyka"),
        (r"\b[Gg]uh\b", "Uch...", "Filar XVIII - Paralingwistyka"),

        # Trzeci język i kalki translacyjne (Filar X)
        (r"\b[Cc]o sprawia, że tak mówisz\?", "Czemu tak sądzisz?", "Filar X - Anti-Translationese"),
        (r"\b[Jj]estem zrobiony z\b", "Taki już jestem", "Filar X - Anti-Translationese"),
        (r"\b[Ww]zięcie pod uwagę\b", "Biorąc pod uwagę", "Filar X - Anti-Translationese"),

        # Interpunkcja audiowizualna (Filar LX)
        (r"!\?", "?!", "Filar LX - Zespolone Znaki Interpunkcyjne"),
        (r"!\?\?", "?!", "Filar LX - Zespolone Znaki Interpunkcyjne"),
        (r"\?\?\?", "?", "Filar LX - Zespolone Znaki Interpunkcyjne"),

        # Realia kulturowe i Pedersen ECR (Filar XIV)
        (r"\b[Kk]onbini\b", "sklep", "Filar XIV - Pedersen Generalization"),

        # Metryzacja miar i jednostek (Filar LIX)
        (r"\b100\s+stóp\b", "30 metrów", "Filar LIX - Metryzacja Miar"),
        (r"\b10\s+stóp\b", "3 metry", "Filar LIX - Metryzacja Miar"),
        (r"\b6\s+stóp\b", "prawie dwa metry", "Filar LIX - Metryzacja Miar"),

        # Modalność epistemiczna i naturalne wykładniki (Filar XLVI)
        (r"\b[Nn]ie ma wątpliwości, że\b", "bez wątpienia", "Filar XLVI - Modalność Epistemiczna"),
        (r"\b[Jj]est możliwe, że\b", "być może", "Filar XLVI - Modalność Epistemiczna"),

        # Japońskie idiomy somatyczne i pułapki gramatyczne (Filar XV / VI / IX)
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

        # Pragmatyka Shūjoshi (Filar XVI)
        (r"\bIku zo!?\b", "No to ruszamy!", "Filar XVI - Shūjoshi Pragmatics"),

        # Taksonomia Onomatopei (Filar XVII)
        (r"\b[Zz]okutto shita\b", "przeszły mnie ciarki", "Filar XVII - Onomatopoeia Gijougo"),
        (r"\b[Kk]yun to shita\b", "ścisnęło mnie za serce", "Filar XVII - Onomatopoeia Gijougo"),
        (r"\b[Ss]hiin to shita\b", "zapadła cisza jak makiem zasiał", "Filar XVII - Onomatopoeia Gitaigo"),
        (r"\b[Nn]oro-noro\b", "ślimaczym tempem", "Filar XVII - Onomatopoeia Giyougo"),

        # Żargon RPG i Isekai (Filar XXIV)
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
        Analizuje i automatycznie poprawia kwestię dialogową.
        Uwzględnia reguły kanoniczne, fleksję oraz dynamiczne reguły użytkownika.
        Zwraca: (poprawiony_tekst, lista_zastosowanych_korekt)
        """
        if not text:
            return "", []

        modified = text
        applied_fixes = []

        # 1. Automatyczne podmiany leksykalne i frazeologiczne (Kanon AVT)
        for item in cls.FIXED_REPLACEMENTS:
            pattern = item[0]
            repl = item[1]
            pillar_tag = item[2] if len(item) > 2 else "Filar IV - Reguły Belczyka"
            if re.search(pattern, modified):
                modified = re.sub(pattern, repl, modified)
                applied_fixes.append(f"[{pillar_tag}] {pattern} -> {repl}")

        # 2. Dynamiczne reguły zgłoszone przez użytkownika (User Feedback)
        if user_feedback_rules:
            for fb in user_feedback_rules:
                bad_pl = fb.get("bad_pl", "").strip()
                good_pl = fb.get("good_pl", "").strip()
                if not bad_pl or not good_pl or bad_pl == good_pl:
                    continue
                # Sprawdzamy czy podano wielowariantowy zapis (z ukośnikiem)
                bad_variants = [v.strip() for v in bad_pl.split("/") if v.strip()]
                good_choice = good_pl.split("/")[0].strip()

                for variant in bad_variants:
                    pat = rf"\b{re.escape(variant)}\b"
                    if re.search(pat, modified, re.IGNORECASE):
                        modified = re.sub(pat, good_choice, modified, flags=re.IGNORECASE)
                        applied_fixes.append(f"[Korekta Użytkownika] '{variant}' -> '{good_choice}'")

        # 3. Twarde wymuszenia ze słownika (Glossary Overrides)
        if custom_glossary:
            for src, trg in custom_glossary.items():
                if not src or not trg or src.lower() == trg.lower():
                    continue
                pat_src = rf"\b{re.escape(src)}\b"
                if re.search(pat_src, modified, re.IGNORECASE):
                    modified = re.sub(pat_src, trg, modified, flags=re.IGNORECASE)
                    applied_fixes.append(f"[Słownik Deterministyczny] '{src}' -> '{trg}'")

        # 4. Korekta płci gramatycznej dla scen dziewczęcych (Filar XIII)
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

        # 5. Zabezpieczenie przed podwójnymi spacjami lub uciętymi znakami
        modified = re.sub(r"[ \t]+", " ", modified).strip()

        return modified, applied_fixes
