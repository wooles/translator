# -*- coding: utf-8 -*-
"""
Local Japanese Speech Recognition Engine Module (Speech-to-Text).
Uses optimized faster-whisper (CTranslate2) for direct
transcription of audio dialogue into Japanese (Kanji / Kana), enabling
translation directly from the original voice track without reliance on flawed English subs.
"""

import os
import sys
import warnings
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")
warnings.filterwarnings("ignore", category=FutureWarning)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

logger = logging.getLogger("whisper_engine")

# Ensure NVIDIA CUDA/cuBLAS/cuDNN runtime DLLs from pip wheels are visible to Windows CTranslate2
if sys.platform == "win32":
    for p in sys.path:
        if "site-packages" in p:
            nvidia_base = os.path.join(p, "nvidia")
            if os.path.exists(nvidia_base):
                for root, dirs, files in os.walk(nvidia_base):
                    if any(f.endswith(".dll") for f in files):
                        try:
                            os.add_dll_directory(root)
                            if root not in os.environ.get("PATH", ""):
                                os.environ["PATH"] = root + ";" + os.environ.get("PATH", "")
                        except Exception:
                            pass

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
        Initializes the Japanese Whisper engine.
        Default model: 'kotoba-tech/kotoba-whisper-v2.0-faster' (SOTA for Japanese speech, ReazonSpeech).
        Aliases: 'kotoba', 'turbo', 'large-v3', 'anime'
        device: 'cuda' (GPU), 'cpu' or 'auto'
        """
        clean_key = model_size.lower().strip()
        self.model_size = MODEL_ALIASES.get(clean_key, model_size)
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root or str(Path(__file__).parent / ".models")
        self.model: Optional[Any] = None
        self._is_initialized = False
        self._init_lock = threading.Lock()
        self._infer_lock = threading.Lock()

    @staticmethod
    def is_available() -> bool:
        """Checks if faster-whisper package is available in the environment."""
        return FASTER_WHISPER_AVAILABLE

    def _initialize_model(self):
        """Lazy loading of Whisper model on first invocation (Thread-Safe)."""
        if self._is_initialized:
            return

        with self._init_lock:
            if self._is_initialized:
                return

            if not FASTER_WHISPER_AVAILABLE:
                raise RuntimeError(
                    "Package 'faster-whisper' is not installed! "
                    "To enable local audio transcription, run: pip install faster-whisper"
                )

            # Device selection (GPU CUDA or CPU)
            selected_device = self.device
            selected_compute = self.compute_type

            if selected_device == "auto":
                has_cuda = False
                try:
                    import ctranslate2
                    if ctranslate2.get_cuda_device_count() > 0:
                        has_cuda = True
                except Exception:
                    pass
                if not has_cuda:
                    try:
                        import torch
                        if torch.cuda.is_available():
                            has_cuda = True
                    except Exception:
                        pass

                if has_cuda:
                    selected_device = "cuda"
                    if selected_compute == "auto":
                        selected_compute = "float16"
                else:
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
                dev_label = f"GPU (CUDA {selected_compute.upper()})" if selected_device == "cuda" else f"CPU ({selected_compute.upper()})"
                print(f"  [Lokalny Silnik Audio Kotoba-Whisper]: Załadowano model {self.model_size} na {dev_label}.")
            except Exception as e:
                # Fallback 1: Try CPU INT8 on GPU driver failure
                if selected_device != "cpu":
                    try:
                        self.model = WhisperModel(
                            self.model_size,
                            device="cpu",
                            compute_type="int8",
                            download_root=self.download_root
                        )
                        self._is_initialized = True
                        print(f"  [Lokalny Silnik Audio Kotoba-Whisper]: Załadowano model {self.model_size} na CPU (INT8 fallback).")
                        return
                    except Exception:
                        pass

                # Fallback 2: If Kotoba model cannot be loaded, fallback to large-v3-turbo
                if self.model_size != "large-v3-turbo":
                    try:
                        logger.info("[Whisper Engine]: Fallback to standard large-v3-turbo model...")
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
        Transcribes a short audio slice (16kHz WAV) to Japanese text.
        Returns clean Japanese string (Kanji/Kana).
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
                beam_size=1,
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
            logger.warning(f"Whisper transcription error for {wav_path}: {e}")
            return ""

    def transcribe_batch_scene(
        self,
        scene_wav_path: str,
        batch_start_ms: int,
        events: List[Tuple[int, Any]],
        initial_prompt: Optional[str] = None
    ) -> Dict[int, str]:
        """
        Transcribes entire batch scene audio (30-60s) in a SINGLE PASS.
        Returns dictionary {batch_id: transcribed_jp_text}.
        Runs 20x-50x faster!
        """
        if not scene_wav_path or not os.path.exists(scene_wav_path) or not FASTER_WHISPER_AVAILABLE:
            return {}

        try:
            self._initialize_model()
            transcribe_kwargs = {
                "language": "ja",
                "beam_size": 1,
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
            segments_list = list(segments)

            result: Dict[int, List[str]] = {b_id: [] for b_id, _ in events}
            
            for seg in segments_list:
                seg_text = seg.text.strip()
                if not seg_text:
                    continue
                # Segment timestamp in milliseconds in episode timeline
                seg_start_abs = batch_start_ms + int(seg.start * 1000)
                seg_end_abs = batch_start_ms + int(seg.end * 1000)

                for b_id, ev in events:
                    # Check if segment overlaps with dialogue timing
                    overlap_start = max(ev.start, seg_start_abs)
                    overlap_end = min(ev.end, seg_end_abs)
                    if (overlap_end - overlap_start) > 100 or (ev.start <= seg_start_abs and ev.end >= seg_end_abs):
                        if seg_text not in result[b_id]:
                            result[b_id].append(seg_text)

            return {b_id: "".join(texts).strip() for b_id, texts in result.items() if texts}
        except Exception as e:
            logger.warning(f"Batch Whisper transcription error: {e}")
            return {}
