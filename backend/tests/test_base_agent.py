import pytest
from backend.agents.base_agent import BaseAgent


@pytest.fixture
def agent():
    return BaseAgent("Test Agent")


class TestGetTargetCountries:
    def test_extracts_countries_in_order(self, agent):
        context = {
            "market_agent": {
                "top_markets": [
                    {"country": "Germany", "market_score": 0.9},
                    {"country": "Vietnam", "market_score": 0.7},
                ]
            }
        }
        top_markets, countries = agent.get_target_countries(context)

        assert countries == ["Germany", "Vietnam"]
        assert top_markets == context["market_agent"]["top_markets"]

    def test_raises_when_market_agent_missing(self, agent):
        with pytest.raises(ValueError, match="MarketAgent must execute first"):
            agent.get_target_countries({})

    def test_raises_when_top_markets_empty(self, agent):
        context = {"market_agent": {"top_markets": []}}
        with pytest.raises(ValueError, match="MarketAgent must execute first"):
            agent.get_target_countries(context)
