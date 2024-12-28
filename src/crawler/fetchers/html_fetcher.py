import hashlib

import requests
from bs4 import BeautifulSoup


def fetch_html_content(url, source):
    if 'medium.com' in url:
        return fetch_html_articles(url)

    try:
        return fetch_html_articles(url)
    except:
        raise Exception(f"Unsupported URL: {url}")


def fetch_html_articles(url):
    """
    Fetches and extracts multiple articles from an HTML page.
    Returns a list of dictionaries containing title, link, and summary.
    """
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch HTML content. Status code: {response.status_code}")

    soup = BeautifulSoup(response.content, "html.parser")
    articles = []

    for article in soup.find_all("article"):
        # Extract title and link
        title_tag = article.find("h2")
        title = title_tag.get_text(strip=True) if title_tag else None
        link_tag = title_tag.find("a", href=True) or article.find("a", href=True)
        link = link_tag["href"] if link_tag else None

        # Extract summary text
        summary_tag = article.find("h3")
        summary = summary_tag.get_text(strip=True) if summary_tag else None

        # Skip entries without a title or link
        if not title or not link:
            continue

        # Generate a unique ID based on the link
        article_id = hashlib.sha256(link.encode("utf-8")).hexdigest()

        articles.append({
            "id": article_id,
            "title": title,
            "link": link,
            "summary": summary
        })

    return articles
