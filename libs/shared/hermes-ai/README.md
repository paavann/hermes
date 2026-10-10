# Hermes AI — Shared Intelligence & Geocoding Library

The `hermes-ai` library centralizes all LLM orchestration, structured news/timeline extraction, token-bucket rate limiting, vector embedding generation, and grounded geospatial resolution for Project Hermes.

Both `hermes-api` and `hermes-worker` consume `hermes-ai` as a shared workspace dependency, ensuring unified extraction prompts, standardized schemas, and shared rate-limiting controls.

---

## Key Capabilities

### 1. Dual-Tier LLM Orchestration & Failover
- **LiteLLM Router**: Automatically load-balances and routes extraction requests between primary and fallback inference providers.
- **Semantic Schema Fallback**: Automatically falls back to secondary models if a primary model returns malformed JSON or invalid schema structures.

### 2. High-Throughput Token Bucket Rate Limiting
- **`TbRateLimiter`**: An asynchronous, thread-safe token-bucket algorithm that precisely caps requests-per-minute (RPM) across chat completions and embedding generation.

### 3. Structured Information Extractors
- **`EventExtractor`**: Batches unstructured RSS articles, extracts location names and categories, validates against predefined taxonomy, and assigns tactical category colors.
- **`TlExtractor`**: Evaluates news headlines for Wikipedia timeline viability and extracts chronological milestone graphs (nodes and causal edges) from Wikipedia prose.

### 4. Zero-Hallucination Geocoding Shield
- **`GeocodingService`**: Converts extracted place names into verified coordinates using OpenStreetMap Nominatim.
- **`NominatimResilienceManager`**: Enforces strict request pacing (1.5s minimum interval), handles HTTP 429 backoff, and trips an internal circuit breaker under sustained rate limits.
- **Protocol-Based Cache**: Connects to any database cache implementing `GeocodeCacheProtocol` without hard dependencies on ORM models.

---

## Usage Example

```python
from hermes_ai import (
    AiConfig,
    ArticleInput,
    GeocodingService,
    HermesAiClient,
)

# 1. Initialize configuration
config = AiConfig(
    primary_model="mistral/ministral-8b-latest",
    primary_api_key="your-api-key",
    fallback_model="nvidia_nim/meta/llama-3.1-70b-instruct",
    fallback_api_key="your-fallback-key",
    rpm_limit=60,
)

# 2. Initialize client
client = HermesAiClient(config)

# 3. Extract events from articles
articles = [
    ArticleInput(
        title="Major Treaty Signed in Geneva",
        content="Diplomats concluded an agreement in Geneva today.",
    )
]

events = await client.extract_events(articles)
for event in events:
    if event:
        print(event.headline, event.location_name, event.category_color)
```

---

## Testing & Linting

```bash
# Run test suite
npx nx test hermes-ai

# Run linter
npx nx lint hermes-ai
```
