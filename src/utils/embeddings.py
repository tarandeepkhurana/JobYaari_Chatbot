from src.config import settings
from src.factories.embedding_factory import EmbeddingFactory


async def generate_embeddings(jobs: list[dict]) -> list[dict]:
    """Generate OpenAI embeddings for job embedding_text values."""
    client = EmbeddingFactory.get_openai_embedding_client()

    texts = [job["embedding_text"] or "" for job in jobs]

    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts
    )

    for i, job in enumerate(jobs):
        job["embedding"] = response.data[i].embedding

    return jobs


async def generate_embedding(query: str) -> list[float]:
    """Generate an OpenAI embedding for a single retrieval query."""
    client = EmbeddingFactory.get_openai_embedding_client()

    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=query
    )

    return response.data[0].embedding
