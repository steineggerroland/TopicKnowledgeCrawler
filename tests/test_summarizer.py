import unittest
from unittest.mock import patch
from unittest.mock import patch, mock_open, MagicMock

from src.crawler.summarizer import process_raw_data, summarize_article_json, calculate_hash


@patch(
    "src.crawler.summarizer.client.chat.completions.create",
    return_value=MagicMock(choices=[MagicMock(message=MagicMock(content='{"teaser": "test"}'))]),
)
class TestSummarizerBasicFunctionality(unittest.TestCase):

    @patch("os.makedirs")
    @patch("os.path.exists", side_effect=lambda p: p == "article.md")
    @patch("builtins.open", new_callable=mock_open, read_data="# Test Article\n\nContent")
    def test_happy_path(self, mock_open, mock_exists, mock_makedirs, mock_openai):
        # Given
        input_path = "article.json"
        output_path = "processed_article.json"
        entry = {"id": "1", "summary": "Fallback content."}
        with patch("json.load", return_value=entry):
            # When
            process_raw_data(input_path, output_path, {})

            # Then
            mock_open.assert_any_call("article.md", "r", encoding="utf-8")

    @patch("os.makedirs")
    @patch("os.path.exists", side_effect=lambda p: p == "article.json")
    @patch("builtins.open", new_callable=mock_open, read_data="# Test Article\n\n")
    def test_fallback_to_summary_if_markdown_not_found(self, mock_makedirs, mock_exists, mock_file, mock_openai):
        # Given
        input_path = "article.json"
        output_path = "processed_article.json"
        entry = {"id": "1", "title": "Title", "summary": "Fallback content."}
        with patch("json.load", return_value=entry):
            with patch("src.crawler.summarizer.logger.info") as mock_logger:
                # When
                process_raw_data(input_path, output_path, {})

                # Then
                mock_logger.assert_any_call(f"Processing new or updated article: {entry['id']} (Title)")

    @patch("os.makedirs")
    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="# Test Article\n\n")
    def test_fallback_to_summary_if_markdown_is_empty(self, mock_open, mock_exists, mock_makedirs, mock_openai):
        # Given
        input_path = "article.json"
        output_path = "processed_article.json"
        entry = {"id": "1", "summary": "Fallback content."}
        with patch("json.load", return_value=entry):
            # When
            process_raw_data(input_path, output_path, {})

            # Then
            mock_open.assert_any_call("article.md", "r", encoding="utf-8")


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
        entry = {"id": "1", "summary": "Test content."}
        history = {"1": {"hash": calculate_hash("Test content.")}}
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
        entry = {"id": "1", "title": "Title", "summary": "New content."}
        history = {"1": {"hash": calculate_hash("Old content.")}}
        with patch("json.load", side_effect=[entry]), patch(
                "src.crawler.summarizer.logger.info") as mock_logger:
            # When
            process_raw_data(input_path, output_path, history)

            # Then
            mock_logger.assert_any_call("Processing new or updated article: 1 (Title)")



if __name__ == "__main__":
    unittest.main()
