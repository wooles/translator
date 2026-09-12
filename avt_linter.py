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
        (r"(^|[^\w]|\\[Nnh])([Nn])ie\s+róbcie\s+sobie\s+nadziei\b", lambda m: f"{m.group(1)}{'Nie liczcie na mnie' if m.group(2).isupper() else 'nie liczcie na mnie'}", "Filar CLXVI - Eliminacja Kalki 'Don't get your hopes up'"),
        (r"(^|[^\w]|\\[Nnh])([Nn])ie\s+rób\s+sobie\s+nadziei\b", lambda m: f"{m.group(1)}{'Nie licz na mnie' if m.group(2).isupper() else 'nie licz na mnie'}", "Filar CLXVI - Eliminacja Kalki 'Don't get your hopes up'"),
        (r"(^|[^\w]|\\[Nnh])([Zz]ginąć\s+)z\s+ręki\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+|kaiju|potwora|bestii|monstrum)\b", r"\g<1>\g<2>od ciosu \g<3>", "Filar CLXVI - Eliminacja Kalki 'die at the hands of [monster]'"),
        (r"(^|[^\w]|\\[Nnh])([Ss]kop(?:ać|cie|my)?)\s+mu\s+tyłek\b", lambda m: f"{m.group(1)}{'Daj mu popalić' if m.group(2)[0].isupper() else 'daj mu popalić'}", "Filar CLXVI - Eliminacja Kalki 'kick his ass'"),
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

        # Anime & Literary Calques (Filary XXV, X, CLXIV, CXXXVII)
        (r"\bcykl(?:u)?\s+inputu\s+i\s+outputu\b", "cykl czerpania inspiracji i tworzenia", "Filar X/I - Żargon Twórczy 'input/output'"),
        (r"\bwięcej\s+inputu\b", "więcej inspiracji", "Filar X/I - Żargon Twórczy 'więcej inputu'"),
        (r"\bInputu(\s*[\?!]+)", r"Inspiracji\1", "Filar X/I - Żargon Twórczy 'Inputu?!'"),
        (r"(?i)(\b|\\N)zapisywa[^\s]*\s+w\s+takim\s+pomys[^\s,]*", r"\1zapisywałaś w nim pomysły", "Filar IV - Kalka Składniowa 'w takim'"),
        (r"(?i)\b([Dd]la mnie|[Pp]oproszę)\s+Gojinka\s+z\s+wodą\b", r"\1 Gojinkę z wodą", "Filar CXXXVII - Biernik Zamówienia 'Gojinkę z wodą'"),
        (r"\bTamaya[!]*", "Ale widok!", "Filar CLXIV - Lokalizacja Okrzyku 'Tamaya!'"),
        (r"\bpanno\s+Teshimo\b", "pani Teshimo", "Filar XXV/CLVI - Tytulatura Szkolna"),
        (r"\bPanno\s+Teshimo\b", "Pani Teshimo", "Filar XXV/CLVI - Tytulatura Szkolna"),
        (r"\bpanny\s+Teshimy\b", "pani Teshimy", "Filar XXV/CLVI - Tytulatura Szkolna"),
        (r"\bPanna\s+Teshima\b", "Pani Teshima", "Filar XXV/CLVI - Tytulatura Szkolna"),
        (r"\bPanno\s+Yasumi\b", "Yasumi", "Filar XXV/CLVI - Tytulatura Szkolna"),
        (r"\bPani\s+Fujimori,\s*ma\s+pani\s+skaner\?", "Fujimori, masz skaner?", "Filar XXV/IX - Tytulatura Rówieśnicza 'Fujimori, masz skaner?'"),
        (r"\bPani\s+Fujimori,\s*spokojnie!", "Fujimori, spokojnie!", "Filar XXV/IX - Tytulatura Rówieśnicza 'Fujimori, spokojnie!'"),
        (r"\bgdy\s+pani\s+Fujimori\s+skończy\b", "gdy Fujimori skończy", "Filar XXV/IX - Tytulatura Rówieśnicza 'gdy Fujimori skończy'"),
        (r"\bZaufaj\s+mi\.", "Proszę mi zaufać.", "Filar XXV/CLVI - Spójność T-V Redaktor-Autor 'Proszę mi zaufać'"),
        (r"\bCo\s+zamierzasz\?", "Co pani zamierza?", "Filar XXV/CLVI - Spójność T-V Redaktor-Autor 'Co pani zamierza?'"),
        (r"\bJeśli\s+chcesz\s+publikować\s+w\s+naszym(?P<sep>\s+|\\N)magazynie,\s*musisz\s+wprowadzić\s+zmiany\b", r"Jeśli chce pani publikować w naszym\g<sep>magazynie, musi pani wprowadzić zmiany", "Filar XXV/CLVI - Spójność T-V Redaktor-Autor"),
        (r"\bWiem,\s*że\s+masz\s+opory\b", "Wiem, że ma pani opory", "Filar XXV/CLVI - Spójność T-V Redaktor-Autor"),
        (r"\bJeśli\s+jesteś\s+na\s+to(?P<sep>\s+|\\N)gotowa,\s*w\s+pełni\s+ci\s+pomogę\b", r"Jeśli jest pani na to\g<sep>gotowa, w pełni pani pomogę", "Filar XXV/CLVI - Spójność T-V Redaktor-Autor"),
        (r"\bTak\s+myślałam,\s*że\s+to\s+powiesz\b", "Tak myślałam, że pani to powie", "Filar XXV/CLVI - Spójność T-V Redaktor-Autor"),
        (r"\bA\s+może\s+spróbujesz\s+w\s+innym\s+magazynie\?", "A może spróbuje pani w innym magazynie?", "Filar XXV/CLVI - Spójność T-V Redaktor-Autor"),
        (r"~[!]+", "!", "Filar LX - Eliminacja Japońskiej Tyldy i Wielokrotnych Wykrzykników"),
        (r"\bodchodzę\s+od\s+zmysłów\s+ze\s+szczęścia\b", "szaleję ze szczęścia", "Filar X - Związek Frazeologiczny (szaleć ze szczęścia, nie odchodzić od zmysłów)"),
        (r"\bOdchodzę\s+od\s+zmysłów\s+ze\s+szczęścia\b", "Szaleję ze szczęścia", "Filar X - Związek Frazeologiczny (szaleć ze szczęścia, nie odchodzić od zmysłów)"),
        (r"\bDwa\s+tysiące\s+w\s+zupełności\s+wystarczy\b", "Dwa tysiące w zupełności wystarczą", "Filar IV - Związek Zgody Liczebnika"),
        (r"\bdwa\s+tysiące\s+w\s+zupełności\s+wystarczy\b", "dwa tysiące w zupełności wystarczą", "Filar IV - Związek Zgody Liczebnika"),
        (r"\bnie\s+mam\s+na\s+kim\s+się(?P<sep>\s+|\\N)+mścić\b", r"nie mam na kim się\g<sep>zemścić", "Filar IV - Aspekt Czasownika 'zemścić'"),
        (r"\bzrobi\s+się\s+tylko\s+groźniej\b", "zrobi się naprawdę niebezpiecznie", "Filar IV - Kalka 'zrobi się groźniej'"),
        (r"\bMniejsza\s+z\s+tym\b", "Mniejsza o to", "Filar X - Idiomatyka"),
        (r"\bmniejsza\s+z\s+tym\b", "mniejsza o to", "Filar X - Idiomatyka"),
        (r"\b(Kronik[a-ząćęłńóśźż]*|Kronice)\s+Kronika\s+Taiheiki\b", r"\1 Taiheiki", "Filar X - Tautologia Słownikowa Kronika Taiheiki"),
        (r"\[\s*KRONIKA\s+Kronika(?:\s+|\\N)+Taiheiki(?:\s+|\\N)+TOM\s+DZIESIĄTY\s*\]", r"[ KRONIKA TAIHEIKI:\\NTOM DZIESIĄTY ]", "Filar X - Tautologia Słownikowa Kronika Taiheiki"),
        (r"\bpowódź\s+piwa\b", "fala piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fala piwa)"),
        (r"\bPowodzi\s+piwa\b", "Fali piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fali piwa)"),
        (r"\bpowodzi\s+piwa\b", "fali piwa", "Filar CXXXVIII - Kolokacja Cieczy (Fali piwa)"),
        (r"\bPowódź\s+wina\b", "Fala wina", "Filar CXXXVIII - Kolokacja Cieczy (Fala wina)"),
        (r"\bpowódź\s+wina\b", "fala wina", "Filar CXXXVIII - Kolokacja Cieczy (Fala wina)"),
        (r"\bPowodzi\s+wina\b", "Fali wina", "Filar CXXXVIII - Kolokacja Cieczy (Fali wina)"),
        (r"\bpowodzi\s+wina\b", "fali wina", "Filar CXXXVIII - Kolokacja Cieczy (Fali wina)"),

        # Clevatess Canon & Heroic Dark Fantasy Lexicon
        (r"\bmoja(?:\s+|\\N)+droga(?:\s+|\\N)+ja\b", "moja ty mała", "Filar X - Kalka Auto-Referencyjna (My Dear Me)"),
        (r"\bMoja(?:\s+|\\N)+droga(?:\s+|\\N)+ja\b", "Moja ty mała", "Filar X - Kalka Auto-Referencyjna (My Dear Me)"),
        (r"\bw\s+cztery(?P<sep>\s+|\\N)+oczy(?:\s+|\\N)+od\s+czasu\b", r"na osobności\g<sep>od czasów", "Filar X - Zniekształcenie Frazeologiczne"),
        (r"\bzrobię(?:\s+|\\N)+raban\b", "wywołam zamieszanie", "Filar X - Rejestr Dark Fantasy (zrobić raban)"),
        (r"\bZrobię(?:\s+|\\N)+raban\b", "Wywołam zamieszanie", "Filar X - Rejestr Dark Fantasy (zrobić raban)"),
        (r"\bzbrzydło(?:\s+|\\N)+mi(?:\s+|\\N)+już(?:\s+|\\N)+szukanie\b", "znudziło mi się już szukanie", "Filar X - Rejestr Dark Fantasy"),
        (r"\bspuścił(?:\s+|\\N)+ci(?:\s+|\\N)+potworny(?:\s+|\\N)+łomot\b", "zmiażdżył cię bez trudu", "Filar X - Rejestr Dark Fantasy (spuścić łomot)"),
        (r"\bmoja(?:\s+|\\N)+sługa(?:\s+|\\N)+mogła(?:\s+|\\N)+uciec\b", "moja podwładna mogła uciec", "Filar IV - Związek Zgody Rodzaju ('moja podwładna')"),
        (r"\bAlyssa\s+Sleihunt\b", "Alicia Sleihunt", "Filar II - Spójność Imienia Bohaterki (Alicia Sleihunt)"),
        (r"\bDla\s+wszystkiego\s+poza(?P<sep>\s+|\\N)roślinami\s+nie\s+ma\s+litości\b", r"Nie ma litości dla niczego prócz\g<sep>roślin", "Filar IV - Kalka Składniowa Wykluczenia"),
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
        (r"\bZavthier(?:\s+|\\N)+od(?:\s+|\\N)+Złudzeń\b", "Zavthier Pani Iluzji", "Filar X - Kalka Przydomka 'no' (Zavthier)"),
        (r"\bVordin(?:\s+|\\N)+od(?:\s+|\\N)+Płomiennego(?:\s+|\\N)+Żaru\b", "Vordin Płomiennego Żaru", "Filar X - Kalka Przydomka 'no' (Vordin)"),
        (r"\bŚwięty(?:\s+|\\N)+Miecza(?:\s+|\\N)+Owenie(?:\s+|\\N)+Koath\b", "Święty Miecza Owenie Koacie", "Filar CLVII - Wołacz Nazwiska (Koacie)"),
        (r"\bciało(?:\s+|\\N)+małej(?:\s+|\\N)+Hidenki\b", "ciało dziewczynki z Hiden", "Filar X - Kalka Etnonimiczna (małej Hidenki)"),
        (r"\bDźgnięto(?:\s+|\\N)+mnie(?:\s+|\\N)+w(?:\s+|\\N)+plecy\b", "Wbito mi nóż w plecy", "Filar X - Kalka Idiomatyczna (Dźgnięto w plecy)"),
        (r"\bten(?:\s+|\\N)+typ(?:\s+|\\N)+z(?:\s+|\\N)+Eslinn\b", "nauczyciel z Eslinn", "Filar X - Rejestr Dark Fantasy (ten typ)"),
        (r"\bTen(?:\s+|\\N)+typ(?:\s+|\\N)+z(?:\s+|\\N)+Eslinn\b", "Nauczyciel z Eslinn", "Filar X - Rejestr Dark Fantasy (ten typ)"),
        (r"\bnie(?:\s+|\\N)+znikniecie(?:\s+|\\N)+z(?:\s+|\\N)+tym,\s*co\b", "nie uciekniecie z tym, co", "Filar X - Kalka Składniowa (zniknąć z tym)"),
        (r"\b(to\s+)?oberwę([!\?…\.]*)$", r"to poniosę karę\2", "Filar X - Rejestr Dark Fantasy (oberwę)"),
        (r"\bPani(?:\s+|\\N)+bohaterko\b", "Pani Bohaterko", "Filar CLVII - Tytulatura Bohaterki"),
        (r"\btrzecia(?:\s+|\\N)+z(?:\s+|\\N)+najlepszych\b", "trzecia pod względem siły", "Filar X - Kalka Składniowa (trzecia z najlepszych)"),
        (r"\bKsięg(a|i|ę|ą)(?:\s+|\\N)+Toah\b", r"Księg\1 Toaha", "Filar IV - Fleksja Dopełniacza (Toaha)"),
        (r"\bBez\s+jaj!?\b", "Niemożliwe!", "Filar X - Rejestr Dark Fantasy (Bez jaj)"),
        (r"\bbez\s+jaj!?\b", "niemożliwe", "Filar X - Rejestr Dark Fantasy (bez jaj)"),
        (r"\b[Gg]uzik\s+mnie\s+to\s+obchodzi\b", lambda m: "Nic mnie to nie obchodzi" if m.group(0)[0].isupper() else "nic mnie to nie obchodzi", "Filar X - Rejestr Dark Fantasy (guzik mnie to obchodzi)"),
        (r"\b([Pp]ora|[Cc]zas)\s+stąd\s+zwiewać\b", r"\1 stąd uciekać", "Filar X - Rejestr Dark Fantasy (pora stąd zwiewać)"),
        (r"\b[Mm]am\s+przez\s+(?:nie|nich)\s+uraz\b", lambda m: "Mam do nich uraz" if m.group(0)[0].isupper() else "mam do nich uraz", "Filar IV - Kalka Składniowa Rządu (uraz przez coś -> uraz do czegoś)"),
        (r"\b[Dd]urna\s+jestem\b", lambda m: "Głupia jestem" if m.group(0)[0].isupper() else "głupia jestem", "Filar X - Stylistyka Monologu (Durna jestem)"),

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

        # Manga canon titular enforcement: 'Książę Kaiju' -> 'Potworny Królewicz' (Filar II / XXIII / Kanon)
        (r"\b[Kk]siążę\s+[Kk]aiju\b", lambda m: "Potworny Królewicz" if m.group(0)[0].isupper() else "potworny królewicz", "Filar XXIII - Kanon Mangi Potworny Królewicz"),
        (r"\b[Kk]sięcia\s+[Kk]aiju\b", lambda m: "Potwornego Królewicza" if m.group(0)[0].isupper() else "potwornego królewicza", "Filar XXIII - Kanon Mangi Potworny Królewicz"),
        (r"\b[Kk]sięciu\s+[Kk]aiju\b", lambda m: "Potwornemu Królewiczowi" if m.group(0)[0].isupper() else "potwornemu królewiczowi", "Filar XXIII - Kanon Mangi Potworny Królewicz"),
        (r"\b[Kk]sięciem\s+[Kk]aiju\b", lambda m: "Potwornym Królewiczem" if m.group(0)[0].isupper() else "potwornym królewiczem", "Filar XXIII - Kanon Mangi Potworny Królewicz"),

        # Otaku slang & honorifics adaptation (Filar II / XXVII)
        (r"\bKuro-?(?:taso|tan)\b", "Kuroe", "Filar II - Slang Otaku Kuro-tan/taso -> Kuroe"),
        (r"\bkuro-?(?:taso|tan)\b", "kuroe", "Filar II - Slang Otaku Kuro-tan/taso -> Kuroe"),
        (r"\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)-(?:senpai|taso|tan)\b", r"\1", "Filar XXVII - Adaptacja Sufiksów Honoryfikatywnych"),

        # Binary alternative comma eradication (Filar LX)
        (r"\b([A-Za-ząćęłńóśźż0-9]+),\s+czy\s+(bez|nie|tak)\b", r"\1 czy \2", "Filar LX - Zakaz Przecinka przed Czy w Alternatywie Rozłącznej"),

        # Trailing cut-off speech attached dash (Filar LX)
        (r"([A-Za-ząćęłńóśźż])[–—\-](?=\s*\\N|\s*$|[!\?…])", r"\1...", "Filar LX - Formatowanie Przerwania Wypowiedzi"),

        # Historical & Fantasy Register Governance & English Calques (Filar IV / CLXVII)
        (r"\b[Dd]obre pytanie\b", lambda m: "Trudno powiedzieć" if m.group(0)[0].isupper() else "trudno powiedzieć", "Filar IV/CLXVII - Eliminacja Angielskiej Kalki 'Good question'"),
        (r"\b[Ww]\s+sumie\s+to\s+nam\s+na\s+rękę\b", lambda m: "W istocie to nam na rękę" if m.group(0)[0].isupper() else "w istocie to nam na rękę", "Filar CLXVII - Puryzm Rejestru Historycznego 'W sumie' -> 'W istocie'"),
        (r"\b[Oo]j\s+tam[!,\?]?\b", lambda m: "Daj spokój" if m.group(0)[0].isupper() else "daj spokój", "Filar CLXVII - Eliminacja Slangu 'Oj tam' w Dramacie Historycznym"),
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

        # 3. Strict glossary overrides (Sanitized from parenthetical notes/brackets & homograph protection)
        if custom_glossary:
            for src, raw_trg in custom_glossary.items():
                if not src or not raw_trg:
                    continue
                src_clean = src.strip()
                # Stopword & safety protection: do not substitute single short words that collide with Polish homographs
                if " " not in src_clean and (len(src_clean) < 3 or src_clean.lower() in {
                    "to", "no", "do", "on", "i", "a", "ja", "ze", "ma", "te", "ta", "co",
                    "ten", "pan", "tam", "dla", "bez", "jak", "sie", "się", "ale", "lub", "czy"
                }):
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

NON_VERBS_ON_ALA = {
    "mała", "biała", "skała", "chwała", "ciała", "pała", "żała", "strzała", "pochwała"
}

NON_VERBS_ON_AL = {
    "kanał", "kryształ", "szał", "wał", "ciał", "dział", "przydział", "rozdział"
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
}

FIRST_PERSON_FEMININE_IRREGULAR_TO_MASCULINE = {
    "poszłam": "poszedłem", "wyszłam": "wyszedłem", "przyszłam": "przyszedłem",
    "odeszłam": "odszedłem", "weszłam": "wszedłem", "przeszłam": "przeszedłem",
    "doszłam": "doszedłem", "zaszłam": "zaszedłem", "zeszłam": "zeszłem",
    "znalazłam": "znalazłem", "mogłabym": "mógłbym", "chciałabym": "chciałbym",
    "wolałabym": "wolałbym", "powinnam": "powinienem", "doniosłabym": "doniósłbym",
    "wzięłam": "wziąłem", "zaczęłam": "zacząłem", "zdjęłam": "zdjąłem",
    "przyjęłam": "przyjąłem", "objąłem": "objąłem", "zajęłam": "zająłem",
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
    elif v_lower.endswith("ałbym"):
        res = v_lower[:-5] + "ałabym"
    elif v_lower.endswith("iłbym"):
        res = v_lower[:-5] + "iłabym"
    elif v_lower.endswith("yłbym"):
        res = v_lower[:-5] + "yłabym"
    elif v_lower.endswith("ułbym"):
        res = v_lower[:-5] + "ułabym"
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
    elif v_lower.endswith("ałabym"):
        res = v_lower[:-6] + "ałbym"
    elif v_lower.endswith("iłabym"):
        res = v_lower[:-6] + "iłbym"
    elif v_lower.endswith("yłabym"):
        res = v_lower[:-6] + "yłbym"
    elif v_lower.endswith("ułabym"):
        res = v_lower[:-6] + "ułbym"
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
}

def convert_2nd_person_masculine_to_feminine(verb: str) -> Optional[str]:
    v_lower = verb.lower()
    if v_lower in MASCULINE_2ND_SG_IRREGULAR_TO_FEMININE:
        res = MASCULINE_2ND_SG_IRREGULAR_TO_FEMININE[v_lower]
        return res.capitalize() if verb[0].isupper() else res

    if v_lower.endswith("ąłeś"):
        res = v_lower[:-4] + "ęłaś"
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

    if v_lower.endswith("ęłaś"):
        res = v_lower[:-4] + "ąłeś"
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
    r"mistrz|mistrza|mistrzowi|mistrzem|mistrzowie|mistrzów|"
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
                cd_sanitized = re.sub(r"zakaz\s+form\s+(?:żeńsk|męsk)[a-ząćęłńóśźż]*", "", cd_lower)
                gen = None
                if any(k in cd_sanitized for k in ["male", "mężczyzna", "chłopak", "męsk"]):
                    gen = "MALE"
                elif any(k in cd_sanitized for k in FEMALE_ROLE_KEYWORDS):
                    gen = "FEMALE"
                if gen:
                    for p in re.split(r"[/,]", cname):
                        clean_p = p.strip()
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
                    clean_ckey = re.sub(r"[\(\[].*?[\)\]]", "", c_key).strip().lower()
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
            "esleburg", "hyderat", "elden", "luna", "dunn", "złudzeń", "złudzenia", "złudzenie", "płomiennego", "żaru", "początku", "kuźni", "świątynia"
        }
        if series_bible and hasattr(series_bible, "data") and "glossary" in series_bible.data:
            for g_k, g_v in series_bible.data["glossary"].items():
                g_str = (str(g_k) + " " + str(g_v)).lower()
                if any(kw in g_str for kw in ["kraina", "królestwo", "lokacja", "kopalnia", "akademia", "chram", "świątynia", "szkoła", "miasto", "rzeka", "góra", "zamek", "twierdza"]):
                    for w in re.findall(r"\b[a-ząćęłńóśźż]{3,}\b", g_str):
                        NON_NAME_ACTORS.add(w)

        all_candidate_chars = set()
        for k in candidate_names:
            all_candidate_chars.add(k.strip())
        if custom_glossary:
            for k, v in custom_glossary.items():
                for name_src in [k, v]:
                    for token in re.findall(r"\b[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,}\b", name_src):
                        tok_l = token.lower()
                        if tok_l not in NON_NAME_ACTORS and not tok_l.endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "em", "iem", "owi", "eń", "ań", "ów", "ich", "ych", "ość", "ości")):
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
                if tok_lower not in NON_NAME_ACTORS and tok_lower not in {
                    "pan", "pani", "niego", "mnie", "ciebie", "nas", "was", "nich", "tego", "tamto", "jeden", "sama", "samo", "sami", "same", "wszystko", "wszyscy", "wszystkich", "cały", "cała", "całe"
                }:
                    # Odrzuć formy już odmienione przypadków zależnych oraz znane formy zależne istniejących postaci
                    if tok_lower in existing_decl_forms:
                        continue
                    if any(tok_lower.startswith(k.lower()) and len(tok_lower) > len(k) for k in character_declensions.keys()):
                        continue
                    if not tok_lower.endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "em", "iem", "owi", "eń", "ań", "ów", "ich", "ych", "ość", "ości")):
                        all_candidate_chars.add(prop_tok)
                        candidate_names.add(tok_lower)

        for cand in all_candidate_chars:
            if not cand or len(cand) < 3 or cand.lower() in NON_NAME_ACTORS:
                continue
            if cand.lower().endswith(("ą", "ę", "ej", "ach", "ami", "om", "ego", "emu", "em", "iem", "owi", "eń", "ań", "ów", "ich", "ych", "ość", "ości")):
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

        # Precompile character declension and vocative patterns once for high-throughput execution
        compiled_decl_rules = []
        if character_declensions:
            for c_name, c_decl in character_declensions.items():
                if not c_name or len(c_name) < 3 or c_name.lower() in NON_NAME_ACTORS or not c_decl or not isinstance(c_decl, dict):
                    continue
                m_form = c_decl.get("M", c_name)
                if not m_form or m_form.lower() in NON_NAME_ACTORS:
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

                compiled_decl_rules.append(rule)

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

                # 1b-2: Isolated physical exertion kakegoe ("Hop...", "I siup...", "Raz, dwa...") -> elision
                m_kakegoe_noise = re.match(r"^([Hh]op[\.!\?…]*|[Ii]\s+siup[\.!\?…]*|[Rr]az,?\s+dwa[\.!\?…]*|[Hh]opla[\.!\?…]*)$", clean_no_tags)
                if m_kakegoe_noise:
                    ev.text = ""
                    fixes.append(f"[Episode Quality Gate - Filar XVIII Elipsa Szumu] Linia #{i+1}: wyciszono infantylny odgłos kinezjatyczny '{clean_no_tags}' do pustego napisu (standard AVT)")

            # 2. THOUGHT-TO-SPEECH BOUNDARY: Strip unsolicited thought italics on plain dialogue lines
            if not is_sign and prev_ev:
                prev_is_thought_style = "italic" in (prev_ev.style or "").lower()
                curr_style_thought = "italic" in (ev.style or "").lower()
                # If previous event was explicitly styled as Italics, and current event is regular Default dialogue, strip artificial {\i1}...{\i0}
                if prev_is_thought_style and not curr_style_thought:
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
                    first_name_in_prev = bool(re.search(
                        r"(?<!\bpanie\s)(?<!\bpani\s)(?<!\bpanno\s)(?<!\bmistrzu\s)(?<!\blordzie\s)\b([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]{2,})[,?!]",
                        prev_clean
                    )) and not has_formal_voc_prev
                    if first_name_in_prev and not has_formal_voc_curr:
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

            # 3b-4. SUBJECT NOMINATIVE CASE REPAIR FOR TITLE APPOSITION (Filar CLVII)
            if not is_sign:
                def _fix_nominative_title_apposition(m):
                    prefix = m.group(1)
                    pan = m.group(2)
                    sep = m.group(3)
                    name_stem = m.group(4)
                    verb = m.group(5)
                    full_name = name_stem + "a"
                    if full_name.lower() in {
                        "akira", "shira", "soma", "gaara", "ashitaka", "kiba", "kenta",
                        "ryoma", "hanza", "koba", "soya", "toma", "genga"
                    }:
                        return m.group(0)
                    fixes.append(f"[Episode Quality Gate - Filar CLVII] Linia #{i+1}: skorygowano skażenie mianownika tytulatury 'pan {full_name}' -> '{pan} {name_stem}'")
                    return f"{prefix}{pan}{sep}{name_stem} {verb}"

                ev.text = re.sub(
                    r"(^|[^\w]|\\[Nnh])([Pp]an)(\s+|\\[Nnh]+)([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]*[bcdfghjklmnprstvwxz])a\s+([a-ząćęłńóśźż]+(?:ł|łby|ła|ło|li|ły))\b",
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
                        def _morph_f_to_m_repl(m):
                            word = m.group(0)
                            converted = convert_first_person_feminine_to_masculine(word)
                            if converted and converted != word:
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano morfologicznie 1. os. '{word}' -> '{converted}' dla mówcy '{ev.name}'")
                                return converted
                            return word
                        ev.text = re.sub(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łam|łabym)\b", _morph_f_to_m_repl, ev.text)
                    elif spk_gen == "FEMALE":
                        for m_pat, f_repl in FIRST_PERSON_MASCULINE_TO_FEMININE:
                            if re.search(m_pat, ev.text, re.IGNORECASE):
                                def _f_case_repl(m, repl=f_repl):
                                    return repl.capitalize() if m.group(0)[0].isupper() else repl
                                ev.text = re.sub(m_pat, _f_case_repl, ev.text, flags=re.IGNORECASE)
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano 1. os. na rodzaj żeński dla mówczyni '{ev.name}'")
                        def _morph_m_to_f_repl(m):
                            word = m.group(0)
                            converted = convert_first_person_masculine_to_feminine(word)
                            if converted and converted != word:
                                fixes.append(f"[Episode Quality Gate - Spójność Płci Postaci] Linia #{i+1}: skorygowano morfologicznie 1. os. '{word}' -> '{converted}' dla mówczyni '{ev.name}'")
                                return converted
                            return word
                        ev.text = re.sub(r"\b[A-ZĄĆĘŁŃÓŚŹŻa-ząćęłńóśźż]+(?:łem|łbym)\b", _morph_m_to_f_repl, ev.text)

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

                    if is_single_female:
                        # 1. Convert masculine 2nd-person singular past verbs (-łeś, poszedłeś, etc.) -> feminine (-łaś, poszłaś)
                        for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+łeś)\b", ev.text)):
                            v_masc = m.group(1)
                            v_fem = convert_2nd_person_masculine_to_feminine(v_masc)
                            if v_fem and v_fem.lower() != v_masc.lower():
                                ev.text = re.sub(rf"\b{re.escape(v_masc)}\b", v_fem, ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Morfologia Żeńska 2. os. lp.] Linia #{i+1}: skorygowano formę męską '{v_masc}' -> '{v_fem}' (adresat: kobieta)")

                        # 2. Convert masculine adjectives / participles -> feminine
                        for m_adj, f_adj in MASCULINE_SG_ADJECTIVES_TO_FEMININE.items():
                            pat_adj = rf"\b((?:byłaś|byłeś|jesteś|bądź|zostałaś|zostałeś|zostań|będziesz|czujesz\s+się|[A-Za-ząćęłńóśźż]+(?:łeś|łaś)(?:\s+\w+)?)\s+)({re.escape(m_adj)})\b"
                            for m in list(re.finditer(pat_adj, ev.text, re.IGNORECASE)):
                                prefix = m.group(1)
                                old_adj = m.group(2)
                                repl_adj = f_adj.capitalize() if old_adj[0].isupper() else f_adj
                                ev.text = re.sub(rf"\b{re.escape(prefix)}{re.escape(old_adj)}\b", f"{prefix}{repl_adj}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Przymiotnik Żeński 2. os. lp.] Linia #{i+1}: skorygowano '{prefix}{old_adj}' -> '{prefix}{repl_adj}' (adresat: kobieta)")

                    elif is_single_male:
                        # 1. Convert feminine 2nd-person singular past verbs (-łaś, poszłaś, etc.) -> masculine (-łeś, poszedłeś)
                        for m in list(re.finditer(r"\b([A-Za-ząćęłńóśźż]+łaś)\b", ev.text)):
                            v_fem = m.group(1)
                            v_masc = convert_2nd_person_feminine_to_masculine(v_fem)
                            if v_masc and v_masc.lower() != v_fem.lower():
                                ev.text = re.sub(rf"\b{re.escape(v_fem)}\b", v_masc, ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Morfologia Męska 2. os. lp.] Linia #{i+1}: skorygowano formę żeńską '{v_fem}' -> '{v_masc}' (adresat: mężczyzna)")

                        # 2. Convert feminine adjectives / participles -> masculine
                        for f_adj, m_adj in FEMININE_SG_ADJECTIVES_TO_MASCULINE.items():
                            pat_adj = rf"\b((?:byłeś|byłaś|jesteś|bądź|zostałeś|zostałaś|zostań|będziesz|czujesz\s+się|[A-Za-ząćęłńóśźż]+(?:łeś|łaś)(?:\s+\w+)?)\s+)({re.escape(f_adj)})\b"
                            for m in list(re.finditer(pat_adj, ev.text, re.IGNORECASE)):
                                prefix = m.group(1)
                                old_adj = m.group(2)
                                repl_adj = m_adj.capitalize() if old_adj[0].isupper() else m_adj
                                ev.text = re.sub(rf"\b{re.escape(prefix)}{re.escape(old_adj)}\b", f"{prefix}{repl_adj}", ev.text, count=1)
                                fixes.append(f"[Episode Quality Gate - Filar CLXIII Przymiotnik Męski 2. os. lp.] Linia #{i+1}: skorygowano '{prefix}{old_adj}' -> '{prefix}{repl_adj}' (adresat: mężczyzna)")

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

            # 3f. MICRO-LINE LENGTH & CPS CLAMPING (< 0.5s / 500ms or extreme verbose micro-lines <= 1.0s)
            line_dur_ms = ev.end - ev.start
            if not is_sign and 0 < line_dur_ms <= 1000:
                clean_t = re.sub(r"\{[^\}]*\}", "", ev.text).strip()
                cl_lower = clean_t.lower()
                repl = None
                if "przecież to o mnie chodzi" in cl_lower:
                    repl = "To o mnie..."
                elif line_dur_ms <= 500 and (len(clean_t) > 14 or len(clean_t.split()) > 3):
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

                if repl and repl != clean_t:
                    # Preserve leading typesetting tags
                    m_prefix = re.match(r"^(\{[^\}]*\})+", ev.text)
                    prefix = m_prefix.group(0) if m_prefix else ""
                    ev.text = f"{prefix}{repl}"
                    fixes.append(f"[Episode Quality Gate - Kompresja Mikro-Kwestii <0.5s/CPS] Linia #{i+1}: skondensowano zbyt długą kwestię ({line_dur_ms}ms, {len(clean_t)} zn.) '{clean_t}' -> '{repl}'")

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
                # Kuro-tan / Kuro-taso -> Kuroe
                if re.search(r"\bKuro-?(?:taso|tan)\b", ev.text, re.IGNORECASE):
                    old_t = ev.text
                    ev.text = re.sub(r"\bKuro-?(?:taso|tan)\b", "Kuroe", ev.text)
                    ev.text = re.sub(r"\bkuro-?(?:taso|tan)\b", "kuroe", ev.text)
                    if ev.text != old_t:
                        fixes.append(f"[Episode Quality Gate - Filar II/XXVII Kanon] Linia #{i+1}: zastąpiono zdrobnienie 'Kuro-tan/taso' kanonicznym imieniem 'Kuroe'")

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

            # 3j. MANGA CANON TITULAR ENFORCEMENT (Filar XXIII / Manga Canon)
            if re.search(r"\bksi(?:ążę|ęcia|ęciu|ęciem)\s+kaiju\b", ev.text, re.IGNORECASE):
                old_t = ev.text
                def _repl_kaiju_prince(m):
                    txt = m.group(0)
                    if re.search(r"książę", txt, re.IGNORECASE):
                        res = "Potworny Królewicz"
                    elif re.search(r"księcia", txt, re.IGNORECASE):
                        res = "Potwornego Królewicza"
                    elif re.search(r"księciu", txt, re.IGNORECASE):
                        res = "Potwornemu Królewiczowi"
                    elif re.search(r"księciem", txt, re.IGNORECASE):
                        res = "Potwornym Królewiczem"
                    else:
                        res = "Potworny Królewicz"
                    if txt.isupper():
                        return res.upper()
                    elif txt[0].isupper():
                        return res
                    else:
                        return res.lower()
                ev.text = re.sub(r"\bksi(?:ążę|ęcia|ęciu|ęciem)\s+kaiju\b", _repl_kaiju_prince, ev.text, flags=re.IGNORECASE)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar XXIII Kanon Mangi] Linia #{i+1}: zastąpiono kalkę 'Książę Kaiju' oficjalnym kanonem 'Potworny Królewicz'")

            # Standalone Vocative Moniker (e.g. "Wypadłeś idealnie, książę!" -> "...królewiczu!")
            is_carameliser_or_prince = False
            if series_bible:
                t_low = getattr(series_bible, "anime_title", "").lower()
                if "caramel" in t_low or "kaiju" in t_low:
                    is_carameliser_or_prince = True
                gloss = getattr(series_bible, "data", {}).get("glossary", {})
                if any("królewicz" in str(v).lower() for v in gloss.values()):
                    is_carameliser_or_prince = True

            if is_carameliser_or_prince and not is_sign:
                if re.search(r"(?:,\s*|\b)[Kk]siążę(?=[!,\?…\.]|\s*$|\s*\\N)", ev.text):
                    old_t = ev.text
                    def _repl_voc_prince(m):
                        txt = m.group(0)
                        prefix = ", " if txt.startswith(",") else ""
                        word = txt.lstrip(", ")
                        repl = "Królewiczu" if word[0].isupper() else "królewiczu"
                        return f"{prefix}{repl}"
                    ev.text = re.sub(r"(,\s*|\b)[Kk]siążę(?=[!,\?…\.]|\s*$|\s*\\N)", _repl_voc_prince, ev.text)
                    if ev.text != old_t:
                        fixes.append(f"[Episode Quality Gate - Filar XXIII Kanon Mangi] Linia #{i+1}: zastąpiono wołacz 'książę' oficjalnym kanonem przydomka 'królewiczu'")

            # Attached Cut-off Dash Sanitizer (Filar LX)
            if not is_sign and re.search(r"([A-Za-ząćęłńóśźż])[–—\-](?=\s*\\N|\s*$|[!\?…])", ev.text):
                old_t = ev.text
                ev.text = re.sub(r"([A-Za-ząćęłńóśźż])[–—\-](?=\s*\\N|\s*$|[!\?…])", r"\1...", ev.text)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar LX Formatowanie Przerwania Wypowiedzi] Linia #{i+1}: zamieniono przyklejony myślnik urwanej kwestii na standardowy wielokropek AVT")

            # 3k. RELACJE SZKOLNE I MENTORSKIE - ANTY-ARCHAIZM "PANNA" (Filar XXV / CLVI / CLXVI)
            if not is_sign:
                old_t = ev.text
                # Rei do Ai / Uczennicy: "Panno Yasumi" -> "Yasumi"
                ev.text = re.sub(r"\bPanno\s+Yasumi\b", "Yasumi", ev.text)
                # Uczennica do Nauczycielki: "panno Teshimo" -> "pani Teshimo"
                ev.text = re.sub(r"\bpanno\s+Teshimo\b", "pani Teshimo", ev.text)
                ev.text = re.sub(r"\bPanno\s+Teshimo\b", "Pani Teshimo", ev.text)
                # O nauczycielce w 3. osobie: "panny Teshimy" -> "pani Teshimy", "Panna Teshima" -> "Pani Teshima"
                ev.text = re.sub(r"\bpanny\s+Teshimy\b", "pani Teshimy", ev.text)
                ev.text = re.sub(r"\bPanna\s+Teshima\b", "Pani Teshima", ev.text)
                # Ogólna reguła szkolna dla nauczycielek/mentorek w wołaczu
                ev.text = re.sub(r"\b([Pp])anno\s+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+-sensei)\b", r"\1ani \2", ev.text)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar XXV/CLVI Tytulatura Szkolna] Linia #{i+1}: skorygowano archaizm 'Panna/Panno' na naturalną formę relacji edukacyjnej")

            # 3l. PROCES TWÓRCZY - ELIMINACJA ŻARGONU IT "INPUT / OUTPUT" (Filar X & I)
            if not is_sign:
                old_t = ev.text
                ev.text = re.sub(r"\bcykl(?:u)?\s+inputu\s+i\s+outputu\b", "cykl czerpania inspiracji i tworzenia", ev.text, flags=re.IGNORECASE)
                ev.text = re.sub(r"\bwięcej\s+inputu\b", "więcej inspiracji", ev.text, flags=re.IGNORECASE)
                ev.text = re.sub(r"\bInputu(\s*[\?!]+)", r"Inspiracji\1", ev.text)
                ev.text = re.sub(r"\binputu\b", "inspiracji", ev.text, flags=re.IGNORECASE)
                ev.text = re.sub(r"\boutputu\b", "tworzenia", ev.text, flags=re.IGNORECASE)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar X/I Żargon Twórczy] Linia #{i+1}: zastąpiono żargon IT 'input/output' naturalnymi pojęciami procesu twórczego")

            # 3m. SKŁADNIA I KALKI ANGIELSKIE - "W TAKIM POMYSŁY" (Filar IV / Belczyk)
            if not is_sign:
                old_t = ev.text
                ev.text = re.sub(r"(\b|\\N)zapisywa[^\s]*\s+w\s+takim\s+pomys[^\s,]*", r"\1zapisywałaś w nim pomysły", ev.text, flags=re.IGNORECASE)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar IV Kalka Składniowa] Linia #{i+1}: skorygowano kalkę eliptyczną 'w takim' -> 'w nim pomysły'")

            # 3n. FLEKSJA ZAMÓWIEŃ GASTRONOMICZNYCH (Filar CXXXVII: Biernik przy zamawianiu)
            if not is_sign:
                old_t = ev.text
                ev.text = re.sub(r"\b(dla mnie|poproszę)\s+Gojinka\s+z\s+wodą\b", r"\1 Gojinkę z wodą", ev.text, flags=re.IGNORECASE)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar CXXXVII Fleksja Zamówień] Linia #{i+1}: skorygowano mianownik na biernik w zamówieniu: 'Gojinkę z wodą'")

            # 3o. LOKALIZACJA JAPOŃSKICH OKRZYKÓW FESTIWALOWYCH / KAKEGOE (Filar CLXIV)
            if not is_sign:
                old_t = ev.text
                ev.text = re.sub(r"\bTamaya[!]*", "Ale widok!", ev.text)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar CLXIV Lokalizacja Okrzyku] Linia #{i+1}: zlokalizowano tradycyjny okrzyk 'Tamaya!' -> 'Ale widok!'")

            # 3p. RELACJE RÓWIEŚNICZE W SZKOLE - DE-FORMALIZACJA "PANI FUJIMORI" (Filar XXV / IX)
            if not is_sign:
                old_t = ev.text
                ev.text = re.sub(r"\bPani\s+Fujimori,\s*ma\s+pani\s+skaner\?", "Fujimori, masz skaner?", ev.text)
                ev.text = re.sub(r"\bPani\s+Fujimori,\s*spokojnie!", "Fujimori, spokojnie!", ev.text)
                ev.text = re.sub(r"\bgdy\s+pani\s+Fujimori\s+skończy\b", "gdy Fujimori skończy", ev.text)
                ev.text = re.sub(r"\bPani\s+Fujimori\b", "Fujimori", ev.text)
                ev.text = re.sub(r"\bpani\s+Fujimori\b", "Fujimori", ev.text)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar XXV/IX Tytulatura Rówieśnicza] Linia #{i+1}: zlikwidowano sztuczną formę 'Pani Fujimori' na rzecz naturalnej relacji koleżeńskiej na 'ty'")

            # 3q. RELACJE ZAWODOWE REDAKTOR-AUTOR - SPÓJNOŚĆ T-V (Filar XXV / CLVI)
            if not is_sign:
                old_t = ev.text
                ev.text = re.sub(r"\bZaufaj\s+mi\b", "Proszę mi zaufać", ev.text)
                ev.text = re.sub(r"\bCo\s+zamierzasz\?", "Co pani zamierza?", ev.text)
                ev.text = re.sub(r"\bJeśli\s+chcesz\s+publikować\s+w\s+naszym(?P<sep>\s+|\\N)magazynie,\s*musisz\s+wprowadzić\s+zmiany\b", r"Jeśli chce pani publikować w naszym\g<sep>magazynie, musi pani wprowadzić zmiany", ev.text)
                ev.text = re.sub(r"\bWiem,\s*że\s+masz\s+opory\b", "Wiem, że ma pani opory", ev.text)
                ev.text = re.sub(r"\bJeśli\s+jesteś\s+na\s+to(?P<sep>\s+|\\N)gotowa,\s*w\s+pełni\s+ci\s+pomogę\b", r"Jeśli jest pani na to\g<sep>gotowa, w pełni pani pomogę", ev.text)
                ev.text = re.sub(r"\bTak\s+myślałam,\s*że\s+to\s+powiesz\b", "Tak myślałam, że pani to powie", ev.text)
                ev.text = re.sub(r"\bA\s+może\s+spróbujesz\s+w\s+innym\s+magazynie\?", "A może spróbuje pani w innym magazynie?", ev.text)
                if ev.text != old_t:
                    fixes.append(f"[Episode Quality Gate - Filar XXV/CLVI Niezmienniczość T-V Redakcji] Linia #{i+1}: ujednolicono formę grzecznościową redaktorki do autorki na formę per 'Pani'")

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
