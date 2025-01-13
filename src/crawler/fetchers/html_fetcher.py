import json
from datetime import datetime
from hashlib import sha256
from urllib.parse import urljoin

import requests
import trafilatura
from bs4 import BeautifulSoup

from src.crawler.utils.logger import getLogger

# Initialize logger
logger = getLogger(__name__)


class HtmlFetcher:
    def __init__(self, source_config):
        self.source_config = source_config

    def fetch(self):
        """
        Fetch articles based on the source configuration.
        """
        try:
            logger.debug(f"Fetching articles from {self.source_config['url']}")
            main_page_html = self._fetch_html(self.source_config["url"])

            # Parse main page to extract articles
            article_blocks = self.extract_article_blocks(main_page_html)
            articles = [self.process_article_block(block) for block in article_blocks]

            return [article for article in articles if article]  # Filter out None articles
        except Exception as e:
            logger.error(f"Error fetching articles from {self.source_config['url']}: {e}")
            return []

    def _fetch_html(self, url):
        """
        Fetch the HTML content of a given URL.
        """
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch HTML content. Status code: {response.status_code}")
        return response.text

    def extract_article_blocks(self, html):
        """
        Extract the article blocks using the article_selector.
        """
        soup = BeautifulSoup(html, "html.parser")
        article_selector = self.source_config["configuration"]["article_selector"]
        return soup.select(article_selector)

    def process_article_block(self, article_block):
        """
        Process a single article block to extract details and content.
        """
        try:
            # Extract the main page link
            anchor_selector = self.source_config["configuration"]["main_page_anchor_selector"]
            anchor_element = article_block.select_one(anchor_selector)
            if not anchor_element:
                logger.warning("Could not find main page anchor for article.")
                return None

            main_page_url = urljoin(self.source_config["url"], anchor_element.get("href"))
            logger.debug(f'Fetching article from "{main_page_url}".')

            # Fetch article details
            article = self.extract_article_content(main_page_url)
            if not article:
                logger.warning(f"Could not extract content from page: {main_page_url}")
                return None

            # Add Markdown content
            article["content_md"] = self.generate_markdown_from_url(main_page_url)

            return article
        except Exception as e:
            logger.error(f"Error processing article block: {e}")
            return None

    def extract_article_content(self, url):
        """
        Extract article content using trafilatura.
        """
        try:
            html = self._fetch_html(url)
            # Extract article content and metadata
            result = trafilatura.extract(
                html,
                with_metadata=True,
                include_links=True,
                include_images=True,
                include_formatting=True,
                output_format='json'
            )
            if not result:
                logger.warning("trafilatura could not extract content")
                return None

            json_result = json.loads(result)

            # Extract relevant fields
            title = json_result.get("title")
            summary = json_result.get("raw_text")
            published_at_raw = json_result.get("date")
            updated_at_raw = json_result.get("last-modified")
            author = json_result.get("author")

            # Parse and format dates
            published_at = self.parse_date(published_at_raw)
            updated_at = self.parse_date(updated_at_raw)

            # Generate a unique ID based on the URL
            article_id = sha256(url.encode("utf-8")).hexdigest()

            # Return the structured article data
            return {
                "title": title,
                "link": url,
                "summary": summary,
                "publishedAt": published_at,
                "updatedAt": updated_at,
                "id": article_id,
                "author": author
            }
        except Exception as e:
            logger.error(f"Error extracting article content for {url}: {e}")
            return None

    @staticmethod
    def generate_markdown_from_url(url):
        """
        Fetches a webpage and converts its content into Markdown using trafilatura.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            html_content = response.text

            markdown = trafilatura.extract(
                html_content,
                include_formatting=True,
                include_links=True,
                include_images=True,
                output_format="markdown"
            )
            if markdown:
                return markdown
            else:
                logger.warning("Failed to extract content as Markdown for URL: %s", url)
                return "No content available."
        except Exception as e:
            logger.error("Error fetching or converting URL to Markdown: %s", str(e))
            return "No content available."

    @staticmethod
    def parse_date(date_str):
        """
        Helper method to parse dates into ISO 8601 format.
        """
        if not date_str:
            return None
        try:
            parsed_date = datetime.fromisoformat(date_str)
            return parsed_date.isoformat()
        except ValueError:
            try:
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                return parsed_date.isoformat()
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                return None
