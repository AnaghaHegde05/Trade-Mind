import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from backend.config.settings import settings
from backend.database.connection import engine, Base, init_db
from backend.routes import analysis, datasets, reports, websocket
from backend.utils.logging import setup_websocket_logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("trade_intel")

# Setup websocket logging capture
setup_websocket_logging()

# Create tables
try:
    logger.info("Initializing database and creating tables if not exist...")
    init_db()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Error creating database tables: {e}", exc_info=True)

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Multi-agent production platform for global trade intelligence analysis.",
    version="1.0.0"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple Rate Limiting Middleware
request_timestamps = {}

@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    client_ip = request.client.host
    now = time.time()
    
    # Clean old requests
    request_timestamps[client_ip] = [t for t in request_timestamps.get(client_ip, []) if now - t < 60]
    
    # Rate check
    if len(request_timestamps[client_ip]) >= settings.RATE_LIMIT_PER_MIN:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again later."}
        )
        
    request_timestamps[client_ip].append(now)
    response = await call_next(request)
    return response

# Mount routers
app.include_router(analysis.router)
app.include_router(datasets.router)
app.include_router(reports.router)
app.include_router(websocket.router)

@app.get("/")
def read_root():
    """Root welcome endpoint providing API links."""
    return {
        "project": "Antigravity Multi-Agent Trade Management System API",
        "status": "RUNNING",
        "documentation": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health_check():
    """Health check endpoint to test connection of DB, Redis, and overall status."""
    health_status = {
        "status": "HEALTHY",
        "timestamp": time.time(),
        "database": "CONNECTED",
        "cache": "CONNECTED"
    }
    
    # Test DB
    try:
        connection = engine.connect()
        connection.close()
    except Exception as e:
        health_status["database"] = f"DISCONNECTED: {str(e)}"
        health_status["status"] = "DEGRADED"
        
    # Test Redis cache
    from backend.cache.redis_client import redis_cache
    if redis_cache.client is None:
        health_status["cache"] = "DEGRADED: Using In-Memory Cache"
        health_status["status"] = "DEGRADED"
        
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
