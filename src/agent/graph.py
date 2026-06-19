from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.nodes import answer_node
import logging

logger = logging.getLogger("agent.graph")


def build_graph():
    """Define the agent's reasoning graph structure."""

    logger.info("Building agent graph")
    
    graph = StateGraph(AgentState)

    graph.add_node("answer", answer_node)

    graph.set_entry_point("answer")
    graph.add_edge("answer", END)

    return graph.compile()
