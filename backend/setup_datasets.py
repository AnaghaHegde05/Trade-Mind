"""
One-time local developer utility — NOT part of the shipped application.

Copies raw source datasets from a local `data/` directory (outside this
repo, gitignored, never committed) into `backend/datasets/`, which is what
the running app actually reads from.

This script will not run out of the box: it expects `data/` to exist at
the project root, populated with the original raw files (see the
`mappings` list below for expected paths). That directory is not included
in this repository. Use this only if you have the original raw dataset
files and want to regenerate `backend/datasets/` from scratch; otherwise
ignore it — the app ships with `backend/datasets/` already populated.
"""

import os
import shutil
from pathlib import Path

def setup_datasets():
    base_dir = Path(__file__).resolve().parent
    project_root = base_dir.parent
    raw_data_dir = project_root / "data"
    target_datasets_dir = base_dir / "datasets"

    print(f"Base Dir: {base_dir}")
    print(f"Raw Data Dir: {raw_data_dir}")
    print(f"Target Datasets Dir: {target_datasets_dir}")

    # Define source and target mappings
    mappings = [
        # Market
        (raw_data_dir / "market" / "TradeData_4_29_2026_9_4_45.csv", target_datasets_dir / "market" / "TradeData_4_29_2026_9_4_45.csv"),
        (raw_data_dir / "market" / "TradeStat-Eidb-Export-Commodity-wise-all-countries.xlsx", target_datasets_dir / "market" / "TradeStat-Eidb-Export-Commodity-wise-all-countries.xlsx"),
        
        # Pricing
        (raw_data_dir / "pricing" / "CMO-Historical-Data-Monthly.xlsx", target_datasets_dir / "pricing" / "cotton_prices_worldbank.xlsx"),
        
        # Logistics
        (raw_data_dir / "logistic" / "world_bank_lpi.csv" / "LPICSV.csv", target_datasets_dir / "logistics" / "world_bank_lpi.csv"),
        (raw_data_dir / "logistic" / "world_ports.csv.csv", target_datasets_dir / "logistics" / "world_ports.csv"),
        
        # Suppliers
        (raw_data_dir / "supplier" / "cotton_suppliers.csv", target_datasets_dir / "suppliers" / "cotton_suppliers.csv")
    ]

    for src, dest in mappings:
        if not src.exists():
            print(f"Warning: Source file {src} does not exist!")
            continue
        
        # Ensure target parent directory exists
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(src, dest)
        print(f"Copied: {src} -> {dest}")

if __name__ == "__main__":
    setup_datasets()
