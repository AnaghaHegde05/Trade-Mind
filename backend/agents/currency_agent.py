from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.services.forex import ForexService


class CurrencyAgent(BaseAgent):
    """Evaluates FX exchange rates and currency stability/risk for each target market."""

    def __init__(self):
        super().__init__("Currency Agent")

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        self.log_step("Starting currency exchange and FX risk analysis...", progress=10.0)

        top_markets, countries = self.get_target_countries(context)
        self.log_step(f"Retrieving exchange rates for target countries: {', '.join(countries)}", progress=35.0)

        rates = await ForexService.get_exchange_rates()

        currency_scores = {}
        currency_conversions = {}

        for country in countries:
            currency_code = ForexService.get_currency_for_country(country)
            rate = rates.get(currency_code, 1.0)
            vol = ForexService.get_currency_volatility(currency_code)

            currency_conversions[country] = {
                "currency": currency_code,
                "rate": rate,
                "volatility": vol
            }

            # Lower volatility -> higher score (0.0 = USD baseline, ~0.28 = highly volatile)
            # e.g. vol=0.05 -> score 0.85 (stable); vol=0.15 -> score 0.55 (moderate risk)
            c_score = round(max(0.1, min(1.0, 1.0 - (vol * 3.0))), 2)
            risk_label = "Low" if vol < 0.04 else "Medium" if vol < 0.08 else "High" if vol < 0.15 else "Critical"

            currency_scores[country] = {
                "currency_score": c_score,
                "currency_risk": risk_label,
                "rate": rate,
                "volatility": vol
            }

        overall_score = round(sum(c["currency_score"] for c in currency_scores.values()) / len(currency_scores), 2) if currency_scores else 0.5

        output = {
            "currency_rates": rates,
            "currency_scores": currency_scores,
            "currency_conversions": currency_conversions,
            "currency_score": overall_score
        }

        self.log_step("Currency exchange and FX risk analysis completed.", progress=100.0)
        return output
