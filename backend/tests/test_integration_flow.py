"""
End-to-end integration test: boots the full FastAPI app in-process,
triggers a real analysis run (all 9 agents, real external API calls),
and verifies the result lands correctly in the database and is
retrievable via the API.

Requires a reachable database (DATABASE_URL from settings/.env - there is
no automatic fallback if it's unreachable; init_db() will raise, see
database/connection.py) and network access to the external APIs the
agents call (World Bank, FRED, WITS, exchange rate API). Not run by
default alongside the fast unit tests; run explicitly with:

    pytest -m integration
"""
import asyncio
import logging
import pytest

pytestmark = pytest.mark.integration

httpx = pytest.importorskip("httpx")

# backend.main -> backend.database.connection calls init_db() at import
# time (not inside a startup event), which raises immediately if
# DATABASE_URL isn't reachable. Guard the import so that simply
# collecting this file - even when deselecting -m "not integration" -
# can't crash the whole test session; skip this module gracefully
# instead if the app can't even be constructed.
try:
    from backend.main import app
    from backend.database.connection import SessionLocal, init_db, Base, engine
    from backend.database import models
except Exception as e:
    pytest.skip(
        f"Skipping integration test - could not import app, database likely unreachable: {e}",
        allow_module_level=True,
    )

logger = logging.getLogger("trade_intel.tests.test_integration_flow")


@pytest.mark.asyncio
async def test_full_analysis_flow_end_to_end():
    init_db()
    Base.metadata.create_all(bind=engine)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        health_response = await client.get("/health")
        assert health_response.status_code == 200, "Health check failed"

        payload = {
            "hs_code": "5201",
            "quantity_tons": 50.0,
            "commodity_name": "cotton"
        }
        response = await client.post("/analyze", json=payload)
        assert response.status_code == 200, "Analyze trigger failed"
        task_id = response.json()["task_id"]

        db = SessionLocal()
        completed = False
        try:
            # Poll for completion - full pipeline (9 agents + real external
            # API calls) can take a while, hence the generous timeout.
            for _ in range(35):
                await asyncio.sleep(1.0)
                result = db.query(models.AnalysisResult).filter(
                    models.AnalysisResult.id == task_id
                ).first()
                if result:
                    completed = True
                    assert result.best_export_market is not None
                    assert result.expected_profit_usd > 0
                    assert result.final_ai_score > 0

                    scores = db.query(models.CountryScore).filter(
                        models.CountryScore.analysis_id == task_id
                    ).all()
                    assert len(scores) > 0, "No country scores saved in database"
                    break

            assert completed, "Analysis task did not complete within timeout"
        finally:
            db.close()

        reports_response = await client.get("/reports")
        assert reports_response.status_code == 200
        assert len(reports_response.json()) > 0

        report_detail = await client.get(f"/reports/{task_id}")
        assert report_detail.status_code == 200
        detail_json = report_detail.json()
        assert detail_json["best_export_market"] is not None
        assert "global_importance" in detail_json["shap_explainability"]
