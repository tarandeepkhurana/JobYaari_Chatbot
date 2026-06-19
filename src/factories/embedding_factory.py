"""
Embedding Factory:
- Creates/caches embedding clients
- Centralizes embedding configs
- Uses OpenAI embeddings
"""

import threading

from openai import AsyncOpenAI

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

