
from loader import load_documents
from chunker import chunk_documents
from embeddings import embed_chunks


def main():
    documents = load_documents("../data")

    print(f"Loaded records: {len(documents)}")

    chunks = chunk_documents(
        documents,
        chunk_size=500,
        overlap=100,
    )

    # print(f"Generated chunks: {len(chunks)}")

    # if chunks:
    #     first_chunk = chunks[10]

    #     print("\nFirst chunk metadata:")
    #     print(first_chunk["metadata"])

    #     print("\nFirst chunk text preview:")
    #     print(first_chunk["text"][:200])

    #     print("\nAll source files:")
    #     sources = sorted({
    #         chunk["metadata"]["source"]
    #         for chunk in chunks
    #     })

    #     for source in sources:
    #         print(f"- {source}")
    print(embed_chunks([chunks[0]]))


if __name__ == "__main__":
    main()
