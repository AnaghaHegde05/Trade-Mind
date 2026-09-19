import asyncio
from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.services.world_bank import WorldBankService


class RiskAgent(BaseAgent):
    """Assesses political stability and inflation risk for each target market via World Bank indicators."""

    def __init__(self):
        super().__init__("Risk Agent")

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        self.log_step("Starting country risk and stability assessment...", progress=10.0)

        top_markets, countries = self.get_target_countries(context)
        self.log_step(f"Analyzing political/economic risks for countries: {', '.join(countries)}", progress=30.0)

        risk_records = {}

        async def process_single_country(country: str):
            self.log_step(f"Retrieving risk parameters for {country}...", progress=40.0)

            ps_task = WorldBankService.get_indicator_for_country(country, "political_stability")
            inf_task = WorldBankService.get_indicator_for_country(country, "inflation")
            ps_history, inf_history = await asyncio.gather(ps_task, inf_task)

            # WGI Political Stability Index: -2.5 (very unstable) to +2.5 (very stable)
            latest_ps = float(ps_history[0]["value"]) if ps_history else 0.0
            latest_inf = float(inf_history[0]["value"]) if inf_history else 3.0

            # Normalize -2.5..+2.5 to 0.0-1.0
            ps_score = max(0.0, min(1.0, (latest_ps + 2.5) / 5.0))

            if latest_inf < 0:
                # Deflation is also risky: -5% -> 0.2, 0% -> 1.0
                inf_score = max(0.2, 1.0 - abs(latest_inf) / 5.0)
            elif latest_inf <= 4.0:
                # 0-4% is healthy, normal range for developed economies
                inf_score = 1.0
            else:
                # High inflation penalty: 4% -> 1.0, 15% -> 0.1
                inf_score = max(0.1, 1.0 - (latest_inf - 4.0) / 11.0)

            # Political stability weighted more heavily (60/40) as the broader risk indicator
            r_score = round(0.6 * ps_score + 0.4 * inf_score, 2)

            overall_risk = 1.0 - r_score
            risk_label = "Low" if overall_risk < 0.3 else "Medium" if overall_risk < 0.6 else "High"

            return country, {
                "political_stability_index": round(latest_ps, 2),
                "inflation_rate_pct": round(latest_inf, 2),
                "risk_score": r_score,
                "overall_risk_level": risk_label
            }

        tasks = [process_single_country(c) for c in countries]
        results = await asyncio.gather(*tasks)

        for country, record in results:
            risk_records[country] = record

        overall_score = round(sum(r["risk_score"] for r in risk_records.values()) / len(risk_records), 2) if risk_records else 0.5

        output = {
            "risk_records": risk_records,
            "risk_score": overall_score
        }

        self.log_step("Country risk and stability assessment completed.", progress=100.0)
        return output
