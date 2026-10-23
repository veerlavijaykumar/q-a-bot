from answerer import answer_question
from retriever import retrieve_chunks


def main():
    print("=" * 60)
    print(" 📚 Document Q&A Bot (Interactive CLI)")
    print(" Type 'exit' or 'quit' to exit.")
    print("=" * 60)

    while True:
        question = input("\nYour question: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        if not question:
            continue

        try:
            # Step 1: Retrieve relevant source chunks
            results = retrieve_chunks(question, top_k=3)

            # Step 2: Generate the answer
            answer = answer_question(
                question,
                top_k=3,
                results=results,
            )

            # Step 3: Display the answer
            print("\nAnswer:")
            print(answer)

            # Step 4: Display the retrieved source chunks
            print("\nRetrieved source chunks:")

            if not results:
                print("No matching chunks found.")
            else:
                for rank, result in enumerate(results, start=1):
                    metadata = result["metadata"]

                    print(f"\n--- Source {rank} ---")
                    print(f"Filename: {metadata.get('source', 'Unknown')}")
                    print(f"Page: {metadata.get('page', 'N/A')}")
                    print(f"Similarity score: {result['score']:.4f}")
                    print(f"Text:\n{result['text']}")

        except Exception as error:
            print(f"\nError: {error}")


if __name__ == "__main__":
    main()
