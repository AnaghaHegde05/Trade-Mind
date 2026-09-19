import pytest
from backend.services.logistics_service import LogisticsService


class TestCalculateDistance:
    def test_same_point_is_zero(self):
        d = LogisticsService.calculate_distance(19.076, 72.877, 19.076, 72.877)
        assert d == pytest.approx(0.0, abs=1e-6)

    def test_known_route_mumbai_to_rotterdam(self):
        # Haversine gives great-circle ("as the crow flies") distance, not
        # actual sea route via Suez - Mumbai to Rotterdam great-circle is
        # roughly 6800-7000 km. Wide tolerance since this is a sanity
        # check on the formula, not a precision test.
        mumbai = (19.0760, 72.8777)
        rotterdam = (51.9225, 4.4792)
        d = LogisticsService.calculate_distance(*mumbai, *rotterdam)
        assert 6500 < d < 7300

    def test_distance_is_symmetric(self):
        a = (19.0760, 72.8777)
        b = (1.3521, 103.8198)  # Singapore
        d1 = LogisticsService.calculate_distance(*a, *b)
        d2 = LogisticsService.calculate_distance(*b, *a)
        assert d1 == pytest.approx(d2)
