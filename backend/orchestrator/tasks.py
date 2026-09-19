import asyncio
import logging
from celery.exceptions import MaxRetriesExceededError
from backend.orchestrator.celery_app import celery_app

logger = logging.getLogger("trade_intel.orchestrator.tasks")

@celery_app.task(bind=True, max_retries=3)
def execute_trade_intelligence_analysis(self, hs_code: str, quantity_tons: float, commodity_name: str):
    """
    Celery background worker task wrapping the orchestrator trade intelligence runner.
    """
    task_id = self.request.id
    logger.info(f"Starting Celery background job {task_id} for HS code {hs_code}...")
    
    # Import runner locally to avoid circular dependencies
    from backend.orchestrator.runner import run_trade_analysis
    
    try:
        # Run async function in a sync celery context
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        result = loop.run_until_complete(
            run_trade_analysis(
                hs_code=hs_code, 
                quantity_tons=quantity_tons, 
                commodity_name=commodity_name,
                task_id=task_id
            )
        )
        return {
            "status": "SUCCESS",
            "task_id": task_id,
            "best_country": result.get("best_export_market"),
            "expected_profit": result.get("expected_profit_usd")
        }
    except Exception as e:
        logger.error(f"Celery task {task_id} failed: {e}", exc_info=True)
        # Retry with exponential backoff.
        # self.retry() raises celery.exceptions.Retry internally (by
        # design) to signal the worker to actually retry the task - that
        # exception must propagate, not be swallowed. Only
        # MaxRetriesExceededError (raised once max_retries is exhausted)
        # should be caught here.
        try:
            self.retry(exc=e, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            return {
                "status": "FAILED",
                "task_id": task_id,
                "error": str(e)
            }
