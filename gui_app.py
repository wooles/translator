# -*- coding: utf-8 -*-
"""
Aplikacja Okienkowa GUI dla Tłumacza Anime (PySide6 / Qt 6).
Zawiera:
- Pełną integrację z silnikiem 43 Filarów AVT i Context Cache.
- Obsługę przeciągania plików i folderów (Drag & Drop).
- Asynchroniczne przetwarzanie w osobnym wątku (QThread) - zero zacięć okna.
- Podgląd tłumaczenia na żywo linijka po linijce oraz licznik kosztów w PLN.
- Panel Ustawień (Klucz API, Whisper large-v3-turbo, Biblia Serialu).
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QIcon, QFont, QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QRadioButton, QButtonGroup,
    QCheckBox, QFileDialog, QMessageBox, QDialog, QLineEdit,
    QComboBox, QGroupBox, QSplitter, QFrame, QScrollArea
)

# Załadowanie zmiennych środowiskowych (.env)
from dotenv import load_dotenv, set_key
load_dotenv()

from translator import MultimodalTranslator as TranslatorEngine
from verifier import DialogueVerifier
from model_resolver import resolve_best_models
from pricing_guard import PricingGuard
from series_memory import SeriesBible
from main import collect_input_files, resolve_episode_files

# ─────────────────────────────────────────────────────────────────────────────
# STYLIZACJA DARK FLUENT DESIGN (QSS)
# ─────────────────────────────────────────────────────────────────────────────
MODERN_DARK_STYLE = """
QMainWindow, QDialog {
    background-color: #0f111a;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}

QWidget {
    background-color: transparent;
    color: #e2e8f0;
    font-size: 13px;
}

QGroupBox {
    border: 1px solid #2d3748;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #90cdf4;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
}

QPushButton {
    background-color: #1a202c;
    border: 1px solid #4a5568;
    border-radius: 6px;
    padding: 8px 16px;
    color: #f7fafc;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2b6cb0;
    border-color: #3182ce;
}

QPushButton:pressed {
    background-color: #2c5282;
}

QPushButton#PrimaryButton {
    background-color: #3182ce;
    border: 1px solid #4299e1;
    font-size: 14px;
    padding: 10px 20px;
}

QPushButton#PrimaryButton:hover {
    background-color: #2b6cb0;
}

QPushButton#StopButton {
    background-color: #e53e3e;
    border: 1px solid #f56565;
}

QPushButton#StopButton:hover {
    background-color: #c53030;
}

QLineEdit, QComboBox, QTextEdit {
    background-color: #1a202c;
    border: 1px solid #4a5568;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f7fafc;
    selection-background-color: #3182ce;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #63b3ed;
}

QProgressBar {
    border: 1px solid #2d3748;
    border-radius: 6px;
    text-align: center;
    background-color: #1a202c;
    color: #ffffff;
    font-weight: bold;
    height: 22px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3182ce, stop:1 #48bb78);
    border-radius: 5px;
}

QTableWidget {
    background-color: #141824;
    border: 1px solid #2d3748;
    border-radius: 6px;
    gridline-color: #2d3748;
    color: #e2e8f0;
}

QHeaderView::section {
    background-color: #1a202c;
    color: #a0aec0;
    padding: 6px;
    font-weight: bold;
    border: none;
    border-bottom: 1px solid #2d3748;
}

QScrollBar:vertical {
    border: none;
    background: #0f111a;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #4a5568;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #718096;
}

QRadioButton, QCheckBox {
    spacing: 8px;
    color: #e2e8f0;
}

QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# WĄTEK ROBOCZY TŁUMACZENIA (QThread)
# ─────────────────────────────────────────────────────────────────────────────
class TranslationWorker(QThread):
    progress_signal = Signal(int, int, list, float)  # current, total, previews, cost_pln
    log_signal = Signal(str)
    file_finished_signal = Signal(str, float)        # output_path, total_cost_pln
    queue_finished_signal = Signal()
    error_signal = Signal(str)

    def __init__(
        self,
        files_to_process: List[Dict[str, str]],
        profile_idx: str,
        keep_honorifics: bool,
        use_whisper: bool,
        whisper_model: str
    ):
        super().__init__()
        self.files_to_process = files_to_process
        self.profile_idx = profile_idx
        self.keep_honorifics = keep_honorifics
        self.use_whisper = use_whisper
        self.whisper_model = whisper_model
        self.is_running = True

    def run(self):
        try:
            api_key = os.environ.get("GEMINI_API_KEY", "").strip()
            if not api_key:
                self.error_signal.emit("Brak klucza GEMINI_API_KEY! Ustaw go w oknie Ustawień.")
                return

            # Wykrycie najnowszych modeli
            models = resolve_best_models()
            if self.profile_idx == "1":
                p1_model = models["flash_lite"]
                p2_model = None
                enable_verifier = False
            elif self.profile_idx == "2":
                p1_model = models["flash"]
                p2_model = None
                enable_verifier = False
            else:  # Profil 3 (Master Pro)
                p1_model = models["flash"]
                p2_model = models["pro"]
                enable_verifier = True

            self.log_signal.emit(f"🚀 Inicjalizacja silnika: Faza 1 ({p1_model})" + (f" -> Faza 2 ({p2_model})" if enable_verifier else ""))

            engine = TranslatorEngine(
                api_key=api_key,
                model=p1_model,
                model_phase2=p2_model,
                enable_verifier=enable_verifier,
                keep_honorifics=self.keep_honorifics,
                use_whisper=self.use_whisper,
                whisper_model_size=self.whisper_model
            )

            total_files = len(self.files_to_process)
            for file_idx, item in enumerate(self.files_to_process, 1):
                if not self.is_running:
                    self.log_signal.emit("⏹ Tłumaczenie przerwane przez użytkownika.")
                    break

                subs_path = item["subs"]
                video_path = item.get("video")
                file_name = Path(subs_path).name

                self.log_signal.emit(f"\n[{file_idx}/{total_files}] Rozpoczynanie: {file_name}")

                def progress_bridge(cur, tot, previews, cost):
                    if self.is_running:
                        self.progress_signal.emit(cur, tot, previews, cost)

                output_path = engine.translate_file(
                    subs_path=subs_path,
                    video_path=video_path,
                    progress_callback=progress_bridge
                )

                f1_stats = engine.current_episode_tokens
                f2_stats = engine.verifier.current_episode_tokens if engine.verifier else None
                final_cost = PricingGuard.calculate_actual_cost_pln(f1_stats, f2_stats)

                self.file_finished_signal.emit(output_path, final_cost)

            self.queue_finished_signal.emit()

        except Exception as e:
            self.error_signal.emit(f"Błąd podczas tłumaczenia: {str(e)}")

    def stop(self):
        self.is_running = False


# ─────────────────────────────────────────────────────────────────────────────
# OKNO USTAWIEŃ (SettingsDialog)
# ─────────────────────────────────────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Ustawienia Tłumacza i Klucza API")
        self.resize(550, 360)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Klucz API Google
        gb_api = QGroupBox("Klucz Google AI Studio (Gemini API)")
        api_layout = QVBoxLayout(gb_api)
        
        lbl_info = QLabel("Wklej swój klucz API z https://aistudio.google.com/app/apikey :")
        api_layout.addWidget(lbl_info)

        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.Password)
        self.txt_api_key.setText(os.environ.get("GEMINI_API_KEY", ""))
        api_layout.addWidget(self.txt_api_key)

        h_api_btns = QHBoxLayout()
        self.btn_show_key = QPushButton("👁 Pokaż")
        self.btn_show_key.clicked.connect(self.toggle_echo)
        self.btn_test_api = QPushButton("🔌 Testuj Połączenie")
        self.btn_test_api.clicked.connect(self.test_api_connection)
        h_api_btns.addWidget(self.btn_show_key)
        h_api_btns.addWidget(self.btn_test_api)
        api_layout.addLayout(h_api_btns)
        layout.addWidget(gb_api)

        # Ustawienia Whisper
        gb_whisper = QGroupBox("Lokalny Japoński Whisper STT")
        wh_layout = QVBoxLayout(gb_whisper)
        lbl_wh = QLabel("Domyślny model transkrypcji audio ze słuchu:")
        wh_layout.addWidget(lbl_wh)

        self.cb_whisper_model = QComboBox()
        self.cb_whisper_model.addItems([
            "large-v3-turbo (Zalecany / Najwyższa jakość)",
            "medium",
            "small",
            "base"
        ])
        wh_layout.addWidget(self.cb_whisper_model)
        layout.addWidget(gb_whisper)

        # Przyciski Zapisz / Anuluj
        h_bottom = QHBoxLayout()
        h_bottom.addStretch()
        btn_save = QPushButton("💾 Zapisz Ustawienia")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self.save_settings)
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        h_bottom.addWidget(btn_cancel)
        h_bottom.addWidget(btn_save)
        layout.addLayout(h_bottom)

    def toggle_echo(self):
        if self.txt_api_key.echoMode() == QLineEdit.Password:
            self.txt_api_key.setEchoMode(QLineEdit.Normal)
            self.btn_show_key.setText("🔒 Ukryj")
        else:
            self.txt_api_key.setEchoMode(QLineEdit.Password)
            self.btn_show_key.setText("👁 Pokaż")

    def test_api_connection(self):
        key = self.txt_api_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Błąd", "Wprowadź klucz API przed testem!")
            return

        try:
            from google import genai
            client = genai.Client(api_key=key)
            res = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents="Test PING"
            )
            QMessageBox.information(self, "Sukces", f"Połączenie nawiązane pomyślnie!\nOdpowiedź Google: {res.text.strip()}")
        except Exception as e:
            QMessageBox.critical(self, "Błąd Połączenia", f"Nie udało się połączyć z API:\n{str(e)}")

    def save_settings(self):
        key = self.txt_api_key.text().strip()
        env_path = Path(__file__).parent / ".env"
        os.environ["GEMINI_API_KEY"] = key
        set_key(str(env_path), "GEMINI_API_KEY", key)
        QMessageBox.information(self, "Zapisano", "Ustawienia zostały pomyślnie zapisane!")
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# GŁÓWNE OKNO APLIKACJI (MainWindow)
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Anime Subtitle Translator Pro — AVT Master Engine (43 Filary)")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)
        self.setAcceptDrops(True)

        self.files_queue: List[Dict[str, str]] = []
        self.worker: Optional[TranslationWorker] = None
        self.start_time = 0.0

        self.setup_ui()
        self.update_pricing_banner()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Górny nagłówek i status
        h_header = QHBoxLayout()
        lbl_title = QLabel("🎬 ANIME SUBTITLE TRANSLATOR PRO")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #63b3ed;")
        h_header.addWidget(lbl_title)

        h_header.addStretch()
        btn_settings = QPushButton("⚙️ Ustawienia API")
        btn_settings.clicked.connect(self.open_settings)
        btn_bible = QPushButton("📚 Biblia Serialu")
        btn_bible.clicked.connect(self.open_series_bible)
        h_header.addWidget(btn_bible)
        h_header.addWidget(btn_settings)
        main_layout.addLayout(h_header)

        # 2. Główny splitter (Lewa: Pliki i Ustawienia | Prawa: Podgląd na żywo)
        splitter = QSplitter(Qt.Horizontal)

        # LEWY PANEL
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Strefa Drag & Drop
        self.drop_box = QFrame()
        self.drop_box.setStyleSheet("""
            QFrame {
                border: 2px dashed #4a5568;
                border-radius: 8px;
                background-color: #141824;
                padding: 16px;
            }
            QFrame:hover {
                border-color: #63b3ed;
                background-color: #1a202c;
            }
        """)
        drop_layout = QVBoxLayout(self.drop_box)
        lbl_drop = QLabel("📁 Przeciągnij i upuść pliki wideo (.mkv, .mp4) lub napisy (.ass, .srt)\nlub kliknij przycisk poniżej:")
        lbl_drop.setAlignment(Qt.AlignCenter)
        lbl_drop.setStyleSheet("color: #a0aec0; font-size: 13px;")
        drop_layout.addWidget(lbl_drop)

        h_file_btns = QHBoxLayout()
        btn_add_files = QPushButton("➕ Wybierz Pliki")
        btn_add_files.clicked.connect(self.browse_files)
        btn_add_folder = QPushButton("📁 Cały Folder (Sezon)")
        btn_add_folder.clicked.connect(self.browse_folder)
        btn_clear_queue = QPushButton("🗑️ Wyczyść")
        btn_clear_queue.clicked.connect(self.clear_queue)
        h_file_btns.addWidget(btn_add_files)
        h_file_btns.addWidget(btn_add_folder)
        h_file_btns.addWidget(btn_clear_queue)
        drop_layout.addLayout(h_file_btns)
        left_layout.addWidget(self.drop_box)

        # Tabela Kolejki Plików
        self.table_queue = QTableWidget()
        self.table_queue.setColumnCount(3)
        self.table_queue.setHorizontalHeaderLabels(["Plik Napisów", "Wideo", "Status"])
        self.table_queue.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_queue.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_queue.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_queue.setSelectionBehavior(QTableWidget.SelectRows)
        left_layout.addWidget(self.table_queue)

        # Wybór Jakości Tłumaczenia
        gb_profiles = QGroupBox("Profil Jakości Tłumaczenia")
        prof_layout = QVBoxLayout(gb_profiles)
        
        self.bg_profiles = QButtonGroup(self)
        self.rb_prof1 = QRadioButton("[1] Szybki (Free Tier) — 0,00 PLN (Model Flash-Lite)")
        self.rb_prof2 = QRadioButton("[2] Studyjny Flash — ~0,08 PLN / odc. (3-5 min, 43 Filary, Rekomendowany)")
        self.rb_prof3 = QRadioButton("[3] Master Pro — ~1,35 PLN / odc. (Flagowy Gemini 3.1 Pro Preview)")
        self.rb_prof2.setChecked(True)

        self.bg_profiles.addButton(self.rb_prof1, 1)
        self.bg_profiles.addButton(self.rb_prof2, 2)
        self.bg_profiles.addButton(self.rb_prof3, 3)

        prof_layout.addWidget(self.rb_prof1)
        prof_layout.addWidget(self.rb_prof2)
        prof_layout.addWidget(self.rb_prof3)
        left_layout.addWidget(gb_profiles)

        # Opcje dodatkowe
        gb_opts = QGroupBox("Opcje Zaawansowane")
        opts_layout = QHBoxLayout(gb_opts)
        self.chk_honorifics = QCheckBox("Zachowaj honoryfikatory (-kun, -chan, -san)")
        self.chk_honorifics.setChecked(True)
        self.chk_whisper = QCheckBox("Lokalny Whisper STT (Japońskie audio large-v3-turbo)")
        self.chk_whisper.setChecked(True)
        opts_layout.addWidget(self.chk_honorifics)
        opts_layout.addWidget(self.chk_whisper)
        left_layout.addWidget(gb_opts)

        splitter.addWidget(left_widget)

        # PRAWY PANEL (PODGLĄD NA ŻYWO I LOGI)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Karta Podglądu na żywo
        gb_live = QGroupBox("Podgląd Tłumaczenia na Żywo (Bilingual Live Stream)")
        live_layout = QVBoxLayout(gb_live)

        self.table_live = QTableWidget()
        self.table_live.setColumnCount(3)
        self.table_live.setHorizontalHeaderLabels(["ID", "Oryginał (EN / JP)", "Polski Przekład AVT"])
        self.table_live.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_live.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_live.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        live_layout.addWidget(self.table_live)
        right_layout.addWidget(gb_live)

        # Konsola Logów
        gb_logs = QGroupBox("Dziennik Zdarzeń (Logi)")
        logs_layout = QVBoxLayout(gb_logs)
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        logs_layout.addWidget(self.txt_logs)
        right_layout.addWidget(gb_logs)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        main_layout.addWidget(splitter)

        # 3. Dolny pasek postępu i przycisk START
        bottom_box = QFrame()
        bottom_box.setStyleSheet("background-color: #141824; border-radius: 8px; padding: 10px;")
        b_layout = QVBoxLayout(bottom_box)

        h_stats = QHBoxLayout()
        self.lbl_progress = QLabel("Gotowy do pracy.")
        self.lbl_progress.setStyleSheet("font-weight: bold; color: #90cdf4;")
        self.lbl_cost = QLabel("💰 Koszt tego odcinka: 0.00 PLN")
        self.lbl_cost.setStyleSheet("font-weight: bold; color: #48bb78; font-size: 14px;")
        h_stats.addWidget(self.lbl_progress)
        h_stats.addStretch()
        h_stats.addWidget(self.lbl_cost)
        b_layout.addLayout(h_stats)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        b_layout.addWidget(self.progress_bar)

        h_actions = QHBoxLayout()
        self.btn_start = QPushButton("▶ ROZPOCZNIJ TŁUMACZENIE")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_start.clicked.connect(self.start_translation)

        self.btn_stop = QPushButton("⏹ Przerwij")
        self.btn_stop.setObjectName("StopButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_translation)

        self.btn_open_folder = QPushButton("📂 Otwórz Folder Wynikowy")
        self.btn_open_folder.clicked.connect(self.open_output_folder)

        h_actions.addWidget(self.btn_start, 3)
        h_actions.addWidget(self.btn_stop, 1)
        h_actions.addWidget(self.btn_open_folder, 1)
        b_layout.addLayout(h_actions)

        main_layout.addWidget(bottom_box)

    # ─────────────────────────────────────────────────────────────────────────
    # OBSŁUGA DRAG & DROP
    # ─────────────────────────────────────────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.add_paths_to_queue(paths)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Wybierz pliki z napisami lub wideo",
            "",
            "Napisy i Wideo (*.ass *.srt *.mkv *.mp4);;Wszystkie pliki (*.*)"
        )
        if files:
            self.add_paths_to_queue(files)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder z serią")
        if folder:
            self.add_paths_to_queue([folder])

    def add_paths_to_queue(self, paths: List[str]):
        raw_files = collect_input_files(paths)
        if not raw_files:
            QMessageBox.information(self, "Informacja", "Nie znaleziono obsługiwanych plików napisów (.ass, .srt) ani wideo.")
            return

        added_count = 0
        for f in raw_files:
            vid, subs, _ = resolve_episode_files(f)
            if subs:
                item = {
                    "subs": str(subs),
                    "video": str(vid) if vid else None
                }
                if item not in self.files_queue:
                    self.files_queue.append(item)
                    added_count += 1

        self.refresh_queue_table()
        self.log(f"Dodano {added_count} elementów do kolejki.")

    def clear_queue(self):
        self.files_queue.clear()
        self.refresh_queue_table()
        self.log("Wyczyszczono kolejkę plików.")

    def refresh_queue_table(self):
        self.table_queue.setRowCount(len(self.files_queue))
        for r, it in enumerate(self.files_queue):
            subs_name = Path(it["subs"]).name
            video_name = Path(it["video"]).name if it.get("video") else "Brak (tryb tekstowy)"
            
            self.table_queue.setItem(r, 0, QTableWidgetItem(subs_name))
            self.table_queue.setItem(r, 1, QTableWidgetItem(video_name))
            self.table_queue.setItem(r, 2, QTableWidgetItem("Oczekuje"))

    # ─────────────────────────────────────────────────────────────────────────
    # LOGI I AKTUALIZACJA WIDOKU
    # ─────────────────────────────────────────────────────────────────────────
    def log(self, text: str):
        self.txt_logs.append(text)
        sb = self.txt_logs.verticalScrollBar()
        sb.setValue(sb.maximum())

    def update_pricing_banner(self):
        pass

    # ─────────────────────────────────────────────────────────────────────────
    # START / STOP TŁUMACZENIA
    # ─────────────────────────────────────────────────────────────────────────
    def start_translation(self):
        if not self.files_queue:
            QMessageBox.warning(self, "Pusta Kolejka", "Dodaj przynajmniej jeden plik napisów lub wideo!")
            return

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            QMessageBox.critical(self, "Brak Klucza", "Klucz GEMINI_API_KEY nie został skonfigurowany!\nOtwórz Ustawienia API i wklej swój klucz.")
            self.open_settings()
            return

        profile_id = str(self.bg_profiles.checkedId())
        keep_hon = self.chk_honorifics.isChecked()
        use_wh = self.chk_whisper.isChecked()
        wh_model = "large-v3-turbo"

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)
        self.start_time = time.time()

        self.worker = TranslationWorker(
            files_to_process=self.files_queue,
            profile_idx=profile_id,
            keep_honorifics=keep_hon,
            use_whisper=use_wh,
            whisper_model=wh_model
        )

        self.worker.progress_signal.connect(self.on_progress)
        self.worker.log_signal.connect(self.log)
        self.worker.file_finished_signal.connect(self.on_file_finished)
        self.worker.queue_finished_signal.connect(self.on_queue_finished)
        self.worker.error_signal.connect(self.on_error)

        self.worker.start()

    def stop_translation(self):
        if self.worker:
            self.worker.stop()
            self.btn_stop.setEnabled(False)
            self.log("Wysyłanie sygnału zatrzymania...")

    def on_progress(self, current: int, total: int, previews: list, cost_pln: float):
        pct = int((current / max(1, total)) * 100)
        self.progress_bar.setValue(pct)
        elapsed = time.time() - self.start_time
        
        self.lbl_progress.setText(f"Postęp: {current}/{total} kwestii ({pct}%) | Czas: {elapsed:.0f}s")
        self.lbl_cost.setText(f"💰 Rzeczywisty koszt: {cost_pln:.2f} PLN")

        # Dodanie kwestii do tabeli na żywo
        for item in previews:
            row = self.table_live.rowCount()
            self.table_live.insertRow(row)
            self.table_live.setItem(row, 0, QTableWidgetItem(str(item.get("id", row + 1))))
            self.table_live.setItem(row, 1, QTableWidgetItem(item.get("en", "")))
            self.table_live.setItem(row, 2, QTableWidgetItem(item.get("pl", "")))
        
        self.table_live.scrollToBottom()

    def on_file_finished(self, output_path: str, total_cost: float):
        self.log(f"✅ Zakończono plik: {Path(output_path).name} (Łączny koszt: {total_cost:.2f} PLN)")
        self.lbl_cost.setText(f"💰 Łączny koszt odcinka: {total_cost:.2f} PLN")

    def on_queue_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setValue(100)
        self.lbl_progress.setText("🎉 Wszystkie zadania zostały ukończone!")
        QMessageBox.information(self, "Gotowe", "Tłumaczenie całej kolejki zostało pomyślnie zakończone!")

    def on_error(self, err_msg: str):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.log(f"❌ {err_msg}")
        QMessageBox.critical(self, "Błąd Tłumaczenia", err_msg)

    # ─────────────────────────────────────────────────────────────────────────
    # FUNKCJE POMOCNICZE
    # ─────────────────────────────────────────────────────────────────────────
    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def open_series_bible(self):
        QMessageBox.information(
            self,
            "Biblia Serialu",
            "Pamięć międzyodcinkowa (Biblia Serialu) automatycznie synchronizuje postacie i słowniczek "
            "w plikach *.profile.json oraz bazie pamięci tłumaczeniowej."
        )

    def open_output_folder(self):
        if self.files_queue:
            target = Path(self.files_queue[0]["subs"]).parent
            os.startfile(str(target))
        else:
            os.startfile(os.getcwd())


# ─────────────────────────────────────────────────────────────────────────────
# GŁÓWNY PUNKT WEJŚCIA
# ─────────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(MODERN_DARK_STYLE)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
