from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.services.logistics_service import LogisticsService


class LogisticsAgent(BaseAgent):
    """Calculates shipping routes, transit times, and per-ton costs from India to each target market."""

    def __init__(self):
        super().__init__("Logistics Agent")

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        qty_tons = float(inputs.get("quantity_tons", 50.0))
        self.log_step(f"Starting logistics and shipping cost analysis for {qty_tons} tons...", progress=10.0)

        top_markets, countries = self.get_target_countries(context)
        logistics_records = {}

        for idx, country in enumerate(countries):
            pct = 20.0 + (float(idx) / len(countries)) * 70.0
            self.log_step(f"Calculating route transit and container pricing to {country}...", progress=pct)

            route_data = LogisticsService.calculate_route(country)
            cost_per_ton = route_data["cost_per_ton"]
            total_shipping_cost = cost_per_ton * qty_tons

            logistics_records[country] = {
                "origin_port": route_data["origin_port"],
                "destination_port": route_data["destination_port"],
                "distance_km": route_data["distance_km"],
                "transit_days": route_data["transit_days"],
                "cost_per_ton": cost_per_ton,
                "total_shipping_cost_usd": round(total_shipping_cost, 2),
                "logistics_score": route_data["logistics_score"]
            }

        overall_score = round(sum(l["logistics_score"] for l in logistics_records.values()) / len(logistics_records), 2) if logistics_records else 0.5

        output = {
            "logistics_records": logistics_records,
            "logistics_score": overall_score
        }

        self.log_step("Logistics routing and transit cost estimation completed.", progress=100.0)
        return output
