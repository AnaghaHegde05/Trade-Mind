import uuid
import logging
import asyncio
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.database.connection import SessionLocal
from backend.database import models
from backend.agents.market_agent import MarketAgent
from backend.agents.demand_agent import DemandAgent
from backend.agents.price_agent import PriceAgent
from backend.agents.currency_agent import CurrencyAgent
from backend.agents.tariff_agent import TariffAgent
from backend.agents.logistics_agent import LogisticsAgent
from backend.agents.risk_agent import RiskAgent
from backend.agents.supplier_agent import SupplierAgent
from backend.agents.decision_agent import DecisionAgent

logger = logging.getLogger("trade_intel.orchestrator.runner")

async def run_trade_analysis(
    hs_code: str, 
    quantity_tons: float, 
    commodity_name: str,
    task_id: str = None
) -> Dict[str, Any]:
    """
    Coordinates the parallel asynchronous execution of all agents.
    Saves outputs to SQL database.
    """
    if not task_id:
        task_id = str(uuid.uuid4())
        
    inputs = {
        "hs_code": hs_code,
        "quantity_tons": quantity_tons,
        "commodity_name": commodity_name
    }
    
    context = {}
    
    # Initialize agents
    market_agent = MarketAgent()
    demand_agent = DemandAgent()
    price_agent = PriceAgent()
    currency_agent = CurrencyAgent()
    tariff_agent = TariffAgent()
    logistics_agent = LogisticsAgent()
    risk_agent = RiskAgent()
    supplier_agent = SupplierAgent()
    decision_agent = DecisionAgent()
    
    logger.info(f"Task {task_id}: Initializing trade analysis workflow...", extra={"agent": "System", "progress": 5.0})
    
    # 1. Execute Market Agent first (defines candidate country context)
    try:
        context["market_agent"] = await market_agent.execute(inputs, context)
    except Exception as e:
        logger.error(f"Market Agent failed: {e}", exc_info=True)
        raise e
        
    logger.info(f"Task {task_id}: Market analysis complete. Starting parallel agents...", extra={"agent": "System", "progress": 35.0})
    
    # 2. Run intermediate agents in parallel
    tasks = {
        "demand_agent": demand_agent.execute(inputs, context),
        "price_agent": price_agent.execute(inputs, context),
        "currency_agent": currency_agent.execute(inputs, context),
        "tariff_agent": tariff_agent.execute(inputs, context),
        "logistics_agent": logistics_agent.execute(inputs, context),
        "risk_agent": risk_agent.execute(inputs, context),
        "supplier_agent": supplier_agent.execute(inputs, context)
    }
    
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    
    for key, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            logger.error(f"Agent {key} failed during concurrent execution: {result}", exc_info=True)
            # Failsafe defaults
            context[key] = {}
        else:
            context[key] = result
            
    logger.info(f"Task {task_id}: Parallel agents execution completed. Running Decision Agent...", extra={"agent": "System", "progress": 85.0})
    
    # 3. Run Decision Agent to consolidate scoring and recommendations
    try:
        decision_results = await decision_agent.execute(inputs, context)
        context["decision_agent"] = decision_results
    except Exception as e:
        logger.error(f"Decision Agent failed: {e}", exc_info=True)
        raise e
        
    logger.info(f"Task {task_id}: Decision score complete. Persisting records to database...", extra={"agent": "System", "progress": 95.0})
    
    # 4. Save results to Database
    db: Session = SessionLocal()
    try:
        # Create Analysis Result
        db_result = models.AnalysisResult(
            id=task_id,
            hs_code=hs_code,
            commodity_name=commodity_name,
            quantity_tons=quantity_tons,
            best_export_market=decision_results["best_export_market"],
            expected_profit_usd=decision_results["expected_profit_usd"],
            risk_level=str(decision_results["risk_level"]),
            final_ai_score=decision_results["final_ai_score"],
            recommendations=[r for r in decision_results["recommendations"]],
            shap_explainability=decision_results["shap_explainability"]
        )
        db.add(db_result)
        db.flush() # Flush to bind relationship FKs
        
        # Save Country Scores
        for country_score in decision_results["top_markets"]:
            db_score = models.CountryScore(
                analysis_id=task_id,
                country=country_score["country"],
                market_score=country_score["market_score"],
                import_volume=country_score.get("import_volume", 0.0),
                import_value=country_score.get("import_value", 0.0),
                demand_score=country_score["demand_score"],
                price_score=country_score["price_score"],
                currency_score=country_score["currency_score"],
                tariff_score=country_score["tariff_score"],
                logistics_score=country_score["logistics_score"],
                risk_score=country_score["risk_score"],
                supplier_score=country_score["supplier_score"],
                final_score=country_score["final_score"],
                rank=country_score["rank"],
                predicted_demand_growth_pct=country_score["predicted_demand_growth_pct"],
                shipping_cost_per_ton=country_score["shipping_cost_per_ton"],
                transit_days=country_score["transit_days"],
                tariff_pct=country_score["tariff_pct"],
                currency_risk_level=country_score["currency_risk_level"],
                political_stability_score=country_score["political_stability_score"],
                inflation_rate_pct=country_score["inflation_rate_pct"],
                expected_profit_usd=country_score["expected_profit_usd"]
            )
            db.add(db_score)
            
        # Save Forecasts
        # From Market Agent
        market_forecasts = context["market_agent"].get("market_forecast", {})
        for country, fc_data in market_forecasts.items():
            for yr, val in fc_data.items():
                db_fc = models.Forecast(
                    analysis_id=task_id,
                    country=country,
                    indicator_type="trade_volume_usd",
                    year=yr,
                    value=val,
                    is_forecast=1
                )
                db.add(db_fc)
                
            # Store historical points too
            hist_data = context["market_agent"].get("market_trends", {}).get(country, {}).get("historical", {})
            for yr, val in hist_data.items():
                db_hist = models.Forecast(
                    analysis_id=task_id,
                    country=country,
                    indicator_type="trade_volume_usd",
                    year=yr,
                    value=val,
                    is_forecast=0
                )
                db.add(db_hist)
                
        # From Price Agent
        price_history = context["price_agent"].get("price_history", {})
        for yr, val in price_history.items():
            db_price_hist = models.Forecast(
                analysis_id=task_id,
                country="Global",
                indicator_type="price_usd_per_ton",
                year=yr,
                value=val,
                is_forecast=0
            )
            db.add(db_price_hist)
            
        price_forecast = context["price_agent"].get("price_forecast", {})
        for yr, val in price_forecast.items():
            db_price_fc = models.Forecast(
                analysis_id=task_id,
                country="Global",
                indicator_type="price_usd_per_ton",
                year=yr,
                value=val,
                is_forecast=1
            )
            db.add(db_price_fc)
            
        # Save Logistics Route details
        logistics_recs = context["logistics_agent"].get("logistics_records", {})
        for country, l_rec in logistics_recs.items():
            db_logistics = models.LogisticsData(
                analysis_id=task_id,
                country=country,
                origin_port=l_rec["origin_port"],
                destination_port=l_rec["destination_port"],
                distance_km=l_rec["distance_km"],
                transit_days=l_rec["transit_days"],
                cost_per_ton=l_rec["cost_per_ton"]
            )
            db.add(db_logistics)
            
        # Save Suppliers
        # The supplier registry is a static reference table (same ~157 rows
        # every run) re-scored per-run only by regional cluster density, so
        # persisting the entire table on every /analyze call would grow the
        # DB unboundedly with duplicate data. Only the top-ranked suppliers
        # (already sorted by SupplierAgent, best cluster first) are kept -
        # comfortably more than the top 10 the frontend displays, without
        # re-inserting the full table each time.
        SUPPLIER_PERSIST_LIMIT = 20
        suppliers_list = context["supplier_agent"].get("suppliers", [])[:SUPPLIER_PERSIST_LIMIT]
        for sup in suppliers_list:
            db_sup = models.SupplierAnalysis(
                analysis_id=task_id,
                supplier_name=sup["supplier_name"],
                country=sup["country"],
                capacity_tons=sup["capacity_tons"],
                rating=sup["rating"],
                cost_competitiveness=sup["cost_competitiveness"],
                overall_score=sup["overall_score"],
                address=sup.get("address"),
                contact_no=sup.get("contact_no"),
                email=sup.get("email"),
                city_state=sup.get("city_state")
            )
            db.add(db_sup)
            
        # Save Tariffs
        tariff_records = context["tariff_agent"].get("tariff_records", {})
        for country, t_rec in tariff_records.items():
            db_tariff = models.TariffData(
                analysis_id=task_id,
                country=country,
                hs_code=hs_code,
                tariff_pct=t_rec["tariff_pct"],
                trade_barrier_severity=t_rec["tariff_severity"],
                score=t_rec["tariff_score"]
            )
            db.add(db_tariff)
            
        # Save Risks
        risk_recs = context["risk_agent"].get("risk_records", {})
        for country, r_rec in risk_recs.items():
            db_risk = models.RiskData(
                analysis_id=task_id,
                country=country,
                political_stability=r_rec["political_stability_index"],
                inflation_rate=r_rec["inflation_rate_pct"],
                overall_risk_score=r_rec["risk_score"]
            )
            db.add(db_risk)
            
        db.commit()
        logger.info(f"Task {task_id}: Trade analysis results successfully persisted.", extra={"agent": "System", "progress": 100.0})
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist trade analysis data: {e}", exc_info=True)
        raise e
    finally:
        db.close()
        
    return decision_results
