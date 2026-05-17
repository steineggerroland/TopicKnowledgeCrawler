# infl0 Crawler Ingest API

TopicKnowledgeCrawler sends processed content items to infl0 through the crawler
ingest endpoint.

Endpoint:

```http
POST /api/crawler/ingest
Content-Type: application/json
Authorization: Bearer <crawler-api-key>
```

The payload is flat JSON. `crawlKey` identifies the subscribed source in infl0.
The remaining fields describe one content item. Historically these items were
all articles; the contract now distinguishes item kinds via `item_kind`.

Current item kinds:

- `article`: RSS/Atom articles and HTML pages.
- `episode`: podcast episodes from `rss+podcast` feeds.
- `section`: stable Markdown sections split from long-form parent items.

Unknown future item kinds should not be invented by infl0. They should be added
to this contract first.

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `crawlKey` | string | Stable source key shared by infl0 and TopicKnowledgeCrawler. |
| `id` | string | Stable crawler-generated item id. |
| `title` | string or null | Display title. |
| `link` | string | Human-facing canonical item URL. |
| `item_kind` | string | `article`, `episode` or `section`. Defaults to `article` for older payloads. |

## Common optional fields

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string or null | Source-provided summary or description. |
| `author` | string or null | Author, creator or podcast author. |
| `publishedAt` | ISO/RSS date string or null | Source publication timestamp. |
| `updatedAt` | ISO/RSS date string or null | Source update timestamp. |
| `content_md` | string or null | Markdown body used for reading and LLM enrichment. |
| `source_type` | string or null | Source type such as `rss`, `html`, `rss+podcast`. |
| `tld` | string or null | Registered source domain. |
| `content_hash` | string or null | Hash over `content_md`. |
| `parent_item_id` | string or null | Parent content id for split sections. |
| `position` | number or null | 1-based position for split sections. |
| `teaser` | string or null | LLM teaser. Applies to all item kinds. |
| `summary_long` | string or null | LLM summary. Applies to all item kinds. |
| `category` | string[] or null | LLM categories. |
| `tags` | string[] or null | LLM tags. |
| `seriousness_rating` | string or null | LLM reliability/seriousness rating. |

## Article payload

Articles usually use the common fields only. infl0 should render these as normal
reader cards.

Example:

[`docs/examples/ingest/article.json`](examples/ingest/article.json)

## Podcast episode payload

Podcast episodes use `item_kind: "episode"` and may include additional media
metadata. infl0 should store these fields and render episodes differently from
plain text articles, for example with audio duration, source episode link,
direct media link and chapter navigation.

| Field | Type | Description |
|-------|------|-------------|
| `media_url` | string or null | Direct audio/media URL from RSS enclosure. |
| `media_type` | string or null | Media MIME type, for example `audio/mpeg`. |
| `media_length_bytes` | number or null | Enclosure size in bytes. |
| `duration_seconds` | number or null | Episode duration in seconds. |
| `episode_number` | number or null | Podcast episode number. |
| `season_number` | number or null | Podcast season number. |
| `episode_type` | string or null | iTunes episode type such as `full`, `trailer`, `bonus`. |
| `explicit` | string/boolean or null | Source explicit flag as provided by the feed. |
| `subtitle` | string or null | Episode subtitle. |
| `image_url` | string or null | Episode image URL. |
| `categories` | string[] or null | Source categories/tags. |
| `shownotes_md` | string or null | Markdown shownotes derived from feed content/description. |
| `chapters_url` | string or null | Podcasting 2.0 chapters document URL. |
| `chapters_type` | string or null | Chapters MIME type. |
| `chapters` | object[] or null | Parsed chapter markers. |
| `chapters_fetch_error` | string or null | Non-fatal chapter fetch/parse error. |
| `transcript_url` | string or null | Transcript document URL when advertised. |
| `transcript_type` | string or null | Transcript MIME type. |
| `transcript_md` | string or null | Transcript text normalized to Markdown/plain text when fetched. |
| `transcript_fetch_error` | string or null | Non-fatal transcript fetch/parse error. |

`link` is still the human-facing episode page. `media_url` is the direct media
asset and should not replace `link` in labels or canonical URLs.

For episodes, `content_md` is assembled from feed text before any detail-page
fallback. Rich feed content such as `content:encoded` wins. If rich content is
missing, the crawler uses RSS description as shownotes and appends
`itunes:summary`/`summary` when distinct. The episode page is fetched only when
the feed does not provide usable text.

Transcripts are optional metadata for this phase. `transcript_md` is stored
beside the episode when `transcript_url` can be fetched, but it is not merged
into `content_md`; enrichment should treat `content_md` as the primary summary
input and use transcripts only when a workflow explicitly opts into that.

Chapter objects use this normalized shape:

| Field | Type | Description |
|-------|------|-------------|
| `start_seconds` | number | Chapter start offset in seconds. |
| `title` | string | Chapter title. |
| `url` | string, optional | Optional chapter URL. |
| `image_url` | string, optional | Optional chapter image. |

Example:

[`docs/examples/ingest/episode.json`](examples/ingest/episode.json)

## Section payload

Sections use `item_kind: "section"` and are produced by `segment_content` for
PDF/EPUB-style or otherwise long-form content. They preserve the parent
canonical `link`, use their own stable `id`, and point back to the source item
with `parent_item_id`.

Example:

[`docs/examples/ingest/section.json`](examples/ingest/section.json)

## JSON Schema

The machine-readable contract lives at
[`docs/schemas/ingest-item.schema.json`](schemas/ingest-item.schema.json).

The schema allows `article`, `episode` and `section` payloads. It is intentionally
strict at the top level so that accidental n8n-internal fields do not silently
become public API.

## Compatibility notes

Older infl0 versions may ignore unknown episode fields. Once infl0 supports
episodes, it should persist the episode metadata and use `item_kind` for
rendering decisions.

The n8n workflow still uses field names such as `article` and `article_id`
internally. That is workflow compatibility only. The public ingest payload is
the flat object documented here.
