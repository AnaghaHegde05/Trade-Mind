import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

from sklearn.linear_model import LinearRegression

def train_and_forecast_timeseries(
    history: List[Tuple[int, float]], 
    forecast_years: List[int],
    country: str,
    indicator: str
) -> Dict[str, Any]:
    """
    Forecasts future values from historical (year, value) pairs.

    These histories are typically 2-8 yearly points with a single feature
    (year). A heavier ML cascade (Prophet -> XGBoost -> LightGBM ->
    RandomForest) cannot learn anything from that little data that a
    trend extrapolation doesn't already capture, so this uses CAGR-based
    compounding growth from the latest historical value - the standard,
    explainable approach for short trade/demand series, with no
    model-fitting, caching, or compiled-dependency overhead.

    The returned "r2" is a genuine (not simulated) R^2 of an ordinary
    least-squares fit against the actual history - a diagnostic of how
    linear the trend is, not a stand-in for forecast accuracy. It's only
    reported with 3+ data points, since R^2 is undefined/trivial (always
    exactly 1.0) for a 2-point fit.
    """
    if len(history) < 2:
        # Too little data - fall back to a flat continuation of the one point we have
        val = history[0][1] if len(history) == 1 else 0.0
        return {
            "forecast": {yr: val for yr in forecast_years},
            "model_used": "Constant Fallback (insufficient history)",
            "cagr": 0.0,
            "r2": None
        }
        
    df = pd.DataFrame(history, columns=["year", "value"])
    df = df.sort_values("year").reset_index(drop=True)
    
    # Calculate CAGR
    years_diff = df["year"].iloc[-1] - df["year"].iloc[0]
    val_start = df["value"].iloc[0]
    val_end = df["value"].iloc[-1]
    
    if years_diff > 0 and val_start > 0 and val_end > 0:
        cagr = ((val_end / val_start) ** (1 / years_diff)) - 1
    else:
        cagr = 0.0

    # Forecast: compound the CAGR forward from the latest known value.
    # Clipped at 0 since negative prices/volumes aren't meaningful.
    last_year = int(df["year"].iloc[-1])
    last_value = float(df["value"].iloc[-1])
    forecast_results = {
        yr: max(0.0, last_value * ((1.0 + cagr) ** (yr - last_year)))
        for yr in forecast_years
    }

    # Genuine R^2 of an OLS trend fit against the real history, only when
    # it's statistically meaningful (3+ points).
    r2_score: Optional[float] = None
    if len(df) >= 3:
        X_train = df[["year"]].values
        y_train = df["value"].values
        ols = LinearRegression()
        ols.fit(X_train, y_train)
        r2_score = float(ols.score(X_train, y_train))

    return {
        "forecast": forecast_results,
        "model_used": "CAGR Trend Extrapolation",
        "cagr": float(cagr),
        "r2": r2_score
    }

def compute_explainability(
    country_data: List[Dict[str, Any]], 
    weights: Dict[str, float]
) -> Dict[str, Any]:
    """
    Computes per-country factor attributions and global feature importance
    for the final weighted score.

    Local attributions are a transparent, hand-written formula -
    weight * (value - baseline) per factor - which is honestly
    explainable on its own and needs no ML model to justify it.

    Global importance is NOT fit from a model. It used to be: a surrogate
    RandomForestRegressor (optionally wrapped in a SHAP TreeExplainer)
    trained on at most one row per evaluated country - typically ~5-7
    rows - against 7 features. That's fewer samples than features, which
    is statistically meaningless regardless of which library computes
    it. Since `final_score` is by construction a known linear combination
    of `weights` (see DEFAULT_WEIGHTS in decision_agent.py), the "global
    feature importance" already *is* those weights, normalized to sum to
    1 - no model-fitting required or justified.
    """
    if not country_data:
        return {}
        
    features = list(weights.keys())
    
    # Convert list of dicts to DataFrame
    df = pd.DataFrame(country_data)
    
    # Calculate baseline scores (mean of each feature score)
    baselines = {feat: df[f"{feat}_score"].mean() for feat in features if f"{feat}_score" in df.columns}
    
    explainability = {}
    
    for item in country_data:
        country = item["country"]
        contributions = {}
        total_attrib = 0.0
        
        for feat in features:
            val_col = f"{feat}_score"
            if val_col in item:
                val = item[val_col]
                base = baselines.get(feat, 0.5)
                weight = weights[feat]
                # Contribution is weight * (value - baseline)
                contrib = weight * (val - base)
                contributions[feat] = float(contrib)
                total_attrib += contrib
                
        explainability[country] = {
            "contributions": contributions,
            "baseline_score": sum(weights[f] * baselines.get(f, 0.5) for f in features),
            "actual_score": item["final_score"]
        }

    # Global feature importance = the known scoring weights, normalized.
    # final_score is defined as sum(weights[f] * f_score), so this is the
    # exact, real answer - not an approximation of one.
    total_w = sum(weights.values())
    global_importance = {k: v / total_w for k, v in weights.items()}

    return {
        "local_attributions": explainability,
        "global_importance": global_importance
    }
