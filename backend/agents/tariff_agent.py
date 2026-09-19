import logging
import httpx
from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.utils.schema import get_country_iso3

logger = logging.getLogger("trade_intel.agents.tariff_agent")

# WITS (World Integrated Trade Solution) requires numeric reporter codes,
# not ISO3 - e.g. "DEU" (Germany) -> "276"
ISO_TO_REPORTER_CODE = {
    "DEU": "276", "BGD": "050", "CHN": "156", "VNM": "704", "USA": "842",
    "ARE": "784", "GBR": "826", "AUS": "036", "DZA": "012", "ZAF": "710",
    "EGY": "818", "BRA": "076", "IND": "356", "PAK": "586", "JPN": "392",
    "KOR": "410", "POL": "616", "BEL": "056", "FRA": "250", "ITA": "380",
    "ESP": "724", "PRT": "620", "GRC": "300", "SWE": "752", "CHE": "756",
    "MYS": "458", "IDN": "360", "THA": "764", "SAU": "682"
}


class TariffAgent(BaseAgent):
    """Queries the World Bank WITS API for real-time import tariff data per target country."""

    def __init__(self):
        super().__init__("Tariff Agent")

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        hs_code = str(inputs.get("hs_code", "5201")).strip()
        self.log_step(f"Starting real-time tariff analysis for HS code: {hs_code}", progress=10.0)

        # WITS requires a 6-digit HS code (HS6)
        hs_code_6 = hs_code
        if len(hs_code_6) == 4:
            hs_code_6 = hs_code_6 + "00"
        elif len(hs_code_6) < 6:
            hs_code_6 = hs_code_6.ljust(6, '0')
        elif len(hs_code_6) > 6:
            hs_code_6 = hs_code_6[:6]

        top_markets, countries = self.get_target_countries(context)
        tariff_records = {}

        self.log_step(f"Querying World Bank WITS API for {len(countries)} target markets...", progress=30.0)

        async with httpx.AsyncClient(timeout=20.0) as client:
            for idx, country in enumerate(countries):
                pct = 30.0 + (float(idx) / len(countries)) * 60.0

                iso = get_country_iso3(country)
                reporter_code = ISO_TO_REPORTER_CODE.get(iso)
                if not reporter_code:
                    raise ValueError(f"ISO numeric reporter code not found for country: {country} (ISO: {iso})")

                url = f"https://wits.worldbank.org/API/V1/SDMX/V21/rest/data/DF_WITS_Tariff_TRAINS/.{reporter_code}.000.{hs_code_6}.reported/?startperiod=2015&endperiod=2024"
                self.log_step(f"Fetching WITS tariff data for {country} (ISO: {iso}, code: {reporter_code})", progress=pct)

                try:
                    r = await client.get(url, headers={"Accept": "application/json"})
                    if r.status_code == 200:
                        data = r.json()
                        series = data.get("dataSets", [{}])[0].get("series", {})
                        if series:
                            series_key = list(series.keys())[0]
                            obs_dict = series[series_key].get("observations", {})
                            if obs_dict:
                                latest_key = str(max(int(k) for k in obs_dict.keys()))
                                tariff_pct = float(obs_dict[latest_key][0])
                            else:
                                raise ValueError(f"No observations found in WITS response for {country}")
                        else:
                            raise ValueError(f"No series data found in WITS response for {country}")
                    else:
                        raise ValueError(f"WITS API returned status code {r.status_code} for {country}")
                except Exception as e:
                    logger.error(f"Error querying WITS API for {country}: {e}")
                    raise e

                # Lower tariff = higher score. 30% treated as a very-high-tariff
                # ceiling: 0% -> 1.0, 15% -> 0.5, 30% -> 0.1
                t_score = round(max(0.1, min(1.0, 1.0 - (tariff_pct / 30.0))), 2)
                severity = "Low" if tariff_pct <= 2.0 else "Medium" if tariff_pct <= 8.0 else "High"

                tariff_records[country] = {
                    "tariff_pct": tariff_pct,
                    "tariff_score": t_score,
                    "tariff_severity": severity
                }

        overall_score = round(sum(t["tariff_score"] for t in tariff_records.values()) / len(tariff_records), 2) if tariff_records else 0.5

        output = {
            "tariff_records": tariff_records,
            "tariff_score": overall_score
        }

        self.log_step("Real-time tariff analysis completed successfully.", progress=100.0)
        return output
