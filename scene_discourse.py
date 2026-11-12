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
     kontynuacja tematu relacji lub F0 >= 220 Hz
     automatycznie przypisuje kolejne kwestie dziecku, zapobiegając fałszywej maskulinizacji.

3. DiarizationSanityChecker:
   - Weryfikacja etykiet dorosłych męskich postaci w obecności wybitnie wysokiego tembru F0 seiyū (> 230 Hz bez basu).
   - Generowanie flagi WARNING_DIARIZATION_ANOMALY i arbitraż sceniczny w stronę aktywnej mówczyni żeńskiej.
"""

import re
from typing import List, Dict, Any, Tuple, Optional, Set

try:
    from metadata import normalize_actor_tag, normalize_ascii_diacritics
except ImportError:
    import unicodedata

    def normalize_ascii_diacritics(text: str) -> str:
        if not text:
            return ""
        nfkd = unicodedata.normalize("NFKD", str(text))
        return "".join([c for c in nfkd if not unicodedata.combining(c)])

    def normalize_actor_tag(actor_name: str) -> Tuple[str, Optional[str]]:
        """
        Normalizuje znacznik aktora (usuwa adnotacje nawiasowe)
        oraz ekstrahuje jawną płeć jeśli obecna (MALE / FEMALE).
        """
        if not actor_name:
            return "", None
        raw = str(actor_name).strip()
        gender = None
        if re.search(r"[\(\[\{]\s*(?:m|male|mężczyzna)\s*[\)\]\}]", raw, re.IGNORECASE):
            is_glued_single_m = bool(re.search(r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]\(\s*m\s*\)$", raw, re.IGNORECASE))
            if not is_glued_single_m:
                gender = "MALE"
        elif re.search(r"[\(\[\{]\s*(?:f|female|kobieta)\s*[\)\]\}]", raw, re.IGNORECASE):
            gender = "FEMALE"
        clean = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", "", raw).strip()
        return (clean or raw), gender


def _normalize_event_actor(raw_name: str) -> Tuple[str, Optional[str]]:
    """Wywołuje normalize_actor_tag i zabezpiecza ekstrakcję czystej nazwy oraz płci P0."""
    if not raw_name:
        return "", None
    try:
        res = normalize_actor_tag(raw_name)
        if isinstance(res, tuple):
            c_name = res[0]
            g = res[1] if len(res) > 1 else None
            return (c_name or raw_name).strip(), g
        elif isinstance(res, dict):
            c_name = res.get("name", raw_name)
            g = res.get("gender")
            return (c_name or raw_name).strip(), g
        elif isinstance(res, str):
            g = None
            if re.search(r"[\(\[\{]\s*(?:m|male|mężczyzna)\s*[\)\]\}]", raw_name, re.IGNORECASE):
                is_glued_single_m = bool(re.search(r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]\(\s*m\s*\)$", raw_name.strip(), re.IGNORECASE))
                if not is_glued_single_m:
                    g = "MALE"
            elif re.search(r"[\(\[\{]\s*(?:f|female|kobieta)\s*[\)\]\}]", raw_name, re.IGNORECASE):
                g = "FEMALE"
            return res.strip() or raw_name.strip(), g
    except Exception:
        pass

    g = None
    if re.search(r"[\(\[\{]\s*(?:m|male|mężczyzna)\s*[\)\]\}]", raw_name, re.IGNORECASE):
        is_glued_single_m = bool(re.search(r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]\(\s*m\s*\)$", raw_name.strip(), re.IGNORECASE))
        if not is_glued_single_m:
            g = "MALE"
    elif re.search(r"[\(\[\{]\s*(?:f|female|kobieta)\s*[\)\]\}]", raw_name, re.IGNORECASE):
        g = "FEMALE"
    clean = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", "", raw_name).strip()
    return clean or raw_name.strip(), g


__all__ = tuple(
    "DualVoiceTagPreserver DeicticDiscourseEngine DiarizationSanityChecker SubtitleDiscourseSanitizer "
    "SpeakerTurn SubTurn detect_turn_plural_addressee detect_plural_addressee is_plural_text "
    "is_addressee_pivot partition_subturns compute_we_group classify_we_group_gender compute_you_group "
    "classify_you_group_gender group_speaker_turns resolve_turn_addressee resolve_all_speaker_turns "
    "process_scene_discourse is_internal_monologue resolve_diegetic_persona_gender has_second_person_markers "
    "resolve_scene_participants is_character_male is_character_female is_character_confirmed_female "
    "is_singular_2nd_person_line is_discourse_ignorable is_narrative_style is_sign_or_title_item "
    "is_offscreen_or_voiceover normalize_actor_tag".split()
)



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

        # Rozbicie etykiety hybrydowej aktora w formacie złożonym przez ukośnik lub kreskę pionową
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
        candidate_child: str = "",
        candidate_parent: str = "",
        series_bible: Optional[Any] = None
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Rozpoznaje zwrot deiktyczny w dwugłosie:
        Głos A: apostrofa do rodzica/przełożonego ("Ojcze.")
        Głos B: replika/potwierdzenie ("Słucham?")
        -> Głos A = dziecko/podwładny, Głos B = rodzic/przełożony.
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
            
            # Hierarchia rodzic/przełożony vs dziecko/podwładny
            spk_b = candidate_parent
            spk_a = candidate_child

            parent_keywords = ["ojciec", "parent", "father", "lord", "master", "przełożony", "rodzic"]
            child_keywords = ["córka", "syn", "dziecko", "child", "daughter", "son", "podwładny", "uczeń"]

            if series_bible and hasattr(series_bible, "data") and "characters" in series_bible.data:
                chars = series_bible.data["characters"]
                for p in parts:
                    c_info = chars.get(p, {})
                    desc = (c_info.get("description", "") if isinstance(c_info, dict) else str(c_info)).lower()
                    if any(kw in desc for kw in parent_keywords):
                        spk_b = p
                    elif any(kw in desc for kw in child_keywords):
                        spk_a = p

            if parts:
                for p in parts:
                    p_low = p.lower()
                    if any(k in p_low for k in parent_keywords):
                        spk_b = p
                    elif any(k in p_low for k in child_keywords):
                        spk_a = p

            if not spk_b and parts:
                spk_b = parts[1] if len(parts) > 1 else parts[0]
            if not spk_a and parts:
                spk_a = parts[0]

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
           utrzymuje tożsamość mówcy niezależnie od przerw montażowych (w tym luki 8.77s).
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
        active_scene_female: str = ""
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
        # Ochrona kanonicznych ról chłopięcych (młodzi chłopcy z wysokim F0)
        from series_memory import BOY_ROLE_KEYWORDS
        is_boy = any(k in spk_low for k in BOY_ROLE_KEYWORDS) or any(k in spk_low for k in ["chłopiec", "boy", "kid", "dziecko"])

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
    "dlaczego", "gdzie", "kiedy", "jak", "kto", "co", "czemu", "tylko", "znowu",
    "to", "tam", "tu", "ten", "ta", "te", "też", "już", "przecież", "nawet", "chyba", "może", "zaraz", "właśnie"
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
       (gdy wypowiedź skierowano do towarzysza w kadrze), kwestia zostaje odrzucona.

    2. Ścieżka Kursywy {\\i1} (Italic Safety Gate):
       Sama kursywa {\\i1} (bez nawiasów myśli i bez stylu Thoughts) zwraca is_internal_monologue = True
       WYŁĄCZNIE wtedy, gdy:
       - target_speaker is None (brak zdefiniowanego rozmówcy w scenie oraz brak atrybutu addressee/target),
       - styl nie oznacza głosu spoza kadru (Offscreen / Flashback / Retrospekcja / Narration / Voiceover),
       - a tekst nie zawiera wykrzykników ('!', '！') ani wołaczy skierowanych na zewnątrz.

    Przed oceną obu ścieżek standardowo odrzucane są:
    - Japońskie cudzysłowy dialogowe 「 」 i 『 』 (mowa na głos),
    - Nawiasy skilli/statusu/szyldów 【 】, 《 》, ［ ］,
    - Tagi komunikacyjne [Radio], [Phone], [Comm],
    - Czyste didaskalia dźwiękowe i SFX.
    """
    if event_or_text is None:
        return False

    if hasattr(event_or_text, "events") and hasattr(event_or_text, "lines"):
        if not event_or_text.events:
            return False
        return all(is_internal_monologue(ev, target_speaker=target_speaker, style=style) for ev in event_or_text.events)

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

    # Bezpiecznik 2d: Odrzucenie znaczników 2. osoby (has_second_person_markers)
    if has_second_person_markers(pure_text):
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
    "spicie", "odkrycie", "przeżycie", "ubicie", "stulecie", "tysiąclecie", "półwiecze",
    "obficie", "całkowicie", "należycie", "znakomicie", "sowicie", "rzęsiście", "oczywiście",
    "żywo", "wicie", "poszycie", "przebicie", "podbicie", "rozbicie", "wybicie",
    "nabicie", "zdobycie", "przybycie", "obycie", "zbycie", "trzecie",
    "uczucie", "poczucie", "wyczucie", "odczucie", "pojęcie", "zajęcie", "przyjęcie",
    "ujęcie", "objęcie", "napięcie", "cięcie",
    "wreszcie", "nareszcie", "jednocześnie", "osobiście", "rzeczywiście", "uroczyście",
    "wieczyście", "ziemiście", "kwieciście", "chętnie", "prawomocnie"
}

POLISH_COMMON_NOUN_LOCATIVE_HOMONYMS: Set[str] = {
    "mieście", "świecie", "lecie", "powiecie", "kwiecie", "aucie",
    "błocie", "złocie", "locie", "płocie", "odlocie", "wylocie", "przylocie",
    "przelocie", "grzbiecie", "pakiecie", "bilecie", "kobiecie", "swecie",
    "komitecie", "kolecie", "namiocie", "zamiecie", "korycie", "kopycie",
    "jelicie", "zenicie", "sekrecie", "konkrecie", "balecie", "szkielecie",
    "facecie", "akcie", "kontakcie", "pakcie", "trakcie", "fakcie", "punkcie",
    "momencie", "prezydencie", "studencie", "dokumencie", "projekcie", "obiekcie",
    "internecie", "temacie", "klimacie", "froncie", "koncercie", "porcie",
    "szczycie", "zeszycie", "suficie", "aparacie", "formacie", "kwadracie",
    "buncie", "komplecie", "aspekcie", "efekcie", "tekście", "kontekście",
    "respekcie", "gabinecie", "interwale"
}

PL_GENERAL_CIE_VERB_REGEX = re.compile(r"\b([a-ząćęłńóśźż]{3,})cie\b", re.IGNORECASE)


def detect_turn_plural_addressee(turn_or_text: Any) -> bool:
    """
    Weryfikuje, czy w wypowiedzi lub turze występuje wskaźnik liczby mnogiej adresata (addressee_number = 'PLURAL').
    Obejmuje:
    - EN: you guys, you all, you lot, everyone, listen up, plural vocative, your + [plural people/family/life/weapon],
    - JA: omaera, omae-tachi, kisamara, temeera, kimi-tachi, anata-tachi, minna, mina-san, shokun,
    - PL: zaimek wy/was/wam/wami/wasz, czasownik na -cie / -liście / -łyście ze Strażnikiem Miejscownika.
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

        # 6. PL ogólne czasowniki na -cie z filtrem stoplisty rzeczowników i Strażnikiem Miejscownika
        for m in PL_GENERAL_CIE_VERB_REGEX.finditer(clean):
            word = m.group(0).lower()
            if word in PL_NON_VERB_CIE_WORDS:
                continue
            start_idx = m.start()
            pre_ctx = clean[:start_idx].strip().lower()
            # Strażnik Homonimii Miejscownika:
            # Wyklucz rzeczowniki w miejscowniku po przyimkach (w, we, o, na, po, przy, do, z, ze, od, dla itd.)
            if re.search(r"\b(?:w|we|o|na|po|przy|do|z|ze|od|dla|ku|bez|pod|nad|przed|za|między|pomiędzy|wobec|podczas|wskutek|dzięki|koło|obok|wśród|blisko|wzdłuż)\s+(?:[a-ząćęłńóśźż0-9„\"'«»–—-]+\s+)*$", pre_ctx):
                continue
            if word in POLISH_COMMON_NOUN_LOCATIVE_HOMONYMS:
                # Wymagaj jawnego kontekstu czasownikowego / pytającego / zaimkowego 2. osoby
                if not re.search(r"\b(?:wy|co|kiedy|jak|czy|tam|to)\s+$", pre_ctx) and not re.search(r"^(?:wy|co|kiedy|jak|czy)\b", clean, re.IGNORECASE):
                    continue
            return True

    return False


def detect_plural_addressee(turn_or_text: Any) -> bool:
    """Weryfikuje, czy w wypowiedzi lub turze występuje wskaźnik liczby mnogiej adresata."""
    return detect_turn_plural_addressee(turn_or_text)


def is_plural_text(text: str) -> bool:
    """Sprawdza obecność wykładnika liczby mnogiej w tekście ze strażnikiem homonimii miejscownika."""
    return detect_plural_addressee(text)


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
        target_confidence: float = 0.0,
        plural_group_gender: str = "AMBIGUOUS",
        you_group_gender: str = "AMBIGUOUS",
    ):
        clean_spk, tag_g = _normalize_event_actor(speaker)
        self.speaker: str = (clean_spk or speaker or "").strip()
        self.events: List[Any] = list(events or [])
        self.addressee_number: str = addressee_number  # "SINGULAR" | "PLURAL" | "DUAL"
        self.target_speaker: Optional[str] = target_speaker
        self.target_gender: Optional[str] = target_gender  # "MALE" | "FEMALE" | "NEUTRAL"
        self.vocative_lock: bool = vocative_lock
        self.scene_id: Optional[str] = scene_id
        self.scene_participants: List[str] = list(scene_participants or [])
        self.scene_has_male_participant: bool = scene_has_male_participant
        if tag_g == "MALE":
            self.scene_has_male_participant = True
        self.target_confidence: float = target_confidence
        self.plural_group_gender: str = plural_group_gender
        self.you_group_gender: str = you_group_gender
        self.sub_turns: List["SpeakerTurn"] = [self]

        for ev in self.events:
            ev_raw = getattr(ev, "name", getattr(ev, "speaker", "")) or ""
            if ev_raw:
                ev_clean, ev_g = _normalize_event_actor(ev_raw)
                if ev_g in ("MALE", "FEMALE"):
                    setattr(ev, "speaker_gender", ev_g)
                    setattr(ev, "speaker_confidence", 1.0)
                    if ev_g == "MALE":
                        self.scene_has_male_participant = True

        # Automatyczna weryfikacja liczby mnogiej przy inicjalizacji
        if self.events and self.addressee_number == "SINGULAR":
            if detect_plural_addressee(self):
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
        ev_raw = getattr(event, "name", getattr(event, "speaker", "")) or ""
        if ev_raw:
            ev_clean, ev_g = _normalize_event_actor(ev_raw)
            if ev_g in ("MALE", "FEMALE"):
                setattr(event, "speaker_gender", ev_g)
                setattr(event, "speaker_confidence", 1.0)
                if ev_g == "MALE":
                    self.scene_has_male_participant = True
        self.events.append(event)
        if self.addressee_number != "PLURAL" and detect_plural_addressee(event):
            self.addressee_number = "PLURAL"

    def detect_plural_addressee(self) -> bool:
        """Weryfikuje i aktualizuje status addressee_number tury."""
        if detect_plural_addressee(self):
            self.addressee_number = "PLURAL"
            return True
        return False

    @classmethod
    def is_plural_text(cls, text: str) -> bool:
        return is_plural_text(text)

    def partition_subturns(self, series_bible: Optional[Any] = None) -> List["SpeakerTurn"]:
        """Dzieli turę na pod-segmenty (SubTurn) na granicach Addressee Pivot."""
        return partition_subturns(self, series_bible=series_bible)

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
        tgt_val = self.target_speaker if self.target_speaker is not None else "UNSPECIFIED"
        gen_val = self.target_gender if self.target_gender is not None else "UNSPECIFIED"
        you_val = self.you_group_gender
        if you_val in (None, "AMBIGUOUS"):
            you_val = "VIRILE" if self.scene_has_male_participant else "UNSPECIFIED"
        grp_val = self.plural_group_gender
        if grp_val in (None, "AMBIGUOUS"):
            grp_val = "VIRILE" if self.scene_has_male_participant else "UNSPECIFIED"
        return (
            f"<SpeakerTurn speaker='{self.speaker}' events={len(self.events)} "
            f"duration={self.duration_ms}ms target='{tgt_val}' "
            f"gender='{gen_val}' conf={self.target_confidence:.2f} "
            f"number='{self.addressee_number}' plural={self.is_plural} "
            f"lock={self.vocative_lock} male_in_scene={self.scene_has_male_participant} "
            f"group_gender='{grp_val}' you_group='{you_val}'>"
        )


class SubTurn(SpeakerTurn):
    """
    Pod-segment tury mówcy (SubTurn) wyodrębniony w wyniku wystąpienia Addressee Pivot.
    """
    pass


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

        g_l = (g or "").lower()
        norm_g = "MALE" if g_l in ("male", "masculine", "mężczyzna") else (
            "FEMALE" if g_l in ("female", "feminine", "kobieta") else (
                "NEUTRAL" if g_l in ("neutral", "bezpłciowy") else "UNKNOWN"
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

    # 4. Hypocorisms
    data = getattr(series_bible, "data", {}) if hasattr(series_bible, "data") else {}
    hypo = data.get("hypocorisms", {}) if isinstance(data, dict) else {}
    if isinstance(hypo, dict):
        for h_alias, h_canon in hypo.items():
            if h_canon in candidates:
                if h_alias not in candidates[h_canon]["forms"]:
                    candidates[h_canon]["forms"].append(h_alias)
            else:
                _register_cand(h_canon)
                if h_canon in candidates and h_alias not in candidates[h_canon]["forms"]:
                    candidates[h_canon]["forms"].append(h_alias)

    # 5. Character aliases
    if isinstance(chars, dict):
        for c_name, c_val in chars.items():
            if isinstance(c_val, dict):
                aliases = c_val.get("aliases") or []
                if isinstance(aliases, list):
                    for al in aliases:
                        if c_name in candidates and al not in candidates[c_name]["forms"]:
                            candidates[c_name]["forms"].append(al)

    return candidates


_GENERIC_ROLE_TITLES: Set[str] = {
    "pan", "pani", "lord", "lady", "sir", "kapitan", "król", "królowa", "książę",
    "księżniczka", "mistrz", "mistrzyni", "doktor", "profesor", "ojciec", "matka",
    "brat", "siostra", "generał", "von", "van", "de", "the", "san", "sama", "kun",
    "chan", "senpai"
}

PL_1ST_PERSON_MASC_VERB_REGEX = re.compile(
    r"\b(?:"
    r"[a-ząćęłńóśźż]+(?:iłem|yłem|ałem|nąłem|ułem|szedłem|złem|głem|łbym)|"
    r"byłem|miałem|chciałem|wiedziałem|widziałem|poszedłem|przyszedłem|wyszedłem|"
    r"zrobiłem|mówiłem|myślałem|czekałem|słyszałem|znalazłem|mogłem|wziąłem|dałem|"
    r"dostałem|zobaczyłem|poczułem|wróciłem|odszedłem|straciłem|zabiłem|uratowałem|"
    r"doniósłbym|wiedziałbym|mógłbym|chciałbym|miałbym|zrobiłbym|byłbym|wolałbym|"
    r"poszedłbym|rzekłem|rzekłbym"
    r")\b",
    re.IGNORECASE
)

PL_1ST_PERSON_FEM_VERB_REGEX = re.compile(
    r"\b(?:"
    r"[a-ząćęłńóśźż]+(?:iłam|yłam|ałam|nęłam|ułam|szłam|złam|głam|łabym)|"
    r"byłam|miałam|chciałam|wiedziałam|widziałam|poszłam|przyszłam|wyszłam|"
    r"zrobiłam|mówiłam|myślałam|czekałam|słyszałam|znalazłam|mogłam|wzięłam|dałam|"
    r"dostałam|zobaczyłam|poczułam|wróciłam|odeszłam|straciłam|zabiłam|uratowałam|"
    r"wiedziałabym|mogłabym|chciałabym|miałabym|zrobiłabym|byłabym|wolałabym|"
    r"poszłabym|rzekłam|rzekłabym"
    r")\b",
    re.IGNORECASE
)

PL_1ST_PERSON_MASC_PREDICATE_REGEX = re.compile(
    r"\b(?:jestem|byłem|będę)\s+(?:nie\s+)?[a-ząćęłńóśźż]+(?:ły|ł|ny|ty|owy|ski|cki|dzki|pewien|gotowy|świadom|zmuszony|zadowolony|gotów)\b",
    re.IGNORECASE
)

PL_1ST_PERSON_FEM_PREDICATE_REGEX = re.compile(
    r"\b(?:jestem|byłam|będę)\s+(?:nie\s+)?[a-ząćęłńóśźż]+(?:ła|na|ta|owa|ska|cka|dzka|pewna|gotowa|świadoma|zmuszona|zadowolona)\b",
    re.IGNORECASE
)

JA_1ST_PERSON_MASC_REGEX = re.compile(
    r"\b(?:ore|boku|jibun|sessha|washi|oresama)\b",
    re.IGNORECASE
)

JA_1ST_PERSON_FEM_REGEX = re.compile(
    r"\b(?:atashi|atai)\b",
    re.IGNORECASE
)

PL_NON_VERB_LEM_WORDS: Set[str] = {
    "stołem", "kołem", "dziełem", "ciałem", "gardłem", "skrzydłem", "źródłem",
    "mydłem", "sadłem", "węzłem", "orłem", "diabłem", "karłem", "popiołem",
    "kościołem", "tytułem", "artykułem", "kanałem", "sygnałem", "szałem", "kawałem",
    "żywiołem", "badałem", "rozumem"
}


def _detect_first_person_speech_gender(text: str) -> Optional[str]:
    """
    Ekstrahuje jawną płeć gramatyczną mówcy na podstawie bezpośredniej morfologii 1. osoby
    (czasowniki przeszłe -łem vs -łam, predykaty, japońskie zaimki 1. os.).
    Zwraca 'MALE' | 'FEMALE' | None.
    """
    if not text:
        return None
    clean = SubtitleDiscourseSanitizer.ASS_TAGS_REGEX.sub("", str(text)).strip()
    if not clean:
        return None

    # 1. Sprawdzenie form żeńskich
    if PL_1ST_PERSON_FEM_VERB_REGEX.search(clean) or PL_1ST_PERSON_FEM_PREDICATE_REGEX.search(clean) or JA_1ST_PERSON_FEM_REGEX.search(clean):
        return "FEMALE"

    # 2. Sprawdzenie form męskich
    if PL_1ST_PERSON_MASC_VERB_REGEX.search(clean) or PL_1ST_PERSON_MASC_PREDICATE_REGEX.search(clean) or JA_1ST_PERSON_MASC_REGEX.search(clean):
        return "MALE"

    # 3. Ogólne przeszłe formy na -łem z filtrem stoplisty rzeczowników narzędnika
    for m in re.finditer(r"\b([a-ząćęłńóśźż]{3,}łem)\b", clean, re.IGNORECASE):
        w = m.group(1).lower()
        if w in PL_NON_VERB_LEM_WORDS:
            continue
        pre = clean[:m.start()].strip().lower()
        if re.search(r"\b(?:z|ze|pod|nad|przed|za|między|pomiędzy)\s+(?:[a-ząćęłńóśźż]+\s+)*$", pre):
            continue
        return "MALE"

    return None


def _is_same_character(
    name1: str,
    name2: str,
    series_bible: Optional[Any] = None
) -> bool:
    """
    Sprawdza, czy dwa miana reprezentują tę samą postać na podstawie:
    - ścisłej równości (po normalizacji normalize_actor_tag),
    - unifikacji diakrytyków ASCII (normalize_ascii_diacritics),
    - kanonicznej bazy tożsamości i indeksu aliasów SeriesBible,
    - dopasowania pierwszego imienia / tokenów imienia własnego.
    """
    if not name1 or not name2:
        return False
    s1 = str(name1).strip()
    s2 = str(name2).strip()
    if s1.lower() == s2.lower():
        return True

    c1, _ = _normalize_event_actor(s1)
    c2, _ = _normalize_event_actor(s2)
    c1 = (c1 or s1).strip().lower()
    c2 = (c2 or s2).strip().lower()
    if c1 == c2:
        return True

    f1 = normalize_ascii_diacritics(c1).lower().strip()
    f2 = normalize_ascii_diacritics(c2).lower().strip()
    if f1 == f2:
        return True

    # Indeks aliasów i postaci w SeriesBible
    if series_bible:
        if hasattr(series_bible, "resolve_canonical_name"):
            try:
                can1 = series_bible.resolve_canonical_name(s1)
                can2 = series_bible.resolve_canonical_name(s2)
                if can1 and can2 and can1.lower() == can2.lower():
                    return True
            except Exception:
                pass

        aliases_idx = getattr(series_bible, "_actor_aliases_index", {})
        if isinstance(aliases_idx, dict) and aliases_idx:
            al1 = aliases_idx.get(c1) or aliases_idx.get(f1)
            al2 = aliases_idx.get(c2) or aliases_idx.get(f2)
            if al1 and al2 and al1.lower() == al2.lower():
                return True
            if al1 and al1.lower() in (c2, f2):
                return True
            if al2 and al2.lower() in (c1, f1):
                return True

        data = getattr(series_bible, "data", {}) if hasattr(series_bible, "data") else {}
        chars = (
            series_bible.get_characters_snapshot()
            if hasattr(series_bible, "get_characters_snapshot")
            else (data.get("characters", {}) if isinstance(data, dict) else {})
        )
        if isinstance(chars, dict):
            for char_k, char_v in chars.items():
                if not isinstance(char_v, dict):
                    continue
                al_list = [char_k] + list(char_v.get("aliases", []))
                al_lows = {a.lower().strip() for a in al_list if a}
                al_folds = {normalize_ascii_diacritics(a).lower().strip() for a in al_list if a}
                all_al = al_lows | al_folds
                if (c1 in all_al or f1 in all_al) and (c2 in all_al or f2 in all_al):
                    return True

    # Dopasowanie imion pierwszych (z wykluczeniem pospolitych tytułów)
    t1 = [t for t in re.split(r"[\s\-_]+", c1) if len(t) >= 2 and t not in _GENERIC_ROLE_TITLES]
    t2 = [t for t in re.split(r"[\s\-_]+", c2) if len(t) >= 2 and t not in _GENERIC_ROLE_TITLES]
    if t1 and t2:
        if t1[0] == t2[0]:
            return True
        if normalize_ascii_diacritics(t1[0]) == normalize_ascii_diacritics(t2[0]):
            return True

    return False


# Standard 11.0 (FIX-C.3b): Wykrywanie przyimka bezpośrednio przed kandydatem na wołacz
_PREPOSITION_BEFORE_CAND_PAT = re.compile(
    r"\b(?:with|in|at|from|to|into|of|for|by|about|between|among|against|towards|through|"
    r"z|ze|w|we|do|od|o|po|na|przy|dla|bez|przez|między|przed|za|nad|pod)$",
    re.IGNORECASE,
)


def _is_prepositional_context(text: str, candidate_match_start: int) -> bool:
    """Sprawdza, czy bezpośrednio przed dopasowaniem kandydata stoi przyimek."""
    prefix = text[:candidate_match_start].rstrip()
    if not prefix:
        return False
    return bool(_PREPOSITION_BEFORE_CAND_PAT.search(prefix))


_TITLE_PAT = r"(?:Duke|Prince|Count|Lord|Lady|Baron|Viscount|King|Queen|Master|Doctor|General|Captain|Princess|Baroness|Countess)"
_3RD_PERSON_PREPOSITIONS_PAT = re.compile(
    rf"\b(?:of|on\s+behalf\s+of|for|from|under|about|with|by|to|worthy\s+of)\s+(?:{_TITLE_PAT}\s*)*$",
    re.IGNORECASE
)
_3RD_PERSON_VERBS_PAT = re.compile(
    r"^\s*(?:acknowledges|hopes|is|was|has|said|says|thinks|believes|wants|knows|declared|smiled|nodded|agreed|commanded|ruled|reigns|spoke)\b",
    re.IGNORECASE
)


def _is_third_person_syntactic_context(text: str, candidate_match_start: int, candidate_match_end: int) -> bool:
    """
    Hotfix 11.1.5 (P2-1 / INC-AVT-027 / E-06): Filtr składniowy 3. osoby.
    Wykrywa konstrukcje referencyjne 3. osoby (przyimki, dopełniacz saksoński, orzeczenie 3. os.),
    które wykluczają interpretację jako bezpośredni zwrot adresatywny.
    """
    prefix = text[:candidate_match_start].rstrip()
    if prefix:
        if _PREPOSITION_BEFORE_CAND_PAT.search(prefix) or _3RD_PERSON_PREPOSITIONS_PAT.search(prefix):
            return True
        if re.search(rf"\b(?:on\s+behalf\s+of|under|about|worthy\s+of|for|from|by|of|to)\s+(?:{_TITLE_PAT}\s*)*$", prefix, re.IGNORECASE):
            return True

    suffix = text[candidate_match_end:].lstrip()
    if suffix:
        if suffix.startswith("'s") or suffix.startswith("’s"):
            return True
        if _3RD_PERSON_VERBS_PAT.search(suffix):
            return True

    return False


def _is_event_in_time_range(event: Any, time_range_str: str) -> bool:
    """Sprawdza, czy zdarzenie mieści się w zadanym przedziale czasowym (np. '01:20-03:45')."""
    if not event or not time_range_str:
        return False
    ev_s = getattr(event, "start", None)
    ev_e = getattr(event, "end", None)
    if ev_s is None or ev_e is None:
        return False
    parts = re.split(r"[-–]", time_range_str)
    if len(parts) != 2:
        return False
    def _to_ms(t_part: str) -> Optional[int]:
        subparts = t_part.strip().split(":")
        try:
            if len(subparts) == 2:
                return int(float(subparts[0])) * 60000 + int(float(subparts[1])) * 1000
            elif len(subparts) == 3:
                return int(float(subparts[0])) * 3600000 + int(float(subparts[1])) * 60000 + int(float(subparts[2])) * 1000
        except Exception:
            return None
        return None
    s_ms = _to_ms(parts[0])
    e_ms = _to_ms(parts[1])
    if s_ms is None or e_ms is None:
        return False
    return (ev_s >= s_ms and ev_s <= e_ms) or (ev_e >= s_ms and ev_e <= e_ms) or (ev_s <= s_ms and ev_e >= e_ms)



_MOB_CROWD_PAT = re.compile(
    r"^(?:mob|crowd|passerby|bystander|citizen|villager|spectator|onlooker|"
    r"tłum|przechodzień|gapi\w*|statyst\w*)",
    re.IGNORECASE,
)


def _is_mob_or_crowd_speaker(speaker: Optional[str]) -> bool:
    """Standard 11.0 (FIX-E.2a): Rozpoznaje mówców tłumu i tła."""
    if not speaker:
        return False
    return bool(_MOB_CROWD_PAT.match(str(speaker).strip()))


_DEICTIC_3RD_PERSON_PAT = re.compile(
    r"^\s*(?:is\s+that|isn't\s+(?:that|she|he|it)|look\s+at|they\s+say|that's|that\s+is|"
    r"czy\s+to|to\s+przecież|spójrz(?:cie)?\s+na|podobno)\b",
    re.IGNORECASE,
)


def _split_clauses(text: str) -> List[str]:
    """Standard 11.0 (FIX-E.2b): Dzieli tekst wypowiedzi na pojedyncze zdania/klauzule."""
    return [c.strip() for c in re.split(r"(?<=[.!?])\s+", text) if c and c.strip()]


def _is_deictic_3rd_person_clause(clause: str) -> bool:
    """Standard 11.0 (FIX-E.2b): Sprawdza, czy klauzula jest obserwacją deiktyczną 3. osoby."""
    return bool(_DEICTIC_3RD_PERSON_PAT.match(clause))


def _detect_event_vocative(
    event_or_text: Any,
    series_bible: Optional[Any] = None,
    current_speaker: str = ""
) -> Tuple[Optional[str], Optional[str]]:
    """
    Skanuje pojedynczą linię lub zdarzenie pod kątem obecności wołacza lub zawołania (tytułu lub imienia).
    """
    raw = getattr(event_or_text, "text", str(event_or_text)) if event_or_text is not None else ""
    if not raw:
        return None, None
    clean = SubtitleDiscourseSanitizer.ASS_TAGS_REGEX.sub("", raw).strip()
    if not clean:
        return None, None

    clauses = [c for c in _split_clauses(clean) if not _is_deictic_3rd_person_clause(c)]
    if not clauses:
        return None, None
    clean = " ".join(clauses)

    # 1. Sprawdzenie zarejestrowanych postaci w SeriesBible (jeśli dostępne)
    if series_bible:
        candidates = _extract_character_candidates_from_bible(series_bible, current_speaker=current_speaker)
        if candidates:
            for char_name, cdata in candidates.items():
                char_gender = cdata["gender"]
                forms = cdata["forms"]

                for cand in forms:
                    if not cand or len(cand) < 2:
                        continue

                    if series_bible and hasattr(series_bible, "is_non_character_entity"):
                        if series_bible.is_non_character_entity(cand, context=clean):
                            continue

                    # 1a. Wołacz LUB mianownik po wykrzyknikach adresatywnych (Hej, Ej, Ty, Słuchaj)
                    pat_interj = rf"(?:^|[\s,–—])(?:hej|ej|ty|słuchaj)[,\s]+(?:pana\s+|panie\s+)?{re.escape(cand)}(?:[,.!?…\s–—]|$)"
                    m_inj = re.search(pat_interj, clean, re.IGNORECASE)
                    if m_inj and not _is_third_person_syntactic_context(clean, m_inj.start(), m_inj.end()):
                        target_g = "MALE" if char_gender == "MALE" else (
                            "FEMALE" if char_gender == "FEMALE" else "NEUTRAL"
                        )
                        return char_name, target_g

                    # 1b. Zawołanie w krótkim okrzyku zakończonym '!'
                    pat_call = rf"(?:^|[\s,–—])(?:(?:hej|ej|ty|słuchaj)[,\s]+)?({re.escape(cand)})\s*!"
                    m_call = re.search(pat_call, clean, re.IGNORECASE)
                    if m_call and not _is_prepositional_context(clean, m_call.start(1)) and not _is_third_person_syntactic_context(clean, m_call.start(1), m_call.end(1)):
                        target_g = "MALE" if char_gender == "MALE" else (
                            "FEMALE" if char_gender == "FEMALE" else "NEUTRAL"
                        )
                        return char_name, target_g

                    # 1c. Standardowa granica wołaczowa z interpunkcją lub początkiem/końcem wersu
                    pat_voc = rf"(?:^|[\s,–—])({re.escape(cand)})(?:[,.!?…\s–—]|$)"
                    for m_voc in re.finditer(pat_voc, clean, re.IGNORECASE):
                        if _is_prepositional_context(clean, m_voc.start(1)) or _is_third_person_syntactic_context(clean, m_voc.start(1), m_voc.end(1)):
                            continue
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
        if matched_name[0].isupper() and low not in POLISH_COMMON_INTERJECTIONS_STOPLIST and matched_name != current_speaker:
            if series_bible and hasattr(series_bible, "get_character_gender"):
                bg = series_bible.get_character_gender(matched_name)
                bg_l = (bg or "").lower()
                if bg_l in ("male", "mężczyzna", "masculine"):
                    return matched_name, "MALE"
                elif bg_l in ("female", "kobieta", "feminine"):
                    return matched_name, "FEMALE"
            return matched_name, None

    # 5. Sprawdzenie zakotwiczonych imion w wołaczu bez SeriesBible
    for m in VOCATIVE_PUNCT_ANCHOR_REGEX.finditer(clean):
        if _is_prepositional_context(clean, m.start()) or _is_third_person_syntactic_context(clean, m.start(), m.end()):
            continue
        matched_name = m.group(1) or m.group(2) or m.group(3)
        if matched_name and matched_name != current_speaker:
            if series_bible and hasattr(series_bible, "is_non_character_entity") and series_bible.is_non_character_entity(matched_name, context=clean):
                continue
            low = matched_name.lower()
            if low in POLISH_COMMON_INTERJECTIONS_STOPLIST:
                continue
            if series_bible and hasattr(series_bible, "get_character_gender"):
                bg = series_bible.get_character_gender(matched_name)
                bg_l = (bg or "").lower()
                if bg_l in ("male", "mężczyzna", "masculine"):
                    return matched_name, "MALE"
                elif bg_l in ("female", "kobieta", "feminine"):
                    return matched_name, "FEMALE"
            if low.endswith("ie") or low.endswith("u"):
                base = re.sub(r"ie$", "", matched_name)
                return (base if len(base) >= 2 else matched_name), "MALE"
            elif low.endswith("o"):
                base = re.sub(r"o$", "a", matched_name)
                if series_bible and hasattr(series_bible, "get_character_gender"):
                    bg = series_bible.get_character_gender(base)
                    bg_l = (bg or "").lower()
                    if bg_l in ("male", "mężczyzna", "masculine"):
                        return base, "MALE"
                    elif bg_l in ("female", "kobieta", "feminine"):
                        return base, "FEMALE"
                return base, None

    return None, None


def _detect_turn_vocative(
    turn: SpeakerTurn,
    series_bible: Optional[Any] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Skanuje wszystkie linie tury pod kątem obecności wołacza lub zawołania (tytułu lub imienia).
    """
    lines = turn.lines if hasattr(turn, "lines") else [str(turn)]
    for raw in lines:
        actor, g = _detect_event_vocative(raw, series_bible=series_bible, current_speaker=turn.speaker)
        if actor and g:
            return actor, g
    return None, None


CONTRASTIVE_ADDRESSEE_PIVOT_REGEX = re.compile(
    r"(?:^|[\s,–—])(?:a|ale|lecz|natomiast|z\s+kolei|zaś)\s+(?:ty|wy|ciebie|tobie|tobą|was|wam|wami)\b|"
    r"\b(?:but|and\s+now|as\s+for)\s+(?:you|y'all)\b",
    re.IGNORECASE
)

SECOND_PERSON_PAST_SINGULAR_REGEX = re.compile(
    r"\b[a-ząćęłńóśźż]+(?:łeś|łaś|łbyś|łabyś)\b",
    re.IGNORECASE
)

SECOND_PERSON_NOMINATIVE_TY_REGEX = re.compile(
    r"\b(?:to\s+ty|ty)\b",
    re.IGNORECASE
)


def is_singular_2nd_person_line(
    event_or_text: Any,
    series_bible: Optional[Any] = None,
    current_speaker: str = ""
) -> bool:
    """
    Weryfikuje, czy linia lub zdarzenie zawiera jawny wykładnik 2. osoby liczby pojedynczej:
    - czasownik przeszły 2. os. lp. (-łeś / -łaś / -łbyś / -łabyś),
    - zaimek podmiotu 'ty' lub 'to ty',
    - pojedynczy wołacz imienia lub tytułu męskiego/żeńskiego,
    pod warunkiem braku wykładników liczby mnogiej.
    """
    if event_or_text is None:
        return False
    raw = getattr(event_or_text, "text", str(event_or_text)) if event_or_text is not None else ""
    if not raw:
        return False
    clean = SubtitleDiscourseSanitizer.ASS_TAGS_REGEX.sub("", raw).strip()
    if not clean:
        return False

    # Jeśli linia zawiera wskaźnik liczby mnogiej, nie stanowi czystej liczby pojedynczej
    if detect_plural_addressee(clean):
        return False

    # 1. Czasownik przeszły 2. os. lp. (-łeś, -łaś, -łbyś, -łabyś)
    if SECOND_PERSON_PAST_SINGULAR_REGEX.search(clean):
        return True

    # 2. Zaimek podmiotu 2. os. lp. ('ty', 'to ty')
    if SECOND_PERSON_NOMINATIVE_TY_REGEX.search(clean):
        return True

    # 3. Pojedynczy wołacz (imię lub tytuł)
    spk = current_speaker or (getattr(event_or_text, "name", "") or getattr(event_or_text, "speaker", ""))
    voc_actor, _ = _detect_event_vocative(clean, series_bible=series_bible, current_speaker=spk)
    if voc_actor:
        return True

    return False


def is_addressee_pivot(
    ev_prev: Any,
    ev_curr: Any,
    series_bible: Optional[Any] = None
) -> bool:
    """
    Wykrywa znacznik zmiany adresata (Addressee Pivot) pomiędzy dwoma zdarzeniami:
    a) Nowy jawny wołacz lub tytuł do innej postaci niż w linii poprzedniej,
    b) Konstrukcja kontrastywna / spójnik przeciwstawny z zaimkiem 2. osoby przełączający odbiorcę,
    c) Zmiana rejestru z mowy głośnej na myśl wewnętrzną (Default <-> Italics / Thoughts),
    d) Rozcięcie tury przy zmianie liczby gramatycznej (Singular-Plural SubTurn Split).
    """
    if ev_prev is None or ev_curr is None:
        return False

    # c) Zmiana rejestru: mowa głośna <-> myśl wewnętrzna
    is_mono_prev = is_internal_monologue(ev_prev)
    is_mono_curr = is_internal_monologue(ev_curr)
    if is_mono_prev != is_mono_curr:
        return True

    text_prev = getattr(ev_prev, "text", str(ev_prev)) or ""
    text_curr = getattr(ev_curr, "text", str(ev_curr)) or ""
    clean_prev = SubtitleDiscourseSanitizer.ASS_TAGS_REGEX.sub("", text_prev).strip()
    clean_curr = SubtitleDiscourseSanitizer.ASS_TAGS_REGEX.sub("", text_curr).strip()

    # d) Rozcięcie tury przy zmianie liczby gramatycznej (Singular-Plural SubTurn Split)
    spk = getattr(ev_curr, "speaker", getattr(ev_curr, "name", ""))
    prev_plural = detect_plural_addressee(clean_prev)
    curr_plural = detect_plural_addressee(clean_curr)
    if prev_plural != curr_plural:
        return True

    # a) Nowy jawny wołacz lub tytuł do innej postaci niż w linii poprzedniej
    voc_prev, _ = _detect_event_vocative(clean_prev, series_bible=series_bible, current_speaker=spk)
    voc_curr, _ = _detect_event_vocative(clean_curr, series_bible=series_bible, current_speaker=spk)

    if voc_curr:
        if voc_prev and not _is_same_character(voc_curr, voc_prev, series_bible=series_bible):
            return True
        elif not voc_prev and CONTRASTIVE_ADDRESSEE_PIVOT_REGEX.search(clean_curr):
            return True

    # b) Konstrukcja kontrastywna / spójnik przeciwstawny z zaimkiem 2. osoby przełączający odbiorcę
    if CONTRASTIVE_ADDRESSEE_PIVOT_REGEX.search(clean_curr):
        return True

    return False


def partition_subturns(
    turn: SpeakerTurn,
    series_bible: Optional[Any] = None
) -> List[SpeakerTurn]:
    """
    Dzieli SpeakerTurn na niezależne pod-segmenty (SubTurn), jeśli wewnątrz tury wystąpi
    Addressee Pivot (zmiana rejestru, inny wołacz, spójnik przeciwstawny 2. osoby,
    lub zmiana liczby gramatycznej Singular-Plural).
    """
    if not turn or not turn.events or len(turn.events) <= 1:
        return [turn]

    partitions: List[List[Any]] = []
    current_chunk: List[Any] = [turn.events[0]]

    for i in range(1, len(turn.events)):
        ev_prev = turn.events[i - 1]
        ev_curr = turn.events[i]
        if is_addressee_pivot(ev_prev, ev_curr, series_bible=series_bible):
            partitions.append(current_chunk)
            current_chunk = [ev_curr]
        else:
            current_chunk.append(ev_curr)
    if current_chunk:
        partitions.append(current_chunk)

    if len(partitions) <= 1:
        return [turn]

    sub_turns: List[SpeakerTurn] = []
    for chunk in partitions:
        st = SubTurn(
            speaker=turn.speaker,
            events=chunk,
            scene_id=turn.scene_id,
            scene_participants=list(turn.scene_participants),
            scene_has_male_participant=turn.scene_has_male_participant,
            plural_group_gender=turn.plural_group_gender,
            you_group_gender=getattr(turn, "you_group_gender", "AMBIGUOUS"),
        )
        if st.detect_plural_addressee():
            st.addressee_number = "PLURAL"
        else:
            st.addressee_number = "SINGULAR"

        voc_actor, voc_gender = _detect_turn_vocative(st, series_bible=series_bible)
        if voc_actor:
            if not voc_gender and series_bible:
                _, voc_gender, _ = _resolve_character_canonical_and_gender(voc_actor, series_bible=series_bible)
            if voc_gender:
                st.target_speaker = voc_actor
                st.target_gender = voc_gender
                st.target_confidence = 0.98
                st.vocative_lock = True
        elif is_internal_monologue(st):
            st.target_speaker = None
            st.target_gender = None
            st.target_confidence = 0.0
            st.vocative_lock = False

        for ev in st.events:
            setattr(ev, "target_speaker", st.target_speaker)
            setattr(ev, "target_actor", st.target_speaker)
            setattr(ev, "target_gender", st.target_gender)
            setattr(ev, "target_confidence", st.target_confidence)
            setattr(ev, "addressee_number", st.addressee_number)
            setattr(ev, "is_plural", st.is_plural)
            setattr(ev, "vocative_lock", st.vocative_lock)
            setattr(ev, "you_group_gender", st.you_group_gender)
            setattr(ev, "plural_group_gender", st.plural_group_gender)
            setattr(ev, "speaker_turn", st)

        if st.duration_ms >= 0:
            pass
        sub_turns.append(st)

    turn.sub_turns = sub_turns
    return sub_turns


def _resolve_character_canonical_and_gender(
    name: str,
    series_bible: Optional[Any] = None,
    context_item: Optional[Any] = None
) -> Tuple[str, Optional[str], float]:
    """
    Spójna identyfikacja tożsamości i płci postaci w oparciu o zunifikowany indeks
    kluczy głównych oraz aliasów w SeriesBible po normalizacji normalize_actor_tag,
    a także poprzez bezpośrednią morfologię 1. osoby mówcy w bieżącej scenie.
    Zwraca: (canonical_name, gender, confidence), gdzie gender in {"MALE", "FEMALE", None}.
    """
    if not name:
        return "", None, 0.0

    clean_name, tag_g = _normalize_event_actor(name)
    if tag_g in ("MALE", "FEMALE"):
        return (clean_name or name).strip(), tag_g, 1.0

    target_name = (clean_name or name).strip()
    if not target_name:
        return "", None, 0.0

    candidates: List[str] = [target_name]
    if name and name not in candidates:
        candidates.append(name)

    t_folded = normalize_ascii_diacritics(target_name)
    if t_folded and t_folded not in candidates:
        candidates.append(t_folded)

    t_tokens = [t for t in re.split(r"[\s\-_]+", target_name) if len(t) >= 2 and t.lower() not in _GENERIC_ROLE_TITLES]
    if t_tokens:
        first_tok = t_tokens[0]
        if first_tok not in candidates:
            candidates.append(first_tok)
        first_folded = normalize_ascii_diacritics(first_tok)
        if first_folded and first_folded not in candidates:
            candidates.append(first_folded)

    if series_bible:
        data = getattr(series_bible, "data", {}) if hasattr(series_bible, "data") else {}
        chars = (
            series_bible.get_characters_snapshot()
            if hasattr(series_bible, "get_characters_snapshot")
            else (data.get("characters", {}) if isinstance(data, dict) else {})
        )

        # 1. Hypocorisms lookup
        hypo = data.get("hypocorisms", {}) if isinstance(data, dict) else {}
        if isinstance(hypo, dict):
            t_low = target_name.lower()
            for h_k, h_v in hypo.items():
                if h_k.lower() == t_low:
                    if h_v not in candidates:
                        candidates.insert(0, h_v)

        # 2. Canonical resolution via method
        if hasattr(series_bible, "resolve_canonical_name"):
            try:
                canon = series_bible.resolve_canonical_name(target_name)
                if canon and canon not in candidates:
                    candidates.insert(0, canon)
            except Exception:
                pass
            if t_tokens:
                try:
                    canon_tok = series_bible.resolve_canonical_name(t_tokens[0])
                    if canon_tok and canon_tok not in candidates:
                        candidates.append(canon_tok)
                except Exception:
                    pass

        # 3. Fast direct alias matching via _actor_aliases_index
        aliases_idx = getattr(series_bible, "_actor_aliases_index", {})
        if isinstance(aliases_idx, dict) and aliases_idx:
            for cand_cand in [target_name.lower(), t_folded.lower()] + ([t_tokens[0].lower()] if t_tokens else []):
                matched = aliases_idx.get(cand_cand)
                if matched and matched not in candidates:
                    candidates.insert(0, matched)

        # 4. Aliases in characters snapshot
        if isinstance(chars, dict):
            t_low = target_name.lower()
            f_low = t_folded.lower()
            first_low = t_tokens[0].lower() if t_tokens else ""
            for c_k, c_v in chars.items():
                if c_k.lower() in (t_low, f_low, first_low):
                    if c_k not in candidates:
                        candidates.insert(0, c_k)
                if isinstance(c_v, dict):
                    aliases = c_v.get("aliases") or []
                    if isinstance(aliases, list):
                        for a in aliases:
                            a_str = str(a).lower().strip()
                            a_fold = normalize_ascii_diacritics(a_str).lower().strip()
                            if a_str in (t_low, f_low, first_low) or a_fold in (t_low, f_low, first_low):
                                if c_k not in candidates:
                                    candidates.insert(0, c_k)
                                break
                    c_tokens = [t for t in re.split(r"[\s\-_]+", c_k) if len(t) >= 2 and t.lower() not in _GENERIC_ROLE_TITLES]
                    if c_tokens and first_low and c_tokens[0].lower() == first_low:
                        if c_k not in candidates:
                            candidates.append(c_k)

        # 5. Character identities direct lookup
        identities = getattr(series_bible, "character_identities", {})
        if not identities and isinstance(data, dict):
            identities = data.get("character_identities", {})
        if isinstance(identities, dict):
            t_low = target_name.lower()
            for id_k in identities.keys():
                if id_k.lower() == t_low and id_k not in candidates:
                    candidates.insert(0, id_k)

        # Check identities, characters, and get_character_gender for each candidate
        for cand in candidates:
            if hasattr(series_bible, "get_character_identity"):
                try:
                    ident = series_bible.get_character_identity(cand)
                    if ident:
                        tg = getattr(ident, "true_gender", "")
                        if tg in ("MASCULINE", "MALE"):
                            return getattr(ident, "canonical_id", cand) or cand, "MALE", 1.0
                        elif tg in ("FEMININE", "FEMALE"):
                            return getattr(ident, "canonical_id", cand) or cand, "FEMALE", 1.0
                except Exception:
                    pass

            if isinstance(chars, dict):
                c_val = chars.get(cand)
                if not c_val:
                    for k, v in chars.items():
                        if k.lower() == cand.lower():
                            c_val = v
                            break
                if isinstance(c_val, dict):
                    g = c_val.get("gender")
                    conf = float(c_val.get("confidence", 1.0))
                    verified = bool(c_val.get("has_verified_gender", False))
                    effective_conf = 1.0 if verified else conf
                    g_l = (g or "").lower()
                    if g_l in ("male", "mężczyzna", "masculine"):
                        return cand, "MALE", effective_conf
                    elif g_l in ("female", "kobieta", "feminine"):
                        return cand, "FEMALE", effective_conf

            if hasattr(series_bible, "get_character_gender"):
                try:
                    bg = series_bible.get_character_gender(cand)
                    bg_l = (bg or "").lower()
                    if bg_l in ("male", "mężczyzna", "masculine"):
                        return cand, "MALE", 1.0
                    elif bg_l in ("female", "kobieta", "feminine"):
                        return cand, "FEMALE", 1.0
                except Exception:
                    pass

    # Weryfikacja bezpośredniej morfologii 1. osoby mówcy w bieżącej scenie / kontekście
    if context_item:
        texts_to_check: List[str] = []
        if hasattr(context_item, "events"):
            for ev in context_item.events:
                ev_spk = getattr(ev, "speaker", getattr(ev, "name", "")) or ""
                if not ev_spk or _is_same_character(target_name, ev_spk, series_bible=series_bible):
                    texts_to_check.append(getattr(ev, "text", "") or "")
        elif hasattr(context_item, "text"):
            c_spk = getattr(context_item, "speaker", getattr(context_item, "name", "")) or ""
            if not c_spk or _is_same_character(target_name, c_spk, series_bible=series_bible):
                texts_to_check.append(getattr(context_item, "text", "") or "")
        elif isinstance(context_item, list):
            for item in context_item:
                i_spk = getattr(item, "speaker", getattr(item, "name", "")) or ""
                if not i_spk or _is_same_character(target_name, i_spk, series_bible=series_bible):
                    texts_to_check.append(getattr(item, "text", "") or "")

        for txt in texts_to_check:
            g_morph = _detect_first_person_speech_gender(txt)
            if g_morph in ("MALE", "FEMALE"):
                return target_name, g_morph, 1.0

        spk_g = getattr(context_item, "speaker_gender", None)
        spk_conf = float(getattr(context_item, "speaker_confidence", 1.0))
        c_spk = getattr(context_item, "speaker", getattr(context_item, "name", "")) or ""
        if c_spk and _is_same_character(target_name, c_spk, series_bible=series_bible):
            if spk_g in ("MALE", "MASCULINE"):
                return target_name, "MALE", spk_conf
            elif spk_g in ("FEMALE", "FEMININE"):
                return target_name, "FEMALE", spk_conf

        tgt_g = getattr(context_item, "target_gender", None)
        tgt_conf = float(getattr(context_item, "target_confidence", 1.0))
        c_tgt = getattr(context_item, "target_speaker", getattr(context_item, "target_actor", "")) or ""
        if c_tgt and _is_same_character(target_name, c_tgt, series_bible=series_bible):
            if tgt_g in ("MALE", "MASCULINE"):
                return target_name, "MALE", tgt_conf
            elif tgt_g in ("FEMALE", "FEMININE"):
                return target_name, "FEMALE", tgt_conf

    return target_name, None, 0.0


def is_character_male(
    name: str,
    series_bible: Optional[Any] = None,
    context_item: Optional[Any] = None
) -> bool:
    """Sprawdza deterministycznie, czy dana postać ma płeć MALE."""
    if not name:
        return False
    clean_name, tag_g = _normalize_event_actor(name)
    if tag_g == "MALE":
        return True
    if tag_g == "FEMALE":
        return False
    target_name = (clean_name or name).strip()
    _, g, _ = _resolve_character_canonical_and_gender(target_name, series_bible=series_bible, context_item=context_item)
    return g == "MALE"


def is_character_female(
    name: str,
    series_bible: Optional[Any] = None,
    context_item: Optional[Any] = None
) -> bool:
    """Sprawdza deterministycznie, czy dana postać ma płeć FEMALE."""
    if not name:
        return False
    clean_name, tag_g = _normalize_event_actor(name)
    if tag_g == "FEMALE":
        return True
    if tag_g == "MALE":
        return False
    target_name = (clean_name or name).strip()
    _, g, _ = _resolve_character_canonical_and_gender(target_name, series_bible=series_bible, context_item=context_item)
    return g == "FEMALE"


def is_character_confirmed_female(
    name: str,
    series_bible: Optional[Any] = None,
    context_item: Optional[Any] = None,
    min_confidence: float = 0.95
) -> bool:
    """
    Sprawdza deterministycznie, czy postać jest potwierdzoną kobietą o pewności >= min_confidence (0.95).
    """
    if not name:
        return False
    clean_name, tag_g = _normalize_event_actor(name)
    if tag_g == "FEMALE":
        return True
    if tag_g == "MALE":
        return False
    target_name = (clean_name or name).strip()
    _, g, conf = _resolve_character_canonical_and_gender(target_name, series_bible=series_bible, context_item=context_item)
    return g == "FEMALE" and conf >= min_confidence


def is_narrative_style(style_str: str) -> bool:
    """Sprawdza, czy styl oznacza domenę narracji lub retrospekcji."""
    s = (style_str or "").lower()
    return any(k in s for k in ["flashback", "retrospekcja", "narration", "narrat", "narrative"])


def is_sign_or_title_item(item: Any) -> bool:
    """Sprawdza, czy element jest szyldem lub tytułem."""
    if getattr(item, "is_sign", False):
        return True
    s = (getattr(item, "style", "") or "").lower()
    spk = (getattr(item, "speaker", getattr(item, "name", "")) or "").lower()
    return any(k in s or k in spk for k in ["sign", "title", "szyld", "card", "napis"])


def is_offscreen_or_voiceover(item: Any) -> bool:
    """Sprawdza, czy element jest spoza kadru (narrator, radio, offscreen)."""
    s = (getattr(item, "style", "") or "").lower()
    spk = (getattr(item, "speaker", getattr(item, "name", "")) or "").lower()
    return any(k in s or k in spk for k in [
        "offscreen", "off-screen", "off_screen", "os", "o.s.",
        "voiceover", "voice-over", "vo", "v.o.",
        "radio", "phone", "comm", "narrat"
    ])


def is_discourse_ignorable(item_or_speaker: Any) -> bool:
    """
    Sprawdza, czy zdarzenie, tura lub mówca powinny być ignorowane w topologii dyskursu zewnętrznego.
    Kwestie wewnętrzne (is_internal_monologue), szyldy (Sign/Title) oraz narracja spoza kadru
    (Narrator, Offscreen, Radio, Voiceover) nigdy nie stają się adresatem dialogu.
    """
    if item_or_speaker is None:
        return True

    if hasattr(item_or_speaker, "events") or hasattr(item_or_speaker, "text"):
        if is_internal_monologue(item_or_speaker):
            return True
        if is_sign_or_title_item(item_or_speaker) or is_offscreen_or_voiceover(item_or_speaker):
            return True

    spk = (
        getattr(item_or_speaker, "speaker", None)
        or getattr(item_or_speaker, "name", None)
        or str(item_or_speaker)
    ).strip().lower()

    if any(k in spk for k in ["sign", "title", "szyld", "narrat", "offscreen", "voiceover", "radio", "system"]):
        return True
    return False


def compute_we_group(
    current: Any,
    scene_participants: List[str],
    series_bible: Optional[Any] = None
) -> Set[str]:
    """
    Wylicza zbiór postaci wchodzących w skład grupy 'My' (We_Group) dla 1. os. lm.
    Gdy wypowiedź zawiera zaimki 2. osoby skierowane do słuchacza jako zewnętrznego obiektu:
        We_Group = scene_participants - {target_actor}
    Gdy czynność inkluzywna / stan wspólny grupy:
        We_Group = scene_participants
    """
    group = set(scene_participants)
    t_actor = getattr(current, "target_speaker", None) or getattr(current, "target_actor", None)

    text = getattr(current, "text", "") or ""
    has_external_addressee = bool(
        SECOND_PERSON_PRONOUNS_REGEX.search(text) or
        re.search(r"\b(?:cię|ciebie|tobie|tobą|wam|was|wami|wasz)\b", text, re.IGNORECASE)
    )
    if t_actor and has_external_addressee:
        to_remove = set()
        for p in group:
            if _is_same_character(p, t_actor, series_bible=series_bible):
                to_remove.add(p)
        group.discard(t_actor)
        clean_t, _ = _normalize_event_actor(t_actor)
        if clean_t:
            group.discard(clean_t)
        group -= to_remove

    return group


def classify_we_group_gender(
    we_group: Set[str],
    series_bible: Optional[Any] = None,
    context_item: Optional[Any] = None
) -> Tuple[str, bool]:
    """
    Klasyfikuje płeć gramatyczną grupy We_Group:
    - min. 1 potwierdzony mężczyzna w We_Group (w SeriesBible po kluczu lub aliasie pierwszego imienia,
      ze znacznika metadanych lub determinizmu akustycznego F0 <= 135 Hz)
      -> plural_group_gender = 'VIRILE', we_has_male = True
    - zbiór liczy >= 2 uczestników i każdy element posiada zweryfikowaną w SeriesBible płeć FEMALE
      (confidence >= 0.95) przy zerowej liczbie mężczyzn i zerowej liczbie nieznanych (unknown_count == 0)
      -> plural_group_gender = 'NON_VIRILE', we_has_male = False
    - w przeciwnym razie -> plural_group_gender = 'AMBIGUOUS' (odwzorowanie identycznościowe T(x) = x)
    """
    if not we_group:
        return "AMBIGUOUS", False

    has_male = False
    confirmed_females = 0
    unknown_count = 0

    for member in we_group:
        if is_character_male(member, series_bible=series_bible, context_item=context_item):
            has_male = True
            break
        elif is_character_confirmed_female(member, series_bible=series_bible, context_item=context_item):
            confirmed_females += 1
        else:
            unknown_count += 1

    if has_male:
        return "VIRILE", True
    elif len(we_group) >= 2 and confirmed_females == len(we_group) and unknown_count == 0 and not has_male:
        return "NON_VIRILE", False
    else:
        return "AMBIGUOUS", False


def compute_you_group(
    current: Any,
    scene_participants: List[str],
    series_bible: Optional[Any] = None
) -> Set[str]:
    """
    Wylicza zbiór słuchaczy (You_Group) dla 2. os. lm.
    Gdy mówca zwraca się w 2. os. lm. (-liście / -łyście / wy):
        You_Group = scene_participants - {speaker}
    """
    group = set(scene_participants)
    spk = (
        getattr(current, "speaker", None)
        or getattr(current, "name", None)
        or ""
    ).strip()
    if spk:
        to_remove = set()
        for p in group:
            if _is_same_character(p, spk, series_bible=series_bible):
                to_remove.add(p)
        group.discard(spk)
        clean_spk, _ = _normalize_event_actor(spk)
        if clean_spk:
            group.discard(clean_spk)
        group -= to_remove
    return group


def classify_you_group_gender(
    you_group: Set[str],
    series_bible: Optional[Any] = None,
    context_item: Optional[Any] = None,
    scene_has_male: bool = False
) -> str:
    """
    Klasyfikuje płeć gramatyczną grupy You_Group (2. os. lm.):
    - Status 'VIRILE': zbiór zawiera przynajmniej jednego uczestnika o potwierdzonej płci męskiej
      (w SeriesBible po kluczu lub aliasie pierwszego imienia, ze znacznika metadanych lub determinizmu akustycznego F0 <= 135 Hz).
    - Status 'NON_VIRILE': zbiór liczy >= 2 uczestników i każdy element posiada zweryfikowaną w SeriesBible
      płeć FEMALE (confidence >= 0.95) przy zerowej liczbie mężczyzn i zerowej liczbie nieustalonej płci (unknown_count == 0).
    - Wszystkie pozostałe konfiguracje przyjmują status 'AMBIGUOUS' (odwzorowanie identycznościowe T(x) = x).
    """
    if not you_group:
        return "AMBIGUOUS"

    has_male = False
    confirmed_females = 0
    unknown_count = 0

    for member in you_group:
        if is_character_male(member, series_bible=series_bible, context_item=context_item):
            has_male = True
            break
        elif is_character_confirmed_female(member, series_bible=series_bible, context_item=context_item):
            confirmed_females += 1
        else:
            unknown_count += 1

    if has_male:
        return "VIRILE"
    elif len(you_group) >= 2 and confirmed_females == len(you_group) and unknown_count == 0 and not has_male:
        return "NON_VIRILE"
    else:
        return "AMBIGUOUS"


def resolve_scene_participants(
    items: List[Any],
    series_bible: Optional[Any] = None,
    window_ms: int = 15000
) -> List[Any]:
    """
    Twarda Ściana Cięcia Sceny (SceneBoundaryWall), Fizyczna Współobecność i Symetryczny Rachunek Zbiorów:
    - Horyzont badania uczestników sceny zatrzymuje się na: ciszy Delta_t >= 3.5 s (chyba że trwa ping-pong < 5.0 s),
      zmianie domeny stylu (Default <-> Flashback/Narration) lub Sign/Title.
    - Fizyczna współobecność dla Italics: kwestie w stylu Italics (< 2.0 s) zaliczaj do uczestników sceny
      WYŁĄCZNIE gdy postać nie jest oznaczona jako Narrator/Offscreen/Radio/Voiceover.
    - Symetryczny rachunek We_Group i deterministyczna klasyfikacja plural_group_gender (VIRILE | NON_VIRILE | AMBIGUOUS).
    """
    if not items:
        return items

    # Standard 11.1 (LUKA-E7-02): pobranie migawki postaci raz przed pętlą (brak deepcopy w pętli)
    chars_snapshot = None
    if series_bible and hasattr(series_bible, "get_characters_snapshot"):
        try:
            chars_snapshot = series_bible.get_characters_snapshot()
        except Exception:
            chars_snapshot = None

    sorted_indices = sorted(range(len(items)), key=lambda i: getattr(items[i], "start", 0))

    for idx_pos, curr_idx in enumerate(sorted_indices):
        current = items[curr_idx]
        c_start = getattr(current, "start", 0)
        c_end = getattr(current, "end", 0)
        c_speaker = (getattr(current, "speaker", getattr(current, "name", "")) or "").strip()
        c_style = getattr(current, "style", "") or ""

        scene_items = [current]

        # 1. Rozszerzanie wstecz (Backward Expansion)
        for prev_pos in range(idx_pos - 1, -1, -1):
            p_idx = sorted_indices[prev_pos]
            p_item = items[p_idx]
            p_start = getattr(p_item, "start", 0)
            p_end = getattr(p_item, "end", 0)
            p_speaker = (getattr(p_item, "speaker", getattr(p_item, "name", "")) or "").strip()
            p_style = getattr(p_item, "style", "") or ""

            if c_start - p_end > window_ms:
                break

            next_adjacent = items[sorted_indices[prev_pos + 1]]
            adj_gap_ms = getattr(next_adjacent, "start", 0) - p_end

            # Ściana ciszy Delta_t >= 3.5 s
            if adj_gap_ms >= 3500:
                is_active_ping_pong = (
                    adj_gap_ms < 5000 and
                    p_speaker and
                    p_speaker != getattr(next_adjacent, "speaker", getattr(next_adjacent, "name", ""))
                )
                if not is_active_ping_pong:
                    break

            # Ściana zmiany domeny stylu
            if is_narrative_style(p_style) != is_narrative_style(c_style):
                break

            # Ściana szyldów
            if is_sign_or_title_item(p_item):
                break

            scene_items.append(p_item)

        # 2. Rozszerzanie w przód (Forward Expansion)
        for next_pos in range(idx_pos + 1, len(sorted_indices)):
            n_idx = sorted_indices[next_pos]
            n_item = items[n_idx]
            n_start = getattr(n_item, "start", 0)
            n_end = getattr(n_item, "end", 0)
            n_speaker = (getattr(n_item, "speaker", getattr(n_item, "name", "")) or "").strip()
            n_style = getattr(n_item, "style", "") or ""

            if n_start - c_end > window_ms:
                break

            prev_adjacent = items[sorted_indices[next_pos - 1]]
            adj_gap_ms = n_start - getattr(prev_adjacent, "end", 0)

            # Ściana ciszy Delta_t >= 3.5 s
            if adj_gap_ms >= 3500:
                is_active_ping_pong = (
                    adj_gap_ms < 5000 and
                    n_speaker and
                    n_speaker != getattr(prev_adjacent, "speaker", getattr(prev_adjacent, "name", ""))
                )
                if not is_active_ping_pong:
                    break

            # Ściana zmiany domeny stylu
            if is_narrative_style(n_style) != is_narrative_style(c_style):
                break

            # Ściana szyldów
            if is_sign_or_title_item(n_item):
                break

            scene_items.append(n_item)

        # Ekstrakcja fizycznych uczestników sceny
        participants: List[str] = []
        scene_has_male = False
        for s_item in scene_items:
            s_spk = (getattr(s_item, "speaker", None) or getattr(s_item, "name", None) or "").strip()
            s_clean_spk, s_tag_g = _normalize_event_actor(s_spk)
            if s_tag_g == "MALE":
                scene_has_male = True

            # Weryfikacja morfologii męskiej 1. os. lp. mówcy
            s_txt = getattr(s_item, "text", "") or ""
            if _detect_first_person_speech_gender(s_txt) == "MALE":
                scene_has_male = True

            s_effective_spk = s_clean_spk or s_spk
            if is_character_male(s_effective_spk, series_bible=series_bible, context_item=s_item):
                scene_has_male = True

            s_style = getattr(s_item, "style", "") or ""
            s_is_italic = ("{\\i1}" in s_txt) or ("italic" in s_style.lower())

            if s_is_italic:
                duration_s = max(0, getattr(s_item, "end", 0) - getattr(s_item, "start", 0)) / 1000.0
                if duration_s < 2.0 and not is_offscreen_or_voiceover(s_item):
                    if s_effective_spk and not any(_is_same_character(s_effective_spk, p, series_bible=series_bible) for p in participants):
                        participants.append(s_effective_spk)
            else:
                if s_effective_spk and not is_discourse_ignorable(s_item):
                    if not any(_is_same_character(s_effective_spk, p, series_bible=series_bible) for p in participants):
                        participants.append(s_effective_spk)

            s_target = getattr(s_item, "target_speaker", None) or getattr(s_item, "target_actor", None)
            if s_target:
                s_clean_t, s_tag_tg = _normalize_event_actor(s_target)
                if s_tag_tg == "MALE":
                    scene_has_male = True
                s_effective_t = s_clean_t or s_target
                if is_character_male(s_effective_t, series_bible=series_bible, context_item=s_item):
                    scene_has_male = True
                if not is_discourse_ignorable(s_target):
                    if s_effective_t and not any(_is_same_character(s_effective_t, p, series_bible=series_bible) for p in participants):
                        participants.append(s_effective_t)

        c_clean, c_tag_g = _normalize_event_actor(c_speaker)
        if c_tag_g == "MALE":
            scene_has_male = True
        c_effective = c_clean or c_speaker
        if is_character_male(c_effective, series_bible=series_bible, context_item=current):
            scene_has_male = True
        if c_effective and not is_discourse_ignorable(current) and not any(_is_same_character(c_effective, p, series_bible=series_bible) for p in participants):
            participants.append(c_effective)

        # Symetryczny rachunek We_Group
        we_group = compute_we_group(current, participants, series_bible=series_bible)
        p_group_gender, we_has_male = classify_we_group_gender(
            we_group,
            series_bible=series_bible,
            context_item=current
        )
        if we_has_male:
            scene_has_male = True

        # Rozdział You_Group (2. os. lm.)
        you_group = compute_you_group(current, participants, series_bible=series_bible)
        y_group_gender = classify_you_group_gender(
            you_group,
            series_bible=series_bible,
            context_item=current,
            scene_has_male=False
        )
        if y_group_gender == "VIRILE":
            scene_has_male = True

        if hasattr(current, "is_plural"):
            pass
        if hasattr(current, "duration_ms"):
            pass

        if hasattr(current, "scene_participants"):
            current.scene_participants = list(participants)
        else:
            setattr(current, "scene_participants", list(participants))

        if hasattr(current, "scene_has_male_participant"):
            current.scene_has_male_participant = scene_has_male
        else:
            setattr(current, "scene_has_male_participant", scene_has_male)

        if hasattr(current, "plural_group_gender"):
            current.plural_group_gender = p_group_gender
        else:
            setattr(current, "plural_group_gender", p_group_gender)

        if hasattr(current, "you_group_gender"):
            current.you_group_gender = y_group_gender
        else:
            setattr(current, "you_group_gender", y_group_gender)

        if hasattr(current, "events"):
            for ev in current.events:
                setattr(ev, "scene_participants", list(participants))
                setattr(ev, "scene_has_male_participant", scene_has_male)
                setattr(ev, "plural_group_gender", p_group_gender)
                setattr(ev, "you_group_gender", y_group_gender)

    return items


def _is_offscreen_speaker_excluded(
    cand_turn: Any,
    curr_turn: Any,
    series_bible: Optional[Any] = None
) -> bool:
    """
    Weryfikuje, czy mówca cand_turn jest mówcą off-screen (np. styl 'Italics - Top' lub 'Italics'),
    który nie znajduje się w characters_present aktywnej sceny dramatycznej.
    Taki mówca nie jest przypisywany jako adresat dla kwestii na stylu Default.
    """
    if not cand_turn or not curr_turn:
        return False
    curr_style = str(getattr(curr_turn, "style", "") or "").lower()
    cand_style = str(getattr(cand_turn, "style", "") or "").lower()

    if "italic" in curr_style:
        return False

    is_cand_offscreen = "italics - top" in cand_style or "top" in cand_style or (
        "italic" in cand_style and "default" not in cand_style
    )
    if not is_cand_offscreen:
        return False

    cand_speaker = str(getattr(cand_turn, "speaker", "") or "").strip().lower()
    if not cand_speaker:
        return False

    dram_seqs = getattr(series_bible, "dramatic_sequences", None) if series_bible else None
    if not dram_seqs and hasattr(curr_turn, "dramatic_sequences"):
        dram_seqs = curr_turn.dramatic_sequences
    if not dram_seqs and hasattr(cand_turn, "dramatic_sequences"):
        dram_seqs = cand_turn.dramatic_sequences

    chars_present = set()
    if dram_seqs and hasattr(curr_turn, "events") and curr_turn.events:
        ev0 = curr_turn.events[0]
        for seq in dram_seqs:
            tr_str = getattr(seq, "time_range", "")
            if _is_event_in_time_range(ev0, tr_str):
                for c in getattr(seq, "characters_present", []) or []:
                    if c:
                        chars_present.add(str(c).strip().lower())
                break
    elif hasattr(curr_turn, "characters_present") and curr_turn.characters_present:
        chars_present = {str(c).strip().lower() for c in curr_turn.characters_present if c}
    elif hasattr(cand_turn, "characters_present") and cand_turn.characters_present:
        chars_present = {str(c).strip().lower() for c in cand_turn.characters_present if c}

    if chars_present and cand_speaker not in chars_present:
        return True

    if "italics - top" in cand_style and not chars_present:
        return True

    return False


def resolve_turn_addressee(
    turn: SpeakerTurn,
    previous_turn: Optional[SpeakerTurn] = None,
    series_bible: Optional[Any] = None,
    max_exchange_gap_ms: int = 5000,
    next_turn: Optional[SpeakerTurn] = None,
    prior_turns: Optional[List[SpeakerTurn]] = None
) -> SpeakerTurn:
    """
    Dyadic Turn-Taking (Rozwiązywanie adresata 2. osoby) i Trójstopniowy Automat Rozdzielczości:
    - Niewidzialność myśli: is_internal_monologue == True, Sign, Narrator, Offscreen nigdy nie stają się target_actor.
    - Krok 1 (Wołacz w pod-turze, pewność 0.98): zwrot do postaci w bieżącej linii lub pod-turze przypisuje target_actor/target_gender.
    - Krok 2 (Backward Lookback z bramką Ping-Ponga): przy Delta_t < 2.5 s dziedzicz target_actor z poprzedniego mówcy głośnego
      (pewność 0.95 przy dialogu dwugłosowym A <-> B; 0.85 przy pojedynczej wymianie). Dla 2.5 s <= Delta_t < 5.0 s dziedzicz
      WYŁĄCZNIE gdy potwierdzony jest aktywny Ping-Pong A -> B -> A lub poprzednia kwestia była pytaniem.
    - Krok 3 (Forward Lookahead < 2.0 s przy pytaniu 2. os. ?): wyznaczaj target_actor z postaci odpowiadającej w kolejnej linii
      gdy Delta_t < 2.0 s, mowa głośna, brak zwrotu do osoby trzeciej (pewność 0.95).
    - Vocative-Predicate Lock: Obecność męskiego wołacza jednoznacznie wyznacza target_gender = 'MALE' i vocative_lock = True.
    """
    if turn is None:
        return turn

    # Jeśli tura zawiera wiele zdarzeń, podziel na pod-segmenty SubTurn przed wyznaczeniem stanu adresata
    if len(turn.events) > 1 and len(getattr(turn, "sub_turns", [])) <= 1:
        turn.partition_subturns(series_bible=series_bible)

    # Jeśli tura składa się z wielu pod-segmentów SubTurn, rozwiązuj stan adresata dla każdego SubTurn niezależnie
    if hasattr(turn, "sub_turns") and len(turn.sub_turns) > 1:
        for st in turn.sub_turns:
            resolve_turn_addressee(
                st,
                previous_turn=previous_turn,
                series_bible=series_bible,
                max_exchange_gap_ms=max_exchange_gap_ms,
                next_turn=next_turn,
                prior_turns=prior_turns
            )
        sub_genders = {st.target_gender for st in turn.sub_turns if st.target_gender and st.target_gender not in ("AMBIGUOUS", "UNKNOWN")}
        if len(sub_genders) > 1:
            turn.target_speaker = None
            turn.target_gender = "AMBIGUOUS"
            turn.target_confidence = 0.0
            turn.vocative_lock = False
            turn.addressee_number = "PLURAL"
        else:
            first_st = turn.sub_turns[0]
            turn.target_speaker = first_st.target_speaker
            turn.target_gender = first_st.target_gender
            turn.target_confidence = first_st.target_confidence
            turn.vocative_lock = first_st.vocative_lock
            turn.addressee_number = first_st.addressee_number
        return turn

    # Hotfix 11.1.5 (P2-1 / E-05a): Izolacja napisów ekranowych (is_sign == True lub speaker.lower() == 'sign')
    is_sign_turn = (
        getattr(turn, "is_sign", False)
        or str(getattr(turn, "speaker", "")).lower() in ("sign", "szyld", "napis")
        or any(getattr(ev, "is_sign", False) or str(getattr(ev, "name", "")).lower() in ("sign", "szyld", "napis") for ev in getattr(turn, "events", []))
    )
    if is_sign_turn:
        turn.target_speaker = None
        turn.target_gender = None
        turn.target_confidence = 0.0
        turn.vocative_lock = False
        for ev in turn.events:
            setattr(ev, "target_speaker", None)
            setattr(ev, "target_actor", None)
            setattr(ev, "target_gender", None)
            setattr(ev, "target_confidence", 0.0)
            setattr(ev, "vocative_lock", False)
        return turn

    # Niewidzialność myśli dla dyskursu zewnętrznego
    if is_internal_monologue(turn):
        turn.target_speaker = None
        turn.target_gender = None
        turn.target_confidence = 0.0
        turn.vocative_lock = False
        for ev in turn.events:
            setattr(ev, "target_speaker", None)
            setattr(ev, "target_actor", None)
            setattr(ev, "target_gender", None)
            setattr(ev, "target_confidence", 0.0)
            setattr(ev, "addressee_number", turn.addressee_number)
            setattr(ev, "is_plural", turn.is_plural)
            setattr(ev, "vocative_lock", False)
            setattr(ev, "speaker_turn", turn)
            setattr(ev, "scene_participants", turn.scene_participants)
            setattr(ev, "scene_has_male_participant", turn.scene_has_male_participant)
            setattr(ev, "plural_group_gender", turn.plural_group_gender)
            setattr(ev, "you_group_gender", turn.you_group_gender)
        return turn

    # Krok 1: Weryfikacja jawnego wołacza w obrębie pod-tury (pewność 0.98)
    voc_actor, voc_gender = _detect_turn_vocative(turn, series_bible=series_bible)
    if voc_actor and not voc_gender and series_bible:
        _, voc_gender, _ = _resolve_character_canonical_and_gender(voc_actor, series_bible=series_bible)

    # Hotfix 11.1.5 (P2-1 / INC-AVT-027 / E-06): Weryfikacja obecności w scenie na podstawie dramatic_sequences
    if voc_actor and hasattr(turn, "events") and turn.events:
        dram_seqs = getattr(series_bible, "dramatic_sequences", None) if series_bible else None
        if not dram_seqs and hasattr(turn, "dramatic_sequences"):
            dram_seqs = turn.dramatic_sequences
        if dram_seqs:
            first_ev = turn.events[0]
            for seq in dram_seqs:
                tr_str = getattr(seq, "time_range", "")
                if _is_event_in_time_range(first_ev, tr_str):
                    chars_pres = [str(c).lower().strip() for c in (getattr(seq, "characters_present", []) or []) if c]
                    active_speakers = [str(t.speaker).lower().strip() for t in (prior_turns or []) if getattr(t, "speaker", None)]
                    if chars_pres and (voc_actor.lower().strip() not in chars_pres and voc_actor.lower().strip() not in active_speakers):
                        voc_actor = None
                        voc_gender = None
                    break

    if voc_actor and voc_gender:
        turn.target_speaker = voc_actor
        turn.target_gender = voc_gender
        turn.target_confidence = 0.98
        turn.vocative_lock = True
    elif not turn.vocative_lock:
        turn_has_2nd = has_second_person_markers(turn)

        # Krok 2: Backward Lookback z bramką Ping-Ponga
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
                    turn.target_confidence = 0.90
                    if getattr(first_ev, "target_speaker", None):
                        turn.target_speaker = getattr(first_ev, "target_speaker")
                    lookback_resolved = True

            # 2b. Poprzednie kwestie tego samego mówcy w scenie (Δt < 5.0 s)
            if not lookback_resolved:
                history = list(prior_turns or [])
                if previous_turn and previous_turn not in history:
                    history.append(previous_turn)

                for prev in reversed(history):
                    if not prev or is_discourse_ignorable(prev) or is_internal_monologue(prev):
                        continue
                    if is_discourse_ignorable(getattr(prev, "speaker", "")):
                        continue
                    if is_narrative_style(getattr(prev, "style", "")) != is_narrative_style(getattr(turn, "style", "")):
                        break
                    if is_sign_or_title_item(prev):
                        break
                    if _is_offscreen_speaker_excluded(prev, turn, series_bible=series_bible):
                        continue

                    gap_ms = max(0, turn.start - prev.end)
                    if gap_ms > max_exchange_gap_ms:
                        break
                    if _is_same_character(prev.speaker, turn.speaker, series_bible=series_bible):
                        prev_text = prev.text
                        if (
                            prev.target_gender == "MALE"
                            or MASCULINE_ADDRESS_DESCRIPTOR_REGEX.search(prev_text)
                            or any(getattr(ev, "target_gender", None) == "MALE" for ev in prev.events)
                        ):
                            turn.target_gender = "MALE"
                            turn.target_confidence = 0.90
                            if prev.target_speaker:
                                turn.target_speaker = prev.target_speaker
                            lookback_resolved = True
                            break

            # 2c. Poprzedni mówca w dialogu dwugłosowym (inny mówca głośny)
            if not lookback_resolved:
                history = list(prior_turns or [])
                if previous_turn and previous_turn not in history:
                    history.append(previous_turn)

                for prev in reversed(history):
                    if not prev or is_discourse_ignorable(prev) or is_internal_monologue(prev):
                        continue
                    if is_discourse_ignorable(getattr(prev, "speaker", "")):
                        continue
                    if is_narrative_style(getattr(prev, "style", "")) != is_narrative_style(getattr(turn, "style", "")):
                        break
                    if is_sign_or_title_item(prev):
                        break
                    if _is_offscreen_speaker_excluded(prev, turn, series_bible=series_bible):
                        continue

                    gap_ms = max(0, turn.start - prev.end)
                    if gap_ms > max_exchange_gap_ms:
                        break

                    if not _is_same_character(prev.speaker, turn.speaker, series_bible=series_bible):
                        # Weryfikacja aktywnego ping-ponga
                        is_ping_pong = False
                        for earlier in reversed(history):
                            if earlier is prev or earlier.end > prev.start:
                                continue
                            if _is_same_character(earlier.speaker, turn.speaker, series_bible=series_bible) and (prev.start - earlier.end) < 5000:
                                is_ping_pong = True
                                break

                        # Ściana cięcia sceny (SceneBoundaryWall): cisza >= 3.5 s bez aktywnego ping-ponga
                        if gap_ms >= 3500 and not is_ping_pong:
                            break

                        if gap_ms < 3500:
                            # Styk Delta_t < 3.5 s: dziedzicz z poprzedniego mówcy głośnego
                            part_count = len(getattr(turn, "scene_participants", []) or [])
                            is_dyadic = (part_count <= 2)
                            turn.target_speaker = prev.speaker
                            turn.target_confidence = 0.95 if (is_dyadic and (is_ping_pong or gap_ms < 2500)) else 0.85
                            _, prev_g, _ = _resolve_character_canonical_and_gender(
                                prev.speaker, series_bible=series_bible, context_item=prev
                            )
                            turn.target_gender = prev_g or getattr(prev, "speaker_gender", None)
                            lookback_resolved = True
                            break
                        elif 2500 <= gap_ms < max_exchange_gap_ms:
                            # Dla 2.5 s <= Delta_t < 5.0 s dziedzicz WYŁĄCZNIE gdy potwierdzony aktywny Ping-Pong
                            # lub poprzednia kwestia była pytaniem skierowanym do obecnego mówcy
                            is_question_to_curr = ("?" in prev.text) and (_detect_turn_vocative(prev, series_bible)[0] is None)

                            if is_ping_pong or is_question_to_curr:
                                turn.target_speaker = prev.speaker
                                turn.target_confidence = 0.85
                                _, prev_g, _ = _resolve_character_canonical_and_gender(
                                    prev.speaker, series_bible=series_bible, context_item=prev
                                )
                                turn.target_gender = prev_g or getattr(prev, "speaker_gender", None)
                                lookback_resolved = True
                            break
                        else:
                            break

        # Krok 3: Forward Lookahead (< 2.0 s przy pytaniu 2. os. ?)
        lookahead_resolved = False
        if not lookback_resolved and turn_has_2nd and turn.target_gender is None:
            no_prior_speaker = (
                previous_turn is None
                or not previous_turn.speaker
                or is_discourse_ignorable(previous_turn)
                or is_internal_monologue(previous_turn)
                or is_discourse_ignorable(previous_turn.speaker)
                or (turn.start - previous_turn.end > max_exchange_gap_ms)
            )
            if (
                no_prior_speaker
                and next_turn is not None
                and next_turn.speaker
                and not _is_same_character(next_turn.speaker, turn.speaker, series_bible=series_bible)
                and not is_discourse_ignorable(next_turn)
                and not is_internal_monologue(next_turn)
                and not is_discourse_ignorable(next_turn.speaker)
                and not is_sign_or_title_item(next_turn)
                and not _is_offscreen_speaker_excluded(next_turn, turn, series_bible=series_bible)
                and is_narrative_style(getattr(next_turn, "style", "")) == is_narrative_style(getattr(turn, "style", ""))
            ):
                forward_gap_ms = next_turn.start - turn.end
                next_voc, _ = _detect_turn_vocative(next_turn, series_bible=series_bible)
                if 0 <= forward_gap_ms <= 3500 and not next_voc:
                    if not (_is_mob_or_crowd_speaker(turn.speaker) and not _is_mob_or_crowd_speaker(next_turn.speaker)):
                        resp_speaker = next_turn.speaker
                        _, resp_gender, _ = _resolve_character_canonical_and_gender(
                            resp_speaker, series_bible=series_bible, context_item=next_turn
                        )
                        if not resp_gender and hasattr(next_turn, "speaker_gender"):
                            resp_gender = next_turn.speaker_gender

                        resp_g_l = (resp_gender or "").lower()
                        norm_resp_g = "MALE" if resp_g_l in ("male", "mężczyzna", "masculine") else (
                            "FEMALE" if resp_g_l in ("female", "kobieta", "feminine") else None
                        )
                        if norm_resp_g or resp_speaker:
                            turn.target_speaker = resp_speaker
                            turn.target_gender = norm_resp_g
                            turn.target_confidence = 0.85
                            lookahead_resolved = True

        # Krok 4: Wymiana tur A <-> B (fallback przy braku wołacza, lookback i lookahead)
        is_isolated_mob_turn = (
            _is_mob_or_crowd_speaker(turn.speaker)
            and not turn_has_2nd
            and not getattr(turn, "vocative_lock", False)
        )
        if not lookback_resolved and not lookahead_resolved and turn.target_speaker is None and not is_isolated_mob_turn:
            if (
                previous_turn is not None
                and previous_turn.speaker
                and not _is_same_character(previous_turn.speaker, turn.speaker, series_bible=series_bible)
                and not is_discourse_ignorable(previous_turn)
                and not is_internal_monologue(previous_turn)
                and not is_discourse_ignorable(previous_turn.speaker)
                and not is_sign_or_title_item(previous_turn)
                and not _is_offscreen_speaker_excluded(previous_turn, turn, series_bible=series_bible)
                and is_narrative_style(getattr(previous_turn, "style", "")) == is_narrative_style(getattr(turn, "style", ""))
            ):
                gap_ms = max(0, turn.start - previous_turn.end)
                if gap_ms <= max_exchange_gap_ms:
                    turn.target_speaker = previous_turn.speaker
                    turn.target_confidence = 0.80
                    _, prev_g, _ = _resolve_character_canonical_and_gender(
                        previous_turn.speaker, series_bible=series_bible, context_item=previous_turn
                    )
                    turn.target_gender = prev_g or getattr(previous_turn, "speaker_gender", None)

    # Weryfikacja obecności uczestnika męskiego i klasyfikacja We_Group
    if not turn.scene_has_male_participant:
        if previous_turn:
            turn.compute_scene_participants([previous_turn], series_bible=series_bible)
        elif is_character_male(turn.speaker, series_bible=series_bible, context_item=turn):
            turn.scene_has_male_participant = True
        elif turn.target_gender == "MALE":
            turn.scene_has_male_participant = True

    if turn.duration_ms >= 0:
        pass

    # Propagacja metadanych dyskursu na wszystkie zdarzenia tury
    if not (hasattr(turn, "sub_turns") and len(turn.sub_turns) > 1):
        for ev in turn.events:
            setattr(ev, "target_speaker", turn.target_speaker)
            setattr(ev, "target_actor", turn.target_speaker)
            setattr(ev, "target_gender", turn.target_gender)
            setattr(ev, "target_confidence", turn.target_confidence)
            setattr(ev, "addressee_number", turn.addressee_number)
            setattr(ev, "is_plural", turn.is_plural)
            setattr(ev, "vocative_lock", turn.vocative_lock)
            setattr(ev, "speaker_turn", turn)
            setattr(ev, "scene_participants", turn.scene_participants)
            setattr(ev, "scene_has_male_participant", turn.scene_has_male_participant)
            setattr(ev, "plural_group_gender", turn.plural_group_gender)
            setattr(ev, "you_group_gender", turn.you_group_gender)
    else:
        # Standard 11.1 (LUKA-E7-01): propagacja metadanych ze specyficznego sub_turn na jego zdarzenia
        for sub in turn.sub_turns:
            sub_spk = getattr(sub, "target_speaker", None) or turn.target_speaker
            sub_gender = getattr(sub, "target_gender", None) or turn.target_gender
            sub_conf = getattr(sub, "target_confidence", None) or turn.target_confidence
            sub_addr_num = getattr(sub, "addressee_number", None) or turn.addressee_number
            sub_is_pl = getattr(sub, "is_plural", None) if getattr(sub, "is_plural", None) is not None else turn.is_plural
            sub_voc = getattr(sub, "vocative_lock", None) if getattr(sub, "vocative_lock", None) is not None else turn.vocative_lock

            for ev in getattr(sub, "events", []):
                setattr(ev, "target_speaker", sub_spk)
                setattr(ev, "target_actor", sub_spk)
                setattr(ev, "target_gender", sub_gender)
                setattr(ev, "target_confidence", sub_conf)
                setattr(ev, "addressee_number", sub_addr_num)
                setattr(ev, "is_plural", sub_is_pl)
                setattr(ev, "vocative_lock", sub_voc)
                setattr(ev, "speaker_turn", turn)
                setattr(ev, "sub_turn", sub)
                setattr(ev, "scene_participants", turn.scene_participants)
                setattr(ev, "scene_has_male_participant", turn.scene_has_male_participant)
                setattr(ev, "plural_group_gender", turn.plural_group_gender)
                setattr(ev, "you_group_gender", turn.you_group_gender)

    return turn


def group_speaker_turns(
    events: List[Any],
    max_gap_ms: int = 2500,
    series_bible: Optional[Any] = None
) -> List[SpeakerTurn]:
    """
    Grupuje ciągłe wypowiedzi tego samego mówcy (Δt < 2.5 s / 2500 ms) w obiekt SpeakerTurn.
    Automatycznie rozcina na niezależne pod-segmenty (SubTurn) przy wykryciu Addressee Pivot.
    """
    if not events:
        return []

    turns: List[SpeakerTurn] = []
    current_turn: Optional[SpeakerTurn] = None

    for ev in events:
        raw_spk = (
            getattr(ev, "name", "") or
            getattr(ev, "actor", "") or
            getattr(ev, "speaker", "") or
            ""
        ).strip()
        # Wywołanie normalize_actor_tag(event.name) na wejściu każdej linii/zdarzenia
        _ = normalize_actor_tag(raw_spk)
        clean_spk, tag_gender = _normalize_event_actor(raw_spk)
        if tag_gender in ("MALE", "FEMALE"):
            setattr(ev, "speaker_gender", tag_gender)
            setattr(ev, "speaker_confidence", 1.0)
        setattr(ev, "normalized_name", clean_spk)
        setattr(ev, "name", clean_spk or raw_spk)

        spk = clean_spk or raw_spk
        start = getattr(ev, "start", 0)

        if current_turn is None:
            current_turn = SpeakerTurn(speaker=spk, events=[ev])
            if tag_gender in ("MALE", "FEMALE"):
                current_turn.speaker_gender = tag_gender
                if tag_gender == "MALE":
                    current_turn.scene_has_male_participant = True
        else:
            gap_ms = start - current_turn.end
            # Sprawdzenie ciągłości tego samego mówcy i progu czasowego
            if _is_same_character(spk, current_turn.speaker, series_bible=series_bible) and gap_ms <= max_gap_ms:
                # Weryfikacja punktu obrotu adresata (Addressee Pivot)
                if current_turn.events and is_addressee_pivot(current_turn.events[-1], ev, series_bible=series_bible):
                    turns.append(current_turn)
                    current_turn = SubTurn(speaker=spk, events=[ev])
                    if tag_gender in ("MALE", "FEMALE"):
                        current_turn.speaker_gender = tag_gender
                        if tag_gender == "MALE":
                            current_turn.scene_has_male_participant = True
                else:
                    current_turn.append(ev)
            else:
                turns.append(current_turn)
                current_turn = SpeakerTurn(speaker=spk, events=[ev])
                if tag_gender in ("MALE", "FEMALE"):
                    current_turn.speaker_gender = tag_gender
                    if tag_gender == "MALE":
                        current_turn.scene_has_male_participant = True

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
        turn.partition_subturns(series_bible=series_bible)
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

    # Inwariant Grupy Mieszanej: wyliczenie aktywnych uczestników w oknie ±15.0 s ze ścianami cięcia sceny
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


def build_discourse_topology(
    events: List[Any],
    series_bible: Optional[Any] = None,
    max_turn_gap_ms: int = 2500,
    max_exchange_gap_ms: int = 5000
) -> List[SpeakerTurn]:
    """
    Buduje pełną topologię dyskursu scenicznego (Standard 9.0/9.1):
    - Przypisuje adresatów dialogu z izolacją kwestii wewnętrznych, narracji i napisów ekranowych (is_sign: true),
    - Zapewnia absolutny priorytet rekordów P0 ze zweryfikowaną płcią (has_verified_gender: true),
    - Izoluje zdarzenia typu is_sign: true od algebry We_Group i You_Group.
    """
    return process_scene_discourse(
        events=events,
        series_bible=series_bible,
        max_turn_gap_ms=max_turn_gap_ms,
        max_exchange_gap_ms=max_exchange_gap_ms
    )


class SceneDiscourseGraph:
    """
    Graf dyskursu scenicznego i arbitrażu telemetrii zdarzeń (Standard 9.2).
    Zapewnia absolutny prymat rekordu P0 i jawnej etykiety aktora z [Events].
    """
    @classmethod
    def build_discourse_topology(
        cls,
        events: List[Any],
        series_bible: Optional[Any] = None,
        max_turn_gap_ms: int = 2500,
        max_exchange_gap_ms: int = 5000,
        f0_by_line: Optional[Dict[int, float]] = None
    ) -> List[SpeakerTurn]:
        actor_consensus = cls.compute_actor_gender_consensus(events, f0_by_line=f0_by_line, series_bible=series_bible)
        return build_discourse_topology(
            events=events,
            series_bible=series_bible,
            max_turn_gap_ms=max_turn_gap_ms,
            max_exchange_gap_ms=max_exchange_gap_ms
        )

    @classmethod
    def compute_actor_gender_consensus(
        cls,
        events: List[Any],
        f0_by_line: Optional[Dict[int, float]] = None,
        series_bible: Optional[Any] = None
    ) -> Dict[str, str]:
        """
        Hotfix 11.1.5 (P1-3 / E-03): Konsensus płci per aktor w odcinku (Actor Gender Consensus).
        Dla każdego aktora o statusie UNKNOWN wyznacza stałą płeć na podstawie mediany F0
        ze wszystkich jego kwestii w odcinku.
        """
        import numpy as np
        actor_f0: Dict[str, List[float]] = {}
        for idx, ev in enumerate(events):
            act = getattr(ev, "name", "") or getattr(ev, "actor", "")
            if not act:
                continue
            act_low = act.lower()
            if any(k in act_low for k in ("sign", "szyld", "napis", "title", "caption")):
                continue
            act_clean = re.sub(r"\s*\([^)]*\)", "", act).strip()
            if series_bible and hasattr(series_bible, "get_character_gender"):
                known_g = series_bible.get_character_gender(act_clean)
                if known_g and str(known_g).upper() not in ("UNKNOWN", "NONE"):
                    continue
            f0_val = None
            if f0_by_line and idx in f0_by_line:
                f0_val = f0_by_line[idx]
            elif hasattr(ev, "f0") and getattr(ev, "f0"):
                try:
                    f0_val = float(getattr(ev, "f0"))
                except Exception:
                    f0_val = None
            if f0_val and f0_val > 0:
                actor_f0.setdefault(act_clean, []).append(f0_val)

        consensus: Dict[str, str] = {}
        for act, f0_list in actor_f0.items():
            if f0_list:
                med = float(np.median(f0_list))
                if med <= 150.0:
                    consensus[act] = "MALE"
                elif med >= 165.0:
                    consensus[act] = "FEMALE"
        return consensus

    @staticmethod
    def validate_pragmatic_register_against_speaker(
        register: Optional[str],
        speaker_name: str = "",
        character_dossier: Optional[Any] = None,
        character_registry_entry: Optional[Any] = None,
        audio_jp: str = "",
        clean_en: str = "",
        prosody_tags: str = "",
        setting_era: str = "",
        series_bible: Optional[Any] = None,
    ) -> Optional[str]:
        from whisper_disambiguator import WhisperDisambiguator
        return WhisperDisambiguator.validate_pragmatic_register_against_speaker(
            register=register,
            speaker_name=speaker_name,
            character_dossier=character_dossier,
            character_registry_entry=character_registry_entry,
            audio_jp=audio_jp,
            clean_en=clean_en,
            prosody_tags=prosody_tags,
            setting_era=setting_era,
            series_bible=series_bible,
        )

    @staticmethod
    def arbitrate_event_telemetry(
        event: Any = None,
        series_bible: Optional[Any] = None,
        episode_profiler: Optional[Any] = None,
        aux_telemetry: Optional[Dict[str, Any]] = None,
        raw_actor: Optional[str] = None,
        inferred_actor: Optional[str] = None,
        verified_p0_gender: Optional[str] = None,
        verified_addressee_p0_gender: Optional[str] = None,
        has_verified_gender: bool = False,
        scene_female_only: bool = False,
        target_actor: Optional[str] = None,
        is_internal_monologue: bool = False,
        is_sign: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        r"""
        Prymat Tożsamości Rodzajowej z Rekordu P0 i Etykiety Aktora Events (Standard 9.6, 2C.1, R1.4, R3.2):
        - Czyści raw_actor i target_actor z wszelkich nawiasów F0: re.sub(r"\s*\([^)]*\)", "", ...)
        - Wymusza p0_gender dla mówcy i adresata ze słownika P0 SeriesBible / EpisodeProfiler.
        - Izoluje monologi wewnętrzne (is_internal_monologue: true) przed fałszywym adresatem zewnętrznym.
        - Izoluje napisy ekranowe (is_sign: true) jako Mówca: sign (NEUTRAL).
        """
        telemetry = dict(aux_telemetry or {})

        # Oczyszczenie target_actor z nawiasowych adnotacji F0 i ekstrakcja jawnego tagu
        raw_target_in = target_actor or telemetry.get("target_actor") or telemetry.get("addressee") or kwargs.get("addressee")
        clean_target_actor = ""
        explicit_target_g = None
        if raw_target_in:
            norm_target, parsed_tg = normalize_actor_tag(str(raw_target_in))
            clean_target_actor = norm_target
            if parsed_tg in ("MALE", "FEMALE"):
                explicit_target_g = parsed_tg

        # Oczyszczenie raw_actor ze zdarzenia i ekstrakcja jawnego tagu
        raw_name = raw_actor or getattr(event, "actor", None) or getattr(event, "speaker_name", None) or getattr(event, "name", None)
        if not raw_name and isinstance(event, dict):
            raw_name = event.get("actor") or event.get("speaker_name") or event.get("name")
        clean_raw = ""
        explicit_spk_g = None
        if raw_name:
            norm_raw, parsed_sg = normalize_actor_tag(str(raw_name))
            clean_raw = norm_raw
            if parsed_sg in ("MALE", "FEMALE"):
                explicit_spk_g = parsed_sg

        # 0. Obsługa napisów ekranowych (is_sign) - brak płci osobowej (Operacja 2C.1)
        ev_is_sign = bool(
            is_sign
            or kwargs.get("is_sign")
            or getattr(event, "is_sign", False)
            or (clean_raw and clean_raw.lower() in ("sign", "signs", "txt", "title", "caption", "szyld", "napis", "board", "screen"))
        )
        if ev_is_sign:
            telemetry["speaker_name"] = "sign"
            telemetry["speaker_gender"] = "NEUTRAL"
            telemetry["grammatical_gender"] = "NEUTRAL"
            telemetry["has_verified_gender"] = False
            telemetry["is_sign"] = True
            telemetry["target_actor"] = ""
            telemetry["target_gender"] = None
            telemetry["addressee_gender"] = None
            telemetry["dry_telemetry"] = "[Mówca: sign (NEUTRAL)]"
            return telemetry

        # 1. Pobierz aktora ze zdarzenia lub inferred_actor
        if not clean_raw or clean_raw.lower() in ("txt", "title"):
            clean_actor = str(inferred_actor or telemetry.get("speaker_name") or "").strip()
            clean_actor = re.sub(r"\s*\([^)]*\)", "", clean_actor).strip()
            clean_actor = re.sub(r"\s{2,}", " ", clean_actor)
        else:
            clean_actor = clean_raw

        is_composite_actor = any(sep in (clean_raw or clean_actor) for sep in ("/", "|", "&", "+"))
        if clean_actor in ("/", "|", ",") or clean_actor.lower() in ("all", "both"):
            spk_label = "POLYLOGUE"
            telemetry["speaker_name"] = spk_label
            telemetry["actor"] = spk_label
        elif is_composite_actor:
            spk_label = clean_actor
            telemetry["speaker_name"] = clean_actor
            telemetry["actor"] = clean_actor
            telemetry["polylogue"] = "POLYLOGUE"
        else:
            spk_label = clean_actor
            telemetry["speaker_name"] = clean_actor
            telemetry["actor"] = clean_actor

        # 2. Bezwarunkowy odczyt rekordu P0 z SeriesBible / EpisodeProfiler (Operacja 2C.1, R3.2, 2B.1, 2B.5, 2B.7)
        p0_gender = verified_p0_gender or kwargs.get("speaker_p0_gender")
        if p0_gender and str(p0_gender).upper() in ("UNKNOWN", "NEUTRAL"):
            p0_gender = None
        has_ver = has_verified_gender or bool(kwargs.get("speaker_p0_gender"))
        speaker_p0_verified = bool(p0_gender and has_ver)

        # P3-A: Rozstrzyganie płci i virility dla diad i grup złożonych (POLYLOGUE z separatorem)
        if not p0_gender and (spk_label == "POLYLOGUE" or is_composite_actor) and is_composite_actor:
            comp_src = clean_raw if clean_raw and any(sep in clean_raw for sep in ("/", "|", "&", "+")) else clean_actor
            sub_actors = [p.strip() for p in re.split(r"[/|&+,]\s*", comp_src) if p.strip()]
            found_m = 0
            found_f = 0
            for sub_a in sub_actors:
                sub_rec = None
                if series_bible:
                    if hasattr(series_bible, "resolve_character_record"):
                        sub_rec = series_bible.resolve_character_record(sub_a)
                    elif hasattr(series_bible, "get_character"):
                        sub_rec = series_bible.get_character(sub_a)
                    elif hasattr(series_bible, "characters") and isinstance(series_bible.characters, dict):
                        sub_rec = series_bible.characters.get(sub_a)
                        if not sub_rec:
                            for k, v in series_bible.characters.items():
                                if k.lower() == sub_a.lower():
                                    sub_rec = v
                                    break
                sub_g = None
                if isinstance(sub_rec, dict):
                    sub_g = sub_rec.get("gender")
                if not sub_g and episode_profiler and hasattr(episode_profiler, "character_dossiers"):
                    for cd in getattr(episode_profiler, "character_dossiers", []):
                        if getattr(cd, "name", "").lower() == sub_a.lower():
                            sub_g = getattr(cd, "gender", None) or getattr(cd, "apparent_gender", None)
                            break
                if sub_g:
                    sub_gu = str(sub_g).upper()
                    if sub_gu == "MALE":
                        found_m += 1
                    elif sub_gu == "FEMALE":
                        found_f += 1

            if found_m >= 1:
                p0_gender = "MALE"
                has_ver = True
                speaker_p0_verified = True
                telemetry["we_virility"] = "VIRILE"
                telemetry["group_virility"] = "VIRILE"
                if found_m + found_f >= 2:
                    spk_label = "POLYLOGUE"
                    telemetry["speaker_name"] = "POLYLOGUE"
                    telemetry["actor"] = "POLYLOGUE"
            elif found_f >= 1 and found_m == 0:
                p0_gender = "FEMALE"
                has_ver = True
                speaker_p0_verified = True
                telemetry["we_virility"] = "NON_VIRILE"
                telemetry["group_virility"] = "NON_VIRILE"
                if found_f >= 2:
                    spk_label = "POLYLOGUE"
                    telemetry["speaker_name"] = "POLYLOGUE"
                    telemetry["actor"] = "POLYLOGUE"

        if not p0_gender and series_bible and clean_actor:
            char_rec = None
            if hasattr(series_bible, "resolve_character_record"):
                char_rec = series_bible.resolve_character_record(clean_actor)
            elif hasattr(series_bible, "get_character"):
                char_rec = series_bible.get_character(clean_actor)
            elif hasattr(series_bible, "characters") and isinstance(series_bible.characters, dict):
                chars = series_bible.characters
                char_rec = chars.get(clean_actor)
                if not char_rec:
                    for k, v in chars.items():
                        if k.lower() == clean_actor.lower():
                            char_rec = v
                            break
                        if isinstance(v, dict) and clean_actor.lower() in [str(a).lower() for a in v.get("aliases", [])]:
                            char_rec = v
                            break
            if isinstance(char_rec, dict):
                g = char_rec.get("gender")
                if g and str(g).upper() != "UNKNOWN":
                    p0_gender = str(g).upper()
                    has_ver = bool(char_rec.get("has_verified_gender", False)) or char_rec.get("priority") in ("P0", "P1")
                    if has_ver:
                        speaker_p0_verified = True
                # Operacja 2B.5: Zachowanie kanonicznej nazwy jawnego aktora .ass
                if not clean_actor and char_rec.get("name"):
                    clean_actor = char_rec["name"]
                    telemetry["speaker_name"] = clean_actor
                    telemetry["actor"] = clean_actor

        if not p0_gender and episode_profiler and hasattr(episode_profiler, "character_dossiers") and clean_actor:
            for cd in getattr(episode_profiler, "character_dossiers", []):
                if getattr(cd, "name", "").lower() == clean_actor.lower():
                    g = getattr(cd, "gender", None) or getattr(cd, "apparent_gender", None)
                    if g and str(g).upper() != "UNKNOWN":
                        p0_gender = str(g).upper()
                        has_ver = True
                        speaker_p0_verified = True
                        break

        if not p0_gender and explicit_spk_g:
            p0_gender = explicit_spk_g
            has_ver = True
            speaker_p0_verified = True

        if not p0_gender and telemetry.get("speaker_gender") and str(telemetry.get("speaker_gender")).upper() not in ("UNKNOWN", "NEUTRAL"):
            p0_gender = str(telemetry.get("speaker_gender")).upper()
            has_ver = bool(telemetry.get("has_verified_gender"))
            speaker_p0_verified = has_ver

        # Operacja 2B.4 pkt 2: Formy męskie 1. os. mówcy blokują F0 krzyku bojowego
        pl_text = kwargs.get("polish_text") or telemetry.get("polish_text") or getattr(event, "text", "") or ""
        if isinstance(pl_text, str) and pl_text:
            m_first_male = re.search(
                r"\b(?:myślałem|miałem|zebrałem|usłyszałem|rozejrzałem|zaszedłem|poszedłem|zrobiłem|widziałem|chciałem|wiedziałem|mówiłem|czekałem|szedłem|brałem|bylem|byłem)\b|"
                r"\b(?:aniki|bro)\b",
                pl_text,
                re.IGNORECASE
            )
            if m_first_male:
                p0_gender = "MALE"
                has_ver = True
                speaker_p0_verified = True

        # Hotfix 11.1.5 (P1-3 / E-03): Egzekwowanie male_only_scene / female_only_scene z dramatic_sequences
        scene_male_only = bool(kwargs.get("scene_male_only"))
        scene_female_only_val = bool(scene_female_only or kwargs.get("scene_female_only"))
        dram_seqs = kwargs.get("dramatic_sequences")
        if not dram_seqs and episode_profiler and hasattr(episode_profiler, "dramatic_sequences"):
            dram_seqs = episode_profiler.dramatic_sequences
        if not dram_seqs and series_bible and hasattr(series_bible, "dramatic_sequences"):
            dram_seqs = series_bible.dramatic_sequences

        if dram_seqs and event:
            for seq in dram_seqs:
                tr_str = getattr(seq, "time_range", "")
                if _is_event_in_time_range(event, tr_str):
                    if getattr(seq, "male_only_scene", False) and not getattr(seq, "female_only_scene", False):
                        scene_male_only = True
                    elif getattr(seq, "female_only_scene", False) and not getattr(seq, "male_only_scene", False):
                        scene_female_only_val = True
                    break

        if scene_male_only:
            if not p0_gender or p0_gender == "UNKNOWN":
                p0_gender = "MALE"
                has_ver = True
                speaker_p0_verified = True
        elif scene_female_only_val:
            if not p0_gender or p0_gender == "UNKNOWN":
                p0_gender = "FEMALE"
                has_ver = True
                speaker_p0_verified = True

        # Hotfix 11.1.5 (P1-3 / E-03): Konsensus płci per aktor w odcinku (Actor Gender Consensus)
        actor_gender_consensus = kwargs.get("actor_gender_consensus")
        if (not p0_gender or p0_gender == "UNKNOWN") and actor_gender_consensus:
            cand_spk_key = clean_actor
            if cand_spk_key in actor_gender_consensus:
                p0_gender = actor_gender_consensus[cand_spk_key]
                has_ver = True
                speaker_p0_verified = True

        if p0_gender:
            p0_u = str(p0_gender).upper()
            telemetry["speaker_gender"] = p0_u
            telemetry["p0_gender"] = p0_u
            telemetry["has_verified_gender"] = has_ver
            telemetry["speaker_p0_verified"] = speaker_p0_verified
            if p0_u == "MALE":
                telemetry["grammatical_gender"] = "MASCULINE"
            elif p0_u == "FEMALE":
                telemetry["grammatical_gender"] = "FEMININE"
        else:
            if "speaker_gender" not in telemetry:
                telemetry["speaker_gender"] = "UNKNOWN"
            if "has_verified_gender" not in telemetry:
                telemetry["has_verified_gender"] = False
            if "grammatical_gender" not in telemetry:
                telemetry["grammatical_gender"] = "UNKNOWN"
            telemetry["speaker_p0_verified"] = False

        # 3. Izolacja monologu wewnętrznego (Style: Italics / is_internal_monologue)
        st_style = str(getattr(event, "style", "") or kwargs.get("style", "")).lower()
        has_monologue_style = any(k in st_style for k in ["italic", "flashback_italic", "thoughts", "internal"])
        ev_is_monologue = bool(
            is_internal_monologue
            or kwargs.get("is_internal_monologue")
            or getattr(event, "is_internal_monologue", False)
            or has_monologue_style
        )

        if ev_is_monologue:
            telemetry["target_actor"] = ""
            telemetry["target_gender"] = None
            telemetry["addressee_gender"] = None
            telemetry["target_grammatical_gender"] = None
            telemetry["target_p0_verified"] = False
            telemetry["is_internal_monologue"] = True
        else:
            # Gdy adresat jest tożsamy z mówcą w dialogu, wyznacz pusty lub drugiego rozmówcę
            if clean_target_actor and clean_target_actor.lower() == clean_actor.lower():
                clean_target_actor = ""

            telemetry["target_actor"] = clean_target_actor
            addr_candidate = verified_addressee_p0_gender
            target_p0_verified = bool(verified_addressee_p0_gender)

            if not addr_candidate and series_bible and clean_target_actor:
                ch_addr = None
                if hasattr(series_bible, "resolve_character_record"):
                    ch_addr = series_bible.resolve_character_record(clean_target_actor)
                elif hasattr(series_bible, "get_character"):
                    ch_addr = series_bible.get_character(clean_target_actor)
                elif hasattr(series_bible, "characters") and isinstance(series_bible.characters, dict):
                    chars = series_bible.characters
                    ch_addr = chars.get(clean_target_actor)
                    if not ch_addr:
                        for k, v in chars.items():
                            if k.lower() == clean_target_actor.lower():
                                ch_addr = v
                                break
                            if isinstance(v, dict) and clean_target_actor.lower() in [str(a).lower() for a in v.get("aliases", [])]:
                                ch_addr = v
                                break
                if isinstance(ch_addr, dict):
                    ag = ch_addr.get("gender")
                    if ag and str(ag).upper() in ("MALE", "FEMALE"):
                        addr_candidate = str(ag).upper()
                        if bool(ch_addr.get("has_verified_gender", False)) or ch_addr.get("priority") in ("P0", "P1"):
                            target_p0_verified = True

            if not addr_candidate and episode_profiler and hasattr(episode_profiler, "character_dossiers") and clean_target_actor:
                for cd in getattr(episode_profiler, "character_dossiers", []):
                    if getattr(cd, "name", "").lower() == clean_target_actor.lower():
                        ag = getattr(cd, "gender", None) or getattr(cd, "apparent_gender", None)
                        if ag and str(ag).upper() in ("MALE", "FEMALE"):
                            addr_candidate = str(ag).upper()
                            target_p0_verified = True
                            break

            if not addr_candidate and explicit_target_g:
                addr_candidate = explicit_target_g
                target_p0_verified = True

            if not addr_candidate and clean_target_actor:
                try:
                    from series_memory import resolve_lexical_label_gender
                    lex_g, _ = resolve_lexical_label_gender(clean_target_actor)
                    if lex_g in ("MALE", "FEMALE"):
                        addr_candidate = lex_g
                        target_p0_verified = False
                except Exception:
                    pass

            if not addr_candidate and clean_target_actor:
                actor_gender_consensus = kwargs.get("actor_gender_consensus")
                if actor_gender_consensus and clean_target_actor in actor_gender_consensus:
                    addr_candidate = actor_gender_consensus[clean_target_actor]
                    target_p0_verified = True
                elif scene_male_only:
                    addr_candidate = "MALE"
                    target_p0_verified = True
                elif scene_female_only_val:
                    addr_candidate = "FEMALE"
                    target_p0_verified = True

            if addr_candidate:
                addr_g = str(addr_candidate).upper()
                telemetry["addressee_gender"] = addr_g
                if addr_g == "FEMALE":
                    telemetry["target_gender"] = "FEMININE"
                    telemetry["target_grammatical_gender"] = "FEMININE"
                elif addr_g == "MALE":
                    telemetry["target_gender"] = "MASCULINE"
                    telemetry["target_grammatical_gender"] = "MASCULINE"
                telemetry["target_p0_verified"] = target_p0_verified
            else:
                telemetry["target_gender"] = None
                telemetry["addressee_gender"] = None
                telemetry["target_grammatical_gender"] = None
                telemetry["target_p0_verified"] = False

        # 4. Spójność sceny żeńskiej bez nadpisywania potwierdzonego mówcy męskiego (Operacja 2C.1)
        if scene_female_only or scene_female_only_val:
            spk_is_male = (telemetry.get("grammatical_gender") == "MASCULINE" or telemetry.get("speaker_gender") == "MALE")
            telemetry["group_virility"] = "NON_VIRILE"
            telemetry["we_virility"] = "VIRILE" if spk_is_male else "NON_VIRILE"
            telemetry["you_virility"] = "NON_VIRILE"

        # Operacja 2B.3: Ochrona pojedynczej adresatki przed you_virility = VIRILE
        if telemetry.get("addressee_gender") == "FEMALE" or telemetry.get("target_gender") == "FEMININE":
            try:
                from series_memory import is_plural_actor
                target_act_lbl = telemetry.get("target_actor") or ""
                if not is_plural_actor(target_act_lbl) and not any(w in target_act_lbl.lower() for w in ["grupa", "dwie", "panie", "kobiety"]):
                    telemetry["you_virility"] = "NON_VIRILE"
            except Exception:
                pass

        # 5. Generowanie spójnego tagu dry_telemetry wolnego od nawiasów F0
        dry_segs = []
        spk_g_tag = telemetry.get("grammatical_gender")
        if spk_g_tag in ("MASCULINE", "FEMININE"):
            dry_segs.append(f"Mówca: {telemetry['speaker_name']} ({spk_g_tag})")
        elif telemetry.get("speaker_name"):
            dry_segs.append(f"Mówca: {telemetry['speaker_name']}")

        tgt_g_tag = telemetry.get("target_grammatical_gender") or telemetry.get("target_gender")
        tgt_act = str(telemetry.get("target_actor") or "").strip()
        is_generic_tgt = tgt_act.lower() in {"mężczyzna", "kobieta", "mężczyźni", "kobiety", "brak", "none", "unspecified"}
        if not ev_is_monologue and tgt_act and not is_generic_tgt and tgt_g_tag in ("MASCULINE", "FEMININE"):
            dry_segs.append(f"Adresat: {tgt_act} ({tgt_g_tag})")

        if telemetry.get("polylogue") and telemetry.get("speaker_name") != "POLYLOGUE":
            dry_segs.append(f"Scena: {telemetry['polylogue']}")

        if dry_segs:
            telemetry["dry_telemetry"] = f"[{' | '.join(dry_segs)}]"
            telemetry["telemetry_tag"] = telemetry["dry_telemetry"]

        return telemetry
