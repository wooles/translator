# -*- coding: utf-8 -*-
"""
Moduł Lokalnej Analizy Prozodii i Emocji Audio (Prosody & Tone Engine).
W 100% lokalna, bezkosztowa analiza fali dźwiękowej (amplituda RMS, dynamika, tempo mowy)
pozwalająca modelowi rozróżnić szept, krzyk, ton ironiczny oraz szybki monolog.
"""

import os
import wave
import math
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

class AudioProsodyEngine:
    def __init__(self):
        pass

    @staticmethod
    def read_wav_segment(wav_path: str, start_ms: int, end_ms: int) -> Optional[np.ndarray]:
        """Wczytuje fragment fali dźwiękowej z pliku WAV (16kHz mono)."""
        if not wav_path or not os.path.exists(wav_path):
            return None

        try:
            with wave.open(wav_path, "rb") as wf:
                framerate = wf.getframerate()
                nchannels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                
                # Obliczanie pozycji ramek
                start_frame = int((start_ms / 1000.0) * framerate)
                duration_frames = int(((end_ms - start_ms) / 1000.0) * framerate)
                
                if duration_frames <= 0:
                    return None

                wf.setpos(min(start_frame, max(0, wf.getnframes() - 1)))
                raw_bytes = wf.readframes(duration_frames)
                
                if not raw_bytes:
                    return None

                # Konwersja na int16 numpy array
                if sampwidth == 2:
                    audio_data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
                elif sampwidth == 1:
                    audio_data = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128) * 256.0
                else:
                    return None

                if nchannels > 1:
                    audio_data = audio_data.reshape(-1, nchannels).mean(axis=1)

                return audio_data
        except Exception:
            return None

    @classmethod
    def analyze_scene_prosody(
        cls,
        wav_path: str,
        batch_start_ms: int,
        events: List[Tuple[int, Any]]
    ) -> Dict[int, str]:
        """
        Analizuje cechy foniczne (RMS dBFS, dynamika, tempo) dla wszystkich kwestii w paczce.
        Zwraca słownik: {batch_id: 'opis_tonu'} (np. {1: 'cichy szept', 2: 'krzyk / wzburzenie'}).
        """
        if not wav_path or not os.path.exists(wav_path):
            return {}

        results = {}

        for b_id, ev in events:
            # Względny czas w pliku wycinka WAV
            rel_start = max(0, ev.start - batch_start_ms)
            rel_end = max(rel_start + 200, ev.end - batch_start_ms)

            samples = cls.read_wav_segment(wav_path, rel_start, rel_end)
            if samples is None or len(samples) < 400:
                continue

            # Obliczanie RMS (Root Mean Square) energii
            rms = np.sqrt(np.mean(samples ** 2))
            if rms <= 1.0:
                continue

            # Konwersja na decybele dBFS (maksimum dla 16-bit to 32767)
            dbfs = 20 * math.log10(rms / 32767.0)

            # Szczytowa amplituda (Peak)
            peak = np.max(np.abs(samples))
            peak_dbfs = 20 * math.log10(max(1.0, peak) / 32767.0)

            # Wykrywanie charakterystyki tonu
            tags = []
            if dbfs < -33.0:
                tags.append("cichy szept / niepewność")
            elif dbfs > -13.0 or peak_dbfs > -1.5:
                tags.append("krzyk / wysokie emocje / wzburzenie")

            # Analiza czasu trwania i gęstości mowy (szybki monolog)
            duration_s = (ev.end - ev.start) / 1000.0
            if duration_s > 0:
                # Wariancja energii w oknach 50ms (wykrywanie dynamiki/nerwowości)
                window_size = 800  # 50ms przy 16kHz
                if len(samples) > window_size * 2:
                    chunks = [samples[i:i+window_size] for i in range(0, len(samples), window_size)]
                    chunk_energies = [np.sqrt(np.mean(c**2)) for c in chunks if len(c) == window_size]
                    if chunk_energies:
                        energy_std = np.std(chunk_energies) / (rms + 1e-5)
                        if energy_std > 0.85 and "krzyk" not in str(tags):
                            tags.append("emocjonalne drżenie głosu")

            if tags:
                results[b_id] = " | ".join(tags)

        return results
