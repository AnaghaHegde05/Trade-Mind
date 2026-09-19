import httpx
import logging
import datetime
from typing import Dict, Any

logger = logging.getLogger("trade_intel.services.forex")

# Currency maps
COUNTRY_TO_CURRENCY = {
    "GERMANY": "EUR", "BANGLADESH": "BDT", "BANGLADESH PR": "BDT", "CHINA": "CNY", 
    "CHINA P RP": "CNY", "VIETNAM": "VND", "VIETNAM SOC REP": "VND", "USA": "USD", 
    "U S A": "USD", "UNITED STATES": "USD", "ALGERIA": "DZD", "ANGOLA": "AOA",
    "AUSTRALIA": "AUD", "BELGIUM": "EUR", "FRANCE": "EUR", "ITALY": "EUR",
    "NETHERLAND": "EUR", "NETHERLANDS": "EUR", "SPAIN": "EUR", "PORTUGAL": "EUR",
    "POLAND": "PLN", "GREECE": "EUR", "SWEDEN": "SEK", "SWITZERLAND": "CHF",
    "UNITED KINGDOM": "GBP", "U K": "GBP", "JAPAN": "JPY", "KOREA RP": "KRW",
    "REPUBLIC OF KOREA": "KRW", "MALAYSIA": "MYR", "INDONESIA": "IDR",
    "THAILAND": "THB", "INDIA": "INR", "SAUDI ARAB": "SAR", "U ARAB EMTS": "AED",
    "UAE": "AED", "EGYPT": "EGP", "PAKISTAN": "PKR", "BRAZIL": "BRL"
}

# Standard currency risk volatility (historical SD of annual currency returns relative to USD)
CURRENCY_VOLATILITY = {
    "USD": 0.0,       # Base Currency
    "EUR": 0.045,     # Low volatility
    "GBP": 0.052,     # Low
    "CHF": 0.048,     # Low
    "JPY": 0.085,     # Medium (safe haven but volatile recently)
    "CNY": 0.025,     # Low (managed peg)
    "SGD": 0.030,     # Low
    "AUD": 0.065,     # Medium
    "CAD": 0.042,     # Low
    "INR": 0.022,     # Low (highly managed)
    "KRW": 0.068,     # Medium
    "BDT": 0.098,     # High (recently depreciating/volatile)
    "VND": 0.035,     # Low/Medium (managed peg)
    "DZD": 0.060,     # Medium
    "AOA": 0.180,     # Very High
    "EGP": 0.220,     # Very High
    "PKR": 0.150,     # High
    "BRL": 0.095,     # High
    "TRY": 0.280      # Very High
}

_forex_cache: Dict[str, Any] = {
    "rates": {},
    "last_fetched": None
}

class ForexService:
    @staticmethod
    async def get_exchange_rates() -> Dict[str, float]:
        """Fetches latest exchange rates relative to USD from open.er-api.com."""
        now = datetime.datetime.now()
        
        # Check cache (valid for 12 hours)
        if (
            _forex_cache["rates"] and 
            _forex_cache["last_fetched"] and 
            (now - _forex_cache["last_fetched"]) < datetime.timedelta(hours=12)
        ):
            return _forex_cache["rates"]
            
        url = "https://open.er-api.com/v6/latest/USD"
        
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    logger.info("Fetching real-time exchange rates from ExchangeRate API...")
                    r = await client.get(url)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get("result") == "success":
                            rates = {k: float(v) for k, v in data.get("rates", {}).items()}
                            _forex_cache["rates"] = rates
                            _forex_cache["last_fetched"] = now
                            return rates
            except Exception as e:
                logger.warning(f"Forex API call attempt {attempt+1} failed: {e}")
                
        # API Fail: return fallback static rates
        logger.warning("Forex API failed. Returning fallback exchange rates.")
        return ForexService.get_fallback_rates()

    @staticmethod
    def get_fallback_rates() -> Dict[str, float]:
        """Provides realistic exchange rates in case API is unavailable."""
        return {
            "USD": 1.0,
            "EUR": 0.92,
            "GBP": 0.79,
            "CNY": 7.24,
            "INR": 83.35,
            "BDT": 117.50,
            "VND": 25450.0,
            "AUD": 1.51,
            "CAD": 1.36,
            "JPY": 156.80,
            "KRW": 1365.0,
            "DZD": 134.50,
            "EGP": 47.20,
            "AED": 3.67,
            "SAR": 3.75
        }

    @staticmethod
    def get_currency_for_country(country_name: str) -> str:
        """Gets currency code for a given country."""
        norm_name = country_name.upper().strip()
        for k, v in COUNTRY_TO_CURRENCY.items():
            if k in norm_name or norm_name in k:
                return v
        return "USD" # Default to USD

    @staticmethod
    def get_currency_volatility(currency_code: str) -> float:
        """Returns the annual standard deviation (volatility score) of the currency."""
        return CURRENCY_VOLATILITY.get(currency_code, 0.080) # Default to 8% if unknown
