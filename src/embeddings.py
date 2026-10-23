
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError


# Resolve .env relative to this file, not the terminal's current directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)

MODEL_NAME = os.getenv(
    "GEMINI_EMBEDDING_MODEL",
    "gemini-embedding-001",
)
BATCH_SIZE = 16
MAX_RETRIES = 3


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Generate and attach Gemini embeddings to document chunks."""

    if not chunks:
        return []

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            f"GEMINI_API_KEY is missing. Check {PROJECT_ROOT / '.env'}."
        )

    client = genai.Client(api_key=api_key)
    embedded_chunks = []

    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        batch_number = start // BATCH_SIZE + 1
        texts = [chunk["text"] for chunk in batch]

        print(
            f"Embedding batch {batch_number}/{total_batches} "
            f"({len(batch)} chunks)..."
        )

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = client.models.embed_content(
                    model=MODEL_NAME,
                    contents=texts,
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT"
                    ),
                )
                break

            except ClientError as exc:
                status_code = getattr(exc, "code", None)

                # Retry transient quota/rate-limit errors with backoff.
                if status_code == 429 and attempt < MAX_RETRIES:
                    wait_seconds = 30 * (2**attempt)
                    print(
                        f"Gemini quota/rate limit reached. "
                        f"Waiting {wait_seconds}s before retry "
                        f"{attempt + 1}/{MAX_RETRIES}..."
                    )
                    time.sleep(wait_seconds)
                    continue

                if status_code == 429:
                    raise RuntimeError(
                        "Gemini embedding quota is still exhausted after "
                        "retries. Check your project's quota and usage at "
                        "https://ai.dev/rate-limit. No complete new index "
                        "has been confirmed."
                    ) from exc

                raise

        if not response.embeddings or len(response.embeddings) != len(batch):
            raise RuntimeError(
                f"Embedding count mismatch in batch {batch_number}: "
                f"expected {len(batch)}, received "
                f"{len(response.embeddings or [])}."
            )

        for chunk, embedding in zip(batch, response.embeddings):
            if embedding.values is None:
                raise RuntimeError(
                    f"Gemini returned an empty embedding in batch "
                    f"{batch_number}."
                )

            embedded_chunks.append(
                {
                    **chunk,
                    "embedding": embedding.values,
                }
            )

    print(f"Successfully embedded {len(embedded_chunks)} chunks.")
    return embedded_chunks
