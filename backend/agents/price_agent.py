import httpx
import logging
import pandas as pd
from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.ml.pipelines import train_and_forecast_timeseries
from backend.config.settings import settings

logger = logging.getLogger("trade_intel.agents.price_agent")


class PriceAgent(BaseAgent):
    """
    Analyzes historical commodity prices and forecasts future price trends.
    Sources real-time data from FRED when an API key is configured, and
    falls back to a local historical pricing dataset otherwise.
    """

    def __init__(self):
        super().__init__("Price Agent")

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        commodity = str(inputs.get("commodity_name", "cotton")).lower().strip()
        self.log_step(f"Starting price prediction for: {commodity}", progress=10.0)

        pricing_file = settings.PRICING_DATASET_DIR / "cotton_prices_worldbank.xlsx"
        history = []

        if settings.FRED_API_KEY:
            self.log_step("FRED API key detected. Querying real-time FRED commodity database...", progress=20.0)
            # PCOUTUSDM = Cotton Price (USD/lb), PALLFNFINDEXM = All commodities index
            series_id = "PCOUTUSDM" if "cotton" in commodity else "PALLFNFINDEXM"
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key": settings.FRED_API_KEY,
                "file_type": "json",
                "observation_start": "2018-01-01"
            }

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.get(url, params=params)
                    if r.status_code == 200:
                        data = r.json()
                        temp_df = pd.DataFrame(data.get("observations", []))
                        temp_df = temp_df[temp_df["value"] != "."]  # "." marks missing values in FRED
                        temp_df["year"] = pd.to_datetime(temp_df["date"]).dt.year
                        temp_df["value"] = pd.to_numeric(temp_df["value"])

                        # FRED gives cotton in $/lb; convert to $/ton (1 ton = 2204.62 lb)
                        factor = 22.0462 if "cotton" in commodity else 1.0
                        grouped = temp_df.groupby("year", as_index=False)["value"].mean()
                        grouped["value"] = grouped["value"] * factor
                        history = list(zip(grouped["year"].astype(int).tolist(), grouped["value"].astype(float).tolist()))
                        self.log_step("Successfully fetched real-time pricing data from FRED.", progress=40.0)
            except Exception as e:
                logger.warning(f"Failed to fetch from FRED API: {e}. Falling back to local files.")

        if not history:
            if not pricing_file.exists():
                raise FileNotFoundError(f"Pricing dataset not found at: {pricing_file}")

            self.log_step(f"Parsing local Pink Sheet pricing dataset: {pricing_file}", progress=30.0)
            df_xl = pd.read_excel(pricing_file, sheet_name="Monthly Prices", header=None)

            data_rows = []
            for _, row in df_xl.iterrows():
                # Date column looks like "2018M01" (year 'M' month)
                val_date = row[0]
                if isinstance(val_date, str) and len(val_date) == 7 and 'M' in val_date:
                    parts = val_date.split('M')
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        year = int(parts[0])
                        price_val = row[54]  # price is in column 54 of this sheet
                        try:
                            # Sheet has prices in $/kg; convert to $/ton (1 ton = 1000 kg)
                            price_usd_per_ton = float(price_val) * 1000.0
                            data_rows.append({"year": year, "value": price_usd_per_ton})
                        except (ValueError, TypeError):
                            continue

            if not data_rows:
                raise ValueError(f"No valid price rows found in {pricing_file} for column 54.")

            df_clean = pd.DataFrame(data_rows)
            grouped = df_clean.groupby("year", as_index=False)["value"].mean()
            history = list(zip(grouped["year"].astype(int).tolist(), grouped["value"].astype(float).tolist()))
            self.log_step(f"Successfully loaded and parsed {len(history)} annual price records from local Excel file.", progress=50.0)

        latest_year = history[-1][0]
        forecast_years = [latest_year + 1, latest_year + 2, latest_year + 3]

        self.log_step("Forecasting price trend...", progress=70.0)
        forecast_out = train_and_forecast_timeseries(
            history=history,
            forecast_years=forecast_years,
            country="Global",
            indicator=f"{commodity}_price"
        )
        forecast_prices = forecast_out["forecast"]

        # Volatility: standard deviation of price history as a fraction of the mean
        prices_seq = [h[1] for h in history]
        mean_p = sum(prices_seq) / len(prices_seq)
        diffs = [abs(p - mean_p) for p in prices_seq]
        std_p = (sum(d**2 for d in diffs) / len(prices_seq)) ** 0.5
        volatility = round(std_p / mean_p, 3)

        next_year = latest_year + 1
        predicted_price = forecast_prices.get(next_year, prices_seq[-1])

        trend_cagr = forecast_out["cagr"]
        # Score = base 0.7, penalized for volatility above 15%, adjusted for trend
        # direction (CAGR capped at +/-0.2), clamped to a 0.2-1.0 floor/ceiling
        vol_penalty = max(0.0, volatility - 0.15)
        trend_bonus = max(-0.2, min(0.2, trend_cagr))
        price_score = max(0.2, min(1.0, round(0.7 - vol_penalty + trend_bonus, 2)))

        output = {
            "predicted_price_usd_per_ton": round(predicted_price, 2),
            "price_volatility": volatility,
            "price_forecast": forecast_prices,
            "price_history": {int(y): float(v) for y, v in history},
            "price_trend": "Bullish" if trend_cagr > 0.01 else "Bearish" if trend_cagr < -0.01 else "Stable",
            "price_score": price_score
        }

        self.log_step(f"Price forecast complete. Predicted {next_year} price: ${predicted_price:.2f}/ton, Volatility: {volatility*100:.1f}%.", progress=100.0)
        return output
