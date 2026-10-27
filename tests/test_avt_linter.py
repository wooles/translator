import pytest
import pysubs2
from avt_linter import AVTLinter, EpisodeQualityGate, deduplicate_alignment_tags


def test_lint_and_fix_line_identity_and_newline_preservation():
    linter = AVTLinter()
    
    # Standard 9.1: Primary LLM Translation Authority preservation T(x) = x
    lines = [
        "Wiem o wszystkim, co się wczoraj wydarzyło.",
        "Czy naprawdę sądzisz, że zdołasz to osiągnąć?",
        "Nie mam pojęcia, jak to rozwiązać.",
        "Zaraz tam dotrę i sprawdzę stan sytuacji.",
        "Chyba już czas podjąć ostateczną decyzję."
    ]
    for line in lines:
        fixed, _ = linter.lint_and_fix_line(
            line,
            speaker_gender="MALE",
            target_gender="FEMALE",
            strict_positive_domain=True
        )
        assert fixed == line, f"Oczekiwano tożsamości T(x)=x, otrzymano: '{fixed}'"

    # Explicit \n converted to \N without flattening when lines <= 2 and CPL <= 38
    two_line_text = "Pierwszy krótki wiersz\ndrugi krótki wiersz"
    fixed_two_line, _ = linter.lint_and_fix_line(two_line_text, strict_positive_domain=True)
    assert fixed_two_line == "Pierwszy krótki wiersz\\Ndrugi krótki wiersz"

    # Sign text preserves multi-line structure
    sign_text = "Tytuł Informacyjny\nPodpis: Dowództwo"
    fixed_sign, _ = linter.lint_and_fix_line(sign_text, is_sign=True, strict_positive_domain=True)
    assert fixed_sign == "Tytuł Informacyjny\\NPodpis: Dowództwo"


def test_eqg_no_verb_mutation_and_normative_ellipsis():
    eqg = EpisodeQualityGate()
    subs = pysubs2.SSAFile()

    ev1 = pysubs2.SSAEvent(start=1000, end=3000, text="Czy naprawdę jesteś pewien tego kroku?..")
    ev2 = pysubs2.SSAEvent(start=3500, end=5500, text="Co ty wyprawiasz!..")
    ev3 = pysubs2.SSAEvent(start=6000, end=8000, text="Zrobiłem wszystko, co było konieczne.")
    ev4 = pysubs2.SSAEvent(start=8500, end=10500, text="Może powinniśmy poczekać na wsparcie?")
    subs.events = [ev1, ev2, ev3, ev4]

    fixed_subs, fixes = eqg.audit_and_fix_entire_episode(
        subs,
        is_production=True,
        strict_positive_domain=True
    )

    # Verbs must not be mutated in production mode
    assert "Zrobiłem wszystko" in fixed_subs.events[2].text
    assert "powinniśmy poczekać" in fixed_subs.events[3].text

    # Ellipsis must be strictly normative 3-dot or single mark, never 2 dots
    import re
    assert not re.search(r"\?[.]{2}(?![.])", fixed_subs.events[0].text)
    assert "?..." in fixed_subs.events[0].text or fixed_subs.events[0].text.endswith("?")
    assert not re.search(r"\![.]{2}(?![.])", fixed_subs.events[1].text)
    assert "!..." in fixed_subs.events[1].text or fixed_subs.events[1].text.endswith("!")


def test_phase7_hygiene_clitic_binding_and_tag_deduplication():
    eqg = EpisodeQualityGate()

    # 1. Syntactic binding across \N: verb + reflexive clitic
    subs1 = pysubs2.SSAFile()
    ev_clitic = pysubs2.SSAEvent(start=1000, end=3000, text="Nagle okazało\\Nsię to zupełnie jasne.")
    subs1.events = [ev_clitic]
    fixed1, _ = eqg.audit_and_fix_entire_episode(subs1, is_production=True, strict_positive_domain=True)
    assert "\\Nokazało się" in fixed1.events[0].text or "okazało się" in fixed1.events[0].text

    # 2. Syntactic binding across \N: preposition + noun
    subs2 = pysubs2.SSAFile()
    ev_prep = pysubs2.SSAEvent(start=1000, end=3000, text="Spotkamy się w\\Ndomu przyjaciela.")
    subs2.events = [ev_prep]
    fixed2, _ = eqg.audit_and_fix_entire_episode(subs2, is_production=True, strict_positive_domain=True)
    assert "\\Nw domu" in fixed2.events[0].text or "w domu" in fixed2.events[0].text

    # 3. Signature dash + sender binding
    subs3 = pysubs2.SSAFile()
    ev_sig = pysubs2.SSAEvent(start=1000, end=3000, text="Wiadomość z frontu.\\N— Autor")
    subs3.events = [ev_sig]
    fixed3, _ = eqg.audit_and_fix_entire_episode(subs3, is_production=True, strict_positive_domain=True)
    assert "— Autor" in fixed3.events[0].text

    # 4. Multi-line bullet list preservation for signs
    subs4 = pysubs2.SSAFile()
    ev_sign = pysubs2.SSAEvent(start=1000, end=3000, text="Punkt pierwszy\\NPunkt drugi\\NPunkt trzeci", style="Sign")
    setattr(ev_sign, "is_sign", True)
    subs4.events = [ev_sign]
    fixed4, _ = eqg.audit_and_fix_entire_episode(subs4, is_production=True, strict_positive_domain=True)
    assert "\\N" in fixed4.events[0].text

    # 5. Deduplication of ASS alignment tags
    text_dup_an = "{\\an7\\pos(1500,200)\\an8}Napis w rogu ekranu"
    deduped = deduplicate_alignment_tags(text_dup_an, play_res_x=1920)
    assert deduped.count(r"\an") <= 1
    assert r"\an3" in deduped or r"\an9" in deduped or r"\an6" in deduped


def test_linter_preserves_phase2_lexical_choice_over_slash_glossary():
    linter = AVTLinter()
    phase2_line = "Namiestnik podjął decyzję o wymarszu wojsk."
    glossary_map = {"Governor": "namiestnik / gubernator"}
    res = linter.lint_and_fix_line(
        phase2_line,
        glossary=glossary_map,
        strict_positive_domain=True
    )
    fixed_text = res.text if hasattr(res, "text") else res[0]
    assert fixed_text == phase2_line


def test_eqg_respects_v4_styles_alignment_and_italic_attributes():
    # 1. Top alignment on collision is applied when styles Alignment == 2, different speakers, and top band free
    assert EpisodeQualityGate.should_apply_top_alignment_on_collision(2, 2, speaker_a="Mówca 1", speaker_b="Mówca 2", has_active_top_sign=False) is True
    assert EpisodeQualityGate.should_apply_top_alignment_on_collision(2, 2, speaker_a="Mówca 1", speaker_b="Mówca 1", has_active_top_sign=False) is False
    assert EpisodeQualityGate.should_apply_top_alignment_on_collision(2, 2, speaker_a="Mówca 1", speaker_b="Mówca 2", has_active_top_sign=True) is False
    assert EpisodeQualityGate.should_apply_top_alignment_on_collision(2, 8, speaker_a="Mówca 1", speaker_b="Mówca 2") is False
    assert EpisodeQualityGate.should_apply_top_alignment_on_collision(8, 2, speaker_a="Mówca 1", speaker_b="Mówca 2") is False
    assert EpisodeQualityGate.should_apply_top_alignment_on_collision(1, 2) is False
    assert EpisodeQualityGate.should_apply_top_alignment_on_collision(7, 8) is False

    # 2. Collision execution in EpisodeQualityGate
    eqg = EpisodeQualityGate()
    subs = pysubs2.SSAFile()
    subs.styles["BottomStyle"] = pysubs2.SSAStyle(alignment=2)
    subs.styles["TopStyle"] = pysubs2.SSAStyle(alignment=8)

    ev1 = pysubs2.SSAEvent(start=1000, end=3000, text="Kwestia pierwsza na dole", style="BottomStyle", name="Mówca 1")
    ev2 = pysubs2.SSAEvent(start=1500, end=3500, text="Kwestia druga", style="BottomStyle", name="Mówca 2")
    subs.events = [ev1, ev2]

    fixed_subs, fixes = eqg.audit_and_fix_entire_episode(subs, strict_positive_domain=True)
    assert any(r"\an8" in ev.text for ev in fixed_subs.events)


@pytest.mark.parametrize("input_text,is_sign,expected_text", [
    (r"{(\an8}Tekst na górze", True, r"{\an8}Tekst na górze"),
    (r"{\i1}Tekst wyróżniony{\i0}{\i0}", False, r"{\i1}Tekst wyróżniony{\i0}"),
    (r"{\an8}Tytuł części:\NCzęść pierwsza\NCzęść druga", True, r"{\an8}Tytuł części: Część pierwsza\NCzęść druga"),
])
def test_phase7_hygiene_preserves_single_sign_event_and_normalizes_ass_tags(input_text, is_sign, expected_text):
    normalized = EpisodeQualityGate.normalize_ass_tags_and_sign_layout(input_text, is_sign=is_sign)
    assert normalized == expected_text


@pytest.mark.parametrize(
    "speaker_a,speaker_b,top_sign_active,expected_lift",
    [
        # Kategoria 1: ten sam mówca → NIE podnoś.
        ("Jan", "Jan", False, False),
        # Kategoria 2: różni mówcy, górne pasmo zajęte → NIE podnoś.
        ("Jan", "Anna", True, False),
        # Kategoria 3: różni mówcy, górne pasmo wolne → podnieś.
        ("Jan", "Anna", False, True),
    ],
)
def test_collision_alignment_keeps_same_speaker_continuity_and_checks_top_sign(
    speaker_a, speaker_b, top_sign_active, expected_lift
):
    """Weryfikuje zachowanie ciągłości zdania tego samego mówcy na dole oraz blokadę przy zajętym paśmie górnym."""
    from avt_linter import EpisodeQualityGate
    should_lift = EpisodeQualityGate.should_apply_top_alignment_on_collision(
        style_a_alignment=2,
        style_b_alignment=2,
        speaker_a=speaker_a,
        speaker_b=speaker_b,
        has_active_top_sign=top_sign_active,
    )
    assert should_lift is expected_lift


@pytest.mark.parametrize(
    "raw_text,prev_italic,next_italic,expected_text",
    [
        # Kategoria 1: scalanie zduplikowanych bloków {\...}{\...}.
        (r"{\3c&H000000&\bord3}{\an1\1c&HFFFFFF&\3c&H000000&\shad1}Napis", False, False, r"{\an1\1c&HFFFFFF&\3c&H000000&\bord3\shad1}Napis"),
        # Kategoria 2: domykanie kursywy w monologu wewnętrznym.
        ("...ciąg dalszy myśli.", True, True, r"{\i1}...ciąg dalszy myśli.{\i0}"),
    ],
)
def test_phase7_hygiene_merges_duplicate_tag_blocks_and_bridges_italic_monologue(
    raw_text, prev_italic, next_italic, expected_text
):
    """Weryfikuje scalanie zduplikowanych bloków tagów {\...} oraz domykanie kursywy w monologu wewnętrznym."""
    from avt_linter import EpisodeQualityGate
    cleaned = EpisodeQualityGate.normalize_ass_tags_and_sign_layout(
        text=raw_text,
        prev_same_speaker_italic=prev_italic,
        next_same_speaker_italic=next_italic,
    )
    assert cleaned == expected_text
