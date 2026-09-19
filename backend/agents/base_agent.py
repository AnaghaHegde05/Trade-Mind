import logging
import asyncio
from typing import Dict, Any, List
from backend.utils.logging import get_agent_logger, AgentLoggerAdapter


class BaseAgent:
    """Base class all specialized agents (CurrencyAgent, DemandAgent, etc.) inherit from."""

    def __init__(self, name: str):
        self.name: str = name
        self.logger: AgentLoggerAdapter = get_agent_logger(name)

    def log_step(self, message: str, progress: float = 0.0, level: int = logging.INFO):
        """Logs a step with progress metadata, streamed to the frontend over WebSocket."""
        self.logger.log(level, message, agent=self.name, progress=progress)

    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the agent's analysis.

        Args:
            inputs: hs_code, quantity_tons, commodity_name (plus any agent-specific params)
            context: shared pipeline context - results from previously executed agents

        Must be overridden by every subclass.
        """
        raise NotImplementedError("Each agent must implement its own execute method.")

    def get_target_countries(self, context: Dict[str, Any]):
        """
        Extracts the candidate export countries produced by MarketAgent from
        the shared pipeline context. Every downstream agent (Demand, Currency,
        Tariff, Logistics, Risk) needs this same data in the same shape, so
        it's centralized here instead of being duplicated in each agent.

        Returns:
            (top_markets, countries): the raw MarketAgent records, and just
            their country names in the same order.

        Raises:
            ValueError: if MarketAgent hasn't run yet, or found no candidates.
        """
        market_data = context.get("market_agent", {})
        top_markets = market_data.get("top_markets", [])

        if not top_markets:
            raise ValueError("No target countries found in shared context. MarketAgent must execute first and provide top_markets.")

        countries = [m["country"] for m in top_markets]
        return top_markets, countries
