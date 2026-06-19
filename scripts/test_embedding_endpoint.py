import asyncio

from openai import AuthenticationError, BadRequestError, OpenAIError

from src.config import settings
from src.factories.embedding_factory import EmbeddingFactory


TEST_TEXT = "civil engineering internships and jobs"


async def test_client(name: str, client) -> None:
    """Call one embedding endpoint and print a compact success/failure report."""

    print(f"\n=== {name} ===")
    print(f"model: {settings.OPENAI_EMBEDDING_MODEL}")

    try:
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=TEST_TEXT,
        )
    except AuthenticationError as exc:
        print("status: FAILED")
        print("error: authentication failed")
        print(exc)
        return
    except BadRequestError as exc:
        print("status: FAILED")
        print("error: bad request")
        print(exc)
        return
    except OpenAIError as exc:
        print("status: FAILED")
        print("error: OpenAI client error")
        print(exc)
        return
    except Exception as exc:
        print("status: FAILED")
        print("error: unexpected error")
        print(repr(exc))
        return

    embedding = response.data[0].embedding
    print("status: OK")
    print(f"embedding_dimensions: {len(embedding)}")
    print(f"first_5_values: {embedding[:5]}")


async def main() -> None:
    print("Testing OpenAI embedding endpoint with current .env configuration")
    await test_client(
        "OpenAI embedding client",
        EmbeddingFactory.get_openai_embedding_client(),
    )


if __name__ == "__main__":
    asyncio.run(main())
