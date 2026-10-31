
import os
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv
from google import genai
from google.genai import types

from vector_store import load_vector_store

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env", override=True)

MODEL_NAME = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")


def retrieve_chunks(
    question: str,
    top_k: int = 5,
    store_dir: str | Path | None = None,
) -> list[dict]:
    """Retrieve the most relevant chunks for a question."""

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    # Load the existing index and saved chunk records.
    index, chunks = load_vector_store(store_dir)

    if not chunks:
        return []

    # Prepare the Gemini client.
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing.")

    client = genai.Client(api_key=api_key)

    # Embed the question using the query task type.
    response = client.models.embed_content(
        model=MODEL_NAME,
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY"
        ),
    )

    if not response.embeddings:
        raise RuntimeError("No question embedding was returned.")

    query_vector = np.asarray(
        [response.embeddings[0].values],
        dtype=np.float32,
    )

    if query_vector.shape[1] != index.d:
        raise ValueError(
            "Question embedding dimensions do not match "
            "the stored index."
        )

    # Normalize the query the same way as document vectors.
    faiss.normalize_L2(query_vector)

    # Search for the most similar stored vectors.
    result_count = min(top_k, index.ntotal)
    scores, indices = index.search(query_vector, result_count)

    results = []

    for score, chunk_index in zip(scores[0], indices[0]):
        if chunk_index < 0:
            continue

        chunk = chunks[int(chunk_index)]

        results.append({
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "score": float(score),
        })

    return results
