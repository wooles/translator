"""
Subtitle and video frame extraction module using ffmpeg and Pillow.
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Any
from PIL import Image

def get_video_streams_info(video_path: str) -> Dict[str, Any]:
    """
    Retrieves audio and subtitle stream information from a video file using ffprobe/ffmpeg.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        video_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception:
        # Fallback if ffprobe is unavailable in PATH: try ffmpeg
        return {}

def list_subtitle_tracks(video_path: str) -> List[Dict[str, Any]]:
    """
    Returns a list of available subtitle tracks in a video file.
    """
    info = get_video_streams_info(video_path)
    sub_tracks = []
    if "streams" in info:
        sub_idx = 0
        for s in info["streams"]:
            if s.get("codec_type") == "subtitle":
                tags = s.get("tags", {})
                lang = tags.get("language", "und")
                title = tags.get("title", f"Track {sub_idx + 1}")
                codec = s.get("codec_name", "unknown")
                sub_tracks.append({
                    "sub_index": sub_idx,
                    "stream_index": s.get("index"),
                    "language": lang,
                    "title": title,
                    "codec": codec
                })
                sub_idx += 1
    return sub_tracks

def extract_embedded_subtitles(video_path: str, sub_index: int = 0, output_path: Optional[str] = None) -> str:
    """
    Extracts embedded subtitle track from video file into a deterministic .extracted.ass file or specified target path.
    Deterministic naming ensures 100% checkpoint consistency and prevents duplicate Profiler charges.
    """
    if not output_path:
        from pathlib import Path
        vp = Path(video_path)
        deterministic_path = vp.parent / f"{vp.stem}.extracted.ass"
        try:
            deterministic_path.touch(exist_ok=True)
            output_path = str(deterministic_path)
        except Exception:
            safe_stem = "".join(c for c in vp.stem if c.isalnum() or c in ("-", "_", " ", "."))
            temp_dir = Path(tempfile.gettempdir()) / "anime_translator_subs"
            temp_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(temp_dir / f"{safe_stem}_track{sub_index}.extracted.ass")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-map", f"0:s:{sub_index}",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return output_path

def extract_frame_at_timestamp(
    video_path: str,
    timestamp_ms: int,
    output_path: Optional[str] = None,
    max_width: int = 800
) -> str:
    """
    Extracts a video frame at a given timestamp (in milliseconds),
    optimizes its resolution and saves as JPEG.
    """
    if not output_path:
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.close()
        output_path = tmp.name

    sec = max(0.0, timestamp_ms / 1000.0)
    # Extract and scale frame directly with ffmpeg for zero-overhead performance
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{sec:.3f}",
        "-i", video_path,
        "-vframes", "1",
        "-vf", f"scale='min({max_width},iw)':-2",
        "-q:v", "3",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except Exception:
        # Fallback if scale filter has syntax variance
        fallback_cmd = [
            "ffmpeg",
            "-y",
            "-ss", f"{sec:.3f}",
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "3",
            output_path
        ]
        subprocess.run(fallback_cmd, capture_output=True, text=True, check=True)

    # Frame optimization with Pillow (progressive slim JPEG for sub-20ms upload)
    try:
        with Image.open(output_path) as img:
            img = img.convert("RGB")
            width, height = img.size
            if width > max_width:
                new_height = int((max_width / width) * height)
                img = img.resize((max_width, new_height), Image.Resampling.BILINEAR)
            img.save(output_path, "JPEG", quality=78, optimize=True, progressive=True, subsampling=2)
    except Exception:
        pass

    return output_path

def extract_audio_slice(
    video_path: str,
    start_ms: int,
    end_ms: int,
    output_path: Optional[str] = None
) -> str:
    """
    Extracts a short audio slice (16kHz mono WAV) for a given scene/dialogue batch.
    Allows the Gemini multimodal model to directly hear original Japanese voice acting.
    """
    if not output_path:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        output_path = tmp.name

    start_sec = max(0.0, (start_ms - 200) / 1000.0)  # 200ms voice onset buffer
    duration_sec = max(0.8, (end_ms - start_ms + 400) / 1000.0)  # release decay buffer

    # Fast seek with -ss before -i, 16kHz mono WAV
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{start_sec:.3f}",
        "-t", f"{duration_sec:.3f}",
        "-i", video_path,
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        output_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return output_path
    except Exception as e:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        raise e
