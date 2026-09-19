# AI-Powered Multi-Agent Intelligent Trade Management System

A global trade intelligence platform. The system processes commodity datasets and integrates live indicators from public APIs (World Bank, ExchangeRate) using a multi-agent workflow to rank export opportunities for commodities (primary example: Cotton, HS Code `5201`).

---

## System Architecture

The platform operates using a parallel, multi-agent orchestration architecture:

```
[Next.js 15 Frontend] <--- HTTP & WebSockets ---> [FastAPI Backend Server]
                                                            |
                                               [Orchestrator Runner]
                                                            |
                                        +-------------------+-------------------+
                                        |                   |                   |
                                  [Market Agent]     [Price Agent]       [Logistics Agent]
                                        |                   |                   |
                                  [Demand Agent]     [Currency Agent]    [Supplier Agent]
                                        |                   |                   |
                                  [Risk Agent]       [Tariff Agent]             |
                                        +-------------------+-------------------+
                                                            |
                                                   [Decision Agent]
                                                            |
                                                 [PostgreSQL Database]
```

1. **Market Agent**: The primary source of truth. Parses local files dynamically, maps column schemas, filters by HS code, calculates Compound Annual Growth Rate (CAGR), and ranks countries by volume.
2. **Demand Agent**: Evaluates economic growth. Integrates World Bank Indicators API for real GDP growth and population sizes.
3. **Price Agent**: Forecasts pricing trends. Integrates FRED API / World Bank commodity series to forecast prices over a 3-year horizon.
4. **Currency Agent**: Assesses currency volatility. Fetches live rates from ExchangeRate API and scales adjustments on profit.
5. **Tariff Agent**: Resolves import duties. Uses local tariff tables and WTO schedules to estimate trade barriers.
6. **Logistics Agent**: Calculates sea routing distances, shipping costs, and vessel transit times from Nhava Sheva, India to target ports.
7. **Risk Agent**: Scores country risks. Integrates World Bank political stability indices (`PV.EST`) and inflation metrics.
8. **Supplier Agent**: Matches domestic exporter capacity.
9. **Decision Agent**: Consolidates scores using weighted aggregation and computes per-country factor attributions and global feature importance to explain each recommendation.

> **A note on "agents" and the LLM**: all 9 agents share the same base
> interface, but only the Decision Agent calls an LLM. The other eight
> compute the numbers a financial recommendation depends on (scores,
> tariffs, transit times, forecasts), so they're deterministic and
> reproducible by design — an LLM has no role in generating a number
> that feeds a profit estimate. The Decision Agent's LLM call is a
> synthesis step only: it takes the already-finalized numbers for the
> top 3 countries and writes the natural-language reasoning explaining
> the ranking. If the call fails or no API key is configured, it falls
> back to a template-based reasoning string — the pipeline never
> breaks because of it.

---

## Tech Stack

* **Frontend**: Next.js 15, TypeScript, Tailwind CSS, Zustand, Recharts, Framer Motion, Axios.
* **Backend**: FastAPI, Python 3.12, SQLAlchemy, Uvicorn, Celery, Redis, PostgreSQL.
* **Machine Learning**: Scikit-Learn (Linear Regression for OLS diagnostics), CAGR-based trend extrapolation for forecasting.
* **LLM**: Groq (`llama-3.3-70b-versatile`) — used only by the Decision Agent, to synthesize already-computed scores into natural-language reasoning (see note below).

---

## Folder Structure

```
trade-intelligence-system/
│
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages & SPA views
│   │   ├── components/    # Recharts & UI elements
│   │   ├── store/         # Zustand store (state, WebSocket sync)
│   │   └── globals.css    # Glowing dark mode design tokens
│   ├── Dockerfile
│   └── package.json
│
├── backend/
│   ├── agents/            # BaseAgent & specific agent implementations
│   ├── cache/             # Redis connection & fallback handlers
│   ├── config/            # Settings & directory initialization
│   ├── database/          # Connection pools & SQLAlchemy ORM models
│   ├── datasets/          # Subdirectories for user CSV/Excel uploads
│   ├── ml/                # Time-series forecasting & score explainability
│   ├── routes/            # FastAPI router endpoints
│   ├── services/          # World Bank, Forex, and Logistics clients
│   ├── utils/             # Column normalisation & WebSocket log adapters
│   ├── main.py            # Entrypoint
│   ├── requirements.txt
│   └── Dockerfile
│
├── data/                  # Original raw seed datasets
├── docker-compose.yml
└── README.md
```

---

## Setup & Running Instructions

### Option 1: Quick Run with Docker Compose (Recommended)

To spin up all services (PostgreSQL, Redis, Celery, FastAPI, Next.js) in a fully configured container network, run:

```bash
docker-compose up --build
```

Access interfaces:
* **Frontend Dashboard**: `http://localhost:3000`
* **FastAPI Swagger API Documentation**: `http://localhost:8000/docs`

---

### Option 2: Standalone Developer Mode (Local)

The backend features dynamic fallback handlers that run successfully without docker services (utilizes **SQLite** instead of Postgres, and **In-Memory Caches** if Redis is offline).

#### Step 1: Start Backend
Navigate to the root workspace and run:
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Step 2: Start Frontend
Open a new terminal, navigate to the `frontend/` folder, and run:
```bash
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## API Endpoints

* `POST /analyze`: Starts async orchestration (returns `task_id`).
* `GET /reports/{id}`: Retrieves complete aggregated report scores and forecasts.
* `POST /datasets/upload`: Uploads a file (CSV/XLSX/JSON) to a target folder (`market`, `demand`, `pricing`, etc.).
* `GET /health`: Health metrics of database, cache, and external APIs.
* `/ws`: WebSocket connection for real-time logs streaming.

---

## Sample Payloads

### Ingestion Request (`POST /analyze`)
```json
{
  "hs_code": "5201",
  "quantity_tons": 50,
  "commodity_name": "cotton"
}
```

### Analysis Result Structure
```json
{
  "best_export_market": "Germany",
  "expected_profit_usd": 105650.00,
  "final_ai_score": 0.88,
  "top_markets": [
    {
      "country": "Germany",
      "rank": 1,
      "final_score": 0.88,
      "expected_profit_usd": 105650.00,
      "predicted_demand_growth_pct": 0.20
    }
  ],
  "shap_explainability": {
    "local_attributions": {
      "Germany": {
        "contributions": {
          "market": 0.12,
          "demand": 0.08,
          "price": 0.05
        }
      }
    }
  }
}
```

## Testing

```bash
cd backend
pytest                    # runs fast unit tests only (integration test auto-skips if DB unreachable)
pytest -m integration     # runs the full end-to-end flow (requires a reachable DB and network access)
```

Unit tests cover the pure logic that's easiest to get subtly wrong:
country/column normalization (`utils/schema.py`), CAGR forecasting and
explainability weighting (`ml/pipelines.py`), currency lookups
(`services/forex.py`), the Haversine distance calculation
(`services/logistics_service.py`), supplier address parsing
(`agents/supplier_agent.py`), and the API-key auth dependency
(`utils/auth.py`). The integration test boots the full app in-process
and runs one real end-to-end analysis through all 9 agents.
