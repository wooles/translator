# -*- coding: utf-8 -*-
"""
Standard 12.2.1 Regression Suite (OBS-19 .. OBS-23).
100% Z1-clean synthetic test fixtures operating strictly on production schemas and functions.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pysubs2
import pytest
from PIL import Image
from google import genai
from google.genai import types as genai_types

from profiler import (
    CharacterCatchphrase,
    DangerLinePreScan,
    EpisodeProfile,
    _map_catchphrase_variant_pairs,
    _split_catchphrase_variants,
    format_episode_profile_for_prompt,
    resolve_profile_alerts_to_events,
)
from series_memory import SeriesBible
from sign_detector import VisualSignDetector
from translator import (
    BatchTranslationResponse,
    LineTranslation,
    MultimodalTranslator,
    SceneDiagnosis,
    _append_phase1_official_announcement_rule,
    _classify_collective_speaker_actor,
    _detect_official_announcement_line,
    _detect_polish_typo_anomaly,
    _restore_phase2_trailing_period,
    extract_typesetting_tags,
    is_generic_actor_or_category,
)


def _make_mock_genai_client(handler) -> genai.Client:
    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    c = genai.Client(api_key="mock_k0", http_options=genai_types.HttpOptions(httpx_client=http_client))
    if getattr(c._api_client, "_httpx_client", None) is not http_client:
        c._api_client._httpx_client = http_client
    return c


class _DummyPbar:
    def write(self, msg: str) -> None:
        pass

    def set_postfix_str(self, s: str) -> None:
        pass

    def refresh(self) -> None:
        pass


def _make_translator(tmp_path: Path, batch_translations=None) -> MultimodalTranslator:
    """Builds a real MultimodalTranslator bound to an isolated temp SeriesBible and mock HTTP transport."""
    resp_obj = BatchTranslationResponse(
        scene_diagnosis=SceneDiagnosis(
            dramatic_context="Test scene",
            dialogue_flow="Natural exchange",
            audio_intent_check="Consistent",
            dominant_tone="Neutralny",
        ),
        translations=batch_translations
        or [
            LineTranslation(
                id=1,
                polish_text="Razem teraz!",
                speaker_gender="UNKNOWN",
                speaker_name="",
                addressee=None,
            )
        ],
    )
    payload_text = resp_obj.model_dump_json()

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"role": "model", "parts": [{"text": payload_text}]}}],
                "usageMetadata": {
                    "promptTokenCount": 500,
                    "cachedContentTokenCount": 0,
                    "candidatesTokenCount": 60,
                    "thoughtsTokenCount": 0,
                },
            },
        )

    tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=True)
    mock_c = _make_mock_genai_client(_handler)
    tr.client_pool_f1.clients = [mock_c]
    tr.client_pool.clients = [mock_c]
    tr.client = mock_c
    tr.series_bible = SeriesBible("SyntheticSeries1221", storage_dir=tmp_path)
    return tr


# ------------------------------------------------------------------------------
# OBS-19: Phase 2 trailing period restoration inside closing ASS tags
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_obs19_trailing_period_inside_ass_tags_and_no_quad_dots():
    # Positive: dot already inside {\i0} -> no trailing dot appended after '}'
    assert (
        _restore_phase2_trailing_period(
            refined_pl=r"{\i1}Przywykłam do samotności.{\i0}",
            orig_pl=r"{\i1}Przywykłam do samotności.{\i0}",
            orig_en="I got used to being alone.",
        )
        == r"{\i1}Przywykłam do samotności.{\i0}"
    )

    # Positive: ellipsis inside {\i0} -> never turns into ....
    assert (
        _restore_phase2_trailing_period(
            refined_pl=r"{\i1}Nie mówcie, że ona też...{\i0}",
            orig_pl=r"{\i1}Nie mówcie, że ona też...{\i0}",
            orig_en="Don't tell me she also...",
        )
        == r"{\i1}Nie mówcie, że ona też...{\i0}"
    )

    # Positive: missing period inside closing italic block -> inserted before {\i0}
    assert (
        _restore_phase2_trailing_period(
            refined_pl=r"{\i1}Zdanie bez kropki{\i0}",
            orig_pl=r"{\i1}Zdanie z kropką.{\i0}",
            orig_en="A sentence with a dot.",
        )
        == r"{\i1}Zdanie bez kropki.{\i0}"
    )

    # Negative: plain dialogue missing period still restores trailing period normally
    assert (
        _restore_phase2_trailing_period(
            refined_pl="Zwykłe zdanie bez kropki",
            orig_pl="Zwykłe zdanie z kropką.",
            orig_en="Plain sentence with a dot.",
        )
        == "Zwykłe zdanie bez kropki."
    )

    # Sign protection: signs never receive automatic trailing dots
    assert (
        _restore_phase2_trailing_period(
            refined_pl="NAPIS EKRANOWY",
            orig_pl="NAPIS EKRANOWY.",
            orig_en="ON-SCREEN SIGN.",
            is_sign=True,
        )
        == "NAPIS EKRANOWY"
    )


# ------------------------------------------------------------------------------
# OBS-20: Multiline full italics vs partial first-line italics
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_obs20_extract_typesetting_tags_multiline_and_partial_italics():
    # Positive: two-line full italic subtitle removes all {\i1}/{\i0} cleanly (0 half-italics)
    pref, clean = extract_typesetting_tags(r"{\i1}Wiersz pierwszy{\i0}\N{\i1}Wiersz drugi{\i0}")
    assert pref == ""
    assert clean == r"Wiersz pierwszy\NWiersz drugi"
    assert r"\i1" not in clean and r"\i0" not in clean

    # Positive: combined leading tag block + second italic line
    pref_top, clean_top = extract_typesetting_tags(r"{\an8\i1}Górny wiersz{\i0}\N{\i1}Drugi wiersz{\i0}")
    assert pref_top == r"{\an8}"
    assert clean_top == r"Górny wiersz\NDrugi wiersz"

    # Negative: partial italics only on line 1 preserves complete {\i1}...{\i0} span
    pref_part, clean_part = extract_typesetting_tags(r"{\i1}Tylko pierwszy wiersz{\i0}\NDrugi zwykły wiersz")
    assert pref_part == ""
    assert clean_part == r"{\i1}Tylko pierwszy wiersz{\i0}\NDrugi zwykły wiersz"

    # Regression (Standard 11.1.7)
    p1, c1 = extract_typesetting_tags(r"{\an8\i1}Two{\i0}!")
    assert p1 == r"{\an8}" and c1 == "Two!"
    p2, c2 = extract_typesetting_tags(r"{\an8}{\i1}Episode Title{\i0}!")
    assert p2 == r"{\an8}" and c2 == "Episode Title!"


# ------------------------------------------------------------------------------
# OBS-21: Punctuation-only '/' dual-dialogue actor guard
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_obs21_slash_dual_dialogue_blocked_from_registry_and_polylogue_feminine(tmp_path):
    assert is_generic_actor_or_category("/") is True
    assert is_generic_actor_or_category("//") is True
    assert is_generic_actor_or_category("-") is True
    assert _classify_collective_speaker_actor("/") == "DUAL_DIALOGUE"
    assert _classify_collective_speaker_actor("BROTHERS") == "VIRILE"

    tr = _make_translator(tmp_path)
    tr._register_character_safe("/", "kobieta", role="seiyū Whisper")
    assert "/" not in tr.character_registry

    ev_slash = pysubs2.SSAEvent(start=1000, end=2500, name="/", text="Let's go together!")
    tr._arbitrate_speaker_gender(
        event=ev_slash,
        raw_phase1_gender="FEMALE",
        batch_id=1,
        speaker_tags={1: "sopran (~309 Hz)"},
        whisper_transcriptions={1: "あたし行くわ"},
        pl_candidate="",
        raw_speaker_name="/",
        event_idx=0,
    )
    assert "/" not in tr.character_registry
    assert "/" not in tr.series_bible.data.get("characters", {})

    batch_ev = [(0, ev_slash, ev_slash.text, "")]
    prompt = tr._prepare_batch_prompt(
        batch_events=batch_ev,
        history_context=[],
        speaker_tags={1: "sopran (~309 Hz)"},
        whisper_transcriptions={1: "あたし行くわ"},
    )
    assert "• /:" not in prompt
    assert "POLYLOGUE (FEMININE)" not in prompt

    tr_f1 = _make_translator(
        tmp_path,
        batch_translations=[
            LineTranslation(
                id=1,
                polish_text="Razem teraz!",
                speaker_gender="kobieta",
                speaker_name="POLYLOGUE",
                addressee=None,
            )
        ],
    )
    p1 = tr_f1._process_phase1_only(
        b_idx=0,
        batch=batch_ev,
        untranslated_in_batch=batch_ev,
        batches=[batch_ev],
        video_path=None,
        is_ass=True,
        anime_meta=None,
        episode_profile=None,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={},
        all_user_rules=[],
        translated_results={},
        history=[],
        pbar=_DummyPbar(),
    )
    item0 = p1["pass1_items"][0]
    assert item0["speaker_gender"] is None
    assert "POLYLOGUE (FEMININE)" not in item0["notes"]
    assert "POLYLOGUE (FEMININE)" not in item0["telemetry_tag"]

    # Negative: real named speaker with verified male audio still registers normally
    ev_hero = pysubs2.SSAEvent(start=3000, end=4500, name="HeroAlpha", text="I am ready.")
    g_hero, _ = tr._arbitrate_speaker_gender(
        event=ev_hero,
        raw_phase1_gender="MALE",
        batch_id=1,
        speaker_tags={1: "baryton (~115 Hz)"},
        whisper_transcriptions={1: "俺がやる"},
        pl_candidate="",
        raw_speaker_name="HeroAlpha",
        event_idx=1,
    )
    assert g_hero == "mężczyzna"
    assert "HeroAlpha" in tr.character_registry


# ------------------------------------------------------------------------------
# OBS-22: VisualSignDetector proximity filter & canonical glossary injection
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_obs22_visual_sign_detector_proximity_and_glossary(tmp_path, monkeypatch):
    existing_sign = pysubs2.SSAEvent(
        start=170250,
        end=176540,
        style="TopCenter",
        text=r"{\an8}CANON TITLE CARD",
    )
    # Nearby gap within 1.75s (<= 3000ms threshold)
    assert VisualSignDetector.is_near_existing_sign(165290, 168500, [existing_sign], proximity_ms=3000) is True
    # Distant gap > 5s away
    assert VisualSignDetector.is_near_existing_sign(150000, 152000, [existing_sign], proximity_ms=3000) is False

    dummy_video = tmp_path / "dummy.mp4"
    dummy_video.write_bytes(b"video")

    mock_client = MagicMock()
    res_blocked = VisualSignDetector.detect_signs_in_gaps(
        video_path=str(dummy_video),
        gaps=[(165040, 169000)],
        client=mock_client,
        custom_glossary={"Arcane Emblem": "Emblemat Energii"},
        existing_events=[existing_sign],
        sign_proximity_ms=3000,
    )
    assert res_blocked == []
    mock_client.models.generate_content.assert_not_called()

    # Non-colliding gap (> 5s away) receives canonical glossary in prompt & aligns term
    frame_img = tmp_path / "frame.png"
    Image.new("RGB", (16, 16), color="white").save(frame_img)
    monkeypatch.setattr("sign_detector.extract_frame_at_timestamp", lambda *args, **kwargs: str(frame_img))

    captured_prompts = []

    def _sign_handler(request: httpx.Request) -> httpx.Response:
        req_json = json.loads(request.content.decode("utf-8"))
        for part in req_json.get("contents", [{}])[0].get("parts", []):
            if "text" in part:
                captured_prompts.append(part["text"])
        sign_payload = json.dumps({
            "is_title_or_banner": True,
            "original_text": "Arcane Emblem",
            "translation_pl": "Energetyczny Emblemat",
            "banner_type": "CHAPTER_SIGN",
            "screen_region": "top_center",
        })
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"role": "model", "parts": [{"text": sign_payload}]}}]},
        )

    ok_client = _make_mock_genai_client(_sign_handler)
    res_ok = VisualSignDetector.detect_signs_in_gaps(
        video_path=str(dummy_video),
        gaps=[(10000, 14500)],
        client=ok_client,
        custom_glossary=[{"term_en": "Arcane Emblem", "translation_pl": "Emblemat Energii"}],
        existing_events=[existing_sign],
        sign_proximity_ms=3000,
    )
    assert len(res_ok) == 1
    assert captured_prompts
    assert "KANONICZNA TERMINOLOGIA SERII" in captured_prompts[0]
    assert "Arcane Emblem" in captured_prompts[0]
    assert "Emblemat Energii" in captured_prompts[0]
    assert "EMBLEMAT ENERGII" in res_ok[0].text


# ------------------------------------------------------------------------------
# OBS-23: Catchphrase priority over danger_lines, F1 announcement rule & F2 scoring
# ------------------------------------------------------------------------------
@pytest.mark.unit
def test_obs23_catchphrase_priority_over_danger_lines_and_variant_split(tmp_path):
    assert _split_catchphrase_variants("TokenAlpha / TokenBeta") == ["TokenAlpha", "TokenBeta"]
    assert _map_catchphrase_variant_pairs("TokenAlpha / TokenBeta", "TokenAlpha / TokenBeta") == [
        ("TokenAlpha", "TokenAlpha"),
        ("TokenBeta", "TokenBeta"),
    ]

    profile = EpisodeProfile(
        episode_summary="Synthetic catchphrase arbitration test",
        danger_lines_prescan=[
            DangerLinePreScan(
                approx_time="00:00:10",
                speaker="HeroAlpha",
                english_phrase="TokenAlpha. / TokenBeta!",
                contextual_trap="Potencjalne zdrobnienie",
                contextual_guidance="np. ZamiennikA / ZamiennikB",
            )
        ],
        character_catchphrases=[
            CharacterCatchphrase(
                character_name="HeroAlpha",
                original_phrase="TokenAlpha / TokenBeta",
                canonical_pl="TokenAlpha / TokenBeta",
                context_notes="Stałe powiedzonko postaci",
            )
        ],
    )

    events = [
        (0, pysubs2.SSAEvent(start=10000, end=11200, name="HeroAlpha", text="TokenAlpha."), "TokenAlpha.", ""),
        (1, pysubs2.SSAEvent(start=12000, end=13200, name="HeroAlpha", text="TokenBeta!"), "TokenBeta!", ""),
    ]
    resolved = resolve_profile_alerts_to_events(profile, events)
    assert 0 in resolved and 1 in resolved
    assert any("KWESTIA-WIZYTÓWKA: 'TokenAlpha'" in a for a in resolved[0])
    assert any("KWESTIA-WIZYTÓWKA: 'TokenBeta'" in a for a in resolved[1])
    assert not any("pułapka_profilera" in a for a in resolved[0])
    assert not any("pułapka_profilera" in a for a in resolved[1])

    formatted_full = format_episode_profile_for_prompt(profile)
    assert "ZAMROŻONE POWIEDZONKA" in formatted_full
    assert "TokenAlpha. / TokenBeta!" not in formatted_full

    # Fallback paths in MultimodalTranslator (_prepare_batch_prompt & _process_phase1_only)
    tr_fb = _make_translator(
        tmp_path,
        batch_translations=[
            LineTranslation(id=1, polish_text="TokenAlpha.", speaker_gender="mężczyzna", speaker_name="HeroAlpha")
        ],
    )
    tr_fb.profile_line_alerts = {}
    prompt_fb = tr_fb._prepare_batch_prompt(
        batch_events=[events[0]],
        history_context=[],
        episode_profile=profile,
    )
    assert "KWESTIA-WIZYTÓWKA: 'TokenAlpha'" in prompt_fb
    assert "pułapka_kontekstowa" not in prompt_fb

    p1_fb = tr_fb._process_phase1_only(
        b_idx=0,
        batch=[events[0]],
        untranslated_in_batch=[events[0]],
        batches=[[events[0]]],
        video_path=None,
        is_ass=True,
        anime_meta=None,
        episode_profile=profile,
        anime_context_str="",
        episode_profile_str="",
        series_bible_str="",
        manga_canon_str="",
        combined_glossary={},
        all_user_rules=[],
        translated_results={},
        history=[],
        pbar=_DummyPbar(),
    )
    fb_notes = p1_fb["pass1_items"][0]["notes"]
    assert "KWESTIA-WIZYTÓWKA: 'TokenAlpha'" in fb_notes
    assert "pułapka_profilera" not in fb_notes


@pytest.mark.unit
def test_obs23_semideterministic_f1_announcement_rule_and_f2_priority_scoring(tmp_path):
    # 1. F1 positive announcement rule triggers only on ceremonial announcement signal
    base_rules = _append_phase1_official_announcement_rule(
        "REGUŁA BAZOWA.",
        [{"en": "Next up, we'll hear from the representative of the new students.", "is_sign": False}],
    )
    assert "[REJESTR KOMUNIKATÓW OFICJALNYCH]" in base_rules
    unchanged_rules = _append_phase1_official_announcement_rule(
        "REGUŁA BAZOWA.",
        [{"en": "Shall we go to the cafeteria?", "is_sign": False}],
    )
    assert unchanged_rules == "REGUŁA BAZOWA."

    # 2. Polish typo detector (positive + valid Polish false-positive protection)
    assert _detect_polish_typo_anomaly("To jest najibardziej niesamowity wynik.") is True
    assert _detect_polish_typo_anomaly("Naprawdę jesterem pewien.") is True
    assert _detect_polish_typo_anomaly("Dzisiaj popołudnie było spokojne.") is False
    assert _detect_polish_typo_anomaly("To najistotniejszy argument w tej sprawie.") is False
    assert _detect_polish_typo_anomaly("Najinteligentniejszy uczeń odpowiedział od razu.") is False
    assert _detect_polish_typo_anomaly("Zjadłem na śniadanie świeży banan.") is False

    # 3. Announcement detector (positive + negative)
    assert (
        _detect_official_announcement_line(
            "Next up, we'll hear from the representative of the new students.",
            "Następnie posłuchamy wysłannika pierwszaków.",
        )
        is True
    )
    assert _detect_official_announcement_line("What do you want for lunch?", "Co chcesz na obiad?") is False
    assert _detect_official_announcement_line("Join us later!", "Zapraszamy do nas, ziomku!") is False

    # 4. Selector prioritizes both typo and official-announcement lines above normal dialogue
    tr = _make_translator(tmp_path)
    items = []
    for i in range(1, 15):
        items.append({
            "id": i,
            "en": "Okay, got it.",
            "pl": "Dobrze, rozumiem.",
            "speaker_confidence": 1.0,
            "target_confidence": 1.0,
        })
    items.append({
        "id": 85,
        "en": "Next up, we'll hear from the representative of the new students.",
        "pl": "Teraz wysłuchamy przedstawiciela nowych uczniów.",
        "speaker_confidence": 1.0,
        "target_confidence": 1.0,
    })
    items.append({
        "id": 93,
        "en": "That was fair.",
        "pl": "To było najibardziej sprawiedliwe.",
        "speaker_confidence": 1.0,
        "target_confidence": 1.0,
    })

    selected = tr._select_hydrogen_phase2_candidates(items, total_batches=6, episode_line_cap=115)
    sel_ids = {it["id"] for it in selected}
    assert 85 in sel_ids
    assert 93 in sel_ids
