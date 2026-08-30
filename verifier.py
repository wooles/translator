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
from client_factory import format_friendly_api_error

class RefinedLine(BaseModel):
    id: int = Field(description="ID kwestii dialogowej zgodne z wejściem")
    refined_pl: str = Field(description="Ostateczna, perfekcyjnie zredagowana kwestia w języku polskim, wolna od kalek")
    changes_made: Optional[str] = Field(default=None, description="Dokładne uzasadnienie i numer Filaru AVT dla poprawionej kwestii (np. '[Filar IV - Szyk Zdania] Usunięto kalkę'). Jeśli kwestia nie wymagała zmian, wpisz null.")

class RefinedBatchResponse(BaseModel):
    scene_diagnosis: Optional[SceneDiagnosis] = Field(default=None, description="Diagnoza i weryfikacja intencji dramaturgicznych sceny")
    lines: List[RefinedLine] = Field(description="Lista zredagowanych i zweryfikowanych kwestii dialogowych")

import os
import threading

class DialogueVerifier:
    _STATUS_LOCK = threading.Lock()
    _STATUS_ACTIVE: bool = False
    _LAST_STATUS_TIME: float = 0.0

    def __init__(
        self,
        client: genai.Client,
        model: str = "gemini-3.5-flash-lite",
        keep_honorifics: bool = True,
        thinking_budget: Optional[int] = None
    ):
        self.client = client
        if hasattr(client, "get_client") and hasattr(client, "clients"):
            self.client_pool = client
        else:
            from client_factory import MultiKeyClientPool
            timeout_sec = float(os.getenv("GEMINI_HTTP_TIMEOUT_SEC", "90.0"))
            self.client_pool = MultiKeyClientPool(raw_keys=os.getenv("GEMINI_API_KEY"), timeout_sec=timeout_sec)
        self.model = model
        self.keep_honorifics = keep_honorifics
        self.system_prompt = get_verifier_system_prompt(keep_honorifics=keep_honorifics)
        self.current_episode_tokens: Dict[str, Any] = {"prompt": 0, "cached": 0, "output": 0, "model": self.model}
        import threading
        self.lock = threading.Lock()
        
        if thinking_budget is not None:
            self.thinking_budget = thinking_budget
        else:
            try:
                self.thinking_budget = int(os.getenv("PHASE2_THINKING_BUDGET", "6144"))
            except (ValueError, TypeError):
                self.thinking_budget = 6144

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
        prompt_lines.append("W polu 'changes_made' dla KAŻDEJ poprawionej kwestii podaj DOKŁADNE uzasadnienie i numer Filaru AVT (np. '[Filar IV - Szyk Zdania] Usunięto kalkę angielską'). Jeśli kwestia nie wymagała poprawek, wpisz null.")
        
        if focused_rules_str:
            prompt_lines.append(f"\n{focused_rules_str}\n")
        if scene_summary:
            prompt_lines.append(f"\n[Kontekst sceny]: {scene_summary}\n")

        # Static Episode Knowledge (Only appended if not already baked into Cached System Instructions)
        if not getattr(self, "_episode_knowledge_cached", False):
            if user_feedback_str:
                prompt_lines.append(f"\n{user_feedback_str}\n")
            if glossary_str:
                prompt_lines.append(f"\n{glossary_str}\n")
            if episode_profile_str:
                prompt_lines.append(f"\n{episode_profile_str}\n")

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
            vis_sub_info = f"  [🎬 Wizja, Mimika & Usta]: {item['visual_subtext']}\n" if item.get('visual_subtext') else ""
            prag_reg_info = f"  [🎎 Rejestr Pragmatyczny JP]: {item['pragmatic_register']}\n" if item.get('pragmatic_register') else ""
            lit_info = f"  [📖 Dosłowny Sens JP]: {item['literal_meaning']}\n" if item.get('literal_meaning') else ""
            cond_info = f"  {item['condensation_directive']}\n" if item.get('condensation_directive') else ""
            
            prompt_lines.append(
                f"- [ID: {item['id']}]{type_tag}{gender_info}{voice_info}{prosody_info}{song_info}{cps_info}{visual_info}\n"
                f"{audio_info}"
                f"{alert_info}"
                f"{prag_reg_info}"
                f"{vis_sub_info}"
                f"{lit_info}"
                f"{cond_info}"
                f"  EN: {item['en']}\n"
                f"  Wstępne PL: {item['pl']}{notes_info}"
            )

        prompt_text = "\n".join(prompt_lines)

        import time
        attempt = 0

        # Determine adaptive CoT thinking budget based on batch complexity (Elastic Multi-Tier Budget)
        has_song = any(item.get("is_song") for item in batch_items)
        has_audio_alert = any(item.get("audio_alert") for item in batch_items)
        has_pragmatic_reg = any(item.get("pragmatic_register") for item in batch_items)
        has_condensation = any(item.get("condensation_directive") for item in batch_items)
        has_long_dialogue = any(len(item.get("en", "").split()) > 10 for item in batch_items)

        # Separate adaptive CoT tiers for Pro Model ($12/1M output rate) vs Flash Model ($3.75/1M output rate)
        if "pro" in self.model.lower():
            # PRO MODEL DEDICATED TIERS (Level 4: High Literary Depth without token bloating)
            # Tier 1 (Pro): Piosenki OP/ED, gry słowne, zawiłe metafory, alarmy Whisper
            if has_song or has_audio_alert:
                effective_budget = 2048
            # Tier 2 (Pro): Rejestry militarne, stylizacja feudalna, kompresja, narady
            elif has_pragmatic_reg or has_condensation or has_long_dialogue:
                effective_budget = 1024
            # Tier 3 (Pro): Proste, krótkie dialogi i okrzyki bojowe
            else:
                effective_budget = 512
        else:
            # FLASH MODEL TIERS (Level 3: Full Deep CoT up to 6144 unchanged)
            # Tier 1: Piosenki OP/ED (Barańczak), kalambury fonetyczne i alarmy rozbieżności audio
            if has_song or has_audio_alert:
                effective_budget = max(4096, min(self.thinking_budget, 6144))
            # Tier 2: Rejestry feudalne/dworskie, kompresja czasowa i długie narady militarne
            elif has_pragmatic_reg or has_condensation or has_long_dialogue:
                effective_budget = max(2048, min(self.thinking_budget, 3072))
            # Tier 3: Standardowy, żywy dialog codzienny
            else:
                effective_budget = min(self.thinking_budget, 1280)

        while True:
            attempt += 1
            cached_name = None
            try:
                from context_cache import ContextCacheManager
                gen_config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": RefinedBatchResponse,
                }
                if "3.7" in self.model.lower() or "pro" in self.model.lower() or "2.5-pro" in self.model.lower():
                    gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=effective_budget)

                import concurrent.futures

                last_used_client = None
                def _single_generate():
                    nonlocal cached_name, last_used_client
                    from client_factory import global_rate_limiter
                    global_rate_limiter.acquire()
                    active_c = self.client_pool.get_client() if hasattr(self, "client_pool") and self.client_pool else self.client
                    last_used_client = active_c
                    cached_name = ContextCacheManager.get_or_create_cache(
                        client=active_c,
                        model=self.model,
                        system_instruction=self.system_prompt
                    )
                    cfg_kwargs = dict(gen_config_kwargs)
                    if cached_name:
                        cfg_kwargs["cached_content"] = cached_name
                    else:
                        cfg_kwargs["system_instruction"] = self.system_prompt
                    cfg = types.GenerateContentConfig(**cfg_kwargs)
                    return active_c.models.generate_content(
                        model=self.model,
                        contents=[prompt_text],
                        config=cfg
                    )

                # Direct generation using thread-safe multi-key rotation and token bucket pacing with hard 95s watchdog
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_single_generate)
                    response = fut.result(timeout=95.0)

                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    um = response.usage_metadata
                    with self.lock:
                        self.current_episode_tokens["prompt"] += getattr(um, "prompt_token_count", 0) or 0
                        self.current_episode_tokens["cached"] += getattr(um, "cached_content_token_count", 0) or 0
                        cands = getattr(um, "candidates_token_count", 0) or 0
                        thoughts = getattr(um, "thoughts_token_count", 0) or 0
                        self.current_episode_tokens["output"] += (cands + thoughts)
                        self.current_episode_tokens["model"] = self.model

                # Retrieve parsed structured output
                if hasattr(response, "parsed") and response.parsed is not None:
                    parsed_obj: RefinedBatchResponse = response.parsed
                    with DialogueVerifier._STATUS_LOCK:
                        if DialogueVerifier._STATUS_ACTIVE:
                            print(f"  └─ [OK / Faza 2]: Połączenie z Google API przywrócone.")
                            DialogueVerifier._STATUS_ACTIVE = False
                            DialogueVerifier._LAST_STATUS_TIME = 0.0
                    return parsed_obj.lines
                
                # Fallback to response.text if SDK returned raw string
                data = json.loads(response.text)
                batch_resp = RefinedBatchResponse.model_validate(data)
                with DialogueVerifier._STATUS_LOCK:
                    if DialogueVerifier._STATUS_ACTIVE:
                        print(f"  └─ [OK / Faza 2]: Połączenie z Google API przywrócone.")
                        DialogueVerifier._STATUS_ACTIVE = False
                        DialogueVerifier._LAST_STATUS_TIME = 0.0
                return batch_resp.lines

            except Exception as e:
                err_str = str(e).lower()
                if hasattr(self, "client_pool") and self.client_pool and last_used_client:
                    self.client_pool.report_error(last_used_client, err_str)

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

                import random
                import time as _time
                num_keys = len(self.client_pool.clients) if hasattr(self, "client_pool") and self.client_pool else 1
                if is_unavailable or is_timeout:
                    cycle = attempt // max(1, num_keys)
                    wait_sec = min(4.0, 1.5 + 0.5 * min(cycle, 5) + random.uniform(0.1, 0.4))
                else:
                    if attempt % max(1, num_keys) != 0:
                        wait_sec = 0.2 + random.uniform(0.05, 0.15)
                    else:
                        cycle = attempt // max(1, num_keys)
                        wait_sec = min(3.0, 0.6 + 0.4 * min(cycle, 4) + random.uniform(0.1, 0.3))
                
                friendly_msg = format_friendly_api_error(e)
                with DialogueVerifier._STATUS_LOCK:
                    if not DialogueVerifier._STATUS_ACTIVE:
                        print(f"\n[Status / Faza 2]: {friendly_msg} -> oczekiwanie na serwery Google i automatyczna rotacja kluczy...")
                        DialogueVerifier._STATUS_ACTIVE = True

                time.sleep(wait_sec)
