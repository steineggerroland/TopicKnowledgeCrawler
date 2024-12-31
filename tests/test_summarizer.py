import json
import os
import shutil
from unittest.mock import patch

import pytest

from src.crawler.summarizer import process_raw_data, load_summary_history, save_summary_history

RAW_DIR = "tests/fixtures/raw/"
PROCESSED_DIR = "tests/fixtures/processed/"
SUMMARY_HISTORY_FILE = "tests/fixtures/summary_history.json"


@pytest.fixture
def setup_test_environment():
    """Sets up the test environment: directories and files."""
    # Clean up old test data
    if os.path.exists(RAW_DIR):
        shutil.rmtree(RAW_DIR)
    if os.path.exists(PROCESSED_DIR):
        shutil.rmtree(PROCESSED_DIR)
    if os.path.exists(SUMMARY_HISTORY_FILE):
        os.remove(SUMMARY_HISTORY_FILE)

    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # Mock raw files
    raw_data_1 = {
        "id": "article_1",
        "summary": "This is the first test article summary."
    }
    raw_data_2 = {
        "id": "article_2",
        "summary": "This is the second test article summary."
    }

    with open(os.path.join(RAW_DIR, "article_1.json"), "w") as f:
        json.dump(raw_data_1, f)
    with open(os.path.join(RAW_DIR, "article_2.json"), "w") as f:
        json.dump(raw_data_2, f)

    # Mock initial summary history
    with open(SUMMARY_HISTORY_FILE, "w") as f:
        json.dump({}, f)

    yield

    # Clean up after tests
    shutil.rmtree(RAW_DIR)
    shutil.rmtree(PROCESSED_DIR)
    if os.path.exists(SUMMARY_HISTORY_FILE):
        os.remove(SUMMARY_HISTORY_FILE)


@patch("src.crawler.summarizer.summarize_article_json")
def test_process_all_raw_files(mock_summarize_text, setup_test_environment):
    """Test that all raw files are processed correctly and saved."""
    # Mock the OpenAI API response
    mock_summarize_text.return_value = {'teaser': 'Some teaser', 'summary_long': 'Long summary', 'category': 'category', 'tags': ['test'],'tone': ['informative']}

    # Process files
    raw_files = os.listdir(RAW_DIR)
    for file_name in raw_files:
        input_path = os.path.join(RAW_DIR, file_name)
        output_path = os.path.join(PROCESSED_DIR, file_name)
        process_raw_data(input_path, output_path, SUMMARY_HISTORY_FILE)

    # Assertions
    processed_files = os.listdir(PROCESSED_DIR)
    assert len(processed_files) == len(raw_files)

    for file_name in raw_files:
        output_path = os.path.join(PROCESSED_DIR, file_name)
        assert os.path.exists(output_path)

        with open(output_path, "r") as f:
            data = json.load(f)
            assert "teaser" in data
            assert "summary_long" in data


def test_summary_history_update(setup_test_environment):
    """Test that the summary history file is updated correctly."""
    test_history_file = SUMMARY_HISTORY_FILE

    history = load_summary_history(test_history_file)
    assert history == {}  # Initially empty

    # Update history
    new_entry = {
        "hash": "mocked_hash",
        "summary_text": "This is a mock article.",
        "summary_short": "Mock short summary",
        "summary_long": "Mock long summary",
        "last_updated": "2024-06-06T10:00:00"
    }
    history["article_1"] = new_entry
    save_summary_history(history, test_history_file)

    # Reload and verify
    updated_history = load_summary_history(test_history_file)
    assert "article_1" in updated_history
    assert updated_history["article_1"]["summary_short"] == "Mock short summary"


@patch("src.crawler.summarizer.summarize_article_json")
def test_changes_detection(mock_summarize_text, setup_test_environment):
    """Test that changes in text trigger the 'changes' summary."""
    # Initial raw data
    raw_data = {
        "id": "article_1",
        "summary": "This is the first version of the summary."
    }
    with open(os.path.join(RAW_DIR, "article_1.json"), "w") as f:
        json.dump(raw_data, f)

    # Initial summary history
    initial_history = {
        "article_1": {
            "hash": "old_hash",
            "summary_text": "This is the old version of the summary.",
            "teaser": "Old short summary",
            "summary_long": "Old long summary"
        }
    }
    with open(SUMMARY_HISTORY_FILE, "w") as f:
        json.dump(initial_history, f)

    # Mock summarize_text responses
    mock_summarize_text.return_value = {'teaser': 'Some teaser', 'summary_long': 'Long summary', 'category': 'category', 'tags': ['test'],'tone': ['informative']}

    # Process file
    input_path = os.path.join(RAW_DIR, "article_1.json")
    output_path = os.path.join(PROCESSED_DIR, "article_1.json")
    process_raw_data(
        input_path=input_path,
        output_path=output_path,
        history_file=SUMMARY_HISTORY_FILE
    )

    # Verify history update
    updated_history = load_summary_history(SUMMARY_HISTORY_FILE)
    assert "article_1" in updated_history
    assert updated_history["article_1"]["summary_text"] == "This is the first version of the summary."
