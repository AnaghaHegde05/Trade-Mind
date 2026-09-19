import json
import logging
from typing import Dict, Any, List, Optional

from backend.config.settings import settings

logger = logging.getLogger("trade_intel.services.llm")

SYSTEM_PROMPT = (
    "You are a trade analysis assistant. You will be given already-computed "
    "quantitative results for a set of candidate export countries. Write a "
    "short (2-3 sentence) natural-language reasoning summary for each country, "
    "explaining why it ranked where it did.\n\n"
    "Rules:\n"
    "- Use ONLY the numbers provided. Do not invent, estimate, or round in a "
    "way that changes any figure.\n"
    "- Do not add countries, statistics, or claims not present in the input.\n"
    "- Respond with strict JSON only: {\"<country>\": \"<summary text>\", ...}\n"
    "- No markdown, no commentary outside the JSON object."
)


class LLMService:
    """
    Wraps a Groq chat completion call used to synthesize the Decision Agent's
    natural-language reasoning from already-computed structured data.

    This is a synthesis step only: every number the model can reference is
    computed elsewhere in the pipeline before this is ever called. If the
    call fails for any reason, callers must fall back to template-based
    reasoning - this service never raises to its caller.
    """

    @staticmethod
    async def generate_narratives(
        countries: List[Dict[str, Any]]
    ) -> Optional[Dict[str, str]]:
        """
        Given a list of country records (rank, scores, profit, tariff, transit,
        etc.), returns {country_name: narrative_text} or None on any failure.
        """
        if not settings.GROQ_API_KEY:
            logger.info("GROQ_API_KEY not configured. Skipping LLM synthesis.")
            return None

        if not countries:
            return None

        try:
            from groq import AsyncGroq
        except ImportError:
            logger.warning("groq package not installed. Skipping LLM synthesis.")
            return None

        # Build a minimal, explicit numeric payload - nothing the model has to guess at
        payload = [
            {
                "country": c["country"],
                "rank": c["rank"],
                "final_score": c["final_score"],
                "expected_profit_usd": c["expected_profit_usd"],
                "market_score": c["market_score"],
                "predicted_demand_growth_pct": c["predicted_demand_growth_pct"],
                "tariff_pct": c["tariff_pct"],
                "transit_days": c["transit_days"],
                "currency_risk_level": c["currency_risk_level"],
                "political_stability_score": c["political_stability_score"],
            }
            for c in countries
        ]

        try:
            client = AsyncGroq(api_key=settings.GROQ_API_KEY)
            response = await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload)},
                ],
                temperature=0.3,
                max_tokens=600,
                response_format={"type": "json_object"},
                timeout=15.0,
            )
            raw = response.choices[0].message.content
            narratives = json.loads(raw)

            if not isinstance(narratives, dict):
                raise ValueError("LLM response was not a JSON object")

            return {str(k): str(v) for k, v in narratives.items()}

        except Exception as e:
            logger.warning(f"LLM narrative synthesis failed, falling back to template reasoning: {e}")
            return None
