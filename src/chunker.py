
def chunk_documents(
    documents: list[dict],
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[dict]:
    """Create overlapping chunks while preferring natural text boundaries."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    chunks = []
    step = chunk_size - overlap

    for document in documents:
        text = document["text"]
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Prefer ending at a natural boundary.
            if end < len(text):
                window = text[start:end]
                boundaries = [
                    window.rfind("\n"),
                    window.rfind(". "),
                    window.rfind("? "),
                    window.rfind("! "),
                    window.rfind(" "),
                ]

                boundary = max(boundaries)

                # Avoid creating tiny chunks from early boundaries.
                if boundary >= chunk_size // 2:
                    end = start + boundary + 1

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        **document["metadata"],
                        "chunk_index": len(chunks),
                        "start_char": start,
                        "end_char": end,
                    },
                })

            if end >= len(text):
                break

            # Move forward while preserving approximate overlap.
            next_start = max(start + 1, end - overlap)

            # Prefer starting at a natural boundary, too.
            search_end = min(next_start + overlap, len(text))
            remaining = text[next_start:search_end]

            boundaries = [
                pos for pos in (
                    remaining.find("\n"),
                    remaining.find(". "),
                    remaining.find("? "),
                    remaining.find("! "),
                    remaining.find(" "),
                )
                if pos >= 0
            ]

            if boundaries:
                next_start += min(boundaries) + 1

            start = next_start

    return chunks
