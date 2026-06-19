import logging

from src.agent.graph import build_graph


logger = logging.getLogger("agent.runtime")

_cached_agent = None


async def initialize_agent():
    """Compile and cache the LangGraph app once per Python process."""

    global _cached_agent
    if _cached_agent is None:
        _cached_agent = build_graph()
        logger.info("Job agent initialized")
    return _cached_agent


async def get_agent():
    """Return the cached compiled agent, lazily initializing if needed."""

    return await initialize_agent()
