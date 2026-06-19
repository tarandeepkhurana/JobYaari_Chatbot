"""
LLM Factory:
- Creates/caches LLMs
- Centralizes configs
- Used by services
See: docs/llm_factory.md and Excalidraw Agentic AI Module
"""

import threading
from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI
from src.config import settings


class LLMFactory:
    _cache = {}
    _lock = threading.Lock()
    
    # --------------------------
    # CHAT LLM
    # --------------------------
    @classmethod
    def create_chat_llm(cls):
        cache_key = "chat_llm"

        with cls._lock:
            if cache_key in cls._cache:
                return cls._cache[cache_key]

            llm = ChatOpenAI(
                model="gpt-5-mini",
                api_key=settings.OPENAI_API_KEY,
                streaming=True,

                # Responses API
                use_responses_api=True,

                # Responses API reasoning
                reasoning={
                    "effort": "low",
                    "summary": "auto"
                },

                temperature=0.2,

                # response storage
                store=False,

                timeout=120,
            )

            cls._cache[cache_key] = llm
            return llm

    @classmethod
    def get_chat_llm(cls):
        return cls.create_chat_llm()
    
    # --------------------------
    # RESUME PARSER LLM          
    # --------------------------
    @classmethod
    def create_resume_parser_llm(cls):
        cache_key = "resume_parser_llm"

        with cls._lock:
            if cache_key in cls._cache:
                return cls._cache[cache_key]

            llm = ChatOpenAI(
                model="gpt-4o-mini",

                api_key=settings.OPENAI_API_KEY,

                temperature=0,

                streaming=False,

                timeout=60,

                store=False,

                use_responses_api=True,

            )

            cls._cache[cache_key] = llm
            return llm


    @classmethod
    def get_resume_parser_llm(cls):
        return cls.create_resume_parser_llm()
    
    # --------------------------
    # DECISION LLM
    # --------------------------
    @classmethod
    def create_decision_llm(cls):
        cache_key = "decision_llm"

        with cls._lock:
            if cache_key in cls._cache:
                return cls._cache[cache_key]

            llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=0,
                streaming=False,
                timeout=30,
                store=False,
                use_responses_api=True,
            )

            cls._cache[cache_key] = llm
            return llm

    @classmethod
    def get_decision_llm(cls):
        return cls.create_decision_llm()
    

    # --------------------------
    # QUERY PARSER LLM
    # --------------------------
    @classmethod
    def create_query_parser_llm(cls):
        cache_key = "query_parser_llm"

        with cls._lock:
            if cache_key in cls._cache:
                return cls._cache[cache_key]

            llm = ChatOpenAI(
                model="gpt-4o-mini",

                api_key=settings.OPENAI_API_KEY,

                temperature=0,

                streaming=False,

                timeout=60,

                store=False,

                use_responses_api=True,

            )

            cls._cache[cache_key] = llm
            return llm


    @classmethod
    def get_query_parser_llm(cls):
        return cls.create_query_parser_llm()

    # --------------------------
    # RERANKER LLM
    # --------------------------
    @classmethod
    def create_reranker_llm(cls):
        cache_key = "reranker_llm"

        with cls._lock:
            if cache_key in cls._cache:
                return cls._cache[cache_key]

            llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=0,
                streaming=False,
                timeout=60,
                store=False,
                use_responses_api=True,
            )

            cls._cache[cache_key] = llm
            return llm

    @classmethod
    def get_reranker_llm(cls):
        return cls.create_reranker_llm()

    

if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage

    async def main():

        chat_llm = LLMFactory.get_chat_llm()

        response = await chat_llm.ainvoke([HumanMessage(content="Say hello")])

        print("\n=== CHAT LLM ===")
        print(response.content)

        resume_llm = LLMFactory.get_resume_parser_llm()

        response = await resume_llm.ainvoke(
            [HumanMessage(content="Say parser works")]
        )

        print("\n=== RESUME PARSER LLM ===")
        print(response.content)

        decision_llm = LLMFactory.get_decision_llm()

        response = await decision_llm.ainvoke([HumanMessage(content="Reply OK")])

        print("\n=== DECISION LLM ===")
        print(response.content)

    asyncio.run(main())
