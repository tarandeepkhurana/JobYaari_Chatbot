from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field, field_validator

from src.factories.llm_factory import LLMFactory
from src.services.llm.prompts import QUERY_PARSER_SYSTEM_PROMPT
import logging

logger = logging.getLogger("retrieval.query_parser")


class ParsedJobQuery(BaseModel):
    """Structured search intent extracted from a user's job query."""

    semantic_query: str = Field(
        default="",
        description="Clean role/domain/skill query used for semantic retrieval.",
    )
    work_mode: str | None = None
    remote: bool | None = None
    is_paid: bool | None = None
    min_stipend: int | None = None
    max_stipend: int | None = None
    duration_months: int | None = None
    skills: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)

    @field_validator("skills", "categories", "cities", mode="before")
    @classmethod
    def normalize_list(cls, value):
        if not value:
            return []

        normalized = []
        seen = set()

        for item in value:
            text = str(item).strip().lower()

            if text and text not in seen:
                seen.add(text)
                normalized.append(text)

        return normalized


DEFAULT_RESPONSE = {
    "semantic_query": "",
    "work_mode": None,
    "remote": None,
    "is_paid": None,
    "min_stipend": None,
    "max_stipend": None,
    "duration_months": None,
    "skills": [],
    "categories": [],
    "cities": []
}


async def parse_query(user_query: str) -> dict:
    """Parse the user query to extract structured filters for job search."""
    
    logger.info(f"Parsing user query: {user_query}")

    llm = LLMFactory.get_query_parser_llm().with_structured_output(
        ParsedJobQuery
    )

    messages = [
        SystemMessage(content=QUERY_PARSER_SYSTEM_PROMPT),
        HumanMessage(content=user_query)
    ]

    try:
        response = await llm.ainvoke(messages)

        parsed = response.model_dump()
        parsed["semantic_query"] = parsed.get("semantic_query") or user_query
        
        logger.info("Parsed query successfully: %s", parsed)
        
        return {
            **DEFAULT_RESPONSE,
            **parsed
        }

    except Exception as e:
        logger.error(f"Error parsing query: {e}")
        return {
            **DEFAULT_RESPONSE,
            "semantic_query": user_query
        }
