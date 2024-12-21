import hashlib
import json
import os
import re
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from src.crawler.utils.logger import logger

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


def clean_json_response(raw_content):
    """
    Cleans the raw content of a response to ensure it's a valid JSON string.
    Handles cases where the response is encapsulated in a code block.
    """
    # Remove triple backticks or any surrounding code block markers
    cleaned_content = re.sub(r"^```(?:json)?\n?|\n?```$", "", raw_content.strip())
    return cleaned_content


def summarize_article_json(text, old_text=None):
    """Summarizes the article into JSON format using OpenAI's GPT model."""
    prompt = f"""
    You are a content creator who transforms educational content into engaging, motivating, and captivating summaries. Your task is to rewrite the following article in a way that:
    1. Provides a short teaser of no more than 200 characters to intrigue the reader.
    2. Summarizes the article in an engaging and motivating tone, keeping it concise but reflecting the unique style of the original content (e.g., humorous, critical, or light-hearted).
    3. Categorizes the article into one or more categories like "knowledge", "opinion", "news", "experience", "fun", etc., based on its content and tone.
    4. Adds relevant tags or keywords that describe the article.
    {"5. Describes changes between the old and new text if applicable." if old_text else ""}

    Return your response as a JSON object in this exact format:
    {{
        "teaser": "...",
        "summary_long": "...",
        "category": ["..."],
        "tags": ["...", "..."],
        "tone": ["..."]{"," if old_text else ""}
        {"\"teaser\": \"...\"" if old_text else ""}
    }}

    Article Text: {text}

    {"Old Text: " + old_text if old_text else ""}
    """

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a creative summarization assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    raw_content = response.choices[0].message.content
    cleaned_content = clean_json_response(raw_content)

    try:
        return json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        logger.error("Failed to decode JSON response: %s", e)
        return None


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
        entry.update(history[article_id])
    else:
        logger.info("Processing new or updated article: %s", article_id)

        # Generate JSON summary
        summary_json = summarize_article_json(text_to_summarize, old_text=previous_text)

        if summary_json:
            entry.update(summary_json)
            history[article_id] = {
                "hash": text_hash,
                "summary_text": text_to_summarize,
                "teaser": summary_json["teaser"],
                "summary_long": summary_json["summary_long"],
                "category": summary_json["category"],
                "tags": summary_json["tags"],
                "tone": summary_json["tone"],
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
            process_raw_data(os.path.join(RAW_DATA_FOLDER, filename), os.path.join("data/processed", filename), HISTORY_FILE)