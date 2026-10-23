
from pathlib import Path

from loader import load_documents
from chunker import chunk_documents
from embeddings import embed_chunks
from vector_store import save_vector_store

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_index(
    data_dir: str | Path | None = None,
    store_dir: str | Path | None = None,
    chunk_size: int = 500,
    overlap: int = 100,
) -> dict:
    """Load documents, chunk them, embed, and persist to FAISS vector store."""
    resolved_data_dir = Path(data_dir) if data_dir else PROJECT_ROOT / "data"
    if not resolved_data_dir.is_dir() and (PROJECT_ROOT / resolved_data_dir.name).is_dir():
        resolved_data_dir = PROJECT_ROOT / resolved_data_dir.name

    resolved_store_dir = Path(store_dir) if store_dir else PROJECT_ROOT / "vector_store"
    if not resolved_store_dir.is_dir() and (PROJECT_ROOT / resolved_store_dir.name).is_dir():
        resolved_store_dir = PROJECT_ROOT / resolved_store_dir.name

    print(f"Step 1: Loading documents from {resolved_data_dir}...")
    documents = load_documents(resolved_data_dir)

    if not documents:
        raise ValueError("No document records were loaded.")

    print(f"Loaded records: {len(documents)}")

    print("\nStep 2: Creating chunks...")
    chunks = chunk_documents(
        documents,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    if not chunks:
        raise ValueError("No chunks were generated.")

    print(f"Generated chunks: {len(chunks)}")

    print("\nStep 3: Generating embeddings...")
    embedded_chunks = embed_chunks(chunks)

    if len(embedded_chunks) != len(chunks):
        raise RuntimeError("Some chunks did not receive embeddings.")

    print(f"Embedded chunks: {len(embedded_chunks)}")

    print(f"\nStep 4: Saving vector store to {resolved_store_dir}...")
    save_vector_store(embedded_chunks, resolved_store_dir)

    sources = sorted({doc["metadata"]["source"] for doc in documents})
    print("\nIndexing completed successfully!")
    return {
        "status": "success",
        "documents_count": len(sources),
        "pages_or_records": len(documents),
        "chunks_count": len(chunks),
        "sources": sources,
        "store_dir": str(resolved_store_dir),
    }


def main():
    build_index()


if __name__ == "__main__":
    main()

