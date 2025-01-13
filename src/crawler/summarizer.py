import hashlib
import json
import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from src.crawler.utils.logger import logger
from src.crawler.utils.sanitize import clean_json_response

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




def summarize_article_json(text, old_text=None):
    """Summarizes the article into JSON format using OpenAI's GPT model."""
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
        "seriousness_rating": "high/medium/low"
        {", " if old_text else ""}
        {"\"changes\": \"...\"" if old_text else ""}
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
                    {"role": "system", "content": "You are a creative summarization assistant and expert content analyst."},
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
        logger.info(f'Processing new or updated article: %s ({entry.get("title", "")})', article_id)
        try:
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
        except:
            logger.error("Failed to summarize article: %s. Skipping summarization.", article_id)

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