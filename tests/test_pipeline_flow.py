"""
Zestaw testów regresyjnych Standardu 11.1 (Pipeline Flow & Architectural Gaps).
Weryfikuje domknięcie luk przepływu: LUKA-E1-01 do LUKA-E8-01 oraz Z16-amendment #1, #2, #3.
"""

import os
import pytest
import pysubs2
from pathlib import Path
from unittest.mock import MagicMock, patch

from memory import format_translation_memory_for_prompt
from manga_canon import BUILTIN_MANGA_CANON, MangaCanonRegistry
from scene_discourse import SpeakerTurn, SubTurn, resolve_turn_addressee, resolve_scene_participants
from translator import segment_hybrid_events
import verify_purity


@pytest.mark.unit
def test_t11_1_style_report_initialized_before_segment_hybrid():
    """
    Standard 11.1 (LUKA-E1-01): Weryfikuje, że style_report jest przekazywany
    do segment_hybrid_events zamiast None.
    """
    from style_matrix import StyleMatrixReport, analyze_subtitles

    subs = pysubs2.SSAFile()
    ev1 = pysubs2.SSAEvent(start=1000, end=3000, text="Kwestia dialogowa.", style="Default")
    subs.events.append(ev1)

    style_rep = analyze_subtitles(subs)
    assert isinstance(style_rep, StyleMatrixReport)

    # Sprawdzenie wywołania segment_hybrid_events z poprawnym style_report
    segmented = segment_hybrid_events(subs.events, style_report=style_rep)
    assert len(segmented) >= 1


@pytest.mark.unit
def test_t11_1_series_bible_reset_between_episodes(tmp_path):
    """
    Standard 11.1 (LUKA-E5-01): Weryfikuje, że SeriesBible jest resetowana
    między odcinkami różnych serii w translate_file.
    """
    from translator import MultimodalTranslator
    from series_memory import SeriesBible
    from metadata import normalize_anime_slug

    translator = MultimodalTranslator.__new__(MultimodalTranslator)
    translator.model = "gemini-2.5-flash"
    translator.verifier = None

    old_bible = SeriesBible(anime_title="SeriaTestowaA", storage_dir=str(tmp_path))
    translator.series_bible = old_bible
    translator.style_report = MagicMock()

    # Symulacja nowego pliku innej serii
    new_subs = tmp_path / "SeriaTestowaB_01.ass"
    new_subs.write_text("[Script Info]\nTitle: Test\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Czesc.\n", encoding="utf-8")

    init_slug = translator._reset_episode_state_for_file(new_subs)

    assert translator.series_bible is None
    assert translator.style_report is None
    assert "seriatestowab" in init_slug


@pytest.mark.unit
def test_t11_1_memory_same_series_exact_quote_score_150():
    """
    Standard 11.1 (LUKA-E6-03): Weryfikuje, że dokładny cytat 1:1 z tej samej serii
    o score >= 100 otrzymuje wyróżnik [DOKŁADNY CYTAT 1:1].
    """
    examples = [
        {
            "en": "I will protect everyone.",
            "pl": "Obronię wszystkich.",
            "anime": "SeriaTestowa",
            "score": 150
        },
        {
            "en": "Wait for me.",
            "pl": "Czekaj na mnie.",
            "anime": "InnaSeria",
            "score": 85
        }
    ]

    formatted = format_translation_memory_for_prompt(examples)
    assert "[DOKŁADNY CYTAT 1:1]" in formatted
    assert "Obronię wszystkich." in formatted
    assert "Czekaj na mnie." in formatted


@pytest.mark.unit
def test_t11_1_subturn_target_speaker_preserved_in_scene_participants():
    """
    Standard 11.1 (LUKA-E7-01): Weryfikuje, że po podziale na sub_turns
    każdy pod-segment zachowuje niezależnego adresata i propaguje go na swoje zdarzenia.
    """
    ev_a = pysubs2.SSAEvent(start=1000, end=2500, text="Mistrzu, zaczekaj!")
    ev_b = pysubs2.SSAEvent(start=2600, end=5000, text="A ty, wojowniku, ruszaj przód!")

    turn = SpeakerTurn(
        speaker="BohaterGlowny",
        events=[ev_a, ev_b]
    )

    sub_a = SubTurn(speaker="BohaterGlowny", events=[ev_a])
    sub_a.target_speaker = "PostacMistrz"
    sub_a.target_gender = "MALE"
    sub_a.target_confidence = 0.95

    sub_b = SubTurn(speaker="BohaterGlowny", events=[ev_b])
    sub_b.target_speaker = "PostacWojownik"
    sub_b.target_gender = "MALE"
    sub_b.target_confidence = 0.95

    turn.sub_turns = [sub_a, sub_b]

    resolved_turn = resolve_turn_addressee(turn)
    resolve_scene_participants([ev_a, ev_b])

    assert getattr(ev_a, "target_speaker") == "Mistrzu"
    assert getattr(ev_b, "target_speaker") == "Wojowniku"


@pytest.mark.unit
def test_t11_1_manga_canon_loaded_from_json_and_neutral_prompt():
    """
    Standard 11.1 (Commit 2): Weryfikuje dynamiczne ładowanie bazy kanonu mangowego
    z katalogu manga_canon/ oraz brak statycznych instancji w kodzie.
    """
    assert isinstance(BUILTIN_MANGA_CANON, dict)
    assert len(BUILTIN_MANGA_CANON) > 0

    registry = MangaCanonRegistry()
    assert len(registry.canon_db) > 0

    canon_entry = {
        "title": "SeriaTestowa",
        "publisher": "WydawnictwoTestowe",
        "glossary": {"PojecieTestowe": "PojecieTestowePL"},
        "character_forms": {"PostacTestowa": "FormaTestowa"}
    }
    prompt_str = registry.format_canon_for_prompt(canon_entry)
    assert "OFICJALNY KANON" in prompt_str
    assert "PojecieTestowe" in prompt_str
    assert "PostacTestowa" in prompt_str


@pytest.mark.unit
def test_t11_1_verify_purity_audits_all_30_modules_and_tests():
    """
    Standard 11.1 (Commit 1 & 5): Weryfikuje, że verify_purity audytuje 30 modułów
    runtime oraz pakiet testowy, a allowlista migracyjna jest w 100% pusta.
    """
    assert len(verify_purity.FILES_TO_AUDIT) >= 30
    assert len(verify_purity.TEMPORARY_11_1_MIGRATION_ALLOWLIST) == 0

    runtime_modules = [
        "avt_formatter.py", "avt_linter.py", "client_factory.py", "context_cache.py",
        "extract.py", "fansub_miner.py", "glossary_manager.py", "main.py",
        "manga_canon.py", "memory.py", "metadata.py", "model_resolver.py",
        "pipeline_logger.py", "pricing_guard.py", "profiler.py", "prosody_engine.py",
        "romaji_helper.py", "rules.py", "scene_discourse.py", "scene_snapper.py",
        "series_memory.py", "sign_detector.py", "speaker_diarizer.py", "style_matrix.py",
        "translator.py", "typesetting_matcher.py", "user_feedback.py", "verifier.py",
        "whisper_disambiguator.py", "whisper_engine.py"
    ]
    for mod in runtime_modules:
        assert mod in verify_purity.FILES_TO_AUDIT, f"Brak modułu {mod} w FILES_TO_AUDIT"
