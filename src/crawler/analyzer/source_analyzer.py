import requests
from src.crawler.analyzer.llm_based_source_analyzer import LlmBasedSourceAnalyzer
from src.crawler.utils.logger import getLogger

# Initialize logger
logger = getLogger(__name__)

class SourceAnalyzer:
    """
    Determines the type of a source (RSS or HTML) and analyzes its structure if necessary.
    """

    def __init__(self):
        self.llm_analyzer = LlmBasedSourceAnalyzer()

    def analyze_source(self, source):
        """
        Analyzes the source and updates its type or structure.
        """
        url = source["url"]

        try:
            response = requests.get(url, timeout=10)
            content_type = response.headers.get("content-type", "")

            if "xml" in content_type or "rss" in content_type:
                source["type"] = "rss"
            elif "html" in content_type:
                source["type"] = "html"
                if "selectors" not in source:
                    logger.info("Performing detailed analysis for HTML source: %s", url)
                    source["configuration"] = self.llm_analyzer.analyze_html_structure(url)["configuration"]
            else:
                raise ValueError(f"Unknown content type: {content_type}")

        except Exception as e:
            logger.error("Failed to analyze source '%s': %s", url, str(e))

        return source