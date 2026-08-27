# -*- coding: utf-8 -*-
"""
Desktop GUI Application for Anime Subtitle Translator (PySide6 / Qt 6).
Includes:
- Full integration with 43 AVT Pillars engine and Context Cache.
- Drag & Drop file and folder support.
- Asynchronous processing in background QThread (responsive UI).
- Live line-by-line translation monitor and real-time PLN cost tracker.
- Settings Panel (API Key, Whisper Japanese STT, Series Bible).
"""

import os
import sys
import warnings
import logging

# Silence Hugging Face Hub warnings, symlink notices, and benign messages
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")
warnings.filterwarnings("ignore", category=FutureWarning)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

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
    QComboBox, QGroupBox, QSplitter, QFrame, QScrollArea, QTabWidget,
    QMenu
)

# Load environment variables (.env)
from dotenv import load_dotenv, set_key
load_dotenv()

from translator import MultimodalTranslator as TranslatorEngine
from verifier import DialogueVerifier
from model_resolver import resolve_best_models
from pricing_guard import PricingGuard
from series_memory import SeriesBible
from main import collect_input_files, resolve_episode_files
from user_feedback import UserFeedbackManager
from glossary_manager import GlossaryManager

# ─────────────────────────────────────────────────────────────────────────────
# MODERN DARK FLUENT DESIGN STYLESHEET (QSS)
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
# TRANSLATION WORKER THREAD (QThread)
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

            # Dynamic model resolution
            models = resolve_best_models()
            thinking_budget = 4096
            if self.profile_idx == "1":
                p1_model = models["flash_lite"]
                p2_model = None
                enable_verifier = False
            elif self.profile_idx == "2":
                p1_model = models["flash"]
                p2_model = None
                enable_verifier = False
            elif self.profile_idx == "4":
                p1_model = models["flash"]
                p2_model = models["pro"]
                enable_verifier = True
                thinking_budget = 2048
            else:  # Profile 3 (Mistrzowski Flash Reasoning Adaptive CoT do 6144 - Domyślny)
                p1_model = models["flash"]
                p2_model = models["flash"]
                enable_verifier = True
                thinking_budget = 6144

            self.log_signal.emit(f"🚀 Inicjalizacja silnika: Faza 1 ({p1_model})" + (f" -> Faza 2 ({p2_model} CoT {thinking_budget})" if enable_verifier else ""))

            engine = TranslatorEngine(
                api_key=api_key,
                model=p1_model,
                model_phase2=p2_model,
                enable_verifier=enable_verifier,
                keep_honorifics=self.keep_honorifics,
                use_whisper=self.use_whisper,
                whisper_model_size=self.whisper_model,
                thinking_budget_phase2=thinking_budget
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
                    progress_callback=progress_bridge,
                    cancel_check=lambda: not self.is_running
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
# SETTINGS DIALOG (SettingsDialog)
# ─────────────────────────────────────────────────────────────────────────────
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Ustawienia Tłumacza i Klucza API")
        self.resize(550, 360)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Google API Key
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

        # European Vertex AI Settings
        gb_vertex = QGroupBox("🇪🇺 Europejskie Klastry Google (Vertex AI Enterprise — Ominięcie Kolejek)")
        vx_layout = QVBoxLayout(gb_vertex)
        
        self.chk_use_vertex = QCheckBox("Włącz europejski region Vertex AI (europe-west1 / Belgia — bez przeciążeń 503)")
        self.chk_use_vertex.setChecked(os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in ["1", "true", "yes"])
        self.chk_use_vertex.toggled.connect(self.on_vertex_toggled)
        vx_layout.addWidget(self.chk_use_vertex)

        lbl_proj_info = QLabel("ID Projektu Google Cloud (znajdziesz w Google AI Studio w kolumnie 'Project' lub console.cloud.google.com):")
        lbl_proj_info.setStyleSheet("color: #a0aec0; font-size: 11px;")
        vx_layout.addWidget(lbl_proj_info)

        self.txt_project_id = QLineEdit()
        self.txt_project_id.setPlaceholderText("np. my-gcp-project-12345 lub gen-lang-client-...")
        self.txt_project_id.setText(os.environ.get("GOOGLE_CLOUD_PROJECT", ""))
        self.txt_project_id.setEnabled(self.chk_use_vertex.isChecked())
        vx_layout.addWidget(self.txt_project_id)

        h_loc = QHBoxLayout()
        lbl_loc = QLabel("Region Datacenter:")
        self.cb_location = QComboBox()
        self.cb_location.addItems([
            "europe-west1 (Belgia / Najniższe opóźnienia PL)",
            "europe-west4 (Holandia)",
            "europe-west3 (Frankfurt)"
        ])
        cur_loc = os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west1")
        for idx in range(self.cb_location.count()):
            if cur_loc in self.cb_location.itemText(idx):
                self.cb_location.setCurrentIndex(idx)
                break
        self.cb_location.setEnabled(self.chk_use_vertex.isChecked())
        h_loc.addWidget(lbl_loc)
        h_loc.addWidget(self.cb_location)
        vx_layout.addLayout(h_loc)

        layout.addWidget(gb_vertex)

        # Whisper settings
        gb_whisper = QGroupBox("Lokalny Japoński Whisper STT")
        wh_layout = QVBoxLayout(gb_whisper)
        lbl_wh = QLabel("Domyślny model transkrypcji audio ze słuchu:")
        wh_layout.addWidget(lbl_wh)

        self.cb_whisper_model = QComboBox()
        self.cb_whisper_model.addItems([
            "kotoba-tech/kotoba-whisper-v2.0-faster (Zalecany / Japoński SOTA ASR)",
            "large-v3-turbo (Wielojęzyczny Fast)",
            "large-v3",
            "medium",
            "small"
        ])
        wh_layout.addWidget(self.cb_whisper_model)
        layout.addWidget(gb_whisper)

        # Save / Cancel buttons
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

    def on_vertex_toggled(self, checked: bool):
        self.txt_project_id.setEnabled(checked)
        self.cb_location.setEnabled(checked)

    def toggle_echo(self):
        if self.txt_api_key.echoMode() == QLineEdit.Password:
            self.txt_api_key.setEchoMode(QLineEdit.Normal)
            self.btn_show_key.setText("🔒 Ukryj")
        else:
            self.txt_api_key.setEchoMode(QLineEdit.Password)
            self.btn_show_key.setText("👁 Pokaż")

    def test_api_connection(self):
        key = self.txt_api_key.text().strip()
        use_vx = self.chk_use_vertex.isChecked()
        proj = self.txt_project_id.text().strip()
        loc_str = self.cb_location.currentText().split()[0]

        if not key:
            QMessageBox.warning(self, "Błąd", "Wprowadź klucz API przed testem!")
            return
        if use_vx and not proj:
            QMessageBox.warning(self, "Błąd Vertex AI", "Podaj ID Projektu Google Cloud przed testem Vertex AI!")
            return

        try:
            from client_factory import get_genai_client
            # Temporarily set env for testing
            os.environ["GEMINI_API_KEY"] = key
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1" if use_vx else "0"
            os.environ["GOOGLE_CLOUD_PROJECT"] = proj
            os.environ["GOOGLE_CLOUD_LOCATION"] = loc_str

            client = get_genai_client(api_key=key, timeout_ms=15000)
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Test PING"
            )
            mode_desc = f"Europejski Vertex AI ({loc_str})" if use_vx else "Google AI Studio"
            QMessageBox.information(self, "Sukces", f"Połączenie nawiązane pomyślnie!\nTryb: {mode_desc}\nOdpowiedź: {res.text.strip()}")
        except Exception as e:
            QMessageBox.critical(self, "Błąd Połączenia", f"Nie udało się połączyć z API:\n{str(e)}")

    def save_settings(self):
        key = self.txt_api_key.text().strip()
        use_vx = "1" if self.chk_use_vertex.isChecked() else "0"
        proj = self.txt_project_id.text().strip()
        loc_str = self.cb_location.currentText().split()[0]

        env_path = Path(__file__).parent / ".env"
        os.environ["GEMINI_API_KEY"] = key
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = use_vx
        os.environ["GOOGLE_CLOUD_PROJECT"] = proj
        os.environ["GOOGLE_CLOUD_LOCATION"] = loc_str

        set_key(str(env_path), "GEMINI_API_KEY", key)
        set_key(str(env_path), "GOOGLE_GENAI_USE_VERTEXAI", use_vx)
        set_key(str(env_path), "GOOGLE_CLOUD_PROJECT", proj)
        set_key(str(env_path), "GOOGLE_CLOUD_LOCATION", loc_str)

        QMessageBox.information(self, "Zapisano", "Ustawienia zostały pomyślnie zapisane!")
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# USER CORRECTION & INTERACTIVE LEARNING DIALOG (UserCorrectionDialog)
# ─────────────────────────────────────────────────────────────────────────────
class UserCorrectionDialog(QDialog):
    def __init__(self, orig_en: str, cur_pl: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✍️ Korekta Kwestii i Uczenie AI")
        self.resize(600, 420)
        self.orig_en = orig_en
        self.cur_pl = cur_pl
        self.result_pl = cur_pl
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Original EN
        lbl_en = QLabel("Oryginał angielski / japoński:")
        lbl_en.setStyleSheet("color: #a0aec0; font-weight: bold;")
        layout.addWidget(lbl_en)
        self.txt_orig = QLineEdit(self.orig_en)
        self.txt_orig.setReadOnly(True)
        layout.addWidget(self.txt_orig)

        # Initial draft translation
        lbl_bad = QLabel("Wersja pierwotna AI (do poprawy):")
        lbl_bad.setStyleSheet("color: #fc8181; font-weight: bold;")
        layout.addWidget(lbl_bad)
        self.txt_bad = QLineEdit(self.cur_pl)
        layout.addWidget(self.txt_bad)

        # Correct translation
        lbl_good = QLabel("Twoja poprawna wersja (jak powinno brzmieć po polsku):")
        lbl_good.setStyleSheet("color: #68d391; font-weight: bold;")
        layout.addWidget(lbl_good)
        self.txt_good = QLineEdit(self.cur_pl)
        layout.addWidget(self.txt_good)

        # Rule rationale
        lbl_reason = QLabel("Uzasadnienie / Zasada (dla promptu AI):")
        lbl_reason.setStyleSheet("color: #90cdf4; font-weight: bold;")
        layout.addWidget(lbl_reason)
        self.txt_reason = QLineEdit("Unikaj dosłowności, stosuj naturalną polszczyznę mówioną")
        layout.addWidget(self.txt_reason)

        # Storage options
        gb_opts = QGroupBox("Opcje Zapamiętywania")
        opts_layout = QVBoxLayout(gb_opts)
        self.chk_save_rule = QCheckBox("🧠 Zapisz jako Złotą Regułę AI (Few-Shot Prompting w kolejnych tłumaczeniach)")
        self.chk_save_rule.setChecked(True)
        self.chk_save_glossary = QCheckBox("📖 Zapisz do Słownika Deterministycznego (twarde wymuszenie słowa)")
        opts_layout.addWidget(self.chk_save_rule)
        opts_layout.addWidget(self.chk_save_glossary)
        layout.addWidget(gb_opts)

        # Action buttons
        h_btns = QHBoxLayout()
        h_btns.addStretch()
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("💾 Zastosuj Korektę")
        btn_save.setObjectName("PrimaryButton")
        btn_save.clicked.connect(self.apply_correction)
        h_btns.addWidget(btn_cancel)
        h_btns.addWidget(btn_save)
        layout.addLayout(h_btns)

    def apply_correction(self):
        good_text = self.txt_good.text().strip()
        bad_text = self.txt_bad.text().strip()
        reason = self.txt_reason.text().strip()
        orig = self.txt_orig.text().strip()

        if not good_text:
            QMessageBox.warning(self, "Błąd", "Wprowadź poprawioną wersję tekstu!")
            return

        self.result_pl = good_text

        # 1. Save to UserFeedbackManager
        if self.chk_save_rule.isChecked():
            try:
                fb_mgr = UserFeedbackManager()
                fb_mgr.add_feedback(
                    original_en=orig,
                    bad_pl=bad_text,
                    good_pl=good_text,
                    rule_reason=reason,
                    scope="global"
                )
            except Exception as e:
                print(f"[Błąd zapisu reguły]: {e}")

        # 2. Save to GlossaryManager
        if self.chk_save_glossary.isChecked() and orig:
            try:
                gloss_mgr = GlossaryManager()
                gloss_mgr.add_term(src=orig, pl=good_text, desc=reason)
            except Exception as e:
                print(f"[Błąd zapisu słownika]: {e}")

        QMessageBox.information(
            self,
            "Zapisano",
            "Korekta została pomyślnie zastosowana i zapamiętana w bazie reguł!"
        )
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# RULES & DETERMINISTIC GLOSSARY MANAGER DIALOG (RulesAndGlossaryDialog)
# ─────────────────────────────────────────────────────────────────────────────
class RulesAndGlossaryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🧠 Baza Reguł Użytkownika i Słownik Deterministyczny")
        self.resize(850, 520)
        self.fb_mgr = UserFeedbackManager()
        self.gloss_mgr = GlossaryManager()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()

        # TAB 1: User Golden Examples (Few-Shot)
        tab_rules = QWidget()
        rules_layout = QVBoxLayout(tab_rules)
        
        lbl_rules_info = QLabel("Złote Wzorce są wstrzykiwane z najwyższym priorytetem do promptu LLM (Few-Shot Learning):")
        lbl_rules_info.setStyleSheet("color: #a0aec0;")
        rules_layout.addWidget(lbl_rules_info)

        self.table_rules = QTableWidget()
        self.table_rules.setColumnCount(4)
        self.table_rules.setHorizontalHeaderLabels(["Oryginał EN", "Błąd [X]", "Poprawne [OK]", "Uzasadnienie"])
        self.table_rules.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_rules.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_rules.setSelectionBehavior(QTableWidget.SelectRows)
        rules_layout.addWidget(self.table_rules)

        h_rule_btns = QHBoxLayout()
        btn_add_rule = QPushButton("➕ Dodaj Regułę")
        btn_add_rule.clicked.connect(self.add_manual_rule)
        btn_del_rule = QPushButton("🗑️ Usuń Wybraną")
        btn_del_rule.clicked.connect(self.delete_selected_rule)
        h_rule_btns.addWidget(btn_add_rule)
        h_rule_btns.addWidget(btn_del_rule)
        h_rule_btns.addStretch()
        rules_layout.addLayout(h_rule_btns)
        self.tabs.addTab(tab_rules, "🧠 Złote Wzorce (Few-Shot)")

        # TAB 2: Deterministic Glossary
        tab_gloss = QWidget()
        gloss_layout = QVBoxLayout(tab_gloss)

        lbl_gloss_info = QLabel("Pojęcia ze słownika są deterministycznie wymuszane w post-processingu (100% gwarancji):")
        lbl_gloss_info.setStyleSheet("color: #a0aec0;")
        gloss_layout.addWidget(lbl_gloss_info)

        self.table_gloss = QTableWidget()
        self.table_gloss.setColumnCount(3)
        self.table_gloss.setHorizontalHeaderLabels(["Pojęcie Źródłowe", "Wymagane Tłumaczenie PL", "Opis / Rola"])
        self.table_gloss.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_gloss.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_gloss.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_gloss.setSelectionBehavior(QTableWidget.SelectRows)
        gloss_layout.addWidget(self.table_gloss)

        h_gloss_btns = QHBoxLayout()
        btn_add_term = QPushButton("➕ Dodaj Termin")
        btn_add_term.clicked.connect(self.add_manual_term)
        btn_del_term = QPushButton("🗑️ Usuń Wybrany")
        btn_del_term.clicked.connect(self.delete_selected_term)
        h_gloss_btns.addWidget(btn_add_term)
        h_gloss_btns.addWidget(btn_del_term)
        h_gloss_btns.addStretch()
        gloss_layout.addLayout(h_gloss_btns)
        self.tabs.addTab(tab_gloss, "📖 Słownik Deterministyczny")

        # TAB 3: Side-by-Side Reviewer & Quick Learn
        tab_review = QWidget()
        review_layout = QVBoxLayout(tab_review)

        lbl_rev_info = QLabel("Wczytaj przetłumaczony plik (.ass/.srt), aby przejrzeć kwestie i jednym kliknięciem uczyć model (1-Click Learn):")
        lbl_rev_info.setStyleSheet("color: #a0aec0;")
        review_layout.addWidget(lbl_rev_info)

        h_rev_top = QHBoxLayout()
        btn_load_sub = QPushButton("📂 Wczytaj Napisy do Przeglądu")
        btn_load_sub.clicked.connect(self.load_subtitles_for_review)
        self.lbl_loaded_file = QLabel("Brak wczytanego pliku")
        self.lbl_loaded_file.setStyleSheet("color: #63b3ed; font-style: italic;")
        h_rev_top.addWidget(btn_load_sub)
        h_rev_top.addWidget(self.lbl_loaded_file)
        h_rev_top.addStretch()
        review_layout.addLayout(h_rev_top)

        self.table_review = QTableWidget()
        self.table_review.setColumnCount(3)
        self.table_review.setHorizontalHeaderLabels(["ID / Czas", "Tekst Oryginalny / Kwestia", "Polski Przekład"])
        self.table_review.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_review.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_review.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_review.setSelectionBehavior(QTableWidget.SelectRows)
        review_layout.addWidget(self.table_review)

        h_rev_actions = QHBoxLayout()
        btn_learn_from_rev = QPushButton("⚡ 1-Click Learn (Zapamiętaj regułę z zaznaczonej kwestii)")
        btn_learn_from_rev.setObjectName("PrimaryButton")
        btn_learn_from_rev.clicked.connect(self.learn_from_selected_review_line)
        h_rev_actions.addWidget(btn_learn_from_rev)
        h_rev_actions.addStretch()
        review_layout.addLayout(h_rev_actions)

        self.tabs.addTab(tab_review, "🔍 Porównywarka i Szlif (Side-by-Side)")

        layout.addWidget(self.tabs)

        # Close button
        h_bottom = QHBoxLayout()
        h_bottom.addStretch()
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        h_bottom.addWidget(btn_close)
        layout.addLayout(h_bottom)

        self.refresh_rules_table()
        self.refresh_glossary_table()

    def load_subtitles_for_review(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik napisów", "", "Napisy (*.ass *.srt)")
        if not file_path:
            return
        try:
            import pysubs2
            subs = pysubs2.load(file_path)
            self.lbl_loaded_file.setText(os.path.basename(file_path))
            self.table_review.setRowCount(len(subs))
            for idx, ev in enumerate(subs):
                start_m, start_s = divmod(ev.start // 1000, 60)
                time_str = f"#{idx+1} ({start_m:02d}:{start_s:02d})"
                clean_text = ev.text.replace(r"\N", " ").replace(r"\n", " ").strip()
                self.table_review.setItem(idx, 0, QTableWidgetItem(time_str))
                self.table_review.setItem(idx, 1, QTableWidgetItem(clean_text))
                self.table_review.setItem(idx, 2, QTableWidgetItem(clean_text))
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się wczytać pliku: {e}")

    def learn_from_selected_review_line(self):
        row = self.table_review.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Wybór", "Zaznacz kwestię z tabeli!")
            return
        orig_item = self.table_review.item(row, 1)
        trans_item = self.table_review.item(row, 2)
        orig_text = orig_item.text() if orig_item else ""
        trans_text = trans_item.text() if trans_item else ""
        dlg = UserCorrectionDialog(orig_text, trans_text, self)
        if dlg.exec():
            self.refresh_rules_table()
            self.refresh_glossary_table()

    def refresh_rules_table(self):
        self.fb_mgr.load()
        items = self.fb_mgr.list_all()
        self.table_rules.setRowCount(len(items))
        for r_idx, item in enumerate(items):
            self.table_rules.setItem(r_idx, 0, QTableWidgetItem(item.get("original_en", "")))
            self.table_rules.setItem(r_idx, 1, QTableWidgetItem(item.get("bad_pl", "")))
            self.table_rules.setItem(r_idx, 2, QTableWidgetItem(item.get("good_pl", "")))
            self.table_rules.setItem(r_idx, 3, QTableWidgetItem(item.get("rule_reason", "")))

    def refresh_glossary_table(self):
        self.gloss_mgr.load()
        terms = self.gloss_mgr.global_terms
        self.table_gloss.setRowCount(len(terms))
        for r_idx, (src, info) in enumerate(terms.items()):
            pl = info.get("pl", "") if isinstance(info, dict) else str(info)
            desc = info.get("desc", "") if isinstance(info, dict) else ""
            self.table_gloss.setItem(r_idx, 0, QTableWidgetItem(src))
            self.table_gloss.setItem(r_idx, 1, QTableWidgetItem(pl))
            self.table_gloss.setItem(r_idx, 2, QTableWidgetItem(desc))

    def add_manual_rule(self):
        dlg = UserCorrectionDialog("", "", self)
        if dlg.exec():
            self.refresh_rules_table()

    def delete_selected_rule(self):
        row = self.table_rules.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Wybór", "Zaznacz regułę do usunięcia!")
            return
        items = self.fb_mgr.list_all()
        if row < len(items):
            item_id = items[row].get("id")
            if item_id:
                self.fb_mgr.remove_feedback(item_id)
                self.refresh_rules_table()

    def add_manual_term(self):
        src, ok1 = QInputDialog_getText(self, "Nowy Termin", "Pojęcie źródłowe (np. angielskie/japońskie):")
        if ok1 and src.strip():
            pl, ok2 = QInputDialog_getText(self, "Tłumaczenie PL", f"Polskie tłumaczenie dla '{src}':")
            if ok2 and pl.strip():
                self.gloss_mgr.add_term(src.strip(), pl.strip())
                self.refresh_glossary_table()

    def delete_selected_term(self):
        row = self.table_gloss.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Wybór", "Zaznacz termin do usunięcia!")
            return
        src_item = self.table_gloss.item(row, 0)
        if src_item:
            self.gloss_mgr.remove_term(src_item.text())
            self.refresh_glossary_table()


def QInputDialog_getText(parent, title, label):
    """Simple text prompt dialog replacing QInputDialog."""
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.resize(400, 150)
    layout = QVBoxLayout(dlg)
    layout.addWidget(QLabel(label))
    txt = QLineEdit()
    layout.addWidget(txt)
    h_b = QHBoxLayout()
    btn_ok = QPushButton("OK")
    btn_ok.setObjectName("PrimaryButton")
    btn_ok.clicked.connect(dlg.accept)
    btn_c = QPushButton("Anuluj")
    btn_c.clicked.connect(dlg.reject)
    h_b.addStretch()
    h_b.addWidget(btn_c)
    h_b.addWidget(btn_ok)
    layout.addLayout(h_b)
    res = dlg.exec()
    return txt.text(), res == QDialog.Accepted


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APPLICATION WINDOW (MainWindow)
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

        # 1. Top header and navigation
        h_header = QHBoxLayout()
        lbl_title = QLabel("🎬 ANIME SUBTITLE TRANSLATOR PRO")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #63b3ed;")
        h_header.addWidget(lbl_title)

        h_header.addStretch()
        btn_rules = QPushButton("🧠 Reguły i Słownik")
        btn_rules.clicked.connect(self.open_rules_manager)
        btn_settings = QPushButton("⚙️ Ustawienia API")
        btn_settings.clicked.connect(self.open_settings)
        btn_bible = QPushButton("📚 Biblia Serialu")
        btn_bible.clicked.connect(self.open_series_bible)
        h_header.addWidget(btn_rules)
        h_header.addWidget(btn_bible)
        h_header.addWidget(btn_settings)
        main_layout.addLayout(h_header)

        # 2. Main splitter (Left: Files & Settings | Right: Live Monitor & Logs)
        splitter = QSplitter(Qt.Horizontal)

        # LEFT PANEL
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Drag & Drop Zone
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

        # File Queue Table
        self.table_queue = QTableWidget()
        self.table_queue.setColumnCount(3)
        self.table_queue.setHorizontalHeaderLabels(["Plik Napisów", "Wideo", "Status"])
        self.table_queue.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_queue.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_queue.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_queue.setSelectionBehavior(QTableWidget.SelectRows)
        left_layout.addWidget(self.table_queue)

        # Translation Quality Profile Selection
        gb_profiles = QGroupBox("Profil Jakości Tłumaczenia")
        prof_layout = QVBoxLayout(gb_profiles)
        
        self.bg_profiles = QButtonGroup(self)
        self.rb_prof1 = QRadioButton("[1] Szybki (Free Tier) — 0,00 PLN (Model Flash-Lite, bez Fazy 2)")
        self.rb_prof2 = QRadioButton("[2] Studyjny Flash — ~1,07 PLN / odc. (Szkic Flash, bez Fazy 2)")
        self.rb_prof3 = QRadioButton("[3] Mistrzowski Flash Reasoning ⭐ — ~2,30 PLN / odc. (ZALECANY: Faza 1 Flash + Faza 2 Flash z Adaptive CoT do 6144)")
        self.rb_prof4 = QRadioButton("[4] Kinowy Pro 👑 — ~3,80 PLN / odc. (Maksymalna Głębia: Faza 1 Flash + Faza 2 Gemini 3.1 Pro z Adaptacyjnym CoT)")
        self.rb_prof3.setChecked(True)

        self.bg_profiles.addButton(self.rb_prof1, 1)
        self.bg_profiles.addButton(self.rb_prof2, 2)
        self.bg_profiles.addButton(self.rb_prof3, 3)
        self.bg_profiles.addButton(self.rb_prof4, 4)

        prof_layout.addWidget(self.rb_prof1)
        prof_layout.addWidget(self.rb_prof2)
        prof_layout.addWidget(self.rb_prof3)
        prof_layout.addWidget(self.rb_prof4)
        left_layout.addWidget(gb_profiles)

        # Additional Options
        gb_opts = QGroupBox("Opcje Zaawansowane")
        opts_layout = QHBoxLayout(gb_opts)
        self.chk_honorifics = QCheckBox("Zachowaj honoryfikatory (-kun, -chan, -san)")
        self.chk_honorifics.setChecked(True)
        self.chk_whisper = QCheckBox("Lokalny Whisper STT (Japoński Kotoba-Whisper v2.0 SOTA)")
        self.chk_whisper.setChecked(True)
        opts_layout.addWidget(self.chk_honorifics)
        opts_layout.addWidget(self.chk_whisper)
        left_layout.addWidget(gb_opts)

        splitter.addWidget(left_widget)

        # RIGHT PANEL (LIVE STREAM MONITOR & LOGS)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Live Bilingual Stream Card
        gb_live = QGroupBox("Podgląd Tłumaczenia na Żywo (Bilingual Live Stream)")
        live_layout = QVBoxLayout(gb_live)

        self.table_live = QTableWidget()
        self.table_live.setColumnCount(3)
        self.table_live.setHorizontalHeaderLabels(["ID", "Oryginał (EN / JP)", "Polski Przekład AVT"])
        self.table_live.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_live.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_live.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_live.cellDoubleClicked.connect(self.on_live_cell_double_clicked)
        self.table_live.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_live.customContextMenuRequested.connect(self.on_live_table_context_menu)
        live_layout.addWidget(self.table_live)

        h_live_btns = QHBoxLayout()
        btn_edit_line = QPushButton("✍️ Popraw kwestię...")
        btn_edit_line.clicked.connect(self.edit_selected_live_line)
        
        btn_quick_learn = QPushButton("⚡ 1-Click Learn (Zapamiętaj regułę)")
        btn_quick_learn.setStyleSheet("background-color: #2b6cb0; color: white; font-weight: bold;")
        btn_quick_learn.clicked.connect(self.quick_learn_selected_line)

        btn_play_scene = QPushButton("🎬 Odtwórz scenę w wideo")
        btn_play_scene.clicked.connect(self.play_selected_scene)

        h_live_btns.addWidget(btn_edit_line)
        h_live_btns.addWidget(btn_quick_learn)
        h_live_btns.addWidget(btn_play_scene)
        h_live_btns.addStretch()
        live_layout.addLayout(h_live_btns)

        right_layout.addWidget(gb_live)

        # Logs Console
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

        # 3. Bottom progress bar and START actions
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
    # DRAG & DROP HANDLERS
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
    # LOGGING AND UI UPDATES
    # ─────────────────────────────────────────────────────────────────────────
    def log(self, text: str):
        self.txt_logs.append(text)
        sb = self.txt_logs.verticalScrollBar()
        sb.setValue(sb.maximum())

    def update_pricing_banner(self):
        pass

    # ─────────────────────────────────────────────────────────────────────────
    # TRANSLATION LIFECYCLE (START / STOP)
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

        # Add lines to live table monitor
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
    # HELPER AND INTERACTION METHODS
    # ─────────────────────────────────────────────────────────────────────────
    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def open_rules_manager(self):
        dlg = RulesAndGlossaryDialog(self)
        dlg.exec()

    def on_live_cell_double_clicked(self, row: int, column: int):
        self._open_correction_for_row(row)

    def on_live_table_context_menu(self, pos):
        row = self.table_live.rowAt(pos.y())
        if row < 0:
            return
        self.table_live.selectRow(row)

        menu = QMenu(self)
        act_edit = menu.addAction("✍️ Popraw i utwórz regułę...")
        act_quick = menu.addAction("⚡ 1-Click Learn (Błyskawiczne uczenie)")
        act_play = menu.addAction("🎬 Odtwórz tę scenę w wideo")

        action = menu.exec(self.table_live.viewport().mapToGlobal(pos))
        if action == act_edit:
            self._open_correction_for_row(row)
        elif action == act_quick:
            self.quick_learn_selected_line()
        elif action == act_play:
            self.play_selected_scene()

    def quick_learn_selected_line(self):
        row = self.table_live.currentRow()
        if row < 0 or row >= self.table_live.rowCount():
            QMessageBox.warning(self, "Wybór", "Zaznacz w tabeli kwestię, z której chcesz utworzyć regułę uczenia!")
            return

        orig_en = self.table_live.item(row, 1).text() if self.table_live.item(row, 1) else ""
        cur_pl = self.table_live.item(row, 2).text() if self.table_live.item(row, 2) else ""

        if not orig_en or not cur_pl:
            return

        try:
            from user_feedback import UserFeedbackManager
            from glossary_manager import GlossaryManager

            fb = UserFeedbackManager()
            fb.add_feedback(
                original_en=orig_en,
                bad_pl=orig_en,
                good_pl=cur_pl,
                rule_reason=f"Żelazne tłumaczenie kwestii: '{orig_en}' -> '{cur_pl}'"
            )

            # If phrase is short (1-3 words), also add to deterministic glossary
            if len(orig_en.split()) <= 3:
                gm = GlossaryManager()
                gm.add_term(src=orig_en, pl=cur_pl, desc="Reguła 1-Click z GUI")

            self.log(f"⚡ [1-Click Learn] Zapisano złotą regułę: '{orig_en}' => '{cur_pl}'")
            QMessageBox.information(
                self,
                "Zapisano Regułę",
                f"Pomyślnie zapisano regułę uczenia AI:\n\n'{orig_en}' ➔ '{cur_pl}'\n\nBędzie ona automatycznie egzekwowana we wszystkich kolejnych odcinkach!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać reguły: {e}")

    def play_selected_scene(self):
        row = self.table_live.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Wybór", "Zaznacz kwestię w tabeli, którą chcesz odtworzyć!")
            return

        video_path = None
        if self.files_queue:
            video_path = self.files_queue[0].get("video")

        if not video_path or not os.path.exists(video_path):
            QMessageBox.information(self, "Brak wideo", "Brak powiązanego pliku wideo dla tej sesji tłumaczenia.")
            return

        try:
            # Launch system default video player
            os.startfile(str(video_path))
            self.log(f"🎬 Uruchomiono odtwarzacz wideo: {Path(video_path).name}")
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie udało się otworzyć wideo: {e}")

    def edit_selected_live_line(self):
        row = self.table_live.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Wybór", "Kliknij dwukrotnie lub zaznacz kwestię w tabeli, którą chcesz poprawić!")
            return
        self._open_correction_for_row(row)

    def _open_correction_for_row(self, row: int):
        if row < 0 or row >= self.table_live.rowCount():
            return
        orig_en = self.table_live.item(row, 1).text() if self.table_live.item(row, 1) else ""
        cur_pl = self.table_live.item(row, 2).text() if self.table_live.item(row, 2) else ""
        dlg = UserCorrectionDialog(orig_en=orig_en, cur_pl=cur_pl, parent=self)
        if dlg.exec():
            new_pl = dlg.result_pl
            self.table_live.setItem(row, 2, QTableWidgetItem(new_pl))
            self.log(f"✍️ Zastosowano korektę w linijce #{row + 1}: '{new_pl}'")

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

    def closeEvent(self, event):
        """Clean up server-side Context Cache upon closing the GUI."""
        try:
            from context_cache import ContextCacheManager
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                client = genai.Client(api_key=api_key)
                ContextCacheManager.cleanup_all_active_caches(client)
        except Exception:
            pass
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
# APPLICATION ENTRY POINT
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
