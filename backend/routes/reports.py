import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from backend.database.connection import get_db
from backend.database import models

logger = logging.getLogger("trade_intel.routes.reports")

router = APIRouter(tags=["Reports"])

@router.get("/reports/{analysis_id}", response_model=Dict[str, Any])
def get_report_by_id(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieves full aggregated analysis scores, forecasts, and agent results for a specific run ID."""
    result = db.query(models.AnalysisResult).filter(models.AnalysisResult.id == analysis_id).first()
    if not result:
        raise HTTPException(status_code=404, detail=f"Report with ID '{analysis_id}' not found.")
        
    # Get associated tables
    scores = db.query(models.CountryScore).filter(models.CountryScore.analysis_id == analysis_id).all()
    forecasts = db.query(models.Forecast).filter(models.Forecast.analysis_id == analysis_id).all()
    logistics = db.query(models.LogisticsData).filter(models.LogisticsData.analysis_id == analysis_id).all()
    suppliers = db.query(models.SupplierAnalysis).filter(models.SupplierAnalysis.analysis_id == analysis_id).all()
    tariffs = db.query(models.TariffData).filter(models.TariffData.analysis_id == analysis_id).all()
    risks = db.query(models.RiskData).filter(models.RiskData.analysis_id == analysis_id).all()
    
    # Structure country data
    countries_data = []
    for s in scores:
        country = s.country
        
        # Match routes
        route_item = next((l for l in logistics if l.country == country), None)
        route_data = {
            "origin_port": route_item.origin_port,
            "destination_port": route_item.destination_port,
            "distance_km": route_item.distance_km,
            "transit_days": route_item.transit_days,
            "cost_per_ton": route_item.cost_per_ton
        } if route_item else {}
        
        # Match risk
        risk_item = next((r for r in risks if r.country == country), None)
        risk_data = {
            "political_stability": risk_item.political_stability,
            "inflation_rate": risk_item.inflation_rate,
            "risk_score": risk_item.overall_risk_score
        } if risk_item else {}
        
        # Match tariff
        tariff_item = next((t for t in tariffs if t.country == country), None)
        tariff_data = {
            "tariff_pct": tariff_item.tariff_pct,
            "tariff_severity": tariff_item.trade_barrier_severity,
            "tariff_score": tariff_item.score
        } if tariff_item else {}
        
        # Match forecasts
        country_forecasts = {}
        country_history = {}
        for f in forecasts:
            if f.country == country:
                if f.is_forecast == 1:
                    country_forecasts[f.year] = f.value
                else:
                    country_history[f.year] = f.value
                    
        countries_data.append({
            "country": country,
            "rank": s.rank,
            "final_score": s.final_score,
            "market_score": s.market_score,
            "import_volume": s.import_volume,
            "import_value": s.import_value,
            "demand_score": s.demand_score,
            "price_score": s.price_score,
            "currency_score": s.currency_score,
            "tariff_score": s.tariff_score,
            "logistics_score": s.logistics_score,
            "risk_score": s.risk_score,
            "supplier_score": s.supplier_score,
            "expected_profit_usd": s.expected_profit_usd,
            "predicted_demand_growth_pct": s.predicted_demand_growth_pct,
            "shipping_cost_per_ton": s.shipping_cost_per_ton,
            "transit_days": s.transit_days,
            "tariff_pct": s.tariff_pct,
            "currency_risk_level": s.currency_risk_level,
            "political_stability_score": s.political_stability_score,
            "inflation_rate_pct": s.inflation_rate_pct,
            "logistics_details": route_data,
            "risk_details": risk_data,
            "tariff_details": tariff_data,
            "trade_volume_history": country_history,
            "trade_volume_forecast": country_forecasts
        })
        
    # Global price forecasts
    global_price_history = {f.year: f.value for f in forecasts if f.country == "Global" and f.indicator_type == "price_usd_per_ton" and f.is_forecast == 0}
    global_price_forecast = {f.year: f.value for f in forecasts if f.country == "Global" and f.indicator_type == "price_usd_per_ton" and f.is_forecast == 1}
    
    # Suppliers
    suppliers_list = [
        {
            "name": s.supplier_name,
            "country": s.country,
            "capacity_tons": s.capacity_tons,
            "rating": s.rating,
            "cost_competitiveness": s.cost_competitiveness,
            "overall_score": s.overall_score,
            "address": s.address,
            "contact_no": s.contact_no,
            "email": s.email,
            "city_state": s.city_state
        }
        for s in suppliers
    ]
    
    # Sort countries by rank
    countries_data = sorted(countries_data, key=lambda x: x["rank"])
    
    return {
        "id": result.id,
        "hs_code": result.hs_code,
        "commodity_name": result.commodity_name,
        "quantity_tons": result.quantity_tons,
        "best_export_market": result.best_export_market,
        "expected_profit_usd": result.expected_profit_usd,
        "risk_level": result.risk_level,
        "final_ai_score": result.final_ai_score,
        "recommendations": result.recommendations,
        "shap_explainability": result.shap_explainability,
        "created_at": result.created_at,
        "countries": countries_data,
        "global_pricing": {
            "price_history": global_price_history,
            "price_forecast": global_price_forecast
        },
        "suppliers": suppliers_list
    }

@router.get("/reports", response_model=List[Dict[str, Any]])
def list_all_reports(db: Session = Depends(get_db)):
    """Lists summary of all executed trade analysis reports."""
    results = db.query(models.AnalysisResult).order_by(models.AnalysisResult.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "hs_code": r.hs_code,
            "commodity_name": r.commodity_name,
            "quantity_tons": r.quantity_tons,
            "best_export_market": r.best_export_market,
            "expected_profit_usd": r.expected_profit_usd,
            "final_ai_score": r.final_ai_score,
            "created_at": r.created_at
        }
        for r in results
    ]
