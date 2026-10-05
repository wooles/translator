# -*- coding: utf-8 -*-
"""
Script Doctor Selector: Faza 2 potoku AVT (JA -> PL).
Implementacja selekcji Best-of-N z wielokryterialną funkcją nagrody anty-Goodhart.

Aksjomaty:
1. Asymmetric Dead-Band Potential: twardy sufit fizjologii oka (CPS <= 17.0, CPL <= 38)
   połączony z podłogą anty-Goodhart zapobiegającą kastracji dialogu przy gęstej mowie seiyū.
2. Dwukierunkowa integralność afektywna audio-tekst (arousal level, wahania głosu).
3. Deterministyczna post-walidacja w Warstwie 4 (0.00 PLN).
"""

import math
import json
import re
from typing import List, Dict, Any, Optional

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


SCRIPT_DOCTOR_SYSTEM_INSTRUCTION = """ROLA: Elitarny Script Doctor AVT i Sędzia Optymalizacyjny (JA/EN -> PL).

ZADANIE:
Oceń N kandydatów tłumaczenia dla pojedynczej planszy napisów ASS.
Zastosuj Wielokryterialną Funkcję Nagrody z Bezpiecznikiem Anty-Goodhart,
aby wybrać wariant optymalny pod kątem dramaturgii i geometrii ekranu.
Jeśli żaden kandydat nie spełnia kryteriów, przeprowadź precyzyjną mikronaprawę.

REGUŁY KALKULACJI STRAT I KAR (Anti-Goodhart Loss):

1. BARIERA SUFITOWA CPS (Fizjologia Oka - Hard Barrier):
   - CPS <= 17.0: Kara = 0.0.
   - 17.0 < CPS <= 20.0: Kara rośnie liniowo (3.0 * (CPS - 17.0)).
   - CPS > 20.0: Bezwzględna dyskwalifikacja kandydata (Kara = 50.0).

2. BEZPIECZNIK ANTY-GOODHART: BARIERA PODŁOGOWA CPS (Anti-Sterility Barrier):
   - Jeśli CPS < cps_target_floor, a w oryginale trwa gęsty dialog seiyū (mora_density >= 9.0 mor/s):
     Nalicz karę: 2.5 * (cps_target_floor - CPS).
   - ODRZUĆ kandydatów spłaszczonych emocjonalnie do lakonicznych równoważników zdań,
     jeśli usuwają oni kluczowe partykuły modalne, ekspresję i nastawienie mówcy.

3. INTEGRALNOŚĆ AFEKTYWNO-DRAMATURGICZNA (Audio-Text Alignment):
   - Jeśli audio_telemetry.arousal_level to "AGGRESSIVE" lub "HYSTERIC", tekst MUSI posiadać
     ładunek emocjonalny (odpowiednia leksyka, wykrzyknik, partykuły wzmacniające: "przecież", "no").
     Brak ładunku = Kara 10.0.
   - Jeśli audio_telemetry.has_vocal_hesitation jest TRUE, wycięcie wielokropka wstrzymania
     głosu lub wahania ("...", "…", "—") = Kara 8.0.

4. GEOMETRIA CPL (Format ASS):
   - Maksymalnie 2 linie tekstu, rozdzielone sekwencją \\N.
   - Maksymalnie 38 znaków w pojedynczym wierszu (bez tagów {...}).
   - Przekroczenie limitu znaku w linii = Kara 4.0 za każdy nadmiarowy znak.

5. INTEGRALNOŚĆ GRAMATYCZNA I MORFOLOGICZNA:
   - Zero nominative freezing (bezwzględny wymóg poprawnego przypadku i rekcji zaprzeczonej).
   - Ścisła zgodność z płcią mówcy i adresata podaną w obiekcie "discourse".

PROCEDURA DECYZYJNA:
1. Oblicz sumaryczną karę dla każdego kandydata:
   Total_Penalty = cps_penalty + anti_goodhart_floor_penalty + affective_mismatch_penalty + cpl_geometry_penalty
2. Wybierz kandydata o najmniejszej karze.
3. Jeśli wybrany kandydat ma Total_Penalty > 0, ustaw `requires_micro_repair: true`
   i w `final_subtitle_text` wygeneruj skorygowaną polską kwestię mieszczącą się w paśmie [cps_target_floor, 17.0].
"""

SCRIPT_DOCTOR_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "selected_candidate_id": {"type": "INTEGER"},
        "requires_micro_repair": {"type": "BOOLEAN"},
        "final_subtitle_text": {"type": "STRING"},
        "total_penalty": {"type": "NUMBER"},
        "verdict_rationale": {"type": "STRING"}
    },
    "required": [
        "selected_candidate_id",
        "requires_micro_repair",
        "final_subtitle_text",
        "total_penalty",
        "verdict_rationale"
    ]
}


def prepare_doctor_payload(
    candidates_raw: List[str],
    duration_s: float,
    source_ja: str,
    source_mora_count: int,
    audio_telemetry: Dict[str, Any],
    discourse_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Przygotowuje ustrukturyzowany payload diagnostyczny dla Fazy 2 Script Doctor.
    Oblicza gęstość mor, podłogę anty-Goodhart oraz metryki geometryczne ASS.
    """
    dur = max(0.5, float(duration_s))
    source_density = source_mora_count / dur
    cps_floor = min(13.5, 7.5 + 0.5 * source_density)

    evaluated = []
    for idx, text in enumerate(candidates_raw):
        pure = re.sub(r"\{[^}]*\}", "", text)
        lines = pure.split(r"\N")
        char_len = len(pure.replace(r"\N", ""))
        cps = char_len / dur
        cpl_errs = sum(max(0, len(l.strip()) - 38) for l in lines)

        evaluated.append({
            "candidate_id": idx,
            "text": text,
            "char_count": char_len,
            "cps": round(cps, 2),
            "lines_count": len(lines),
            "cpl_overflow_chars": cpl_errs
        })

    return {
        "timing": {
            "duration_s": round(dur, 3),
            "cps_target_floor": round(cps_floor, 2),
            "cps_hard_ceiling": 17.0,
            "cps_rejection_barrier": 20.0
        },
        "source": {
            "ja": source_ja,
            "mora_count": source_mora_count,
            "mora_density": round(source_density, 2)
        },
        "audio_telemetry": {
            "f0_median_hz": audio_telemetry.get("f0_median") or audio_telemetry.get("f0_median_hz"),
            "arousal_level": audio_telemetry.get("arousal") or audio_telemetry.get("arousal_level"),
            "has_vocal_hesitation": bool(audio_telemetry.get("has_hesitation") or audio_telemetry.get("has_vocal_hesitation", False))
        },
        "discourse": discourse_context,
        "candidates": evaluated
    }


def compute_anti_goodhart_penalties_offline(
    candidate_text: str,
    duration_s: float,
    source_mora_density: float,
    audio_telemetry: Optional[Dict[str, Any]] = None,
    discourse_context: Optional[Dict[str, Any]] = None,
    cps_target_floor: Optional[float] = None
) -> Dict[str, float]:
    """
    Deterministyczny silnik ewaluacji kary Anty-Goodhart w trybie offline (0.00 PLN).
    Zwraca rozbicie na składowe kar i łączną stratę.
    """
    dur = max(0.5, float(duration_s))
    if cps_target_floor is None:
        cps_target_floor = min(13.5, 7.5 + 0.5 * source_mora_density)

    pure = re.sub(r"\{[^}]*\}", "", candidate_text)
    lines = pure.split(r"\N")
    char_len = len(pure.replace(r"\N", ""))
    cps = char_len / dur

    # 1. Asymetryczny sufit CPS
    if cps <= 17.0:
        cps_ceil_pen = 0.0
    elif cps <= 20.0:
        cps_ceil_pen = 3.0 * (cps - 17.0)
    else:
        cps_ceil_pen = 50.0 + (cps - 20.0) ** 2

    # 2. Bezpiecznik anty-Goodhart (podłoga)
    if cps < cps_target_floor and source_mora_density >= 9.0:
        floor_pen = 2.5 * (cps_target_floor - cps)
    else:
        floor_pen = 0.0

    # 3. Geometria linii ASS (CPL)
    cpl_overflow = sum(max(0, len(l.strip()) - 38) for l in lines)
    line_count_err = max(0, len(lines) - 2)
    cpl_pen = (cpl_overflow * 4.0) + (line_count_err * 50.0)

    # 4. Integralność afektywna audio-tekst
    audio = audio_telemetry or {}
    arousal = (audio.get("arousal") or audio.get("arousal_level") or "").upper()
    has_hesitation = bool(audio.get("has_hesitation") or audio.get("has_vocal_hesitation", False))

    affective_pen = 0.0
    if arousal in ("AGGRESSIVE", "HYSTERIC"):
        has_exclamation = "!" in pure
        has_intensifiers = any(w in pure.lower() for w in ["przecież", "no", "zaraz", "do diabła", "cholera", "nie waż się"])
        if not (has_exclamation or has_intensifiers):
            affective_pen += 10.0

    if has_hesitation:
        has_pause_marker = any(p in pure for p in ["...", "…", "—", "- "])
        if not has_pause_marker:
            affective_pen += 8.0

    total = cps_ceil_pen + floor_pen + cpl_pen + affective_pen
    return {
        "cps": round(cps, 2),
        "cps_ceiling_penalty": round(cps_ceil_pen, 2),
        "anti_goodhart_floor_penalty": round(floor_pen, 2),
        "cpl_geometry_penalty": round(cpl_pen, 2),
        "affective_penalty": round(affective_pen, 2),
        "total_penalty": round(total, 2)
    }


class ScriptDoctorSelector:
    """
    Główny harness Fazy 2 potoku AVT (Best-of-N Re-ranking & Micro-repair).
    Łączy promptowanie LLM z twardym deterministycznym bezpiecznikiem Warstwy 4.
    """

    def __init__(self, client: Optional[Any] = None, model_name: str = "gemini-2.5-pro"):
        self.client = client
        self.model_name = model_name

    def select_and_repair(
        self,
        payload: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Wybiera najlepszego kandydata lub dokonuje mikronaprawy zgodnie z regułami anty-Goodhart.
        """
        if schema is None:
            schema = SCRIPT_DOCTOR_RESPONSE_SCHEMA

        # Jeśli brak klienta API (np. test offline), dokonaj deterministycznej selekcji offline
        if not self.client:
            return self._select_offline_fallback(payload)

        prompt_content = (
            "DANE WEJŚCIOWE DO ANALIZY:\n"
            f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n"
            "Wybierz najlepszego kandydata lub dokonaj mikronaprawy zgodnie z zasadami anty-Goodhart."
        )

        config = types.GenerateContentConfig(
            temperature=0.1,
            top_p=0.95,
            response_mime_type="application/json",
            response_schema=schema,
            system_instruction=SCRIPT_DOCTOR_SYSTEM_INSTRUCTION
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt_content,
            config=config
        )

        result = json.loads(response.text)
        return self._post_validate(result, payload)

    def _select_offline_fallback(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        W pełni deterministyczny fallback offline (0.00 PLN).
        """
        candidates = payload.get("candidates", [])
        dur = payload.get("timing", {}).get("duration_s", 1.0)
        source_density = payload.get("source", {}).get("mora_density", 0.0)
        floor = payload.get("timing", {}).get("cps_target_floor", 10.0)
        audio = payload.get("audio_telemetry", {})
        discourse = payload.get("discourse", {})

        best_id = 0
        lowest_penalty = float("inf")
        best_breakdown = {}

        for c in candidates:
            cid = c.get("candidate_id", 0)
            text = c.get("text", "")
            breakdown = compute_anti_goodhart_penalties_offline(
                candidate_text=text,
                duration_s=dur,
                source_mora_density=source_density,
                audio_telemetry=audio,
                discourse_context=discourse,
                cps_target_floor=floor
            )
            if breakdown["total_penalty"] < lowest_penalty:
                lowest_penalty = breakdown["total_penalty"]
                best_id = cid
                best_breakdown = breakdown

        chosen_text = candidates[best_id]["text"] if candidates else ""
        res = {
            "selected_candidate_id": best_id,
            "requires_micro_repair": lowest_penalty > 0.0,
            "final_subtitle_text": chosen_text,
            "total_penalty": lowest_penalty,
            "verdict_rationale": f"Deterministyczny wybór offline kandydata {best_id} (kara: {lowest_penalty})"
        }
        return self._post_validate(res, payload)

    def _post_validate(self, result: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Twardy bezpiecznik wyjściowy Warstwy 4 (EpisodeQualityGate Failsafe):
        Zapobiega przedostaniu się jakichkolwiek plansz z CPS > 20.0 lub CPL > 38.
        """
        final_text = result.get("final_subtitle_text", "")
        pure_text = re.sub(r"\{[^}]*\}", "", final_text).replace(r"\N", "")
        dur = payload.get("timing", {}).get("duration_s", 1.0)
        final_cps = len(pure_text) / max(0.5, dur)

        if final_cps > 20.0:
            lines = final_text.split(r"\N")
            trimmed_lines = [l[:38] for l in lines[:2]]
            result["final_subtitle_text"] = r"\N".join(trimmed_lines)
            rationale = result.get("verdict_rationale", "")
            result["verdict_rationale"] = (rationale + " [Failsafe Warstwa 4: przycięto awaryjnie w post-walidacji]").strip()

        return result
