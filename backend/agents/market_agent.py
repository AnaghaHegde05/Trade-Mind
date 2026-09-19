import logging
import pandas as pd
from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.utils.schema import load_all_datasets_in_dir
from backend.ml.pipelines import train_and_forecast_timeseries
from backend.config.settings import settings


class MarketAgent(BaseAgent):
    """
    First agent in the pipeline. Loads historical trade data for the given
    commodity/HS code, identifies the top importing countries by trade value,
    and produces a CAGR-based forecast + attractiveness score for each.
    """

    def __init__(self):
        super().__init__("Market Agent")

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        hs_code_prefix = str(inputs.get("hs_code", "5201")).strip()
        commodity_filter = str(inputs.get("commodity_name", "cotton")).lower().strip()

        self.log_step(f"Starting market analysis for HS code: {hs_code_prefix} ({commodity_filter})", progress=10.0)

        market_dir = settings.MARKET_DATASET_DIR
        self.log_step(f"Scanning directory: {market_dir}", progress=20.0)

        df = load_all_datasets_in_dir(market_dir)
        if df.empty:
            raise FileNotFoundError(f"No real market datasets found in {market_dir}.")

        self.log_step(f"Successfully loaded dataset. Raw records count: {len(df)}", progress=50.0)

        # Match by HS code prefix (e.g. '5201' matches '520100', '520110', ...)
        # or by commodity name containing the filter term
        df["hs_code_str"] = df["hs_code"].astype(str)
        filtered_df = df[
            df["hs_code_str"].str.startswith(hs_code_prefix) |
            df["commodity_name"].str.lower().str.contains(commodity_filter)
        ]

        if filtered_df.empty:
            # No exact match - fall back to the full dataset rather than erroring out
            self.log_step("Filter matched 0 records. Relaxing filter to general categories...", progress=55.0, level=logging.WARNING)
            filtered_df = df

        self.log_step(f"Filtered records count matching '{hs_code_prefix}': {len(filtered_df)}", progress=60.0)

        # Consolidate multiple trade records into country-year totals
        grouped = filtered_df.groupby(["country", "year"], as_index=False).agg({
            "value": "sum",
            "quantity": "sum"
        })

        latest_year = int(grouped["year"].max())
        self.log_step(f"Analyzing latest trade statistics for year: {latest_year}", progress=70.0)

        latest_data = grouped[grouped["year"] == latest_year]
        if latest_data.empty:
            # No data for the latest year - use the mean across all available years instead
            latest_data = grouped.groupby("country", as_index=False).agg({
                "value": "mean",
                "quantity": "mean"
            })

        # Rank by trade value - largest importers are the most attractive markets
        sorted_countries = latest_data.sort_values(by="value", ascending=False).reset_index(drop=True)
        top_countries = sorted_countries["country"].head(7).tolist()

        market_forecast = {}   # 3-year forecast values per country
        market_trends = {}     # historical series + CAGR + model used, per country
        top_markets = []

        forecast_years = [latest_year + 1, latest_year + 2, latest_year + 3]
        self.log_step(f"Training time-series forecasting models for top markets: {', '.join(top_countries)}", progress=80.0)

        country_results = []
        for country in top_countries:
            c_df = grouped[grouped["country"] == country].sort_values("year")
            history = list(zip(c_df["year"].astype(int).tolist(), c_df["value"].astype(float).tolist()))

            forecast_out = train_and_forecast_timeseries(
                history=history,
                forecast_years=forecast_years,
                country=country,
                indicator="trade_volume"
            )

            market_forecast[country] = forecast_out["forecast"]
            market_trends[country] = {
                "historical": {int(y): float(v) for y, v in history},
                "cagr": forecast_out["cagr"],
                "model": forecast_out["model_used"]
            }

            latest_val = float(c_df["value"].iloc[-1])
            cagr = forecast_out["cagr"]

            country_results.append({
                "country": country,
                "import_volume": float(c_df["quantity"].iloc[-1]),
                "import_value": latest_val,
                "growth_rate": round(cagr * 100, 2),
                # Larger markets with higher growth score higher
                "raw_score": latest_val * (1.0 + cagr)
            })

        # Normalize raw scores to a 0.1-1.0 range so they're comparable across countries
        if country_results:
            max_score = max(c["raw_score"] for c in country_results)

            for c in country_results:
                c["market_score"] = round(max(0.1, c["raw_score"] / max_score), 2) if max_score > 0 else 0.5

            for c in country_results:
                top_markets.append({
                    "country": c["country"],
                    "import_volume": c["import_volume"],
                    "import_value": c["import_value"],
                    "growth_rate": c["growth_rate"],
                    "market_score": c["market_score"]
                })

        overall_market_score = round(sum(m["market_score"] for m in top_markets) / len(top_markets), 2) if top_markets else 0.5

        output = {
            "top_markets": top_markets,
            "market_forecast": market_forecast,
            "market_trends": market_trends,
            "market_score": overall_market_score
        }

        self.log_step(f"Market analysis complete. Identified {len(top_markets)} major export destinations.", progress=100.0)
        return output
