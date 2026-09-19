import math
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from backend.config.settings import settings
from backend.utils.schema import get_country_iso3

logger = logging.getLogger("trade_intel.services.logistics")

AVERAGE_SHIP_SPEED_KNOTS = 18.0
AVERAGE_SHIP_SPEED_KMH = AVERAGE_SHIP_SPEED_KNOTS * 1.852

# In-memory cache for the static reference CSVs (ports, LPI). These files
# don't change at runtime, so they're loaded from disk once per process
# and reused - previously calculate_route() re-read and re-parsed both
# files on every call (up to once per candidate country per analysis run).
_csv_cache: Dict[str, pd.DataFrame] = {}


def _load_csv_cached(path: Path) -> pd.DataFrame:
    """Loads a CSV once and reuses it on subsequent calls, keyed by path."""
    key = str(path)
    if key not in _csv_cache:
        _csv_cache[key] = pd.read_csv(path)
    return _csv_cache[key]

ISO_TO_STANDARD_NAME = {
    "DEU": "Germany",
    "BGD": "Bangladesh",
    "CHN": "China",
    "VNM": "Vietnam",
    "USA": "United States",
    "ARE": "United Arab Emirates",
    "GBR": "United Kingdom",
    "AUS": "Australia",
    "DZA": "Algeria",
    "ZAF": "South Africa",
    "EGY": "Egypt",
    "BRA": "Brazil",
    "IND": "India",
    "PAK": "Pakistan",
    "JPN": "Japan",
    "KOR": "South Korea",
    "POL": "Poland",
    "BEL": "Belgium",
    "FRA": "France",
    "ITA": "Italy",
    "ESP": "Spain",
    "PRT": "Portugal",
    "GRC": "Greece",
    "SWE": "Sweden",
    "CHE": "Switzerland",
    "MYS": "Malaysia",
    "IDN": "Indonesia",
    "THA": "Thailand",
    "SAU": "Saudi Arabia"
}

class LogisticsService:
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates straight-line great-circle distance in kilometers using the Haversine formula."""
        R = 6371.0  # Earth radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def calculate_route(country_name: str) -> Dict[str, Any]:
        """
        Computes maritime distance, travel days, and shipping cost per ton from an Indian port to target country ports
        using world_ports.csv and world_bank_lpi.csv.
        """
        ports_file = settings.LOGISTICS_DATASET_DIR / "world_ports.csv"
        lpi_file = settings.LOGISTICS_DATASET_DIR / "world_bank_lpi.csv"
        
        if not ports_file.exists():
            raise FileNotFoundError(f"Logistics ports database not found at: {ports_file}")
        if not lpi_file.exists():
            raise FileNotFoundError(f"Logistics LPI database not found at: {lpi_file}")

        # Normalize country_name using ISO code to find the standard name in world_ports.csv
        iso = get_country_iso3(country_name)
        search_country = ISO_TO_STANDARD_NAME.get(iso, country_name)

        # 1. Load world ports (cached after first load)
        df_ports = _load_csv_cached(ports_file)
        
        # Find Indian origin port (Nhava Sheva/Mumbai preferred, or first Large/Medium)
        india_ports = df_ports[df_ports['Country Code'].str.lower() == 'india']
        if india_ports.empty:
            raise ValueError("No Indian ports found in world_ports.csv to use as origin.")
            
        mumbai_ports = india_ports[india_ports['Main Port Name'].str.contains('Nhava|Mumbai|Bombay', case=False, na=False)]
        if not mumbai_ports.empty:
            origin_port = mumbai_ports.iloc[0]
        else:
            origin_port = india_ports.iloc[0]
            
        origin_name = f"{origin_port['Main Port Name']} (India)"
        lat1, lon1 = float(origin_port['Latitude']), float(origin_port['Longitude'])
        
        # Find destination ports in target country
        dest_ports = df_ports[df_ports['Country Code'].str.lower() == search_country.lower()]
        if dest_ports.empty:
            # Substring relaxation
            dest_ports = df_ports[df_ports['Country Code'].str.lower().str.contains(search_country.lower(), na=False)]
            
        if dest_ports.empty:
            raise ValueError(f"No ports found for country {search_country} (alias: {country_name}) in world_ports.csv")
            
        # Preferred Large/Medium ports
        pref_ports = dest_ports[dest_ports['Harbor Size'].str.lower().isin(['large', 'medium'])]
        if not pref_ports.empty:
            dest_port = pref_ports.iloc[0]
        else:
            dest_port = dest_ports.iloc[0]
            
        dest_name = f"Port of {dest_port['Main Port Name']}"
        lat2, lon2 = float(dest_port['Latitude']), float(dest_port['Longitude'])
        
        # 2. Calculate Great Circle distance and apply circumnavigation factor of 1.3x
        gcd_km = LogisticsService.calculate_distance(lat1, lon1, lat2, lon2)
        distance_km = gcd_km * 1.3
        
        # Convert km to Nautical Miles for marine time calculations
        distance_nm = distance_km / 1.852
        
        # 3. Load World Bank LPI efficiency index (cached after first load)
        df_lpi = _load_csv_cached(lpi_file)
        
        # Find country row with indicator "Logistics performance index: Overall score (1=low to 5=high)"
        indicator_name = 'Logistics performance index: Overall score (1=low to 5=high)'
        c_lpi = df_lpi[
            (df_lpi['Country Name'].str.lower() == search_country.lower()) &
            (df_lpi['Indicator Name'] == indicator_name)
        ]
        if c_lpi.empty:
            c_lpi = df_lpi[
                (df_lpi['Country Name'].str.lower().str.contains(search_country.lower(), na=False)) &
                (df_lpi['Indicator Name'] == indicator_name)
            ]
            
        lpi_score = 2.80  # Global baseline average LPI score if not found
        if not c_lpi.empty:
            for year_col in ['2023', '2018', '2016', '2014', '2012', '2010', '2007']:
                val = c_lpi.iloc[0].get(year_col)
                if pd.notna(val) and val > 0:
                    lpi_score = float(val)
                    break
                    
        # Normalize LPI to efficiency (from 0.2 to 1.0)
        efficiency = lpi_score / 5.0
        
        # Sea travel duration: hours = distance in NM / speed in knots
        travel_hours = distance_nm / AVERAGE_SHIP_SPEED_KNOTS
        sea_days = travel_hours / 24.0
        
        # Port handling delay scales with efficiency (lower efficiency adds more days)
        port_delay_days = (1.0 - efficiency) * 12.0
        total_transit_days = round(sea_days + port_delay_days, 1)
        
        # Cost per ton calculation
        # Freight rate: $0.055 per km per ton
        # Add port handling and terminal congestion fees modified by LPI efficiency
        base_freight = distance_km * 0.055
        terminal_charge = (1.5 - efficiency) * 120.0
        cost_per_ton = round(base_freight + terminal_charge, 2)
        
        # Logistics Score: based on transit time and cost normalized (higher score is better)
        norm_cost = min(1.0, cost_per_ton / 1200.0)
        norm_time = min(1.0, total_transit_days / 45.0)
        logistics_score = round(1.0 - (0.6 * norm_cost + 0.4 * norm_time), 2)
        
        return {
            "origin_port": origin_name,
            "destination_port": dest_name,
            "distance_km": round(distance_km, 1),
            "transit_days": total_transit_days,
            "cost_per_ton": cost_per_ton,
            "logistics_score": max(0.1, min(1.0, logistics_score))
        }
