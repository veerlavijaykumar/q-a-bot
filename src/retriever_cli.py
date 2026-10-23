
from retriever import retrieve_chunks


def main():
    question = input("Ask a question: ").strip()

    results = retrieve_chunks(question, top_k=3)

    if not results:
        print("No matching chunks found.")
        return

    for rank, result in enumerate(results, start=1):
        metadata = result["metadata"]

        print(f"\n--- Result {rank} ---")
        print(f"Similarity score: {result['score']:.4f}")
        print(f"Source: {metadata['source']}")
        print(f"Page: {metadata['page']}")
        print(f"Text: {result['text'][:500]}")


if __name__ == "__main__":
    main()
