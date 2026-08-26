"""
Tool for automatic batch extraction of English subtitles (.ass / .srt) from video files (.mkv, .mp4).
Supports:
- Drag-and-drop of single or multiple video files
- Processing entire folders recursively
- Automatic detection of English tracks (eng / english / dialogues)
- Preservation of original subtitle formats (.ass with full typesetting or .srt)
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".mov", ".m4v", ".webm"}

def get_subtitles_info(video_path: str) -> List[Dict[str, Any]]:
    """
    Returns a detailed list of subtitle tracks in the video file.
    """
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        video_path
    ]
    import json
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        tracks = []
        sub_idx = 0
        for s in data.get("streams", []):
            if s.get("codec_type") == "subtitle":
                tags = s.get("tags", {})
                codec = s.get("codec_name", "ass").lower()
                tracks.append({
                    "sub_index": sub_idx,
                    "stream_index": s.get("index"),
                    "codec": codec,
                    "language": tags.get("language", "und").lower(),
                    "title": tags.get("title", "")
                })
                sub_idx += 1
        return tracks
    except Exception:
        return []

def extract_track_from_video(video_path: Path, output_dir: Optional[Path] = None, track_idx: Optional[int] = None) -> Optional[Path]:
    """
    Extracts English subtitle track from video file and saves it next to video or in target directory.
    """
    tracks = get_subtitles_info(str(video_path))
    if not tracks:
        print(f"[Skipped]: {video_path.name} (no embedded subtitle tracks)")
        return None

    # Select appropriate track (search for 'eng', 'en', 'dialogue' or take specified/first)
    chosen_track = None
    if track_idx is not None and 0 <= track_idx < len(tracks):
        chosen_track = tracks[track_idx]
    else:
        # Priority 1: Language 'eng' / 'en' with dialogue
        for t in tracks:
            if t["language"] in ("eng", "en", "english") and "sign" not in t["title"].lower():
                chosen_track = t
                break
        
        # Priority 2: Any 'eng'
        if not chosen_track:
            for t in tracks:
                if t["language"] in ("eng", "en", "english"):
                    chosen_track = t
                    break

        # Priority 3: First available track
        if not chosen_track:
            chosen_track = tracks[0]

    # Determine output format
    codec = chosen_track["codec"]
    if "ass" in codec or "ssa" in codec:
        ext = ".ass"
    elif "subrip" in codec or "srt" in codec:
        ext = ".srt"
    elif "pgs" in codec or "hdmv" in codec or "vobsub" in codec or "dvd" in codec:
        print(f"[Warning]: Track in {video_path.name} is bitmap/PGS ({codec}). Extraction may require OCR.")
        ext = ".sup"
    else:
        ext = ".ass"

    target_dir = output_dir if output_dir else video_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / f"{video_path.stem}.en{ext}"

    # Ffmpeg command for extraction
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-map", f"0:s:{chosen_track['sub_index']}",
        str(out_file)
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        lang_info = f"language={chosen_track['language']}, title='{chosen_track['title']}'"
        print(f"[Success]: Extracted {out_file.name} (Track {chosen_track['sub_index']}: {lang_info})")
        return out_file
    except Exception as e:
        print(f"[Extraction error]: {video_path.name} -> {e}")
        return None

def pick_files_or_dir_gui() -> List[Path]:
    """
    Opens file picker dialog for Windows (GUI).
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        files = filedialog.askopenfilenames(
            title="Select video files for subtitle extraction",
            filetypes=[
                ("Video files", "*.mkv *.mp4 *.avi *.mov *.webm"),
                ("All files", "*.*")
            ]
        )
        root.destroy()
        return [Path(f) for f in files] if files else []
    except Exception:
        return []

def main():
    parser = argparse.ArgumentParser(
        description="English subtitle extractor for video files (.mkv, .mp4)"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Paths to video files or directories"
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Optional target directory for extracted subtitles (default: beside video)"
    )
    parser.add_argument(
        "--track", "-t",
        type=int,
        default=None,
        help="Force specific subtitle track index (default: auto-detect English)"
    )

    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs] if args.inputs else []
    
    if not input_paths:
        print("[Info] No file arguments provided. Opening file picker dialog...")
        input_paths = pick_files_or_dir_gui()
        if not input_paths:
            print("[Info] No files selected. Exiting.")
            sys.exit(0)

    # Collect all video files (including inside nested folders)
    video_files: List[Path] = []
    for p in input_paths:
        if p.is_dir():
            for root_dir, _, files in os.walk(p):
                for f in files:
                    fpath = Path(root_dir) / f
                    if fpath.suffix.lower() in VIDEO_EXTENSIONS:
                        video_files.append(fpath)
        elif p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS:
            video_files.append(p)

    if not video_files:
        print("[Error]: No supported video files found (.mkv, .mp4, .avi).")
        sys.exit(1)

    print(f"\n=======================================================")
    print(f"  English Subtitle Video Extractor")
    print(f"  Found video files to process: {len(video_files)}")
    print(f"=======================================================\n")

    out_dir = Path(args.output_dir) if args.output_dir else None
    extracted_count = 0

    for i, vfile in enumerate(video_files, 1):
        print(f"[{i}/{len(video_files)}] Processing: {vfile.name}")
        res = extract_track_from_video(vfile, output_dir=out_dir, track_idx=args.track)
        if res:
            extracted_count += 1

    print(f"\n=======================================================")
    print(f"  Completed! Successfully extracted subtitles for {extracted_count}/{len(video_files)} files.")
    print(f"=======================================================\n")

if __name__ == "__main__":
    main()
