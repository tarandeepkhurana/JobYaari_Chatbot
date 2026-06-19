from src.factories.embedding_factory import EmbeddingFactory
from src.config import settings

async def generate_embeddings_openai(jobs: list[dict]) -> list[dict]:

    client = EmbeddingFactory.get_openai_embedding_client()

    texts = [job["embedding_text"] or "" for job in jobs]

    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts
    )

    for i, job in enumerate(jobs):
        job["embedding"] = response.data[i].embedding

    return jobs


async def generate_embeddings_azure_endpoint(jobs: list[dict]) -> list[dict]:

    try:

        client = EmbeddingFactory.get_azure_embedding_client()

        texts = [job["embedding_text"] or "" for job in jobs]

        response = await client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=texts
        )

        for i, job in enumerate(jobs):
            job["embedding"] = response.data[i].embedding

        return jobs

    except Exception as e:
        raise ValueError(f"Failed to generate embedding: {str(e)}")
    

async def generate_embedding(query: str) -> list[float]:

    client = EmbeddingFactory.get_azure_embedding_client()

    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=query
    )

    return response.data[0].embedding