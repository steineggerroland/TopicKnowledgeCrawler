import json
from datetime import datetime
from hashlib import sha256
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup

from crawler.utils import text_processor
from crawler.utils.logger import getLogger

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

            if not article_blocks:
                logger.error("No article blocks found on the page.")
                return []

            articles = []
            for block in article_blocks:
                try:
                    article = self.process_article_block(block)
                    if article and article["link"] not in (a["link"] for a in articles):
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Error processing article block: {e}")

            return articles
        except Exception as e:
            logger.error(f"Error fetching articles from {self.source_config['url']}: {e}")
            return []

    def extract_article_blocks(self, html):
        """
        Extract the article blocks using the article_selector.
        """
        soup = BeautifulSoup(html, "html.parser")
        article_selector = self.source_config["configuration"].get("article_selector", "")
        if not article_selector:
            logger.error("No article selector provided in configuration.")
            return []
        return soup.select(article_selector)

    def process_article_block(self, article_block):
        """
        Process a single article block to extract details and content.
        """
        try:
            # Extract the main page link
            anchor_selector = self.source_config["configuration"].get("main_page_anchor_selector", "")
            anchor_element = article_block.select_one(anchor_selector)

            if not anchor_element or not anchor_element.get("href"):
                logger.warning("Could not find a valid main page anchor for article.")
                return None

            # Sanitize the link
            raw_url = urljoin(self.source_config["url"], anchor_element.get("href"))
            sanitized_url = self.sanitize_link(raw_url)

            logger.debug(f"Fetching article from sanitized URL: {sanitized_url}")

            # Fetch article details
            article = self.extract_article_meta(sanitized_url)
            if not article:
                logger.warning(f"Failed to extract content from page: {sanitized_url}")
                return None

            # Add sanitized link to article
            article["link"] = sanitized_url

            # Add Markdown content
            try:
                article["content_md"] = self.generate_markdown_from_url(sanitized_url)
            except Exception as e:
                logger.warning(f"Markdown generation failed for article {article}: {e}")
                raise e

            return article
        except Exception as e:
            logger.error(f"Error processing article block: {e}")
            return None

    def extract_article_meta(self, url):
        """
        Extract article content using trafilatura.
        """
        try:
            html = self._fetch_html(url)
            result = text_processor.analyze_meta(html)
            if not result:
                logger.warning("trafilatura could not extract content")
                return None

            json_result = json.loads(result)

            return {
                "title": json_result.get("title"),
                "link": url,
                "summary": json_result.get("raw_text"),
                "publishedAt": self.parse_date(json_result.get("date")),
                "updatedAt": self.parse_date(json_result.get("last-modified")),
                "id": sha256(url.encode("utf-8")).hexdigest(),
                "author": json_result.get("author"),
            }
        except Exception as e:
            logger.error(f"Error extracting article content for {url}: {e}")
            return None

    @staticmethod
    def generate_markdown_from_url(url, *, verify=True):
        """
        Fetches a webpage and converts its content into Markdown using trafilatura.
        """
        try:
            html_content = HtmlFetcher._fetch_html(url, verify=verify)
            markdown = text_processor.convert_from_html_to_markdown(html_content)
            if markdown:
                return markdown
            else:
                logger.warning("Failed to extract content as Markdown for URL: %s", url)
                raise Exception()
        except Exception as e:
            logger.error("Error fetching or converting URL to Markdown: %s", str(e))
            raise e

    @staticmethod
    def _fetch_html(url, *, verify=True):
        """
        Fetch the HTML content of a given URL.
        """
        response = requests.get(url, timeout=10, verify=verify)
        response.raise_for_status()
        return response.text

    @staticmethod
    def parse_date(date_str):
        """
        Helper method to parse dates into ISO 8601 format.
        """
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).isoformat()
        except ValueError:
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").isoformat()
            except ValueError:
                logger.warning(f"Could not parse date: {date_str}")
                return None

    @staticmethod
    def sanitize_link(url):
        """
        Remove unnecessary parameters like tracking IDs from the URL.
        """
        try:
            parsed_url = urlparse(url)
            query = parse_qs(parsed_url.query)
            # Remove common tracking parameters
            filtered_query = {k: v for k, v in query.items() if
                              k not in {"q", "query", "source", "referrer", "tracking", "utm_source", "utm_medium",
                                        "utm_campaign"}}
            sanitized_url = urlunparse(
                parsed_url._replace(query=urlencode(filtered_query, doseq=True))
            )
            return sanitized_url
        except Exception as e:
            logger.warning(f"Failed to sanitize URL {url}: {e}")
            return url
