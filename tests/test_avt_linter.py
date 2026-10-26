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
