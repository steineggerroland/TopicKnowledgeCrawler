import json
import multiprocessing
import os
from datetime import datetime

from dotenv import load_dotenv

from src.crawler.utils.llm_prompter import LlmPrompter
from src.crawler.utils.logger import getLogger

# Initialize logger
logger = getLogger(__name__)

load_dotenv()
LLM_PROVIDER_NAME = os.getenv("LLM_PROVIDER", "ollama")  # Default to OpenAI

# Initialize the LLM prompter
llm_prompter = LlmPrompter(LLM_PROVIDER_NAME)


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


def load_markdown_content(markdown_path):
    """Loads the content of the Markdown file if it exists."""
    if os.path.exists(markdown_path):
        with open(markdown_path, "r", encoding="utf-8") as file:
            return file.read()
    return None


def process_raw_data(input_path, output_path, history_entry):
    """Processes a raw JSON file, generates summaries, and checks against history."""
    # Load raw article
    try:
        with open(input_path, "r") as file:
            entry = json.load(file)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in {input_path}: {e}")
        return

    # Calculate text hash
    article_id = entry.get("id", os.path.basename(input_path))
    text_hash = entry.get("content_hash")
    if not text_hash:
        logger.debug(f"No content detected for article: {article_id}. Skipping summarization.")
        return
    input_markdown_path = input_path.replace(".json", ".md")
    output_markdown_path = output_path.replace(".json", ".md")

    # Check history for existing summaries
    previous_hash = history_entry.get("hash", None)
    previous_text = load_markdown_content(output_markdown_path)

    if previous_hash == text_hash:
        logger.info(f"No changes detected for article: {article_id}. Skipping summarization.")
        entry.update(history_entry)
    else:
        logger.info(f'Processing new or updated article: {article_id} ({entry.get("title", "")})')

        # Load Markdown content if available
        markdown_content = load_markdown_content(input_markdown_path)

        if not markdown_content:
            logger.warning(f"No content available to summarize for article: {entry.get('id', 'Unknown')}")
            return

        with open(output_markdown_path, "w", encoding="utf-8") as md_file:
            md_file.write(markdown_content)

        try:
            # Generate JSON summary
            summary_json = llm_prompter.summarize_article_json(markdown_content, old_text=previous_text)
            assert all(
                key in summary_json for key in ["teaser", "summary_long", "category", "tags", "seriousness_rating"])

            if summary_json:
                entry.update(summary_json)
                history_entry = {
                    "hash": text_hash,
                    "summary_text": markdown_content,
                    "teaser": summary_json["teaser"],
                    "summary_long": summary_json["summary_long"],
                    "category": summary_json["category"],
                    "tags": summary_json["tags"],
                    "seriousness_rating": summary_json["seriousness_rating"],
                    "last_updated": datetime.now().isoformat(),
                }
        except Exception as e:
            logger.error("Failed to summarize article: %s. Skipping summarization: %s", article_id, e)

    # Save updated article
    with open(output_path, "w") as file:
        json.dump(entry, file, indent=4)
    return history_entry


execution_path = os.getcwd()
RAW_DATA_FOLDER = os.path.join(execution_path, "data/raw/")
PROCESSED_DATA_FOLDER = os.path.join("data/processed")
HISTORY_FILE = "data/summary_history.json"
history = load_summary_history(HISTORY_FILE)


def process_article(article_id):
    return {"id": article_id, "entry": process_raw_data(os.path.join(RAW_DATA_FOLDER, f"{article_id}.json"),
                                                        os.path.join(PROCESSED_DATA_FOLDER, f"{article_id}.json"),
                                                        history.get(article_id, {}) or {})}


if __name__ == "__main__":
    os.makedirs(os.path.dirname(PROCESSED_DATA_FOLDER), exist_ok=True)
    # Load history
    try:
        with multiprocessing.Pool(processes=1) as pool:
            results = pool.map(process_article, list(
                map(lambda f: f[0:-5], filter(lambda f: f.endswith(".json"), os.listdir(RAW_DATA_FOLDER)))))
            for result in list(filter(lambda r: r["entry"], results)):
                history[result["id"]] = result["entry"]
    except KeyboardInterrupt:
        logger.error("Stopping summarizing articles.")
    finally:
        save_summary_history(history, HISTORY_FILE)
