import uuid
import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from backend.database.connection import get_db
from backend.database import models
from backend.orchestrator.runner import run_trade_analysis
from backend.utils.auth import verify_api_key

logger = logging.getLogger("trade_intel.routes.analysis")

router = APIRouter(tags=["Analysis"])

class AnalysisRequest(BaseModel):
    hs_code: str = Field(..., example="5201", description="4-digit HS code")
    quantity_tons: float = Field(..., example=50.0, description="Quantity in Metric Tons")
    commodity_name: str = Field(..., example="cotton", description="Name of the commodity")

class AnalysisStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None

@router.post("/analyze", response_model=Dict[str, Any])
async def trigger_analysis(req: AnalysisRequest, _auth: None = Depends(verify_api_key)):
    """Triggers multi-agent analysis asynchronously. Falls back to local runner if Celery is down."""
    task_id = str(uuid.uuid4())
    logger.info(f"Triggering analysis for {req.commodity_name} (HS {req.hs_code}), Task ID: {task_id}")
    
    # Try Celery first
    try:
        # Check if Redis is running before delay
        from backend.cache.redis_client import redis_cache
        if redis_cache.client is not None:
            # Dynamically import celery task
            from backend.orchestrator.tasks import execute_trade_intelligence_analysis
            execute_trade_intelligence_analysis.apply_async(
                args=[req.hs_code, req.quantity_tons, req.commodity_name],
                task_id=task_id
            )
            logger.info(f"Analysis task queued in Celery broker with ID: {task_id}")
            return {"task_id": task_id, "status": "QUEUED", "broker": "celery"}
    except Exception as e:
        logger.warning(f"Failed to queue task in Celery: {e}. Executing in-process background task...")
        
    # Local Async Fallback
    async def run_local():
        try:
            await run_trade_analysis(req.hs_code, req.quantity_tons, req.commodity_name, task_id=task_id)
        except Exception as e:
            logger.error(f"Local in-process analysis task {task_id} failed: {e}", exc_info=True)
            
    asyncio.create_task(run_local())
    return {"task_id": task_id, "status": "STARTED", "broker": "local_async"}

@router.get("/market-analysis", response_model=Dict[str, Any])
def get_latest_market_analysis(db: Session = Depends(get_db)):
    """Retrieves the country ranking and market stats of the latest run."""
    latest = db.query(models.AnalysisResult).order_by(models.AnalysisResult.created_at.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No analyses found.")
        
    country_scores = db.query(models.CountryScore).filter(models.CountryScore.analysis_id == latest.id)
    scores_list = [
        {
            "country": c.country,
            "final_score": c.final_score,
            "rank": c.rank,
            "expected_profit": c.expected_profit_usd,
            "market_score": c.market_score
        }
        for c in country_scores.all()
    ]
    
    return {
        "analysis_id": latest.id,
        "commodity": latest.commodity_name,
        "hs_code": latest.hs_code,
        "best_country": latest.best_export_market,
        "top_markets": scores_list,
        "created_at": latest.created_at
    }

@router.get("/price-forecast", response_model=Dict[str, Any])
def get_latest_price_forecast(db: Session = Depends(get_db)):
    """Retrieves the price forecast from the latest run."""
    latest = db.query(models.AnalysisResult).order_by(models.AnalysisResult.created_at.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No analyses found.")
        
    price_forecasts = db.query(models.Forecast).filter(
        models.Forecast.analysis_id == latest.id,
        models.Forecast.indicator_type == "price_usd_per_ton"
    ).all()
    
    forecasts = {f.year: f.value for f in price_forecasts if f.is_forecast == 1}
    history = {f.year: f.value for f in price_forecasts if f.is_forecast == 0}
    
    return {
        "analysis_id": latest.id,
        "commodity": latest.commodity_name,
        "price_history": history,
        "price_forecast": forecasts
    }

@router.get("/risk-analysis", response_model=Dict[str, Any])
def get_latest_risk_analysis(db: Session = Depends(get_db)):
    """Retrieves political/economic risk statistics from the latest run."""
    latest = db.query(models.AnalysisResult).order_by(models.AnalysisResult.created_at.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="No analyses found.")
        
    risks = db.query(models.RiskData).filter(models.RiskData.analysis_id == latest.id).all()
    risk_list = [
        {
            "country": r.country,
            "political_stability": r.political_stability,
            "inflation_rate": r.inflation_rate,
            "risk_score": r.overall_risk_score
        }
        for r in risks
    ]
    
    return {
        "analysis_id": latest.id,
        "risk_records": risk_list
    }
