# AI Node Prompts

The crawler itself does not call an LLM in the production path. LLM processing happens in n8n AI Nodes. The prompt below works well with one AI/LLM node and a structured JSON output parser.

## System Message

```text
You are a creative summarization assistant and expert content analyst.
```

## User Message

Use the article Markdown from the previous node, for example `{{ $json.article.content_md }}`.

```text
You are an expert content analyst and a content creator who transforms educational content into engaging and well-organized summaries. Your task is to analyze the following article and:
1. Provide a short teaser of no more than 200 characters to intrigue the reader.
2. Summarize the article in an engaging and concise tone, while maintaining its unique style.
3. Categorize the article into one or more of the following categories: [factual information, expert opinions, debates and discussions, entertainment/personal, miscellaneous].
4. Assign a seriousness rating to the article based on its credibility and reliability:
   - high: credible and well-founded.
   - medium: solid, but subjective or less verified.
   - low: poorly founded, polemical, or possibly inaccurate.
5. Add relevant tags or keywords.

Always use the language of the article.

Respond in this exact format as valid JSON only, without Markdown fences:
{
  "teaser": "...",
  "summary_long": "...",
  "category": ["..."],
  "tags": ["...", "..."],
  "seriousness_rating": "high"
}

Article Text:
{{ $json.article.content_md }}
```

## After the AI Node

1. Parse JSON from the model response. If needed, use the logic from `tkcrawler.text.clean_json_response` to remove Markdown fences.
2. Merge enrichment fields with the item.
3. Call `build_ingest_body` before the HTTP request to infl0.

## Multi-Step Variant

The same work can be split into multiple AI nodes: categories and tags, teaser and long summary, and seriousness rating. Merge the intermediate fields into one flat enrichment object before calling `build_ingest_body`.
