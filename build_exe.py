# -*- coding: utf-8 -*-
"""
Skrypt automatycznej kompilacji projektu do samodzielnego pliku translator.exe (PyInstaller).
Pakuje wszystkie zależności, zasoby, bazy pamięci i moduły w jeden plik wykonywalny.
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

    # Podstawowe argumenty PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=translator",
        "--windowed",            # Bez czarnego okna konsoli w tle
        "--noconfirm",           # Nadpisywanie poprzedniego buildu
        "--clean",               # Czyszczenie cache
    ]

    # Dołączenie folderu z bazą napisów jeśli istnieje
    baza_dir = base_dir / "baza napisów"
    if baza_dir.exists():
        cmd.extend(["--add-data", f"{baza_dir};baza napisów"])

    # Dołączenie głównego skryptu
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
