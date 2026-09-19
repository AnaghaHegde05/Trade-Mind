import os
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Trade Intelligence Multi-Agent System"
    ENV: str = os.getenv("ENV", "development")
    BASE_DIR: Path = BASE_DIR
    
    # Database Settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/trade_intel"
    )
    SQLITE_FALLBACK_URL: str = f"sqlite:///{BASE_DIR}/trade_intelligence.db"
    
    # Redis & Broker Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    
    # Dataset Paths
    DATASET_DIR: Path = BASE_DIR / "datasets"
    MARKET_DATASET_DIR: Path = BASE_DIR / "datasets" / "market"
    DEMAND_DATASET_DIR: Path = BASE_DIR / "datasets" / "demand"
    PRICING_DATASET_DIR: Path = BASE_DIR / "datasets" / "pricing"
    LOGISTICS_DATASET_DIR: Path = BASE_DIR / "datasets" / "logistics"
    TARIFFS_DATASET_DIR: Path = BASE_DIR / "datasets" / "tariffs"
    RISK_DATASET_DIR: Path = BASE_DIR / "datasets" / "risk"
    SUPPLIERS_DATASET_DIR: Path = BASE_DIR / "datasets" / "suppliers"
    
    # External APIs
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")
    WORLD_BANK_API_URL: str = "https://api.worldbank.org/v2"
    FOREX_API_URL: str = "https://open.er-api.com/v6/latest/USD"

    # LLM Synthesis (Decision Agent narrative generation only)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    # Security
    API_KEY_HEADER: str = "X-API-Key"
    # No default secret shipped in source. If TRADE_API_KEY is unset, auth
    # is treated as not configured (see utils/auth.py) - set it via
    # environment variable to actually enforce it on write endpoints.
    API_KEY: str = os.getenv("TRADE_API_KEY", "")
    RATE_LIMIT_PER_MIN: int = 60
    
    # CORS
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        case_sensitive = True
        env_file = os.path.join(BASE_DIR, ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
for path in [
    settings.DATASET_DIR,
    settings.MARKET_DATASET_DIR,
    settings.DEMAND_DATASET_DIR,
    settings.PRICING_DATASET_DIR,
    settings.LOGISTICS_DATASET_DIR,
    settings.TARIFFS_DATASET_DIR,
    settings.RISK_DATASET_DIR,
    settings.SUPPLIERS_DATASET_DIR
]:
    path.mkdir(parents=True, exist_ok=True)
