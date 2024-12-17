import os
import hashlib
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from utils.logger import logger

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)


def load_summary_history(history_file):
    """Loads the summary history file, or returns an empty dictionary if it doesn't exist."""
    if os.path.exists(history_file):
        with open(history_file, "r") as file:
            return json.load(file)
    return {}


def save_summary_history(history, history_file):
    """Saves the updated summary history to the file."""
    with open(history_file, "w") as file:
        json.dump(history, file, indent=4)


def calculate_hash(text):
    """Generates a SHA256 hash for the given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def summarize_text(text, mode="short", old_text=None):
    """Summarizes the text using OpenAI's GPT model."""
    if mode == "short":
        prompt = f"Summarize this article:\n{text}\n\nUse less than 200 characters."
    elif mode == "long":
        prompt = f"Summarize this article:\n{text}\n\nExplain the key points in detail."
    elif mode == "changes":
        prompt = (
            f"Briefly describe the changes between the old and new versions of the text.\n\n"
            f"Old Text:\n{old_text}\n\nNew Text:\n{text}\n\nFocus on the main differences."
        )
    else:
        raise ValueError("Invalid mode specified.")

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a summarization and comparison assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


def process_raw_data(input_path, output_path, history_file):
    """Processes a raw JSON file, generates summaries, and checks against history."""
    # Load history
    history = load_summary_history(history_file)

    # Load raw article
    with open(input_path, "r") as file:
        entry = json.load(file)

    # Calculate text hash
    text_to_summarize = entry.get("summary", "")
    text_hash = calculate_hash(text_to_summarize)

    # Check history for existing summaries
    article_id = entry.get("id", os.path.basename(input_path))
    previous_hash = history.get(article_id, {}).get("hash")
    previous_text = history.get(article_id, {}).get("summary_text")

    if previous_hash == text_hash:
        logger.info("No changes detected for article: %s. Skipping summarization.", article_id)
        entry["summary_short"] = history[article_id]["summary_short"]
        entry["summary_long"] = history[article_id]["summary_long"]
    else:
        if previous_text:  # If previous text exists, describe the changes
            logger.info("Updated text detected for article: %s. Generating summaries...", article_id)
            entry["summary_changes"] = summarize_text(
                text_to_summarize, mode="changes", old_text=previous_text
            )
        else:
            logger.info("New text detected for article: %s. Generating summaries...", article_id)

        # Generate summaries
        entry["summary_short"] = summarize_text(text_to_summarize, mode="short")
        entry["summary_long"] = summarize_text(text_to_summarize, mode="long")

        # Update history
        history[article_id] = {
            "hash": text_hash,
            "summary_text": text_to_summarize,
            "summary_short": entry["summary_short"],
            "summary_long": entry["summary_long"],
            "last_updated": datetime.now().isoformat()
        }

    # Save updated article
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as file:
        json.dump(entry, file, indent=4)

    # Save updated history
    save_summary_history(history, history_file)

if __name__ == "__main__":
    HISTORY_FILE = "data/summary_history.json"

    execution_path = os.getcwd()
    RAW_DATA_FOLDER = os.path.join(execution_path, "data/raw/")
    for filename in os.listdir(RAW_DATA_FOLDER):
        if filename.endswith(".json"):
            process_raw_data(os.path.join("data/raw", filename), os.path.join("data/processed", filename), HISTORY_FILE)
