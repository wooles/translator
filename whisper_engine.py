# -*- coding: utf-8 -*-
"""
Moduł Lokalnego Silnika Transkrypcji Mowy Japońskiej (Speech-to-Text).
Wykorzystuje zoptymalizowaną bibliotekę faster-whisper (CTranslate2) do bezpośredniej
transkrypcji kwestii audio na język japoński (Kanji / Kana), co pozwala modelowi
tłumaczyć bezpośrednio ze źródła z pominięciem błędów w napisach angielskich.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

logger = logging.getLogger("whisper_engine")

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False


DEFAULT_JAPANESE_WHISPER_MODEL = "kotoba-tech/kotoba-whisper-v2.0-faster"

MODEL_ALIASES = {
    "kotoba": "kotoba-tech/kotoba-whisper-v2.0-faster",
    "kotoba-v2": "kotoba-tech/kotoba-whisper-v2.0-faster",
    "kotoba-whisper": "kotoba-tech/kotoba-whisper-v2.0-faster",
    "turbo": "large-v3-turbo",
    "large-turbo": "large-v3-turbo",
    "large-v3-turbo": "large-v3-turbo",
    "large-v3": "large-v3",
    "anime": "quantumcookie/anime-whisper-ct2",
}


class JapaneseWhisperEngine:
    def __init__(
        self,
        model_size: str = DEFAULT_JAPANESE_WHISPER_MODEL,
        device: str = "auto",
        compute_type: str = "auto",
        download_root: Optional[str] = None
    ):
        """
        Inicjalizacja silnika japońskiego Whisper.
        Domyślny model: 'kotoba-tech/kotoba-whisper-v2.0-faster' (SOTA dla mowy japońskiej, ReazonSpeech).
        Aliasy: 'kotoba', 'turbo', 'large-v3', 'anime'
        device: 'cuda' (GPU), 'cpu' lub 'auto'
        """
        clean_key = model_size.lower().strip()
        self.model_size = MODEL_ALIASES.get(clean_key, model_size)
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root or str(Path(__file__).parent / ".models")
        self.model: Optional[Any] = None
        self._is_initialized = False

    @staticmethod
    def is_available() -> bool:
        """Sprawdza czy biblioteka faster-whisper jest zainstalowana w środowisku."""
        return FASTER_WHISPER_AVAILABLE

    def _initialize_model(self):
        """Leniwa inicjalizacja (Lazy Loading) modelu Whisper przy pierwszym użyciu."""
        if self._is_initialized:
            return
        
        if not FASTER_WHISPER_AVAILABLE:
            raise RuntimeError(
                "Biblioteka 'faster-whisper' nie jest zainstalowana! "
                "Aby włączyć lokalną transkrypcję audio, uruchom: pip install faster-whisper"
            )

        # Dobór urządzenia (GPU CUDA lub CPU)
        selected_device = self.device
        selected_compute = self.compute_type

        if selected_device == "auto":
            try:
                import torch
                if torch.cuda.is_available():
                    selected_device = "cuda"
                    if selected_compute == "auto":
                        selected_compute = "float16"
                else:
                    selected_device = "cpu"
                    if selected_compute == "auto":
                        selected_compute = "int8"
            except ImportError:
                selected_device = "cpu"
                if selected_compute == "auto":
                    selected_compute = "int8"

        if selected_compute == "auto":
            selected_compute = "int8" if selected_device == "cpu" else "float16"

        try:
            os.makedirs(self.download_root, exist_ok=True)
            self.model = WhisperModel(
                self.model_size,
                device=selected_device,
                compute_type=selected_compute,
                download_root=self.download_root
            )
            self._is_initialized = True
        except Exception as e:
            # Fallback 1: Próba na CPU INT8 w razie problemów ze sterownikami GPU
            if selected_device != "cpu":
                try:
                    self.model = WhisperModel(
                        self.model_size,
                        device="cpu",
                        compute_type="int8",
                        download_root=self.download_root
                    )
                    self._is_initialized = True
                    return
                except Exception:
                    pass

            # Fallback 2: Jeśli model japoński Kotoba nie mógł być pobrany, fallback do large-v3-turbo
            if self.model_size != "large-v3-turbo":
                try:
                    logger.info("[Whisper Engine]: Fallback na standardowy model large-v3-turbo...")
                    self.model = WhisperModel(
                        "large-v3-turbo",
                        device=selected_device if selected_device == "cpu" else "cuda",
                        compute_type=selected_compute,
                        download_root=self.download_root
                    )
                    self.model_size = "large-v3-turbo"
                    self._is_initialized = True
                    return
                except Exception:
                    pass

            raise e

    def transcribe_audio_slice(self, wav_path: str) -> str:
        """
        Transkrybuje krótki wycinek audio (16kHz WAV) na tekst japoński.
        Zwraca czysty japoński string (Kanji/Kana).
        """
        if not wav_path or not os.path.exists(wav_path):
            return ""

        if not FASTER_WHISPER_AVAILABLE:
            return ""

        try:
            self._initialize_model()
            segments, info = self.model.transcribe(
                wav_path,
                language="ja",
                beam_size=3,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=200)
            )
            
            transcribed_parts = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    transcribed_parts.append(text)
            
            return "".join(transcribed_parts).strip()
        except Exception as e:
            logger.warning(f"Błąd transkrypcji Whisper dla {wav_path}: {e}")
            return ""

    def transcribe_batch_scene(
        self,
        scene_wav_path: str,
        batch_start_ms: int,
        events: List[Tuple[int, Any]],
        initial_prompt: Optional[str] = None
    ) -> Dict[int, str]:
        """
        Transkrybuje całe audio paczki (np. 30-60 sek) W JEDNYM PRZEBIEGU (zamiast 14 osobnych wywołań).
        Zwraca słownik {batch_id: transcribed_jp_text}.
        Działa 20x-50x szybciej!
        """
        if not scene_wav_path or not os.path.exists(scene_wav_path) or not FASTER_WHISPER_AVAILABLE:
            return {}

        try:
            self._initialize_model()
            transcribe_kwargs = {
                "language": "ja",
                "beam_size": 3,
                "vad_filter": True,
                "vad_parameters": dict(min_silence_duration_ms=200),
                "condition_on_previous_text": False,
                "repetition_penalty": 1.2,
                "no_repeat_ngram_size": 3,
                "compression_ratio_threshold": 2.4
            }
            if initial_prompt:
                transcribe_kwargs["initial_prompt"] = initial_prompt

            segments, info = self.model.transcribe(
                scene_wav_path,
                **transcribe_kwargs
            )

            result: Dict[int, List[str]] = {b_id: [] for b_id, _ in events}
            
            for seg in segments:
                seg_text = seg.text.strip()
                if not seg_text:
                    continue
                # Czas segmentu w milisekundach w skali całego filmu
                seg_start_abs = batch_start_ms + int(seg.start * 1000)
                seg_end_abs = batch_start_ms + int(seg.end * 1000)

                for b_id, ev in events:
                    # Sprawdzamy czy segment nakłada się na czas kwestii
                    overlap_start = max(ev.start, seg_start_abs)
                    overlap_end = min(ev.end, seg_end_abs)
                    if (overlap_end - overlap_start) > 100 or (ev.start <= seg_start_abs and ev.end >= seg_end_abs):
                        if seg_text not in result[b_id]:
                            result[b_id].append(seg_text)

            return {b_id: "".join(texts).strip() for b_id, texts in result.items() if texts}
        except Exception as e:
            logger.warning(f"Błąd transkrypcji paczki Whisper: {e}")
            return {}
