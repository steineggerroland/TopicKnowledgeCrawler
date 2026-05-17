# AI Node Prompts

The crawler itself does not call an LLM in the production path. LLM processing happens in n8n AI Nodes. Python steps prepare model input and consume structured JSON output.

There are two LLM call sites in the current workflow:

1. HTML selector generation for sources that need listing-page configuration.
2. Item enrichment for finalized article or podcast episode content.

## HTML Selector Generation

Use this call after `prepare_html_analysis`. That step fetches and compacts the HTML page, then writes the full suggested prompt into `html_analysis_prompt`.

### Input

Use `{{ $json.html_analysis_prompt }}` as the user message, or recreate the same shape from:

- `{{ $json.html_analysis_url }}`
- `{{ $json.html_analysis_input }}`

### Expected Output

Return valid JSON only:

```json
{
  "article_selector": "article",
  "main_page_anchor_selector": "h2 > a",
  "confidence": "high",
  "notes": "The listing contains repeated article cards with heading links."
}
```

### Prompt Outline

```text
Analyze this HTML listing page and identify CSS selectors for article discovery.

Return valid JSON only, without markdown fences, in exactly this shape:
{
  "article_selector": "CSS selector matching each repeated article/listing item",
  "main_page_anchor_selector": "CSS selector, relative to each article item, matching the <a> element for the article detail page",
  "confidence": "high|medium|low",
  "notes": "short explanation"
}

Rules:
- Prefer short structural selectors.
- The anchor selector must match an <a> element, not a child heading.
- You may use :has(...) when it makes the selector simpler.
- Do not rely on tracking query parameters or unique article URLs.
- If no articles are found, return empty selector strings and confidence "low".
```

### After the AI Node

1. Pass the model output as `html_analysis_result`, `output`, `text` or `response`.
2. Call `apply_html_analysis`.
3. Call `validate_source_configuration`.

## Item Enrichment

Use this call after `limit_llm_items`. The prompt below works well with one AI/LLM node and a structured JSON output parser.

### System Message

```text
You are a creative summarization assistant and expert content analyst.
```

### User Message

Use the finalized item content from the previous node, for example `{{ $json.article.content_md }}`. For podcast episodes, this may contain rich feed content, shownotes plus summary, or a detail-page fallback. Transcript URLs remain metadata unless a separate workflow fetches transcript text.

```text
You are an expert content analyst and a content creator who transforms educational content into engaging and well-organized summaries. Your task is to analyze the following content item and:
1. Provide a short teaser of no more than 200 characters to intrigue the reader.
2. Summarize the item in an engaging and concise tone, while maintaining its unique style.
3. Categorize the item into one or more of the following categories: [factual information, expert opinions, debates and discussions, entertainment/personal, miscellaneous].
4. Assign a seriousness rating to the item based on its credibility and reliability:
   - high: credible and well-founded.
   - medium: solid, but subjective or less verified.
   - low: poorly founded, polemical, or possibly inaccurate.
5. Add relevant tags or keywords.

Always use the language of the item.

Respond in this exact format as valid JSON only, without Markdown fences:
{
  "teaser": "...",
  "summary_long": "...",
  "category": ["..."],
  "tags": ["...", "..."],
  "seriousness_rating": "high"
}

Item Kind:
{{ $json.article.item_kind || "article" }}

Item Text:
{{ $json.article.content_md }}
```

### After the AI Node

1. Parse JSON from the model response. If needed, use the logic from `tkcrawler.text.clean_json_response` to remove Markdown fences.
2. Merge enrichment fields with the item.
3. Call `build_ingest_body` before the HTTP request to infl0.

### Multi-Step Variant

The same work can be split into multiple AI nodes: categories and tags, teaser and long summary, and seriousness rating. Merge the intermediate fields into one flat enrichment object before calling `build_ingest_body`.
