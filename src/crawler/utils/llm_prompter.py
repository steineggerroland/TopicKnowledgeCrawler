import json
import os
from functools import reduce
from logging import DEBUG

from dotenv import load_dotenv
from ollama import chat
from openai import OpenAI

from src.crawler.utils.logger import getLogger
from src.crawler.utils.text_processor import clean_json_response

# Initialize logger
logger = getLogger(__name__)
logger.setLevel(DEBUG)

load_dotenv()
MAX_TRIALS_PER_REQUEST = 2
CATEGORIES = ["factual information", "expert opinions", "debates and discussions", "entertainment/personal",
              "miscellaneous"]
RATINGS = ["high", "medium", "low"]


class LlmPrompter:
    def __init__(self, provider_name):
        self.provider_name = provider_name
        if provider_name == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif provider_name == "ollama":
            pass
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")

    def summarize_article_json(self, text, old_text=None) -> dict:
        if self.provider_name == "openai":
            return self._summarize_with_openai(text, old_text)
        elif self.provider_name == "ollama":
            return self._summarize_with_ollama(text, old_text)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider_name}")

    def _summarize_with_openai(self, text, old_text):
        prompt = self._build_prompt(text, old_text)

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system",
                     "content": "You are a creative summarization assistant and expert content analyst."},
                    {"role": "user", "content": prompt}
                ]
            )
        except Exception as exception:
            if 'context_length_exceeded' in str(exception):
                response = self.client.chat.completions.create(
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

    def _summarize_with_ollama(self, text, old_text):
        try:
            big_ollama_model = 'qwen2.5:14b'
            categories_and_tags = self._categorize_and_tag_text(big_ollama_model, text)
            rating = self._rate_text(big_ollama_model, text)
            teaser = self._summarize_text(big_ollama_model, text, old_text)
            return reduce(lambda x, y: {**x, **y}, [teaser, categories_and_tags, rating])
        except Exception as e:
            logger.error("Failed to summarize text: %s", e)

    def _summarize_text(self, big_ollama_model,  text, old_text):
        def is_answer_correct(answer):
            return answer and "teaser" in answer and "summary_long" in answer

        if old_text:
            logger.debug("Summarizing text with changes.")
        trials = 0
        summary = None
        while not is_answer_correct(summary) and trials < MAX_TRIALS_PER_REQUEST:
            try:
                response = chat(model=big_ollama_model,
                        messages=[{"role": "system", "content": "You are an incredible, successful content creator."},
                                  {"role": "system", "content": self._build_teaser_and_summary_system_prompt(text, None)},
                                  {"role": "user", "content": self._build_teaser_and_summary_user_prompt(text, None)}],
                                options={'temperature': 0.5})
                logger.debug("Summary response: %s", response)
                summary = json.loads(clean_json_response(response.message.content))
            except Exception as e:
                logger.debug("Summarizing attempt %s (response: '%s') failed: %s", trials, response or "", e)
            finally:
                trials += 1
        if not is_answer_correct(summary):
            raise "LLM failed to summarize text."
        return summary

    def _rate_text(self, big_ollama_model, text):
        def is_answer_correct(answer):
            return answer and "seriousness_rating" in answer and answer["seriousness_rating"] in RATINGS

        trials = 0
        rating = None
        while not is_answer_correct(rating) and trials < MAX_TRIALS_PER_REQUEST:
            try:
                response = chat(model=big_ollama_model,
                                messages=[{"role": "system", "content": "You are an expert content analyst."},
                                          {"role": "user", "content": self._build_serioussnessrating_prompt(text)}])
                logger.debug("Rating response: %s", response)
                rating = json.loads(clean_json_response(response.message.content))
                rating["seriousness_rating"] = rating["seriousness_rating"].lower()
            except Exception as e:
                logger.debug("Rating attempt %s (response: '%s') failed: %s", trials, response or "", e)
            finally:
                trials += 1
        if not is_answer_correct(rating):
            raise "LLM failed to rate text."
        return rating

    def _categorize_and_tag_text(self, big_ollama_model, text):
        def is_answer_correct(answer):
            return (answer and "category" in answer and "tags" in answer and
                    all(c in CATEGORIES for c in answer["category"]))

        trials = 0
        categories_and_tags = None
        while not is_answer_correct(categories_and_tags) and trials < MAX_TRIALS_PER_REQUEST:
            try:
                response = chat(model=big_ollama_model,
                                messages=[{"role": "system", "content": "You are an expert content analyst."},
                                          {"role": "user", "content": self._build_categorizing_prompt(text)}])
                logger.debug("Categorize response: %s", response)
                categories_and_tags = json.loads(clean_json_response(response.message.content))
            except Exception as e:
                logger.debug("Categorizing attempt %s (response: '%s') failed: %s", trials, response or "", e)
            finally:
                trials += 1
        if not is_answer_correct(categories_and_tags):
            raise "LLM failed to categorize text."
        return categories_and_tags

    def _build_prompt(self, text, old_text):
        changes_attribute_text = '"changes": "..."'
        return f'''
        You are an expert content analyst and a content creator who transforms educational content into engaging and well-organized summaries. Your task is to analyze the following article and:
        1. Provide a short teaser of no more than 200 characters to intrigue the reader.
        2. Summarize the article in an engaging and concise tone, while maintaining its unique style (e.g., factual, humorous, or critical).
        3. Categorize the article into one or more of the following categories: [{(",".join(CATEGORIES))}].
        4. Assign a seriousness rating to the article based on its credibility and reliability:
            • High: Credible and well-founded (e.g., academic articles, scientific studies).
            • Medium: Solid, but subjective or less verified (e.g., expert opinions, journalistic articles).
            • Low: Poorly founded, polemical, or possibly inaccurate (e.g., Reddit discussions, blog rants).
        5. Add relevant tags or keywords that describe the article content.
        {"6. Describe changes between the old and new text if applicable." if old_text else ""}

        Respond in this exact format:
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

    def _build_categorizing_prompt(self, text):
        return f'''
        You are an expert content analyst and a content creator who transforms educational content into engaging and well-organized summaries.

        Article Text: {text}
        
        
        Respond in this exact format:
        {{
            "category": ["...", "..."],
            "tags": ["...", "..."],
        }}
        
        Your task is to analyze the text and:
        1. Categorize the article into one or more of the following categories: ["factual information", "expert opinions", "debates and discussions", "entertainment/personal", "miscellaneous"].
        2. Add relevant tags or keywords that describe the article content.
        3. Don't use more than 5 tags.
        '''

    def _build_teaser_and_summary_system_prompt(self, text, old_text):
        return f'''
        You are a successful content creator who transforms educational content into engaging and well-organized summaries.

        '''
    def _build_teaser_and_summary_user_prompt(self, text, old_text):
        changes_attribute_text = '"changes": "..."'
        return f'''
        Summarize the following article: {text}

        {"Old Text of the article: " + old_text if old_text else ""}
        
        
        Respond in this exact format:
        {{
            "teaser": "...",
            "summary_long": "..."{"," if old_text else ""}
            {changes_attribute_text if old_text else ""}
        }}
        
        Your task is to summarize the text and:
        1. Provide a short teaser of no more than 200 characters to intrigue the reader.
        2. Summarize the article in an engaging and concise tone, while maintaining its unique style (e.g., factual, humorous, or critical).
        3. Do not alter quotes, short social media posts or similar.
        {"4. Describe changes between the old and new text if applicable." if old_text else ""}
        '''


    def _build_serioussnessrating_prompt(self, text):
        return f'''
        You are an expert content analyst and a content creator who transforms educational content into engaging and well-organized summaries. Your task is to analyze the following article and:
        1. Assign a seriousness rating to the article based on its credibility and reliability:
            • High: Credible and well-founded (e.g., academic articles, scientific studies).
            • Medium: Solid, but subjective or less verified (e.g., expert opinions, journalistic articles). It must be a known expert.
            • Low: Poorly founded, polemical, or possibly inaccurate (e.g., Reddit discussions, blog rants).

        Article Text: {text}
        
        
        Respond in this exact format:
        {{
            "seriousness_rating": "high/medium/low"
        }}
        '''
