# -*- coding: utf-8 -*-
"""
Moduł Kinowego Dociągania Napisów do Cięć Montażowych (Shot-Cut Snapper / Netflix AVT Standard).
Wykrywa twarde cięcia kamerowe (Shot Transitions) za pomocą szybkiego filtra FFmpeg
i precyzyjnie dociąga krawędzie czasowe napisów (start/end), eliminując zjawisko
mrugania napisów na zmianach ujęć (tzw. Subtitle Shot-Bleed).
"""

import os
import re
import subprocess
from typing import List, Tuple, Optional, Any
import logging

logger = logging.getLogger("scene_snapper")


class SceneShotSnapper:
    @staticmethod
    def detect_scene_cuts_ffmpeg(
        video_path: str,
        threshold: float = 0.38,
        max_duration_sec: Optional[float] = None
    ) -> List[int]:
        """
        Szybko wykrywa znaczniki czasowe cięć montażowych w wideo (w milisekundach)
        za pomocą natywnego filtra FFmpeg 'select=gt(scene,0.38)'.
        Działa z prędkością kilkuset klatek na sekundę (bez renderingu wideo).
        """
        if not video_path or not os.path.exists(video_path):
            return []

        cuts_ms: List[int] = []
        
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i", video_path,
            "-filter:v", f"select='gt(scene,{threshold})',showinfo",
            "-f", "null",
            "-"
        ]
        if max_duration_sec:
            cmd.insert(4, "-t")
            cmd.insert(5, str(max_duration_sec))

        try:
            # Uruchamiamy proces i przechwytujemy stderr ze znacznikami showinfo
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=120
            )
            
            # Wzorzec FFmpeg showinfo: pts_time:12.345
            for line in result.stderr.splitlines():
                if "pts_time:" in line:
                    match = re.search(r"pts_time:([0-9\.]+)", line)
                    if match:
                        sec = float(match.group(1))
                        cuts_ms.append(int(sec * 1000))

        except Exception as e:
            logger.warning(f"Nie udało się pobrać cięć montażowych przez FFmpeg: {e}")

        return sorted(list(set(cuts_ms)))

    @classmethod
    def snap_subtitles_to_cuts(
        cls,
        events: List[Any],
        scene_cuts_ms: List[int],
        snap_window_ms: int = 250,
        min_duration_ms: int = 700
    ) -> Tuple[List[Any], int]:
        """
        Dociąga czasy startu i końca każdego napisu do najbliższego cięcia montażowego,
        jeśli odległość mieści się w oknie tolerancji snap_window_ms (domyślnie ~250ms / 6 klatek).
        
        Zwraca: (zmodyfikowane_eventy, liczba_dokonanych_dociągnięć)
        """
        if not events or not scene_cuts_ms:
            return events, 0

        snapped_count = 0

        for ev in events:
            if not hasattr(ev, "start") or not hasattr(ev, "end"):
                continue

            orig_start = ev.start
            orig_end = ev.end

            # 1. Dociąganie punktu wejścia (START)
            for cut in scene_cuts_ms:
                if abs(ev.start - cut) <= snap_window_ms:
                    # Sprawdź czy nie skróci napisu poniżej minimum
                    if (ev.end - cut) >= min_duration_ms:
                        ev.start = cut
                        snapped_count += 1
                        break

            # 2. Dociąganie punktu wyjścia (END)
            for cut in scene_cuts_ms:
                if abs(ev.end - cut) <= snap_window_ms:
                    # Sprawdź czy po dociągnięciu zachowano minimalny czas ekspozycji
                    if (cut - ev.start) >= min_duration_ms:
                        ev.end = cut
                        snapped_count += 1
                        break

            # Zabezpieczenie integralności
            if ev.end <= ev.start:
                ev.start = orig_start
                ev.end = max(ev.start + min_duration_ms, orig_end)

        return events, snapped_count
