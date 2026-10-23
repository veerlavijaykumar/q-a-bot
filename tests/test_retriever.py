
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from vector_store import save_vector_store
from retriever import retrieve_chunks


class TestRetriever(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_dir = Path(self.temp_dir.name)

        self.chunks = [
            {
                "text": "Python is a programming language.",
                "metadata": {
                    "source": "python.txt",
                    "page": None,
                    "chunk_index": 0,
                },
                "embedding": [1.0, 0.0, 0.0],
            },
            {
                "text": "FAISS searches vectors by similarity.",
                "metadata": {
                    "source": "faiss.pdf",
                    "page": 1,
                    "chunk_index": 1,
                },
                "embedding": [0.0, 1.0, 0.0],
            },
        ]

        save_vector_store(self.chunks, str(self.store_dir))

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("retriever.genai.Client")
    def test_retrieves_most_similar_chunk(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_embedding = MagicMock()
        mock_embedding.values = [1.0, 0.0, 0.0]

        mock_response = MagicMock()
        mock_response.embeddings = [mock_embedding]

        mock_client.models.embed_content.return_value = mock_response

        results = retrieve_chunks(
            "Tell me about Python",
            top_k=1,
            store_dir=str(self.store_dir),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["text"],
            "Python is a programming language.",
        )
        self.assertEqual(
            results[0]["metadata"]["source"],
            "python.txt",
        )
        self.assertAlmostEqual(results[0]["score"], 1.0, places=5)

    def test_empty_question_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "Question cannot be empty",
        ):
            retrieve_chunks(
                "   ",
                store_dir=str(self.store_dir),
            )

    def test_non_positive_top_k_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "top_k must be positive",
        ):
            retrieve_chunks(
                "Python",
                top_k=0,
                store_dir=str(self.store_dir),
            )

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("retriever.genai.Client")
    def test_missing_embedding_is_rejected(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.embeddings = []
        mock_client.models.embed_content.return_value = mock_response

        with self.assertRaisesRegex(
            RuntimeError,
            "No question embedding was returned",
        ):
            retrieve_chunks(
                "Python",
                store_dir=str(self.store_dir),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
