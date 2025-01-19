import json
import multiprocessing
import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from src.crawler.utils.logger import getLogger
from src.crawler.utils.text_processor import clean_json_response

# Initialize logger
logger = getLogger(__name__)

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


def load_markdown_content(markdown_path):
    """Loads the content of the Markdown file if it exists."""
    if os.path.exists(markdown_path):
        with open(markdown_path, "r", encoding="utf-8") as file:
            return file.read()
    return None


def summarize_article_json(text, old_text=None):
    """Summarizes the article into JSON format using OpenAI's GPT model."""
    changes_attribute_text = "\"changes\": \"...\""
    prompt = f'''
    You are an expert content analyst and a content creator who transforms educational content into engaging and well-organized summaries. Your task is to analyze the following article and:
    1. Provide a short teaser of no more than 200 characters to intrigue the reader.
    2. Summarize the article in an engaging and concise tone, while maintaining its unique style (e.g., factual, humorous, or critical).
    3. Categorize the article into one or more of the following categories: ["factual information", "expert opinions", "debates and discussions", "entertainment/personal", "miscellaneous"].
    4. Assign a seriousness rating to the article based on its credibility and reliability:
        • High: Credible and well-founded (e.g., academic articles, scientific studies).
        • Medium: Solid, but subjective or less verified (e.g., expert opinions, journalistic articles).
        • Low: Poorly founded, polemical, or possibly inaccurate (e.g., Reddit discussions, blog rants).
    5. Add relevant tags or keywords that describe the article content.
    {"6. Describe changes between the old and new text if applicable." if old_text else ""}

    Return your response as a JSON object in this exact format:
    {{
        "teaser": "...",
        "summary_long": "...",
        "category": ["..."],
        "tags": ["...", "..."],
        "seriousness_rating": "high/medium/low"{"," if old_text else ""}
        {changes_attribute_text if old_text else ""}
    }}

    Article Text: {text}

    {"Old Text: " + old_text if old_text else ""}
    '''

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative summarization assistant and expert content analyst."},
                {"role": "user", "content": prompt}
            ]
        )
    except Exception as exception:
        if 'context_length_exceeded' in str(exception):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system",
                     "content": "You are a creative summarization assistant and expert content analyst."},
                    {"role": "user", "content": prompt}
                ]
            )
        else:
            raise exception

    raw_content = response.choices[0].message.content
    cleaned_content = clean_json_response(raw_content)

    try:
        return json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        logger.error("Failed to decode JSON response: %s", e)
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
            summary_json = summarize_article_json(markdown_content, old_text=previous_text)
            assert all(key in summary_json for key in ["teaser", "summary_long", "category", "tags", "seriousness_rating"])

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
    with multiprocessing.Pool() as pool:
        results = pool.map(process_article, list(
            map(lambda f: f[0:-5], filter(lambda f: f.endswith(".json"), os.listdir(RAW_DATA_FOLDER)))))
        for result in list(filter(lambda r: r["entry"], results)):
            history[result["id"]] = result["entry"]

    save_summary_history(history, HISTORY_FILE)
