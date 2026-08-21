"""
Moduł weryfikacji językowej, polskiej redakcji dialogów oraz eliminacji kalek językowych.
"""

import json
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from rules import get_verifier_system_prompt

class RefinedLine(BaseModel):
    id: int = Field(description="ID kwestii dialogowej zgodne z wejściem")
    original_en: str = Field(description="Oryginalny tekst angielski")
    refined_pl: str = Field(description="Ostateczna, perfekcyjnie zredagowana kwestia w języku polskim, wolna od kalek")
    changes_made: Optional[str] = Field(default=None, description="Krótkie uzasadnienie redakcyjne (np. 'Zmieniono kalkę Widzę na Rozumiem')")

class RefinedBatchResponse(BaseModel):
    lines: List[RefinedLine] = Field(description="Lista zredagowanych i zweryfikowanych kwestii dialogowych")

class DialogueVerifier:
    def __init__(self, client: genai.Client, model: str = "gemini-3.5-flash-lite", keep_honorifics: bool = True):
        self.client = client
        self.model = model
        self.keep_honorifics = keep_honorifics
        self.system_prompt = get_verifier_system_prompt(keep_honorifics=keep_honorifics)

    def verify_batch(
        self,
        batch_items: List[Dict[str, Any]],
        scene_summary: str = "",
        episode_profile_str: str = ""
    ) -> List[RefinedLine]:
        """
        Przeprowadza redakcję i weryfikację paczki dialogów.
        batch_items zawiera elementy:
        [{'id': int, 'en': str, 'pl': str, 'speaker_gender': str, 'notes': str}, ...]
        """
        if not batch_items:
            return []

        prompt_lines = []
        prompt_lines.append("Zredaguj poniższe kwestie dialogowe. BEZWZGLĘDNIE wyeliminuj dosłowne tłumaczenie 1 do 1, sztuczne konstrukcje i kalki.")
        prompt_lines.append("Zastąp drewniane sformułowania żywym, potoczystym językiem polskim mówionym (tak jak w profesjonalnym dubbingu / u polskich nastolatków):")
        if episode_profile_str:
            prompt_lines.append(f"\n{episode_profile_str}\n")
        if scene_summary:
            prompt_lines.append(f"\n[Kontekst sceny]: {scene_summary}\n")

        for item in batch_items:
            type_tag = f" [[Napis] {item['visual_type']}]" if item.get("is_sign") else " [DIALOG]"
            gender_info = f" (Mówca: {item.get('speaker_gender')})" if item.get('speaker_gender') else ""
            voice_info = f" [Głos: {item.get('speaker_voice')}]" if item.get('speaker_voice') else ""
            prosody_info = f" [Ton: {item.get('prosody')}]" if item.get('prosody') else ""
            cps_info = f" [CPS: {item.get('cps_warning')}]" if item.get('cps_warning') else ""
            notes_info = f" [Notatki: {item.get('notes')}]" if item.get('notes') else ""
            visual_info = f" [Położenie/Styl: {item.get('visual_details')}]" if item.get('visual_details') else ""
            
            prompt_lines.append(
                f"- [ID: {item['id']}]{type_tag}{gender_info}{voice_info}{prosody_info}{cps_info}{visual_info}\n"
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
                    system_instruction=self.system_prompt,
                    ttl_seconds=7200
                )
                gen_config_kwargs = {
                    "response_mime_type": "application/json",
                    "response_schema": RefinedBatchResponse,
                    "temperature": 0.35,
                }
                if cached_name:
                    gen_config_kwargs["cached_content"] = cached_name
                else:
                    gen_config_kwargs["system_instruction"] = self.system_prompt

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[prompt_text],
                    config=types.GenerateContentConfig(**gen_config_kwargs)
                )

                # Pobieramy sparsowany wynik
                if hasattr(response, "parsed") and response.parsed is not None:
                    parsed_obj: RefinedBatchResponse = response.parsed
                    return parsed_obj.lines
                
                # Fallback z response.text jeśli SDK zwróciło surowy json
                data = json.loads(response.text)
                batch_resp = RefinedBatchResponse.model_validate(data)
                return batch_resp.lines

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

                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str
                
                if is_unavailable or is_rate_limit:
                    wait_sec = min(5 + attempt * 3, 30)
                    print(f"\n[Redaktor Dialogów / Redakcja]: Chwilowe przeciążenie serwerów Google (503/429 na {self.model}).")
                    print(f"  [..] Utrzymuję najwyższą jakość PRO. Czekam {wait_sec}s na wolny slot serwera (próba #{attempt})...")
                    time.sleep(wait_sec)
                else:
                    wait_sec = min(4 + attempt * 2, 20)
                    print(f"\n[Redaktor Dialogów]: Ponawianie próby #{attempt} za {wait_sec}s ({e})...")
                    time.sleep(wait_sec)
