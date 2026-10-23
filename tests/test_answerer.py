
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "src"),
)

import answerer


class TestAnswerer(unittest.TestCase):

    def setUp(self):
        self.results = [
            {
                "text": "The candidate is a Software Developer Intern.",
                "metadata": {
                    "source": "sample.pdf",
                    "page": 2,
                },
                "score": 0.85,
            }
        ]

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("answerer.genai.Client")
    @patch("answerer.retrieve_chunks")
    def test_reuses_supplied_chunks(
        self,
        mock_retrieve,
        mock_client_class,
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_client.models.generate_content.return_value.text = (
            "The candidate is a Software Developer Intern "
            "[Source: sample.pdf, page 2]."
        )

        result = answerer.answer_question(
            "What is the candidate's role?",
            results=self.results,
        )

        self.assertIn("Software Developer Intern", result)

        # Supplied chunks should prevent another retrieval call.
        mock_retrieve.assert_not_called()

        # The source text and citation should reach the model prompt.
        prompt = (
            mock_client.models.generate_content.call_args.kwargs[
                "contents"
            ]
        )
        self.assertIn("sample.pdf, page 2", prompt)
        self.assertIn(
            "Software Developer Intern",
            prompt,
        )

    @patch("answerer.genai.Client")
    @patch("answerer.retrieve_chunks")
    def test_empty_results_refuse_to_answer(
        self,
        mock_retrieve,
        mock_client_class,
    ):
        mock_retrieve.return_value = []

        result = answerer.answer_question(
            "What is the answer?",
        )

        self.assertEqual(result, answerer.REFUSAL)
        mock_client_class.assert_not_called()

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
    @patch("answerer.genai.Client")
    @patch("answerer.retrieve_chunks")
    def test_retrieves_when_results_not_supplied(
        self,
        mock_retrieve,
        mock_client_class,
    ):
        mock_retrieve.return_value = self.results

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.models.generate_content.return_value.text = (
            "The candidate is a Software Developer Intern."
        )

        answerer.answer_question(
            "What is the candidate's role?",
        )

        mock_retrieve.assert_called_once()

    def test_empty_question_is_rejected(self):
        with self.assertRaises(ValueError):
            answerer.answer_question("   ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
