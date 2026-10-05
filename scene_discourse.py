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
from typing import List, Dict, Any, Tuple, Optional


class DualVoiceTagPreserver:
    """
    Deterministyczny rozbijacz i rekompozytor dwugłosów w zdarzeniach ASS (0.00 PLN).
    Chroni tagi formatowania (np. {\\an8}, {\\pos(x,y)}) oraz stylizację fansuberską.
    """

    DUAL_VOICE_STRICT_REGEX = re.compile(
        r"^((?:\{[^}]*\})*)\s*[-–—]\s*(.+?)(?:\\[Nnh]|\n)\s*[-–—]\s*(.+)$",
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

        prefix_tags = m.group(1) or ""
        line_a = m.group(2).strip()
        line_b = m.group(3).strip()

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
        setattr(ev_a, "_prefix_tags", prefix_tags)

        ev_b = event.copy()
        ev_b.text = line_b
        ev_b.name = spk_b
        setattr(ev_b, "_is_dual_voice_sub", True)
        setattr(ev_b, "_dual_voice_part", "B")
        setattr(ev_b, "_master_orig_idx", orig_idx)
        setattr(ev_b, "_prefix_tags", prefix_tags)

        meta = {
            "orig_idx": orig_idx,
            "prefix_tags": prefix_tags,
            "speaker_a": spk_a,
            "speaker_b": spk_b,
            "raw_name": raw_name,
            "line_a_raw": line_a,
            "line_b_raw": line_b
        }

        return ev_a, ev_b, meta

    @classmethod
    def recompose_text(cls, text_a: str, text_b: str, prefix_tags: str = "") -> str:
        """
        Rekomponuje przetłumaczone kwestie A i B w pojedynczy poprawny format ASS:
        prefix_tags + "- " + text_a + "\\N- " + text_b
        Usuwa nadmiarowe, zduplikowane myślniki i spacje.
        """
        clean_a = (text_a or "").strip()
        clean_b = (text_b or "").strip()

        # Usunięcie wiodących myślników, aby nie dopuścić do "-- " lub "- - "
        clean_a = re.sub(r"^[-–—]\s*", "", clean_a).strip()
        clean_b = re.sub(r"^[-–—]\s*", "", clean_b).strip()

        # Oczyszczenie zduplikowanych \N
        clean_a = re.sub(r"\\[Nnh]+", " ", clean_a).strip()
        clean_b = re.sub(r"\\[Nnh]+", " ", clean_b).strip()

        tags = prefix_tags.strip() if prefix_tags else ""
        return f"{tags}- {clean_a}\\N- {clean_b}".strip()


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
        Jeśli Δt <= max_delta_ms i (temat kontynuuje rzemiosło/zbroję,
        lub następuje bezpośrednio po replice ojca 'Słucham?',
        lub tembr F0 >= 220 Hz wskazuje głos dziewczynki/kobiety),
        utrzymuje tożsamość mówcy (np. Shizuku) i blokuje maskulinizację.
        """
        if delta_ms > max_delta_ms and not (audio_f0 and audio_f0 >= 220.0):
            return None

        has_topic = bool(cls.ARMOR_CRAFTING_TOPIC_REGEX.search(text))
        has_female_f0 = (audio_f0 is not None and audio_f0 >= 220.0)

        if is_after_acknowledgment or has_topic or has_female_f0:
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
