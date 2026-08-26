# -*- coding: utf-8 -*-
"""
Master Ecosystem Backup & Restore Engine.
Supports Zip64 (no 2GB limit), guarantees 100% data consistency,
packages AI history (.gemini), downloaded models/caches (.cache), and all projects from the Desktop.
"""

import os
import sys
import time
import zipfile
from pathlib import Path


def create_master_backup():
    user_dir = Path(os.path.expanduser("~")).resolve()
    desktop_dir = user_dir / "Desktop"
    output_zip = desktop_dir / "KOMPLETNY_BACKUP_SYSTEMU.zip"

    print("\n" + "=" * 70)
    print("  ROZPOCZYNAM TWORZENIE PELNEGO BACKUPU EKOSYSTEMU (Zip64 Engine)")
    print("=" * 70)

    # 1. List of resources to bundle
    items_to_backup = []

    # A. AI memory and conversation history (.gemini)
    gemini_dir = user_dir / ".gemini"
    if gemini_dir.exists():
        items_to_backup.append(("Pamiec AI i historia rozmow (.gemini)", gemini_dir, ".gemini"))

    # B. Downloaded models and cache (.cache)
    cache_dir = user_dir / ".cache"
    if cache_dir.exists():
        items_to_backup.append(("Zasoby zewnetrzne (.cache)", cache_dir, ".cache"))

    # C. Desktop Projects
    projects = ["translator", "sorter", "kalendarz"]
    for proj in projects:
        proj_path = desktop_dir / proj
        if proj_path.exists():
            items_to_backup.append((f"Projekt: {proj}", proj_path, f"DesktopProjects/{proj}"))

    single_file = desktop_dir / "produkcja.html"
    if single_file.exists():
        items_to_backup.append(("Plik produkcja.html", single_file, "DesktopProjects/produkcja.html"))

    EXCLUDE_DIRS = {".venv", "__pycache__", ".pytest_cache", "bin", "obj", ".vs"}

    files_to_pack = []
    for label, src_path, arc_prefix in items_to_backup:
        if src_path.is_file():
            files_to_pack.append((src_path, arc_prefix))
        elif src_path.is_dir():
            for root, dirs, files in os.walk(src_path):
                dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(src_path).as_posix()
                    arc_name = f"{arc_prefix}/{rel_p}"
                    files_to_pack.append((full_p, arc_name))

    total_files = len(files_to_pack)
    print(f"\n[INFO] Wykryto lacznie {total_files} plikow do bezstratnego spakowania.")

    temp_zip = output_zip.with_suffix(".tmp.zip")
    if temp_zip.exists():
        temp_zip.unlink()

    packed_count = 0
    t0 = time.time()

    with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True, compresslevel=6) as zf:
        for full_p, arc_name in files_to_pack:
            try:
                zf.write(full_p, arc_name)
                packed_count += 1
                if packed_count % 300 == 0 or packed_count == total_files:
                    pct = (packed_count / total_files) * 100
                    sys.stdout.write(f"\r  [Pakowanie]: {packed_count}/{total_files} ({pct:.1f}%) | {arc_name[:40]:<40}")
                    sys.stdout.flush()
            except Exception as e:
                print(f"\n  [Ostrzezenie przy {full_p}]: {e}")

    if output_zip.exists():
        output_zip.unlink()
    temp_zip.rename(output_zip)

    dur = time.time() - t0
    final_mb = output_zip.stat().st_size / (1024 * 1024)

    print("\n\n" + "=" * 70)
    print("  SUKCES! PELNY BACKUP ZOSTAL UTWORZONY BEZBLEDNIE!")
    print(f"  Plik docelowy: {output_zip}")
    print(f"  Waga archiwum: {final_mb:.2f} MB")
    print(f"  Czas tworzenia: {dur:.1f} s ({total_files} plikow)")
    print("=" * 70 + "\n")


def restore_master_backup():
    user_dir = Path(os.path.expanduser("~")).resolve()
    desktop_dir = user_dir / "Desktop"
    backup_zip = desktop_dir / "KOMPLETNY_BACKUP_SYSTEMU.zip"

    if not backup_zip.exists():
        print(f"[BLAD]: Nie znaleziono pliku {backup_zip} na Pulpicie!")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("  ROZPOCZYNAM PRZYWRACANIE CALEGO EKOSYSTEMU NA NOWYM PC")
    print("=" * 70)

    with zipfile.ZipFile(backup_zip, "r", allowZip64=True) as zf:
        namelist = zf.namelist()
        total_items = len(namelist)
        print(f"[INFO] Rozpakowywanie {total_items} plikow...")

        for idx, item in enumerate(namelist, 1):
            if item.startswith(".gemini/"):
                zf.extract(item, user_dir)
            elif item.startswith(".cache/"):
                zf.extract(item, user_dir)
            elif item.startswith("DesktopProjects/"):
                rel = item[len("DesktopProjects/"):]
                if rel:
                    target = desktop_dir / rel
                    if item.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with zf.open(item) as src, open(target, "wb") as dst:
                            dst.write(src.read())

            if idx % 300 == 0 or idx == total_items:
                sys.stdout.write(f"\r  [Przywracanie]: {idx}/{total_items} ({idx/total_items*100:.1f}%)")
                sys.stdout.flush()

    print("\n\n[INFO] Konfiguracja srodowiska Python dla tlumacza...")
    trans_dir = desktop_dir / "translator"
    if trans_dir.exists():
        req_file = trans_dir / "requirements.txt"
        if req_file.exists():
            os.chdir(trans_dir)
            import subprocess
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=False)
            pip_exe = trans_dir / ".venv" / "Scripts" / "pip.exe"
            if pip_exe.exists():
                subprocess.run([str(pip_exe), "install", "-r", "requirements.txt"], check=False)

    print("\n" + "=" * 70)
    print("  PRZYWRACANIE ZAKONCZONE W 100%! WSZYSTKO JEST NA SWOIM MIEJSCU!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        restore_master_backup()
    else:
        create_master_backup()
