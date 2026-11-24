"""
Zestaw testów regresyjnych dla Standardu 11.2.25 (domknięcie residualnej luki DEF-02):
1. test_def02_residual_5_production_scene_cuts_do_not_leak_stale_addressee
2. test_def02_residual_standalone_resolve_line_addressee_respects_scene_cuts_and_preserves_intrascene
"""

import pytest
import pysubs2

from series_memory import SeriesBible
from scene_discourse import SceneDiscourseGraph
from translator import MultimodalTranslator, format_dry_telemetry_tag


def _build_synthetic_bible(tmp_path) -> SeriesBible:
    sb = SeriesBible(anime_title="Seria Testowa", storage_dir=tmp_path)
    sb.data["characters"] = {
        "Postac_Zenska_A": {
            "name": "Postac_Zenska_A",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "priority": "P0",
            "confidence": 0.99,
            "has_verified_gender": True,
            "aliases": ["Postac_Zenska_A"],
        },
        "Postac_Zenska_B": {
            "name": "Postac_Zenska_B",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "priority": "P0",
            "confidence": 0.99,
            "has_verified_gender": True,
            "aliases": ["Postac_Zenska_B"],
        },
        "Postac_Meska_A": {
            "name": "Postac_Meska_A",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "priority": "P0",
            "confidence": 0.99,
            "has_verified_gender": True,
            "aliases": ["Postac_Meska_A"],
        },
        "Postac_Meska_B": {
            "name": "Postac_Meska_B",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "priority": "P0",
            "confidence": 0.99,
            "has_verified_gender": True,
            "aliases": ["Postac_Meska_B"],
        },
        "Grupa_Zenska": {
            "name": "Grupa_Zenska",
            "gender": "FEMALE",
            "grammatical_gender": "FEMININE",
            "priority": "P0",
            "confidence": 0.99,
            "has_verified_gender": True,
            "aliases": ["Grupa_Zenska"],
        },
        "Ochroniarz_C": {
            "name": "Ochroniarz_C",
            "gender": "MALE",
            "grammatical_gender": "MASCULINE",
            "priority": "P0",
            "confidence": 0.99,
            "has_verified_gender": True,
            "aliases": ["Ochroniarz_C"],
        },
    }
    sb._rebuild_actor_aliases_index()
    return sb


def _run_production_telemetry_chain(
    tr: MultimodalTranslator,
    sb: SeriesBible,
    curr_ev: pysubs2.SSAEvent,
    batch_events,
    curr_idx: int,
    lookback_history=None,
):
    addr_cat, addr_lbl = tr._resolve_line_addressee(
        event=curr_ev,
        raw_phase1_addressee=None,
        batch_events=batch_events,
        event_idx=curr_idx,
        clean_text=curr_ev.text or "",
        lookback_history=lookback_history,
    )
    disc_telem = SceneDiscourseGraph.arbitrate_event_telemetry(
        event=curr_ev,
        series_bible=sb,
        raw_actor=curr_ev.name,
        target_actor=addr_lbl or addr_cat,
    )
    p0_spk_gram = disc_telem.get("grammatical_gender")
    spk_gram = p0_spk_gram if p0_spk_gram in ("MASCULINE", "FEMININE") else None

    p0_tgt_gram = disc_telem.get("target_gender")
    if p0_tgt_gram in ("MASCULINE", "FEMININE"):
        tgt_gram = p0_tgt_gram
        tgt_conf = 1.0
    elif addr_cat == "kobieta":
        tgt_gram = "FEMININE"
        tgt_conf = 1.0
    elif addr_cat == "mężczyzna":
        tgt_gram = "MASCULINE"
        tgt_conf = 1.0
    else:
        tgt_gram = None
        tgt_conf = 0.0

    telemetry_tag = format_dry_telemetry_tag(
        speaker_gender=spk_gram,
        speaker_confidence=1.0 if spk_gram else 0.0,
        target_gender=tgt_gram,
        target_confidence=tgt_conf,
        speaker_name=disc_telem.get("speaker_name") or curr_ev.name,
        target_name=disc_telem.get("target_actor") or addr_lbl,
    )
    return addr_cat, addr_lbl, disc_telem, telemetry_tag


@pytest.mark.unit
def test_def02_residual_5_production_scene_cuts_do_not_leak_stale_addressee(tmp_path):
    """
    Standard 11.2.25 (Residual DEF-02): Odtwarza dokładnie 5 geometrii czasowych i cięć FFmpeg
    (#80, #189, #255, #264 przez lookback_history z event_idx==0, #293) na pełnym łańcuchu:
    SceneDiscourseGraph.build_discourse_topology -> _resolve_line_addressee ->
    arbitrate_event_telemetry -> format_dry_telemetry_tag.
    Weryfikuje, że reset UNSPECIFIED nie jest obchodzony i stara postać nie wycieka do telemetry_tag.
    """
    sb = _build_synthetic_bible(tmp_path)

    cases = [
        # #80: gap=4810ms, cięcia [388346, 390849], z kolejną kwestią w nowej scenie
        {
            "case_id": "#80",
            "cuts": [388346, 390849],
            "prev": pysubs2.SSAEvent(start=383600, end=386320, text="Please be careful on the road.", name="Postac_Zenska_A"),
            "curr": pysubs2.SSAEvent(start=391130, end=393330, text="We have a situation inside.", name="Postac_Meska_A"),
            "next": pysubs2.SSAEvent(start=393600, end=398580, text="Bring the files right away.", name="Postac_Meska_B"),
            "cross_batch": False,
        },
        # #189: gap=3180ms, cięcie [832790]
        {
            "case_id": "#189",
            "cuts": [832790],
            "prev": pysubs2.SSAEvent(start=830100, end=831840, text="Stay right where you are.", name="Postac_Meska_B"),
            "curr": pysubs2.SSAEvent(start=835020, end=837040, text="What is that noise outside?", name="Grupa_Zenska"),
            "next": None,
            "cross_batch": False,
        },
        # #255: gap=2720ms, prev w stylu Main - Italics, cięcie [1042250]
        {
            "case_id": "#255",
            "cuts": [1042250],
            "prev": pysubs2.SSAEvent(start=1036820, end=1041260, style="Main - Italics", text="I knew this would happen.", name="Postac_Zenska_B"),
            "curr": pysubs2.SSAEvent(start=1043980, end=1046760, text="State your business here.", name="Ochroniarz_C"),
            "next": None,
            "cross_batch": False,
        },
        # #264: gap=4630ms, cięcia [1072488, 1073990], event_idx=0 przez lookback_history
        {
            "case_id": "#264",
            "cuts": [1072488, 1073990],
            "prev": pysubs2.SSAEvent(start=1068830, end=1072460, text="Leave the paperwork to me.", name="Postac_Zenska_A"),
            "curr": pysubs2.SSAEvent(start=1077090, end=1078640, text="Nothing moved since noon.", name="Postac_Meska_B"),
            "next": None,
            "cross_batch": True,
        },
        # #293: gap=3400ms, prev w stylu Main - Italics, cięcie [1177510]
        {
            "case_id": "#293",
            "cuts": [1177510],
            "prev": pysubs2.SSAEvent(start=1172560, end=1176840, style="Main - Italics", text="Those days will never return.", name="Postac_Zenska_B"),
            "curr": pysubs2.SSAEvent(start=1180240, end=1181740, text="The outer gate is open.", name="Postac_Meska_A"),
            "next": None,
            "cross_batch": False,
        },
    ]

    for c in cases:
        tr = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
        tr.series_bible = sb
        tr.scene_cuts_ms = list(c["cuts"])

        prev_ev = c["prev"]
        curr_ev = c["curr"]
        evs = [prev_ev, curr_ev] + ([c["next"]] if c["next"] is not None else [])

        # 1. Produkcyjny zapis topologii w scene_discourse.py
        SceneDiscourseGraph.build_discourse_topology(evs, series_bible=sb, scene_boundaries=c["cuts"])
        assert getattr(curr_ev, "target_speaker", None) == "UNSPECIFIED", f"{c['case_id']}: oczekiwano resetu UNSPECIFIED"
        assert getattr(curr_ev, "target_gender", None) == "UNSPECIFIED", f"{c['case_id']}: oczekiwano target_gender=UNSPECIFIED"

        # 2-4. Produkcyjny ciąg w translator.py
        if c["cross_batch"]:
            batch_events = [(0, curr_ev, curr_ev.text, "")]
            curr_idx = 0
            lookback_history = [{
                "en": prev_ev.text,
                "pl": "Poprzednia kwestia.",
                "speaker": prev_ev.name,
                "speaker_gender": "kobieta",
                "is_thought": False,
                "start_ms": int(prev_ev.start),
                "end_ms": int(prev_ev.end),
            }]
        else:
            batch_events = [(idx, ev, ev.text, "") for idx, ev in enumerate(evs)]
            curr_idx = 1
            lookback_history = None

        addr_cat, addr_lbl, _, telemetry_tag = _run_production_telemetry_chain(
            tr=tr,
            sb=sb,
            curr_ev=curr_ev,
            batch_events=batch_events,
            curr_idx=curr_idx,
            lookback_history=lookback_history,
        )

        assert addr_cat is None, f"{c['case_id']}: _resolve_line_addressee wyciekło addr_cat={addr_cat}"
        assert addr_lbl is None, f"{c['case_id']}: _resolve_line_addressee wyciekło addr_lbl={addr_lbl}"
        assert "Adresat:" not in telemetry_tag, f"{c['case_id']}: wyciek 'Adresat:' w {telemetry_tag}"
        assert prev_ev.name not in telemetry_tag, f"{c['case_id']}: wyciek '{prev_ev.name}' w {telemetry_tag}"


@pytest.mark.unit
def test_def02_residual_standalone_resolve_line_addressee_respects_scene_cuts_and_preserves_intrascene(tmp_path):
    """
    Standard 11.2.25 (Kontrola nietautologiczna Warstwy 2):
    Weryfikuje bezpośrednio _resolve_line_addressee BEZ wcześniejszego build_discourse_topology:
    - pauza >= 3500 ms (4000 ms, brak cięć FFmpeg) -> (None, None)
    - pauza 2500 <= gap < 3500 ms (3000 ms) z cięciem FFmpeg -> (None, None)
    - granica paczek (event_idx=0 + lookback_history z end_ms przy pauzie 4630 ms) -> (None, None)
    - kontrola zachowawcza wewnątrz sceny (640 ms bez cięcia) -> ('kobieta', 'Postac_Zenska_A (Kobieta)')
      oraz 'Adresat: Postac_Zenska_A (FEMININE)' w format_dry_telemetry_tag.
    """
    sb = _build_synthetic_bible(tmp_path)

    # 1. Pauza 4000 ms bez cięć FFmpeg -> brak dziedziczenia
    tr1 = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    tr1.series_bible = sb
    tr1.scene_cuts_ms = []
    ev_p1 = pysubs2.SSAEvent(start=640000, end=643000, text="See you soon.", name="Postac_Zenska_A")
    ev_c1 = pysubs2.SSAEvent(start=647000, end=649000, text="Let us begin.", name="Postac_Meska_A")
    cat1, lbl1 = tr1._resolve_line_addressee(
        event=ev_c1,
        raw_phase1_addressee=None,
        batch_events=[(0, ev_p1, ev_p1.text, ""), (1, ev_c1, ev_c1.text, "")],
        event_idx=1,
        clean_text=ev_c1.text,
    )
    assert (cat1, lbl1) == (None, None)

    # 2. Pauza 3000 ms z cięciem FFmpeg wewnątrz okna -> brak dziedziczenia
    tr2 = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    tr2.series_bible = sb
    tr2.scene_cuts_ms = [644500]
    ev_p2 = pysubs2.SSAEvent(start=640000, end=643000, text="Goodbye for now.", name="Postac_Zenska_A")
    ev_c2 = pysubs2.SSAEvent(start=646000, end=648000, text="Time to report.", name="Postac_Meska_A")
    cat2, lbl2 = tr2._resolve_line_addressee(
        event=ev_c2,
        raw_phase1_addressee=None,
        batch_events=[(0, ev_p2, ev_p2.text, ""), (1, ev_c2, ev_c2.text, "")],
        event_idx=1,
        clean_text=ev_c2.text,
    )
    assert (cat2, lbl2) == (None, None)

    # 3. Granica paczek (event_idx == 0) z lookback_history zawierającym end_ms (gap=4630 ms)
    tr3 = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    tr3.series_bible = sb
    tr3.scene_cuts_ms = []
    ev_c3 = pysubs2.SSAEvent(start=1077090, end=1078640, text="Wait over here.", name="Postac_Meska_A")
    cat3, lbl3 = tr3._resolve_line_addressee(
        event=ev_c3,
        raw_phase1_addressee=None,
        batch_events=[(0, ev_c3, ev_c3.text, "")],
        event_idx=0,
        clean_text=ev_c3.text,
        lookback_history=[{
            "en": "I will handle this.",
            "pl": "Zajmę się tym.",
            "speaker": "Postac_Zenska_A",
            "speaker_gender": "kobieta",
            "is_thought": False,
            "start_ms": 1068830,
            "end_ms": 1072460,
        }],
    )
    assert (cat3, lbl3) == (None, None)

    # 4. Kontrola zachowawcza wewnątrz sceny: pauza 640 ms bez cięcia FFmpeg
    tr4 = MultimodalTranslator(api_key="mock_k0", model="gemini-4-hydrogen", enable_verifier=False)
    tr4.series_bible = sb
    tr4.scene_cuts_ms = []
    ev_p4 = pysubs2.SSAEvent(start=640000, end=643000, text="How is everything going?", name="Postac_Zenska_A")
    ev_c4 = pysubs2.SSAEvent(start=643640, end=645000, text="Everything is ready.", name="Postac_Meska_A")
    cat4, lbl4, _, telemetry_tag4 = _run_production_telemetry_chain(
        tr=tr4,
        sb=sb,
        curr_ev=ev_c4,
        batch_events=[(0, ev_p4, ev_p4.text, ""), (1, ev_c4, ev_c4.text, "")],
        curr_idx=1,
    )
    assert (cat4, lbl4) == ("kobieta", "Postac_Zenska_A (Kobieta)")
    assert "Adresat: Postac_Zenska_A (FEMININE)" in telemetry_tag4
