from backend.services.forex import ForexService


class TestGetCurrencyForCountry:
    def test_known_country(self):
        assert ForexService.get_currency_for_country("Germany") == "EUR"
        assert ForexService.get_currency_for_country("INDIA") == "INR"

    def test_unknown_country_defaults_to_usd(self):
        assert ForexService.get_currency_for_country("Atlantis") == "USD"


class TestGetCurrencyVolatility:
    def test_known_currency(self):
        assert ForexService.get_currency_volatility("USD") == 0.0
        assert ForexService.get_currency_volatility("EGP") == 0.220

    def test_unknown_currency_uses_default(self):
        assert ForexService.get_currency_volatility("XYZ") == 0.080


class TestGetFallbackRates:
    def test_contains_usd_baseline(self):
        rates = ForexService.get_fallback_rates()
        assert rates["USD"] == 1.0

    def test_contains_common_trade_currencies(self):
        rates = ForexService.get_fallback_rates()
        for code in ["EUR", "INR", "CNY", "BDT"]:
            assert code in rates
            assert rates[code] > 0
