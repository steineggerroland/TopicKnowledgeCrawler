import json
import os
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from trafilatura import extract

from crawler.utils.llm_prompter import LlmPrompter
from crawler.utils.logger import getLogger
from crawler.utils.text_processor import clean_json_response

# Initialize logger
logger = getLogger(__name__)

load_dotenv()
LLM_PROVIDER_NAME = os.getenv("LLM_PROVIDER", "ollama")  # Default to OpenAI

# Initialize the LLM prompter
llm_prompter = LlmPrompter(LLM_PROVIDER_NAME)
lb = '\n'  # line break for f-string


class LlmBasedSourceAnalyzer:
    """
    Uses an LLM to recursively analyze HTML pages, following referrer selectors when needed.
    """

    def analyze_html_structure(self, url: str) -> Dict[str, Any]:
        """
        Analyzes the HTML structure and identifies the configuration for parsing articles.
        """
        html = self.fetch_html(url)
        logger.info(f"Asking GPT to analyze {url}")

        # Use GPT to analyze the main page
        analysis = self.analyze_articles_page(html)

        try:

            if not analysis.get("articles_found"):
                raise Exception(f"Website {url} does not contain articles.")

            if not analysis.get("article_selector"):
                raise Exception(f"Bogus response from GPT for URL {url}: {analysis}")

            logger.info(f"GPT identified articles on {url}. Building configuration.")
            parser_config = {
                "configuration": {
                    "article_selector": analysis["article_selector"]
                }
            }

            if not analysis.get("title_selector"):
                raise Exception(f"No title_selector found for URL {url}: {analysis}")

            # Process main page links to identify the main article page
            soup = BeautifulSoup(html.content, "html.parser")
            articles_html = soup.select(analysis["article_selector"], limit=4)
            first_article = articles_html.pop()
            title = first_article.select_one(analysis["title_selector"]).text.strip()

            # Handle main page link identification
            logger.info("Finding the main page for the first article.")
            main_page_info = self.identify_main_page(
                url=url, article_html=first_article.decode_contents(), representative_title=title,
                other_article_html_examples=list(map(lambda a: a.decode_contents(), articles_html))
            )
            if main_page_info:
                parser_config["configuration"]["main_page_anchor_selector"] = main_page_info["anchor_selector"]

            return parser_config

        except json.JSONDecodeError:
            raise Exception(f"Failed to decode GPT response for URL: {url}")
        except Exception as e:
            raise Exception(f"Failed to analyze HTML structure for {url}: {str(e)}") from e

    def analyze_articles_page(self, html):
        prompt = self.create_main_prompt(html.text)
        response = llm_prompter.query(prompt, model_size='large')
        cleaned_response = clean_json_response(response)
        analysis = json.loads(cleaned_response)
        return analysis

    def identify_main_page(self, url: str, article_html: str, representative_title: str,
                           other_article_html_examples: List[str]) -> Dict[
        str, Any]:
        """
        Identifies the main page of an article by following links and analyzing content with trafilatura.
        """
        soup = BeautifulSoup(article_html, "html.parser")
        links = soup.find_all("a", href=True)

        for link in links:
            if link.text.strip() == "":
                continue
            href = link["href"]
            full_url = urljoin(url, href)
            logger.info(f"Checking link: {full_url}")

            # Fetch content from the link
            response = requests.get(full_url)
            if response.status_code != 200:
                continue

            # Extract content with trafilatura
            json_extraction = extract(response.text, include_formatting=True, include_links=True, include_images=True,
                                      include_tables=True, output_format='json', with_metadata=True)
            extracted_content = json.loads(json_extraction)
            if not extracted_content or "title" not in extracted_content:
                continue
            page_title = extracted_content["title"]
            if self.titles_are_similar(representative_title, page_title):
                # Use GPT to refine the anchor selector
                logger.info(f"Main page identified: {full_url}. Refining anchor selector.")
                response = llm_prompter.query(self.refine_anchor_selector(known_article_block=article_html,
                                                                          known_anchor_html=link.decode_contents(),
                                                                          additional_blocks=other_article_html_examples),
                                              model_size="large")
                anchor_selector = json.loads(clean_json_response(response)).get("anchor_selector", "")
                return {"url": full_url, "anchor_selector": anchor_selector}

        logger.warning("No main page identified.")
        return {}

    def create_main_prompt(self, html: str) -> list:
        """
        Create the LLM prompt for analyzing the main HTML structure.
        """
        prompt = f"""
        You are assisting in analyzing an HTML document to help an automated HTML parser process the page.
        The parser uses CSS selectors in Python to extract the necessary information.

        The goal is to extract articles from the page. Each article has the following attributes:
        - **Title:** The title of the article, which must be identified by a `title_selector`.
        - **Article block:** The overall block of the article on the page, identified by an `article_selector`.

        **Specific guidelines:**
        1. Provide an `article_selector` to iterate over each article on the page.
        2. Provide a `title_selector` to extract the title from within the article block.
        3. Ensure the CSS selectors are short, simple, and concise.
        4. Only include selectors when confident they fully represent the corresponding attribute.
        5. Pseudo-class `:has(<selector>)` can be used to simplify selectors.

        **Response Format:**
        ```json
        z.object({{
            article_selector: z.string().describe('Selector for all articles on the page used for iteration'),
            title_selector: z.string().describe('Selector for the title of the article applied within the article selector'),
            articles_found: z.boolean().describe('"true" if articles were found, otherwise "false"')
        }})
        ```

        Example scenarios:
        1. If the articles are clearly defined blocks on the page, provide an `article_selector` to iterate over them.
        2. Ensure the `title_selector` precisely identifies the title within the article block.
        3. If no articles are found on the page, set `articles_found` to `false`.

        Here is the HTML document:
        ```html
        {html}
        ```
        """
        return [
            {"role": "system",
             "content": "You are an assistant helping analyze HTML documents for article extraction."},
            {"role": "user", "content": prompt}
        ]

    def refine_anchor_selector(self, known_article_block: str, known_anchor_html: str,
                               additional_blocks: List[str]) -> list:
        """
        Uses GPT to refine the anchor selector for articles based on a known example and structurally similar blocks.
        """
        prompt = f"""
You are assisting in analyzing an HTML block to determine the CSS selector for an anchor (`<a>` tag) linking to the main page of an article.

The goal is to find a **short and generic CSS selector** that targets only the `<a>` tag containing the article link.

### Key Guidelines:
1. **Target Only `<a>`**: The selector must select the `<a>` tag linking to the main page of the article. It must not select any child elements (e.g., `<h2>` or `<h3>`).
2. **Structural Elements**: Focus on structural tags such as `<h1>`, `<h2>`, `<h3>`, or semantic landmarks near the anchor. Use :has(<selector>) to select an anchor containing specific tags.
3. **Avoid Specific Attributes**: Do not rely on `href` values, unique classes, or IDs. Instead, leverage structural relationships (e.g., `:has(<selector>)` or `>`, `~`).
4. **Short and Concise**: The CSS selector must be as short and robust as possible, avoiding deeply nested paths.

### Example Context:
Below is the known HTML block for an article preview. The anchor linking to the main page of the article has been identified.

#### Known Example:
```html
{known_article_block}
```
The target anchor is: `{known_anchor_html}`

Below are additional article blocks. Use them to generalize the selector.

#### Additional Examples:
{''.join([f'{lb}```html{lb}{block}{lb}```{lb}' for block in additional_blocks])}

### Expected Answer:
Answer in this exact JSON format:

```json
{{
    "anchor_selector": "CSS_SELECTOR"
}}
```

Replace CSS_SELECTOR with the appropriate CSS selector. The selector must:
	•	Target only the <a> tag in the known example.
	•	Work generically for structurally similar blocks.
	•	Use structural relationships, not specific attributes.

Validation Examples:

	1.	Selector a > h2 is invalid because it targets the <h2>, not the <a> tag.
	2.	Selector div > a is valid if it targets the <a> tag and works for all provided examples.
	3.	Selector a:has(h2) is valid if the <a> contains an <h2>.
"""
        return [
            {"role": "system",
             "content": "You are an assistant helping analyze HTML documents for article extraction."},
            {"role": "user", "content": prompt}
        ]

    def fetch_html(self, url: str):
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch HTML content. Status code: {response.status_code}")
        return response

    def titles_are_similar(self, title1: str, title2: str) -> bool:
        """
        Compares two titles for similarity using fuzzy matching.
        """
        return fuzz.ratio(title1.lower(), title2.lower()) > 80
