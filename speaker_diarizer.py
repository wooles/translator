# -*- coding: utf-8 -*-
"""
Moduł Lokalnej Klasyfikacji Barwy Głosu i Diarizacji Mówców (Voice Pitch & Speaker Diarization).
W 100% lokalny, bazujący na autokorelacji fali dźwiękowej (F0 Fundamental Frequency)
w celu bezbłędnego określenia płci mówcy (głos męski niski vs żeński wysoki) w scenach zza kadru.
"""

import os
import wave
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

class SpeakerVoiceClassifier:
    def __init__(self):
        pass

    @staticmethod
    def estimate_pitch_f0(samples: np.ndarray, sample_rate: int = 16000) -> Optional[float]:
        """
        Szacuje średnią częstotliwość podstawową głosu (F0) metodą autokorelacji fonicznej.
        Zakres ludzkiego głosu: 75 Hz (niski męski) do 450 Hz (wysoki żeński/dziecięcy).
        """
        if samples is None or len(samples) < sample_rate * 0.3:
            return None

        # Normalizacja i usunięcie składowej stałej (DC offset)
        samples = samples - np.mean(samples)
        if np.max(np.abs(samples)) < 50.0:
            return None

        # Zakres poszukiwania okresu tonu podstawowego przy 16kHz
        # Min F0 = 75 Hz -> Max Lag = 16000 / 75 = 213 próbek
        # Max F0 = 400 Hz -> Min Lag = 16000 / 400 = 40 próbek
        min_lag = int(sample_rate / 400)  # ~40
        max_lag = int(sample_rate / 75)   # ~213

        # Analiza w oknach 60ms z 50% nakładaniem
        window_size = int(sample_rate * 0.06)  # 960 próbek
        hop_size = int(sample_rate * 0.03)     # 480 próbek

        f0_estimates = []

        for start in range(0, len(samples) - window_size, hop_size):
            frame = samples[start:start + window_size]
            energy = np.sum(frame ** 2)
            if energy < 1e5:  # Pomiń ciszę
                continue

            # Autokorelacja okna
            corr = np.correlate(frame, frame, mode="full")
            corr = corr[len(frame) - 1:]

            if len(corr) <= max_lag:
                continue

            # Szukanie szczytu w zakresie lagów mowy
            search_region = corr[min_lag:max_lag]
            if len(search_region) == 0:
                continue

            peak_idx = np.argmax(search_region) + min_lag
            peak_val = corr[peak_idx]

            # Próg pewności periodyczności (unvoiced vs voiced)
            if corr[0] > 0 and (peak_val / corr[0]) > 0.35:
                f0 = sample_rate / peak_idx
                if 75.0 <= f0 <= 450.0:
                    f0_estimates.append(f0)

        if not f0_estimates or len(f0_estimates) < 3:
            return None

        # Mediana z wykrytych tonów
        return float(np.median(f0_estimates))

    @classmethod
    def classify_scene_speakers(
        cls,
        wav_path: str,
        batch_start_ms: int,
        events: List[Tuple[int, Any]]
    ) -> Dict[int, str]:
        """
        Klasyfikuje płeć i rejestr głosu dla wszystkich kwestii w paczce.
        Zwraca słownik: {batch_id: 'Głos: żeński/wysoki' | 'Głos: męski/niski'}.
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

                chunk = full_audio[start_idx:min(end_idx, len(full_audio))]
                f0 = cls.estimate_pitch_f0(chunk, sample_rate=framerate)

                if f0 is not None:
                    if f0 >= 175.0:
                        results[b_id] = f"żeński / wysoki (~{int(f0)}Hz)"
                    elif f0 <= 155.0:
                        results[b_id] = f"męski / niski (~{int(f0)}Hz)"
                    else:
                        results[b_id] = f"mieszany/pośredni (~{int(f0)}Hz)"

        except Exception:
            pass

        return results
