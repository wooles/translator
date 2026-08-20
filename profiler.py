# -*- coding: utf-8 -*-
"""
Moduł Profilowania Odcinka (Pre-pass Episode Profiler & Glossary Engine).
Przed rozpoczęciem tłumaczenia analizuje cały odcinek, mapuje relacje między postaciami
(kto do kogo mówi na 'ty', kto per 'pan/pani') oraz tworzy słowniczek specyficznych pojęć,
gwarantując idealną spójność dialogów w całym odcinku.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

logger = logging.getLogger("profiler")


class CharacterRelationship(BaseModel):
    speaker: str = Field(description="Imię postaci mówiącej")
    listener: str = Field(description="Imię postaci słuchającej / adresata")
    address_form: str = Field(description="Polska forma zwrotu (np. 'pani Teshima', 'panie profesorze', 'na ty / po imieniu: Minami')")
    relationship_type: str = Field(description="Typ relacji (np. 'uczeń -> nauczycielka', 'koleżanki z klasy', 'rodzeństwo')")


class GlossaryTerm(BaseModel):
    term_en: str = Field(description="Termin w języku angielskim lub japońskim")
    translation_pl: str = Field(description="Ustalony, spójny polski odpowiednik")
    explanation: str = Field(description="Wyjaśnienie kontekstu / znaczenia w anime")


class EpisodeProfile(BaseModel):
    episode_summary: str = Field(description="Krótkie 2-3 zdaniowe streszczenie fabuły i tonu odcinka")
    setting_and_era: str = Field(default="", description="Epoka historyczna, czas i miejsce akcji (np. 'XIII wiek, Imperium Mongolskie', 'Współczesne Tokio')")
    dialogue_stylization: str = Field(default="", description="Wytyczne stylizacji rejestru języka i zakazy/nakazy słownictwa dla tej epoki")
    tone_and_genre: str = Field(description="Rejestr i ton dialogów (np. 'szlachetny epos historyczny', 'lekkie młodzieżowe anime')")
    characters: List[CharacterRelationship] = Field(default_factory=list, description="Macierz relacji i form grzecznościowych między bohaterami")
    glossary: List[GlossaryTerm] = Field(default_factory=list, description="Słowniczek kluczowych pojęć, tytułów i nazw własnych odcinka")
    key_conventions: List[str] = Field(default_factory=list, description="Kluczowe wytyczne stylistyczne dla tego konkretnego odcinka")


def format_episode_profile_for_prompt(profile: Optional[EpisodeProfile]) -> str:
    """Formatuje profil odcinka do postaci zwięzłego bloku promptu systemowego."""
    if not profile:
        return ""

    lines = ["=== SŁOWNICZEK, REALIA HISTORYCZNE I MACIERZ RELACJI (PROFILER ODCINKA) ==="]
    if profile.setting_and_era:
        lines.append(f"🏛️ Epoka i realia świata: {profile.setting_and_era}")
    if profile.dialogue_stylization:
        lines.append(f"📜 Stylizacja językowa i rejestr: {profile.dialogue_stylization}")
    if profile.episode_summary:
        lines.append(f"Fabuła odcinka: {profile.episode_summary}")
    if profile.tone_and_genre:
        lines.append(f"Ton dialogów: {profile.tone_and_genre}")

    if profile.characters:
        lines.append("\nRELACJE SPOŁECZNE I FORMY ZWROTU (BEZWZGLĘDNIE PRZESTRZEGAJ):")
        for rel in profile.characters:
            lines.append(f"- {rel.speaker} -> {rel.listener}: {rel.address_form} ({rel.relationship_type})")

    if profile.glossary:
        lines.append("\nUSTALONY SŁOWNICZEK POJĘĆ I TYTUŁÓW:")
        for g in profile.glossary:
            lines.append(f"- '{g.term_en}' = '{g.translation_pl}' ({g.explanation})")

    if profile.key_conventions:
        lines.append("\nWYTYCZNE SPECYFICZNE DLA TEGO ODCINKA:")
        for conv in profile.key_conventions:
            lines.append(f"- {conv}")

    lines.append("==========================================================================\n")
    return "\n".join(lines)


class EpisodeProfiler:
    def __init__(self, client: genai.Client, model: str = "gemini-3.5-flash-lite"):
        self.client = client
        self.model = model

    def profile_episode(
        self,
        subs_text_sample: str,
        anime_metadata_str: str = "",
        cache_path: Optional[str] = None
    ) -> EpisodeProfile:
        """
        Generuje lub wczytuje z cache profil odcinka (Pre-pass).
        """
        if cache_path and os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info(f"Wczytano profil odcinka z cache: {cache_path}")
                    return EpisodeProfile.model_validate(data)
            except Exception as e:
                logger.warning(f"Błąd odczytu cache profilu ({e}), generowanie na nowo...")

        prompt = f"""Jesteś Głównym Reżyserem i Konsultantem Historycznym Lokalizacji Anime.
Twoim zadaniem jest wstępna analiza całego odcinka na podstawie poniższych dialogów i metadanych, aby stworzyć kompletny PROFIL ODCINKA, ustalić REALIA HISTORYCZNE ORAZ REJESTR STYLIZACJI DIALOGÓW.

METADANE Z BAZY ANILIST:
{anime_metadata_str}

PRÓBKA KWESTII DIALOGOWYCH Z ODCINKA:
{subs_text_sample[:12000]}

ZADANIE:
1. Zidentyfikuj EPOKĘ HISTORYCZNĄ ORAZ MIEJSCE AKCJI (np. "XIII wiek, Imperium Mongolskie / dwór chanów", "Okres Edo w feudalnej Japonii", "Współczesna szkoła w Tokio", "Średniowieczny świat fantasy").
2. Ustal WYTYCZNE STYLIZACJI JĘZYKOWEJ dla tej epoki (np. dla epoki dawnej: ZAKAZ współczesnego slangu, szlachetny język, etykieta dworska/historyczna).
3. Zidentyfikuj kluczowe postacie, ich role oraz ustal, jak powinny się do siebie zwracać po polsku (kto per 'pan/pani', kto 'Wasza Dostojność / Chanie', kto po imieniu).
4. Wyodrębnij specyficzne pojęcia epokowe, tytuły dzieł, nazwy potraw, broni lub miejsc i ustal dla nich bezbłędne, polskie tłumaczenie.
5. Określ ton i rejestr językowy dialogów.

Zwróć wynik w formacie JSON zgodnym ze schematem EpisodeProfile."""

        import time
        attempt = 0

        while True:
            attempt += 1
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=EpisodeProfile,
                        temperature=0.2
                    )
                )
                profile_data = json.loads(response.text)
                profile = EpisodeProfile.model_validate(profile_data)

                if cache_path:
                    try:
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass

                return profile
            except Exception as e:
                err_str = str(e).lower()
                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str
                
                if is_unavailable or is_rate_limit:
                    wait_sec = min(5 + attempt * 3, 30)
                    print(f"\n[Profiler Odcinka]: Chwilowe przeciążenie serwerów Google (503/429 na {self.model}).")
                    print(f"  ⏳ Utrzymuję najwyższą jakość profilu. Czekam {wait_sec}s na zwolnienie zasobów (próba #{attempt})...")
                    time.sleep(wait_sec)
                else:
                    wait_sec = min(4 + attempt * 2, 20)
                    print(f"\n[Profiler Odcinka]: Ponawianie próby #{attempt} za {wait_sec}s ({e})...")
                    time.sleep(wait_sec)
