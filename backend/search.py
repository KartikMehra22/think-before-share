import os
from tavily import TavilyClient


def search_evidence(claim: str, max_results: int = 3) -> dict:
    """
    Search the web for evidence related to a factual claim.
    Returns a dict with 'snippets' (list of str) and 'sources' (list of URLs).
    """
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

    return {"snippets": snippets, "sources": sources}
