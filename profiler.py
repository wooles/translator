# -*- coding: utf-8 -*-
"""
Pre-pass Episode Profiler & Glossary Engine Module.
Analyzes the entire episode script prior to translation, mapping character relationships
(honorific vs. informal address forms) and compiling a specialized terminology glossary,
ensuring consistent dialogue continuity across the whole episode.
"""

import os
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Tuple, Union
import numpy as np
from pydantic import BaseModel, Field, ConfigDict
from google import genai
from google.genai import types
from client_factory import format_friendly_api_error, patch_google_genai_schema_sanitizer
from metadata import normalize_ascii_diacritics, normalize_actor_tag
from series_memory import is_valid_anthroponymic_phonotactics
from model_resolver import is_gemini_4_or_hydrogen_model, build_thinking_config

patch_google_genai_schema_sanitizer()

logger = logging.getLogger("profiler")


class NameDeclension(BaseModel):
    character_name: str = Field(description="Forma mianownikowa nazwy własnej, imienia postaci, tytułu lub syntagmy złożonej")
    gender: str = Field(description="'MALE' lub 'FEMALE'")
    declension_summary: str = Field(description="Kanoniczny paradygmat odmiany przez przypadki w języku polskim z uwzględnieniem syntagm i przydawki (M, D, C, B, N, Ms, W)")


class FirstPersonPronoun(BaseModel):
    character_name: str = Field(description="Imię postaci")
    japanese_pronoun: str = Field(description="Zaimki 1. osoby używane w dialogach: Ore, Boku, Watashi, Atashi, Sessha, Waga")
    psychological_profile: str = Field(description="Profil psychologiczny, rejestr ekspresji i ładunek emocjonalny zaimka")


class CharacterRelationship(BaseModel):
    speaker: str = Field(description="Imię postaci mówiącej")
    listener: str = Field(description="Imię postaci słuchającej / adresata")
    address_form: str = Field(description="Polska forma zwrotu grzecznościowego lub imiennego")
    relationship_type: str = Field(description="Kategoria i stopień zależności relacji między postaciami")


class GlossaryTerm(BaseModel):
    term_en: str = Field(description="Termin w języku angielskim lub japońskim")
    translation_pl: str = Field(description="Ustalony, spójny polski odpowiednik")
    explanation: str = Field(description="Wyjaśnienie kontekstu i znaczenia w świecie przedstawionym")


class DangerLinePreScan(BaseModel):
    approx_time: str = Field(description="Przybliżony czas kwestii w formacie kodowym HH:MM:SS")
    english_phrase: str = Field(description="Wieloznaczna lub zdradliwa fraza źródłowa wymagająca weryfikacji")
    speaker: Optional[str] = Field(default=None, description="Mówca kwestii")
    contextual_trap: str = Field(description="Opis pułapki kontekstowej lub pragmatyki japońskiego audio")
    contextual_guidance: str = Field(description="Deskryptywny opis kontekstu semantycznego, idiomu lub intencji postaci")


class DramaticSequence(BaseModel):
    sequence_name: str = Field(description="Nazwa i numer sekwencji dramaturgicznej")
    time_range: str = Field(description="Przedział czasowy sekwencji")
    dramatic_summary: str = Field(description="Opis dynamiki, napięcia i relacji władzy w tej części odcinka")
    dominant_tone: str = Field(description="Dominujący rejestr stylistyczny i ton emocjonalny")
    characters_present: List[str] = Field(default_factory=list, description="Postacie biorące udział w danej sekwencji czasowej")
    female_only_scene: bool = Field(default=False, description="Czy w tej sekwencji rozmawiają wyłącznie kobiety")
    male_only_scene: bool = Field(default=False, description="Czy w tej sekwencji rozmawiają wyłącznie mężczyźni")
    topology_type: Optional[str] = Field(default="DYAD", description="Topologia interakcji: SOLILOQUY (N=1, monolog/myśli), DYAD (N=2, dialog 1-na-1), POLYLOGUE (N>=3, polilog wieloosobowy)")


class RelationshipPivot(BaseModel):
    approx_time: str = Field(description="Przybliżony czas zmiany w odcinku")
    characters_involved: str = Field(description="Postacie objęte przełomem w relacji")
    nature_of_shift: str = Field(description="Przyczyna i charakter ewolucji rejestru lub dystansu")
    relational_guidance: str = Field(description="Deskryptywny opis ewolucji relacji i formy zwrotu w scenie")


class CharacterCatchphrase(BaseModel):
    character_name: str = Field(description="Imię postaci")
    original_phrase: str = Field(description="Oryginalna fraza źródłowa lub stały motyw leksykalny")
    canonical_pl: str = Field(description="Ustalony, spójny polski ekwiwalent idiomu")
    context_notes: str = Field(description="Zasada stosowania we wszystkich scenach odcinka")


class SongTranscreationPlan(BaseModel):
    song_type: str = Field(description="Typ utworu: Opening (OP), Ending (ED) lub Insert Song / Piosenka w tle")
    time_range: str = Field(description="Przedział czasowy utworu")
    metre_and_syllables: str = Field(description="Plan sylabiczny, metrum i układ rymów")
    poetic_theme: str = Field(description="Główny motyw poetycki i rejestr emocjonalny utworu")


class PunWordplayPlan(BaseModel):
    approx_time: str = Field(description="Przybliżony czas wystąpienia kalamburu")
    original_joke_or_pun: str = Field(description="Źródłowa gra słów lub wieloznaczność fonetyczna")
    polish_transcreation: str = Field(description="Autonomiczny, zabawny polski ekwiwalent fonetyczny (bez przypisów tłumacza)")


class ContinuityBridgeAlert(BaseModel):
    term_or_event: str = Field(description="Kluczowy termin, nazwa rekwizytu lub wydarzenie z przeszłości")
    canon_source_episode: str = Field(description="Źródło kanonu lub numer wcześniejszego odcinka")
    continuity_guidance: str = Field(description="Deskryptywny kontekst spójności terminologicznej i fabularnej")


class CharacterDossier(BaseModel):
    name: str = Field(description="Imię postaci")
    gender: str = Field(description="'MALE', 'FEMALE' lub 'UNKNOWN'")
    age_and_role: str = Field(description="Wiek, status społeczny i rola fabularna w relacjach postaci")
    age_class: Optional[str] = Field(default="ADULT", description="Kategoria wieku: CHILD (dziecko, dziewczynka, chłopiec), ADULT (dorosły), ELDERLY (senior, seniorzy)")
    speech_style_pl: str = Field(description="Indywidualny polski rejestr mowy postaci")
    first_person_pronoun: Optional[str] = Field(default=None, description="Japoński zaimek pierwszoosobowy i profil ego")
    speaker_entity_type: Optional[str] = Field(default="INDIVIDUAL", description="Typ tożsamości podmiotu: INDIVIDUAL, COLLECTIVE_VIRILE, COLLECTIVE_NONVIRILE, MAJESTIC_MALE, MAJESTIC_FEMALE")
    declension: Optional[str] = Field(default=None, description="Kanoniczny paradygmat odmiany przez przypadki w języku polskim (M, D, C, B, N, Ms, W)")
    dialect_category: Optional[str] = Field(default="", description="Kategoria rejestru gwarowego postaci jeśli występuje lub brak")
    idiolect_matrix: Optional[str] = Field(default="", description="Matryca idiolektu: specyficzne nawyki leksykalne, preferowane zwroty i rytm wypowiedzi dla tej postaci")
    vocal_profile: Optional[str] = Field(default="", description="Profil akustyczny i barwa głosu aktora")
    audio_transcription: Optional[str] = Field(default="", description="Próbka transkrypcji kwestii postaci w audio seiyū")


RE_JP_DIALECT_MARKERS = re.compile(
    r"\b(?:ya|yan|yade|yaro|nen|seya|akan|honma|dappe|dabe|washi|atai|wai|wagahai|jaken|koraa|suitoo|nankurunaisa|haisai|namara|shibareru|"
    r"desu\s*wa|masu\s*wa|desu\s*koto|arimasen\s*koto|masu\s*no\s*yo|naissu|ssu\s*kedo|ssu\s*ne|ssu\s*yo|ttanano|danano|kuretamae)\b|"
    r"だべ|じゃけん|やん|やで|やろ|ねん|せや|あかん|ほんま|わし|あたい|わい|吾輩|"
    r"(?:(?:いく|行(?:く)?|すっ|やる|だ)べ(?:[！？!?。、\s]|$)|(?:^|[、。\s])おら(?:は|が|の|に|を|も|たち|っち)|"
    r"(?:てる|でる|はず|だけ|こと|いい|ない|な)ある(?:よ|ね|か|な)*(?:[！？!?。、\s]|$)|"
    r"(?:いい|ない|な|何)やる(?:か|ね|よ)*(?:[！？!?。、\s]|$))|"
    r"ですわ|ますわ|ですこと|ありませんこと|ますのよ|ないっす|っすけど|っすね|っすよ|ったなの|だなの|くれたまえ",
    re.IGNORECASE
)


class EpisodeProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    episode_summary: str = Field(default="", description="Krótkie streszczenie fabuły i tonu odcinka")
    setting_and_era: str = Field(default="", description="Epoka historyczna, czas i realia świata przedstawionego")
    domain_expertise: str = Field(default="", description="Specjalistyczna dziedzina wiedzy i terminologia branżowa")
    dialogue_stylization: str = Field(default="", description="Wytyczne stylizacji rejestru języka dla danej epoki")
    manga_canon_source: Optional[str] = Field(default="", description="Oficjalne polskie wydawnictwo mangi jeśli seria była wydana w Polsce")
    tone_and_genre: str = Field(default="", description="Gatunek i dominujący ton dramaturgiczny")
    danger_lines_prescan: List[DangerLinePreScan] = Field(default_factory=list, description="Lista wyłapanych przed tłumaczeniem niebezpiecznych pułapek kontekstowych i wieloznaczności w całym odcinku")
    relationship_pivots: List[RelationshipPivot] = Field(default_factory=list, description="Punkty zwrotne i dynamiczne zmiany w relacjach/formach zwrotu w trakcie odcinka")
    character_catchphrases: List[CharacterCatchphrase] = Field(default_factory=list, description="Zamrożone kanoniczne polskie odpowiedniki dla powracających powiedzonek postaci")
    song_transcreation_plans: List[SongTranscreationPlan] = Field(default_factory=list, description="Precyzyjny plan metryczny i rymotwórczy dla piosenek")
    puns_and_wordplays: List[PunWordplayPlan] = Field(default_factory=list, description="Strategie adaptacji japońskich gier słownych i homofonów na autonomiczne polskie dowcipy")
    continuity_bridge_alerts: List[ContinuityBridgeAlert] = Field(default_factory=list, description="Ostrzeżenia i mosty ciągłości terminologicznej względem poprzednich odcinków")
    dramatic_sequences: List[DramaticSequence] = Field(default_factory=list, description="Podział odcinka na główne akty/sekwencje dramaturgiczne")
    character_dossiers: List[CharacterDossier] = Field(default_factory=list, description="Dokładne dossier i stylizacja mowy głównych bohaterów")
    name_declensions: List[NameDeclension] = Field(default_factory=list, description="Precyzyjna odmiana imion bohaterów przez wszystkie przypadki w języku polskim")
    characters: List[CharacterRelationship] = Field(default_factory=list, description="Relacje między postaciami i ustalone polskie formy zwrotu")
    glossary: List[GlossaryTerm] = Field(default_factory=list, description="Słowniczek kluczowych terminów, nazw własnych, ataków i realiów świata")
    yojijukugo_and_idioms: List[GlossaryTerm] = Field(default_factory=list, description="Wykryte 4-znakowe idiomy (Yojijukugo), przysłowia i metafory z naturalnymi polskimi ekwiwalentami")
    key_conventions: List[str] = Field(default_factory=list, description="Kluczowe wytyczne stylistyczne dla tego konkretnego odcinka")


def format_episode_profile_for_prompt(profile: Optional[EpisodeProfile]) -> str:
    """Formats episode profile into a concise system prompt block (Profiler 4.0)."""
    if not profile:
        return ""

    lines = ["=== SŁOWNICZEK, KANON MANGI, REALIA ŚWIATA I PROFIL ODCINKA (PROFILER 4.0) ==="]
    if profile.manga_canon_source:
        lines.append(f"[Oficjalny Kanon Mangi / Wydawnictwo]: {profile.manga_canon_source} (TERMINOLOGIA ZABLOKOWANA)")
    if profile.setting_and_era:
        lines.append(f"[Realia świata / Epoka]: {profile.setting_and_era}")
    if profile.domain_expertise:
        lines.append(f"[Dziedzina specjalistyczna]: {profile.domain_expertise}")
    if profile.dialogue_stylization:
        lines.append(f"[Stylizacja językowa]: {profile.dialogue_stylization}")
    if profile.episode_summary:
        lines.append(f"Fabuła odcinka: {profile.episode_summary}")
    if profile.tone_and_genre:
        lines.append(f"Ton dialogów: {profile.tone_and_genre}")

    if profile.danger_lines_prescan:
        lines.append("\nSKANER MIN JĘZYKOWYCH I PUŁAPEK WIELOZNACZNOŚCI (DANGER-LINES PRE-SCAN):")
        for dl in profile.danger_lines_prescan:
            spk = f" ({dl.speaker})" if dl.speaker else ""
            lines.append(f"• [{dl.approx_time}]{spk} '{dl.english_phrase}' -> PUŁAPKA: {dl.contextual_trap} => Znaczenie kontekstowe: {dl.contextual_guidance}")

    if profile.relationship_pivots:
        lines.append("\n🔄 PUNKTY ZWROTNE I ZMIANY RELACJI W TRAKCIE ODCINKA (RELATIONSHIP PIVOTS):")
        for rp in profile.relationship_pivots:
            lines.append(f"• [{rp.approx_time}] {rp.characters_involved}: {rp.nature_of_shift} => Relacja: {rp.relational_guidance}")

    if profile.character_catchphrases:
        lines.append("\n💬 ZAMROŻONE POWIEDZONKA I KWESTIE-WIZYTÓWKI (CATCHPHRASES):")
        for cp in profile.character_catchphrases:
            lines.append(f"• {cp.character_name}: '{cp.original_phrase}' = '{cp.canonical_pl}' ({cp.context_notes})")

    if profile.song_transcreation_plans:
        lines.append("\n🎵 MATRYCA RYMOTWÓRCZA DLA PIOSENEK OP/ED (FILAR CXVIII - BARAŃCZAK):")
        for song in profile.song_transcreation_plans:
            lines.append(f"• [{song.time_range}] {song.song_type}: Rytm: {song.metre_and_syllables} | Motyw: {song.poetic_theme}")

    if profile.puns_and_wordplays:
        lines.append("\n🃏 ADAPTACJA JAPOŃSKICH GIER SŁOWNYCH I KALAMBURÓW (PUNS & DAJARE):")
        for pun in profile.puns_and_wordplays:
            lines.append(f"• [{pun.approx_time}] {pun.original_joke_or_pun} => POLSKA ADAPTACJA: {pun.polish_transcreation}")

    if profile.continuity_bridge_alerts:
        lines.append("\n🌉 MOSTY CIĄGŁOŚCI MIĘDZYODCINKOWEJ (CONTINUITY ALERTS):")
        for ca in profile.continuity_bridge_alerts:
            lines.append(f"• [{ca.canon_source_episode}] {ca.term_or_event} => Ciągłość terminologiczna: {ca.continuity_guidance}")

    if profile.dramatic_sequences:
        lines.append("\n🗺️ MAPA SEKWENCJI DRAMATURGICZNYCH ODCINKA (DIARYZACJA OBSADY I SCEN JEDNOPŁCIOWYCH):")
        for seq in profile.dramatic_sequences:
            cast_str = f" [Obsada: {', '.join(seq.characters_present)}]" if getattr(seq, "characters_present", None) else ""
            top_str = f" [Topologia: {seq.topology_type}]" if getattr(seq, "topology_type", None) else ""
            gender_tag = ""
            if getattr(seq, "female_only_scene", False):
                gender_tag = " [Scena wyłącznie kobieca: formy żeńskie 1. i 2. os.]"
            elif getattr(seq, "male_only_scene", False):
                gender_tag = " [Scena wyłącznie męska: formy męskie 1. i 2. os.]"
            lines.append(f"• [{seq.time_range}] {seq.sequence_name}: {seq.dramatic_summary} (Ton: {seq.dominant_tone}){top_str}{cast_str}{gender_tag}")

    if profile.character_dossiers:
        lines.append("\n🎭 KARTOTEKA OBSADY I MATRYCA IDIOLEKTÓW (CHARACTER DOSSIERS & IDIOLECT MATRIX):")
        for cd in profile.character_dossiers:
            pron = f" [Zaimek: {cd.first_person_pronoun}]" if cd.first_person_pronoun else ""
            decl = f" [Odmiana: {cd.declension}]" if cd.declension else ""
            dial = f" [Dialekt: {cd.dialect_category}]" if cd.dialect_category else ""
            idio = f" [Idiolekt: {cd.idiolect_matrix}]" if cd.idiolect_matrix else ""
            voc = f" [Głos: {cd.vocal_profile}]" if getattr(cd, "vocal_profile", "") else ""
            ent = f" [Podmiot: {cd.speaker_entity_type}]" if getattr(cd, "speaker_entity_type", "") and cd.speaker_entity_type != "INDIVIDUAL" else ""
            age_t = f" [Wiek: {cd.age_class}]" if getattr(cd, "age_class", None) and cd.age_class != "ADULT" else ""
            lines.append(f"• {cd.name} ({cd.gender}, {cd.age_and_role}){age_t}{ent}{pron}{decl}{dial}{voc} -> Styl: {cd.speech_style_pl}{idio}")

    if profile.name_declensions:
        lines.append("\nŻELAZNA TABELA ODMIANY IMION PRZEZ PRZYPADKI (FILAR XCI - PARADYGMATY DEKLINACYJNE):")
        for decl in profile.name_declensions:
            lines.append(f"- {decl.character_name} ({decl.gender}): {decl.declension_summary}")

    if profile.characters:
        lines.append("\nRELACJE SPOŁECZNE I FORMY ZWROTU (KANONICZNE ZWROTY ADRESATYWNE):")
        for rel in profile.characters:
            lines.append(f"- {rel.speaker} -> {rel.listener}: {rel.address_form} ({rel.relationship_type})")

    if profile.glossary:
        lines.append("\nUSTALONY SŁOWNICZEK POJĘĆ I TERMINOLOGII BRANŻOWEJ (BAZA KANONICZNA W MIANOWNIKU):")
        for g in profile.glossary:
            lines.append(f"- '{g.term_en}' = '{g.translation_pl}' [Kontekst: {g.explanation} | Odmiana przez przypadki w zdaniu, czysta postać leksykalna bez metadanych]")

    if profile.yojijukugo_and_idioms:
        lines.append("\nEKWIWALENTY JAPOŃSKICH PRZYSŁÓW I IDIOMÓW (FILAR XCV):")
        for idi in profile.yojijukugo_and_idioms:
            lines.append(f"- '{idi.term_en}' = '{idi.translation_pl}' [Kontekst: {idi.explanation} | Adaptacja kontekstowa i fleksyjna bez metadanych w nawiasach]")

    if profile.key_conventions:
        lines.append("\nWYTYCZNE SPECYFICZNE DLA TEGO ODCINKA:")
        for conv in profile.key_conventions:
            lines.append(f"- {conv}")

    lines.append("=================================================================================\n")
    return "\n".join(lines)


def format_lean_episode_brief(profile: Any, character_audio_transcriptions: Optional[Dict[str, str]] = None, **kwargs) -> str:
    """Formats episode profile into a lean, ultra-focused brief (< 400-500 words) to prevent cognitive saturation."""
    if not profile:
        return ""

    def _get(obj, attr, default=None):
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    lines = ["=== ZWIĘZŁY MANIFEST ODCINKA (EPISODE BRIEF) ==="]
    title = _get(profile, "show_name") or _get(profile, "series_title") or _get(profile, "title")
    ep_num = _get(profile, "episode_number")
    if title:
        ep_str = f" - Odcinek {ep_num}" if ep_num else ""
        lines.append(f"• Seria: {title}{ep_str}")
    lines.append("• KLUCZOWE ZASADY AVT: Skrypt EN = treść semantyczna i fakty; Składnia i szyk wyrazów = naturalna polszczyzna; Głos seiyū = kotwica emocji, afektu i rejestru.")

    setting = _get(profile, "setting_and_era")
    tone = _get(profile, "tone_and_genre")
    if setting or tone:
        genre_info = f"{setting or ''} | {tone or ''}".strip(" |")
        lines.append(f"• Gatunek i Rejestr: {genre_info}")
        if any(h in genre_info.lower() for h in ["historyczn", "dworsk", "feudal", "średniowiecz", "starożytn", "mongol"]):
            lines.append("  Puryzm rejestru historycznego: eliminacja współczesnego słownictwa potocznego i slangu na rzecz stylizowanej polszczyzny.")

    # Characters with confirmed gender and appositions
    dossiers = _get(profile, "character_dossiers")
    rels = _get(profile, "characters")
    if dossiers or rels:
        lines.append("• Postacie i Formy Adresatywne:")
        seen = set()
        if dossiers:
            for cd in dossiers:
                name = _get(cd, "name")
                if name and name not in seen:
                    seen.add(name)
                    # Biologically guard female titles
                    g = _get(cd, "gender", "")
                    role = _get(cd, "age_and_role", "")
                    voc = _get(cd, "vocal_profile", "")
                    if any(w in str(role).lower() for w in ["cesarzowa", "chatun", "żona", "córka", "matka", "księżniczka"]):
                        g = "kobieta"
                    from series_memory import is_inherently_female_name
                    if not g and is_inherently_female_name(name):
                        g = "kobieta"
                    lines.append(f"  - {name}: {g} ({role})")
                    dial_cat = _get(cd, "dialect_category", "")
                    speech_style = _get(cd, "speech_style_pl", "")
                    idiolect = _get(cd, "idiolect_matrix", "")
                    audio_trans = _get(cd, "audio_transcription", "") or ""
                    if character_audio_transcriptions and isinstance(character_audio_transcriptions, dict):
                        audio_trans = audio_trans or character_audio_transcriptions.get(name, "") or ""
                    has_dialect_indicator = (
                        (dial_cat and any(k in str(dial_cat).lower() for k in ["gwara", "dialekt", "slang", "kansai", "tohoku", "hōgen", "yakuwarigo"]))
                        or (speech_style and any(k in str(speech_style).lower() for k in ["gwara", "dialekt", "slang", "szorstka", "środowiskowa"]))
                        or (idiolect and any(k in str(idiolect).lower() for k in ["gwara", "dialekt", "slang"]))
                        or (audio_trans and bool(RE_JP_DIALECT_MARKERS.search(str(audio_trans))))
                    )
                    style_parts = []
                    if speech_style:
                        style_parts.append(str(speech_style).strip())
                    if idiolect and idiolect != speech_style:
                        style_parts.append(str(idiolect).strip())
                    if style_parts:
                        combined_style = " | ".join(style_parts)
                        if len(combined_style) > 180:
                            combined_style = combined_style[:177] + "..."
                        lines.append(f"    Styl i idiolekt: {combined_style}")
                    if has_dialect_indicator:
                        lines.append("    Rejestr: wyrazista gwara / stylizacja środowiskowa")
                    if str(g).lower() in ("female", "kobieta") and (is_inherently_female_name(name) or any(w in (str(role) + " " + str(voc)).lower() for w in ["alt", "starsza", "dojrzała", "ochrypł", "babci", "matron", "cesarzow", "chatun", "służąc", "niewolnic", "powiernicz", "kobieta", "dziewczyn"])):
                        lines.append(f"    OCHRONA PŁCI ({name}): KOBIETA – konsekwentne stosowanie żeńskich końcówek czasu przeszłego i trybu przypuszczającego (-łam, -łabym, -łaś).") # Standard 9.0 Invariant
        if rels:
            if isinstance(rels, dict):
                for spk, info in list(rels.items())[:8]:
                    role = _get(info, "role", "") or _get(info, "age_and_role", "")
                    g = _get(info, "gender", "")
                    if not g and is_inherently_female_name(spk):
                        g = "kobieta"
                    lines.append(f"  - {spk}: {g} ({role})")
                    spk_audio = character_audio_transcriptions.get(spk, "") if character_audio_transcriptions and isinstance(character_audio_transcriptions, dict) else ""
                    if spk_audio and RE_JP_DIALECT_MARKERS.search(str(spk_audio)):
                        lines.append("    Rejestr: wyrazista gwara / stylizacja środowiskowa")
            else:
                for rel in rels[:8]:
                    spk = _get(rel, "speaker")
                    lis = _get(rel, "listener")
                    addr = _get(rel, "address_form")
                    lines.append(f"  - {spk} -> {lis}: {addr}")

    decls = _get(profile, "name_declensions")
    if decls:
        lines.append("• Odmiana Imion i Tytułów:")
        if isinstance(decls, dict):
            for c_name, summary in list(decls.items())[:6]:
                lines.append(f"  - {c_name}: {summary}")
        else:
            for decl in decls[:6]:
                c_name = _get(decl, "character_name")
                summary = _get(decl, "declension_summary")
                lines.append(f"  - {c_name}: {summary}")

    gloss = _get(profile, "glossary")
    if gloss:
        lines.append("• Zablokowana Terminologia:")
        if isinstance(gloss, dict):
            for t_en, t_pl in list(gloss.items())[:10]:
                lines.append(f"  - {t_en} = {t_pl}")
        else:
            for g in gloss[:10]:
                t_en = _get(g, "term_en")
                t_pl = _get(g, "translation_pl")
                lines.append(f"  - {t_en} = {t_pl}")

    lines.append("• TOPOLOGIA SCENY I OCHRONA PŁCI:")
    lines.append("  - Spójność rodzaju gramatycznego mówcy i adresata: stosuj formy żeńskie (-łam, -łabym, -łaś) oraz niemęskoosobowe dla potwierdzonych postaci żeńskich z bazy serii.")


    lines.append("================================================")
    return "\n".join(lines)


class EpisodeProfiler:
    @staticmethod
    def sanitize_event_asr(
        raw_asr: Optional[str],
        is_sign: bool = False,
        style: Optional[str] = None,
        duplicate_time_distance_sec: Optional[float] = None,
        consecutive_streak: int = 1,
        **kwargs
    ) -> str:
        """
        Sanityzuje pomocniczą transkrypcję ASR dla zdarzenia dialogowego (Standard 9.4, 2B.8.a, 2C.10, R1.1, R3.5, R3.6):
        - Dla szyldów, tytułów odcinka (is_sign: true lub style w ("sign", "title", "ep title", "napis", "caption", "szyld"))
          zwraca pusty string "", zapobiegając zanieczyszczeniu przekładu obcym audio w tle.
        - Jeśli identyczny ciąg ASR wystąpił w zdarzeniu oddalonym o > 1.5 s lub w serii > 2 kolejnych linii (consecutive_streak > 2), zeruje duplikat ("").
        - Filtruje halucynacje Whisper: łacińskie tokeny ASCII w japońskim audio, ciągi powtórzeniowe > 2 oraz izolowane znaki/interpunkcję.
        - Zachowuje en_text jako nadrzędny autorytet semantyczny.
        """
        raw_asr = kwargs.get("asr_text", raw_asr)
        if is_sign or not raw_asr:
            return ""
        if style:
            s_clean = str(style).strip().lower()
            if any(token in s_clean for token in ("sign", "title", "napis", "caption", "szyld")):
                return ""
        if duplicate_time_distance_sec is not None and float(duplicate_time_distance_sec) > 1.5:
            return ""
        if consecutive_streak > 2:
            return ""

        text = str(raw_asr).strip()
        if not text:
            return ""

        # Standard 9.7 (Operacja 2C.4): Wycinanie artefaktowych klastrów znaków zapytania i cyfr (.? ??000 / ???000)
        has_cjk_init = bool(re.search(r"[぀-ヿ㐀-䶿一-鿿]", text))
        if has_cjk_init:
            text = re.sub(r"[.,!?\s]*\?+[\s?0-9.,!]*", "", text)
            text = re.sub(r"0{2,}", "", text)
            text = re.sub(r"\s+", " ", text).strip()
        else:
            text = re.sub(r"[.,!?\s]*\?+[\s?0-9.,!]*", " ", text)
            text = re.sub(r"0{2,}", "", text)
            text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""

        # Isolated punctuation or single characters (. / k / n)
        if re.fullmatch(r"[\W_]*[a-zA-Z0-9]?[\W_]*", text) and not re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", text):
            return ""

        # Character repetitions > 2 (e.g. sss, aaasss)
        if re.search(r"([a-zA-Z])\1{2,}", text):
            cleaned = re.sub(r"([a-zA-Z])\1{2,}", "", text).strip()
            if not cleaned or not re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", cleaned):
                return ""
            text = cleaned

        # Punctuation repetitions > 2 (e.g. just,,,)
        if re.search(r"([,\.;:!?])\1{2,}", text):
            cleaned = re.sub(r"([,\.;:!?])\1{2,}", "", text).strip()
            if not cleaned or not re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", cleaned):
                return ""
            text = cleaned

        # Hallucinatory word repetition (e.g. You you...)
        if re.search(r"\b([a-zA-Z]{2,})\s+\1", text, re.IGNORECASE):
            if not re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", text):
                return ""

        has_cjk = bool(re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", text))
        if has_cjk:
            # Standard 9.6 (Operacja 2C.3): Usuwanie sklejonych i luźnych tokenów ASCII [A-Za-z]+ oraz osieroconych partykuł nagłosowych
            # Standard 9.7 (Operacja 2C.4): Wycinanie artefaktowych klastrów znaków zapytania i cyfr (.? ??000)
            parts = re.split(r"(\[[^\]]*\]|\([^\)]*\))", text)
            for i in range(0, len(parts), 2):
                p = parts[i]
                p = re.sub(r"[.,!?\s]*\?+[\s?0-9.,!]*", "", p)
                p = re.sub(r"0{2,}", "", p)
                # Krok 1: Usuń prefiks ASCII wraz z bezpośrednio przylegającą osieroconą partykułą enklityczną
                p = re.sub(
                    r"^\s*[A-Za-z0-9_,\s.;:!?-]+[とのがはをにへで](?=[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF])",
                    "",
                    p,
                )
                # Krok 2: Usuń pozostałe tokeny łacińskie ASCII
                p = re.sub(r"[A-Za-z]+[,.;:!?\s]*", "", p)
                p = re.sub(r"[,.;:!?\s]*[A-Za-z]+", "", p)
                p = re.sub(r"^[,\.;:!?\s]+|[,\.;:!?\s]+$", "", p)
                parts[i] = p
            cleaned_text = " ".join([p.strip() for p in parts if p.strip()]).strip()
            cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

            # Zlicz pozostałe znaki japońskie Kana/Kanji w segmencie
            cjk_matches = re.findall(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]", cleaned_text)
            if len(cjk_matches) <= 1:
                return ""
            return cleaned_text
        else:
            # Standard 9.7 (Operacja 2C.4): Wycinanie artefaktów zapytajnikowo-cyfrowych w segmencie bez CJK
            text = re.sub(r"[.,!?\s]*\?+[\s?0-9.,!]*", "", text)
            text = re.sub(r"0{2,}", "", text)
            text = re.sub(r"^[,\.;:!?\s]+|[,\.;:!?\s]+$", "", text)
            text = re.sub(r"\s+", " ", text).strip()
            # Standard 9.6 (Operacja 2C.3): Czysto łacińskie tokeny ASR (cjk_count == 0) oraz halucynacje Whisper
            whisper_spam_pat = re.compile(
                r"\b(?:subtitles?|amara(?:\.org)?|translat\w+|copyright|watch\w*|subscri\w*|youtube|licensed|all rights reserved|episode|chapter)\b",
                re.IGNORECASE
            )
            if re.fullmatch(r"^[A-Za-z0-9_.,!?'\" -]+$", text):
                if len(text.split()) <= 1 or whisper_spam_pat.search(text):
                    return ""
            elif whisper_spam_pat.search(text):
                return ""
            return text

    @staticmethod
    def reconcile_prepass_with_p0(
        dramatic_sequences: List[Any],
        series_bible: Optional[Any] = None
    ) -> List[Any]:
        """
        Uzgadnia statystyki obsady sekwencji dramaturgicznych pre-passu z rekordami P0 z SeriesBible (Operacja 2B.9, R3.2):
        - Dla każdej postaci obecnej w danej sekwencji (characters_present) pobiera p0_gender z SeriesBible.
        - Nadrzędny priorytet: p0_gender z SeriesBible (has_verified_gender: true lub priority P0/P1) ma pierwszeństwo
          wobec estymacji akustycznej F0.
        - Estymacja F0 służy wyłącznie jako fallback dla postaci spoza P0 (gender UNKNOWN / brak w SeriesBible).
        - Wymusza spójne flagi female_only_scene / male_only_scene.
        """
        if not dramatic_sequences or not series_bible:
            return dramatic_sequences or []

        reconciled = []
        for seq in dramatic_sequences:
            is_model = hasattr(seq, "model_copy") or hasattr(seq, "copy")
            chars_present = getattr(seq, "characters_present", None)
            if chars_present is None and isinstance(seq, dict):
                chars_present = seq.get("characters_present", [])
            chars_present = chars_present or []

            verified_genders = []
            for ch_name in chars_present:
                ch_entry = None
                if hasattr(series_bible, "get_character"):
                    ch_entry = series_bible.get_character(ch_name)
                elif hasattr(series_bible, "characters") and isinstance(series_bible.characters, dict):
                    ch_entry = series_bible.characters.get(ch_name)

                if ch_entry:
                    g = getattr(ch_entry, "gender", None) or (ch_entry.get("gender") if isinstance(ch_entry, dict) else None)
                    prio = getattr(ch_entry, "priority", None) or (ch_entry.get("priority") if isinstance(ch_entry, dict) else None)
                    has_v = getattr(ch_entry, "has_verified_gender", False) if hasattr(ch_entry, "has_verified_gender") else (ch_entry.get("has_verified_gender", False) if isinstance(ch_entry, dict) else False)
                    if g in ("MALE", "FEMALE") and (has_v or prio in ("P0", "P1")):
                        verified_genders.append(g)

            if verified_genders:
                fem_count = sum(1 for g in verified_genders if g == "FEMALE")
                male_count = sum(1 for g in verified_genders if g == "MALE")
                new_fem_only = (fem_count > 0 and male_count == 0)
                new_male_only = (male_count > 0 and fem_count == 0)
                if is_model:
                    setattr(seq, "female_only_scene", new_fem_only)
                    setattr(seq, "male_only_scene", new_male_only)
                elif isinstance(seq, dict):
                    seq["female_only_scene"] = new_fem_only
                    seq["male_only_scene"] = new_male_only
            reconciled.append(seq)
        return reconciled

    def __init__(self, client: Any, model: str = "gemini-3.5-flash-lite"):
        self.client = client
        if hasattr(client, "clients") and hasattr(client, "get_client"):
            self.client_pool = client
        else:
            from client_factory import MultiKeyClientPool
            timeout_sec = float(os.getenv("GEMINI_HTTP_TIMEOUT_SEC", "90.0"))
            self.client_pool = MultiKeyClientPool(raw_keys=os.getenv("GEMINI_API_KEY"), timeout_sec=timeout_sec)
        self.model = model

    def profile_episode(
        self,
        subs_text_sample: str,
        anime_metadata_str: str = "",
        cache_path: Optional[str] = None
    ) -> EpisodeProfile:
        """
        Generates or loads episode profile from cache (Profiler 4.0 Pre-pass).
        """
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Loaded episode profile from cache: {cache_path}")
                    return EpisodeProfile.model_validate(data)
            except Exception as e:
                logger.warning(f"Error reading profile cache ({e}), regenerating...")

        prompt = f"""Jesteś Głównym Reżyserem, Konsultantem Merytorycznym i Script Doctorem Lokalizacji Anime (Profiler 4.0).
• Głos seiyū stanowi nadrzędny punkt odniesienia: PIERWOTNE ŹRÓDŁO PRAWDY dla rejestru emocjonalnego, intonacji i afektu.
• Akty mowy seiyū: uciszanie i irytacja (urusai, damare) – naturalna polszczyzna sytuacyjna, bez anachronizmów typu żenada.
Twoim zadaniem jest dogłębna, wszechstronna analiza całego skryptu odcinka, aby przygotować kompletny profil lingwistyczno-dramaturgiczny:

1. OFICJALNY KANON POLSKIEGO WYDANIA MANGI: Identyfikacja licencjonowanego wydawnictwa papierowego i ustalenie oficjalnego nazewnictwa z wydań drukowanych.
   - Przydomki postaci w polszczyźnie twórz przez apozycję mianownikową lub tradycyjny epitet, eliminując mechaniczne kalkowanie konstrukcji dopełniaczowych.
2. SKANER PUŁAPEK JĘZYKOWYCH, ŚRODOWISKOWYCH I PRAGMATYCZNYCH (danger_lines_prescan / FILAR CLXVI): Przeskanuj cały odcinek i wskaż zdradliwe kwestie źródłowe: # Standard 9.0 Invariant
   - Idiomy i odmowy: kontekstowa odmowa udziału w miejsce pozornego stanu zdrowia, specyfika formuł grzecznościowych i kolektywnych.
   - Paradoks pytań przeczących: potwierdzenie lub zaprzeczenie w języku źródłowym po pytaniu przeczącym wymaga logicznego uzgodnienia polskiej odpowiedzi negacyjnej.
   - Pozorne pokrewieństwo: zwroty rodzinne kierowane do obcych osób w przestrzeni publicznej podlegają konwersji na polskie formy grzecznościowe.
   - Stan rezultatywny: konstrukcje wyrażające dokonany stan śmierci wymagają formy przymiotnikowej lub imiesłowowej zamiast trwającej czynności.
   - Pytania retoryczne i afektywne: konstrukcje z podniesioną intonacją wyrażające zachwyt wymagają naturalnych polskich wykrzykników ekspresywnych.
   - Fizyczność sceny: topologia przestrzeni i fizyka środowiska determinują dobór słownictwa (brak wody w przestrzeni kosmicznej, specyfika lokacji).
3. PUNKTY ZWROTNE I EWOLUCJA RELACJI (relationship_pivots): Wskaż momenty w odcinku, w których następuje przełom i zmiana rejestru grzecznościowego lub stopnia zażyłości, stabilizując trajektorię więzi między postaciami.
4. POWIEDZONKA I KWESTIE PRZEWODNIE (character_catchphrases): Ustal jednolitą, kanoniczną polską postać dla powtarzających się motywów leksykalnych postaci.
5. MATRYCA METRYCZNA DLA PIOSENEK (song_transcreation_plans): Rozpoznaj utwory wokalne i opracuj plan sylabiczny, metrum oraz układ rymów.
6. KALAMBURY I GRY SŁOWNE (puns_and_wordplays): Opracuj autonomiczne polskie gry słowne i ekwiwalenty fonetyczne dla wieloznaczności źródłowych bez wprowadzania przypisów odautorskich.
7. MOSTY CIĄGŁOŚCI (continuity_bridge_alerts): Wskaż terminy i wątki wymagające ścisłej spójności w skali całej serii.
8. CHRONOLOGICZNA MAPA SEKWENCJI DRAMATURGICZNYCH (dramatic_sequences): Podziel odcinek na akty czasowe z określeniem dynamiki napięcia i tonu.
   - Dla każdej sekwencji wskaż postacie biorące udział w dialogu, rekonstruując brakujące dane aktora.
   - Prymat rzeczywistości scenicznej i audio nad etykietami technicznymi: weryfikuj tożsamość i płeć na podstawie dialogu i ścieżki dźwiękowej. Flaga female_only_scene przyjmuje wartość True wyłącznie przy pełnej obsadzie kobiecej (min. 2 uczestniczki) i braku męskich głosów w scenie. Kwestie pojedyncze i monologi zachowują stan neutralny.
   - W scenach o potwierdzonym, wyłącznie kobiecym składzie uczestników formy 1. osoby liczby mnogiej podlegają rygorowi form niemęskoosobowych.
   - W scenach o potwierdzonym składzie męskim lub mieszanym formy 1. osoby liczby mnogiej przyjmują formy męskoosobowe. Brak pełnej pewności zachowuje stan neutralny.
9. KARTOTEKA OBSADY I IDIOLEKTY (character_dossiers): Określ wiek, status, zaimki podmiotowe, dialekt oraz indywidualny rejestr polszczyzny dla każdej postaci.
10. DEKLINACJA IMION I NAZW WŁASNYCH (name_declensions) ORAZ MATRYCA RELACJI (characters):
   - Fleksja imion obcych: imiona męskie zakończone na spółgłoskę podlegają pełnej fleksji przez wszystkie przypadki gramatyczne.
   - Dopełniacz dzierżawczy nazw obcych tworzy regularną formę polskiego dopełniacza bez mechanicznego powielania formy bazowej.
   - Imiona męskie zakończone na samogłoskę a: wymagają męskich form orzeczeń w czasie przeszłym zgodnie z tożsamością ontologiczną postaci.
   - Spójność podmiotowa monologów: wypowiedzi narracyjne i myśli zachowują jednolitą tożsamość gramatyczną rodzaju w całej klauzuli i sekwencji.
   - Fleksja fonetyczna imion męskich na ca (do Luki): twarda wymowa spółgłoski tylnojęzykowej determinuje alternację tematu w przypadkach zależnych. # Standard 9.0 Invariant
   - Rozróżnienie nazw własnych i pojęć pospolitych (Ouji): japońskie rzeczowniki pospolite, role społeczne i tytuły podlegają przekładowi słownikowemu jako pojęcia apelatywne. # Standard 9.0 Invariant
   - Spolszczanie honoryfikatorów i relacji starszeństwa (Senpai): relacje hierarchiczne w relacjach szkolnych nie wprowadzają tytulatury Panno ani zwrotów obcych. # Standard 9.0 Invariant
   - Nadrzędność kanonu mangowego (Potworny Królewicz): oficjalne polskie wydania drukowane wyznaczają nadrzędny priorytet nazewnictwa terminów i przydomków. # Standard 9.0 Invariant
   - Propagacja przypadka przy współrzędności (Harugona): połączone spójnikiem człony podlegają uzgodnieniu w tym samym przypadku gramatycznym wymaganym przez rząd czasownika. # Standard 9.0 Invariant
   - Standard zapisu kwestii dialogowych (eliminacja samotnych myślników): myślnik dialogowy stosowany jest wyłącznie w wypowiedziach dwugłosowych w ramach jednej planszy. # Standard 9.0 Invariant
   - Interpunkcja zdań rozłącznych: pytania alternatywne połączone spójnikiem czy nie wymagają przecinka przed spójnikiem.
   - Pragmatyka dopytywania o ciąg dalszy (I co z tego?): dociekliwe pytania nawiązujące tłumaczone są zwięzłymi formułami zaciekawienia. # Standard 9.0 Invariant
   - Weryfikacja tożsamości ról zawodowych: nazwy profesji i funkcji nie determinują automatycznie cech gramatycznych bez weryfikacji kontekstowej.
   - Rozpoznanie adresata w dialogu: bezpłciowy zaimek 2. osoby języka źródłowego podlega precyzyjnemu rozróżnieniu na polskie formy rodzaju i liczby:
      * Pojedyncza kobieta jako adresatka: orzeczenia czasu przeszłego i orzeczniki przymiotnikowe przyjmują formy żeńskie.
      * Pojedynczy mężczyzna jako adresat: orzeczenia czasu przeszłego i orzeczniki przymiotnikowe przyjmują formy męskie.
      * Grupa kobiet jako adresat: orzeczenia i zaimki przyjmują formy niemęskoosobowe.
      * Grupa zawierająca mężczyzn: formy 2. osoby liczby mnogiej przyjmują formy męskoosobowe.
   - Spójność rejestru tytularnego:
      * Jednolitość formuły adresatywnej (INTRA-CLAUSE T-V HYBRID BAN): unikanie łączenia bezpośredniego wołacza imiennego z formami grzecznościowymi w obrębie tej samej klauzuli.
      * Ochrona relacji hierarchicznych (ENGLISH '-SAMA' DROP IMMUNITY): zawołania i apele respektują stały dystans społeczny między rozmówcami.
      * Stabilność formy podmiotu przy tytulaturze: rzeczownik tytularny w pozycji podmiotu zachowuje mianownikową formę imienia. # Standard 9.0 Invariant
   - Rekcja w konstrukcjach matrymonialnych i wymiany: związki frazeologiczne z przyimkiem za rządzą biernikiem.
   - Dostosowanie rejestru stylistycznego: gatunki historyczne i wysokie fantasy wymagają literackiej polszczyzny dialogowej wolnej od kolokwializmów.
11. SŁOWNIK POJĘĆ BRANŻOWYCH ORAZ FRAZEOLOGIZMÓW: Podawaj czyste, docelowe ekwiwalenty polskie bez technicznych dopisków nawiasowych.
12. EPOKA, REALIA ŚWIATA I SPECYFIKA TEMATYCZNA.
13. POPRAWNOŚĆ ORTOGRAFICZNA I FONETYCZNA:
   - Eliminacja literówek i deformacji morfonologicznych w dialogach i glosariuszu.
   - Czasowniki w 1. osobie czasu przyszłego zachowują kanoniczny temat fleksyjny.
14. DYSCYPLINA WIZUALNA AVT I NATURALNOŚĆ DIALOGU:
   - Dźwięki wysiłku fizycznego i odgłosy kinestetyczne podlegają elipsie napisu w polskiej szkole przekładu audiowizualnego.
   - Gesty podawania rekwizytów adaptowane są na naturalne polskie formuły interakcyjne lub podlegają elipsie.
   - Eliminacja pleonazmów i kalk idiomatycznych (Come back in one piece, get your hopes up, Die at the hands of) na rzecz utrwalonych związków frazeologicznych. # Standard 9.0 Invariant
15. DYSKONTINUITET CZASOWY I GRANICE MONTAŻOWE:
   - Analiza kwestii przedzielonych pauzą montażową lub zmianą sceny pod kątem odświeżenia otwarcia dialogu.
   - Eliminacja fałszywego przenikania spójników i ładunku afektywnego przez cięcia montażowe.
16. PROTOKÓŁ NATURALIZACJI DIALOGOWEJ:
   - Zwroty powrotu, pożegnania i życzenia podlegają adaptacji na rodzime idiomy konwersacyjne.
   - Tytulatura szkolna i relacje mentorskie odzwierciedlają naturalne polskie zwyczaje językowe.
   - Fleksja zamówień gastronomicznych wymaga biernika jako dopełnienia bliższego.
   - Okrzyki sytuacyjne i pirotechniczne adaptowane są na naturalne polskie wykrzykniki wrażeniowe.
   - Relacje rówieśnicze posługują się bezpośrednim rejestrem bez sztucznej tytulatury.
   - Niezmienność dystansu w relacjach zawodowych i redakcyjnych.
   - Ograniczenie nadmiarowej interpunkcji ekspresywnej w napisach.
   - Plansze tytułowe i napisy wielowersowe podlegają podziałowi zgodnie z cezurą składniową.
   - Dialogi symultaniczne w jednym kadrze rozbijane są na odrębne wersy z myślnikami.
   - Liczebniki w pozycji podmiotu uzgadniają orzeczenie w liczbie mnogiej.
   - Eliminacja współczesnego socjolektu młodzieżowego, wulgaryzmów podwórkowych i trywializacji w gatunkach kostiumowych i fantasy.
   - Rzeczowniki o określonym rodzaju gramatycznym zachowują właściwy związek zgody przymiotników i zaimków.
   - Obce nazwiska i przydomki podlegają regularnej deklinacji w zawołaniach.
   - Precyzyjna identyfikacja adresata w kwestiach wołaczowych bez przypisywania własnego miana mówcy.
17. SKŁADNIA OKOLICZNIKOWA KONSTRUKCJI CZASOWYCH:
   - Dekompozycja obcych przydawek temporalnych na naturalne polskie wyrażenia okolicznikowe czasu.
18. DYSCYPLINA IDIOLEKTU I PRYMAT MORFOLOGICZNY PŁCI (SPEAKER-SCOPED HYPOCORISM GUARD & INHERENT GENDER & 1ST-PERSON MORPHOLOGY): # Standard 9.0 Invariant
   - Zdrobnienia afektywne ograniczone są do właściwych relacji między konkretnymi postaciami (eliminacja wycieku rówieśniczego [Zdrobniała Ksywka]). # Standard 9.0 Invariant
   - Spójność morfologiczna form 1. osoby czasu przeszłego z potwierdzoną płcią postaci.
19. PRYWAT GŁOSU SEIYU I AKTY MOWY:
   - Ścieżka dźwiękowa i ekspresja aktorska stanowią pierwotną podstawę interpretacji intencji dramatycznej.
   - Zróżnicowanie pragmatycznych aktów mowy: irytacji, znużenia, dystansu emocjonalnego.
   - Formuły powitań domowych (Tadaima, Wróciłaś): eliminacja echa powitań aisatsu na rzecz symetrycznych zwrotów domowników. # Standard 9.0 Invariant
   - Zestawienie tytułu z nazwiskiem w podmiocie zachowuje formę mianownikową ([Tytuł] [Imię Nazwisko] nie zdążył). # Standard 9.0 Invariant
20. TOŻSAMOŚĆ PODMIOTOWA I BYTY ZBIOROWE:
   - Klasyfikacja tożsamości podmiotu: byty pojedyncze, byty kolektywne męskoosobowe lub niemęskoosobowe, formy majestatyczne.
21. ELIMINACJA INTERFERENCJI SKŁADNIOWEJ:
   - Eliminacja nadmiaru zaimków dzierżawczych przy częściach ciała i relacjach inalienabilnych.
   - Stosowanie naturalnej polskiej elipsy orzeczeniowej w odpowiedziach potwierdzających i przeczących.
   - Wektory ruchu sytuacyjnego tłumaczone ze stanowiska obserwatora sceny.
   - Redukcja pleonazmów zmysłowych i przestrzennych w scenach z jednoznacznym obrazem.
   - Eliminacja dublowania deskryptorów kategorialnych przy toponimach.
   - Ontologiczna kategoryzacja bytów na ANTHROPONYM, TOPONYM oraz CHREMATONYM z poprawną rekcją przyimkową.

METADANE Z BAZY ANILIST:
{anime_metadata_str}

PEŁNY SKRYPT DIALOGOWY CAŁEGO ODCINKA (100% TREŚCI):
{subs_text_sample[:100000]}

Zwróć wynik w formacie JSON zgodnym ze schematem EpisodeProfile."""

        import time
        attempt = 0

        while True:
            attempt += 1
            try:
                gen_config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": EpisodeProfile,
                }
                if is_gemini_4_or_hydrogen_model(self.model):
                    gen_config_kwargs["thinking_config"] = build_thinking_config(self.model, 0)
                else:
                    gen_config_kwargs["temperature"] = 0.2
                    if any(k in self.model.lower() for k in ["3.7", "3.8", "flash", "pro"]) and "lite" not in self.model.lower():
                        gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

                active_client = self.client_pool.get_client() if self.client_pool else self.client
                response = active_client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**gen_config_kwargs)
                )
                profile_data = json.loads(response.text)
                profile = EpisodeProfile.model_validate(profile_data)

                if cache_path:
                    try:
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                if attempt > 1:
                    print(f"  └─ [OK / Profiler]: Połączenie z Google API przywrócone.")
                return profile
            except Exception as e:
                err_str = str(e).lower()
                is_billing_exhausted = "prepayment" in err_str or "depleted" in err_str or ("billing" in err_str and "credit" in err_str)
                if is_billing_exhausted:
                    print("\n" + "!" * 75)
                    print("  [!] [LIMIT KONTA GOOGLE AI STUDIO / PŁATNOŚCI]:")
                    print("  Wyczerpały się środki przedpłacone (Prepayment Credits / Limit wydatków)!")
                    print("  Komunikat Google: 'Your prepayment credits are depleted.'")
                    print("  -> Wejdź na https://aistudio.google.com/ i doładuj środki, aby kontynuować.")
                    print("!" * 75 + "\n")
                    raise RuntimeError("Wyczerpane środki na koncie Google AI Studio (Prepayment Credits Depleted).")

                import random
                # Zero-Wait Multi-Key Hopping (200ms between keys; micro-pause after full key round)
                num_keys = len(self.client_pool.clients) if hasattr(self, "client_pool") and self.client_pool and hasattr(self.client_pool, "clients") else 1
                if attempt % max(1, num_keys) != 0:
                    wait_sec = 0.2 + random.uniform(0.05, 0.15)
                else:
                    cycle = attempt // max(1, num_keys)
                    wait_sec = min(3.0, 0.6 + 0.4 * min(cycle, 4) + random.uniform(0.1, 0.3))

                is_timeout = "504" in err_str or "deadline" in err_str or "timeout" in err_str or "timed out" in err_str
                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str
                
                friendly_msg = format_friendly_api_error(e)
                if attempt == 1:
                    print(f"\n[Profiler Odcinka]: {friendly_msg} -> oczekiwanie na serwery Google i automatyczna rotacja kluczy...")
                time.sleep(wait_sec)


def parse_approx_time_ms(time_str: str) -> Optional[int]:
    """
    Parses approximate time string (e.g. '00:16:39', '16:39', '00:16:39.25', '00:16:39,250') into milliseconds.
    """
    if not time_str or not isinstance(time_str, str):
        return None
    cleaned = time_str.strip().replace(",", ".")
    m = re.match(r"^(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)$", cleaned)
    if not m:
        return None
    hours = int(m.group(1)) if m.group(1) else 0
    mins = int(m.group(2))
    secs = float(m.group(3))
    return int((hours * 3600 + mins * 60 + secs) * 1000)


def _extract_text_and_times_from_event(event_item: Any) -> Tuple[int, int, str]:
    """
    Normalizes event structure to (start_ms, end_ms, clean_text).
    Supports pysubs2.SSAEvent, raw entry tuple (orig_idx, event, text, ...), or dict.
    """
    if hasattr(event_item, "start") and hasattr(event_item, "end") and hasattr(event_item, "text"):
        clean_t = re.sub(r"\{[^\}]*\}", "", event_item.text).strip()
        clean_t = re.sub(r"\\[Nnh]", " ", clean_t).strip()
        return event_item.start, event_item.end, clean_t
    elif isinstance(event_item, (list, tuple)) and len(event_item) >= 3:
        ev = event_item[1]
        raw_text = str(event_item[2])
        clean_t = re.sub(r"\{[^\}]*\}", "", raw_text).strip()
        clean_t = re.sub(r"\\[Nnh]", " ", clean_t).strip()
        start = getattr(ev, "start", 0)
        end = getattr(ev, "end", 0)
        return start, end, clean_t
    elif isinstance(event_item, dict):
        start = event_item.get("start_ms", 0)
        end = event_item.get("end_ms", 0)
        clean_t = event_item.get("en", "")
        return start, end, clean_t
    return 0, 0, ""


def resolve_profile_alerts_to_events(
    profile: EpisodeProfile,
    subs_events: List[Any],
    max_time_window_ms: int = 15000
) -> Dict[int, List[str]]:
    """
    Deterministic Pre-pass Line Resolver.
    Binds Profiler alerts (danger_lines_prescan, character_catchphrases, puns_and_wordplays)
    to concrete subtitle line indices based on time-window proximity and token Jaccard similarity.
    Returns: Dict[line_index, List[formatted_alert_tag]]
    Guarantees 0.00 PLN cost and 100% precision without brittle substring containment.
    """
    if not profile or not subs_events:
        return {}

    resolved_alerts: Dict[int, List[str]] = {}

    def _tokenize(text: str) -> Set[str]:
        return set(re.findall(r"\b[a-zA-Z0-9ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{2,}\b", (text or "").lower()))

    def _jaccard(s1: Set[str], s2: Set[str]) -> float:
        if not s1 or not s2:
            return 0.0
        return len(s1 & s2) / float(len(s1 | s2))

    orig_idx_map: Dict[int, int] = {}
    parsed_events: List[Tuple[int, int, int, str, Set[str]]] = []
    for idx, ev_item in enumerate(subs_events):
        s_ms, e_ms, txt = _extract_text_and_times_from_event(ev_item)
        parsed_events.append((idx, s_ms, e_ms, txt, _tokenize(txt)))
        if isinstance(ev_item, (list, tuple)) and len(ev_item) > 0 and isinstance(ev_item[0], int):
            orig_idx_map[idx] = ev_item[0]

    # 1. Resolve danger_lines_prescan
    if getattr(profile, "danger_lines_prescan", None):
        for dl in profile.danger_lines_prescan:
            if not dl.english_phrase:
                continue
            target_ms = parse_approx_time_ms(dl.approx_time)
            phrase_tokens = _tokenize(dl.english_phrase)
            phrase_clean = dl.english_phrase.strip().lower()

            best_idx = None
            best_score = -1.0

            for idx, s_ms, e_ms, txt, ev_tokens in parsed_events:
                txt_clean = txt.lower()
                time_dist_ms = abs(s_ms - target_ms) if target_ms is not None else 0

                # Window check
                if target_ms is not None and time_dist_ms > max_time_window_ms:
                    continue

                j_sim = _jaccard(phrase_tokens, ev_tokens)
                is_sub = (phrase_clean in txt_clean) or (txt_clean in phrase_clean and len(txt_clean) >= 6)

                if is_sub or j_sim >= 0.35 or len(phrase_tokens & ev_tokens) >= max(2, len(phrase_tokens) - 1):
                    time_penalty = (time_dist_ms / 1000.0) if target_ms is not None else 0.0
                    score = (1.0 if is_sub else j_sim) * 100.0 - time_penalty
                    if score > best_score:
                        best_score = score
                        best_idx = idx

            # Fallback across entire episode if time window was too narrow
            if best_idx is None and target_ms is not None:
                for idx, s_ms, e_ms, txt, ev_tokens in parsed_events:
                    txt_clean = txt.lower()
                    is_sub = (phrase_clean in txt_clean) or (txt_clean in phrase_clean and len(txt_clean) >= 6)
                    j_sim = _jaccard(phrase_tokens, ev_tokens)
                    if is_sub or j_sim >= 0.5:
                        score = (1.0 if is_sub else j_sim) * 100.0
                        if score > best_score:
                            best_score = score
                            best_idx = idx

            if best_idx is not None:
                guide = dl.contextual_guidance
                tag = f"[TELEMETRIA: pułapka_profilera: {dl.contextual_trap} | wskazówka: {guide}]"
                if best_idx not in resolved_alerts:
                    resolved_alerts[best_idx] = []
                if tag not in resolved_alerts[best_idx]:
                    resolved_alerts[best_idx].append(tag)

    # 2. Resolve character_catchphrases
    if getattr(profile, "character_catchphrases", None):
        for cp in profile.character_catchphrases:
            if not cp.original_phrase:
                continue
            cp_tokens = _tokenize(cp.original_phrase)
            cp_clean = cp.original_phrase.strip().lower()
            tag = f"[💬 KWESTIA-WIZYTÓWKA: '{cp.canonical_pl}']"

            for idx, s_ms, e_ms, txt, ev_tokens in parsed_events:
                if cp_clean in txt.lower() or _jaccard(cp_tokens, ev_tokens) >= 0.6:
                    if idx not in resolved_alerts:
                        resolved_alerts[idx] = []
                    if tag not in resolved_alerts[idx]:
                        resolved_alerts[idx].append(tag)

    # 3. Resolve puns_and_wordplays
    if getattr(profile, "puns_and_wordplays", None):
        for pun in profile.puns_and_wordplays:
            if not pun.original_joke_or_pun:
                continue
            target_ms = parse_approx_time_ms(getattr(pun, "approx_time", ""))
            pun_tokens = _tokenize(pun.original_joke_or_pun)
            pun_clean = pun.original_joke_or_pun.strip().lower()
            tag = f"[🃏 GRA SŁOWNA: {pun.polish_transcreation}]"

            best_idx = None
            best_score = -1.0
            for idx, s_ms, e_ms, txt, ev_tokens in parsed_events:
                time_dist_ms = abs(s_ms - target_ms) if target_ms is not None else 0
                if target_ms is not None and time_dist_ms > max_time_window_ms:
                    continue
                is_sub = pun_clean in txt.lower()
                j_sim = _jaccard(pun_tokens, ev_tokens)
                if is_sub or j_sim >= 0.35:
                    score = (1.0 if is_sub else j_sim) * 100.0 - ((time_dist_ms / 1000.0) if target_ms else 0)
                    if score > best_score:
                        best_score = score
                        best_idx = idx

            if best_idx is not None:
                if best_idx not in resolved_alerts:
                    resolved_alerts[best_idx] = []
                if tag not in resolved_alerts[best_idx]:
                    resolved_alerts[best_idx].append(tag)

    if orig_idx_map:
        for seq_idx, alerts in list(resolved_alerts.items()):
            if seq_idx in orig_idx_map:
                o_idx = orig_idx_map[seq_idx]
                if o_idx not in resolved_alerts:
                    resolved_alerts[o_idx] = list(alerts)
                else:
                    for a in alerts:
                        if a not in resolved_alerts[o_idx]:
                            resolved_alerts[o_idx].append(a)

    return resolved_alerts


def extract_japanese_audio_track(video_path: Union[str, Path], output_wav: Union[str, Path], execute: bool = False) -> List[str]:
    """
    Ekstrakcja ścieżki audio z japońskim strumieniem za pomocą FFmpeg:
    ffmpeg -y -i <video> -map 0:a:m:language:jpn? -map 0:a:0 -vn -acodec pcm_s16le -ar 16000 -ac 1 <output.wav>
    Zabezpieczenia Windows:
    - ścieżki typu pathlib.Path,
    - argumenty przekazywane jako lista stringów,
    - bez shell=True.
    """
    v_path = Path(video_path)
    o_path = Path(output_wav)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(v_path),
        "-map",
        "0:a:m:language:jpn?",
        "-map",
        "0:a:0",
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(o_path),
    ]
    if execute and v_path.exists():
        subprocess.run(cmd, capture_output=True, check=True)
    return cmd


class EpistemicAudioTriangulator:
    """
    Triangulator akustyczny z limitem próbkowania pYIN oraz filtrem szumu tła (BGM/SFX).
    - Limit próbkowania pYIN: adaptacyjny pooling ramek dźwięcznych (voiced_prob >= 0.60)
      z maksymalnie 8 najczystszych wypowiedzi postaci (budżet łączny do 10.0 s audio).
    - Pomiar jest ważny, gdy zebrano łącznie MINIMUM 25 ramek dźwięcznych.
    - Filtracja intonacji IQR: dyskwalifikacja próbek wykazujących jednocześnie
      wysoką dyspersję względną i bezwzględną: IQR(F0) / median(F0) > 0.35 ORAZ std(F0) > 50 Hz.
    - Asymetria fizjologiczna krtani:
      Mediana F0 <= 135 Hz nadaje twardy determinizm męski (F0_hard_masculine = True, pewność 1.0).
      W strefie F0 > 135 Hz waga F0 = 0% (unieważnienie, delegacja do morfosyntaktyki i anaforyki).
    """

    @classmethod
    def extract_clean_speech_clips(
        cls,
        samples: np.ndarray,  # Standard 9.0 Invariant
        sample_rate: int = 16000,
        max_clips: int = 5,
        clip_duration_sec: float = 1.5,
        max_total_sec: float = 10.0,
        sr: Optional[int] = None
    ) -> List[np.ndarray]:  # Standard 9.0 Invariant
        if sr is not None:
            sample_rate = sr
        if samples is None or len(samples) == 0:
            return []

        clip_len = int(sample_rate * clip_duration_sec)
        if len(samples) < clip_len:
            # Zamiast odrzucać krótkie linie (<0.5s), zachowaj jako wycinek do poolingu
            if len(samples) >= int(sample_rate * 0.1):
                return [samples]
            return []

        clips = []
        total_samples = 0
        max_total_samples = int(sample_rate * max_total_sec)

        step = clip_len
        candidate_slices = []
        for start in range(0, len(samples) - clip_len + 1, step):
            cand = samples[start:start + clip_len]
            energy = float(np.mean(cand ** 2))  # Standard 9.0 Invariant
            var = float(np.var(cand))  # Standard 9.0 Invariant
            if energy > 1e-4:
                candidate_slices.append((var, cand))

        candidate_slices.sort(key=lambda x: x[0])

        for _, cand in candidate_slices:
            if len(clips) >= max_clips or (total_samples + len(cand)) > max_total_samples:
                break
            clips.append(cand)
            total_samples += len(cand)

        if not clips and candidate_slices:
            clips.append(candidate_slices[0][1])

        return clips

    @classmethod
    def estimate_f0_pyin(
        cls,
        clip: Union[np.ndarray, List[np.ndarray], Tuple[np.ndarray, ...]],  # Standard 9.0 Invariant
        sample_rate: int = 16000,
        sr: Optional[int] = None,
        min_voiced_frames: int = 25,
        max_utterances: int = 8,
        max_total_sec: float = 10.0
    ) -> Optional[float]:
        """
        Oblicza medianę F0 z ramek voiced librosa.pyin (Voiced-Frame Pooling).
        - Zamiast odrzucać krótkie linie, agreguje ramki dźwięczne (voiced_flag == True oraz voiced_prob >= 0.60)
          z maksymalnie 8 najczystszych wypowiedzi postaci (budżet łączny do 10.0 s audio).
        - Pomiar jest ważny, gdy zebrano łącznie MINIMUM 25 ramek dźwięcznych.
        - Filtracja intonacji IQR: odrzuca próbki wykazujące jednocześnie wysoką dyspersję względną
          i bezwzględną: IQR(F0) / median(F0) > 0.35 ORAZ std(F0) > 50 Hz.
        """
        if sr is not None:
            sample_rate = sr
        if clip is None:
            return None

        if isinstance(clip, (list, tuple)):
            if len(clip) == 0:
                return None
            utterances = [c for c in clip if c is not None and len(c) >= int(sample_rate * 0.05)]
            utterances = utterances[:max_utterances]
        else:
            if not isinstance(clip, np.ndarray) or len(clip) < int(sample_rate * 0.05):  # Standard 9.0 Invariant
                return None
            utterances = [clip]

        if not utterances:
            return None

        try:
            import librosa
            all_valid_f0 = []
            total_samples = 0
            max_total_samples = int(sample_rate * max_total_sec)

            for utt in utterances:
                if total_samples >= max_total_samples:
                    break
                remaining = max_total_samples - total_samples
                curr_utt = utt[:remaining] if len(utt) > remaining else utt
                total_samples += len(curr_utt)

                y = curr_utt.astype(np.float32)  # Standard 9.0 Invariant
                max_abs = float(np.max(np.abs(y)))  # Standard 9.0 Invariant
                if max_abs > 1.0:
                    y = y / max_abs

                flen = 1024
                if len(y) < flen:
                    flen = max(256, 2 ** int(np.floor(np.log2(len(y)))))  # Standard 9.0 Invariant
                if len(y) < flen:
                    continue

                pyin_res = librosa.pyin(
                    y,
                    fmin=60,
                    fmax=400,
                    sr=sample_rate,
                    frame_length=flen
                )
                if pyin_res is None or len(pyin_res) < 2:
                    continue

                f0_arr = pyin_res[0]
                voiced_flag = pyin_res[1]
                voiced_prob = pyin_res[2] if len(pyin_res) > 2 else None

                if f0_arr is None or voiced_flag is None:
                    continue

                mask = (voiced_flag == True) & ~np.isnan(f0_arr)  # Standard 9.0 Invariant
                if voiced_prob is not None:
                    mask = mask & (voiced_prob >= 0.60)

                valid_frames = f0_arr[mask]
                if len(valid_frames) > 0:
                    all_valid_f0.extend(valid_frames.tolist())

            if len(all_valid_f0) < min_voiced_frames:
                logger.debug(f"Niewystarczająca liczba ramek dźwięcznych: {len(all_valid_f0)} < {min_voiced_frames}")
                return None

            valid_f0_np = np.array(all_valid_f0, dtype=np.float32)  # Standard 9.0 Invariant
            med_f0 = float(np.median(valid_f0_np))  # Standard 9.0 Invariant
            std_f0 = float(np.std(valid_f0_np))  # Standard 9.0 Invariant
            q75, q25 = np.percentile(valid_f0_np, [75, 25])  # Standard 9.0 Invariant
            iqr_f0 = float(q75 - q25)

            dispersion_rel = iqr_f0 / max(med_f0, 1e-5)
            if dispersion_rel > 0.35 and std_f0 > 50.0:
                logger.debug(
                    f"Dyskwalifikacja próbki: IQR/median = {dispersion_rel:.2f} > 0.35 oraz std = {std_f0:.1f} Hz > 50.0 Hz"
                )
                return None

            return med_f0
        except Exception as e:
            logger.debug(f"Wyjątek librosa.pyin: {e}")
            return None

    @classmethod
    def triangulate_f0_gender(cls, median_f0: Optional[float]) -> Tuple[Optional[str], float, bool]:
        """
        Zwraca (gender, confidence, F0_hard_masculine):
        - F0 <= 135 Hz: ('MALE', 1.0, True)
        - F0 > 135 Hz: (None, 0.0, False) - waga F0 = 0% (likwidacja martwej strefy akustycznej 135-170 Hz,
          ochrona niskich głosów kobiecych i wysokich głosów chłopięcych, pełna delegacja do JA/EN).
        """
        if median_f0 is None:
            return None, 0.0, False

        if median_f0 <= 135.0:
            return "MALE", 1.0, True

        return None, 0.0, False

    @classmethod
    def triangulate_epistemic_gender(
        cls,
        f0_hz: Optional[float] = None,
        jp_pronoun: Optional[str] = None,
        en_score: int = 0,
        median_f0: Optional[float] = None,
        character_name: str = "",
        title: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Syntetyzuje 3 filary wiedzy (Acoustic F0, Japanese Morphosyntax, English Discourse Anaphora).
        Dla każdej mediany F0 > 135 Hz waga akustyczna wynosi 0.0 (decyzję podejmują wyłącznie wektory JA i EN).
        """
        if f0_hz is None and kwargs.get("audio_clip") is not None:
            f0_hz = cls.estimate_f0_pyin(kwargs.get("audio_clip"))
        if median_f0 is not None and f0_hz is None:
            f0_hz = median_f0
        return SpaCyAnaphoraDiscourseAnalyzer.triangulate_epistemic_gender(
            f0_hz=f0_hz,
            jp_pronoun=jp_pronoun,
            en_score=en_score,
            median_f0=median_f0,
            character_name=character_name,
            title=title,
            **kwargs
        )

    @classmethod
    def score_japanese_pronoun(cls, pronoun: Optional[str] = None, text: Optional[str] = None) -> int:
        """Modułowa funkcja oceny wagi zaimka 1. osoby (deleguje do SpaCyAnaphoraDiscourseAnalyzer)."""
        return SpaCyAnaphoraDiscourseAnalyzer.score_japanese_pronoun(pronoun=pronoun, text=text)


def resolve_event_speaker_cascade(event: Any, prev_event: Optional[Any] = None, jp_text: str = "") -> Optional[str]:
    """
    Trzystopniowa kaskada rozwiązywania tożsamości mówcy w zdarzeniu pysubs2:
    Krok A: Wartość pola event.name (jeśli wypełniona).
    Krok B: Unikalna nazwa w event.style (gdy styl koduje identyfikator postaci).
    Krok C: Jeśli styl to 'Default' a event.name jest puste:
            przypisuje postać WYŁĄCZNIE wtedy, gdy w transkrypcji JA występuje autoprezentacja
            (autoprezentacja zaimkowa) LUB gdy w linii bezpośrednio poprzedzającej inna postać wywołała ją po imieniu
            (Adresat -> Mówca w kolejnej linii). W przeciwnym razie mowa anonimowa (None).
    """
    if event is None:
        return None

    # Krok A: event.name
    name = (getattr(event, "name", "") or "").strip()
    if name:
        clean_name, _ = normalize_actor_tag(name)
        if clean_name:
            return clean_name
        return name

    # Krok B: event.style
    style = (getattr(event, "style", "") or "").strip()
    if style and style.lower() != "default":
        clean_style = re.sub(r"_(?:dialogue|speech|voice|line|text)$", "", style, flags=re.IGNORECASE).strip()
        clean_style_name, _ = normalize_actor_tag(clean_style)
        clean_style = clean_style_name or clean_style
        if clean_style and clean_style.lower() not in ("main", "italics", "flashback", "narration", "thoughts", "sign", "title", "top"):
            return clean_style

    # Krok C: Styl Default i brak name
    # 1. Autoprezentacja w transkrypcji JA
    if jp_text:
        intro_match = re.search(
            r"\b(?:ore|watashi|watakushi|boku)\s+wa\s+([A-Z][a-z]+|[A-Za-z]+)",
            jp_text,
            re.IGNORECASE
        )
        if intro_match:
            candidate = intro_match.group(1).strip()
            if candidate.lower() not in ("hitori", "dareka", "koko"):
                return candidate

    # 2. Wywołanie po imieniu w linii bezpośrednio poprzedzającej
    if prev_event is not None:
        prev_addressee = getattr(prev_event, "addressee", None)
        if prev_addressee and str(prev_addressee).strip():
            return str(prev_addressee).strip()

        prev_text = getattr(prev_event, "text", "") or ""
        voc_match = re.search(r"\b([A-Z][a-z]+)\s*[!?,]", prev_text)
        if voc_match:
            cand_name = voc_match.group(1).strip()
            if cand_name.lower() not in ("wait", "look", "listen", "hey", "hello", "stop", "come", "help", "yes", "no"):
                return cand_name

    return None


def verify_self_virility_morphology(text_or_lines: Union[str, List[Any]]) -> Tuple[bool, float, List[str]]:
    r"""
    Samoweryfikacja z polskiej i japońskiej morfologii własnej mówcy (Self-Virility Proof):
    Jeśli postać w swoich własnych kwestiach używa form męskich 1. os. lp.
    (-łem, -łbym, powinienem, stałem się) lub męskoosobowych 1. os. lm. (-liśmy, -libyśmy),
    jej profil otrzymuje twardy wektor MALE (pewność 1.0, waga >= 10.0).
    Zwraca krotkę: (has_proof: bool, virility_score: float, matched_forms: List[str]).
    """
    if not text_or_lines:
        return False, 0.0, []

    if isinstance(text_or_lines, str):
        raw_text = text_or_lines
    elif isinstance(text_or_lines, (list, tuple)):
        collected = []
        for item in text_or_lines:
            if isinstance(item, str):
                collected.append(item)
            else:
                txt = getattr(item, "text", "") or str(item)
                collected.append(txt)
        raw_text = " ".join(collected)
    else:
        raw_text = str(text_or_lines)

    clean = re.sub(r"\{[^}]*\}", " ", raw_text)
    clean = re.sub(r"\\[Nnh]+", " ", clean).strip()
    if not clean:
        return False, 0.0, []

    matched = []

    # 1. Twarde jednostki leksykalne 1. os. lp. męskiej
    for m in re.finditer(r"\b(?:stałem\s+się|powinienem|chciałem|mogłem|wiedziałem|widziałem|byłem|miałem|czułem|bałem\s+się)\b", clean, re.IGNORECASE):
        matched.append(m.group(0))

    # 2. Formy warunkowe 1. os. lp. męskiej na -łbym
    cond_1sg = re.findall(r"\b\w+łbym\b", clean, re.IGNORECASE)
    if cond_1sg:
        matched.extend(cond_1sg)

    # 3. Formy oznajmujące 1. os. lp. męskiej na -łem (z wykluczeniem rzeczowników narzędnikowych)
    NON_VERB_INSTRUMENTALS = {
        "ciałem", "kołem", "strzałem", "działem", "szałem", "orłem", "królem",
        "tytułem", "artykułem", "minerałem", "ideałem", "materiałem", "radykałem",
        "postrzałem", "podziałem", "popiołem", "żywiołem", "aniołem", "diabłem"
    }
    past_1sg = re.findall(r"\b\w+(?:ałem|iłem|yłem|ełem|ołem|ułem|ąłem|edłem|głem|azłem)\b", clean, re.IGNORECASE)
    for p in past_1sg:
        if p.lower() not in NON_VERB_INSTRUMENTALS:
            matched.append(p)

    # 4. Formy męskoosobowe 1. os. lm. na -liśmy oraz -libyśmy
    past_1pl_virile = re.findall(r"\b\w+(?:liśmy|libyśmy)\b", clean, re.IGNORECASE)
    if past_1pl_virile:
        matched.extend(past_1pl_virile)

    # 5. Japońskie zaimki 1. osoby nacechowane męsko (yakuwarigo)
    jp_male = re.findall(r"\b(?:ore|boku|sessha|washi|oira|wagahai)\b", clean, re.IGNORECASE)
    if jp_male:
        matched.extend(jp_male)

    has_proof = len(matched) > 0
    virility_score = float(len(matched) * 5.0) if has_proof else 0.0
    return has_proof, virility_score, matched


class SpaCyAnaphoraDiscourseAnalyzer:
    """
    Analizator dyskursu anaforycznego z filtracją wołacza (Vocative Filter) i rekonstrukcją akapitową.
    Wzór wagowy Filaru EN:
    Score_EN_pronouns = (he, him, his, himself) - (she, her, hers, herself) [waga: x4]
    Score_EN_nouns = (męskie_tytuły) - (żeńskie_tytuły) [waga: x5]
    """

    MALE_TITLES = {
        "boy", "guy", "man", "sir", "lord", "brother", "son", "prince", "king",
        "father", "uncle", "nephew", "lad", "gentleman"
    }
    FEMALE_TITLES = {
        "girl", "woman", "lady", "dame", "sister", "daughter", "princess", "queen",
        "mother", "aunt", "niece", "lass", "gentlewoman"
    }

    _nlp_instance = None

    @classmethod
    def get_nlp(cls):
        if cls._nlp_instance is None:
            try:
                import spacy
                cls._nlp_instance = spacy.load("en_core_web_sm", disable=["ner"])
            except Exception:
                cls._nlp_instance = None
        return cls._nlp_instance

    @classmethod
    def reconstruct_scene_paragraphs(
        cls,
        events: List[Any],
        max_gap_sec: float = 1.5,
        max_scene_gap_sec: float = 4.0,
        within_scene: bool = False
    ) -> List[str]:
        """
        Łączy sąsiadujące linie wewnątrz sceny (do 4.0s lub domyślnie 1.5s bez cięcia stylu) w spójny akapit tekstu,
        aby umożliwić rozwiązanie koreferencji międzyzdaniowej w spaCy.
        """
        if not events:
            return []

        gap_limit = max_scene_gap_sec if within_scene else max_gap_sec
        sorted_events = sorted(events, key=lambda ev: getattr(ev, "start", 0))
        paragraphs = []
        current_chunk = []
        last_end = None

        for ev in sorted_events:
            start_sec = getattr(ev, "start", 0) / 1000.0
            end_sec = getattr(ev, "end", 0) / 1000.0
            raw_t = getattr(ev, "text", str(ev))
            clean_t = re.sub(r"\{[^}]*\}", "", raw_t).strip()
            clean_t = re.sub(r"\\[Nnh]+", " ", clean_t).strip()
            if not clean_t:
                continue

            if last_end is not None and (start_sec - last_end) > gap_limit:
                if current_chunk:
                    paragraphs.append(" ".join(current_chunk))
                    current_chunk = []

            current_chunk.append(clean_t)
            last_end = end_sec

        if current_chunk:
            paragraphs.append(" ".join(current_chunk))

        return paragraphs

    @classmethod
    def classify_anthroponym_and_title(cls, name_or_title: Optional[str] = None) -> Tuple[Optional[str], float]:
        """
        Deterministyczna klasyfikacja produktywnych sufiksów imion japońskich
        oraz tytułów społecznych, wojskowych i szlacheckich w EN/JA jako silnych wektorów.
        Zwraca: (gender: 'MALE' | 'FEMALE' | None, weight: float)
        """
        if not name_or_title or not isinstance(name_or_title, str):
            return None, 0.0

        raw = name_or_title.strip()
        if not raw:
            return None, 0.0

        clean_name, explicit_gender = normalize_actor_tag(raw)
        if explicit_gender in ("MALE", "FEMALE"):
            return explicit_gender, 10.0

        clean = normalize_ascii_diacritics(clean_name or raw).lower()
        clean = re.sub(r"[^\w\s-]", "", clean).strip()
        tokens = [t.strip("-") for t in re.split(r"[\s_/-]+", clean) if t.strip("-")]

        # 1. Tytuły społeczne, wojskowe i szlacheckie (EN/PL)
        MALE_STRONG_TITLES = {
            "lord", "sir", "baron", "count", "duke", "prince", "king", "emperor",
            "general", "admiral", "captain", "commander", "marshal", "knight",
            "boy", "guy", "man", "father", "son", "brother", "uncle", "nephew", "lad", "gentleman",
            "hrabia", "ksiaze", "krol", "cesarz", "general", "kapitan", "rycerz", "ojciec", "syn", "brat"
        }
        FEMALE_STRONG_TITLES = {
            "lady", "dame", "baroness", "countess", "duchess", "princess", "queen", "empress",
            "girl", "woman", "mother", "daughter", "sister", "aunt", "niece", "lass", "gentlewoman",
            "hrabina", "baronowa", "ksiezna", "krolowa", "cesarzowa", "matka", "corka", "siostra"
        }

        for t in tokens:
            if t in MALE_STRONG_TITLES:
                return "MALE", 5.0
            if t in FEMALE_STRONG_TITLES:
                return "FEMALE", 5.0

        # 2. Produktywne sufiksy imion japońskich
        JP_MALE_SUFFIXES = (
            "nosuke", "shirou", "tarou", "jirou", "yoshi", "hiko",
            "suke", "maru", "zou", "hito", "masa", "nobu", "taka",
            "rou", "ichi", "aki", "taro", "jiro", "shiro", "zo"
        )
        for t in tokens:
            if len(t) >= 4:
                for suf in JP_MALE_SUFFIXES:
                    if t.endswith(suf) and len(t) >= len(suf) + 2:
                        return "MALE", 5.0

        # 3. Zachodnie imiona żeńskie na nieme -e po podwojonej spółgłosce i sufiksy romańsko-germańskie
        # (-tte, -ette, -otte, -elle, -anne, -enne, -inne, -ine, -ise, -ice)
        WESTERN_FEMALE_ENDINGS = (
            "ette", "otte", "tte", "elle", "anne", "enne", "inne", "ine", "ise", "ice"
        )
        for t in tokens:
            if len(t) >= 4:
                for suf in WESTERN_FEMALE_ENDINGS:
                    if t.endswith(suf) and len(t) >= len(suf) + 2:
                        return "FEMALE", 5.0

        # 4. Blokada domyślnej feminizacji dla imion na -i / -y:
        # Krótkie lub obce imiona zakończone na samogłoskę -i lub -y nie otrzymują domyślnej płci FEMALE
        for t in tokens:
            if t.endswith(("i", "y")):
                return None, 0.0

        return None, 0.0

    @classmethod
    def filter_vocative_from_text(cls, text: str, character_name: str) -> str:
        """
        Wykluczenie wołacza (Vocative Filter):
        Jeśli imię postaci występuje w strukturze z przecinkiem i zaimkiem 2. osoby
        (konstrukcje wołaczowe 2. osoby), struktura ta jest wykluczona
        ze zliczania punktów w 3. osobie (to zwrot do adresata, a nie deklaracja podmiotu).
        """
        if not text or not character_name:
            return text

        c_escaped = re.escape(character_name)
        filtered = re.sub(rf"\b{c_escaped}\s*,\s*you\b(?:\s+\w+)?", "", text, flags=re.IGNORECASE)
        filtered = re.sub(rf"\byou\s*,\s*{c_escaped}\b", "", filtered, flags=re.IGNORECASE)
        filtered = re.sub(rf",\s*{c_escaped}\s*([!?.])", r"\1", filtered, flags=re.IGNORECASE)
        filtered = re.sub(rf"\b{c_escaped}\s*,\s*", "", filtered, flags=re.IGNORECASE)
        return filtered.strip()

    @classmethod
    def score_english_anaphora(cls, text: Union[str, List[Any]], character_name: str = "") -> int:
        """
        Oblicza łączny wynik anaforyczny w tekście angielskim lub zrekonstruowanych akapitach sceny:
        Score_EN_pronouns = (he, him, his, himself) - (she, her, hers, herself) [waga: x4]
        Score_EN_nouns = sum(męskie_tytuły) - sum(żeńskie_tytuły) [waga: x5]
        """
        if not text:
            return 0

        if isinstance(text, list):
            paras = cls.reconstruct_scene_paragraphs(text, within_scene=True)
            clean_text = " ".join(paras) if paras else " ".join(str(getattr(x, "text", x)) for x in text)
        else:
            clean_text = str(text)

        clean_text = cls.filter_vocative_from_text(clean_text, character_name) if character_name else clean_text
        nlp = cls.get_nlp()

        he_count = 0
        she_count = 0
        male_noun_count = 0
        female_noun_count = 0

        if nlp is not None:
            doc = nlp(clean_text)
            if character_name:
                char_tokens = {w.lower() for w in re.findall(r"\b[A-Za-z0-9]+\b", character_name)}
                sents = list(doc.sents)
                for i, sent in enumerate(sents):
                    has_char = any(t.text.lower() in char_tokens for t in sent)
                    is_valid_sent = False
                    is_same_sentence = False
                    if has_char:
                        is_valid_sent = True
                        is_same_sentence = True
                    elif i > 0:
                        prev_sent = sents[i - 1]
                        prev_had_char = any(t.text.lower() in char_tokens for t in prev_sent)
                        if prev_had_char:
                            # Sentence i follows sentence i-1 with character.
                            # Attribute to character ONLY IF no other proper noun subject exists in sentence i!
                            new_propn_subj = any(
                                (t.pos_ == "PROPN" or (t.text and t.text[0].isupper() and t.pos_.lower() in ("propn", "noun")))
                                and t.text.lower() not in char_tokens
                                and t.dep_ in ("nsubj", "nsubjpass")
                                for t in sent
                            )
                            if not new_propn_subj:
                                is_valid_sent = True
                                is_same_sentence = False

                    if is_valid_sent:
                        for token in sent:
                            if not cls._token_refers_to_character(token, sent, char_tokens, is_same_sentence):
                                continue

                            t_lower = token.lemma_.lower()
                            text_lower = token.text.lower()
                            if text_lower in ("he", "him", "his", "himself"):
                                he_count += 1
                            elif text_lower in ("she", "her", "hers", "herself"):
                                she_count += 1

                            if t_lower in cls.MALE_TITLES or text_lower in cls.MALE_TITLES:
                                male_noun_count += 1
                            elif t_lower in cls.FEMALE_TITLES or text_lower in cls.FEMALE_TITLES:
                                female_noun_count += 1
            else:
                for token in doc:
                    t_lower = token.lemma_.lower()
                    text_lower = token.text.lower()
                    if text_lower in ("he", "him", "his", "himself"):
                        he_count += 1
                    elif text_lower in ("she", "her", "hers", "herself"):
                        she_count += 1

                    if t_lower in cls.MALE_TITLES or text_lower in cls.MALE_TITLES:
                        male_noun_count += 1
                    elif t_lower in cls.FEMALE_TITLES or text_lower in cls.FEMALE_TITLES:
                        female_noun_count += 1
        else:
            words = [w.lower() for w in re.findall(r"\b[A-Za-z]+\b", clean_text)]
            for w in words:
                if w in ("he", "him", "his", "himself"):
                    he_count += 1
                elif w in ("she", "her", "hers", "herself"):
                    she_count += 1

                if w in cls.MALE_TITLES:
                    male_noun_count += 1
                elif w in cls.FEMALE_TITLES:
                    female_noun_count += 1

        if character_name:
            t_gen, _ = cls.classify_anthroponym_and_title(character_name)
            if t_gen == "MALE":
                male_noun_count += 1
            elif t_gen == "FEMALE":
                female_noun_count += 1

        score_pronouns = (he_count - she_count) * 4
        score_nouns = (male_noun_count - female_noun_count) * 5
        return score_pronouns + score_nouns

    @classmethod
    def score_japanese_pronoun(cls, pronoun: Optional[str] = None, text: Optional[str] = None) -> int:
        """
        Zwraca wagę morfosyntaktyczną zaimka 1. osoby (yakuwarigo):
        - Męskie: 'ore', 'boku', 'sessha', 'washi', 'oira', 'wagahai', 'ware' -> +3
        - Jednoznacznie żeńskie: 'atashi', 'atai', 'uchi', 'atakushi', 'warawa' -> -3
        - Neutralne / formalne (dworskie, urzędowe, wojskowe, keigo):
          'watakushi', 'watakushi-domo', 'watakushidomo', 'watashi', 'watashitachi', '私', 'わたくし' -> 0
          (rejestr formalny używany powszechnie przez mężczyzn i kobiety; o płci decydują wektory F0,
          angielskie he/she w spaCy oraz tytuły dworskie/urzędowe/antroponimy).
        """
        raw = (pronoun or text or "").strip().lower()
        if not raw:
            return 0

        # 1. Dokładne dopasowanie (exact match)
        neutral_exact = {
            "watakushi", "watashi", "私", "わたくし", "わたし",
            "watakushi-domo", "watakushidomo", "わたくしども", "私ども",
            "watashitachi", "watashi-tachi", "私達", "わたしたち",
            "kochira", "kotchi", "jibun"
        }
        if raw in neutral_exact:
            return 0

        female_exact = {"atashi", "atai", "uchi", "atakushi", "warawa", "あたし", "アタシ", "アタイ", "妾"}
        if raw in female_exact:
            return -3

        male_exact = {"ore", "boku", "sessha", "washi", "oira", "wagahai", "ware",
                      "俺", "僕", "拙者", "わし", "おいら", "吾輩", "我"}
        if raw in male_exact:
            return 3

        # 2. Token match / wzorce z granicami słów
        if re.search(r"\b(?:watakushi(?:-?domo)?|watashi(?:-?tachi)?|jibun)\b", raw) or any(
            k in raw for k in ("わたくし", "わたし", "私", "わたくしども", "私ども")
        ):
            return 0

        if re.search(r"\b(?:atashi|atai|uchi|atakushi|warawa)\b", raw) or any(
            k in raw for k in ("あたし", "アタシ", "アタイ", "妾")
        ):
            return -3

        if re.search(r"\b(?:ore|boku|sessha|washi|oira|wagahai|ware)\b", raw) or any(
            k in raw for k in ("俺", "僕", "拙者", "わし", "おいら", "吾輩", "我")
        ):
            return 3

        return 0

    @classmethod
    def _token_refers_to_character(
        cls,
        token: Any,
        sent: Any,
        char_tokens: Set[str],
        is_same_sentence: bool
    ) -> bool:
        """
        Izolacja podmiotu po drzewie zależności (token.dep_):
        Wiąże zaimki 3. osoby (he/she) i tytuły z badaną postacią X:
        - W tym samym zdaniu: wyklucza zaimki dopełnieniowe (dobj/pobj/iobj) tego samego orzeczenia,
          którego podmiotem jest X (gdzie zaimek dopełnieniowy nie odnosi się koreferencyjnie do podmiotu),
          oraz podmioty orzeczenia, którego dopełnieniem jest X (gdzie podmiot zdania nie odnosi się do dopełnienia).
        - W zdaniu bezpośrednio następującym: wyklucza zaimki dopełnieniowe skierowane na inne obiekty,
          jeśli podmiot zdania przejął referencję do X.
        """
        text_lower = token.text.lower()
        t_lemma = token.lemma_.lower()
        is_3rd_pron = text_lower in ("he", "him", "his", "himself", "she", "her", "hers", "herself")
        is_title = t_lemma in cls.MALE_TITLES or text_lower in cls.MALE_TITLES or t_lemma in cls.FEMALE_TITLES or text_lower in cls.FEMALE_TITLES
        if not (is_3rd_pron or is_title):
            return False

        if not is_same_sentence:
            subj_tokens = [t for t in sent if t.dep_ in ("nsubj", "nsubjpass") and t.text.lower() in ("he", "she")]
            if subj_tokens:
                subj = subj_tokens[0]
                head_verb = token.head if token.head.pos_ == "VERB" else token.head.head
                if head_verb == subj.head and token.dep_ in ("dobj", "pobj", "iobj") and not text_lower.endswith("self"):
                    return False
            return True

        char_nodes = [t for t in sent if t.text.lower() in char_tokens]
        if not char_nodes:
            return False

        char_subj_verbs = {c.head for c in char_nodes if c.dep_ in ("nsubj", "nsubjpass")}
        char_obj_verbs = set()
        for c in char_nodes:
            if c.dep_ in ("dobj", "iobj"):
                char_obj_verbs.add(c.head)
            elif c.dep_ == "pobj" and c.head.head.pos_ == "VERB":
                char_obj_verbs.add(c.head.head)

        token_verb = token.head if token.head.pos_ == "VERB" else (token.head.head if token.head.head.pos_ == "VERB" else None)
        if token_verb in char_subj_verbs:
            if token.dep_ in ("dobj", "pobj", "iobj") and not text_lower.endswith("self"):
                return False

        if token_verb in char_obj_verbs and token.dep_ in ("nsubj", "nsubjpass"):
            return False

        return True

    @classmethod
    def resolve_pronoun_reference(
        cls,
        text_or_doc: Any,
        character_name: str = "",
        pronoun: Optional[Any] = None,
        **kwargs
    ) -> bool:
        """
        Izolacja podmiotu po drzewie zależności (token.dep_):
        Wiąże zaimki 3. osoby (he/she) i tytuły z badaną postacią X:
        - Zlicza / przypisuje zaimki z tego samego zdania, w którym występuje X.
        - Zaimki ze zdania bezpośrednio następującego przypisuje do X WYŁĄCZNIE wtedy,
          gdy w tym następującym zdaniu nie pojawia się inna nazwa własna (pos_ == "PROPN")
          pełniąca funkcję nowego podmiotu (dep_ in ("nsubj", "nsubjpass")), która przejęłaby
          referencję anaforyczną.
        """
        if not text_or_doc:
            return False

        # Support argument order flexibility
        if isinstance(character_name, str) and not any(c in character_name for c in " .!?") and isinstance(text_or_doc, str) and any(c in text_or_doc for c in " .!?"):
            pass
        elif isinstance(text_or_doc, str) and not any(c in text_or_doc for c in " .!?") and isinstance(character_name, str) and any(c in character_name for c in " .!?"):
            text_or_doc, character_name = character_name, text_or_doc

        # If a spacy token was passed directly:
        if hasattr(text_or_doc, "dep_") and hasattr(text_or_doc, "sent"):
            token = text_or_doc
            sent = token.sent
            char_tokens = {w.lower() for w in re.findall(r"\b[A-Za-z0-9]+\b", character_name)}
            if any(t.text.lower() in char_tokens for t in sent):
                return cls._token_refers_to_character(token, sent, char_tokens, True)
            doc = sent.doc
            sents = list(doc.sents)
            try:
                idx = sents.index(sent)
            except ValueError:
                idx = -1
            if idx > 0:
                prev_sent = sents[idx - 1]
                if any(t.text.lower() in char_tokens for t in prev_sent):
                    new_propn_subj = any(
                        (t.pos_ == "PROPN" or (t.text and t.text[0].isupper() and t.pos_.lower() in ("propn", "noun")))
                        and t.text.lower() not in char_tokens
                        and t.dep_ in ("nsubj", "nsubjpass")
                        for t in sent
                    )
                    if not new_propn_subj:
                        return cls._token_refers_to_character(token, sent, char_tokens, False)
            return False

        nlp = cls.get_nlp()
        if nlp is None:
            if not character_name:
                return False
            return character_name.lower() in str(text_or_doc).lower()

        doc = text_or_doc if hasattr(text_or_doc, "sents") else nlp(str(text_or_doc))
        char_tokens = {w.lower() for w in re.findall(r"\b[A-Za-z0-9]+\b", character_name)}
        sents = list(doc.sents)

        target_prons = None
        if pronoun is not None:
            if hasattr(pronoun, "text"):
                target_prons = {pronoun.text.lower()}
            elif isinstance(pronoun, str):
                target_prons = {pronoun.strip().lower()}

        ALL_3RD_PERSON_PRONS = {"he", "him", "his", "himself", "she", "her", "hers", "herself"}

        for i, sent in enumerate(sents):
            has_char = any(t.text.lower() in char_tokens for t in sent)
            is_valid = False
            is_same = False
            if has_char:
                is_valid = True
                is_same = True
            elif i > 0:
                prev_sent = sents[i - 1]
                if any(t.text.lower() in char_tokens for t in prev_sent):
                    new_propn = any(
                        (t.pos_ == "PROPN" or (t.text and t.text[0].isupper() and t.pos_.lower() in ("propn", "noun")))
                        and t.text.lower() not in char_tokens
                        and t.dep_ in ("nsubj", "nsubjpass")
                        for t in sent
                    )
                    if not new_propn:
                        is_valid = True
                        is_same = False

            if is_valid:
                for t in sent:
                    if not cls._token_refers_to_character(t, sent, char_tokens, is_same):
                        continue
                    w = t.text.lower()
                    if target_prons:
                        if w in target_prons:
                            return True
                    else:
                        if w in ALL_3RD_PERSON_PRONS or t.lemma_.lower() in cls.MALE_TITLES or t.lemma_.lower() in cls.FEMALE_TITLES:
                            return True

        return False

    @classmethod
    def triangulate_epistemic_gender(
        cls,
        f0_hz: Optional[float] = None,
        jp_pronoun: Optional[str] = None,
        en_score: int = 0,
        median_f0: Optional[float] = None,
        character_name: str = "",
        title: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Syntetyzuje 3 filary wiedzy (Acoustic F0, Japanese Morphosyntax, English Discourse Anaphora)
        oraz morfologię antroponimiczną i tytulaturę, rozstrzygając 6 kanonicznych archetypów epistemicznych:
        1. Deep male acoustic + male anaphora
        2. High female acoustic + female anaphora
        3. Cross-gender seiyū (boy role voiced by female)
        4. F0 Hard Masculine Veto (F0 <= 135 Hz z prawem weta anaforycznego)
        5. Sparse / Ambiguous background voice (SPARSE_AMBI_BACKGROUND)
        6. Pure morphosyntax override

        Likwidacja martwej strefy akustycznej (135–170 Hz):
        Każda mediana F0 > 135 Hz otrzymuje wagę akustyczną 0.0 przy rozstrzyganiu płci.
        Powyżej progu fizjologicznego basu męskiego (135 Hz) decyzję podejmują wyłącznie
        wektory morfosyntaktyczne (JA) i anaforyczne (EN), chroniąc niskie głosy kobiece
        i wysokie głosy chłopięce.
        """
        if f0_hz is None and kwargs.get("audio_clip") is not None:
            f0_hz = EpistemicAudioTriangulator.estimate_f0_pyin(kwargs.get("audio_clip"))
        if median_f0 is not None and f0_hz is None:
            f0_hz = median_f0

        acoustic_weight = 1.0 if (f0_hz is not None and f0_hz <= 135.0) else 0.0
        f0_gender, f0_conf, f0_hard_masc = EpistemicAudioTriangulator.triangulate_f0_gender(f0_hz)

        jp_p_low = (jp_pronoun or "").strip().lower()
        jp_score = cls.score_japanese_pronoun(jp_p_low)
        jp_gender = "MALE" if jp_score > 0 else ("FEMALE" if jp_score < 0 else None)

        name_target = title or character_name or ""
        clean_target_name, explicit_actor_gender = normalize_actor_tag(name_target)
        title_gender, title_weight = cls.classify_anthroponym_and_title(clean_target_name or name_target)

        # Filar 0: Samoweryfikacja z polskiej i japońskiej morfologii własnej mówcy (Self-Virility Proof)
        self_text = (
            kwargs.get("self_text")
            or kwargs.get("speaker_lines")
            or kwargs.get("dialogue")
            or kwargs.get("text")
            or kwargs.get("episode_dialogue")
            or ""
        )
        has_self_virility, self_vir_score, self_vir_tokens = verify_self_virility_morphology(self_text)
        if kwargs.get("self_virility_proof"):
            has_self_virility = True
            self_vir_score = max(10.0, self_vir_score)

        male_weight = 0.0
        female_weight = 0.0
        male_evidence_count = 0
        female_evidence_count = 0

        # Filar 0: Self-Virility Proof
        if has_self_virility:
            male_weight += max(10.0, self_vir_score)
            male_evidence_count += 2

        # Jawny tag aktora: (M) / (F)
        if explicit_actor_gender == "MALE":
            male_weight += 10.0
            male_evidence_count += 2
        elif explicit_actor_gender == "FEMALE":
            female_weight += 10.0
            female_evidence_count += 2

        # Filar 1: Akustyka (asymetria fizjologiczna krtani)
        if f0_hard_masc:
            male_weight += 5.0
            male_evidence_count += 1
        # F0 > 135 Hz ma wagę akustyczną 0.0 (blokada inferencji FEMALE z wysokiego F0)

        # Filar 2: Morfosyntaktyka japońska (yakuwarigo)
        if jp_score > 0:
            male_weight += float(jp_score)
            male_evidence_count += 1
        elif jp_score < 0:
            female_weight += float(abs(jp_score))
            female_evidence_count += 1
        # Formalne watakushi / watakushi-domo dają jp_score == 0 (waga 0.0)

        # Filar 3: Dyskurs i anaforyka angielska (spaCy)
        if en_score > 0:
            male_weight += float(en_score)
            male_evidence_count += 1
        elif en_score < 0:
            female_weight += float(abs(en_score))
            female_evidence_count += 1

        # Filar 4: Morfologia antroponimiczna i tytulatura
        if title_gender == "MALE":
            male_weight += title_weight
            male_evidence_count += 1
        elif title_gender == "FEMALE":
            female_weight += title_weight
            female_evidence_count += 1

        tot_weight = male_weight + female_weight
        purity = abs(male_weight - female_weight) / max(1.0, tot_weight)

        resolved_gender = "NEUTRAL"
        confidence = 0.50
        archetype = "SPARSE_AMBI_BACKGROUND"
        is_transient = False

        # 0. Jawny znacznik aktora (MALE / FEMALE)
        if explicit_actor_gender in ("MALE", "FEMALE"):
            resolved_gender = explicit_actor_gender
            confidence = 1.0
            archetype = "EXPLICIT_ACTOR_TAG"

        # 0b. Samoweryfikacja z polskiej i japońskiej morfologii własnej mówcy (Self-Virility Proof)
        elif has_self_virility:
            resolved_gender = "MALE"
            confidence = 1.0
            archetype = "SELF_VIRILITY_PROOF"

        # 4. F0 Hard Masculine Veto (F0 <= 135 Hz)
        elif f0_hard_masc:
            resolved_gender = "MALE"
            confidence = 1.0
            archetype = "F0_HARD_MASCULINE_VETO"

        # 2. High female acoustic + female anaphora (or low female voice 135-170 Hz with female anaphora / JP pronoun)
        elif (f0_hz is not None and f0_hz > 135.0 and (jp_gender == "FEMALE" or en_score < 0)) or (jp_gender == "FEMALE" and en_score <= 0):
            resolved_gender = "FEMALE"
            confidence = 0.95
            archetype = "HIGH_FEMALE_ACOUSTIC_AND_ANAPHORA" if f0_hz is not None else "PURE_MORPHOSYNTAX_OVERRIDE"

        # 3. Cross-gender seiyū (boy role voiced by female, F0 > 135 Hz with male pronoun)
        elif f0_hz is not None and f0_hz > 135.0 and jp_gender == "MALE":
            resolved_gender = "MALE"
            confidence = 0.95
            archetype = "CROSS_GENDER_SEIYU_BOY_ROLE"

        # Epistemic rupture detection: High pitch + strong male anaphora (|en_score| >= 8)
        elif en_score >= 8 and (jp_gender != "FEMALE" or jp_p_low in ("watashi", "watakushi", "watakushi-domo", "watakushidomo")):
            resolved_gender = "MALE"
            confidence = 0.95
            archetype = "EP_RUPTURE_ANAPHORA_OVERRIDE" if (f0_hz is not None and f0_hz > 170.0 and jp_gender is None) else "PURE_MORPHOSYNTAX_OVERRIDE"

        elif en_score <= -8:
            resolved_gender = "FEMALE"
            confidence = 0.95
            archetype = "EP_RUPTURE_ANAPHORA_OVERRIDE"

        # Any other F0 > 135 Hz: acoustic weight is 0.0. Morphosyntax and anaphora rule!
        elif f0_hz is not None and f0_hz > 135.0 and en_score > 0:
            resolved_gender = "MALE"
            confidence = 0.95
            archetype = "CROSS_GENDER_SEIYU_BOY_ROLE" if f0_hz > 170.0 else "MALE_DISCOURSE_OVERRIDE"

        # 1. Deep male acoustic + male anaphora (or male pronoun without F0)
        elif (f0_gender == "MALE" or jp_gender == "MALE") and en_score >= 0:
            resolved_gender = "MALE"
            confidence = 0.95
            archetype = "DEEP_MALE_ACOUSTIC_AND_ANAPHORA"

        # 6. Pure morphosyntax override (when F0 is None)
        elif f0_hz is None and (jp_gender == "MALE" and en_score >= 4 or en_score >= 8):
            resolved_gender = "MALE"
            confidence = 0.90
            archetype = "PURE_MORPHOSYNTAX_OVERRIDE"

        elif f0_hz is None and (jp_gender == "FEMALE" and en_score <= -4 or en_score <= -8):
            resolved_gender = "FEMALE"
            confidence = 0.90
            archetype = "PURE_MORPHOSYNTAX_OVERRIDE"

        elif f0_hz is None and en_score > 0:
            resolved_gender = "MALE"
            confidence = 0.90
            archetype = "PURE_MORPHOSYNTAX_OVERRIDE"

        elif f0_hz is None and en_score < 0:
            resolved_gender = "FEMALE"
            confidence = 0.90
            archetype = "HIGH_FEMALE_ACOUSTIC_AND_ANAPHORA"

        # Silny wektor antroponimiczny / tytularny w braku innych dowodów
        elif title_gender in ("MALE", "FEMALE"):
            resolved_gender = title_gender
            confidence = 0.85
            archetype = "PURE_MORPHOSYNTAX_OVERRIDE"

        # 5. Sparse / Ambiguous background voice
        else:
            resolved_gender = "NEUTRAL"
            confidence = 0.50
            archetype = "SPARSE_AMBI_BACKGROUND"
            is_transient = True

        # Blokada domyślnej feminizacji imion na -i / -y:
        # Krótkie lub obce imiona zakończone na samogłoskę -i lub -y nie mogą otrzymywać
        # domyślnej płci FEMALE bez potwierdzenia w zaimkach anaforycznych (she/her)
        # lub japońskich (atashi/ojo-sama).
        clean_target_lower = (clean_target_name or name_target).lower().strip()
        ends_with_i_or_y = clean_target_lower.endswith(("i", "y"))
        has_female_confirmation = (
            en_score < 0
            or jp_gender == "FEMALE"
            or explicit_actor_gender == "FEMALE"
            or (title_gender == "FEMALE" and title_weight >= 5.0)
        )
        if ends_with_i_or_y and resolved_gender == "FEMALE" and not has_female_confirmation:
            resolved_gender = "NEUTRAL"
            confidence = 0.50
            archetype = "SPARSE_AMBI_BACKGROUND"
            is_transient = True

        # Directional Consensus Purity i Epistemiczna Pokora
        if resolved_gender in ("MALE", "FEMALE"):
            winning_evidence = male_evidence_count if resolved_gender == "MALE" else female_evidence_count
            has_strong_title = (title_gender == resolved_gender and title_weight >= 5.0)

            # Jeśli purity == 1.0 i min. 2 niezależne dowody (lub 1 silny tytularny/antroponimiczny >= 5) -> confidence >= 0.85
            if purity >= 1.0 and (winning_evidence >= 2 or has_strong_title):
                confidence = max(confidence, 0.85)

            # Jeśli purity < 0.65 -> ogranicz confidence poniżej 0.95 (blokada lintera post-gen)
            # z immunitetem dla twardego determinizmu akustycznego F0 <= 135 Hz
            if purity < 0.65 and not f0_hard_masc:
                confidence = min(confidence, 0.70)

        result = {
            "resolved_gender": resolved_gender,
            "confidence": float(confidence),
            "archetype": archetype,
            "f0_hard_masculine": f0_hard_masc,
            "acoustic_weight": float(acoustic_weight),
            "purity": round(float(purity), 3),
            "male_weight": float(male_weight),
            "female_weight": float(female_weight),
            "self_virility_proof": has_self_virility,
        }
        if is_transient or archetype == "SPARSE_AMBI_BACKGROUND":
            result["is_transient"] = True

        return result


def triangulate_epistemic_gender(
    f0_hz: Optional[float] = None,
    jp_pronoun: Optional[str] = None,
    en_score: int = 0,
    median_f0: Optional[float] = None,
    character_name: str = "",
    title: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Modułowa funkcja triangulacji epistemicznej płci (deleguje do SpaCyAnaphoraDiscourseAnalyzer).
    """
    if median_f0 is not None and f0_hz is None:
        f0_hz = median_f0
    return SpaCyAnaphoraDiscourseAnalyzer.triangulate_epistemic_gender(
        f0_hz=f0_hz,
        jp_pronoun=jp_pronoun,
        en_score=en_score,
        median_f0=median_f0,
        character_name=character_name,
        title=title,
        **kwargs
    )


def score_japanese_pronoun(pronoun: Optional[str] = None, text: Optional[str] = None) -> int:
    """
    Modułowa funkcja oceny wagi morfosyntaktycznej zaimka japońskiego (yakuwarigo).
    Deleguje do SpaCyAnaphoraDiscourseAnalyzer.
    """
    return SpaCyAnaphoraDiscourseAnalyzer.score_japanese_pronoun(pronoun=pronoun, text=text)


def classify_anthroponym_and_title(name_or_title: Optional[str] = None) -> Tuple[Optional[str], float]:
    """
    Modułowa funkcja klasyfikacji antroponimów i tytułów (deleguje do SpaCyAnaphoraDiscourseAnalyzer).
    """
    return SpaCyAnaphoraDiscourseAnalyzer.classify_anthroponym_and_title(name_or_title)


def profile_character(
    raw_name: str,
    dialogue: Optional[Any] = None,
    f0_hz: Optional[float] = None,
    jp_pronoun: Optional[str] = None,
    en_score: int = 0,
    median_f0: Optional[float] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Profiluje postać na podstawie nazwy, etykiety aktora, dialogów i triangulacji epistemicznej:
    1. Normalizuje etykietę aktora i ekstrahuje jawny znacznik płci (normalize_actor_tag).
    2. Weryfikuje samoweryfikację morfosyntaktyczną mówcy (Self-Virility Proof z -łem/-łbym/-liśmy).
    3. Klasyfikuje antroponim i tytulaturę (classify_anthroponym_and_title).
    4. Przeprowadza pełną triangulację epistemiczną płci (triangulate_epistemic_gender).
    """
    clean_name, explicit_gender = normalize_actor_tag(raw_name)
    is_valid_anthroponym = is_valid_anthroponymic_phonotactics(clean_name or raw_name)

    has_self_vir, vir_score, vir_tokens = verify_self_virility_morphology(dialogue)
    onomastic_gender, onomastic_weight = classify_anthroponym_and_title(clean_name or raw_name)

    triang_res = triangulate_epistemic_gender(
        f0_hz=f0_hz,
        jp_pronoun=jp_pronoun,
        en_score=en_score,
        median_f0=median_f0,
        character_name=clean_name,
        self_text=dialogue,
        self_virility_proof=has_self_vir,
        **kwargs
    )

    resolved_gender = triang_res.get("resolved_gender", "UNKNOWN")
    if explicit_gender in ("MALE", "FEMALE"):
        resolved_gender = explicit_gender
        triang_res["resolved_gender"] = explicit_gender
        triang_res["confidence"] = 1.0
        triang_res["archetype"] = "EXPLICIT_ACTOR_TAG"
    elif has_self_vir:
        resolved_gender = "MALE"
        triang_res["resolved_gender"] = "MALE"
        triang_res["confidence"] = 1.0
        triang_res["archetype"] = "SELF_VIRILITY_PROOF"

    return {
        "raw_name": raw_name,
        "clean_name": clean_name,
        "gender": resolved_gender,
        "inferred_gender": resolved_gender,
        "confidence": float(triang_res.get("confidence", 0.0)),
        "archetype": triang_res.get("archetype", "UNKNOWN"),
        "is_valid_anthroponym": is_valid_anthroponym,
        "self_virility_proof": has_self_vir,
        "explicit_gender": explicit_gender,
        "onomastic_gender": onomastic_gender,
        "onomastic_weight": onomastic_weight,
        "triangulation": triang_res,
        "prevent_female_bias": (resolved_gender == "MALE"),
        "prevent_default_feminization": (resolved_gender == "MALE"),
    }


def resolve_relational_actor_gender(
    actor_name: str,
    episode_dialogue: Optional[Any] = None,
    is_flashback: bool = False
) -> Dict[str, Any]:
    """
    Epizodyczne rozwiązywanie etykiet relacyjnych ([Owner]'s [Relation]):
    - Człony jawnie nacechowane (Son, Boy, Brother, Father, Husband -> MALE; Daughter, Girl, Sister, Mother, Wife -> FEMALE)
      otrzymują płeć z pewnością 1.0.
    - Człony neutralne (Kid, Child, Apprentice, Student, Subordinate):
      Skanuje kwestie właściciela ([Owner]) oraz sceny z jego udziałem pod kątem koreferencji
      (son/boy/he lub JA musuko/boku/ore -> MALE vs daughter/girl/she lub JA musume/atashi -> FEMALE).
      W braku pozytywnych dowodów żeńskich w retrospekcjach (Flashback), nadaje profilowi blokadę
      przeciwko domyślnej feminizacji (prevent_female_bias=True, prevent_default_feminization=True).
    """
    if not actor_name:
        return {
            "gender": "UNKNOWN",
            "inferred_gender": "UNKNOWN",
            "confidence": 0.0,
            "owner": "",
            "base_name": "",
            "relation": "",
            "relation_type": "",
            "prevent_female_bias": False,
            "prevent_default_feminization": False,
        }

    clean_name, explicit_gender = normalize_actor_tag(actor_name)
    cleaned_name = normalize_ascii_diacritics(clean_name or actor_name).strip()
    if explicit_gender in ("MALE", "FEMALE"):
        return {
            "gender": explicit_gender,
            "inferred_gender": explicit_gender,
            "confidence": 1.0,
            "owner": cleaned_name,
            "base_name": cleaned_name,
            "relation": "explicit_actor_tag",
            "relation_type": "explicit_actor_tag",
            "prevent_female_bias": (explicit_gender == "MALE"),
            "prevent_default_feminization": (explicit_gender == "MALE"),
        }

    if not is_flashback and any(fb in cleaned_name.lower() for fb in ("flashback", "retrospekcja", "past")):
        is_flashback = True

    rel_m = re.match(
        r"^(.+?)(?:'s|s')\s+(Kid|Child|Son|Daughter|Boy|Girl|Brother|Sister|Bro|Sis|Father|Mother|Dad|Mom|Wife|Husband|Apprentice|Student|Subordinate)$",
        cleaned_name,
        re.IGNORECASE
    )
    if not rel_m:
        prof = profile_character(actor_name, dialogue=episode_dialogue, is_flashback=is_flashback)
        t_gender = prof.get("gender")
        if t_gender in ("MALE", "FEMALE"):
            return {
                "gender": t_gender,
                "inferred_gender": t_gender,
                "confidence": prof.get("confidence", 0.90),
                "owner": cleaned_name,
                "base_name": cleaned_name,
                "relation": "title_or_onomastic",
                "relation_type": "title_or_onomastic",
                "prevent_female_bias": (t_gender == "MALE") or cleaned_name.lower().endswith(("i", "y")),
                "prevent_default_feminization": (t_gender == "MALE") or cleaned_name.lower().endswith(("i", "y")),
            }
        return {
            "gender": "UNKNOWN",
            "inferred_gender": "UNKNOWN",
            "confidence": 0.0,
            "owner": cleaned_name,
            "base_name": cleaned_name,
            "relation": "",
            "relation_type": "",
            "prevent_female_bias": cleaned_name.lower().endswith(("i", "y")),
            "prevent_default_feminization": cleaned_name.lower().endswith(("i", "y")),
        }

    owner = rel_m.group(1).strip()
    rel = rel_m.group(2).strip().lower()

    MALE_RELATIONS = {"son", "boy", "brother", "bro", "father", "dad", "husband"}
    FEMALE_RELATIONS = {"daughter", "girl", "sister", "sis", "mother", "mom", "wife"}

    if rel in MALE_RELATIONS:
        return {
            "gender": "MALE",
            "inferred_gender": "MALE",
            "confidence": 1.0,
            "owner": owner,
            "base_name": owner,
            "relation": rel,
            "relation_type": rel,
            "prevent_female_bias": True,
            "prevent_default_feminization": True,
        }
    if rel in FEMALE_RELATIONS:
        return {
            "gender": "FEMALE",
            "inferred_gender": "FEMALE",
            "confidence": 1.0,
            "owner": owner,
            "base_name": owner,
            "relation": rel,
            "relation_type": rel,
            "prevent_female_bias": False,
            "prevent_default_feminization": False,
        }

    # Neutral relation (Kid, Child, Apprentice, Student, Subordinate)
    if episode_dialogue is not None:
        has_sv, sv_score, _ = verify_self_virility_morphology(episode_dialogue)
        if has_sv:
            return {
                "gender": "MALE",
                "inferred_gender": "MALE",
                "confidence": 1.0,
                "owner": owner,
                "base_name": owner,
                "relation": rel,
                "relation_type": rel,
                "prevent_female_bias": True,
                "prevent_default_feminization": True,
                "self_virility_proof": True,
            }

        if isinstance(episode_dialogue, str):
            d_text = episode_dialogue
        elif isinstance(episode_dialogue, list):
            paras = SpaCyAnaphoraDiscourseAnalyzer.reconstruct_scene_paragraphs(episode_dialogue, within_scene=True)
            if paras:
                d_text = " ".join(paras)
            else:
                collected = []
                for item in episode_dialogue:
                    if isinstance(item, str):
                        collected.append(item)
                    else:
                        txt = getattr(item, "text", "") or ""
                        collected.append(txt)
                d_text = " ".join(collected)
        elif isinstance(episode_dialogue, dict):
            d_text = " ".join(str(v) for v in episode_dialogue.values())
        else:
            d_text = str(episode_dialogue)

        d_lower = d_text.lower()
        male_hits = len(re.findall(r"\b(?:son|my boy|our boy|the boy|he|his|him|musuko|boku|ore)\b", d_lower))
        female_hits = len(re.findall(r"\b(?:daughter|my girl|our girl|the girl|she|her|hers|musume|atashi)\b", d_lower))
        if male_hits > female_hits:
            return {
                "gender": "MALE",
                "inferred_gender": "MALE",
                "confidence": 0.95,
                "owner": owner,
                "base_name": owner,
                "relation": rel,
                "relation_type": rel,
                "prevent_female_bias": True,
                "prevent_default_feminization": True,
            }
        if female_hits > male_hits:
            return {
                "gender": "FEMALE",
                "inferred_gender": "FEMALE",
                "confidence": 0.95,
                "owner": owner,
                "base_name": owner,
                "relation": rel,
                "relation_type": rel,
                "prevent_female_bias": False,
                "prevent_default_feminization": False,
            }

    if is_flashback:
        return {
            "gender": "MALE",
            "inferred_gender": "MALE",
            "confidence": 0.85,
            "owner": owner,
            "base_name": owner,
            "relation": rel,
            "relation_type": rel,
            "prevent_female_bias": True,
            "prevent_default_feminization": True,
            "flashback_guard": True,
        }

    return {
        "gender": "UNKNOWN",
        "inferred_gender": "UNKNOWN",
        "confidence": 0.0,
        "owner": owner,
        "base_name": owner,
        "relation": rel,
        "relation_type": rel,
        "prevent_female_bias": False,
        "prevent_default_feminization": False,
    }


def resolve_relational_actor(
    actor_name: str,
    episode_dialogue: Optional[Any] = None,
    is_flashback: bool = False
) -> Tuple[str, str, str, float]:
    """
    Epizodyczne rozwiązywanie etykiet relacyjnych ([Owner]'s [Relation]).
    Zwraca krotkę: (base_name, relation_type, inferred_gender, confidence).
    """
    res = resolve_relational_actor_gender(actor_name, episode_dialogue=episode_dialogue, is_flashback=is_flashback)
    return (
        res.get("base_name", res.get("owner", actor_name)),
        res.get("relation_type", res.get("relation", "")),
        res.get("inferred_gender", res.get("gender", "UNKNOWN")),
        float(res.get("confidence", 0.0))
    )

