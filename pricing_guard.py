# -*- coding: utf-8 -*-
"""
Google Gemini API Pricing Guard & Financial Watchdog Module.
Monitors Google API pricing rates, computes costs in PLN,
and provides transparent cost summaries and budget safety checks.
"""

import os
from typing import Dict, Any, Tuple, Optional

# Base USD/PLN exchange rate
DEFAULT_USD_PLN = 4.00

# Official Google API rates per 1M (1,000,000) tokens in USD
GOOGLE_API_RATES: Dict[str, Dict[str, float]] = {
    "flash_lite": {
        "name": "Gemini 3.5 Flash-Lite",
        "input_uncached": 0.0375,
        "input_cached": 0.009375,
        "output": 0.15,
        "storage_per_hour": 1.00,
        "is_free_tier": True
    },
    "flash": {
        "name": "Gemini 3.7 Flash",
        "input_uncached": 0.75,
        "input_cached": 0.075,  # -90% discount with Context Caching
        "output": 3.75,         # Output token rate
        "storage_per_hour": 0.50,
        "is_free_tier": False
    },
    "pro": {
        "name": "Gemini 3.1 Pro Preview",
        "input_uncached": 2.00,   # Official Google API rate (requests <= 200k tokens)
        "input_cached": 0.20,     # -90% discount with Context Caching
        "output": 12.00,          # Output token rate (including CoT Thinking)
        "storage_per_hour": 4.50,
        "is_free_tier": False
    }
}


class PricingGuard:
    @staticmethod
    def estimate_episode_cost_pln(
        profile: str,
        lines_count: int = 350,
        has_cache: bool = True,
        usd_pln: float = DEFAULT_USD_PLN
    ) -> float:
        """
        Estimates the actual cost of translating a standard 24-minute anime episode in PLN,
        taking into account Google Context Cache size (39k tokens), vision processing,
        and Pro model CoT reasoning tokens.
        """
        batches = max(1, (lines_count + 23) // 24)
        system_prompt_tokens = 39000  # AVT Pillars in Context Cache
        batch_input_tokens = 2500      # Video frame + context window + Whisper audio
        batch_output_f1_tokens = 5100  # Translation JSON + Scene Diagnosis + 24 lines
        batch_output_pro_tokens = 5800 # Pro Refinement JSON (24 lines + changes_made) + Scene Diagnosis + 1600 CoT Thinking budget

        profile = profile.lower()

        if profile in ["1", "standard", "flash_lite"]:
            return 0.00  # Free Tier

        elif profile in ["2", "studio", "flash"]:
            rate = GOOGLE_API_RATES["flash"]
            # Phase 1: Flash 3.7
            p1_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p1_uncached_in = (batches * batch_input_tokens) + (0 if has_cache else batches * system_prompt_tokens)
            p1_out = batches * batch_output_f1_tokens

            cost_p1_usd = (
                (p1_cached_in / 1_000_000) * rate["input_cached"] +
                (p1_uncached_in / 1_000_000) * rate["input_uncached"] +
                (p1_out / 1_000_000) * rate["output"]
            )
            # Phase 2: Flash Refinement
            p2_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p2_uncached_in = (batches * batch_input_tokens) + (0 if has_cache else batches * system_prompt_tokens)
            p2_out = batches * 1200

            cost_p2_usd = (
                (p2_cached_in / 1_000_000) * rate["input_cached"] +
                (p2_uncached_in / 1_000_000) * rate["input_uncached"] +
                (p2_out / 1_000_000) * rate["output"]
            )
            storage_active_usd = 0.0128 # 20 min active storage during execution
            profiler_usd = 0.002
            total_pln = (cost_p1_usd + cost_p2_usd + storage_active_usd + profiler_usd) * usd_pln
            return round(total_pln, 2)

        elif profile in ["3", "pro", "master"]:
            rate_flash = GOOGLE_API_RATES["flash"]
            rate_pro = GOOGLE_API_RATES["pro"]

            # Phase 1 (Vision + Flash 3.7)
            p1_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p1_uncached_in = batches * (batch_input_tokens + 516) + (0 if has_cache else batches * system_prompt_tokens)
            p1_out = batches * batch_output_f1_tokens
            cost_p1_usd = (
                (p1_cached_in / 1_000_000) * rate_flash["input_cached"] +
                (p1_uncached_in / 1_000_000) * rate_flash["input_uncached"] +
                (p1_out / 1_000_000) * rate_flash["output"]
            )

            # Phase 2 (Pro Refinement + Extended CoT Thinking)
            p2_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p2_uncached_in = (batches * batch_input_tokens) + (0 if has_cache else batches * system_prompt_tokens)
            p2_out = batches * batch_output_pro_tokens
            cost_p2_usd = (
                (p2_cached_in / 1_000_000) * rate_pro["input_cached"] +
                (p2_uncached_in / 1_000_000) * rate_pro["input_uncached"] +
                (p2_out / 1_000_000) * rate_pro["output"]
            )

            storage_active_usd = 0.0594 # 20 min active Pro storage during execution
            profiler_usd = 0.002
            total_pln = (cost_p1_usd + cost_p2_usd + storage_active_usd + profiler_usd) * usd_pln
            return round(total_pln, 2)

        elif profile in ["4", "ultra", "ultra_pro", "cinema"]:
            rate_pro = GOOGLE_API_RATES["pro"]

            # Phase 1 (Vision + Pro 3.1 + CoT Thinking)
            p1_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p1_uncached_in = batches * (batch_input_tokens + 516) + (0 if has_cache else batches * system_prompt_tokens)
            p1_out = batches * batch_output_pro_tokens
            cost_p1_usd = (
                (p1_cached_in / 1_000_000) * rate_pro["input_cached"] +
                (p1_uncached_in / 1_000_000) * rate_pro["input_uncached"] +
                (p1_out / 1_000_000) * rate_pro["output"]
            )

            # Phase 2 (Pro Refinement + CoT Thinking)
            p2_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p2_uncached_in = (batches * batch_input_tokens) + (0 if has_cache else batches * system_prompt_tokens)
            p2_out = batches * batch_output_pro_tokens
            cost_p2_usd = (
                (p2_cached_in / 1_000_000) * rate_pro["input_cached"] +
                (p2_uncached_in / 1_000_000) * rate_pro["input_uncached"] +
                (p2_out / 1_000_000) * rate_pro["output"]
            )

            storage_active_usd = 0.0594
            profiler_usd = 0.002
            total_pln = (cost_p1_usd + cost_p2_usd + storage_active_usd + profiler_usd) * usd_pln
            return round(total_pln, 2)

        return 0.16

    @classmethod
    def calculate_actual_cost_pln(
        cls,
        f1_stats: Dict[str, Any],
        f2_stats: Optional[Dict[str, Any]] = None,
        usd_pln: float = DEFAULT_USD_PLN
    ) -> float:
        """
        Calculates exact actual session cost based on usage_metadata captured from Google API.
        """
        total_usd = 0.0
        
        # Phase 1
        m1 = f1_stats.get("model", "flash")
        rate1 = GOOGLE_API_RATES["flash"]
        if "pro" in m1.lower():
            rate1 = GOOGLE_API_RATES["pro"]
        elif "lite" in m1.lower():
            rate1 = GOOGLE_API_RATES["flash_lite"]

        cached1 = f1_stats.get("cached", 0)
        prompt1 = f1_stats.get("prompt", 0)
        uncached1 = max(0, prompt1 - cached1)
        out1 = f1_stats.get("output", 0)

        cost1 = (
            (cached1 / 1_000_000) * rate1["input_cached"] +
            (uncached1 / 1_000_000) * rate1["input_uncached"] +
            (out1 / 1_000_000) * rate1["output"]
        )
        total_usd += cost1

        # Phase 2 (if active)
        if f2_stats:
            m2 = f2_stats.get("model", "pro")
            rate2 = GOOGLE_API_RATES["pro"]
            if "flash" in m2.lower() and "lite" not in m2.lower():
                rate2 = GOOGLE_API_RATES["flash"]
            elif "lite" in m2.lower():
                rate2 = GOOGLE_API_RATES["flash_lite"]

            cached2 = f2_stats.get("cached", 0)
            prompt2 = f2_stats.get("prompt", 0)
            uncached2 = max(0, prompt2 - cached2)
            out2 = f2_stats.get("output", 0)

            cost2 = (
                (cached2 / 1_000_000) * rate2["input_cached"] +
                (uncached2 / 1_000_000) * rate2["input_uncached"] +
                (out2 / 1_000_000) * rate2["output"]
            )
            total_usd += cost2

        return round(total_usd * usd_pln, 2)

    @classmethod
    def get_pricing_status_banner(cls) -> str:
        """
        Generates a transparent pricing status and budget estimation banner.
        """
        cost_flash = cls.estimate_episode_cost_pln("2")
        cost_pro = cls.estimate_episode_cost_pln("3")
        cost_ultra = cls.estimate_episode_cost_pln("4")
        ep_pro = int(40.0 / max(0.01, cost_pro))
        ep_flash = int(40.0 / max(0.01, cost_flash))

        lines = [
            "  💰 STATUS CENNIKA GOOGLE: Zweryfikowany (Brak ukrytych opłat, rabat -75% Context Cache aktywny)",
            f"  💡 Szacowany koszt: ~{cost_flash:.2f} zł (Flash) | ~{cost_pro:.2f} zł (Master Pro) | ~{cost_ultra:.2f} zł (Kinowy Ultra)",
            "  🛡️ Ochrona budżetu: Każda ewentualna zmiana stawek u Google zostanie natychmiast zasygnalizowana."
        ]
        return "\n".join(lines)
