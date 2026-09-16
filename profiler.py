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
from pathlib import Path
from typing import List, Optional, Dict, Any, Set, Tuple
from pydantic import BaseModel, Field, ConfigDict
from google import genai
from google.genai import types
from client_factory import format_friendly_api_error, patch_google_genai_schema_sanitizer

patch_google_genai_schema_sanitizer()

logger = logging.getLogger("profiler")


class NameDeclension(BaseModel):
    character_name: str = Field(description="Imię postaci w mianowniku (np. 'Issei', 'Tomine', 'Shizuku')")
    gender: str = Field(description="'MALE' lub 'FEMALE'")
    declension_summary: str = Field(description="Polska odmiana imienia/nazwiska przez przypadki (np. 'Issei -> D. Isseia, C. Isseiowi, B. Isseia, N. z Isseiem, Msc. o Isseiu' lub 'Shizuku -> nieodmienne (z Shizuku, o Shizuku)')")


class FirstPersonPronoun(BaseModel):
    character_name: str = Field(description="Imię postaci")
    japanese_pronoun: str = Field(description="Zaimki 1. osoby używane w dialogach: 'Ore', 'Boku', 'Watashi', 'Atashi', 'Sessha', 'Waga'")
    psychological_profile: str = Field(description="Profil psychologiczny i rejestr (np. 'Ore -> pewny siebie, szorstki, bezkompromisowy', 'Boku -> skromny, uprzejmy, chłopięcy', 'Watashi -> formalny/neutralny')")


class CharacterRelationship(BaseModel):
    speaker: str = Field(description="Imię postaci mówiącej")
    listener: str = Field(description="Imię postaci słuchającej / adresata")
    address_form: str = Field(description="Polska forma zwrotu (np. 'pani Teshima', 'panie profesorze', 'na ty / po imieniu: Minami')")
    relationship_type: str = Field(description="Typ relacji (np. 'uczeń -> nauczycielka', 'koleżanki z klasy', 'rodzeństwo')")


class GlossaryTerm(BaseModel):
    term_en: str = Field(description="Termin w języku angielskim lub japońskim")
    translation_pl: str = Field(description="Ustalony, spójny polski odpowiednik")
    explanation: str = Field(description="Wyjaśnienie kontekstu / znaczenia w anime")


class DangerLinePreScan(BaseModel):
    approx_time: str = Field(description="Przybliżony czas kwestii w odcinku (np. '00:06:12')")
    english_phrase: str = Field(description="Wieloznaczna lub zdradliwa fraza angielska (np. 'I\\'m… fine.', 'Bless you', 'That bombed')")
    speaker: Optional[str] = Field(default=None, description="Mówca kwestii")
    contextual_trap: str = Field(description="Wyjaśnienie pułapki kontekstowej / japońskiego audio (np. 'Odmowa udziału w powitaniu [boku wa ii desu], a NIE stan zdrowia/rany!')")
    mandatory_direction: str = Field(description="Ścisła dyrektywa przekładu dla tłumacza (np. 'Tłumacz jako: Ja... podziękuję / Nie mam ochoty. KATEGORYCZNY ZAKAZ: Nic mi nie jest.')")


class DramaticSequence(BaseModel):
    sequence_name: str = Field(description="Nazwa sekwencji (np. 'Sekwencja 1: Ucieczka z Kamakury', 'Sekwencja 2: Świątynia Suwa i zazdrość')")
    time_range: str = Field(description="Przedział czasowy (np. '00:00 - 05:30')")
    dramatic_summary: str = Field(description="Opis dynamiki, napięcia i relacji władzy w tej części odcinka")
    dominant_tone: str = Field(description="Dominujący rejestr i ton (np. 'panika i tempo bojowe', 'dworska etykieta i tłumiona zazdrość', 'patos rycerski')")
    characters_present: List[str] = Field(default_factory=list, description="Postacie biorące udział w danej sekwencji czasowej (np. ['Fatima', 'Boraqchin Khatun'])")
    female_only_scene: bool = Field(default=False, description="Czy w tej sekwencji rozmawiają wyłącznie kobiety")
    male_only_scene: bool = Field(default=False, description="Czy w tej sekwencji rozmawiają wyłącznie mężczyźni")


class RelationshipPivot(BaseModel):
    approx_time: str = Field(description="Przybliżony czas zmiany w odcinku (np. '00:14:20')")
    characters_involved: str = Field(description="Postacie, których dotyczy zmiana (np. 'Shin i Kyoukai', 'Nauczyciel i Arata')")
    nature_of_shift: str = Field(description="Przyczyna i charakter zmiany relacji (np. 'Przejście ze sztywnego dystansu na poufałość po wyznaniu prawdy')")
    strict_direction_pl: str = Field(description="Ścisła dyrektywa formy zwrotu (np. 'Od tej minuty ZAKAZ formy per pani, przejście na bezpośrednie ty / po imieniu: Kyoukai')")


class CharacterCatchphrase(BaseModel):
    character_name: str = Field(description="Imię postaci")
    original_phrase: str = Field(description="Oryginalna fraza lub motyw w EN/JP (np. 'Yare yare daze', 'Dattebayo', 'Good grief')")
    canonical_pl: str = Field(description="Ustalony, kultowy i jednolity polski odpowiednik (np. 'Dajcie mi święty spokój...', 'I to jak!')")
    context_notes: str = Field(description="Zasada stosowania we wszystkich scenach odcinka")


class SongTranscreationPlan(BaseModel):
    song_type: str = Field(description="Typ utworu: 'Opening (OP)', 'Ending (ED)' lub 'Insert Song / Piosenka w tle'")
    time_range: str = Field(description="Przedział czasowy piosenki (np. '00:01:30 - 00:03:00')")
    metre_and_syllables: str = Field(description="Plan sylabiczny i metrum (np. '8 sylab w wersie (8/8/8/8), rymy parzyste AABB')")
    poetic_theme: str = Field(description="Główny motyw poetycki i rejestr emocjonalny (np. 'Młodość, tęsknota i walka z przeznaczeniem')")


class PunWordplayPlan(BaseModel):
    approx_time: str = Field(description="Przybliżony czas kalamburu (np. '00:08:45')")
    original_joke_or_pun: str = Field(description="Oryginalny żart słowny lub homofon (np. 'Dajare Kami [bóg] vs Kami [papier]')")
    polish_transcreation: str = Field(description="Autonomiczny, zabawny polski ekwiwalent fonetyczny (ZAKAZ przypisów [Przyp. tłum.]!)")


class ContinuityBridgeAlert(BaseModel):
    term_or_event: str = Field(description="Kluczowy termin, nazwa rekwizytu lub wydarzenie z przeszłości")
    canon_source_episode: str = Field(description="Źródło kanonu (np. 'Ustalenie z Odcinka 2 / Biblia Serialu')")
    continuity_directive: str = Field(description="Ścisły wymóg spójności dla tłumacza w tym odcinku")


class CharacterDossier(BaseModel):
    name: str = Field(description="Imię postaci")
    gender: str = Field(description="'MALE', 'FEMALE' lub 'UNKNOWN'")
    age_and_role: str = Field(description="Wiek, status społeczny i rola (np. '7 lat, młody arystokrata/kapłan, syn Yorishige')")
    speech_style_pl: str = Field(description="Unikalny polski rejestr mowy (np. 'Chłodny, dumny, krótki, arystokratyczny bez poufałości')")
    first_person_pronoun: Optional[str] = Field(default=None, description="Japoński zaimek 'ja' (Ore, Boku, Watashi, Atashi) i profil ego")
    declension: Optional[str] = Field(default=None, description="Polska odmiana przez przypadki (np. 'Yoritsugu -> D. Yoritsugu, C. Yoritsugu, B. Yoritsugu')")
    dialect_category: Optional[str] = Field(default="", description="Dialekt regionalny postaci jeśli występuje: 'Satsuma-ben', 'Kansai-ben', 'Kyoto-ben', 'Tohoku-ben', 'Hiroshima-ben', 'Hakata-ben', 'Nagoya-ben', 'Okinawa-ben', 'Hokkaido-ben' lub brak (Filar CXXXV)")
    idiolect_matrix: Optional[str] = Field(default="", description="Matryca idiolektu: specyficzne nawyki leksykalne, zakazane/preferowane zwroty i rytm wypowiedzi dla tej postaci")
    vocal_profile: Optional[str] = Field(default="", description="Profil wokalny postaci (np. 'starsza kobieta, niski/ochrypły głos seiyū', 'młody chłopiec, wysoki głos żeńskiej seiyū')")


class EpisodeProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    episode_summary: str = Field(default="", description="Krótkie 2-3 zdaniowe streszczenie fabuły i tonu odcinka")
    setting_and_era: str = Field(default="", description="Epoka historyczna, czas i miejsce akcji (np. 'XIII wiek, Imperium Mongolskie', 'Współczesne Tokio')")
    domain_expertise: str = Field(default="", description="Specjalistyczna dziedzina wiedzy i profesjonalna terminologia branżowa (np. 'Enologia / Sommelierstwo: terminologia winiarska, szczepy, apelacje', 'Szachy / Shogi')")
    dialogue_stylization: str = Field(default="", description="Wytyczne stylizacji rejestru języka i zakazy/nakazy słownictwa dla tej epoki")
    manga_canon_source: Optional[str] = Field(default="", description="Oficjalne polskie wydawnictwo mangi (np. Waneko, J.P.Fantastica, Studio JG, Hanami), jeśli seria była wydana w Polsce")
    tone_and_genre: str = Field(default="", description="Gatunek i dominujący ton emocjonalny (np. 'Komediodramat młodzieżowy, ciepły z elementami absurdu')")
    danger_lines_prescan: List[DangerLinePreScan] = Field(default_factory=list, description="Lista wyłapanych przed tłumaczeniem niebezpiecznych pułapek kontekstowych i wieloznaczności w całym odcinku")
    relationship_pivots: List[RelationshipPivot] = Field(default_factory=list, description="Punkty zwrotne i dynamiczne zmiany w relacjach/formach zwrotu w trakcie odcinka")
    character_catchphrases: List[CharacterCatchphrase] = Field(default_factory=list, description="Zamrożone kanoniczne polskie odpowiedniki dla powracających powiedzonek postaci")
    song_transcreation_plans: List[SongTranscreationPlan] = Field(default_factory=list, description="Precyzyjny plan metryczny i rymotwórczy dla piosenek (Barańczak)")
    puns_and_wordplays: List[PunWordplayPlan] = Field(default_factory=list, description="Strategie adaptacji japońskich gier słownych (Dajare) i homofonów na autonomiczne polskie dowcipy")
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
        lines.append("\n🚨 SKANER MIN JĘZYKOWYCH I PUŁAPEK WIELOZNACZNOŚCI (DANGER-LINES PRE-SCAN):")
        for dl in profile.danger_lines_prescan:
            spk = f" ({dl.speaker})" if dl.speaker else ""
            lines.append(f"• [{dl.approx_time}]{spk} '{dl.english_phrase}' -> PUŁAPKA: {dl.contextual_trap} => DYREKTYWA: {dl.mandatory_direction}")

    if profile.relationship_pivots:
        lines.append("\n🔄 PUNKTY ZWROTNE I ZMIANY RELACJI W TRAKCIE ODCINKA (RELATIONSHIP PIVOTS):")
        for rp in profile.relationship_pivots:
            lines.append(f"• [{rp.approx_time}] {rp.characters_involved}: {rp.nature_of_shift} => NAKAZ: {rp.strict_direction_pl}")

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
            lines.append(f"• [{ca.canon_source_episode}] {ca.term_or_event} => DYREKTYWA: {ca.continuity_directive}")

    if profile.dramatic_sequences:
        lines.append("\n🗺️ MAPA SEKWENCJI DRAMATURGICZNYCH ODCINKA (DIARYZACJA OBSADY I SCEN JEDNOPŁCIOWYCH):")
        for seq in profile.dramatic_sequences:
            cast_str = f" [Obsada: {', '.join(seq.characters_present)}]" if getattr(seq, "characters_present", None) else ""
            gender_tag = ""
            if getattr(seq, "female_only_scene", False):
                gender_tag = " (🚨 SCENA WYŁĄCZNIE KOBIECA: bezwzględny wymóg form żeńskich w 1. i 2. os.!)"
            elif getattr(seq, "male_only_scene", False):
                gender_tag = " (SCENA WYŁĄCZNIE MĘSKA: bezwzględny wymóg form męskich!)"
            lines.append(f"• [{seq.time_range}] {seq.sequence_name}: {seq.dramatic_summary} (Ton: {seq.dominant_tone}){cast_str}{gender_tag}")

    if profile.character_dossiers:
        lines.append("\n🎭 KARTOTEKA OBSADY I MATRYCA IDIOLEKTÓW (CHARACTER DOSSIERS & IDIOLECT MATRIX):")
        for cd in profile.character_dossiers:
            pron = f" [Zaimek: {cd.first_person_pronoun}]" if cd.first_person_pronoun else ""
            decl = f" [Odmiana: {cd.declension}]" if cd.declension else ""
            dial = f" [Dialekt: {cd.dialect_category}]" if cd.dialect_category else ""
            idio = f" [Idiolekt: {cd.idiolect_matrix}]" if cd.idiolect_matrix else ""
            voc = f" [Głos: {cd.vocal_profile}]" if getattr(cd, "vocal_profile", "") else ""
            lines.append(f"• {cd.name} ({cd.gender}, {cd.age_and_role}){pron}{decl}{dial}{voc} -> Styl: {cd.speech_style_pl}{idio}")

    if profile.name_declensions:
        lines.append("\nŻELAZNA TABELA ODMIANY IMION PRZEZ PRZYPADKI (FILAR XCI - BEZWZGLĘDNIE STOSUJ):")
        for decl in profile.name_declensions:
            lines.append(f"- {decl.character_name} ({decl.gender}): {decl.declension_summary}")

    if profile.characters:
        lines.append("\nRELACJE SPOŁECZNE I FORMY ZWROTU (BEZWZGLĘDNIE PRZESTRZEGAJ):")
        for rel in profile.characters:
            lines.append(f"- {rel.speaker} -> {rel.listener}: {rel.address_form} ({rel.relationship_type})")

    if profile.glossary:
        lines.append("\nUSTALONY SŁOWNICZEK POJĘĆ I TERMINOLOGII BRANŻOWEJ (BAZA KANONICZNA W MIANOWNIKU):")
        for g in profile.glossary:
            lines.append(f"- '{g.term_en}' = '{g.translation_pl}' [Kontekst: {g.explanation} -> W zdaniu BEZWZGLĘDNIE ODMIENIAJ PRZEZ PRZYPADKI (np. 'w {g.translation_pl.lower()}'); wklejaj czystą polską nazwę bez dopisków w nawiasach!]")

    if profile.yojijukugo_and_idioms:
        lines.append("\nEKWIWALENTY JAPOŃSKICH PRZYSŁÓW I IDIOMÓW (FILAR XCV):")
        for idi in profile.yojijukugo_and_idioms:
            lines.append(f"- '{idi.term_en}' = '{idi.translation_pl}' [Kontekst: {idi.explanation} -> W zdaniu dopasuj gramatycznie i fleksyjnie do kontekstu; bez dopisków w nawiasach!]")

    if profile.key_conventions:
        lines.append("\nWYTYCZNE SPECYFICZNE DLA TEGO ODCINKA:")
        for conv in profile.key_conventions:
            lines.append(f"- {conv}")

    lines.append("=================================================================================\n")
    return "\n".join(lines)


def format_lean_episode_brief(profile: Any) -> str:
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
    lines.append("• KLUCZOWE ZASADY AVT: Angielski skrypt = treść, fakty i składnia; Głos seiyū = kotwica emocji, afektu i rejestru.")

    setting = _get(profile, "setting_and_era")
    tone = _get(profile, "tone_and_genre")
    if setting or tone:
        genre_info = f"{setting or ''} | {tone or ''}".strip(" |")
        lines.append(f"• Gatunek i Rejestr: {genre_info}")
        if any(h in genre_info.lower() for h in ["historyczn", "dworsk", "feudal", "średniowiecz", "starożytn", "mongol"]):
            lines.append("  (!) KATEGORYCZNY ZAKAZ WSPÓŁCZESNEGO SLANGU (np. 'zmywajmy się', 'nakryją nas') -> stosuj szlachetne 'uciekajmy', 'schwytają / odkryją'.")

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
                    if str(g).lower() in ("female", "kobieta") and any(w in (str(role) + " " + str(voc) + " " + str(name)).lower() for w in ["starsza", "dojrzała", "ochrypł", "babci", "matron", "cesarzow", "chatun", "boraqchin", "fatima", "töregene", "sitara", "möge"]):
                        lines.append(f"    (!) OCHRONA PŁCI ({name}): KOBIETA (niski F0 / ochrypły alt / zamknięta przestrzeń – zakaz męskich form!) – BEZWZGLĘDNY NAKAZ form żeńskich: -łam, -łabym, -łaś (np. 'miałabym', 'wiedziałam', 'zamierzałam')!")
        if rels:
            if isinstance(rels, dict):
                for spk, info in list(rels.items())[:8]:
                    role = _get(info, "role", "") or _get(info, "age_and_role", "")
                    g = _get(info, "gender", "")
                    if not g and is_inherently_female_name(spk):
                        g = "kobieta"
                    lines.append(f"  - {spk}: {g} ({role})")
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

    lines.append("================================================")
    return "\n".join(lines)


class EpisodeProfiler:
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
Twoim zadaniem jest dogłębna, wszechstronna analiza 100% skryptu całego odcinka, aby przygotować dla zespołu tłumaczy i redaktorów kompletny PROFIL ODCINKA 4.0:

1. OFICJALNY KANON POLSKIEGO WYDANIA MANGI (Filar XXIII, XCIV & XCVIII): Zidentyfikuj wydawnictwo (Waneko, J.P.Fantastica, Studio JG, Kotori, Hanami, Dango, Egmont) i podaj oficjalne nazwy z tomików papierowych.
   - KATEGORYCZNY ZAKAZ tworzenia sztucznych konstrukcji peryfrastycznych z przyimkiem 'od' dla przydomków i tytulatury (np. 'Aura the Guillotine' / 'Dantōdai no Aura' -> KATEGORYCZNY ZAKAZ 'Aura od Gilotyny'; POPRAWNY KANON Studio JG: 'Aura Gilotyna'; 'Jack the Ripper' -> 'Kuba Rozpruwacz'). Przydomki postaci w polszczyźnie tworzy się przez apozycję mianownikową (np. 'Aura Gilotyna', dop. 'Aury Gilotyny') lub tradycyjny epitet, a NIGDY przez mechaniczne kalkowanie 'X of the Y' jako 'X od Y'!
2. SKANER MIN JĘZYKOWYCH, PUŁAPEK ŚRODOWISKOWYCH I PRAGMATYCZNYCH (danger_lines_prescan): Przeskanuj cały odcinek i wskaż zdradliwe kwestie angielskie:
   - Idiomy i odmowy: 'I\'m fine' jako odmowa 'Ja podziękuję' zamiast 'Nic mi nie jest', 'Bless you', 'That bombed', 'Kikanaide', 'Sumimasen', 'Kanojo-tachi'.
   - Paradoks pytań przeczących (Filar CXXXIX): 'Hai/Yes' po pytaniu przeczącym ('Didn't you go?') -> ostrzeż przed dosłownym 'Tak!', nakaż 'Nie, nie poszedłem!'.
   - Fałszywe pokrewieństwo (Filar CXL): 'Big brother / Uncle / Onii-san' do obcych osób na ulicy -> ostrzeż przed bratem/wujkiem, nakaż 'Proszę pana / Młodzieńcze'.
   - Stan rezultatywny (Filar CXLI): 'Shinde iru / is dead' -> ostrzeż przed 'on umiera', nakaż 'nie żyje / jest martwy'.
   - Pytania z zachwytem (Filar CXLII): 'Janai ka? / Isn't it delicious / Umai janai' z podniesionym tonem -> ostrzeż przed krytyką, nakaż zachwyt 'Ale pycha!'.
   - Fizyczność sceny (Filar CXXXVIII): 'underwater' w browarze/bagnie -> ostrzeż przed słowem 'woda'; 'get down' w kosmosie -> ostrzeż przed 'padnij na ziemię'.
3. PUNKTY ZWROTNE I EWOLUCJA RELACJI (relationship_pivots & dynamiczne wektory więzi): Wskaż momenty w odcinku, w których następuje przełom i zmiana formy zwracania się do siebie (np. przejście z 'pani' na 'ty') oraz ogólną trajektorię rozwoju więzi w odcinku (np. nieufność -> narastające zaufanie po wspólnej walce), zabezpieczając przed regresją form grzecznościowych w kolejnych odcinkach.
4. POWIEDZONKA I KWESTIE-WIZYTÓWKI (character_catchphrases): Ustal jedno, kanoniczne polskie tłumaczenie dla powtarzających się motywów/zawołań postaci.
5. MATRYCA METRYCZNA DLA PIOSENEK OP/ED (song_transcreation_plans): Rozpoznaj piosenki i ustal plan sylabiczny (np. 8 sylab) i rymy Barańczaka (AABB/ABAB).
6. KALAMBURY I GRY SŁOWNE (puns_and_wordplays): Przekształć japońskie Dajare i Goroawase na autonomiczne polskie gry słowne wg zasad Stanisława Barańczaka (bez przypisów [Przyp. tłum.]!).
7. MOSTY CIĄGŁOŚCI (continuity_bridge_alerts): Wskaż terminy i wątki wymagające żelaznej spójności z całą serią.
8. CHRONOLOGICZNA MAPA SEKWENCJI DRAMATURGICZNYCH (dramatic_sequences): Podziel odcinek na 3-4 akty/sekwencje czasowe z opisem napięcia i tonu.
   - DLA KAŻDEJ SEKWENCJI BEZWZGLĘDNIE WSKAŻ characters_present (listę postaci rozmawiających w tej scenie, zwłaszcza gdy linie w skrypcie nie mają wpisanych nazwisk w polu Actor!).
   - PRYMAT RZECZYWISTOŚCI SCENICZNEJ I AUDIO NAD SKAŻONYMI TAGAMI FANSUBÓW (FILAR CLXXIV): W zewnętrznych plikach napisów (fansubach) pole Actor/Name bywa fałszywie otagowane (np. wpisany męski władca 'Ögedei', podczas gdy na ekranie w namiocie rozmawiają kobiety: 'Möge' i 'Boraqchin', a seiyū wymawia kwestię żeńskim głosem). W takich sytuacjach BEZWZGLĘDNIE zignoruj błędny tag aktora! Wskaż rzeczywistą obsadę obecną w scenie i ustaw female_only_scene = True! Zabezpiecz sceny przed fałszywym dodawaniem wspominanych w dialogach postaci historycznych/genealogicznych (np. 'rody Ugedeja, Tołuja' nie oznacza obecności tych mężczyzn w scenie!).
   - Jeśli w scenie rozmawiają wyłącznie kobiety (np. Fatima, Möge i Boraqchin Khatun), BEZWZGLĘDNIE ustaw female_only_scene = True! Zabezpiecza to potok przed domyślnym męskim biasem LLM w dialogach anonimowych.
   - Jeśli w scenie rozmawiają wyłącznie mężczyźni, ustaw male_only_scene = True!
9. KARTOTEKA OBSADY I IDIOLEKTY YAKUWARIGO (character_dossiers): Określ wiek, status, japońskie zaimki (Ore/Boku/Watashi/Washi/Sessha), dialekt (Kansai-ben) i unikalny polski rejestr mowy (Ojou-sama salonowy, Starzec staroświecki, Samuraj rycerski, Yankii szorstki, Kansai gawędziarski).
10. TABELA ODMIANY IMION PRZEZ PRZYPADKI (name_declensions) & MATRYCA RELACJI I TYTULATURY (characters):
   - ŻELAZNA FLEKSJA IMION FANTASY I ZACHODNICH (FILAR XCI): W seriach fantasy i obcojęzycznych imiona męskie zakończone na spółgłoskę (np. Drel, Gart, Klen, Arthur, Roland, Thorfinn, Eren, Armin) BEZWZGLĘDNIE ODMIENIAMY przez wszystkie polskie przypadki!
   - KATEGORYCZNY ZAKAZ pozostawiania obcych imion w mianowniku w dopełniaczu dzierżawczym (BŁĄD: 'Drel\'s secrets' -> 'sekretów Drel' [KOSZMARNA KALKA!]; POPRAWNIE: 'sekretów Drela'; 'Gart\'s sword' -> 'miecz Garta'). W tabeli 'name_declensions' bezwzględnie rejestruj WSZYSTKIE postacie (zarówno mówiące, jak i wspominane w dialogach w 3. osobie!) z ich pełną deklinacją.
   - PUŁAPKA KOŃCÓWKI '-A' W IMIONACH MĘSKICH (FILAR CLVII & CLXII): Wiele imion japońskich i orientalnych kończy się na samogłoskę '-a' (np. Shira, Akira, Gaara, Ashitaka, Kiba, Soma, Kenta, Ryoma, Hanza) i są to POSTACIE MĘSKIE! KATEGORYCZNY ZAKAZ klasyfikowania postaci jako kobiety wyłącznie na podstawie litery '-a' na końcu imienia. Sprawdź rolę społeczną, zaimki (Ore/Boku) i kontekst wypowiedzi. W języku polskim dla postaci męskich orzeczenia w czasie przeszłym BEZWZGLĘDNIE wymagają formy męskiej: 'Shira mówił / ostrzegał / pomógł / zrobił', a NIE żeńskiej ('ostrzegała')!
   - PUŁAPKA FONETYCZNA OBCYCH IMION MĘSKICH NA '-CA' (FILAR CLVII): Imiona męskie obcego pochodzenia zakończone na '-ca' (np. Luca, Petrarca, Seneca, Checa) w języku polskim wymawiane są z twardym [k] i odmieniają się ze zmianą na 'k': dopełniacz: 'do Luki' (KATEGORYCZNY ZAKAZ ŻEŃSKIEGO POTWORKA: 'do Luci' [błąd zmiany płci na Łucję!]); biernik: 'Lukę', narzędnik: 'z Luką', miejscownik: 'o Luce', wołacz: 'Luco / Luko'!
   - PUŁAPKA FAŁSZYWYCH IMION Z JAPOŃSKICH RZECZOWNIKÓW POSPOLITYCH I TYTUŁÓW (FILAR II & KANON): Kategoryczny zakaz traktowania japońskich rzeczowników pospolitych, ról baśniowych i tytułów jako imion własnych pisanych wielką literą! Dotyczy to w szczególności: 'ōji / ouji' (książę -> KATEGORYCZNY ZAKAZ: 'Ouji' jako imię!), 'hime / oujo' (księżniczka), 'sensei' (nauczyciel / mistrz), 'senpai' (starszy kolega), 'kouhai', 'shishou', 'danna', 'aniki'. W dialogach i tabelach rejestruj ich poprawne polskie odpowiedniki!
   - SPOLSZCZANIE HONORYFIKATORÓW 'SENPAI' I SLANGU (FILAR II & C): Japońskie relacje starszeństwa ('senpai') w polskim dialogu filmowym nie mogą być pozostawiane jako surowe słowo 'Senpai' wielką literą ani '[Nazwisko]-senpai' (BŁĄD: 'prawda, Senpai?' / 'Akaishi-senpai'). Zastępuj je imieniem/nazwiskiem rozmówcy ('Akaishi!', 'Rinko!'), zwrotem grzecznościowym ('pani Akaishi') lub usuwaj z zawołania. Służący za pieszczotliwy slang internetowy sufiks '-taso' (np. 'Kuro-taso') adaptuj jako kanoniczne imię / pieszczotliwe zdrobnienie ('Kuroe' / 'Kuro-tan').
   - BEZWZGLĘDNA NADRZĘDNOŚĆ OFICJALNEGO KANONU MANGOWEGO (FILAR II & KANON): Jeśli seria posiada licencjonowane polskie wydanie papierowe (np. Studio JG dla 'Otome Kaijuu Carameliser' / 'Potworna słodycz'), oficjalne przydomki i pojęcia mają bezwzględny priorytet (np. 'Monster Prince' = 'Potworny Królewicz'; KATEGORYCZNY ZAKAZ amatorskich wariantów typu 'Książę Kaiju').
   - PROPAGACJA BIERNIKA PRZY WSPÓŁRZĘDNOŚCI (FILAR CLVII & XCI): Gdy czasownik rządzi biernikiem w konstrukcji z dwoma dopełnieniami połączonymi spójnikiem 'i' / 'oraz' (np. 'Przedstawiono Minamiego i Harugona'), oba człony BEZWZGLĘDNIE podlegają deklinacji w bierniku (KATEGORYCZNY ZAKAZ: 'Minamiego i Harugon'!).
   - ZAKAZ SAMOTNYCH MYŚLNIKÓW DIALOGOWYCH W KWESTIACH JEDNOOSOBOWYCH (FILAR XCI): W polskiej szkole AVT myślnik '- ' stosuje się wyłącznie przy dwóch mówcach w jednym kadrze (dialogue double). Kategoryczny zakaz rozpoczynania kwestii jednoosobowej od myślnika (BŁĄD: '- Ocalę cię!' -> POPRAWNIE: 'Ocalę cię!').
   - ZAKAZ ZBĘDNEGO PRZECINKA PRZED 'CZY' W ALTERNATYWIE ROZŁĄCZNEJ (FILAR XCI): W pytaniach rozłącznych typu 'w kapciach czy bez?', 'kawa czy herbata?' przecinek przed 'czy' jest błędem interpunkcyjnym (KATEGORYCZNY ZAKAZ: 'w kapciach, czy bez?').
   - ZAKAZ AGRESYWNEJ KALKI 'I CO Z TEGO?' DLA ZACIEKAWIONEGO 'AND SO? / SORE DE?' (FILAR IV & CLVI): W naturalnym dialogu dopytującym o ciąg dalszy, wyznanie miłości lub rozwój sytuacji, japońskie 'Sore de?' / angielskie 'And so?' tłumaczymy jako 'I co?', 'I jak?', 'Więc?' (KATEGORYCZNY ZAKAZ opryskliwego, wrogiego 'I co z tego?').
   - PUŁAPKA TYTUŁÓW I RÓL ZAWODOWYCH (FILAR CLXII): Tytuły i profesje (np. teacher/nauczyciel, professor/profesor, spy/szpieg, knight/rycerz, commander/dowódca, mage/mag) w języku angielskim i japońskim są bezpłciowe. KATEGORYCZNY ZAKAZ domyślnego uznawania postaci za mężczyznę wyłącznie z powodu funkcji zawodowej! Zawsze zweryfikuj czy postać nie jest kobietą (nauczycielką, szpiegiem-kobietą) na podstawie relacji, głosu seiyū, kontekstu i zaimków.
   - ROZPOZNANIE ADRESATA: POJEDYNCZA KOBIETA/MĘŻCZYZNA ORAZ LICZBA MNOGA (FILAR CLXIII): W dialogach zwracaj uwagę na to, do kogo skierowana jest wypowiedź (adresat). W języku angielskim zaimek 'you' jest bezpłciowy i wieloznaczny (ty [kobieta/mężczyzna], wy [grupa kobiet/mężczyzn/mieszana], pan, pani):
      * POJEDYNCZA KOBIETA ('kobieta'): Gdy w rozmowie 1-na-1 'you' skierowane jest do kobiety/dziewczyny (np. 'Are you sure?', 'Were you there?', 'You did well'), w języku polskim orzeczenia czasu przeszłego i przymiotniki BEZWZGLĘDNIE wymagają rodzaju żeńskiego: 'Jesteś pewna? / Byłaś tam? / Dobrze się spisałaś / Zrobiłaś to / Miałaś rację' (KATEGORYCZNY ZAKAZ form męskich: 'byłeś', 'zrobiłeś', 'miałeś', 'pewien')!
      * POJEDYNCZY MĘŻCZYZNA ('mężczyzna'): Gdy wypowiedź skierowana jest do mężczyzny/chłopaka, bezwzględnie stosuj formy męskie: 'Jesteś pewien? / Byłeś tam? / Dobrze się spisałeś / Zrobiłeś to' (ZAKAZ: 'byłaś', 'zrobiłaś').
      * GRUPA KOBIET ('grupa_kobiet'): Wymusza formy niemęskoosobowe ('zrobiłyście / byłyście gotowe / widziałyście').
      * GRUPA MĘŻCZYZN / MIESZANA ('grupa_mężczyzn' / 'grupa_mieszana'): Wymaga form męskoosobowych ('zrobiliście / byliście gotowi / widzieliście'). Ostrzegaj przed kalkowaniem 'you' w liczbie pojedynczej tam, gdzie w scenie lub audio seiyū (-tachi, minna, omae-ra) zwrot skierowany jest do grupy!
    - RELACYJNA STAŁOŚĆ REJESTRU (T-V INVARIANCE) I OCHRONA PRZED HYBRYDAMI WOŁACZA (FILAR C & CLVII):
       * KATEGORYCZNY ZAKAZ WEWNĄTRZZDANIOWYCH HYBRYD WOŁACZA Z FORMĄ GRZECZNOŚCIOWĄ (INTRA-CLAUSE T-V HYBRID BAN): Kategorycznie zabrania się łączenia w jednej wypowiedzi poufałego wołacza po imieniu z honoryfikatywną formą grzecznościową per pan/pani (KARDYNALNY BŁĄD [X]: 'Poza tym, Eftalu... ma pan zaczerwienioną twarz'; POPRAWNIE: 'Poza tym, panie Eftalu... ma pan zaczerwienioną twarz' LUB na 'ty': 'Poza tym, Eftalu... masz zaczerwienioną twarz'). Jeśli postać zwraca się per pan/pani, wołacz ZAWSZE musi zawierać tytuł: 'Panie [Imię]!' / 'Pani [Imię]!'.
       * ODPORNOŚĆ NA ANGIELSKIE OPUSZCZANIE SUFIKSU -SAMA (ENGLISH '-SAMA' DROP IMMUNITY): W angielskich skryptach anime zachodni tłumacze nagminnie usuwają honoryfikatywny przyrostek '-sama' / '-dono' / '-sensei' w okrzykach i zawołaniach (np. w JP: 'Eftal-sama!', w EN: 'Ephtal!'). KATEGORYCZNY ZAKAZ kopiowania tego nawyku jako poufałego wołacza po imieniu (BŁĄD: 'Co za kunszt, Eftalu!' w ustach uczennicy/służącej). W polszczyźnie relacja uczeń-mistrz czy podwładny-pan jest stała: w zawołaniach BEZWZGLĘDNIE stosuj 'Panie [Imię]!' ('Co za kunszt, panie Eftalu!').
       * KONSISTENTNOŚĆ TYTULATURY PODMIOTU (BRAK SKAŻENIA PRZYPADKA): Gdy tytulatura 'pan' występuje w mianowniku jako podmiot z czasownikiem w 3. osobie (np. 'pan [Imię] zniszczył / zrobił / pokonał'), męskie imię na spółgłoskę BEZWZGLĘDNIE pozostaje w mianowniku (BŁĄD: 'odkąd pan Eftala zniszczył' [skażenie dopełniaczem!]; POPRAWNIE: 'odkąd pan Eftal zniszczył').
    - PODWÓJNY RZĄD PRZYIMKA 'ZA' W KONSTRUKCJACH MAŁŻEŃSTWA I WYMIANY (FILAR CLXVII): W języku polskim 'wyjść za' kogoś rządzi BIERNIKIEM (np. 'wyjść za Gujuka' [Biernik od Gujuk], 'oddać za kogoś życie', 'zapłacić za brata', 'uznać za zmarłego'). KATEGORYCZNY ZAKAZ fałszywego narzędnika: 'wyjść za Gujukiem', ani fałszywego mianownika: 'wyjść za Gujukę'!
    - PURYZM REJESTRU DRAMATU HISTORYCZNEGO I DARK FANTASY (FILAR CLXVII): W seriach historycznych i epickich kategorycznie eliminuj współczesne kalki konwersacyjne i potoczny slang: 'Good question' -> 'Trudno powiedzieć / Ciekawe zagadnienie' (ZAKAZ: 'Dobre pytanie!'), 'W sumie to nam na rękę' -> 'W istocie / W gruncie rzeczy to nam na rękę', 'Oj tam!' -> 'Daj spokój!'.
11. SŁOWNICZEK POJĘĆ BRANŻOWYCH (glossary) ORAZ JAPOŃSKICH PRZYSŁÓW/IDIOMÓW (yojijukugo_and_idioms): Podawaj wyłącznie CZYSTE, DOCELOWE polskie nazwy własne i terminy bez żadnych dopisków w nawiasach.
12. EPOKA, REALIA ŚWIATA I DZIEDZINA SPECJALISTYCZNA.
13. ŻELAZNA CZYSTOŚĆ ORTOGRAFICZNA I BEZWZGLĘDNA ELIMINACJA LITERÓWEK (FILAR CLXIV):
   - Kategoryczny zakaz wprowadzania lub tolerowania zniekształconych, nieistniejących form leksykalnych i literówek w dialogach i glosariuszu.
   - Czasownik 'spytać / zapytać': w 1. os. lp. czasu przyszłego ma wyłącznie formę 'spytam' lub 'zapytam' (KARDYNALNY BŁĄD [X]: 'spyham' [nieistniejący potworek leksykalny!]; POPRAWNIE: 'spytam / zapytam').
   - Ostrzegaj przed wszelkimi deformacjami ortograficzno-fonetycznymi ('spyham' -> 'spytam', 'wziąść' -> 'wziąć', 'poszłem' -> 'poszedłem', 'włanczać' -> 'włączać').
14. KANON CZYSTOŚCI WIZUALNEJ AVT, ZASADA ELIPSY SZUMU KINEZJATYCZNEGO I OCHRONA PRZED KALKAMI 'HERE' (FILAR XVIII & IV):
   - Kakegoe kinestetyczne (odgłosy wysiłku fizycznego seiyū: Yoisho, Dokkoisho, Yotto, Yoi-kora, hai oddechowe przy wstawaniu z krzesła, podnoszeniu ciężaru, siadaniu, kucaniu):
     * KATEGORYCZNY NAKAZ ELIPSY (pusty napis `""` lub pominięcie kwestii). W polskiej szkole AVT dorosłe postacie nie mają napisów pod stęknięciem przy wstawaniu!
     * KATEGORYCZNY ZAKAZ infantylnych podpisów w rodzaju 'Hop...', 'I siup...', 'Raz, dwa...' oraz grzecznościowych pomyłek 'Proszę...'.
   - Gest podawania przedmiotu / częstowania (Hai, Dōzo, Hora -> w EN: 'Here', 'There you go'):
     * KATEGORYCZNY ZAKAZ KOSZMARNEJ KALKI: 'Here' -> 'Tutaj' / 'Tu' (nikt w Polsce podając herbatę czy klucze nie mówi 'Tutaj!').
     * POPRAWNIE: w większości scen elipsa `""`, a jeśli gest wymaga zaznaczenia w dialogu: wyłącznie naturalne 'Proszę' lub 'Trzymaj / Masz' (w akcji: 'Łap!').
   - Bezwzględne niezmienniki językowe: 'w każdym bądź razie' -> 'w każdym razie', 'w cudzysłowiu' -> 'w cudzysłowie', 'po najmniejszej linii oporu' -> 'po linii najmniejszego oporu', 'pod rząd' -> 'z rzędu', 'spowrotem' -> 'z powrotem', 'dlatego bo' -> 'dlatego że', 'Zrób swoje najlepsze!' -> 'Daj z siebie wszystko!', 'Dobrej nocy!' -> 'Dobranoc!'.
15. DYSKONTINUITET CZASOWY, PRZESKOKI SCEN I ODCZAROWANIE FAŁSZYWEGO PRZYLEGANIA (FILAR CLXV):
   - Przeskanuj cały odcinek pod kątem kwestii przedzielonych dużą przerwą czasową (Δt ≥ 5-10s) lub cięciem montażowym (przejście do innego pomieszczenia, pleneru, na osobność):
      * PUŁAPKA OPÓŹNIONEGO POTWIERDZENIA (DELAYED AGREEMENT FALLACY): Gdy postać A prosi o rozmowę na osobności ('Moglibyśmy porozmawiać na osobności?' / 'Can we talk in private?'), a po długiej pauzie (np. 15-25s) postać B w nowej lokacji odpowiada w EN 'Sure, what is it?' / 'All right, what\'s up?':
        -> KATEGORYCZNY ZAKAZ traktowania tego jako opóźnionej zgody na wyjście: 'Jasne / Pewnie / W porządku, o co chodzi?' (bohaterowie JUŻ tam stoją!).
        -> NAKAZ otwarcia rozmowy w nowej scenie: 'Więc o co chodzi?' / 'No to o co chodzi?' / 'Słucham cię' / 'O co chodzi?'.
      * WYCIEK SPÓJNIKÓW PO CIĘCIU (CONJUNCTION BLEED): ZAKAZ zaczynania kwestii po długiej pauzie od spójników łączących ('I co z tego?', 'A więc...').
      * DRYF ZAIMKOWY I RESET EMOCJONALNY: Zaimki 'to/on' po zmianie kadru muszą być sprecyzowane; krzyk z walki nie może przenikać do cichej sceny po cięciu.
      * W sekcji danger_lines_prescan bezwzględnie wskaż tego typu luki czasowe i nakaż właściwe otwarcie dialogu!

16. PROTOKÓŁ ANTY-PIVOT I ELIMINACJA KLISZ FANSUBERSKICH (FILAR CLXVI):
       * 'Come back in one piece / Return in one piece' -> 'Wracaj cały i zdrowy!' / 'Wracaj cały!' (KATEGORYCZNY ZAKAZ: 'w jednym kawałku').
       * 'Don\'t get your hopes up / Don\'t get your hope up' -> 'Nie liczcie na mnie!' / 'Przeliczycie się!' / 'Nie łudźcie się!' (KATEGORYCZNY ZAKAZ: 'nie róbcie sobie nadziei' / 'nie rób sobie nadziei').
       * 'Die at the hands of [monster/kaiju/beast]' -> 'zginąć pod ciosami / w starciu z / w paszczy' (KATEGORYCZNY ZAKAZ kalki: 'zginąć z ręki [potwora/bestii]').
       * 'Kick his/someone\'s ass' w ustach dzieci i młodzieży -> 'Daj mu popalić!' / 'Dołóż mu!' (KATEGORYCZNY ZAKAZ kalki: 'Skop mu tyłek!').
       * 'Why didn\'t I just listen to her' -> 'Dlaczego jej nie posłuchałem?' (KATEGORYCZNY ZAKAZ: 'Czemu po prostu jej nie wysłuchałem').
       * 'Sure, what is it?' / 'All right, what\'s up?' po pauzie -> 'Więc o co chodzi?' / 'Słucham cię' (ZAKAZ: 'Jasne...').
       * 'Welcome back' (l. poj. i mn.: 'Witaj!', 'Witajcie!', 'Wróciłeś!', 'Wróciła!', 'Wróciliście!') -> KATEGORYCZNY ZAKAZ: 'Witaj z powrotem' / 'Witajcie z powrotem' / 'Witam z powrotem'.
       * 'Makes sense / That makes sense' -> 'To ma sens / Rozumiem / To logiczne' (KATEGORYCZNY ZAKAZ: 'Robić sens' we wszystkich odmianach i szykach: 'robi sens', 'robi to sens', 'robiło sens', 'robiłoby sens').
       * 'I hope so / We hope so / He hopes so' -> 'Oby!' / 'Mam nadzieję!' / 'Mamy nadzieję!' (KATEGORYCZNY ZAKAZ: 'mieć taką nadzieję' we wszystkich osobach: 'mam taką nadzieję', 'mamy taką nadzieję', 'ma taką nadzieję').
       * 'There is no way (that)...' -> 'Wykluczone, by...', 'To niemożliwe, żeby...', 'Nie ma mowy, bym/byśmy/żeby/aby...'.
       * Tytulatura w relacjach szkolnych i mentorskich: KATEGORYCZNY ZAKAZ archaizmu 'Panno [Imię/Nazwisko]'! W relacji uczeń -> nauczycielka/mentorka obowiązkowo stosuj 'pani [Nazwisko]' (np. 'pani Teshimo'), 'pani profesor' lub 'Teshima-sensei' (KATEGORYCZNY ZAKAZ: 'panno Teshimo'). Nauczycielka do uczennicy mówi po nazwisku ('Yasumi') lub imieniu ('Ai') bądź 'Yasumi-san' (KATEGORYCZNY ZAKAZ: 'Panno Yasumi'). Wypowiedzi o nauczycielce w 3. osobie wymagają 'pani [Nazwisko]' (np. 'notes pani Teshimy', 'pani Teshima mówiła'; ZAKAZ: 'panny Teshimy', 'Panna Teshima').
       * Zakaz żargonu IT w procesie twórczym (Filar X & I): KATEGORYCZNY ZAKAZ kalkowania pojęć 'input / output' w odniesieniu do twórczości mangowej i pisarskiej (BŁĄD: 'cykl inputu i outputu', 'potrzebujesz więcej inputu'). Stosuj wyłącznie naturalne polskie pojęcia: 'czerpanie inspiracji / zbieranie doświadczeń / chłonięcie wrażeń' oraz 'tworzenie / przelewanie na papier / rysowanie'.
       * Fleksja zamówień gastronomicznych (Filar CXXXVII): Zwrot zamówienia w lokalu ('Dla mnie [co?]') bezwzględnie wymaga biernika (np. 'Dla mnie Gojinkę z wodą', 'Dla mnie herbatę'; KATEGORYCZNY ZAKAZ mianownika: 'Dla mnie Gojinka').
       * Lokalizacja japońskich okrzyków pirotechnicznych (Filar CLXIV): Japoński okrzyk festiwalowy 'Tamaya!' (tradycyjny okrzyk cechu pirotechników z Edo) bezwzględnie zlokalizuj na naturalny okrzyk zachwytu nad fajerwerkami ('Ale widok!', 'Cudo!', 'Ooo, jak pięknie!'; KATEGORYCZNY ZAKAZ surowego fansuberskiego 'Tamaya!').
       * Zdrobnienia slangu: KATEGORYCZNY ZAKAZ tworzenia sztucznych fonetycznych potworków w rodzaju 'Kuro-tasia', 'Manacia' pod japońskie sufiksy '-taso' / '-cchin'.
       * Relacje rówieśnicze w szkole i klubie (Filar XXV & IX): KATEGORYCZNY ZAKAZ form per 'Pan/Pani [Nazwisko]' i czasowników w 3. osobie grzecznościowej między uczniami i rówieśnikami z tej samej klasy/klubu szkolnego (KARDYNALNY BŁĄD: 'Pani Fujimori, ma pani skaner?' / 'Pani Fujimori, spokojnie!'). Japoński grzeczny przyrostek '-san' używany przez licealistkę do koleżanki z klubu mangi to w polszczyźnie samo nazwisko lub imię w bezpośredniej relacji na 'ty' (POPRAWNIE: 'Fujimori, masz skaner?' / 'Fujimori, spokojnie!' / 'gdy Fujimori skończy').
       * Żelazna niezmienniczość T-V w relacji wydawca-autor (Filar XXV & CLVI): W relacji redaktorki wydawnictwa z autorką mangi (np. Hana Kongouji <-> Rei Teshima) bezwzględnie utrzymuj żelazny rejestr grzecznościowy per 'Pani' w 100% kwestii. KATEGORYCZNY ZAKAZ hybrydyzacji i zsuwania się na 'ty' w tej samej scenie! Angielskie 'Trust me!' to wyłącznie 'Proszę mi zaufać!' / 'Niech mi pani zaufa!' (KATEGORYCZNY ZAKAZ poufałego 'Zaufaj mi!'). Pytania i zdania warunkowe redaktorki: 'Co pani zamierza?', 'Jeśli chce pani publikować... musi pani wprowadzić zmiany...', 'Wiem, że ma pani opory', 'Jeśli jest pani na to gotowa, w pełni pani pomogę' (ZAKAZ: 'Co zamierzasz?', 'Jeśli chcesz... musisz...', 'masz opory', 'ci pomogę').
        * Typografia i czystość dialogowa AVT (Filar LX): KATEGORYCZNY ZAKAZ wprowadzania japońskich tyld emocjonalnych ('~') oraz zwielokrotnionych wykrzykników/pytajników w dialogach (BŁĄD: 'odjechane~!!!!' -> POPRAWNIE: 'odjechane!'). Maksymalnie jeden wykrzyknik lub pytajnik.
        * Typografia plansz tytułowych i szyldów (Filar XCVIII & LX): KATEGORYCZNY ZAKAZ pakowania wieloczłonowych plansz w jedną niepodzieloną linię (>42 znaki) oraz używania notacji nawiasów kwadratowych [ A ] [ B ]. Plansze tytułowe dziel na zwięzłe wersy z \\N (maks. 36-40 znaków na wiersz).
       * Wielogłos symultaniczny i kwestie dwugłosowe (Filar LVII): Kwestie dwóch różnych postaci połączone myślnikiem w jednej linii ('A - B') BEZWZGLĘDNIE rozbijaj na dwie osobne linie z myślnikiem i spacją na początku każdej ('- A\\N- B'). KATEGORYCZNY ZAKAZ łączenia ich w jeden wiersz bez formatowania dwugłosu!
       * Tautologie i zacięcia słownikowe tytułów dzieł/kronik: KATEGORYCZNY ZAKAZ dublowania słowa 'kronika' ('w Kronice Kronika Taiheiki' -> 'w Kronice Taiheiki', '[ KRONIKA Kronika Taiheiki ]' -> '[ KRONIKA TAIHEIKI ]').
       * Błędne związki frazeologiczne i inwersja afektywna (Filar X): KATEGORYCZNY ZAKAZ łączenia idiomu 'odchodzić od zmysłów' z pozytywnymi emocjami (KARDYNALNY BŁĄD: 'odchodzić od zmysłów ze szczęścia'). 'Odchodzić od zmysłów' łączy się wyłącznie z negatywnymi stanami (rozpacz, lęk, żal). W radości stosuj: 'szaleć ze szczęścia' lub 'nie posiadać się z radości'.
       * Składnia związku zgody liczebników wielotysięcznych (Filar IV): Konstrukcje z podmiotem liczebnikowym w liczbie mnogiej wymagają orzeczenia w liczbie mnogiej (POPRAWNIE: 'Dwa tysiące w zupełności wystarczą'; BŁĄD: 'wystarczy').
       * Kalka auto-referencyjna z angielskiego: KATEGORYCZNY ZAKAZ 'moja droga ja' / 'droga ja' (kalka z angielskiego 'my dear me'). W monologu wewnętrznym stosuj naturalne polskie formy: 'moja ty mała', 'mała ja', 'taka ze mnie drobina'.
       * PROAKTYWNA MATRYCA REJESTRU DARK FANTASY (4 KLASY ZAKAZANEGO SLANGU): W uniwersach mrocznego i wysokiego fantasy (Clevatess, Frieren itp.) bezwzględnie obowiązuje podniosły, literacki rejestr dialogowy. Kategoryczny zakaz używania 4 klas współczesnego socjolektu:
           - KLASA A (Slang młodzieżowy/potoczny): 'I gitara' -> 'Doskonale / Świetnie', 'spoko', 'siemanko', 'wchodzę w to' -> 'Zgadzam się / Przyjmuję ten układ', 'Bez jaj!' -> 'Niemożliwe! / To jakieś kpiny! / Chyba żartujesz!'.
           - KLASA B (Agresja podwórkowa i trywializacja): 'stul pysk' -> 'Zamilcz / Milcz', 'zamknij się', 'spuścić potworny łomot' -> 'zmiażdżyć bez trudu / rozgromić w pył', 'oberwę' -> 'poniosę karę / zginę', 'guzik mnie to obchodzi' -> 'nic mnie to nie obchodzi / niewiele mnie to obchodzi', 'pora stąd zwiewać / zwiewamy' -> 'pora stąd uciekać / uciekajmy'.
           - KLASA C (Współczesne metafory potoczne): 'przejmuję stery' -> 'teraz ja mówię / ja przejmuję kontrolę', 'dla zabicia czasu' -> 'dla rozrywki', 'kłamstwo jak byk' -> 'bezczelne kłamstwo / łgarstwo w żywe oczy', 'wylatuje ze szkoły' -> 'zostaje wydalony ze szkoły', 'utrzeć nosa' -> 'pokazać swoje miejsce'.
           - KLASA D (Trywializujące określenia osób i zaimki): 'ten typ' -> 'ten człowiek / ten nauczyciel', 'dzikuska / chuliganka' -> 'prostaczka / awanturnica', 'dzieciaki' -> 'uczniowie / młodzież', 'durna jestem' -> 'głupia jestem'.
        * ZAKAZ KALKI PRZYDOMKÓW 'X OD Y' (FILAR X & KANON): Japońskie przydomki bóstw i władców 'no' (np. Gensou no Zavthier, Enshou no Vordin) w polszczyźnie fantasy tłumaczymy przymiotnikowo lub czystym dopełniaczem, NIGDY kalką z przyimkiem 'od' (KATEGORYCZNY ZAKAZ: 'Zavthier od Złudzeń' -> 'Zavthier Pani Iluzji / Iluzoryczna Zavthier'; 'Vordin od Płomiennego Żaru' -> 'Vordin Płomiennego Żaru / Płomienny Vordin'; jak w kanonie Frieren: 'Aura Gilotyna', nie 'od Gilotyny').
        * RZĄD I RODZAJ GRAMATYCZNY RZECZOWNIKA 'POSOKA': 'Posoka' jest w języku polskim wyłącznie rodzaju żeńskiego (ta czarna posoka, tej czarnej posoki, tę czarną posokę). KATEGORYCZNY ZAKAZ tworzenia form męskich ('czarny posok', 'przez czarny posok', 'z czarnego posoku' -> POPRAWNIE: 'czarna posoka', 'przez czarną posokę', 'z czarnej posoki').
        * FLEKSJA I WOŁACZ TYTUŁÓW I NAZWISK OBCYCH: 'Święty Miecza Owenie Koath' -> 'Święty Miecza Owenie Koacie' (nazwisko Koath w wołaczu podlega regularnemu zmiękczeniu). 'Księga Toah' -> 'Księga Toaha'. 'Andrew' w wołaczu -> 'Andrewie'.
        * Rząd przyimkowy dla urazu i traumy: KATEGORYCZNY ZAKAZ 'mam przez coś uraz' (kalka z angielskiego 'have trauma from'). W języku polskim: 'mam do czegoś uraz' lub 'mam przez to traumę'.
        * Związek zgody rodzaju gramatycznego dla rzeczownika 'sługa': KATEGORYCZNY ZAKAZ 'moja sługa'! Rzeczownik sługa jest gramatycznie męskoosobowy. Jeśli mowa o kobiecie (np. Alicii jako podwładnej Klena), stosuj 'moja podwładna' lub 'moja służąca' ('by moja podwładna mogła uciec').
        * Kalka składniowa wykluczenia: KATEGORYCZNY ZAKAZ 'dla wszystkiego poza X nie ma litości' (kalka z 'no mercy for anything other than'). Stosuj czystą polszczyznę: 'Nie ma litości dla niczego prócz X' lub 'Oszczędza wyłącznie X'.
        * Błędne łączenie idiomu ze sformułowaniem czasowym: KATEGORYCZNY ZAKAZ 'w cztery oczy od czasu X'. 'W cztery oczy' oznacza rozmowę na osobności, a nie cezurę czasową. Stosuj: 'na osobności od czasów X' lub 'sam na sam od czasów X'.
        * KATEGORYCZNY ZAKAZ AUTO-ADRESACJI I ŚLEDZENIE PARTNERA DIALOGOWEGO: Mówca nigdy nie zwraca się do siebie własnym imieniem! Przy adaptacji japońskich wołaczy ('Senpai', 'Sensei') w kwestiach jedno- i wieloliniowych, jeśli zwrot jest tłumaczony imieniem, należy bezwzględnie zidentyfikować partnera dialogowego (adresata), a NIE mówcę. W przypadku wątpliwości stosować formę bezimienną lub eliptyczną ('Prawda?', 'Słuchaj!', 'Nic ci nie jest?').
        * ZDROBNIENIA SEIYŪ I SŁOWOTWÓRSTWO AFEKTYWNE ('-tan', '-taso', '-cchin'): KATEGORYCZNY ZAKAZ okaleczania imion do uciętych rdzeni (np. 'Kuro-tan' / 'Kuro-taso' -> KARDYNALNY BŁĄD: 'Kuro'; POPRAWNIE: kanoniczne pełne imię 'Kuroe'). W sekcji glossary oraz character_dossiers należy bezwzględnie powiązać hipokorystyki z pełnymi imionami kanonicznymi.
        * KOREKTA POUFAŁOŚCI NA FORMĘ OFICJALNĄ ('[Nazwisko]-senpai'): Gdy postać wycofuje się z poufałego imienia do formy formalnej (np. 'Odpuść, Rinko' -> 'Nie ma mowy!' -> 'To znaczy... Akaishi-senpai'), w języku polskim należy bezwzględnie zastosować 'panno [Nazwisko]' (dla kobiety) lub 'panie [Nazwisko]' (dla mężczyzny), a NIE chłodne, obcesowe samo nazwisko bez tytułu ('To znaczy... panno Akaishi', ZAKAZ: 'To znaczy... Akaishi').
        * WOŁACZ PRZYDOMKÓW MEDIALNYCH I TYTUŁÓW: Gdy postacie zwracają się do bohatera jego oficjalnym przydomkiem (np. Arata jako 'Potworny Królewicz' w Otome Kaijuu Carameliser), zwrot bezpośredni w wołaczu musi brzmieć 'królewiczu!' lub 'Królewiczu!', a nie 'książę' (zgodnie z oficjalnym kanonem wydawnictwa papierowego Studio JG).
        * Gest podania rekwizytu z angielskim 'Here' -> 'Proszę' / 'Trzymaj' (KARDYNALNY BŁĄD: 'Tutaj!').
 17. NATURALNA SKŁADNIA DEIKTYCZNO-TEMPORALNA I DEKOMPOZYCJA PRZYDAWKI CZASOWEJ (FILAR CLXVIII):
    - KATEGORYCZNY ZAKAZ tworzenia sztucznych odprzysłówkowych przymiotników temporalnych w dialogach (np. 'pojutrzejszy', 'przedwczorajszy', 'w dzisiejszy wieczór', 'w jutrzejszy poranek', 'we wczorajszy wieczór', 'przyszłotygodniowy').
    - Japońskie konstrukcje temporalne 'X no Y' (np. 明後日の宴 asatte no utage, 明日の朝 ashita no asa, 今日の夜 kyou no yoru) oraz angielskie fansuberskie przydawki czasu ('day-after-tomorrow\'s feast') w polszczyźnie mówionej ZAWSZE dekomponuj na naturalne frazy okolicznikowe:
      * 'Chodzi o pojutrzejszą ucztę' -> KATEGORYCZNY BŁĄD! POPRAWNIE: 'Chodzi o ucztę pojutrze' / 'Chodzi o tę ucztę za dwa dni' / 'Chodzi o ucztę zaplanowaną na pojutrze'.
      * 'pojutrzejsze spotkanie' -> 'spotkanie pojutrze' / 'spotkanie za dwa dni'.
      * 'przedwczorajszy incydent / kłótnia' -> 'incydent sprzed dwóch dni / kłótnia sprzed dwóch dni'.
      * 'w dzisiejszy wieczór' -> 'dziś wieczorem'; 'w jutrzejszy poranek' -> 'jutro rano'; 'we wczorajszy wieczór' -> 'wczoraj wieczorem'; 'w dzisiejszą noc' -> 'dziś w nocy'.
      * 'przyszłotygodniowe zawody' -> 'zawody w przyszłym tygodniu'.
    - W glosariuszu i osi czasu odcinka kategorycznie zakazuj wprowadzania terminów ze sztuczną przydawką temporalną.
    - W mandatory_direction wymuś nadrzędność dramaturgii i japońskiego audio seiyū nad dosłownym skryptem angielskim.
 18. DYSCYPLINA SOCJOLEKTU, ZAKAZ WYCIEKU KSYWEK RÓWIEŚNICZYCH I MORFOLOGICZNY PRYMAT PŁCI POSTACI (FILAR CLXIX):
    - SPEAKER-SCOPED HYPOCORISM GUARD: Specyficzne, slangowe zdrobnienia i ksywki nadawane przez pojedynczych rówieśników (np. gyaru Sachi Akafuku mówiąca 'Hikarun' do Hikaru Sekiryu, 'Tessie' do Teshimy) należą WYŁĄCZNIE do tej pary postaci!
      * KATEGORYCZNY ZAKAZ przypisywania tych ksywek matce ('Hebichika'), ojcu, mentorom czy w retrospekcjach ('Flashback')!
      * Gdy matka w audio mówi 'Hikaru-chan', polskim ekwiwalentem jest 'Hikaru', 'Córeczko' lub 'Hikaruś' (KARDYNALNY BŁĄD [X]: 'Hikarun, posłuchaj uważnie').
    - INHERENT GENDER & 1ST-PERSON MORPHOLOGY: Nazwy mówców ze stylami ASS (np. 'Girl\\Italic', 'Woman') to potwierdzone postacie żeńskie!
      * KATEGORYCZNY ZAKAZ stosowania męskich form czasowników 1. osoby czasu przeszłego ('zraniłem', 'zrobiłem', 'byłem') dla mówczyń żeńskich! Wymuszaj formy żeńskie: 'zraniłam', 'zrobiłam', 'byłam', 'powiedziałam'.
    - W mandatory_direction wymuś nadrzędność dramaturgii i japońskiego audio seiyū nad dosłownym skryptem angielskim.
 19. ODWRÓCENIE HIERARCHII ŹRÓDEŁ (INVERSION OF AUTHORITY / SEIYU VOICE SOVEREIGNTY), HARMONIZACJA AISATSU, APOZYCJA TYTULATURY PODMIOTU I AKTY MOWY SEIYŪ (FILAR CLXX):
    - INVERSION OF AUTHORITY (SEIYU VOICE SOVEREIGNTY): Głos seiyū jest PIERWOTNYM I NAJWYŻSZYM ŹRÓDŁEM PRAWDY (PIERWOTNE ŹRÓDŁO PRAWDY) semantycznej i emocjonalnej. Angielski skrypt fansubera jest jedynie wtórnym rusztowaniem czasowym! Kategoryczny zakaz powielania zamerykanizowanych parafraz fansubów, gdy stoją w sprzeczności ze słowami seiyū.
    - PRAGMATIC SPEECH ACT CATEGORIES (AKTY MOWY SEIYŪ):
      * Akty Irytacji i Uciszania (urusai, urusai na, urusee, ussee, damare, shizuka ni): wyrażają poirytowanie gadaniem lub natręctwem rozmówcy! KATEGORYCZNY ZAKAZ dryfu semantycznego ku zażenowaniu/wstydowi i młodzieżowemu slangowi ('Ale żenada...', 'przypał', 'obciach')! Wymuszaj naturalne polskie reakcje zniecierpliwienia: 'Ale marudzisz...', 'Daj mi spokój...', 'Nie truj...', 'Ale gadasz...', 'Ucisz się...'.
      * Akty Znużenia i Ciężaru (mendokusai, yare yare, shouganai): zakaz dosłownego bólu fizycznego ('co za ból') czy obojętności ('nie obchodzi mnie to') na rzecz 'Ale mi się nie chce...', 'Co za męczarnia...', 'Trudno...'.
      * Akty Dystansu i Emocjonalnego Odepchnięcia (betsuni, hitori ni shite): chłód i prośba o samotność ('Wcale nie', 'Zostaw mnie samą', zakaz 'To nic takiego').
    - DOMESTIC AISATSU ADJACENCY DIALOGUE: W formułach powitań domowych (Tadaima -> Okaeri) KATEGORYCZNY ZAKAZ robotycznego echa czasownikowego ('Wróciłam.' -> BŁĄD: 'Wróciłaś.'). Wymuszaj naturalne polskie powitanie domowników: 'Wróciłam!' -> 'Witaj w domu!' / 'O, już jesteś?' / 'Dobrze, że jesteś!'.
    - TITLE NOMINATIVE APPOSITION & JAPANESE NAME CAPITALIZATION: Przy zestawieniu tytułu mistrzowskiego/zawodowego z imieniem i nazwiskiem w podmiocie zdania ('Mistrz', 'Pan', 'Profesor' + Nazwisko + Imię + Czasownik 3. os.), nazwisko ZAWSZE pozostaje w mianowniku: 'Mistrz Tonden Minoru nie zdążył' (KARDYNALNY BŁĄD [X]: 'Mistrz Tondena minoru'). Każdy człon imienia i nazwiska bezwzględnie piszemy WIELKĄ LITERĄ ('Tonden Minoru', NIGDY małą 'minoru').
    - W mandatory_direction wymuś nadrzędność dramaturgii i japońskiego audio seiyū nad dosłownym skryptem angielskim.

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
                    "temperature": 0.2,
                }
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
                    print("  [!] [BŁĄD KONTA GOOGLE AI STUDIO / PŁATNOŚCI]:")
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
                tag = f"[🚨 PUŁAPKA PROFILERA: {dl.contextual_trap} => DYREKTYWA: {dl.mandatory_direction}]"
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

