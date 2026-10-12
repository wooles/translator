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


def is_internal_monologue(event_or_text: Any, target_speaker: Optional[str] = None) -> bool:
    """
    Kryteria zatwierdzenia monologu wewnętrznego (is_internal_monologue = True):
    Kwestia otrzymuje dostęp do true_gender postaci WYŁĄCZNIE wtedy, gdy spełnia łącznie:
    1) Cała linia ujęta jest w nawiasy okrągłe ASCII ( ) lub CJK （ ） ALBO posiada styl ASS typu 'Thoughts'/'Internal'
       ALBO jest w całości zapisana kursywą {\\i1}.
    2) ORAZ nie zawiera prefiksów radiowych/telefonicznych ([Radio], [Phone], [Comm]).
    3) ORAZ nie posiada zdefiniowanego adresata w grafie dyskursu (target_speaker is None; brak szeptu do towarzysza).
    4) ORAZ nie zawiera japońskich cudzysłowów dialogowych 「 」/『 』 ani nawiasów skilli 【 】/《 》.
    """
    if event_or_text is None:
        return False

    raw_text = getattr(event_or_text, "text", str(event_or_text)) or ""
    style = getattr(event_or_text, "style", "") or ""

    # Odrzucenie cudzysłowów dialogowych i nawiasów skilli
    if SubtitleDiscourseSanitizer.is_dialogue_quote(raw_text):
        return False
    if SubtitleDiscourseSanitizer.is_skill_or_system_bracket(raw_text):
        return False

    # Sprawdzenie prefiksów radiowych/telefonicznych
    if re.search(r"\[(?:Radio|Phone|Comm)\]", raw_text, re.IGNORECASE):
        return False

    # Sprawdzenie zdefiniowanego adresata
    target = target_speaker if target_speaker is not None else (getattr(event_or_text, "addressee", None) or getattr(event_or_text, "target", None))
    if target is not None and str(target).strip():
        return False

    # Oczyszczenie z tagów ASS dla analizy nawiasów
    pure_text = SubtitleDiscourseSanitizer.ASS_TAGS_REGEX.sub("", raw_text).strip()

    # 1. Styl "Thoughts" / "Internal"
    style_low = style.lower()
    if any(k in style_low for k in ["thought", "internal", "myśl"]):
        return True

    # 2. Nawiasy okrągłe ASCII ( ) lub CJK （ ） obejmujące całą linię
    if (pure_text.startswith("(") and pure_text.endswith(")")) or (pure_text.startswith("（") and pure_text.endswith("）")):
        return True

    # 3. W całości zapisana kursywą {\i1}
    if raw_text.strip().startswith("{\\i1}") and ("{\\i0}" not in raw_text or raw_text.strip().endswith("{\\i0}")):
        return True

    return False


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
