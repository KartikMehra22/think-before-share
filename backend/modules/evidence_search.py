import os
import json
import logging
from tavily import TavilyClient

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
CACHE_FILE = os.path.join(CACHE_DIR, "search_cache.json")

def _normalize_claim(claim: str) -> str:
    """Normalize the claim to use as a cache key by lowercasing and stripping whitespace."""
    return claim.strip().lower()

def _load_cache() -> dict:
    """Load the cache from search_cache.json, handling missing and malformed cases."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(
            f"Failed to parse search cache file at {CACHE_FILE}: {e}. Falling back to empty cache."
        )
        return {}

def _save_cache(cache: dict):
    """Save the cache dictionary to search_cache.json, creating parent directory if needed."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to write search cache file at {CACHE_FILE}: {e}")

def search_evidence(claim: str, max_results: int = 3) -> dict:
    """
    Search the web for evidence related to a factual claim.
    Returns a dict with 'snippets' (list of str) and 'sources' (list of URLs).
    Caching is enabled by default unless USE_CACHE=false in environment variables.
    """
    use_cache_str = os.environ.get("USE_CACHE", "true").lower()
    use_cache = use_cache_str not in ("false", "0", "no")

    normalized_claim = _normalize_claim(claim)

    if use_cache:
        cache = _load_cache()
        if normalized_claim in cache:
            logger.info(f"Search cache hit for claim: '{claim}'")
            return cache[normalized_claim]

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY is not set in environment variables.")

    client = TavilyClient(api_key=api_key)

    # Use a fact-checking oriented search query
    query = f'fact check: "{claim}"'

    response = client.search(
        query=query,
        search_depth="basic",
        max_results=max_results,
        include_answer=True,
    )

    snippets = []
    sources = []

    # Include Tavily's synthesized answer if available
    if response.get("answer"):
        snippets.append(f"Tavily Summary: {response['answer']}")
        sources.append("tavily-synthesis")

    # Include individual search result snippets
    for result in response.get("results", []):
        content = result.get("content", "").strip()
        url = result.get("url", "")
        if content:
            snippets.append(content[:600])  # Limit each snippet
            sources.append(url)

    result_data = {"snippets": snippets, "sources": sources}

    if use_cache:
        # Reload cache to avoid race conditions/overwriting recent writes in same/separate process
        cache = _load_cache()
        cache[normalized_claim] = result_data
        _save_cache(cache)

    return result_data

