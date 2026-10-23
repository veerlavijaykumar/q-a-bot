
import json
from pathlib import Path

import faiss
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE_DIR = PROJECT_ROOT / "vector_store"


def _resolve_store_dir(store_dir: str | Path | None) -> Path:
    if store_dir is None:
        return DEFAULT_STORE_DIR
    p = Path(store_dir)
    if p.is_dir() or (p / "index.faiss").is_file():
        return p
    # If running from src/ and default was "../vector_store" or similar
    if (PROJECT_ROOT / p.name).is_dir() or (PROJECT_ROOT / p).is_dir():
        if (PROJECT_ROOT / p).exists():
            return PROJECT_ROOT / p
        return PROJECT_ROOT / p.name
    return p


def save_vector_store(
    embedded_chunks: list[dict],
    store_dir: str | Path | None = None,
) -> None:
    """Persist embeddings in FAISS and chunk data in JSON."""


    if not embedded_chunks:
        raise ValueError("No embedded chunks to save.")

    vectors = np.asarray(
        [chunk["embedding"] for chunk in embedded_chunks],
        dtype=np.float32,
    )

    if vectors.ndim != 2 or vectors.shape[1] == 0:
        raise ValueError("Embeddings must be non-empty vectors.")

    if not np.isfinite(vectors).all():
        raise ValueError("Embeddings contain invalid numbers.")

    # Normalize vectors so inner product gives cosine similarity.
    faiss.normalize_L2(vectors)

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    directory = _resolve_store_dir(store_dir)
    directory.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(directory / "index.faiss"))

    chunks_to_save = [
        {
            "text": chunk["text"],
            "metadata": chunk["metadata"],
        }
        for chunk in embedded_chunks
    ]

    with (directory / "chunks.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(chunks_to_save, file, ensure_ascii=False, indent=2)

    print(f"Saved {index.ntotal} vectors to {directory}")


def load_vector_store(
    store_dir: str | Path | None = None,
) -> tuple[faiss.Index, list[dict]]:
    """Load the saved FAISS index and corresponding chunk data."""

    directory = _resolve_store_dir(store_dir)
    index_path = directory / "index.faiss"
    chunks_path = directory / "chunks.json"

    if not index_path.is_file() or not chunks_path.is_file():
        raise FileNotFoundError(
            f"Vector store not found in {directory}. "
            "Run the indexing pipeline first."
        )

    index = faiss.read_index(str(index_path))

    with chunks_path.open("r", encoding="utf-8") as file:
        saved_chunks = json.load(file)

    if index.ntotal != len(saved_chunks):
        raise ValueError(
            "FAISS vector count does not match saved chunk count."
        )

    return index, saved_chunks
