import logging

from src.factories.llm_factory import LLMFactory


logger = logging.getLogger("warmup")


async def warmup_models():
    """Pre-create and cache LLM clients used by the chat flow."""

    LLMFactory.create_chat_llm()
    LLMFactory.create_decision_llm()
    LLMFactory.create_query_parser_llm()
    LLMFactory.create_reranker_llm()
    LLMFactory.create_resume_parser_llm()

    logger.info("LLM warmup complete")
