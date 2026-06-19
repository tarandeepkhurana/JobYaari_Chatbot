"""
Embedding Factory:
- Creates/caches embedding clients
- Centralizes embedding configs
- Supports OpenAI/Azure providers
"""

import threading

from openai import AsyncOpenAI, AsyncAzureOpenAI

from src.config import settings


class EmbeddingFactory:

    _cache = {}
    _lock = threading.Lock()

    # --------------------------
    # OPENAI EMBEDDINGS
    # --------------------------
    @classmethod
    def create_openai_embedding_client(cls):

        cache_key = "openai_embedding_client"

        with cls._lock:

            if cache_key in cls._cache:
                return cls._cache[cache_key]

            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY
            )

            cls._cache[cache_key] = client

            return client

    @classmethod
    def get_openai_embedding_client(cls):
        return cls.create_openai_embedding_client()

    # --------------------------
    # AZURE EMBEDDINGS
    # --------------------------
    @classmethod
    def create_azure_embedding_client(cls):

        cache_key = "azure_embedding_client"

        with cls._lock:

            if cache_key in cls._cache:
                return cls._cache[cache_key]

            client = AsyncAzureOpenAI(
                api_key=settings.AZURE_AI_FOUNDRY_PROJECT_API_KEY,
                api_version="2024-12-01-preview",
                azure_endpoint=settings.AZURE_AI_FOUNDRY_PROJECT_ENDPOINT.rstrip("/")
            )

            cls._cache[cache_key] = client

            return client

    @classmethod
    def get_azure_embedding_client(cls):
        return cls.create_azure_embedding_client()