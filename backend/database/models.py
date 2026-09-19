from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import relationship
import datetime
from backend.database.connection import Base

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String(50), primary_key=True, index=True) # UUID or Task ID
    hs_code = Column(String(20), nullable=False)
    commodity_name = Column(String(100), nullable=False)
    quantity_tons = Column(Float, nullable=False)
    
    best_export_market = Column(String(100), nullable=True)
    expected_profit_usd = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    final_ai_score = Column(Float, nullable=True)
    
    # Detailed explanations and recommendations
    recommendations = Column(JSON, default=list) # List of dicts or strings
    shap_explainability = Column(JSON, default=dict) # Weight contributions
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    country_scores = relationship("CountryScore", back_populates="analysis", cascade="all, delete-orphan")

class CountryScore(Base):
    __tablename__ = "country_scores"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(50), ForeignKey("analysis_results.id"), nullable=False)
    country = Column(String(100), nullable=False)
    
    # Scores (0.0 to 1.0)
    market_score = Column(Float, nullable=True)
    demand_score = Column(Float, nullable=True)
    price_score = Column(Float, nullable=True)
    currency_score = Column(Float, nullable=True)
    tariff_score = Column(Float, nullable=True)
    logistics_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    supplier_score = Column(Float, nullable=True)
    
    final_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=True)
    
    # Values
    import_volume = Column(Float, nullable=True)
    import_value = Column(Float, nullable=True)
    predicted_demand_growth_pct = Column(Float, nullable=True)
    shipping_cost_per_ton = Column(Float, nullable=True)
    transit_days = Column(Float, nullable=True)
    tariff_pct = Column(Float, nullable=True)
    currency_risk_level = Column(String(50), nullable=True)
    political_stability_score = Column(Float, nullable=True)
    inflation_rate_pct = Column(Float, nullable=True)
    expected_profit_usd = Column(Float, nullable=True)
    
    analysis = relationship("AnalysisResult", back_populates="country_scores")

class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(50), ForeignKey("analysis_results.id"), nullable=False)
    country = Column(String(100), nullable=False)
    indicator_type = Column(String(50), nullable=False) # 'trade_volume_usd', 'demand_tons', 'price_usd_per_ton'
    year = Column(Integer, nullable=False)
    value = Column(Float, nullable=False)
    is_forecast = Column(Integer, default=0) # 0 = historical, 1 = predicted

class LogisticsData(Base):
    __tablename__ = "logistics_data"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(50), ForeignKey("analysis_results.id"), nullable=False)
    country = Column(String(100), nullable=False)
    origin_port = Column(String(100), nullable=False)
    destination_port = Column(String(100), nullable=False)
    distance_km = Column(Float, nullable=False)
    transit_days = Column(Float, nullable=False)
    cost_per_ton = Column(Float, nullable=False)
    efficiency_index = Column(Float, nullable=True)

class SupplierAnalysis(Base):
    __tablename__ = "supplier_analysis"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(50), ForeignKey("analysis_results.id"), nullable=False)
    supplier_name = Column(String(200), nullable=False)
    country = Column(String(100), nullable=False)
    capacity_tons = Column(Float, nullable=True)  # Not in source data - genuinely unknown, not faked
    rating = Column(Float, nullable=True)
    cost_competitiveness = Column(Float, nullable=True) # Score (0-1)
    overall_score = Column(Float, nullable=False)
    address = Column(String(500), nullable=True)
    contact_no = Column(String(100), nullable=True)
    email = Column(String(150), nullable=True)
    city_state = Column(String(200), nullable=True)

class TariffData(Base):
    __tablename__ = "tariffs"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(50), ForeignKey("analysis_results.id"), nullable=False)
    country = Column(String(100), nullable=False)
    hs_code = Column(String(20), nullable=False)
    tariff_pct = Column(Float, nullable=False)
    trade_barrier_severity = Column(String(50), default="Low") # Low, Medium, High
    score = Column(Float, nullable=False) # Normalised tariff score (0-1)

class RiskData(Base):
    __tablename__ = "risks"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(String(50), ForeignKey("analysis_results.id"), nullable=False)
    country = Column(String(100), nullable=False)
    political_stability = Column(Float, nullable=True) # -2.5 to 2.5 standard
    inflation_rate = Column(Float, nullable=True)
    economic_confidence = Column(Float, nullable=True) # Index
    overall_risk_score = Column(Float, nullable=False)
