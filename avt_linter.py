# -*- coding: utf-8 -*-
"""
AVT Linter Module (Automated Polish Film Subtitle Auditor & Quality Guard).
Based on guidelines by Arkadiusz Belczyk, Agnieszka Szarkowska, Netflix Polish Style Guide,
and the dynamic user feedback & glossary rules.
Acts as a final, independent quality shield inspecting translated lines for
calques, unnatural questions, incorrect gender forms, and machine-translation artifacts.
"""

import re
from typing import Dict, List, Tuple, Optional, Any, Set, Union
from pathlib import Path
from series_memory import extract_clean_speaker_name, INHERENT_FEMALE_NOUNS, INHERENT_MALE_NOUNS, GENERIC_CATEGORY_TAGS, is_generic_actor_or_category, ETHNONYMS_AND_COLLECTIVES

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

def _fix_aura_gilotyna_match(m: Any) -> str:
    lead = m.group(1) or ""
    first_letter = m.group(2)
    ending = m.group(3).lower()
    mapping = {
        "a": "ura Gilotyna",
        "y": "ury Gilotyny",
        "ze": "urze Gilotynie",
        "ę": "urę Gilotynę",
        "ą": "urą Gilotyną",
        "o": "uro Gilotyno",
    }
    tail = mapping.get(ending, "ura Gilotyna")
    capitalized = f"A{tail}" if first_letter.isupper() else f"a{tail}"
    return f"{lead}{capitalized}"

def _fix_robic_sens_match(m: Any) -> str:
    neg = m.group(1) or ""
    verb = m.group(2)
    middle = m.group(3) or ""
    sens = m.group(4)
    v_lower = verb.lower()
    mapping = {
        "robić": "mieć",
        "robi": "ma",
        "robią": "mają",
        "robisz": "masz",
        "robię": "mam",
        "robimy": "mamy",
        "robicie": "macie",
        "robił": "miał",
        "robiła": "miała",
        "robiło": "miało",
        "robili": "mieli",
        "robiły": "miały",
        "robiłby": "miałby",
        "robiłaby": "miałaby",
        "robiłoby": "miałoby",
        "robiliby": "mieliby",
        "robiłyby": "miałyby",
    }
    miec_verb = mapping.get(v_lower, "ma")
    if verb[0].isupper():
        miec_verb = miec_verb.capitalize()
    if neg:
        sens = "sensu"
    return f"{neg}{miec_verb} {middle}{sens}"

def _fix_witaj_z_powrotem_match(m: Any) -> str:
    ending = m.group(2)
    punct = m.group(3) or ""
    forms = {
        "j": "Witaj",
        "jcie": "Witajcie",
        "m": "Witam",
        "my": "Witamy"
    }
    word = forms.get(ending, "Witaj")
    if punct == "!":
        return f"{word}!"
    elif punct in [".", ",", "..."]:
        return f"{word}{punct}"
    return f"{word}!"

def _fix_hazard_biologiczny(m: Any) -> str:
    is_cap = m.group(1).isupper()
    suffix = m.group(2)
    if suffix == "y":
        noun = "Zagrożenie" if is_cap else "zagrożenie"
        adj = "biologiczne"
    elif suffix == "ego":
        noun = "Zagrożenia" if is_cap else "zagrożenia"
        adj = "biologicznego"
    elif suffix == "emu":
        noun = "Zagrożeniu" if is_cap else "zagrożeniu"
        adj = "biologicznemu"
    elif suffix == "ym":
        noun = "Zagrożeniem" if is_cap else "zagrożeniem"
        adj = "biologicznym"
    elif suffix == "e":
        noun = "Zagrożenia" if is_cap else "zagrożenia"
        adj = "biologiczne"
    else:
        noun = "Zagrożenie" if is_cap else "zagrożenie"
        adj = "biologiczne"
    return f"{noun} {adj}"

def load_subtitle_file_resilient(subs_file: Any) -> Any:
    """
    Safely load SSA/ASS/SRT subtitle files, repairing common fansub timestamp malformations
    (e.g. missing hour digit '10:10.79' -> '0:10:10.79') and handling multi-byte encodings.
    """
    import pysubs2
    file_path = str(subs_file)
    raw_content = None
    encodings = ["utf-8", "utf-8-sig", "latin2", "cp1250"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                raw_content = f.read()
            break
        except (UnicodeDecodeError, OSError):
            continue
    if raw_content is None:
        return pysubs2.load(file_path)

    # Sanitize missing hour in ASS dialogue timestamps:
    # e.g. "Dialogue: 0,10:10.79,10:12.79," -> "Dialogue: 0,0:10:10.79,0:10:12.79,"
    sanitized = re.sub(r"(?m)(Dialogue:\s*\d+,)(\d{1,2}:\d{2}\.\d{2}),(\d{1,2}:\d{2}\.\d{2}),", r"\g<1>0:\2,0:\3,", raw_content)
    sanitized = re.sub(r"(?m)(Dialogue:\s*\d+,\d+:\d{2}:\d{2}\.\d{2},)(\d{1,2}:\d{2}\.\d{2}),", r"\g<1>0:\2,", sanitized)
    sanitized = re.sub(r"(?m)(Dialogue:\s*\d+,)(\d{1,2}:\d{2}\.\d{2}),", r"\g<1>0:\2,", sanitized)

    try:
        return pysubs2.SSAFile.from_string(sanitized)
    except Exception:
        return pysubs2.load(file_path, encoding="utf-8")

class AVTLinter:
    """
    Automated validator and corrector for mechanical language calques in subtitle tracks.
    """
    
    # Dictionary of automated instant calque replacements mapped to AVT Pillars
    # Supports flexible inflectional and tense patterns
    FIXED_REPLACEMENTS = [
        # Historical & Steppe Titulary (Filar XXV: Chan / Wielki Chan - zakaz fonetycznych kalk 'Chagan')
        (r"\b([Ww]ielki(?:m|ego|emu)?)\s+[Cc]hagan(a|em|owi|ie)?\b", lambda m: f"{m.group(1)} " + ("Chanie" if m.group(2) == "ie" else ("Chana" if m.group(2) == "a" else ("Chanem" if m.group(2) == "em" else ("Chanowi" if m.group(2) == "owi" else "Chan")))), "Filar XXV - Kanon Tytulatury Stepowej ('Wielki Chagan' -> 'Wielki Chan')"),
        (r"\b([Ww]ielki)\s+[Cc]haganie\b", r"\1 Chanie", "Filar XXV - Kanon Tytulatury Stepowej ('Wielki Chaganie' -> 'Wielki Chanie')"),
        (r"\b[Cc]haganie\b", "Chanie", "Filar XXV - Kanon Tytulatury Stepowej ('Chaganie' -> 'Chanie')"),
        (r"\b[Cc]hagan(a|em|owi)?\b", lambda m: "Chana" if m.group(1) == "a" else ("Chanem" if m.group(1) == "em" else ("Chanowi" if m.group(1) == "owi" else "Chan")), "Filar XXV - Kanon Tytulatury Stepowej ('Chagan' -> 'Chan')"),

        # Ethnonym Inflection Purism (Filar CLVII / CLXX: Eliminacja angielskich końcówek i błędów deklinacji etnonimów)
        (r"\b([Dd]la|[Oo]d|[Dd]o|[Uu]|[Zz]|[Ww]obec)\s+[Mm]ongolsa\b", r"\1 Mongołów", "Filar CLVII/CLXX - Eliminacja Angielskiej Końcówki w Odmianie Etnonimów ('dla Mongolsa' -> 'dla Mongołów')"),
        (r"\b([Dd]la|[Oo]d|[Dd]o|[Uu]|[Zz]|[Ww]obec)\s+[Mm]ongola\b(?=.*(?:lud|ród|imperium|plemię|naród|korzyść|los|sprawa))", r"\1 Mongołów", "Filar CLVII/CLXX - Eliminacja Błędnej Liczby Etnonimów ('dla Mongola' -> 'dla Mongołów')"),
        (r"\b([Mm])ongolsa\b", r"\1ongołów", "Filar CLVII/CLXX - Eliminacja Deformacji Leksykalnej 'Mongolsa' -> 'Mongołów'"),

        # Anime publishing canon & titular calques: 'Aura od Gilotyny' / 'Aura Ścięcia' -> 'Aura Gilotyna' (Filar XCVIII / Studio JG)
        (r"(^|[^\w]|\\[Nnh])([Aa])ur(a|y|ze|ę|ą|o)\s+od\s+[Gg]ilotyn(?:y|ą)?\b", _fix_aura_gilotyna_match, "Filar XCVIII - Oficjalny Kanon Mangowy (Studio JG: Aura Gilotyna)"),
        (r"(^|[^\w]|\\[Nnh])([Aa])ur(a|y|ze|ę|ą|o)\s+[Śś]cięcia\b", _fix_aura_gilotyna_match, "Filar XCVIII - Oficjalny Kanon Mangowy (Studio JG: Aura Gilotyna)"),

        # Deformed adjective comparatives / superlatives (Filar CLXIV)
        (r"(^|[^\w]|\\[Nnh])([Nn])ajdobrejsz(y|ego|emu|ym|a|ej|ą|e|ych|ymi)?\b", r"\g<1>\g<2>ajlepsz\g<3>", "Filar CLXIV - Eliminacja Zniekształcenia Leksykalnego 'najdobrejszy' -> 'najlepszy'"),
        (r"(^|[^\w]|\\[Nnh])dobrejsz(y|ego|emu|ym|a|ej|ą|e|ych|ymi)?\b", r"\g<1>lepsz\g<2>", "Filar CLXIV - Eliminacja Zniekształcenia Leksykalnego 'dobrejszy' -> 'lepszy'"),
        (r"(^|[^\w]|\\[Nnh])Dobrejsz(y|ego|emu|ym|a|ej|ą|e|ych|ymi)?\b", r"\g<1>Lepsz\g<2>", "Filar CLXIV - Eliminacja Zniekształcenia Leksykalnego 'dobrejszy' -> 'lepszy'"),

        # Americanisms and lexical calques (Pillar IV / XXXVI / CLXVI)
        (r"\b([Ww])ita(j|jcie|m|my)\s+z\s+powrotem(!|\.|\.\.\.|,)?(?=\s|$|[,\.!\?])", _fix_witaj_z_powrotem_match, "Filar IV/XXXVI/CLXVI - Eliminacja Kalek Amerykańskich ('Witaj z powrotem')"),
        (r"\b([Nn])ie\s+ma\s+mowy,?\s+(?:że|a)?by(śmy|ście|m|ś)?\b", lambda m: ("Wykluczone, by" if m.group(1).isupper() else "wykluczone, by") + (m.group(2) or ""), "Filar CLXVI - Likwidacja Kalki 'There is no way that' -> 'Wykluczone, by'"),
        
        # Inflections of "mieć taką nadzieję" -> "mieć nadzieję"
        (r"\b([Mm](?:am|asz|a|amy|acie|ają|iałem|iałam|iał|iała|iało|ieliśmy|iałyśmy|ieli|iały|iałby|iałaby|iałoby|ieliby|iałyby)|[Bb]ęd(?:ę|ziesz|zie|ziemy|ziecie|dą)\s+mieć)\s+taką\s+nadzieję\b", r"\1 nadzieję", "Filar IV/CLXVI - Czystość Idiomatyczna (Eliminacja 'mieć taką nadzieję')"),
        (r"\b([Mm](?:am|asz|a|amy|acie|ają|iałem|iałam|iał|iała|iało|ieliśmy|iałyśmy|ieli|iały|iałby|iałaby|iałoby|ieliby|iałyby)|[Bb]ęd(?:ę|ziesz|zie|ziemy|ziecie|dą)\s+mieć)\s+nadzieję\s+na\s+to\b", r"\1 nadzieję", "Filar IV/CLXVI - Czystość Idiomatyczna (Eliminacja 'mieć nadzieję na to')"),

        # Fansub Clichés & Pivot English Calques (Filar CLXVI)
        (r"(^|[^\w]|\\[Nnh])([Tt]ylko\s+)?([Ww]róć|[Ww]racaj|[Ww]róćcie|[Ww]racajcie)\s+w\s+jednym\s+kawałku\b", lambda m: f"{m.group(1)}{m.group(2) or ''}{m.group(3)} cały i zdrowy", "Filar CLXVI - Eliminacja Kalki Fansuberskiej 'w jednym kawałku' (in one piece)"),
        (r"(^|[^\w]|\\[Nnh])w\s+jednym\s+kawałku\b", r"\g<1>w całości", "Filar CLXVI - Eliminacja Kalki Fansuberskiej 'w jednym kawałku'"),
        (r"(^|[^\w]|\\[Nnh])([Zz]ginąć\s+)z\s+ręki\s+(kaiju|potwora|bestii|monstrum)\b", r"\g<1>\g<2>od ciosu \g<3>", "Filar CLXVI - Eliminacja Kalki 'die at the hands of [monster]'"),
        (r"(^|[^\w]|\\[Nnh])([Cc])zemu\s+po\s+prostu\s+jej\s+nie\s+wysłuchałem\b", lambda m: f"{m.group(1)}{'Dlaczego jej nie posłuchałem' if m.group(2).isupper() else 'dlaczego jej nie posłuchałem'}", "Filar CLXVI - Eliminacja Kalki 'Why didn't I just listen to her'"),
        (r"(^|[^\w]|\\[Nnh])([Zz])a\s+nic\s+z\s+tym\s+nie\s+zawalczę\b", lambda m: f"{m.group(1)}{'Za nic nie stanę do walki z czymś takim' if m.group(2).isupper() else 'za nic nie stanę do walki z czymś takim'}", "Filar CLXVI - Eliminacja Koślawej Składni Fansuberskiej"),
        
        # Inflections of "robić sens" -> "mieć sens"
        (r"\b([Nn]ie\s+)?([Rr]obi(?:ć|ę|sz|my|cie|ą|ł|ła|ło|li|ły|łby|łaby|łoby|liby|łyby)?)\s+((?:(?:to|jakikolwiek|żaden)\s+)*)(sens(?:u)?)\b", _fix_robic_sens_match, "Filar IV - Eliminacja Kalki 'robić sens' -> 'mieć sens'"),

        (r"\b[Jj]esteś w porządku\?", "Wszystko w porządku?", "Filar IV - Szablony Angielskie"),
        (r"\b[Bb]yłem w stanie to znaleźć\b", "Udało mi się to znaleźć", "Filar IV - Konstrukcje Obce"),
        (r"\b[Bb]yłam w stanie to znaleźć\b", "Udało mi się to znaleźć", "Filar IV - Konstrukcje Obce"),
        (r"\b[Ww]ygląda jakby miało padać\b", "Chyba będzie padać", "Filar XXXII - Modalność Epistemiczna"),
        (r"\b[Mm]am uczucie że\b", "Coś mi mówi, że", "Filar IV - Naturalność Mówiona"),
        (r"\b[Ww]ydaje się być\b", "Wydaje się", "Filar IV - Konstrukcje Obce"),
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
        
        # False Friends from Pivot English (Filar IV / CLXVI)
        (r"\b([Ee])wentualnie\s+(udało\s+się|zrobiliśmy|dotarliśmy|przegrał|wygrał|zrozumiał|poległ|zginął|zwyciężył|osiągnęliśmy|zdecydował|zgodził)\b",
         lambda m: ("Ostatecznie " if m.group(1) == "E" else "ostatecznie ") + m.group(2), "Filar IV - False Friends ('eventually' -> 'ostatecznie', nie 'ewentualnie')"),
        (r"\b([Jj])esteś\s+patetyczn(y|a|i)\b",
         lambda m: ("Jesteś żałosn" if m.group(1) == "J" else "jesteś żałosn") + m.group(2), "Filar IV - False Friends ('pathetic' -> 'żałosny', nie 'patetyczny')"),
        (r"\b([Tt])o\s+patetyczn(e|y)\b",
         lambda m: ("To żałosn" if m.group(1) == "T" else "to żałosn") + m.group(2), "Filar IV - False Friends ('pathetic' -> 'żałosne', nie 'patetyczne')"),
        (r"\b([Tt])en\s+lunatyk\b",
         lambda m: ("Ten szaleniec" if m.group(1) == "T" else "ten szaleniec"), "Filar IV - False Friends ('lunatic' -> 'szaleniec', nie 'lunatyk')"),
        (r"\b([Hh])azard\s+biologiczn(y|ego|emu|ym|e)\b",
         _fix_hazard_biologiczny, "Filar IV - False Friends ('biological hazard' -> 'zagrożenie biologiczne')"),
        (r"\bw\s+klozecie\b", "w szafie", "Filar IV - False Friends ('in the closet' -> 'w szafie')"),
        (r"\bW\s+klozecie\b", "W szafie", "Filar IV - False Friends ('in the closet' -> 'w szafie')"),

        # Pivot English Clichés & Dialogue Templates (Filar IV / CXXXVII / CLXVI)
        (r"\b([Cc])o\s+masz\s+na\s+myśli\?", lambda m: "O co ci chodzi?" if m.group(1) == "C" else "o co ci chodzi?", "Filar CXXXVII - Eliminacja Kalki 'What do you mean?'"),
        (r"\b([Cc])o\s+jest\s+nie\s+tak\?", lambda m: "Co się stało?" if m.group(1) == "C" else "co się stało?", "Filar CXXXVII - Eliminacja Kalki 'What's wrong?'"),
        (r"\b([Jj])estem\s+w\s+porządku([!\.\?]*)", lambda m: ("Nic mi nie jest" if m.group(1) == "J" else "nic mi nie jest") + m.group(2), "Filar CXXXVII - Eliminacja Kalki 'I'm fine / I'm okay'"),
        (r"\b([Bb])ądź\s+ostrożn(y|a)\b", lambda m: "Uważaj" if m.group(1) == "B" else "uważaj", "Filar CXXXVII - Eliminacja Kalki 'Be careful'"),
        (r"\b([Bb])ądźcie\s+ostrożni\b", lambda m: "Uważajcie" if m.group(1) == "B" else "uważajcie", "Filar CXXXVII - Eliminacja Kalki 'Be careful'"),
        (r"\b([Tt])o\s+nie\s+moja\s+sprawa\b", lambda m: "Nic mi do tego" if m.group(1) == "T" else "nic mi do tego", "Filar CXXXVII - Eliminacja Kalki 'None of my business'"),
        (r"\b([Nn])ie\s+zrozum\s+mnie\s+źle\b", lambda m: "Nie zrozum mnie opacznie" if m.group(1) == "N" else "nie zrozum mnie opacznie", "Filar CXXXVII - Eliminacja Kalki 'Don't get me wrong'"),
        (r"\b([Ww])\s+ten\s+czy\s+inny\s+sposób\b", lambda m: "Tak czy inaczej" if m.group(1) == "W" else "tak czy inaczej", "Filar CXXXVII - Eliminacja Kalki 'One way or another'"),
        (r"\b([Ww])szystko,?\s+co\s+musisz\s+zrobić,?\s+to\b", lambda m: "Wystarczy, że" if m.group(1) == "W" else "wystarczy, że", "Filar CXXXVII - Eliminacja Kalki 'All you have to do is'"),
        (r"\b([Nn])ie\s+masz\s+pojęcia,?\s+jak\b", lambda m: "Pojęcia nie masz, jak" if m.group(1) == "N" else "pojęcia nie masz, jak", "Filar CXXXVII - Eliminacja Kalki 'You have no idea how'"),
        (r"\b([Mm])ówię\s+poważnie\b", lambda m: "Mówię serio" if m.group(1) == "M" else "mówię serio", "Filar CXXXVII - Eliminacja Kalki 'I mean it'"),
        (r"\b([Zz])aufaj\s+mi\s+na\s+tym\b", lambda m: "Wierz mi" if m.group(1) == "Z" else "wierz mi", "Filar CXXXVII - Eliminacja Kalki 'Trust me on this'"),
        (r"\b([Oo])piekuj\s+się\s+sobą\b", lambda m: "Trzymaj się" if m.group(1) == "O" else "trzymaj się", "Filar CXXXVII - Eliminacja Kalki 'Take care'"),
        (r"\b([Mm])am\s+złe\s+uczucie\b", lambda m: "Mam złe przeczucia" if m.group(1) == "M" else "mam złe przeczucia", "Filar CXXXVII - Eliminacja Kalki 'I have a bad feeling'"),
        (r"\b([Zz])rób\s+się\s+jak\s+w\s+domu\b", lambda m: "Rozgość się" if m.group(1) == "Z" else "rozgość się", "Filar CXXXVII - Eliminacja Kalki 'Make yourself at home'"),
        
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

        # Anime & Literary Calques (Filary XXV, X, CLXIV, CXXXVII)
        (r"(?i)(\b|\\N)zapisywa[^\s]*\s+w\s+takim\s+pomys[^\s,]*", r"\1zapisywałaś w nim pomysły", "Filar IV - Kalka Składniowa 'w takim'"),
        (r"~[!]+", "!", "Filar LX - Eliminacja Japońskiej Tyldy i Wielokrotnych Wykrzykników"),
        (r"\bodchodzę\s+od\s+zmysłów\s+ze\s+szczęścia\b", "szaleję ze szczęścia", "Filar X - Związek Frazeologiczny (szaleć ze szczęścia, nie odchodzić od zmysłów)"),
        (r"\bOdchodzę\s+od\s+zmysłów\s+ze\s+szczęścia\b", "Szaleję ze szczęścia", "Filar X - Związek Frazeologiczny (szaleć ze szczęścia, nie odchodzić od zmysłów)"),
        (r"\bDwa\s+tysiące\s+w\s+zupełności\s+wystarczy\b", "Dwa tysiące w zupełności wystarczą", "Filar IV - Związek Zgody Liczebnika"),
        (r"\bdwa\s+tysiące\s+w\s+zupełności\s+wystarczy\b", "dwa tysiące w zupełności wystarczą", "Filar IV - Związek Zgody Liczebnika"),
        (r"\bnie\s+mam\s+na\s+kim\s+się(?P<sep>\s+|\\N)+mścić\b", r"nie mam na kim się\g<sep>zemścić", "Filar IV - Aspekt Czasownika 'zemścić'"),
        (r"\bzrobi\s+się\s+tylko\s+groźniej\b", "zrobi się naprawdę niebezpiecznie", "Filar IV - Kalka 'zrobi się groźniej'"),
        (r"\bMniejsza\s+z\s+tym\b", "Mniejsza o to", "Filar X - Idiomatyka"),
        (r"\bmniejsza\s+z\s+tym\b", "mniejsza o to", "Filar X - Idiomatyka"),
        (r"\bpowódź\s+piwa\b", "fala piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fala piwa)"),
        (r"\bPowodzi\s+piwa\b", "Fali piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fali piwa)"),
        (r"\bpowodzi\s+piwa\b", "fali piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fali piwa)"),
        (r"\bPowódź\s+wina\b", "Fala wina", "Filar CXXXVIII - Kolokacja Cieczy (Fala wina)"),
        (r"\bpowódź\s+wina\b", "fala wina", "Filar CXXXVIII - Kolokacja Cieczy (Fala wina)"),
        (r"\bPowodzi\s+wina\b", "Fali wina", "Filar CXXXVIII - Kolokacja Cieczy (Fali wina)"),
        (r"\bpowodzi\s+wina\b", "fali wina", "Filar CXXXVIII - Kolokacja Cieczy (Fali wina)"),

        # Universal Heroic & Dark Fantasy Lexicon / Idioms (Filar X, IV)
        (r"\bmoja(?:\s+|\\N)+droga(?:\s+|\\N)+ja\b", "moja ty mała", "Filar X - Kalka Auto-Referencyjna (My Dear Me)"),
        (r"\bMoja(?:\s+|\\N)+droga(?:\s+|\\N)+ja\b", "Moja ty mała", "Filar X - Kalka Auto-Referencyjna (My Dear Me)"),
        (r"\bw\s+cztery(?P<sep>\s+|\\N)+oczy(?:\s+|\\N)+od\s+czasu\b", r"na osobności\g<sep>od czasów", "Filar X - Zniekształcenie Frazeologiczne"),
        (r"\bzrobię(?:\s+|\\N)+raban\b", "wywołam zamieszanie", "Filar X - Rejestr Dark Fantasy (zrobić raban)"),
        (r"\bZrobię(?:\s+|\\N)+raban\b", "Wywołam zamieszanie", "Filar X - Rejestr Dark Fantasy (zrobić raban)"),
        (r"\bzbrzydło(?:\s+|\\N)+mi(?:\s+|\\N)+już(?:\s+|\\N)+szukanie\b", "znudziło mi się już szukanie", "Filar X - Rejestr Dark Fantasy"),
        (r"\bspuścił(?:\s+|\\N)+ci(?:\s+|\\N)+potworny(?:\s+|\\N)+łomot\b", "zmiażdżył cię bez trudu", "Filar X - Rejestr Dark Fantasy (spuścić łomot)"),
        (r"\bmoja(?:\s+|\\N)+sługa(?:\s+|\\N)+mogła(?:\s+|\\N)+uciec\b", "moja podwładna mogła uciec", "Filar IV - Związek Zgody Rodzaju ('moja podwładna')"),
        (r"\bwyprułam(?:\s+|\\N)+się(?:\s+|\\N)+do(?:\s+|\\N)+cna\b", "opadłam z sił", "Filar X - Rejestr Heroic Fantasy (wypruć się do cna)"),
        (r"\bWyprułam(?:\s+|\\N)+się(?:\s+|\\N)+do(?:\s+|\\N)+cna\b", "Opadłam z sił", "Filar X - Rejestr Heroic Fantasy (wypruć się do cna)"),
        (r"\bzmywam(?:\s+|\\N)+się(?:\s+|\\N)+stąd\b", "uciekam stąd", "Filar X - Rejestr Heroic Fantasy (zmywać się)"),
        (r"\bZmywam(?:\s+|\\N)+się(?:\s+|\\N)+stąd\b", "Uciekam stąd", "Filar X - Rejestr Heroic Fantasy (zmywać się)"),
        (r"\butrę(?:\s+|\\N)+nosa\b", "pokażę mu", "Filar X - Rejestr Heroic Fantasy (utrzeć nosa)"),
        (r"\bDrogowskaz,\s*kretynko\b", "To drogowskaz, głupia", "Filar X - Rejestr Stylistyczny Obelgi"),
        (r"\bI(?:\s+|\\N)+gitara\b", "Doskonale", "Filar X - Rejestr Dark Fantasy (I gitara)"),
        (r"\bi(?:\s+|\\N)+gitara\b", "doskonale", "Filar X - Rejestr Dark Fantasy (i gitara)"),
        (r"\b[Ss]tul(?:\s+|\\N)+pysk\b", lambda m: "Zamilcz" if m.group(0)[0].isupper() else "zamilcz", "Filar X - Rejestr Dark Fantasy (stul pysk)"),
        (r"\bkłamstwo(?:\s+|\\N)+jak(?:\s+|\\N)+byk\b", "bezczelne kłamstwo", "Filar X - Rejestr Dark Fantasy (kłamstwo jak byk)"),
        (r"\bKłamstwo(?:\s+|\\N)+jak(?:\s+|\\N)+byk\b", "Bezczelne kłamstwo", "Filar X - Rejestr Dark Fantasy (kłamstwo jak byk)"),
        (r"\bprzejmuję(?:\s+|\\N)+stery\b", "teraz ja mówię", "Filar X - Rejestr Dark Fantasy (przejmuję stery)"),
        (r"\bPrzejmuję(?:\s+|\\N)+stery\b", "Teraz ja mówię", "Filar X - Rejestr Dark Fantasy (przejmuję stery)"),
        (r"\bdla(?:\s+|\\N)+zabicia(?:\s+|\\N)+czasu\b", "dla rozrywki", "Filar X - Rejestr Dark Fantasy (dla zabicia czasu)"),
        (r"\bDla(?:\s+|\\N)+zabicia(?:\s+|\\N)+czasu\b", "Dla rozrywki", "Filar X - Rejestr Dark Fantasy (dla zabicia czasu)"),
        (r"\bnie(?:\s+|\\N)+władzasz\b", "nie władasz", "Filar IV - Błąd Fleksji Czasownika (władać)"),
        (r"\bprzez(?:\s+|\\N)+czarny(?:\s+|\\N)+posok\b", "przez czarną posokę", "Filar IV - Rząd i Rodzaj Rzeczownika Posoka"),
        (r"\bPrzez(?:\s+|\\N)+czarny(?:\s+|\\N)+posok\b", "Przez czarną posokę", "Filar IV - Rząd i Rodzaj Rzeczownika Posoka"),
        (r"\bz(?:\s+|\\N)+czarnego(?:\s+|\\N)+posoku\b", "z czarnej posoki", "Filar IV - Rząd i Rodzaj Rzeczownika Posoka"),
        (r"\bZ(?:\s+|\\N)+czarnego(?:\s+|\\N)+posoku\b", "Z czarnej posoki", "Filar IV - Rząd i Rodzaj Rzeczownika Posoka"),
        (r"\bczarny(?:\s+|\\N)+posok\b", "czarna posoka", "Filar IV - Rodzaj Rzeczownika Posoka"),
        (r"\bCzarny(?:\s+|\\N)+posok\b", "Czarna posoka", "Filar IV - Rodzaj Rzeczownika Posoka"),
        (r"\bDźgnięto(?:\s+|\\N)+mnie(?:\s+|\\N)+w(?:\s+|\\N)+plecy\b", "Wbito mi nóż w plecy", "Filar X - Kalka Idiomatyczna (Dźgnięto w plecy)"),
        (r"\bnie(?:\s+|\\N)+znikniecie(?:\s+|\\N)+z(?:\s+|\\N)+tym,\s*co\b", "nie uciekniecie z tym, co", "Filar X - Kalka Składniowa (zniknąć z tym)"),
        (r"\b(to\s+)?oberwę([!\?…\.]*)$", r"to poniosę karę\2", "Filar X - Rejestr Dark Fantasy (oberwę)"),
        (r"\bPani(?:\s+|\\N)+bohaterko\b", "Pani Bohaterko", "Filar CLVII - Tytulatura Bohaterki"),
        (r"\btrzecia(?:\s+|\\N)+z(?:\s+|\\N)+najlepszych\b", "trzecia pod względem siły", "Filar X - Kalka Składniowa (trzecia z najlepszych)"),
        (r"\bBez\s+jaj!?\b", "Niemożliwe!", "Filar X - Rejestr Dark Fantasy (Bez jaj)"),
        (r"\bbez\s+jaj!?\b", "niemożliwe", "Filar X - Rejestr Dark Fantasy (bez jaj)"),
        (r"\b[Gg]uzik\s+mnie\s+to\s+obchodzi\b", lambda m: "Nic mnie to nie obchodzi" if m.group(0)[0].isupper() else "nic mnie to nie obchodzi", "Filar X - Rejestr Dark Fantasy (guzik mnie to obchodzi)"),
        (r"\b([Pp]ora|[Cc]zas)\s+stąd\s+zwiewać\b", r"\1 stąd uciekać", "Filar X - Rejestr Dark Fantasy (pora stąd zwiewać)"),
        (r"\b[Mm]am\s+przez\s+(?:nie|nich)\s+uraz\b", lambda m: "Mam do nich uraz" if m.group(0)[0].isupper() else "mam do nich uraz", "Filar IV - Kalka Składniowa Rządu (uraz przez coś -> uraz do czegoś)"),
        (r"\b[Dd]urna\s+jestem\b", lambda m: "Głupia jestem" if m.group(0)[0].isupper() else "głupia jestem", "Filar X - Stylistyka Monologu (Durna jestem)"),
        (r"\bAle\s+żenada\.{2,}", "Ale marudzisz...", "Filar CLXX Taksonomia Aktów Mowy"),
        (r"\bAle\s+żenada\b", "Ale marudzisz", "Filar CLXX Taksonomia Aktów Mowy"),

        # Real-time Invariant Safeguards (Deterministyczne Normy Morfologiczne i Afekt Seiyū - 0.00 PLN)
        (r"\b([Ii])mperiuma\b", r"\1mperium", "Rzeczowniki Nieodmienne na -um (Imperium)"),
        (r"\b(do|dla|wobec|u|od)\s+Mongola\b", r"\1 Mongołów", "Filar IV - Fleksja Etnonimów (Mongołów, nie Mongola)"),
        (r"\b(Do|Dla|Wobec|U|Od)\s+Mongola\b", r"\1 Mongołów", "Filar IV - Fleksja Etnonimów (Mongołów, nie Mongola)"),
        (r"\bprzeciw(?:ko)?\s+Mongolowi\b", "przeciwko Mongołom", "Filar IV - Fleksja Etnonimów"),
        (r"\bPrzeciw(?:ko)?\s+Mongolowi\b", "Przeciwko Mongołom", "Filar IV - Fleksja Etnonimów"),
        (r"\b(przed|z|ze)\s+Mongolem\b", r"\1 Mongołami", "Filar IV - Fleksja Etnonimów (Mongołami)"),
        (r"\b(Przed|Z|Ze)\s+Mongolem\b", r"\1 Mongołami", "Filar IV - Fleksja Etnonimów (Mongołami)"),
        (
            r"\b[Cc]-[Cc]zekaj\b",
            lambda m: "Czekaj" if m.group(0)[0].isupper() else "czekaj",
            "Likwidacja Literowego Jąkania Fansuberskiego (C-Czekaj)"
        ),
        (r"\bCzekaj,\s+mówisz\s+poważnie\?!?", "Chyba żartujesz...", "Filar CLVIII - Solilokwium Seiyū Maji Ka Yo"),
        (r"\bczekaj,\s+mówisz\s+poważnie\?!?", "chyba żartujesz...", "Filar CLVIII - Solilokwium Seiyū Maji Ka Yo"),

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
        (r"\b[Pp]anie\s+[Ss]hishou\b", "Mistrzu", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych (Panie Shishou -> Mistrzu)"),
        (r"\b[Pp]anie\s+[Tt]aichou\b", "Kapitanie", "Filar XLVIII - Zakaz Hybryd Honoryfikatywnych (Panie Taichou -> Kapitanie)"),
        (r"\b([Zz]e?|[Dd]o|[Oo]d|[Dd]la|[Oo]|[Uu])\s+[Pp]an(?:i|a|u|em|ie|ią)?\s+([Ss]ensei|[Ss]enpai|[Kk]ohai|[Ss]hishou|[Tt]aichou|[Ss]ama|[Dd]ono)\b", r"\1 \2", "Filar XXVII/XLVIII - Zakaz Hybryd Honoryfikatywnych po przyimku"),
        (r"\b[Pp]an(?:i|a|u|em|ie|ią)?\s+([Ss]ensei|[Ss]enpai|[Kk]ohai|[Ss]hishou|[Tt]aichou|[Ss]ama|[Dd]ono)\b", r"\1", "Filar XXVII/XLVIII - Zakaz Hybryd Honoryfikatywnych"),
        
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

        # Lexical Typos & Orthographic Deformations (Pillar CLXIV)
        (r"(^|[^\w]|\\[Nnh])([Ss])pyh(am|asz|a|amy|acie|ają|ać|ał|ała|ało|ali|ały|ano)\b", r"\g<1>\g<2>pyt\g<3>", "Filar CLXIV - Eliminacja Literówki 'spyham' -> 'spytam'"),
        (r"(^|[^\w]|\\[Nnh])([Ww])ziąść\b", r"\g<1>\g<2>ziąć", "Filar CLXIV - Eliminacja Błędu Ortograficznego 'wziąść' -> 'wziąć'"),
        (r"(^|[^\w]|\\[Nnh])([Pp])oszłem\b", r"\g<1>\g<2>oszedłem", "Filar CLXIV - Eliminacja Błędu Fleksyjnego 'poszłem' -> 'poszedłem'"),
        (r"(^|[^\w]|\\[Nnh])([Ww])łancza(ć|m|sz|my|cie|ją|ł|ła|ło|li|ły|no|nie|nia|niem)?\b", r"\g<1>\g<2>łącza\g<3>", "Filar CLXIV - Eliminacja Błędu Fonetycznego 'włanczać' -> 'włączać'"),
        (r"(^|[^\w]|\\[Nnh])([Ww])yłancza(ć|m|sz|my|cie|ją|ł|ła|ło|li|ły|no|nie|nia|niem)?\b", r"\g<1>\g<2>yłącza\g<3>", "Filar CLXIV - Eliminacja Błędu Fonetycznego 'wyłanczać' -> 'wyłączać'"),
        (r"(^|[^\w]|\\[Nnh])([Nn])a\s+codzień\b", r"\g<1>\g<2>a co dzień", "Filar CLXIV - Eliminacja Błędu Pisowni 'na codzień' -> 'na co dzień'"),
        (r"(^|[^\w]|\\[Nnh])([Cc])onajmniej\b", r"\g<1>\g<2>o najmniej", "Filar CLXIV - Eliminacja Błędu Pisowni 'conajmniej' -> 'co najmniej'"),
        (r"(^|[^\w]|\\[Nnh])([Nn])arazie\b", r"\g<1>\g<2>a razie", "Filar CLXIV - Eliminacja Błędu Pisowni 'narazie' -> 'na razie'"),
        (r"(^|[^\w]|\\[Nnh])([Zz])\s+przed\b", r"\g<1>sprzed", "Filar CLXIV - Eliminacja Błędu Pisowni 'z przed' -> 'sprzed'"),
        (r"(^|[^\w]|\\[Nnh])([Zz])\s+poza\b", r"\g<1>spoza", "Filar CLXIV - Eliminacja Błędu Pisowni 'z poza' -> 'spoza'"),
        (r"(^|[^\w]|\\[Nnh])([Ww])\s*każdym\s+bądź\s+razie\b", r"\g<1>\g<2> każdym razie", "Filar CLXIV - Eliminacja Skażenia 'w każdym bądź razie' -> 'w każdym razie'"),
        (r"(^|[^\w]|\\[Nnh])([Ww])\s+cudzysłowiu\b", r"\g<1>\g<2> cudzysłowie", "Filar CLXIV - Eliminacja Błędu Odmiany 'w cudzysłowiu' -> 'w cudzysłowie'"),
        (r"(^|[^\w]|\\[Nnh])([Pp])o\s+najmniejszej\s+linii\s+oporu\b", r"\g<1>\g<2>o linii najmniejszego oporu", "Filar CLXIV - Eliminacja Błędu Frazeologicznego 'po najmniejszej linii oporu'"),
        (r"(^|[^\w]|\\[Nnh])spowrotem\b", r"\g<1>z powrotem", "Filar CLXIV - Eliminacja Błędu Pisowni 'spowrotem' -> 'z powrotem'"),
        (r"(^|[^\w]|\\[Nnh])Spowrotem\b", r"\g<1>Z powrotem", "Filar CLXIV - Eliminacja Błędu Pisowni 'spowrotem' -> 'z powrotem'"),
        (r"(^|[^\w]|\\[Nnh])([Dd])latego\s+bo\b", r"\g<1>\g<2>latego że", "Filar CLXIV - Eliminacja Pleonazmu Spójnikowego 'dlatego bo' -> 'dlatego że'"),
        (r"(^|[^\w]|\\[Nnh])([Oo])d\s+nienacka\b", r"\g<1>znienacka", "Filar CLXIV - Eliminacja Błędu Pisowni 'od nienacka' -> 'znienacka'"),
        (r"\b((?:[A-Za-ząćęłńóśźż0-9]+\s+)?(?:raz|razy|kroć|dni|lat|godzin|minut|sekund|miesięcy|tygodni|kolejek|prób|zwycięstw|porażek))\s+pod\s+rząd\b", r"\1 z rzędu", "Filar CLXIV - Eliminacja Rusycyzmu 'pod rząd' -> 'z rzędu'"),
        (r"\b([Dd]wa|[Tt]rzy|[Cc]ztery|[Pp]ięć|[Ss]ześć|[Ss]iedem|[Oo]siem|[Dd]ziewięć|[Dd]ziesiąt|[Kk]ilka|[Pp]arę|[Ww]iele|[Kk]olejn[a-ząćęłńóśźż]*)\s+([a-ząćęłńóśźż]+)\s+pod\s+rząd\b", r"\1 \2 z rzędu", "Filar CLXIV - Eliminacja Rusycyzmu 'pod rząd' -> 'z rzędu'"),

        # Double inflection / case endings (Pillar CLXIV)
        (r"\b([Ww])ielkimem\b", r"\g<1>ielkim", "Filar CLXIV - Podwójna końcówka narzędnika 'Wielkimem' -> 'Wielkim'"),

        # Historical & Epic Dialogue Slang (Pillar XXXV / AGENTS.md Klasa A/B/C)
        (r"\b[Zz]mywajmy\s+się\b", lambda m: "Uciekajmy" if m.group(0)[0].isupper() else "uciekajmy", "Filar XXXV - Eliminacja Slangu 'zmywajmy się' -> 'uciekajmy'"),
        (r"\b[Zz]mywaj\s+się\b", lambda m: "Uciekaj" if m.group(0)[0].isupper() else "uciekaj", "Filar XXXV - Eliminacja Slangu 'zmywaj się' -> 'uciekaj'"),
        (r"\b[Zz]mywajcie\s+się\b", lambda m: "Uciekajcie" if m.group(0)[0].isupper() else "uciekajcie", "Filar XXXV - Eliminacja Slangu 'zmywajcie się' -> 'uciekajcie'"),
        (r"\b([Jj])ak\s+nas\s+nakryją\b", r"\g<1>ak nas schwytają", "Filar XXXV - Eliminacja Slangu 'jak nas nakryją' -> 'jak nas schwytają'"),
        (r"\b([Jj])eśli\s+nas\s+nakryją\b", r"\g<1>eśli nas schwytają", "Filar XXXV - Eliminacja Slangu 'jeśli nas nakryją' -> 'jeśli nas schwytają'"),
        (r"\b([Gg])dy\s+nas\s+nakryją\b", r"\g<1>dy nas schwytają", "Filar XXXV - Eliminacja Slangu 'gdy nas nakryją' -> 'gdy nas schwytają'"),
        (r"\b([Nn])akryją\s+nas\b", r"\g<1>as schwytają", "Filar XXXV - Eliminacja Slangu 'nakryją nas' -> 'schwytają nas'"),

        # Pleonasms & tautologies (Filar IV / Belczyk)
        (r"\b([Ss]pada(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+w\s+dół\b", r"\1", "Filar IV - Eliminacja Pleonazmu 'spadać w dół'"),
        (r"\b([Ww]znosi(?:ć|m|sz|my|cie|ją|ł|ła|ło|li|ły)?)\s+się\s+w\s+górę\b", r"\1 się", "Filar IV - Eliminacja Pleonazmu 'wznosić się w górę'"),
        (r"\b[Ww]zajemn(?:a|ej|ą|e|ych|ym|ymi)\s+(współprac(?:a|y|ę|ą|ie|om|ami))\b", lambda m: m.group(1).capitalize() if m.group(0)[0].isupper() else m.group(1), "Filar IV - Eliminacja Pleonazmu 'wzajemna współpraca'"),
        (r"\b([Ff]akt(?:y|ów|om|ami|ach)?)\s+autentyczn(?:e|ych|ym|ymi)\b", r"\1", "Filar IV - Eliminacja Pleonazmu 'fakty autentyczne'"),

        # Dialogic calques & gestural idioms (Filar IV / CXXXVII / XVIII)
        (r"\b[Zz]rób\s+swoje\s+najlepsze\b", lambda m: "Daj z siebie wszystko" if m.group(0)[0].isupper() else "daj z siebie wszystko", "Filar IV/CLIII - Eliminacja Kalki 'Zrób swoje najlepsze'"),
        (r"\b[Zz]róbcie\s+swoje\s+najlepsze\b", lambda m: "Dajcie z siebie wszystko" if m.group(0)[0].isupper() else "dajcie z siebie wszystko", "Filar IV/CLIII - Eliminacja Kalki 'Zróbcie swoje najlepsze'"),
        (r"\b[Dd]obrej\s+nocy\b", lambda m: "Dobranoc" if m.group(0)[0].isupper() else "dobranoc", "Filar IV - Eliminacja Kalki 'Dobrej nocy' -> 'Dobranoc'"),
        (r"^\s*[Zz]gadnij\s+co\?([!\.\?]*)\s*$", r"Wiesz co?\1", "Filar CXXXVII - Eliminacja Kalki 'Guess what?'"),
        (r"^\s*[Tt]o\s+jest\s+to,?\s+o\s+czym\s+mówię([!\.\?]*)\s*$", r"O tym właśnie mówię\1", "Filar CXXXVII - Eliminacja Kalki 'That's what I'm talking about'"),
        (r"\b[Tt]utaj\s+masz\b", lambda m: "Trzymaj" if m.group(0)[0].isupper() else "trzymaj", "Filar IV/XVIII - Eliminacja Kalki Gestu 'Here you go' -> 'Trzymaj'"),
        (r"\b[Oo]to\s+masz\b", lambda m: "Trzymaj" if m.group(0)[0].isupper() else "trzymaj", "Filar IV/XVIII - Eliminacja Kalki Gestu 'Here you go' -> 'Trzymaj'"),
        (r"\b[Oo]to\s+jest\b", lambda m: "Proszę" if m.group(0)[0].isupper() else "proszę", "Filar IV/XVIII - Eliminacja Kalki Gestu 'Here it is' -> 'Proszę'"),

        # Historical & Fantasy Register Governance & English Calques (Filar IV / CLXVII)
        (r"\b[Dd]obre pytanie\b", lambda m: "Trudno powiedzieć" if m.group(0)[0].isupper() else "trudno powiedzieć", "Filar IV/CLXVII - Eliminacja Angielskiej Kalki 'Good question'"),
        (r"\b[Ww]\s+sumie\s+to\s+nam\s+na\s+rękę\b", lambda m: "W istocie to nam na rękę" if m.group(0)[0].isupper() else "w istocie to nam na rękę", "Filar CLXVII - Puryzm Rejestru Historycznego 'W sumie' -> 'W istocie'"),
        (r"\b[Oo]j\s+tam[!,\?]?\b", lambda m: "Daj spokój" if m.group(0)[0].isupper() else "daj spokój", "Filar CLXVII - Eliminacja Slangu 'Oj tam' w Dramacie Historycznym"),

        # Otaku slang & honorifics adaptation (Filar XXVII)
        (r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)-(?:senpai|taso|tan)\b", r"\1", "Filar XXVII - Adaptacja Sufiksów Honoryfikatywnych"),

        # Binary alternative comma eradication (Filar LX)
        (r"\b([A-Za-ząćęłńóśźż0-9]+),\s+czy\s+(bez|nie|tak)\b", r"\1 czy \2", "Filar LX - Zakaz Przecinka przed Czy w Alternatywie Rozłącznej"),

        # Trailing cut-off speech attached dash (Filar LX)
        (r"([A-Za-ząćęłńóśźż])[–—\-](?=\s*\\N|\s*$|[!\?…])", r"\1...", "Filar LX - Formatowanie Przerwania Wypowiedzi"),

        # Deictic Temporal Syntax & Anti-Adjectivization (Filar CLXVIII)
        (r"\b([Pp])ojutrzejsz(?:y|ą|a|e|ego|ej|emu|ym|ych|ymi)?\s+([a-ząćęłńóśźż]+)\b",
         lambda m: (f"{m.group(2)} pojutrze" if m.group(1) == "p" else f"{m.group(2).capitalize()} pojutrze"),
         "Filar CLXVIII - Dekompozycja Sztucznej Przydawki 'Pojutrzejszy' -> 'Pojutrze'"),
        (r"\b([Pp])rzedwczorajsz(?:y|ą|a|e|ego|ej|emu|ym|ych|ymi)?\s+([a-ząćęłńóśźż]+)\b",
         lambda m: (f"{m.group(2)} sprzed dwóch dni" if m.group(1) == "p" else f"{m.group(2).capitalize()} sprzed dwóch dni"),
         "Filar CLXVIII - Dekompozycja Sztucznej Przydawki 'Przedwczorajszy' -> 'Sprzed dwóch dni'"),
        (r"\b([Ww])\s+dzisiejszy\s+wieczór\b",
         lambda m: "Dziś wieczorem" if m.group(1) == "W" else "dziś wieczorem",
         "Filar CLXVIII - Naturalna Deiksa Pory Dnia 'dziś wieczorem'"),
        (r"\b([Ww])\s+jutrzejszy\s+poranek\b",
         lambda m: "Jutro rano" if m.group(1) == "W" else "jutro rano",
         "Filar CLXVIII - Naturalna Deiksa Pory Dnia 'jutro rano'"),
        (r"\b([Ww])e\s+wczorajszy\s+wieczór\b",
         lambda m: "Wczoraj wieczorem" if m.group(1) == "W" else "wczoraj wieczorem",
         "Filar CLXVIII - Naturalna Deiksa Pory Dnia 'wczoraj wieczorem'"),
        (r"\b([Ww])\s+dzisiejszą\s+noc\b",
         lambda m: "Dziś w nocy" if m.group(1) == "W" else "dziś w nocy",
         "Filar CLXVIII - Naturalna Deiksa Pory Dnia 'dziś w nocy'"),
        (r"\b([Pp])rzyszłotygodniow(?:y|ą|a|e|ego|ej|emu|ym|ych|ymi)?\s+([a-ząćęłńóśźż]+)\b",
         lambda m: (f"{m.group(2)} w przyszłym tygodniu" if m.group(1) == "p" else f"{m.group(2).capitalize()} w przyszłym tygodniu"),
         "Filar CLXVIII - Dekompozycja 'Przyszłotygodniowy' -> 'W przyszłym tygodniu'"),
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
        prev_line_text: str = "",
        source_en: str = ""
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

        # 1b. Definite Article Nominative vs False Vocative (Filar CLXXIII / §0 & §3 Offline-First)
        if source_en:
            from series_memory import resolve_definite_article_nominative
            fixed_nom, nom_changed = resolve_definite_article_nominative(source_en, modified)
            if nom_changed:
                modified = fixed_nom
                applied_fixes.append(f"[Filar CLXXIII - Mianownik Wykrzyknikowy] Przywrócono mianownik dla '{source_en.strip()}'")

        # 1c. Token Punctuation Stutter Sanitizer (Filar CLXXIV - 0.00 PLN)
        stutter_pat = r"\b([A-Za-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]{2,}[\.!\?…]+)\s*\1(?!\w)"
        if re.search(stutter_pat, modified):
            modified = re.sub(stutter_pat, r"\1", modified)
            applied_fixes.append("[Filar CLXXIV - Higiena Tokenów] Usunięto zacięcie/jąkanie tokenu z interpunkcją")

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

        # 3. Strict glossary overrides (Sanitized from parenthetical notes/brackets & homograph protection)
        if custom_glossary:
            for src, raw_trg in sorted(custom_glossary.items(), key=lambda x: len(x[0]), reverse=True):
                if not src or not raw_trg:
                    continue
                src_clean = src.strip()
                # Stopword & safety protection: do not substitute single short words that collide with Polish homographs
                if " " not in src_clean and (len(src_clean) < 3 or src_clean.lower() in {
                    "to", "no", "do", "on", "i", "a", "ja", "ze", "ma", "te", "ta", "co",
                    "ten", "pan", "tam", "dla", "bez", "jak", "sie", "się", "ale", "lub", "czy"
                }):
                    continue
                # Strip parenthetical clarifications e.g. "Tus (Miasto w Persji)" -> "Tus" (preserving bracketed signs like "[ KRONIKA ... ]")
                raw_trg_clean = raw_trg.strip()
                if raw_trg_clean.startswith("[") and raw_trg_clean.endswith("]"):
                    clean_trg = raw_trg_clean
                else:
                    clean_trg = re.sub(r"\s*[\(\[].*?[\)\]]", "", raw_trg).strip()
                if "/" in clean_trg:
                    clean_trg = clean_trg.split("/")[0].strip()
                if not clean_trg or src.lower() == clean_trg.lower():
                    continue
                prefix_b = r"\b" if re.match(r"^\w", src_clean) else ""
                suffix_b = r"\b" if re.search(r"\w$", src_clean) else ""
                if clean_trg and clean_trg[-1] in "!?.:":
                    trail_punct = re.escape(clean_trg[-1])
                    pat_src = rf"{prefix_b}{re.escape(src_clean)}{suffix_b}(?:\s*{trail_punct}+)?"
                else:
                    pat_src = rf"{prefix_b}{re.escape(src_clean)}{suffix_b}"

                if re.search(pat_src, modified, re.IGNORECASE):
                    def _case_gloss_repl_single(m, target=clean_trg):
                        matched = m.group(0)
                        if matched.isupper():
                            return target.upper()
                        elif matched[0].isupper():
                            return target[0].upper() + target[1:]
                        else:
                            if target[0].isupper() and len(target) > 1 and target[1].islower():
                                return target
                            return target[0].lower() + target[1:]
                    modified = re.sub(pat_src, _case_gloss_repl_single, modified, flags=re.IGNORECASE)
                    applied_fixes.append(f"[Słownik Deterministyczny] '{src}' -> '{clean_trg}'")

        # 4. Grammatical gender alignment (Filar XIII & Filar CXXXVI: Acoustic & Cognitive Gender Triangulation)
        if not is_sign:
            spk_norm = (speaker_gender or "").lower()
            is_male_speaker = any(w in spk_norm for w in ["mężczyzna", "chłopiec", "male", "boy", "męski"]) and not any(w in spk_norm for w in ["alt", "kobieta", "żeńsk", "starszej"])
            is_explicit_female_speaker = any(w in spk_norm for w in ["kobieta", "dziewczynka", "female", "girl", "żeński", "alt starszej", "alt dojrzały", "boraqchin", "cesarzowa", "chatun", "matrona"])
            is_female_speaker = is_explicit_female_speaker or (is_all_girls_scene and not is_male_speaker)

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
                    (r"\b[Bb]ałam się\b", lambda m: "Bałam się" if m.group(0)[0].isupper() else "bałam się"),
                    (r"\b[Uu]dałam się\b", lambda m: "Udałem się" if m.group(0)[0].isupper() else "udałem się"),
                    (r"\b[Bb]yłam\b", lambda m: "Byłem" if m.group(0)[0].isupper() else "byłem"),
                    (r"\b[Zz]gubiłam się\b", lambda m: "Zgubiłem się" if m.group(0)[0].isupper() else "zgubiłem się"),
                    (r"\b[Mm]iałabym\b", lambda m: "Miałbym" if m.group(0)[0].isupper() else "miałbym"),
                    (r"\b[Cc]hciałabym\b", lambda m: "Chciałbym" if m.group(0)[0].isupper() else "chciałbym"),
                    (r"\b[Mm]ogłabym\b", lambda m: "Mógłbym" if m.group(0)[0].isupper() else "mógłbym"),
                    (r"\b[Ww]iedziałabym\b", lambda m: "Wiedziałbym" if m.group(0)[0].isupper() else "wiedziałbym"),
                    (r"\b[Zz]robiłabym\b", lambda m: "Zrobiłbym" if m.group(0)[0].isupper() else "zrobiłbym"),
                    (r"\b[Bb]yłabym\b", lambda m: "Byłbym" if m.group(0)[0].isupper() else "byłbym"),
                    (r"\b[Jj]esteś pewna\?", "Jesteś pewien?"),
                    (r"\b[Gg]łupia jesteś\?", "Głupi jesteś?"),
                    (r"\b[Oo]szalałaś\?", "Oszalałeś?"),
                    (r"\b[Zz]głupiałaś\?", "Zgłupiałeś?"),
                ]
                for pattern, repl in male_fixes:
                    if re.search(pattern, modified):
                        modified = re.sub(pattern, repl, modified)
                        applied_fixes.append(f"[Filar CXXXVI - Mówca Męski/Chłopiec] Korekta rodzaju żeńskiego na męski: {pattern}")

                def _morph_f_to_m_repl(m):
                    word = m.group(0)
                    converted = convert_first_person_feminine_to_masculine(word)
                    if converted and converted != word:
                        applied_fixes.append(f"[Filar CXXXVI - Mówca Męski 1. os.] Korekta rodzaju żeńskiego na męski: '{word}' -> '{converted}'")
                        return converted
                    return word
                modified = re.sub(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łam|łabym)\b", _morph_f_to_m_repl, modified)

            elif is_female_speaker:
                female_address_fixes = [
                    (r"\b[Gg]łupi jesteś\?", "Głupia jesteś?"),
                    (r"\b[Jj]esteś pewien\?", "Jesteś pewna?"),
                    (r"\b[Oo]szalałeś\?", "Oszalałaś?"),
                    (r"\b[Zz]głupiałeś\?", "Zgłupiałaś?"),
                    (r"\b[Ww]idziałeś to\?", "Widziałaś to?"),
                    (r"\b[Ss]łyszałeś to\?", "Słyszałaś to?"),
                    (r"\b[Zz]robiłeś to\?", "Zrobiłaś to?"),
                    (r"\b[Pp]oszedłeś tam\?", "Poszłaś tam?"),
                    (r"\b[Mm]yślałeś, że\b", "Myślałaś, że"),
                    (r"\b([Ww]yglądasz\s+na|[Ss]prawiasz\s+wrażenie)\s+([A-Za-ząćęłńóśźż]{3,})ego\b", lambda m: f"{m.group(1)} {m.group(2)}ą" if m.group(2).lower() not in {"cz", "k", "dlacz", "tamt", "t", "nicz", "jakieś", "wszystki", "jedn"} else m.group(0)),
                    (r"\b[Ww]yglądasz na wzburzonego\b", "Wyglądasz na wzburzoną"),
                    (r"\bwyglądasz na wzburzonego\b", "wyglądasz na wzburzoną"),
                    (r"\b[Jj]esteś pewien\b", lambda m: "Jesteś pewna" if m.group(0)[0].isupper() else "jesteś pewna"),
                    (r"\b[Jj]esteś gotowy\b", lambda m: "Jesteś gotowa" if m.group(0)[0].isupper() else "jesteś gotowa"),
                    (r"\b[Jj]esteś sam\b", lambda m: "Jesteś sama" if m.group(0)[0].isupper() else "jesteś sama"),
                ]
                for pattern, repl in female_address_fixes:
                    if re.search(pattern, modified):
                        modified = re.sub(pattern, repl, modified)
                        applied_fixes.append(f"[Filar XIII/CXXXVI - Adresat Żeński/Dziewczynka] Korekta rodzaju męskiego na żeński: {pattern}")

                if is_explicit_female_speaker:
                    female_1st_person_fixes = [
                        (r"\b[Dd]omyślałem się\b", lambda m: "Domyślałam się" if m.group(0)[0].isupper() else "domyślałam się"),
                        (r"\b[Mm]yślałem\b", lambda m: "Myślałam" if m.group(0)[0].isupper() else "myślałam"),
                        (r"\b[Ww]iedziałem\b", lambda m: "Wiedziałam" if m.group(0)[0].isupper() else "wiedziałam"),
                        (r"\b[Ww]idziałem\b", lambda m: "Widziałam" if m.group(0)[0].isupper() else "widziałam"),
                        (r"\b[Zz]robiłem\b", lambda m: "Zrobiłam" if m.group(0)[0].isupper() else "zrobiłam"),
                        (r"\b[Pp]oszedłem\b", lambda m: "Poszłam" if m.group(0)[0].isupper() else "poszłam"),
                        (r"\b[Pp]rzyszedłem\b", lambda m: "Przyszłam" if m.group(0)[0].isupper() else "przyszłam"),
                        (r"\b[Zz]nalazłem\b", lambda m: "Znalazłam" if m.group(0)[0].isupper() else "znalazłam"),
                        (r"\b[Cc]zułem\b", lambda m: "Czułam" if m.group(0)[0].isupper() else "czułam"),
                        (r"\b[Ss]łyszałem\b", lambda m: "Słyszałam" if m.group(0)[0].isupper() else "słyszałam"),
                        (r"\b[Chch]ciałem\b", lambda m: "Chciałam" if m.group(0)[0].isupper() else "chciałam"),
                        (r"\b[Mm]ogłem\b", lambda m: "Mogłam" if m.group(0)[0].isupper() else "mogłam"),
                        (r"\b[Zz]rozumiałem\b", lambda m: "Zrozumiałam" if m.group(0)[0].isupper() else "zrozumiałam"),
                        (r"\b[Pp]owiedziałem\b", lambda m: "Powiedziałam" if m.group(0)[0].isupper() else "powiedziałam"),
                        (r"\b[Bb]ałem się\b", lambda m: "Bałam się" if m.group(0)[0].isupper() else "bałam się"),
                        (r"\b[Uu]dałem się\b", lambda m: "Udałam się" if m.group(0)[0].isupper() else "udałam się"),
                        (r"\b[Bb]yłem\b", lambda m: "Byłam" if m.group(0)[0].isupper() else "byłam"),
                        (r"\b[Mm]iałem\b", lambda m: "Miałam" if m.group(0)[0].isupper() else "miałam"),
                        (r"\b[Ww]róciłem\b", lambda m: "Wróciłam" if m.group(0)[0].isupper() else "wróciłam"),
                        (r"\b[Dd]ostałem\b", lambda m: "Dostałam" if m.group(0)[0].isupper() else "dostałam"),
                        (r"\b[Pp]omyślałem\b", lambda m: "Pomyślałam" if m.group(0)[0].isupper() else "pomyślałam"),
                        (r"\b[Zz]gubiłem się\b", lambda m: "Zgubiłam się" if m.group(0)[0].isupper() else "zgubiłam się"),
                        (r"\b[Zz]raniłem\b", lambda m: "Zraniłam" if m.group(0)[0].isupper() else "zraniłam"),
                        (r"\b[Ss]krzywdziłem\b", lambda m: "Skrzywdziłam" if m.group(0)[0].isupper() else "skrzywdziłam"),
                        (r"\b[Uu]ratowałem\b", lambda m: "Uratowałam" if m.group(0)[0].isupper() else "uratowałam"),
                        (r"\b[Oo]ddałem\b", lambda m: "Oddałam" if m.group(0)[0].isupper() else "oddałam"),
                        (r"\b[Mm]iałbym\b", lambda m: "Miałabym" if m.group(0)[0].isupper() else "miałabym"),
                        (r"\b[Cc]hciałbym\b", lambda m: "Chciałbym" if m.group(0)[0].isupper() else "chciałabym"),
                        (r"\b[Mm]ógłbym\b", lambda m: "Mogłabym" if m.group(0)[0].isupper() else "mogłabym"),
                        (r"\b[Ww]olałbym\b", lambda m: "Wolałabym" if m.group(0)[0].isupper() else "wolałabym"),
                        (r"\b[Mm]usiałbym\b", lambda m: "Musiałabym" if m.group(0)[0].isupper() else "musiałabym"),
                        (r"\b[Ww]iedziałbym\b", lambda m: "Wiedziałabym" if m.group(0)[0].isupper() else "wiedziałabym"),
                        (r"\b[Zz]robiłbym\b", lambda m: "Zrobiłabym" if m.group(0)[0].isupper() else "zrobiłabym"),
                        (r"\b[Bb]yłbym\b", lambda m: "Byłabym" if m.group(0)[0].isupper() else "byłabym"),
                        (r"\b[Pp]oszedłbym\b", lambda m: "Poszłabym" if m.group(0)[0].isupper() else "poszłabym"),
                        (r"\b[Pp]rzyszedłbym\b", lambda m: "Przyszłabym" if m.group(0)[0].isupper() else "przyszłabym"),
                        (r"\b[Zz]nalazłbym\b", lambda m: "Znalazłabym" if m.group(0)[0].isupper() else "znalazłabym"),
                        (r"\b[Pp]owiedziałbym\b", lambda m: "Powiedziałabym" if m.group(0)[0].isupper() else "powiedziałabym"),
                        (r"\b[Cc]zułbym\b", lambda m: "Czułabym" if m.group(0)[0].isupper() else "czułabym"),
                        (r"\b[Ww]idziałbym\b", lambda m: "Widziałabym" if m.group(0)[0].isupper() else "widziałabym"),
                        (r"\b[Pp]omyślałbym\b", lambda m: "Pomyślałabym" if m.group(0)[0].isupper() else "pomyślałabym"),
                    ]
                    for pattern, repl in female_1st_person_fixes:
                        if re.search(pattern, modified):
                            modified = re.sub(pattern, repl, modified)
                            applied_fixes.append(f"[Filar XIII/CXXXVI/CLXIX - Mówczyni Żeńska 1. os.] Korekta rodzaju męskiego na żeński: {pattern}")

                    def _morph_m_to_f_repl(m):
                        word = m.group(0)
                        converted = convert_first_person_masculine_to_feminine(word)
                        if converted and converted != word:
                            applied_fixes.append(f"[Filar XIII/CXXXVI/CLXIX - Mówczyni Żeńska 1. os.] Korekta rodzaju męskiego na żeński: '{word}' -> '{converted}'")
                            return converted
                        return word
                    modified = re.sub(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łem|łbym)\b", _morph_m_to_f_repl, modified)

        # 4a-2. Female Vocative Case Harmonization (Filar LX & CLVII: Mianownik -> Wołacz dla imion żeńskich na -a)
        if not is_sign:
            from series_memory import is_inherently_female_name, to_polish_female_vocative
            def _fem_voc_repl(m):
                prefix = m.group(1) or ""
                name = m.group(2)
                punct = m.group(3)
                if is_inherently_female_name(name) and name.lower().endswith("a"):
                    voc = to_polish_female_vocative(name)
                    if voc != name:
                        applied_fixes.append(f"[Filar LX/CLVII - Tarcza Wołacza] Zamiana mianownika na wołacz dla imienia żeńskiego: '{name}' -> '{voc}'")
                        return f"{prefix}{voc}{punct}"
                return m.group(0)

            modified = re.sub(r"(^|[\\\/][Nnh]|\b(?:och|ach|hej|o|ej|halo),?\s+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})([,?!])", _fem_voc_repl, modified)

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
            first_w = ""
            if not has_explicit_formal_vocative:
                yobi_m = re.search(r"(?<!\bpanie\s)(?<!\bpani\s)(?<!\bpanno\s)(?<!\bpanu\s)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})[,?!](?:\s+|\\N)+.*\b(pan|pani|pana|panu)\b", modified, re.IGNORECASE)
                if yobi_m:
                    first_w = yobi_m.group(1).lower()
                    if first_w not in ["panie", "pani", "panno", "panu", "pana", "proszę", "przepraszam", "doktorze", "profesorze", "inspektorze", "zaraz", "chwila", "czekaj", "słuchaj", "patrz", "widzisz"]:
                        line_has_yobisute = True

                # Also check vocative at the start of the line: e.g. "Moniko, ..." or "Shizuku, ..."
                if not line_has_yobisute:
                    start_voc_m = re.match(r"^([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})[,?!]", modified)
                    if start_voc_m:
                        sw = start_voc_m.group(1).lower()
                        if sw not in ["proszę", "przepraszam", "doktorze", "profesorze", "zaraz", "chwila", "czekaj", "słuchaj", "patrz", "widzisz", "panie", "pani"]:
                            first_w = sw
                            line_has_yobisute = True

            if (is_informal_ty or line_has_yobisute) and not has_explicit_formal_vocative:
                from series_memory import is_inherently_female_name
                is_female_addressee = False
                if first_w and is_inherently_female_name(first_w):
                    is_female_addressee = True

                if is_female_addressee:
                    raw_pan_pairs = [
                        ("wygrał", "pan", "wygrałaś"),
                        ("wygrała", "pani", "wygrałaś"),
                        ("zrobił", "pan", "zrobiłaś"),
                        ("zrobiła", "pani", "zrobiłaś"),
                        ("widział", "pan", "widziałaś"),
                        ("widziała", "pani", "widziałaś"),
                        ("słyszał", "pan", "słyszałaś"),
                        ("słyszała", "pani", "słyszałaś"),
                        ("powiedział", "pan", "powiedziałaś"),
                        ("powiedziała", "pani", "powiedziałaś"),
                        ("poszedł", "pan", "poszłaś"),
                        ("poszła", "pani", "poszłaś"),
                        ("miał", "pan", "miałaś"),
                        ("miała", "pani", "miałaś"),
                        ("był", "pan", "byłaś"),
                        ("była", "pani", "byłaś"),
                        ("chciał", "pan", "chciałaś"),
                        ("chciała", "pani", "chciałaś"),
                        ("mógł", "pan", "mogłaś"),
                        ("mogła", "pani", "mogłaś"),
                        ("wiedział", "pan", "wiedziałaś"),
                        ("wiedziała", "pani", "wiedziałaś"),
                        ("myślał", "pan", "myślałaś"),
                        ("myślała", "pani", "myślałaś"),
                        ("pan", "wygrał", "wygrałaś"),
                        ("pani", "wygrała", "wygrałaś"),
                        ("pan", "zrobił", "zrobiłaś"),
                        ("pani", "zrobiła", "zrobiłaś"),
                        ("pan", "widział", "widziałaś"),
                        ("pani", "widziała", "widziałaś"),
                        ("pan", "słyszał", "słyszałaś"),
                        ("pani", "słyszała", "słyszałaś"),
                        ("pan", "powiedział", "powiedziałaś"),
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
                else:
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

            # 7. MAJI KA YO / MAJI DE / USO DARO (マジかよ / マジで / 嘘だろ / まさか):
            # Solilokwium niedowierzania rzucane pod nosem -> eliminacja sztucznych pytań dialogowych do rozmówcy ('Czekaj, mówisz poważnie?!')
            if any(k in clean_audio_jp for k in ["maji ka yo", "maji de", "マジかよ", "マジで", "uso daro", "嘘だろ", "masaka", "まさか"]):
                if re.search(r"\b(?:[Cc]-[Cc]zekaj|[Cc]zekaj),\s+mówisz\s+poważnie\b", modified, re.IGNORECASE):
                    def _maji_repl(m):
                        return "Chyba żartujesz..." if m.group(0)[0].isupper() else "chyba żartujesz..."
                    modified = re.sub(r"\b(?:[Cc]-[Cc]zekaj|[Cc]zekaj),\s+mówisz\s+poważnie(?:\?!|\?|!|\.\.\.)?", _maji_repl, modified, flags=re.IGNORECASE)
                    applied_fixes.append("[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Maji ka yo / Uso daro' w audio: zastąpiono dialogowe pytanie 'mówisz poważnie' solilokwium 'chyba żartujesz...'")

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
        # 5. Anti-Bracket normalization for all subtitles (Pillars IV & LX)
        # 5a. Strip outer and chained square brackets e.g. "[ Przepraszam za zwłokę! ]" -> "Przepraszam za zwłokę!"
        # e.g. "[ ODCINEK 10 ] [ TYTUŁ 1 ] [ TYTUŁ 2 ]" -> "ODCINEK 10\NTYTUŁ 1\NTYTUŁ 2"
        # Preserves legitimate RPG/Game UI system tags (e.g. [ OKNO STATUSU ], [ STATUS ]) per Filar XXIV
        if ("[" in modified or "]" in modified) and not any(k in modified for k in ["[ OKNO STATUSU ]", "[ STATUS ]", "[ STATYSTYKI ]", "[ UMIEJĘTNOŚĆ ]", "[ POZIOM ]"]):
            bracket_before = modified
            if re.search(r"\]\s*\[", modified):
                if is_sign:
                    modified = re.sub(r"\s*\]\s*\[\s*", r"\\N", modified)
                else:
                    modified = re.sub(r"\s*\]\s*\[\s*", r" - ", modified)

            lines_m = modified.split(r"\N")
            new_lines_m = []
            for lm in lines_m:
                lm_stripped = lm.strip()
                if lm_stripped.startswith("[") and lm_stripped.endswith("]"):
                    lm_stripped = lm_stripped[1:-1].strip()
                new_lines_m.append(lm_stripped)
            modified = r"\N".join(new_lines_m)

            modified = re.sub(r"^[ \t]*\[+[ \t]*", "", modified)
            modified = re.sub(r"[ \t]*\]+[ \t]*$", "", modified)
            if modified != bracket_before:
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

        # 6b. Title & Subtitle capitalization (Filar XLI & LX)
        # In episode titles (e.g. "Odcinek 12\Nniezmienny step" -> "Odcinek 12\NNiezmienny step")
        # and signs, ensure title lines start with a capital letter.
        if is_sign or re.search(r"\b(?:Odcinek|Rozdział)\s+\d+\b", modified, re.IGNORECASE):
            def _cap_title_line(m):
                return f"{m.group(1)}{m.group(2).upper()}"
            modified = re.sub(r"(\\N\s*(?:\{[^\}]*\}\s*)*)([a-ząćęłńóśźż])", _cap_title_line, modified)
            if is_sign:
                def _cap_start_sign(m):
                    tag = m.group(1) or ""
                    return f"{tag}{m.group(2).upper()}"
                modified = re.sub(r"^(\s*(?:\{[^\}]*\}\s*)*)([a-ząćęłńóśźż])", _cap_start_sign, modified)

        # 6c. Title Apposition Case Agreement (Filar CXXIV & CLVII)
        # When a title in Nominative (generał, pułkownik, major, kapitan, admirał, książę, król, chan, baron, hrabia, wódz)
        # is preceded by a Genitive/Accusative-governing preposition/phrase (e.g. na ziemiach, do rąk, w rękach, u boku, pod wodzą)
        # and precedes a proper name (e.g. 'na ziemiach generał Ilüge'), inflect title to Genitive/Accusative.
        TITLE_GEN_MAP = {
            "generał": "generała",
            "pułkownik": "pułkownika",
            "major": "majora",
            "kapitan": "kapitana",
            "admirał": "admirała",
            "książę": "księcia",
            "król": "króla",
            "chan": "chana",
            "baron": "barona",
            "hrabia": "hrabiego",
            "wódz": "wodza",
        }
        appos_pat = r"\b(na\s+ziemiach|na\s+ziemie|w\s+rękach|do\s+rąk|u\s+boku|pod\s+wodzą|z\s+rozkazu|przeciwko|przeciw|dla|z\s+rąk)\s+(generał|pułkownik|major|kapitan|admirał|książę|król|chan|baron|hrabia|wódz)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\w]+)"
        if re.search(appos_pat, modified, re.IGNORECASE):
            def _fix_appos_match(m):
                prep = m.group(1)
                title = m.group(2)
                name = m.group(3)
                repl_title = TITLE_GEN_MAP.get(title.lower(), title)
                if title[0].isupper():
                    repl_title = repl_title.capitalize()
                return f"{prep} {repl_title} {name}"
            modified = re.sub(appos_pat, _fix_appos_match, modified, flags=re.IGNORECASE)
            applied_fixes.append("[Filar CXXIV - Tytulatura i Zgoda Przypadkowa w Apozycji] Poprawiono mianownik tytułu na dopełniacz po przyimku rządu dopełniaczowego")

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
    (r"\bweszłam\b", "wszedłem"),
    (r"\bzamierzałam\b", "zamierzałem"),
    (r"\bdopięłam\b", "dopiąłem"),
    (r"\bmiałabym\b", "miałbym"),
    (r"\bmusiałabym\b", "musiałbym"),
    (r"\bwiedziałabym\b", "wiedziałbym"),
    (r"\bzrobiłabym\b", "zrobiłbym"),
    (r"\bbyłabym\b", "byłbym"),
    (r"\bposzłabym\b", "poszedłbym"),
    (r"\bprzyszłabym\b", "przyszedłbym"),
    (r"\bznalazłabym\b", "znalazłbym"),
    (r"\bpowiedziałabym\b", "powiedziałbym"),
    (r"\bczułabym\b", "czułbym"),
    (r"\bwidziałabym\b", "widziałbym"),
    (r"\bpomyślałabym\b", "pomyślałbym"),
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
    (r"\bmogłem\b", "mogłam"),
    (r"\bzraniłem\b", "zraniłam"),
    (r"\bskrzywdziłem\b", "skrzywdziłam"),
    (r"\bpomyślałem\b", "pomyślałam"),
    (r"\bpowiedziałem\b", "powiedziałam"),
    (r"\bznalazłem\b", "znalazłam"),
    (r"\boddałem\b", "oddałam"),
    (r"\buratowałem\b", "uratowałam"),
    (r"\bzgubiłem\s+się\b", "zgubiłam się"),
    (r"\bzostawiłem\b", "zostawiłam"),
    (r"\bpoczułem\b", "poczułam"),
    (r"\bzobaczyłem\b", "zobaczyłam"),
    (r"\bdostałem\b", "dostałam"),
    (r"\bzamierzałem\b", "zamierzałam"),
    (r"\bdopiąłem\b", "dopięłam"),
    (r"\bmiałbym\b", "miałabym"),
    (r"\bmusiałbym\b", "musiałabym"),
    (r"\bwiedziałbym\b", "wiedziałabym"),
    (r"\bzrobiłbym\b", "zrobiłabym"),
    (r"\bbyłbym\b", "byłabym"),
    (r"\bposzedłbym\b", "poszłabym"),
    (r"\bprzyszedłbym\b", "przyszłabym"),
    (r"\bznalazłbym\b", "znalazłabym"),
    (r"\bpowiedziałbym\b", "powiedziałabym"),
    (r"\bczułbym\b", "czułabym"),
    (r"\bwidziałbym\b", "widziałabym"),
    (r"\bpomyślałbym\b", "pomyślałabym")
]

NON_VERBS_ON_ALA = {
    "mała", "biała", "skała", "chwała", "ciała", "pała", "żała", "strzała", "pochwała",
    "generała", "admirała", "marszałka", "rywala", "diabła", "karła", "orła"
}

NON_VERBS_ON_AL = {
    "kanał", "kryształ", "szał", "wał", "ciał", "dział", "przydział", "rozdział",
    "generał", "admirał", "rywal"
}

def convert_feminine_past_to_masculine(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in NON_VERBS_ON_ALA:
        return None
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
    if v_lower in NON_VERBS_ON_AL:
        return None
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

NON_VERBS_ON_LEM = {
    "ciałem", "działem", "szałem", "kryształem", "materiałem", "kanałem", "finałem",
    "kapitałem", "przedziałem", "udziałem", "rozdziałem", "orłem", "diabłem", "kozłem",
    "osłem", "gardłem", "mydłem", "skrzydłem", "źródłem", "bydłem", "godłem", "wiosłem",
    "żądłem", "ciepłem", "szkłem", "światłem", "kołem", "dołem", "stołem", "popiołem",
    "żywiołem", "czołem", "aniołem", "mułem", "umysłem", "zmysłem", "przemysłem",
    "domysłem", "namysłem", "zamysłem", "rozmysłem", "hasłem", "masłem", "krzesłem",
    "ciosłem", "przęsłem", "pomięsłem"
}

FIRST_PERSON_MASCULINE_IRREGULAR_TO_FEMININE = {
    "poszedłem": "poszłam", "wyszedłem": "wyszłam", "przyszedłem": "przyszłam",
    "odszedłem": "odeszłam", "wszedłem": "weszłam", "przeszedłem": "przeszłam",
    "doszedłem": "doszłam", "zaszedłem": "zaszłam", "zeszłem": "zeszłam",
    "znalazłem": "znalazłam", "mógłbym": "mogłabym", "chciałbym": "chciałabym",
    "wolałbym": "wolałabym", "powinienem": "powinnam", "doniósłbym": "doniosłabym",
    "wziąłem": "wzięłam", "zacząłem": "zaczęłam", "zdjąłem": "zdjęłam",
    "przyjąłem": "przyjęłam", "objąłem": "objęłam", "zająłem": "zajęłam",
    "wziąłbym": "wzięłabym", "zacząłbym": "zaczęłabym", "dopiąłbym": "dopięłabym",
    "odpiąłbym": "odpięłabym", "przypiąłbym": "przypięłabym", "napiąłbym": "napięłabym",
    "stanąłbym": "stanęłabym", "zamknąłbym": "zamknęłabym", "dotknąłbym": "dotknęłabym",
    "machnąłbym": "machnęłabym", "krzyknąłbym": "krzyknęłabym", "zerknąłbym": "zerknęłabym",
    "pomógłbym": "pomogłabym", "poszedłbym": "poszłabym", "przyszedłbym": "przyszłabym",
    "wyszedłbym": "wyszłabym", "odszedłbym": "odeszłabym", "wszedłbym": "weszłabym",
    "padłem": "padłam", "przepadłem": "przepadłam", "odpadłem": "odpadłam",
    "usiadłem": "usiadłam", "wsiadłem": "wsiadłam", "wysiadłem": "wysiadłam",
    "zbiegłem": "zbiegłam", "odbiegłem": "odbiegłam", "uległem": "uległam",
    "mokłem": "mokłam", "zmarzłem": "zmarzłam", "zgasłem": "zgasłam",
}

FIRST_PERSON_FEMININE_IRREGULAR_TO_MASCULINE = {
    "poszłam": "poszedłem", "wyszłam": "wyszedłem", "przyszłam": "przyszedłem",
    "odeszłam": "odszedłem", "weszłam": "wszedłem", "przeszłam": "przeszedłem",
    "doszłam": "doszedłem", "zaszłam": "zaszedłem", "zeszłam": "zeszłem",
    "znalazłam": "znalazłem", "mogłabym": "mógłbym", "chciałabym": "chciałbym",
    "wolałabym": "wolałbym", "powinnam": "powinienem", "doniosłabym": "doniósłbym",
    "wzięłam": "wziąłem", "zaczęłam": "zacząłem", "zdjęłam": "zdjąłem",
    "przyjęłam": "przyjąłem", "objąłem": "objąłem", "zajęłam": "zająłem",
    "wzięłabym": "wziąłbym", "zaczęłabym": "zacząłbym", "dopięłabym": "dopiąłbym",
    "odpięłabym": "odpiąłbym", "przypięłabym": "przypiąłbym", "napięłabym": "napiąłbym",
    "stanęłabym": "stanąłbym", "zamknęłabym": "zamknąłbym", "dotknęłabym": "dotknąłbym",
    "machnęłabym": "machnąłbym", "krzyknęłabym": "krzyknąłbym", "zerknęłabym": "zerknąłbym",
    "pomogłabym": "pomógłbym", "poszłabym": "poszedłbym", "przyszłabym": "przyszedłbym",
    "wyszłabym": "wyszedłbym", "odeszłabym": "odszedłbym", "weszłabym": "wszedłbym",
    "padłam": "padłem", "przepadłam": "przepadłem", "odpadłam": "odpadłem",
    "usiadłam": "usiadłem", "wsiadłam": "wsiadłem", "wysiadłam": "wysiadłem",
    "zbiegłam": "zbiegłem", "odbiegłam": "odbiegłem", "uległam": "uległem",
    "mokłam": "mokłem", "zmarzłam": "zmarzłem", "zgasłam": "zgasłem",
}

def convert_first_person_masculine_to_feminine(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in NON_VERBS_ON_LEM:
        return None
    if v_lower in FIRST_PERSON_MASCULINE_IRREGULAR_TO_FEMININE:
        res = FIRST_PERSON_MASCULINE_IRREGULAR_TO_FEMININE[v_lower]
        return res.capitalize() if verb[0].isupper() else res
    if v_lower.endswith("iałbym"):
        res = v_lower[:-6] + "iałabym"
    elif v_lower.endswith("ąłbym"):
        res = v_lower[:-5] + "ęłabym"
    elif v_lower.endswith("ógłbym"):
        res = v_lower[:-6] + "ogłabym"
    elif v_lower.endswith("ałbym"):
        res = v_lower[:-5] + "ałabym"
    elif v_lower.endswith("iłbym"):
        res = v_lower[:-5] + "iłabym"
    elif v_lower.endswith("yłbym"):
        res = v_lower[:-5] + "yłabym"
    elif v_lower.endswith("ułbym"):
        res = v_lower[:-5] + "ułabym"
    elif v_lower.endswith("łbym"):
        res = v_lower[:-4] + "łabym"
    elif v_lower.endswith("iałem"):
        res = v_lower[:-5] + "iałam"
    elif v_lower.endswith("ałem"):
        res = v_lower[:-4] + "ałam"
    elif v_lower.endswith("iłem"):
        res = v_lower[:-4] + "iłam"
    elif v_lower.endswith("yłem"):
        res = v_lower[:-4] + "yłam"
    elif v_lower.endswith("ułem"):
        res = v_lower[:-4] + "ułam"
    elif v_lower.endswith("ąłem"):
        res = v_lower[:-4] + "ęłam"
    elif v_lower.endswith("adłem"):
        res = v_lower[:-5] + "adłam"
    elif v_lower.endswith("iadłem"):
        res = v_lower[:-6] + "iadłam"
    elif v_lower.endswith("egłem"):
        res = v_lower[:-5] + "egłam"
    elif any(v_lower.endswith(stem) for stem in ("niosłem", "trząsłem", "prząsłem", "pasłem", "rosłem")):
        res = v_lower[:-4] + "słam"
    else:
        return None
    return res.capitalize() if verb[0].isupper() else res

def convert_first_person_feminine_to_masculine(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in {"błam"}:
        return None
    if v_lower in FIRST_PERSON_FEMININE_IRREGULAR_TO_MASCULINE:
        res = FIRST_PERSON_FEMININE_IRREGULAR_TO_MASCULINE[v_lower]
        return res.capitalize() if verb[0].isupper() else res
    if v_lower.endswith("iałabym"):
        res = v_lower[:-7] + "iałbym"
    elif v_lower.endswith("ęłabym"):
        res = v_lower[:-6] + "ąłbym"
    elif v_lower.endswith("ogłabym"):
        res = v_lower[:-7] + "ógłbym"
    elif v_lower.endswith("ałabym"):
        res = v_lower[:-6] + "ałbym"
    elif v_lower.endswith("iłabym"):
        res = v_lower[:-6] + "iłbym"
    elif v_lower.endswith("yłabym"):
        res = v_lower[:-6] + "yłbym"
    elif v_lower.endswith("ułabym"):
        res = v_lower[:-6] + "ułbym"
    elif v_lower.endswith("łabym"):
        res = v_lower[:-5] + "łbym"
    elif v_lower.endswith("iałam"):
        res = v_lower[:-5] + "iałem"
    elif v_lower.endswith("ałam"):
        res = v_lower[:-4] + "ałem"
    elif v_lower.endswith("iłam"):
        res = v_lower[:-4] + "iłem"
    elif v_lower.endswith("yłam"):
        res = v_lower[:-4] + "yłem"
    elif v_lower.endswith("ułam"):
        res = v_lower[:-4] + "ułem"
    elif v_lower.endswith("ęłam"):
        res = v_lower[:-4] + "ąłem"
    elif v_lower.endswith("adłam"):
        res = v_lower[:-5] + "adłem"
    elif v_lower.endswith("iadłam"):
        res = v_lower[:-6] + "iadłem"
    elif v_lower.endswith("egłam"):
        res = v_lower[:-5] + "egłem"
    elif any(v_lower.endswith(stem) for stem in ("niosłam", "trząsłam", "prząsłam", "pasłam", "rosłam")):
        res = v_lower[:-4] + "słem"
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
    "zmuszeni": "zmuszone",
    "zobowiązani": "zobowiązane",
    "szczęśliwi": "szczęśliwe",
    "nieszczęśliwi": "nieszczęśliwe",
    "spokojni": "spokojne",
    "świadomi": "świadome",
    "nieświadomi": "nieświadome",
    "oburzeni": "oburzone",
    "przerażeni": "przerażone",
    "zachwyceni": "zachwycone",
    "wściekli": "wściekłe",
    "głodni": "głodne",
    "spragnieni": "spragnione",
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
    "zmuszone": "zmuszeni",
    "zobowiązane": "zobowiązani",
    "szczęśliwe": "szczęśliwi",
    "nieszczęśliwe": "nieszczęśliwi",
    "spokojne": "spokojni",
    "świadome": "świadomi",
    "nieświadome": "nieświadomi",
    "oburzone": "oburzeni",
    "przerażone": "przerażeni",
    "zachwycone": "zachwyceni",
    "wściekłe": "wściekli",
    "głodne": "głodni",
    "spragnione": "spragnieni",
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

# 1st-person plural irregular past tense mappings (Filar CLXXV - 0.00 PLN)
VIRILE_1ST_PL_IRREGULAR_TO_NONVIRILE: Dict[str, str] = {
    "poszliśmy": "poszłyśmy",
    "przyszliśmy": "przyszłyśmy",
    "wyszliśmy": "wyszłyśmy",
    "odeszliśmy": "odeszłyśmy",
    "weszliśmy": "weszłyśmy",
    "przeszliśmy": "przeszłyśmy",
    "doszliśmy": "doszłyśmy",
    "zeszliśmy": "zeszłyśmy",
    "znaleźliśmy": "znalazłyśmy",
    "odnaleźliśmy": "odnalazłyśmy",
    "mogliśmy": "mogłyśmy",
    "pomogliśmy": "pomogłyśmy",
    "byliśmy": "byłyśmy",
    "widzieliśmy": "widziałyśmy",
    "słyszeliśmy": "słyszałyśmy",
    "chcieliśmy": "chciałyśmy",
    "wiedzieliśmy": "wiedziałyśmy",
    "myśleliśmy": "myślałyśmy",
    "powiedzieliśmy": "powiedziałyśmy",
    "zrozumieliśmy": "zrozumiałyśmy",
    "zapomnieliśmy": "zapomniałyśmy",
    "musieliśmy": "musiałyśmy",
    "mieliśmy": "miałyśmy",
    "wzięliśmy": "wzięłyśmy",
    "zaczęliśmy": "zaczęłyśmy",
    "dopięliśmy": "dopięłyśmy",
    "stanęliśmy": "stanęłyśmy",
    "padliśmy": "padłyśmy",
    "zjedliśmy": "zjadłyśmy",
    "usiedliśmy": "usiadłyśmy",
    "biegliśmy": "biegłyśmy",
    "uciekliśmy": "uciekłyśmy",
}

NONVIRILE_1ST_PL_IRREGULAR_TO_VIRILE: Dict[str, str] = {
    v: k for k, v in VIRILE_1ST_PL_IRREGULAR_TO_NONVIRILE.items()
}

VIRILE_1ST_PL_CONDITIONAL_IRREGULAR_TO_NONVIRILE: Dict[str, str] = {
    "poszlibyśmy": "poszłybyśmy",
    "przyszlibyśmy": "przyszłybyśmy",
    "wyszlibyśmy": "wyszłybyśmy",
    "odeszlibyśmy": "odeszłybyśmy",
    "weszlibyśmy": "weszłybyśmy",
    "przeszlibyśmy": "przeszłybyśmy",
    "znaleźlibyśmy": "znalazłybyśmy",
    "moglibyśmy": "mogłybyśmy",
    "pomoglibyśmy": "pomogłybyśmy",
    "bylibyśmy": "byłybyśmy",
    "widzielibyśmy": "widziałybyśmy",
    "chcielibyśmy": "chciałybyśmy",
    "wolelibyśmy": "wolałybyśmy",
    "wiedzielibyśmy": "wiedziałybyśmy",
    "myślelibyśmy": "myślałybyśmy",
    "musielibyśmy": "musiałybyśmy",
    "mielibyśmy": "miałybyśmy",
    "wzięlibyśmy": "wzięłybyśmy",
    "zaczęlibyśmy": "zaczęłybyśmy",
}

NONVIRILE_1ST_PL_CONDITIONAL_IRREGULAR_TO_VIRILE: Dict[str, str] = {
    v: k for k, v in VIRILE_1ST_PL_CONDITIONAL_IRREGULAR_TO_NONVIRILE.items()
}

def convert_1st_person_plural_virile_to_nonvirile(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in VIRILE_1ST_PL_IRREGULAR_TO_NONVIRILE:
        res = VIRILE_1ST_PL_IRREGULAR_TO_NONVIRILE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("agliśmy"):
        res = v_lower[:-7] + "agłyśmy"
    elif v_lower.endswith("egliśmy"):
        res = v_lower[:-7] + "egłyśmy"
    elif v_lower.endswith("ogliśmy"):
        res = v_lower[:-7] + "ogłyśmy"
    elif v_lower.endswith("szliśmy"):
        res = v_lower[:-7] + "szłyśmy"
    elif v_lower.endswith("ieliśmy"):
        res = v_lower[:-7] + "iałyśmy"
    elif v_lower.endswith("aliśmy"):
        res = v_lower[:-6] + "ałyśmy"
    elif v_lower.endswith("iliśmy"):
        res = v_lower[:-6] + "iłyśmy"
    elif v_lower.endswith("yliśmy"):
        res = v_lower[:-6] + "yłyśmy"
    elif v_lower.endswith("ęliśmy"):
        res = v_lower[:-6] + "ęłyśmy"
    elif v_lower.endswith("liśmy"):
        res = v_lower[:-5] + "łyśmy"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

def convert_1st_person_plural_nonvirile_to_virile(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in NONVIRILE_1ST_PL_IRREGULAR_TO_VIRILE:
        res = NONVIRILE_1ST_PL_IRREGULAR_TO_VIRILE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("agłyśmy"):
        res = v_lower[:-7] + "agliśmy"
    elif v_lower.endswith("egłyśmy"):
        res = v_lower[:-7] + "egliśmy"
    elif v_lower.endswith("ogłyśmy"):
        res = v_lower[:-7] + "ogliśmy"
    elif v_lower.endswith("szłyśmy"):
        res = v_lower[:-7] + "szliśmy"
    elif v_lower.endswith("iałyśmy"):
        res = v_lower[:-7] + "ieliśmy"
    elif v_lower.endswith("ałyśmy"):
        res = v_lower[:-6] + "aliśmy"
    elif v_lower.endswith("iłyśmy"):
        res = v_lower[:-6] + "iliśmy"
    elif v_lower.endswith("yłyśmy"):
        res = v_lower[:-6] + "yliśmy"
    elif v_lower.endswith("ęłyśmy"):
        res = v_lower[:-6] + "ęliśmy"
    elif v_lower.endswith("łyśmy"):
        res = v_lower[:-5] + "liśmy"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

def convert_1st_person_plural_conditional_virile_to_nonvirile(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in VIRILE_1ST_PL_CONDITIONAL_IRREGULAR_TO_NONVIRILE:
        res = VIRILE_1ST_PL_CONDITIONAL_IRREGULAR_TO_NONVIRILE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("alibyśmy"):
        res = v_lower[:-8] + "ałybyśmy"
    elif v_lower.endswith("ilibyśmy"):
        res = v_lower[:-8] + "iłybyśmy"
    elif v_lower.endswith("ylibyśmy"):
        res = v_lower[:-8] + "yłybyśmy"
    elif v_lower.endswith("ielibyśmy"):
        res = v_lower[:-9] + "iałybyśmy"
    elif v_lower.endswith("ęlibyśmy"):
        res = v_lower[:-8] + "ęłybyśmy"
    elif v_lower.endswith("libyśmy"):
        res = v_lower[:-7] + "łybyśmy"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

def convert_1st_person_plural_conditional_nonvirile_to_virile(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in NONVIRILE_1ST_PL_CONDITIONAL_IRREGULAR_TO_VIRILE:
        res = NONVIRILE_1ST_PL_CONDITIONAL_IRREGULAR_TO_VIRILE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("ałybyśmy"):
        res = v_lower[:-8] + "alibyśmy"
    elif v_lower.endswith("iłybyśmy"):
        res = v_lower[:-8] + "ilibyśmy"
    elif v_lower.endswith("yłybyśmy"):
        res = v_lower[:-8] + "ylibyśmy"
    elif v_lower.endswith("iałybyśmy"):
        res = v_lower[:-9] + "ielibyśmy"
    elif v_lower.endswith("ęłybyśmy"):
        res = v_lower[:-8] + "ęlibyśmy"
    elif v_lower.endswith("łybyśmy"):
        res = v_lower[:-7] + "libyśmy"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

MASCULINE_2ND_SG_IRREGULAR_TO_FEMININE: Dict[str, str] = {
    "poszedłeś": "poszłaś",
    "przyszedłeś": "przyszłaś",
    "wyszedłeś": "wyszłaś",
    "odszedłeś": "odeszłaś",
    "wszedłeś": "weszłaś",
    "przeszedłeś": "przeszłaś",
    "doszedłeś": "doszłaś",
    "zszedłeś": "zeszłaś",
    "znalazłeś": "znalazłaś",
    "odnalazłeś": "odnalazłaś",
    "mogłeś": "mogłaś",
    "pomogłeś": "pomogłaś",
    "wziąłeś": "wzięłaś",
    "zacząłeś": "zaczęłaś",
    "wpadłeś": "wpadłaś",
    "upadłeś": "upadłaś",
    "powinieneś": "powinnaś",
    "poszedłbyś": "poszłabyś",
    "przyszedłbyś": "przyszłabyś",
    "wyszedłbyś": "wyszłabyś",
    "odszedłbyś": "odeszłabyś",
    "wszedłbyś": "weszłabyś",
    "mógłbyś": "mogłabyś",
    "pomógłbyś": "pomogłabyś",
    "wziąłbyś": "wzięłabyś",
    "zacząłbyś": "zaczęłabyś",
    "dopiąłbyś": "dopięłabyś",
    "stanąłbyś": "stanęłabyś",
    "padłbyś": "padłabyś",
    "znalazłbyś": "znalazłabyś",
    "chciałbyś": "chciałabyś",
    "wolałbyś": "wolałabyś",
    "doniósłbyś": "doniosłabyś",
}

FEMININE_2ND_SG_IRREGULAR_TO_MASCULINE: Dict[str, str] = {
    "poszłaś": "poszedłeś",
    "przyszłaś": "przyszedłeś",
    "wyszłaś": "wyszedłeś",
    "odeszłaś": "odszedłeś",
    "weszłaś": "wszedłeś",
    "przeszłaś": "przeszedłeś",
    "doszłaś": "doszedłeś",
    "zeszłaś": "zszedłeś",
    "znalazłaś": "znalazłeś",
    "odnalazłaś": "odnalazłeś",
    "mogłaś": "mogłeś",
    "pomogłaś": "pomogłeś",
    "wzięłaś": "wziąłeś",
    "zaczęłaś": "zacząłeś",
    "wpadłaś": "wpadłeś",
    "upadłaś": "upadłeś",
    "powinnaś": "powinieneś",
    "poszłabyś": "poszedłbyś",
    "przyszłabyś": "przyszedłbyś",
    "wyszłabyś": "wyszedłbyś",
    "odeszłabyś": "odszedłbyś",
    "weszłabyś": "wszedłbyś",
    "mogłabyś": "mógłbyś",
    "pomogłabyś": "pomógłbyś",
    "wzięłabyś": "wziąłbyś",
    "zaczęłabyś": "zacząłbyś",
    "dopięłabyś": "dopiąłbyś",
    "stanęłabyś": "stanąłbyś",
    "padłabyś": "padłbyś",
    "znalazłabyś": "znalazłbyś",
    "chciałabyś": "chciałbyś",
    "wolałabyś": "wolałbyś",
    "doniosłabyś": "doniósłbyś",
}

MASCULINE_SG_ADJECTIVES_TO_FEMININE: Dict[str, str] = {
    "pewien": "pewna",
    "pewny": "pewna",
    "gotów": "gotowa",
    "gotowy": "gotowa",
    "sam": "sama",
    "bezpieczny": "bezpieczna",
    "zmęczony": "zmęczona",
    "ciekawy": "ciekawa",
    "zadowolony": "zadowolona",
    "zaskoczony": "zaskoczona",
    "zdziwiony": "zdziwiona",
    "spokojny": "spokojna",
    "szczęśliwy": "szczęśliwa",
    "wzburzony": "wzburzona",
    "zdenerwowany": "zdenerwowana",
    "zmartwiony": "zmartwiona",
    "przygnębiony": "przygnębiona",
    "wściekły": "wściekła",
    "smutny": "smutna",
    "samotny": "samotna",
    "zły": "zła",
    "chory": "chora",
    "chętny": "chętna",
}

FEMININE_SG_ADJECTIVES_TO_MASCULINE: Dict[str, str] = {
    "pewna": "pewien",
    "gotowa": "gotowy",
    "sama": "sam",
    "bezpieczna": "bezpieczny",
    "zmęczona": "zmęczony",
    "ciekawa": "ciekawy",
    "zadowolona": "zadowolony",
    "zaskoczona": "zaskoczony",
    "zdziwiona": "zdziwiony",
    "spokojna": "spokojny",
    "szczęśliwa": "szczęśliwy",
    "wzburzona": "wzburzony",
    "zdenerwowana": "zdenerwowany",
    "zmartwiona": "zmartwiony",
    "przygnębiona": "przygnębiony",
    "wściekła": "wściekły",
    "smutna": "smutny",
    "samotna": "samotny",
    "zła": "zły",
    "chora": "chory",
    "chętna": "chętny",
}

def convert_2nd_person_masculine_to_feminine(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in MASCULINE_2ND_SG_IRREGULAR_TO_FEMININE:
        res = MASCULINE_2ND_SG_IRREGULAR_TO_FEMININE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("iałbyś"):
        res = v_lower[:-6] + "iałabyś"
    elif v_lower.endswith("ąłbyś"):
        res = v_lower[:-5] + "ęłabyś"
    elif v_lower.endswith("ógłbyś"):
        res = v_lower[:-6] + "ogłabyś"
    elif v_lower.endswith("ałbyś"):
        res = v_lower[:-5] + "ałabyś"
    elif v_lower.endswith("iłbyś"):
        res = v_lower[:-5] + "iłabyś"
    elif v_lower.endswith("yłbyś"):
        res = v_lower[:-5] + "yłabyś"
    elif v_lower.endswith("ułbyś"):
        res = v_lower[:-5] + "ułabyś"
    elif v_lower.endswith("łbyś"):
        res = v_lower[:-4] + "łabyś"
    elif v_lower.endswith("ąłeś"):
        res = v_lower[:-4] + "ęłaś"
    elif v_lower.endswith("adłeś"):
        res = v_lower[:-5] + "adłaś"
    elif v_lower.endswith("iadłeś"):
        res = v_lower[:-6] + "iadłaś"
    elif v_lower.endswith("egłeś"):
        res = v_lower[:-5] + "egłaś"
    elif v_lower.endswith("łeś"):
        res = v_lower[:-3] + "łaś"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

def convert_2nd_person_feminine_to_masculine(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in FEMININE_2ND_SG_IRREGULAR_TO_MASCULINE:
        res = FEMININE_2ND_SG_IRREGULAR_TO_MASCULINE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("iałabyś"):
        res = v_lower[:-7] + "iałbyś"
    elif v_lower.endswith("ęłabyś"):
        res = v_lower[:-6] + "ąłbyś"
    elif v_lower.endswith("ogłabyś"):
        res = v_lower[:-7] + "ógłbyś"
    elif v_lower.endswith("ałabyś"):
        res = v_lower[:-6] + "ałbyś"
    elif v_lower.endswith("iłabyś"):
        res = v_lower[:-6] + "iłbyś"
    elif v_lower.endswith("yłabyś"):
        res = v_lower[:-6] + "yłbyś"
    elif v_lower.endswith("ułabyś"):
        res = v_lower[:-6] + "ułbyś"
    elif v_lower.endswith("łabyś"):
        res = v_lower[:-5] + "łbyś"
    elif v_lower.endswith("ęłaś"):
        res = v_lower[:-4] + "ąłeś"
    elif v_lower.endswith("adłaś"):
        res = v_lower[:-5] + "adłeś"
    elif v_lower.endswith("iadłaś"):
        res = v_lower[:-6] + "iadłeś"
    elif v_lower.endswith("egłaś"):
        res = v_lower[:-5] + "egłeś"
    elif v_lower.endswith("łaś"):
        res = v_lower[:-3] + "łeś"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

POSSESSIVE_GOVERNING_NOUNS_PATTERN = (
    r"(?:sekret|sekretu|sekretom|sekrety|sekretów|"
    r"tajemnic|tajemnica|tajemnice|tajemnicy|tajemnicom|tajemnicą|tajemnicę|"
    r"miecz|miecza|mieczem|mieczu|miecze|mieczom|mieczami|"
    r"oręż|oręża|orężem|"
    r"zbroj|zbroja|zbroi|zbroję|zbroją|"
    r"rozkaz|rozkazu|rozkazem|rozkazy|rozkazów|rozkazom|"
    r"wol[aieyęą]|moc|mocy|mocą|potęg[aieyęą]|magi[aieyęą]|"
    r"śmierć|śmierci|śmiercią|życi[aeeęu]|dusz[aieyęą]|ciał[aoeuy]|kr[ew|wi]|"
    r"obecnoś[ćci]|powrót|powrotu|powrotem|zdrad[aieyęą]|zemst[aieyęą]|gniew|gniewu|gniewem|"
    r"pomoc|pomocy|pomocą|łask[aieyęą]|cień|cienia|cieniem|"
    r"herb|herbu|herbem|herby|herbów|twierdz[aieyęą]|zamek|zamku|zamkiem|zamki|zamków|"
    r"grób|grobu|grobem|groby|grobów|świątyni[aieyęą]|"
    r"armi[aieyęą]|armii|armiom|wojsk[aoeuy]|"
    r"słudzy|sług|sług[aieyęą]|ludzi|ludźmi|ludziom|zwolennik|zwolennika|zwolennicy|zwolenników|"
    r"syn|syna|synowi|synem|synowie|synów|córk[aieyęą]|córek|córkom|"
    r"brat|brata|bratu|bratem|bracia|braci|braciom|siostr[aieyęą]|sióstr|siostrom|"
    r"ojciec|ojca|ojcu|ojcem|matk[aieyęą]|matek|matkom|"
    r"żon[aieyęą]|żon|żonom|mąż|męża|mężowi|mężem|"
    r"pana|panu|panem|panowie|panów|władc[aeyęą]|władców|"
    r"mistrza|mistrzowi|mistrzem|mistrzowie|mistrzów|"
    r"uczeń|ucznia|uczniowi|uczniem|uczniowie|uczniów|"
    r"przyjaciel|przyjaciela|przyjacielowi|przyjacielem|przyjaciele|przyjaciół|"
    r"wróg|wroga|wrogowi|wrogiem|wrogowie|wrogów|"
    r"los|losu|losem|losy|losów|imię|imienia|imieniem|imiona|imion|"
    r"głos|głosu|głosem|głosy|głosów|wzrok|wzroku|wzrokiem|"
    r"oczy|oczach|oczami|oczu|dłonie|dłoni|dłoniach|dłońmi|ręce|rąk|rękach|rękami)"
)

GENITIVE_GOVERNING_VERBS_PATTERN = (
    r"(?:szukam|szukasz|szuka|szukamy|szukacie|szukają|szukałem|szukałam|szukał|szukała|szukali|szukały|"
    r"potrzebuj[ęesz]|potrzebujemy|potrzebujecie|potrzebują|potrzebowałem|potrzebowałam|potrzebował|potrzebowała|potrzebowali|"
    r"pilnuj|pilnujesz|pilnuje|pilnujemy|pilnujecie|pilnują|pilnowałem|pilnowałam|pilnował|pilnowała|pilnowali|"
    r"broń|bronisz|broni|bronimy|bronicie|bronią|broniłem|broniłam|bronił|broniła|bronili|"
    r"unikaj|unikasz|unika|unikamy|unikacie|unikają|unikałem|unikałam|unikał|unikała|unikali|"
    r"boję\s+się|boisz\s+się|boi\s+się|boimy\s+się|boicie\s+się|boją\s+się|bałem\s+się|bałam\s+się|bał\s+się|bała\s+się|bali\s+się|"
    r"nie\s+ma|nie\s+widzę|nie\s+widzisz|nie\s+widzi|nie\s+widziałem|nie\s+widziałam|nie\s+widział|nie\s+widziała|nie\s+widzieli|"
    r"nie\s+znam|nie\s+znasz|nie\s+zna|nie\s+znałem|nie\s+znałam|nie\s+znał|nie\s+znała|nie\s+znali|"
    r"nie\s+pamiętam|nie\s+pamiętasz|nie\s+pamięta|nie\s+pamiętałem|nie\s+pamiętałam|nie\s+pamiętał|nie\s+pamiętała|nie\s+pamiętali|"
    r"nie\s+słyszę|nie\s+słyszysz|nie\s+słyszy|nie\s+słyszałem|nie\s+słyszałam|nie\s+słyszał|nie\s+słyszała|nie\s+słyszeli)"
)

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
        line_addressees: Optional[Dict[int, str]] = None,
        source_subs: Optional[Any] = None,
        line_speakers: Optional[Dict[int, str]] = None,
        whisper_transcriptions: Optional[Dict[int, str]] = None
    ) -> Tuple[Any, List[str]]:
        if not subs or not hasattr(subs, "events") or not subs.events:
            return subs, []

        fixes: List[str] = []
        events = subs.events
        orig_speakers: Dict[int, str] = {
            idx_ev: (getattr(ev_item, "name", "") or getattr(ev_item, "actor", "") or getattr(ev_item, "speaker", "") or (line_speakers.get(idx_ev) if line_speakers else "") or "")
            for idx_ev, ev_item in enumerate(events)
        }

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

        # 0. Inherent Lexical Gender Pre-pass from Event Names (Filar CLXIX)
        for i_ev, ev in enumerate(events):
            ev_spk = getattr(ev, "name", None) or getattr(ev, "actor", None) or getattr(ev, "speaker", None)
            if ev_spk and is_generic_actor_or_category(str(ev_spk)):
                ev.name = ""
                ev_spk = None
            if (not ev_spk or not str(ev_spk).strip()) and line_speakers and i_ev in line_speakers:
                cand_lspk = line_speakers[i_ev]
                if cand_lspk and not is_generic_actor_or_category(str(cand_lspk)):
                    ev_spk = cand_lspk
            if not ev_spk or is_generic_actor_or_category(str(ev_spk)):
                continue
            clean_spk = extract_clean_speaker_name(ev_spk).lower()
            spk_norm = str(ev_spk).strip().lower()
            if is_generic_actor_or_category(clean_spk):
                continue
            tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", clean_spk))
            if clean_spk in INHERENT_FEMALE_NOUNS or any(t in INHERENT_FEMALE_NOUNS for t in tokens):
                char_gender_map[clean_spk] = "FEMALE"
                char_gender_map[spk_norm] = "FEMALE"
            elif clean_spk in INHERENT_MALE_NOUNS or any(t in INHERENT_MALE_NOUNS for t in tokens):
                char_gender_map[clean_spk] = "MALE"
                char_gender_map[spk_norm] = "MALE"

        # 0a. From Character Registry
        if character_registry:
            for cname, cdesc in character_registry.items():
                cd_lower = str(cdesc).lower()
                cd_sanitized = re.sub(r"zakaz\s+form\s+(?:żeńsk|męsk)[a-ząćęłńóśźż]*", "", cd_lower)
                gen = None
                if any(k in cd_sanitized for k in ["male", "mężczyzna", "chłopak", "męsk"]):
                    gen = "MALE"
                elif any(k in cd_sanitized for k in FEMALE_ROLE_KEYWORDS):
                    gen = "FEMALE"
                if gen:
                    clean_c = extract_clean_speaker_name(cname).lower()
                    if clean_c:
                        char_gender_map[clean_c] = gen
                    for p in re.split(r"[/,]", cname):
                        clean_p = extract_clean_speaker_name(p).strip()
                        if len(clean_p) >= 3:
                            char_gender_map[clean_p.lower()] = gen

        # 0b. From Series Bible
        if series_bible and hasattr(series_bible, "data"):
            bible_chars = series_bible.data.get("characters", {})
            for c_key, c_val in bible_chars.items():
                if "->" in c_key or "/" in c_key or "," in c_key:
                    continue  # Relationships handled separately, avoid poisoning listener gender
                desc_str = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
                desc_lower = desc_str.lower()
                desc_sanitized = re.sub(r"zakaz\s+form\s+(?:żeńsk|męsk)[a-ząćęłńóśźż]*", "", desc_lower)
                gen = None
                if any(k in desc_sanitized for k in ["male", "mężczyzna", "chłopak", "męsk"]):
                    gen = "MALE"
                elif any(k in desc_sanitized for k in FEMALE_ROLE_KEYWORDS):
                    gen = "FEMALE"
                if gen:
                    clean_ckey = extract_clean_speaker_name(c_key).strip().lower()
                    if clean_ckey and len(clean_ckey) >= 3:
                        char_gender_map[clean_ckey] = gen
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
            if is_generic_actor_or_category(str(ev.name)):
                continue
            spk_norm = ev.name.strip().lower()
            spk_clean = extract_clean_speaker_name(ev.name).lower()
            if not spk_clean or len(spk_clean) < 3 or is_generic_actor_or_category(spk_clean):
                continue
            clean_t = re.sub(r"\{[^\}]*\}", "", ev.text).lower()

            if re.search(r"\b(powinienem|mógłbym|chciałbym|wolałbym|poszedłem|zrobiłem|byłem|widziałem|wiedziałem|pomyślałem|mówiłem|czekałem|wróciłem|znalazłem|przyszedłem|odszedłem|wyszedłem|wszedłem|zrozumiałem|myślałem|słyszałem|czułem|obiecałem|postanowiłem|zraniłem|skrzywdziłem)\b", clean_t):
                speaker_male_votes[spk_clean] = speaker_male_votes.get(spk_clean, 0) + 1
                speaker_male_votes[spk_norm] = speaker_male_votes.get(spk_norm, 0) + 1

            if re.search(r"\b(powinnam|mogłabym|chciałabym|wolałabym|poszłam|zrobiłam|byłam|widziałam|wiedziałam|pomyślałam|mówiłam|czekałam|wróciłam|znalazłam|przyszłam|odeszłam|wyszłam|weszłam|zrozumiałam|myślałam|słyszałam|czułam|obiecałam|postanowiłam|zraniłam|skrzywdziłam)\b", clean_t):
                speaker_female_votes[spk_clean] = speaker_female_votes.get(spk_clean, 0) + 1
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

        # 0f. 7-Case Character Declension Matrix from Series Bible / Registry / Actors
        from series_memory import generate_polish_name_declension
        character_declensions: Dict[str, Dict[str, str]] = {}
        if series_bible and hasattr(series_bible, "data") and "declensions" in series_bible.data:
            for k, val in series_bible.data["declensions"].items():
                if k and len(k) >= 3 and not any(ch in k for ch in "->/"):
                    if isinstance(val, dict) and "M" in val and "W" in val:
                        character_declensions[k] = val
                    else:
                        g = char_gender_map.get(k.lower(), "UNKNOWN")
                        if g == "UNKNOWN" and " " in k:
                            for part in k.split():
                                if part.lower() in char_gender_map and char_gender_map[part.lower()] != "UNKNOWN":
                                    g = char_gender_map[part.lower()]
                                    break
                        character_declensions[k] = generate_polish_name_declension(k, g)

        if character_registry:
            for k in character_registry.keys():
                for p in re.split(r"[/,]", k):
                    clean_p = p.strip()
                    if len(clean_p) >= 3 and not any(clean_p.lower() == existing_k.lower() for existing_k in character_declensions.keys()):
                        g = char_gender_map.get(clean_p.lower(), "UNKNOWN")
                        character_declensions[clean_p] = generate_polish_name_declension(clean_p, g)

        # Also populate from candidate names / event actors if not present
        NON_NAME_ACTORS = {
            "wszyscy", "ktos", "ktoś", "glos", "głos", "narrator", "napis", "napisy",
            "tytul", "tytuł", "tlumaczenie", "tłumaczenie", "kobieta", "mezczyzna",
            "mężczyzna", "chlopak", "chłopak", "dziewczyna", "tlum", "tłum", "strażnik",
            "straznik", "zolnierz", "żołnierz", "main", "default", "alt", "sign", "signs",
            "ziemia", "ziemią", "ziemi", "ziemię", "ziemiom", "ziemiach", "słońce", "słońca", "słońcu", "słońcem",
            "księżyc", "księżyca", "księżycu", "księżycem", "świat", "świata", "światu", "światem", "świecie",
            "niebo", "nieba", "niebios", "niebiosach", "bóg", "boga", "bogu", "bogiem", "bogowie", "bogów",
            "japonia", "japonii", "tokio", "polska", "polski", "polsce", "polskę", "polską", "europa", "europy",
            "motomachi", "mihara", "ohshima", "ōshima", "shiman", "wyspa", "wyspy", "wyspie", "wyspą", "morze", "morza", "morzem",
            "hiden", "elbe", "solsein", "boelate", "eslinn", "toah", "elds", "shinano", "suwa", "kamakura", "kioto",
            "esleburg", "hyderat", "elden", "luna", "dunn", "złudzeń", "złudzenia", "złudzenie", "płomiennego", "żaru", "początku", "kuźni", "świątynia",
            "imperium", "cesarstwo", "królestwo", "księstwo", "państwo", "republika", "federacja", "unia", "senat", "rada", "armia", "zakon", "klan", "ród", "dynastia", "plemię", "sojusz", "muzeum", "liceum", "technikum", "akwarium", "koloseum", "seminarium"
        }
        if series_bible and hasattr(series_bible, "data") and "glossary" in series_bible.data:
            for g_k, g_v in series_bible.data["glossary"].items():
                g_str = (str(g_k) + " " + str(g_v)).lower()
                if any(kw in g_str for kw in ["kraina", "królestwo", "lokacja", "kopalnia", "akademia", "chram", "świątynia", "szkoła", "miasto", "rzeka", "góra", "zamek", "twierdza", "imperium", "państwo"]):
                    for w in re.findall(r"\b[a-ząćęłńóśźż]{3,}\b", g_str):
                        NON_NAME_ACTORS.add(w)

        all_candidate_chars = set()
        for k in candidate_names:
            all_candidate_chars.add(k.strip())
        if custom_glossary:
            for k, v in custom_glossary.items():
                for name_src in [v]:
                    for token in re.findall(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}\b", name_src):
                        tok_l = token.lower()
                        if tok_l not in NON_NAME_ACTORS and tok_l not in ETHNONYMS_AND_COLLECTIVES and not tok_l.endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "em", "iem", "owi", "eń", "ań", "ów", "ich", "ych", "ość", "ości")) and not tok_l.endswith("um"):
                            all_candidate_chars.add(token)
                            candidate_names.add(tok_l)

        # Build collection of all known declined forms of existing characters to avoid creating phantom nominatives
        existing_decl_forms: Set[str] = set()
        for c_decl in character_declensions.values():
            if isinstance(c_decl, dict):
                for val in c_decl.values():
                    if isinstance(val, str):
                        for part in val.split("/"):
                            cl_part = part.strip().lower()
                            if cl_part and len(cl_part) >= 3:
                                existing_decl_forms.add(cl_part)

        for ev in events:
            ev_act = getattr(ev, "name", None) or getattr(ev, "actor", None)
            if ev_act and str(ev_act).strip():
                act_clean = str(ev_act).strip()
                if len(act_clean) >= 3 and not any(ch in act_clean for ch in "{}[]():;"):
                    all_candidate_chars.add(act_clean)
            clean_ev = re.sub(r"\{[^\}]*\}", "", ev.text or "")
            for m_prop in re.finditer(r"\b(?:o|do|dla|u|z|ze|od|przed|nad|pod|przy|przez|za|i|oraz)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})\b", clean_ev):
                prop_tok = m_prop.group(1)
                tok_lower = prop_tok.lower()
                if tok_lower in ETHNONYMS_AND_COLLECTIVES or (series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(prop_tok)):
                    continue
                if tok_lower not in NON_NAME_ACTORS and tok_lower not in {
                    "pan", "pani", "niego", "mnie", "ciebie", "nas", "was", "nich", "tego", "tamto", "jeden", "sama", "samo", "sami", "same", "wszystko", "wszyscy", "wszystkich", "cały", "cała", "całe"
                }:
                    # Odrzuć formy już odmienione przypadków zależnych oraz znane formy zależne istniejących postaci
                    if tok_lower in existing_decl_forms:
                        continue
                    if any(tok_lower.startswith(k.lower()) and len(tok_lower) > len(k) for k in character_declensions.keys()):
                        continue
                    if not tok_lower.endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "em", "iem", "owi", "eń", "ań", "ów", "ich", "ych", "ość", "ości")) and not tok_lower.endswith("um"):
                        all_candidate_chars.add(prop_tok)
                        candidate_names.add(tok_lower)

        for cand in all_candidate_chars:
            if not cand or len(cand) < 3 or cand.lower() in NON_NAME_ACTORS or cand.lower() in ETHNONYMS_AND_COLLECTIVES:
                continue
            if series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(cand):
                continue
            if cand.lower().endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "em", "iem", "owi", "eń", "ań", "ów", "ich", "ych", "ość", "ości")) or cand.lower().endswith("um"):
                continue
            if cand.lower() in existing_decl_forms:
                continue
            if any(cand.lower().startswith(k.lower()) and len(cand) > len(k) for k in character_declensions.keys()):
                continue
            cand_proper = cand.capitalize()
            if not any(cand.lower() == existing_k.lower() for existing_k in character_declensions.keys()):
                cand_g = char_gender_map.get(cand.lower(), "UNKNOWN")
                character_declensions[cand_proper] = generate_polish_name_declension(cand_proper, cand_g)

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

        # Track speaker formality toward candidate characters for T-V vocative harmonization (Anti-Sama-Drop)
        speaker_formal_char: Dict[Tuple[str, str], int] = {}
        speaker_informal_to_char: Dict[Tuple[str, str], int] = {}
        for ev in events:
            if not ev.text or not ev.text.strip():
                continue
            spk = (getattr(ev, "name", "") or "").strip().lower()
            if not spk:
                continue
            clean_t = re.sub(r"\{[^\}]*\}", "", ev.text)
            clean_t = re.sub(r"\\[Nnh]", " ", clean_t)
            for c_name in candidate_names:
                if any(ch in c_name for ch in "{}[]():;->/"):
                    continue
                stem_len = max(3, len(c_name) - 2)
                stem = c_name[:stem_len]
                stem_esc = re.escape(stem)
                if re.search(rf"\b{stem_esc}[a-ząćęłńóśźż]*\b", clean_t, re.IGNORECASE):
                    # Check formal address
                    if re.search(rf"\b(?:panie|pan|pana|panu|panem)\s+{stem_esc}[a-ząćęłńóśźż]*\b", clean_t, re.IGNORECASE) or \
                       re.search(r"\b(?:ma pan|niech pan|pan szuka|pan pamięta|pan prosił|pan wie|pan czuje|źle się pan|smakuje panu)\b", clean_t, re.IGNORECASE):
                        speaker_formal_char[(spk, c_name)] = speaker_formal_char.get((spk, c_name), 0) + 1
                    # Check informal address
                    if re.search(r"\b(?:wiesz|widzisz|myślisz|pamiętasz|rozumiesz|mówisz|robisz|chcesz|możesz|masz|musisz|znasz|słyszysz|jesteś)\b|\b[a-ząćęłńóśźż]+(?:łeś|łaś)\b", clean_t, re.IGNORECASE):
                        if not re.search(r"\b(?:pan|pani|pana|panu|panie)\b", clean_t, re.IGNORECASE):
                            speaker_informal_to_char[(spk, c_name)] = speaker_informal_to_char.get((spk, c_name), 0) + 1

        # Purge non-character entities and ethnonyms from character_declensions
        if character_declensions:
            for bad_k in list(character_declensions.keys()):
                bad_k_l = bad_k.lower()
                if bad_k_l in NON_NAME_ACTORS or bad_k_l in ETHNONYMS_AND_COLLECTIVES or (series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(bad_k)):
                    del character_declensions[bad_k]

        # Precompile character declension and vocative patterns once for high-throughput execution
        compiled_decl_rules = []
        if character_declensions:
            for c_name, c_decl in list(character_declensions.items()):
                c_name_l = c_name.lower()
                if not c_name or len(c_name) < 3 or c_name_l in NON_NAME_ACTORS or c_name_l in ETHNONYMS_AND_COLLECTIVES or not c_decl or not isinstance(c_decl, dict):
                    continue
                if series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(c_name):
                    continue
                m_form = c_decl.get("M", c_name)
                if not m_form or m_form.lower() in NON_NAME_ACTORS or m_form.lower() in ETHNONYMS_AND_COLLECTIVES:
                    continue
                stem_len = len(c_name) - 1 if c_name.endswith("a") else max(3, len(c_name) - 2)
                c_stem = c_name[:stem_len]

                rule = {
                    "name": c_name,
                    "m_form": m_form,
                    "c_stem": c_stem,
                    "m_lower": m_form.lower(),
                    "stem_lower": c_stem.lower()
                }

                n_form = c_decl.get("N")
                if n_form and n_form != m_form:
                    rule["n_form"] = n_form
                    rule["re_n"] = re.compile(rf"\b(z|ze|przed|nad|pod|za|między)(\s+|\\(?:[Nnh])+)+({re.escape(m_form)})\b", re.IGNORECASE)

                d_form = c_decl.get("D")
                if d_form and d_form != m_form:
                    rule["d_form"] = d_form
                    rule["re_prep_d"] = re.compile(rf"\b(do|dla|od|u|bez|koło|obok|wzdłuż|podczas|zamiast|oprócz|wokół|wobec)(\s+|\\(?:[Nnh])+)+({re.escape(m_form)}|{re.escape(c_stem)}[a-ząćęłńóśźż]*)\b", re.IGNORECASE)
                    rule["re_pos_d"] = re.compile(rf"\b({POSSESSIVE_GOVERNING_NOUNS_PATTERN}|{GENITIVE_GOVERNING_VERBS_PATTERN})((?:(?:\s+|\\(?:[Nnh])+)+(?:samego|tamtego|tego))?(?:\s+|\\(?:[Nnh])+)+)({re.escape(m_form)})\b", re.IGNORECASE)

                c_form = c_decl.get("C")
                if c_form and c_form != m_form:
                    rule["c_form"] = c_form
                    rule["re_c"] = re.compile(rf"\b(ku|przeciw|przeciwko|dzięki|wbrew)(\s+|\\(?:[Nnh])+)+({re.escape(m_form)})\b", re.IGNORECASE)

                ms_form = c_decl.get("Ms")
                if ms_form and ms_form != m_form:
                    rule["ms_form"] = ms_form
                    rule["re_ms"] = re.compile(rf"\b(o|przy)(\s+|\\(?:[Nnh])+)+({re.escape(m_form)})\b", re.IGNORECASE)

                b_form = c_decl.get("B")
                if b_form and b_form.lower() != m_form.lower():
                    rule["b_form"] = b_form

                w_form = c_decl.get("W")
                if w_form and w_form.lower() != m_form.lower():
                    rule["w_form"] = w_form
                    rule["re_end_voc"] = re.compile(rf"(,\s*)({re.escape(m_form)})\s*([\.!\?…]+)(?=\s+[A-ZĄĆĘŁŃÓŚŹŻ]|\s*\\N|\s*$)", re.IGNORECASE)
                    rule["re_intro_voc"] = re.compile(rf"((?:^|[^\w]|\\[Nnh])(?:[Hh]ej|[Ee]j|[Aa]\s+więc|[Aa]\s+zatem|[Ss]łuchaj|[Pp]atrz|[Ss]pójrz|[Dd]obra|[Aa]le|[Nn]o)\s*,\s*)({re.escape(m_form)})\s*([,\.!\?…]+|\s*\\N|$)", re.IGNORECASE)
                    rule["re_lead_voc"] = re.compile(rf"(^|\\[Nnh])({re.escape(m_form)})\s*,\s*(?=[a-ząćęłńóśźż]*(?:aj|ajcie|yj|yjcie|ij|ijcie|my|myśl|zrób|patrz|słuchaj|uważaj|chodź|czekaj|stój|pospiesz|szybciej|nie\s+|daj|powiedz)\b)", re.IGNORECASE)

                # Check for indeclinable female names ending in consonant (e.g. Khulan, Chulan, Carmen, Ines)
                char_gender = char_gender_map.get(c_name.lower()) or char_gender_map.get(m_form.lower()) or c_decl.get("gender")
                is_fem = char_gender and any(w in str(char_gender).lower() for w in ["female", "kobieta", "żeński", "girl"])
                if is_fem and not m_form.lower().endswith("a"):
                    rule["re_illegal_fem_masc_a"] = re.compile(rf"\b({re.escape(m_form)})a\b", re.IGNORECASE)

                compiled_decl_rules.append(rule)

        # 0g. Scene Partitioning & Anonymous Diarization Pre-pass (0.00 PLN)
        # Groups events into scene blocks based on temporal gap (>= 3200ms) or scene boundary.
        # Resolves scene-level gender exclusivity when individual events have empty ev.name.
        event_scene_gender: Dict[int, str] = {}  # event_idx -> 'FEMALE' | 'MALE'

        scene_blocks: List[List[int]] = []
        cur_scene: List[int] = []
        for idx_ev, ev_item in enumerate(events):
            if not cur_scene:
                cur_scene.append(idx_ev)
            else:
                prev_ev = events[cur_scene[-1]]
                gap = ev_item.start - prev_ev.end
                if gap >= 10000 or (ev_item.start - events[cur_scene[0]].start > 180000):
                    scene_blocks.append(cur_scene)
                    cur_scene = [idx_ev]
                else:
                    cur_scene.append(idx_ev)
        if cur_scene:
            scene_blocks.append(cur_scene)

        for s_block in scene_blocks:
            scene_spks = set()
            scene_texts: List[str] = []
            for s_idx in s_block:
                s_ev = events[s_idx]
                s_act = getattr(s_ev, "name", None) or getattr(s_ev, "actor", None) or (line_speakers.get(s_idx) if line_speakers else None)
                if s_act and not is_generic_actor_or_category(str(s_act)):
                    cl_act = extract_clean_speaker_name(str(s_act))
                    if len(cl_act) >= 3:
                        scene_spks.add(cl_act)
                if s_ev.text:
                    cl_t = re.sub(r"\{[^\}]*\}", "", s_ev.text).strip()
                    if cl_t:
                        scene_texts.append(cl_t)

            s_gender = None
            # 1. If named speakers are present in the scene (require at least 2 distinct speakers)
            if len(scene_spks) >= 2:
                if series_bible and hasattr(series_bible, "is_all_female_cast"):
                    if series_bible.is_all_female_cast(scene_spks):
                        s_gender = "FEMALE"
                    elif series_bible.is_all_male_cast(scene_spks):
                        s_gender = "MALE"
                if not s_gender:
                    all_f = all(char_gender_map.get(s.lower()) == "FEMALE" for s in scene_spks)
                    all_m = all(char_gender_map.get(s.lower()) == "MALE" for s in scene_spks)
                    if all_f:
                        s_gender = "FEMALE"
                    elif all_m:
                        s_gender = "MALE"

            # 2. If a female group speaker (e.g. 'grupa_kobiet', 'zakonnice') is in the scene
            if not s_gender and series_bible and hasattr(series_bible, "is_female_group_speaker"):
                if any(series_bible.is_female_group_speaker(orig_speakers.get(s_idx, "")) for s_idx in s_block):
                    s_gender = "FEMALE"

            # 3. If no named speakers (all ev.name blank in scene), infer from textual content / plot anchors
            if not s_gender and series_bible and hasattr(series_bible, "infer_scene_cast_from_text"):
                scene_whisper = [whisper_transcriptions.get(s_idx + 1, "") for s_idx in s_block if whisper_transcriptions]
                _, inferred_g = series_bible.infer_scene_cast_from_text(scene_texts, whisper_texts=scene_whisper)
                if inferred_g:
                    s_gender = inferred_g

            # 3. Disqualify scene exclusivity if any line has explicit opposite addressee
            if s_gender:
                has_opp_addr = False
                for s_idx in s_block:
                    s_ev = events[s_idx]
                    r_addr = getattr(s_ev, "addressee", None) or (line_addressees.get(s_idx) if line_addressees else None)
                    if r_addr:
                        r_lower = str(r_addr).lower()
                        if s_gender == "FEMALE" and any(w in r_lower for w in ["mężczyzna", "male", "chłopak"]):
                            # Check if male addressee was derived from an audited contaminated tag (e.g. 'Ögedei (Mężczyzna)')
                            cand_addr_name = re.sub(r"\s*\(.*?\)", "", str(r_addr)).strip()
                            is_cont_addr = False
                            if series_bible and hasattr(series_bible, "audit_speaker_metadata_against_audio") and cand_addr_name:
                                _, is_cont_addr = series_bible.audit_speaker_metadata_against_audio(cand_addr_name, scene_gender=s_gender)
                            if not is_cont_addr:
                                has_opp_addr = True
                                break
                        elif s_gender == "MALE" and any(w in r_lower for w in ["kobieta", "female", "dziewczyn"]):
                            has_opp_addr = True
                            break
                if not has_opp_addr:
                    for s_idx in s_block:
                        event_scene_gender[s_idx] = s_gender

        for i, ev in enumerate(events):
            if not ev.text or not ev.text.strip():
                continue

            # Sanitize inverted / negative duration timestamps (start >= end)
            if ev.start >= ev.end:
                old_start = ev.start
                prev_start = events[i-1].start if i > 0 else 0
                prev_end = events[i-1].end if i > 0 else 0
                fixed_ts = False
                for m_shift in [60000, 120000, 300000, 600000, 1200000, 1800000, 3600000]:
                    cand_start = ev.start - m_shift
                    if (cand_start >= prev_start) and (0 < ev.end - cand_start <= 15000):
                        ev.start = cand_start
                        fixes.append(f"[Episode Quality Gate - Timestamp Sanitization] Linia #{i+1}: skorygowano odwrócony znacznik czasu ({old_start}ms -> {ev.start}ms)")
                        fixed_ts = True
                        break
                if not fixed_ts and ev.start >= ev.end:
                    char_count = len(re.sub(r"\{[^\}]*\}", "", ev.text).strip())
                    est_dur = min(max(1500, char_count * 60), 5000)
                    ev.start = max(prev_start, ev.end - est_dur)
                    fixes.append(f"[Episode Quality Gate - Timestamp Sanitization] Linia #{i+1}: skorygowano ujemny czas trwania napisu na {ev.start}ms - {ev.end}ms")

            text_before = ev.text

            # Sanitize corrupted escaped backslashes inside ASS override tags (e.g. {\\b1} -> {\b1})
            if r"\\" in ev.text:
                old_tag_text = ev.text
                ev.text = re.sub(r"\\\\([bibupancfqskKFtrposmvefadorgcxylh0-9\\])", r"\\\1", ev.text)
                if ev.text != old_tag_text:
                    fixes.append(f"[Episode Quality Gate - Tag Sanitization] Linia #{i+1}: naprawiono uszkodzony znacznik ASS (podwójny backslash)")

            # Numerical Sanity Gate (Filar CLXXI): Ensure numbers from source_en are preserved without mutation
            source_en = getattr(ev, "source_en", "") or ""
            if source_en:
                en_digits = re.findall(r"\b\d+\b", source_en)
                clean_pl_digits = re.findall(r"\b\d+\b", re.sub(r"\{[^\}]*\}", "", ev.text))
                for num_str in en_digits:
                    if num_str not in clean_pl_digits:
                        mutated = [p for p in clean_pl_digits if (p in num_str or num_str in p) and p != num_str]
                        if mutated:
                            fixes.append(f"[Episode Quality Gate - Filar CLXXI Zgodność Liczebników] Linia #{i+1}: wykryto mutację liczby {num_str} na {mutated[0]}")

            # Identify if current event is a sign/title (e.g. style has "Sign", "Title", or contains \pos / \an8)
            ev_style_lower = (ev.style or "").lower()
            # Strip redundant {\i1} / {\i0} in lines that are already rendered in Italics style
            if "italic" in ev_style_lower and (r"\i1" in ev.text or r"\i0" in ev.text):
                old_it_t = ev.text
                ev.text = re.sub(r"\{\\i[01]\}", "", ev.text).strip()
                if ev.text != old_it_t:
                    fixes.append(f"[Episode Quality Gate - Redundancja Kursywy] Linia #{i+1}: usunięto zbędne znaczniki {{\\i1}}/{{\\i0}} w stylu pochyłym 'Italics'")

            # Normalize non-normative ellipsis clusters (e.g. ?... -> ?.., !... -> !..)
            if re.search(r"[\?!]\.{3,}", ev.text):
                old_punc_t = ev.text
                ev.text = re.sub(r"\?\.{3,}", "?..", ev.text)
                ev.text = re.sub(r"!\.{3,}", "!..", ev.text)
                if ev.text != old_punc_t:
                    fixes.append(f"[Episode Quality Gate - Higiena Interpunkcji] Linia #{i+1}: znormalizowano nienormatywny wielokropek (?...) na standardowy AVT (?..)")

            # Token Punctuation Stutter Sanitizer (Filar CLXXIV - 0.00 PLN)
            # Eliminates immediate token repetitions with punctuation (e.g. 'odebrać.odebrać.' -> 'odebrać.', 'tak.tak.' -> 'tak.')
            stutter_pat = r"\b([A-Za-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]{2,}[\.!\?…]+)\s*\1(?!\w)"
            if re.search(stutter_pat, ev.text):
                old_stutter_t = ev.text
                ev.text = re.sub(stutter_pat, r"\1", ev.text)
                if ev.text != old_stutter_t:
                    fixes.append(f"[Episode Quality Gate - Filar CLXXIV Higiena Tokenów] Linia #{i+1}: usunięto zacięcie/jąkanie tokenu z interpunkcją")

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

            # 0. FORMATTING TAG SANITIZATION (Deduplicate stacked {\i1}{\i1}, {\b1}{\b1}, {\i0}{\i0}, etc.)
            old_t = ev.text
            ev.text = re.sub(r"(\{\\[ibus][01]\})\1+", r"\1", ev.text)
            if ev.text != old_t:
                fixes.append(f"[Episode Quality Gate - Tag Sanitization] Linia #{i+1}: usunięto zduplikowane znaczniki formatowania ASS")

            # 0b. IN-LINE DUAL SPEAKER DIALOGUE SPLIT (Filar LVII)
            if not is_sign:
                clean_body = re.sub(r"^(\s*\{[^\}]*\})+", "", ev.text)
                ts_prefix = ev.text[:len(ev.text) - len(clean_body)]
                dual_match = re.match(
                    r"^[-–—]?\s*(.+?(?:[.!?…]+|\]|\))\s*)[-–—]\s*((?:\{[^\}]*\})*[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż…\[].+)$",
                    clean_body,
                    re.DOTALL
                )
                if dual_match and r"\N-" not in ev.text and r"\N -" not in ev.text and r"\N–" not in ev.text and r"\N –" not in ev.text:
                    p1 = re.sub(r"^[-–—]\s*", "", dual_match.group(1)).strip()
                    p2 = re.sub(r"^[-–—]\s*", "", dual_match.group(2)).strip()
                    old_t = ev.text
                    ev.text = f"{ts_prefix}- {p1}\\N- {p2}"
                    if ev.text != old_t:
                        fixes.append(f"[Episode Quality Gate - Filar LVII Wielogłos Symultaniczny] Linia #{i+1}: sformatowano połączone kwestie dwóch mówców na dwie osobne linie z myślnikami")

            # 0c. DIEGETIC SPOKEN DIALOGUE ITALICS PURISM (Filar LX / AVT Belczyk & Netflix Canon)
            # Remove artificial {\i1}...{\i0} flashback/thought wrappers on direct diegetic speech between characters
            if not is_sign and (r"\i1" in ev.text or r"\i0" in ev.text):
                ev_style_l = (ev.style or "").lower()
                is_song = bool(re.search(r"\b(song|music|op|ed|karaoke)\b", ev_style_l)) or ("♪" in ev.text) or ("♫" in ev.text)
                if not is_song:
                    clean_no_tags = re.sub(r"\{[^\}]*\}", "", ev.text).strip()
                    raw_spk = getattr(ev, "name", None) or getattr(ev, "actor", None) or (line_speakers.get(i) if line_speakers else None)
                    spk_clean = extract_clean_speaker_name(str(raw_spk or "")).strip() if raw_spk else ""
                    spk_lower = spk_clean.lower()
                    is_voiceover_or_device = any(w in spk_lower for w in ["narrator", "voiceover", "lektor", "radio", "tv", "telefon", "system", "interkom"])
                    
                    has_char_speaker = bool(spk_clean and len(spk_clean) >= 3 and not is_voiceover_or_device and not is_generic_actor_or_category(spk_clean))
                    has_direct_vocative = bool(re.search(r"\b(?:generale|panie|pani|panno|mistrzu|chanie|lordzie|wasale|chaganie)\s+[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+|\b(?:Wielki\s+)?Chanie\b", clean_no_tags, re.IGNORECASE))
                    has_dialogue_alternation = False
                    if prev_ev:
                        prev_raw = getattr(prev_ev, "name", None) or getattr(prev_ev, "actor", None)
                        prev_clean_spk = extract_clean_speaker_name(str(prev_raw or "")).strip() if prev_raw else ""
                        if prev_clean_spk and spk_clean and len(prev_clean_spk) >= 3 and len(spk_clean) >= 3:
                            if prev_clean_spk.lower() != spk_clean.lower() and (ev.start - prev_ev.end < 4000):
                                has_dialogue_alternation = True
                    has_qa_markers = bool(re.search(r"^(?:Tak|Nie|Słucham|Owszem)\b", clean_no_tags, re.IGNORECASE))
                    
                    is_diegetic_speech = has_direct_vocative or (has_char_speaker and has_dialogue_alternation) or (has_char_speaker and has_qa_markers and prev_ev and (ev.start - prev_ev.end < 3000))
                    
                    if is_diegetic_speech:
                        old_it_text = ev.text
                        ev.text = re.sub(r"\{\\i[01]\}", "", ev.text).strip()
                        if ev.text != old_it_text:
                            fixes.append(f"[Episode Quality Gate - Filar LX Puryzm Kursywy AVT] Linia #{i+1}: usunięto sztuczną kursywę {{\\i1}} z bezpośredniej mowy diegetycznej")

            # 1a. LONE DIALOGUE DASH SANITIZER (Filar LVII / Netflix AVT: Zakaz samotnego myślnika w kwestiach jednoosobowych)
            if not is_sign:
                clean_for_dash = re.sub(r"\{[^\}]*\}", "", ev.text).strip()
                if clean_for_dash.startswith("- ") or clean_for_dash.startswith("– ") or clean_for_dash.startswith("— "):
                    # Dual-speaker line requires a second speaker dash (\N- or \N– or \N—)
                    has_second_dash = bool(re.search(r"\\(?:[Nnh])+\s*[-–—]\s+", ev.text))
                    if not has_second_dash:
                        old_t = ev.text
                        ev.text = re.sub(r"^((?:\{[^\}]*\})*)\s*[-–—]\s+", r"\1", ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Filar LVII Zakaz Samotnego Myślnika] Linia #{i+1}: usunięto pojedynczy myślnik dialogowy w kwestii jednoosobowej")

            # 1b. TITLE & SIGN CAPITALIZATION (Filar XLI & LX)
            if is_sign or re.search(r"\b(?:Odcinek|Rozdział)\s+\d+\b", ev.text, re.IGNORECASE):
                old_cap_t = ev.text
                ev.text = re.sub(r"(\\N\s*(?:\{[^\}]*\}\s*)*)([a-ząćęłńóśźż])", lambda m: f"{m.group(1)}{m.group(2).upper()}", ev.text)
                if is_sign:
                    ev.text = re.sub(r"^(\s*(?:\{[^\}]*\}\s*)*)([a-ząćęłńóśźż])", lambda m: f"{m.group(1)}{m.group(2).upper()}", ev.text)
                if ev.text != old_cap_t:
                    fixes.append(f"[Episode Quality Gate - Filar XLI/LX Majuskuła Napisów] Linia #{i+1}: skapitalizowano początek tytułu/napisu ekranowego")

            # 1c. TITLE APPOSITION CASE AGREEMENT (Filar CXXIV & CLVII)
            appos_pat = r"\b(na\s+ziemiach|na\s+ziemie|w\s+rękach|do\s+rąk|u\s+boku|pod\s+wodzą|z\s+rozkazu|przeciwko|przeciw|dla|z\s+rąk)\s+(generał|pułkownik|major|kapitan|admirał|książę|król|chan|baron|hrabia|wódz)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż\w]+)"
            if re.search(appos_pat, ev.text, re.IGNORECASE):
                old_appos_t = ev.text
                TITLE_GEN_MAP = {
                    "generał": "generała",
                    "pułkownik": "pułkownika",
                    "major": "majora",
                    "kapitan": "kapitana",
                    "admirał": "admirała",
                    "książę": "księcia",
                    "król": "króla",
                    "chan": "chana",
                    "baron": "barona",
                    "hrabia": "hrabiego",
                    "wódz": "wodza",
                }
                def _fix_appos_eqg(m):
                    prep = m.group(1)
                    title = m.group(2)
                    name = m.group(3)
                    repl_title = TITLE_GEN_MAP.get(title.lower(), title)
                    if title[0].isupper():
                        repl_title = repl_title.capitalize()
                    return f"{prep} {repl_title} {name}"
                ev.text = re.sub(appos_pat, _fix_appos_eqg, ev.text, flags=re.IGNORECASE)
                if ev.text != old_appos_t:
                    fixes.append(f"[Episode Quality Gate - Filar CXXIV Tytulatura w Apozycji] Linia #{i+1}: skorygowano mianownik tytułu na dopełniacz/biernik w apozycji")

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
                        re.search(r"\bnie\s+[a-ząćęłńóśźż]+", prev_clean, re.IGNORECASE) or
                        any(prev_clean.lower().startswith(w) for w in ["don't", "aren't", "didn't", "can't", "won't", "haven't", "isn't"])
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
                    elif is_prev_neg_q:
                        # Negative questions answered affirmatively in JP (Hai/Un) must be negative in PL (Nie / N-Nie)
                        m_aff = re.match(r"^(\s*\{[^\}]*\})*([Tt]-[Tt]ak|[Tt]ak)([\.!\?…]*)(\{[^\}]*\}\s*)*$", ev.text.strip())
                        if m_aff:
                            word = m_aff.group(2)
                            punct = m_aff.group(3) or "."
                            repl_word = "N-Nie" if word.lower().startswith("t-") else ("Nie" if word[0].isupper() else "nie")
                            ev.text = re.sub(rf"\b{re.escape(word)}", repl_word, ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Echo Agreement] Linia #{i+1}: zastąpiono '{word}{punct}' przez '{repl_word}{punct}' w reakcji na pytanie z przeczeniem '{prev_clean[:25]}...'")
                        # Also handle "Tak, nie..." -> "Nie, nie..." (calque of JP 'Hai, [negation]')
                        m_tak_nie = re.match(r"^(\s*\{[^\}]*\})*([Tt]ak),\s+(nie\s+[a-ząćęłńóśźż]+)", ev.text, re.IGNORECASE)
                        if m_tak_nie:
                            ev.text = re.sub(r"^(\s*\{[^\}]*\})*[Tt]ak,\s+nie\b", r"\g<1>Nie, nie", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Echo Agreement] Linia #{i+1}: skorygowano kalkę 'Tak, nie...' na 'Nie, nie...' w reakcji na pytanie z przeczeniem")

            # 1c. TEMPORAL DISCONTINUITY & SCENE BOUNDARY AUDIT (Filar CLXV)
            if not is_sign and prev_clean and prev_ev:
                time_gap_ms = ev.start - prev_ev.end
                is_prev_private_request = bool(re.search(
                    r"\b(na\s+osobności|w\s+cztery\s+oczy|porozmawiać|pogadać|w\s+ustronne\s+miejsce|wyjdźmy|chodźmy|talk\s+in\s+private|alone|somewhere\s+quiet|private)\b",
                    prev_clean,
                    re.IGNORECASE
                ))
                # Check for delayed agreement fallacy ("Jasne, o co chodzi?" / "Pewnie, o co chodzi?" 4-25s after relocation request or 6s+ gap)
                if (time_gap_ms >= 4000 and is_prev_private_request) or time_gap_ms >= 6000:
                    m_delayed_agree = re.search(
                        r"^(\s*\{[^\}]*\})*([Jj]asne|[Pp]ewnie|[Ww]\s+porządku|[Dd]obrze|[Tt]ak|[Aa]\s+zatem|[Aa]\s+więc|[Nn]o\s+dobrze|[Nn]o\s+dobra)(?:[,.!?…—–-]+|\\[Nnh]+)*(?:\s+|\\N)+(o\s+co\s+chodzi|co\s+się\s+stało|w\s+czym\s+rzecz|słucham|słucham\s+cię|co\s+jest|czego\s+chcesz|o\s+czym\s+chcesz|o\s+czym\s+chciałaś|o\s+czym\s+chciałeś|w\s+czym\s+mogę\s+pomóc|zamieniam\s+się\s+w\s+słuch|o\s+co\s+biega|mów)\b",
                        ev.text,
                        re.IGNORECASE
                    )
                    if m_delayed_agree:
                        orig_lead = m_delayed_agree.group(0)
                        is_cap = m_delayed_agree.group(2)[0].isupper()
                        repl_starter = "Więc" if is_cap else "więc"
                        q_part = m_delayed_agree.group(3)
                        tag_prefix = m_delayed_agree.group(1) or ""
                        sep_chunk = orig_lead[len(tag_prefix) + len(m_delayed_agree.group(2)):-len(q_part)]
                        sep_repl = r"\N" if r"\N" in sep_chunk else " "
                        if sep_repl == " " and q_part:
                            q_part = q_part[0].lower() + q_part[1:]
                        repl_full = f"{tag_prefix}{repl_starter}{sep_repl}{q_part}"
                        ev.text = ev.text[:m_delayed_agree.start()] + repl_full + ev.text[m_delayed_agree.end():]
                        fixes.append(
                            f"[Episode Quality Gate - Filar CLXV Dyskontinuitet Czasowy] Linia #{i+1}: "
                            f"zlikwidowano opóźnione potwierdzenie '{orig_lead.strip()}' "
                            f"(pauza {time_gap_ms/1000.0:.1f}s po prośbie o rozmowę) -> '{repl_full.strip()}'"
                        )

            # 1d. AISATSU RETURN/DEPARTURE ADJACENCY ECHO GUARD (Filar CLXX)
            if not is_sign and prev_clean and prev_ev:
                time_gap_ms = ev.start - prev_ev.end
                if time_gap_ms < 6000:
                    is_prev_return = bool(re.search(r"\b(wróciłam|wróciłem|wróciłam do domu|wróciłem do domu)\b", prev_clean, re.IGNORECASE))
                    if is_prev_return:
                        # Echo verb responses like "Wróciłaś.", "Wróciłeś.", "Już wróciłaś.", "Wróciłaś!"
                        m_echo_return = re.search(r"^(\s*\{[^\}]*\})*([Jj]uż\s+)?([Ww]róciłaś|[Ww]róciłeś)([\.!\?…]*)(\{[^\}]*\}\s*)*$", ev.text.strip())
                        if m_echo_return:
                            punct = m_echo_return.group(4) or "."
                            repl_text = f"O, już jesteś{punct}"
                            ev.text = re.sub(r"\b([Jj]uż\s+)?([Ww]róciłaś|[Ww]róciłeś)[\.!\?…]*", repl_text, ev.text, count=1)
                            fixes.append(
                                f"[Episode Quality Gate - Filar CLXX Harmonizacja Aisatsu] Linia #{i+1}: "
                                f"zlikwidowano nienaturalne echo czasownikowe powitania powrotu w reakcji na '{prev_clean[:25]}...' -> '{repl_text}'"
                            )

            # 1b. GESTURAL / PHYSICAL "HERE" -> "TUTAJ" CALQUE & ISOLATED KAKEGOE GUARD (Filar IV & XVIII)
            if not is_sign:
                clean_no_tags = re.sub(r"\{[^\}]*\}", "", ev.text).strip()
                # 1b-1: Lone or compound "Tutaj / Tu / Oto" when NOT answering a spatial wh-question ("Gdzie? / Dokąd?")
                m_tutaj = re.match(r"^([Tt]utaj|[Tt]u|[Oo]to)([\.!\?…]*)$", clean_no_tags)
                m_tutaj_compound = re.match(r"^([Tt]utaj|[Tt]u|[Oo]to)[,\s]+(weź|bierz|masz|trzymaj|proszę)\b", clean_no_tags, re.IGNORECASE)
                if m_tutaj or m_tutaj_compound:
                    word = m_tutaj.group(1) if m_tutaj else m_tutaj_compound.group(1)
                    punct = m_tutaj.group(2) if m_tutaj else ""
                    is_answering_loc = False
                    if prev_clean and prev_ev and (ev.start - prev_ev.end < 6000):
                        if any(w in prev_clean.lower() for w in ["gdzie", "dokąd", "skąd", "w którym miejscu", "gdzie to"]):
                            is_answering_loc = True
                    if not is_answering_loc:
                        has_informal = False
                        if prev_clean and any(w in prev_clean.lower() for w in ["masz", "wiesz", "daj", "dzięki", "twoje", "twój", "ty"]):
                            has_informal = True
                        repl_w = "Trzymaj" if has_informal else "Proszę"
                        if not word[0].isupper():
                            repl_w = repl_w.lower()
                        ev.text = re.sub(rf"\b{re.escape(word)}", repl_w, ev.text, count=1)
                        fixes.append(f"[Episode Quality Gate - Filar IV/XVIII] Linia #{i+1}: zlikwidowano kalkę gestu 'Here' -> '{word}{punct}' na rzecz naturalnego '{repl_w}{punct}'")

            # 2. THOUGHT-TO-SPEECH BOUNDARY: Strip unsolicited thought italics on plain dialogue lines
            if not is_sign and prev_ev:
                prev_is_thought_style = "italic" in (prev_ev.style or "").lower()
                curr_style_thought = "italic" in (ev.style or "").lower()
                # If previous event was explicitly styled as Italics, and current event is regular Default dialogue, strip artificial {\i1}...{\i0}
                if prev_is_thought_style and not curr_style_thought:
                    if r"\i1" in ev.text and r"\i0" in ev.text:
                        ev.text = re.sub(r"\{\\i[01]\}", "", ev.text).strip()
                        fixes.append(f"[Episode Quality Gate - Bariera Myśli] Linia #{i+1}: usunięto sztuczną kursywę {{\\i1}} po przejściu z myśli do mowy diegetycznej")

            # 3b. INTER-LINE T-V INVARIANCE (Filar CLVII): First name in dialogue vs unexpected 'pan/pani'
            if not is_sign and prev_clean and prev_ev:
                time_gap_ms = ev.start - prev_ev.end
                if time_gap_ms < 6000:
                    has_formal_voc_prev = bool(re.search(
                        r"\b(panie|pani|panno|panu|pana|mistrzu|lordzie|książę|panienko)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b",
                        prev_clean,
                        re.IGNORECASE
                    ))
                    has_formal_voc_curr = bool(re.search(
                        r"\b(panie|pani|panno|panu|pana|mistrzu|lordzie|książę|panienko)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+|doktorze|profesorze|inspektorze|prezesie|dyrektorze|kierowniku|komisarzu)\b",
                        ev.text,
                        re.IGNORECASE
                    ))
                    fn_prev_m = re.search(
                        r"(?<!\bpanie\s)(?<!\bpani\s)(?<!\bpanno\s)(?<!\bmistrzu\s)(?<!\blordzie\s)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})[,?!]",
                        prev_clean
                    )
                    first_name_in_prev = bool(fn_prev_m) and not has_formal_voc_prev
                    if first_name_in_prev and not has_formal_voc_curr:
                        prev_voc_name = fn_prev_m.group(1) if fn_prev_m else ""
                        from series_memory import is_inherently_female_name, MALE_EXCEPTIONS_ON_A
                        is_female_target = False
                        is_male_target = False
                        if prev_voc_name:
                            p_clean_n = prev_voc_name.lower()
                            if char_gender_map.get(p_clean_n) == "FEMALE":
                                is_female_target = True
                            elif char_gender_map.get(p_clean_n) == "MALE" or p_clean_n in MALE_EXCEPTIONS_ON_A:
                                is_male_target = True
                            elif series_bible and hasattr(series_bible, "get_character_gender"):
                                bg = series_bible.get_character_gender(prev_voc_name, allow_generic_nouns=False)
                                if bg == "FEMALE":
                                    is_female_target = True
                                elif bg == "MALE":
                                    is_male_target = True
                            if not is_female_target and not is_male_target and is_inherently_female_name(prev_voc_name):
                                is_female_target = True

                        if is_female_target:
                            drift_matches = [
                                (r"\bwygrał\s+pan\b", "wygrałaś"),
                                (r"\bwygrała\s+pani\b", "wygrałaś"),
                                (r"\bwidział\s+pan\b", "widziałaś"),
                                (r"\bwidziała\s+pani\b", "widziałaś"),
                                (r"\bzrobił\s+pan\b", "zrobiłaś"),
                                (r"\bzrobiła\s+pani\b", "zrobiłaś"),
                                (r"\bbył\s+pan\b", "byłaś"),
                                (r"\bbyła\s+pani\b", "byłaś"),
                                (r"\bmiał\s+pan\b", "miałaś"),
                                (r"\bmiała\s+pani\b", "miałaś"),
                                (r"\bpan\s+wie\b", "wiesz"),
                                (r"\bpani\s+wie\b", "wiesz"),
                                (r"\bpan\s+myśli\b", "myślisz"),
                                (r"\bpani\s+myśli\b", "myślisz"),
                                (r"\bniech\s+pan\s+spojrzy\b", "spójrz"),
                                (r"\bniech\s+pani\s+spojrzy\b", "spójrz")
                            ]
                        else:
                            drift_matches = [
                                (r"\bwygrał\s+pan\b", "wygrałeś"),
                                (r"\bwygrała\s+pani\b", "wygrałaś"),
                                (r"\bwidział\s+pan\b", "widziałeś"),
                                (r"\bwidziała\s+pani\b", "widziałaś"),
                                (r"\bzrobił\s+pan\b", "zrobiłeś"),
                                (r"\bzrobiła\s+pani\b", "zrobiłaś"),
                                (r"\bbył\s+pan\b", "byłeś"),
                                (r"\bbyła\s+pani\b", "byłaś"),
                                (r"\bmiał\s+pan\b", "miałeś"),
                                (r"\bmiała\s+pani\b", "miałaś"),
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

            # 3b-3. INTRA-LINE HYBRID VOCATIVE + FORMAL ADDRESS GUARD (Filar C & CLVII)
            if not is_sign:
                clean_ev_check = re.sub(r"\\[Nnh]", " ", ev.text)
                has_formal_address_in_line = bool(re.search(
                    r"\b(?:ma|niech|chce|chciał|może|widzi|wie|pamięta|szuka|prosił|prosiła|czuje|smakuje|stoi|jest)\s+(?:pan|pani|pana|panu)\b|"
                    r"\b(?:pan|pani|pana|panu)\s+(?:ma|niech|chce|chciał|może|widzi|wie|pamięta|szuka|prosił|prosiła|czuje|smakuje|stoi|jest|prosił|szuka)\b|"
                    r"\b(?:u|dla|od|przeciwko)\s+(?:pana|pani|panu)\b|"
                    r"\bźle\s+się\s+pan\b|\bsmakuje\s+panu\b|\bpanu\s+o\s+tym\b|\bpanu\s+nie\b|\bniech\s+pan\b|\bchciał\s+pan\b|\bpan\s+szuka\b|\bma\s+pan\b",
                    clean_ev_check,
                    re.IGNORECASE
                ))
                if has_formal_address_in_line:
                    def _fix_hybrid_voc(m):
                        name = m.group(1)
                        name_low = name.lower()
                        if name_low in {"panie", "pani", "panno", "mistrzu", "panu", "bogu", "czasu", "domu", "końcu", "początku", "bratu", "chłopcu", "wtedy", "znowu", "ogromny", "ognisty", "smakuje", "nigdy"}:
                            return m.group(0)
                        # Check that the vocative corresponds to a candidate character name
                        is_cand = any(name_low.startswith(c[:max(3, len(c)-2)].lower()) for c in candidate_names)
                        if not is_cand:
                            return m.group(0)
                        before = ev.text[:m.start()].rstrip()
                        is_start = (before == "" or bool(re.search(r"[\.!\?…]$|\\[Nnh]$", before)))
                        title = "Panie" if is_start else "panie"
                        fixes.append(f"[Episode Quality Gate - Filar C/CLVII] Linia #{i+1}: zlikwidowano hybrydę wołacza '{name}' + zwrot formalny -> '{title} {name}'")
                        return f"{title} {name}"

                    ev.text = re.sub(
                        r"(?<!\bpanie\s)(?<!\bPanie\s)(?<!\bpani\s)(?<!\bPani\s)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}[uey])\b",
                        _fix_hybrid_voc,
                        ev.text
                    )

            # 3b-4. SUBJECT NOMINATIVE CASE REPAIR FOR TITLE APPOSITION (Filar CLVII / CLXX)
            if not is_sign:
                TITLES_SUBJECT_PAT = r"[Pp]an|[Pp]ani|[Mm]istrz|[Pp]rofesor|[Dd]oktor|[Pp]isarz|[Rr]eżyser|[Rr]edaktor|[Aa]utor|[Mm]angaka|[Ss]ensei"
                CANONICAL_A_NAMES = {
                    "akira", "shira", "soma", "gaara", "ashitaka", "kiba", "kenta",
                    "ryoma", "hanza", "koba", "soya", "toma", "genga"
                }

                # Case 1: Title + Surname + Given Name + Verb (e.g. 'Mistrz Tondena minoru\Nnie zdążył' -> 'Mistrz Tonden Minoru\Nnie zdążył')
                def _fix_nominative_two_part_title_apposition(m):
                    prefix = m.group(1)
                    title = m.group(2)
                    sep1 = m.group(3)
                    surname_stem = m.group(4)
                    sep2 = m.group(5)
                    given_name = m.group(6)
                    sep3 = m.group(7)
                    verb = m.group(8)
                    full_surname = (surname_stem + "a").lower()
                    if full_surname in CANONICAL_A_NAMES:
                        clean_surname = surname_stem + "a"
                    else:
                        clean_surname = surname_stem
                    clean_given = given_name.capitalize()
                    fixes.append(
                        f"[Episode Quality Gate - Filar CLVII/CLXX] Linia #{i+1}: "
                        f"skorygowano mianownik i wielkość liter tytulatury '{title} {surname_stem}a {given_name}' -> '{title} {clean_surname} {clean_given}'"
                    )
                    return f"{prefix}{title}{sep1}{clean_surname}{sep2}{clean_given}{sep3}{verb}"

                ev.text = re.sub(
                    rf"(^|[^\w]|\\[Nnh])({TITLES_SUBJECT_PAT})(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]*[bcdfghjklmnprstvwxz])a(\s+|\\[Nnh]+)([A-Za-ząćęłńóśźż]+)(\s+|\\[Nnh]+)((?:nie\s+)?[a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
                    _fix_nominative_two_part_title_apposition,
                    ev.text
                )

                # Case 2: Title + Single Name + Verb (e.g. 'pan Eftala zniszczył' -> 'pan Eftal zniszczył')
                def _fix_nominative_title_apposition(m):
                    prefix = m.group(1)
                    title = m.group(2)
                    sep1 = m.group(3)
                    name_stem = m.group(4)
                    sep2 = m.group(5)
                    verb = m.group(6)
                    full_name = (name_stem + "a").lower()
                    if full_name in CANONICAL_A_NAMES:
                        return m.group(0)
                    fixes.append(f"[Episode Quality Gate - Filar CLVII/CLXX] Linia #{i+1}: skorygowano skażenie mianownika tytulatury '{title} {name_stem}a' -> '{title} {name_stem}'")
                    return f"{prefix}{title}{sep1}{name_stem}{sep2}{verb}"

                ev.text = re.sub(
                    rf"(^|[^\w]|\\[Nnh])({TITLES_SUBJECT_PAT})(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]*[bcdfghjklmnprstvwxz])a(\s+|\\[Nnh]+)((?:nie\s+)?[a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
                    _fix_nominative_title_apposition,
                    ev.text
                )

            # 3b-5. EPISODE-LEVEL SPEAKER T-V VOCATIVE HARMONIZATION (Filar C & CLVII Anti-Sama-Drop)
            if not is_sign and getattr(ev, "name", None):
                curr_spk = ev.name.strip().lower()
                for c_name in candidate_names:
                    if speaker_formal_char.get((curr_spk, c_name), 0) >= 2 and speaker_informal_to_char.get((curr_spk, c_name), 0) == 0:
                        stem_len = max(3, len(c_name) - 2)
                        stem = c_name[:stem_len]
                        def _fix_spk_voc(m):
                            voc_name = m.group(1)
                            punct = m.group(2)
                            before = ev.text[:m.start()].rstrip()
                            is_start = (before == "" or bool(re.search(r"[\.!\?…]$|\\[Nnh]$", before)))
                            title = "Panie" if is_start else "panie"
                            fixes.append(f"[Episode Quality Gate - Filar C/CLVII Anti-Sama-Drop] Linia #{i+1}: zharmonizowano wołacz formalny dla mówcy '{ev.name}': '{title} {voc_name}{punct}'")
                            return f"{title} {voc_name}{punct}"

                        ev.text = re.sub(
                            rf"(?<!\bpanie\s)(?<!\bPanie\s)\b({stem}[a-ząćęłńóśźż]*[uey])(!|\s*!)",
                            _fix_spk_voc,
                            ev.text,
                            flags=re.IGNORECASE
                        )

            # 3c. CHARACTER GENDER CONSISTENCY GUARD (Filar CLXII)
            if not is_sign:
                # Sanitize event name against generic category nouns
                if getattr(ev, "name", None) and is_generic_actor_or_category(str(ev.name)):
                    ev.name = ""

                # 3c-1: 1st-person self-reference consistency for the speaker
                spk_name = getattr(ev, "name", None) or getattr(ev, "actor", None) or getattr(ev, "speaker", None)
                if spk_name and is_generic_actor_or_category(str(spk_name)):
                    spk_name = None

                if (not spk_name or not str(spk_name).strip()) and line_speakers and i in line_speakers:
                    cand_spk = line_speakers[i]
                    if cand_spk and not is_generic_actor_or_category(str(cand_spk)):
                        spk_name = cand_spk

                if (not spk_name or not str(spk_name).strip()) and line_addressees:
                    if i > 0 and (i - 1) in line_addressees and (ev.start - events[i-1].end < 6000):
                        cand = line_addressees[i - 1]
                        if cand and not is_generic_actor_or_category(cand):
                            clean_cand = extract_clean_speaker_name(cand).lower()
                            if clean_cand in char_gender_map or (series_bible and series_bible.get_character_gender(cand, allow_generic_nouns=False) != "UNKNOWN"):
                                spk_name = cand

                if (not spk_name or not str(spk_name).strip()) and i > 0 and getattr(events[i-1], "addressee", None):
                    cand = getattr(events[i-1], "addressee", None)
                    if cand and not is_generic_actor_or_category(cand) and (ev.start - events[i-1].end < 6000):
                        clean_cand = extract_clean_speaker_name(cand).lower()
                        if clean_cand in char_gender_map or (series_bible and series_bible.get_character_gender(cand, allow_generic_nouns=False) != "UNKNOWN"):
                            spk_name = cand

                spk_gen = None
                if spk_name and str(spk_name).strip() and not is_generic_actor_or_category(str(spk_name)):
                    if not getattr(ev, "name", None) or not str(ev.name).strip() or is_generic_actor_or_category(str(ev.name)):
                        ev.name = str(spk_name).strip()
                    spk_name_lower = str(spk_name).strip().lower()
                    spk_clean = extract_clean_speaker_name(str(spk_name)).lower()
                    spk_gen = char_gender_map.get(spk_clean) or char_gender_map.get(spk_name_lower)
                    if not spk_gen and series_bible and hasattr(series_bible, "get_character_gender"):
                        b_g = series_bible.get_character_gender(spk_clean, allow_generic_nouns=False)
                        if b_g in ("FEMALE", "MALE"):
                            spk_gen = b_g
                    if not spk_gen and series_bible and hasattr(series_bible, "is_low_pitch_female"):
                        if series_bible.is_low_pitch_female(spk_clean):
                            spk_gen = "FEMALE"

                    if spk_gen == "MALE":
                        # Acoustic & Scene Primacy Shield (Filar CLXXIV - 0.00 PLN):
                        # If actor tag is MALE (e.g. 'Ögedei'), but scene is confirmed FEMALE
                        # or physical audio is FEMALE, override spk_gen to FEMALE and prevent masculine mutations!
                        jp_aud = (whisper_transcriptions.get(i + 1, "") if whisper_transcriptions else "") or (getattr(ev, "audio_jp", "") or "")
                        w_is_fem = any(m in jp_aud.lower() for m in ["warawa", "妾", "atashi", "あたし", "atai", "あたい", "wa yo", "わよ", "kashira", "かしら"])
                        sc_is_fem = (event_scene_gender.get(i) == "FEMALE")
                        is_cont = False
                        if series_bible and hasattr(series_bible, "audit_speaker_metadata_against_audio"):
                            aud_res, is_cont = series_bible.audit_speaker_metadata_against_audio(spk_clean, whisper_gender="FEMALE" if w_is_fem else None, scene_gender="FEMALE" if sc_is_fem else None)
                            if is_cont and aud_res == "FEMALE":
                                spk_gen = "FEMALE"
                        if not is_cont and (sc_is_fem or w_is_fem):
                            spk_gen = "FEMALE"

                # Scene-Level Exclusive Gender Assignment for Anonymous Speaker
                if not spk_gen and event_scene_gender.get(i):
                    spk_gen = event_scene_gender.get(i)

                # Turn-Level Gender Harmony Gate (Speaker Turn Continuity):
                # Detect contiguous dialogue turn morphology (gap < 2200ms, no question-answer boundary)
                turn_s = i
                while turn_s > 0:
                    p_ev = events[turn_s - 1]
                    c_ev = events[turn_s]
                    gap = c_ev.start - p_ev.end
                    if gap >= 2200:
                        break
                    p_clean = re.sub(r"\{[^\}]*\}", "", p_ev.text or "").strip()
                    if p_clean.endswith("?") and gap >= 600:
                        break
                    p_n = getattr(p_ev, "name", "") or ""
                    c_n = getattr(c_ev, "name", "") or ""
                    if p_n and c_n and not is_generic_actor_or_category(p_n) and not is_generic_actor_or_category(c_n):
                        if extract_clean_speaker_name(p_n).lower() != extract_clean_speaker_name(c_n).lower():
                            break
                    turn_s -= 1

                turn_e = i
                while turn_e < len(events) - 1:
                    c_ev = events[turn_e]
                    n_ev = events[turn_e + 1]
                    gap = n_ev.start - c_ev.end
                    if gap >= 2200:
                        break
                    c_clean = re.sub(r"\{[^\}]*\}", "", c_ev.text or "").strip()
                    if c_clean.endswith("?") and gap >= 600:
                        break
                    c_n = getattr(c_ev, "name", "") or ""
                    n_n = getattr(n_ev, "name", "") or ""
                    if c_n and n_n and not is_generic_actor_or_category(c_n) and not is_generic_actor_or_category(n_n):
                        if extract_clean_speaker_name(c_n).lower() != extract_clean_speaker_name(n_n).lower():
                            break
                    turn_e += 1

                turn_evs = events[turn_s : turn_e + 1]
                turn_fem_count = sum(
                    1 for tev in turn_evs
                    if re.search(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łam|łabym)\b", tev.text or "", re.IGNORECASE)
                )
                turn_masc_count = sum(
                    1 for tev in turn_evs
                    if re.search(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łem|łbym)\b", tev.text or "", re.IGNORECASE)
                )

                # Prevent circular LLM bias locking: only infer from turn counts when not already determined from scene/bible
                if spk_gen is None:
                    if turn_fem_count > 0 and (turn_s < turn_e and turn_fem_count >= turn_masc_count):
                        spk_gen = "FEMALE"
                    elif turn_masc_count > 0 and (turn_s < turn_e and turn_masc_count > turn_fem_count):
                        spk_gen = "MALE"

                label_spk = spk_name or ("kobieta" if spk_gen == "FEMALE" else "mężczyzna")
                if spk_gen == "MALE":
                    for f_pat, m_repl in FIRST_PERSON_FEMININE_TO_MASCULINE:
                        match = re.search(f_pat, ev.text, re.IGNORECASE)
                        if match:
                            matched_word = match.group(0)
                            def _m_case_repl(m, repl=m_repl):
                                return repl.capitalize() if m.group(0)[0].isupper() else repl
                            ev.text = re.sub(f_pat, _m_case_repl, ev.text, flags=re.IGNORECASE)
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano 1. os. na rodzaj męski dla mówcy '{label_spk}' ('{matched_word}' -> '{m_repl}')")
                    def _morph_f_to_m_repl(m):
                        word = m.group(0)
                        converted = convert_first_person_feminine_to_masculine(word)
                        if converted and converted != word:
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano 1. os. na rodzaj męski dla mówcy '{label_spk}' ('{word}' -> '{converted}')")
                            return converted
                        return word
                    ev.text = re.sub(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łam|łabym)\b", _morph_f_to_m_repl, ev.text)
                    # Compound predicates for male speaker
                    for f_adj, m_adj in FEMININE_SG_ADJECTIVES_TO_MASCULINE.items():
                        pat_pred = rf"\b((?:byłem|byłam|czułem\s+się|czułam\s+się|zostałem|zostałam|poczułem\s+się|poczułam\s+się)\s+)({re.escape(f_adj)})\b"
                        for match in list(re.finditer(pat_pred, ev.text, re.IGNORECASE)):
                            p_prefix = match.group(1)
                            p_adj = match.group(2)
                            p_repl = m_adj.capitalize() if p_adj[0].isupper() else m_adj
                            ev.text = re.sub(rf"\b{re.escape(p_prefix)}{re.escape(p_adj)}\b", f"{p_prefix}{p_repl}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano orzecznik 1. os. na rodzaj męski dla mówcy '{label_spk}' ('{p_prefix}{p_adj}' -> '{p_prefix}{p_repl}')")
                    # Clitics for male speaker
                    clitic_pat = r"\b((?:gdybym|jakbym|żebym|abym|bym|choćbym|chociażbym)\s+)([A-Za-ząćęłńóśźż]+(?:ała|iła|yła|ęła))\b"
                    for match in list(re.finditer(clitic_pat, ev.text, re.IGNORECASE)):
                        c_prefix = match.group(1)
                        c_verb = match.group(2)
                        c_masc = convert_feminine_past_to_masculine(c_verb)
                        if c_masc and c_masc.lower() != c_verb.lower():
                            ev.text = re.sub(rf"\b{re.escape(c_prefix)}{re.escape(c_verb)}\b", f"{c_prefix}{c_masc}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano klitykę 1. os. na rodzaj męski dla mówcy '{label_spk}' ('{c_prefix}{c_verb}' -> '{c_prefix}{c_masc}')")
                elif spk_gen == "FEMALE":
                    for m_pat, f_repl in FIRST_PERSON_MASCULINE_TO_FEMININE:
                        match = re.search(m_pat, ev.text, re.IGNORECASE)
                        if match:
                            matched_word = match.group(0)
                            def _f_case_repl(m, repl=f_repl):
                                return repl.capitalize() if m.group(0)[0].isupper() else repl
                            ev.text = re.sub(m_pat, _f_case_repl, ev.text, flags=re.IGNORECASE)
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano 1. os. na rodzaj żeński dla mówczyni '{label_spk}' ('{matched_word}' -> '{f_repl}')")
                    def _morph_m_to_f_repl(m):
                        word = m.group(0)
                        converted = convert_first_person_masculine_to_feminine(word)
                        if converted and converted != word:
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano 1. os. na rodzaj żeński dla mówczyni '{label_spk}' ('{word}' -> '{converted}')")
                            return converted
                        return word
                    ev.text = re.sub(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łem|łbym)\b", _morph_m_to_f_repl, ev.text)
                    # Compound predicates for female speaker
                    for m_adj, f_adj in MASCULINE_SG_ADJECTIVES_TO_FEMININE.items():
                        pat_pred = rf"\b((?:byłam|byłem|czułam\s+się|czułem\s+się|zostałam|zostałem|poczułam\s+się|poczułem\s+się)\s+)({re.escape(m_adj)})\b"
                        for match in list(re.finditer(pat_pred, ev.text, re.IGNORECASE)):
                            p_prefix = match.group(1)
                            p_adj = match.group(2)
                            p_repl = f_adj.capitalize() if p_adj[0].isupper() else f_adj
                            ev.text = re.sub(rf"\b{re.escape(p_prefix)}{re.escape(p_adj)}\b", f"{p_prefix}{p_repl}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano orzecznik 1. os. na rodzaj żeński dla mówczyni '{label_spk}' ('{p_prefix}{p_adj}' -> '{p_prefix}{p_repl}')")
                    # Clitics for female speaker
                    clitic_pat = r"\b((?:gdybym|jakbym|żebym|abym|bym|choćbym|chociażbym)\s+)([A-Za-ząćęłńóśźż]+(?:ał|ił|ył|eł|ół|ął))\b"
                    for match in list(re.finditer(clitic_pat, ev.text, re.IGNORECASE)):
                        c_prefix = match.group(1)
                        c_verb = match.group(2)
                        c_fem = convert_masculine_past_to_feminine(c_verb)
                        if c_fem and c_fem.lower() != c_verb.lower():
                            ev.text = re.sub(rf"\b{re.escape(c_prefix)}{re.escape(c_verb)}\b", f"{c_prefix}{c_fem}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano klitykę 1. os. na rodzaj żeński dla mówczyni '{label_spk}' ('{c_prefix}{c_verb}' -> '{c_prefix}{c_fem}')")

                # 3c-2: 3rd-person subject-verb past-tense agreement (Filar CLXII)
                for char_lower, gender in char_gender_map.items():
                    if len(char_lower) < 3:
                        continue
                    
                    # 1. Forward search: [Name] ... [verb]
                    for m in list(re.finditer(rf"\b{re.escape(char_lower)}\b", ev.text, re.IGNORECASE)):
                        after_pos = m.end()
                        remainder = ev.text[after_pos:]
                        clause_match = re.match(r"^[^\.,!\?;—–-]+", remainder)
                        if clause_match:
                            clause_text = clause_match.group(0)
                            tokens = list(re.finditer(r"\b[A-Za-ząćęłńóśźż]+\b", clause_text))
                            for tok in tokens[:4]:  # check within next 4 words in clause
                                w = tok.group(0)
                                if gender == "MALE":
                                    new_v = convert_feminine_past_to_masculine(w)
                                elif gender == "FEMALE":
                                    new_v = convert_masculine_past_to_feminine(w)
                                else:
                                    new_v = None

                                if new_v and new_v.lower() != w.lower():
                                    abs_start = after_pos + tok.start()
                                    abs_end = after_pos + tok.end()
                                    matched_name = m.group(0)
                                    ev.text = ev.text[:abs_start] + new_v + ev.text[abs_end:]
                                    fixes.append(
                                        f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: "
                                        f"skorygowano orzeczenie 3. osoby '{matched_name}... {w}' -> '{matched_name}... {new_v}' "
                                        f"(potwierdzona płeć {'męska' if gender == 'MALE' else 'żeńska'})"
                                    )
                                    break

                    # 2. Inverted search: [verb] ... [Name]
                    for m in list(re.finditer(rf"\b{re.escape(char_lower)}\b", ev.text, re.IGNORECASE)):
                        before_pos = m.start()
                        prefix = ev.text[:before_pos]
                        clause_match = re.search(r"[^\.,!\?;—–-]+$", prefix)
                        if clause_match:
                            clause_text = clause_match.group(0)
                            tokens = list(re.finditer(r"\b[A-Za-ząćęłńóśźż]+\b", clause_text))
                            for tok in reversed(tokens[-4:]):  # check backwards within last 4 words in clause
                                w = tok.group(0)
                                if gender == "MALE":
                                    new_v = convert_feminine_past_to_masculine(w)
                                elif gender == "FEMALE":
                                    new_v = convert_masculine_past_to_feminine(w)
                                else:
                                    new_v = None

                                if new_v and new_v.lower() != w.lower():
                                    abs_start = clause_match.start() + tok.start()
                                    abs_end = clause_match.start() + tok.end()
                                    matched_name = m.group(0)
                                    ev.text = ev.text[:abs_start] + new_v + ev.text[abs_end:]
                                    fixes.append(
                                        f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: "
                                        f"skorygowano orzeczenie szyku przestawnego '{w}... {matched_name}' -> '{new_v}... {matched_name}' "
                                        f"(potwierdzona płeć {'męska' if gender == 'MALE' else 'żeńska'})"
                                    )
                                    break

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

                else:
                    # 2ND-PERSON SINGULAR ADDRESSEE AGREEMENT (kobieta vs mężczyzna)
                    is_single_female = False
                    is_single_male = False

                    if addr_norm in ["kobieta", "female", "dziewczyna"] or any(k in addr_norm for k in ["(kobieta)", "(female)"]):
                        is_single_female = True
                    elif addr_norm in ["mężczyzna", "male", "chłopak"] or any(k in addr_norm for k in ["(mężczyzna)", "(male)"]):
                        # Check if male addressee was derived from a contaminated tag in a female scene
                        cand_addr_name = re.sub(r"\s*\(.*?\)", "", raw_ev_addressee or "").strip()
                        is_cont_addr = False
                        if series_bible and hasattr(series_bible, "audit_speaker_metadata_against_audio") and cand_addr_name:
                            _, is_cont_addr = series_bible.audit_speaker_metadata_against_audio(cand_addr_name, scene_gender=event_scene_gender.get(i))
                        if is_cont_addr or event_scene_gender.get(i) == "FEMALE":
                            is_single_female = True
                            is_single_male = False
                        else:
                            is_single_male = True
                    else:
                        # Check character vocative in line
                        if character_registry:
                            for cname, cdesc in character_registry.items():
                                if len(cname) >= 3 and re.search(rf"\b{re.escape(cname)}[!,\?]", clean_ev_text, re.IGNORECASE):
                                    cdesc_l = cdesc.lower()
                                    if any(k in cdesc_l for k in ["kobieta", "female", "dziewczyn", "nauczycielka", "uczennica", "kapłanka"]):
                                        is_single_female = True
                                        break
                                    elif any(k in cdesc_l for k in ["mężczyzna", "male", "chłopak", "żołnierz", "rycerz"]):
                                        is_single_male = True
                                        break
                        if not is_single_female and not is_single_male:
                            if re.search(r"\b(dziewczyno|kobieto|panienko|siostro|mamo)[!,\?]", clean_ev_text, re.IGNORECASE):
                                is_single_female = True
                            elif re.search(r"\b(chłopcze|młodzieńcze|bracie|ojcze|tato)[!,\?]", clean_ev_text, re.IGNORECASE):
                                is_single_male = True

                        if not is_single_female and not is_single_male and series_bible and hasattr(series_bible, "get_character_gender") and raw_ev_addressee:
                            cand_name = re.sub(r"\s*\(.*?\)", "", raw_ev_addressee).strip()
                            if cand_name and not is_generic_actor_or_category(cand_name):
                                bg = series_bible.get_character_gender(cand_name, allow_generic_nouns=False)
                                if bg == "FEMALE":
                                    is_single_female = True
                                elif bg == "MALE":
                                    is_single_male = True

                        if not is_single_female and not is_single_male:
                            jp_aud = (whisper_transcriptions.get(i + 1, "") if whisper_transcriptions else "") or (getattr(ev, "audio_jp", "") or "")
                            if jp_aud:
                                try:
                                    from whisper_disambiguator import WhisperDisambiguator
                                    wtag = WhisperDisambiguator.disambiguate_line(
                                        clean_en=clean_ev_text,
                                        jp_audio=jp_aud,
                                        speaker=getattr(ev, "name", ""),
                                        character_registry=character_registry,
                                        series_bible=series_bible
                                    )
                                    if wtag and not wtag.addressee_is_group and wtag.addressee_gender:
                                        if wtag.addressee_gender == "FEMALE":
                                            is_single_female = True
                                        elif wtag.addressee_gender == "MALE":
                                            is_single_male = True
                                except Exception:
                                    pass

                    scene_cast_female_only = (event_scene_gender.get(i) == "FEMALE")
                    scene_cast_male_only = (event_scene_gender.get(i) == "MALE")
                    if not is_single_female and not is_single_male and not scene_cast_female_only and not scene_cast_male_only:
                        # Scene-Level Cast Gender Concordance:
                        # If all named speakers in the contiguous scene window (+/- 8 events or within 20s) are confirmed female,
                        # any 2nd-person address is addressing a female character.
                        nearby_speakers = set()
                        for offset in range(-8, 9):
                            idx = i + offset
                            if 0 <= idx < len(events):
                                ev_near = events[idx]
                                act_near = getattr(ev_near, "name", None) or getattr(ev_near, "actor", None) or (line_speakers.get(idx) if line_speakers else None)
                                if act_near and not is_generic_actor_or_category(str(act_near)):
                                    cl_spk = extract_clean_speaker_name(str(act_near))
                                    if len(cl_spk) >= 3:
                                        nearby_speakers.add(cl_spk)
                        if nearby_speakers:
                            all_females = True
                            all_males = True
                            for spk_cand in nearby_speakers:
                                cand_g = char_gender_map.get(spk_cand.lower())
                                if not cand_g and series_bible and hasattr(series_bible, "get_character_gender"):
                                    cand_g = series_bible.get_character_gender(spk_cand, allow_generic_nouns=False)
                                if cand_g != "FEMALE":
                                    all_females = False
                                if cand_g != "MALE":
                                    all_males = False
                            if all_females and len(nearby_speakers) >= 1:
                                scene_cast_female_only = True
                            elif all_males and len(nearby_speakers) >= 1:
                                scene_cast_male_only = True

                    is_confirmed_single = (is_single_female or is_single_male) and not (is_female_group or is_male_group or is_mixed_group)

                    # Dyadic Addressee Number Concordance Gate (Filar CLXIII - 0.00 PLN)
                    # Harmonize leaking 2nd-person plural forms into confirmed dyadic dialogue (Taxonomy K1-K6 + Prepositional & Verbal Extensions)
                    if is_confirmed_single:
                        src_text = ""
                        if source_subs and hasattr(source_subs, "events") and i < len(source_subs.events):
                            src_text = getattr(source_subs.events[i], "plaintext", None) or getattr(source_subs.events[i], "text", "") or ""

                        has_explicit_plural = bool(re.search(
                            r"\b(wszyscy|wszystkie|wszystkim|wszystkich|kochani|panowie|panie|dziewczęta|chłopcy|ludzie|zebrani|przyjaciele|rodzice|państwo)\b",
                            clean_ev_text, re.IGNORECASE
                        )) or bool(re.search(
                            r"\b(everyone|everybody|guys|all of you|team|class|ladies and gentlemen|minna|tachi|zen'in|shokun|omae-ra|kisama-ra)\b",
                            src_text, re.IGNORECASE
                        ))

                        if not has_explicit_plural:
                            old_dyadic_t = ev.text
                            # K1: Wyjaśnienia i deklaracje relacyjne (opowiem/powiem/wyjaśnię wam -> ci)
                            def _repl_k1(m):
                                prefix = m.group(1)
                                to_part = m.group(2) or ""
                                verb = m.group(3)
                                if prefix:
                                    return f"{prefix} ci {to_part}{verb}"
                                matched = m.group(0)
                                if matched and matched[0].isupper():
                                    return f"Ci {to_part}{verb}"
                                return f"ci {to_part}{verb}"

                            ev.text = re.sub(
                                r"\b(zaraz\s+wszystko|wszystko|to\s+wszystko|zaraz|już|chętnie)?\s*wam\s+(to\s+)?(opowiem|powiem|wyjaśnię|zdradzę|pokażę|nakreślę|wytłumaczę)\b",
                                _repl_k1,
                                ev.text,
                                flags=re.IGNORECASE
                            )
                            ev.text = re.sub(
                                r"\b(opowiem|powiem|wyjaśnię|zdradzę|pokażę|nakreślę|wytłumaczę)\s+wam\b",
                                lambda m: f"{m.group(1)} ci",
                                ev.text,
                                flags=re.IGNORECASE
                            )

                            # K2: Zwroty wdzięczności i zależności (dzięki wam -> dzięki tobie)
                            ev.text = re.sub(
                                r"\b(to\s+wszystko\s+)?dzięki\s+wam\b",
                                lambda m: (m.group(1) or "") + ("Dzięki tobie" if m.group(0).startswith("D") else "dzięki tobie"),
                                ev.text,
                                flags=re.IGNORECASE
                            )

                            # K3: Konstrukcje afektywne i celownikowe (na was mi zależy -> na tobie mi zależy, wam zależy -> tobie zależy)
                            ev.text = re.sub(
                                r"\bWam\s+(na\s+tym\s+zależy|zależy)\b",
                                r"Tobie \1",
                                ev.text
                            )
                            ev.text = re.sub(
                                r"\bwam\s+(na\s+tym\s+zależy|zależy)\b",
                                r"tobie \1",
                                ev.text
                            )
                            ev.text = re.sub(
                                r"\bNa\s+was\s+(mi\s+zależy|zależy)\b",
                                r"Na tobie \1",
                                ev.text
                            )
                            ev.text = re.sub(
                                r"\bna\s+was\s+(mi\s+zależy|zależy)\b",
                                r"na tobie \1",
                                ev.text
                            )
                            ev.text = re.sub(r"\bzależy\s+wam\b", "zależy ci", ev.text, flags=re.IGNORECASE)
                            ev.text = re.sub(r"\b(ufałem|ufałam|wierzyłem|wierzyłam)\s+wam\b", r"\1 tobie", ev.text, flags=re.IGNORECASE)

                            # K4: Zwroty modalne i zobowiązania (muszę/chcę was prosić -> muszę/chcę cię prosić, błagam was -> błagam cię)
                            ev.text = re.sub(r"\b(muszę|chcę|pragnę)\s+was\s+(o\s+coś\s+)?(prosić|poprosić)\b", r"\1 cię \2\3", ev.text, flags=re.IGNORECASE)
                            ev.text = re.sub(r"\b(błagam|proszę|przepraszam)\s+was\b", r"\1 cię", ev.text, flags=re.IGNORECASE)

                            # K5: Dyrektywy deeskalacyjne / imperatywy (uspokójcie się -> uspokój się, posłuchajcie mnie -> posłuchaj mnie)
                            ev.text = re.sub(r"\b(uspokój|czekaj|poczekaj|zaczekaj|posłuchaj|spójrz|wybacz)cie\b", r"\1", ev.text, flags=re.IGNORECASE)

                            # K6 & Rozszerzenia przyimkowe (Prepositional Plural Harmonization)
                            # Prepositions + was -> ciebie
                            ev.text = re.sub(r"\b([Dd]o|[Oo]d|[Uu]|[Dd]la|[Oo]|[Bb]ez|[Pp]rzez)\s+was\b", lambda m: f"{m.group(1)} ciebie", ev.text)
                            # Prepositions + wami -> tobą
                            ev.text = re.sub(r"\b([Zz]|[Zz]a|[Pp]rzed|[Nn]ad|[Pp]od)\s+wami\b", lambda m: f"{m.group(1)} tobą", ev.text)
                            # Przeciw / przeciwko wam -> tobie
                            ev.text = re.sub(r"\b([Pp]rzeciw(?:ko)?)\s+wam\b", lambda m: f"{m.group(1)} tobie", ev.text)

                            # Verb + wam -> ci (dative) across dialogue verbs
                            ev.text = re.sub(
                                r"\b(dam|daję|dałem|dałam|mówię|mówiłem|mówiłam|powiedziałem|powiedziałam|pomogę|pomagałem|pomagałam|radzę|poradziłem|poradziłam|życzę|obiecuję|obiecałem|obiecałam|przysięgam|przysięgłem|przysięgłam|przyniosę|przyniosłem|przyniosłam|zazdroszczę|dziękuję|podziękowałem|podziękowałam|współczuję|pozwolę|odpowiem|odpowiedziałem|odpowiedziałam)\s+wam\b",
                                r"\1 ci",
                                ev.text,
                                flags=re.IGNORECASE
                            )
                            # General modal / auxiliary + wam -> ci
                            ev.text = re.sub(
                                r"\b(chcę|muszę|mogę|pragnę|zamierzam)\s+wam\b",
                                r"\1 ci",
                                ev.text,
                                flags=re.IGNORECASE
                            )
                            # Inquiries: co wam (jest/dolega) -> co ci (jest/dolega)
                            ev.text = re.sub(r"\b([Cc]o|[Ww]\s+czym)\s+wam\b", r"\1 ci", ev.text)

                            # Accusative verbs + was -> cię
                            ev.text = re.sub(
                                r"\b(widzę|widziałem|widziałam|znam|znałem|znałam|kocham|kochałem|kochałam|lubię|lubiłem|lubiłam|uratuję|uratowałem|uratowałam|ocalę|ocaliłem|ocaliłam|zostawię|zostawiłem|zostawiłam|znajdę|znalazłem|znalazłam|słyszę|słyszałem|słyszałam|zabiję|zabijam)\s+was\b",
                                r"\1 cię",
                                ev.text,
                                flags=re.IGNORECASE
                            )

                            # Nominative / Vocative wy -> ty
                            ev.text = re.sub(r"\b([Aa])\s+wy\b", r"\1 ty", ev.text)
                            ev.text = re.sub(r"\b([Cc]o)\s+wy\s+na\s+to\b", r"\1 ty na to", ev.text)

                            # Initial Wam to -> Ci to (Test 89 case: Wam to powiem -> Ci to powiem)
                            ev.text = re.sub(r"\bWam\s+to\b", "Ci to", ev.text)

                            if ev.text != old_dyadic_t:
                                clean_ev_text = re.sub(r"\{[^\}]*\}", "", ev.text)
                                fixes.append(
                                    f"[Episode Quality Gate - Filar CLXIII Zgodność Liczby w Relacji Diadycznej] Linia #{i+1}: "
                                    f"zharmonizowano formę 2. os. l. mn. -> l. poj. w dialogu 1-na-1: '{old_dyadic_t}' -> '{ev.text}'"
                                )

                    if (is_single_female or scene_cast_female_only) and not is_single_male:
                        # 1. Convert masculine 2nd-person singular past/conditional/modal verbs -> feminine
                        ev.text = re.sub(r"\bpowinieneś\s+był\b", "powinnaś była", ev.text)
                        for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+(?:łeś|łbyś)|powinieneś)\b", ev.text)):
                            v_masc = m.group(1)
                            v_fem = convert_2nd_person_masculine_to_feminine(v_masc)
                            if v_fem and v_fem.lower() != v_masc.lower():
                                ev.text = re.sub(rf"\b{re.escape(v_masc)}\b", v_fem, ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Morfologia Żeńska 2. os. lp.] Linia #{i+1}: skorygowano formę męską '{v_masc}' -> '{v_fem}' (adresat: kobieta)")

                        # 2. Convert masculine adjectives / participles -> feminine (supporting intensifiers like 'taki/taka' and 'wyglądasz')
                        for m_adj, f_adj in MASCULINE_SG_ADJECTIVES_TO_FEMININE.items():
                            pat_adj = rf"\b((?:byłaś|byłeś|jesteś|bądź|zostałaś|zostałeś|zostań|będziesz|czujesz\s+się|wydajesz\s+się|stajesz\s+się|wyglądasz|nie\s+wyglądasz|[A-Za-ząćęłńóśźż]+(?:łeś|łaś|łbyś|łabyś)(?:\s+\w+)?)\s+(?:taki\s+|taka\s+|zbyt\s+|tak\s+|bardzo\s+|dość\s+)?)({re.escape(m_adj)})\b"
                            for m in list(re.finditer(pat_adj, ev.text, re.IGNORECASE)):
                                prefix = m.group(1)
                                old_adj = m.group(2)
                                repl_adj = f_adj.capitalize() if old_adj[0].isupper() else f_adj
                                new_prefix = re.sub(r"\btaki\s*$", "taka ", prefix)
                                ev.text = re.sub(rf"\b{re.escape(prefix)}{re.escape(old_adj)}\b", f"{new_prefix}{repl_adj}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Przymiotnik Żeński 2. os. lp.] Linia #{i+1}: skorygowano '{prefix}{old_adj}' -> '{new_prefix}{repl_adj}' (adresat: kobieta)")

                        # 3. Convert masculine prepositional predicate adjectives (wyglądasz na wzburzonego -> wyglądasz na wzburzoną)
                        prep_adj_pat = r"\b((?:nie\s+)?(?:wyglądasz|sprawiasz\s+wrażenie)\s+na)\s+([A-Za-ząćęłńóśźż]{3,})ego\b"
                        for m in list(re.finditer(prep_adj_pat, ev.text, re.IGNORECASE)):
                            prefix = m.group(1)
                            adj_stem = m.group(2)
                            adj_stem_l = adj_stem.lower()
                            if adj_stem_l not in {"cz", "k", "dlacz", "tamt", "t", "nicz", "jakieś", "wszystki", "jedn"}:
                                repl_word = adj_stem + "ą"
                                ev.text = re.sub(rf"\b{re.escape(prefix)}\s+{re.escape(adj_stem)}ego\b", f"{prefix} {repl_word}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLVII/CLXIII Orzecznik Przymiotnikowy Żeński] Linia #{i+1}: skorygowano '{prefix} {adj_stem}ego' -> '{prefix} {repl_word}' (adresat: kobieta)")

                    elif (is_single_male or scene_cast_male_only) and not is_single_female:
                        # 1. Convert feminine 2nd-person singular past/conditional/modal verbs -> masculine
                        ev.text = re.sub(r"\bpowinnaś\s+była\b", "powinieneś był", ev.text)
                        for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+(?:łaś|łabyś)|powinnaś)\b", ev.text)):
                            v_fem = m.group(1)
                            v_masc = convert_2nd_person_feminine_to_masculine(v_fem)
                            if v_masc and v_masc.lower() != v_fem.lower():
                                ev.text = re.sub(rf"\b{re.escape(v_fem)}\b", v_masc, ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Morfologia Męska 2. os. lp.] Linia #{i+1}: skorygowano formę żeńską '{v_fem}' -> '{v_masc}' (adresat: mężczyzna)")

                        # 2. Convert feminine adjectives / participles -> masculine (supporting intensifiers like 'taki/taka' and 'wyglądasz')
                        for f_adj, m_adj in FEMININE_SG_ADJECTIVES_TO_MASCULINE.items():
                            pat_adj = rf"\b((?:byłeś|byłaś|jesteś|bądź|zostałeś|zostałaś|zostań|będziesz|czujesz\s+się|wydajesz\s+się|stajesz\s+się|wyglądasz|nie\s+wyglądasz|[A-Za-ząćęłńóśźż]+(?:łeś|łaś|łbyś|łabyś)(?:\s+\w+)?)\s+(?:taki\s+|taka\s+|zbyt\s+|tak\s+|bardzo\s+|dość\s+)?)({re.escape(f_adj)})\b"
                            for m in list(re.finditer(pat_adj, ev.text, re.IGNORECASE)):
                                prefix = m.group(1)
                                old_adj = m.group(2)
                                repl_adj = m_adj.capitalize() if old_adj[0].isupper() else m_adj
                                new_prefix = re.sub(r"\btaka\s*$", "taki ", prefix)
                                ev.text = re.sub(rf"\b{re.escape(prefix)}{re.escape(old_adj)}\b", f"{new_prefix}{repl_adj}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Przymiotnik Męski 2. os. lp.] Linia #{i+1}: skorygowano '{prefix}{old_adj}' -> '{new_prefix}{repl_adj}' (adresat: mężczyzna)")

                        # 3. Convert feminine prepositional predicate adjectives (wyglądasz na wzburzoną -> wyglądasz na wzburzonego)
                        prep_adj_pat = r"\b((?:nie\s+)?(?:wyglądasz|sprawiasz\s+wrażenie)\s+na)\s+([A-Za-ząćęłńóśźż]{3,})ą\b"
                        for m in list(re.finditer(prep_adj_pat, ev.text, re.IGNORECASE)):
                            prefix = m.group(1)
                            adj_stem = m.group(2)
                            adj_stem_l = adj_stem.lower()
                            if adj_stem_l not in {"t", "tamt", "jedn", "inn", "sob", "mni"}:
                                repl_word = adj_stem + "ego"
                                ev.text = re.sub(rf"\b{re.escape(prefix)}\s+{re.escape(adj_stem)}ą\b", f"{prefix} {repl_word}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLVII/CLXIII Orzecznik Przymiotnikowy Męski] Linia #{i+1}: skorygowano '{prefix} {adj_stem}ą' -> '{prefix} {repl_word}' (adresat: mężczyzna)")

            # 3c-6. 1ST-PERSON PLURAL FEMININE GROUP AGREEMENT & SPEAKER ENTITY CONCORDANCE (Filar CLXXV & Filar CLXXVI - 0.00 PLN)
            if not is_sign:
                is_female_scene_1pl = (event_scene_gender.get(i) == "FEMALE")
                is_male_scene_1pl = (event_scene_gender.get(i) == "MALE")
                spk_orig = orig_speakers.get(i, "") or getattr(ev, "name", "") or getattr(ev, "actor", "")

                # Filar CLXXVI: Speaker Entity Identity Shield & Pluralis Maiestatis Gate (0.00 PLN)
                is_coll_virile = False
                is_coll_nonvirile = False
                is_majestic_fem = False
                is_majestic_masc = False

                if series_bible and hasattr(series_bible, "get_speaker_entity_type"):
                    ent_type = series_bible.get_speaker_entity_type(spk_orig)
                    if ent_type == "COLLECTIVE_VIRILE":
                        is_coll_virile = True
                    elif ent_type == "COLLECTIVE_NONVIRILE":
                        is_coll_nonvirile = True
                    elif ent_type == "MAJESTIC_FEMALE":
                        is_majestic_fem = True
                    elif ent_type == "MAJESTIC_MALE":
                        is_majestic_masc = True

                if not is_coll_virile and character_registry and spk_orig:
                    c_desc = character_registry.get(spk_orig, "").lower()
                    if any(w in c_desc for w in ["collective_virile", "żarłoczność", "zarlocznosc", "byt mnogi męskoosobowy", "byt zbiorowy męskoosobowy"]):
                        is_coll_virile = True
                    elif any(w in c_desc for w in ["majestic_female", "pluralis maiestatis (kobieta)", "monarchini"]):
                        is_majestic_fem = True

                # Apply Filar CLXXVI overrides:
                if is_coll_virile or is_majestic_masc:
                    # Immunity Shield: mixed/virile collective or male monarch cannot be overridden by female scene cast!
                    is_female_scene_1pl = False
                elif is_majestic_fem or is_coll_nonvirile:
                    # Sovereign Female / All-female collective enforces non-virile plural even in mixed/neutral scenes!
                    is_female_scene_1pl = True
                    is_male_scene_1pl = False
                elif not is_female_scene_1pl and series_bible and hasattr(series_bible, "is_female_group_speaker"):
                    is_female_scene_1pl = series_bible.is_female_group_speaker(spk_orig)

                if is_female_scene_1pl:
                    # 1. Convert virile 1st-person plural past tense verbs (-liśmy -> -łyśmy)
                    for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+liśmy)\b", ev.text)):
                        v_virile = m.group(1)
                        v_nonvirile = convert_1st_person_plural_virile_to_nonvirile(v_virile)
                        if v_nonvirile and v_nonvirile.lower() != v_virile.lower():
                            ev.text = re.sub(rf"\b{re.escape(v_virile)}\b", v_nonvirile, ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXXV Morfologia Niemęskoosobowa 1. os. lm.] Linia #{i+1}: skorygowano formę męskoosobową '{v_virile}' -> '{v_nonvirile}' (scena kobieca)")

                    # 2. Convert virile 1st-person plural conditional verbs (-libyśmy -> -łybyśmy)
                    for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+libyśmy)\b", ev.text)):
                        v_virile = m.group(1)
                        v_nonvirile = convert_1st_person_plural_conditional_virile_to_nonvirile(v_virile)
                        if v_nonvirile and v_nonvirile.lower() != v_virile.lower():
                            ev.text = re.sub(rf"\b{re.escape(v_virile)}\b", v_nonvirile, ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXXV Tryb Przypuszczający 1. os. lm.] Linia #{i+1}: skorygowano '{v_virile}' -> '{v_nonvirile}' (scena kobieca)")

                    # 3. Convert virile compound predicates and adjectives
                    for v_adj, nv_adj in VIRILE_ADJECTIVES_TO_NONVIRILE.items():
                        pat_pred = rf"\b((?:byliśmy|byłyśmy|bylibyśmy|byłybyśmy|jesteśmy|zostaliśmy|zostałyśmy|czujemy\s+się)\s+)({re.escape(v_adj)})\b"
                        for m in list(re.finditer(pat_pred, ev.text, re.IGNORECASE)):
                            prefix = m.group(1)
                            old_adj = m.group(2)
                            repl_adj = nv_adj.capitalize() if old_adj[0].isupper() else nv_adj
                            new_prefix = re.sub(r"\bbyliśmy\b", "byłyśmy", prefix, flags=re.IGNORECASE)
                            new_prefix = re.sub(r"\bbylibyśmy\b", "byłybyśmy", new_prefix, flags=re.IGNORECASE)
                            new_prefix = re.sub(r"\bzostaliśmy\b", "zostałyśmy", new_prefix, flags=re.IGNORECASE)
                            ev.text = re.sub(rf"\b{re.escape(prefix)}{re.escape(old_adj)}\b", f"{new_prefix}{repl_adj}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXXV Orzecznik Niemęskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{prefix}{old_adj}' -> '{new_prefix}{repl_adj}' (scena kobieca)")

                    # 4. Numerals and pronouns (1st-person plural requires 'my')
                    def _repl_my_dual(m):
                        is_cap = m.group(1).startswith("M")
                        repl = "My obie" if is_cap else "my obie"
                        fixes.append(f"[Episode Quality Gate - Filar CLXXV Liczebnik Podwójny 1. os. lm.] Linia #{i+1}: skorygowano '{m.group(0)}' -> '{repl}' (scena kobieca)")
                        return repl
                    ev.text = re.sub(r"\b([Mm]y\s+)(?:obaj|oboje)\b", _repl_my_dual, ev.text)

                    def _repl_my_same(m):
                        is_cap = m.group(1).startswith("M")
                        repl = "My same" if is_cap else "my same"
                        fixes.append(f"[Episode Quality Gate - Filar CLXXV Zaimek Niemęskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{m.group(0)}' -> '{repl}' (scena kobieca)")
                        return repl
                    ev.text = re.sub(r"\b([Mm]y\s+)sami\b", _repl_my_same, ev.text)

                elif is_male_scene_1pl:
                    # Symmetrical check for male scenes: convert non-virile 1st-person plural -> virile
                    for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+łyśmy)\b", ev.text)):
                        v_nonvirile = m.group(1)
                        v_virile = convert_1st_person_plural_nonvirile_to_virile(v_nonvirile)
                        if v_virile and v_virile.lower() != v_nonvirile.lower():
                            ev.text = re.sub(rf"\b{re.escape(v_nonvirile)}\b", v_virile, ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXXV Morfologia Męskoosobowa 1. os. lm.] Linia #{i+1}: skorygowano formę niemęskoosobową '{v_nonvirile}' -> '{v_virile}' (scena męska)")

                    for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+łybyśmy)\b", ev.text)):
                        v_nonvirile = m.group(1)
                        v_virile = convert_1st_person_plural_conditional_nonvirile_to_virile(v_nonvirile)
                        if v_virile and v_virile.lower() != v_nonvirile.lower():
                            ev.text = re.sub(rf"\b{re.escape(v_nonvirile)}\b", v_virile, ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXXV Tryb Przypuszczający 1. os. lm.] Linia #{i+1}: skorygowano '{v_nonvirile}' -> '{v_virile}' (scena męska)")

                    # Convert non-virile compound predicates and adjectives
                    for nv_adj, v_adj in NONVIRILE_ADJECTIVES_TO_VIRILE.items():
                        pat_pred = rf"\b((?:byłyśmy|byliśmy|byłybyśmy|bylibyśmy|jesteśmy|zostałyśmy|zostaliśmy|czujemy\s+się)\s+)({re.escape(nv_adj)})\b"
                        for m in list(re.finditer(pat_pred, ev.text, re.IGNORECASE)):
                            prefix = m.group(1)
                            old_adj = m.group(2)
                            repl_adj = v_adj.capitalize() if old_adj[0].isupper() else v_adj
                            new_prefix = re.sub(r"\bbyłyśmy\b", "byliśmy", prefix, flags=re.IGNORECASE)
                            new_prefix = re.sub(r"\bbyłybyśmy\b", "bylibyśmy", new_prefix, flags=re.IGNORECASE)
                            new_prefix = re.sub(r"\bzostałyśmy\b", "zostaliśmy", new_prefix, flags=re.IGNORECASE)
                            ev.text = re.sub(rf"\b{re.escape(prefix)}{re.escape(old_adj)}\b", f"{new_prefix}{repl_adj}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXXV Orzecznik Męskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{prefix}{old_adj}' -> '{new_prefix}{repl_adj}' (scena męska)")

                    # Numerals and pronouns (1st-person plural requires 'my')
                    def _repl_my_dual_m(m):
                        is_cap = m.group(1).startswith("M")
                        repl = "My obaj" if is_cap else "my obaj"
                        fixes.append(f"[Episode Quality Gate - Filar CLXXV Liczebnik Podwójny 1. os. lm.] Linia #{i+1}: skorygowano '{m.group(0)}' -> '{repl}' (scena męska)")
                        return repl
                    ev.text = re.sub(r"\b([Mm]y\s+)obie\b", _repl_my_dual_m, ev.text)

                    def _repl_my_sami_m(m):
                        is_cap = m.group(1).startswith("M")
                        repl = "My sami" if is_cap else "my sami"
                        fixes.append(f"[Episode Quality Gate - Filar CLXXV Zaimek Męskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{m.group(0)}' -> '{repl}' (scena męska)")
                        return repl
                    ev.text = re.sub(r"\b([Mm]y\s+)same\b", _repl_my_sami_m, ev.text)

            # 3c-5. WHISPER DETERMINISTIC DISAMBIGUATION INTEGRITY (K1-K8 - 0.00 PLN)
            if not is_sign:
                jp_audio = (whisper_transcriptions.get(i + 1, "") if whisper_transcriptions else "") or (getattr(ev, "audio_jp", "") or "")
                src_en = getattr(ev, "source_en", "") or (getattr(source_subs.events[i], "text", "") if source_subs and hasattr(source_subs, "events") and i < len(source_subs.events) else "")
                prev_src_en = (getattr(source_subs.events[i - 1], "text", "") if source_subs and hasattr(source_subs, "events") and i > 0 and len(source_subs.events) > i - 1 else "")

                if jp_audio:
                    try:
                        from whisper_disambiguator import WhisperDisambiguator
                        wdd_tag = WhisperDisambiguator.disambiguate_line(
                            clean_en=src_en,
                            jp_audio=jp_audio,
                            speaker=getattr(ev, "name", "") or getattr(ev, "actor", ""),
                            character_registry=character_registry,
                            series_bible=series_bible,
                            prev_clean_en=prev_src_en,
                            prev_clean_pl=prev_clean
                        )

                        # K6 Polar agreement audit: Preceding question had negation, seiyū said 'hai'/'un', Polish draft said 'Tak'/'T-Tak'
                        if wdd_tag.polar_agreement:
                            if re.search(r"^(\s*(?:\{[^\}]*\}\s*)*)(?:Tak|T-Tak)[,!\.]\s*", ev.text, re.IGNORECASE):
                                old_pol_t = ev.text
                                ev.text = re.sub(r"^(\s*(?:\{[^\}]*\}\s*)*)(?:Tak|T-Tak)[,!\.]\s*", r"\1Nie. ", ev.text, flags=re.IGNORECASE)
                                if ev.text != old_pol_t:
                                    fixes.append(f"[Episode Quality Gate - Filar CLIV Echo Agreement / Whisper K6] Linia #{i+1}: skorygowano fałszywe 'Tak' po pytaniu z przeczeniem -> 'Nie'")

                        # K4 Kinship sanity audit: Seiyū used 'aniki'/'onii-san' but text translated as 'młodszy brat'
                        if wdd_tag.kinship_term:
                            if "starsz" in wdd_tag.kinship_term.lower():
                                if re.search(r"\bmłodsz(?:y|ego|emu|ym)\s+(?:brat|brata|bratu|bratem|bracie)\b", ev.text, re.IGNORECASE):
                                    old_k_t = ev.text
                                    ev.text = re.sub(r"\bmłodsz(y|ego|emu|ym)(\s+(?:brat|brata|bratu|bratem|bracie))\b", r"starsz\1\2", ev.text, flags=re.IGNORECASE)
                                    if ev.text != old_k_t:
                                        fixes.append(f"[Episode Quality Gate - Filar CLXXI Pokrewieństwo / Whisper K4] Linia #{i+1}: skorygowano stopień starszeństwa na 'starszy brat' (audio: aniki/onii-san)")
                                elif re.search(r"\bmłodsz(?:a|ej|ą)\s+(?:siostra|siostry|siostrze|siostrę|siostrą)\b", ev.text, re.IGNORECASE):
                                    old_k_t = ev.text
                                    ev.text = re.sub(r"\bmłodsz(a|ej|ą)(\s+(?:siostra|siostry|siostrze|siostrę|siostrą))\b", r"starsz\1\2", ev.text, flags=re.IGNORECASE)
                                    if ev.text != old_k_t:
                                        fixes.append(f"[Episode Quality Gate - Filar CLXXI Pokrewieństwo / Whisper K4] Linia #{i+1}: skorygowano stopień starszeństwa na 'starsza siostra' (audio: onee-san)")
                            elif "młodsz" in wdd_tag.kinship_term.lower():
                                if re.search(r"\bstarsz(?:y|ego|emu|ym)\s+(?:brat|brata|bratu|bratem|bracie)\b", ev.text, re.IGNORECASE):
                                    old_k_t = ev.text
                                    ev.text = re.sub(r"\bstarsz(y|ego|emu|ym)(\s+(?:brat|brata|bratu|bratem|bracie))\b", r"młodsz\1\2", ev.text, flags=re.IGNORECASE)
                                    if ev.text != old_k_t:
                                        fixes.append(f"[Episode Quality Gate - Filar CLXXI Pokrewieństwo / Whisper K4] Linia #{i+1}: skorygowano stopień starszeństwa na 'młodszy brat' (audio: otouto)")
                                elif re.search(r"\bstarsz(?:a|ej|ą)\s+(?:siostra|siostry|siostrze|siostrę|siostrą)\b", ev.text, re.IGNORECASE):
                                    old_k_t = ev.text
                                    ev.text = re.sub(r"\bstarsz(a|ej|ą)(\s+(?:siostra|siostry|siostrze|siostrę|siostrą))\b", r"młodsz\1\2", ev.text, flags=re.IGNORECASE)
                                    if ev.text != old_k_t:
                                        fixes.append(f"[Episode Quality Gate - Filar CLXXI Pokrewieństwo / Whisper K4] Linia #{i+1}: skorygowano stopień starszeństwa na 'młodsza siostra' (audio: imouto)")

                    except Exception:
                        pass

            # 3c-4. DUAL AND COLLECTIVE NUMERAL AGREEMENT (Filar CLXXIII - 0.00 PLN)
            if not is_sign and re.search(r"\b(oboje|obojga|obojgu|obojgiem|obaj|obydwaj|obie|obydwie)\b", ev.text, re.IGNORECASE):
                # Detect whether referents are two female characters
                is_female_dual = False

                # Check 1: In the same line, feminine plural past tense or 2 female entities mentioned
                clean_line_lower = re.sub(r"\{[^\}]*\}", "", ev.text).lower()
                if re.search(r"\b[a-ząćęłńóśźż]+(?:ły|łyście|łyśmy)\b", clean_line_lower):
                    is_female_dual = True

                # Check 2: Context scan (previous 10 dialogue events in current scene):
                # Search for mentions of two female characters (e.g. 'ty i Töregene', 'Fatima i Töregene')
                if not is_female_dual:
                    context_corpus = []
                    for k in range(max(0, i - 10), i):
                        cand_prev = events[k]
                        if cand_prev.text and (ev.start - cand_prev.end < 25000):
                            context_corpus.append(re.sub(r"\{[^\}]*\}", "", cand_prev.text))
                    joined_ctx = " ".join(context_corpus).lower()

                    # Detect co-occurrence of female names or female relationship
                    female_names_found = set()
                    for f_name, f_gen in char_gender_map.items():
                        if f_gen == "FEMALE" and len(f_name) >= 3 and f_name in joined_ctx:
                            female_names_found.add(f_name)
                    if len(female_names_found) >= 2:
                        is_female_dual = True
                    elif any(p in joined_ctx for p in ["ty i töregene", "ty i toregene", "töregene i ty", "fatima i töregene", "fatimie i töregene", "odnalazły", "odnalazłyście"]):
                        is_female_dual = True

                if not is_female_dual and event_scene_gender.get(i) == "FEMALE":
                    is_female_dual = True

                if is_female_dual:
                    def _repl_dual_fem(m):
                        word = m.group(1)
                        is_upper = word[0].isupper()
                        w_l = word.lower()
                        if w_l == "oboje":
                            res = "obie"
                        elif w_l in ("obojga", "obojgu"):
                            res = "obu"
                        elif w_l == "obojgiem":
                            res = "obiema"
                        else:
                            res = "obie"
                        return res.capitalize() if is_upper else res

                    old_dual_t = ev.text
                    ev.text = re.sub(r"\b(oboje|obojga|obojgu|obojgiem)\b", _repl_dual_fem, ev.text, flags=re.IGNORECASE)
                    ev.text = re.sub(r"\b([Ww]y\s+)?obaj\b", lambda m: ("Wy obie" if m.group(1) and m.group(1).startswith("W") else "wy obie") if m.group(1) else ("Obie" if m.group(0).startswith("O") else "obie"), ev.text)
                    ev.text = re.sub(r"\b([Ww]y\s+)?obydwaj\b", lambda m: ("Wy obydwie" if m.group(1) and m.group(1).startswith("W") else "wy obydwie") if m.group(1) else ("Obydwie" if m.group(0).startswith("O") else "obydwie"), ev.text)
                    ev.text = re.sub(r"\b([Dd]la\s+was\s+)obojga\b", r"\1obu", ev.text)
                    ev.text = re.sub(r"\b([Ww]as\s+)oboje\b", r"\1obie", ev.text)
                    ev.text = re.sub(r"\bwas\s+obie\b", "was obie", ev.text)
                    ev.text = re.sub(r"\bich\s+obie\b", "je obie", ev.text)
                    if ev.text != old_dual_t:
                        fixes.append(f"[Episode Quality Gate - Filar CLXII Zgodność Liczebników Podwójnych] Linia #{i+1}: skorygowano 'oboje' -> 'obie' (referenci: 2 kobiety)")
                else:
                    is_male_dual = False
                    if re.search(r"\b[a-ząćęłńóśźż]+(?:li|liście|liśmy)\b", clean_line_lower) or event_scene_gender.get(i) == "MALE":
                        is_male_dual = True
                    if is_male_dual:
                        old_dual_m = ev.text
                        ev.text = re.sub(r"\b([Ww]y\s+)?obie\b", lambda m: ("Wy obaj" if m.group(1) and m.group(1).startswith("W") else "wy obaj") if m.group(1) else ("Obaj" if m.group(0).startswith("O") else "obaj"), ev.text)
                        ev.text = re.sub(r"\b([Ww]y\s+)?obydwie\b", lambda m: ("Wy obydwaj" if m.group(1) and m.group(1).startswith("W") else "wy obydwaj") if m.group(1) else ("Obydwaj" if m.group(0).startswith("O") else "obydwaj"), ev.text)
                        if ev.text != old_dual_m:
                            fixes.append(f"[Episode Quality Gate - Filar CLXII Zgodność Liczebników Podwójnych] Linia #{i+1}: skorygowano liczebnik na rodzaj męski (referenci: 2 mężczyzn)")

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
            if not is_sign and compiled_decl_rules:
                clean_lower = re.sub(r"\{[^\}]*\}", "", ev.text).lower()
                for r in compiled_decl_rules:
                    # Fast rejection: only run regexes if character name or stem appears in text
                    if r["m_lower"] not in clean_lower and r["stem_lower"] not in clean_lower:
                        continue

                    if "re_n" in r:
                        n_form = r["n_form"]
                        def _repl_n(m, target=n_form):
                            matched_prep = m.group(1).lower()
                            # Dual-governance preposition 'za': in marriage, exchange, substitution, perception
                            # 'za' governs Accusative (Biernik), NOT Instrumental (Narzędnik)!
                            if matched_prep == "za":
                                before_text = ev.text[:m.start()]
                                if re.search(r"\b(?:wyjść|wyjdzie|wyszła|wyszło|wyszli|wyjście|wyjścia|wychodzić|wychodzi|wziąć|brać|weźmie|oddać|odda|oddał|zapłacić|płacić|uznać|uznaje|uważać|uważa|uchodzić|uchodzi|mieć|odpowiadać|odpowiada|trzymać|złapać|chwycić|dziękować|przepraszać)\s+(?:zaś\s+|zaraz\s+|chyba\s+|tam\s+)?$", before_text, re.IGNORECASE):
                                    return m.group(0)
                            matched = m.group(3)
                            tgt = target.upper() if matched.isupper() else (target.capitalize() if matched.istitle() else target)
                            return f"{m.group(1)}{m.group(2)}{tgt}"
                        old_t = ev.text
                        ev.text = r["re_n"].sub(_repl_n, ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Matryca Narzędnika] Linia #{i+1}: ujednolicono formę na '{n_form}' po przyimku narzędnika")

                    if "re_prep_d" in r:
                        d_form = r["d_form"]
                        def _repl_prep_d(m, target=d_form, c_name=r["name"]):
                            matched = m.group(3)
                            if matched.lower() == target.lower():
                                return m.group(0)
                            if len(matched) > len(c_name) + 3:
                                return m.group(0)
                            tgt = target.upper() if matched.isupper() else (target.capitalize() if matched.istitle() else target)
                            return f"{m.group(1)}{m.group(2)}{tgt}"
                        old_t = ev.text
                        ev.text = r["re_prep_d"].sub(_repl_prep_d, ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Matryca Dopełniacza] Linia #{i+1}: ujednolicono formę na '{d_form}' po przyimku dopełniacza")

                    if "re_pos_d" in r:
                        d_form = r["d_form"]
                        def _repl_pos_d(m, target=d_form):
                            lead_word = m.group(1).lower()
                            if lead_word in {"pan", "pani", "mistrz", "profesor", "doktor", "sensei", "autor", "redaktor", "mangaka", "pisarz"}:
                                return m.group(0)
                            matched = m.group(3)
                            tgt = target.upper() if matched.isupper() else (target.capitalize() if matched.istitle() else target)
                            return f"{m.group(1)}{m.group(2)}{tgt}"
                        old_t = ev.text
                        ev.text = r["re_pos_d"].sub(_repl_pos_d, ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Dopełniacz Dzierżawczy] Linia #{i+1}: ujednolicono formę na '{d_form}' po określeniu dzierżawczym/rządzącym")

                    if "re_c" in r:
                        c_form = r["c_form"]
                        def _repl_c(m, target=c_form):
                            matched = m.group(3)
                            tgt = target.upper() if matched.isupper() else (target.capitalize() if matched.istitle() else target)
                            return f"{m.group(1)}{m.group(2)}{tgt}"
                        old_t = ev.text
                        ev.text = r["re_c"].sub(_repl_c, ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Matryca Celownika] Linia #{i+1}: ujednolicono formę na '{c_form}' po przyimku celownika")

                    if "re_ms" in r:
                        ms_form = r["ms_form"]
                        def _repl_ms(m, target=ms_form):
                            matched = m.group(3)
                            tgt = target.upper() if matched.isupper() else (target.capitalize() if matched.istitle() else target)
                            return f"{m.group(1)}{m.group(2)}{tgt}"
                        old_t = ev.text
                        ev.text = r["re_ms"].sub(_repl_ms, ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Matryca Miejscownika] Linia #{i+1}: ujednolicono formę na '{ms_form}' po przyimku miejscownika")

                    # Deterministic Vocative
                    if "w_form" in r:
                        w_form = r["w_form"]
                        if "re_end_voc" in r:
                            def _repl_end_voc(m, target=w_form):
                                sep = m.group(1)
                                matched = m.group(2)
                                punct = m.group(3) or ""
                                tgt = target.upper() if matched.isupper() else target
                                return f"{sep}{tgt}{punct}"
                            old_t = ev.text
                            ev.text = r["re_end_voc"].sub(_repl_end_voc, ev.text)
                            if ev.text != old_t:
                                fixes.append(f"[Episode Quality Gate - Wołacz Adresatywny] Linia #{i+1}: ujednolicono wołacz na '{w_form}' w zwrocie bezpośrednim po przecinku")

                        if "re_intro_voc" in r:
                            def _repl_intro_voc(m, target=w_form):
                                intro = m.group(1)
                                matched = m.group(2)
                                punct = m.group(3) or ""
                                tgt = target.upper() if matched.isupper() else target
                                return f"{intro}{tgt}{punct}"
                            old_t = ev.text
                            ev.text = r["re_intro_voc"].sub(_repl_intro_voc, ev.text)
                            if ev.text != old_t:
                                fixes.append(f"[Episode Quality Gate - Wołacz Inwokacyjny] Linia #{i+1}: ujednolicono wołacz na '{w_form}' po zwrocie inwokacyjnym")

                        if "re_lead_voc" in r:
                            def _repl_lead_voc(m, target=w_form):
                                lead = m.group(1)
                                matched = m.group(2)
                                tgt = target.upper() if matched.isupper() else target
                                return f"{lead}{tgt}, "
                            old_t = ev.text
                            ev.text = r["re_lead_voc"].sub(_repl_lead_voc, ev.text)
                            if ev.text != old_t:
                                fixes.append(f"[Episode Quality Gate - Wołacz Apelatywny] Linia #{i+1}: ujednolicono wołacz na '{w_form}' przed imperatywem/apelem")

                    if "re_illegal_fem_masc_a" in r:
                        old_t = ev.text
                        ev.text = r["re_illegal_fem_masc_a"].sub(r"\1", ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Nieodmienność Imion Żeńskich na Spółgłoskę] Linia #{i+1}: usunięto męską końcówkę '-a' z nieodmiennego imienia żeńskiego '{r['m_form']}'")

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

            # 3d3. COORDINATED ACCUSATIVE PROPAGATION (Filar XCI / PWN Norm: Biernik po 'i' / 'oraz')
            # e.g. "Minamiego i Harugon" -> "Minamiego i Harugona", "Kuroe i Harugon" -> "Kuroe i Harugona"
            if not is_sign and compiled_decl_rules:
                for r in compiled_decl_rules:
                    if "b_form" in r:
                        m_form = r["m_form"]
                        b_form = r["b_form"]
                        pat_coord = rf"\b([A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:ego|a|ą|ę|ie|ich|e))(?:\s+|\\(?:[Nnh])+)+(?:i|oraz)\s+({re.escape(m_form)})\b"
                        def _repl_coord_acc(m, target_b=b_form):
                            lead = m.group(1)
                            matched_nom = m.group(2)
                            tgt = target_b.upper() if matched_nom.isupper() else (target_b.capitalize() if matched_nom.istitle() else target_b)
                            sep = m.group(0)[len(lead):-len(matched_nom)]
                            return f"{lead}{sep}{tgt}"
                        old_t = ev.text
                        ev.text = re.sub(pat_coord, _repl_coord_acc, ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Filar XCI Biernik Współrzędny] Linia #{i+1}: skorygowano biernik po spójniku 'i/oraz' na '{b_form}'")


            # 3g. JAPANESE FALSE-PROPER-NOUN & TITULAR GUARD (Filar II & Kanon)
            if not is_sign:
                if re.search(r"\bOuji\b", ev.text):
                    old_t = ev.text
                    def _repl_ouji(m):
                        matched = m.group(0)
                        return "Książę" if matched[0].isupper() else "książę"
                    ev.text = re.sub(r"\bOuji\b", _repl_ouji, ev.text)
                    if ev.text != old_t:
                        fixes.append(f"[Episode Quality Gate - Filar II Kanon] Linia #{i+1}: przetłumaczono japoński rzeczownik 'Ouji' na 'Książę'")

            # 3h. CONVERSATIONAL CALQUE GUARD (Filar IV / CLVI): "I co z tego?" vs "I co?"
            if not is_sign:
                # Form 1: "I co z tego?" followed by continuation questions like "To wy..." / "Chodzicie..." / "Co dalej..."
                pat_icoz_inline = r"\b([Ii]|[Aa])\s+co\s+z\s+tego\?(\s*\\N\s*|\s+)(?=[Tt]o\s+wy\b|[Cc]hodzicie\b|[Jj]esteście\b|[Cc]o\s+było\b|[Cc]o\s+dalej\b|[Jj]ak\s+to\b|[Cc]o\s+się\s+stało\b|[Pp]owiedz\b|[Mm]ów\b)"
                if re.search(pat_icoz_inline, ev.text):
                    old_t = ev.text
                    ev.text = re.sub(pat_icoz_inline, r"\g<1> co?\g<2>", ev.text, count=1)
                    if ev.text != old_t:
                        fixes.append(f"[Episode Quality Gate - Filar IV/CLVI] Linia #{i+1}: skorygowano agresywną kalkę 'I co z tego?' na naturalne 'I co?'")

                # Form 2: Standalone "I co z tego?" when followed by next event starting with "To wy..." or answering revelation
                clean_curr = re.sub(r"\{[^\}]*\}", "", ev.text).strip()
                if re.match(r"^([Ii]|[Aa])\s+co\s+z\s+tego\?[\s!\?.]*$", clean_curr):
                    next_ev = events[i + 1] if i + 1 < len(events) and not bool(re.search(r"\\(pos|move)\b", events[i + 1].text or "")) else None
                    next_text = re.sub(r"\{[^\}]*\}", "", next_ev.text).strip() if next_ev else ""
                    is_followed_by_continuation = bool(next_text and re.match(r"^(To\s+wy\b|Chodzicie\b|Jesteście\b|Co\s+dalej\b|I\s+jak\b)", next_text, re.IGNORECASE))
                    is_answering_confession = bool(prev_clean and any(w in prev_clean.lower() for w in ["wyznał", "wyznała", "miłość", "uczucia", "uczucie", "zakoch", "podobasz", "razem", "przyjemne"]))
                    
                    if is_followed_by_continuation or is_answering_confession:
                        lead_char = clean_curr[0]
                        repl_q = f"{lead_char} co?"
                        old_t = ev.text
                        ev.text = re.sub(r"\b([Ii]|[Aa])\s+co\s+z\s+tego\?", repl_q, ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Filar IV/CLVI] Linia #{i+1}: zamieniono agresywne 'I co z tego?' na zaciekawione '{repl_q}'")

            # 3i. JAPANESE HONORIFICS & OTAKU SLANG ADAPTATION (Filar XXV, XXVII & Kanon)
            if not is_sign:
                # General [Name]-senpai / [Name]-taso / [Name]-tan strip & canonical resolution
                if re.search(r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)-(?:senpai|taso|tan)\b", ev.text, re.IGNORECASE):
                    old_t = ev.text
                    def _repl_stem(m):
                        raw_stem = m.group(1)
                        full_match = m.group(0)
                        suffix = full_match.split("-")[-1].lower()

                        # 1. Check if SeriesBible has registered hypocorism (e.g. 'Kuro' -> 'Kuroe')
                        if series_bible and hasattr(series_bible, "resolve_canonical_name"):
                            canon = series_bible.resolve_canonical_name(raw_stem)
                            if canon and canon.lower() != raw_stem.lower():
                                return canon

                        # 2. Check polite surname recovery for [Surname]-senpai
                        if suffix == "senpai":
                            target_gender = "UNKNOWN"
                            if series_bible and hasattr(series_bible, "get_character_gender"):
                                target_gender = series_bible.get_character_gender(raw_stem)
                            if target_gender == "UNKNOWN" and character_registry:
                                target_gender = character_registry.get(raw_stem, "UNKNOWN")

                            # If known female character/surname, polite address in Polish is 'panno [Nazwisko]'
                            if target_gender == "FEMALE":
                                return f"panno {raw_stem}"
                            elif target_gender == "MALE":
                                return f"panie {raw_stem}"
                            return raw_stem

                        return raw_stem

                    ev.text = re.sub(r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)-(?:senpai|taso|tan)\b", _repl_stem, ev.text, flags=re.IGNORECASE)
                    if ev.text != old_t:
                        fixes.append(f"[Episode Quality Gate - Filar XXVII Adaptacja Tytułów] Linia #{i+1}: zaadaptowano japoński sufiks honoryfikatywny do kanonicznej formy polskiej")

                # Standalone 'Senpai!' or ', senpai?' in dialogue with Anti-Self-Address Guard
                if re.search(r"\bSenpai\b", ev.text, re.IGNORECASE):
                    current_speaker = ev.name.strip() if getattr(ev, "name", None) else ""
                    addressee_name = None

                    # 1. Check SeriesBible relationships and characters
                    if series_bible and hasattr(series_bible, "data") and current_speaker:
                        all_rels = {}
                        if "relationships" in series_bible.data:
                            all_rels.update(series_bible.data["relationships"])
                        if "characters" in series_bible.data:
                            for k, v in series_bible.data["characters"].items():
                                if "->" in k:
                                    all_rels[k] = v
                        for rel_k, rel_v in all_rels.items():
                            if "->" in rel_k:
                                spk, lst = [p.strip() for p in rel_k.split("->", 1)]
                                if spk.lower() == current_speaker.lower() or current_speaker.lower() in spk.lower() or spk.lower() in current_speaker.lower():
                                    clean_lst = lst.split()[0]
                                    if clean_lst.lower() != current_speaker.lower():
                                        addressee_name = clean_lst
                                        break

                    # 2. Scan backward up to 20 lines for interlocutor (skipping current_speaker and signs)
                    if not addressee_name:
                        for prev_idx in range(i - 1, max(-1, i - 21), -1):
                            cand_ev = events[prev_idx]
                            cand_spk = cand_ev.name.strip() if getattr(cand_ev, "name", None) else ""
                            # Stop if time gap > 45 seconds (major scene cut)
                            if hasattr(ev, "start") and hasattr(cand_ev, "end") and (ev.start - cand_ev.end > 45000):
                                break
                            if cand_spk and cand_spk.lower() not in ["sign", "signs", "default", "main"]:
                                if current_speaker and cand_spk.lower() == current_speaker.lower():
                                    continue
                                addressee_name = cand_spk.split()[0]
                                break

                    # 3. Scan forward up to 12 lines (if speaker opens the scene)
                    if not addressee_name:
                        for next_idx in range(i + 1, min(len(events), i + 13)):
                            cand_ev = events[next_idx]
                            cand_spk = cand_ev.name.strip() if getattr(cand_ev, "name", None) else ""
                            if hasattr(ev, "end") and hasattr(cand_ev, "start") and (cand_ev.start - ev.end > 45000):
                                break
                            if cand_spk and cand_spk.lower() not in ["sign", "signs", "default", "main"]:
                                if current_speaker and cand_spk.lower() == current_speaker.lower():
                                    continue
                                addressee_name = cand_spk.split()[0]
                                break

                    # Final Anti-Self-Address Guard: addressee CAN NEVER be current speaker!
                    if addressee_name and current_speaker and addressee_name.lower() == current_speaker.lower():
                        addressee_name = None

                    old_t = ev.text
                    if addressee_name:
                        def _repl_senpai_addr(m):
                            lead = m.group(1) or ""
                            punct = m.group(2) or ""
                            w_name = addressee_name
                            if w_name.endswith("a"):
                                w_name = w_name[:-1] + "o"
                            return f"{lead}{w_name}{punct}"
                        ev.text = re.sub(r"(^|[,\.!\?…]\s*|\bHej,\s*|\bEj,\s*)\b[Ss]enpai([!,\?…]+|\s*\\N|$)", _repl_senpai_addr, ev.text)
                        ev.text = re.sub(r",\s*[Ss]enpai\b", f", {addressee_name}", ev.text)
                    else:
                        ev.text = re.sub(r",\s*[Ss]enpai\b", "", ev.text)
                        clean_plain = re.sub(r"\{[^\}]*\}", "", ev.text).strip()
                        if clean_plain in ["Senpai!", "Senpai?", "Senpai", "senpai!", "senpai"]:
                            ev.text = re.sub(r"\b[Ss]enpai\b", "Uwaga", ev.text)
                        else:
                            ev.text = re.sub(r"\b[Ss]enpai[!,\?…]*", "", ev.text).strip()
                    if ev.text != old_t:
                        fixes.append(f"[Episode Quality Gate - Filar XXVII Adaptacja Senpai] Linia #{i+1}: zaadaptowano zwrot 'Senpai' na formę polską z ochroną przed auto-adresacją")

            # Attached Cut-off Dash Sanitizer (Filar LX)
            if not is_sign and re.search(r"([A-Za-ząćęłńóśźż])[–—\-](?=\s*\\N|\s*$|[!\?…])", ev.text):
                old_t = ev.text
                ev.text = re.sub(r"([A-Za-ząćęłńóśźż])[–—\-](?=\s*\\N|\s*$|[!\?…])", r"\1...", ev.text)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar LX Formatowanie Przerwania Wypowiedzi] Linia #{i+1}: zamieniono przyklejony myślnik urwanej kwestii na standardowy wielokropek AVT")

            # 3j. SPEAKER-SCOPED HYPOCORISM & SOCIOLECT GUARD (Filar CLXIX)
            # Prevent peer hypocorisms / school nicknames from leaking into parents', adults', or hierarchical speech
            if not is_sign and getattr(ev, "name", None):
                curr_spk_clean = extract_clean_speaker_name(ev.name).lower()
                # Dynamic extraction from SeriesBible relationships
                if series_bible and hasattr(series_bible, "data"):
                    all_chars_rels = {}
                    if "characters" in series_bible.data:
                        all_chars_rels.update(series_bible.data["characters"])
                    if "relationships" in series_bible.data:
                        all_chars_rels.update(series_bible.data["relationships"])
                    
                    for rel_k, rel_v in all_chars_rels.items():
                        if "->" not in rel_k:
                            continue
                        r_spk, r_trg = [p.strip() for p in rel_k.split("->", 1)]
                        clean_r_spk = extract_clean_speaker_name(r_spk).lower()
                        if curr_spk_clean == clean_r_spk or curr_spk_clean in clean_r_spk:
                            desc = rel_v.get("description", "") if isinstance(rel_v, dict) else str(rel_v)
                            m_ban = re.search(r"KATEGORYCZNY\s+ZAKAZ\s+(?:szkolnego\s+)?(?:przydomka|ksywki)\s+'([^']+)'", desc, re.IGNORECASE)
                            if m_ban:
                                bad_hypo = m_ban.group(1).strip()
                                canon_target = None
                                m_zwrot = re.search(r"Zwrot:\s*'([^'/]+)", desc)
                                if m_zwrot:
                                    canon_target = m_zwrot.group(1).strip()
                                if not canon_target:
                                    canon_target = extract_clean_speaker_name(r_trg).split()[0].strip()
                                
                                if bad_hypo and canon_target:
                                    pat_hypo = rf"\b{re.escape(bad_hypo)}\b"
                                    if re.search(pat_hypo, ev.text):
                                        old_t = ev.text
                                        def _repl_hypo(m, repl=canon_target):
                                            matched = m.group(0)
                                            return repl.capitalize() if matched[0].isupper() else repl
                                        ev.text = re.sub(pat_hypo, _repl_hypo, ev.text)
                                        if ev.text != old_t:
                                            fixes.append(
                                                f"[Episode Quality Gate - Filar CLXIX Socjolekt] Linia #{i+1}: "
                                                f"wyeliminowano ksywkę rówieśniczą '{bad_hypo}' w wypowiedzi mówcy '{ev.name}' -> '{canon_target}'"
                                            )


            # 4. RESIDUAL ENGLISH CALQUE SWEEP (Belczyk AVT Canon)
            for item in AVTLinter.FIXED_REPLACEMENTS:
                pattern = item[0]
                repl = item[1]
                pillar_tag = item[2] if len(item) > 2 else "Belczyk AVT"
                # Dictionary leak parentheses cleanup must NOT apply to signs!
                if is_sign and "wycieku" in pillar_tag.lower():
                    continue
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

            # 4c. SERIES BIBLE & CUSTOM GLOSSARY ENFORCEMENT (Offline-First 0.00 PLN)
            active_glossary = {}
            if series_bible and hasattr(series_bible, "data") and "glossary" in series_bible.data:
                active_glossary.update(series_bible.data["glossary"])
            if custom_glossary:
                active_glossary.update(custom_glossary)

            if active_glossary:
                for g_src, g_trg in sorted(active_glossary.items(), key=lambda x: len(x[0]), reverse=True):
                    if not g_src or not g_trg or g_src.strip().lower() == g_trg.strip().lower():
                        continue
                    src_clean = g_src.strip()
                    raw_trg_clean = g_trg.strip()
                    if raw_trg_clean.startswith("[") and raw_trg_clean.endswith("]"):
                        clean_trg = raw_trg_clean
                    else:
                        clean_trg = re.sub(r"\s*[\(\[].*?[\)\]]", "", g_trg).strip()
                    if "/" in clean_trg:
                        clean_trg = clean_trg.split("/")[0].strip()
                    if not clean_trg or len(src_clean) < 3:
                        continue
                    prefix_b = r"\b" if re.match(r"^\w", src_clean) else ""
                    suffix_b = r"\b" if re.search(r"\w$", src_clean) else ""
                    if clean_trg and clean_trg[-1] in "!?.:":
                        trail_punct = re.escape(clean_trg[-1])
                        pat_gloss = rf"{prefix_b}{re.escape(src_clean)}{suffix_b}(?:\s*{trail_punct}+)?"
                    else:
                        pat_gloss = rf"{prefix_b}{re.escape(src_clean)}{suffix_b}"

                    if re.search(pat_gloss, ev.text, re.IGNORECASE):
                        def _case_gloss_repl(m, target=clean_trg):
                            matched = m.group(0)
                            if matched.isupper():
                                return target.upper()
                            elif matched[0].isupper():
                                return target[0].upper() + target[1:]
                            else:
                                if target[0].isupper() and len(target) > 1 and target[1].islower():
                                    return target
                                return target[0].lower() + target[1:]
                        old_t = ev.text
                        ev.text = re.sub(pat_gloss, _case_gloss_repl, ev.text, flags=re.IGNORECASE)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Glosariusz Serii] Linia #{i+1}: '{g_src}' -> '{clean_trg}'")

            # Titular Vocative resolution driven by series glossary (e.g. 'Potworny Królewicz' -> 'królewiczu!')
            if series_bible and hasattr(series_bible, "data") and not is_sign:
                gloss = series_bible.data.get("glossary", {})
                if any("królewicz" in str(v).lower() for v in gloss.values()):
                    if re.search(r"(?:,\s*|\b)[Kk]siążę(?=[!,\?…\.]|\s*$|\s*\\N)", ev.text):
                        def _repl_voc_prince(m):
                            txt = m.group(0)
                            prefix = ", " if txt.startswith(",") else ""
                            word = txt.lstrip(", ")
                            repl = "Królewiczu" if word[0].isupper() else "królewiczu"
                            return f"{prefix}{repl}"
                        old_t = ev.text
                        ev.text = re.sub(r"(,\s*|\b)[Kk]siążę(?=[!,\?…\.]|\s*$|\s*\\N)", _repl_voc_prince, ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Filar XXIII Kanon Mangi] Linia #{i+1}: zastąpiono wołacz 'książę' oficjalnym kanonem przydomka 'królewiczu'")

            # 4d. PWN TYPO, PLEONASM & GRAMMATICAL NORMALIZATION (0.00 PLN)
            if not is_sign:
                from series_memory import sanitize_lexical_text
                old_san_t = ev.text
                ev.text = sanitize_lexical_text(ev.text)
                if ev.text != old_san_t:
                    fixes.append(f"[Episode Quality Gate - Normalizacja PWN / Pleonazmy] Linia #{i+1}: znormalizowano błędy leksykalne/pleonazmy")

            # 4e. DEFINITE ARTICLE NOMINATIVE VS FALSE VOCATIVE (Filar CLXXIII / §0 & §3 Offline-First)
            if not is_sign:
                src_en = getattr(ev, "source_en", None)
                if not src_en and source_subs and hasattr(source_subs, "events") and i < len(source_subs.events):
                    src_en = getattr(source_subs.events[i], "plaintext", None) or source_subs.events[i].text

                if src_en:
                    from series_memory import resolve_definite_article_nominative
                    fixed_nom, nom_changed = resolve_definite_article_nominative(src_en, ev.text)
                    if nom_changed:
                        old_t = ev.text
                        ev.text = fixed_nom
                        fixes.append(f"[Episode Quality Gate - Filar CLXXIII Mianownik Wykrzyknikowy] Linia #{i+1}: przywrócono mianownik wykrzyknikowy '{ev.text}' dla angielskiego '{src_en.strip()}' (zastąpiono fałszywy wołacz)")

            # 4d. FEMALE VOCATIVE CASE HARMONIZATION (Filar LX & CLVII: Mianownik -> Wołacz dla imion żeńskich na -a)
            if not is_sign:
                from series_memory import is_inherently_female_name, to_polish_female_vocative
                def _eqg_fem_voc_repl(m):
                    prefix = m.group(1) or ""
                    name = m.group(2)
                    punct = m.group(3)
                    if is_inherently_female_name(name) and name.lower().endswith("a"):
                        voc = to_polish_female_vocative(name)
                        if voc != name:
                            fixes.append(f"[Episode Quality Gate - Tarcza Wołacza] Linia #{i+1}: zamiana mianownika na wołacz dla imienia żeńskiego: '{name}' -> '{voc}'")
                            return f"{prefix}{voc}{punct}"
                    return m.group(0)
                ev.text = re.sub(r"(^|[\\\/][Nnh]|\b(?:och|ach|hej|o|ej|halo),?\s+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})([,?!])", _eqg_fem_voc_repl, ev.text)

            # 5. PUNCTUATION & TYPOGRAPHY HYGIENE
            # Clean accidental double dots (e.g. "To prawda..") -> "To prawda..." (excluding intentional AVT ?.. and !..)
            ev.text = re.sub(r"(?<![\.\?!])\.\.(?!\.)", "...", ev.text)
            # Normalize non-normative ellipsis clusters (e.g. ?... -> ?.., !... -> !..)
            if re.search(r"[\?!]\.{3,}", ev.text):
                old_punc_t = ev.text
                ev.text = re.sub(r"\?\.{3,}", "?..", ev.text)
                ev.text = re.sub(r"!\.{3,}", "!..", ev.text)
                if ev.text != old_punc_t and not any(f"Linia #{i+1}:" in f for f in fixes):
                    fixes.append(f"[Episode Quality Gate - Higiena Interpunkcji] Linia #{i+1}: znormalizowano nienormatywny wielokropek (?...) na standardowy AVT (?..)")
            # Remove space before comma/period/exclamation/question mark
            ev.text = re.sub(r"\s+([,\.!\?…])", r"\1", ev.text)
            # Normalize whitespace around ASS line breaks
            ev.text = re.sub(r"\s*\\N\s*", r"\\N", ev.text)
            # Remove Japanese emotional tildes and runaway multiple exclamations in dialogue (Filar LX)
            if not is_sign and "~" in ev.text:
                old_t = ev.text
                ev.text = re.sub(r"~[!]+", "!", ev.text)
                ev.text = re.sub(r"~", "", ev.text)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar LX Typografia] Linia #{i+1}: usunięto japońską tyldę i znormalizowano wykrzykniki")
            # Remove comma before "czy" in direct binary alternatives (Filar LX)
            if re.search(r"\b([A-Za-ząćęłńóśźż0-9]+),\s+czy\s+(bez|nie|tak)\b", ev.text):
                ev.text = re.sub(r"\b([A-Za-ząćęłńóśźż0-9]+),\s+czy\s+(bez|nie|tak)\b", r"\1 czy \2", ev.text)
                fixes.append(f"[Episode Quality Gate - Filar LX Interpunkcja] Linia #{i+1}: usunięto zbędny przecinek przed 'czy' w alternatywie rozłącznej")
            # Replace trailing cut-off speech glued en-dash (e.g. "Rin–") with ellipsis "Rin..." (Filar LX)
            if re.search(r"([A-Za-ząćęłńóśźż])–(?=\s*\\N|\s*$|[!\?…])", ev.text):
                ev.text = re.sub(r"([A-Za-ząćęłńóśźż])–(?=\s*\\N|\s*$|[!\?…])", r"\1...", ev.text)
                fixes.append(f"[Episode Quality Gate - Filar LX Interpunkcja] Linia #{i+1}: zamieniono przyklejony myślnik urwanej mowy na wielokropek")
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

            # 7b. SIGN & TITLE OVERFLOW PROTECTION (Filar XCVIII / Title-Safe Area 80%)
            # Ensure no individual line in a sign/title exceeds 45 characters, and purge chained bracket leaks '] ['
            if is_sign:
                clean_lines = [re.sub(r"\{[^}]*\}", "", p).strip() for p in ev.text.split(r"\N")]
                if any(len(l) > 45 for l in clean_lines) or re.search(r"\]\s*\[", ev.text):
                    from avt_formatter import split_subtitle_syntactically
                    ev.text = split_subtitle_syntactically(ev.text, max_line_len=38, is_ass=True, is_sign=True)
                    fixes.append(f"[Episode Quality Gate - Filar XCVIII (Plansze i Szyldy)] Linia #{i+1}: sformatowano napis ekranowy zapobiegając przepełnieniu kadru")

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
