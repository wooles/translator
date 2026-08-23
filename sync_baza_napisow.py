# -*- coding: utf-8 -*-
r"""
Automatyczny Synchronizator i Budowniczy Bazy Napisów (Translation Memory).

Obsługuje:
- Przeciąganie pojedynczych lub wielu plików wideo (.mkv, .mp4)
- Przeciąganie całych folderów (np. 'E:\Kingdom 6th Season', 'E:\Mushoku Tensei S2')
- Pełną obsługę wydań Blu-ray / BDMV (pliki 00001.mkv, BD_01.mkv, EP01.mkv)
- Inteligentne rozwiązywanie nazwy anime z folderu nadrzędnego dla generycznych nazw plików
- Automatyczną ekstrakcję angielskich napisów (.en.ass / .en.srt)
- 3-poziomowe parowanie polskich napisów (.ass / .srt) w folderze
- Kopiowanie pełnych par (EN + PL) z czytelnymi nazwami do 'baza napisów'
- Automatyczne usuwanie tymczasowych angielskich napisów z folderu źródłowego
- Błyskawiczne przeindeksowanie lokalnej bazy SQLite (translation_memory.db) w ~20 sekund
"""

import os
import re
import sys
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from extract_subtitles import get_subtitles_info, VIDEO_EXTENSIONS
from memory import TranslationMemory

BAZA_NAPISOW_DIR = Path(__file__).parent / "baza napisów"


def extract_episode_num(name: str) -> str:
    """
    Ekstraktuje numer odcinka z dowolnego formatu nazwy (00001, BD_01, EP01, E01, - 01).
    """
    # 1. Standardowe wzorce: - 01, _01, EP01, E01, Episode 01, Odc 01
    m = re.search(r"(?:ep|e|episode|odc|vol|[-_\s\[\.])0*(\d{1,4})(?:v\d+)?(?:[-_\s\.\]\)]|$)", name, re.IGNORECASE)
    if m:
        return m.group(1).lstrip("0") or "0"
    # 2. Same cyfry (np. 00001, 01, 1)
    m2 = re.match(r"^0*(\d{1,4})$", name)
    if m2:
        return m2.group(1).lstrip("0") or "0"
    return ""


def find_matching_polish_sub(video_path: Path) -> Tuple[Optional[Path], str]:
    """
    Wyszukuje odpowiadający plik z polskimi napisami w folderze wideo za pomocą 3 strategii:
    1. Dokładne dopasowanie nazwy pliku
    2. Dopasowanie po wyekstrahowanym numerze odcinka
    3. Dopasowanie po naturalnym porządku sortowania (dla wydań Blu-ray 00001.mkv)
    Zwraca krotkę: (sciezka_do_pliku_pl, numer_odcinka).
    """
    parent_dir = video_path.parent
    stem = video_path.stem
    ep_num = extract_episode_num(stem)

    # 1. Dokładne dopasowanie nazwy
    candidates = [
        parent_dir / f"{stem}.ass",
        parent_dir / f"{stem}.srt",
        parent_dir / f"{stem}.pl.ass",
        parent_dir / f"{stem}.pl.srt",
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c, ep_num

    # 2. Szukanie pliku po numerze odcinka
    if ep_num:
        for f in parent_dir.glob("*"):
            if f.is_file() and f.suffix.lower() in (".ass", ".srt"):
                if ".en." in f.name.lower() or ".ang." in f.name.lower():
                    continue
                f_ep = extract_episode_num(f.stem)
                if f_ep == ep_num:
                    return f, ep_num

    # 3. Strategia Blu-ray: parowanie według naturalnego sortowania w folderze
    all_videos = sorted([
        f for f in parent_dir.iterdir()
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS
    ])
    all_pl_subs = sorted([
        f for f in parent_dir.iterdir()
        if f.is_file() and f.suffix.lower() in (".ass", ".srt")
        and ".en." not in f.name.lower() and ".ang." not in f.name.lower()
    ])

    if len(all_videos) > 0 and len(all_videos) == len(all_pl_subs):
        try:
            v_idx = all_videos.index(video_path)
            matching_sub = all_pl_subs[v_idx]
            sub_ep = extract_episode_num(matching_sub.stem) or str(v_idx + 1)
            return matching_sub, sub_ep
        except Exception:
            pass

    return None, ep_num


def resolve_baza_base_stem(vpath: Path, pl_sub_path: Path, ep_num: str) -> str:
    """
    Ustala czytelną nazwę bazową dla plików w 'baza napisów',
    aby baza wiedzy i Pamięć Tłumaczeniowa poprawnie powiązały tytuł anime.
    """
    # 1. Sprawdzamy czy nazwa pliku polskiego jest bogata/opisowa (np. '[Grupa] Mushoku Tensei S2 - 01.ass')
    pl_stem = pl_sub_path.stem
    if len(pl_stem) > 6 and not pl_stem.isdigit() and not re.match(r"^(?:bd_?\d+|ep_?\d+|0*\d+)$", pl_stem, re.IGNORECASE):
        return pl_stem

    # 2. Sprawdzamy czy nazwa wideo jest bogata/opisowa
    v_stem = vpath.stem
    if len(v_stem) > 6 and not v_stem.isdigit() and not re.match(r"^(?:bd_?\d+|ep_?\d+|0*\d+)$", v_stem, re.IGNORECASE):
        return v_stem

    # 3. Fallback dla wydań Blu-ray (np. folder 'Mushoku Tensei S2' + '00001.mkv'):
    parent_clean = vpath.parent.name.replace("[BD]", "").replace("[BDMV]", "").strip()
    try:
        ep_formatted = f"{int(ep_num):02d}" if ep_num else "01"
    except Exception:
        ep_formatted = ep_num or "01"
    return f"{parent_clean} - {ep_formatted}"


def extract_english_track(video_path: Path, dest_dir: Path, target_stem: str) -> Optional[Path]:
    """
    Wyciąga angielską ścieżkę dialogową bezpośrednio do wskazanego pliku w folderze bazy.
    """
    tracks = get_subtitles_info(str(video_path))
    if not tracks:
        return None

    chosen_track = None
    for t in tracks:
        if t["language"] in ("eng", "en", "english") and "sign" not in t["title"].lower():
            chosen_track = t
            break
    if not chosen_track:
        for t in tracks:
            if t["language"] in ("eng", "en", "english"):
                chosen_track = t
                break
    if not chosen_track:
        chosen_track = tracks[0]

    codec = chosen_track["codec"]
    if "pgs" in codec or "hdmv" in codec or "vobsub" in codec or "dvd" in codec:
        print(f"  ⚠️  [Ostrzeżenie Blu-ray]: Ścieżka napisów w '{video_path.name}' to napisy graficzne PGS/Bitmap ({codec}).")
        print(f"      Ekstrakcja wymaga ścieżki tekstowej (.ass / .srt).")
        return None

    ext = ".ass" if ("ass" in codec or "ssa" in codec) else (".srt" if ("subrip" in codec or "srt" in codec) else ".ass")
    out_file = dest_dir / f"{target_stem}.en{ext}"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-map", f"0:s:{chosen_track['sub_index']}",
        str(out_file)
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return out_file
    except Exception as e:
        print(f"  ❌ [Błąd FFmpeg]: {video_path.name} -> {e}")
        return None


def sync_videos_to_baza(video_files: List[Path], baza_dir: Path = BAZA_NAPISOW_DIR) -> int:
    """
    Przetwarza listę plików wideo: wyciąga EN, paruje z PL, kopiuje parę do bazy i czyści śmieci.
    """
    baza_dir.mkdir(parents=True, exist_ok=True)
    synced_pairs = 0

    print("\n" + "═" * 70)
    print("  🚀 ROZPOCZYNANIE SYNCHRONIZACJI BAZY NAPISÓW (Translation Memory)")
    print(f"  Folder docelowy bazy: {baza_dir}")
    print(f"  Liczba plików wideo do przetworzenia: {len(video_files)}")
    print("═" * 70 + "\n")

    for idx, vpath in enumerate(video_files, 1):
        print(f"[{idx}/{len(video_files)}] Skanowanie: {vpath.name}")

        # 1. Sprawdzamy czy w folderze wideo są polskie napisy
        pl_sub_path, ep_num = find_matching_polish_sub(vpath)
        if not pl_sub_path:
            print(f"  ⚠️  [Pominięto]: Brak polskich napisów (.ass/.srt) w folderze: {vpath.parent.name}")
            print(f"      Aby dodać odcinek do bazy, umieść obok wideo plik z polskimi napisami.")
            continue

        # 2. Ustalamy reprezentatywną nazwę pliku w bazie (dla wydań Blu-ray)
        baza_stem = resolve_baza_base_stem(vpath, pl_sub_path, ep_num)

        # 3. Wyciągamy angielskie napisy bezpośrednio do folderu bazy
        en_target_path = extract_english_track(vpath, dest_dir=baza_dir, target_stem=baza_stem)
        if not en_target_path or not en_target_path.exists() or en_target_path.stat().st_size == 0:
            print(f"  ❌ [Błąd]: Nie udało się wyciągnąć angielskich napisów tekstowych z {vpath.name}")
            continue

        # 4. Kopiujemy polskie napisy do folderu bazy (z zachowaniem spójnej nazwy)
        pl_target_ext = pl_sub_path.suffix
        pl_target_path = baza_dir / f"{baza_stem}{pl_target_ext}"
        try:
            shutil.copy2(pl_sub_path, pl_target_path)
        except Exception as e:
            print(f"  ❌ [Błąd kopiowania PL]: {e}")
            continue

        # 5. Sprawdzamy i ewentualnie usuwamy tymczasowy angielski plik z folderu źródłowego
        for temp_pattern in [f"{vpath.stem}.en.*", f"{baza_stem}.en.*"]:
            for temp_f in vpath.parent.glob(temp_pattern):
                if temp_f.is_file():
                    try:
                        temp_f.unlink()
                    except Exception:
                        pass

        synced_pairs += 1
        print(f"  ✅ [SPAROWANO I SKOPIOWANO DO BAZY]:")
        print(f"      ├─ Źródło: {vpath.name} + {pl_sub_path.name}")
        print(f"      ├─ Zapis EN: {en_target_path.name}")
        print(f"      └─ Zapis PL: {pl_target_path.name}")
        print(f"      (Folder źródłowy '{vpath.parent.name}' pozostawiony w 100% czysty)")

    # 6. Automatyczne błyskawiczne przeindeksowanie bazy SQLite
    if synced_pairs > 0:
        print("\n" + "─" * 70)
        print("  🔄 AKTUALIZACJA I RE-INDEKSACJA PAMIĘCI TŁUMACZENIOWEJ (SQLite)...")
        tm = TranslationMemory()
        total_db_pairs = tm.index_database_directory(baza_dir)
        print(f"  ✨ [SUKCES]: Baza Pamięci Tłumaczeniowej zawiera teraz {total_db_pairs} aktywnych par dialogowych!")
        print("─" * 70 + "\n")
    else:
        print("\n[Info]: Nie dodano żadnych nowych par do bazy.\n")

    return synced_pairs


def main():
    parser = argparse.ArgumentParser(
        description="Automatyczny synchronizator par napisów EN+PL do bazy Translation Memory"
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Ścieżki do plików wideo (.mkv) lub całych folderów"
    )
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs] if args.inputs else []
    if not input_paths:
        from extract_subtitles import pick_files_or_dir_gui
        print("[Info] Nie podano plików jako argumentu. Otwieram okno wyboru...")
        input_paths = pick_files_or_dir_gui()
        if not input_paths:
            print("[Info] Nie wybrano żadnych plików. Zamykam program.")
            sys.exit(0)

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
        print("[Błąd]: Nie znaleziono żadnych plików wideo (.mkv, .mp4).")
        sys.exit(1)

    sync_videos_to_baza(video_files)


if __name__ == "__main__":
    main()
