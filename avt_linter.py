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
from series_memory import (
    extract_clean_speaker_name, INHERENT_FEMALE_NOUNS, INHERENT_MALE_NOUNS,
    GENERIC_CATEGORY_TAGS, is_generic_actor_or_category, ETHNONYMS_AND_COLLECTIVES,
    FEMALE_ROLE_KEYWORDS, MALE_ROLE_KEYWORDS, BOY_ROLE_KEYWORDS,
    resolve_actor_gender, is_plural_actor
)

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

        # Module C: Polish clitic pronoun syntax at start of utterance/turn (PWN Canon)
        # Słownik poprawnej polszczyzny PWN: "Formy krótkie zaimków (mi, cię, go, mu) nigdy nie mogą stać na początku zdania ani po pauzie."
        (r"(^|\\[Nnh]|[-–—]\s*)Mi\b\s+([a-ząćęłńóśźż]+)", r"\g<1>Mnie \g<2>", "PWN Składnia Zaimkowa - Eliminacja Formy Ściągniętej 'Mi' w Nagłosie"),
        (r"(^|\\[Nnh]|[-–—]\s*)Cię\b\s+([a-ząćęłńóśźż]+)", r"\g<1>Ciebie \g<2>", "PWN Składnia Zaimkowa - Eliminacja Formy Ściągniętej 'Cię' w Nagłosie"),
        (r"(^|\\[Nnh]|[-–—]\s*)Go\b\s+([a-ząćęłńóśźż]+)", r"\g<1>Jego \g<2>", "PWN Składnia Zaimkowa - Eliminacja Formy Ściągniętej 'Go' w Nagłosie"),
        (r"(^|\\[Nnh]|[-–—]\s*)Mu\b\s+([a-ząćęłńóśźż]+)", r"\g<1>Jemu \g<2>", "PWN Składnia Zaimkowa - Eliminacja Formy Ściągniętej 'Mu' w Nagłosie"),

        # Module D1: Verbal Dative Government (Eliminacja kalek accusative)
        (r"\b([Uu]fam)\s+ciebie\b", r"\1 ci", "PWN Rekcja Czasowników - Prymat Celownika ('ufam ciebie' -> 'ufam ci')"),
        (r"\b([Uu]fam)\s+was\b", r"\1 wam", "PWN Rekcja Czasowników - Prymat Celownika ('ufam was' -> 'ufam wam')"),
        (r"\b([Ww]ybacz)\s+mnie\b", r"\1 mi", "PWN Rekcja Czasowników - Prymat Celownika ('wybacz mnie' -> 'wybacz mi')"),
        (r"\b([Pp]omóż)\s+mnie\b", r"\1 mi", "PWN Rekcja Czasowników - Prymat Celownika ('pomóż mnie' -> 'pomóż mi')"),
        (r"\b([Pp]omóżcie)\s+mnie\b", r"\1 mi", "PWN Rekcja Czasowników - Prymat Celownika ('pomóżcie mnie' -> 'pomóżcie mi')"),
        (r"\b([Zz]azdroszczę)\s+ciebie\b", r"\1 ci", "PWN Rekcja Czasowników - Prymat Celownika ('zazdroszczę ciebie' -> 'zazdroszczę ci')"),
        (r"\b([Ww]ybaczam)\s+ciebie\b", r"\1 ci", "PWN Rekcja Czasowników - Prymat Celownika ('wybaczam ciebie' -> 'wybaczam ci')"),

        # Module D2: Genitive of Negation (Genetivus Negationis) for Fixed Collocations
        (r"\b([Nn]ie\s+mam)\s+czas\b", r"\1 czasu", "PWN Dopełniacz Negacji - Stała Kolokacja ('nie mam czas' -> 'nie mam czasu')"),
        (r"\b([Nn]ie\s+ma)\s+sens\b", r"\1 sensu", "PWN Dopełniacz Negacji - Stała Kolokacja ('nie ma sens' -> 'nie ma sensu')"),
        (r"\b([Nn]ie\s+widzę)\s+problem\b", r"\1 problemu", "PWN Dopełniacz Negacji - Stała Kolokacja ('nie widzę problem' -> 'nie widzę problemu')"),
        (r"\b([Nn]ie\s+widzę)\s+różnica\b", r"\1 różnicy", "PWN Dopełniacz Negacji - Stała Kolokacja ('nie widzę różnica' -> 'nie widzę różnicy')"),
        (r"\b([Nn]ie\s+czuję)\s+ból\b", r"\1 bólu", "PWN Dopełniacz Negacji - Stała Kolokacja ('nie czuję ból' -> 'nie czuję bólu')"),
        (r"\b([Nn]ie\s+ma)\s+mowa\b", r"\1 mowy", "PWN Dopełniacz Negacji - Stała Kolokacja ('nie ma mowa' -> 'nie ma mowy')"),
        (r"\b([Nn]ie\s+mam)\s+pojęcie\b", r"\1 pojęcia", "PWN Dopełniacz Negacji - Stała Kolokacja ('nie mam pojęcie' -> 'nie mam pojęcia')"),
        (r"\b([Nn]ie\s+ma)\s+potrzeba\b", r"\1 potrzeby", "PWN Dopełniacz Negacji - Stała Kolokacja ('nie ma potrzeba' -> 'nie ma potrzeby')"),
        (r"\b([Nn]ie\s+ma)\s+wyjście\b", r"\1 wyjścia", "PWN Dopełniacz Negacji - Stała Kolokacja ('nie ma wyjście' -> 'nie ma wyjścia')"),
        (r"\b([Nn]ie\s+ma)\s+znaczenie\b", r"\1 znaczenia", "PWN Dopełniacz Negacji - Stała Kolokacja ('nie ma znaczenie' -> 'nie ma znaczenia')"),

        (r"\b[Jj]esteś w porządku\?", "Wszystko w porządku?", "Filar IV - Szablony Angielskie"),
        (r"\b[Bb]yłem w stanie to znaleźć\b", "Udało mi się to znaleźć", "Filar IV - Konstrukcje Obce"),
        (r"\b[Bb]yłam w stanie to znaleźć\b", "Udało mi się to znaleźć", "Filar IV - Konstrukcje Obce"),
        (r"\b[Ww]ygląda jakby miało padać\b", "Chyba będzie padać", "Filar XXXII - Modalność Epistemiczna"),
        (r"\b[Mm]am uczucie że\b", "Coś mi mówi, że", "Filar IV - Naturalność Mówiona"),
        (r"\b[Ww]ydaje się być\b", "Wydaje się", "Filar IV - Konstrukcje Obce"),
        (r"\b[Pp]oniosło klapę\b", "Nie wyszło", "Filar IV - Idiomatyka"),
        (r"\b[Ww]asz [Hh]onor\b", "Wysoki Sądzie", "Filar XVI - Realia Sądownicze"),
        
        # AnimeSub.info (ANSI) Anti-Translationese & Phatic Calques
        (r"\b[Zz]godnie z oczekiwaniami\b", "tak jak myślałem", "Filar CXLVII - Eliminacja Kalki 'As expected'"),
        (r"(^|\\[Nnh]|[-–]\s*)\s*[Nn]ie da się pomóc([.!?…]*(?:\s*(?=$|\\[Nnh])))", r"\1nic na to nie poradzimy\2", "Filar CXLVII - Eliminacja Kalki 'It can't be helped'"),
        (r"(^|\\[Nnh]|[-–]\s*)\s*[Nn]ie można pomóc([.!?…]*(?:\s*(?=$|\\[Nnh])))", r"\1nic nie poradzimy\2", "Filar CXLVII - Eliminacja Kalki 'It can't be helped'"),
        (r"(?i)(^|\\[Nnh]|[-–]\s*)\s*Oho,?\s+spokojnie(?:\.{1,3}|[!])\s*(?=$|\\[Nnh])", r"\1Ło, ło, ło...", "Filar XVIII - Eliminacja Kalki Somatycznej 'Whoa, easy' (Ottotto)"),
        (r"(^|\\[Nnh]|[-–]\s*)\s*[Tt]o\s+jest\s+gorące(?:[!]+(?:\s*(?=[A-ZĄĆĘŁŃÓŚŹŻ])|\s*$|\s*\\[Nnh])|(?=\s*$|\s*\\[Nnh]))", r"\1Parzy!", "Filar XVIII - Eliminacja Opisu Bólu (Acchichi)"),
        (r"(^|\\[Nnh]|[-–]\s*)\s*[Tt]o\s+boli(?:[!]+(?:\s*(?=[A-ZĄĆĘŁŃÓŚŹŻ])|\s*$|\s*\\[Nnh])|(?=\s*$|\s*\\[Nnh]))", r"\1Ała!", "Filar XVIII - Eliminacja Opisu Bólu (Itta)"),
        (r"(^|\\[Nnh]|[-–]\s*)\s*[Nn]iebezpiecznie[!]+(?:\s*(?=[A-ZĄĆĘŁŃÓŚŹŻ])|\s*$|\s*\\[Nnh])", r"\1Uważaj!", "Filar CLII - Eliminacja Opisu Zagrożenia (Abunai)"),
        (r"(^|\\[Nnh]|[-–]\s*)\s*[Tt]o\s+jest\s+niebezpieczne(?:[!]+(?:\s*(?=[A-ZĄĆĘŁŃÓŚŹŻ])|\s*$|\s*\\[Nnh])|(?=\s*$|\s*\\[Nnh]))", r"\1Uważaj!", "Filar CLII - Eliminacja Opisu Zagrożenia (Abunai)"),
        (r"(?i)(^|\\[Nnh]|[-–]\s*)\s*Ocal\s+mnie[!.]*\s*(?=$|\\[Nnh])", r"\1Ratunku!", "Filar CLII - Eliminacja Teatralnego Zwrotu (Tasukete)"),
        (r"(?i)(^|\\[Nnh]|[-–]\s*)\s*Będę\s+przeszkadzał[!.]*\s*(?=$|\\[Nnh])", r"\1Przepraszam za najście", "Filar CLI - Formuła Ojama Shimasu"),
        (r"(?i)(^|\\[Nnh]|[-–]\s*)\s*Wróciłe[mś]\s+do\s+domu[!.]*\s*(?=$|\\[Nnh])", r"\1Wróciłem!", "Filar CLI - Formuła Tadaima"),
        (r"(?i)(^|\\[Nnh]|[-–]\s*)\s*Nic\s+nie\s+da\s+się\s+zrobić[!.]*\s*(?=$|\\[Nnh])", r"\1Trudno", "Filar XXI - Eliminacja Kalki 'Shouganai' (ANSI Standard)"),
        (r"\b[Dd]zięki za zmęczenie\b", "Dobra robota", "Filar XXI - Eliminacja Kalki 'Otsukaresama' (ANSI Standard)"),
        (r"\b[Dd]zięki za dobrą pracę\b", "Dobra robota", "Filar XXI - Eliminacja Kalki 'Otsukaresama' (ANSI Standard)"),
        (r"(?i)(^|\\[Nnh]|[-–]\s*)\s*Nie\s+ma\s+drogi[!]+\s*(?=$|\\[Nnh])", r"\1Wykluczone!", "Filar IV - Eliminacja Kalki 'No way' (ANSI Standard)"),
        
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
        (r"(^|\\[Nnh]|[-–]\s*|[,\.!\?…]\s*)\b([Ss]tarszy\s+brat\s+powiedział)\b", lambda m: f"{m.group(1)}{'Mój brat powiedział' if m.group(2)[0].isupper() else 'mój brat powiedział'}", "Filar CLIV - Relacja Rodzinna w 3. Osobie"),
        (r"(^|\\[Nnh]|[-–]\s*|[,\.!\?…]\s*)\b([Ss]tarsza\s+siostra\s+powiedziała)\b", lambda m: f"{m.group(1)}{'Moja siostra powiedziała' if m.group(2)[0].isupper() else 'moja siostra powiedziała'}", "Filar CLIV - Relacja Rodzinna w 3. Osobie"),
        
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
        (r"(?:^|[,\.!\?…]\s*|\bNo\s+)I(?:\s+|\\N)+gitara(?=[!\.\?…]*\s*(?:\\N|$))", "Doskonale", "Filar X - Rejestr Dark Fantasy (I gitara)"),
        (r"(?:^|[,\.!\?…]\s*|\bNo\s+)i(?:\s+|\\N)+gitara(?=[!\.\?…]*\s*(?:\\N|$))", "doskonale", "Filar X - Rejestr Dark Fantasy (i gitara)"),
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
        (r"(?i)\b(to\s+)?oberwę([!\?…\.]*)$", lambda m: ("to poniosę karę" if m.group(1) else ("Poniosę karę" if m.group(0)[0].isupper() else "poniosę karę")) + m.group(2), "Filar X - Rejestr Dark Fantasy (oberwę)"),
        (r"\bPani(?:\s+|\\N)+bohaterko\b", "Pani Bohaterko", "Filar CLVII - Tytulatura Bohaterki"),
        (r"\btrzecia(?:\s+|\\N)+z(?:\s+|\\N)+najlepszych\b", "trzecia pod względem siły", "Filar X - Kalka Składniowa (trzecia z najlepszych)"),
        (r"\bBez\s+jaj[!]+", "Niemożliwe!", "Filar X - Rejestr Dark Fantasy (Bez jaj)"),
        (r"\bbez\s+jaj[!]+", "niemożliwe!", "Filar X - Rejestr Dark Fantasy (bez jaj)"),
        (r"\b[Gg]uzik\s+mnie\s+to\s+obchodzi\b", lambda m: "Nic mnie to nie obchodzi" if m.group(0)[0].isupper() else "nic mnie to nie obchodzi", "Filar X - Rejestr Dark Fantasy (guzik mnie to obchodzi)"),
        (r"\b([Pp]ora|[Cc]zas)\s+stąd\s+zwiewać\b", r"\1 stąd uciekać", "Filar X - Rejestr Dark Fantasy (pora stąd zwiewać)"),
        (r"\b[Mm]am\s+przez\s+(?:nie|nich)\s+uraz\b", lambda m: "Mam do nich uraz" if m.group(0)[0].isupper() else "mam do nich uraz", "Filar IV - Kalka Składniowa Rządu (uraz przez coś -> uraz do czegoś)"),
        (r"\b[Dd]urna\s+jestem\b", lambda m: "Głupia jestem" if m.group(0)[0].isupper() else "głupia jestem", "Filar X - Stylistyka Monologu (Durna jestem)"),
        (r"(?i)(^|\\[Nnh]|[-–]\s*)\s*Ale\s+żenada\.{2,}", r"\1Ale marudzisz...", "Filar CLXX Taksonomia Aktów Mowy"),
        (r"(?i)(^|\\[Nnh]|[-–]\s*)\s*Ale\s+żenada([!\?…\.]*)\s*(?=$|\\[Nnh])", lambda m: f"{m.group(1)}{'Ale marudzisz' if m.group(0).lstrip(' -–').startswith('A') else 'ale marudzisz'}{m.group(2)}", "Filar CLXX Taksonomia Aktów Mowy"),
        # Closed invariant PWN preposition-pronoun phonetic forms and idioms (0.00 PLN)
        (r"\b([Dd]la)\s+mię\b", lambda m: "Dla mnie" if m.group(1)[0].isupper() else "dla mnie", "PWN - Rząd Przyimka (dla mnie)"),
        (r"\b([Oo]de)\s+mie\b", lambda m: "Ode mnie" if m.group(1)[0].isupper() else "ode mnie", "PWN - Rząd Przyimka (ode mnie)"),
        (r"\b([Oo]d)\s+mnie\b", lambda m: "Ode mnie" if m.group(1)[0].isupper() else "ode mnie", "PWN - Fonetyka Przyimka (ode mnie)"),
        (r"\b([Zz])\s+mną\b", lambda m: "Ze mną" if m.group(1)[0].isupper() else "ze mną", "PWN - Fonetyka Przyimka (ze mną)"),
        (r"\b([Pp]rzed)\s+mną\b", lambda m: "Przede mną" if m.group(1)[0].isupper() else "przede mną", "PWN - Fonetyka Przyimka (przede mną)"),
        (r"\b([Ww])\s+każdym\s+bądź\s+razie\b", lambda m: "W każdym razie" if m.group(1)[0].isupper() else "w każdym razie", "PWN - Kalka Frazeologiczna (w każdym razie)"),
        (r"\b([Pp])omiędzy\s+tobą\s+i\s+mną\b", lambda m: "Między nami" if m.group(1)[0].isupper() else "między nami", "PWN - Związek Przyimkowy (między nami)"),
        (r"\b([Pp])omiędzy\s+nami\b", lambda m: "Między nami" if m.group(1)[0].isupper() else "między nami", "PWN - Związek Przyimkowy (między nami)"),
        (r"\b([Ww])\s+mrugnięciu\s+oka\b", lambda m: "W mgnieniu oka" if m.group(1)[0].isupper() else "w mgnieniu oka", "PWN - Frazeologia (w mgnieniu oka)"),

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
        (r"\b[Ss]tarszy bracie\b", lambda m: "Bracie" if m.group(0)[0].isupper() else "bracie", "Filar XXV - Relacje Rodzinne"),
        (r"\b[Ss]tarsza siostro\b", lambda m: "Siostro" if m.group(0)[0].isupper() else "siostro", "Filar XXV - Relacje Rodzinne"),

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

        # Cultural realia and Pedersen ECR (Pillar XIV) - Full Prepositional Declension Matrix
        (r"\b([Ww]|we)\s+[Kk]onbini\b", r"\1 sklepie", "Filar XIV - Pedersen Generalization (Miejscownik: w sklepie)"),
        (r"\b([Dd]o)\s+[Kk]onbini\b", r"\1 sklepu", "Filar XIV - Pedersen Generalization (Dopełniacz: do sklepu)"),
        (r"\b([Zz]|ze|[Oo]d)\s+[Kk]onbini\b", r"\1 sklepu", "Filar XIV - Pedersen Generalization (Dopełniacz: ze sklepu)"),
        (r"\b([Pp]rzed|[Zz]a)\s+[Kk]onbini\b", r"\1 sklepem", "Filar XIV - Pedersen Generalization (Narzędnik: przed sklepem)"),
        (r"\b([Kk]oło|[Oo]bok)\s+[Kk]onbini\b", r"\1 sklepu", "Filar XIV - Pedersen Generalization (Dopełniacz: koło sklepu)"),
        (r"\b[Kk]onbini\b", lambda m: "Sklep" if m.group(0)[0].isupper() else "sklep", "Filar XIV - Pedersen Generalization"),

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
        (r"(?i)(^|\\[Nnh]|[-–]\s*)\s*Dobre\s+pytanie[!.]*\s*(?=$|\\[Nnh])", lambda m: f"{m.group(1)}{'Trudno powiedzieć' if 'D' in m.group(0) else 'trudno powiedzieć'}", "Filar IV/CLXVII - Eliminacja Angielskiej Kalki 'Good question'"),
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

        # Filar CLXXXIII: Nienaruszalność toponimów obcojęzycznych z niemymi głoskami (Bordeaux, Margaux, Calais)
        (r"\b([Bb]ordeaux)(?:a|em|ie|owi)\b", r"\1",
         "Filar CLXXXIII - Nieodmienne toponimy obcojęzyczne (Bordeaux)"),
        (r"\b([Mm]argaux)a\b", r"\1",
         "Filar CLXXXIII - Nieodmienne toponimy obcojęzyczne (Margaux)"),
        (r"\b([Cc]alais)a\b", r"\1",
         "Filar CLXXXIII - Nieodmienne toponimy obcojęzyczne (Calais)"),
        (r"\b([Mm]eaux)a\b", r"\1",
         "Filar CLXXXIII - Nieodmienne toponimy obcojęzyczne (Meaux)"),

        # Filar CLXXXIII: Zgodność liczby w zaimkach z liczebnikami (A ty dwie -> A wy dwie)
        (r"\b([Aa]\s+)?([Tt]y)\s+(dwie|dwaj|dwa|dwoje|troje|trzej|trzy|czworo|czterej|cztery|oboje|obie|obaj|wszyscy)\b",
         lambda m: f"{m.group(1) or ''}{'Wy' if m.group(2)[0].isupper() else 'wy'} {m.group(3)}",
         "Filar CLXXXIII - Zgodność liczby w zaimkach z liczebnikami (wy dwie / wy dwaj)"),

        # Filar CLXXXIII: Puryzm tytulatury w dopełnieniu (od pana panie X -> od pana X)
        (r"\b(od|dla|u|do|wobec)\s+[Pp]an(?:a|u|em)?\s+panie\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b",
         lambda m: f"{m.group(1)} pana {m.group(2)}",
         "Filar CLXXXIII - Puryzm tytulatury w dopełnieniu (od pana Hayamy)"),
        (r"\b([Zz]|ze)\s+[Pp]an(?:a|u|em)?\s+panie\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b",
         lambda m: f"{m.group(1)} panem {m.group(2)}",
         "Filar CLXXXIII - Puryzm tytulatury w narzędniku (z panem Hayamą)"),
        (r"\b(o|przy)\s+[Pp]an(?:a|u|em)?\s+panie\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b",
         lambda m: f"{m.group(1)} panu {m.group(2)}",
         "Filar CLXXXIII - Puryzm tytulatury w miejscowniku (o panu Hayamie)"),
        (r"\b([Pp]an(?:a|u|em)?)\s+panie\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b",
         lambda m: f"{m.group(1)} {m.group(2)}",
         "Filar CLXXXIII - Likwidacja zdublowanej tytulatury (pana Hayamy)"),

        # Filar CLXXXIV: Eliminacja Pleonazmów Toponimicznych i Jąkania Słownikowego
        (r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})(?:\s+|\\N)+\1\b",
         r"\1",
         "Filar CLXXXIV - Likwidacja mechanicznego jąkania słownikowego"),
        (r"\b(prowincj[a-ząćęłńóśźż]*|prefektur[a-ząćęłńóśźż]*|gór[a-ząćęłńóśźż]*|rzek[a-ząćęłńóśźż]*|jezior[a-ząćęłńóśźż]*|morz[a-ząćęłńóśźż]*|dolin[a-ząćęłńóśźż]*|wysp[a-ząćęłńóśźż]*|zatok[a-ząćęłńóśźż]*|zamk[a-ząćęłńóśźż]*|zamek|twierdz[a-ząćęłńóśźż]*|świątyni[a-ząćęłńóśźż]*|chram[a-ząćęłńóśźż]*|bram[a-ząćęłńóśźż]*|miast[a-ząćęłńóśźż]*|kronik[a-ząćęłńóśźż]*|księg[a-ząćęłńóśźż]*)(?:\s+|\\N)+(?:[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]*\1[a-ząćęłńóśźż]*(?:\s+|\\N)+)+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)\b",
         r"\1 \2",
         "Filar CLXXXIV - Eliminacja Pleonazmu Toponimicznego"),
    ]

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Convenience method to lint and fix a single text line (0.00 PLN)."""
        return cls.lint_and_fix_line(text)[0]

    @classmethod
    def lint_subtitles(cls, subs, **kwargs):
        """Convenience method to audit and fix an entire subtitle file via EpisodeQualityGate (0.00 PLN)."""
        return EpisodeQualityGate.audit_and_fix_entire_episode(subs, **kwargs)

    @classmethod
    def lint_and_fix_line(
        cls,
        text: str,
        speaker_gender: Optional[str] = None,
        addressee_gender: Optional[str] = None,
        is_all_girls_scene: bool = False,
        is_sign: bool = False,
        user_feedback_rules: Optional[List[Dict[str, Any]]] = None,
        custom_glossary: Optional[Dict[str, str]] = None,
        is_informal_ty: bool = False,
        audio_jp: str = "",
        prev_line_text: str = "",
        source_en: str = ""
    ) -> Tuple[str, List[str]]:
        """
        Comprehensive AVT linter. Checks Polish subtitle line against multiple AVT rules
        and automatically fixes violations.
        """
        if not text:
            return text, []

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

        # 1d. Toponymic Pleonasm and Stuttering Sanitizer (Filar CLXXXIV - 0.00 PLN)
        from series_memory import (
            sanitize_toponymic_pleonasms_and_stuttering,
            sanitize_toponymic_origin_and_companionship,
            sanitize_toponymic_preposition_governance
        )
        old_top_t = modified
        modified = sanitize_toponymic_pleonasms_and_stuttering(modified)
        if modified != old_top_t:
            applied_fixes.append("[Filar CLXXXIV - Pleonazmy Toponimiczne i Jąkanie] Zlikwidowano pleonazm toponimiczny/jąkanie słownikowe")

        # 1e. Toponymic Origin Genitive vs Companionship Sanitizer (Filar CLXXXIV - 0.00 PLN)
        old_orig_t = modified
        modified = sanitize_toponymic_origin_and_companionship(modified, custom_glossary=custom_glossary)
        if modified != old_orig_t:
            applied_fixes.append("[Filar CLXXXIV - Harmonizacja Pochodzenia Toponimów] Skorygowano narzędnik toponimu na dopełniacz pochodzenia lub ujednolicono toponim")

        # 1f. Toponymic Preposition Governance Sanitizer (Filar CLXXXIV / Zasada 15 - 0.00 PLN)
        old_top_prep_t = modified
        modified = sanitize_toponymic_preposition_governance(modified)
        if modified != old_top_prep_t:
            applied_fixes.append("[Filar CLXXXIV / Zasada 15 - Rekcja Przyimkowa Toponimów] Skorygowano zamrożony mianownik toponimu na przypadek zależny")

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
            is_boy_role = any(w in spk_norm for w in ["chłopiec", "chłopak", "boy", "syn", "młodzieniec", "bocchan", "książę"])
            is_male_speaker = (any(w in spk_norm for w in ["mężczyzna", "male", "męski"]) and not any(w in spk_norm for w in ["alt", "kobieta", "żeńsk", "starszej"])) or is_boy_role
            is_explicit_female_speaker = not is_boy_role and any(w in spk_norm for w in ["kobieta", "dziewczynka", "female", "girl", "żeński", "alt starszej", "alt dojrzały", "cesarzowa", "chatun", "matrona"])
            is_female_speaker = is_explicit_female_speaker

            # 4a. 1st-PERSON (SPEAKER) MORPHOLOGY: Ja / Mówca (Filar CLXIX)
            if is_male_speaker:
                male_1st_fixes = [
                    (r"\b[Dd]omyślałam się\b", lambda m: "Domyślałem się" if m.group(0)[0].isupper() else "domyślałem się"),
                    (r"\b[Mm]yślałam\b", lambda m: "Myślałem" if m.group(0)[0].isupper() else "myślałem"),
                    (r"\b[Ww]iedziałam\b", lambda m: "Wiedziałem" if m.group(0)[0].isupper() else "wiedziałem"),
                    (r"\b[Ww]idziałam\b", lambda m: "Widziałem" if m.group(0)[0].isupper() else "widziałem"),
                    (r"\b[Zz]robiłam\b", lambda m: "Zrobiłem" if m.group(0)[0].isupper() else "zrobiłem"),
                    (r"\b[Pp]oszłam\b", lambda m: "Poszedłem" if m.group(0)[0].isupper() else "poszedłem"),
                    (r"\b[Pp]rzyszłam\b", lambda m: "Przyszedłem" if m.group(0)[0].isupper() else "przyszedłem"),
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
                    (r"\b[Mm]iałam\b", lambda m: "Miałem" if m.group(0)[0].isupper() else "miałem"),
                    (r"\b[Ww]róciłam\b", lambda m: "Wróciłem" if m.group(0)[0].isupper() else "wróciłem"),
                    (r"\b[Dd]ostałam\b", lambda m: "Dostałem" if m.group(0)[0].isupper() else "dostałem"),
                    (r"\b[Pp]omyślałam\b", lambda m: "Pomyślałem" if m.group(0)[0].isupper() else "pomyślałem"),
                    (r"\b[Zz]gubiłam się\b", lambda m: "Zgubiłem się" if m.group(0)[0].isupper() else "zgubiłem się"),
                    (r"\b[Zz]raniłam\b", lambda m: "Zraniłem" if m.group(0)[0].isupper() else "zraniłem"),
                    (r"\b[Ss]krzywdziłam\b", lambda m: "Skrzywdziłem" if m.group(0)[0].isupper() else "skrzywdziłem"),
                    (r"\b[Uu]ratowałam\b", lambda m: "Uratowałem" if m.group(0)[0].isupper() else "uratowałem"),
                    (r"\b[Oo]ddałam\b", lambda m: "Oddałem" if m.group(0)[0].isupper() else "oddałem"),
                    (r"\b[Mm]iałabym\b", lambda m: "Miałbym" if m.group(0)[0].isupper() else "miałbym"),
                    (r"\b[Cc]hciałabym\b", lambda m: "Chciałbym" if m.group(0)[0].isupper() else "chciałbym"),
                    (r"\b[Mm]ogłabym\b", lambda m: "Mógłbym" if m.group(0)[0].isupper() else "mógłbym"),
                    (r"\b[Ww]olałabym\b", lambda m: "Wolałbym" if m.group(0)[0].isupper() else "wolałbym"),
                    (r"\b[Mm]usiałabym\b", lambda m: "Musiałbym" if m.group(0)[0].isupper() else "musiałbym"),
                    (r"\b[Ww]iedziałabym\b", lambda m: "Wiedziałbym" if m.group(0)[0].isupper() else "wiedziałbym"),
                    (r"\b[Zz]robiłabym\b", lambda m: "Zrobiłbym" if m.group(0)[0].isupper() else "zrobiłbym"),
                    (r"\b[Bb]yłabym\b", lambda m: "Byłbym" if m.group(0)[0].isupper() else "byłbym"),
                    (r"\b[Pp]oszłabym\b", lambda m: "Poszedłbym" if m.group(0)[0].isupper() else "poszedłbym"),
                    (r"\b[Pp]rzyszłabym\b", lambda m: "Przyszedłbym" if m.group(0)[0].isupper() else "przyszedłbym"),
                    (r"\b[Zz]nalazłabym\b", lambda m: "Znalazłbym" if m.group(0)[0].isupper() else "znalazłbym"),
                    (r"\b[Pp]owiedziałabym\b", lambda m: "Powiedziałbym" if m.group(0)[0].isupper() else "powiedziałbym"),
                    (r"\b[Cc]zułabym\b", lambda m: "Czułbym" if m.group(0)[0].isupper() else "czułbym"),
                    (r"\b[Ww]idziałabym\b", lambda m: "Widziałbym" if m.group(0)[0].isupper() else "widziałbym"),
                    (r"\b[Pp]omyślałbym\b", lambda m: "Pomyślałabym" if m.group(0)[0].isupper() else "pomyślałabym"),
                ]
                for pattern, repl in male_1st_fixes:
                    if re.search(pattern, modified):
                        modified = re.sub(pattern, repl, modified)
                        applied_fixes.append(f"[Filar CXXXVI/CLXIX - Mówca Męski/Chłopiec 1. os.] Korekta rodzaju żeńskiego na męski: {pattern}")

                def _morph_f_to_m_repl(m):
                    word = m.group(0)
                    converted = convert_first_person_feminine_to_masculine(word)
                    if converted and converted != word:
                        applied_fixes.append(f"[Filar CXXXVI/CLXIX - Mówca Męski 1. os.] Korekta rodzaju żeńskiego na męski: '{word}' -> '{converted}'")
                        return converted
                    return word
                modified = re.sub(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łam|łabym)\b", _morph_f_to_m_repl, modified)

            elif is_female_speaker and is_explicit_female_speaker:
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
                    (r"\b[Zz]gubiłem się\b", lambda m: "Zgubiłem się" if m.group(0)[0].isupper() else "zgubiłem się"),
                    (r"\b[Zz]raniłem\b", lambda m: "Zraniłam" if m.group(0)[0].isupper() else "zraniłam"),
                    (r"\b[Ss]krzywdziłem\b", lambda m: "Skrzywdziłam" if m.group(0)[0].isupper() else "skrzywdziłam"),
                    (r"\b[Uu]ratowałem\b", lambda m: "Uratowałam" if m.group(0)[0].isupper() else "uratowałam"),
                    (r"\b[Oo]ddałem\b", lambda m: "Oddałam" if m.group(0)[0].isupper() else "oddałam"),
                    (r"\b[Mm]iałbym\b", lambda m: "Miałabym" if m.group(0)[0].isupper() else "miałabym"),
                    (r"\b[Cc]hciałbym\b", lambda m: "Chciałabym" if m.group(0)[0].isupper() else "chciałabym"),
                    (r"\b[Mm]ógłbym\b", lambda m: "Mogłabym" if m.group(0)[0].isupper() else "mogłabym"),
                    (r"\b[Ww]olałbym\b", lambda m: "Wolałabym" if m.group(0)[0].isupper() else "wolałabym"),
                    (r"\b[Mm]usiałbym\b", lambda m: "Musiałabym" if m.group(0)[0].isupper() else "musiałabym"),
                    (r"\b[Ww]iedziałbym\b", lambda m: "Wiedziałabym" if m.group(0)[0].isupper() else "wiedziałabym"),
                    (r"\b[Zz]robiłbym\b", lambda m: "Zrobiłabym" if m.group(0)[0].isupper() else "zrobiłabym"),
                    (r"\b[Bb]yłbym\b", lambda m: "Byłabym" if m.group(0)[0].isupper() else "byłabym"),
                    (r"\b[Pp]oszedłbym\b", lambda m: "Poszłabym" if m.group(0)[0].isupper() else "poszłabym"),
                    (r"\b[Pp]rzyszzedłbym\b", lambda m: "Przyszłabym" if m.group(0)[0].isupper() else "przyszłabym"),
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

            # 4b. 2nd-PERSON (ADDRESSEE) MORPHOLOGY: Ty / Adresat (Filar XIII & CLXIII)
            addr_norm = (addressee_gender or "").lower()
            is_boy_addr = any(re.search(rf"\b{re.escape(w)}\b", addr_norm) for w in ["chłopiec", "chłopak", "boy", "syn", "młodzieniec", "bocchan", "książę"])
            is_male_addressee = (any(re.search(rf"\b{re.escape(w)}\b", addr_norm) for w in ["mężczyzna", "male", "męski", "man", "on"]) and not any(re.search(rf"\b{re.escape(w)}\b", addr_norm) for w in ["alt", "kobieta", "żeńsk", "starszej"])) or is_boy_addr
            is_explicit_female_addressee = not is_boy_addr and any(re.search(rf"\b{re.escape(w)}\b", addr_norm) for w in ["kobieta", "dziewczynka", "female", "girl", "żeński", "alt starszej", "alt dojrzały", "cesarzowa", "chatun", "matrona", "ona"])
            is_female_addressee = is_explicit_female_addressee

            if is_female_addressee:
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

            elif is_male_addressee:
                male_address_fixes = [
                    (r"\b[Gg]łupia jesteś\?", "Głupi jesteś?"),
                    (r"\b[Jj]esteś pewna\?", "Jesteś pewien?"),
                    (r"\b[Oo]szalałaś\?", "Oszalałeś?"),
                    (r"\b[Zz]głupiałaś\?", "Zgłupiałeś?"),
                    (r"\b[Ww]idziałaś to\?", "Widziałeś to?"),
                    (r"\b[Ss]łyszałaś to\?", "Słyszałeś to?"),
                    (r"\b[Zz]robiłaś to\?", "Zrobiłeś to?"),
                    (r"\b[Pp]oszłaś tam\?", "Poszedłeś tam?"),
                    (r"\b[Mm]yślałaś, że\b", "Myślałeś, że"),
                    (r"\b[Ww]yglądasz na wzburzoną\b", "Wyglądasz na wzburzonego"),
                    (r"\bwyglądasz na wzburzoną\b", "wyglądasz na wzburzonego"),
                    (r"\b[Jj]esteś pewna\b", lambda m: "Jesteś pewien" if m.group(0)[0].isupper() else "jesteś pewien"),
                    (r"\b[Jj]esteś gotowa\b", lambda m: "Jesteś gotowy" if m.group(0)[0].isupper() else "jesteś gotowy"),
                    (r"\b[Jj]esteś sama\b", lambda m: "Jesteś sam" if m.group(0)[0].isupper() else "jesteś sam"),
                ]
                for pattern, repl in male_address_fixes:
                    if re.search(pattern, modified):
                        modified = re.sub(pattern, repl, modified)
                        applied_fixes.append(f"[Filar XIII/CLXIII - Adresat Męski/Chłopiec] Korekta rodzaju żeńskiego na męski: {pattern}")

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

                # Also check vocative at the start of the line: e.g. "Moniko, ..." or "Anno, ..."
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
            is_boy_spk = any(re.search(rf"\b{re.escape(w)}\b", spk_norm) for w in ["chłopiec", "chłopak", "boy", "syn", "młodzieniec", "bocchan", "książę"])
            is_male_spk = (any(re.search(rf"\b{re.escape(w)}\b", spk_norm) for w in ["mężczyzna", "chłopiec", "male", "boy", "męski"]) and not any(re.search(rf"\b{re.escape(w)}\b", spk_norm) for w in ["alt", "kobieta", "żeńsk"])) or is_boy_spk
            is_female_spk = not is_boy_spk and any(re.search(rf"\b{re.escape(w)}\b", spk_norm) for w in ["kobieta", "dziewczynka", "female", "girl", "żeński"])

            # 1. HITORI (一人 / 独り / ひとり): w audio prośba o samotność -> ZAKAZ 'daj mi spokój'
            if any(k in clean_audio_jp for k in ["hitori", "一人", "独り", "ひとり"]):
                if re.search(r"\b[Dd]aj(?:\s+|\\N)+mi(?:\s+|\\N)+spokój\b", modified):
                    repl_hitori = "Zostaw mnie samą" if is_female_spk else ("Zostaw mnie samego" if is_male_spk else "Zostaw mnie w spokoju")
                    def _hitori_repl(m, r=repl_hitori):
                        return r if m.group(0)[0].isupper() else r.lower()
                    modified = re.sub(r"\b[Dd]aj(?:\s+|\\N)+mi(?:\s+|\\N)+spokój\b", _hitori_repl, modified)
                    applied_fixes.append(f"[Filar CLVIII - Zgodność Foniczna Seiyū] Wykryto 'Hitori' w audio: zastąpiono 'daj mi spokój' przez '{repl_hitori.lower()}'")
                elif re.search(r"\b[Dd]ajcie(?:\s+|\\N)+mi(?:\s+|\\N)+spokój\b", modified):
                    repl_hitori = "Zostawcie mnie samą" if is_female_spk else ("Zostawcie mnie samego" if is_male_spk else "Zostawcie mnie w spokoju")
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

        # 6b. Filars CLXXVII-CLXXXI: Somatic decoupling, deictic motion vector, sensory pleonasm
        from series_memory import (
            sanitize_pronominal_somatic_possession,
            sanitize_deictic_motion_vector,
            sanitize_sensory_pleonasm
        )
        mod_som = sanitize_pronominal_somatic_possession(modified)
        if mod_som != modified:
            applied_fixes.append(f"[Filar CLXXVII Pronominal Decoupling] Oczyszczono zaimkozę somatyczną/relacyjną -> '{mod_som}'")
            modified = mod_som

        mod_deic = sanitize_deictic_motion_vector(modified)
        if mod_deic != modified:
            applied_fixes.append(f"[Filar CLXXX Wektor Deiktyczny Ruchu] Skorygowano fałszywy wektor ruchu -> '{mod_deic}'")
            modified = mod_deic

        mod_pleon = sanitize_sensory_pleonasm(modified)
        if mod_pleon != modified:
            applied_fixes.append(f"[Filar CLXXXI Tłumienie Pleonazmów Zmysłowych] Zlikwidowano pleonazm sensoryczno-przestrzenny -> '{mod_pleon}'")
            modified = mod_pleon

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
    # Non-declinable / feminine nouns on -ała:
    "mała", "biała", "skała", "chwała", "ciała", "pała", "żała", "strzała", "pochwała",
    "centrala", "sala", "hala", "kabała", "brygala", "działa",
    # Adjectives on -ała (inherently adjectival, not past verbs):
    "cała", "stała", "wspaniała", "doskonała", "okazała", "zardzewiała", "ocalała", "oszalała",
    "zdumiała", "zgorzkniała", "zmartwiała", "skamieniała", "osłupiała", "posiniała", "spęczniała",
    "dojrzała", "niedojrzała", "zuchwała", "ospała", "nieśmiała", "śmiała", "trwała", "nietrwała",
    # Genitive / Accusative forms of nouns on -ał, -oł, -eł, -ło:
    "generała", "admirała", "marszałka", "rywala", "diabła", "karła", "orła", "sokoła", "anioła",
    "archanioła", "osła", "kozła", "kanała", "kryształa", "zapała", "banała", "arsenała", "ideała",
    "minerała", "kardynała", "oryginała", "kryminała", "trybunała", "kapitała", "materiała",
    "przedziała", "udziała", "rozdziała", "podziała", "przydziała", "cymbała", "kawała", "zawała",
    "finała", "półfinała", "ćwierćfinała", "kaprała", "postrzała", "wystrzała", "odstrzała", "ostrzała",
    "prześcieradła", "zwierciadła", "kowadła", "prawidła", "imadła", "kadzidła", "sidła", "straszydła",
    "wędzidła", "malowidła", "widziadła", "mamidła", "mydła", "gardła", "skrzydła", "źródła", "godła",
    "bydła", "siodła", "wiosła", "szkła", "ciepła", "piekła", "pudła", "arcydzieła", "dzieła", "czółna",
    "koła", "czoła"
}

NON_VERBS_ON_AL = {
    "kanał", "kryształ", "szał", "wał", "ciał", "dział", "przydział", "rozdział", "podział",
    "generał", "admirał", "rywal", "finał", "półfinał", "ćwierćfinał", "kapitał", "materiał",
    "minerał", "przedział", "udział", "zapał", "banał", "arsenał", "ideał", "kryminał", "trybunał",
    "piedestał", "rytuał", "serial", "festiwal", "skandal", "wandal", "szpital", "metal", "medal",
    "pedal", "detal", "portal", "cymbał", "kawał", "zawał", "pował", "nawał", "strzał", "postrzał",
    "wystrzał", "odstrzał", "ostrzał", "morał", "korał", "kardynał", "oryginał", "prowincjał", "oficjał",
    "kaprał", "koronał"
}

def convert_feminine_past_to_masculine(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in NON_VERBS_ON_ALA:
        return None
    if v_lower in FEMININE_IRREGULAR_TO_MASCULINE:
        res = FEMININE_IRREGULAR_TO_MASCULINE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    # Class 1: -szła -> -szedł
    if v_lower.endswith("szła"):
        prefix = v_lower[:-4]
        if prefix.endswith("ode"): prefix = prefix[:-3] + "od"
        elif prefix.endswith("we"): prefix = prefix[:-2] + "w"
        elif prefix.endswith("ze"): prefix = prefix[:-2] + "z"
        elif prefix.endswith("roze"): prefix = prefix[:-4] + "roz"
        elif prefix.endswith("nade"): prefix = prefix[:-4] + "nad"
        elif prefix.endswith("pode"): prefix = prefix[:-4] + "pod"
        elif prefix.endswith("obe"): prefix = prefix[:-3] + "ob"
        res = prefix + "szedł"
    elif v_lower.endswith("szłaby"):
        prefix = v_lower[:-6]
        if prefix.endswith("ode"): prefix = prefix[:-3] + "od"
        elif prefix.endswith("we"): prefix = prefix[:-2] + "w"
        elif prefix.endswith("ze"): prefix = prefix[:-2] + "z"
        elif prefix.endswith("roze"): prefix = prefix[:-4] + "roz"
        elif prefix.endswith("nade"): prefix = prefix[:-4] + "nad"
        elif prefix.endswith("pode"): prefix = prefix[:-4] + "pod"
        elif prefix.endswith("obe"): prefix = prefix[:-3] + "ob"
        res = prefix + "szedłby"
    # Class 2: -ogła -> -ógł
    elif v_lower.endswith("ogła"):
        res = v_lower[:-4] + "ógł"
    elif v_lower.endswith("ogłaby"):
        res = v_lower[:-6] + "ógłby"
    # Class 3: -osła -> -ósł, -iozła -> -iózł, -iodła -> -iódł, -otła -> -ótł
    elif v_lower.endswith("niosła"):
        res = v_lower[:-6] + "niósł"
    elif v_lower.endswith("niosłaby"):
        res = v_lower[:-8] + "niósłby"
    elif v_lower.endswith("wiozła"):
        res = v_lower[:-6] + "wiózł"
    elif v_lower.endswith("wiozłaby"):
        res = v_lower[:-8] + "wiózłby"
    elif v_lower.endswith("wiodła"):
        res = v_lower[:-6] + "wiódł"
    elif v_lower.endswith("wiodłaby"):
        res = v_lower[:-8] + "wiódłby"
    elif v_lower.endswith("plotła"):
        res = v_lower[:-6] + "plótł"
    elif v_lower.endswith("miotła"):
        res = v_lower[:-6] + "miótł"
    elif v_lower.endswith("gniotła"):
        res = v_lower[:-7] + "gniótł"
    elif v_lower.endswith("rosła"):
        res = v_lower[:-5] + "rósł"
    # Class 4: -arła -> -arł
    elif v_lower.endswith("arła"):
        res = v_lower[:-1]
    elif v_lower.endswith("arłaby"):
        res = v_lower[:-3] + "y"
    # Class 5: -ekła -> -ekł, -egła -> -egł
    elif v_lower.endswith(("ekła", "egła")):
        res = v_lower[:-1]
    elif v_lower.endswith(("ekłaby", "egłaby")):
        res = v_lower[:-3] + "y"
    # Class 6: -adła -> -adł, -asła -> -asł, -arzła -> -arzł, -okła -> -okł
    elif v_lower.endswith(("adła", "asła", "arzła", "okła", "ilkła")):
        res = v_lower[:-1]
    elif v_lower.endswith(("adłaby", "asłaby", "arzłaby", "okłaby")):
        res = v_lower[:-3] + "y"
    # Class 7: -ęła -> -ął
    elif v_lower.endswith("ęła"):
        res = v_lower[:-3] + "ął"
    elif v_lower.endswith("ęłaby"):
        res = v_lower[:-5] + "ąłby"
    # Regular:
    elif v_lower.endswith("iałaby"):
        res = v_lower[:-6] + "iałby"
    elif v_lower.endswith("ałaby"):
        res = v_lower[:-5] + "ałby"
    elif v_lower.endswith("iłaby"):
        res = v_lower[:-5] + "iłby"
    elif v_lower.endswith("yłaby"):
        res = v_lower[:-5] + "yłby"
    elif v_lower.endswith("ułaby"):
        res = v_lower[:-5] + "ułby"
    elif v_lower.endswith("łaby"):
        res = v_lower[:-4] + "łby"
    elif v_lower.endswith("iała"):
        res = v_lower[:-4] + "iał"
    elif v_lower.endswith("ała"):
        res = v_lower[:-3] + "ał"
    elif v_lower.endswith("iła"):
        res = v_lower[:-3] + "ił"
    elif v_lower.endswith("yła"):
        res = v_lower[:-3] + "ył"
    elif v_lower.endswith("uła"):
        res = v_lower[:-3] + "uł"
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

    # Class 1: -szedł -> -szła
    if v_lower.endswith("szedł"):
        prefix = v_lower[:-5]
        if prefix.endswith("od"): prefix = prefix[:-2] + "ode"
        elif prefix.endswith("w"): prefix = prefix[:-1] + "we"
        elif prefix.endswith("z"): prefix = prefix[:-1] + "ze"
        elif prefix.endswith("roz"): prefix = prefix[:-3] + "roze"
        elif prefix.endswith("nad"): prefix = prefix[:-3] + "nade"
        elif prefix.endswith("pod"): prefix = prefix[:-3] + "pode"
        elif prefix.endswith("ob"): prefix = prefix[:-2] + "obe"
        res = prefix + "szła"
    elif v_lower.endswith("szedłby"):
        prefix = v_lower[:-7]
        if prefix.endswith("od"): prefix = prefix[:-2] + "ode"
        elif prefix.endswith("w"): prefix = prefix[:-1] + "we"
        elif prefix.endswith("z"): prefix = prefix[:-1] + "ze"
        elif prefix.endswith("roz"): prefix = prefix[:-3] + "roze"
        elif prefix.endswith("nad"): prefix = prefix[:-3] + "nade"
        elif prefix.endswith("pod"): prefix = prefix[:-3] + "pode"
        elif prefix.endswith("ob"): prefix = prefix[:-2] + "obe"
        res = prefix + "szłaby"
    # Class 2: -ógł -> -ogła
    elif v_lower.endswith("ógł"):
        res = v_lower[:-3] + "ogła"
    elif v_lower.endswith("ógłby"):
        res = v_lower[:-5] + "ogłaby"
    # Class 3: -ósł -> -osła, -iózł -> -iozła, -iódł -> -iodła, -ótł -> -otła
    elif v_lower.endswith("niósł"):
        res = v_lower[:-5] + "niosła"
    elif v_lower.endswith("niósłby"):
        res = v_lower[:-7] + "niosłaby"
    elif v_lower.endswith("wiózł"):
        res = v_lower[:-5] + "wiozła"
    elif v_lower.endswith("wiózłby"):
        res = v_lower[:-7] + "wiozłaby"
    elif v_lower.endswith("wiódł"):
        res = v_lower[:-5] + "wiodła"
    elif v_lower.endswith("wiódłby"):
        res = v_lower[:-7] + "wiodłaby"
    elif v_lower.endswith(("plótł", "plotł")):
        res = v_lower[:-5] + "plotła"
    elif v_lower.endswith(("plótłby", "plotłby")):
        res = v_lower[:-7] + "plotłaby"
    elif v_lower.endswith(("miótł", "miotł")):
        res = v_lower[:-5] + "miotła"
    elif v_lower.endswith(("miótłby", "miotłby")):
        res = v_lower[:-7] + "miotłaby"
    elif v_lower.endswith(("gniótł", "gniotł")):
        res = v_lower[:-6] + "gniotła"
    elif v_lower.endswith(("gniótłby", "gniotłby")):
        res = v_lower[:-8] + "gniotłaby"
    elif v_lower.endswith(("rósł", "rosł")):
        res = v_lower[:-4] + "rosła"
    elif v_lower.endswith(("rósłby", "rosłby")):
        res = v_lower[:-6] + "rosłaby"
    # Class 4: -arł -> -arła
    elif v_lower.endswith("arł"):
        res = v_lower + "a"
    elif v_lower.endswith("arłby"):
        res = v_lower[:-2] + "aby"
    # Class 5: -ekł -> -ekła, -egł -> -egła
    elif v_lower.endswith(("ekł", "egł")):
        res = v_lower + "a"
    elif v_lower.endswith(("ekłby", "egłby")):
        res = v_lower[:-2] + "aby"
    # Class 6: -adł -> -adła, -asł -> -asła, -arzł -> -arzła, -okł -> -okła
    elif v_lower.endswith(("adł", "asł", "arzł", "okł", "ilkł")):
        res = v_lower + "a"
    elif v_lower.endswith(("adłby", "asłby", "arzłby", "okłby")):
        res = v_lower[:-2] + "aby"
    # Class 7: -ął -> -ęła
    elif v_lower.endswith("ął"):
        res = v_lower[:-2] + "ęła"
    elif v_lower.endswith("ąłby"):
        res = v_lower[:-4] + "ęłaby"
    # Standard regular endings:
    elif v_lower.endswith("iałby"):
        res = v_lower[:-5] + "iałaby"
    elif v_lower.endswith("ałby"):
        res = v_lower[:-4] + "ałaby"
    elif v_lower.endswith("iłby"):
        res = v_lower[:-4] + "iłaby"
    elif v_lower.endswith("yłby"):
        res = v_lower[:-4] + "yłaby"
    elif v_lower.endswith("ułby"):
        res = v_lower[:-4] + "ułaby"
    elif v_lower.endswith("łby"):
        res = v_lower[:-3] + "łaby"
    elif v_lower.endswith("iał"):
        res = v_lower[:-3] + "iała"
    elif v_lower.endswith("ał"):
        res = v_lower[:-2] + "ała"
    elif v_lower.endswith("ił"):
        res = v_lower[:-2] + "iła"
    elif v_lower.endswith("ył"):
        res = v_lower[:-2] + "yła"
    elif v_lower.endswith("uł"):
        res = v_lower[:-2] + "uła"
    else:
        return None

    return res.capitalize() if verb[0].isupper() else res

NON_VERBS_ON_LEM = {
    # Nouns ending with -łem (Instrumental singular of masculine/neuter nouns):
    "ciałem", "działem", "szałem", "kryształem", "materiałem", "kanałem", "finałem",
    "półfinałem", "ćwierćfinałem", "kapitałem", "przedziałem", "udziałem", "rozdziałem",
    "podziałem", "przydziałem", "zapałem", "banałem", "arsenałem", "ideałem", "minerałem",
    "kardynałem", "oryginałem", "kryminałem", "trybunałem", "piedestałem", "rytuałem",
    "serialem", "festiwalem", "skandalem", "wandalem", "szpitalem", "metalem", "medalem",
    "portalem", "detalem", "cymbałem", "kawałem", "zawałem", "powałem", "nawałem",
    "orłem", "diabłem", "kozłem", "osłem", "gardłem", "mydłem", "skrzydłem", "źródłem",
    "bydłem", "godłem", "wiosłem", "żądłem", "ciepłem", "szkłem", "światłem", "kołem",
    "dołem", "stołem", "popiołem", "żywiołem", "czołem", "aniołem", "archaniołem",
    "sokołem", "dzięciołem", "karłem", "posłem", "mułem", "tiulem", "ulem", "karakułem",
    "artykułem", "protokołem", "kościołem", "rosołem", "kotłem", "węzłem", "kubłem",
    "wróblem", "szczeblem", "bąblem", "bublem", "kneblem", "meblem", "skoblem",
    "kartoflem", "kaflem", "kuflem", "ryglem", "węglem", "żaglem", "kręglem", "pudłem",
    "dziełem", "arcydziełem", "piekłem", "sidłem", "stadłem", "siodłem", "rzemiosłem",
    "zwierciadłem", "kowadłem", "prawidłem", "imadłem", "kadzidłem", "kropidłem",
    "powidłem", "straszydłem", "wędzidłem", "malowidłem", "widziadłem", "mamidłem",
    "prześcieradłem", "umysłem", "zmysłem", "przemysłem", "domysłem", "namysłem",
    "zamysłem", "rozmysłem", "pomysłem", "wymysłem", "hasłem", "masłem", "krzesłem",
    "ciosłem", "przęsłem", "pomięsłem", "czółnem", "cokołem", "matołem", "generałem",
    "admirałem", "marszałkiem", "rywalem", "kaprałem", "postrzałem", "wystrzałem",
    "odstrzałem", "ostrzałem"
}

FIRST_PERSON_MASCULINE_IRREGULAR_TO_FEMININE = {
    "poszedłem": "poszłam", "wyszedłem": "wyszłam", "przyszedłem": "przyszłam",
    "odszedłem": "odeszłam", "wszedłem": "weszłam", "przeszedłem": "przeszłam",
    "doszedłem": "doszłam", "zaszedłem": "zaszłam", "zszedłem": "zeszłam", "zeszedłem": "zeszłam", "zeszłem": "zeszłam",
    "rozszedłem": "rozeszłam", "znalazłem": "znalazłam", "mógłbym": "mogłabym", "chciałbym": "chciałabym",
    "wolałbym": "wolałabym", "powinienem": "powinnam", "doniósłbym": "doniosłabym",
    "wziąłem": "wzięłam", "zacząłem": "zaczęłam", "zdjąłem": "zdjęłam",
    "przyjąłem": "przyjęłam", "objąłem": "objęłam", "zająłem": "zajęłam",
    "wziąłbym": "wzięłabym", "zacząłbym": "zaczęłabym", "dopiąłbym": "dopięłabym",
    "odpiąłbym": "odpięłabym", "przypiąłbym": "przypięłabym", "napiąłbym": "napięłabym",
    "stanąłbym": "stanęłabym", "zamknąłbym": "zamknęłabym", "dotknąłbym": "dotknęłabym",
    "machnąłbym": "machnęłabym", "krzyknąłbym": "krzyknęłabym", "zerknąłbym": "zerknęłabym",
    "pomógłbym": "pomogłabym", "poszedłbym": "poszłabym", "przyszedłbym": "przyszłabym",
    "wyszedłbym": "wyszłabym", "odszedłbym": "odeszłabym", "wszedłbym": "weszłabym",
    "padszedłbym": "podeszłabym", "podszedłbym": "podeszłabym", "nadszedłbym": "nadeszłabym",
    "obszedłbym": "obeszłabym", "zszedłbym": "zeszłabym", "przeszedłbym": "przeszłabym",
    "doszedłbym": "doszłabym", "zaszedłbym": "zaszłabym", "rozszedłbym": "rozeszłabym",
    "nadszedłem": "nadeszłam", "podszedłem": "podeszłam", "obszedłem": "obeszłam",
    "padłem": "padłam", "przepadłem": "przepadłam", "odpadłem": "odpadłam", "dopadłem": "dopadłam",
    "wypadłem": "wypadłam", "napadłem": "napadłam", "zapadłem": "zapadłam", "rozpadłem": "rozpadłam",
    "upadłem": "upadłam", "przypadłem": "przypadłam", "opadłem": "opadłam",
    "usiadłem": "usiadłam", "wsiadłem": "wsiadłam", "wysiadłem": "wysiadłam", "przysiadłem": "przysiadłam",
    "podsiadłem": "podsiadłam", "dosiadłem": "dosiadłam", "osiadłem": "osiadłam", "zsiadłem": "zsiadłam",
    "zbiegłem": "zbiegłam", "odbiegłem": "odbiegłam", "uległem": "uległam", "wybiegłem": "wybiegłam",
    "przybiegłem": "przybiegłam", "pobiegłem": "pobiegłam", "nadbiegłem": "nadbiegłam", "podbiegłem": "podbiegłam",
    "dobiegłem": "dobiegłam", "zabiegłem": "zabiegłam", "ubiegłem": "ubiegłam", "przebiegłem": "przebiegłam",
    "mokłem": "mokłam", "zmokłem": "zmokłam", "przemokłem": "przemokłam", "namokłem": "namokłam",
    "zmarzłem": "zmarzłam", "zamarzłem": "zamarzłam", "przemarzłem": "przemarzłam", "przymarzłem": "przymarzłam",
    "zgasłem": "zgasłam", "wygasłem": "wygasłam", "przygasłem": "przygasłam",
    "zmilkłem": "zmilkłam", "umilkłem": "umilkłam", "pomilkłem": "pomilkłam", "zamilkłem": "zamilkłam",
    "wyblakłem": "wyblakłam", "zbladłem": "zbladłam", "pobladłem": "pobladłam",
    "ochrypłem": "ochrypłam", "schrypłem": "schrypłam",
    "mogłem": "mogłam", "pomogłem": "pomogłam", "wspomogłem": "wspomogłam", "przemogłem": "przemogłam",
    "rzekłem": "rzekłam", "odrzekłem": "odrzekłam", "uciekłem": "uciekłam",
    "umarłem": "umarłam", "zmarłem": "zmarłam", "zamarłem": "zamarłam", "pomarłem": "pomarłam",
    "starłem": "starłam", "wytarłem": "wytarłam", "przetarłem": "przetarłam", "otarłem": "otarłam",
    "dotarłem": "dotarłam", "natarłem": "natarłam", "podparłem": "podparłam", "oparłem": "oparłam",
    "odparłem": "odparłam", "zaparłem": "zaparłam", "wsparłem": "wsparłam", "rozparłem": "rozparłam",
    "uparłem": "uparłam", "zawarłem": "zawarłam", "otwarłem": "otwarłam", "wywarłem": "wywarłam",
    "odwarłem": "odwarłam", "rozwarłem": "rozwarłam", "zwarłem": "zwarłam", "rozdarłem": "rozdarłam",
    "wydarłem": "wydarłam", "podarłem": "podarłam", "przedarłem": "przedarłam", "odarłem": "odarłam",
    "wdarłem": "wdarłam",
    "plotłem": "plotłam", "wyplotłem": "wyplotłam", "zaplotłem": "zaplotłam", "splotłem": "splotłam",
    "zmiotłem": "zmiotłam", "omiotłem": "omiotłam", "wymiotłem": "wymiotłam", "zamiotłem": "zamiotłam",
    "urosłem": "urosłam", "wyrosłem": "wyrosłam", "dorosłem": "dorosłam", "porosłem": "porosłam",
    "zarosłem": "zarosłam", "wzrosłem": "wzrosłam",
    "przyniosłem": "przyniosłam", "odniosłem": "odniosłam", "wniosłem": "wniosłam", "wyniosłem": "wyniosłam",
    "zaniosłem": "zaniosłam", "podniosłem": "podniosłam", "poniosłem": "poniosłam", "doniosłem": "doniosłam",
    "przeniosłem": "przeniosłam",
    "przywiozłem": "przywiozłam", "odwiozłem": "odwiozłam", "wwiozłem": "wwiozłam", "wywiozłem": "wywiozłam",
    "zawiozłem": "zawiozłam", "podwiozłem": "podwiozłam", "dowiozłem": "dowiozłam", "przewiozłem": "przewiozłam",
    "przywiodłem": "przywiodłam", "odwiodłem": "odwiodłam", "wywiodłem": "wywiodłam", "zawiodłem": "zawiodłam",
    "dowiodłem": "dowiodłam", "uwiodłem": "uwiodłam", "zwiodłem": "zwiodłam",
}

FIRST_PERSON_FEMININE_IRREGULAR_TO_MASCULINE = {
    "poszłam": "poszedłem", "wyszłam": "wyszedłem", "przyszłam": "przyszedłem",
    "odeszłam": "odszedłem", "weszłam": "wszedłem", "przeszłam": "przeszedłem",
    "doszłam": "doszedłem", "zaszłam": "zaszedłem", "zeszłam": "zszedłem",
    "rozeszłam": "rozszedłem", "znalazłam": "znalazłem", "mogłabym": "mógłbym", "chciałabym": "chciałbym",
    "wolałabym": "wolałbym", "powinnam": "powinienem", "doniosłabym": "doniósłbym",
    "wzięłam": "wziąłem", "zaczęłam": "zacząłem", "zdjąłam": "zdjąłem",
    "przyjęłam": "przyjąłem", "objęłam": "objąłem", "zajęłam": "zajęłem",
    "wzięłabym": "wziąłbym", "zaczęłabym": "zacząłbym", "dopięłabym": "dopiąłbym",
    "odpięłabym": "odpiąłbym", "przypięłabym": "przypiąłbym", "napięłabym": "napiąłbym",
    "stanęłabym": "stanąłbym", "zamknęłabym": "zamknąłbym", "dotknęłabym": "dotknąłbym",
    "machnęłabym": "machnąłbym", "krzyknęłabym": "krzyknąłbym", "zerknęłabym": "zerknąłbym",
    "pomogłabym": "pomógłbym", "poszłabym": "poszedłbym", "przyszłabym": "przyszedłbym",
    "wyszłabym": "wyszedłbym", "odeszłabym": "odszedłbym", "weszłabym": "wszedłbym",
    "podeszłabym": "podszedłbym", "nadeszłabym": "nadszedłbym", "obeszłabym": "obszedłbym",
    "zeszłabym": "zszedłbym", "przeszłabym": "przeszedłbym", "doszłabym": "doszedłbym",
    "zaszłabym": "zaszedłbym", "rozeszłabym": "rozszedłbym",
    "nadeszłam": "nadszedłem", "podeszłam": "podszedłem", "obeszłam": "obszedłem",
    "padłam": "padłem", "przepadłam": "przepadłem", "odpadłam": "odpadłem", "dopadłam": "dopadłem",
    "wypadłam": "wypadłem", "napadłam": "napadłem", "zapadłam": "zapadłem", "rozpadłam": "rozpadłem",
    "upadłam": "upadłem", "przypadłam": "przypadłem", "opadłam": "opadłem",
    "usiadłam": "usiadłem", "wsiadłam": "wsiadłem", "wysiadłam": "wysiadłem", "przysiadłam": "przysiadłem",
    "podsiadłam": "podsiadłem", "dosiadłam": "dosiadłem", "osiadłam": "osiadłem", "zsiadłam": "zsiadłem",
    "zbiegłam": "zbiegłem", "odbiegłam": "odbiegłem", "uległam": "uległem", "wybiegłam": "wybiegłem",
    "przybiegłam": "przybiegłem", "pobiegłam": "pobiegłem", "nadbiegłam": "nadbiegłem", "podbiegłam": "podbiegłem",
    "dobiegłam": "dobiegłem", "zabiegłam": "zabiegłem", "ubiegłam": "ubiegłem", "przebiegłam": "przebiegłem",
    "mokłam": "mokłem", "zmokłam": "zmokłem", "przemokłam": "przemokłem", "namokłam": "namokłem",
    "zmarzłam": "zmarzłem", "zamarzłam": "zamarzłem", "przemarzłam": "przemarzłem", "przymarzłam": "przymarzłem",
    "zgasłam": "zgasłem", "wygasłam": "wygasłem", "przygasłam": "przygasłem",
    "zmilkłam": "zmilkłem", "umilkłam": "umilkłem", "pomilkłam": "pomilkłem", "zamilkłam": "zamilkłem",
    "wyblakłam": "wyblakłem", "zbladłam": "zbladłem", "pobladłam": "pobladłem",
    "ochrypłam": "ochrypłem", "schrypłam": "schrypłem",
    "mogłam": "mogłem", "pomogłam": "pomogłem", "wspomogłam": "wspomogłem", "przemogłam": "przemogłem",
    "rzekłam": "rzekłem", "odrzekłam": "odrzekłem", "uciekłam": "uciekłem",
    "umarłam": "umarłem", "zmarłam": "zmarłem", "zamarłam": "zamarłem", "pomarłam": "pomarłem",
    "starłam": "starłem", "wytarłam": "wytarłem", "przetarłam": "przetarłem", "otarłam": "otarłem",
    "dotarłam": "dotarłem", "natarłam": "natarłem", "podparłam": "podparłem", "oparłam": "oparłem",
    "odparłam": "odparłem", "zaparłam": "zaparłem", "wsparłam": "wsparłem", "rozparłam": "rozparłem",
    "uparłam": "uparłem", "zawarłam": "zawarłem", "otwarłam": "otwarłem", "wywarłam": "wywarłem",
    "odwarłam": "odwarłem", "rozwarłam": "rozwarłem", "zwarłam": "zwarłem", "rozdarłam": "rozdarłem",
    "wydarłam": "wydarłem", "podarłam": "podarłem", "przedarłam": "przedarłem", "odarłam": "odarłem",
    "wdarłam": "wdarłem",
    "plotłam": "plotłem", "wyplotłam": "wyplotłem", "zaplotłam": "zaplotłem", "splotłam": "splotłem",
    "zmiotłam": "zmiotłem", "omiotłam": "omiotłem", "wymiotłam": "wymiotłem", "zamiotłam": "zamiotłem",
    "urosłam": "urosłem", "wyrosłam": "wyrosłem", "dorosłam": "dorosłem", "porosłam": "porosłem",
    "zarosłam": "zarosłem", "wzrosłam": "wzrosłem",
    "przyniosłam": "przyniosłem", "odniosłam": "odniosłem", "wniosłam": "wniosłem", "wyniosłam": "wyniosłem",
    "zaniosłam": "zaniosłem", "podniosłam": "podniosłem", "poniosłam": "poniosłem", "doniosłam": "doniosłem",
    "przeniosłam": "przeniosłem",
    "przywiozłam": "przywiozłem", "odwiozłam": "odwiozłem", "wwiozłam": "wwiozłem", "wywiozłam": "wywiozłem",
    "zawiozłam": "zawiozłem", "podwiozłam": "podwiozłem", "dowiozłam": "dowiozłem", "przewiozłam": "przewiozłem",
    "przywiodłam": "przywiodłem", "odwiodłam": "odwiodłem", "wywiodłam": "wywiodłem", "zawiodłam": "zawiodłem",
    "dowiodłam": "dowiodłem", "uwiodłam": "uwiodłem", "zwiodłam": "zwiodłem",
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
    elif v_lower.endswith("szedłbym"):
        prefix = v_lower[:-8]
        if prefix.endswith("od"): prefix = prefix[:-2] + "ode"
        elif prefix.endswith("w"): prefix = prefix[:-1] + "we"
        elif prefix.endswith("z"): prefix = prefix[:-1] + "ze"
        elif prefix.endswith("roz"): prefix = prefix[:-3] + "roze"
        elif prefix.endswith("nad"): prefix = prefix[:-3] + "nade"
        elif prefix.endswith("pod"): prefix = prefix[:-3] + "pode"
        elif prefix.endswith("ob"): prefix = prefix[:-2] + "obe"
        res = prefix + "szłabym"
    elif v_lower.endswith("niósłbym"):
        res = v_lower[:-8] + "niosłabym"
    elif v_lower.endswith("wiózłbym"):
        res = v_lower[:-8] + "wiozłabym"
    elif v_lower.endswith("wiódłbym"):
        res = v_lower[:-8] + "wiodłabym"
    elif v_lower.endswith(("plótłbym", "plotłbym")):
        res = v_lower[:-8] + "plotłabym"
    elif v_lower.endswith(("miótłbym", "miotłbym")):
        res = v_lower[:-8] + "miotłabym"
    elif v_lower.endswith(("gniótłbym", "gniotłbym")):
        res = v_lower[:-9] + "gniotłabym"
    elif v_lower.endswith(("rósłbym", "rosłbym")):
        res = v_lower[:-7] + "rosłabym"
    elif v_lower.endswith("arłbym"):
        res = v_lower[:-6] + "arłabym"
    elif v_lower.endswith("ekłbym"):
        res = v_lower[:-6] + "ekłabym"
    elif v_lower.endswith("egłbym"):
        res = v_lower[:-6] + "egłabym"
    elif v_lower.endswith("adłbym"):
        res = v_lower[:-6] + "adłabym"
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
    elif v_lower.endswith("ogłem"):
        res = v_lower[:-5] + "ogłam"
    elif v_lower.endswith("ekłem"):
        res = v_lower[:-5] + "ekłam"
    elif v_lower.endswith("arłem"):
        res = v_lower[:-5] + "arłam"
    elif v_lower.endswith("otłem"):
        res = v_lower[:-5] + "otłam"
    elif v_lower.endswith("wiodłem"):
        res = v_lower[:-7] + "wiodłam"
    elif v_lower.endswith("wiozłem"):
        res = v_lower[:-7] + "wiozłam"
    elif v_lower.endswith("gniotłem"):
        res = v_lower[:-8] + "gniotłam"
    elif v_lower.endswith("szedłem"):
        prefix = v_lower[:-7]
        if prefix.endswith("od"): prefix = prefix[:-2] + "ode"
        elif prefix.endswith("w"): prefix = prefix[:-1] + "we"
        elif prefix.endswith("z"): prefix = prefix[:-1] + "ze"
        elif prefix.endswith("roz"): prefix = prefix[:-3] + "roze"
        elif prefix.endswith("nad"): prefix = prefix[:-3] + "nade"
        elif prefix.endswith("pod"): prefix = prefix[:-3] + "pode"
        elif prefix.endswith("ob"): prefix = prefix[:-2] + "obe"
        res = prefix + "szłam"
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
    elif v_lower.endswith("szłabym"):
        prefix = v_lower[:-7]
        if prefix.endswith("ode"): prefix = prefix[:-3] + "od"
        elif prefix.endswith("we"): prefix = prefix[:-2] + "w"
        elif prefix.endswith("ze"): prefix = prefix[:-2] + "z"
        elif prefix.endswith("roze"): prefix = prefix[:-4] + "roz"
        elif prefix.endswith("nade"): prefix = prefix[:-4] + "nad"
        elif prefix.endswith("pode"): prefix = prefix[:-4] + "pod"
        elif prefix.endswith("obe"): prefix = prefix[:-3] + "ob"
        res = prefix + "szedłbym"
    elif v_lower.endswith("niosłabym"):
        res = v_lower[:-9] + "niósłbym"
    elif v_lower.endswith("wiozłabym"):
        res = v_lower[:-9] + "wiózłbym"
    elif v_lower.endswith("wiodłabym"):
        res = v_lower[:-9] + "wiódłbym"
    elif v_lower.endswith("plotłabym"):
        res = v_lower[:-9] + "plótłbym"
    elif v_lower.endswith("miotłabym"):
        res = v_lower[:-9] + "miótłbym"
    elif v_lower.endswith("gniotłabym"):
        res = v_lower[:-10] + "gniótłbym"
    elif v_lower.endswith("rosłabym"):
        res = v_lower[:-8] + "rósłbym"
    elif v_lower.endswith("arłabym"):
        res = v_lower[:-7] + "arłbym"
    elif v_lower.endswith("ekłabym"):
        res = v_lower[:-7] + "ekłbym"
    elif v_lower.endswith("egłabym"):
        res = v_lower[:-7] + "egłbym"
    elif v_lower.endswith("adłabym"):
        res = v_lower[:-7] + "adłbym"
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
    elif v_lower.endswith("ogłam"):
        res = v_lower[:-5] + "ogłem"
    elif v_lower.endswith("ekłam"):
        res = v_lower[:-5] + "ekłem"
    elif v_lower.endswith("arłam"):
        res = v_lower[:-5] + "arłem"
    elif v_lower.endswith("otłam"):
        res = v_lower[:-5] + "otłem"
    elif v_lower.endswith("wiodłam"):
        res = v_lower[:-7] + "wiodłem"
    elif v_lower.endswith("wiozłam"):
        res = v_lower[:-7] + "wiozłem"
    elif v_lower.endswith("gniotłam"):
        res = v_lower[:-8] + "gniotłem"
    elif v_lower.endswith("szłam"):
        prefix = v_lower[:-5]
        if prefix.endswith("ode"): prefix = prefix[:-3] + "od"
        elif prefix.endswith("we"): prefix = prefix[:-2] + "w"
        elif prefix.endswith("ze"): prefix = prefix[:-2] + "z"
        elif prefix.endswith("roze"): prefix = prefix[:-4] + "roz"
        elif prefix.endswith("nade"): prefix = prefix[:-4] + "nad"
        elif prefix.endswith("pode"): prefix = prefix[:-4] + "pod"
        elif prefix.endswith("obe"): prefix = prefix[:-3] + "ob"
        res = prefix + "szedłem"
    elif any(v_lower.endswith(stem) for stem in ("niosłam", "trząsłam", "prząsłam", "pasłam", "rosłam")):
        res = v_lower[:-4] + "słem"
    else:
        return None
    return res.capitalize() if verb[0].isupper() else res


def convert_passive_participle_to_masculine(participle: str) -> Optional[str]:
    p_lower = participle.lower()
    if p_lower.endswith("ona"):
        res = p_lower[:-3] + "ony"
    elif p_lower.endswith("ana"):
        res = p_lower[:-3] + "any"
    elif p_lower.endswith("ta"):
        res = p_lower[:-2] + "ty"
    elif p_lower.endswith("iona"):
        res = p_lower[:-4] + "iony"
    else:
        return None
    return res.capitalize() if participle[0].isupper() else res

def convert_passive_participle_to_feminine(participle: str) -> Optional[str]:
    p_lower = participle.lower()
    if p_lower.endswith("ony"):
        res = p_lower[:-3] + "ona"
    elif p_lower.endswith("any"):
        res = p_lower[:-3] + "ana"
    elif p_lower.endswith("ty"):
        res = p_lower[:-2] + "ta"
    elif p_lower.endswith("iony"):
        res = p_lower[:-4] + "iona"
    else:
        return None
    return res.capitalize() if participle[0].isupper() else res

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
    "niósłbyś": "niosłabyś",
    "doniósłbyś": "doniosłabyś",
    "przyniósłbyś": "przyniosłabyś",
    "wyniósłbyś": "wyniosłabyś",
    "zaniósłbyś": "zaniosłabyś",
    "odniósłbyś": "odniosłabyś",
    "przeniósłbyś": "przeniosłabyś",
    "podniósłbyś": "podniosłabyś",
    "wiózłbyś": "wiozłabyś",
    "przywiózłbyś": "przywiozłabyś",
    "wywiózłbyś": "wywiozłabyś",
    "zawiózłbyś": "zawiozłabyś",
    "odwiózłbyś": "odwiozłabyś",
    "przewiózłbyś": "przewiozłabyś",
    "dowiózłbyś": "dowiozłabyś",
    "wiódłbyś": "wiodłabyś",
    "przywiódłbyś": "przywiodłabyś",
    "wywiódłbyś": "wywiodłabyś",
    "dowiódłbyś": "dowiodłabyś",
    "odwiódłbyś": "odwiodłabyś",
    "przewiódłbyś": "przewiodłabyś",
    "zawiódłbyś": "zawiodłabyś",
    "wiódłeś": "wiodłaś",
    "dowiódłeś": "dowiodłaś",
    "przywiódłeś": "przywiodłaś",
    "odwiódłeś": "odwiodłaś",
    "wywiódłeś": "wywiodłaś",
    "przewiódłeś": "przewiodłaś",
    "zawiódłeś": "zawiodłaś",
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
    "niosłabyś": "niósłbyś",
    "doniosłabyś": "doniósłbyś",
    "przyniosłabyś": "przyniósłbyś",
    "wyniosłabyś": "wyniósłbyś",
    "zaniosłabyś": "zaniósłbyś",
    "odniosłabyś": "odniósłbyś",
    "przeniosłabyś": "przeniósłbyś",
    "podniosłabyś": "podniósłbyś",
    "wiozłabyś": "wiózłbyś",
    "przywiozłabyś": "przywiózłbyś",
    "wywiozłabyś": "wywiózłbyś",
    "zawiozłabyś": "zawiózłbyś",
    "odwiozłabyś": "odwiózłbyś",
    "przewiozłabyś": "przewiózłbyś",
    "dowiozłabyś": "dowiózłbyś",
    "wiodłabyś": "wiódłbyś",
    "przywiodłabyś": "przywiódłbyś",
    "wywiodłabyś": "wywiódłbyś",
    "dowiodłabyś": "dowiódłbyś",
    "odwiodłabyś": "odwiódłbyś",
    "przewiodłabyś": "przewiódłbyś",
    "zawiodłabyś": "zawiódłbyś",
    "wiodłaś": "wiódłeś",
    "dowiodłaś": "dowiódłeś",
    "przywiodłaś": "przywiódłeś",
    "odwiodłaś": "odwiódłeś",
    "wywiodłaś": "wywiódłeś",
    "przewiodłaś": "przewiódłeś",
    "zawiodłaś": "zawiódłeś",
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
    "głodny": "głodna",
    "spragniony": "spragniona",
    "śpiący": "śpiąca",
    "ranny": "ranna",
    "przytomny": "przytomna",
    "żywy": "żywa",
    "pijany": "pijana",
    "wykończony": "wykończona",
    "wyczerpany": "wyczerpana",
    "szalony": "szalona",
    "ślepy": "ślepa",
    "głuchy": "głucha",
    "dumny": "dumna",
    "zazdrosny": "zazdrosna",
    "przestraszony": "przestraszona",
    "zawstydzony": "zawstydzona",
    "przekonany": "przekonana",
    "zawiedziony": "zawiedziona",
    "rozczarowany": "rozczarowana",
    "naiwny": "naiwna",
    "głupi": "głupia",
    "okrutny": "okrutna",
    "niecierpliwy": "niecierpliwa",
    "niewinny": "niewinna",
    "winny": "winna",
    "spóźniony": "spóźniona",
    "zajęty": "zajęta",
    "zmuszony": "zmuszona",
    "zobowiązany": "zobowiązana",
    "uratowany": "uratowana",
    "pozbawiony": "pozbawiona",
    "skazany": "skazana",
    "oskarżony": "oskarżona",
    "zrozpaczony": "zrozpaczona",
    "zachwycony": "zachwycona",
    "poruszony": "poruszona",
    "wzruszony": "wzruszona",
    "przerażony": "przerażona",
    "upokorzony": "upokorzona",
    "oszołomiony": "oszołomiona",
    "otoczony": "otoczona",
    "uwięziony": "uwięziona",
    "zgubiony": "zgubiona",
    "znaleziony": "znaleziona",
    "zgładzony": "zgładzona",
    "zniszczony": "zniszczona",
    "zraniony": "zraniona",
    "uzbrojony": "uzbrojona",
    "związany": "związana",
    "odcięty": "odcięta",
    "zamknięty": "zamknięta",
    "otwarty": "otwarta",
    "rozdarty": "rozdarta",
    "przejęty": "przejęta",
    "przeklęty": "przeklęta",
    "silny": "silna",
    "słaby": "słaba",
    "mądry": "mądra",
    "piękny": "piękna",
    "brzydki": "brzydka",
    "młody": "młoda",
    "stary": "stara",
    "czysty": "czysta",
    "brudny": "brudna",
    "wolny": "wolna",
    "wdzięczny": "wdzięczna",
    "niewdzięczny": "niewdzięczna",
    "zakochany": "zakochana",
    "oburzony": "oburzona",
    "oszukany": "oszukana",
    "zdradzony": "zdradzona",
    "ocalony": "ocalona",
    "zbawiony": "zbawiona",
    "potępiony": "potępiona",
    "bezradny": "bezradna",
    "bezbronny": "bezbronna",
    "bezsilny": "bezsilna",
    "zdecydowany": "zdecydowana",
    "niezdecydowany": "niezdecydowana",
    "ostrożny": "ostrożna",
    "nieostrożny": "nieostrożna",
    "czujny": "czujna",
    "odważny": "odważna",
    "tchórzliwy": "tchórzliwa",
    "cierpliwy": "cierpliwa",
    "łagodny": "łagodna",
    "surowy": "surowa",
    "sprawiedliwy": "sprawiedliwa",
    "niesprawiedliwy": "niesprawiedliwa",
    "wierny": "wierna",
    "niewierny": "niewierna",
    "życzliwy": "życzliwa",
    "nieżyczliwy": "nieżyczliwa",
    "szczery": "szczera",
    "nieszczery": "nieszczera",
    "chciwy": "chciwa",
    "hojny": "hojna",
    "pokorny": "pokorna",
    "posłuszny": "posłuszna",
    "nieposłuszny": "nieposłuszna",
    "uległy": "uległa",
    "uparty": "uparta",
    "wesoły": "wesoła",
    "ponury": "ponura",
    "groźny": "groźna",
    "niebezpieczny": "niebezpieczna",
    "zdrowy": "zdrowa",
    "zabity": "zabita",
    "martwy": "martwa",
    "obudzony": "obudzona",
    "uśpiony": "uśpiona",
    "trzeźwy": "trzeźwa",
    "syty": "syta",
    "nagi": "naga",
    "ubrany": "ubrana",
    "przebrany": "przebrana",
    "rozbrojony": "rozbrojona",
    "rozwiązany": "rozwiązana",
    "uwolniony": "uwolniona",
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
    "głodna": "głodny",
    "spragniona": "spragniony",
    "śpiąca": "śpiący",
    "ranna": "ranny",
    "przytomna": "przytomny",
    "żywa": "żywy",
    "pijana": "pijany",
    "wykończona": "wykończony",
    "wyczerpana": "wyczerpany",
    "szalona": "szalony",
    "ślepa": "ślepy",
    "głucha": "głuchy",
    "dumna": "dumny",
    "zazdrosna": "zazdrosny",
    "przestraszona": "przestraszony",
    "zawstydzona": "zawstydzony",
    "przekonana": "przekonany",
    "zawiedziona": "zawiedziony",
    "rozczarowana": "rozczarowany",
    "naiwna": "naiwny",
    "głupia": "głupi",
    "okrutna": "okrutny",
    "niecierpliwa": "niecierpliwy",
    "niewinna": "niewinny",
    "winna": "winny",
    "spóźniona": "spóźniony",
    "zajęta": "zajęty",
    "zmuszona": "zmuszony",
    "zobowiązana": "zobowiązany",
    "uratowana": "uratowany",
    "pozbawiona": "pozbawiony",
    "skazana": "skazany",
    "oskarżona": "oskarżony",
    "zrozpaczona": "zrozpaczony",
    "zachwycona": "zachwycony",
    "poruszona": "poruszony",
    "wzruszona": "wzruszony",
    "przerażona": "przerażony",
    "upokorzona": "upokorzony",
    "oszołomiona": "oszołomiony",
    "otoczona": "otoczony",
    "uwięziona": "uwięziony",
    "zgubiona": "zgubiony",
    "znaleziona": "znaleziony",
    "zgładzona": "zgładzony",
    "zniszczona": "zniszczony",
    "zraniona": "zraniony",
    "uzbrojona": "uzbrojony",
    "związana": "związany",
    "odcięta": "odcięty",
    "zamknięta": "zamknięty",
    "otwarta": "otwarty",
    "rozdarta": "rozdarty",
    "przejęta": "przejęty",
    "przeklęta": "przeklęty",
    "silna": "silny",
    "słaba": "słaby",
    "mądra": "mądry",
    "piękna": "piękny",
    "brzydka": "brzydki",
    "młoda": "młody",
    "stara": "stary",
    "czysta": "czysty",
    "brudna": "brudny",
    "wolna": "wolny",
    "wdzięczna": "wdzięczny",
    "niewdzięczna": "niewdzięczny",
    "zakochana": "zakochany",
    "oburzona": "oburzony",
    "oszukana": "oszukany",
    "zdradzona": "zdradzony",
    "ocalona": "ocalony",
    "zbawiona": "zbawiony",
    "potępiona": "potępiony",
    "bezradna": "bezradny",
    "bezbronna": "bezbronny",
    "bezsilna": "bezsilny",
    "zdecydowana": "zdecydowany",
    "niezdecydowana": "niezdecydowany",
    "ostrożna": "ostrożny",
    "nieostrożna": "nieostrożny",
    "czujna": "czujny",
    "odważna": "odważny",
    "tchórzliwa": "tchórzliwy",
    "cierpliwa": "cierpliwy",
    "łagodna": "łagodny",
    "surowa": "surowy",
    "sprawiedliwa": "sprawiedliwy",
    "niesprawiedliwa": "niesprawiedliwy",
    "wierna": "wierny",
    "niewierna": "niewierny",
    "życzliwa": "życzliwy",
    "nieżyczliwa": "nieżyczliwy",
    "szczera": "szczery",
    "nieszczera": "nieszczery",
    "chciwa": "chciwy",
    "hojna": "hojny",
    "pokorna": "pokorny",
    "posłuszna": "posłuszny",
    "nieposłuszna": "nieposłuszny",
    "uległa": "uległy",
    "uparta": "uparty",
    "wesoła": "wesoły",
    "ponura": "ponury",
    "groźna": "groźny",
    "niebezpieczna": "niebezpieczny",
    "zdrowa": "zdrowy",
    "zabita": "zabity",
    "martwa": "martwy",
    "obudzona": "obudzony",
    "uśpiona": "uśpiony",
    "trzeźwa": "trzeźwy",
    "syta": "syty",
    "naga": "nagi",
    "ubrana": "ubrany",
    "przebrana": "przebrany",
    "rozbrojona": "rozbrojony",
    "rozwiązana": "rozwiązany",
    "uwolniona": "uwolniony",
}

# ==============================================================================
# 82 CANONICAL PREDICATE NOUN PAIRS & MODIFIERS (Zasada 12 & 15 AGENTS.md - 0.00 PLN)
# Full symmetrical paradigm for 1st & 2nd person (Instrumental & Nominative)
# ==============================================================================

PREDICATE_NOUNS_INSTRUMENTAL_PAIRS: List[Tuple[str, str]] = [
    # 1. Relacje rodzinne i bliskie (12 par)
    ("przyjacielem", "przyjaciółką"),
    ("bratem", "siostrą"),
    ("synem", "córką"),
    ("ojcem", "matką"),
    ("kuzynem", "kuzynką"),
    ("partnerem", "partnerką"),
    ("narzeczonym", "narzeczoną"),
    ("małżonkiem", "małżonką"),
    ("mężem", "żoną"),
    ("towarzyszem", "towarzyszką"),
    ("sąsiadem", "sąsiadką"),
    ("opiekunem", "opiekunką"),
    # 2. Relacje militarne, rycerskie i feudalne (16 par)
    ("wojownikiem", "wojowniczką"),
    ("rycerzem", "rycerką"),
    ("żołnierzem", "żołnierką"),
    ("dowódcą", "dowódczynią"),
    ("strażnikiem", "strażniczką"),
    ("zwiadowcą", "zwiadowczynią"),
    ("obrońcą", "obrończynią"),
    ("czempionem", "czempionką"),
    ("bohaterem", "bohaterką"),
    ("szpiegiem", "agentką"),
    ("wasalem", "wasalką"),
    ("władcą", "władczynią"),
    ("księciem", "księżniczką"),
    ("królem", "królową"),
    ("szlachcicem", "szlachcianką"),
    ("kapitanem", "panią kapitan"),
    # 3. Klasy fantasy, magia i religia (14 par)
    ("czarodziejem", "czarodziejką"),
    ("magiem", "maginią"),
    ("czarnoksiężnikiem", "czarownicą"),
    ("kapłanem", "kapłanką"),
    ("uzdrowicielem", "uzdrowicielką"),
    ("medykiem", "medyczką"),
    ("łowcą", "łowczynią"),
    ("zabójcą", "zabójczynią"),
    ("złodziejem", "złodziejką"),
    ("wędrowcem", "wędrowniczką"),
    ("przewodnikiem", "przewodniczką"),
    ("sługą", "służącą"),
    ("niewolnikiem", "niewolnicą"),
    ("więźniem", "więźniarką"),
    # 4. Relacje edukacyjne i hierarchiczne (10 par)
    ("mistrzem", "mistrzynią"),
    ("uczniem", "uczennicą"),
    ("nauczycielem", "nauczycielką"),
    ("lekarzem", "lekarką"),
    ("sojusznikiem", "sojuszniczką"),
    ("rywalem", "rywalką"),
    ("wrogiem", "nieprzyjaciółką"),
    ("zdrajcą", "zdrajczynią"),
    ("członkiem", "członkinią"),
    ("gościem", "gościnią"),
    # 5. Statusy i tożsamości (12 par)
    ("obcym", "obcą"),
    ("nieznajomym", "nieznajomą"),
    ("samotnikiem", "samotniczką"),
    ("żebrakiem", "żebraczką"),
    ("świadkiem", "świadkinią"),
    ("zbawcą", "wybawicielką"),
    ("zdobywcą", "zdobywczynią"),
    ("zwycięzcą", "zwyciężczynią"),
    ("przegranym", "przegraną"),
    ("szczęściarzem", "szczęściarą"),
    ("pechowcem", "pechową"),
    ("potworem", "potworem"),  # epicene protected
    # 6. Cechy ekspresywne i emocjonalne (18 par)
    ("kłamcą", "kłamczynią"),
    ("tchórzem", "tchórzawką"),
    ("głupcem", "głupią"),
    ("szaleńcem", "szaloną"),
    ("wsiarzem", "dziewką"),
    ("naiwniakiem", "naiwniaczką"),
    ("szkodnikiem", "szkodniczką"),
    ("okrutnikiem", "okrutnicą"),
    ("leniem", "leniuchą"),
    ("prostakiem", "prostaczką"),
    ("bękartem", "bękarcicą"),
    ("dzieckiem", "dzieckiem"),  # neuter protected
    ("włóczęgą", "włóczęgą"),  # epicene protected
]

PREDICATE_NOUNS_NOMINATIVE_PAIRS: List[Tuple[str, str]] = [
    # 1. Relacje rodzinne i bliskie
    ("przyjaciel", "przyjaciółka"),
    ("brat", "siostra"),
    ("syn", "córka"),
    ("ojciec", "matka"),
    ("kuzyn", "kuzynka"),
    ("partner", "partnerka"),
    ("narzeczony", "narzeczona"),
    ("małżonek", "małżonka"),
    ("mąż", "żona"),
    ("towarzysz", "towarzyszka"),
    ("sąsiad", "sąsiadka"),
    ("opiekun", "opiekunka"),
    # 2. Relacje militarne i feudalne
    ("wojownik", "wojowniczka"),
    ("rycerz", "rycerka"),
    ("żołnierz", "żołnierka"),
    ("dowódca", "dowódczyni"),
    ("strażnik", "strażniczka"),
    ("zwiadowca", "zwiadowczyni"),
    ("obrońca", "obrończyni"),
    ("czempion", "czempionka"),
    ("bohater", "bohaterka"),
    ("szpieg", "agentka"),
    ("wasal", "wasalka"),
    ("władca", "władczyni"),
    ("książę", "księżniczka"),
    ("król", "królowa"),
    ("szlachcic", "szlachcianka"),
    ("kapitan", "pani kapitan"),
    # 3. Klasy fantasy, magia i religia
    ("czarodziej", "czarodziejka"),
    ("mag", "magini"),
    ("czarnoksiężnik", "czarownica"),
    ("kapłan", "kapłanka"),
    ("uzdrowiciel", "uzdrowicielka"),
    ("medyk", "medyczka"),
    ("łowca", "łowczyni"),
    ("zabójca", "zabójczyni"),
    ("złodziej", "złodziejka"),
    ("wędrowiec", "wędrowniczka"),
    ("przewodnik", "przewodniczka"),
    ("sługa", "służąca"),
    ("niewolnik", "niewolnica"),
    ("więzień", "więźniarka"),
    # 4. Relacje edukacyjne i hierarchiczne
    ("mistrz", "mistrzyni"),
    ("uczeń", "uczennica"),
    ("nauczyciel", "nauczycielka"),
    ("lekarz", "lekarka"),
    ("sojusznik", "sojuszniczka"),
    ("rywal", "rywalka"),
    ("wróg", "nieprzyjaciółka"),
    ("zdrajca", "zdrajczyni"),
    ("członek", "członkini"),
    ("gość", "gościni"),
    # 5. Statusy i tożsamości
    ("obcy", "obca"),
    ("nieznajomy", "nieznajoma"),
    ("samotnik", "samotniczka"),
    ("żebrak", "żebraczka"),
    ("świadek", "świadkini"),
    ("zbawca", "wybawicielka"),
    ("zdobywca", "zdobywczyni"),
    ("zwycięzca", "zwyciężczyni"),
    ("przegrany", "przegrana"),
    ("szczęściarz", "szczęściara"),
    ("pechowiec", "pechowa"),
    ("potwór", "potwór"),
    # 6. Cechy ekspresywne
    ("kłamca", "kłamczyni"),
    ("tchórz", "tchórzawka"),
    ("głupiec", "głupia"),
    ("szaleniec", "szalona"),
    ("wsiarz", "dziewka"),
    ("naiwniak", "naiwniaczka"),
    ("szkodnik", "szkodniczka"),
    ("okrutnik", "okrutnica"),
    ("leń", "leniucha"),
    ("prostak", "prostaczka"),
    ("bękart", "bękarcica"),
    ("dziecko", "dziecko"),
    ("włóczęga", "włóczęga"),
]

PREDICATE_MODS_INSTRUMENTAL: List[Tuple[str, str]] = [
    ("dobrym", "dobrą"), ("złym", "złą"), ("prawdziwym", "prawdziwą"),
    ("najlepszym", "najlepszą"), ("moim", "moją"), ("naszym", "naszą"),
    ("twoim", "twoją"), ("jedynym", "jedyną"), ("wiernym", "wierną"),
    ("nowym", "nową"), ("lojalnym", "lojalną"), ("wspaniałym", "wspaniałą"),
    ("dzielnym", "dzielną"), ("potężnym", "potężną"), ("wielkim", "wielką"),
    ("bliskim", "bliską"), ("drogim", "drogą"), ("kochanym", "kochaną"),
    ("ostatnim", "ostatnią"), ("pierwszym", "pierwszą"),
]

PREDICATE_MODS_NOMINATIVE: List[Tuple[str, str]] = [
    ("dobry", "dobra"), ("zły", "zła"), ("prawdziwy", "prawdziwa"),
    ("najlepszy", "najlepsza"), ("mój", "moja"), ("nasz", "nasza"),
    ("twój", "twoja"), ("jedyny", "jedyna"), ("wierny", "wierna"),
    ("nowy", "nowa"), ("lojalny", "lojalna"), ("wspaniały", "wspaniała"),
    ("dzielny", "dzielna"), ("potężny", "potężna"), ("wielki", "wielka"),
    ("bliski", "bliska"), ("drogi", "droga"), ("kochany", "kochana"),
    ("ostatni", "ostatnia"), ("pierwszy", "pierwsza"),
]

PREDICATE_NOUNS_PLURAL_INSTRUMENTAL_PAIRS: List[Tuple[str, str]] = [
    # 40 par (męskoosobowy, niemęskoosobowy) w narzędniku l. mn.
    ("przyjaciółmi", "przyjaciółkami"),
    ("żołnierzami", "żołnierkami"),
    ("wojownikami", "wojowniczkami"),
    ("bohaterami", "bohaterkami"),
    ("magami", "maginiami"),
    ("obrońcami", "obrończyniami"),
    ("strażnikami", "strażniczkami"),
    ("towarzyszami", "towarzyszkami"),
    ("zabójcami", "zabójczyniami"),
    ("zdrajcami", "zdrajczyniami"),
    ("sługami", "służącymi"),
    ("uczniami", "uczennicami"),
    ("nauczycielami", "nauczycielkami"),
    ("władcami", "władczyniami"),
    ("królami", "królowymi"),
    ("książętami", "księżniczkami"),
    ("kapłanami", "kapłankami"),
    ("rycerzami", "rycerkami"),
    ("czarodziejami", "czarodziejkami"),
    ("doradcami", "doradczyniami"),
    ("opiekunami", "opiekunkami"),
    ("mistrzami", "mistrzyniami"),
    ("dowódcami", "dowódczyniami"),
    ("szpiegami", "szpieżkami"),
    ("niewolnikami", "niewolnicami"),
    ("jeńcami", "jenkiniami"),
    ("rebeliantami", "rebeliantkami"),
    ("sojusznikami", "sojuszniczkami"),
    ("wrogami", "wroginiami"),
    ("przeciwnikami", "przeciwniczkami"),
    ("przewodnikami", "przewodniczkami"),
    ("członkami", "członkiniami"),
    ("reprezentantami", "reprezentantkami"),
    ("świadkami", "świadkiniami"),
    ("posłańcami", "posłanniczkami"),
    ("wędrowcami", "wędrowniczkami"),
    ("zbawcami", "zbawczyniami"),
    ("następcami", "następczyniami"),
    ("pomocnikami", "pomocniczkami"),
    ("potworami", "potworami"),
    ("dziećmi", "dziećmi"),
]

PREDICATE_NOUNS_PLURAL_NOMINATIVE_PAIRS: List[Tuple[str, str]] = [
    # 40 par (męskoosobowy, niemęskoosobowy) w mianowniku l. mn.
    ("przyjaciele", "przyjaciółki"),
    ("żołnierze", "żołnierki"),
    ("wojownicy", "wojowniczki"),
    ("bohaterowie", "bohaterki"),
    ("magowie", "maginie"),
    ("obrońcy", "obrończynie"),
    ("strażnicy", "strażniczki"),
    ("towarzysze", "towarzyszki"),
    ("zabójcy", "zabójczynie"),
    ("zdrajcy", "zdrajczynie"),
    ("słudzy", "służące"),
    ("uczniowie", "uczennice"),
    ("nauczyciele", "nauczycielki"),
    ("władcy", "władczynie"),
    ("królowie", "królowe"),
    ("książęta", "księżniczki"),
    ("kapłani", "kapłanki"),
    ("rycerze", "rycerki"),
    ("czarodzieje", "czarodziejki"),
    ("doradcy", "doradczynie"),
    ("opiekunowie", "opiekunki"),
    ("mistrzowie", "mistrzynie"),
    ("dowódcy", "dowódczynie"),
    ("szpiedzy", "szpieżki"),
    ("niewolnicy", "niewolnice"),
    ("jeńcy", "jenkinie"),
    ("rebelianci", "rebeliantki"),
    ("sojusznicy", "sojuszniczki"),
    ("wrogowie", "wroginie"),
    ("przeciwnicy", "przeciwniczki"),
    ("przewodnicy", "przewodniczki"),
    ("członkowie", "członkinie"),
    ("reprezentanci", "reprezentantki"),
    ("świadkowie", "świadkinie"),
    ("posłańcy", "posłanniczki"),
    ("wędrowcy", "wędrowniczki"),
    ("zbawcy", "zbawczynie"),
    ("następcy", "następczynie"),
    ("pomocnicy", "pomocniczki"),
    ("potwory", "potwory"),
    ("dzieci", "dzieci"),
]

PREDICATE_MODS_PLURAL_NOMINATIVE: List[Tuple[str, str]] = [
    ("moi", "moje"), ("twoi", "twoje"), ("nasi", "nasze"), ("wasi", "wasze"),
    ("sami", "same"), ("jedyni", "jedyne"), ("wierni", "wierne"),
    ("dzielni", "dzielne"), ("wspaniali", "wspaniałe"), ("nowi", "nowe"),
    ("prawdziwi", "prawdziwe"), ("najlepsi", "najlepsze"), ("pierwsi", "pierwsze"),
    ("ostatni", "ostatnie"), ("dobrzy", "dobre"), ("źli", "złe"),
    ("bliscy", "bliskie"), ("drodzy", "drogie"), ("kochani", "kochane"),
    ("lojalni", "lojalne"),
]

PREDICATE_NOUNS_PAIRS = PREDICATE_NOUNS_INSTRUMENTAL_PAIRS
PREDICATE_MODS = PREDICATE_MODS_INSTRUMENTAL

INSTITUTIONAL_COLLECTIVE_NOUNS_PATTERN: str = (
    r"(?:klan(?:ie|u|em)?|rodzin(?:a|y|ie|ę|ą|o|om|ach)?|rodzic(?:e|ów|om|ami|ach)|"
    r"ród|rod(?:u|em|zie|a)?|oddział(?:u|em|a)?|oddziale|drużyn(?:a|y|ie|ę|ą|o|om|ach)?|"
    r"armi(?:a|i|ę|o|ą|om|ach)?|grup(?:a|y|ie|ę|ą|o|om|ach)?|dwójk(?:a|i|ę|ą|o)?|"
    r"trójk(?:a|i|ę|ą|o)?|lud(?:u|em|zie|a)?|naród|narod(?:u|em|zie|a)?|"
    r"wojsk(?:o|a|u|iem|ach)?|wieś|wsi|miast(?:o|a|u|em)?|mieście|miastach|"
    r"kraj(?:u|em|a|ach)?|świat(?:u|em|a)?|świecie|gatunk(?:u|iem|a|ach)?|plemi(?:ę|enia|eniem|eniu)|"
    r"rząd(?:u|em|zie)?|senat(?:u|em|cie)?|rad(?:a|y|zie|ę|ą|o|om|ach)|sąd(?:u|em|zie)?|"
    r"policj(?:a|i|ę|ą|o)|straż(?:y|ą|e|om|ach)?|gildi(?:a|i|ę|ą|o|om|ach)|"
    r"zakon(?:u|em|ie|y|ów|om|ami|ach)?|kościół|kościoł(?:a|u|em|e|ów|om|ami|ach)|"
    r"sekt(?:a|y|cie|ę|ą|o|om|ach)|parti(?:a|i|ę|ą|o|om|ach)|rebeli(?:a|i|ę|ą|o|antów|antom|antami|anci)|"
    r"imperium|królestw(?:o|a|u|em|ie|om|ach)|cesarstw(?:o|a|u|em|ie|om|ach)|państw(?:o|a|u|em|ie|om|ach)|"
    r"korporacj(?:a|i|ę|ą|o|om|ach)|firm(?:a|y|ie|ę|ą|o|om|ach)|uniwersytet(?:u|em|cie|y|ów)?|"
    r"akademi(?:a|i|ę|ą|o|om|ach)|szkoł(?:a|y|e|ę|ą|o|om|ach)|ministerstw(?:o|a|u|em|ie)|"
    r"magistrat(?:u|em|cie)?|garnizon(?:u|em|ie)?|"
    r"arystokracj(?:a|i|ę|ą|o|atów|atom|atami|aci)|szlacht(?:a|y|cie|ę|ą|o)|"
    r"mieszczaństw(?:o|a|u|em)|elit(?:a|y|cie|ę|ą|o|om|ach)|polityk(?:a|i|ów|om|ami|ach)|"
    r"wrog(?:owie|ów|om|ami|ach)|najeźdźc(?:y|ów|om|ami|ach)|potwor(?:y|ów|om|ami|ach)|"
    r"demon(?:y|ów|om|ami|ach)|obc(?:y|ych|ym|ymi))"
)

def convert_2nd_person_masculine_to_feminine(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in MASCULINE_2ND_SG_IRREGULAR_TO_FEMININE:
        res = MASCULINE_2ND_SG_IRREGULAR_TO_FEMININE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    # Class 1: -szedłeś -> -szłaś, -szedłbyś -> -szłabyś
    if v_lower.endswith("szedłeś"):
        prefix = v_lower[:-7]
        if prefix.endswith("od"): prefix = prefix[:-2] + "ode"
        elif prefix.endswith("w"): prefix = prefix[:-1] + "we"
        elif prefix.endswith("z"): prefix = prefix[:-1] + "ze"
        elif prefix.endswith("roz"): prefix = prefix[:-3] + "roze"
        elif prefix.endswith("nad"): prefix = prefix[:-3] + "nade"
        elif prefix.endswith("pod"): prefix = prefix[:-3] + "pode"
        elif prefix.endswith("ob"): prefix = prefix[:-2] + "obe"
        res = prefix + "szłaś"
    elif v_lower.endswith("szedłbyś"):
        prefix = v_lower[:-8]
        if prefix.endswith("od"): prefix = prefix[:-2] + "ode"
        elif prefix.endswith("w"): prefix = prefix[:-1] + "we"
        elif prefix.endswith("z"): prefix = prefix[:-1] + "ze"
        elif prefix.endswith("roz"): prefix = prefix[:-3] + "roze"
        elif prefix.endswith("nad"): prefix = prefix[:-3] + "nade"
        elif prefix.endswith("pod"): prefix = prefix[:-3] + "pode"
        elif prefix.endswith("ob"): prefix = prefix[:-2] + "obe"
        res = prefix + "szłabyś"
    # Class 2: -ogłeś -> -ogłaś, -ógłbyś -> -ogłabyś
    elif v_lower.endswith("ogłeś"):
        res = v_lower[:-5] + "ogłaś"
    elif v_lower.endswith("ógłbyś"):
        res = v_lower[:-6] + "ogłabyś"
    # Class 3: -ósłbyś -> -osłabyś, -iózłbyś -> -iozłabyś, -iódłbyś -> -iodłabyś, -ótłbyś -> -otłabyś
    elif v_lower.endswith("niósłbyś"):
        res = v_lower[:-8] + "niosłabyś"
    elif v_lower.endswith("wiózłbyś"):
        res = v_lower[:-8] + "wiozłabyś"
    elif v_lower.endswith("wiódłbyś"):
        res = v_lower[:-8] + "wiodłabyś"
    elif v_lower.endswith(("gniótłbyś", "gniotłbyś")):
        res = v_lower[:-9] + "gniotłabyś"
    elif v_lower.endswith(("miótłbyś", "miotłbyś")):
        res = v_lower[:-8] + "miotłabyś"
    elif v_lower.endswith(("plótłbyś", "plotłbyś")):
        res = v_lower[:-8] + "plotłabyś"
    elif v_lower.endswith(("rósłbyś", "rosłbyś")):
        res = v_lower[:-7] + "rosłabyś"
    elif v_lower.endswith("wiódłeś"):
        res = v_lower[:-7] + "wiodłaś"
    elif v_lower.endswith("wiozłeś"):
        res = v_lower[:-7] + "wiozłaś"
    elif v_lower.endswith("niosłeś"):
        res = v_lower[:-7] + "niosłaś"
    elif v_lower.endswith("plotłeś"):
        res = v_lower[:-7] + "plotłaś"
    elif v_lower.endswith("miotłeś"):
        res = v_lower[:-7] + "miotłaś"
    elif v_lower.endswith("gniotłeś"):
        res = v_lower[:-8] + "gniotłaś"
    elif v_lower.endswith("rosłeś"):
        res = v_lower[:-6] + "rosłaś"
    # Class 4: -arłeś -> -arłaś, -arłbyś -> -arłabyś
    elif v_lower.endswith("arłeś"):
        res = v_lower[:-5] + "arłaś"
    elif v_lower.endswith("arłbyś"):
        res = v_lower[:-6] + "arłabyś"
    # Class 5: -ekłeś -> -ekłaś, -egłeś -> -egłaś, -ekłbyś -> -ekłabyś, -egłbyś -> -egłabyś
    elif v_lower.endswith("ekłeś"):
        res = v_lower[:-5] + "ekłaś"
    elif v_lower.endswith("egłeś"):
        res = v_lower[:-5] + "egłaś"
    elif v_lower.endswith("ekłbyś"):
        res = v_lower[:-6] + "ekłabyś"
    elif v_lower.endswith("egłbyś"):
        res = v_lower[:-6] + "egłabyś"
    # Class 6: -adłeś -> -adłaś, -iadłeś -> -iadłaś, -asłeś -> -asłaś, -arzłeś -> -arzłaś, -okłeś -> -okłaś
    elif v_lower.endswith("iadłeś"):
        res = v_lower[:-6] + "iadłaś"
    elif v_lower.endswith("adłeś"):
        res = v_lower[:-5] + "adłaś"
    elif v_lower.endswith("asłeś"):
        res = v_lower[:-5] + "asłaś"
    elif v_lower.endswith("arzłeś"):
        res = v_lower[:-6] + "arzłaś"
    elif v_lower.endswith("okłeś"):
        res = v_lower[:-5] + "okłaś"
    elif v_lower.endswith("adłbyś"):
        res = v_lower[:-6] + "adłabyś"
    elif v_lower.endswith("asłbyś"):
        res = v_lower[:-6] + "asłabyś"
    # Class 7: -ąłeś -> -ęłaś, -ąłbyś -> -ęłabyś
    elif v_lower.endswith("ąłeś"):
        res = v_lower[:-4] + "ęłaś"
    elif v_lower.endswith("ąłbyś"):
        res = v_lower[:-5] + "ęłabyś"
    # Regular conditionals:
    elif v_lower.endswith("iałbyś"):
        res = v_lower[:-6] + "iałabyś"
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
    # Regular past:
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

    # Class 1: -szłaś -> -szedłeś, -szłabyś -> -szedłbyś
    if v_lower.endswith("szłaś"):
        prefix = v_lower[:-5]
        if prefix.endswith("ode"): prefix = prefix[:-3] + "od"
        elif prefix.endswith("we"): prefix = prefix[:-2] + "w"
        elif prefix.endswith("ze"): prefix = prefix[:-2] + "z"
        elif prefix.endswith("roze"): prefix = prefix[:-4] + "roz"
        elif prefix.endswith("nade"): prefix = prefix[:-4] + "nad"
        elif prefix.endswith("pode"): prefix = prefix[:-4] + "pod"
        elif prefix.endswith("obe"): prefix = prefix[:-3] + "ob"
        res = prefix + "szedłeś"
    elif v_lower.endswith("szłabyś"):
        prefix = v_lower[:-7]
        if prefix.endswith("ode"): prefix = prefix[:-3] + "od"
        elif prefix.endswith("we"): prefix = prefix[:-2] + "w"
        elif prefix.endswith("ze"): prefix = prefix[:-2] + "z"
        elif prefix.endswith("roze"): prefix = prefix[:-4] + "roz"
        elif prefix.endswith("nade"): prefix = prefix[:-4] + "nad"
        elif prefix.endswith("pode"): prefix = prefix[:-4] + "pod"
        elif prefix.endswith("obe"): prefix = prefix[:-3] + "ob"
        res = prefix + "szedłbyś"
    # Class 2: -ogłaś -> -ogłeś, -ogłabyś -> -ógłbyś
    elif v_lower.endswith("ogłaś"):
        res = v_lower[:-5] + "ogłeś"
    elif v_lower.endswith("ogłabyś"):
        res = v_lower[:-7] + "ógłbyś"
    # Class 3:
    elif v_lower.endswith("niosłabyś"):
        res = v_lower[:-9] + "niósłbyś"
    elif v_lower.endswith("wiozłabyś"):
        res = v_lower[:-9] + "wiózłbyś"
    elif v_lower.endswith("wiodłabyś"):
        res = v_lower[:-9] + "wiódłbyś"
    elif v_lower.endswith("gniotłabyś"):
        res = v_lower[:-10] + "gniótłbyś"
    elif v_lower.endswith("miotłabyś"):
        res = v_lower[:-9] + "miótłbyś"
    elif v_lower.endswith("plotłabyś"):
        res = v_lower[:-9] + "plótłbyś"
    elif v_lower.endswith("rosłabyś"):
        res = v_lower[:-8] + "rósłbyś"
    elif v_lower.endswith("wiodłaś"):
        res = v_lower[:-7] + "wiódłeś"
    elif v_lower.endswith("wiozłaś"):
        res = v_lower[:-7] + "wiozłeś"
    elif v_lower.endswith("niosłaś"):
        res = v_lower[:-7] + "niosłeś"
    elif v_lower.endswith("plotłaś"):
        res = v_lower[:-7] + "plotłeś"
    elif v_lower.endswith("miotłaś"):
        res = v_lower[:-7] + "miotłeś"
    elif v_lower.endswith("gniotłaś"):
        res = v_lower[:-8] + "gniotłeś"
    elif v_lower.endswith("rosłaś"):
        res = v_lower[:-6] + "rosłeś"
    # Class 4: -arłaś -> -arłeś, -arłabyś -> -arłbyś
    elif v_lower.endswith("arłaś"):
        res = v_lower[:-5] + "arłeś"
    elif v_lower.endswith("arłabyś"):
        res = v_lower[:-7] + "arłbyś"
    # Class 5: -ekłaś -> -ekłeś, -egłaś -> -egłeś, -ekłabyś -> -ekłbyś, -egłabyś -> -egłbyś
    elif v_lower.endswith("ekłaś"):
        res = v_lower[:-5] + "ekłeś"
    elif v_lower.endswith("egłaś"):
        res = v_lower[:-5] + "egłeś"
    elif v_lower.endswith("ekłabyś"):
        res = v_lower[:-7] + "ekłbyś"
    elif v_lower.endswith("egłabyś"):
        res = v_lower[:-7] + "egłbyś"
    # Class 6: -adłaś -> -adłeś, -iadłaś -> -iadłeś, -asłaś -> -asłeś, -arzłaś -> -arzłeś, -okłaś -> -okłeś
    elif v_lower.endswith("iadłaś"):
        res = v_lower[:-6] + "iadłeś"
    elif v_lower.endswith("adłaś"):
        res = v_lower[:-5] + "adłeś"
    elif v_lower.endswith("asłaś"):
        res = v_lower[:-5] + "asłeś"
    elif v_lower.endswith("arzłaś"):
        res = v_lower[:-6] + "arzłeś"
    elif v_lower.endswith("okłaś"):
        res = v_lower[:-5] + "okłeś"
    elif v_lower.endswith("adłabyś"):
        res = v_lower[:-7] + "adłbyś"
    elif v_lower.endswith("asłabyś"):
        res = v_lower[:-7] + "asłbyś"
    # Class 7: -ęłaś -> -ąłeś, -ęłabyś -> -ąłbyś
    elif v_lower.endswith("ęłaś"):
        res = v_lower[:-4] + "ąłeś"
    elif v_lower.endswith("ęłabyś"):
        res = v_lower[:-6] + "ąłbyś"
    # Regular conditionals:
    elif v_lower.endswith("iałabyś"):
        res = v_lower[:-7] + "iałbyś"
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
    # Regular past:
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

def preserve_declension_casing(matched_text: str, target_form: str) -> str:
    """
    Preserves proper title/multi-word casing when replacing inflected forms.
    Avoids Python's .capitalize() defect which lower-cases subsequent words (e.g. 'Księgi Toaha' -> 'Księgi toaha').
    """
    if not target_form:
        return target_form
    if matched_text.isupper():
        return target_form.upper()
    if matched_text.islower():
        return target_form.lower()
    if matched_text[0].isupper() and target_form[0].islower():
        return target_form[0].upper() + target_form[1:]
    return target_form

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
        whisper_transcriptions: Optional[Dict[int, str]] = None,
        prosody_tags: Optional[Dict[int, str]] = None,
        enforce_line_split: bool = False,
        report_cps_fixes: bool = False
    ) -> Tuple[Any, List[str]]:
        if not subs or not hasattr(subs, "events") or not subs.events:
            return subs, []

        fixes: List[str] = []
        events = subs.events
        orig_speakers: Dict[int, str] = {
            idx_ev: (getattr(ev_item, "name", "") or getattr(ev_item, "actor", "") or getattr(ev_item, "speaker", "") or (line_speakers.get(idx_ev) if line_speakers else "") or "")
            for idx_ev, ev_item in enumerate(events)
        }

        # Step 0a: Temporal Subtitle Collision & Screen Elevation (Filar LVII & Netflix AVT Standard)
        # When two dialogue events overlap in time by > 400ms without explicit vertical positioning,
        # elevate the secondary event to the top of the screen {\an8} to prevent pixel stacking and visual unreadability.
        non_sign_dialogues = []
        for idx_ev, ev_item in enumerate(events):
            ev_style_l = (ev_item.style or "").lower()
            ev_is_sub = bool(re.search(r"\bsubtitles?\b", ev_style_l))
            ev_is_sign = bool(
                re.search(r"\\(pos|move|an[789]|clip)\b", ev_item.text or "") or
                (not ev_is_sub and (
                    bool(re.search(r"\b(sign|signs|title|titles|caption|captions|typeset|typesetting|op|ed)\b", ev_style_l))
                    or ev_style_l.startswith("caption")
                ))
            )
            if not ev_is_sign and ev_item.text and ev_item.text.strip():
                non_sign_dialogues.append((idx_ev, ev_item))

        for d_i in range(len(non_sign_dialogues) - 1):
            idx_a, ev_a = non_sign_dialogues[d_i]
            idx_b, ev_b = non_sign_dialogues[d_i + 1]
            overlap_ms = ev_a.end - ev_b.start
            if overlap_ms > 400 and ev_b.end > ev_a.start:
                has_pos_a = bool(re.search(r"\\(pos|move|an[1-9])\b", ev_a.text))
                has_pos_b = bool(re.search(r"\\(pos|move|an[1-9])\b", ev_b.text))
                if not has_pos_a and not has_pos_b:
                    target_ev = ev_b if len(ev_b.text) <= len(ev_a.text) else ev_a
                    target_idx = idx_b if len(ev_b.text) <= len(ev_a.text) else idx_a
                    target_ev.text = r"{\an8}" + target_ev.text
                    fixes.append(f"[Episode Quality Gate - Filar LVII Kolizja Czasowa] Linia #{target_idx+1}: podniesiono nakładającą się kwestię dialogową na górę kadru (\\an8)")

        # Step 0: Episode-Wide Character Gender Knowledge Base (Filar CLXII)
        from series_memory import CANONICAL_MALE_NAMES
        CANONICAL_MALE_NAMES_ON_A = {
            "shira", "akira", "gaara", "ashitaka", "kiba", "soma", "kenta",
            "ryoma", "hanza", "koba", "soya", "toma", "genga", "sinbad", "judar", "alibaba"
        }
        char_gender_map: Dict[str, str] = {}  # char_name_lower -> "MALE" or "FEMALE"

        # 0. Inherent Lexical Gender Pre-pass from Event Names (Filar CLXIX)
        for i_ev, ev in enumerate(events):
            ev_spk = getattr(ev, "name", None) or getattr(ev, "actor", None) or getattr(ev, "speaker", None)
            if (not ev_spk or not str(ev_spk).strip()) and line_speakers and i_ev in line_speakers:
                cand_lspk = line_speakers[i_ev]
                if cand_lspk and not is_generic_actor_or_category(str(cand_lspk)):
                    ev_spk = cand_lspk
            if not ev_spk:
                continue
            clean_spk = extract_clean_speaker_name(ev_spk).lower()
            spk_norm = str(ev_spk).strip().lower()
            tokens = set(re.findall(r"\b[a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+\b", clean_spk))
            if is_plural_actor(clean_spk) or is_plural_actor(spk_norm):
                char_gender_map[clean_spk] = "PLURAL"
                char_gender_map[spk_norm] = "PLURAL"
            elif clean_spk in INHERENT_FEMALE_NOUNS or any(t in INHERENT_FEMALE_NOUNS for t in tokens):
                char_gender_map[clean_spk] = "FEMALE"
                char_gender_map[spk_norm] = "FEMALE"
            elif clean_spk in INHERENT_MALE_NOUNS or any(t in INHERENT_MALE_NOUNS for t in tokens) or clean_spk in CANONICAL_MALE_NAMES or any(t in CANONICAL_MALE_NAMES for t in tokens):
                char_gender_map[clean_spk] = "MALE"
                char_gender_map[spk_norm] = "MALE"

        # 0a. From Character Registry
        if character_registry:
            for cname, cdesc in character_registry.items():
                gen = None
                if isinstance(cdesc, dict):
                    c_g = str(cdesc.get("gender", "")).upper()
                    if c_g in ("MALE", "FEMALE"):
                        gen = c_g
                    else:
                        cd_desc = str(cdesc.get("description", "") or cdesc.get("role", "")).lower()
                        cd_sanitized = re.sub(r"zakaz\s+form\s+(?:żeńsk|męsk)[a-ząćęłńóśźż]*", "", cd_desc)
                        if any(k in cd_sanitized for k in FEMALE_ROLE_KEYWORDS):
                            gen = "FEMALE"
                        elif any(k in cd_sanitized for k in MALE_ROLE_KEYWORDS):
                            gen = "MALE"
                else:
                    cd_lower = str(cdesc).lower()
                    cd_sanitized = re.sub(r"zakaz\s+form\s+(?:żeńsk|męsk)[a-ząćęłńóśźż]*", "", cd_lower)
                    if any(k in cd_sanitized for k in FEMALE_ROLE_KEYWORDS):
                        gen = "FEMALE"
                    elif any(k in cd_sanitized for k in MALE_ROLE_KEYWORDS):
                        gen = "MALE"
                if gen:
                    clean_c = extract_clean_speaker_name(cname).lower()
                    if clean_c:
                        char_gender_map[clean_c] = gen
                    for p in re.split(r"[/,]", cname):
                        clean_p = extract_clean_speaker_name(p).strip()
                        if len(clean_p) >= 3:
                            char_gender_map[clean_p.lower()] = gen
                    for n in re.findall(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}\b", cname):
                        nl = n.lower()
                        if not is_generic_actor_or_category(nl) and nl not in char_gender_map:
                            char_gender_map[nl] = gen

        # 0b. From Series Bible
        if series_bible and hasattr(series_bible, "data"):
            bible_chars = series_bible.data.get("characters", {})
            # Pass 1: exact character names
            for c_key, c_val in bible_chars.items():
                if "->" in c_key or "/" in c_key or "," in c_key:
                    continue  # Relationships handled separately, avoid poisoning listener gender
                gen = series_bible.get_character_gender(c_key, allow_generic_nouns=False) if hasattr(series_bible, "get_character_gender") else None
                if gen not in ("MALE", "FEMALE"):
                    desc_str = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
                    desc_lower = desc_str.lower()
                    desc_sanitized = re.sub(r"zakaz\s+form\s+(?:żeńsk|męsk)[a-ząćęłńóśźż]*", "", desc_lower)
                    from series_memory import RE_FEMALE_ROLE, RE_MALE_ROLE
                    if RE_FEMALE_ROLE.search(desc_sanitized):
                        gen = "FEMALE"
                    elif RE_MALE_ROLE.search(desc_sanitized):
                        gen = "MALE"
                if gen in ("MALE", "FEMALE"):
                    clean_ckey = extract_clean_speaker_name(c_key).strip().lower()
                    if clean_ckey and len(clean_ckey) >= 3:
                        char_gender_map[clean_ckey] = gen

            # Pass 2: token decomposition with conflict tracking
            token_gender_candidates: Dict[str, Set[str]] = {}
            for c_key, c_val in bible_chars.items():
                if "->" in c_key or "/" in c_key or "," in c_key:
                    continue
                gen = series_bible.get_character_gender(c_key, allow_generic_nouns=False) if hasattr(series_bible, "get_character_gender") else None
                if gen not in ("MALE", "FEMALE"):
                    desc_str = c_val.get("description", "") if isinstance(c_val, dict) else str(c_val)
                    desc_lower = desc_str.lower()
                    desc_sanitized = re.sub(r"zakaz\s+form\s+(?:żeńsk|męsk)[a-ząćęłńóśźż]*", "", desc_lower)
                    from series_memory import RE_FEMALE_ROLE, RE_MALE_ROLE
                    if RE_FEMALE_ROLE.search(desc_sanitized):
                        gen = "FEMALE"
                    elif RE_MALE_ROLE.search(desc_sanitized):
                        gen = "MALE"
                if gen in ("MALE", "FEMALE"):
                    for n in re.findall(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}\b", c_key):
                        nl = n.lower()
                        if nl not in token_gender_candidates:
                            token_gender_candidates[nl] = set()
                        token_gender_candidates[nl].add(gen)

            for token, gens in token_gender_candidates.items():
                if token not in char_gender_map:
                    if len(gens) == 1:
                        char_gender_map[token] = next(iter(gens))
                    elif series_bible and hasattr(series_bible, "get_character_gender"):
                        # Disambiguate colliding surname via series_bible's relational precedence
                        res_g = series_bible.get_character_gender(token, allow_generic_nouns=False)
                        if res_g in ("MALE", "FEMALE"):
                            char_gender_map[token] = res_g

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
            if is_generic_actor_or_category(str(ev.name)) or is_plural_actor(str(ev.name)):
                continue
            spk_norm = ev.name.strip().lower()
            spk_clean = extract_clean_speaker_name(ev.name).lower()
            if not spk_clean or len(spk_clean) < 3 or is_generic_actor_or_category(spk_clean) or is_plural_actor(spk_clean):
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

        # 0e. Pre-pass for Foreign Name Declension & Vocative Uniformity (Case-Segregated)
        prep_case_counts: Dict[str, Dict[str, Dict[str, int]]] = {
            "gen": {}, "dat": {}, "acc": {}, "ins": {}, "loc": {}
        }
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

        if series_bible and hasattr(series_bible, "data") and "characters" in series_bible.data:
            for k in series_bible.data["characters"].keys():
                if k and len(k) >= 3 and not any(ch in k for ch in "->/"):
                    clean_k = extract_clean_speaker_name(k).strip()
                    if clean_k and not any(clean_k.lower() == existing_k.lower() for existing_k in character_declensions.keys()):
                        g = char_gender_map.get(clean_k.lower(), "UNKNOWN")
                        character_declensions[clean_k] = generate_polish_name_declension(clean_k, g)

        if character_registry:
            for k in character_registry.keys():
                for p in re.split(r"[/,]", k):
                    clean_p = p.strip()
                    if len(clean_p) >= 3 and not any(clean_p.lower() == existing_k.lower() for existing_k in character_declensions.keys()):
                        g = char_gender_map.get(clean_p.lower(), "UNKNOWN")
                        character_declensions[clean_p] = generate_polish_name_declension(clean_p, g)

        # Also populate character_declensions from custom_glossary and manga canon entries
        glossary_to_scan = {}
        if custom_glossary:
            glossary_to_scan.update(custom_glossary)
        if series_bible and hasattr(series_bible, "data") and "glossary" in series_bible.data:
            glossary_to_scan.update(series_bible.data["glossary"])
        for g_k, g_v in glossary_to_scan.items():
            cand_terms = [g_v] if isinstance(g_v, str) else []
            for raw_term in cand_terms:
                term_clean = re.sub(r"\s*[\(\[].*?[\)\]]", "", raw_term).strip()
                if "/" in term_clean:
                    term_clean = term_clean.split("/")[0].strip()
                if len(term_clean) >= 3 and term_clean[0].isupper() and not any(ch in term_clean for ch in "->/"):
                    if not any(term_clean.lower() == existing_k.lower() for existing_k in character_declensions.keys()):
                        g = char_gender_map.get(term_clean.lower(), "UNKNOWN")
                        character_declensions[term_clean] = generate_polish_name_declension(term_clean, g)

        # Also populate from candidate names / event actors if not present
        NON_NAME_ACTORS = {
            "wszyscy", "ktos", "ktoś", "glos", "głos", "narrator", "napis", "napisy",
            "tytul", "tytuł", "tlumaczenie", "tłumaczenie", "kobieta", "mezczyzna",
            "mężczyzna", "chlopak", "chłopak", "dziewczyna", "tlum", "tłum", "strażnik",
            "straznik", "zolnierz", "żołnierz", "main", "default", "alt", "sign", "signs",
            "ziemia", "ziemią", "ziemi", "ziemię", "ziemiom", "ziemiach", "słońce", "słońca", "słońcu", "słońcem",
            "księżyc", "księżyca", "księżycu", "księżycem", "świat", "świata", "światu", "światem", "świecie",
            "niebo", "nieba", "niebios", "niebiosach", "bóg", "boga", "bogu", "bogiem", "bogowie", "bogów",
            "japonia", "japonii", "tokio", "bordeaux", "polska", "polski", "polsce", "polskę", "polską", "europa", "europy",
            "motomachi", "mihara", "ohshima", "ōshima", "shiman", "wyspa", "wyspy", "wyspie", "wyspą", "morze", "morza", "morzem",
            "hiden", "haiden", "elbe", "erbe", "solsein", "solcein", "boelate", "boirate", "eslinn", "esrin", "toah", "elds", "shinano", "suwa", "kamakura", "kioto",
            "esleburg", "esreburg", "hyderat", "haiderat", "heiderat", "elden", "luna", "dunn", "złudzeń", "złudzenia", "złudzenie", "płomiennego", "żaru", "początku", "kuźni", "świątynia",
            "imperium", "cesarstwo", "królestwo", "księstwo", "państwo", "republika", "federacja", "unia", "senat", "rada", "armia", "zakon", "klan", "ród", "dynastia", "plemię", "sojusz", "muzeum", "liceum", "technikum", "akwarium", "koloseum", "seminarium"
        }
        if series_bible and hasattr(series_bible, "data") and "glossary" in series_bible.data:
            for g_k, g_v in series_bible.data["glossary"].items():
                g_str = (str(g_k) + " " + str(g_v)).lower()
                if any(kw in g_str for kw in ["kraina", "królestwo", "lokacja", "kopalnia", "akademia", "chram", "świątynia", "szkoła", "miasto", "rzeka", "góra", "zamek", "twierdza", "imperium", "państwo", "toponim", "stolica"]):
                    for w in re.findall(r"\b[a-ząćęłńóśźż]{3,}\b", g_str):
                        NON_NAME_ACTORS.add(w)

        # Collect foreign/English source tokens from glossary to protect them from phantom character harvesting
        glossary_source_tokens: Set[str] = set()
        for g_dict in [custom_glossary, (series_bible.data.get("glossary") if series_bible and hasattr(series_bible, "data") else None)]:
            if g_dict and isinstance(g_dict, dict):
                for k, v in g_dict.items():
                    if isinstance(k, str) and isinstance(v, str) and k.strip().lower() != v.strip().lower():
                        for tok in re.findall(r"\b[A-Za-ząćęłńóśźż]{2,}\b", k):
                            glossary_source_tokens.add(tok.lower())

        all_candidate_chars = set()
        for k in candidate_names:
            if k.strip().lower() not in glossary_source_tokens:
                all_candidate_chars.add(k.strip())
        if custom_glossary:
            for k, v in custom_glossary.items():
                for name_src in [v]:
                    for token in re.findall(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}\b", name_src):
                        tok_l = token.lower()
                        if tok_l not in NON_NAME_ACTORS and tok_l not in glossary_source_tokens and tok_l not in ETHNONYMS_AND_COLLECTIVES and not tok_l.endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "em", "iem", "owi", "eń", "ań", "ów", "ich", "ych", "ość", "ości")) and not tok_l.endswith("um"):
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
                if len(act_clean) >= 3 and not any(ch in act_clean for ch in "{}[]():;") and act_clean.lower() not in glossary_source_tokens:
                    all_candidate_chars.add(act_clean)
            clean_ev = re.sub(r"\{[^\}]*\}", "", ev.text or "")
            for m_prop in re.finditer(r"\b(o|do|dla|u|z|ze|od|przed|nad|pod|przy|przez|za|i|oraz)\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})\b", clean_ev):
                prep_word = m_prop.group(1).lower()
                prop_tok = m_prop.group(2)
                tok_lower = prop_tok.lower()
                if tok_lower in ETHNONYMS_AND_COLLECTIVES or tok_lower in glossary_source_tokens or (series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(prop_tok)):
                    continue
                from series_memory import is_proper_noun_homonym
                if is_proper_noun_homonym(tok_lower):
                    continue
                if tok_lower in NON_NAME_ACTORS or tok_lower in {
                    "pan", "pani", "niego", "mnie", "ciebie", "nas", "was", "nich", "tego", "tamto", "jeden", "sama", "samo", "sami", "same", "wszystko", "wszyscy", "wszystkich", "cały", "cała", "całe"
                }:
                    continue
                # Odrzuć formy już odmienione przypadków zależnych oraz znane formy zależne istniejących postaci
                if tok_lower in existing_decl_forms:
                    continue
                if any(tok_lower.startswith(k.lower()) and len(tok_lower) > len(k) for k in character_declensions.keys()):
                    continue
                if any(tok_lower in k.lower().split() for k in character_declensions.keys()):
                    continue

                # Rekonstrukcja formy mianownikowej z form zależnych po przyimkach
                cand_nom = prop_tok
                cand_gender = char_gender_map.get(tok_lower, "UNKNOWN")

                if prep_word in {"do", "dla", "od", "u", "bez", "przez", "za"}:
                    # Po przyimkach rządzących dopełniaczem lub biernikiem męskie imiona spółgłoskowe przyjmują końcówkę -a (np. do Brandona, dla Klena, od Leona).
                    # Uznanie tej formy za mianownik (Brandona, Klena) powoduje błędne wygenerowanie żeńskiej odmiany na -y (do Brandony, do Kleny).
                    from series_memory import is_inherently_female_name, POLISH_FEMALE_NAMES, UNIVERSAL_FEMALE_NAMES_ON_A
                    is_known_female = (
                        cand_gender == "FEMALE" or
                        is_inherently_female_name(prop_tok) or
                        tok_lower in POLISH_FEMALE_NAMES or
                        tok_lower in UNIVERSAL_FEMALE_NAMES_ON_A or
                        (series_bible and hasattr(series_bible, "get_character_gender") and series_bible.get_character_gender(prop_tok, allow_generic_nouns=False) == "FEMALE")
                    )
                    if is_known_female:
                        cand_nom = prop_tok
                        cand_gender = "FEMALE"
                    elif tok_lower.endswith("a") and tok_lower not in CANONICAL_MALE_NAMES_ON_A:
                        cand_nom = prop_tok[:-1]
                        cand_gender = "MALE"
                elif prep_word in {"z", "ze", "przed", "nad", "pod"}:
                    # Po przyimkach narzędnika męskie imiona przyjmują końcówkę -em/-iem (np. z Brandonem, z Klenem)
                    if tok_lower.endswith("iem") and len(tok_lower) > 4 and cand_gender != "FEMALE":
                        cand_nom = prop_tok[:-3]
                        cand_gender = "MALE"
                    elif tok_lower.endswith("em") and len(tok_lower) > 4 and cand_gender != "FEMALE":
                        cand_nom = prop_tok[:-2]
                        cand_gender = "MALE"
                elif prep_word in {"o", "przy"}:
                    # Po przyimkach miejscownika męskie imiona przyjmują końcówkę -ie (np. o Brandonie, o Klenie)
                    if tok_lower.endswith("ie") and len(tok_lower) > 3 and cand_gender != "FEMALE":
                        cand_nom = prop_tok[:-2]
                        cand_gender = "MALE"

                cand_nom_lower = cand_nom.lower()
                if cand_nom_lower in NON_NAME_ACTORS or cand_nom_lower in glossary_source_tokens or cand_nom_lower in ETHNONYMS_AND_COLLECTIVES:
                    continue
                if series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(cand_nom):
                    continue

                if not cand_nom_lower.endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "em", "iem", "owi", "eń", "ań", "ów", "ich", "ych", "ość", "ości")) and not cand_nom_lower.endswith("um"):
                    all_candidate_chars.add(cand_nom)
                    candidate_names.add(cand_nom_lower)
                    if cand_gender != "UNKNOWN" and cand_nom_lower not in char_gender_map:
                        char_gender_map[cand_nom_lower] = cand_gender

        for cand in all_candidate_chars:
            if not cand or len(cand) < 3 or cand.lower() in NON_NAME_ACTORS or cand.lower() in glossary_source_tokens or cand.lower() in ETHNONYMS_AND_COLLECTIVES:
                continue
            if series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(cand):
                continue
            if cand.lower().endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "em", "iem", "owi", "eń", "ań", "ów", "ich", "ych", "ość", "ości")) or cand.lower().endswith("um"):
                continue
            if cand.lower() in existing_decl_forms:
                continue
            if any(cand.lower().startswith(k.lower()) and len(cand) > len(k) for k in character_declensions.keys()):
                continue
            if any(cand.lower() in k.lower().split() for k in character_declensions.keys()):
                continue
            cand_proper = cand.capitalize()
            if not any(cand.lower() == existing_k.lower() for existing_k in character_declensions.keys()):
                cand_g = char_gender_map.get(cand.lower(), "UNKNOWN")
                character_declensions[cand_proper] = generate_polish_name_declension(cand_proper, cand_g)

        for ev in events:
            if not ev.text:
                continue
            clean_t = re.sub(r"\{[^\}]*\}", "", ev.text)

            # Preposition + Capitalized Word (Case-Segregated Preposition Governance)
            GEN_PREPS = {"do", "dla", "od", "u", "bez", "koło", "obok", "wzdłuż", "podczas", "zamiast", "oprócz", "wokół", "wobec"}
            DAT_PREPS = {"ku", "przeciw", "przeciwko", "dzięki", "wbrew"}
            ACC_PREPS = {"przez"}
            INS_PREPS = {"przed", "nad", "pod", "między"}
            LOC_PREPS = {"przy"}

            for m in re.finditer(r"\b(z|ze|do|dla|o|u|od|przed|nad|pod|przy|przez|za)\s+([^\s,\.!\?…]+)", clean_t):
                prep_raw = m.group(1).lower()
                n_form = m.group(2)
                case_bucket = None
                if prep_raw in GEN_PREPS:
                    case_bucket = "gen"
                elif prep_raw in DAT_PREPS:
                    case_bucket = "dat"
                elif prep_raw in ACC_PREPS:
                    case_bucket = "acc"
                elif prep_raw in INS_PREPS:
                    case_bucket = "ins"
                elif prep_raw in LOC_PREPS:
                    case_bucket = "loc"
                elif prep_raw in {"z", "ze"}:
                    if series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(n_form):
                        case_bucket = "gen"
                    else:
                        case_bucket = "ins"
                elif prep_raw == "za":
                    before_t = clean_t[:m.start()]
                    if re.search(r"\b(?:walczyć|walczy|walczył|bić|bije|oddać|odda|oddał|zginąć|zginie|umrzeć|umrze|polec|modlić|modli|wstawić|wstawi|ręczyć|ręczy|stać\s+murem|wyjść|wyjdzie|wydać|zapłacić|płacić|kara|odpowiadać|uznać|uznaje|uważać|uważa|uchodzić|uchodzi|wziąć|brać|weźmie|chwycić|chwyci|złapać|złapie|trzymać|dziękować|przepraszać)\s+(?:zaś\s+|zaraz\s+|chyba\s+|tam\s+)?$", before_t, re.IGNORECASE):
                        case_bucket = "acc"
                    else:
                        case_bucket = "ins"
                elif prep_raw == "o":
                    before_t = clean_t[:m.start()]
                    if re.search(r"\b(?:walczyć|bić|uderzyć|rozbić|prosić|błagać|grać|gra)\s+(?:zaś\s+|zaraz\s+|chyba\s+|tam\s+)?$", before_t, re.IGNORECASE):
                        case_bucket = "acc"
                    else:
                        case_bucket = "loc"

                if case_bucket:
                    for c_name in candidate_names:
                        stem_len = max(3, len(c_name) - 2)
                        stem = c_name[:stem_len]
                        if n_form.lower().startswith(stem):
                            if c_name not in prep_case_counts[case_bucket]:
                                prep_case_counts[case_bucket][c_name] = {}
                            prep_case_counts[case_bucket][c_name][n_form] = prep_case_counts[case_bucket][c_name].get(n_form, 0) + 1
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

        dominant_prep_case_names: Dict[str, Dict[str, str]] = {"gen": {}, "dat": {}, "acc": {}, "ins": {}, "loc": {}}
        for case_k, names_dict in prep_case_counts.items():
            for c_name, forms in names_dict.items():
                total = sum(forms.values())
                if total >= 2:
                    dom_form, dom_count = max(forms.items(), key=lambda x: x[1])
                    if dom_count / total >= 0.75:
                        dominant_prep_case_names[case_k][c_name] = dom_form

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
                m_words = m_form.split()
                c_stem = c_name[:stem_len]

                rule = {
                    "name": c_name,
                    "m_form": m_form,
                    "c_stem": c_stem,
                    "m_lower": m_form.lower(),
                    "stem_lower": c_stem.lower(),
                    "words_lower": [w.lower() for w in m_words]
                }

                n_form = c_decl.get("N")
                if n_form and n_form != m_form:
                    rule["n_form"] = n_form
                    n_words = n_form.split()
                    if len(m_words) == 2 and len(n_words) == 2:
                        w1_n_pat = rf"(?:{re.escape(m_words[0])}|{re.escape(n_words[0])})"
                        w2_n_pat = rf"(?:{re.escape(m_words[1])}|{re.escape(n_words[1])})"
                        n_pat = rf"(?:{re.escape(m_form)}|{w1_n_pat}(?:\s+|\\(?:[Nnh])+)+{w2_n_pat})"
                    else:
                        n_pat = re.escape(m_form)
                    rule["re_n"] = re.compile(rf"\b(z|ze|przed|nad|pod|za|między)(\s+|\\(?:[Nnh])+)+({n_pat})\b", re.IGNORECASE)

                d_form = c_decl.get("D")
                if d_form and d_form != m_form:
                    rule["d_form"] = d_form
                    d_words = d_form.split()
                    if len(m_words) == 2 and len(d_words) == 2:
                        w1_d_pat = rf"(?:{re.escape(m_words[0])}|{re.escape(d_words[0])})"
                        w2_d_pat = rf"(?:{re.escape(m_words[1])}|{re.escape(d_words[1])})"
                        d_pat = rf"(?:{re.escape(m_form)}|{w1_d_pat}(?:\s+|\\(?:[Nnh])+)+{w2_d_pat})"
                    else:
                        d_pat = rf"{re.escape(m_form)}|{re.escape(c_stem)}[a-ząćęłńóśźż]*"
                    rule["re_prep_d"] = re.compile(rf"\b(do|dla|od|u|bez|koło|obok|wzdłuż|podczas|zamiast|oprócz|wokół|wobec)(\s+|\\(?:[Nnh])+)+({d_pat})\b", re.IGNORECASE)
                    rule["re_pos_d"] = re.compile(rf"\b({POSSESSIVE_GOVERNING_NOUNS_PATTERN}|{GENITIVE_GOVERNING_VERBS_PATTERN})((?:(?:\s+|\\(?:[Nnh])+)+(?:samego|tamtego|tego))?(?:\s+|\\(?:[Nnh])+)+)({re.escape(m_form)})\b", re.IGNORECASE)

                c_form = c_decl.get("C")
                if c_form and c_form != m_form:
                    rule["c_form"] = c_form
                    c_words = c_form.split()
                    if len(m_words) == 2 and len(c_words) == 2:
                        w1_c_pat = rf"(?:{re.escape(m_words[0])}|{re.escape(c_words[0])})"
                        w2_c_pat = rf"(?:{re.escape(m_words[1])}|{re.escape(c_words[1])})"
                        c_pat = rf"(?:{re.escape(m_form)}|{w1_c_pat}(?:\s+|\\(?:[Nnh])+)+{w2_c_pat})"
                    else:
                        c_pat = re.escape(m_form)
                    rule["re_c"] = re.compile(rf"\b(ku|przeciw|przeciwko|dzięki|wbrew)(\s+|\\(?:[Nnh])+)+({c_pat})\b", re.IGNORECASE)

                ms_form = c_decl.get("Ms")
                if ms_form and ms_form != m_form:
                    rule["ms_form"] = ms_form
                    ms_words = ms_form.split()
                    if len(m_words) == 2 and len(ms_words) == 2:
                        w1_ms_pat = rf"(?:{re.escape(m_words[0])}|{re.escape(ms_words[0])})"
                        w2_ms_pat = rf"(?:{re.escape(m_words[1])}|{re.escape(ms_words[1])})"
                        ms_pat = rf"(?:{re.escape(m_form)}|{w1_ms_pat}(?:\s+|\\(?:[Nnh])+)+{w2_ms_pat})"
                    else:
                        ms_pat = re.escape(m_form)
                    rule["re_ms"] = re.compile(rf"\b(o|przy)(\s+|\\(?:[Nnh])+)+({ms_pat})\b", re.IGNORECASE)

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
                            # Check if male addressee was derived from an audited contaminated tag (e.g. 'Actor (Mężczyzna)')
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
                elif r"\N" in clean_body:
                    parts = re.split(r"\\N", clean_body)
                    if len(parts) == 2:
                        p0 = parts[0].strip()
                        p1 = parts[1].strip()
                        has_dash0 = bool(re.match(r"^[-–—]\s+", p0))
                        has_dash1 = bool(re.match(r"^[-–—]\s+", p1))
                        if has_dash0 and not has_dash1:
                            if re.search(r"[.!?…]$", p0) and re.match(r"^[A-ZĄĆĘŁŃÓŚŹŻ0-9„\"'\(]", p1):
                                clean_p0 = re.sub(r"^[-–—]\s*", "", p0).strip()
                                clean_p1 = re.sub(r"^[-–—]\s*", "", p1).strip()
                                old_t = ev.text
                                ev.text = f"{ts_prefix}- {clean_p0}\\N- {clean_p1}"
                                if ev.text != old_t:
                                    fixes.append(f"[Episode Quality Gate - Filar LVII Symetria Myślników AVT] Linia #{i+1}: uzupełniono brakujący myślnik w drugim wersie dwugłosu")
                        elif not has_dash0 and has_dash1:
                            if re.search(r"[.!?…]$", p0) and re.match(r"^[A-ZĄĆĘŁŃÓŚŹŻ0-9„\"'\(]", p1):
                                clean_p0 = re.sub(r"^[-–—]\s*", "", p0).strip()
                                clean_p1 = re.sub(r"^[-–—]\s*", "", p1).strip()
                                old_t = ev.text
                                ev.text = f"{ts_prefix}- {clean_p0}\\N- {clean_p1}"
                                if ev.text != old_t:
                                    fixes.append(f"[Episode Quality Gate - Filar LVII Symetria Myślników AVT] Linia #{i+1}: uzupełniono brakujący myślnik w pierwszym wersie dwugłosu")

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

            # 3b. INTER-LINE T-V INVARIANCE (Filar CLVII & Filar CLXXXII): First name in dialogue vs unexpected 'pan/pani'
            if not is_sign and prev_clean and prev_ev:
                time_gap_ms = ev.start - prev_ev.end
                has_tv_transition_cue = bool(re.search(
                    r"\b(?:mów mi po imieniu|przejdźmy na ty|nie mów do mnie pan|nie mów do mnie pani|mówmy sobie po imieniu|po imieniu|zwracaj się do mnie po imieniu)\b",
                    prev_clean + " " + ev.text,
                    re.IGNORECASE
                )) or ("SHOCK_DROP" in getattr(ev, "effect", "") or "SHOCK_DROP" in getattr(prev_ev, "effect", ""))

                if time_gap_ms < 6000 and not has_tv_transition_cue:
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
                        r"(?<!\bpanie\s)(?<!\bpani\s)(?<!\bpanno\s)(?<!\bmistrzu\s)(?<!\blordzie\s)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})[,!]",
                        prev_clean
                    )
                    prev_voc_name = fn_prev_m.group(1) if fn_prev_m else ""
                    p_clean_n = prev_voc_name.lower() if prev_voc_name else ""
                    NON_NAME_INTERJECTIONS = {
                        "gdzie", "dokąd", "kiedy", "dlaczego", "czemu", "naprawdę", "serio", "jasne",
                        "właśnie", "może", "chyba", "pewnie", "oczywiście", "proszę", "przepraszam",
                        "uwaga", "uważaj", "uważajcie", "zaraz", "chwila", "czekaj", "poczekaj",
                        "pomocy", "ratunku", "zobacz", "spójrz", "słuchaj", "witaj", "witajcie",
                        "cześć", "żegnaj", "dzień", "dobry", "wieczór", "noc", "pora", "brawo",
                        "dzięki", "dobrze", "jasne", "racja", "prawda", "spokojnie", "powoli"
                    }
                    is_excluded_entity = bool(
                        not prev_voc_name or
                        p_clean_n in NON_NAME_ACTORS or
                        p_clean_n in ETHNONYMS_AND_COLLECTIVES or
                        p_clean_n in NON_NAME_INTERJECTIONS or
                        (series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(prev_voc_name))
                    )
                    first_name_in_prev = bool(fn_prev_m) and not is_excluded_entity and not has_formal_voc_prev
                    if first_name_in_prev and not has_formal_voc_curr:
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
                        (r"\balbo\s+pan\b(?!\s+[A-ZĄĆĘŁŃÓŚŹŻ])", "albo ty"),
                        (r"\balbo\s+pani\b(?!\s+[A-ZĄĆĘŁŃÓŚŹŻ])", "albo ty"),
                        (r"\bdowiesz\s+się\s+pierwszy\b", "dowiesz się pierwsza" if addressee_is_female else "dowiesz się pierwszy")
                    ]
                    for tv_pat, tv_rep in intra_tv_fixes:
                        if re.search(tv_pat, ev.text, re.IGNORECASE):
                            ev.text = re.sub(tv_pat, tv_rep, ev.text, flags=re.IGNORECASE)
                            fixes.append(f"[Episode Quality Gate - Intra-Line T-V Invariance] Linia #{i+1}: zlikwidowano hybrydę 'ty' + zwrot formalny: '{tv_pat}' -> '{tv_rep}'")

            # 3b-2b. CHILD ADDRESSEE ANTI-PATRONIZING & DIRECT-TY GATE (Filar CLXIII - 0.00 PLN)
            # Adults addressing young children (CHILD_FEMALE, CHILD_MALE, dziewczynka, chłopiec)
            # NEVER use formal 'Pan/Pani' in Polish AVT. Harmonize formal address to direct, caring 'ty'.
            if not is_sign:
                is_child_addr = False
                child_addr_gender = "UNKNOWN"
                raw_ev_addr = getattr(ev, "addressee", None) or (line_addressees.get(i) if line_addressees else None) or ""
                addr_text = str(raw_ev_addr).lower()
                clean_ev_c = re.sub(r"\{[^\}]*\}", "", ev.text)

                if any(w in addr_text for w in ["child_female", "dziewczynk", "mała dziewczynka", "young girl", "little girl"]):
                    is_child_addr = True
                    child_addr_gender = "FEMALE"
                elif any(w in addr_text for w in ["child_male", "chłopiec", "mały chłopiec", "young boy", "little boy", "bocchan", "bozu", "kozo"]):
                    is_child_addr = True
                    child_addr_gender = "MALE"
                elif "child" in addr_text or "dziecko" in addr_text:
                    is_child_addr = True

                if not is_child_addr and series_bible and hasattr(series_bible, "get_character_age_class"):
                    cand_addr_clean = extract_clean_speaker_name(re.sub(r"\s*\(.*?\)", "", str(raw_ev_addr))).strip()
                    if cand_addr_clean and series_bible.get_character_age_class(cand_addr_clean) == "CHILD":
                        is_child_addr = True
                        if hasattr(series_bible, "get_character_gender"):
                            bg = series_bible.get_character_gender(cand_addr_clean, allow_generic_nouns=False)
                            if bg in ("FEMALE", "MALE"):
                                child_addr_gender = bg

                if not is_child_addr:
                    # Check vocatives in current line or preceding event
                    if re.search(r"\b(dziewczynko|mała|córeczko|panienko)\b[!,\?]", clean_ev_c, re.IGNORECASE):
                        is_child_addr = True
                        child_addr_gender = "FEMALE"
                    elif re.search(r"\b(chłopcze|maluchu|synku|chłopczyku)\b[!,\?]", clean_ev_c, re.IGNORECASE):
                        is_child_addr = True
                        child_addr_gender = "MALE"
                    elif prev_clean and re.search(r"\b(dziewczynko|mała|córeczko|panienko)\b[!,\?]", prev_clean, re.IGNORECASE) and (ev.start - prev_ev.end < 4000):
                        is_child_addr = True
                        child_addr_gender = "FEMALE"
                    elif prev_clean and re.search(r"\b(chłopcze|maluchu|synku|chłopczyku)\b[!,\?]", prev_clean, re.IGNORECASE) and (ev.start - prev_ev.end < 4000):
                        is_child_addr = True
                        child_addr_gender = "MALE"

                if is_child_addr:
                    old_c_t = ev.text
                    child_rules = [
                        # Questions & Inquiries
                        (r"\b(?:czy\s+)?pani\s+się\s+zgubiła\b", "zgubiłaś się"),
                        (r"\b(?:czy\s+)?pan\s+się\s+zgubił\b", "zgubiłeś się"),
                        (r"\bzgubiła\s+się\s+pani\b", "zgubiłaś się"),
                        (r"\bzgubił\s+się\s+pan\b", "zgubiłeś się"),
                        (r"\bco\s+pani\s+tu\s+robi\b", "co tu robisz"),
                        (r"\bco\s+pan\s+tu\s+robi\b", "co tu robisz"),
                        (r"\bco\s+pani\s+się\s+stało\b", "co ci się stało"),
                        (r"\bco\s+panu\s+się\s+stało\b", "co ci się stało"),
                        (r"\bjak\s+ma\s+pani\s+na\s+imię\b", "jak masz na imię"),
                        (r"\bjak\s+ma\s+pan\s+na\s+imię\b", "jak masz na imię"),
                        (r"\bgdzie\s+są\s+pani\s+rodzice\b", "gdzie są twoi rodzice"),
                        (r"\bgdzie\s+są\s+pana\s+rodzice\b", "gdzie są twoi rodzice"),
                        (r"\bgdzie\s+jest\s+pani\s+mama\b", "gdzie jest twoja mama"),
                        (r"\bgdzie\s+jest\s+pana\s+mama\b", "gdzie jest twoja mama"),
                        # Imperatives & Warnings
                        (r"\bniech\s+pani\s+uważa\b", "uważaj"),
                        (r"\bniech\s+pan\s+uważa\b", "uważaj"),
                        (r"\bniech\s+pani\s+nie\s+płacze\b", "nie płacz"),
                        (r"\bniech\s+pan\s+nie\s+płacze\b", "nie płacz"),
                        (r"\bniech\s+pani\s+weźmie\b", "weź"),
                        (r"\bniech\s+pan\s+weźmie\b", "weź"),
                        (r"\bniech\s+pani\s+zostawi\b", "zostaw"),
                        (r"\bniech\s+pan\s+zostawi\b", "zostaw"),
                        (r"\bniech\s+pani\s+poczeka\b", "poczekaj"),
                        (r"\bniech\s+pan\s+poczeka\b", "poczekaj"),
                        (r"\bniech\s+pani\s+idzie\b", "idź"),
                        (r"\bniech\s+pan\s+idzie\b", "idź"),
                        (r"\bniech\s+pani\s+ucieka\b", "uciekaj"),
                        (r"\bniech\s+pan\s+ucieka\b", "uciekaj"),
                        # Caring requests & Offers
                        (r"\bpani\s+pozwoli\b", "pozwól"),
                        (r"\bpan\s+pozwoli\b", "pozwól"),
                        (r"\boferuję\s+pani\s+pomoc\b", "oferuję ci pomoc"),
                        (r"\boferuję\s+panu\s+pomoc\b", "oferuję ci pomoc"),
                        (r"\bchcę\s+pani\s+pomóc\b", "chcę ci pomóc"),
                        (r"\bchcę\s+panu\s+pomóc\b", "chcę ci pomóc"),
                        (r"\bmogę\s+pani\s+pomóc\b", "mogę ci pomóc"),
                        (r"\bmogę\s+panu\s+pomóc\b", "mogę ci pomóc"),
                        (r"\bpomogę\s+pani\b", "pomogę ci"),
                        (r"\bpomogę\s+panu\b", "pomogę ci"),
                        (r"\bbo\s+pani\s+spadnie\b", "bo spadniesz"),
                        (r"\bbo\s+pan\s+spadnie\b", "bo spadniesz"),
                        (r"\bprzysłał\s+tu\s+panią\b", "przysłał cię tu"),
                        (r"\bprzysłał\s+tu\s+pana\b", "przysłał cię tu"),
                        # Family & Possessives
                        (r"\bpani\s+mama\b", "twoja mama"),
                        (r"\bpana\s+mama\b", "twoja mama"),
                        (r"\bpani\s+tat[aę]\b", "twój tata" if "tata" in ev.text.lower() else "twojego tatę"),
                        (r"\bpana\s+tat[aę]\b", "twój tata" if "tata" in ev.text.lower() else "twojego tatę"),
                        (r"\bpani\s+rodzice\b", "twoi rodzice"),
                        (r"\bpana\s+rodzice\b", "twoi rodzice"),
                        (r"\bpani\s+rodziców\b", "twoich rodziców"),
                        (r"\bpana\s+rodziców\b", "twoich rodziców"),
                        # Prepositions + pan/pani
                        (r"\bdla\s+pani\b", "dla ciebie"),
                        (r"\bdla\s+pana\b", "dla ciebie"),
                        (r"\bu\s+pani\b", "u ciebie"),
                        (r"\bu\s+pana\b", "u ciebie"),
                        (r"\bod\s+pani\b", "od ciebie"),
                        (r"\bod\s+pana\b", "od ciebie"),
                        (r"\bo\s+pani\b", "o tobie"),
                        (r"\bo\s+pana\b", "o ciebie"),
                        (r"\bz\s+panią\b", "z tobą"),
                        (r"\bz\s+panem\b", "z tobą"),
                    ]
                    for c_pat, c_rep in child_rules:
                        if re.search(c_pat, ev.text, re.IGNORECASE):
                            def _c_repl(m, r_str=c_rep):
                                matched = m.group(0)
                                if matched[0].isupper():
                                    return r_str[0].upper() + r_str[1:]
                                return r_str
                            ev.text = re.sub(c_pat, _c_repl, ev.text, flags=re.IGNORECASE)
                    if ev.text != old_c_t:
                        fixes.append(f"[Episode Quality Gate - Filar CLXIII Adresat Dziecięcy] Linia #{i+1}: zredukowano sztuczny zwrot formalny (Pan/Pani) na bezpośredni rejestr opiekuńczy 'ty'")

            # 3b-3. INTRA-LINE HYBRID VOCATIVE + FORMAL ADDRESS GUARD (Filar C & CLVII)
            if not is_sign:
                clean_ev_check = re.sub(r"\\[Nnh]", " ", ev.text)
                has_formal_address_in_line = bool(re.search(
                    r"\b[a-ząćęłńóśźż]+(?:ł|ła|li|ły|łby|łaby)\s+(?:pan|pani)\b|"
                    r"\b(?:pan|pani)\s+[a-ząćęłńóśźż]+(?:ł|ła|li|ły|łby|łaby)\b|"
                    r"\b(?:ma|niech|chce|chciał|chciała|może|widzi|widział|widziała|słyszy|słyszał|słyszała|wie|wiedział|wiedziała|pamięta|pamiętał|szuka|szukał|prosił|prosiła|czuje|czuł|smakuje|stoi|stał|jest|był|była)\s+(?:pan|pani|pana|panu)\b|"
                    r"\b(?:pan|pani|pana|panu)\s+(?:ma|niech|chce|chciał|chciała|może|widzi|widział|widziała|słyszy|słyszał|słyszała|wie|wiedział|wiedziała|pamięta|pamiętał|szuka|szukał|prosił|prosiła|czuje|czuł|smakuje|stoi|stał|jest|był|była|prosił|szuka)\b|"
                    r"\b(?:u|dla|od|przeciwko)\s+(?:pana|pani|panu)\b|"
                    r"\bźle\s+się\s+pan\b|\bsmakuje\s+panu\b|\bpanu\s+o\s+tym\b|\bpanu\s+nie\b|\bniech\s+pan\b|\bchciał\s+pan\b|\bpan\s+szuka\b|\bma\s+pan\b",
                    clean_ev_check,
                    re.IGNORECASE
                ))
                if has_formal_address_in_line:
                    def _fix_hybrid_voc(m):
                        lead_sep = m.group(1) or ""
                        name = m.group(2)
                        trail_punct = m.group(3) or ""
                        name_low = name.lower()
                        if name_low in {"panie", "pani", "panno", "mistrzu", "panu", "bogu", "czasu", "domu", "końcu", "początku", "bratu", "chłopcu", "wtedy", "znowu", "ogromny", "ognisty", "smakuje", "nigdy", "razem"}:
                            return m.group(0)
                        # Check that the vocative corresponds to a candidate character name
                        is_cand = any(name_low.startswith(c[:max(3, len(c)-2)].lower()) for c in candidate_names)
                        if not is_cand:
                            return m.group(0)
                        before = ev.text[:m.start()].rstrip()
                        # Strict safeguard: NEVER apply if preceded by ANY preposition or title form
                        if re.search(r"\b(?:od|do|dla|z|ze|u|o|przy|w|we|na|przez|bez|przeciwko|wobec|pan|pani|pana|panu|panem|panie)\s*$", before, re.IGNORECASE):
                            return m.group(0)
                        is_start = (before == "" or bool(re.search(r"[\.!\?…]$|\\[Nnh]$", before)))
                        title = "Panie" if is_start else "panie"
                        fixes.append(f"[Episode Quality Gate - Filar C/CLVII] Linia #{i+1}: zlikwidowano hybrydę wołacza '{name}' + zwrot formalny -> '{title} {name}'")
                        return f"{lead_sep}{title} {name}{trail_punct}"

                    ev.text = re.sub(
                        r"(^|\\[Nnh]|[-–]\s*|,\s*)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}[uey])([,!?…\.]+|\s*\\[Nnh]|\s*$)",
                        _fix_hybrid_voc,
                        ev.text
                    )

            # 3b-4. SUBJECT NOMINATIVE CASE REPAIR FOR TITLE APPOSITION (Filar CLVII / CLXX)
            if not is_sign:
                TITLES_SUBJECT_PAT = r"[Pp]an|[Pp]ani|[Mm]istrz|[Pp]rofesor|[Dd]oktor|[Pp]isarz|[Rr]eżyser|[Rr]edaktor|[Aa]utor|[Mm]angaka|[Ss]ensei"

                # Closed-World Invariance (Aksjomat 4):
                # Trimming '-a' in title apposition is PERMITTED ONLY IF the base stem
                # explicitly exists in the project's knowledge base (series_memory, candidate_names, series_bible).
                # Otherwise, proper names are invariant!
                known_stems = {n.lower() for n in candidate_names}
                if series_bible and hasattr(series_bible, "character_names"):
                    known_stems.update({n.lower() for n in series_bible.character_names})
                if character_registry:
                    known_stems.update({k.lower() for k in character_registry.keys()})

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
                    if title.lower() == "pani":
                        return m.group(0)
                    
                    if surname_stem.lower() in known_stems:
                        clean_surname = surname_stem
                    else:
                        clean_surname = surname_stem + "a"

                    clean_given = given_name.capitalize()
                    if clean_surname != surname_stem + "a" or clean_given != given_name:
                        fixes.append(
                            f"[Episode Quality Gate - Filar CLVII/CLXX] Linia #{i+1}: "
                            f"skorygowano mianownik i wielkość liter tytulatury '{title} {surname_stem}a {given_name}' -> '{title} {clean_surname} {clean_given}'"
                        )
                        return f"{prefix}{title}{sep1}{clean_surname}{sep2}{clean_given}{sep3}{verb}"
                    return m.group(0)

                ev.text = re.sub(
                    rf"(^|[^\w]|\\[Nnh])({TITLES_SUBJECT_PAT})(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻŌŪĀĒĪ][a-ząćęłńóśźżōūāēī]*[bcdfghjklmnprstvwxz])a(\s+|\\[Nnh]+)([A-Za-ząćęłńóśźżōūāēī]+)(\s+|\\[Nnh]+)((?:nie\s+)?[a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
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
                    if title.lower() == "pani":
                        return m.group(0)
                    
                    if name_stem.lower() in known_stems:
                        fixes.append(f"[Episode Quality Gate - Filar CLVII/CLXX] Linia #{i+1}: skorygowano skażenie mianownika tytulatury '{title} {name_stem}a' -> '{title} {name_stem}'")
                        return f"{prefix}{title}{sep1}{name_stem}{sep2}{verb}"
                    
                    # Name is invariant (e.g. Luca, Joshua, Sasha, Vegeta, Kiba, Katsura, Asura)
                    return m.group(0)

                ev.text = re.sub(
                    rf"(^|[^\w]|\\[Nnh])({TITLES_SUBJECT_PAT})(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻŌŪĀĒĪ][a-ząćęłńóśźżōūāēī]*[bcdfghjklmnprstvwxz])a(\s+|\\[Nnh]+)((?:nie\s+)?[a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
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
                    if not spk_gen and series_bible and hasattr(series_bible, "get_character_age_class"):
                        if series_bible.get_character_age_class(spk_clean) == "CHILD":
                            if hasattr(series_bible, "get_character_gender"):
                                b_g = series_bible.get_character_gender(spk_clean, allow_generic_nouns=False)
                                if b_g in ("FEMALE", "MALE"):
                                    spk_gen = b_g
                    if not spk_gen and series_bible and hasattr(series_bible, "is_low_pitch_female"):
                        if series_bible.is_low_pitch_female(spk_clean):
                            spk_gen = "FEMALE"

                # Acoustic, Prosody & Pronoun Gender Check (Runs for both named and anonymous speakers)
                jp_aud_check = (whisper_transcriptions.get(i + 1, "") if whisper_transcriptions else "") or (getattr(ev, "audio_jp", "") or "")
                pt_val = (prosody_tags.get(i, "") if prosody_tags else "") or getattr(ev, "prosody", "") or ""
                pt_lower = str(pt_val).lower()
                has_female_prosody = bool(re.search(r"\b(?:sopran|alt|żeńsk[a-ząćęłńóśźż]*|mowca_k|speaker_f|dziewczyn[a-ząćęłńóśźż]*|kobiet[a-ząćęłńóśźż]*|girl|f0\s*>=\s*185|wysoki\s+f0)\b", pt_lower))
                has_male_prosody = not has_female_prosody and bool(re.search(r"\b(?:baryton|bas|męsk[a-ząćęłńóśźż]*|mowca_m|speaker_m|chłopak[a-ząćęłńóśźż]*|chłopiec|chłopca|chłopcu|chłopcem|chłopce|chłopcy|mężczyzn[a-ząćęłńóśźż]*|boy|f0\s*<=\s*165|niski\s+f0)\b", pt_lower))
                has_male_jp_pronoun = any(re.search(rf"\b{pr}\b", jp_aud_check, re.IGNORECASE) for pr in ["boku", "ore", "washi", "僕", "俺", "Mówca_M", "CHILD_MALE"])
                if not spk_gen:
                    if "CHILD_FEMALE" in jp_aud_check or "Mówca_K" in jp_aud_check or has_female_prosody:
                        spk_gen = "FEMALE"
                    elif "CHILD_MALE" in jp_aud_check or "Mówca_M" in jp_aud_check or has_male_prosody or has_male_jp_pronoun:
                        spk_gen = "MALE"

                if spk_gen == "MALE":
                    # Acoustic & Scene Primacy Shield (Filar CLXXIV - 0.00 PLN):
                    # If actor tag is MALE, but scene is confirmed FEMALE
                    # or physical audio is FEMALE, override spk_gen to FEMALE only if contaminated!
                    jp_aud = (whisper_transcriptions.get(i + 1, "") if whisper_transcriptions else "") or (getattr(ev, "audio_jp", "") or "")
                    w_is_fem = any(m in jp_aud.lower() for m in ["warawa", "妾", "atashi", "あたし", "atai", "あtai", "wa yo", "わよ", "kashira", "かしら"])
                    sc_is_fem = (event_scene_gender.get(i) == "FEMALE")
                    is_cont = False
                    checked_bible = False
                    spk_c = extract_clean_speaker_name(str(spk_name)).lower() if spk_name else ""
                    if series_bible and hasattr(series_bible, "audit_speaker_metadata_against_audio") and spk_c:
                        aud_res, is_cont = series_bible.audit_speaker_metadata_against_audio(spk_c, whisper_gender="FEMALE" if w_is_fem else None, scene_gender="FEMALE" if sc_is_fem else None)
                        checked_bible = True
                        if is_cont and aud_res == "FEMALE":
                            spk_gen = "FEMALE"
                    if not checked_bible and not spk_c and (sc_is_fem or w_is_fem):
                        spk_gen = "FEMALE"


                # Scene-Level Exclusive Gender Assignment for Anonymous Speaker
                if not spk_gen and event_scene_gender.get(i):
                    spk_gen = event_scene_gender.get(i)

                # Turn-Level Gender Harmony Gate (Speaker Turn Continuity & Monologue Arc - Filar CLXXXV):
                # Detect contiguous dialogue turn morphology (gap < 2200ms, or up to 5000ms for monologue/thought arcs)
                turn_s = i
                while turn_s > 0:
                    p_ev = events[turn_s - 1]
                    c_ev = events[turn_s]
                    gap = c_ev.start - p_ev.end

                    p_is_italic = bool(re.search(r"\{\\i1\}", p_ev.text or ""))
                    c_is_italic = bool(re.search(r"\{\\i1\}", c_ev.text or ""))
                    p_clean = re.sub(r"\{[^\}]*\}", "", p_ev.text or "").strip()
                    c_clean = re.sub(r"\{[^\}]*\}", "", c_ev.text or "").strip()
                    has_ellipsis = p_clean.endswith("...") or p_clean.endswith("…") or c_clean.startswith("...") or c_clean.startswith("…")

                    is_monologue_arc = (p_is_italic and c_is_italic) or has_ellipsis
                    max_gap = 5000 if is_monologue_arc else 2200

                    if gap >= max_gap:
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

                    c_is_italic = bool(re.search(r"\{\\i1\}", c_ev.text or ""))
                    n_is_italic = bool(re.search(r"\{\\i1\}", n_ev.text or ""))
                    c_clean = re.sub(r"\{[^\}]*\}", "", c_ev.text or "").strip()
                    n_clean = re.sub(r"\{[^\}]*\}", "", n_ev.text or "").strip()
                    has_ellipsis = c_clean.endswith("...") or c_clean.endswith("…") or n_clean.startswith("...") or n_clean.startswith("…")

                    is_monologue_arc = (c_is_italic and n_is_italic) or has_ellipsis
                    max_gap = 5000 if is_monologue_arc else 2200

                    if gap >= max_gap:
                        break
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
                    if re.search(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łam|łabym|szłam)\b|\b(?:będę)\s+[A-Za-ząćęłńóśźż]+(?:ała|iła|yła|ogła)\b", tev.text or "", re.IGNORECASE)
                )
                turn_masc_count = sum(
                    1 for tev in turn_evs
                    if re.search(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łem|łbym|szedłem)\b|\b(?:będę)\s+[A-Za-ząćęłńóśźż]+(?:ał|ił|ył|eł|ół|ógł)\b", tev.text or "", re.IGNORECASE)
                )

                # Zero-Evidence Invariance Gate: Only determine spk_gen from hard external evidence
                # (metadata, character registry, acoustics, or Japanese audio pronouns).
                # KATEGORYCZNY ZAKAZ auto-zgadywania płci z tekstu wygenerowanego przez LLM,
                # co tworzyło błędne koło inferencji i narzucało fałszywą maskulinizację/feminizację.
                if spk_gen is None:
                    pt_val = (prosody_tags.get(i, "") if prosody_tags else "") or getattr(ev, "prosody", "") or ""
                    pt_lower = str(pt_val).lower()
                    has_female_prosody_turn = bool(re.search(r"\b(?:sopran|alt|żeńsk[a-ząćęłńóśźż]*|mowca_k|speaker_f|dziewczyn[a-ząćęłńóśźż]*|kobiet[a-ząćęłńóśźż]*|girl|f0\s*>=\s*185|wysoki\s+f0)\b", pt_lower))
                    has_male_acoustic = not has_female_prosody_turn and bool(re.search(r"\b(?:baryton|bas|męsk[a-ząćęłńóśźż]*|mowca_m|speaker_m|chłopak[a-ząćęłńóśźż]*|chłopiec|chłopca|chłopcu|chłopcem|chłopce|chłopcy|mężczyzn[a-ząćęłńóśźż]*|boy|f0\s*<=\s*165|niski\s+f0)\b", pt_lower))
                    jp_aud_line = (whisper_transcriptions.get(i + 1, "") if whisper_transcriptions else "") or (getattr(ev, "audio_jp", "") or "")
                    has_male_jp = any(re.search(rf"\b{pr}\b", jp_aud_line, re.IGNORECASE) for pr in ["boku", "ore", "washi", "僕", "俺", "Mówca_M", "CHILD_MALE"])
                    has_fem_jp = any(re.search(rf"\b{pr}\b", jp_aud_line, re.IGNORECASE) for pr in ["atashi", "atai", "あたし", "Mówca_K", "CHILD_FEMALE"])

                    has_masc_modal = any(re.search(r"\b(?:będę\s+musiał|musiałem|będę\s+mógł|będę\s+chciał)\b", tev.text or "", re.IGNORECASE) for tev in turn_evs)
                    has_fem_modal = any(re.search(r"\b(?:będę\s+musiała|musiałam|będę\s+mogła|będę\s+chciała)\b", tev.text or "", re.IGNORECASE) for tev in turn_evs)

                    if has_female_prosody_turn or has_fem_jp:
                        spk_gen = "FEMALE"
                    elif has_male_acoustic or has_male_jp:
                        spk_gen = "MALE"
                    elif has_masc_modal and not has_fem_modal:
                        spk_gen = "MALE"
                    elif has_fem_modal and not has_masc_modal:
                        spk_gen = "FEMALE"
                    elif turn_fem_count > 0 and (turn_s < turn_e and turn_fem_count >= turn_masc_count):
                        spk_gen = "FEMALE"
                    elif turn_masc_count > 0 and (turn_s < turn_e and turn_masc_count > turn_fem_count):
                        spk_gen = "MALE"

                label_spk = spk_name or ("kobieta" if spk_gen == "FEMALE" else "mężczyzna")

                # Quote & Indirect Speech Shield (Filar CLXX / CLXXXVII - 0.00 PLN)
                # Protect reported speech enclosed within quotes („...”, "...", »...«, «...»)
                quote_shield_map = {}
                def _quote_shield_repl(qm):
                    q_key = f"__QUOTE_SHIELD_{len(quote_shield_map)}__"
                    quote_shield_map[q_key] = qm.group(0)
                    return q_key

                ev.text = re.sub(r'(„[^”\r\n]+”|\"[^\"\r\n]+\"|»[^«\r\n]+«|«[^»\r\n]+»)', _quote_shield_repl, ev.text)

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
                    dyn_part_pat_m = rf"\b((?:byłem|byłam|czułem\s+się|czułam\s+się|zostałem|zostałam|poczułem\s+się|poczułam\s+się)\s+)([A-Za-ząćęłńóśźż]+(?:ona|ana|ta|iona))\b"
                    for match in list(re.finditer(dyn_part_pat_m, ev.text, re.IGNORECASE)):
                        p_prefix = match.group(1)
                        p_part = match.group(2)
                        p_masc = convert_passive_participle_to_masculine(p_part)
                        if p_masc and p_masc.lower() != p_part.lower():
                            ev.text = re.sub(rf"\b{re.escape(p_prefix)}{re.escape(p_part)}\b", f"{p_prefix}{p_masc}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano imiesłów 1. os. na rodzaj męski dla mówcy '{label_spk}' ('{p_prefix}{p_part}' -> '{p_prefix}{p_masc}')")
                    # Clitics for male speaker
                    clitic_pat = r"\b((?:gdybym|jakbym|żebym|abym|bym|choćbym|chociażbym)\s+)([A-Za-ząćęłńóśźż]+(?:ała|iła|yła|ęła))\b"
                    for match in list(re.finditer(clitic_pat, ev.text, re.IGNORECASE)):
                        c_prefix = match.group(1)
                        c_verb = match.group(2)
                        c_masc = convert_feminine_past_to_masculine(c_verb)
                        if c_masc and c_masc.lower() != c_verb.lower():
                            ev.text = re.sub(rf"\b{re.escape(c_prefix)}{re.escape(c_verb)}\b", f"{c_prefix}{c_masc}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano klitykę 1. os. na rodzaj męski dla mówcy '{label_spk}' ('{c_prefix}{c_verb}' -> '{c_prefix}{c_masc}')")
                    # Predicate nouns for male speaker in 1st person (Zasada 12 & 15)
                    mods_m_pat_1p = "|".join([m for m, f in PREDICATE_MODS_INSTRUMENTAL])
                    mods_f_pat_1p = "|".join([f for m, f in PREDICATE_MODS_INSTRUMENTAL])
                    all_mods_pat_1p = f"{mods_m_pat_1p}|{mods_f_pat_1p}"
                    masc_all_nouns_pat_1p = "|".join([m for m, f in PREDICATE_NOUNS_INSTRUMENTAL_PAIRS if m != f])
                    has_1p_copula_m = bool(re.search(r"\b(?:byłem|byłam|zostałem|zostałam|stałem\s+się|stałam\s+się|będę|jestem)\b", ev.text, re.IGNORECASE))
                    if has_1p_copula_m:
                        for m_n, f_n in PREDICATE_NOUNS_INSTRUMENTAL_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn = rf"((?:\b(?:byłem|byłam|zostałem|zostałam|stałem\s+się|stałam\s+się|będę|jestem)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_f_pat_1p})\s+){{0,3}})({re.escape(f_n)})\b"
                            for match in list(re.finditer(pat_pn, ev.text, re.IGNORECASE)):
                                pref = match.group(1)
                                old_n = match.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_pat_1p})\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = m_n.capitalize() if old_n[0].isupper() else m_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano orzecznik rzeczownikowy 1. os. na rodzaj męski dla mówcy '{label_spk}' ('{old_n}' -> '{repl_n}')")
                        for m_mod, f_mod in PREDICATE_MODS_INSTRUMENTAL:
                            pat_mod = rf"((?:\b(?:byłem|byłam|zostałem|zostałam|stałem\s+się|stałam\s+się|będę|jestem)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_pat_1p})\s+){{0,2}})({re.escape(f_mod)})(\s+(?:(?:{all_mods_pat_1p})\s+)*(?:{masc_all_nouns_pat_1p}))\b"
                            ev.text = re.sub(pat_mod, rf"\g<1>{m_mod}\g<3>", ev.text, flags=re.IGNORECASE)

                    # Predicate nouns for male speaker in Nominative 1st person
                    mods_m_nom_pat_1p = "|".join([m for m, f in PREDICATE_MODS_NOMINATIVE])
                    mods_f_nom_pat_1p = "|".join([f for m, f in PREDICATE_MODS_NOMINATIVE])
                    all_mods_nom_pat_1p = f"{mods_m_nom_pat_1p}|{mods_f_nom_pat_1p}"
                    masc_all_nouns_nom_pat_1p = "|".join([m for m, f in PREDICATE_NOUNS_NOMINATIVE_PAIRS if m != f])
                    has_1p_nom_copula_m = bool(re.search(r"\b(?:jestem|byłem|byłam|zostałem|zostałam|to\s+jest|to)\b", ev.text, re.IGNORECASE))
                    if has_1p_nom_copula_m:
                        for m_n, f_n in PREDICATE_NOUNS_NOMINATIVE_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn_nom = rf"((?:\b(?:jestem|byłem|byłam|zostałem|zostałam|to\s+jest|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_f_nom_pat_1p})\s+){{0,3}})({re.escape(f_n)})\b"
                            for match in list(re.finditer(pat_pn_nom, ev.text, re.IGNORECASE)):
                                pref = match.group(1)
                                old_n = match.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_nom_pat_1p})\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = m_n.capitalize() if old_n[0].isupper() else m_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano mianownik orzecznikowy 1. os. na rodzaj męski dla mówcy '{label_spk}' ('{old_n}' -> '{repl_n}')")
                        for m_mod, f_mod in PREDICATE_MODS_NOMINATIVE:
                            pat_mod_nom = rf"((?:\b(?:jestem|byłem|byłam|zostałem|zostałam|to\s+jest|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_nom_pat_1p})\s+){{0,2}})({re.escape(f_mod)})(\s+(?:(?:{all_mods_nom_pat_1p})\s+)*(?:{masc_all_nouns_nom_pat_1p}))\b"
                            ev.text = re.sub(pat_mod_nom, rf"\g<1>{m_mod}\g<3>", ev.text, flags=re.IGNORECASE)
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
                    dyn_part_pat_f = rf"\b((?:byłam|byłem|czułam\s+się|czułem\s+się|zostałam|zostałem|poczułam\s+się|poczułem\s+się)\s+)([A-Za-ząćęłńóśźż]+(?:ony|any|ty|iony))\b"
                    for match in list(re.finditer(dyn_part_pat_f, ev.text, re.IGNORECASE)):
                        p_prefix = match.group(1)
                        p_part = match.group(2)
                        p_fem = convert_passive_participle_to_feminine(p_part)
                        if p_fem and p_fem.lower() != p_part.lower():
                            ev.text = re.sub(rf"\b{re.escape(p_prefix)}{re.escape(p_part)}\b", f"{p_prefix}{p_fem}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano imiesłów 1. os. na rodzaj żeński dla mówczyni '{label_spk}' ('{p_prefix}{p_part}' -> '{p_prefix}{p_fem}')")
                    # Clitics for female speaker
                    clitic_pat = r"\b((?:gdybym|jakbym|żebym|abym|bym|choćbym|chociażbym)\s+)([A-Za-ząćęłńóśźż]+(?:ał|ił|ył|eł|ół|ął))\b"
                    for match in list(re.finditer(clitic_pat, ev.text, re.IGNORECASE)):
                        c_prefix = match.group(1)
                        c_verb = match.group(2)
                        c_fem = convert_masculine_past_to_feminine(c_verb)
                        if c_fem and c_fem.lower() != c_verb.lower():
                            ev.text = re.sub(rf"\b{re.escape(c_prefix)}{re.escape(c_verb)}\b", f"{c_prefix}{c_fem}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano klitykę 1. os. na rodzaj żeński dla mówczyni '{label_spk}' ('{c_prefix}{c_verb}' -> '{c_prefix}{c_fem}')")
                    # Predicate nouns for female speaker in 1st person (Zasada 12 & 15)
                    mods_m_pat_1p = "|".join([m for m, f in PREDICATE_MODS_INSTRUMENTAL])
                    mods_f_pat_1p = "|".join([f for m, f in PREDICATE_MODS_INSTRUMENTAL])
                    all_mods_pat_1p = f"{mods_m_pat_1p}|{mods_f_pat_1p}"
                    fem_all_nouns_pat_1p = "|".join([f for m, f in PREDICATE_NOUNS_INSTRUMENTAL_PAIRS if m != f])
                    has_1p_copula_f = bool(re.search(r"\b(?:byłam|byłem|zostałam|zostałem|stałam\s+się|stałem\s+się|będę|jestem)\b", ev.text, re.IGNORECASE))
                    if has_1p_copula_f:
                        for m_n, f_n in PREDICATE_NOUNS_INSTRUMENTAL_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn = rf"((?:\b(?:byłam|byłem|zostałam|zostałem|stałam\s+się|stałem\s+się|będę|jestem)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_m_pat_1p})\s+){{0,3}})({re.escape(m_n)})\b"
                            for match in list(re.finditer(pat_pn, ev.text, re.IGNORECASE)):
                                pref = match.group(1)
                                old_n = match.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_pat_1p})\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = f_n.capitalize() if old_n[0].isupper() else f_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano orzecznik rzeczownikowy 1. os. na rodzaj żeński dla mówczyni '{label_spk}' ('{old_n}' -> '{repl_n}')")
                        for m_mod, f_mod in PREDICATE_MODS_INSTRUMENTAL:
                            pat_mod = rf"((?:\b(?:byłam|byłem|zostałam|zostałem|stałam\s+się|stałem\s+się|będę|jestem)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_pat_1p})\s+){{0,2}})({re.escape(m_mod)})(\s+(?:(?:{all_mods_pat_1p})\s+)*(?:{fem_all_nouns_pat_1p}))\b"
                            ev.text = re.sub(pat_mod, rf"\g<1>{f_mod}\g<3>", ev.text, flags=re.IGNORECASE)

                    # Predicate nouns for female speaker in Nominative 1st person
                    mods_m_nom_pat_1p = "|".join([m for m, f in PREDICATE_MODS_NOMINATIVE])
                    mods_f_nom_pat_1p = "|".join([f for m, f in PREDICATE_MODS_NOMINATIVE])
                    all_mods_nom_pat_1p = f"{mods_m_nom_pat_1p}|{mods_f_nom_pat_1p}"
                    fem_all_nouns_nom_pat_1p = "|".join([f for m, f in PREDICATE_NOUNS_NOMINATIVE_PAIRS if m != f])
                    has_1p_nom_copula_f = bool(re.search(r"\b(?:jestem|byłam|byłem|zostałam|zostałem|to\s+jest|to)\b", ev.text, re.IGNORECASE))
                    if has_1p_nom_copula_f:
                        for m_n, f_n in PREDICATE_NOUNS_NOMINATIVE_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn_nom = rf"((?:\b(?:jestem|byłam|byłem|zostałam|zostałem|to\s+jest|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_m_nom_pat_1p})\s+){{0,3}})({re.escape(m_n)})\b"
                            for match in list(re.finditer(pat_pn_nom, ev.text, re.IGNORECASE)):
                                pref = match.group(1)
                                old_n = match.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_nom_pat_1p})\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = f_n.capitalize() if old_n[0].isupper() else f_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano mianownik orzecznikowy 1. os. na rodzaj żeński dla mówczyni '{label_spk}' ('{old_n}' -> '{repl_n}')")
                        for m_mod, f_mod in PREDICATE_MODS_NOMINATIVE:
                            pat_mod_nom = rf"((?:\b(?:jestem|byłam|byłem|zostałam|zostałem|to\s+jest|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_nom_pat_1p})\s+){{0,2}})({re.escape(m_mod)})(\s+(?:(?:{all_mods_nom_pat_1p})\s+)*(?:{fem_all_nouns_nom_pat_1p}))\b"
                            ev.text = re.sub(pat_mod_nom, rf"\g<1>{f_mod}\g<3>", ev.text, flags=re.IGNORECASE)

                if quote_shield_map:
                    for q_key, q_val in quote_shield_map.items():
                        ev.text = ev.text.replace(q_key, q_val)

                # 3c-2: 3rd-person subject-verb past-tense agreement & compound passive voice (Filar CLXII/CLXXXV)
                # Protected by Preposition Shield & Possessive Headword Shield (0.00 PLN)
                prep_pattern = (
                    r"\b(?:"
                    r"do|od|dla|z|ze|u|w|we|na|o|po|za|przed|przede|nad|nade|pod|pode|"
                    r"między|pomiędzy|przez|przeze|koło|obok|wokół|ku|bez|beze|według|"
                    r"przeciwko|naprzeciw|naprzeciwko|wobec|dzięki|oprócz|mimo|pomimo|"
                    r"wśród|pośród|wskutek|dookoła"
                    r")\s*(?:pana|pani|świętego|świętej|młodego|młodej|małego|małej|samego|samej)?\s*$"
                )
                possessive_headwords_pattern = (
                    r"\b(?:"
                    r"ojciec|ojca|ojcu|ojcem|ojcze|"
                    r"matka|matki|matce|matkę|matko|matką|"
                    r"tata|taty|tacie|tatę|tato|tatą|"
                    r"mama|mamy|mamie|mamę|mamo|mamą|"
                    r"brat|brata|bratu|bratem|bracie|bracia|braci|braćmi|"
                    r"siostra|siostry|siostrze|siostrę|siostro|siostrą|sióstr|siostrom|siostrami|"
                    r"syn|syna|synowi|synem|synu|synowie|synów|"
                    r"córka|córki|córce|córkę|córko|córką|córek|córkom|córkami|"
                    r"żona|żony|żonie|żonę|żono|żoną|"
                    r"mąż|męża|mężowi|mężem|mężu|"
                    r"dziadek|dziadka|dziadkowi|dziadkiem|dziadku|"
                    r"babcia|babci|babcię|babciu|babcią|"
                    r"wuj|wuja|wujowi|wujem|wuju|wujek|wujka|wujkowi|wujkiem|wujku|"
                    r"ciotka|ciotki|ciotce|ciotkę|ciotko|ciotką|ciocia|cioci|ciocię|ciociu|ciocią|"
                    r"kolega|kolegi|koledze|kolegę|kolego|kolegą|"
                    r"koleżanka|koleżanki|koleżance|koleżankę|koleżanko|koleżanką|"
                    r"przyjaciel|przyjaciela|przyjacielowi|przyjacielem|przyjacielu|przyjaciele|przyjaciół|"
                    r"przyjaciółka|przyjaciółki|przyjaciółce|przyjaciółkę|przyjaciółko|przyjaciółką|"
                    r"towarzysz|towarzysza|towarzyszowi|towarzyszem|towarzyszu|"
                    r"mistrz|mistrza|mistrzowi|mistrzem|mistrzu|"
                    r"pan|pana|panu|panem|panie|"
                    r"pani|panią|"
                    r"dowódca|dowódcy|dowódcę|dowódco|dowódcą|"
                    r"sługa|sługi|słudze|sługę|sługo|sługą|"
                    r"oddział|oddziału|oddziałem|oddziale|"
                    r"armia|armii|armię|armią|"
                    r"rodzina|rodziny|rodzinie|rodzinę|rodzino|rodziną|"
                    r"dom|domu|domem|domie|"
                    r"imię|imienia|imieniu|imieniem|"
                    r"nazwisko|nazwiska|nazwisku|nazwiskiem|"
                    r"głos|głosu|głosem|głosie|"
                    r"cień|cienia|cieniem|cieniu|"
                    r"ciało|ciała|ciele|ciałem|"
                    r"miecz|miecza|mieczem|mieczu|"
                    r"broń|broni|bronią|"
                    r"statek|statku|statkiem|"
                    r"pokój|pokoju|pokojem|"
                    r"list|listu|listem|liście|"
                    r"wiadomość|wiadomości|wiadomością|"
                    r"zdjęcie|zdjęcia|zdjęciu|zdjęciem|"
                    r"słowa|słów|słowom|słowami|"
                    r"wypowiedź|wypowiedzi|wypowiedzią|"
                    r"decyzja|decyzji|decyzję|decyzją|"
                    r"rozkaz|rozkazu|rozkazem|rozkazie|"
                    r"śmierć|śmierci|śmiercią|"
                    r"życie|życia|życiu|życiem|"
                    r"los|losu|losem|losie|"
                    r"znajomy|znajomego|znajomemu|znajomym|"
                    r"znajoma|znajomej|znajomą|"
                    r"wróg|wroga|wrogowi|wrogiem|wrogu"
                    r")\s*$"
                )
                any_prep_pattern = (
                    r"\b(?:"
                    r"do|od|dla|z|ze|u|w|we|na|o|po|za|przed|przede|nad|nade|pod|pode|"
                    r"między|pomiędzy|przez|przeze|koło|obok|wokół|ku|bez|beze|według|"
                    r"przeciwko|naprzeciw|naprzeciwko|wobec|dzięki|oprócz|mimo|pomimo|"
                    r"wśród|pośród|wskutek|dookoła"
                    r")\b"
                )

                for char_lower, gender in char_gender_map.items():
                    if len(char_lower) < 3:
                        continue
                    if char_lower not in ev.text.lower():
                        continue

                    # 1. Forward search: [Name] ... [verb / passive compound]
                    for m in list(re.finditer(rf"\b{re.escape(char_lower)}\b", ev.text, re.IGNORECASE)):
                        before_pos = m.start()
                        prefix = ev.text[:before_pos]
                        clause_prefix_match = re.search(r"[^\.,!\?;—–-]+$", prefix)
                        clause_prefix = clause_prefix_match.group(0) if clause_prefix_match else prefix

                        # Shield 1: Prepositional object guard (e.g. "poszedł do Yui", "wiadomość od Shira")
                        if re.search(prep_pattern, clause_prefix, re.IGNORECASE):
                            continue
                        # Shield 2: Possessive attribute guard (e.g. "ojciec Yui", "matka Shira")
                        if re.search(possessive_headwords_pattern, clause_prefix, re.IGNORECASE):
                            continue

                        after_pos = m.end()
                        remainder = ev.text[after_pos:]
                        clause_match = re.match(r"^[^\.,!\?;—–-]+", remainder)
                        if clause_match:
                            clause_text = clause_match.group(0)
                            tokens = list(re.finditer(r"\b[A-Za-ząćęłńóśźż]+\b", clause_text))
                            is_passive = False
                            clause_repls = []
                            for tok in tokens[:6]:  # check within next 6 words in clause
                                w = tok.group(0)
                                if w.lower() in ("został", "została"):
                                    is_passive = True
                                    if gender == "MALE" and w.lower() == "została":
                                        new_v = "Został" if w[0].isupper() else "został"
                                    elif gender == "FEMALE" and w.lower() == "został":
                                        new_v = "Została" if w[0].isupper() else "została"
                                    else:
                                        new_v = None
                                elif is_passive:
                                    if gender == "MALE":
                                        new_v = convert_passive_participle_to_masculine(w)
                                    elif gender == "FEMALE":
                                        new_v = convert_passive_participle_to_feminine(w)
                                    else:
                                        new_v = None
                                else:
                                    if gender == "MALE":
                                        new_v = convert_feminine_past_to_masculine(w)
                                    elif gender == "FEMALE":
                                        new_v = convert_masculine_past_to_feminine(w)
                                    else:
                                        new_v = None

                                if new_v and new_v.lower() != w.lower():
                                    clause_repls.append((tok.start(), tok.end(), w, new_v))
                                    if not is_passive:
                                        break

                            if clause_repls:
                                new_clause_text = clause_text
                                for s_idx, e_idx, old_w, rep_w in reversed(clause_repls):
                                    new_clause_text = new_clause_text[:s_idx] + rep_w + new_clause_text[e_idx:]
                                    fixes.append(
                                        f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: "
                                        f"skorygowano orzeczenie 3. osoby '{m.group(0)}... {old_w}' -> '{m.group(0)}... {rep_w}' "
                                        f"(potwierdzona płeć {'męska' if gender == 'MALE' else 'żeńska'})"
                                    )
                                ev.text = ev.text[:after_pos] + new_clause_text + ev.text[after_pos + len(clause_text):]

                    # 2. Inverted search: [verb] ... [Name]
                    for m in list(re.finditer(rf"\b{re.escape(char_lower)}\b", ev.text, re.IGNORECASE)):
                        before_pos = m.start()
                        prefix = ev.text[:before_pos]
                        clause_match = re.search(r"[^\.,!\?;—–-]+$", prefix)
                        if clause_match:
                            clause_text = clause_match.group(0)

                            # Shield 1: Direct Preposition Shield (e.g. "poszedł do Yui", "od Shira")
                            if re.search(prep_pattern, clause_text, re.IGNORECASE):
                                continue
                            # Shield 2: Possessive Headword Shield (e.g. "ojciec Yui", "matka Shira")
                            if re.search(possessive_headwords_pattern, clause_text, re.IGNORECASE):
                                continue

                            tokens = list(re.finditer(r"\b[A-Za-ząćęłńóśźż]+\b", clause_text))
                            for tok in reversed(tokens[-4:]):  # check backwards within last 4 words in clause
                                between_text = clause_text[tok.end():]
                                # Shield 3: Preposition between verb and Name (e.g. "poszedł do ... Yui", "rozmawiał z ... Shirą")
                                if re.search(any_prep_pattern, between_text, re.IGNORECASE):
                                    continue

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

                # 3c-2b: Standalone Compound Passive Voice Agreement Sanitizer (Filar CLXXXV - 0.00 PLN)
                # Harmonizes corrupted auxiliary/participle gender mismatches regardless of explicit subject tag.
                # 1. została + [optional adverb] + masc participle (-ny/-ty) [i/oraz masc participle] -> został + participles
                def _fix_masc_passive_hybrid(m):
                    prefix = m.group(1)
                    aux = m.group(2)
                    adv = m.group(3) or ""
                    p1 = m.group(4)
                    conj = m.group(5) or ""
                    repl_aux = "Został" if aux[0].isupper() else "został"
                    adv_str = f"{adv} " if adv else ""
                    orig_full = f"{aux} {adv_str}{p1}{conj}".strip()
                    repl_full = f"{repl_aux} {adv_str}{p1}{conj}".strip()
                    fixes.append(
                        f"[Episode Quality Gate - Filar CLXXXV Zgoda Imiesłowowa] Linia #{i+1}: "
                        f"zharmonizowano stronę bierną '{orig_full}' -> '{repl_full}'"
                    )
                    return f"{prefix}{repl_aux} {adv_str}{p1}{conj}"

                ev.text = re.sub(
                    r"(^|[^\w]|\\[Nnh])\b([Zz]ostała)\s+(?:([A-Za-ząćęłńóśźż]+(?:nie|o))\s+)?([A-Za-ząćęłńóśźż]+(?:ny|ty))(\s+(?:i|oraz)\s+[A-Za-ząćęłńóśźż]+(?:ny|ty))?\b",
                    _fix_masc_passive_hybrid,
                    ev.text
                )

                # 2. został + [optional adverb] + fem participle (-na/-ta) [i/oraz fem participle] -> została + participles
                def _fix_fem_passive_hybrid(m):
                    prefix = m.group(1)
                    aux = m.group(2)
                    adv = m.group(3) or ""
                    p1 = m.group(4)
                    conj = m.group(5) or ""
                    repl_aux = "Została" if aux[0].isupper() else "została"
                    adv_str = f"{adv} " if adv else ""
                    orig_full = f"{aux} {adv_str}{p1}{conj}".strip()
                    repl_full = f"{repl_aux} {adv_str}{p1}{conj}".strip()
                    fixes.append(
                        f"[Episode Quality Gate - Filar CLXXXV Zgoda Imiesłowowa] Linia #{i+1}: "
                        f"zharmonizowano stronę bierną '{orig_full}' -> '{repl_full}'"
                    )
                    return f"{prefix}{repl_aux} {adv_str}{p1}{conj}"

                ev.text = re.sub(
                    r"(^|[^\w]|\\[Nnh])\b([Zz]ostał)\s+(?:([A-Za-ząćęłńóśźż]+(?:nie|o))\s+)?([A-Za-ząćęłńóśźż]+(?:na|ta))(\s+(?:i|oraz)\s+[A-Za-ząćęłńóśźż]+(?:na|ta))?\b",
                    _fix_fem_passive_hybrid,
                    ev.text
                )

            # 3c-3. 2ND-PERSON PLURAL ADDRESSEE GROUP AGREEMENT (Filar CLXIII - 0.00 PLN)
            if not is_sign:
                raw_ev_addressee = getattr(ev, "addressee", None) or (line_addressees.get(i) if line_addressees else None)
                addr_norm = (raw_ev_addressee or "").strip().lower()

                clean_ev_text = re.sub(r"\{[^\}]*\}", "", ev.text)
                has_female_vocative = bool(re.search(r"\b(dziewczęta|dziewczyny|panie|kobiety|siostry|uczennice|kapłanki)[!,\?]", clean_ev_text, re.IGNORECASE))
                has_male_vocative = bool(re.search(r"\b(chłopaki|panowie|mężczyźni|żołnierze|bracia|chłopcy)[!,\?]", clean_ev_text, re.IGNORECASE))

                if not has_female_vocative and not has_male_vocative and prev_ev:
                    prev_spk = getattr(prev_ev, "name", "") or ""
                    curr_spk = getattr(ev, "name", "") or ""
                    if (prev_spk == curr_spk or not prev_spk or not curr_spk) and (ev.start - prev_ev.end < 3500):
                        prev_clean_t = re.sub(r"\{[^\}]*\}", "", prev_ev.text or "").strip()
                        if re.search(r"\b(dziewczęta|dziewczyny|panie|kobiety|siostry|uczennice|kapłanki)[!,\?]", prev_clean_t, re.IGNORECASE):
                            has_female_vocative = True
                        elif re.search(r"\b(chłopaki|panowie|mężczyźni|żołnierze|bracia|chłopcy)[!,\?]", prev_clean_t, re.IGNORECASE):
                            has_male_vocative = True

                is_female_dual = bool(re.search(r"\b(kobieta_dual|dwie\s+kobiety|obie|kobiety\s*\(dual\))\b", addr_norm)) or ("obie" in clean_ev_text.lower() and bool(re.search(r"\b(dziewczęta|dziewczyny|siostry|kobiety)\b", clean_ev_text, re.IGNORECASE)))
                is_male_dual = bool(re.search(r"\b(mężczyzna_dual|dwóch\s+mężczyzn|dwaj\s+mężczyźni|obaj)\b", addr_norm))
                is_mixed_dual = bool(re.search(r"\b(para_mieszana_dual|para\s+mieszana|oboje)\b", addr_norm))

                is_female_group = ("grupa_kobiet" in addr_norm or "grupa kobiet" in addr_norm or is_female_dual) or has_female_vocative
                is_male_group = ("grupa_mężczyzn" in addr_norm or "grupa mężczyzn" in addr_norm or is_male_dual) or has_male_vocative
                is_mixed_group = ("grupa_mieszana" in addr_norm or "grupa mieszana" in addr_norm or is_mixed_dual)

                if is_female_dual:
                    if re.search(r"\b(obaj|oboje)\b", ev.text, re.IGNORECASE):
                        def _repl_dual_f(m):
                            return "Obie" if m.group(1)[0].isupper() else "obie"
                        ev.text = re.sub(r"\b(obaj|oboje)\b", _repl_dual_f, ev.text, flags=re.IGNORECASE)
                        fixes.append(f"[Episode Quality Gate - Filar CLXIII Dualis Żeński] Linia #{i+1}: zharmonizowano formę dualną na 'obie' (adresat: dwie kobiety)")
                elif is_male_dual:
                    if re.search(r"\b(obie|oboje)\b", ev.text, re.IGNORECASE):
                        def _repl_dual_m(m):
                            return "Obaj" if m.group(1)[0].isupper() else "obaj"
                        ev.text = re.sub(r"\b(obie|oboje)\b", _repl_dual_m, ev.text, flags=re.IGNORECASE)
                        fixes.append(f"[Episode Quality Gate - Filar CLXIII Dualis Męski] Linia #{i+1}: zharmonizowano formę dualną na 'obaj' (adresat: dwóch mężczyzn)")
                elif is_mixed_dual:
                    if re.search(r"\b(obie|obaj)\b", ev.text, re.IGNORECASE):
                        def _repl_dual_mx(m):
                            return "Oboje" if m.group(1)[0].isupper() else "oboje"
                        ev.text = re.sub(r"\b(obie|obaj)\b", _repl_dual_mx, ev.text, flags=re.IGNORECASE)
                        fixes.append(f"[Episode Quality Gate - Filar CLXIII Dualis Mieszany] Linia #{i+1}: zharmonizowano formę dualną na 'oboje' (adresat: para mieszana)")

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

                    # 3. Predicate nouns in instrumental plural for female groups
                    has_2pl_copula_f = bool(re.search(r"\b(?:jesteście|będziecie|byłyście|byliście|zostałyście|zostaliście|bądźcie)\b", ev.text, re.IGNORECASE))
                    if has_2pl_copula_f:
                        for m_n, f_n in PREDICATE_NOUNS_PLURAL_INSTRUMENTAL_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn = rf"((?:\b(?:jesteście|będziecie|byłyście|byliście|zostałyście|zostaliście|bądźcie)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:[A-Za-ząćęłńóśźż]+(?:ymi|imi)|moimi|twoimi|naszymi|waszymi|ich|swoimi)\s+){{0,3}})({re.escape(m_n)})\b"
                            for m in list(re.finditer(pat_pn, ev.text, re.IGNORECASE)):
                                pref = m.group(1)
                                old_n = m.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:[A-Za-ząćęłńóśźż]+\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = f_n.capitalize() if old_n[0].isupper() else f_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Rzeczownik Orzecznikowy Niemęskoosobowy lm.] Linia #{i+1}: skorygowano '{old_n}' -> '{repl_n}' (adresat: grupa kobiet)")

                    # 4. Predicate nouns in nominative plural for female groups
                    has_2pl_nom_copula_f = bool(re.search(r"\b(?:jesteście|będziecie|byłyście|byliście|zostałyście|zostaliście|to\s+są|to)\b", ev.text, re.IGNORECASE))
                    if has_2pl_nom_copula_f:
                        mods_m_nom_pl_pat = "|".join([m for m, f in PREDICATE_MODS_PLURAL_NOMINATIVE])
                        mods_f_nom_pl_pat = "|".join([f for m, f in PREDICATE_MODS_PLURAL_NOMINATIVE])
                        all_mods_nom_pl_pat = f"{mods_m_nom_pl_pat}|{mods_f_nom_pl_pat}"
                        fem_all_nouns_nom_pl_pat = "|".join([f for m, f in PREDICATE_NOUNS_PLURAL_NOMINATIVE_PAIRS if m != f])
                        for m_n, f_n in PREDICATE_NOUNS_PLURAL_NOMINATIVE_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn_nom = rf"((?:\b(?:jesteście|będziecie|byłyście|byliście|zostałyście|zostaliście|to\s+są|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_m_nom_pl_pat})\s+){{0,3}})({re.escape(m_n)})\b"
                            for m in list(re.finditer(pat_pn_nom, ev.text, re.IGNORECASE)):
                                pref = m.group(1)
                                old_n = m.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_nom_pl_pat})\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = f_n.capitalize() if old_n[0].isupper() else f_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Mianownik Orzecznikowy Niemęskoosobowy lm.] Linia #{i+1}: skorygowano '{old_n}' -> '{repl_n}' (adresat: grupa kobiet)")
                        for m_mod, f_mod in PREDICATE_MODS_PLURAL_NOMINATIVE:
                            pat_mod_nom = rf"((?:\b(?:jesteście|będziecie|byłyście|byliście|zostałyście|zostaliście|to\s+są|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_nom_pl_pat})\s+){{0,2}})({re.escape(m_mod)})(\s+(?:(?:{all_mods_nom_pl_pat})\s+)*(?:{fem_all_nouns_nom_pl_pat}))\b"
                            ev.text = re.sub(pat_mod_nom, rf"\g<1>{f_mod}\g<3>", ev.text, flags=re.IGNORECASE)

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

                    # 3. Predicate nouns in instrumental plural for male groups
                    has_2pl_copula_m = bool(re.search(r"\b(?:jesteście|będziecie|byliście|byłyście|zostaliście|zostałyście|bądźcie)\b", ev.text, re.IGNORECASE))
                    if has_2pl_copula_m:
                        for m_n, f_n in PREDICATE_NOUNS_PLURAL_INSTRUMENTAL_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn = rf"((?:\b(?:jesteście|będziecie|byliście|byłyście|zostaliście|zostałyście|bądźcie)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:[A-Za-ząćęłńóśźż]+(?:ymi|imi)|moimi|twoimi|naszymi|waszymi|ich|swoimi)\s+){{0,3}})({re.escape(f_n)})\b"
                            for m in list(re.finditer(pat_pn, ev.text, re.IGNORECASE)):
                                pref = m.group(1)
                                old_n = m.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:[A-Za-ząćęłńóśźż]+\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = m_n.capitalize() if old_n[0].isupper() else m_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Rzeczownik Orzecznikowy Męskoosobowy lm.] Linia #{i+1}: skorygowano '{old_n}' -> '{repl_n}' (adresat: grupa mężczyzn)")

                    # 4. Predicate nouns in nominative plural for male groups
                    has_2pl_nom_copula_m = bool(re.search(r"\b(?:jesteście|będziecie|byliście|byłyście|zostaliście|zostałyście|to\s+są|to)\b", ev.text, re.IGNORECASE))
                    if has_2pl_nom_copula_m:
                        mods_m_nom_pl_pat = "|".join([m for m, f in PREDICATE_MODS_PLURAL_NOMINATIVE])
                        mods_f_nom_pl_pat = "|".join([f for m, f in PREDICATE_MODS_PLURAL_NOMINATIVE])
                        all_mods_nom_pl_pat = f"{mods_m_nom_pl_pat}|{mods_f_nom_pl_pat}"
                        masc_all_nouns_nom_pl_pat = "|".join([m for m, f in PREDICATE_NOUNS_PLURAL_NOMINATIVE_PAIRS if m != f])
                        for m_n, f_n in PREDICATE_NOUNS_PLURAL_NOMINATIVE_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn_nom = rf"((?:\b(?:jesteście|będziecie|byliście|byłyście|zostaliście|zostałyście|to\s+są|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_f_nom_pl_pat})\s+){{0,3}})({re.escape(f_n)})\b"
                            for m in list(re.finditer(pat_pn_nom, ev.text, re.IGNORECASE)):
                                pref = m.group(1)
                                old_n = m.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_nom_pl_pat})\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = m_n.capitalize() if old_n[0].isupper() else m_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Mianownik Orzecznikowy Męskoosobowy lm.] Linia #{i+1}: skorygowano '{old_n}' -> '{repl_n}' (adresat: grupa mężczyzn)")
                        for m_mod, f_mod in PREDICATE_MODS_PLURAL_NOMINATIVE:
                            pat_mod_nom = rf"((?:\b(?:jesteście|będziecie|byliście|byłyście|zostaliście|zostałyście|to\s+są|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_nom_pl_pat})\s+){{0,2}})({re.escape(f_mod)})(\s+(?:(?:{all_mods_nom_pl_pat})\s+)*(?:{masc_all_nouns_nom_pl_pat}))\b"
                            ev.text = re.sub(pat_mod_nom, rf"\g<1>{m_mod}\g<3>", ev.text, flags=re.IGNORECASE)

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
                        checked_addr_bible = False
                        if series_bible and hasattr(series_bible, "audit_speaker_metadata_against_audio") and cand_addr_name:
                            _, is_cont_addr = series_bible.audit_speaker_metadata_against_audio(cand_addr_name, scene_gender=event_scene_gender.get(i))
                            checked_addr_bible = True
                        if is_cont_addr:
                            is_single_female = True
                            is_single_male = False
                        elif not checked_addr_bible and not cand_addr_name and event_scene_gender.get(i) == "FEMALE":
                            is_single_female = True
                            is_single_male = False
                        else:
                            is_single_male = True
                    else:
                        # Check character vocative in line
                        if character_registry:
                            for cname, cdesc in character_registry.items():
                                if len(cname) >= 3 and re.search(rf"\b{re.escape(cname)}[!,\?]", clean_ev_text, re.IGNORECASE):
                                    if isinstance(cdesc, dict):
                                        c_gender = str(cdesc.get("gender", "")).upper()
                                        c_desc = str(cdesc.get("description", "") or cdesc.get("role", "")).lower()
                                        if c_gender == "FEMALE" or any(k in c_desc for k in ["kobieta", "female", "dziewczyn", "nauczycielka", "uczennica", "kapłanka"]):
                                            is_single_female = True
                                            break
                                        elif c_gender == "MALE" or any(k in c_desc for k in ["mężczyzna", "male", "chłopak", "żołnierz", "rycerz"]):
                                            is_single_male = True
                                            break
                                    else:
                                        cdesc_l = str(cdesc).lower()
                                        if any(k in cdesc_l for k in ["kobieta", "female", "dziewczyn", "nauczycielka", "uczennica", "kapłanka"]):
                                            is_single_female = True
                                            break
                                        elif any(k in cdesc_l for k in ["mężczyzna", "male", "chłopak", "żołnierz", "rycerz"]):
                                            is_single_male = True
                                            break
                        if not is_single_female and not is_single_male:
                            if re.search(r"\b(dziewczyno|kobieto|panienko|siostro|mamo|dziewczynko|mała|córeczko)[!,\?]", clean_ev_text, re.IGNORECASE):
                                is_single_female = True
                            elif re.search(r"\b(chłopcze|młodzieńcze|bracie|ojcze|tato|maluchu|synku)[!,\?]", clean_ev_text, re.IGNORECASE):
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

                    partner_gender = None
                    # Dyadic Interlocutor Gender Concordance Gate (Filar CLXXXVI & CLXIII - 0.00 PLN)
                    # In 1-on-1 dialogue, identify the direct conversational partner within temporal proximity
                    if not is_single_female and not is_single_male:
                        curr_spk_raw = getattr(ev, "name", None) or getattr(ev, "actor", None) or (line_speakers.get(i) if line_speakers else None) or ""
                        curr_spk_clean = extract_clean_speaker_name(str(curr_spk_raw)).strip()

                        # Detect Scene Topology: Soliloquy (N=1) or Polylogue (N>=3)
                        nearby_active_speakers = set()
                        for win_idx in range(max(0, i - 6), min(len(events), i + 7)):
                            win_ev = events[win_idx]
                            if abs(getattr(win_ev, "start", 0) - getattr(ev, "start", 0)) <= 12000:
                                win_spk = getattr(win_ev, "name", None) or getattr(win_ev, "actor", None) or (line_speakers.get(win_idx) if line_speakers else None) or ""
                                win_spk_cl = extract_clean_speaker_name(str(win_spk)).strip()
                                if win_spk_cl and not is_generic_actor_or_category(win_spk_cl):
                                    nearby_active_speakers.add(win_spk_cl.lower())
                        is_polylogue = (len(nearby_active_speakers) >= 3)
                        is_soliloquy = bool(
                            re.search(r"\{\\i1\}", ev.text) or
                            "italic" in (getattr(ev, "style", "") or "").lower() or
                            (len(nearby_active_speakers) <= 1 and not re.search(r"[,\?!]\s*(?:ty|ciebie|cię|tobie|twoje|twój)\b", clean_ev_text, re.IGNORECASE))
                        )

                        if not is_soliloquy:
                            # Scan backwards up to 4 events (within 3.8s) for the interlocutor
                            for b_off in range(1, min(5, i + 1)):
                                prev_ev = events[i - b_off]
                                p_spk_raw = getattr(prev_ev, "name", None) or getattr(prev_ev, "actor", None) or (line_speakers.get(i - b_off) if line_speakers else None) or ""
                                p_spk_clean = extract_clean_speaker_name(str(p_spk_raw)).strip()
                                if abs(getattr(ev, "start", 0) - getattr(prev_ev, "end", 0)) >= 3800:
                                    break
                                if is_polylogue:
                                    has_prev_voc = bool(p_spk_clean and re.search(rf"\b{re.escape(p_spk_clean)}[!,\?]", clean_ev_text, re.IGNORECASE))
                                    if not has_prev_voc and not raw_ev_addressee:
                                        continue
                                if p_spk_clean and p_spk_clean.lower() != curr_spk_clean.lower():
                                    p_gen = char_gender_map.get(p_spk_clean.lower()) or resolve_actor_gender(p_spk_clean, character_registry, series_bible)
                                    if series_bible and hasattr(series_bible, "audit_speaker_metadata_against_audio"):
                                        aud_g, is_cont = series_bible.audit_speaker_metadata_against_audio(p_spk_clean, scene_gender=event_scene_gender.get(i - b_off) or event_scene_gender.get(i))
                                        if is_cont and aud_g in ("MALE", "FEMALE"):
                                            p_gen = aud_g
                                    if p_gen in ("MALE", "FEMALE"):
                                        partner_gender = p_gen
                                        break
                                    prev_txt = getattr(prev_ev, "text", "")
                                    if re.search(r"\b[A-Za-ząćęłńóśźż]+łem\b", prev_txt) and not re.search(r"\b[A-Za-ząćęłńóśźż]+łam\b", prev_txt):
                                        partner_gender = "MALE"
                                        break
                                    elif re.search(r"\b[A-Za-ząćęłńóśźż]+łam\b", prev_txt) and not re.search(r"\b[A-Za-ząćęłńóśźż]+łem\b", prev_txt):
                                        partner_gender = "FEMALE"
                                        break

                            # If not found backwards, scan forward up to 3 events (within 3.8s) for the responding interlocutor
                            if not partner_gender:
                                for f_off in range(1, min(4, len(events) - i)):
                                    next_ev = events[i + f_off]
                                    n_spk_raw = getattr(next_ev, "name", None) or getattr(next_ev, "actor", None) or (line_speakers.get(i + f_off) if line_speakers else None) or ""
                                    n_spk_clean = extract_clean_speaker_name(str(n_spk_raw)).strip()
                                    if abs(getattr(next_ev, "start", 0) - getattr(ev, "end", 0)) >= 3800:
                                        break
                                    if is_polylogue:
                                        has_next_voc = bool(n_spk_clean and re.search(rf"\b{re.escape(n_spk_clean)}[!,\?]", clean_ev_text, re.IGNORECASE))
                                        if not has_next_voc and not raw_ev_addressee:
                                            continue
                                    if n_spk_clean and n_spk_clean.lower() != curr_spk_clean.lower():
                                        n_gen = char_gender_map.get(n_spk_clean.lower()) or resolve_actor_gender(n_spk_clean, character_registry, series_bible)
                                        if series_bible and hasattr(series_bible, "audit_speaker_metadata_against_audio"):
                                            aud_g, is_cont = series_bible.audit_speaker_metadata_against_audio(n_spk_clean, scene_gender=event_scene_gender.get(i + f_off) or event_scene_gender.get(i))
                                            if is_cont and aud_g in ("MALE", "FEMALE"):
                                                n_gen = aud_g
                                        if n_gen in ("MALE", "FEMALE"):
                                            partner_gender = n_gen
                                            break
                                        next_txt = getattr(next_ev, "text", "")
                                        if re.search(r"\b[A-Za-ząćęłńóśźż]+łem\b", next_txt) and not re.search(r"\b[A-Za-ząćęłńóśźż]+łam\b", next_txt):
                                            partner_gender = "MALE"
                                            break
                                        elif re.search(r"\b[A-Za-ząćęłńóśźż]+łam\b", next_txt) and not re.search(r"\b[A-Za-ząćęłńóśźż]+łem\b", next_txt):
                                            partner_gender = "FEMALE"
                                            break

                            # If strictly dyadic scene (N=2 named interlocutors in contiguous cluster without montage cut >= 3800ms),
                            # the partner is uniquely determined
                            if not partner_gender:
                                contiguous_cluster_speakers = set()
                                if curr_spk_clean and not is_generic_actor_or_category(curr_spk_clean):
                                    contiguous_cluster_speakers.add(curr_spk_clean.lower())
                                for b_idx in range(i - 1, max(-1, i - 7), -1):
                                    if abs(getattr(events[b_idx + 1], "start", 0) - getattr(events[b_idx], "end", 0)) >= 3800:
                                        break
                                    b_spk = getattr(events[b_idx], "name", None) or getattr(events[b_idx], "actor", None) or (line_speakers.get(b_idx) if line_speakers else None) or ""
                                    b_cl = extract_clean_speaker_name(str(b_spk)).strip()
                                    if b_cl and not is_generic_actor_or_category(b_cl):
                                        contiguous_cluster_speakers.add(b_cl.lower())
                                for f_idx in range(i + 1, min(len(events), i + 7)):
                                    if abs(getattr(events[f_idx], "start", 0) - getattr(events[f_idx - 1], "end", 0)) >= 3800:
                                        break
                                    f_spk = getattr(events[f_idx], "name", None) or getattr(events[f_idx], "actor", None) or (line_speakers.get(f_idx) if line_speakers else None) or ""
                                    f_cl = extract_clean_speaker_name(str(f_spk)).strip()
                                    if f_cl and not is_generic_actor_or_category(f_cl):
                                        contiguous_cluster_speakers.add(f_cl.lower())

                                if len(contiguous_cluster_speakers) == 2:
                                    other_speakers = [s for s in contiguous_cluster_speakers if s != curr_spk_clean.lower()]
                                    if len(other_speakers) == 1:
                                        other_spk = other_speakers[0]
                                        o_gen = char_gender_map.get(other_spk) or resolve_actor_gender(other_spk, character_registry, series_bible)
                                        if series_bible and hasattr(series_bible, "audit_speaker_metadata_against_audio"):
                                            aud_g, is_cont = series_bible.audit_speaker_metadata_against_audio(other_spk, scene_gender=event_scene_gender.get(i))
                                            if is_cont and aud_g in ("MALE", "FEMALE"):
                                                o_gen = aud_g
                                        if o_gen in ("MALE", "FEMALE"):
                                            partner_gender = o_gen

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
                                if series_bible and hasattr(series_bible, "audit_speaker_metadata_against_audio"):
                                    aud_g, is_cont = series_bible.audit_speaker_metadata_against_audio(spk_cand, scene_gender=event_scene_gender.get(i))
                                    if is_cont and aud_g in ("MALE", "FEMALE"):
                                        cand_g = aud_g
                                if cand_g != "FEMALE":
                                    all_females = False
                                if cand_g != "MALE":
                                    all_males = False
                            if all_females and len(nearby_speakers) >= 2:
                                scene_cast_female_only = True
                            elif all_males and len(nearby_speakers) >= 2:
                                scene_cast_male_only = True

                    is_confirmed_single = (is_single_female or is_single_male or (partner_gender in ("MALE", "FEMALE"))) and not (is_female_group or is_male_group or is_mixed_group)

                    # Dyadic Addressee Number Concordance Gate (Filar CLXIII - 0.00 PLN)
                    # Harmonize leaking 2nd-person plural forms into confirmed dyadic dialogue (Taxonomy K1-K6 + Prepositional & Verbal Extensions)
                    if is_confirmed_single:
                        src_text = ""
                        if source_subs and hasattr(source_subs, "events") and i < len(source_subs.events):
                            src_text = getattr(source_subs.events[i], "plaintext", None) or getattr(source_subs.events[i], "text", "") or ""

                        has_explicit_plural = bool(re.search(
                            r"\b(wszyscy|wszystkie|wszystkim|wszystkich|kochani|panowie|panie|dziewczęta|chłopcy|ludzie|zebrani|przyjaciele|rodzice|państwo|dwie|dwaj|dwa|dwóch|dwu|dwom|dwoma|dwiema|dwoje|dwojga|dwojgu|dwojgiem|troje|trojga|trojgu|trojgiem|trzej|trzy|trzech|trzem|trzema|czworo|czworga|czworgu|czworgiem|czterej|cztery|czterech|czterem|czterema|oboje|obojga|obojgu|obojgiem|obie|obaj|obu|obydwoje|obydwie|obydwaj|obydwu|arystokraci|rebelianci|wrogowie|najeźdźcy|potwory|demony|obcy)\b",
                            clean_ev_text, re.IGNORECASE
                        )) or bool(re.search(
                            r"\b(everyone|everybody|guys|all of you|both of you|you two|you three|two of you|three of you|team|class|ladies and gentlemen|minna|tachi|zen'in|shokun|omae-ra|kisama-ra|futari|sannin|your kind|your people|the likes of you|you people|you lot|you guys)\b",
                            src_text, re.IGNORECASE
                        )) or bool(re.search(
                            rf"\b(?:wy\s+i\s+(?:wasz|wasza|wasze)|wy,?\s+(?:[a-ząćęłńóśźż]+\s+)?(?:arystokraci|rebelianci|wrogowie|najeźdźcy|potwory|demony|obcy|[a-ząćęłńóśźż]+(?:owie|y|i|e))|wy\s+(?:z\s+)?{INSTITUTIONAL_COLLECTIVE_NOUNS_PATTERN})\b",
                            clean_ev_text, re.IGNORECASE
                        ))

                        if not has_explicit_plural:
                            old_dyadic_t = ev.text
                            # K1: Wyjaśnienia i deklaracje relacyjne (opowiem/powiem/wyjaśnię wam -> ci)
                            # Strictly single-token mutation: modifies only 'wam'/'Wam', leaving prefix and verbs 100% untouched
                            ev.text = re.sub(
                                r"\b((?:zaraz\s+wszystko|wszystko|to\s+wszystko|zaraz|już|chętnie)\s+)?(wam|Wam)(\s+(?:to\s+)?(?:opowiem|powiem|wyjaśnię|zdradzę|pokażę|nakreślę|wytłumaczę))\b",
                                lambda m: f"{m.group(1) or ''}{'Ci' if m.group(2)[0].isupper() else 'ci'}{m.group(3)}",
                                ev.text,
                                flags=re.IGNORECASE
                            )
                            ev.text = re.sub(
                                r"\b((?:opowiem|powiem|wyjaśnię|zdradzę|pokażę|nakreślę|wytłumaczę)\s+)(wam|Wam)\b",
                                lambda m: f"{m.group(1)}{'Ci' if m.group(2)[0].isupper() else 'ci'}",
                                ev.text,
                                flags=re.IGNORECASE
                            )

                            # K2: Zwroty wdzięczności i zależności (dzięki wam -> dzięki tobie)
                            # Strictly single-token mutation: 'dzięki' is untouched, only 'wam' changes
                            ev.text = re.sub(
                                r"\b([Dd]zięki\s+)(wam|Wam)\b",
                                lambda m: f"{m.group(1)}{'Tobie' if m.group(2)[0].isupper() else 'tobie'}",
                                ev.text
                            )

                            # K3: Konstrukcje afektywne i celownikowe (na was mi zależy -> na tobie mi zależy, wam zależy -> tobie zależy)
                            # Strictly single-token mutation: modifies only 'wam'/'was', preserving all neighboring words
                            ev.text = re.sub(
                                r"\b(Wam|wam)(\s+(?:na\s+tym\s+)?zależy)\b",
                                lambda m: f"{'Tobie' if m.group(1)[0].isupper() else 'tobie'}{m.group(2)}",
                                ev.text
                            )
                            ev.text = re.sub(
                                r"\b([Nn]a\s+)(was|Was)(\s+(?:mi\s+)?zależy)\b",
                                lambda m: f"{m.group(1)}{'Tobie' if m.group(2)[0].isupper() else 'tobie'}{m.group(3)}",
                                ev.text
                            )
                            ev.text = re.sub(r"\b(zależy\s+)(wam|Wam)\b", lambda m: f"{m.group(1)}{'Ci' if m.group(2)[0].isupper() else 'ci'}", ev.text, flags=re.IGNORECASE)
                            ev.text = re.sub(r"\b((?:ufałem|ufałam|wierzyłem|wierzyłam)\s+)(wam|Wam)\b", lambda m: f"{m.group(1)}{'Tobie' if m.group(2)[0].isupper() else 'tobie'}", ev.text, flags=re.IGNORECASE)

                            # K4: Zwroty modalne i zobowiązania (muszę/chcę was prosić -> muszę/chcę cię prosić, błagam was -> błagam cię)
                            # Strictly single-token mutation: modifies only 'was' -> 'cię'
                            ev.text = re.sub(r"\b((?:muszę|chcę|pragnę)\s+)(was|Was)(\s+(?:o\s+coś\s+)?(?:prosić|poprosić))\b", lambda m: f"{m.group(1)}{'Cię' if m.group(2)[0].isupper() else 'cię'}{m.group(3)}", ev.text, flags=re.IGNORECASE)
                            ev.text = re.sub(r"\b((?:błagam|proszę|przepraszam)\s+)(was|Was)\b", lambda m: f"{m.group(1)}{'Cię' if m.group(2)[0].isupper() else 'cię'}", ev.text, flags=re.IGNORECASE)

                            # K5: Dyrektywy deeskalacyjne / imperatywy (uspokójcie się -> uspokój się, posłuchajcie mnie -> posłuchaj mnie)
                            ev.text = re.sub(r"\b(uspokój)cie(\s+się)\b", r"\1\2", ev.text, flags=re.IGNORECASE)
                            ev.text = re.sub(r"\b(posłuchaj)cie(\s+mnie)\b", r"\1\2", ev.text, flags=re.IGNORECASE)
                            ev.text = re.sub(r"\b(spójrz)cie(\s+na\s+mnie)\b", r"\1\2", ev.text, flags=re.IGNORECASE)
                            ev.text = re.sub(r"\b(wybacz)cie(\s+mi)\b", r"\1\2", ev.text, flags=re.IGNORECASE)
                            ev.text = re.sub(r"\b(poczekaj|czekaj|zaczekaj)cie(\s+(?:chwilę|chwileczkę|moment|sekundę|na\s+mnie))\b", r"\1\2", ev.text, flags=re.IGNORECASE)

                            # K6 & Rozszerzenia przyimkowe (Prepositional Plural Harmonization - Zasada 15 AGENTS.md)
                            # All Genitive & Accusative prepositions + was -> ciebie
                            ev.text = re.sub(
                                r"\b([Dd]o|[Oo]d|[Uu]|[Dd]la|[Oo]|[Bb]ez|[Pp]rzez|[Pp]rzeze|[Ww]|[Ww]e|[Nn]a|[Kk]oło|[Oo]bok|[Bb]lisko|[Ww]okół|[Dd]ookoła|[Pp]ośród|[Ww]śród|[Ss]pod|[Zz]za|[Zz]nad|[Ww]zdłuż|[Pp]odczas|[Mm]imo|[Ww]edług|[Ww]skutek|[Ww]obec|[Nn]aprzeciw)(\s+)(was|Was)\b",
                                lambda m: f"{m.group(1)}{m.group(2)}{'Ciebie' if m.group(3)[0].isupper() else 'ciebie'}",
                                ev.text
                            )
                            # All Instrumental prepositions + wami -> tobą
                            ev.text = re.sub(
                                r"\b([Zz]|[Zz]e|[Zz]a|[Pp]rzed|[Pp]rzede|[Nn]ad|[Nn]ade|[Pp]od|[Pp]ode|[Mm]iędzy|[Pp]omiędzy|[Pp]oza)(\s+)(wami|Wami)\b",
                                lambda m: f"{m.group(1)}{m.group(2)}{'Tobą' if m.group(3)[0].isupper() else 'tobą'}",
                                ev.text
                            )
                            # All Dative prepositions + wam -> tobie
                            ev.text = re.sub(
                                r"\b([Dd]zięki|[Pp]rzeciw(?:ko)?|[Kk]u|[Ww]brew)(\s+)(wam|Wam)\b",
                                lambda m: f"{m.group(1)}{m.group(2)}{'Tobie' if m.group(3)[0].isupper() else 'tobie'}",
                                ev.text
                            )
                            # All Locative prepositions + was -> tobie (po was -> po tobie, przy was -> przy tobie)
                            ev.text = re.sub(
                                r"\b([Pp]o|[Pp]rzy)(\s+)(was|Was)\b",
                                lambda m: f"{m.group(1)}{m.group(2)}{'Tobie' if m.group(3)[0].isupper() else 'tobie'}",
                                ev.text
                            )

                            # Verb + wam -> ci (dative) across dialogue verbs
                            ev.text = re.sub(
                                r"\b(dam|daję|dałem|dałam|mówię|mówiłem|mówiłam|powiedziałem|powiedziałam|pomogę|pomagałem|pomagałam|radzę|poradziłem|poradziłam|życzę|obiecuję|obiecałem|obiecałam|przysięgam|przysięgłem|przysięgłam|przyniosę|przyniosłem|przyniosłam|zazdroszczę|dziękuję|podziękowałem|podziękowałam|współczuję|pozwolę|odpowiem|odpowiedziałem|odpowiedziałam)(\s+)(wam|Wam)\b",
                                lambda m: f"{m.group(1)}{m.group(2)}{'Ci' if m.group(3)[0].isupper() else 'ci'}",
                                ev.text,
                                flags=re.IGNORECASE
                            )
                            # General modal / auxiliary + wam -> ci
                            ev.text = re.sub(
                                r"\b(chcę|muszę|mogę|pragnę|zamierzam)(\s+)(wam|Wam)\b",
                                lambda m: f"{m.group(1)}{m.group(2)}{'Ci' if m.group(3)[0].isupper() else 'ci'}",
                                ev.text,
                                flags=re.IGNORECASE
                            )
                            # Inquiries: co wam (jest/dolega) -> co ci (jest/dolega)
                            ev.text = re.sub(r"\b([Cc]o|[Ww]\s+czym)(\s+)(wam|Wam)\b", lambda m: f"{m.group(1)}{m.group(2)}{'Ci' if m.group(3)[0].isupper() else 'ci'}", ev.text)

                            # Accusative verbs + was -> cię
                            ev.text = re.sub(
                                r"\b(widzę|widziałem|widziałam|znam|znałem|znałam|kocham|kochałem|kochałam|lubię|lubiłem|lubiłam|uratuję|uratowałem|uratowałam|ocalę|ocaliłem|ocaliłam|zostawię|zostawiłem|zostawiłam|znajdę|znalazłem|znalazłam|słyszę|słyszałem|słyszałam|zabiję|zabijam)(\s+)(was|Was)\b",
                                lambda m: f"{m.group(1)}{m.group(2)}{'Cię' if m.group(3)[0].isupper() else 'cię'}",
                                ev.text,
                                flags=re.IGNORECASE
                            )

                            # Nominative / Vocative wy -> ty (preserve explicit plural numerals and groups)
                            ev.text = re.sub(r"\b([Aa]\s+)(wy)(?!\s+(?:dwie|dwaj|dwa|dwóch|dwu|dwoje|troje|trzej|trzy|trzech|czworo|czterej|cztery|czterech|oboje|obie|obaj|obu|obydwie|obydwaj|obydwu|wszyscy|wszystkie|razem))\b", r"\g<1>ty", ev.text)
                            ev.text = re.sub(r"\b([Cc]o\s+)(wy)(\s+na\s+to)\b", r"\g<1>ty\g<3>", ev.text)

                            # Initial Wam to -> Ci to (Test 89 case: Wam to powiem -> Ci to powiem)
                            ev.text = re.sub(r"\b(Wam)(\s+to)\b", r"Ci\g<2>", ev.text)

                            if ev.text != old_dyadic_t:
                                clean_ev_text = re.sub(r"\{[^\}]*\}", "", ev.text)
                                fixes.append(
                                    f"[Episode Quality Gate - Filar CLXIII Zgodność Liczby w Relacji Diadycznej] Linia #{i+1}: "
                                    f"zharmonizowano formę 2. os. l. mn. -> l. poj. w dialogu 1-na-1: '{old_dyadic_t}' -> '{ev.text}'"
                                )

                    # K7: Zaimki dzierżawcze w relacji 1-na-1 (wasz/wasza/wasze -> twój/twoja/twoje) z ochroną rzeczowników zbiorowych
                    is_dyadic_poss = (is_confirmed_single or (partner_gender in ("MALE", "FEMALE"))) and not (is_female_group or is_male_group or is_mixed_group)
                    if is_dyadic_poss:
                        src_text_poss = ""
                        if source_subs and hasattr(source_subs, "events") and i < len(source_subs.events):
                            src_text_poss = getattr(source_subs.events[i], "plaintext", None) or getattr(source_subs.events[i], "text", "") or ""

                        has_expl_pl_poss = bool(re.search(
                            r"\b(wszyscy|wszystkie|wszystkim|wszystkich|kochani|panowie|panie|dziewczęta|chłopcy|ludzie|zebrani|przyjaciele|rodzice|państwo|dwie|dwaj|dwa|dwóch|dwu|dwom|dwoma|dwiema|dwoje|dwojga|dwojgu|dwojgiem|troje|trojga|trojgu|trojgiem|trzej|trzy|trzech|trzem|trzema|czworo|czworga|czworgu|czworgiem|czterej|cztery|czterech|czterem|czterema|oboje|obojga|obojgu|obojgiem|obie|obaj|obu|obydwoje|obydwie|obydwaj|obydwu|arystokraci|rebelianci|wrogowie|najeźdźcy|potwory|demony|obcy)\b",
                            clean_ev_text, re.IGNORECASE
                        )) or bool(re.search(
                            r"\b(everyone|everybody|guys|all of you|both of you|you two|you three|two of you|three of you|team|class|ladies and gentlemen|minna|tachi|zen'in|shokun|omae-ra|kisama-ra|futari|sannin|your kind|your people|the likes of you|you people|you lot|you guys)\b",
                            src_text_poss, re.IGNORECASE
                        )) or bool(re.search(
                            rf"\b(?:wy\s+i\s+(?:wasz|wasza|wasze)|wy,?\s+(?:[a-ząćęłńóśźż]+\s+)?(?:arystokraci|rebelianci|wrogowie|najeźdźcy|potwory|demony|obcy|[a-ząćęłńóśźż]+(?:owie|y|i|e))|wy\s+(?:z\s+)?{INSTITUTIONAL_COLLECTIVE_NOUNS_PATTERN})\b",
                            clean_ev_text, re.IGNORECASE
                        )) or bool(re.search(
                            r"\b(?:jesteście|będziecie|macie|chcecie|wiecie|możecie|musicie|uważajcie|bądźcie|idźcie|powiedzcie|dajcie|pomóżcie|słuchajcie|chodźcie|patrzcie|zróbcie|weźcie|stańcie|poczekajcie|ratujcie|zostawcie|przestańcie|[A-Za-ząćęłńóśźż]+(?:liście|łyście|libyście|łybyście))\b",
                            clean_ev_text, re.IGNORECASE
                        ))

                        if not has_expl_pl_poss:
                            old_poss_t = ev.text
                            colls_pat = INSTITUTIONAL_COLLECTIVE_NOUNS_PATTERN
                            poss_pat = rf"\b([Ww]asz|[Ww]asza|[Ww]asze|[Ww]aszego|[Ww]aszej|[Ww]aszym|[Ww]aszą|[Ww]aszemu)\b(?!\s+{colls_pat}\b)"
                            def _repl_poss(m):
                                w = m.group(1)
                                is_cap = w[0].isupper()
                                mapping = {
                                    "wasz": "twój",
                                    "wasza": "twoja",
                                    "wasze": "twoje",
                                    "waszego": "twojego",
                                    "waszej": "twojej",
                                    "waszym": "twoim",
                                    "waszą": "twoją",
                                    "waszemu": "twojemu",
                                }
                                res = mapping.get(w.lower(), w.lower())
                                return res.capitalize() if is_cap else res

                            ev.text = re.sub(poss_pat, _repl_poss, ev.text)

                            # Prepositional pronouns in dyadic (1-on-1) relations: dla was -> dla ciebie, z wami -> z tobą, etc.
                            # Mutates strictly the pronoun token, preserving prepositions and separators in 100%
                            prep_poss_was_pat = rf"\b((?:dla|od|u|bez|do|koło|obok|blisko|wokół|dookoła|pośród|wśród|spod|zza|znad|wzdłuż|podczas|mimo|według|wskutek|wobec|naprzeciw|w|we|na|przez|przeze)\s+)(was|Was)\b(?!\s*(?:,|\\N|\s)+(?:{colls_pat}|dwie|dwaj|dwa|dwóch|dwu|troje|trzej|trzy|czworo|cztery|oboje|obie|obaj|wszyscy|wszystkie|razem)\b)"
                            ev.text = re.sub(prep_poss_was_pat, lambda m: f"{m.group(1)}{'Ciebie' if m.group(2)[0].isupper() else 'ciebie'}", ev.text, flags=re.IGNORECASE)

                            prep_poss_wami_pat = rf"\b((?:z|ze|za|pod|pode|nad|nade|przed|przede|poza)\s+)(wami|Wami)\b(?!\s*(?:,|\\N|\s)+(?:{colls_pat}|dwie|dwaj|dwa|dwóch|dwu|troje|trzej|trzy|czworo|cztery|oboje|obie|obaj|wszyscy|wszystkie|razem)\b)"
                            ev.text = re.sub(prep_poss_wami_pat, lambda m: f"{m.group(1)}{'Tobą' if m.group(2)[0].isupper() else 'tobą'}", ev.text, flags=re.IGNORECASE)

                            prep_poss_wam_pat = rf"\b((?:dzięki|przeciw|przeciwko|ku|wbrew)\s+)(wam|Wam)\b(?!\s*(?:,|\\N|\s)+(?:{colls_pat}|dwie|dwaj|dwa|dwóch|dwu|troje|trzej|trzy|czworo|cztery|oboje|obie|obaj|wszyscy|wszystkie|razem)\b)"
                            ev.text = re.sub(prep_poss_wam_pat, lambda m: f"{m.group(1)}{'Tobie' if m.group(2)[0].isupper() else 'tobie'}", ev.text, flags=re.IGNORECASE)

                            prep_poss_loc_was_pat = rf"\b((?:po|przy)\s+)(was|Was)\b(?!\s*(?:,|\\N|\s)+(?:{colls_pat}|dwie|dwaj|dwa|dwóch|dwu|troje|trzej|trzy|czworo|cztery|oboje|obie|obaj|wszyscy|wszystkie|razem)\b)"
                            ev.text = re.sub(prep_poss_loc_was_pat, lambda m: f"{m.group(1)}{'Tobie' if m.group(2)[0].isupper() else 'tobie'}", ev.text, flags=re.IGNORECASE)

                            if ev.text != old_poss_t:
                                clean_ev_text = re.sub(r"\{[^\}]*\}", "", ev.text)
                                fixes.append(
                                    f"[Episode Quality Gate - Filar CLXIII Zgodność Liczby w Relacji Diadycznej] Linia #{i+1}: "
                                    f"zharmonizowano formę 2. os. l. mn. -> l. poj. w dialogu 1-na-1: '{old_poss_t}' -> '{ev.text}'"
                                )

                    is_target_female = (is_single_female or scene_cast_female_only or partner_gender == "FEMALE") and not (is_single_male or partner_gender == "MALE")
                    is_target_male = (is_single_male or scene_cast_male_only or partner_gender == "MALE") and not (is_single_female or partner_gender == "FEMALE")

                    def _harmonize_2nd_person_gender(t: str, target_female: bool, target_male: bool, line_num: int, fixes_list: List[str]) -> str:
                        if target_female:
                            # 1. Convert masculine 2nd-person singular past/conditional/modal verbs -> feminine
                            for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+(?:łeś|łbyś)|powinieneś)\b", t, re.IGNORECASE)):
                                v_masc = m.group(1)
                                v_fem = convert_2nd_person_masculine_to_feminine(v_masc)
                                if v_fem and v_fem.lower() != v_masc.lower():
                                    t = re.sub(rf"\b{re.escape(v_masc)}\b", v_fem, t, count=1)
                                    fixes_list.append(f"[Episode Quality Gate - Filar CLXIII Morfologia Żeńska 2. os. lp.] Linia #{line_num}: skorygowano formę męską '{v_masc}' -> '{v_fem}' (adresat: kobieta)")
                            # Harmonize auxiliary 'był' -> 'była' after 2nd-person feminine modal/verb (strictly single word)
                            t = re.sub(r"\b((?:[Pp]owinnaś|[Bb]yłaś|[Mm]iałaś)\s+)(był)\b", r"\g<1>była", t)

                            # 2. Convert masculine adjectives / participles -> feminine (with safe long-distance span up to 4 words)
                            # Mutates strictly the adjective token, keeping prefix 100% untouched
                            SAFE_INTERVENING_SPAN = (
                                r"(?:(?:taki|taka|zbyt|tak|bardzo|dość|naprawdę|wreszcie|wtedy|znowu|ciągle|przecież|chyba|pewnie|całkiem|aż\s+tak|w\s+końcu|"
                                r"(?!(?:i|a|oraz|ale|lecz|lub|albo|czy|że|gdy|kiedy|ponieważ|bo|jeśli|gdyby|choć|chociaż)\b)[A-Za-ząćęłńóśźż]{1,15})\s+){0,4}"
                            )
                            for m_adj, f_adj in MASCULINE_SG_ADJECTIVES_TO_FEMININE.items():
                                pat_adj = rf"\b((?:byłaś|byłeś|jesteś|bądź|zostałaś|zostałeś|zostań|będziesz|czujesz\s+się|wydajesz\s+się|stajesz\s+się|wyglądasz|nie\s+wyglądasz|[A-Za-ząćęłńóśźż]+(?:łeś|łaś|łbyś|łabyś)(?:\s+\w+)?)\s+{SAFE_INTERVENING_SPAN})({re.escape(m_adj)})\b"
                                for m in list(re.finditer(pat_adj, t, re.IGNORECASE)):
                                    prefix = m.group(1)
                                    old_adj = m.group(2)
                                    repl_adj = f_adj.capitalize() if old_adj[0].isupper() else f_adj
                                    t = re.sub(rf"\b({re.escape(prefix)})({re.escape(old_adj)})\b", rf"\g<1>{repl_adj}", t, count=1)
                                    fixes_list.append(f"[Episode Quality Gate - Filar CLXIII Przymiotnik Żeński 2. os. lp.] Linia #{line_num}: skorygowano '{old_adj}' -> '{repl_adj}' (adresat: kobieta)")
                                    # If the preceding token in prefix is 'taki', harmonize it to 'taka' as a strictly single-word mutation
                                    if re.search(r"\btaki\s*$", prefix, re.IGNORECASE):
                                        t = re.sub(rf"\b(taki)(\s+{re.escape(repl_adj)})\b", r"taka\g<2>", t)
                                        t = re.sub(rf"\b(Taki)(\s+{re.escape(repl_adj)})\b", r"Taka\g<2>", t)

                            # 3. Convert masculine prepositional predicate adjectives (wyglądasz na wzburzonego -> wyglądasz na wzburzoną)
                            prep_adj_pat = rf"\b((?:nie\s+)?(?:wyglądasz|sprawiasz\s+wrażenie)\s+na\s+{SAFE_INTERVENING_SPAN})([A-Za-ząćęłńóśźż]{{3,}})ego\b"
                            for m in list(re.finditer(prep_adj_pat, t, re.IGNORECASE)):
                                prefix = m.group(1)
                                adj_stem = m.group(2)
                                adj_stem_l = adj_stem.lower()
                                if adj_stem_l not in {"cz", "k", "dlacz", "tamt", "t", "nicz", "jakieś", "wszystki", "jedn"}:
                                    repl_word = adj_stem + "ą"
                                    t = re.sub(rf"\b({re.escape(prefix)})({re.escape(adj_stem)}ego)\b", rf"\g<1>{repl_word}", t, count=1)
                                    fixes_list.append(f"[Episode Quality Gate - Filar CLVII/CLXIII Orzecznik Przymiotnikowy Żeński] Linia #{line_num}: skorygowano '{adj_stem}ego' -> '{repl_word}' (adresat: kobieta)")

                            # 4. Convert masculine passive participles after 2nd person (zostałaś wybrany -> zostałaś wybrana)
                            for m in list(re.finditer(rf"\b((?:zostałaś|zostaniesz|zostałabyś|będziesz|byłaś|byłabyś)\s+{SAFE_INTERVENING_SPAN})([A-Za-ząćęłńóśźż]+(?:ny|ty))\b", t, re.IGNORECASE)):
                                prefix = m.group(1)
                                part_m = m.group(2)
                                repl_part = part_m[:-1] + "a"
                                t = re.sub(rf"\b({re.escape(prefix)})({re.escape(part_m)})\b", rf"\g<1>{repl_part}", t, count=1)
                                fixes_list.append(f"[Episode Quality Gate - Filar CLXIII Strona Bierna Żeńska] Linia #{line_num}: skorygowano '{part_m}' -> '{repl_part}' (adresat: kobieta)")

                            # 5. Predicate nouns in Instrumental (Zasada 12 & 15 AGENTS.md - 82 pairs)
                            mods_m_pat = "|".join([m for m, f in PREDICATE_MODS_INSTRUMENTAL])
                            mods_f_pat = "|".join([f for m, f in PREDICATE_MODS_INSTRUMENTAL])
                            all_mods_pat = f"{mods_m_pat}|{mods_f_pat}"
                            fem_all_nouns_pat = "|".join([f for m, f in PREDICATE_NOUNS_INSTRUMENTAL_PAIRS if m != f])
                            has_2nd_copula_f = bool(re.search(r"\b(?:jesteś|będziesz|byłaś|zostałaś|stajesz\s+się)\b", t, re.IGNORECASE))
                            if has_2nd_copula_f:
                                for m_n, f_n in PREDICATE_NOUNS_INSTRUMENTAL_PAIRS:
                                    if m_n == f_n:
                                        continue
                                    pat_pn = rf"((?:\b(?:jesteś|będziesz|byłaś|zostałaś|stajesz\s+się)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_m_pat})\s+){{0,3}})({re.escape(m_n)})\b"
                                    for m in list(re.finditer(pat_pn, t, re.IGNORECASE)):
                                        pref = m.group(1)
                                        old_n = m.group(2)
                                        if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_pat})\s+)*{re.escape(old_n)}\b", t, re.IGNORECASE):
                                            continue
                                        repl_n = f_n.capitalize() if old_n[0].isupper() else f_n
                                        t = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", t, count=1)
                                        fixes_list.append(f"[Episode Quality Gate - Filar CLXIII Rzeczownik Orzecznikowy Żeński] Linia #{line_num}: skorygowano '{old_n}' -> '{repl_n}' (adresat: kobieta)")
                                for m_mod, f_mod in PREDICATE_MODS_INSTRUMENTAL:
                                    pat_mod = rf"((?:\b(?:jesteś|będziesz|byłaś|zostałaś|stajesz\s+się)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_pat})\s+){{0,2}})({re.escape(m_mod)})(\s+(?:(?:{all_mods_pat})\s+)*(?:{fem_all_nouns_pat}))\b"
                                    t = re.sub(pat_mod, rf"\g<1>{f_mod}\g<3>", t, flags=re.IGNORECASE)

                            # 6. Predicate nouns in Nominative (Mianownik orzecznikowy)
                            mods_m_nom_pat = "|".join([m for m, f in PREDICATE_MODS_NOMINATIVE])
                            mods_f_nom_pat = "|".join([f for m, f in PREDICATE_MODS_NOMINATIVE])
                            all_mods_nom_pat = f"{mods_m_nom_pat}|{mods_f_nom_pat}"
                            fem_all_nouns_nom_pat = "|".join([f for m, f in PREDICATE_NOUNS_NOMINATIVE_PAIRS if m != f])
                            has_2nd_nom_copula_f = bool(re.search(r"\b(?:jesteś|będziesz|byłaś|zostałaś|to\s+jest|to)\b", t, re.IGNORECASE))
                            if has_2nd_nom_copula_f:
                                for m_n, f_n in PREDICATE_NOUNS_NOMINATIVE_PAIRS:
                                    if m_n == f_n:
                                        continue
                                    pat_pn_nom = rf"((?:\b(?:jesteś|będziesz|byłaś|zostałaś|to\s+jest|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_m_nom_pat})\s+){{0,3}})({re.escape(m_n)})\b"
                                    for m in list(re.finditer(pat_pn_nom, t, re.IGNORECASE)):
                                        pref = m.group(1)
                                        old_n = m.group(2)
                                        if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_nom_pat})\s+)*{re.escape(old_n)}\b", t, re.IGNORECASE):
                                            continue
                                        repl_n = f_n.capitalize() if old_n[0].isupper() else f_n
                                        t = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", t, count=1)
                                        fixes_list.append(f"[Episode Quality Gate - Filar CLXIII Mianownik Orzecznikowy Żeński] Linia #{line_num}: skorygowano '{old_n}' -> '{repl_n}' (adresat: kobieta)")
                                for m_mod, f_mod in PREDICATE_MODS_NOMINATIVE:
                                    pat_mod_nom = rf"((?:\b(?:jesteś|będziesz|byłaś|zostałaś|to\s+jest|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_nom_pat})\s+){{0,2}})({re.escape(m_mod)})(\s+(?:(?:{all_mods_nom_pat})\s+)*(?:{fem_all_nouns_nom_pat}))\b"
                                    t = re.sub(pat_mod_nom, rf"\g<1>{f_mod}\g<3>", t, flags=re.IGNORECASE)

                        elif target_male:
                            # 1. Convert feminine 2nd-person singular past/conditional/modal verbs -> masculine
                            for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+(?:łaś|łabyś)|powinnaś)\b", t, re.IGNORECASE)):
                                v_fem = m.group(1)
                                v_masc = convert_2nd_person_feminine_to_masculine(v_fem)
                                if v_masc and v_masc.lower() != v_fem.lower():
                                    t = re.sub(rf"\b{re.escape(v_fem)}\b", v_masc, t, count=1)
                                    fixes_list.append(f"[Episode Quality Gate - Filar CLXIII Morfologia Męska 2. os. lp.] Linia #{line_num}: skorygowano formę żeńską '{v_fem}' -> '{v_masc}' (adresat: mężczyzna)")
                            # Harmonize auxiliary 'była' -> 'był' after 2nd-person masculine modal/verb (strictly single word)
                            t = re.sub(r"\b((?:[Pp]owinieneś|[Bb]yłeś|[Mm]iałeś)\s+)(była)\b", r"\g<1>był", t)

                            # 2. Convert feminine adjectives / participles -> masculine (with safe long-distance span up to 4 words)
                            # Mutates strictly the adjective token, keeping prefix 100% untouched
                            SAFE_INTERVENING_SPAN = (
                                r"(?:(?:taki|taka|zbyt|tak|bardzo|dość|naprawdę|wreszcie|wtedy|znowu|ciągle|przecież|chyba|pewnie|całkiem|aż\s+tak|w\s+końcu|"
                                r"(?!(?:i|a|oraz|ale|lecz|lub|albo|czy|że|gdy|kiedy|ponieważ|bo|jeśli|gdyby|choć|chociaż)\b)[A-Za-ząćęłńóśźż]{1,15})\s+){0,4}"
                            )
                            for f_adj, m_adj in FEMININE_SG_ADJECTIVES_TO_MASCULINE.items():
                                pat_adj = rf"\b((?:byłeś|byłaś|jesteś|bądź|zostałeś|zostałaś|zostań|będziesz|czujesz\s+się|wydajesz\s+się|stajesz\s+się|wyglądasz|nie\s+wyglądasz|[A-Za-ząćęłńóśźż]+(?:łeś|łaś|łbyś|łabyś)(?:\s+\w+)?)\s+{SAFE_INTERVENING_SPAN})({re.escape(f_adj)})\b"
                                for m in list(re.finditer(pat_adj, t, re.IGNORECASE)):
                                    prefix = m.group(1)
                                    old_adj = m.group(2)
                                    repl_adj = m_adj.capitalize() if old_adj[0].isupper() else m_adj
                                    t = re.sub(rf"\b({re.escape(prefix)})({re.escape(old_adj)})\b", rf"\g<1>{repl_adj}", t, count=1)
                                    fixes_list.append(f"[Episode Quality Gate - Filar CLXIII Przymiotnik Męski 2. os. lp.] Linia #{line_num}: skorygowano '{old_adj}' -> '{repl_adj}' (adresat: mężczyzna)")
                                    # If the preceding token in prefix is 'taka', harmonize it to 'taki' as a strictly single-word mutation
                                    if re.search(r"\btaka\s*$", prefix, re.IGNORECASE):
                                        t = re.sub(rf"\b(taka)(\s+{re.escape(repl_adj)})\b", r"taki\g<2>", t)
                                        t = re.sub(rf"\b(Taka)(\s+{re.escape(repl_adj)})\b", r"Taki\g<2>", t)

                            # 3. Convert feminine prepositional predicate adjectives (wyglądasz na wzburzoną -> wyglądasz na wzburzonego)
                            prep_adj_pat = rf"\b((?:nie\s+)?(?:wyglądasz|sprawiasz\s+wrażenie)\s+na\s+{SAFE_INTERVENING_SPAN})([A-Za-ząćęłńóśźż]{{3,}})ą\b"
                            for m in list(re.finditer(prep_adj_pat, t, re.IGNORECASE)):
                                prefix = m.group(1)
                                adj_stem = m.group(2)
                                adj_stem_l = adj_stem.lower()
                                if adj_stem_l not in {"t", "tamt", "jedn", "inn", "sob", "mni"}:
                                    repl_word = adj_stem + "ego"
                                    t = re.sub(rf"\b({re.escape(prefix)})({re.escape(adj_stem)}ą)\b", rf"\g<1>{repl_word}", t, count=1)
                                    fixes_list.append(f"[Episode Quality Gate - Filar CLVII/CLXIII Orzecznik Przymiotnikowy Męski] Linia #{line_num}: skorygowano '{adj_stem}ą' -> '{repl_word}' (adresat: mężczyzna)")

                            # 4. Convert feminine passive participles after 2nd person (zostałeś wybrana -> zostałeś wybrany)
                            for m in list(re.finditer(rf"\b((?:zostałeś|zostaniesz|zostałbyś|będziesz|byłeś|byłbyś)\s+{SAFE_INTERVENING_SPAN})([A-Za-ząćęłńóśźż]+(?:na|ta))\b", t, re.IGNORECASE)):
                                prefix = m.group(1)
                                part_f = m.group(2)
                                repl_part = part_f[:-1] + "y"
                                t = re.sub(rf"\b({re.escape(prefix)})({re.escape(part_f)})\b", rf"\g<1>{repl_part}", t, count=1)
                                fixes_list.append(f"[Episode Quality Gate - Filar CLXIII Strona Bierna Męska] Linia #{line_num}: skorygowano '{part_f}' -> '{repl_part}' (adresat: mężczyzna)")

                            # 5. Predicate nouns in Instrumental (Zasada 12 & 15 AGENTS.md - 82 pairs)
                            mods_m_pat = "|".join([m for m, f in PREDICATE_MODS_INSTRUMENTAL])
                            mods_f_pat = "|".join([f for m, f in PREDICATE_MODS_INSTRUMENTAL])
                            all_mods_pat = f"{mods_m_pat}|{mods_f_pat}"
                            masc_all_nouns_pat = "|".join([m for m, f in PREDICATE_NOUNS_INSTRUMENTAL_PAIRS if m != f])
                            has_2nd_copula_m = bool(re.search(r"\b(?:jesteś|będziesz|byłeś|zostałeś|stajesz\s+się)\b", t, re.IGNORECASE))
                            if has_2nd_copula_m:
                                for m_n, f_n in PREDICATE_NOUNS_INSTRUMENTAL_PAIRS:
                                    if m_n == f_n:
                                        continue
                                    pat_pn = rf"((?:\b(?:jesteś|będziesz|byłeś|zostałeś|stajesz\s+się)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_f_pat})\s+){{0,3}})({re.escape(f_n)})\b"
                                    for m in list(re.finditer(pat_pn, t, re.IGNORECASE)):
                                        pref = m.group(1)
                                        old_n = m.group(2)
                                        if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_pat})\s+)*{re.escape(old_n)}\b", t, re.IGNORECASE):
                                            continue
                                        repl_n = m_n.capitalize() if old_n[0].isupper() else m_n
                                        t = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", t, count=1)
                                        fixes_list.append(f"[Episode Quality Gate - Filar CLXIII Rzeczownik Orzecznikowy Męski] Linia #{line_num}: skorygowano '{old_n}' -> '{repl_n}' (adresat: mężczyzna)")
                                for m_mod, f_mod in PREDICATE_MODS_INSTRUMENTAL:
                                    pat_mod = rf"((?:\b(?:jesteś|będziesz|byłeś|zostałeś|stajesz\s+się)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_pat})\s+){{0,2}})({re.escape(f_mod)})(\s+(?:(?:{all_mods_pat})\s+)*(?:{masc_all_nouns_pat}))\b"
                                    t = re.sub(pat_mod, rf"\g<1>{m_mod}\g<3>", t, flags=re.IGNORECASE)

                            # 6. Predicate nouns in Nominative (Mianownik orzecznikowy)
                            mods_m_nom_pat = "|".join([m for m, f in PREDICATE_MODS_NOMINATIVE])
                            mods_f_nom_pat = "|".join([f for m, f in PREDICATE_MODS_NOMINATIVE])
                            all_mods_nom_pat = f"{mods_m_nom_pat}|{mods_f_nom_pat}"
                            masc_all_nouns_nom_pat = "|".join([m for m, f in PREDICATE_NOUNS_NOMINATIVE_PAIRS if m != f])
                            has_2nd_nom_copula_m = bool(re.search(r"\b(?:jesteś|będziesz|byłeś|zostałeś|to\s+jest|to)\b", t, re.IGNORECASE))
                            if has_2nd_nom_copula_m:
                                for m_n, f_n in PREDICATE_NOUNS_NOMINATIVE_PAIRS:
                                    if m_n == f_n:
                                        continue
                                    pat_pn_nom = rf"((?:\b(?:jesteś|będziesz|byłeś|zostałeś|to\s+jest|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_f_nom_pat})\s+){{0,3}})({re.escape(f_n)})\b"
                                    for m in list(re.finditer(pat_pn_nom, t, re.IGNORECASE)):
                                        pref = m.group(1)
                                        old_n = m.group(2)
                                        if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_nom_pat})\s+)*{re.escape(old_n)}\b", t, re.IGNORECASE):
                                            continue
                                        repl_n = m_n.capitalize() if old_n[0].isupper() else m_n
                                        t = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", t, count=1)
                                        fixes_list.append(f"[Episode Quality Gate - Filar CLXIII Mianownik Orzecznikowy Męski] Linia #{line_num}: skorygowano '{old_n}' -> '{repl_n}' (adresat: mężczyzna)")
                                for m_mod, f_mod in PREDICATE_MODS_NOMINATIVE:
                                    pat_mod_nom = rf"((?:\b(?:jesteś|będziesz|byłeś|zostałeś|to\s+jest|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_nom_pat})\s+){{0,2}})({re.escape(f_mod)})(\s+(?:(?:{all_mods_nom_pat})\s+)*(?:{masc_all_nouns_nom_pat}))\b"
                                    t = re.sub(pat_mod_nom, rf"\g<1>{m_mod}\g<3>", t, flags=re.IGNORECASE)
                        return t

                    # Check for split addressees in the line (e.g. Elena, ... Marku, ...)
                    has_female_voc = bool(re.search(r"\b(dziewczyno|kobieto|panienko|siostro|mamo)\b", clean_ev_text, re.IGNORECASE))
                    has_male_voc = bool(re.search(r"\b(chłopcze|młodzieńcze|bracie|ojcze|tato)\b", clean_ev_text, re.IGNORECASE))
                    found_female_names = []
                    found_male_names = []
                    for c_name, c_gen in char_gender_map.items():
                        if len(c_name) >= 3 and c_gen in ("MALE", "FEMALE"):
                            c_w_form = None
                            decl_entry = character_declensions.get(c_name) or character_declensions.get(c_name.capitalize()) or character_declensions.get(c_name.title())
                            if decl_entry and isinstance(decl_entry, dict):
                                c_w_form = decl_entry.get("W")
                            else:
                                from series_memory import generate_polish_name_declension
                                auto_d = generate_polish_name_declension(c_name.capitalize(), c_gen)
                                if auto_d and isinstance(auto_d, dict):
                                    c_w_form = auto_d.get("W")
                            matched_name_tokens = [c_name]
                            if c_w_form and c_w_form.lower() != c_name.lower():
                                matched_name_tokens.append(c_w_form)
                            name_pat = rf"\b(?:{'|'.join(re.escape(t) for t in matched_name_tokens)})[,!\?]"
                            if re.search(name_pat, clean_ev_text, re.IGNORECASE):
                                if c_gen == "FEMALE":
                                    found_female_names.extend(matched_name_tokens)
                                elif c_gen == "MALE":
                                    found_male_names.extend(matched_name_tokens)

                    is_split_addressee = (has_female_voc or found_female_names) and (has_male_voc or found_male_names)
                    has_dual_dash_turns = bool(re.search(r"(?:^|[\r\n]|\\[Nnh])\s*[-–—]\s*.*\\[Nnh]\s*[-–—]\s*", ev.text))

                    if is_split_addressee:
                        # Split into dialogic clauses, preserving delimiters
                        clause_chunks = re.split(r"([.!?…]+|\\[Nnh]|\s+[-–—]\s+|\s+a\s+ty,\s+)", ev.text)
                        processed_chunks = []
                        current_clause_f = is_target_female
                        current_clause_m = is_target_male

                        for chunk in clause_chunks:
                            chunk_clean = re.sub(r"\{[^\}]*\}", "", chunk)
                            ch_has_f = bool(re.search(r"\b(dziewczyno|kobieto|panienko|siostro|mamo)\b", chunk_clean, re.IGNORECASE)) or any(re.search(rf"\b{re.escape(fn)}\b", chunk_clean, re.IGNORECASE) for fn in found_female_names)
                            ch_has_m = bool(re.search(r"\b(chłopcze|młodzieńcze|bracie|ojcze|tato)\b", chunk_clean, re.IGNORECASE)) or any(re.search(rf"\b{re.escape(mn)}\b", chunk_clean, re.IGNORECASE) for mn in found_male_names)

                            if ch_has_f and not ch_has_m:
                                current_clause_f = True
                                current_clause_m = False
                            elif ch_has_m and not ch_has_f:
                                current_clause_f = False
                                current_clause_m = True

                            if re.match(r"^([.!?…]+|\\[Nnh]|\s+[-–—]\s+|\s+a\s+ty,\s+)$", chunk):
                                processed_chunks.append(chunk)
                            else:
                                processed_chunk = _harmonize_2nd_person_gender(chunk, current_clause_f, current_clause_m, i + 1, fixes)
                                processed_chunks.append(processed_chunk)

                        ev.text = "".join(processed_chunks)
                    elif has_dual_dash_turns and (is_target_female or is_target_male):
                        turn_parts = re.split(r"(\\[Nnh]\s*[-–—]\s*)", ev.text, maxsplit=1)
                        if len(turn_parts) == 3:
                            turn1_text, sep, turn2_text = turn_parts[0], turn_parts[1], turn_parts[2]
                            p_turn1 = _harmonize_2nd_person_gender(turn1_text, is_target_female, is_target_male, i + 1, fixes)
                            p_turn2 = _harmonize_2nd_person_gender(turn2_text, not is_target_female, not is_target_male, i + 1, fixes)
                            ev.text = f"{p_turn1}{sep}{p_turn2}"
                        else:
                            ev.text = _harmonize_2nd_person_gender(ev.text, is_target_female, is_target_male, i + 1, fixes)
                    else:
                        ev.text = _harmonize_2nd_person_gender(ev.text, is_target_female, is_target_male, i + 1, fixes)

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
                    c_val = character_registry.get(spk_orig, "")
                    c_desc = (c_val.get("description", "") or c_val.get("role", "") or c_val.get("gender", "")) if isinstance(c_val, dict) else str(c_val)
                    c_desc = c_desc.lower()
                    c_gen = (c_val.get("gender", "") if isinstance(c_val, dict) else "").upper()
                    if any(w in c_desc for w in ["collective_virile", "żarłoczność", "zarlocznosc", "byt mnogi męskoosobowy", "byt zbiorowy męskoosobowy"]):
                        is_coll_virile = True
                    elif any(w in c_desc for w in ["majestic_female", "pluralis maiestatis (kobieta)", "monarchini"]):
                        is_majestic_fem = True
                    elif c_gen in ("FEMALE_GROUP", "FEMALE") and (is_plural_actor(spk_orig) or any(w in c_desc for w in ["kobiety", "dziewczęt", "dziewczyn", "collective_nonvirile", "grupa kobiet"])):
                        is_coll_nonvirile = True
                    elif c_gen in ("MALE_GROUP", "MALE") and (is_plural_actor(spk_orig) or any(w in c_desc for w in ["mężczyź", "chłopak", "collective_virile", "grupa mężczyzn"])):
                        is_coll_virile = True

                if not is_coll_nonvirile and (spk_orig.lower() in ("kobiety", "dziewczęta", "dziewczyny", "siostry", "zakonnice", "kapłanki") or (is_plural_actor(spk_orig) and char_gender_map.get(spk_orig.lower()) == "FEMALE")):
                    is_coll_nonvirile = True
                if not is_coll_virile and (spk_orig.lower() in ("mężczyźni", "chłopaki", "chłopcy", "panowie", "bracia", "żołnierze") or (is_plural_actor(spk_orig) and char_gender_map.get(spk_orig.lower()) == "MALE")):
                    is_coll_virile = True

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
                            ev.text = re.sub(rf"\b({re.escape(prefix)})({re.escape(old_adj)})\b", rf"\g<1>{repl_adj}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXXV Orzecznik Niemęskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{old_adj}' -> '{repl_adj}' (scena kobieca)")

                    # 4. Numerals and pronouns (1st-person plural requires 'my')
                    # Strictly single-token mutation: preserves 'My' and exact whitespace untouched!
                    def _repl_my_dual(m):
                        word = m.group(2)
                        repl = "obie"
                        fixes.append(f"[Episode Quality Gate - Filar CLXXV Liczebnik Podwójny 1. os. lm.] Linia #{i+1}: skorygowano '{word}' -> '{repl}' (scena kobieca)")
                        return f"{m.group(1)}{repl}"
                    ev.text = re.sub(r"\b([Mm]y\s+)(obaj|oboje)\b", _repl_my_dual, ev.text)

                    def _repl_my_same(m):
                        fixes.append(f"[Episode Quality Gate - Filar CLXXV Zaimek Niemęskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{m.group(2)}' -> 'same' (scena kobieca)")
                        return f"{m.group(1)}same"
                    ev.text = re.sub(r"\b([Mm]y\s+)(sami)\b", _repl_my_same, ev.text)

                    # 5. Predicate nouns in instrumental plural for 1st-person female scene
                    has_1pl_copula_f = bool(re.search(r"\b(?:jesteśmy|będziemy|byłyśmy|byliśmy|zostałyśmy|zostaliśmy)\b", ev.text, re.IGNORECASE))
                    if has_1pl_copula_f:
                        for m_n, f_n in PREDICATE_NOUNS_PLURAL_INSTRUMENTAL_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn = rf"((?:\b(?:jesteśmy|będziemy|byłyśmy|byliśmy|zostałyśmy|zostaliśmy)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:[A-Za-ząćęłńóśźż]+(?:ymi|imi)|moimi|twoimi|naszymi|waszymi|ich|swoimi)\s+){{0,3}})({re.escape(m_n)})\b"
                            for m in list(re.finditer(pat_pn, ev.text, re.IGNORECASE)):
                                pref = m.group(1)
                                old_n = m.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:[A-Za-ząćęłńóśźż]+\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = f_n.capitalize() if old_n[0].isupper() else f_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXXV Rzeczownik Orzecznikowy Niemęskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{old_n}' -> '{repl_n}' (scena kobieca)")

                    # 6. Predicate nouns in nominative plural for 1st-person female scene
                    has_1pl_nom_copula_f = bool(re.search(r"\b(?:jesteśmy|będziemy|byłyśmy|byliśmy|zostałyśmy|zostaliśmy|to\s+są|to)\b", ev.text, re.IGNORECASE))
                    if has_1pl_nom_copula_f:
                        mods_m_nom_pl_pat = "|".join([m for m, f in PREDICATE_MODS_PLURAL_NOMINATIVE])
                        mods_f_nom_pl_pat = "|".join([f for m, f in PREDICATE_MODS_PLURAL_NOMINATIVE])
                        all_mods_nom_pl_pat = f"{mods_m_nom_pl_pat}|{mods_f_nom_pl_pat}"
                        fem_all_nouns_nom_pl_pat = "|".join([f for m, f in PREDICATE_NOUNS_PLURAL_NOMINATIVE_PAIRS if m != f])
                        for m_n, f_n in PREDICATE_NOUNS_PLURAL_NOMINATIVE_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn_nom = rf"((?:\b(?:jesteśmy|będziemy|byłyśmy|byliśmy|zostałyśmy|zostaliśmy|to\s+są|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_m_nom_pl_pat})\s+){{0,3}})({re.escape(m_n)})\b"
                            for m in list(re.finditer(pat_pn_nom, ev.text, re.IGNORECASE)):
                                pref = m.group(1)
                                old_n = m.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_nom_pl_pat})\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = f_n.capitalize() if old_n[0].isupper() else f_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXXV Mianownik Orzecznikowy Niemęskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{old_n}' -> '{repl_n}' (scena kobieca)")
                        for m_mod, f_mod in PREDICATE_MODS_PLURAL_NOMINATIVE:
                            pat_mod_nom = rf"((?:\b(?:jesteśmy|będziemy|byłyśmy|byliśmy|zostałyśmy|zostaliśmy|to\s+są|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_nom_pl_pat})\s+){{0,2}})({re.escape(m_mod)})(\s+(?:(?:{all_mods_nom_pl_pat})\s+)*(?:{fem_all_nouns_nom_pl_pat}))\b"
                            ev.text = re.sub(pat_mod_nom, rf"\g<1>{f_mod}\g<3>", ev.text, flags=re.IGNORECASE)

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
                            ev.text = re.sub(rf"\b({re.escape(prefix)})({re.escape(old_adj)}\b)", rf"\g<1>{repl_adj}", ev.text, count=1)
                            fixes.append(f"[Episode Quality Gate - Filar CLXXV Orzecznik Męskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{old_adj}' -> '{repl_adj}' (scena męska)")

                    # Numerals and pronouns (1st-person plural requires 'my')
                    # Strictly single-token mutation: preserves 'My' and exact whitespace untouched!
                    def _repl_my_dual_m(m):
                        word = m.group(2)
                        repl = "obaj"
                        fixes.append(f"[Episode Quality Gate - Filar CLXXV Liczebnik Podwójny 1. os. lm.] Linia #{i+1}: skorygowano '{word}' -> '{repl}' (scena męska)")
                        return f"{m.group(1)}{repl}"
                    ev.text = re.sub(r"\b([Mm]y\s+)(obie)\b", _repl_my_dual_m, ev.text)

                    def _repl_my_sami_m(m):
                        fixes.append(f"[Episode Quality Gate - Filar CLXXV Zaimek Męskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{m.group(2)}' -> 'sami' (scena męska)")
                        return f"{m.group(1)}sami"
                    ev.text = re.sub(r"\b([Mm]y\s+)(same)\b", _repl_my_sami_m, ev.text)

                    # 5. Predicate nouns in instrumental plural for 1st-person male scene
                    has_1pl_copula_m = bool(re.search(r"\b(?:jesteśmy|będziemy|byliśmy|byłyśmy|zostaliśmy|zostałyśmy)\b", ev.text, re.IGNORECASE))
                    if has_1pl_copula_m:
                        for m_n, f_n in PREDICATE_NOUNS_PLURAL_INSTRUMENTAL_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn = rf"((?:\b(?:jesteśmy|będziemy|byliśmy|byłyśmy|zostaliśmy|zostałyśmy)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:[A-Za-ząćęłńóśźż]+(?:ymi|imi)|moimi|twoimi|naszymi|waszymi|ich|swoimi)\s+){{0,3}})({re.escape(f_n)})\b"
                            for m in list(re.finditer(pat_pn, ev.text, re.IGNORECASE)):
                                pref = m.group(1)
                                old_n = m.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:[A-Za-ząćęłńóśźż]+\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = m_n.capitalize() if old_n[0].isupper() else m_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXXV Rzeczownik Orzecznikowy Męskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{old_n}' -> '{repl_n}' (scena męska)")

                    # 6. Predicate nouns in nominative plural for 1st-person male scene
                    has_1pl_nom_copula_m = bool(re.search(r"\b(?:jesteśmy|będziemy|byliśmy|byłyśmy|zostaliśmy|zostałyśmy|to\s+są|to)\b", ev.text, re.IGNORECASE))
                    if has_1pl_nom_copula_m:
                        mods_m_nom_pl_pat = "|".join([m for m, f in PREDICATE_MODS_PLURAL_NOMINATIVE])
                        mods_f_nom_pl_pat = "|".join([f for m, f in PREDICATE_MODS_PLURAL_NOMINATIVE])
                        all_mods_nom_pl_pat = f"{mods_m_nom_pl_pat}|{mods_f_nom_pl_pat}"
                        masc_all_nouns_nom_pl_pat = "|".join([m for m, f in PREDICATE_NOUNS_PLURAL_NOMINATIVE_PAIRS if m != f])
                        for m_n, f_n in PREDICATE_NOUNS_PLURAL_NOMINATIVE_PAIRS:
                            if m_n == f_n:
                                continue
                            pat_pn_nom = rf"((?:\b(?:jesteśmy|będziemy|byliśmy|byłyśmy|zostaliśmy|zostałyśmy|to\s+są|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{mods_f_nom_pl_pat})\s+){{0,3}})({re.escape(f_n)})\b"
                            for m in list(re.finditer(pat_pn_nom, ev.text, re.IGNORECASE)):
                                pref = m.group(1)
                                old_n = m.group(2)
                                if re.search(rf"\b(?:z|ze|do|od|dla|o|u|w|we|na|przez|nad|pod|przed|za|między)\s+(?:(?:{all_mods_nom_pl_pat})\s+)*{re.escape(old_n)}\b", ev.text, re.IGNORECASE):
                                    continue
                                repl_n = m_n.capitalize() if old_n[0].isupper() else m_n
                                ev.text = re.sub(rf"({re.escape(pref)})({re.escape(old_n)})\b", rf"\g<1>{repl_n}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXXV Mianownik Orzecznikowy Męskoosobowy 1. os. lm.] Linia #{i+1}: skorygowano '{old_n}' -> '{repl_n}' (scena męska)")
                        for m_mod, f_mod in PREDICATE_MODS_PLURAL_NOMINATIVE:
                            pat_mod_nom = rf"((?:\b(?:jesteśmy|będziemy|byliśmy|byłyśmy|zostaliśmy|zostałyśmy|to\s+są|to)\s+|\s*,\s*|\s+(?:i|oraz)\s+)(?:(?:{all_mods_nom_pl_pat})\s+){{0,2}})({re.escape(f_mod)})(\s+(?:(?:{all_mods_nom_pl_pat})\s+)*(?:{masc_all_nouns_nom_pl_pat}))\b"
                            ev.text = re.sub(pat_mod_nom, rf"\g<1>{m_mod}\g<3>", ev.text, flags=re.IGNORECASE)

            # 3c-7. PRONOMINAL DECOUPLING & INALIENABLE SOMATIC POSSESSION (Filar CLXXVII - 0.00 PLN)
            if not is_sign and ev.text:
                from series_memory import sanitize_pronominal_somatic_possession
                old_som_t = ev.text
                ev.text = sanitize_pronominal_somatic_possession(ev.text)
                if ev.text != old_som_t:
                    fixes.append(f"[Episode Quality Gate - Filar CLXXVII Pronominal Decoupling] Linia #{i+1}: oczyszczono zaimkozę somatyczną/relacyjną -> '{ev.text}'")

            # 3c-8. AFFECTIVE SHOCK & EXCLAMATION DAMPER (Filar CLXXVIII - 0.00 PLN)
            if not is_sign and ev.text:
                ev_prosody = str(getattr(ev, "prosody", "") or "")
                if prosody_tags and (i + 1) in prosody_tags:
                    ev_prosody += f" {prosody_tags[i + 1]}"
                is_shock = "Ac=SHOCK_DROP" in ev_prosody or "szok" in ev_prosody.lower() or getattr(ev, "is_shock_drop", False)
                if is_shock:
                    if re.search(r"!{2,}", ev.text):
                        old_shock_t = ev.text
                        ev.text = re.sub(r"!{2,}", "...", ev.text)
                        if ev.text != old_shock_t:
                            fixes.append(f"[Episode Quality Gate - Filar CLXXVIII Reset Inercji Afektywnej] Linia #{i+1}: wytłumiono zwielokrotniony wykrzyknik przy pęknięciu afektywnym (Ac=SHOCK_DROP) -> '{ev.text}'")

            # 3c-9. CONVERSATIONAL ADJACENCY PAIRS & ELLIPTICAL REJOINDERS (Filar CLXXIX - 0.00 PLN)
            if not is_sign and i > 0 and ev.text:
                prev_ev = events[i - 1]
                time_diff = ev.start - prev_ev.end
                if time_diff < 3500:
                    prev_clean_t = re.sub(r"\{[^\}]*\}", "", prev_ev.text or "").strip()
                    if prev_clean_t.endswith("?"):
                        from series_memory import naturalize_adjacency_rejoinder
                        old_adj_t = ev.text
                        ev.text = naturalize_adjacency_rejoinder(prev_clean_t, ev.text)
                        if ev.text != old_adj_t:
                            fixes.append(f"[Episode Quality Gate - Filar CLXXIX Dialogowa Para Przylegania] Linia #{i+1}: znaturalizowano schematyczną odpowiedź na elipsę orzeczeniową -> '{ev.text}'")

            # 3c-10. CINEMATIC SPATIAL DEIXIS & DIRECTIONAL MOTION VERBS (Filar CLXXX - 0.00 PLN)
            if not is_sign and ev.text:
                from series_memory import sanitize_deictic_motion_vector
                old_deic_t = ev.text
                ev.text = sanitize_deictic_motion_vector(ev.text)
                if ev.text != old_deic_t:
                    fixes.append(f"[Episode Quality Gate - Filar CLXXX Wektor Deiktyczny Ruchu] Linia #{i+1}: skorygowano fałszywy wektor ruchu -> '{ev.text}'")

            # 3c-11. SEMIOTIC IMAGE-TEXT COEXISTENCE & PLEONASM COMPRESSOR (Filar CLXXXI - 0.00 PLN)
            if not is_sign and ev.text:
                from series_memory import sanitize_sensory_pleonasm
                old_pleon_t = ev.text
                ev.text = sanitize_sensory_pleonasm(ev.text)
                if ev.text != old_pleon_t:
                    fixes.append(f"[Episode Quality Gate - Filar CLXXXI Tłumienie Pleonazmów Zmysłowych] Linia #{i+1}: zlikwidowano pleonazm sensoryczno-przestrzenny -> '{ev.text}'")

            # 3c-12. TOPONYMIC & CLASSIFIER PLEONASM AND STUTTERING SANITIZER (Filar CLXXXIV - 0.00 PLN)
            if not is_sign and ev.text:
                from series_memory import sanitize_toponymic_pleonasms_and_stuttering, sanitize_toponymic_origin_and_companionship
                old_top_pleon = ev.text
                ev.text = sanitize_toponymic_pleonasms_and_stuttering(ev.text)
                if ev.text != old_top_pleon:
                    fixes.append(f"[Episode Quality Gate - Filar CLXXXIV Eliminacja Pleonazmów Toponimicznych i Jąkania] Linia #{i+1}: zlikwidowano pleonazm toponimiczny/jąkanie -> '{ev.text}'")

                old_top_orig = ev.text
                ev.text = sanitize_toponymic_origin_and_companionship(
                    ev.text,
                    custom_glossary=custom_glossary or (series_bible.data.get("glossary") if series_bible and hasattr(series_bible, "data") else None)
                )
                if ev.text != old_top_orig:
                    fixes.append(f"[Episode Quality Gate - Filar CLXXXIV Harmonizacja Pochodzenia Toponimów] Linia #{i+1}: skorygowano narzędnik toponimu na dopełniacz pochodzenia -> '{ev.text}'")

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
            if not is_sign and re.search(r"\b(oboje|obojga|obojgu|obojgiem|obaj|obydwaj|obie|obydwie|obu|obiema|oboma)\b", ev.text, re.IGNORECASE):
                # Detect whether referents are:
                # 1) two female characters (is_female_dual)
                # 2) mixed dual pair: 1 female + 1 male (is_mixed_dual)
                # 3) two male characters (is_male_dual)
                is_female_dual = False
                is_mixed_dual = False
                is_male_dual = False

                addr_tag = (line_addressees.get(i) or "").lower() if line_addressees else ""
                if addr_tag in ("para_mieszana_dual", "para_mieszana", "grupa_mieszana"):
                    is_mixed_dual = True
                elif addr_tag in ("kobieta_dual", "grupa_kobiet"):
                    is_female_dual = True
                elif addr_tag in ("mężczyzna_dual", "grupa_mężczyzn"):
                    is_male_dual = True

                clean_line_lower = re.sub(r"\{[^\}]*\}", "", ev.text).lower()

                if not (is_female_dual or is_mixed_dual or is_male_dual):
                    # Check 1: Exclusively diarized scene gender (all-female or all-male scene)
                    if event_scene_gender.get(i) == "FEMALE":
                        is_female_dual = True
                    elif event_scene_gender.get(i) == "MALE":
                        is_male_dual = True

                if not (is_female_dual or is_mixed_dual or is_male_dual):
                    # Check 2: In the same line, feminine plural past tense
                    if re.search(r"\b[a-ząćęłńóśźż]+(?:ły|łyście|łyśmy)\b", clean_line_lower):
                        is_female_dual = True

                if not (is_female_dual or is_mixed_dual or is_male_dual):
                    # Check 3: Context scan (previous 10 dialogue events in current scene)
                    context_corpus = []
                    for k in range(max(0, i - 10), i):
                        cand_prev = events[k]
                        if cand_prev.text and (ev.start - cand_prev.end < 25000):
                            context_corpus.append(re.sub(r"\{[^\}]*\}", "", cand_prev.text))
                    joined_ctx = " ".join(context_corpus).lower()

                    female_names_found = set()
                    male_names_found = set()
                    for c_name, c_gen in char_gender_map.items():
                        if len(c_name) >= 3 and c_name in joined_ctx:
                            if c_gen == "FEMALE":
                                female_names_found.add(c_name)
                            elif c_gen == "MALE":
                                male_names_found.add(c_name)

                    if series_bible and hasattr(series_bible, "get_dual_pair_gender_type") and (len(female_names_found) + len(male_names_found) >= 2):
                        bible_dual = series_bible.get_dual_pair_gender_type(female_names_found | male_names_found)
                        if bible_dual == "DUAL_MIXED":
                            is_mixed_dual = True
                        elif bible_dual == "DUAL_FEMALE":
                            is_female_dual = True
                        elif bible_dual == "DUAL_MALE":
                            is_male_dual = True

                    if not (is_female_dual or is_mixed_dual or is_male_dual):
                        if len(female_names_found) >= 1 and len(male_names_found) >= 1:
                            is_mixed_dual = True
                        elif len(female_names_found) >= 2:
                            is_female_dual = True
                        elif any(p in joined_ctx for p in ["odnalazły", "odnalazłyście"]):
                            is_female_dual = True

                if not (is_female_dual or is_mixed_dual or is_male_dual):
                    if re.search(r"\b[a-ząćęłńóśźż]+(?:li|liście|liśmy)\b", clean_line_lower):
                        is_male_dual = True

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
                    # Strictly single-token mutation: 'Wy' is untouched, only 'obaj'/'obydwaj' changes
                    ev.text = re.sub(r"\b([Ww]y\s+)(obaj)\b", r"\g<1>obie", ev.text)
                    ev.text = re.sub(r"\b([Ww]y\s+)(obydwaj)\b", r"\g<1>obydwie", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bObaj\b", "Obie", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bobaj\b", "obie", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bObydwaj\b", "Obydwie", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bobydwaj\b", "obydwie", ev.text)
                    # Strictly single-token mutation: 'dla was' and 'was' are untouched
                    ev.text = re.sub(r"\b([Dd]la\s+was\s+)(obojga)\b", r"\g<1>obu", ev.text)
                    ev.text = re.sub(r"\b([Ww]as\s+)(oboje)\b", r"\g<1>obie", ev.text)
                    # 'ich obie' -> 'obie' is untouched, only 'ich' changes to 'je'
                    ev.text = re.sub(r"\b(ich)(\s+obie)\b", r"je\g<2>", ev.text)
                    if ev.text != old_dual_t:
                        fixes.append(f"[Episode Quality Gate - Filar CLXII Zgodność Liczebników Podwójnych] Linia #{i+1}: skorygowano 'oboje' -> 'obie' (referenci: 2 kobiety)")

                elif is_mixed_dual:
                    old_dual_mixed = ev.text
                    # 1. Nominative / Vocative: Wy obaj / Wy obie -> Wy oboje
                    ev.text = re.sub(r"\b([Ww]y\s+)(obaj|obie)\b", r"\g<1>oboje", ev.text)
                    ev.text = re.sub(r"\b([Ww]y\s+)(obydwaj|obydwie)\b", r"\g<1>obydwoje", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bObaj\b", "Oboje", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bObie\b", "Oboje", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bobaj\b", "oboje", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bobie\b", "oboje", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bObydwaj\b", "Obydwoje", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bObydwie\b", "Obydwoje", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bobydwaj\b", "obydwoje", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bobydwie\b", "obydwoje", ev.text)

                    # 2. Genitive / Prepositional: dla was obu -> dla was obojga
                    ev.text = re.sub(r"\b((?:[Dd]la|[Oo]d|[Dd]o|[Uu]|[Bb]ez)\s+was\s+)(obu|obydwu)\b", r"\g<1>obojga", ev.text)

                    # 3. Accusative: was obu / was obie -> was oboje
                    ev.text = re.sub(r"\b([Ww]as\s+)(obu|obie|obydwu|obydwie)\b", r"\g<1>oboje", ev.text)

                    # 4. Dative: wam obu -> wam obojgu
                    ev.text = re.sub(r"\b((?:[Ww]am|[Dd]zięki\s+wam|[Pp]rzeciwko\s+wam)\s+)(obu|obydwu)\b", r"\g<1>obojgu", ev.text)

                    # 5. Instrumental: z wami oboma / z wami obiema -> z wami obojgiem
                    ev.text = re.sub(r"\b((?:[Zz]|[Pp]rzed|[Mm]iędzy|[Nn]ad)\s+wami\s+)(oboma|obiema|obydwoma|obydwiema)\b", r"\g<1>obojgiem", ev.text)

                    # 6. Locative: o was obu -> o was obojgu
                    ev.text = re.sub(r"\b([Oo]\s+was\s+)(obu|obydwu)\b", r"\g<1>obojgu", ev.text)

                    if ev.text != old_dual_mixed:
                        fixes.append(f"[Episode Quality Gate - Filar CLXXIII Liczebniki Zbiorowe Par Mieszanych] Linia #{i+1}: skorygowano liczebnik podwójny na formę zbiorową ('oboje' / 'obojga' / 'obojgiem') (referenci: para mieszana)")

                elif is_male_dual:
                    old_dual_m = ev.text
                    # Strictly single-token mutation: 'Wy' is untouched, only 'obie'/'obydwie' changes
                    ev.text = re.sub(r"\b([Ww]y\s+)(obie)\b", r"\g<1>obaj", ev.text)
                    ev.text = re.sub(r"\b([Ww]y\s+)(obydwie)\b", r"\g<1>obydwaj", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bObie\b", "Obaj", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bobie\b", "obaj", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bObydwie\b", "Obydwaj", ev.text)
                    ev.text = re.sub(r"(?<!\b[Ww]y\s)\bobydwie\b", "obydwaj", ev.text)
                    if ev.text != old_dual_m:
                        fixes.append(f"[Episode Quality Gate - Filar CLXII Zgodność Liczebników Podwójnych] Linia #{i+1}: skorygowano liczebnik na rodzaj męski (referenci: 2 mężczyzn)")

            # 3d. FOREIGN NAME DECLENSION UNIFORMITY (Case-Segregated Prepositional Cases)
            if not is_sign and any(dominant_prep_case_names.values()):
                CASE_PREP_REGEX_MAP = {
                    "gen": r"\b(do|dla|od|u|bez|koło|obok|wzdłuż|podczas|zamiast|oprócz|wokół|wobec)",
                    "dat": r"\b(ku|przeciw|przeciwko|dzięki|wbrew)",
                    "acc": r"\b(przez)",
                    "ins": r"\b(przed|nad|pod|między|z|ze)",
                    "loc": r"\b(przy|o)",
                }
                for case_k, dom_names in dominant_prep_case_names.items():
                    if not dom_names:
                        continue
                    prep_pattern = CASE_PREP_REGEX_MAP.get(case_k)
                    if not prep_pattern:
                        continue
                    for c_name, dom_form in dom_names.items():
                        stem_len = max(3, len(c_name) - 2)
                        stem = c_name[:stem_len]
                        def _prep_decl_repl(m, target=dom_form, c_k=case_k):
                            prep = m.group(1)
                            sep = m.group(2)
                            matched_form = m.group(3)
                            # Protect non-character toponyms after 'z' / 'ze' from being forced into instrumental
                            if prep.lower() in {"z", "ze"} and c_k == "ins":
                                if series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(matched_form):
                                    return m.group(0)
                            if matched_form != target:
                                return f"{prep}{sep}{target}"
                            return m.group(0)
                        pat = rf"{prep_pattern}(\s+)({re.escape(stem)}[^\s,\.!\?…]*)\b"
                        old_text = ev.text
                        ev.text = re.sub(pat, _prep_decl_repl, ev.text, flags=re.IGNORECASE)
                        if ev.text != old_text:
                            fixes.append(f"[Episode Quality Gate - Jednolita Deklinacja Imion] Linia #{i+1}: ujednolicono formę imienia po przyimku ({case_k}) na '{dom_form}' (dominująca konwencja w odcinku)")

            # 3d2. DETERMINISTIC 7-CASE DECLENSION MATRIX ENFORCEMENT (from Series Bible / Registry)
            if not is_sign and compiled_decl_rules:
                clean_lower = re.sub(r"\{[^\}]*\}", "", ev.text).lower()
                for r in compiled_decl_rules:
                    # Fast rejection: only run regexes if character name, stem, or multi-word part appears in text
                    if r["m_lower"] not in clean_lower and r["stem_lower"] not in clean_lower and not any(wl in clean_lower for wl in r.get("words_lower", [])):
                        continue

                    if "re_n" in r:
                        n_form = r["n_form"]
                        def _repl_n(m, target=n_form, c_name=r["name"]):
                            matched = m.group(3)
                            if matched.lower() == target.lower():
                                return m.group(0)
                            matched_prep = m.group(1).lower()
                            # Dual-governance preposition 'za': in sacrifice, fighting, prayer, marriage, perception
                            # 'za' governs Accusative (Biernik), NOT Instrumental (Narzędnik)!
                            if matched_prep == "za":
                                before_text = ev.text[:m.start()]
                                if re.search(r"\b(?:walczyć|walczy|walczył|walcz|bić|bije|oddać|odda|oddał|zginąć|zginie|zginął|umrzeć|umrze|umarł|polec|polegnie|poległ|modlić|modli|modlił|wstawić|wstawi|wstawił|ręczyć|ręczy|ręczył|stać\s+murem|wyjść|wyjdzie|wyszła|wyszło|wyszli|wyjście|wyjścia|wychodzić|wychodzi|oddać|wydać|wydał|wyda|wziąć|brać|weźmie|zapłacić|płacić|kara|uznać|uznaje|uważać|uważa|uchodzić|uchodzi|mieć|odpowiadać|odpowiada|trzymać|złapać|chwycić|dziękować|przepraszać)\s+(?:zaś\s+|zaraz\s+|chyba\s+|tam\s+)?$", before_text, re.IGNORECASE):
                                    return m.group(0)
                            # Toponyms and non-character entities after 'z' / 'ze' must NOT take personal instrumental!
                            if matched_prep in ["z", "ze"]:
                                if series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(c_name):
                                    return m.group(0)
                            tgt = preserve_declension_casing(matched, target)
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
                            tgt = preserve_declension_casing(matched, target)
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
                            tgt = preserve_declension_casing(matched, target)
                            return f"{m.group(1)}{m.group(2)}{tgt}"
                        old_t = ev.text
                        ev.text = r["re_pos_d"].sub(_repl_pos_d, ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Dopełniacz Dzierżawczy] Linia #{i+1}: ujednolicono formę na '{d_form}' po określeniu dzierżawczym/rządzącym")

                    if "re_c" in r:
                        c_form = r["c_form"]
                        def _repl_c(m, target=c_form):
                            matched = m.group(3)
                            tgt = preserve_declension_casing(matched, target)
                            return f"{m.group(1)}{m.group(2)}{tgt}"
                        old_t = ev.text
                        ev.text = r["re_c"].sub(_repl_c, ev.text)
                        if ev.text != old_t:
                            fixes.append(f"[Episode Quality Gate - Matryca Celownika] Linia #{i+1}: ujednolicono formę na '{c_form}' po przyimku celownika")

                    if "re_ms" in r:
                        ms_form = r["ms_form"]
                        def _repl_ms(m, target=ms_form):
                            matched = m.group(3)
                            tgt = preserve_declension_casing(matched, target)
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
                            tgt = preserve_declension_casing(matched_nom, target_b)
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
                                val = character_registry.get(raw_stem, "UNKNOWN")
                                if isinstance(val, dict):
                                    target_gender = str(val.get("gender", "UNKNOWN")).upper()
                                elif isinstance(val, str):
                                    target_gender = val.upper()

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
                        is_vocative_senpai = bool(re.search(r"(^|[,\.!\?…]\s*|\bHej,\s*|\bEj,\s*)[Ss]enpai[!,\?…]+(?:\s*\\N|$)", ev.text)) or bool(re.search(r",\s*[Ss]enpai\b", ev.text))
                        has_subject_or_prep = bool(re.search(r"\b(nasz|mój|wasz|twój|ten|to|jest|był|będzie|widziałem|widziałaś|słyszałem|gdzie|od|do|dla|u|o|z|ze|przez)\s+[Ss]enpa", ev.text, re.IGNORECASE))
                        if is_vocative_senpai and not has_subject_or_prep:
                            ev.text = re.sub(r",\s*[Ss]enpai\b", "", ev.text)
                            clean_plain = re.sub(r"\{[^\}]*\}", "", ev.text).strip()
                            if clean_plain in ["Senpai!", "Senpai?", "Senpai", "senpai!", "senpai"]:
                                ev.text = re.sub(r"\b[Ss]enpai\b", "Uwaga", ev.text)
                            else:
                                ev.text = re.sub(r"\b[Ss]enpai[!,\?…]*\s*", "", ev.text).strip()
                        elif has_subject_or_prep or bool(re.search(r"\b[Ss]enpai\b", ev.text)):
                            ev.text = re.sub(r"\b[Ss]enpai\b", "starszy kolega", ev.text)
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
                        decl_map = (
                            character_declensions.get(clean_trg)
                            or character_declensions.get(clean_trg.capitalize())
                            or character_declensions.get(clean_trg.title())
                        )
                        dep_forms = (
                            {v.lower() for k_c, v in decl_map.items() if k_c != "M"}
                            if decl_map else set()
                        )

                        def _case_gloss_repl(m, target=clean_trg, d_map=decl_map, dep_set=dep_forms):
                            matched = m.group(0).strip()
                            if dep_set and matched.lower() in dep_set:
                                return m.group(0)

                            if d_map:
                                start_idx = m.start()
                                prev_text = ev.text[:start_idx].rstrip()
                                prev_word_m = re.search(r"\b([a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+)$", prev_text)
                                if prev_word_m:
                                    prev_word = prev_word_m.group(1).lower()
                                    if prev_word in {"z", "ze", "przed", "za", "nad", "pod"} and "N" in d_map:
                                        target = d_map["N"]
                                    elif prev_word in {"do", "od", "dla", "bez", "u", "koło", "podczas"} and "D" in d_map:
                                        target = d_map["D"]
                                    elif prev_word in {"ku", "dzięki", "przeciwko"} and "C" in d_map:
                                        target = d_map["C"]
                                    elif prev_word in {"o", "przy"} and ("Ms" in d_map or "MS" in d_map):
                                        target = d_map.get("Ms") or d_map.get("MS")

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
                    if punct == ",":
                        after_text = ev.text[m.end():].lstrip()
                        if re.match(r"\b(?:która|który|której|którego|którym|których|które|jako|czyli|to|oraz|i)\b", after_text, re.IGNORECASE):
                            return m.group(0)
                    if is_inherently_female_name(name) and name.lower().endswith("a"):
                        voc = to_polish_female_vocative(name)
                        if voc != name:
                            fixes.append(f"[Episode Quality Gate - Tarcza Wołacza] Linia #{i+1}: zamiana mianownika na wołacz dla imienia żeńskiego: '{name}' -> '{voc}'")
                            return f"{prefix}{voc}{punct}"
                    return m.group(0)
                ev.text = re.sub(r"(^|[\\\/][Nnh]|\b(?:och|ach|hej|o|ej|halo),?\s+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})([,?!])", _eqg_fem_voc_repl, ev.text)

            # 4g. GENITIVE OF NEGATION & CANON OBLIQUE CASE NORMALIZATION (Filar CLXXXVIII - 0.00 PLN)
            if not is_sign and ev.text:
                from series_memory import sanitize_genitive_of_negation, sanitize_canon_compound_oblique_cases
                old_neg_t = ev.text
                ev.text = sanitize_genitive_of_negation(ev.text)
                if ev.text != old_neg_t:
                    fixes.append(f"[Episode Quality Gate - Filar CLXXXVIII Rekcja Zaprzeczona] Linia #{i+1}: skorygowano biernik na dopełniacz przy zaprzeczeniu -> '{ev.text}'")

                old_obl_t = ev.text
                ev.text = sanitize_canon_compound_oblique_cases(ev.text)
                if ev.text != old_obl_t:
                    fixes.append(f"[Episode Quality Gate - Filar CLXXXVIII Prewencja Mianownizacji Kanonu] Linia #{i+1}: skorygowano zamrożony mianownik terminu po przyimku -> '{ev.text}'")

            # 5. PUNCTUATION & TYPOGRAPHY HYGIENE
            # Purge punctuation collisions: exclamation mark immediately preceding comma (!,) -> comma
            if "!," in ev.text:
                old_punc_t = ev.text
                ev.text = re.sub(r"([A-Za-ząćęłńóśźż])!,\s*", r"\1, ", ev.text)
                if ev.text != old_punc_t and not any(f"Linia #{i+1}:" in f for f in fixes):
                    fixes.append(f"[Episode Quality Gate - Higiena Interpunkcji] Linia #{i+1}: zlikwidowano kolizję interpunkcyjną '!,'")
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
            # Fix hanging comma after ASS line break (e.g. \N, co -> ,\Nco)
            ev.text = re.sub(r"\\N\s*,\s*", r",\\N", ev.text)
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

            # 7c. STRICT SINGLE-LINE AVT OVERFLOW PROTECTION (Belczyk & Netflix AVT: Max 40 znaków)
            if enforce_line_split and not is_sign and r"\N" not in ev.text:
                from avt_formatter import clean_text_for_len, split_subtitle_syntactically
                clean_l = clean_text_for_len(ev.text)
                if len(clean_l) > 40:
                    old_single_text = ev.text
                    ev.text = split_subtitle_syntactically(ev.text, max_line_len=38, is_ass=True, is_sign=False)
                    if ev.text != old_single_text:
                        fixes.append(f"[Episode Quality Gate - Filar LVII (Podział Zbyt Długiej Linii)] Linia #{i+1}: podzielono wers {len(clean_l)} zn. na 2 wersy AVT")

            # 8. META-LEAK FIREWALL & PURGE (Absolute zero tolerance for meta-language in subtitles)
            meta_leak_pat = r"(?i)\b(zgodnie\s+z\s+polskim\s+kanonem\s+avt|kanon(?:em)?\s*avt|kanon\s+avt|filar\s+[ivxlcdm0-9]+|few-shot|system\s*prompt|prompt\s*leak)\b"
            if re.search(meta_leak_pat, ev.text):
                ev.text = re.sub(meta_leak_pat, "", ev.text)
                ev.text = re.sub(r"[ \t]+", " ", ev.text)
                ev.text = re.sub(r"\\N\s+", r"\\N", ev.text)
                ev.text = re.sub(r"\s+\\N", r"\\N", ev.text).strip()
                fixes.append(f"[Episode Quality Gate - ALARM: Wykryto i usunięto wyciek meta-języka AVT] Linia #{i+1}: wyczyszczono frazę meta-kanoniczną")

            # 9. POLISH SUBTITLE CPS MONITORING & FILLER CONDENSATION (Filar CLIV / Aksjomat 2 & 5)
            if not is_sign and ev.end > ev.start:
                ev_dur_s = max((ev.end - ev.start) / 1000.0, 0.5)
                pure_text = cls.get_pure_onscreen_text(ev.text)
                pl_clean_len = len(pure_text)
                pl_cps = pl_clean_len / ev_dur_s

                # Dynamic token-level filler condensation when CPS exceeds recommended ceiling (Aksjomat 2 & Dyrektywa 3)
                if pl_cps > 20.0 and pl_clean_len > 16:
                    condensed_text = cls.condense_filler_words_token_level(ev.text)
                    if condensed_text != ev.text:
                        ev.text = condensed_text
                        pure_text = cls.get_pure_onscreen_text(ev.text)
                        pl_clean_len = len(pure_text)
                        pl_cps = pl_clean_len / ev_dur_s
                        fixes.append(
                            f"[Episode Quality Gate - Filar CLIV/Aksjomat 2 (Kondensacja Waty)] Linia #{i+1}: "
                            f"zredukowano zbędną watę słowną dla wysokiego CPS (nowy CPS: {pl_cps:.1f})"
                        )

                if report_cps_fixes and pl_cps > 22.0:
                    fixes.append(
                        f"[Episode Quality Gate - Filar CLIV (Wysoki CPS)] Linia #{i+1}: "
                        f"tempo czytania {pl_cps:.1f} CPS ({pl_clean_len} zn. na {ev_dur_s:.1f}s) przekracza zalecany limit AVT 17-20 CPS"
                    )

            # Record if text changed due to hygiene
            if ev.text != text_before and not any(f"Linia #{i+1}:" in f for f in fixes):
                fixes.append(f"[Episode Quality Gate - Higiena Tekstu] Linia #{i+1}: oczyszczono interpunkcję i formatowanie")

        return subs, fixes

    @staticmethod
    def get_pure_onscreen_text(raw_text: str) -> str:
        """
        Normalizes ASS line into pure visible onscreen text (Dyrektywa 4 / Aksjomat 5):
        strips override tags {...}, translates \\N and \\h into space, collapses whitespace.
        Ensures reading speed (CPS) is calculated strictly on what the human eye perceives.
        """
        pure_text = re.sub(r"\{[^}]*\}", "", raw_text or "").replace(r"\N", " ").replace(r"\h", " ").strip()
        pure_text = re.sub(r"\s+", " ", pure_text)
        return pure_text

    @staticmethod
    def condense_filler_words_token_level(text: str) -> str:
        """
        Token-level filler condensation with sentence segmentation, capitalization,
        and strict punctuation hygiene (Aksjomat 2 & Dyrektywa 3).
        - Evaluates length (protection <= 2 words) per individual sentence segment (. ! ? …).
        - Short questions/lines like 'Naprawdę?' or 'Po prostu.' are 100% protected.
        - Capitalizes first preserved letter of sentence if initial token was removed.
        - Cleans hanging punctuation: ,, -> ,, spaces before punct, commas before .?!
        """
        if not text:
            return text

        is_leading_continuation = bool(re.match(r"^(\s*\{[^}]*\})*(\.{3,}|…)", text.strip()))

        def _capitalize_after_prefix(s: str) -> str:
            pat = r'^((\s*\{[^}]*\}|\s*[-–—]|\s*\\[Nnh]|\s+)*)([a-ząćęłńóśźż])'
            return re.sub(pat, lambda m: m.group(1) + m.group(3).upper(), s, count=1)

        def _capitalize_all_dialogue_starts(s: str, is_continuation: bool = False) -> str:
            if not is_continuation:
                s = _capitalize_after_prefix(s)
            # Wewnątrz segmentu wielka litera po \N wymaga jawnego myślnika dialogowego (Korekta 1):
            pat_n = r'(\\[Nnh](?:\s*\{[^}]*\})*\s*[-–—]\s*)([a-ząćęłńóśźż])'
            return re.sub(pat_n, lambda m: m.group(1) + m.group(2).upper(), s)

        def _process_segment(seg: str, is_first_text_seg: bool = False) -> str:
            lead_space = ""
            m_lead = re.match(r"^(\s+)", seg)
            if m_lead:
                lead_space = m_lead.group(1)
                seg_body = seg[len(lead_space):]
            else:
                seg_body = seg

            is_cont = is_leading_continuation and is_first_text_seg

            clean_body = re.sub(r'\{[^}]*\}|\\[Nnh]', ' ', seg_body)
            words = re.findall(r'[A-Za-ząćęłńóśźżĄĆĘŁŃÓŚŹŻ0-9]+', clean_body)
            if len(words) <= 2:
                return lead_space + _capitalize_all_dialogue_starts(seg_body, is_continuation=is_cont)

            # len(words) > 2: execute reduction of filler words
            for f in ['po prostu', 'naprawdę', 'naprawde']:
                # Pomiędzy przecinkami: ', po prostu,' -> ','
                seg_body = re.sub(rf'(?i),\s*{re.escape(f)}\s*,', ',', seg_body)
                # Na początku linii, po \N, po myślniku z opcjonalnymi tagami ASS:
                seg_body = re.sub(rf'(?i)(^|[\r\n]|\\N|[-–—]\s*)((?:\{{[^}}]*\}}|\s)*){re.escape(f)}\s*,?\s*', r'\1\2', seg_body)
                # Przed końcem linii/przecinkiem:
                seg_body = re.sub(rf'(?i),\s*{re.escape(f)}(?=[\s\.,?!–—]|$)', '', seg_body)
                # Wewnątrz zdania:
                seg_body = re.sub(rf'(?i)(^|[\s\-,–—]|\\[Nnh]){re.escape(f)}(?=[\s\.,?!–—]|$)', r'\1', seg_body)

            # Punctuation hygiene
            seg_body = re.sub(r',\s*,+', ',', seg_body)
            seg_body = re.sub(r'\s+([,\.!\?…])', r'\1', seg_body)
            seg_body = re.sub(r',\s*([\.!\?…])', r'\1', seg_body)
            seg_body = re.sub(r'(^|[\r\n]|\\N)\s*([-–—])\s*,+\s*', r'\1\2 ', seg_body)
            seg_body = re.sub(r'(^|[\r\n]|\\N)\s*,+\s*', r'\1', seg_body)
            seg_body = re.sub(r'^\s*,\s*', '', seg_body)
            seg_body = re.sub(r'[ \t]+', ' ', seg_body)

            seg_body = _capitalize_all_dialogue_starts(seg_body, is_continuation=is_cont)
            return lead_space + seg_body

        # Split text into sentence segments bounded by . ! ? …
        parts = re.split(r"([\.!\?…]+)", text)
        processed_parts = []
        seen_first_text = False
        for part in parts:
            if re.match(r"^[\.!\?…]+$", part):
                processed_parts.append(part)
            else:
                is_first = False
                if not seen_first_text and part.strip():
                    is_first = True
                    seen_first_text = True
                processed_parts.append(_process_segment(part, is_first_text_seg=is_first))

        out = "".join(processed_parts)
        out = re.sub(r",\s*,+", ",", out)
        out = re.sub(r"\s+([,\.!\?…])", r"\1", out)
        out = re.sub(r",\s*([\.!\?…])", r"\1", out)
        out = re.sub(r"[ \t]+", " ", out)
        out = re.sub(r"\s*\\N\s*", r"\\N", out)
        return out.strip()

    @classmethod
    def get_cps_warnings(cls, subs: Any, max_cps: float = 22.0) -> List[str]:
        """
        Non-destructive Polish AVT reading speed (CPS) auditor (Filar CLIV - 0.00 PLN).
        Identifies lines exceeding recommended AVT thresholds without mutating subtitle text.
        Strips ASS override tags and uses max(duration, 0.5) per Dyrektywy 4 & 5.
        """
        if not subs or not hasattr(subs, "events") or not subs.events:
            return []
        warnings: List[str] = []
        for i, ev in enumerate(subs.events):
            if getattr(ev, "is_comment", False) or ev.end <= ev.start:
                continue
            ev_style_l = (getattr(ev, "style", "") or "").lower()
            if any(tag in ev_style_l for tag in ["sign", "title", "szyld", "napis"]):
                continue
            ev_dur_s = max((ev.end - ev.start) / 1000.0, 0.5)
            pure_text = cls.get_pure_onscreen_text(ev.text or "")
            pl_clean_len = len(pure_text)
            pl_cps = pl_clean_len / ev_dur_s
            if pl_cps > max_cps:
                warnings.append(
                    f"[Episode Quality Gate - Filar CLIV (Wysoki CPS)] Linia #{i+1}: "
                    f"tempo czytania {pl_cps:.1f} CPS ({pl_clean_len} zn. na {ev_dur_s:.1f}s) przekracza zalecany limit AVT 17-20 CPS"
                )
        return warnings


# Bind methods to AVTLinter as well for seamless access
AVTLinter.get_pure_onscreen_text = staticmethod(EpisodeQualityGate.get_pure_onscreen_text)
AVTLinter.condense_filler_words_token_level = staticmethod(EpisodeQualityGate.condense_filler_words_token_level)


