import logging
from typing import Dict, Any
from backend.agents.base_agent import BaseAgent
from backend.ml.pipelines import compute_explainability
from backend.services.llm_service import LLMService

# Weighted importance of each agent's score in the final decision (sums to 1.0).
# Market (25%) and Demand (20%) lead since market size and growth potential
# matter most; Price (15%) next; the remaining four factors (10% each) are
# supporting considerations.
DEFAULT_WEIGHTS = {
    "market": 0.25,
    "demand": 0.20,
    "price": 0.15,
    "currency": 0.10,
    "tariff": 0.10,
    "logistics": 0.10,
    "risk": 0.10
}


class DecisionAgent(BaseAgent):
    """
    Consolidates outputs from all 8 specialized agents into a single
    weighted ranking, estimates profit per country, and explains each
    recommendation - both via known-weight feature importance and,
    for the top 3 countries, an LLM-synthesized narrative built strictly
    from the numbers computed here (with a template fallback if that
    call is unavailable or fails).
    """

    def __init__(self):
        super().__init__("Decision Agent")

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        qty_tons = float(inputs.get("quantity_tons", 50.0))
        commodity = str(inputs.get("commodity_name", "cotton")).capitalize()

        self.log_step("Starting multi-agent weighted scoring and consolidation...", progress=10.0)

        market_agent = context.get("market_agent", {})
        demand_agent = context.get("demand_agent", {})
        price_agent = context.get("price_agent", {})
        currency_agent = context.get("currency_agent", {})
        tariff_agent = context.get("tariff_agent", {})
        logistics_agent = context.get("logistics_agent", {})
        risk_agent = context.get("risk_agent", {})
        supplier_agent = context.get("supplier_agent", {})

        top_markets_market = market_agent.get("top_markets", [])
        if not top_markets_market:
            raise ValueError("No target countries found in market analysis results.")
        countries = [m["country"] for m in top_markets_market]

        # These three are global (same across all candidate countries)
        price_per_ton = price_agent.get("predicted_price_usd_per_ton", 2200.0)
        price_score = price_agent.get("price_score", 0.70)
        supplier_score = supplier_agent.get("supplier_score", 0.80)

        country_consolidated = []
        self.log_step("Running scoring models and profit projections...", progress=40.0)

        for country in countries:
            m_record = next((m for m in top_markets_market if m["country"] == country), {})
            m_score = m_record.get("market_score", 0.5)
            import_volume = m_record.get("import_volume", 0.0)
            import_value = m_record.get("import_value", 0.0)

            d_data = demand_agent.get("demand_scores", {}).get(country, {})
            d_score = d_data.get("demand_score", 0.5)
            gdp_growth = d_data.get("gdp_growth", 2.0)

            c_data = currency_agent.get("currency_scores", {}).get(country, {})
            c_score = c_data.get("currency_score", 0.5)
            c_risk = c_data.get("currency_risk", "Medium")

            t_data = tariff_agent.get("tariff_records", {}).get(country, {})
            t_score = t_data.get("tariff_score", 0.5)
            tariff_pct = t_data.get("tariff_pct", 5.0)

            l_data = logistics_agent.get("logistics_records", {}).get(country, {})
            l_score = l_data.get("logistics_score", 0.5)
            ship_cost_ton = l_data.get("cost_per_ton", 150.0)
            transit_days = l_data.get("transit_days", 15.0)

            r_data = risk_agent.get("risk_records", {}).get(country, {})
            r_score = r_data.get("risk_score", 0.5)
            r_level = r_data.get("overall_risk_level", "Medium")
            ps_index = r_data.get("political_stability_index", 0.0)
            inf_rate = r_data.get("inflation_rate_pct", 3.0)

            final_score = (
                DEFAULT_WEIGHTS["market"] * m_score +
                DEFAULT_WEIGHTS["demand"] * d_score +
                DEFAULT_WEIGHTS["price"] * price_score +
                DEFAULT_WEIGHTS["currency"] * c_score +
                DEFAULT_WEIGHTS["tariff"] * t_score +
                DEFAULT_WEIGHTS["logistics"] * l_score +
                DEFAULT_WEIGHTS["risk"] * r_score
            )

            # Revenue - shipping - tariff = expected profit
            revenue = price_per_ton * qty_tons
            shipping_cost = ship_cost_ton * qty_tons
            tariff_cost = (tariff_pct / 100.0) * revenue
            expected_profit = revenue - shipping_cost - tariff_cost

            country_consolidated.append({
                "country": country,
                "market_score": m_score,
                "import_volume": import_volume,
                "import_value": import_value,
                "demand_score": d_score,
                "price_score": price_score,
                "currency_score": c_score,
                "tariff_score": t_score,
                "logistics_score": l_score,
                "risk_score": r_score,
                "supplier_score": supplier_score,
                "final_score": round(final_score, 3),
                "predicted_demand_growth_pct": gdp_growth,
                "shipping_cost_per_ton": ship_cost_ton,
                "transit_days": transit_days,
                "tariff_pct": tariff_pct,
                "currency_risk_level": c_risk,
                "risk_level": r_level,
                "political_stability_score": ps_index,
                "inflation_rate_pct": inf_rate,
                "expected_profit_usd": round(expected_profit, 2)
            })

        country_consolidated = sorted(country_consolidated, key=lambda x: x["final_score"], reverse=True)
        for idx, item in enumerate(country_consolidated):
            item["rank"] = idx + 1

        best_item = country_consolidated[0] if country_consolidated else {}
        best_country = best_item.get("country", "Unknown")

        self.log_step("Computing factor attributions and global feature importance...", progress=70.0)

        # Local attributions: weight * (value - baseline) per factor, per country.
        # Global importance: DEFAULT_WEIGHTS, normalized - final_score is by
        # construction a weighted sum of them, so no model-fitting is needed;
        # the weights already are the answer.
        explain_results = compute_explainability(country_consolidated, DEFAULT_WEIGHTS)

        # Deterministic, template-based reasoning for the top 3 countries.
        # This is the guaranteed fallback if LLM synthesis below is
        # unavailable or fails - never removed, only optionally overwritten.
        recommendations = []
        for rank_idx, item in enumerate(country_consolidated[:3]):
            country_name = item["country"]
            profit = item["expected_profit_usd"]
            score = item["final_score"]

            recs = []
            if item["tariff_pct"] == 0:
                recs.append("Zero tariff barriers under bilateral agreements / GSP status.")
            elif item["tariff_pct"] > 10.0:
                recs.append(f"Requires tariff mitigation due to high import duty of {item['tariff_pct']}%.")

            if item["transit_days"] < 10:
                recs.append(f"Highly optimized logistics with transit time of only {item['transit_days']} days.")
            elif item["transit_days"] > 25:
                recs.append(f"Logistics risk due to longer transit time of {item['transit_days']} days.")

            if item["political_stability_score"] < -0.5:
                recs.append("Monitor closely due to lower political stability index.")

            recommendations.append({
                "country": country_name,
                "rank": rank_idx + 1,
                "reasoning": (
                    f"{country_name} ranks #{rank_idx+1} with an AI Score of {score:.2f}. "
                    f"Expected export profit is ${profit:,.2f}. "
                    f"Primary drivers: market volume score ({item['market_score']:.2f}) and demand growth ({item['predicted_demand_growth_pct']}% GDP). "
                    f"Risk level is {item['political_stability_score']:.2f} WGI stability."
                ),
                "recs": recs
            })

        # Attempt to replace the templated reasoning above with an
        # LLM-generated narrative synthesized from the same computed
        # numbers. This cannot alter any score, rank, or figure - it's a
        # synthesis step only. If unconfigured or the call fails, the
        # templated reasoning above is left untouched.
        self.log_step("Requesting LLM narrative synthesis for top recommendations...", progress=80.0)
        narratives = await LLMService.generate_narratives(country_consolidated[:3])
        if narratives:
            for rec in recommendations:
                if rec["country"] in narratives:
                    rec["reasoning"] = narratives[rec["country"]]
            self.log_step("LLM narrative synthesis applied.", progress=85.0)
        else:
            self.log_step("LLM synthesis unavailable; using template-based reasoning.", progress=85.0, level=logging.WARNING)

        output = {
            "best_export_market": best_country,
            "top_markets": country_consolidated,
            "predicted_demand_growth": f"{best_item.get('predicted_demand_growth_pct', 0.0):.1f}% GDP Growth",
            "shipping_cost_per_ton": best_item.get("shipping_cost_per_ton", 0.0),
            "currency_risk": best_item.get("currency_risk_level", "Medium"),
            "tariff_barrier": f"{best_item.get('tariff_pct', 0.0):.1f}% import duty",
            "supplier_confidence": supplier_score,
            "final_ai_score": best_item.get("final_score", 0.0),
            "expected_profit_usd": best_item.get("expected_profit_usd", 0.0),
            "risk_level": best_item.get("risk_level", "Medium"),
            "recommendations": recommendations,
            "shap_explainability": explain_results
        }

        self.log_step(f"Consolidation complete. Identified {best_country} as the top export opportunity.", progress=100.0)
        return output
