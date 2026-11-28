"""
Moduł rejestratora czarnej skrzynki potoku tłumaczenia (EpisodeFlightRecorder).
Zapewnia pełny, deterministyczny, wielowątkowo bezpieczny zapis przebiegu tłumaczenia
odcinka krok po kroku w formatach: czytelnym dla człowieka (.log) oraz maszynowym (.jsonl).
Zgodny ze Standardem 9.0 (Zero-Literal Pure Positive Domain Invariant & Instance-Free Architecture).
"""

import os
import json
import logging
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
        self._io_error_count: int = 0
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
            except Exception as exc:
                self._handle_io_error("init", exc)

    def _handle_io_error(self, context: str, exc: Exception) -> None:
        """Rejestruje błędy I/O rejestratora w sposób bezpieczny dla potoku (ostrzeżenie przy pierwszym błędzie)."""
        with self._lock:
            self._io_error_count += 1
            count = self._io_error_count
        if count == 1:
            logging.getLogger("pipeline_logger").warning(
                "EpisodeFlightRecorder I/O error during %s (suppressed further warnings): %s",
                context,
                exc,
            )

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
            except Exception as exc:
                self._handle_io_error("initialize_log_file", exc)

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
            except Exception as exc:
                self._handle_io_error("record_event_jsonl", exc)

            if message:
                try:
                    with open(self.log_path, "a", encoding="utf-8") as lf:
                        lf.write(message + "\n")
                except Exception as exc:
                    self._handle_io_error("record_event_log", exc)

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
            except Exception as exc:
                self._handle_io_error("write_log_section", exc)

    def log_cli_init(
        self,
        cli_args: Dict[str, Any],
        paths: Dict[str, Any],
        models: Dict[str, Any],
        context_cache_info: Optional[Dict[str, Any]] = None,
        client_pool_info: Optional[Dict[str, Any]] = None,
        runtime_meta: Optional[Dict[str, Any]] = None
    ) -> None:
        """Rejestruje KROK 1: Inicjalizację procesu i parametry CLI (idempotentnie, dokładnie jeden raz)."""
        with self._lock:
            if getattr(self, "_cli_init_logged", False):
                return
            self._cli_init_logged = True
            payload: Dict[str, Any] = {
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
            if runtime_meta is not None:
                payload["runtime_meta"] = runtime_meta
                text_lines.append(
                    f"Metadane runtime: {json.dumps(runtime_meta, default=_safe_json_default, ensure_ascii=False)}"
                )
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
        whisper_results: Optional[Dict[str, Any]] = None,
        batch_id: Optional[int] = None
    ) -> None:
        """Rejestruje KROK 4: Estymację akustyki F0 oraz transkrypcję japońskiego audio."""
        payload: Dict[str, Any] = {
            "f0_metrics": f0_metrics or {},
            "whisper_results": whisper_results or {}
        }
        if batch_id is not None:
            payload["batch_id"] = batch_id
        text_lines = [
            f"Metryki estymacji akustyki F0: {json.dumps(f0_metrics or {}, default=_safe_json_default, ensure_ascii=False)}",
            f"Transkrypcja japońskiego audio i tagi: {json.dumps(whisper_results or {}, default=_safe_json_default, ensure_ascii=False)}"
        ]
        self.record_event("acoustics_whisper", payload, batch_id=batch_id)
        batch_suffix = f" (PACZKA {batch_id})" if batch_id is not None else ""
        self.write_log_section(
            f"[KROK 4: AKUSTYKA DSP, ESTYMACJA F0 I WHISPER ASR{batch_suffix}]",
            "\n".join(text_lines)
        )

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
        declensions: Optional[Dict[str, Any]] = None,
        locked_glossary: Optional[Dict[str, str]] = None,
        ram_sanitization_notes: Optional[List[str]] = None
    ) -> None:
        """Rejestruje KROK 6: Stan bazy wiedzy serii, rejestru postaci i deklinacji."""
        payload: Dict[str, Any] = {
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
        if locked_glossary is not None:
            payload["locked_glossary"] = locked_glossary
            text_lines.append(
                f"Zablokowany glosariusz ({len(locked_glossary)}): {json.dumps(locked_glossary, default=_safe_json_default, ensure_ascii=False)}"
            )
        if ram_sanitization_notes is not None:
            payload["ram_sanitization_notes"] = ram_sanitization_notes
            text_lines.append(
                f"Adnotacje sanitacji RAM: {json.dumps(ram_sanitization_notes, default=_safe_json_default, ensure_ascii=False)}"
            )
        self.record_event("series_bible", payload)
        self.write_log_section("[KROK 6: PAMIĘĆ SERII SERIESBIBLE I PARADYGMATY ODMIANY]", "\n".join(text_lines))

    def log_scene_discourse(
        self,
        scene_boundaries: Optional[List[Any]] = None,
        turns: Optional[List[Any]] = None,
        batches_summary: Optional[List[Dict[str, Any]]] = None,
        episode_scene_genders_summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """Rejestruje KROK 7: Graf dyskursu scenicznego, tury i podział na paczki."""
        payload: Dict[str, Any] = {
            "scene_boundaries": scene_boundaries or [],
            "turns": turns or [],
            "batches_summary": batches_summary or []
        }
        text_lines = [
            f"Wykryte granice scen: {len(scene_boundaries or [])}",
            f"Liczba wyznaczonych tur i pod-tur: {len(turns or [])}",
            f"Podział na paczki adaptacyjne: {json.dumps(batches_summary or [], default=_safe_json_default, ensure_ascii=False)}"
        ]
        if episode_scene_genders_summary is not None:
            payload["episode_scene_genders_summary"] = episode_scene_genders_summary
            text_lines.append(
                f"Podsumowanie płci scenicznych odcinka: {json.dumps(episode_scene_genders_summary, default=_safe_json_default, ensure_ascii=False)}"
            )
        self.record_event("scene_discourse", payload)
        self.write_log_section("[KROK 7: GRAF DYSKURSU SCENICZNEGO I ADAPTACYJNE PACZKI]", "\n".join(text_lines))

    def log_retry(
        self,
        batch_id: Optional[int],
        phase: str,
        error_type: str,
        attempt_number: int,
        wait_ms: int,
        model: str = "",
        error_detail: str = ""
    ) -> None:
        """
        Standard 11.2.26 (OBS-04): Rejestruje zdarzenie ponowienia zapytania API
        (503 / 429 / 504 / TimeoutError) w events.jsonl oraz full_trace.log.
        """
        ts_now = datetime.now().isoformat()
        payload = {
            "batch_id": batch_id,
            "phase": str(phase or "F1"),
            "error_type": str(error_type or "unknown"),
            "attempt_number": int(attempt_number),
            "wait_ms": int(max(0, wait_ms)),
            "timestamp": ts_now,
            "model": str(model or ""),
            "error_detail": str(error_detail or "")[:300]
        }
        msg = (
            f"[RETRY | {payload['phase']} | Paczka {batch_id} | Próba #{payload['attempt_number']}] "
            f"Typ: {payload['error_type']} | Oczekiwanie: {payload['wait_ms']} ms | Model: {payload['model']}"
        )
        self.record_event("retry", payload, batch_id=batch_id, message=msg)

    def log_budget_audit(
        self,
        event_kind: str,
        phase: str = "",
        batch_id: Optional[int] = None,
        session_net_pln: Optional[float] = None,
        ceiling_pln: Optional[float] = None,
        cached_tokens: int = 0,
        detail: str = ""
    ) -> None:
        """Rejestruje zdarzenie audytu pamięci podręcznej kontekstu, budżetu sesji lub wznowienia checkpointu."""
        payload: Dict[str, Any] = {
            "event_kind": event_kind,
            "phase": phase,
            "batch_id": batch_id,
            "session_net_pln": session_net_pln,
            "ceiling_pln": ceiling_pln,
            "cached_tokens": int(cached_tokens or 0),
            "detail": detail,
        }
        net_str = f"{session_net_pln:.4f}" if isinstance(session_net_pln, (int, float)) else "-"
        ceil_str = f"{ceiling_pln:.2f}" if isinstance(ceiling_pln, (int, float)) else "-"
        msg = (
            f"[BUDGET_AUDIT:{event_kind}] faza={phase or '-'} paczka={batch_id if batch_id is not None else '-'} "
            f"koszt={net_str}/{ceil_str} PLN cached={int(cached_tokens or 0)}"
            + (f" | {detail}" if detail else "")
        )
        self.record_event("budget_audit", payload, batch_id=batch_id, message=msg)

    def log_phase1_batch(
        self,
        batch_id: int,
        prompt_dump: str,
        raw_response: Any,
        response_time_sec: float = 0.0,
        token_usage: Optional[Dict[str, Any]] = None,
        focused_rules: Optional[str] = None,
        locked_glossary_count: Optional[int] = None,
        rendered_characters: Optional[List[str]] = None,
        line_ids: Optional[List[int]] = None
    ) -> None:
        """Rejestruje KROK 8: Wykonanie Fazy 1 modelu pierwotnego przekładu."""
        payload: Dict[str, Any] = {
            "batch_id": batch_id,
            "response_time_sec": response_time_sec,
            "token_usage": token_usage or {},
            "raw_response": raw_response
        }
        text_lines = [
            f"Paczka ID: {batch_id}",
            f"Czas odpowiedzi modelu: {response_time_sec:.2f} s",
            f"Zużycie tokenów: {json.dumps(token_usage or {}, default=_safe_json_default, ensure_ascii=False)}",
        ]
        if line_ids is not None:
            payload["line_ids"] = line_ids
            text_lines.append(f"Mapa ID linii (orig_idx): {line_ids}")
        if locked_glossary_count is not None:
            payload["locked_glossary_count"] = locked_glossary_count
            text_lines.append(f"Liczba reguł locked_glossary: {locked_glossary_count}")
        if rendered_characters is not None:
            payload["rendered_characters"] = rendered_characters
            text_lines.append(f"Wyrenderowane postacie ({len(rendered_characters)}): {rendered_characters}")
        if focused_rules is not None:
            payload["focused_rules"] = focused_rules
            text_lines.append(f"Aktywne reguły focused_rules:\n{focused_rules[:600]}")
        text_lines.extend([
            f"Wyrenderowany prompt Fazy 1 (fragment):\n{prompt_dump[:800]}...",
            f"Surowa odpowiedź modelu Fazy 1:\n{json.dumps(raw_response, default=_safe_json_default, ensure_ascii=False)[:1000]}..."
        ])
        self.record_event("phase1_batch", payload, batch_id=batch_id)
        self.write_log_section(f"[KROK 8: FAZA 1 - PIERWOTNE TŁUMACZENIE PRIMARY LLM (PACZKA {batch_id})]", "\n".join(text_lines))

    def log_phase2_verifier(
        self,
        batch_id: int,
        cot_budget: int,
        prompt_dump: str,
        raw_response: Any,
        response_time_sec: float = 0.0,
        token_usage: Optional[Dict[str, Any]] = None,
        focused_rules: Optional[str] = None,
        locked_glossary_count: Optional[int] = None,
        rendered_characters: Optional[List[str]] = None,
        line_ids: Optional[Dict[str, int]] = None,
        f2_selection_summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """Rejestruje KROK 9: Wykonanie Fazy 2 weryfikatora dialogów."""
        payload: Dict[str, Any] = {
            "batch_id": batch_id,
            "cot_budget": cot_budget,
            "raw_response": raw_response,
            "response_time_sec": response_time_sec,
            "token_usage": token_usage or {}
        }
        text_lines = [
            f"Paczka ID: {batch_id}",
            f"Budżet myślenia CoT: {cot_budget}",
            f"Czas odpowiedzi Fazy 2: {response_time_sec:.2f}s",
            f"Zużycie tokenów Fazy 2: {json.dumps(token_usage or {}, default=_safe_json_default, ensure_ascii=False)}",
        ]
        if f2_selection_summary is not None:
            payload["f2_selection_summary"] = f2_selection_summary
            text_lines.append(
                f"Selektor F2: {json.dumps(f2_selection_summary, default=_safe_json_default, ensure_ascii=False)}"
            )
        if line_ids is not None:
            payload["line_ids"] = line_ids
            text_lines.append(
                f"Mapa linii Fazy 2 (local->orig): {json.dumps(line_ids, default=_safe_json_default, ensure_ascii=False)}"
            )
        if locked_glossary_count is not None:
            payload["locked_glossary_count"] = locked_glossary_count
            text_lines.append(f"Liczba reguł locked_glossary: {locked_glossary_count}")
        if rendered_characters is not None:
            payload["rendered_characters"] = rendered_characters
            text_lines.append(f"Wyrenderowane postacie ({len(rendered_characters)}): {rendered_characters}")
        if focused_rules is not None:
            payload["focused_rules"] = focused_rules
            text_lines.append(f"Aktywne reguły focused_rules:\n{focused_rules[:600]}")
        text_lines.extend([
            f"Wyrenderowany prompt Fazy 2 (fragment):\n{prompt_dump[:800]}...",
            f"Surowa odpowiedź weryfikatora:\n{json.dumps(raw_response, default=_safe_json_default, ensure_ascii=False)[:1000]}..."
        ])
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
        fixes_applied: Optional[List[str]] = None,
        batch_id: Optional[int] = None,
        local_id: Optional[int] = None,
        style: Optional[str] = None,
        is_sign: Optional[bool] = None,
        is_song: Optional[bool] = None,
        is_internal_monologue: Optional[bool] = None,
        notes_meta: Optional[Dict[str, Any]] = None,
        f2_score: Optional[int] = None,
        f2_score_reasons: Optional[List[str]] = None,
        f2_selected: Optional[bool] = None,
        f2_not_selected_reason: Optional[str] = None,
        f2_batch_p90: Optional[int] = None,
        f2_batch_cap: Optional[int] = None,
        f2_raw_pl: Optional[str] = None,
        f2_changes_made: Optional[str] = None,
        post_f2_fixes: Optional[List[str]] = None,
        raw_actor: Optional[str] = None,
        speaker_gender_source: Optional[str] = None
    ) -> None:
        """Rejestruje KROK 10: Pełną ścieżkę ewolucji pojedynczej linii dialogowej."""
        payload: Dict[str, Any] = {
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
        optional_fields: Dict[str, Any] = {
            "batch_id": batch_id,
            "local_id": local_id,
            "style": style,
            "is_sign": is_sign,
            "is_song": is_song,
            "is_internal_monologue": is_internal_monologue,
            "notes_meta": notes_meta,
            "f2_score": f2_score,
            "f2_score_reasons": f2_score_reasons,
            "f2_selected": f2_selected,
            "f2_not_selected_reason": f2_not_selected_reason,
            "f2_batch_p90": f2_batch_p90,
            "f2_batch_cap": f2_batch_cap,
            "f2_raw_pl": f2_raw_pl,
            "f2_changes_made": f2_changes_made,
            "post_f2_fixes": post_f2_fixes,
            "raw_actor": raw_actor,
            "speaker_gender_source": speaker_gender_source,
        }
        for key, val in optional_fields.items():
            if val is not None or (key == "f2_not_selected_reason" and f2_selected is not None):
                payload[key] = val
        fixes_str = ", ".join(fixes_applied) if fixes_applied else "BRAK POPRAWEK - IDENTITY PASS-THROUGH"
        actor_hdr = actor or "Brak"
        if raw_actor is not None or speaker_gender_source is not None:
            raw_disp = raw_actor if raw_actor not in (None, "") else "''"
            src_disp = speaker_gender_source or "none"
            actor_hdr = f"{actor_hdr} (raw: {raw_disp} | źródło płci: {src_disp})"
        report_lines = [
            f"[ID: {line_id} | Czas: {start_ms}->{end_ms} | Aktor: {actor_hdr}]",
            f"EN:                 \"{en_text}\"",
            f"JP Audio (Whisper): \"{jp_audio}\" [Tagi: {whisper_tags}]",
            f"Telemetria:         {telemetry_tag}",
            f"Faza 1 (Draft PL):  \"{phase1_pl}\"",
            f"Faza 2 (Verifier):  \"{phase2_pl}\"",
        ]
        if f2_raw_pl is not None and f2_raw_pl != phase2_pl:
            report_lines.append(f"Faza 2 (Surowe PL): \"{f2_raw_pl}\"")
        if post_f2_fixes:
            report_lines.append(f"Etapy post-F2:      [{', '.join(post_f2_fixes)}]")
        if f2_score is not None:
            report_lines.append(
                f"Selektor F2:        score={f2_score} selected={f2_selected} "
                f"p90={f2_batch_p90} cap={f2_batch_cap} reason={f2_not_selected_reason or '-'}"
            )
        report_lines.extend([
            f"AVTLinter (D_pos):  \"{linter_pl}\"",
            f"Lista poprawek D_pos: [{fixes_str}]"
        ])
        line_report = "\n".join(report_lines)
        self.record_event("line_evolution", payload, batch_id=batch_id, line_id=line_id, message=line_report)

    def log_quality_gate_and_pricing(
        self,
        quality_gate_fixes: Optional[List[str]] = None,
        avt_metrics: Optional[Dict[str, Any]] = None,
        pricing_summary: Optional[Dict[str, Any]] = None,
        eqg_diffs: Optional[List[Dict[str, Any]]] = None,
        sign_detector_events: Optional[List[Dict[str, Any]]] = None
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
        payload: Dict[str, Any] = {
            "quality_gate_fixes": all_fixes,
            "consistency_check": consistency_check,
            "avt_metrics": avt_metrics or {},
            "pricing_summary": pricing_summary or {}
        }
        if eqg_diffs is not None:
            payload["eqg_diffs"] = eqg_diffs
        if sign_detector_events is not None:
            payload["sign_detector_events"] = sign_detector_events
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
        if eqg_diffs is not None:
            text_lines.append(
                f"Zmiany EpisodeQualityGate (przed/po: {len(eqg_diffs)}): "
                f"{json.dumps(eqg_diffs, default=_safe_json_default, ensure_ascii=False)}"
            )
        if sign_detector_events is not None:
            text_lines.append(
                f"Zdarzenia VisualSignDetector ({len(sign_detector_events)}): "
                f"{json.dumps(sign_detector_events, default=_safe_json_default, ensure_ascii=False)}"
            )
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
            except Exception as exc:
                self._handle_io_error("finalize", exc)
