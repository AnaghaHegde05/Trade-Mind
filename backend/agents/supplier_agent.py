import pandas as pd
from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.config.settings import settings

# Standardizes messy/inconsistent state-name spellings and abbreviations
# found in the raw address data
STATES_MAPPING = {
    "TAMILNADU": "Tamil Nadu",
    "TAMIL NADU": "Tamil Nadu",
    "MAHARASHTRA": "Maharashtra",
    "MAHARASHT RA": "Maharashtra",  # typo present in source data
    "UTTAR PRADESH": "Uttar Pradesh",
    "UTTARPRADESH": "Uttar Pradesh",
    "GUJARAT": "Gujarat",
    "GUJRAT": "Gujarat",  # misspelling present in source data
    "KERALA": "Kerala",
    "KARNATAKA": "Karnataka",
    "ANDHRA PRADESH": "Andhra Pradesh",
    "TELANGANA": "Telangana",
    "WEST BENGAL": "West Bengal",
    "PUNJAB": "Punjab",
    "HARYANA": "Haryana",
    "RAJASTHAN": "Rajasthan",
    "MADHYA PRADESH": "Madhya Pradesh"
}


def _extract_state(val) -> str:
    """Extracts a standardized state name from a messy address field."""
    if not isinstance(val, str):
        return "Unknown"

    val_upper = val.upper().strip()
    for key, display in STATES_MAPPING.items():
        if key in val_upper:
            return display

    # Fallback: take the text after the last hyphen and strip digits (postal codes)
    parts = val_upper.split('-')
    if len(parts) > 1:
        after_hyphen = parts[-1].strip()
        cleaned = "".join([c for c in after_hyphen if not c.isdigit()]).strip()
        if cleaned:
            return cleaned.title()

    return "Other"


class SupplierAgent(BaseAgent):
    """
    Loads the domestic supplier registry and assesses regional supply
    ecosystem strength - identifying which states have the densest
    clusters of exporters for the given commodity.
    """

    def __init__(self):
        super().__init__("Supplier Agent")

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        commodity = str(inputs.get("commodity_name", "cotton")).lower().strip()
        self.log_step(f"Starting real supplier intelligence analysis for: {commodity}", progress=10.0)

        suppliers_file = settings.SUPPLIERS_DATASET_DIR / "cotton_suppliers.csv"
        if not suppliers_file.exists():
            raise FileNotFoundError(f"Suppliers database not found at: {suppliers_file}")

        df = pd.read_csv(suppliers_file)
        self.log_step(f"Loaded {len(df)} real textile exporters from registry.", progress=30.0)

        df["state"] = df["City-Pin-State"].apply(_extract_state)

        state_counts = df["state"].value_counts().to_dict()
        total_suppliers = len(df)

        regions_density = {}
        top_clusters = []
        for state, count in state_counts.items():
            density_pct = round((count / total_suppliers) * 100, 2)
            regions_density[state] = {"count": int(count), "density_pct": density_pct}
            top_clusters.append({"region": state, "count": int(count), "density_pct": density_pct})

        self.log_step(f"Identified {len(regions_density)} exporter regions. Top cluster: {top_clusters[0]['region'] if top_clusters else 'None'}.", progress=60.0)

        # We only fabricate fields we cannot derive from anything real.
        # capacity_tons, rating, cost_competitiveness are left as None -
        # missing data, not a fake number. overall_score is NOT a made-up
        # constant: it's the supplier's region's share of the total
        # supplier base, normalized against the largest cluster - a
        # supplier sitting in a dense manufacturing hub scores higher
        # than one in a region with few peers, a real (if simple) signal
        # derived from data we actually have.
        max_density_pct = max((d["density_pct"] for d in regions_density.values()), default=1.0) or 1.0
        supplier_list = []
        for idx, row in df.iterrows():
            state = row["state"]
            cluster_density_pct = regions_density.get(state, {}).get("density_pct", 0.0)
            regional_cluster_score = round(cluster_density_pct / max_density_pct, 2)
            supplier_list.append({
                "supplier_name": str(row.get("Name", f"Supplier #{idx}")),
                "country": "INDIA",
                "capacity_tons": None,
                "rating": None,
                "cost_competitiveness": None,
                "overall_score": regional_cluster_score,
                "address": str(row.get("Address", "")).strip(),
                "contact_no": str(row.get("Contact No.", "")).strip(),
                "email": str(row.get("Email", "")).strip(),
                "city_state": str(row.get("City-Pin-State", "")).strip()
            })

        # Best-clustered suppliers first, since downstream consumers (DB
        # persistence, frontend) only display/store a capped subset.
        supplier_list.sort(key=lambda s: s["overall_score"], reverse=True)

        # 50 suppliers assumed as the max-score threshold; fewer -> proportionally lower
        overall_supplier_score = round(min(1.0, total_suppliers / 50.0), 2)

        output = {
            "suppliers": supplier_list,
            "supplier_score": overall_supplier_score,
            "regions_density": regions_density,
            "top_clusters": top_clusters
        }

        self.log_step(f"Supplier intelligence complete. Base ecosystem score: {overall_supplier_score}.", progress=100.0)
        return output
