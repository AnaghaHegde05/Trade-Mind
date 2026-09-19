import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from backend.config.settings import settings

logger = logging.getLogger("trade_intel.database")

Base = declarative_base()

SessionLocal = None
engine = None

def init_db():
    global engine, SessionLocal
    try:
        logger.info(f"Connecting to primary database at {settings.DATABASE_URL.split('@')[-1]}...")
        engine = create_engine(
            settings.DATABASE_URL, 
            pool_pre_ping=True, 
            pool_recycle=1800
        )
        # Test connection
        connection = engine.connect()
        connection.close()
        logger.info("Successfully connected to PostgreSQL database.")
    except Exception as e:
        logger.error(f"FATAL: Failed to connect to PostgreSQL database: {e}")
        raise e
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Run initialization
init_db()

# Dependency for FastAPI endpoints
def get_db():
    global SessionLocal
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
