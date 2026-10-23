import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

from answerer import answer_question, REFUSAL


class TestQAIntegration(unittest.TestCase):
    """End-to-end integration test for the Question-Answering pipeline."""

    @patch("answerer.retrieve_chunks")
    @patch("answerer.genai.Client")
    def test_qa_flow_with_citations(self, mock_client_cls, mock_retrieve):
        mock_retrieve.return_value = [
            {
                "text": "The GATE syllabus covers Algorithms and Data Structures.",
                "metadata": {"source": "GATE_CS_Syllabus.pdf", "page": 1},
                "score": 0.88,
            }
        ]
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.return_value.text = (
            "Algorithms and Data Structures are in the GATE syllabus (GATE_CS_Syllabus.pdf, page 1)."
        )

        ans = answer_question("What topics are in GATE?", top_k=1)
        self.assertIn("Algorithms", ans)
        mock_retrieve.assert_called_once_with("What topics are in GATE?", top_k=1)

    @patch("answerer.retrieve_chunks")
    def test_qa_flow_refusal_when_no_context(self, mock_retrieve):
        mock_retrieve.return_value = []
        ans = answer_question("Unanswerable question?")
        self.assertEqual(ans, REFUSAL)


if __name__ == "__main__":
    unittest.main()
