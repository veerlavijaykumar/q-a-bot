
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from vector_store import save_vector_store, load_vector_store


class TestVectorStore(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store_dir = Path(self.temp_dir.name)

        self.chunks = [
            {
                "text": "Python is a programming language.",
                "metadata": {
                    "source": "sample.txt",
                    "page": None,
                    "chunk_index": 0,
                },
                "embedding": [1.0, 0.0, 0.0],
            },
            {
                "text": "FAISS performs vector similarity search.",
                "metadata": {
                    "source": "sample.pdf",
                    "page": 1,
                    "chunk_index": 1,
                },
                "embedding": [0.0, 1.0, 0.0],
            },
        ]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_load_vector_store(self):
        save_vector_store(self.chunks, str(self.store_dir))

        index, saved_chunks = load_vector_store(
            str(self.store_dir)
        )

        self.assertEqual(index.ntotal, 2)
        self.assertEqual(len(saved_chunks), 2)
        self.assertEqual(
            saved_chunks[0]["text"],
            self.chunks[0]["text"],
        )
        self.assertEqual(
            saved_chunks[1]["metadata"]["source"],
            "sample.pdf",
        )

    def test_saved_index_supports_similarity_search(self):
        save_vector_store(self.chunks, str(self.store_dir))

        index, _ = load_vector_store(str(self.store_dir))

        query = np.asarray(
            [[1.0, 0.0, 0.0]],
            dtype=np.float32,
        )
        import faiss
        faiss.normalize_L2(query)

        scores, indices = index.search(query, 1)

        self.assertEqual(int(indices[0][0]), 0)
        self.assertAlmostEqual(float(scores[0][0]), 1.0, places=5)

    def test_missing_store_raises_error(self):
        with self.assertRaises(FileNotFoundError):
            load_vector_store(
                str(self.store_dir / "missing")
            )

    def test_empty_input_is_rejected(self):
        with self.assertRaises(ValueError):
            save_vector_store([], str(self.store_dir))


if __name__ == "__main__":
    unittest.main(verbosity=2)
