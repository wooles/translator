# -*- coding: utf-8 -*-
"""
Google Gemini API Pricing Guard & Financial Watchdog Module.
Monitors Google API pricing rates, computes costs in PLN,
and provides transparent cost summaries and budget safety checks.
"""

import os
from typing import Dict, Any, Tuple, Optional

# Base USD/PLN exchange rate (supports .env override)
DEFAULT_USD_PLN = float(os.getenv("USD_PLN_RATE", os.getenv("USD_PLN", "4.00")))

# Official Google API rates per 1M (1,000,000) tokens in USD (supports .env override)
GOOGLE_API_RATES: Dict[str, Dict[str, float]] = {
    "hydrogen": {
        "name": "Gemini 4 Hydrogen",
        "input_uncached": float(os.getenv("RATE_HYDROGEN_IN", "1.50")),
        "input_cached": float(os.getenv("RATE_HYDROGEN_CACHE", "0.075")),  # -95% discount with Implicit Context Caching
        "output": float(os.getenv("RATE_HYDROGEN_OUT", "7.50")),           # Output token rate including thinking_level traces
        "storage_per_hour": 0.00,                                          # Implicit caching has 0.00 USD storage fee
        "cache_discount_pct": 95,
        "is_free_tier": False
    },
    "flash_lite": {
        "name": "Gemini 3.5 Flash-Lite",
        "input_uncached": float(os.getenv("RATE_FLASH_LITE_IN", "0.0375")),
        "input_cached": float(os.getenv("RATE_FLASH_LITE_CACHE", "0.009375")),
        "output": float(os.getenv("RATE_FLASH_LITE_OUT", "0.15")),
        "storage_per_hour": 1.00,
        "is_free_tier": True
    },
    "flash": {
        "name": "Gemini 3.7 Flash",
        "input_uncached": float(os.getenv("RATE_FLASH_IN", "0.75")),
        "input_cached": float(os.getenv("RATE_FLASH_CACHE", "0.075")),  # -90% discount with Context Caching
        "output": float(os.getenv("RATE_FLASH_OUT", "3.75")),         # Output token rate including CoT Thinking traces
        "storage_per_hour": 0.50,
        "is_free_tier": False
    },
    "pro": {
        "name": "Gemini 3.1 Pro Preview",
        "input_uncached": float(os.getenv("RATE_PRO_IN", "2.00")),   # Official Google API rate (requests <= 200k tokens)
        "input_cached": float(os.getenv("RATE_PRO_CACHE", "0.20")),     # -90% discount with Context Caching
        "output": float(os.getenv("RATE_PRO_OUT", "12.00")),          # Output token rate (including CoT Thinking)
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
        Estimates the actual cost of translating a 24-minute anime episode in PLN,
        taking into account realistic adaptive batching (18 lines/batch), Google Context Cache (39k tokens),
        vision frames, ironclad OP/ED preservation (0 tokens), and dedicated Pro Adaptive CoT (2048/1024/512).
        """
        # Realistic empirical batching (avg 18 lines per scene-aligned batch)
        batches = max(1, (lines_count + 17) // 18)
        system_prompt_tokens = 33000  # AVT Pillars in Context Cache
        batch_input_tokens = 9500      # Video frames (scaled) + lookahead + Whisper audio + history
        batch_output_f1_tokens = 3800  # Full Masterclass Phase 1 JSON Translation (empirical ~76k tokens / 20 batches)
        batch_output_flash_cot = 3150  # Phase 2 Flash Script Doctor Refinement + Elastic CoT thinking (2048/3072/6144)
        batch_output_pro_tokens = 2350 # Phase 2 Pro Refinement + Dedicated Pro CoT (1024/1536/2048)

        profile = profile.lower()

        if profile in ["1", "standard", "flash_lite"]:
            return 0.00  # Free Tier

        elif profile in ["2", "studio", "flash"]:
            rate = GOOGLE_API_RATES["flash"]
            # Phase 1: Flash (Single phase, no Phase 2 verifier)
            p1_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p1_uncached_in = (batches * batch_input_tokens) + (0 if has_cache else batches * system_prompt_tokens)
            p1_out = batches * batch_output_f1_tokens

            cost_p1_usd = (
                (p1_cached_in / 1_000_000) * rate["input_cached"] +
                (p1_uncached_in / 1_000_000) * rate["input_uncached"] +
                (p1_out / 1_000_000) * rate["output"]
            )
            storage_active_usd = 0.0064
            profiler_usd = 0.002
            total_pln = (cost_p1_usd + storage_active_usd + profiler_usd) * usd_pln
            return round(total_pln, 2)

        elif profile in ["3", "master", "flash_reasoning", "hydrogen", "hydrogen_master", "pro_level3"]:
            rate_h = GOOGLE_API_RATES["hydrogen"]
            batches_h = max(1, (lines_count + 23) // 24)
            lean_output_f1_tokens = 2150
            lean_output_f2_tokens = 1500

            # Phase 1: Vision + Hydrogen
            p1_cached_in = (batches_h * system_prompt_tokens) if has_cache else 0
            p1_uncached_in = batches_h * (batch_input_tokens + 256) + (0 if has_cache else batches_h * system_prompt_tokens)
            p1_out = batches_h * lean_output_f1_tokens
            cost_p1_usd = (
                (p1_cached_in / 1_000_000) * rate_h["input_cached"] +
                (p1_uncached_in / 1_000_000) * rate_h["input_uncached"] +
                (p1_out / 1_000_000) * rate_h["output"]
            )

            # Phase 2: Hydrogen Refinement with LOW/MEDIUM thinking_level
            p2_cached_in = (batches_h * system_prompt_tokens) if has_cache else 0
            p2_uncached_in = (batches_h * batch_input_tokens) + (0 if has_cache else batches_h * system_prompt_tokens)
            p2_out = batches_h * lean_output_f2_tokens
            cost_p2_usd = (
                (p2_cached_in / 1_000_000) * rate_h["input_cached"] +
                (p2_uncached_in / 1_000_000) * rate_h["input_uncached"] +
                (p2_out / 1_000_000) * rate_h["output"]
            )

            storage_active_usd = 0.00  # Implicit caching has 0.00 USD storage fee
            profiler_usd = 0.002
            total_pln = (cost_p1_usd + cost_p2_usd + storage_active_usd + profiler_usd) * usd_pln
            return round(total_pln, 2)

        elif profile in ["4", "ultra", "ultra_pro", "cinema", "pro", "pro_level4"]:
            rate_flash = GOOGLE_API_RATES["flash"]
            rate_pro = GOOGLE_API_RATES["pro"]

            # Phase 1: Vision + Flash
            p1_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p1_uncached_in = batches * (batch_input_tokens + 256) + (0 if has_cache else batches * system_prompt_tokens)
            p1_out = batches * batch_output_f1_tokens
            cost_p1_usd = (
                (p1_cached_in / 1_000_000) * rate_flash["input_cached"] +
                (p1_uncached_in / 1_000_000) * rate_flash["input_uncached"] +
                (p1_out / 1_000_000) * rate_flash["output"]
            )

            # Phase 2: Gemini 3.1 Pro Refinement + Dedicated Pro CoT (100% batches)
            p2_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p2_uncached_in = (batches * batch_input_tokens) + (0 if has_cache else batches * system_prompt_tokens)
            p2_out = batches * batch_output_pro_tokens
            cost_p2_usd = (
                (p2_cached_in / 1_000_000) * rate_pro["input_cached"] +
                (p2_uncached_in / 1_000_000) * rate_pro["input_uncached"] +
                (p2_out / 1_000_000) * rate_pro["output"]
            )

            storage_active_usd = 0.0594
            profiler_usd = 0.004
            total_pln = (cost_p1_usd + cost_p2_usd + storage_active_usd + profiler_usd) * usd_pln
            return round(total_pln, 2)

        return 0.16

    @staticmethod
    def estimate_loaded_workload_cost_pln(
        profile: str,
        lines_count: int,
        batches_count: int,
        has_cache: bool = True,
        usd_pln: float = DEFAULT_USD_PLN,
        vat_rate: float = 0.23
    ) -> Dict[str, float]:
        """
        Oblicza realistyczny koszt netto i brutto dla faktycznej liczby utworzonych paczek
        i kwestii, z uwzględnieniem zdeduplikowanego promptu oraz bufora kontekstowego.
        """
        profile = (profile or "").lower()
        batches = max(1, batches_count)

        if profile in ["1", "standard", "flash_lite"]:
            return {
                "net_pln": 0.00,
                "gross_pln": 0.00,
                "batches": batches_count,
                "lines": lines_count
            }

        elif profile in ["3", "master", "flash_reasoning", "hydrogen", "hydrogen_master", "pro_level3"]:
            rate_h = GOOGLE_API_RATES["hydrogen"]
            system_prompt_tokens = 22000
            batch_input_tokens = 7800
            lean_output_f1_tokens = 1950
            lean_output_f2_tokens = 1550
            p2_input_tokens = 2800

            # Phase 1: Vision + Hydrogen
            p1_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p1_uncached_in = (batches * batch_input_tokens) + (0 if has_cache else batches * system_prompt_tokens)
            p1_out = batches * lean_output_f1_tokens
            cost_p1_usd = (
                (p1_cached_in / 1_000_000) * rate_h["input_cached"] +
                (p1_uncached_in / 1_000_000) * rate_h["input_uncached"] +
                (p1_out / 1_000_000) * rate_h["output"]
            )

            # Phase 2: Hydrogen Refinement
            p2_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p2_uncached_in = (batches * p2_input_tokens) + (0 if has_cache else batches * system_prompt_tokens)
            p2_out = batches * lean_output_f2_tokens
            cost_p2_usd = (
                (p2_cached_in / 1_000_000) * rate_h["input_cached"] +
                (p2_uncached_in / 1_000_000) * rate_h["input_uncached"] +
                (p2_out / 1_000_000) * rate_h["output"]
            )

            profiler_usd = 0.002
            total_usd = cost_p1_usd + cost_p2_usd + profiler_usd
            net_pln = round(total_usd * usd_pln, 2)
            gross_pln = round(net_pln * (1.0 + vat_rate), 2)
            return {
                "net_pln": net_pln,
                "gross_pln": gross_pln,
                "batches": batches_count,
                "lines": lines_count
            }

        elif profile in ["4", "ultra", "ultra_pro", "cinema", "pro", "pro_level4"]:
            rate_flash = GOOGLE_API_RATES["flash"]
            rate_pro = GOOGLE_API_RATES["pro"]
            system_prompt_tokens = 22000
            batch_input_tokens = 7800
            f1_out_tokens = 3200
            f2_out_tokens = 2200

            p1_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p1_uncached_in = (batches * batch_input_tokens) + (0 if has_cache else batches * system_prompt_tokens)
            p1_out = batches * f1_out_tokens
            cost_p1_usd = (
                (p1_cached_in / 1_000_000) * rate_flash["input_cached"] +
                (p1_uncached_in / 1_000_000) * rate_flash["input_uncached"] +
                (p1_out / 1_000_000) * rate_flash["output"]
            )

            p2_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p2_uncached_in = (batches * 2800) + (0 if has_cache else batches * system_prompt_tokens)
            p2_out = batches * f2_out_tokens
            cost_p2_usd = (
                (p2_cached_in / 1_000_000) * rate_pro["input_cached"] +
                (p2_uncached_in / 1_000_000) * rate_pro["input_uncached"] +
                (p2_out / 1_000_000) * rate_pro["output"]
            )

            storage_usd = 0.04
            profiler_usd = 0.002
            total_usd = cost_p1_usd + cost_p2_usd + storage_usd + profiler_usd
            net_pln = round(total_usd * usd_pln, 2)
            gross_pln = round(net_pln * (1.0 + vat_rate), 2)
            return {
                "net_pln": net_pln,
                "gross_pln": gross_pln,
                "batches": batches_count,
                "lines": lines_count
            }

        else:  # Profile 2: Studio / Flash
            rate_f = GOOGLE_API_RATES["flash"]
            system_prompt_tokens = 22000
            batch_input_tokens = 7800
            f1_out_tokens = 3200

            p1_cached_in = (batches * system_prompt_tokens) if has_cache else 0
            p1_uncached_in = (batches * batch_input_tokens) + (0 if has_cache else batches * system_prompt_tokens)
            p1_out = batches * f1_out_tokens
            cost_p1_usd = (
                (p1_cached_in / 1_000_000) * rate_f["input_cached"] +
                (p1_uncached_in / 1_000_000) * rate_f["input_uncached"] +
                (p1_out / 1_000_000) * rate_f["output"]
            )

            storage_usd = 0.005
            profiler_usd = 0.002
            total_usd = cost_p1_usd + storage_usd + profiler_usd
            net_pln = round(total_usd * usd_pln, 2)
            gross_pln = round(net_pln * (1.0 + vat_rate), 2)
            return {
                "net_pln": net_pln,
                "gross_pln": gross_pln,
                "batches": batches_count,
                "lines": lines_count
            }

    @classmethod
    def calculate_actual_cost_breakdown(
        cls,
        f1_stats: Dict[str, Any],
        f2_stats: Optional[Dict[str, Any]] = None,
        usd_pln: float = DEFAULT_USD_PLN,
        vat_rate: float = 0.23
    ) -> Dict[str, float]:
        """
        Calculates exact actual session cost breakdown (net, gross with VAT, standard rate without cache, and savings).
        """
        # Phase 1
        m1 = f1_stats.get("model", "flash")
        rate1 = GOOGLE_API_RATES["flash"]
        if "hydrogen" in str(m1).lower():
            rate1 = GOOGLE_API_RATES["hydrogen"]
        elif "pro" in str(m1).lower() or "argon" in str(m1).lower() or "carbon" in str(m1).lower():
            rate1 = GOOGLE_API_RATES["pro"]
        elif "lite" in str(m1).lower():
            rate1 = GOOGLE_API_RATES["flash_lite"]

        cached1 = f1_stats.get("cached", 0)
        prompt1 = f1_stats.get("prompt", 0)
        uncached1 = max(0, prompt1 - cached1)
        out1 = f1_stats.get("output", 0)

        cost1_usd = (
            (cached1 / 1_000_000) * rate1["input_cached"] +
            (uncached1 / 1_000_000) * rate1["input_uncached"] +
            (out1 / 1_000_000) * rate1["output"]
        )
        cost1_without_cache_usd = (
            (prompt1 / 1_000_000) * rate1["input_uncached"] +
            (out1 / 1_000_000) * rate1["output"]
        )

        cost2_usd = 0.0
        cost2_without_cache_usd = 0.0

        # Phase 2 (if active)
        if f2_stats:
            m2 = f2_stats.get("model") or f1_stats.get("model", "flash")
            rate2 = GOOGLE_API_RATES["flash"]
            if "hydrogen" in str(m2).lower():
                rate2 = GOOGLE_API_RATES["hydrogen"]
            elif "pro" in str(m2).lower() or "argon" in str(m2).lower() or "carbon" in str(m2).lower():
                rate2 = GOOGLE_API_RATES["pro"]
            elif "lite" in str(m2).lower():
                rate2 = GOOGLE_API_RATES["flash_lite"]

            cached2 = f2_stats.get("cached", 0)
            prompt2 = f2_stats.get("prompt", 0)
            uncached2 = max(0, prompt2 - cached2)
            out2 = f2_stats.get("output", 0)

            cost2_usd = (
                (cached2 / 1_000_000) * rate2["input_cached"] +
                (uncached2 / 1_000_000) * rate2["input_uncached"] +
                (out2 / 1_000_000) * rate2["output"]
            )
            cost2_without_cache_usd = (
                (prompt2 / 1_000_000) * rate2["input_uncached"] +
                (out2 / 1_000_000) * rate2["output"]
            )

        total_net_usd = cost1_usd + cost2_usd
        total_without_cache_usd = cost1_without_cache_usd + cost2_without_cache_usd

        f1_net_pln = round(cost1_usd * usd_pln, 2)
        f2_net_pln = round(cost2_usd * usd_pln, 2)
        total_net_pln = round(total_net_usd * usd_pln, 2)
        total_gross_pln = round(total_net_pln * (1.0 + vat_rate), 2)
        
        standard_net_pln = round(total_without_cache_usd * usd_pln, 2)
        standard_gross_pln = round(standard_net_pln * (1.0 + vat_rate), 2)
        savings_pln = round(max(0.0, standard_net_pln - total_net_pln), 2)

        return {
            "net_pln": total_net_pln,
            "gross_pln": total_gross_pln,
            "f1_net_pln": f1_net_pln,
            "f2_net_pln": f2_net_pln,
            "standard_net_pln": standard_net_pln,
            "standard_gross_pln": standard_gross_pln,
            "savings_pln": savings_pln,
            "vat_rate": vat_rate
        }

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
        breakdown = cls.calculate_actual_cost_breakdown(f1_stats, f2_stats, usd_pln=usd_pln)
        return breakdown["net_pln"]

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
            "  💰 STATUS CENNIKA GOOGLE: Zweryfikowany (Brak ukrytych opłat, rabat Context Cache aktywny)",
            f"  💡 Szacowany koszt: ~{cost_flash:.2f} zł (Studyjny) | ~{cost_pro:.2f} zł (Mistrzowski) | ~{cost_ultra:.2f} zł (Kinowy)",
            "  🛡️ Ochrona budżetu: Każda ewentualna zmiana stawek u Google zostanie natychmiast zasygnalizowana."
        ]
        return "\n".join(lines)
