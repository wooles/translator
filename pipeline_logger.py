"""
Moduł rejestratora czarnej skrzynki potoku tłumaczenia (EpisodeFlightRecorder).
Zapewnia pełny, deterministyczny, wielowątkowo bezpieczny zapis przebiegu tłumaczenia
odcinka krok po kroku w formatach: czytelnym dla człowieka (.log) oraz maszynowym (.jsonl).
Zgodny ze Standardem 9.0 (Zero-Literal Pure Positive Domain Invariant & Instance-Free Architecture).
"""

import os
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def _safe_json_default(obj: Any) -> Any:
    """Konwertuje niestandardowe typy do formatu zgodnego z JSON."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, (set, tuple)):
        return list(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    return str(obj)


SEP_80 = "=" * 80
SEP_78 = "-" * 78


class EpisodeFlightRecorder:
    """
    Czarna skrzynka wykonania potoku tłumaczenia dla pojedynczego odcinka.
    Rejestruje wszystkie kroki potoku od ingestii do końcowego audytu jakości.
    """

    def __init__(
        self,
        anime_slug: str = "anime",
        filename: str = "episode",
        trace_dir: Optional[Union[str, Path]] = "logs",
        enabled: bool = True
    ) -> None:
        self.enabled: bool = enabled
        self._lock: threading.RLock = threading.RLock()
        self._initialized: bool = False
        self._finalized: bool = False
        self._cli_init_logged: bool = False
        self.anime_slug: str = anime_slug or "anime"
        self.filename: str = filename or "episode"
        self.trace_dir: Path = Path(trace_dir or "logs")
        self.timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Sanityzacja nazw plików pod kątem znaków niedozwolonych w systemie plików
        safe_slug = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in self.anime_slug).strip("_")
        safe_name = "".join(c if (c.isalnum() or c in ("-", "_")) else "_" for c in self.filename).strip("_")
        if not safe_slug:
            safe_slug = "anime"
        if not safe_name:
            safe_name = "episode"

        self.log_filename: str = f"{safe_slug}_{safe_name}_{self.timestamp}_full_trace.log"
        self.jsonl_filename: str = f"{safe_slug}_{safe_name}_{self.timestamp}_events.jsonl"
        self.log_path: Path = self.trace_dir / self.log_filename
        self.jsonl_path: Path = self.trace_dir / self.jsonl_filename

        if self.enabled:
            try:
                self.trace_dir.mkdir(parents=True, exist_ok=True)
                self.__initialize_log_file()
            except Exception:
                pass

    def __initialize_log_file(self) -> None:
        """Inicjalizuje nagłówek w pliku czytelnym dla człowieka (dokładnie raz)."""
        with self._lock:
            if self._initialized:
                return
            header = (
                f"{SEP_80}\n"
                f"REJESTRATOR PRZEBIEGU POTOKU AVT (EPISODE FLIGHT RECORDER)\n"
                f"Seria: {self.anime_slug}\n"
                f"Plik: {self.filename}\n"
                f"Czas startu: {datetime.now().isoformat()}\n"
                f"{SEP_80}\n\n"
            )
            try:
                with open(self.log_path, "w", encoding="utf-8") as f:
                    f.write(header)
                with open(self.jsonl_path, "a", encoding="utf-8") as jf:
                    pass
                self._initialized = True
            except Exception:
                pass

    def record_event(
        self,
        stage: str,
        payload: Dict[str, Any],
        batch_id: Optional[int] = None,
        line_id: Optional[int] = None,
        message: str = ""
    ) -> None:
        """
        Zapisuje uniwersalne zdarzenie telemetryczne do pliku .jsonl oraz .log.
        """
        if not self.enabled:
            return

        event_data = {
            "timestamp_iso": datetime.now().isoformat(),
            "stage": stage,
            "batch_id": batch_id,
            "line_id": line_id,
            "payload": payload
        }

        with self._lock:
            try:
                line_str = json.dumps(event_data, default=_safe_json_default, ensure_ascii=False)
                with open(self.jsonl_path, "a", encoding="utf-8") as jf:
                    jf.write(line_str + "\n")
            except Exception:
                pass

            if message:
                try:
                    with open(self.log_path, "a", encoding="utf-8") as lf:
                        lf.write(message + "\n")
                except Exception:
                    pass

    def write_log_section(self, section_title: str, content: str) -> None:
        """Zapisuje sformatowaną sekcję do pliku tekstowego logu."""
        if not self.enabled:
            return
        section_text = (
            f"\n{SEP_78}\n"
            f"{section_title}\n"
            f"{SEP_78}\n"
            f"{content}\n"
        )
        with self._lock:
            try:
                with open(self.log_path, "a", encoding="utf-8") as lf:
                    lf.write(section_text)
            except Exception:
                pass

    def log_cli_init(
        self,
        cli_args: Dict[str, Any],
        paths: Dict[str, Any],
        models: Dict[str, Any],
        context_cache_info: Optional[Dict[str, Any]] = None,
        client_pool_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Rejestruje KROK 1: Inicjalizację procesu i parametry CLI (idempotentnie, dokładnie jeden raz)."""
        with self._lock:
            if getattr(self, "_cli_init_logged", False):
                return
            self._cli_init_logged = True
            payload = {
                "cli_args": cli_args,
                "paths": paths,
                "models": models,
                "context_cache": context_cache_info or {},
                "client_pool": client_pool_info or {}
            }
            text_lines = [
                f"Parametry CLI: {json.dumps(cli_args, default=_safe_json_default, ensure_ascii=False)}",
                f"Sciezki: {json.dumps(paths, default=_safe_json_default, ensure_ascii=False)}",
                f"Modele: {json.dumps(models, default=_safe_json_default, ensure_ascii=False)}",
                f"Pamięć podręczna kontekstu: {json.dumps(context_cache_info or {}, default=_safe_json_default, ensure_ascii=False)}",
                f"Pula klientów: {json.dumps(client_pool_info or {}, default=_safe_json_default, ensure_ascii=False)}"
            ]
        self.record_event("cli_init", payload)
        self.write_log_section("[KROK 1: CLI & INICJALIZACJA PROCESU]", "\n".join(text_lines))

    def log_ingestion(
        self,
        encoding: str,
        total_events: int,
        style_matrix: Optional[Dict[str, Any]] = None,
        events_classified: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Rejestruje KROK 2: Wczytanie napisów i klasyfikację wizualną."""
        payload = {
            "encoding": encoding,
            "total_events": total_events,
            "style_matrix": style_matrix or {},
            "sample_events": (events_classified[:20] if events_classified else [])
        }
        text_lines = [
            f"Kodowanie pliku źródłowego: {encoding}",
            f"Liczba wczytanych zdarzeń: {total_events}",
            f"Zestawienie stylów: {json.dumps(style_matrix or {}, default=_safe_json_default, ensure_ascii=False)}"
        ]
        if events_classified:
            text_lines.append(f"Próbka klasyfikacji wizualnej ({len(events_classified)} linii):")
            for ev_info in events_classified[:10]:
                text_lines.append(
                    f"  ID {ev_info.get('id')}: {ev_info.get('start')}->{ev_info.get('end')} "
                    f"[{ev_info.get('style')}] {ev_info.get('type_label', 'DIALOG')} "
                    f"Aktor: '{ev_info.get('raw_actor_name')}' | Tekst: '{ev_info.get('en_raw')}'"
                )
        self.record_event("ingestion", payload)
        self.write_log_section("[KROK 2: INGESTIA NAPISÓW I KLASYFIKACJA WIZUALNA]", "\n".join(text_lines))

    def log_metadata(
        self,
        clean_slug: str,
        anilist_meta: Optional[Dict[str, Any]] = None,
        actor_mappings: Optional[Dict[str, Any]] = None
    ) -> None:
        """Rejestruje KROK 3: Metadane zewnętrzne i normalizację etykiet aktorów."""
        payload = {
            "clean_slug": clean_slug,
            "anilist_meta": anilist_meta or {},
            "actor_mappings": actor_mappings or {}
        }
        text_lines = [
            f"Znormalizowany slug serii: {clean_slug}",
            f"Metadane zewnętrzne: {json.dumps(anilist_meta or {}, default=_safe_json_default, ensure_ascii=False)}",
            f"Normalizacja etykiet aktorów: {json.dumps(actor_mappings or {}, default=_safe_json_default, ensure_ascii=False)}"
        ]
        self.record_event("metadata", payload)
        self.write_log_section("[KROK 3: METADANE ZEWNĘTRZNE I NORMALIZACJA AKTORÓW]", "\n".join(text_lines))

    def log_acoustics_and_whisper(
        self,
        f0_metrics: Optional[Dict[str, Any]] = None,
        whisper_results: Optional[Dict[str, Any]] = None
    ) -> None:
        """Rejestruje KROK 4: Estymację akustyki F0 oraz transkrypcję japońskiego audio."""
        payload = {
            "f0_metrics": f0_metrics or {},
            "whisper_results": whisper_results or {}
        }
        text_lines = [
            f"Metryki estymacji akustyki F0: {json.dumps(f0_metrics or {}, default=_safe_json_default, ensure_ascii=False)}",
            f"Transkrypcja japońskiego audio i tagi: {json.dumps(whisper_results or {}, default=_safe_json_default, ensure_ascii=False)}"
        ]
        self.record_event("acoustics_whisper", payload)
        self.write_log_section("[KROK 4: AKUSTYKA DSP, ESTYMACJA F0 I WHISPER ASR]", "\n".join(text_lines))

    def log_profile_prepass(
        self,
        cache_status: str,
        episode_profile: Optional[Any] = None,
        profile_brief: str = ""
    ) -> None:
        """Rejestruje KROK 5: Wstępną analizę profilera odcinka."""
        payload = {
            "cache_status": cache_status,
            "profile": episode_profile,
            "profile_brief": profile_brief
        }
        text_lines = [
            f"Status pamięci podręcznej profilera: {cache_status}",
            f"Podsumowanie wygenerowanego profilu:\n{profile_brief}"
        ]
        self.record_event("profile_prepass", payload)
        self.write_log_section("[KROK 5: PROFILER ODCINKA PRE-PASS]", "\n".join(text_lines))

    def log_series_bible(
        self,
        bible_summary: Optional[Dict[str, Any]] = None,
        character_registry: Optional[Dict[str, Any]] = None,
        relations: Optional[Dict[str, Any]] = None,
        declensions: Optional[Dict[str, Any]] = None
    ) -> None:
        """Rejestruje KROK 6: Stan bazy wiedzy serii, rejestru postaci i deklinacji."""
        payload = {
            "bible_summary": bible_summary or {},
            "character_registry": character_registry or {},
            "relations": relations or {},
            "declensions": declensions or {}
        }
        text_lines = [
            f"Stan bazy wiedzy serii: {json.dumps(bible_summary or {}, default=_safe_json_default, ensure_ascii=False)}",
            f"Rejestr postaci: {json.dumps(character_registry or {}, default=_safe_json_default, ensure_ascii=False)}",
            f"Relacje skierowane: {json.dumps(relations or {}, default=_safe_json_default, ensure_ascii=False)}",
            f"Paradygmaty odmiany: {json.dumps(declensions or {}, default=_safe_json_default, ensure_ascii=False)}"
        ]
        self.record_event("series_bible", payload)
        self.write_log_section("[KROK 6: PAMIĘĆ SERII SERIESBIBLE I PARADYGMATY ODMIANY]", "\n".join(text_lines))

    def log_scene_discourse(
        self,
        scene_boundaries: Optional[List[Any]] = None,
        turns: Optional[List[Any]] = None,
        batches_summary: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Rejestruje KROK 7: Graf dyskursu scenicznego, tury i podział na paczki."""
        payload = {
            "scene_boundaries": scene_boundaries or [],
            "turns": turns or [],
            "batches_summary": batches_summary or []
        }
        text_lines = [
            f"Wykryte granice scen: {len(scene_boundaries or [])}",
            f"Liczba wyznaczonych tur i pod-tur: {len(turns or [])}",
            f"Podział na paczki adaptacyjne: {json.dumps(batches_summary or [], default=_safe_json_default, ensure_ascii=False)}"
        ]
        self.record_event("scene_discourse", payload)
        self.write_log_section("[KROK 7: GRAF DYSKURSU SCENICZNEGO I ADAPTACYJNE PACZKI]", "\n".join(text_lines))

    def log_phase1_batch(
        self,
        batch_id: int,
        prompt_dump: str,
        raw_response: Any,
        response_time_sec: float = 0.0,
        token_usage: Optional[Dict[str, Any]] = None
    ) -> None:
        """Rejestruje KROK 8: Wykonanie Fazy 1 modelu pierwotnego przekładu."""
        payload = {
            "batch_id": batch_id,
            "response_time_sec": response_time_sec,
            "token_usage": token_usage or {},
            "raw_response": raw_response
        }
        text_lines = [
            f"Paczka ID: {batch_id}",
            f"Czas odpowiedzi modelu: {response_time_sec:.2f} s",
            f"Zużycie tokenów: {json.dumps(token_usage or {}, default=_safe_json_default, ensure_ascii=False)}",
            f"Wyrenderowany prompt Fazy 1 (fragment):\n{prompt_dump[:800]}...",
            f"Surowa odpowiedź modelu Fazy 1:\n{json.dumps(raw_response, default=_safe_json_default, ensure_ascii=False)[:1000]}..."
        ]
        self.record_event("phase1_batch", payload, batch_id=batch_id)
        self.write_log_section(f"[KROK 8: FAZA 1 - PIERWOTNE TŁUMACZENIE PRIMARY LLM (PACZKA {batch_id})]", "\n".join(text_lines))

    def log_phase2_verifier(
        self,
        batch_id: int,
        cot_budget: int,
        prompt_dump: str,
        raw_response: Any
    ) -> None:
        """Rejestruje KROK 9: Wykonanie Fazy 2 weryfikatora dialogów."""
        payload = {
            "batch_id": batch_id,
            "cot_budget": cot_budget,
            "raw_response": raw_response
        }
        text_lines = [
            f"Paczka ID: {batch_id}",
            f"Budżet myślenia CoT: {cot_budget}",
            f"Wyrenderowany prompt Fazy 2 (fragment):\n{prompt_dump[:800]}...",
            f"Surowa odpowiedź weryfikatora:\n{json.dumps(raw_response, default=_safe_json_default, ensure_ascii=False)[:1000]}..."
        ]
        self.record_event("phase2_verifier", payload, batch_id=batch_id)
        self.write_log_section(f"[KROK 9: FAZA 2 - WERYFIKACJA DIALOGUEVERIFIER (PACZKA {batch_id})]", "\n".join(text_lines))

    def log_line_evolution(
        self,
        line_id: int,
        start_ms: int,
        end_ms: int,
        actor: str,
        en_text: str,
        jp_audio: str,
        whisper_tags: str,
        telemetry_tag: str,
        phase1_pl: str,
        phase2_pl: str,
        linter_pl: str,
        fixes_applied: Optional[List[str]] = None
    ) -> None:
        """Rejestruje KROK 10: Pełną ścieżkę ewolucji pojedynczej linii dialogowej."""
        payload = {
            "line_id": line_id,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "actor": actor,
            "en_text": en_text,
            "jp_audio": jp_audio,
            "whisper_tags": whisper_tags,
            "telemetry_tag": telemetry_tag,
            "phase1_pl": phase1_pl,
            "phase2_pl": phase2_pl,
            "linter_pl": linter_pl,
            "fixes_applied": fixes_applied or []
        }
        fixes_str = ", ".join(fixes_applied) if fixes_applied else "BRAK POPRAWEK - IDENTITY PASS-THROUGH"
        line_report = (
            f"[ID: {line_id} | Czas: {start_ms}->{end_ms} | Aktor: {actor or 'Brak'}]\n"
            f"EN:                 \"{en_text}\"\n"
            f"JP Audio (Whisper): \"{jp_audio}\" [Tagi: {whisper_tags}]\n"
            f"Telemetria:         {telemetry_tag}\n"
            f"Faza 1 (Draft PL):  \"{phase1_pl}\"\n"
            f"Faza 2 (Verifier):  \"{phase2_pl}\"\n"
            f"AVTLinter (D_pos):  \"{linter_pl}\"\n"
            f"Lista poprawek D_pos: [{fixes_str}]"
        )
        self.record_event("line_evolution", payload, line_id=line_id, message=line_report)

    def log_quality_gate_and_pricing(
        self,
        quality_gate_fixes: Optional[List[str]] = None,
        avt_metrics: Optional[Dict[str, Any]] = None,
        pricing_summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """Rejestruje KROK 11: Końcowy audyt jakości odcinka oraz podsumowanie kosztów (Standard 9.4, 2C.8, R3.5)."""
        all_fixes = quality_gate_fixes or []
        reported_count = len(all_fixes)
        collected_count = len(all_fixes)
        try:
            from avt_linter import EpisodeQualityGate
            eqg_fixes = EpisodeQualityGate.get_all_fixes()
            if eqg_fixes:
                collected_count = len(eqg_fixes)
        except Exception:
            pass

        consistency_status = "OK" if reported_count == collected_count else "MISMATCH"
        consistency_check = {
            "reported": reported_count,
            "collected": collected_count,
            "status": consistency_status
        }
        payload = {
            "quality_gate_fixes": all_fixes,
            "consistency_check": consistency_check,
            "avt_metrics": avt_metrics or {},
            "pricing_summary": pricing_summary or {}
        }
        # Pełne wylistowanie poprawek (zniesienie limitu [:15], Operacja 2C.8)
        fixes_summary = "\n".join(f"  ├─ {f}" for f in all_fixes)
        if not fixes_summary:
            fixes_summary = "  └─ Brak poprawek (pełna zgodność z bramką jakości)"
        text_lines = [
            f"Łączna liczba poprawek bramki jakości: {len(all_fixes)}",
            f"Lista wszystkich poprawek (spójność: {consistency_status}):\n{fixes_summary}",
            f"Metryki AVT (CPL/CPS): {json.dumps(avt_metrics or {}, default=_safe_json_default, ensure_ascii=False)}",
            f"Podsumowanie finansowe PricingGuard:\n{json.dumps(pricing_summary or {}, default=_safe_json_default, ensure_ascii=False, indent=2)}"
        ]
        self.record_event("quality_gate_pricing", payload)
        self.write_log_section("[KROK 11: EPISODEQUALITYGATE I ROZLICZENIE FINANSOWE PRICINGGUARD]", "\n".join(text_lines))

    # Alias dla zgodności z nazewnictwem Kroku 11 w Standardzie 9.4 (Operacja 2C.8)
    report_step_11_quality_gate = log_quality_gate_and_pricing

    def finalize(self) -> None:
        """Zamyka sesję rejestratora i zapisuje podsumowanie końcowe (dokładnie raz)."""
        if not self.enabled:
            return
        with self._lock:
            if self._finalized:
                return
            footer = (
                f"\n{SEP_80}\n"
                f"ZAKOŃCZENIE PRZEBIEGU POTOKU AVT: {datetime.now().isoformat()}\n"
                f"Plik logu pełnego: {self.log_path}\n"
                f"Plik zdarzeń JSONL: {self.jsonl_path}\n"
                f"{SEP_80}\n"
            )
            try:
                with open(self.log_path, "a", encoding="utf-8") as lf:
                    lf.write(footer)
                self._finalized = True
            except Exception:
                pass
