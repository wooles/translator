"""
scene_discourse.py - Discourse Topology, Turn-Taking & Dual-Voice Disambiguation Engine
Architektura Fazy 2 potoku AVT (0.00 PLN Offline).

Odpowiedzialność:
1. DualVoiceTagPreserver & De-merger:
   - Deterministyczne rozbijanie zbiegów dwugłosu ASS:
     Wzorzec: ^((?:\\{[^}]*\\})*)\\s*[-–—]\\s*(.+?)(?:\\\\[Nnh]|\\n)\\s*[-–—]\\s*(.+)$
   - Podział na dwie niezależne mikrokwestie (Sub-A, Sub-B) z zachowaniem tagów formatowania ASS.
   - Rozbijanie etykiet hybrydowych ("A / B", "A / B / C", "A i B") na niezależnych mówców.
   - Bezpieczna rekompozycja: scalanie przetłumaczonych i przelintowanych mikrokwestii
     z powrotem w pojedynczy event ASS z zachowaniem wspólnego timingu i prefixów formatowania.

2. DeicticDiscourseEngine:
   - Rozpoznawanie apostrof do rodziców / zwierzchników ("Ojcze", "Tato", "Chichi-ue", "Otō-san", "Sensei", "Mistrzu").
   - Detekcja repliki rodzica/przełożonego ("Słucham?", "Co jest?", "Co się stało?").
   - Wymuszenie relacji hierarchicznej: Mówca A = dziecko/podwładny, Mówca B = rodzic/przełożony.
   - Wykrywanie ciągłości tematycznej (monolog po dwugłosie bez pauzy montażowej Δt <= 1.5s):
     kontynuacja tematu (np. opis zbroi, pancerza, stroju, technicznych szczegółów) lub F0 >= 220 Hz
     automatycznie przypisuje kolejne kwestie dziecku (np. Shizuku), zapobiegając fałszywej maskulinizacji.

3. DiarizationSanityChecker:
   - Weryfikacja etykiet dorosłych męskich postaci w obecności wybitnie wysokiego tembru F0 seiyū (> 230 Hz bez basu).
   - Generowanie flagi WARNING_DIARIZATION_ANOMALY i arbitraż sceniczny w stronę aktywnej mówczyni żeńskiej (np. Shizuku).
"""

import re
from typing import List, Dict, Any, Tuple, Optional, Set

__all__ = [
    "DualVoiceTagPreserver",
    "DeicticDiscourseEngine",
    "DiarizationSanityChecker",
    "SubtitleDiscourseSanitizer",
    "SpeakerTurn",
    "detect_turn_plural_addressee",
    "group_speaker_turns",
    "resolve_turn_addressee",
    "resolve_all_speaker_turns",
    "process_scene_discourse",
    "is_internal_monologue",
    "resolve_diegetic_persona_gender",
    "has_second_person_markers",
    "resolve_scene_participants",
    "is_character_male",
]


class DualVoiceTagPreserver:
    """
    Deterministyczny rozbijacz i rekompozytor dwugłosów w zdarzeniach ASS (0.00 PLN).
    Chroni tagi formatowania (np. {\\an8}, {\\pos(x,y)}) oraz stylizację fansuberską.
    """

    DUAL_VOICE_STRICT_REGEX = re.compile(
        r"^((?:\{[^}]*\})*)\s*[-–—]\s*(.+?)(?:\\[Nnh]|\n)\s*((?:\{[^}]*\})*)\s*[-–—]\s*(.+)$",
        re.DOTALL
    )

    @classmethod
    def is_dual_voice(cls, text: str) -> bool:
        """
        Sprawdza, czy linia reprezentuje dwugłos (turn-taking z myślnikami w obu wierszach).
        Nie dzieli pojedynczych myślników dialogowych ani pauz intonacyjnych.
        """
        if not text:
            return False
        clean = text.strip()
        return bool(cls.DUAL_VOICE_STRICT_REGEX.match(clean))

    @classmethod
    def de_merge_event(cls, event: Any, orig_idx: int = 0) -> Optional[Tuple[Any, Any, Dict[str, Any]]]:
        """
        Rozbija pojedyncze zdarzenie SSAEvent zawierające dwugłos na dwie mikrokwestie (Sub-A i Sub-B).
        Zwraca (event_a, event_b, metadata) lub None, jeśli zdarzenie nie jest dwugłosem.
        """
        if not hasattr(event, "text") or not event.text:
            return None

        m = cls.DUAL_VOICE_STRICT_REGEX.match(event.text.strip())
        if not m:
            return None

        tags_a = m.group(1) or ""
        line_a = m.group(2).strip()
        tags_b = m.group(3) or ""
        line_b = m.group(4).strip()
        prefix_tags = tags_a

        # Rozbicie etykiety hybrydowej aktora, np. "Yoritsugu Suwa / Yorishige Suwa" -> ("Yoritsugu Suwa", "Yorishige Suwa")
        raw_name = getattr(event, "name", "") or ""
        spk_a = raw_name
        spk_b = raw_name

        if raw_name:
            if "/" in raw_name or "|" in raw_name:
                parts = [p.strip() for p in re.split(r"\s*(?:/|\|)\s*", raw_name) if p.strip()]
                if len(parts) >= 2:
                    spk_a = parts[0]
                    spk_b = parts[1]
            elif " i " in raw_name:
                parts = [p.strip() for p in raw_name.split(" i ") if p.strip()]
                if len(parts) == 2:
                    spk_a = parts[0]
                    spk_b = parts[1]

        ev_a = event.copy()
        ev_a.text = line_a
        ev_a.name = spk_a
        setattr(ev_a, "_is_dual_voice_sub", True)
        setattr(ev_a, "_dual_voice_part", "A")
        setattr(ev_a, "_master_orig_idx", orig_idx)
        setattr(ev_a, "_prefix_tags", tags_a)
        setattr(ev_a, "_tags_a", tags_a)

        ev_b = event.copy()
        ev_b.text = line_b
        ev_b.name = spk_b
        setattr(ev_b, "_is_dual_voice_sub", True)
        setattr(ev_b, "_dual_voice_part", "B")
        setattr(ev_b, "_master_orig_idx", orig_idx)
        setattr(ev_b, "_prefix_tags", tags_b)
        setattr(ev_b, "_tags_b", tags_b)

        meta = {
            "orig_idx": orig_idx,
            "prefix_tags": prefix_tags,
            "tags_a": tags_a,
            "tags_b": tags_b,
            "speaker_a": spk_a,
            "speaker_b": spk_b,
            "raw_name": raw_name,
            "line_a_raw": line_a,
            "line_b_raw": line_b
        }

        return ev_a, ev_b, meta

    @classmethod
    def recompose_text(cls, text_a: str, text_b: str, prefix_tags: str = "", tags_a: str = "", tags_b: str = "") -> str:
        """
        Rekomponuje przetłumaczone kwestie A i B w pojedynczy poprawny format ASS:
        tags_a + "- " + text_a + "\\N" + tags_b + "- " + text_b
        Usuwa nadmiarowe, zduplikowane myślniki i spacje oraz zapobiega zjawisku Style-Bleed.
        """
        clean_a = (text_a or "").strip()
        clean_b = (text_b or "").strip()

        # Usunięcie wiodących myślników, aby nie dopuścić do "-- " lub "- - "
        clean_a = re.sub(r"^[-–—]\s*", "", clean_a).strip()
        clean_b = re.sub(r"^[-–—]\s*", "", clean_b).strip()

        # Oczyszczenie zduplikowanych \N
        clean_a = re.sub(r"\\[Nnh]+", " ", clean_a).strip()
        clean_b = re.sub(r"\\[Nnh]+", " ", clean_b).strip()

        t_a = tags_a.strip() if tags_a else (prefix_tags.strip() if prefix_tags else "")
        t_b = tags_b.strip() if tags_b else ""

        prefix_a = f"{t_a}- " if t_a else "- "
        sep_b = f"{t_b}- " if t_b else "- "
        return f"{prefix_a}{clean_a}\\N{sep_b}{clean_b}".strip()


class DeicticDiscourseEngine:
    """
    Silnik hierarchii dyskursu i inwersji deiktycznej (0.00 PLN).
    Weryfikuje relacje rodzic-dziecko / przełożony-podwładny oraz ciągłość tematyczną monologu.
    """

    APOSTROPHE_PARENT_REGEX = re.compile(
        r"^(?:[-–—]\s*)?(ojcze|tato|chichi(?:-ue)?|ot[oō]-(?:san|sama)|sensei|panie|mistrzu|lordzie)\b",
        re.IGNORECASE
    )

    ACKNOWLEDGMENT_REGEX = re.compile(
        r"^(?:[-–—]\s*)?(słucham|co|co jest|o co chodzi|co się stało|co tam|nani|doushita|nan da)\b",
        re.IGNORECASE
    )

    ARMOR_CRAFTING_TOPIC_REGEX = re.compile(
        r"\b(pancerz\w*|str[oó]j\w*|zbroj\w*|obszy[łl]\w*|połączy[łl]\w*|ubiór\w*|tkanin\w*|szyci\w*|rzemieśl\w*|ochraniacz\w*)\b",
        re.IGNORECASE
    )

    @classmethod
    def resolve_deictic_hierarchy(
        cls,
        text_a: str,
        text_b: str,
        hybrid_speaker: str = "",
        candidate_child: str = "Shizuku",
        candidate_parent: str = "Yorishige Suwa"
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Rozpoznaje zwrot deiktyczny w dwugłosie:
        Głos A: apostrofa do rodzica/przełożonego ("Ojcze.")
        Głos B: replika/potwierdzenie ("Słucham?")
        -> Głos A = dziecko/podwładny (np. Shizuku), Głos B = rodzic/przełożony (np. Yorishige Suwa).
        """
        is_a_apostrophe = bool(cls.APOSTROPHE_PARENT_REGEX.search(text_a.strip()))
        is_b_ack = bool(cls.ACKNOWLEDGMENT_REGEX.search(text_b.strip()))

        discourse_meta = {
            "is_deictic_inversion": False,
            "speaker_a": "",
            "speaker_b": ""
        }

        if is_a_apostrophe and is_b_ack:
            discourse_meta["is_deictic_inversion"] = True
            # Rozbicie hybrydy
            parts = [p.strip() for p in re.split(r"\s*(?:/|\|)\s*", hybrid_speaker) if p.strip()] if hybrid_speaker else []
            
            # Jeśli w hybrydzie jest ojciec (np. Yorishige), przypisujemy go do Głosu B
            spk_b = candidate_parent
            spk_a = candidate_child

            if parts:
                for p in parts:
                    p_low = p.lower()
                    if any(k in p_low for k in ["yorishige", "ojciec", "parent", "father"]):
                        spk_b = p
                    elif any(k in p_low for k in ["shizuku", "córka", "yoritsugu", "dziecko", "child"]):
                        spk_a = p

            discourse_meta["speaker_a"] = spk_a
            discourse_meta["speaker_b"] = spk_b
            return spk_a, spk_b, discourse_meta

        # Fallback standardowy
        parts = [p.strip() for p in re.split(r"\s*(?:/|\|)\s*", hybrid_speaker) if p.strip()] if hybrid_speaker else []
        spk_a = parts[0] if parts else hybrid_speaker
        spk_b = parts[1] if len(parts) > 1 else hybrid_speaker
        discourse_meta["speaker_a"] = spk_a
        discourse_meta["speaker_b"] = spk_b
        return spk_a, spk_b, discourse_meta

    @classmethod
    def audit_monologue_topic_continuation(
        cls,
        text: str,
        last_speaker: str,
        delta_ms: int,
        audio_f0: Optional[float] = None,
        max_delta_ms: int = 1500,
        is_after_acknowledgment: bool = False
    ) -> Optional[str]:
        """
        Weryfikuje ciągłość monologu technicznego po dwugłosie:
        Dwuwektorowa kotwica ciągłości (Topic & Voice Signature Anchor):
        1. Jeśli temat kontynuuje rzemiosło/zbroję (has_topic) lub tembr F0 >= 220 Hz wskazuje głos dziewczęcy,
           utrzymuje tożsamość mówcy (np. Shizuku) niezależnie od przerw montażowych (w tym luki 8.77s).
        2. W przeciwnym razie wymaga bezpośredniego następstwa po replice ojca (Δt <= max_delta_ms).
        """
        has_topic = bool(cls.ARMOR_CRAFTING_TOPIC_REGEX.search(text or ""))
        has_female_f0 = (audio_f0 is not None and audio_f0 >= 220.0)

        if has_topic or has_female_f0:
            return last_speaker

        if delta_ms <= max_delta_ms and is_after_acknowledgment:
            return last_speaker

        return None


class DiarizationSanityChecker:
    """
    Deterministyczny strażnik spójności diaryzacji akustycznej (0.00 PLN).
    Wykrywa anomalie, gdy tag dorosłego mężczyzny jest sprzeczny z ciągłym pasmem F0 > 230 Hz.
    """

    @classmethod
    def audit_speaker_against_prosody(
        cls,
        speaker_name: str,
        f0_hz: Optional[float],
        text: str = "",
        active_scene_female: str = "Shizuku"
    ) -> Dict[str, Any]:
        """
        Sprawdza, czy przypisany dorosły mówca męski nie jest skażeniem błędnej diaryzacji.
        Dla F0 >= 230 Hz u dorosłego mężczyzny zgłasza anomalię i proponuje aktywną mówczynię żeńską.
        """
        result = {
            "is_anomaly": False,
            "warning": None,
            "resolved_speaker": speaker_name,
            "resolved_gender": "mężczyzna"
        }

        spk_low = (speaker_name or "").lower()
        # Ochrona kanonicznych chłopców (Tokiyuki, Conan, etc.)
        from series_memory import BOY_ROLE_KEYWORDS
        is_boy = any(k in spk_low for k in BOY_ROLE_KEYWORDS) or any(k in spk_low for k in ["tokiyuki", "chojumaru", "conan", "naruto"])

        if is_boy:
            # Chłopiec z wysokim F0 to norma biologiczna seiyū, nie anomalia diaryzacji
            result["resolved_speaker"] = speaker_name
            result["resolved_gender"] = "mężczyzna"
            return result

        # Dorosły mężczyzna z wysokim F0 (>= 230 Hz)
        if f0_hz is not None and f0_hz >= 230.0:
            result["is_anomaly"] = True
            result["warning"] = "WARNING_DIARIZATION_ANOMALY"
            result["resolved_speaker"] = active_scene_female or "kobieta"
            result["resolved_gender"] = "kobieta"
            return result

        return result


class SubtitleDiscourseSanitizer:
    """
    Sanitizer napisów i bramka znaków CJK (Zero-Poisoning Subtitle Sanitizer, 0.00 PLN).
    - Odrzuca japońskie cudzysłowy dialogowe 「 」 i 『 』 jako monolog (zawsze mowa na głos).
    - Odrzuca oznaczenia skilli/statusu/szyldów 【 】, 《 》, ［ ］.
    - Automatycznie usuwa didaskalia dźwiękowe [SFX: ...], [Gasp], (screams), szyldy [Sign: ...], [Title: ...].
    - Usuwa notki tłumacza [TL: ...], [T/N: ...], (Note: ...).
    """

    TL_NOTE_REGEX = re.compile(r"\[(?:TL|T/N|Note):.*?\]|\((?:TL|T/N|Note):.*?\)", re.IGNORECASE)
    SFX_AND_SIGNS_REGEX = re.compile(
        r"\[(?:SFX|Gasp|Screams?|Music|Sound|Sign|Title):.*?\]|\((?:gasp|screams?|sighs|crying|groans|applause)\)",
        re.IGNORECASE
    )
    ASS_TAGS_REGEX = re.compile(r"\{[^}]*\}")
    DIALOGUE_QUOTES_REGEX = re.compile(r"[「」『』]")
    SKILL_BRACKETS_REGEX = re.compile(r"[【】《》［］]")

    @classmethod
    def sanitize_subtitles_for_nlp(cls, text: str) -> str:
        """Oczyszcza tekst napisów z notek tłumacza, didaskaliów, szyldów i tagów ASS."""
        if not text:
            return ""
        clean = cls.TL_NOTE_REGEX.sub("", text)
        clean = cls.SFX_AND_SIGNS_REGEX.sub("", clean)
        clean = cls.ASS_TAGS_REGEX.sub("", clean)
        return clean.strip()

    @classmethod
    def is_dialogue_quote(cls, text: str) -> bool:
        """Zwraca True, jeśli linia zawiera japońskie cudzysłowy dialogowe 「 」 lub 『 』 (mowa na głos)."""
        return bool(cls.DIALOGUE_QUOTES_REGEX.search(text or ""))

    @classmethod
    def is_skill_or_system_bracket(cls, text: str) -> bool:
        """Zwraca True, jeśli linia zawiera nawiasy statusu/skilli/szyldów 【 】, 《 》, ［ ］."""
        return bool(cls.SKILL_BRACKETS_REGEX.search(text or ""))


POLISH_COMMON_INTERJECTIONS_STOPLIST: Set[str] = {
    "nie", "tak", "cóż", "ale", "oto", "ach", "och", "hej", "halo", "ej", "o",
    "aha", "no", "naprawdę", "jasne", "dobrze", "zrozumiałem", "rozumiem",
    "chwila", "moment", "uwaga", "stój", "czekaj", "pomocy", "spokojnie",
    "dlaczego", "gdzie", "kiedy", "jak", "kto", "co", "czemu", "tylko", "znowu"
}

VOCATIVE_OUTWARD_TITLES: Set[str] = {
    "mistrzu", "panie", "kapitanie", "królu", "bracie", "chłopcze", "dowódco",
    "ojcze", "tato", "lordzie", "książę", "generale", "stryju", "wuju", "synu",
    "wojowniku", "młodzieńcze", "przyjacielu", "rycerzu", "starcze", "staruszku",
    "pani", "królowo", "siostro", "matko", "mamo", "dziewczyno", "księżniczko",
    "mistrzyni", "córko", "wojowniczko", "przyjaciółko"
}

VOCATIVE_OUTWARD_TITLES_REGEX = re.compile(
    r"(?:^|[\s,–—])(?:" + "|".join(VOCATIVE_OUTWARD_TITLES) + r")(?:[,.!?…\s–—]|$)",
    re.IGNORECASE
)

VOCATIVE_PUNCT_ANCHOR_REGEX = re.compile(
    r"(?:,\s*([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:ie|u|o))[,.!?…\s–—]*$)|"
    r"(?:^([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:ie|u|o))[,!]\s+)|"
    r"(?:,\s*([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:ie|u|o)),)",
    re.UNICODE
)


def _has_outward_vocative(text: str) -> bool:
    """Sprawdza, czy kwestia zawiera wołacz tytułu lub imienia skierowany na zewnątrz."""
    if not text:
        return False
    if VOCATIVE_OUTWARD_TITLES_REGEX.search(text):
        return True
    for m in VOCATIVE_PUNCT_ANCHOR_REGEX.finditer(text):
        name = m.group(1) or m.group(2) or m.group(3)
        if name and name.lower() not in POLISH_COMMON_INTERJECTIONS_STOPLIST:
            return True
    return False


def is_internal_monologue(
    event_or_text: Any,
    target_speaker: Optional[str] = None,
    style: Optional[str] = None
) -> bool:
    """
    Dwuwarstwowa Bramka Monologu Wewnętrznego (Standard 3.0 / 0.00 PLN Offline):
    Kwestia otrzymuje status monologu wewnętrznego (is_internal_monologue = True) według dwóch ścieżek:

    1. Ścieżka Jawnych Nawiasów Myśli i Stylu (Explicit Thought Marker):
       Gdy cała kwestia jest ujęta w nawiasy okrągłe ASCII ( ) lub CJK （ ）
       ALBO ma styl ASS zawierający 'Thought' / 'Internal' / 'Monologue' / 'Myśl',
       zwraca is_internal_monologue = True NIEZALEŻNIE od tego, czy target_speaker w scenie jest ustawiony (!= None)
       (wewnętrzne myśli podczas rozmowy z kimś w scenie zawsze zachowują true_gender).
       Wyjątek: jeśli target_speaker is None, a obiekt zdarzenia ma jawnie zdefiniowany atrybut addressee
       (np. szept skierowany do towarzysza: ev.addressee = 'Braham'), kwestia zostaje odrzucona.

    2. Ścieżka Kursywy {\\i1} (Italic Safety Gate):
       Sama kursywa {\\i1} (bez nawiasów myśli i bez stylu Thoughts) zwraca is_internal_monologue = True
       WYŁĄCZNIE wtedy, gdy:
       - target_speaker is None (brak zdefiniowanego rozmówcy w scenie oraz brak atrybutu addressee/target),
       - styl nie oznacza głosu spoza kadru (Offscreen / Flashback / Retrospekcja / Narration / Voiceover),
       - a tekst nie zawiera wykrzykników ('!', '！') ani wołaczy skierowanych na zewnątrz.

    Przed oceną obu ścieżek bezwzględnie odrzucane są:
    - Japońskie cudzysłowy dialogowe 「 」 i 『 』 (mowa na głos),
    - Nawiasy skilli/statusu/szyldów 【 】, 《 》, ［ ］,
    - Tagi komunikacyjne [Radio], [Phone], [Comm],
    - Czyste didaskalia dźwiękowe i SFX.
    """
    if event_or_text is None:
        return False

    raw_text = getattr(event_or_text, "text", str(event_or_text)) or ""
    if not raw_text.strip():
        return False

    eff_style = style if style is not None else (getattr(event_or_text, "style", "") or "")
    eff_style_low = eff_style.lower()

    # Krok 0: Odrzucenie cudzysłowów dialogowych i nawiasów skilli/systemu
    if SubtitleDiscourseSanitizer.is_dialogue_quote(raw_text):
        return False
    if SubtitleDiscourseSanitizer.is_skill_or_system_bracket(raw_text):
        return False

    # Krok 0b: Odrzucenie prefiksów radiowych/telefonicznych/komunikacyjnych
    if re.search(r"\[(?:Radio|Phone|Comm)\]", raw_text, re.IGNORECASE):
        return False

    # Krok 0c: Odrzucenie czystych tagów SFX / didaskaliów
    if re.search(r"\[(?:SFX|Sound|Music)\]", raw_text, re.IGNORECASE):
        return False

    # Oczyszczenie z tagów ASS dla analizy tekstu
    pure_text = SubtitleDiscourseSanitizer.ASS_TAGS_REGEX.sub("", raw_text).strip()
    if not pure_text:
        return False

    # Odrzucenie didaskaliów dźwiękowych w nawiasach typu (gasp), (screams)
    if re.fullmatch(r"\(\s*(?:gasp|screams?|sighs|crying|groans|applause|sfx.*?)\s*\)", pure_text, re.IGNORECASE):
        return False

    # Wykrycie jawnych nawiasów myśli ASCII ( ) lub CJK （ ） obejmujących całą kwestię
    has_thought_brackets = (
        (pure_text.startswith("(") and pure_text.endswith(")")) or
        (pure_text.startswith("（") and pure_text.endswith("）"))
    )

    # Wykrycie stylu dedykowanego myślom
    has_thought_style = any(k in eff_style_low for k in ["thought", "internal", "monologue", "myśl"])

    # Sprawdzenie jawnego szeptu do towarzysza (addressee na obiekcie przy braku target_speaker w wywołaniu)
    event_addressee = getattr(event_or_text, "addressee", None)
    if event_addressee and target_speaker is None:
        return False

    # =========================================================================
    # ŚCIEŻKA 1: Jawne Nawiasy Myśli i Styl Dedykowany (Explicit Thought Marker)
    # =========================================================================
    if has_thought_brackets or has_thought_style:
        # Myśl w nawiasach lub stylu Thoughts jest monologiem wewnętrznym ZAWSZE,
        # nawet gdy target_speaker != None (rozmowa z kimś w scenie nie niweluje wewnętrznych myśli)
        return True

    # =========================================================================
    # ŚCIEŻKA 2: Kursywa {\i1} (Italic Safety Gate)
    # =========================================================================
    # Sprawdzenie obecności kursywy ASS {\i1} lub stylu kursywy
    has_italics = ("{\\i1}" in raw_text) or ("italic" in eff_style_low)
    if not has_italics:
        return False

    # Bezpiecznik 2a: target_speaker is None (oraz brak addressee/target na obiekcie)
    if target_speaker is not None and str(target_speaker).strip():
        return False
    target_attr = getattr(event_or_text, "target", None)
    if target_attr and str(target_attr).strip():
        return False

    # Bezpiecznik 2b: Styl nie oznacza głosu spoza kadru, retrospekcji ani narracji
    if any(k in eff_style_low for k in [
        "offscreen", "off-screen", "off_screen", "os", "o.s.",
        "flashback", "retrospekcja",
        "narration", "narrator", "narrative",
        "voiceover", "voice-over", "vo", "v.o."
    ]):
        return False

    # Bezpiecznik 2c: Tekst nie zawiera wykrzykników ani wołaczy skierowanych na zewnątrz
    if "!" in pure_text or "！" in pure_text:
        return False

    # Sprawdzenie wołaczy zewnętrznych (tytuły i imiona zawołane na głos)
    if _has_outward_vocative(pure_text):
        return False

    return True


def resolve_diegetic_persona_gender(
    character_identity: Any,
    episode_index: int = 1,
    is_monologue: bool = False,
    audience: Optional[List[str]] = None,
    secret_knowers: Optional[Set[str]] = None
) -> str:
    """
    Rozstrzyga płeć postaci w oparciu o stan diegetyczny, monolog i świadomość tajemnicy (knows_secret):
    - Monolog wewnętrzny: true_gender.
    - Dialog sam na sam z powiernikiem sekretu (len(audience) == 1 i audience[0] in secret_knowers): true_gender.
    - Scena wieloosobowa lub dialog z osobą nieświadomą: apparent_gender (maska publiczna).
    """
    if character_identity is None:
        return "UNKNOWN"

    audience = audience or []
    secret_knowers = {s.lower() for s in (secret_knowers or set())}

    # 1. Monolog wewnętrzny
    if is_monologue:
        return getattr(character_identity, "true_gender", "UNKNOWN")

    # 2. Sam na sam z powiernikiem sekretu
    if len(audience) == 1 and audience[0].lower() in secret_knowers:
        return getattr(character_identity, "true_gender", "UNKNOWN")

    # 3. Scena wieloosobowa lub nieświadomy adresat -> pobierz stan maski dla episode_index
    if hasattr(character_identity, "get_effective_gender"):
        return character_identity.get_effective_gender(
            episode_index=episode_index,
            is_private_confidant=False,
            in_multi_person_scene=(len(audience) > 1),
            is_monologue=False
        )

    return getattr(character_identity, "true_gender", "UNKNOWN")


# =============================================================================
# FILAR 2 & 3: SPEAKER TURN GROUPING, DYADIC TURN-TAKING & PLURAL ADDRESSEE
# =============================================================================

EN_PLURAL_ADDRESSEE_REGEX = re.compile(
    r"\b(?:"
    r"you\s+guys|you\s+all|y'all|you\s+lot|everyone|everybody|listen\s+up|"
    r"all\s+of\s+you|"
    r"your\s+(?:mothers|mommies|mommas|families|parents|lives|heads|homes|weapons|wives|husbands|children|kids|comrades|ancestors|brothers|sisters|folks|clans|souls|swords|shields|lands|troops|men)|"
    r"(?:hey|listen|look|now)?\s*(?:soldiers|warriors|men|folks|people|guards|knights|comrades|brothers|sisters|friends)\b"
    r")",
    re.IGNORECASE
)

JA_PLURAL_ADDRESSEE_REGEX = re.compile(
    r"\b(?:omaera|omae-tachi|omaetachi|kisamara|temeera|temera|kimi-tachi|kimitachi|anata-tachi|anatachi|minna|mina-san|minasan|shokun)\b|"
    r"(?:お前ら|お前達|貴様ら|貴様達|手前ら|君たち|君達|あなた達|皆さん|皆様|諸君|みんな)",
    re.IGNORECASE
)

PL_PLURAL_PRONOUN_REGEX = re.compile(
    r"\b(?:wy|was|wam|wami|wasz|wasza|wasze|waszych|waszym|waszymi|waszą|waszemu)\b",
    re.IGNORECASE
)

PL_PLURAL_PAST_VERB_REGEX = re.compile(
    r"\b[a-ząćęłńóśźż]+(?:liście|łyście)\b",
    re.IGNORECASE
)

PL_PLURAL_PRESENT_VERB_REGEX = re.compile(
    r"\b(?:"
    r"jesteście|będziecie|macie|wiecie|chcecie|możecie|musicie|idziecie|robicie|myślicie|widzicie|słyszycie|"
    r"rozumiecie|znacie|bądźcie|słuchajcie|patrzcie|chodźcie|czekajcie|poddajcie|walczcie|spójrzcie|uważajcie|"
    r"idźcie|powiedzcie|zróbcie|stójcie|bierzcie|dajcie|ratujcie|brońcie|uciekajcie|przestańcie|mówcie|zostawcie|"
    r"tęsknicie|zobaczycie|pamiętajcie|wybaczcie|zaufajcie|powstrzymajcie|pomóżcie|wracajcie|ruszajcie|"
    r"zabijcie|spalcie|zniszczcie|strzeżcie|wstańcie|siadajcie|wierzycie|szukacie|znajdziecie|czujecie|"
    r"przejdźcie"
    r")\b",
    re.IGNORECASE
)

PL_NON_VERB_CIE_WORDS: Set[str] = {
    "życie", "picie", "bicie", "mycie", "szycie", "krycie", "wycie", "bycie",
    "spicie", "odkrycie", "przeżycie", "ubicie", "mieście", "świecie", "lecie",
    "stulecie", "tysiąclecie", "półwiecze", "powiecie", "kwiecie", "aucie",
    "błocie", "złocie", "locie", "płocie", "odlocie", "wylocie", "przylocie",
    "przelocie", "grzbiecie", "pakiecie", "bilecie", "kobiecie", "swecie",
    "komitecie", "kolecie", "namiocie", "zamiecie", "trzecie", "obficie",
    "całkowicie", "należycie", "znakomicie", "sowicie", "rzęsiście", "oczywiście",
    "żywo", "wicie", "poszycie", "przebicie", "podbicie", "rozbicie", "wybicie",
    "nabicie", "zdobycie", "przybycie", "obycie", "zbycie", "korycie", "kopycie",
    "jelicie", "zenicie", "sekrecie", "konkrecie", "balecie", "szkielecie",
    "facecie", "akcie", "kontakcie", "pakcie", "trakcie", "fakcie", "punkcie"
}

PL_GENERAL_CIE_VERB_REGEX = re.compile(r"\b([a-ząćęłńóśźż]{3,})cie\b", re.IGNORECASE)


def detect_turn_plural_addressee(turn_or_text: Any) -> bool:
    """
    Weryfikuje, czy w wypowiedzi lub turze występuje wskaźnik liczby mnogiej adresata (addressee_number = 'PLURAL').
    Obejmuje:
    - EN: you guys, you all, you lot, everyone, listen up, plural vocative, your + [plural people/family/life/weapon],
    - JA: omaera, omae-tachi, kisamara, temeera, kimi-tachi, anata-tachi, minna, mina-san, shokun,
    - PL: zaimek wy/was/wam/wami/wasz, czasownik na -cie / -liście / -łyście.
    """
    if turn_or_text is None:
        return False

    texts: List[str] = []
    if isinstance(turn_or_text, str):
        texts = [turn_or_text]
    elif hasattr(turn_or_text, "lines"):
        texts = turn_or_text.lines
    elif hasattr(turn_or_text, "events"):
        texts = [getattr(ev, "text", str(ev)) or "" for ev in turn_or_text.events]
    elif hasattr(turn_or_text, "text"):
        texts = [getattr(turn_or_text, "text", "") or ""]
    else:
        texts = [str(turn_or_text)]

    for raw in texts:
        if not raw:
            continue
        clean = SubtitleDiscourseSanitizer.ASS_TAGS_REGEX.sub("", raw).strip()
        if not clean:
            continue

        # 1. EN
        if EN_PLURAL_ADDRESSEE_REGEX.search(clean):
            return True

        # 2. JA
        if JA_PLURAL_ADDRESSEE_REGEX.search(clean):
            return True

        # 3. PL zaimki 2. os. lm.
        if PL_PLURAL_PRONOUN_REGEX.search(clean):
            return True

        # 4. PL formy czasu przeszłego (-liście, -łyście)
        if PL_PLURAL_PAST_VERB_REGEX.search(clean):
            return True

        # 5. PL znane czasowniki teraźniejsze i trybu rozkazującego (-cie)
        if PL_PLURAL_PRESENT_VERB_REGEX.search(clean):
            return True

        # 6. PL ogólne czasowniki na -cie z filtrem stoplisty rzeczowników i przyimków
        for m in PL_GENERAL_CIE_VERB_REGEX.finditer(clean):
            word = m.group(0).lower()
            if word not in PL_NON_VERB_CIE_WORDS:
                start_idx = m.start()
                pre_ctx = clean[:start_idx].strip().lower()
                if re.search(r"\b(?:w|we|o|na|po|przy|do|z|ze|od|dla)\s+$", pre_ctx):
                    continue
                return True

    return False


class SpeakerTurn:
    """
    Reprezentacja ciągłej tury wypowiedzi pojedynczego mówcy (SpeakerTurn).
    Grupuje mikrokwestie tego samego aktora oddalone o Δt < 2.5 s (2500 ms).
    Przechowuje topologię adresata: target_speaker, target_gender, addressee_number.
    """
    def __init__(
        self,
        speaker: str = "",
        events: Optional[List[Any]] = None,
        addressee_number: str = "SINGULAR",
        target_speaker: Optional[str] = None,
        target_gender: Optional[str] = None,
        vocative_lock: bool = False,
        scene_id: Optional[str] = None,
        scene_participants: Optional[List[str]] = None,
        scene_has_male_participant: bool = False,
    ):
        self.speaker: str = (speaker or "").strip()
        self.events: List[Any] = list(events or [])
        self.addressee_number: str = addressee_number  # "SINGULAR" | "PLURAL" | "DUAL"
        self.target_speaker: Optional[str] = target_speaker
        self.target_gender: Optional[str] = target_gender  # "MALE" | "FEMALE" | "NEUTRAL"
        self.vocative_lock: bool = vocative_lock
        self.scene_id: Optional[str] = scene_id
        self.scene_participants: List[str] = list(scene_participants or [])
        self.scene_has_male_participant: bool = scene_has_male_participant

        # Automatyczna weryfikacja liczby mnogiej przy inicjalizacji
        if self.events and self.addressee_number == "SINGULAR":
            if detect_turn_plural_addressee(self):
                self.addressee_number = "PLURAL"

    @property
    def target_actor(self) -> Optional[str]:
        return self.target_speaker

    @target_actor.setter
    def target_actor(self, val: Optional[str]):
        self.target_speaker = val

    @property
    def start(self) -> int:
        if self.events and hasattr(self.events[0], "start"):
            return getattr(self.events[0], "start", 0)
        return 0

    @property
    def end(self) -> int:
        if self.events and hasattr(self.events[-1], "end"):
            return getattr(self.events[-1], "end", 0)
        return 0

    @property
    def duration_ms(self) -> int:
        return max(0, self.end - self.start)

    @property
    def lines(self) -> List[str]:
        res = []
        for ev in self.events:
            txt = getattr(ev, "text", str(ev)) or ""
            res.append(txt)
        return res

    @property
    def text(self) -> str:
        return " ".join(self.lines)

    @property
    def is_plural(self) -> bool:
        return self.addressee_number == "PLURAL"

    def append(self, event: Any):
        self.events.append(event)
        if self.addressee_number != "PLURAL" and detect_turn_plural_addressee(event):
            self.addressee_number = "PLURAL"

    def detect_plural_addressee(self) -> bool:
        """Weryfikuje i aktualizuje status addressee_number tury."""
        if detect_turn_plural_addressee(self):
            self.addressee_number = "PLURAL"
            return True
        return False

    @classmethod
    def is_plural_text(cls, text: str) -> bool:
        return detect_turn_plural_addressee(text)

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self):
        return iter(self.events)

    def __getitem__(self, idx: int) -> Any:
        return self.events[idx]

    def compute_scene_participants(
        self,
        all_turns: List["SpeakerTurn"],
        series_bible: Optional[Any] = None,
        window_ms: int = 15000
    ) -> List[str]:
        """Wylicza uczestników sceny i flagę scene_has_male_participant dla bieżącej tury."""
        resolve_scene_participants([self] + [t for t in all_turns if t is not self], series_bible=series_bible, window_ms=window_ms)
        return self.scene_participants

    def __repr__(self) -> str:
        return (
            f"<SpeakerTurn speaker='{self.speaker}' events={len(self.events)} "
            f"target='{self.target_speaker}' gender='{self.target_gender}' "
            f"number='{self.addressee_number}' lock={self.vocative_lock} "
            f"male_in_scene={self.scene_has_male_participant}>"
        )


MASCULINE_VOCATIVE_TITLES_LIST = [
    "mistrzu", "panie", "kapitanie", "królu", "bracie", "chłopcze", "dowódco",
    "ojcze", "tato", "lordzie", "książę", "generale", "stryju", "wuju", "synu",
    "wojowniku", "młodzieńcze", "przyjacielu", "rycerzu", "starcze", "staruszku"
]

FEMININE_VOCATIVE_TITLES_LIST = [
    "pani", "królowo", "siostro", "matko", "mamo", "dziewczyno", "księżniczko",
    "mistrzyni", "córko", "wojowniczko", "przyjaciółko"
]

MASC_TITLE_REGEX = re.compile(
    r"(?:^|[\s,–—])(" + "|".join(MASCULINE_VOCATIVE_TITLES_LIST) + r")(?:[,.!?…\s–—]|$)",
    re.IGNORECASE
)

FEM_TITLE_REGEX = re.compile(
    r"(?:^|[\s,–—])(" + "|".join(FEMININE_VOCATIVE_TITLES_LIST) + r")(?:[,.!?…\s–—]|$)",
    re.IGNORECASE
)

SECOND_PERSON_PRONOUNS_REGEX = re.compile(
    r"\b(?:"
    r"ty|cię|ciebie|tobie|tobą|ci|"
    r"twój|twoja|twoje|twoim|twoich|twoją|twojego|twojemu|twojej|twoimi|"
    r"wy|was|wam|wami|"
    r"wasz|wasza|wasze|waszych|waszym|waszą|waszemu|waszymi|"
    r"you|your|yours|yourself|yourselves|y'all"
    r")\b",
    re.IGNORECASE
)

SECOND_PERSON_PAST_VERBS_REGEX = re.compile(
    r"\b[a-ząćęłńóśźż]+(?:łeś|łaś|łbyś|łabyś|liście|łyście)\b",
    re.IGNORECASE
)

SECOND_PERSON_PRESENT_VERBS_REGEX = re.compile(
    r"\b(?:"
    r"jesteś|będziesz|masz|wiesz|widzisz|słyszysz|czujesz|myślisz|robisz|mówisz|"
    r"znasz|pamiętasz|chcesz|możesz|musisz|wolisz|idziesz|wracasz|stoisz|siedzisz|"
    r"czekasz|patrzysz|bądź|patrz|słuchaj|czekaj|stój|daj|powiedz|zrób|wracaj|"
    r"chodź|bierz|uważaj|wybacz|zrozum|przestań|zostaw|pomóż"
    r")\b",
    re.IGNORECASE
)

MASCULINE_ADDRESS_DESCRIPTOR_REGEX = re.compile(
    r"\b(?:"
    r"niby\s+taki\s+[a-ząćęłńóśźż]+(?:y|i)|"
    r"(?:taki|jaki|jesteś|byłeś|wyglądasz\s+na)\s+[a-ząćęłńóśźż]+(?:y|i)|"
    r"(?:mój|drogi|młody|stary|mądry|dzielny|odważny)\s+(?:panie|chłopcze|mistrzu|bracie|przyjacielu)|"
    r"(?:pan|mężczyzn\w*|facet\w*|chłopak\w*)"
    r")\b",
    re.IGNORECASE
)

ADDRESS_INTERJECTIONS_REGEX = re.compile(
    r"\b(?:hej|ej|ty|słuchaj)\b",
    re.IGNORECASE
)


def has_second_person_markers(turn_or_text: Any) -> bool:
    """Sprawdza, czy w tekście lub turze występują wskaźniki 2. osoby (zaimki, czasowniki, tryb rozkazujący)."""
    if turn_or_text is None:
        return False
    if isinstance(turn_or_text, str):
        texts = [turn_or_text]
    elif hasattr(turn_or_text, "lines"):
        texts = turn_or_text.lines
    elif hasattr(turn_or_text, "events"):
        texts = [getattr(ev, "text", str(ev)) or "" for ev in turn_or_text.events]
    elif hasattr(turn_or_text, "text"):
        texts = [getattr(turn_or_text, "text", "") or ""]
    else:
        texts = [str(turn_or_text)]

    for raw in texts:
        if not raw:
            continue
        clean = SubtitleDiscourseSanitizer.ASS_TAGS_REGEX.sub("", raw).strip()
        if not clean:
            continue
        if SECOND_PERSON_PRONOUNS_REGEX.search(clean):
            return True
        if SECOND_PERSON_PAST_VERBS_REGEX.search(clean):
            return True
        if SECOND_PERSON_PRESENT_VERBS_REGEX.search(clean):
            return True
        if detect_turn_plural_addressee(clean):
            return True
    return False


def _extract_character_candidates_from_bible(
    series_bible: Optional[Any],
    current_speaker: str = ""
) -> Dict[str, Dict[str, Any]]:
    """
    Ekstrahuje zarejestrowane postacie z SeriesBible wraz z formami mianownika, wołacza i płcią.
    Zwraca słownik: {char_name: {"gender": str, "forms": List[str]}}.
    """
    if not series_bible:
        return {}

    candidates: Dict[str, Dict[str, Any]] = {}

    def _register_cand(name: str, gender: Optional[str] = None, vocative: Optional[str] = None):
        if not name or name == current_speaker or "->" in name:
            return
        g = gender
        if not g and hasattr(series_bible, "get_character_gender"):
            g = series_bible.get_character_gender(name)
        if not g and hasattr(series_bible, "get_character_identity"):
            ident = series_bible.get_character_identity(name)
            if ident:
                tg = getattr(ident, "true_gender", "")
                g = "MALE" if tg == "MASCULINE" else ("FEMALE" if tg == "FEMININE" else None)

        norm_g = "MALE" if g in ["MALE", "MASCULINE", "MĘŻCZYZNA", "mężczyzna"] else (
            "FEMALE" if g in ["FEMALE", "FEMININE", "KOBIETA", "kobieta"] else (
                "NEUTRAL" if g in ["NEUTRAL", "BEZPŁCIOWY"] else "UNKNOWN"
            )
        )

        forms = [name]
        parts = name.split()
        if len(parts) > 1 and len(parts[0]) >= 2:
            forms.append(parts[0])
        if vocative and vocative not in forms:
            forms.append(vocative)

        if name not in candidates:
            candidates[name] = {"gender": norm_g, "forms": forms}
        else:
            if candidates[name]["gender"] in ("UNKNOWN", "NEUTRAL") and norm_g not in ("UNKNOWN", "NEUTRAL"):
                candidates[name]["gender"] = norm_g
            for f in forms:
                if f not in candidates[name]["forms"]:
                    candidates[name]["forms"].append(f)

    # 1. Declensions
    decls = (
        series_bible.get_declensions_snapshot()
        if hasattr(series_bible, "get_declensions_snapshot")
        else (getattr(series_bible, "data", {}).get("declensions", {}) if hasattr(series_bible, "data") else {})
    )
    if isinstance(decls, dict):
        for c_name, d_val in decls.items():
            g = d_val.get("gender") if isinstance(d_val, dict) else None
            voc = (d_val.get("W") or d_val.get("vocative")) if isinstance(d_val, dict) else None
            _register_cand(c_name, g, voc)

    # 2. Characters
    chars = (
        series_bible.get_characters_snapshot()
        if hasattr(series_bible, "get_characters_snapshot")
        else (getattr(series_bible, "data", {}).get("characters", {}) if hasattr(series_bible, "data") else {})
    )
    if isinstance(chars, dict):
        for c_name, c_val in chars.items():
            g = c_val.get("gender") if isinstance(c_val, dict) else None
            _register_cand(c_name, g)

    # 3. Character identities
    identities = getattr(series_bible, "character_identities", {})
    if not identities and hasattr(series_bible, "data"):
        identities = series_bible.data.get("character_identities", {})
    if isinstance(identities, dict):
        for c_name, c_val in identities.items():
            tg = getattr(c_val, "true_gender", "") if hasattr(c_val, "true_gender") else (
                c_val.get("true_gender") if isinstance(c_val, dict) else None
            )
            g = "MALE" if tg == "MASCULINE" else ("FEMALE" if tg == "FEMININE" else None)
            _register_cand(c_name, g)

    return candidates


def _detect_turn_vocative(
    turn: SpeakerTurn,
    series_bible: Optional[Any] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Skanuje wszystkie linie tury pod kątem obecności wołacza lub zawołania (tytułu lub imienia).
    Obsługuje:
    - Wołacz lub mianownik znanej postaci męskiej po wykrzyknikach adresatywnych (Hej, Ej, Ty, Słuchaj)
      lub w krótkich zawołaniach zakończonych '!' (np. 'Hej, [Postać]!').
    - Jawne wołacze z paradygmatu deklinacji i snapshotu postaci SeriesBible.
    - Tytuły wołaczowe męskie i żeńskie (Mistrzu, Panie, Pani itp.).
    - Zakotwiczone wołacze interpunkcyjne.
    Zwraca (target_actor, target_gender) lub (None, None).
    """
    lines = turn.lines if hasattr(turn, "lines") else [str(turn)]
    for raw in lines:
        if not raw:
            continue
        clean = SubtitleDiscourseSanitizer.ASS_TAGS_REGEX.sub("", raw).strip()
        if not clean:
            continue

        # 1. Sprawdzenie zarejestrowanych postaci w SeriesBible (jeśli dostępne)
        if series_bible:
            candidates = _extract_character_candidates_from_bible(series_bible, current_speaker=turn.speaker)
            if candidates:
                for char_name, cdata in candidates.items():
                    char_gender = cdata["gender"]
                    forms = cdata["forms"]

                    for cand in forms:
                        if not cand or len(cand) < 2:
                            continue

                        # 1a. Wołacz LUB mianownik po wykrzyknikach adresatywnych (Hej, Ej, Ty, Słuchaj)
                        pat_interj = rf"(?:^|[\s,–—])(?:hej|ej|ty|słuchaj)[,\s]+(?:pana\s+|panie\s+)?{re.escape(cand)}(?:[,.!?…\s–—]|$)"
                        if re.search(pat_interj, clean, re.IGNORECASE):
                            target_g = "MALE" if char_gender == "MALE" else (
                                "FEMALE" if char_gender == "FEMALE" else "NEUTRAL"
                            )
                            return char_name, target_g

                        # 1b. Zawołanie w krótkim okrzyku zakończonym '!'
                        pat_call = rf"(?:^|[\s,–—])(?:(?:hej|ej|ty|słuchaj)[,\s]+)?{re.escape(cand)}\s*!"
                        if re.search(pat_call, clean, re.IGNORECASE):
                            target_g = "MALE" if char_gender == "MALE" else (
                                "FEMALE" if char_gender == "FEMALE" else "NEUTRAL"
                            )
                            return char_name, target_g

                        # 1c. Standardowa granica wołaczowa z interpunkcją lub początkiem/końcem wersu
                        pat_voc = rf"(?:^|[\s,–—]){re.escape(cand)}(?:[,.!?…\s–—]|$)"
                        if re.search(pat_voc, clean, re.IGNORECASE):
                            target_g = "MALE" if char_gender == "MALE" else (
                                "FEMALE" if char_gender == "FEMALE" else "NEUTRAL"
                            )
                            return char_name, target_g

        # 2. Sprawdzenie męskich tytułów wołaczowych (Vocative-Predicate Lock -> MALE)
        m_masc = MASC_TITLE_REGEX.search(clean)
        if m_masc:
            title_word = m_masc.group(1).capitalize()
            return title_word, "MALE"

        # 3. Sprawdzenie żeńskich tytułów wołaczowych (Vocative-Predicate Lock -> FEMALE)
        m_fem = FEM_TITLE_REGEX.search(clean)
        if m_fem:
            title_word = m_fem.group(1).capitalize()
            return title_word, "FEMALE"

        # 4. Sprawdzenie zawołań adresatywnych bez SeriesBible
        m_ai = re.search(
            r"(?:^|[\s,–—])(?:hej|ej|ty|słuchaj)[,\s]+([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)(?:[,.!?…\s–—]|$)",
            clean,
            re.IGNORECASE
        )
        if m_ai:
            matched_name = m_ai.group(1)
            low = matched_name.lower()
            if low not in POLISH_COMMON_INTERJECTIONS_STOPLIST and matched_name != turn.speaker:
                if low.endswith("a") and not low.endswith("ia"):
                    return matched_name, "FEMALE"
                return matched_name, "MALE"

        # 5. Sprawdzenie zakotwiczonych imion w wołaczu bez SeriesBible (np. Rietzie, Brahamie, Arsie, Rayu)
        for m in VOCATIVE_PUNCT_ANCHOR_REGEX.finditer(clean):
            matched_name = m.group(1) or m.group(2) or m.group(3)
            if matched_name and matched_name != turn.speaker:
                low = matched_name.lower()
                if low in POLISH_COMMON_INTERJECTIONS_STOPLIST:
                    continue
                # Końcówki męskie wołacza: -ie (Rietzie, Brahamie, Arsie), -u (Rayu, Mistrzu)
                if low.endswith("ie") or low.endswith("u"):
                    base = re.sub(r"ie$", "", matched_name)
                    return (base if len(base) >= 2 else matched_name), "MALE"
                elif low.endswith("o"):
                    base = re.sub(r"o$", "a", matched_name)
                    return base, "FEMALE"

    return None, None


def is_character_male(
    name: str,
    series_bible: Optional[Any] = None,
    context_item: Optional[Any] = None
) -> bool:
    """Sprawdza deterministycznie, czy dana postać ma płeć MALE."""
    if not name:
        return False
    if series_bible:
        if hasattr(series_bible, "get_character_gender"):
            g = series_bible.get_character_gender(name)
            if g in ("MALE", "MĘŻCZYZNA", "mężczyzna", "MASCULINE"):
                return True
        if hasattr(series_bible, "get_character_identity"):
            ident = series_bible.get_character_identity(name)
            if ident and getattr(ident, "true_gender", "") in ("MASCULINE", "MALE"):
                return True
    if context_item:
        if getattr(context_item, "speaker_gender", None) in ("MALE", "MASCULINE"):
            return True
        if getattr(context_item, "target_gender", None) in ("MALE", "MASCULINE"):
            return True
    return False


def resolve_scene_participants(
    items: List[Any],
    series_bible: Optional[Any] = None,
    window_ms: int = 15000
) -> List[Any]:
    """
    Inwariant Grupy Mieszanej (Standard 4.0 / Klaster B):
    Wylicza aktywnych uczestników sceny w oknie czasowym ±15.0 s (±15000 ms) wokół bieżącej kwestii/tury.
    Jeśli wśród uczestników znajduje się przynajmniej jedna postać o płci MALE,
    ustawia flagę scene_has_male_participant = True na zdarzeniach i turze.
    """
    if not items:
        return items

    for current in items:
        c_start = getattr(current, "start", 0)
        c_end = getattr(current, "end", 0)
        w_start = c_start - window_ms
        w_end = c_end + window_ms

        participants: List[str] = []
        has_male = False

        for other in items:
            o_start = getattr(other, "start", 0)
            o_end = getattr(other, "end", 0)
            if o_end >= w_start and o_start <= w_end:
                spk = (
                    getattr(other, "speaker", None)
                    or getattr(other, "name", None)
                    or getattr(other, "actor", None)
                    or ""
                ).strip()
                if spk and spk not in participants:
                    participants.append(spk)
                    if is_character_male(spk, series_bible=series_bible, context_item=other):
                        has_male = True

                t_spk = getattr(other, "target_speaker", None)
                if t_spk and t_spk not in participants:
                    participants.append(t_spk)
                    if is_character_male(t_spk, series_bible=series_bible, context_item=other):
                        has_male = True

                if getattr(other, "target_gender", None) == "MALE" or getattr(other, "speaker_gender", None) == "MALE":
                    has_male = True

        if hasattr(current, "scene_participants"):
            current.scene_participants = list(participants)
        else:
            setattr(current, "scene_participants", list(participants))

        if hasattr(current, "scene_has_male_participant"):
            current.scene_has_male_participant = has_male
        else:
            setattr(current, "scene_has_male_participant", has_male)

        if hasattr(current, "events"):
            for ev in current.events:
                setattr(ev, "scene_participants", list(participants))
                setattr(ev, "scene_has_male_participant", has_male)

    return items


def resolve_turn_addressee(
    turn: SpeakerTurn,
    previous_turn: Optional[SpeakerTurn] = None,
    series_bible: Optional[Any] = None,
    max_exchange_gap_ms: int = 5000,
    next_turn: Optional[SpeakerTurn] = None,
    prior_turns: Optional[List[SpeakerTurn]] = None
) -> SpeakerTurn:
    """
    Dyadic Turn-Taking (Rozwiązywanie adresata 2. osoby) i Vocative-Predicate Lock:
    - Krok 1 (Jawny Wołacz / Zawołanie): Jeśli w obrębie tury mówcy (SpeakerTurn, Δt < 2.5 s)
      występuje wołacz lub mianownik imienia (po wykrzykniku 'Hej', 'Ej', 'Ty', 'Słuchaj' lub z '!')
      albo tytuł adresatywny, przypisz tę postać jako target_actor (target_gender) dla całej tury.
    - Krok 2 (Lookback): Jeśli tura zawiera formy 2. osoby i brak jawnego wołacza, sprawdź poprzednie
      kwestie mówcy w scenie (Δt < 5.0 s). Jeśli ten sam mówca wcześniej ustalił już męski adresat
      (np. 'Niby taki poważny...'), zachowaj target_gender = 'MALE' na całą wymianę zdań.
    - Krok 3 (Forward Lookahead): Jeśli tura inicjuje wymianę zdań w 2. osobie (np. 'Zaraz. To ty widziałaś...')
      i przed nią brak mówcy, sprawdź mówcę bezpośrednio odpowiadającego w następnej linii (Δt < 3.5 s w tej samej scenie).
      Jeśli odpowiadający mówca ma znaną płeć (np. MALE), przypisz tę płeć jako target_gender dla tury inicjującej.
    - Krok 4 (Wymiana Tur A <-> B): Jeśli brak wołacza ani lookback/lookahead, a mówca A odzywa się bezpośrednio
      po postaci B (Δt < 5.0 s w tej samej scenie), przypisz poprzedniego mówcę B jako target_actor dla A.
    - Vocative-Predicate Lock: Obecność męskiego wołacza (z DeclensionParadigm lub tytułu)
      w obrębie SpeakerTurn bezwzględnie wymusza target_gender = 'MALE' i vocative_lock = True na całą turę.
    """
    if turn is None:
        return turn

    # Krok 1: Weryfikacja jawnego wołacza w obrębie całej tury
    voc_actor, voc_gender = _detect_turn_vocative(turn, series_bible=series_bible)
    if voc_actor and voc_gender:
        turn.target_speaker = voc_actor
        turn.target_gender = voc_gender
        turn.vocative_lock = True
    elif not turn.vocative_lock:
        turn_has_2nd = has_second_person_markers(turn)

        # Krok 2: Lookback (ten sam mówca wcześniej ustalił męski adresat, Δt < 5.0 s)
        lookback_resolved = False
        if turn_has_2nd:
            # 2a. Wcześniejsze kwestie tego samego mówcy w obrębie tury
            if len(turn.events) > 1:
                first_ev = turn.events[0]
                ev_text = getattr(first_ev, "text", "") or ""
                if (
                    getattr(first_ev, "target_gender", None) == "MALE"
                    or MASCULINE_ADDRESS_DESCRIPTOR_REGEX.search(ev_text)
                ):
                    turn.target_gender = "MALE"
                    if getattr(first_ev, "target_speaker", None):
                        turn.target_speaker = getattr(first_ev, "target_speaker")
                    lookback_resolved = True

            # 2b. Poprzednie kwestie tego samego mówcy w scenie (Δt < 5.0 s)
            if not lookback_resolved:
                history = list(prior_turns or [])
                if previous_turn and previous_turn not in history:
                    history.append(previous_turn)

                for prev in reversed(history):
                    if not prev:
                        continue
                    gap_ms = max(0, turn.start - prev.end)
                    if gap_ms > max_exchange_gap_ms:
                        break
                    if prev.speaker == turn.speaker:
                        prev_text = prev.text
                        if (
                            prev.target_gender == "MALE"
                            or MASCULINE_ADDRESS_DESCRIPTOR_REGEX.search(prev_text)
                            or any(getattr(ev, "target_gender", None) == "MALE" for ev in prev.events)
                        ):
                            turn.target_gender = "MALE"
                            if prev.target_speaker:
                                turn.target_speaker = prev.target_speaker
                            lookback_resolved = True
                            break

        # Krok 3: Forward Lookahead (inicjacja wymiany zdań w 2. os., brak mówcy przed, odpowiadający mówca Δt < 3.5 s)
        lookahead_resolved = False
        if not lookback_resolved and turn_has_2nd and turn.target_gender is None:
            no_prior_speaker = (
                previous_turn is None
                or not previous_turn.speaker
                or (turn.start - previous_turn.end > max_exchange_gap_ms)
            )
            if no_prior_speaker and next_turn is not None and next_turn.speaker and next_turn.speaker != turn.speaker:
                forward_gap_ms = next_turn.start - turn.end
                if 0 <= forward_gap_ms <= 3500:
                    resp_speaker = next_turn.speaker
                    resp_gender = None
                    if series_bible and hasattr(series_bible, "get_character_gender"):
                        resp_gender = series_bible.get_character_gender(resp_speaker)
                    if not resp_gender and hasattr(next_turn, "speaker_gender"):
                        resp_gender = next_turn.speaker_gender

                    norm_resp_g = "MALE" if resp_gender in ["MALE", "MĘŻCZYZNA", "mężczyzna", "MASCULINE"] else (
                        "FEMALE" if resp_gender in ["FEMALE", "KOBIETA", "kobieta", "FEMININE"] else None
                    )
                    if norm_resp_g:
                        turn.target_speaker = resp_speaker
                        turn.target_gender = norm_resp_g
                        lookahead_resolved = True

        # Krok 4: Wymiana tur A <-> B (jeśli brak wołacza, lookback i lookahead)
        if not lookback_resolved and not lookahead_resolved and turn.target_speaker is None:
            if (
                previous_turn is not None and
                previous_turn.speaker and
                previous_turn.speaker != turn.speaker
            ):
                gap_ms = max(0, turn.start - previous_turn.end)
                if gap_ms <= max_exchange_gap_ms:
                    turn.target_speaker = previous_turn.speaker
                    if series_bible and hasattr(series_bible, "get_character_gender"):
                        turn.target_gender = series_bible.get_character_gender(previous_turn.speaker)
                    elif hasattr(previous_turn, "speaker_gender") and previous_turn.speaker_gender:
                        turn.target_gender = previous_turn.speaker_gender

    # Wstępna inicjalizacja flagi obecności uczestnika męskiego
    if not turn.scene_has_male_participant:
        if previous_turn:
            turn.compute_scene_participants([previous_turn], series_bible=series_bible)
        elif is_character_male(turn.speaker, series_bible=series_bible, context_item=turn):
            turn.scene_has_male_participant = True
        elif turn.target_gender == "MALE":
            turn.scene_has_male_participant = True

    # Propagacja metadanych dyskursu na wszystkie zdarzenia tury
    for ev in turn.events:
        setattr(ev, "target_speaker", turn.target_speaker)
        setattr(ev, "target_actor", turn.target_speaker)
        setattr(ev, "target_gender", turn.target_gender)
        setattr(ev, "addressee_number", turn.addressee_number)
        setattr(ev, "vocative_lock", turn.vocative_lock)
        setattr(ev, "speaker_turn", turn)
        setattr(ev, "scene_participants", turn.scene_participants)
        setattr(ev, "scene_has_male_participant", turn.scene_has_male_participant)

    return turn


def group_speaker_turns(
    events: List[Any],
    max_gap_ms: int = 2500,
    series_bible: Optional[Any] = None
) -> List[SpeakerTurn]:
    """
    Grupuje ciągłe wypowiedzi tego samego mówcy (Δt < 2.5 s / 2500 ms) w obiekt SpeakerTurn.
    Automatycznie weryfikuje liczbę mnogą adresata dla każdej tury.
    """
    if not events:
        return []

    turns: List[SpeakerTurn] = []
    current_turn: Optional[SpeakerTurn] = None

    for ev in events:
        spk = (
            getattr(ev, "name", "") or
            getattr(ev, "actor", "") or
            getattr(ev, "speaker", "") or
            ""
        ).strip()
        start = getattr(ev, "start", 0)
        end = getattr(ev, "end", 0)

        if current_turn is None:
            current_turn = SpeakerTurn(speaker=spk, events=[ev])
        else:
            gap_ms = start - current_turn.end
            # Jeśli ten sam mówca i przerwa <= max_gap_ms (w tym nakładanie się / gap < 0):
            if spk == current_turn.speaker and gap_ms <= max_gap_ms:
                current_turn.append(ev)
            else:
                turns.append(current_turn)
                current_turn = SpeakerTurn(speaker=spk, events=[ev])

    if current_turn is not None:
        turns.append(current_turn)

    return turns


def resolve_all_speaker_turns(
    turns: List[SpeakerTurn],
    series_bible: Optional[Any] = None,
    max_exchange_gap_ms: int = 5000
) -> List[SpeakerTurn]:
    """Przetwarza sekwencję tur mówców stosując dyadic turn-taking, blokadę wołacza i inwariant grupy mieszanej."""
    for i, turn in enumerate(turns):
        prev_turn = turns[i - 1] if i > 0 else None
        next_turn = turns[i + 1] if i + 1 < len(turns) else None
        resolve_turn_addressee(
            turn,
            previous_turn=prev_turn,
            next_turn=next_turn,
            prior_turns=turns[:i],
            series_bible=series_bible,
            max_exchange_gap_ms=max_exchange_gap_ms
        )

    # Inwariant Grupy Mieszanej: wyliczenie aktywnych uczestników w oknie ±15.0 s
    resolve_scene_participants(turns, series_bible=series_bible, window_ms=15000)
    return turns


def process_scene_discourse(
    events: List[Any],
    series_bible: Optional[Any] = None,
    max_turn_gap_ms: int = 2500,
    max_exchange_gap_ms: int = 5000
) -> List[SpeakerTurn]:
    """Główny punkt wejścia Filaru 2 & 3: grupowanie w tury i rozwiązanie topologii dyskursu."""
    turns = group_speaker_turns(events, max_gap_ms=max_turn_gap_ms, series_bible=series_bible)
    turns = resolve_all_speaker_turns(turns, series_bible=series_bible, max_exchange_gap_ms=max_exchange_gap_ms)
    resolve_scene_participants(events, series_bible=series_bible, window_ms=15000)
    return turns

