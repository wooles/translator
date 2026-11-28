# -*- coding: utf-8 -*-
"""
Local Voice Pitch Classification & Speaker Diarization Module.
100% local pitch-tracking module delegating F0 estimation to filtered librosa.pyin
(Voiced-Frame Pooling + IQR/std BGM suppression) to identify speaker gender register.
"""

import logging
import os
import wave
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

logger = logging.getLogger("speaker_diarizer")


class SpeakerVoiceClassifier:
    def __init__(self):
        pass

    @staticmethod
    def estimate_pitch_f0(samples: np.ndarray, sample_rate: int = 16000) -> Optional[float]:
        """
        Estimates fundamental voice frequency (F0) using filtered librosa.pyin
        (EpistemicAudioTriangulator.estimate_f0_pyin) instead of raw autocorrelation,
        suppressing low-frequency BGM bass and chaotic noise contamination.
        """
        if samples is None or sample_rate <= 0 or len(samples) < int(sample_rate * 0.3):
            return None

        # Normalize, remove DC offset, and reject silence
        arr = np.asarray(samples, dtype=np.float32)
        centered = arr - np.mean(arr)
        if float(np.max(np.abs(centered))) < 50.0:
            return None

        max_samples = int(sample_rate * 4.0)
        if len(centered) > max_samples:
            centered = centered[:max_samples]

        try:
            import librosa  # noqa: F401
            from profiler import EpistemicAudioTriangulator
        except ImportError as exc:
            logger.warning("Brak librosa lub EpistemicAudioTriangulator (%s); zwracam None.", exc)
            return None

        return EpistemicAudioTriangulator.estimate_f0_pyin(
            centered,
            sample_rate=sample_rate,
            min_voiced_frames=25,
        )

    @classmethod
    def estimate_pitch_dynamics(cls, samples: np.ndarray, sample_rate: int = 16000) -> Optional[Dict[str, Any]]:
        """
        Estimates pitch dynamics across spoken dialogue:
        calculates F0 contour slope (falling/rising/flat) and end-of-phrase energy drop
        to distinguish cold cynicism/sarcasm from sincere engagement.
        """
        if samples is None or len(samples) < sample_rate * 0.35:
            return None

        samples = samples - np.mean(samples)
        if np.max(np.abs(samples)) < 50.0:
            return None

        min_lag = int(sample_rate / 400)
        max_lag = int(sample_rate / 75)
        window_size = int(sample_rate * 0.06)
        hop_size = int(sample_rate * 0.03)

        f0_points = []
        frame_energies = []

        for start in range(0, len(samples) - window_size, hop_size):
            frame = samples[start:start + window_size]
            energy = np.sum(frame ** 2)
            frame_energies.append(energy)
            if energy < 1e5:
                continue

            corr = np.correlate(frame, frame, mode="full")
            corr = corr[len(frame) - 1:]
            if len(corr) <= max_lag:
                continue

            search_region = corr[min_lag:max_lag]
            if len(search_region) == 0:
                continue

            peak_idx = np.argmax(search_region) + min_lag
            peak_val = corr[peak_idx]

            if corr[0] > 0 and (peak_val / corr[0]) > 0.35:
                f0 = sample_rate / peak_idx
                if 75.0 <= f0 <= 450.0:
                    f0_points.append(f0)

        if len(f0_points) < 4:
            return None

        mid = len(f0_points) // 2
        f0_start = float(np.median(f0_points[:mid]))
        f0_end = float(np.median(f0_points[mid:]))
        median_f0 = float(np.median(f0_points))

        if f0_end < f0_start * 0.88:
            slope = "falling"
        elif f0_end > f0_start * 1.12:
            slope = "rising"
        else:
            slope = "flat"

        # Energy drop towards end of phrase
        energy_drop = False
        if len(frame_energies) >= 6:
            e_start = np.mean(frame_energies[:len(frame_energies)//2])
            e_end = np.mean(frame_energies[len(frame_energies)//2:])
            if e_start > 0 and (e_end / e_start) < 0.45:
                energy_drop = True

        return {
            "median_f0": median_f0,
            "f0_start": f0_start,
            "f0_end": f0_end,
            "slope": slope,
            "energy_drop": energy_drop
        }

    @classmethod
    def classify_pitch_register(cls, f0: float) -> str:
        if f0 is None or f0 <= 0:
            return "nieokreślony"
        if f0 <= 155.0:
            return f"niski tembr (~{int(f0)}Hz: bas/baryton lub ochrypły alt starszej kobiety)"
        elif f0 <= 195.0:
            return f"średni tembr (~{int(f0)}Hz: tenor męski / alt żeński)"
        else:
            return f"wysoki tembr (~{int(f0)}Hz: sopran żeński / głos dziecięcy)"

    @classmethod
    def classify_scene_speakers(
        cls,
        wav_path: str,
        batch_start_ms: int,
        events: List[Tuple[int, Any]]
    ) -> Dict[int, str]:
        """
        Classifies voice pitch and register for all dialogue events in a batch.
        Returns a dictionary: {batch_id: 'Głos: ...'}.
        """
        if not wav_path or not os.path.exists(wav_path):
            return {}

        results = {}

        try:
            with wave.open(wav_path, "rb") as wf:
                framerate = wf.getframerate()
                nchannels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                total_frames = wf.getnframes()
                
                raw_bytes = wf.readframes(total_frames)
                if not raw_bytes:
                    return {}

                if sampwidth == 2:
                    full_audio = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
                elif sampwidth == 1:
                    full_audio = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128) * 256.0
                else:
                    return {}

                if nchannels > 1:
                    full_audio = full_audio.reshape(-1, nchannels).mean(axis=1)

            for b_id, ev in events:
                rel_start = max(0, ev.start - batch_start_ms)
                rel_end = max(rel_start + 200, ev.end - batch_start_ms)

                start_idx = int((rel_start / 1000.0) * framerate)
                end_idx = int((rel_end / 1000.0) * framerate)

                if end_idx <= start_idx or start_idx >= len(full_audio):
                    continue

                chunk = full_audio[start_idx:min(end_idx, start_idx + int(framerate * 4.0), len(full_audio))]
                f0 = cls.estimate_pitch_f0(chunk, sample_rate=framerate)

                if f0 is not None:
                    results[b_id] = cls.classify_pitch_register(f0)

        except Exception:
            pass

        return results
