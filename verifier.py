# -*- coding: utf-8 -*-
"""
Linguistic Verification & Polish Dialogue Polish/Refinement Module (Phase 2).
Eliminates translationese, mechanical calques, and refines dialogues for natural spoken Polish flow.
"""

import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from rules import get_verifier_system_prompt, SceneDiagnosis

class RefinedLine(BaseModel):
    id: int = Field(description="ID kwestii dialogowej zgodne z wejściem")
    original_en: str = Field(description="Oryginalny tekst angielski")
    refined_pl: str = Field(description="Ostateczna, perfekcyjnie zredagowana kwestia w języku polskim, wolna od kalek")
    changes_made: Optional[str] = Field(default=None, description="Krótkie uzasadnienie redakcyjne (np. 'Zmieniono kalkę Widzę na Rozumiem')")

class RefinedBatchResponse(BaseModel):
    scene_diagnosis: Optional[SceneDiagnosis] = Field(default=None, description="Diagnoza i weryfikacja intencji dramaturgicznych sceny")
    lines: List[RefinedLine] = Field(description="Lista zredagowanych i zweryfikowanych kwestii dialogowych")

import os

class DialogueVerifier:
    def __init__(
        self,
        client: genai.Client,
        model: str = "gemini-3.5-flash-lite",
        keep_honorifics: bool = True,
        thinking_budget: Optional[int] = None
    ):
        self.client = client
        self.model = model
        self.keep_honorifics = keep_honorifics
        self.system_prompt = get_verifier_system_prompt(keep_honorifics=keep_honorifics)
        self.current_episode_tokens: Dict[str, Any] = {"prompt": 0, "cached": 0, "output": 0, "model": self.model}
        
        if thinking_budget is not None:
            self.thinking_budget = thinking_budget
        else:
            try:
                self.thinking_budget = int(os.getenv("PHASE2_THINKING_BUDGET", "1600"))
            except (ValueError, TypeError):
                self.thinking_budget = 1600

    def verify_batch(
        self,
        batch_items: List[Dict[str, Any]],
        scene_summary: str = "",
        episode_profile_str: str = "",
        user_feedback_str: str = "",
        glossary_str: str = "",
        focused_rules_str: str = ""
    ) -> List[RefinedLine]:
        """
        Executes editorial refinement and verification for a dialogue batch.
        batch_items contains elements:
        [{'id': int, 'en': str, 'pl': str, 'speaker_gender': str, 'notes': str}, ...]
        """
        if not batch_items:
            return []

        prompt_lines = []
        prompt_lines.append("Zredaguj poniższe kwestie dialogowe. BEZWZGLĘDNIE wyeliminuj dosłowne tłumaczenie 1 do 1, sztuczne konstrukcje i kalki.")
        prompt_lines.append("Zastąp drewniane sformułowania żywym, potoczystym językiem polskim mówionym (tak jak w profesjonalnym dubbingu / u polskich nastolatków):")
        
        if user_feedback_str:
            prompt_lines.append(f"\n{user_feedback_str}\n")
        if glossary_str:
            prompt_lines.append(f"\n{glossary_str}\n")
        if focused_rules_str:
            prompt_lines.append(f"\n{focused_rules_str}\n")
        if episode_profile_str:
            prompt_lines.append(f"\n{episode_profile_str}\n")
        if scene_summary:
            prompt_lines.append(f"\n[Kontekst sceny]: {scene_summary}\n")

        for item in batch_items:
            type_tag = f" [[Napis] {item['visual_type']}]" if item.get("is_sign") else " [DIALOG]"
            gender_info = f" (Mówca: {item.get('speaker_gender')})" if item.get('speaker_gender') else ""
            voice_info = f" [Głos: {item.get('speaker_voice')}]" if item.get('speaker_voice') else ""
            prosody_info = f" [Ton: {item.get('prosody')}]" if item.get('prosody') else ""
            song_info = " [🎵 PIOSENKA / WYMÓG RYMU I METRUM SYLABICZNEGO (FILAR CXVIII)]" if item.get("is_song") else ""
            cps_info = f" [CPS: {item.get('cps_warning')}]" if item.get('cps_warning') else ""
            notes_info = f" [Notatki: {item.get('notes')}]" if item.get('notes') else ""
            visual_info = f" [Położenie/Styl: {item.get('visual_details')}]" if item.get('visual_details') else ""
            audio_info = f"  JP (Audio ze słuchu Whisper): {item['audio_jp']}\n" if item.get("audio_jp") else ""
            alert_info = f"  [⚠️ ALARM ROZBIEŻNOŚCI AUDIO JP]: {item['audio_alert']}\n" if item.get("audio_alert") else ""
            
            prompt_lines.append(
                f"- [ID: {item['id']}]{type_tag}{gender_info}{voice_info}{prosody_info}{song_info}{cps_info}{visual_info}\n"
                f"{audio_info}"
                f"{alert_info}"
                f"  EN: {item['en']}\n"
                f"  Wstępne PL: {item['pl']}{notes_info}"
            )

        prompt_text = "\n".join(prompt_lines)

        import time
        attempt = 0

        while True:
            attempt += 1
            try:
                from context_cache import ContextCacheManager
                cached_name = ContextCacheManager.get_or_create_cache(
                    client=self.client,
                    model=self.model,
                    system_instruction=self.system_prompt
                )
                gen_config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": RefinedBatchResponse,
                }
                if "3.7" in self.model.lower() or "pro" in self.model.lower() or "2.5" in self.model.lower() or "3.6" in self.model.lower():
                    gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=self.thinking_budget)

                if cached_name:
                    gen_config_kwargs["cached_content"] = cached_name
                else:
                    gen_config_kwargs["system_instruction"] = self.system_prompt

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[prompt_text],
                    config=types.GenerateContentConfig(**gen_config_kwargs)
                )

                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    um = response.usage_metadata
                    self.current_episode_tokens["prompt"] += getattr(um, "prompt_token_count", 0) or 0
                    self.current_episode_tokens["cached"] += getattr(um, "cached_content_token_count", 0) or 0
                    cands = getattr(um, "candidates_token_count", 0) or 0
                    thoughts = getattr(um, "thoughts_token_count", 0) or 0
                    self.current_episode_tokens["output"] += (cands + thoughts)
                    self.current_episode_tokens["model"] = self.model

                # Retrieve parsed structured output
                if hasattr(response, "parsed") and response.parsed is not None:
                    parsed_obj: RefinedBatchResponse = response.parsed
                    return parsed_obj.lines
                
                # Fallback to response.text if SDK returned raw string
                data = json.loads(response.text)
                batch_resp = RefinedBatchResponse.model_validate(data)
                return batch_resp.lines

            except Exception as e:
                err_str = str(e).lower()
                is_cache_err = "403" in err_str or "cachedcontent" in err_str or "permission" in err_str
                if is_cache_err and cached_name:
                    from context_cache import ContextCacheManager
                    ContextCacheManager.invalidate_cache(self.model, self.system_prompt)
                    cached_name = None
                    continue

                is_billing_exhausted = "prepayment" in err_str or "depleted" in err_str or ("billing" in err_str and "credit" in err_str)
                if is_billing_exhausted:
                    print("\n" + "!" * 75)
                    print("  [!] [BŁĄD KONTA GOOGLE AI STUDIO / PŁATNOŚCI]:")
                    print("  Wyczerpały się środki przedpłacone (Prepayment Credits / Limit wydatków)!")
                    print("  Komunikat Google: 'Your prepayment credits are depleted.'")
                    print("  -> Wejdź na https://aistudio.google.com/ i doładuj środki, aby kontynuować.")
                    print("!" * 75 + "\n")
                    raise RuntimeError("Wyczerpane środki na koncie Google AI Studio (Prepayment Credits Depleted).")

                is_timeout = "504" in err_str or "deadline" in err_str or "timeout" in err_str or "timed out" in err_str
                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str

                wait_sec = 0.5
                if is_timeout:
                    if attempt == 1:
                        timeout_sec = int(os.getenv("GEMINI_HTTP_TIMEOUT_MS", "120000")) // 1000
                        print(f"\n[Redaktor Dialogów / Faza 2]: Serwer Google potrzebował więcej czasu na analizę sceny (limit {timeout_sec}s na {self.model}).")
                        print("  [..] Ponawiam próbę co 0,5 s do uzyskania dostępu do TPU...")
                    time.sleep(wait_sec)
                elif is_unavailable or is_rate_limit:
                    if attempt == 1:
                        print(f"\n[Redaktor Dialogów / Faza 2]: Chwilowe przeciążenie serwerów Google (503/429 na {self.model}).")
                        print("  [..] Ponawiam próbę co 0,5 s do uzyskania dostępu do TPU...")
                    time.sleep(wait_sec)
                else:
                    if attempt == 1:
                        clean_msg = str(e).split("{")[0].strip() if "{" in str(e) else str(e)
                        print(f"\n[Redaktor Dialogów / Faza 2]: Chwilowa przerwa w odpowiedzi API na {self.model} ({clean_msg}).")
                        print("  [..] Ponawiam próbę co 0,5 s do uzyskania dostępu do TPU...")
                    time.sleep(wait_sec)
