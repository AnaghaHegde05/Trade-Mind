import re
import glob
import logging
import datetime
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger("trade_intel.utils.schema")

# Standardized column mappings
COLUMN_PATTERNS = {
    "hs_code": [r"hs.*code", r"cmd.*code", r"commodity.*code", r"code", r"cmdcode"],
    "commodity_name": [r"commodity.*name", r"cmd.*desc", r"commodity.*desc", r"commodity", r"product", r"cmddesc"],
    "country": [r"country", r"region", r"partner.*iso", r"partner.*desc", r"reporter.*desc", r"partneriso", r"partnerdesc", r"partner_desc"],
    "value": [r"value", r"fob.*value", r"cif.*value", r"primary.*value", r"amount", r"usd", r"export.*value", r"fobvalue", r"primaryvalue"],
    "quantity": [r"qty", r"quantity", r"tons", r"kg", r"volume", r"netwgt", r"grosswgt", r"qty_tons"],
    "year": [r"year", r"period", r"date", r"ref.*year", r"refyear"],
    "trade_flow": [r"flow", r"direction", r"trade.*flow", r"flowdesc", r"flowdesc"]
}

COUNTRY_MAP_ISO = {
    "ALGERIA": "DZA", "ANGOLA": "ANG", "ARGENTINA": "ARG", "AUSTRALIA": "AUS",
    "AUSTRIA": "AUT", "BAHRAIN": "BHR", "BANGLADESH": "BGD", "BANGLADESH PR": "BGD",
    "BELGIUM": "BEL", "BENIN": "BEN", "BHUTAN": "BTN", "BRAZIL": "BRA",
    "BULGARIA": "BGR", "CAMEROON": "CMR", "CANADA": "CAN", "CHILE": "CHL",
    "CHINA": "CHN", "CHINA P RP": "CHN", "COLOMBIA": "COL", "CONGO": "COG",
    "CONGO D. REP.": "COD", "COTE D' IVOIRE": "CIV", "DENMARK": "DNK",
    "EGYPT": "EGY", "ETHIOPIA": "ETH", "FRANCE": "FRA", "GERMANY": "DEU",
    "GHANA": "GHA", "GREECE": "GRC", "GUINEA": "GIN", "HONG KONG": "HKG",
    "INDIA": "IND", "INDONESIA": "IDN", "IRAQ": "IRQ", "IRELAND": "IRL",
    "ITALY": "ITA", "JAPAN": "JPN", "KOREA": "KOR", "KOREA RP": "KOR",
    "LUXEMBOURG": "LUX", "MALAYSIA": "MYS", "MALDIVES": "MDV", "MAURITIUS": "MUS",
    "MEXICO": "MEX", "MYANMAR": "MMR", "NEPAL": "NPL", "NETHERLAND": "NLD",
    "NETHERLANDS": "NLD", "NEW ZEALAND": "NZL", "NIGERIA": "NGA", "NORWAY": "NOR",
    "OMAN": "OMN", "PAKISTAN": "PAK", "PHILIPPINES": "PHL", "POLAND": "POL",
    "PORTUGAL": "PRT", "SAUDI ARAB": "SAU", "SAUDI ARABIA": "SAU", "SINGAPORE": "SGP",
    "SOUTH AFRICA": "ZAF", "SPAIN": "ESP", "SRI LANKA": "LKA", "SRI LANKA DSR": "LKA",
    "SWEDEN": "SWE", "SWITZERLAND": "CHE", "TAIWAN": "TWN", "TANZANIA": "TZA",
    "TANZANIA REP": "TZA", "THAILAND": "THA", "TURKEY": "TUR", "U ARAB EMTS": "ARE",
    "UAE": "ARE", "U K": "GBR", "UNITED KINGDOM": "GBR", "U S A": "USA", "USA": "USA",
    "UNITED STATES": "USA", "VIETNAM": "VNM", "VIETNAM SOC REP": "VNM"
}

def normalize_country(country_name: str) -> str:
    """Normalizes country name string to clean standard and retrieves ISO3 code."""
    if not isinstance(country_name, str):
        return "UNKNOWN"
    cleaned = country_name.strip().upper()
    # Remove extra spaces, brackets or double quotes
    cleaned = re.sub(r'["\']', '', cleaned)
    # Check map
    if cleaned in COUNTRY_MAP_ISO:
        return cleaned
    
    # Try fuzzy matching
    for key, iso in COUNTRY_MAP_ISO.items():
        if key in cleaned or cleaned in key:
            return key
            
    return cleaned

def get_country_iso3(country_name: str) -> str:
    """Gets ISO alpha-3 code of a country."""
    normalized = normalize_country(country_name)
    return COUNTRY_MAP_ISO.get(normalized, "W00") # Default to World code if not found

def detect_and_normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Auto-detects and normalizes dataframe columns into standard columns:
    hs_code, commodity_name, country, value, quantity, year, trade_flow
    """
    cols = df.columns.tolist()
    normalized_mapping = {}
    
    # Double check if this is the double header export style (from TradeStat-Eidb)
    # If the first row contains column headers like 'Country / Region' and second row contains numeric labels
    is_tradestat_eidb = False
    
    # Check if first row contains column headers and we need to skip a row
    for i, col in enumerate(cols):
        if "TradeStat->Eidb" in str(col):
            is_tradestat_eidb = True
            break

    if is_tradestat_eidb:
        logger.info("Detected TradeStat EIDB Excel format. Custom processing triggered.")
        # Row 1 has headers: 'S.No.', 'Country / Region', '2023-2024', '2024-2025', '%Growth', '2023-2024', '2024-2025', '%Growth'
        # The first set of 2023-2024, 2024-2025 are Values in US $ Millions
        # The second set of 2023-2024, 2024-2025 are Quantity values
        headers = df.iloc[0].tolist()
        
        # Build structured data
        processed_rows = []
        for idx in range(1, len(df)):
            row = df.iloc[idx].tolist()
            country = row[1]
            if not country or str(country).strip().upper() in ["TOTAL", "S.NO.", "COUNTRY / REGION"]:
                continue
            
            # Value in USD: multiply Millions by 1,000,000
            val_23_24 = float(row[2]) * 1_000_000 if not pd.isna(row[2]) and str(row[2]).replace('.','').isdigit() else 0.0
            val_24_25 = float(row[3]) * 1_000_000 if not pd.isna(row[3]) and str(row[3]).replace('.','').isdigit() else 0.0
            
            # Quantity in tons
            qty_23_24 = float(row[5]) if not pd.isna(row[5]) and str(row[5]).replace('.','').isdigit() else 0.0
            qty_24_25 = float(row[6]) if not pd.isna(row[6]) and str(row[6]).replace('.','').isdigit() else 0.0
            
            if val_23_24 > 0 or qty_23_24 > 0:
                processed_rows.append({
                    "hs_code": "5201", # Seed HS Code
                    "commodity_name": "Cotton; not carded or combed",
                    "country": str(country).strip(),
                    "value": val_23_24,
                    "quantity": qty_23_24,
                    "year": 2023,
                    "trade_flow": "Export"
                })
            if val_24_25 > 0 or qty_24_25 > 0:
                processed_rows.append({
                    "hs_code": "5201",
                    "commodity_name": "Cotton; not carded or combed",
                    "country": str(country).strip(),
                    "value": val_24_25,
                    "quantity": qty_24_25,
                    "year": 2024,
                    "trade_flow": "Export"
                })
        
        return pd.DataFrame(processed_rows)
        
    # Standard column mapping using regex
    for col in cols:
        col_str = str(col).lower().replace("_", "").replace("-", "").strip()
        matched = False
        for std_col, patterns in COLUMN_PATTERNS.items():
            for pattern in patterns:
                if re.match(pattern, col_str) or pattern == col_str:
                    normalized_mapping[col] = std_col
                    matched = True
                    break
            if matched:
                break
                
    if normalized_mapping:
        df_new = df.rename(columns=normalized_mapping)
        # Keep only recognized columns
        keep_cols = [c for c in df_new.columns if c in COLUMN_PATTERNS.keys()]
        df_new = df_new[keep_cols]
        # Deduplicate column names by keeping only the first one
        df_new = df_new.loc[:, ~df_new.columns.duplicated()]
        return df_new
        
    return df

def load_dataset_file(filepath: Path) -> pd.DataFrame:
    """Loads a CSV, XLSX, or JSON file, detects its columns, and normalizes it."""
    ext = filepath.suffix.lower()
    df = pd.DataFrame()
    try:
        if ext == ".csv":
            df = pd.read_csv(filepath)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(filepath)
        elif ext == ".json":
            df = pd.read_json(filepath)
        else:
            logger.warning(f"Unsupported file type for {filepath}")
            return pd.DataFrame()
            
        if df.empty:
            return df
            
        # Clean dataframe columns and normalize
        df = detect_and_normalize_columns(df)
        
        # Basic validation: ensure we have country column, fill default values
        if "country" not in df.columns:
            logger.warning(f"No country column detected in {filepath}")
            # Try to see if there is any column that might represent country
            if len(df.columns) > 1:
                df = df.rename(columns={df.columns[1]: "country"})
            else:
                return pd.DataFrame()
                
        # Fill missing values and ensure type safety
        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0.0)
        else:
            df["value"] = 0.0
            
        if "quantity" in df.columns:
            df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0.0)
        else:
            df["quantity"] = 0.0
            
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(datetime.datetime.now().year)
            df["year"] = df["year"].astype(int)
        else:
            df["year"] = datetime.datetime.now().year
            
        if "hs_code" in df.columns:
            df["hs_code"] = df["hs_code"].astype(str).str.strip()
        else:
            df["hs_code"] = "5201"
            
        if "commodity_name" in df.columns:
            df["commodity_name"] = df["commodity_name"].astype(str).str.strip()
        else:
            df["commodity_name"] = "cotton"
            
        if "trade_flow" in df.columns:
            df["trade_flow"] = df["trade_flow"].astype(str).str.strip().str.capitalize()
        else:
            df["trade_flow"] = "Export"
            
        # Clean and standardise country names
        df["country"] = df["country"].astype(str).apply(normalize_country)
        df = df[df["country"] != "TOTAL"]
        
        # Deduplicate
        group_cols = ["hs_code", "country", "year", "trade_flow"]
        df = df.groupby(group_cols, as_index=False).agg({
            "commodity_name": "first",
            "value": "sum",
            "quantity": "sum"
        })
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading and normalizing file {filepath}: {e}", exc_info=True)
        return pd.DataFrame()

def load_all_datasets_in_dir(directory: Path) -> pd.DataFrame:
    """Loads and aggregates all supported data files in a directory."""
    files = []
    for ext in ["*.csv", "*.xlsx", "*.xls", "*.json"]:
        files.extend(glob.glob(str(directory / ext)))
        
    dfs = []
    for filepath in files:
        df = load_dataset_file(Path(filepath))
        if not df.empty:
            dfs.append(df)
            
    if not dfs:
        return pd.DataFrame()
        
    combined = pd.concat(dfs, ignore_index=True)
    
    # Re-aggregate grouped keys
    group_cols = ["hs_code", "country", "year", "trade_flow"]
    combined = combined.groupby(group_cols, as_index=False).agg({
        "commodity_name": "first",
        "value": "sum",
        "quantity": "sum"
    })
    
    logger.info(f"Aggregated {len(combined)} records from {len(files)} files in {directory}")
    return combined
