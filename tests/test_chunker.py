
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from chunker import chunk_documents


class TestChunker(unittest.TestCase):
    def test_chunking_and_overlap(self):
        text = "A" * 1200

        documents = [
            {
                "text": text,
                "metadata": {
                    "source": "sample.pdf",
                    "page": 1,
                    "file_type": "pdf",
                },
            }
        ]

        chunks = chunk_documents(
            documents,
            chunk_size=500,
            overlap=100,
        )

        # Check the number of chunks
        self.assertEqual(len(chunks), 3)

        # Check the first chunk's size
        self.assertEqual(len(chunks[0]["text"]), 500)

        # Check the 100-character overlap
        self.assertEqual(chunks[0]["text"][400:], chunks[1]["text"][:100])

        # Check metadata preservation
        self.assertEqual(chunks[0]["metadata"]["source"], "sample.pdf")
        self.assertEqual(chunks[0]["metadata"]["page"], 1)


if __name__ == "__main__":
    unittest.main()

