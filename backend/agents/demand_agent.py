import logging
import asyncio
import math
from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.services.world_bank import WorldBankService
from backend.ml.pipelines import train_and_forecast_timeseries


class DemandAgent(BaseAgent):
    """
    Analyzes macro-economic demand for each target market: fetches GDP
    growth and population from the World Bank, forecasts GDP trend, and
    scores each country's demand potential.
    """

    def __init__(self):
        super().__init__("Demand Agent")

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        self.log_step("Starting macro demand growth analysis...", progress=10.0)

        top_markets, countries = self.get_target_countries(context)
        self.log_step(f"Analyzing economic demand for target markets: {', '.join(countries)}", progress=30.0)

        demand_scores = {}
        demand_growth_forecast = {}

        async def process_single_country(country: str):
            self.log_step(f"Retrieving GDP and population stats for {country}...", progress=35.0)

            gdp_task = WorldBankService.get_indicator_for_country(country, "gdp_growth")
            pop_task = WorldBankService.get_indicator_for_country(country, "population")
            gdp_history_raw, pop_history_raw = await asyncio.gather(gdp_task, pop_task)

            latest_gdp_growth = 2.0  # default if no data available (%)
            gdp_cagr = 0.0
            forecasts = {}

            if gdp_history_raw:
                gdp_history = sorted(
                    [(entry["year"], entry["value"]) for entry in gdp_history_raw],
                    key=lambda x: x[0]
                )
                latest_year = gdp_history[-1][0]
                forecast_years = [latest_year + 1, latest_year + 2, latest_year + 3]

                gdp_forecast = train_and_forecast_timeseries(
                    history=gdp_history,
                    forecast_years=forecast_years,
                    country=country,
                    indicator="gdp_growth"
                )

                forecasts = gdp_forecast["forecast"]
                latest_gdp_growth = float(gdp_history[-1][1])
                gdp_cagr = gdp_forecast["cagr"]

            latest_pop = 50_000_000.0  # default: 50 million if no data available
            if pop_history_raw:
                latest_pop = pop_history_raw[0]["value"]

            # GDP factor: assumes growth ranges -2%..+8%, normalized to 0.0-1.0
            gdp_score_factor = max(0.0, min(1.0, (latest_gdp_growth + 2.0) / 10.0))

            # Population factor: log scale, normalizes 1M-1B population to 0.0-1.0
            pop_score_factor = max(0.1, min(1.0, (math.log10(latest_pop) - 6.0) / 3.5))

            # Weighted 70% GDP / 30% population, with growth-trend adjustment
            # capped at +/-0.1 to avoid extreme shifts from a single outlier year
            cagr_adj = max(-0.1, min(0.1, gdp_cagr))
            demand_score = round(0.7 * gdp_score_factor + 0.3 * pop_score_factor + cagr_adj, 2)

            return country, {
                "demand_score": max(0.1, min(1.0, demand_score)),
                "gdp_growth": round(latest_gdp_growth, 2),
                "population": int(latest_pop)
            }, forecasts

        tasks = [process_single_country(c) for c in countries]
        results = await asyncio.gather(*tasks)

        for country, stats, forecasts in results:
            demand_scores[country] = stats
            demand_growth_forecast[country] = forecasts

        overall_demand_score = round(sum(d["demand_score"] for d in demand_scores.values()) / len(demand_scores), 2) if demand_scores else 0.5

        output = {
            "demand_scores": demand_scores,
            "demand_growth_forecast": demand_growth_forecast,
            "demand_score": overall_demand_score
        }

        self.log_step("Economic demand growth analysis completed.", progress=100.0)
        return output
