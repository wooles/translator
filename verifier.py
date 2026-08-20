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
            type_tag = f" [🖼️ {item['visual_type']}]" if item.get("is_sign") else " [💬 DIALOG MÓWIONY]"
            gender_info = f" (Mówca: {item.get('speaker_gender')})" if item.get('speaker_gender') else ""
            notes_info = f" [Notatki: {item.get('notes')}]" if item.get('notes') else ""
            visual_info = f" [Położenie/Styl: {item.get('visual_details')}]" if item.get('visual_details') else ""
            
            prompt_lines.append(
                f"- [ID: {item['id']}]{type_tag}{gender_info}{visual_info}\n"
                f"  EN: {item['en']}\n"
                f"  Wstępne PL: {item['pl']}{notes_info}"
            )

        prompt_text = "\n".join(prompt_lines)

        import time
        max_attempts = 10

        for attempt in range(max_attempts):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[prompt_text],
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_prompt,
                        response_mime_type="application/json",
                        response_schema=RefinedBatchResponse,
                        temperature=0.35,
                    )
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
                is_unavailable = "503" in err_str or "unavailable" in err_str or "high demand" in err_str
                is_rate_limit = "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str
                
                if is_unavailable or is_rate_limit:
                    wait_sec = (attempt + 1) * 4
                    print(f"\n[Script Doctor / Redakcja]: Chwilowe przeciążenie serwerów Google (503/429 na {self.model}).")
                    print(f"  ⏳ Utrzymuję najwyższą jakość PRO bez przełączania na niższe modele.")
                    print(f"  Odczekuję {wait_sec}s przed ponowną próbą ({attempt + 1}/{max_attempts})...")
                    time.sleep(wait_sec)
                else:
                    if attempt < max_attempts - 1:
                        wait_sec = (attempt + 1) * 3
                        print(f"\n[Script Doctor]: Ponawianie próby za {wait_sec}s po napotkaniu błędu ({e})...")
                        time.sleep(wait_sec)
                    else:
                        print(f"\n[Script Doctor]: Nie udało się zredagować paczki dialogów po {max_attempts} próbach ({e}).")

        print("[Script Doctor]: Zachowano wstępne tłumaczenie paczki po wyczerpaniu limitu prób.")
        return [
            RefinedLine(
                id=item["id"],
                original_en=item["en"],
                refined_pl=item["pl"],
                changes_made="Brak weryfikacji (błąd zapytania)"
            )
            for item in batch_items
        ]
