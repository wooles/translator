# -*- coding: utf-8 -*-
"""
Automated build script for compiling the project into a standalone executable (translator.exe) via PyInstaller.
Bundles all dependencies, assets, memory databases, and modules into an executable package.
"""

import os
import sys
import subprocess
from pathlib import Path

def build_executable():
    print("=" * 65)
    print("  🎬 BUDOWANIE SAMODZIELNEJ APLIKACJI: translator.exe")
    print("=" * 65)

    base_dir = Path(__file__).parent.resolve()
    gui_script = base_dir / "gui_app.py"

    if not gui_script.exists():
        print(f"[BŁĄD] Nie znaleziono pliku {gui_script}")
        return

    # Base PyInstaller arguments
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=translator",
        "--windowed",            # No black console window in the background
        "--noconfirm",           # Overwrite previous build
        "--clean",               # Clean cache
    ]

    # Include subtitle database directory if present
    baza_dir = base_dir / "baza napisów"
    if baza_dir.exists():
        cmd.extend(["--add-data", f"{baza_dir};baza napisów"])

    # Include main script
    cmd.append(str(gui_script))

    print("\n[PyInstaller] Uruchamianie kompilacji do dist/translator.exe...")
    print(f"[Komenda]: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=str(base_dir))

    if result.returncode == 0:
        exe_path = base_dir / "dist" / "translator" / "translator.exe"
        if not exe_path.exists():
            exe_path = base_dir / "dist" / "translator.exe"

        print("\n" + "=" * 65)
        print("  🎉 KOMPILACJA ZAKOŃCZONA SUKCESEM!")
        print(f"  Plik wykonywalny: {exe_path}")
        print("=" * 65 + "\n")
    else:
        print("\n[BŁĄD] Kompilacja nie powiodła się. Sprawdź logi powyżej.")

if __name__ == "__main__":
    build_executable()
