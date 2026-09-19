import pytest
from backend.ml.pipelines import train_and_forecast_timeseries, compute_explainability


class TestTrainAndForecastTimeseries:
    def test_insufficient_history_falls_back_to_constant(self):
        result = train_and_forecast_timeseries(
            history=[(2023, 100.0)],
            forecast_years=[2024, 2025],
            country="Testland",
            indicator="test_indicator",
        )
        assert result["model_used"] == "Constant Fallback (insufficient history)"
        assert result["forecast"] == {2024: 100.0, 2025: 100.0}
        assert result["cagr"] == 0.0
        assert result["r2"] is None

    def test_empty_history_falls_back_to_zero(self):
        result = train_and_forecast_timeseries(
            history=[],
            forecast_years=[2024],
            country="Testland",
            indicator="test_indicator",
        )
        assert result["forecast"] == {2024: 0.0}

    def test_cagr_calculation_matches_formula(self):
        # value doubles over 2 years -> CAGR = sqrt(2) - 1 ~= 0.4142
        result = train_and_forecast_timeseries(
            history=[(2022, 100.0), (2024, 200.0)],
            forecast_years=[2025],
            country="Testland",
            indicator="test_indicator",
        )
        assert result["cagr"] == pytest.approx(0.41421, abs=1e-4)

    def test_forecast_compounds_cagr_forward(self):
        result = train_and_forecast_timeseries(
            history=[(2022, 100.0), (2023, 110.0)],
            forecast_years=[2024, 2025],
            country="Testland",
            indicator="test_indicator",
        )
        cagr = result["cagr"]
        assert result["forecast"][2024] == pytest.approx(110.0 * (1 + cagr), rel=1e-6)
        assert result["forecast"][2025] == pytest.approx(110.0 * (1 + cagr) ** 2, rel=1e-6)

    def test_forecast_never_goes_negative(self):
        # Steep decline - naive compounding could go negative, must clip at 0
        result = train_and_forecast_timeseries(
            history=[(2020, 1000.0), (2021, 10.0)],
            forecast_years=[2022, 2023, 2024, 2025],
            country="Testland",
            indicator="test_indicator",
        )
        assert all(v >= 0.0 for v in result["forecast"].values())

    def test_r2_only_reported_with_three_or_more_points(self):
        two_point = train_and_forecast_timeseries(
            history=[(2022, 100.0), (2023, 110.0)],
            forecast_years=[2024],
            country="Testland",
            indicator="test_indicator",
        )
        assert two_point["r2"] is None

        three_point = train_and_forecast_timeseries(
            history=[(2021, 100.0), (2022, 110.0), (2023, 121.0)],
            forecast_years=[2024],
            country="Testland",
            indicator="test_indicator",
        )
        assert three_point["r2"] is not None
        assert 0.0 <= three_point["r2"] <= 1.0

    def test_flat_or_invalid_series_yields_zero_cagr(self):
        # val_start <= 0 should not attempt CAGR (would be undefined/negative-base)
        result = train_and_forecast_timeseries(
            history=[(2022, 0.0), (2023, 50.0)],
            forecast_years=[2024],
            country="Testland",
            indicator="test_indicator",
        )
        assert result["cagr"] == 0.0


class TestComputeExplainability:
    WEIGHTS = {
        "market": 0.25, "demand": 0.20, "price": 0.15,
        "currency": 0.10, "tariff": 0.10, "logistics": 0.10, "risk": 0.10,
    }

    def _make_country(self, name, **scores):
        record = {"country": name, "final_score": scores.get("final_score", 0.5)}
        for feat in self.WEIGHTS:
            record[f"{feat}_score"] = scores.get(feat, 0.5)
        return record

    def test_empty_input_returns_empty_dict(self):
        assert compute_explainability([], self.WEIGHTS) == {}

    def test_global_importance_is_normalized_weights(self):
        data = [self._make_country("A"), self._make_country("B")]
        result = compute_explainability(data, self.WEIGHTS)

        total = sum(self.WEIGHTS.values())
        expected = {k: v / total for k, v in self.WEIGHTS.items()}
        assert result["global_importance"] == pytest.approx(expected)
        assert sum(result["global_importance"].values()) == pytest.approx(1.0)

    def test_local_attributions_present_per_country(self):
        data = [self._make_country("A", market=0.9), self._make_country("B", market=0.1)]
        result = compute_explainability(data, self.WEIGHTS)

        assert "A" in result["local_attributions"]
        assert "B" in result["local_attributions"]
        # A scored above the market-score baseline (mean of 0.9, 0.1 = 0.5),
        # so its market contribution should be positive; B's should be negative.
        assert result["local_attributions"]["A"]["contributions"]["market"] > 0
        assert result["local_attributions"]["B"]["contributions"]["market"] < 0
