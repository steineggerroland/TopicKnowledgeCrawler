import json
import time
from typing import Any

import os
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup

from openai import OpenAI

from src.crawler.utils.sanitize import clean_json_response

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

class LlmBasedSourceAnalyzer:
    """
    Uses an LLM to recursively analyze HTML pages, following referrer selectors when needed.
    """
    def analyze_html_structure(self, url, max_depth=3):
        """
        Recursively analyzes the HTML structure of a webpage and follows referrer selectors.
        Returns a dict that can be used to extract article information from the webpage.
        """
        # Fetch the HTML content of the current URL
        html = self.fetch_html(url)
        prompt = self.create_main_prompt(html.text)

        # Query the LLM to analyze the current page
        response = self.query_llm(prompt)
        cleaned_response = clean_json_response(response)

        try:
            analysis = json.loads(cleaned_response)

            if not analysis.get("articles_found"):
                raise Exception("Website %s seems not to contain any articles" %(url))
            if not analysis.get("article_selector") or not analysis.get("articles"):
                raise Exception("Answer of LLM for URL %s seems to be bogus: %s" %(url, analysis))

            parser_configuration = dict()
            parser_configuration['article_selector'] = analysis["article_selector"]

            expected_selectors = ["title_selector", "content_selector", "link_selector"]

            article = analysis.get("articles")
            parser_configuration['articles'] = {}
            for selector in article:
                if selector in expected_selectors:
                    parser_configuration['articles'][selector] = article[selector]
                    expected_selectors.remove(selector)

            if any(expected_selectors):
                parser_configuration['articles']['referrers'] = []
                soup = BeautifulSoup(html.content, "html.parser")
                first_article = soup.find_all(analysis.get("article_selector"))[0]
                for referrer_selector in first_article.find_all(article.get("referrer_selectors")):
                    referred_url = extract_url(first_article, referrer_selector)
                    visited_urls = set(url)
                    sub_analysis = self._recursive_analyze(referred_url, visited_urls, max_depth, expected_selectors)
                    if sub_analysis:
                        sub_analysis["selector"] = referrer_selector
                        parser_configuration['articles']['referrers'].append(sub_analysis)
                    if not any(expected_selectors):
                        break

            if any(expected_selectors):
                raise Exception("Could not find selectors for all article attributes. Missing selectors: %s" %(expected_selectors))
        except json.JSONDecodeError:
            raise Exception("Failed to decode LLM response for URL: %s" % url)
        except Exception as e:
            raise Exception("Failed to analyze the HTML structure of %s" %(url)) from e

        return analysis
    def _recursive_analyze(self, url, visited_urls, depth_remaining, expected_selectors) -> dict[Any, Any] | None:
        """
        Helper method to perform the recursive analysis.
        Recursively follows referrer selectors to extract missing information.
        """
        if depth_remaining <= 0 or url in visited_urls:
            return None  # Stop recursion if max depth is reached or URL already visited

        visited_urls.add(url)

        # Fetch the HTML content of the referrer page
        html = self.fetch_html(url)
        soup = BeautifulSoup(html.content, "html.parser")

        # Create the prompt for analyzing the referrer page
        title_missing = "title_selector" in expected_selectors
        content_missing = "content_selector" in expected_selectors
        link_missing = "link_selector" in expected_selectors

        prompt = self.create_article_prompt(
            html=html.text,
            title_missing=title_missing,
            content_missing=content_missing,
            link_missing=link_missing,
        )

        # Query the LLM for analysis
        response = self.query_llm(prompt)
        cleaned_response = clean_json_response(response)

        try:
            analysis = json.loads(cleaned_response)

            # Check for new selectors and update the expected selectors list
            new_data = {}
            for key in list(expected_selectors):
                if key in analysis:
                    new_data[key] = analysis[key]
                    expected_selectors.remove(key)

            # If the referrer selectors exist, follow them recursively
            if any(expected_selectors) and "referrer_selectors" in analysis:
                for referrer_selector in analysis["referrer_selectors"]:
                    link = extract_url(soup, referrer_selector)
                    # Perform recursive analysis on each referrer link
                    sub_analysis = self._recursive_analyze(
                        url=link,
                        visited_urls=visited_urls,
                        depth_remaining=depth_remaining - 1,
                        expected_selectors=expected_selectors,
                    )
                    if sub_analysis:
                        sub_analysis["selector"] = referrer_selector
                        new_data['referrers'].append(sub_analysis)
                    if not any(expected_selectors):
                        break

            return new_data if new_data else None
        except json.JSONDecodeError:
            raise Exception("Failed to decode LLM response for URL: %s" % url)
        except Exception as e:
            raise Exception(f"Error during recursive analysis of {url}: {str(e)}")


    def fetch_html(self, url):
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch HTML content. Status code: {response.status_code}")
        return response

    def create_main_prompt(self, html):
        """
        Create the LLM prompt for analyzing the main HTML structure.
        """
        return f"""
        Du hilfst bei der Analyse eines HTML-Dokuments, damit ein HTML-Parser nach der Analyse eine HTML-Seite automatisiert verarbeiten kann. 
        Der Parser wird per HTML-Selektor in python die notwendige Information extrahieren. Die HTML-Selektoren sollten möglichst reduziert und einfach formuliert sein.
        Aus der HTML-Webseite sollen Artikel mit "Titel", "Inhalt" und einem "Link" extrahiert werden. 
        Der Artikelinhalt könnte bereits auf dieser Seite vorhanden sein oder es wird eine Unterseite verlinkt, z. B. durch "Mehr lesen".
        
        Antworte im JSON-Format mit exakt folgendem JSON-Schema:
        z.object({{
            article_selector: z.string().optional().describe('Selector for all articles on the page used for iteration'),
            articles: z.object({{
              title_selector: z.string().optional().describe('Selector for the title of the article applied within the article selector'),
              content_selector: z.string().optional().describe('Selector for the content of the article applied within the article selector'),
              link_selector: z.string().optional().describe('Selector for the anchor having a "href" referring to THE article\'s page'),
              referrer_selectors: z.array(z.string().optional().describe('Selector for an anchor having a "href" referring to a page where additional information on the article might be found')).optional().describe('Necessary if not all information on an article could be found on the page and, therefore, at least one selector is missing.')
            }}).optional().describe('If the "article_selector" is present, this describes the handling within the articles'),
            articles_found: z.boolean().describe('"true", if articles were found and the selector is set, else "false"')
        }})
        
        Bitte füge die optionalen "*_selector" nur hinzu, wenn du dir sehr sicher bist, dass der Text des selektierten Elements das Attribute des Artikels vollständig repräsentiert.
        Für die "referrer_selector" wird davon ausgegangen, dass genau ein "a" gefunden und gefolgt wird. Dieser Selektor sollte also möglichst präzise sein. Du solltest auch nur "referrer_selector" verwenden, bei denen du die fehlenden Attribute des Artikels vermutest.

        Hier ist das HTML-Dokument:
        ```html
        {html}
        ```
        """

    def create_article_prompt(self, html, title_missing, content_missing, link_missing):
        """
        Create a specific prompt for analyzing a referrer page for a single article.
        """
        return f"""
                Du hilfst bei der Analyse eines HTML-Dokuments, damit ein HTML-Parser nach der Analyse eine HTML-Seite automatisiert verarbeiten kann. 
                Der Parser wird per HTML-Selektor in python die notwendige Information extrahieren. Die HTML-Selektoren sollten möglichst reduziert und einfach formuliert sein.
                Aus der HTML-Webseite sollen folgende Informationen des Artikels extrahiert werden:
                {"* Titel" if title_missing else ""}
                {"* Inhalt " if content_missing else ""}
                {"* Link zur Artikelseite " if link_missing else ""}
                Falls die gesuchten Inhalte nicht auf der Seite vorhanden sind, verweist sie möglicherweise zu weiteren relevanten Seiten, z. B. durch einen "Mehr lesen"-Link.

                Antworte im JSON-Format mit exakt folgendem JSON-Schema:
                z.object({{
                  {"title_selector: z.string().optional().describe('Selector for the title of the article applied within the article selector')," if title_missing else ""}
                  {"content_selector: z.string().optional().describe('Selector for the content of the article applied within the article selector')," if content_missing else ""}
                  {"link_selector: z.string().optional().describe('Selector for the anchor having a 'href' referring to THE article\'s page')," if link_missing else ""}
                  referrer_selectors: z.array(z.string().optional().describe('Selector for an anchor having a "href" referring to a page where additional information on the article might be found')).optional().describe('Necessary if not all information on an article could be found on the page and, therefore, at least one selector is missing.')
                }})
                
                Bitte füge die optionalen JSON-Attribute für "selector" nur hinzu, wenn du dir recht sicher bist, dass der Text des selektierten Elements das Attribute des Artikels vollständig repräsentiert.
                Für die "referrer_selector" wird davon ausgegangen, dass genau ein "a" gefunden und gefolgt wird. Dieser Selektor sollte also möglichst präzise sein. Du solltest auch nur "referrer_selector" verwenden, bei denen du die fehlenden Attribute des Artikels vermutest.  

                Hier ist das HTML-Dokument:
                ```html
                {html}
                ```
                """

    def query_llm(self, prompt):
        """
        Queries the LLM for analyzing the HTML.
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        raw_content = response.choices[0].message.content
        print(raw_content)
        time.sleep(60)
        return raw_content



def extract_url(element, selector):
    """
    Extracts url using a given CSS selector on the given element.
    """
    a = element.find(selector)
    return a["href"] if "href" in a.attrs else None

if __name__ == "__main__":
    print(LlmBasedSourceAnalyzer().create_main_prompt('***HTML-PLACEHOLDER***'))