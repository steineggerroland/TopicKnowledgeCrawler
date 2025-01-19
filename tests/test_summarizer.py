import unittest
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock

from src.crawler.summarizer import process_raw_data
from src.crawler.utils.text_processor import calculate_hash


@patch(
    "src.crawler.summarizer.client.chat.completions.create",
    return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='{"teaser": "test", "summary_long": "Long text", "category": "[\\"Test\\", \\"TDD\\"]", "tags": "[\\"Testing\\",\\"Test\\"]", "seriousness_rating": "low"}'))]),
)
class TestSummarizerBasicFunctionality(unittest.TestCase):

    @patch("os.makedirs")
    @patch("os.path.exists", side_effect=lambda p: p == "article.md")
    @patch("builtins.open", new_callable=mock_open, read_data="# Test Article\n\nContent")
    def test_happy_path(self, mock_open, mock_exists, mock_makedirs, mock_openai):
        # Given
        input_path = "article.json"
        output_path = "processed_article.json"
        markdown_output_path = "processed_article.json"
        entry = {"id": "1", "content_hash": "hash123"}
        with patch("json.load", return_value=entry):
            # When
            result = process_raw_data(input_path, output_path, {})

            # Then
            mock_open.assert_called_with(output_path, "w")
            mock_open.assert_called_with(markdown_output_path, "w")
            diff_last_updated_to_now = (datetime.fromisoformat(result["last_updated"]) - datetime.now()).total_seconds()
            self.assertAlmostEqual(diff_last_updated_to_now, 0, 1)
            self.assertEqual(result["hash"], "hash123")


@patch(
    "src.crawler.summarizer.client.chat.completions.create",
    return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='{"teaser": "test"}'))]),
)
class TestSummarizerHashAndHistory(unittest.TestCase):

    @patch("os.path.exists", side_effect=lambda p: p == "article.json")
    @patch("builtins.open", new_callable=mock_open)
    def test_unchanged_content_skips_processing(self, mock_exists, mock_open, mock_openai):
        # Given
        input_path = "article.json"
        output_path = "processed_article.json"
        entry = {"id": "1", "content_hash": "hash123"}
        history = {"hash": "hash123"}
        with patch("json.load", side_effect=[entry]), patch(
                "src.crawler.summarizer.logger.info") as mock_logger:
            # When
            process_raw_data(input_path, output_path, history)

            # Then
            mock_logger.assert_any_call("No changes detected for article: 1. Skipping summarization.")

    @patch("os.path.exists", side_effect=lambda p: p == "article.json")
    @patch("builtins.open", new_callable=mock_open)
    def test_changed_content_triggers_processing(self, mock_exists, mock_open, mock_openai):
        # Given
        input_path = "article.json"
        output_path = "processed_article.json"
        entry = {"id": "1", "title": "Title", "content_hash": "hash123"}
        history = {"hash": calculate_hash("Old content.")}
        with patch("json.load", side_effect=[entry]), patch(
                "src.crawler.summarizer.logger.info") as mock_logger:
            # When
            process_raw_data(input_path, output_path, history)

            # Then
            mock_logger.assert_any_call("Processing new or updated article: 1 (Title)")


if __name__ == "__main__":
    unittest.main()
