# AI-Node Prompts (n8n)

Der klassische `LlmPrompter._build_prompt` (OpenAI-Pfad) liefert **ein JSON** mit Teaser, Langtext, Kategorien, Tags und Seriousness. Das eignet sich für **einen** „Basic LLM Chain“- oder „OpenAI“-Node mit strukturierter Ausgabe.

## System-Rolle (Vorschlag)

```
You are a creative summarization assistant and expert content analyst.
```

## User-Prompt (ein Schritt, JSON-Antwort)

Platzhalter: `{{ $json.content_md }}` bzw. in n8n den Markdown-Text aus dem vorherigen Node.

```
You are an expert content analyst and a content creator who transforms educational content into engaging and well-organized summaries. Your task is to analyze the following article and:
1. Provide a short teaser of no more than 200 characters to intrigue the reader.
2. Summarize the article in an engaging and concise tone, while maintaining its unique style (e.g., factual, humorous, or critical).
3. Categorize the article into one or more of the following categories: [factual information,expert opinions,debates and discussions,entertainment/personal,miscellaneous].
4. Assign a seriousness rating to the article based on its credibility and reliability:
   • High: Credible and well-founded (e.g., academic articles, scientific studies).
   • Medium: Solid, but subjective or less verified (e.g., expert opinions, journalistic articles).
   • Low: Poorly founded, polemical, or possibly inaccurate (e.g., Reddit discussions, blog rants).
5. Add relevant tags or keywords that describe the article content.

Respond in this exact format (valid JSON only, no markdown fences):
{
  "teaser": "...",
  "summary_long": "...",
  "category": ["..."],
  "tags": ["...", "..."],
  "seriousness_rating": "high"
}

Article Text:
<<<ARTICLE>>>
```

Wenn du **Alt-Text** aus der Data Table `article_enrichment` hast (vorheriger Markdown-Stand), kannst du wie im Python-Code einen zweiten Abschnitt **Old Text:** ergänzen und im JSON optional `"changes": "..."` verlangen.

## Nach dem AI-Node

1. **Code (Python oder JavaScript):** JSON aus der Antwort parsen (Code-Node `clean_json_response` aus `text_processor.py` nachbauen: Backticks entfernen).
2. Mit `article`-Feldern mergen → `build_ingest_body` / HTTP Request zu infl0.

## Mehrstufig (wie Ollama-Pfad im Repo)

Optional drei AI-Nodes: (1) Kategorie+Tags, (2) Teaser+`summary_long`, (3) `seriousness_rating` – Prompts stehen in `src/crawler/utils/llm_prompter.py` (`_build_categorizing_prompt`, `_build_teaser_and_summary_user_prompt`, `_build_serioussnessrating_prompt`).
